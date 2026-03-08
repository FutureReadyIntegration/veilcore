#!/usr/bin/env python3
from pathlib import Path
import yaml

BASE = Path("/opt/veil_os")
SPECS = BASE / "organ_specs"
ORGANS = BASE / "organs"

ORGANS.mkdir(exist_ok=True)

def build(name):
    d = ORGANS / name
    d.mkdir(parents=True, exist_ok=True)

    (d / "__init__.py").write_text(
        "from .runner import start, stop, status\n"
    )

(d / "runner.py").write_text(f'''\
import os

NAME = "{name}"
LOG = f"/opt/veil_os/var/log/{name}.log"

_running = False
_pid = None

def start():
    global _running, _pid
    if _running:
        return False
    _running = True
    _pid = os.getpid()
    return True

def stop():
    global _running
    if not _running:
        return False
    _running = False
    return True

def status():
    return {{
        "name": NAME,
        "running": _running,
        "pid": _pid,
        "log": LOG,
    }}
''')

count = 0
for spec in sorted(SPECS.glob("*.yaml")):
    name = spec.stem
    build(name)
    count += 1
    print(f"✓ built organ: {name}")

print(f"\nBuilt {count} organs.")

