from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# Canonical source of organ definitions
DEFAULT_ORGANS_JSON = Path("/opt/veil_os/data/organs.json")

# In-memory cache: key is lowercase organ name
_ORGANS: Dict[str, Dict[str, Any]] = {}


def _organs_path(path: str | Path | None = None) -> Path:
    if path is not None:
        return Path(path)
    env = os.environ.get("VEIL_ORGANS_PATH")
    if env:
        return Path(env)
    return DEFAULT_ORGANS_JSON


def _normalize_entry(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    name = str(item.get("name", "")).strip()
    if not name:
        return None

    tier = str(item.get("tier", "")).strip()
    glyph = str(item.get("glyph", "")).strip()
    affirmation = str(item.get("affirmation", "")).strip()

    return {
        "name": name,
        "tier": tier,
        "glyph": glyph,
        "affirmation": affirmation,
    }


def load_organs(path: str | Path | None = None) -> Dict[str, Dict[str, Any]]:
    """
    Loads organs from JSON file and populates the module cache.

    File format: a JSON array of objects:
      [{"name": "...", "tier": "P0|P1|P2", "glyph": "...", "affirmation": "..."}]

    Override file path with:
      VEIL_ORGANS_PATH=/path/to/organs.json
    """
    global _ORGANS
    p = _organs_path(path)

    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Organs JSON must be a list (got {type(data).__name__})")

    organs: Dict[str, Dict[str, Any]] = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        norm = _normalize_entry(item)
        if not norm:
            continue
        organs[norm["name"].lower()] = norm

    _ORGANS = organs
    return _ORGANS


def _ensure_loaded() -> None:
    if not _ORGANS:
        load_organs()


def list_organs() -> List[str]:
    _ensure_loaded()
    return sorted([v["name"] for v in _ORGANS.values()], key=lambda s: s.lower())


def get_organ(name: str) -> Optional[Dict[str, Any]]:
    _ensure_loaded()
    return _ORGANS.get(name.strip().lower())


def filter_by_tier(tier: str) -> List[str]:
    _ensure_loaded()
    t = tier.strip().lower()
    out: List[str] = []
    for v in _ORGANS.values():
        if str(v.get("tier", "")).strip().lower() == t:
            out.append(v["name"])
    return sorted(out, key=lambda s: s.lower())


def label(name: str) -> str:
    """
    Display label: '⚡ epic (P0)' (used by UI)
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
