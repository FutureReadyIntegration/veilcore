#!/usr/bin/env python3
"""
systemd status bridge for Veil Hospital GUI

Truth source:
- systemctl is-active
- systemctl show MainPID
"""

import subprocess
from typing import Dict, List


def _run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()


def systemd_status(unit: str) -> Dict:
    """
    Return canonical status for a systemd unit.
    """
    try:
        active = _run(["systemctl", "is-active", unit])
        pid = _run(["systemctl", "show", unit, "-p", "MainPID"]).split("=")[1]
        pid = int(pid) if pid.isdigit() and int(pid) > 0 else None

        return {
            "name": unit,
            "running": active == "active",
            "pid": pid,
        }

    except subprocess.CalledProcessError:
        return {
            "name": unit,
            "running": False,
            "pid": None,
        }


def list_veil_units() -> List[Dict]:
    """
    Discover all veil-* services and return status objects.
    """
    out = subprocess.check_output(
        ["systemctl", "list-units", "--type=service", "--all", "--no-pager"]
    ).decode()

    units = []
    for line in out.splitlines():
        if not line.startswith("veil-"):
            continue
        unit = line.split()[0]
        units.append(systemd_status(unit))

    return units

