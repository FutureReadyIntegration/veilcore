from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Anchor ledger to the installed package directory (kept for compatibility)
PACKAGE_ROOT = Path(__file__).resolve().parent

# Active ledger path (kept as-is from your original)
LEDGER_PATH = Path("/opt/veil_os/ledger.json")

# Where we quarantine legacy/unmappable blocks during migration
LEGACY_QUARANTINE_PATH = Path("/opt/veil_os/ledger_legacy.json")


# ----------------------------
# Canonical hashing
# ----------------------------

def _canonical_block_for_hash(
    *,
    index: int,
    organ: str,
    tier: str,
    timestamp: float,
    prev_hash: str,
) -> Dict[str, Any]:
    # Canonical set of fields used for hashing (must remain stable!)
    return {
        "index": index,
        "organ": organ,
        "tier": tier,
        "timestamp": timestamp,
        "prev_hash": prev_hash,
    }


def hash_block(block: Dict[str, Any]) -> str:
    """
    Deterministic hash of canonical block fields.
    """
    return hashlib.sha256(json.dumps(block, sort_keys=True).encode()).hexdigest()


# ----------------------------
# IO helpers
# ----------------------------

def load_ledger() -> List[Dict[str, Any]]:
    if LEDGER_PATH.exists():
        try:
            data = json.loads(LEDGER_PATH.read_text())
            if not isinstance(data, list):
                raise RuntimeError(f"❌ Ledger JSON is not a list: {LEDGER_PATH}")
            return data
        except json.JSONDecodeError as e:
            raise RuntimeError(f"❌ Ledger file is not valid JSON: {LEDGER_PATH}") from e
    return []


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    tmp.replace(path)


def save_ledger(ledger: List[Dict[str, Any]]) -> None:
    _atomic_write_text(LEDGER_PATH, json.dumps(ledger, indent=2))


def _load_json_list(path: Path) -> List[Dict[str, Any]]:
    if path.exists():
        try:
            data = json.loads(path.read_text())
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
    return []


def _save_json_list(path: Path, items: List[Dict[str, Any]]) -> None:
    _atomic_write_text(path, json.dumps(items, indent=2))


# ----------------------------
# Legacy mapping
# ----------------------------

def _map_legacy_fields(block: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """
    Try to map older schema keys into (organ, tier).
    Add more fallbacks here if you discover additional old keys.
    """
    organ = block.get("organ")
    if organ is None:
        organ = block.get("name") or block.get("organ_name") or block.get("service") or block.get("module")

    tier = block.get("tier")
    if tier is None:
        tier = block.get("priority") or block.get("level") or block.get("tier_name") or block.get("class")

    if organ is not None:
        organ = str(organ)
    if tier is not None:
        tier = str(tier)

    return organ, tier


def _has_minimum_fields_for_hash(block: Dict[str, Any]) -> bool:
    """
    Whether we can compute a canonical hash for this block (after legacy mapping).
    """
    organ, tier = _map_legacy_fields(block)
    return (
        organ is not None
        and tier is not None
        and "timestamp" in block
        and "prev_hash" in block  # if missing, migration can fill, but verifier needs something
    )


# ----------------------------
# Public API
# ----------------------------

def append_ledger_entry(organ_name: str, tier: str) -> None:
    """
    Append a new entry to the ledger. Works even if ledger begins with legacy blocks.
    """
    ledger = load_ledger()

    # Determine prev_hash based on the last block in the *active* ledger:
    # - if stored hash exists, use it
    # - else compute from canonical fields if possible
    # - else fall back to GENESIS
    prev_hash = "GENESIS"
    if ledger:
        last = ledger[-1]
        if isinstance(last, dict) and last.get("hash"):
            prev_hash = str(last["hash"])
        elif isinstance(last, dict):
            organ, t = _map_legacy_fields(last)
            try:
                idx = int(last.get("index", len(ledger) - 1))
                ts = float(last["timestamp"])
                ph = str(last.get("prev_hash", "GENESIS"))
                if organ is not None and t is not None:
                    prev_hash = hash_block(
                        _canonical_block_for_hash(
                            index=idx,
                            organ=organ,
                            tier=t,
                            timestamp=ts,
                            prev_hash=ph,
                        )
                    )
            except Exception:
                prev_hash = "GENESIS"

    index = len(ledger)
    timestamp = time.time()

    canonical = _canonical_block_for_hash(
        index=index,
        organ=organ_name,
        tier=tier,
        timestamp=timestamp,
        prev_hash=prev_hash,
    )

    block: Dict[str, Any] = dict(canonical)
    block["hash"] = hash_block(canonical)

    ledger.append(block)
    save_ledger(ledger)

    print(f"✅ Organ '{organ_name}' recorded in ledger (index={index}).")


def verify_ledger(*, strict_hash: bool = False, allow_legacy_prefix: bool = True) -> bool:
    """
    Verify ledger integrity.

    Key behavior:
    - If allow_legacy_prefix=True (default), legacy blocks at the START that cannot be
      mapped/hashed are skipped with a warning, and verification begins at the first
      verifiable modern block.
    - Chaining is validated using computed hashes even if a block is missing stored 'hash'
      (unless strict_hash=True).

    Returns:
        True if verifiable portion of ledger passes integrity checks, else False.
    """
    ledger = load_ledger()
    if not ledger:
        print("ℹ️ Ledger is empty.")
        return True

    start = 0
    if allow_legacy_prefix:
        # Skip unmappable prefix blocks
        for i, block in enumerate(ledger):
            if not isinstance(block, dict):
                continue
            # We can verify a block if it has/derives organ+tier and has timestamp.
            organ, tier = _map_legacy_fields(block)
            if organ is not None and tier is not None and "timestamp" in block:
                start = i
                break
        else:
            print("❌ No verifiable blocks found in ledger (all legacy/unmappable).")
            return False

        if start > 0:
            print(f"⚠️ Skipping {start} legacy ledger block(s) at start (unverifiable schema).")

    prev_expected_hash: Optional[str] = None

    for i in range(start, len(ledger)):
        block = ledger[i]
        if not isinstance(block, dict):
            print(f"❌ Ledger block at position {i} is not a dict/object.")
            return False

        idx = int(block.get("index", i))
        organ, tier = _map_legacy_fields(block)

        if organ is None or tier is None:
            print(f"❌ Ledger block missing required mapped fields at index {i}.")
            return False

        try:
            ts = float(block["timestamp"])
        except Exception:
            print(f"❌ Ledger block has invalid/missing timestamp at index {i}.")
            return False

        # prev_hash rules
        if i == start:
            # For the first verifiable block, accept existing prev_hash or GENESIS if missing.
            prev_hash = str(block.get("prev_hash", "GENESIS"))
        else:
            prev_hash = str(block.get("prev_hash", ""))
            if prev_expected_hash is None or prev_hash != prev_expected_hash:
                print(f"❌ Broken chain at index {i}.")
                return False

        canonical = _canonical_block_for_hash(
            index=idx,
            organ=organ,
            tier=tier,
            timestamp=ts,
            prev_hash=prev_hash,
        )
        expected_hash = hash_block(canonical)

        stored_hash = block.get("hash")
        if stored_hash is not None:
            if str(stored_hash) != expected_hash:
                print(f"❌ Ledger tampering detected at index {i}.")
                return False
        else:
            if strict_hash:
                print(f"❌ Ledger block missing hash at index {i} (strict mode).")
                return False

        prev_expected_hash = expected_hash

    print("🟢 Ledger integrity verified.")
    return True


def migrate_ledger_in_place(*, backup: bool = True) -> Tuple[int, int, int]:
    """
    Safe migration that DOES NOT crash on legacy blocks.

    What it does:
    - Creates a backup of the active ledger (ledger.json.bak) if backup=True
    - Quarantines blocks that cannot be mapped to canonical schema (missing organ/tier/timestamp)
      into /opt/veil_os/ledger_legacy.json (append-only)
    - Rewrites the active ledger as a clean canonical chain:
        - ensures index
        - ensures prev_hash links
        - ensures hash exists and matches computed

    Returns:
        (modified_blocks, quarantined_blocks, total_original_blocks)
    """
    ledger = load_ledger()
    if not ledger:
        print("ℹ️ Ledger is empty. Nothing to migrate.")
        return (0, 0, 0)

    if backup and LEDGER_PATH.exists():
        bak = LEDGER_PATH.with_suffix(LEDGER_PATH.suffix + ".bak")
        _atomic_write_text(bak, LEDGER_PATH.read_text())
        print(f"🧾 Backup written: {bak}")

    quarantined: List[Dict[str, Any]] = []
    cleaned: List[Dict[str, Any]] = []
    modified = 0

    # First pass: split legacy-unmappable vs candidates
    for i, block in enumerate(ledger):
        if not isinstance(block, dict):
            quarantined.append({"_reason": "non-dict block", "_original_index": i, "value": block})
            continue

        organ, tier = _map_legacy_fields(block)
        if organ is None or tier is None or "timestamp" not in block:
            b = dict(block)
            b["_reason"] = "missing organ/tier/timestamp"
            b["_original_index"] = i
            quarantined.append(b)
            continue

        cleaned.append(block)

    # Append quarantined blocks to quarantine file (don’t lose history)
    if quarantined:
        existing = _load_json_list(LEGACY_QUARANTINE_PATH)
        existing.extend(quarantined)
        _save_json_list(LEGACY_QUARANTINE_PATH, existing)
        print(f"📦 Quarantined {len(quarantined)} legacy block(s) -> {LEGACY_QUARANTINE_PATH}")

    if not cleaned:
        print("❌ No migratable blocks remain after quarantining legacy entries.")
        return (0, len(quarantined), len(ledger))

    # Second pass: rewrite into canonical chain
    new_ledger: List[Dict[str, Any]] = []
    prev_hash = "GENESIS"

    for new_index, old_block in enumerate(cleaned):
        organ, tier = _map_legacy_fields(old_block)
        ts = float(old_block["timestamp"])

        canonical = _canonical_block_for_hash(
            index=new_index,
            organ=str(organ),
            tier=str(tier),
            timestamp=ts,
            prev_hash=prev_hash,
        )
        expected_hash = hash_block(canonical)

        new_block = dict(canonical)
        new_block["hash"] = expected_hash

        # Count as modified if anything materially changed
        if (
            old_block.get("index") != new_index
            or old_block.get("prev_hash") != prev_hash
            or old_block.get("hash") != expected_hash
            or old_block.get("organ") != str(organ)  # normalize key name
            or old_block.get("tier") != str(tier)
        ):
            modified += 1

        new_ledger.append(new_block)
        prev_hash = expected_hash

    save_ledger(new_ledger)
    print(f"✅ Migration complete. Active ledger rewritten as canonical chain ({len(new_ledger)} blocks).")
    return (modified, len(quarantined), len(ledger))
