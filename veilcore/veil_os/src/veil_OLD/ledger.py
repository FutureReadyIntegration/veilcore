from __future__ import annotations

import getpass
import hashlib
import json
import os
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_dumps(obj: Any) -> str:
    # Stable encoding for hashing
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def default_ledger_path() -> Path:
    # Prefer system log location; fall back to project logs.
    candidates = [
        Path("/var/log/veil_os/override_ledger.jsonl"),
        Path("/opt/veil_os/logs/override_ledger.jsonl"),
        Path("/tmp/veil_os_logs/override_ledger.jsonl"),
    ]
    for p in candidates:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            # Test writability by opening append without writing
            with open(p, "a", encoding="utf-8"):
                pass
            return p
        except Exception:
            continue
    # Last resort
    return candidates[-1]


@dataclass(frozen=True)
class LedgerAppendResult:
    ledger_path: str
    index: int
    entry_hash: str


def _read_last_line(path: Path) -> Optional[str]:
    if not path.exists() or path.stat().st_size == 0:
        return None
    # Simple approach: read all lines (fine for Phase 1). We’ll optimize later if needed.
    with path.open("r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    return lines[-1] if lines else None


def _extract_hash(line: str) -> str:
    obj = json.loads(line)
    return str(obj.get("hash", ""))


def append_event(event: Dict[str, Any], ledger_path: Optional[Path] = None) -> LedgerAppendResult:
    lp = ledger_path or default_ledger_path()
    last = _read_last_line(lp)

    prev_hash = None
    index = 0

    if last:
        last_obj = json.loads(last)
        prev_hash = last_obj.get("hash")
        index = int(last_obj.get("index", 0)) + 1

    envelope: Dict[str, Any] = {
        "index": index,
        "ts_utc": _utc_now(),
        "host": socket.gethostname(),
        "user": getpass.getuser(),
        "uid": os.getuid(),
        "event": event,
        "prev_hash": prev_hash,
    }

    # Hash the envelope without the hash field
    to_hash = _json_dumps(envelope).encode("utf-8")
    entry_hash = _sha256_hex(to_hash)
    envelope["hash"] = entry_hash

    line = _json_dumps(envelope)

    with lp.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

    return LedgerAppendResult(str(lp), index, entry_hash)


def iter_entries(ledger_path: Optional[Path] = None) -> Iterable[Dict[str, Any]]:
    lp = ledger_path or default_ledger_path()
    if not lp.exists():
        return []
    with lp.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def verify_chain(ledger_path: Optional[Path] = None) -> Tuple[bool, str, int]:
    lp = ledger_path or default_ledger_path()
    if not lp.exists():
        return True, f"Ledger not found at {lp} (treat as empty OK).", 0

    prev_hash = None
    count = 0

    with lp.open("r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            obj = json.loads(raw)

            # Check prev_hash links
            if obj.get("prev_hash") != prev_hash:
                return False, f"Broken link at index={obj.get('index')}: prev_hash mismatch.", count

            # Recompute hash
            expected = obj.get("hash")
            obj_no_hash = dict(obj)
            obj_no_hash.pop("hash", None)
            recomputed = _sha256_hex(_json_dumps(obj_no_hash).encode("utf-8"))

            if expected != recomputed:
                return False, f"Tamper detected at index={obj.get('index')}: hash mismatch.", count

            prev_hash = expected
            count += 1

    return True, f"OK: {count} entries, chain valid.", count
