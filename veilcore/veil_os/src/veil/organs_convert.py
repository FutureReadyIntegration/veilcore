from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

SRC = Path("/opt/veil_os/data/organs.json")

SCHEMA = "veil.organs.registry.v2"


def main() -> int:
    raw = SRC.read_text(encoding="utf-8")
    data = json.loads(raw)

    # Already v2?
    if isinstance(data, dict) and "organs" in data:
        payload = data
        payload.setdefault("schema", SCHEMA)
        payload.setdefault("generated_at", datetime.now(timezone.utc).isoformat())
    # Legacy list -> v2
    elif isinstance(data, list):
        payload = {
            "schema": SCHEMA,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "organs": data,
        }
    else:
        raise SystemExit("Unsupported organs.json format")

    # Normalize: ensure each organ has an id
    fixed = []
    for o in payload.get("organs", []):
        if not isinstance(o, dict):
            continue
        if "id" not in o and "name" in o:
            o["id"] = o["name"]
        fixed.append(o)
    payload["organs"] = fixed

    # Atomic write
    tmp = SRC.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(SRC)

    print("OK: wrote v2 registry:", SRC)
    print("organs:", len(payload["organs"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
