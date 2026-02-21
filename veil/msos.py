#!/usr/bin/env python3
"""
VeilCore MSOS - Micro-Service Operating System (orchestrator)

Minimal v1:
- Heartbeat + inventory of veilcore-* units
- No auto-start/stop yet (we'll add policies once stable)
"""

import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


RUNNING = True


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def handle_shutdown(signum, frame):
    global RUNNING
    RUNNING = False


def systemctl(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["systemctl", *args],
        capture_output=True,
        text=True,
    )


def list_veilcore_units() -> list[str]:
    r = systemctl(["list-unit-files", "veilcore-*.service", "--no-legend"])
    units = []
    for line in r.stdout.splitlines():
        parts = line.split()
        if parts:
            units.append(parts[0].strip())
    return units


def get_unit_state(unit: str) -> dict:
    r = systemctl(["show", unit, "-p", "LoadState", "-p", "ActiveState", "-p", "SubState", "-p", "FragmentPath"])
    out = {}
    for line in r.stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k] = v
    return {
        "unit": unit,
        "load": out.get("LoadState", "unknown"),
        "active": out.get("ActiveState", "unknown"),
        "status": out.get("SubState", "unknown"),
        "fragment": out.get("FragmentPath", ""),
    }


def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(path)


def main() -> int:
    # shutdown handling
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    state_dir = Path(os.environ.get("VEIL_STATE_DIR", "/var/lib/veil")) / "msos"
    status_file = state_dir / "msos.json"

    # main loop
    start = time.time()
    while RUNNING:
        units = list_veilcore_units()
        states = [get_unit_state(u) for u in units]

        payload = {
            "name": "msos",
            "status": "active" if RUNNING else "stopping",
            "started_at": datetime.fromtimestamp(start, tz=timezone.utc).isoformat(),
            "updated_at": now_iso(),
            "units_total": len(units),
            "units_active": sum(1 for s in states if s["active"] == "active"),
            "units": states,
        }

        try:
            write_json(status_file, payload)
        except Exception as e:
            # If state dir isn't writable, at least don't crash-loop
            print(f"[msos] WARN: could not write status: {e}", file=sys.stderr)

        time.sleep(5)

    # final write on shutdown
    payload = {
        "name": "msos",
        "status": "stopped",
        "updated_at": now_iso(),
    }
    try:
        write_json(status_file, payload)
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

