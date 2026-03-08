from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def _canon(obj: Dict[str, Any]) -> bytes:
    # canonical JSON bytes for deterministic hashing
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def default_chronicle_dir() -> Path:
    # Cathedral operational copy default
    p = os.environ.get(
        "VEIL_CHRONICLE_DIR",
        "/opt/veil_os/The-Veil-Sentinel/cathedral_codex/chronicle",
    )
    return Path(p)


def chronicle_path() -> Path:
    d = default_chronicle_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / "chronicle_events.jsonl"


@dataclass(frozen=True)
class AppendResult:
    index: int
    hash: str
    prev_hash: str


def read_last_hash(path: Optional[Path] = None) -> Tuple[int, str]:
    """
    Returns (last_index, last_hash). If empty, returns (-1, genesis_hash).
    """
    p = path or chronicle_path()
    if not p.exists():
        return -1, "0" * 64

    last_idx = -1
    last_hash = "0" * 64
    with p.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict) and "index" in obj and "hash" in obj:
                try:
                    last_idx = int(obj["index"])
                    last_hash = str(obj["hash"])
                except Exception:
                    continue
    return last_idx, last_hash


def append_event(
    event: Dict[str, Any],
    *,
    path: Optional[Path] = None,
) -> AppendResult:
    """
    Append-only, hash-chained Chronicle event.

    Stored fields:
      - index, ts, type, payload, prev_hash, hash
    """
    p = path or chronicle_path()
    p.parent.mkdir(parents=True, exist_ok=True)

    last_idx, prev = read_last_hash(p)
    idx = last_idx + 1

    record: Dict[str, Any] = {
        "index": idx,
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": str(event.get("type", "event")),
        "payload": event.get("payload", {}),
        "prev_hash": prev,
    }

    record_hash = _sha256_hex(_canon(record))
    record["hash"] = record_hash

    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")

    return AppendResult(index=idx, hash=record_hash, prev_hash=prev)


def verify_chain(*, path: Optional[Path] = None) -> Tuple[bool, int, str]:
    """
    Returns (ok, count, last_hash). Validates prev_hash links and per-record hash.
    """
    p = path or chronicle_path()
    if not p.exists():
        return True, 0, "0" * 64

    expected_prev = "0" * 64
    count = 0
    last_hash = expected_prev

    with p.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                return False, count, last_hash

            if not isinstance(obj, dict):
                return False, count, last_hash

            prev = str(obj.get("prev_hash", ""))
            h = str(obj.get("hash", ""))

            # Check link
            if prev != expected_prev:
                return False, count, last_hash

            # Recompute hash for record WITHOUT the "hash" field
            rec = dict(obj)
            rec.pop("hash", None)
            recomputed = _sha256_hex(_canon(rec))
            if recomputed != h:
                return False, count, last_hash

            expected_prev = h
            last_hash = h
            count += 1

    return True, count, last_hash
