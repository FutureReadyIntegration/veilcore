from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_ORGANS_JSON = Path("/opt/veil_os/data/organs.json")

_ORGANS: Dict[str, Dict[str, Any]] = {}


def load_organs(path: str | Path | None = None) -> Dict[str, Dict[str, Any]]:
    global _ORGANS
    p = Path(path) if path else DEFAULT_ORGANS_JSON
    data = json.loads(p.read_text(encoding="utf-8"))

    organs: Dict[str, Dict[str, Any]] = {}
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            organs[name.lower()] = {
                "name": name,
                "tier": str(item.get("tier", "")).strip(),
                "glyph": str(item.get("glyph", "")).strip(),
                "affirmation": str(item.get("affirmation", "")).strip(),
            }

    _ORGANS = organs
    return _ORGANS


def list_organs() -> List[str]:
    if not _ORGANS:
        load_organs()
    return sorted([v["name"] for v in _ORGANS.values()])


def get_organ(name: str) -> Optional[Dict[str, Any]]:
    if not _ORGANS:
        load_organs()
    return _ORGANS.get(name.strip().lower())


def filter_by_tier(tier: str) -> List[str]:
    if not _ORGANS:
        load_organs()
    t = tier.strip().lower()
    out: List[str] = []
    for v in _ORGANS.values():
        if str(v.get("tier", "")).strip().lower() == t:
            out.append(v["name"])
    return sorted(out)


def label(name: str) -> str:
    """
    Display label: '⚡ epic (P0)'
    """
    o = get_organ(name) or {}
    glyph = str(o.get("glyph", "")).strip()
    tier = str(o.get("tier", "")).strip()
    nm = str(o.get("name", name)).strip()

    if glyph and tier:
        return f"{glyph} {nm} ({tier})"
    if glyph:
        return f"{glyph} {nm}"
    if tier:
        return f"{nm} ({tier})"
    return nm
