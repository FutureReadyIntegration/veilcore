from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


DEFAULT_LEDGER_PATH = Path("/opt/veil_os/logs/override_ledger.jsonl")


def _ledger_path() -> Path:
    # Allow override for ops/testing
    p = os.environ.get("VEIL_LEDGER_PATH")
    return Path(p) if p else DEFAULT_LEDGER_PATH


def _parse_json_line(line: str) -> Optional[Dict[str, Any]]:
    line = line.strip()
    if not line:
        return None
    try:
        obj = json.loads(line)
        if isinstance(obj, dict):
            return obj
    except Exception:
        return None
    return None


def list_ledger_events(
    *,
    path: str | Path | None = None,
    limit: int = 200,
    reverse: bool = True,
) -> List[Dict[str, Any]]:
    """
    Reads the Veil ledger JSONL and returns a list of event dicts.

    - limit: max number of events returned
    - reverse=True: returns newest-first (operator-friendly)
    """
    p = Path(path) if path else _ledger_path()
    if not p.exists():
        return []

    events: List[Dict[str, Any]] = []
    with p.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            obj = _parse_json_line(line)
            if obj is not None:
                events.append(obj)

    if reverse:
        events = list(reversed(events))

    if limit and limit > 0:
        events = events[:limit]
    return events


def format_event_line(evt: Dict[str, Any]) -> str:
    """
    Human-readable one-line event for operator consoles.
    Tries to be stable even if fields evolve.
    """
    ts = str(evt.get("ts") or evt.get("time") or evt.get("timestamp") or "").strip()
    action = str(evt.get("action") or evt.get("event") or evt.get("type") or "event").strip()
    status = str(evt.get("status") or "").strip()
    user = str(evt.get("user") or evt.get("actor") or "").strip()
    reason = str(evt.get("reason") or "").strip()
    target = str(evt.get("target") or "").strip()
    idx = evt.get("index", evt.get("i", ""))
    h = str(evt.get("hash") or "")[:12]

    parts = []
    if ts:
        parts.append(ts)
    if user:
        parts.append(f"user={user}")
    if action:
        parts.append(f"action={action}")
    if status:
        parts.append(f"status={status}")
    if target:
        parts.append(f"target={target}")
    if reason:
        parts.append(f"reason={reason}")
    if idx != "":
        parts.append(f"index={idx}")
    if h:
        parts.append(f"hash={h}…")

    return " ".join(parts).strip() or json.dumps(evt, sort_keys=True)


def format_event_json(evt: Dict[str, Any]) -> str:
    """
    Stable JSON representation (pretty) for exporting/inspection.
    """
    return json.dumps(evt, indent=2, sort_keys=True, ensure_ascii=False)
