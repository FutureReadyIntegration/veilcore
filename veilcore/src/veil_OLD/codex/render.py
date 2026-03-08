from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def default_codex_dir() -> Path:
    p = os.environ.get(
        "VEIL_CODEX_DIR",
        "/opt/veil_os/The-Veil-Sentinel/cathedral_codex",
    )
    return Path(p)


def chronicle_events_path() -> Path:
    d = default_codex_dir() / "chronicle"
    return d / "chronicle_events.jsonl"


def timeline_path() -> Path:
    return default_codex_dir() / "codex_timeline.json"


def _read_jsonl(p: Path, limit: int = 5000) -> List[Dict[str, Any]]:
    if not p.exists():
        return []
    out: List[Dict[str, Any]] = []
    with p.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                out.append(obj)
            if len(out) >= limit:
                break
    return out


def render_timeline(*, limit: int = 2000) -> Tuple[int, Path]:
    """
    Reads chronicle_events.jsonl and writes codex_timeline.json
    as a JSON array suitable for UI/portal consumption.
    """
    src = chronicle_events_path()
    dst = timeline_path()
    dst.parent.mkdir(parents=True, exist_ok=True)

    events = _read_jsonl(src, limit=limit)

    # Keep only the public, UI-friendly fields
    timeline = []
    for e in events[-limit:]:
        timeline.append(
            {
                "index": e.get("index"),
                "ts": e.get("ts"),
                "type": e.get("type"),
                "payload": e.get("payload"),
                "hash": e.get("hash"),
                "prev_hash": e.get("prev_hash"),
            }
        )

    dst.write_text(json.dumps(timeline, indent=2, ensure_ascii=False), encoding="utf-8")
    return len(timeline), dst
