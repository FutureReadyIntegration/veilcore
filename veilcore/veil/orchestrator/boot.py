#!/usr/bin/env python3
"""Start all Veil OS organs in priority order"""
from . import start, list

def boot_all():
    organs = list()
    # P0 first (critical)
    for o in organs:
        if o.get("tier") == "P0":
            print(f"Starting P0: {o['name']}")
            start(o["name"])
    # P1 second
    for o in organs:
        if o.get("tier") == "P1":
            print(f"Starting P1: {o['name']}")
            start(o["name"])
    # P2 last
    for o in organs:
        if o.get("tier") == "P2":
            print(f"Starting P2: {o['name']}")
            start(o["name"])
    print("✅ All organs started")

if __name__ == "__main__":
    boot_all()
```

Then systemd calls:
```
ExecStart=/home/user/veil_os/backend/venv/bin/python -m veil.orchestrator.boot
