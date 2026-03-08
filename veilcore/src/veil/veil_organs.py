import json
from pathlib import Path

ORGANS_PATH = Path("/opt/veil_os/data/organs.json")

_ORGANS = {}
_META = {}


def load_organs(path: Path = ORGANS_PATH):
    global _ORGANS, _META
    _ORGANS.clear()
    _META.clear()

    data = json.loads(path.read_text(encoding="utf-8"))

    # --- v2 schema ---
    if isinstance(data, dict) and "organs" in data:
        _META.update({k: v for k, v in data.items() if k != "organs"})
        items = data["organs"]

    # --- legacy schema ---
    elif isinstance(data, list):
        items = data

    else:
        raise ValueError("Unsupported organs.json format")

    for o in items:
        oid = o.get("id") or o.get("name")
        if not oid:
            continue
        _ORGANS[oid] = o

    return _ORGANS


def get_organ(name: str):
    return _ORGANS.get(name)


def list_organs():
    return list(_ORGANS.values())


def filter_by_tier(tier: str):
    return [o for o in _ORGANS.values() if o.get("tier") == tier]


def meta():
    return dict(_META)
