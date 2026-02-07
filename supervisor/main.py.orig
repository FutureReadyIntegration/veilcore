from __future__ import annotations

import json
import subprocess
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse

ORGANS_DIR = Path("/opt/veil_os/organs")

TIERS = {
    "sentinel": "P0",
    "watchtower": "P0",
    "audit": "P0",
    "triage": "P1",
    "telemetry": "P1",
    "zombie_sweeper": "P1",
}

GLYPHS = {
    "sentinel": "🛡️",
    "watchtower": "🛰️",
    "audit": "📜",
}

def get_tier(name: str) -> str:
    return TIERS.get(name, "P2")

def get_glyph(name: str) -> str:
    return GLYPHS.get(name, "🫀")

def get_status(unit: str):
    try:
        out = subprocess.check_output(
            ["systemctl", "is-active", unit],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        return "active" if out == "active" else "inactive"
    except Exception:
        return "inactive"

def get_pid(unit: str):
    try:
        out = subprocess.check_output(
            ["systemctl", "show", unit, "--property=MainPID"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        pid = out.split("=")[1]
        return int(pid) if pid.isdigit() and int(pid) > 0 else None
    except Exception:
        return None

def get_last_log(unit: str):
    try:
        out = subprocess.check_output(
            ["journalctl", "-u", unit, "-n", "1", "--no-pager"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        return out
    except Exception:
        return ""
    
def list_organs():
    organs = []
    if not ORGANS_DIR.exists():
        return organs

    for organ_dir in ORGANS_DIR.iterdir():
        if not organ_dir.is_dir():
            continue

        name = organ_dir.name
        unit = f"veil-{name}.service"
        run_script = organ_dir / "run.sh"

        organs.append({
            "name": name,
            "tier": get_tier(name),
            "glyph": get_glyph(name),
            "status": get_status(unit),
            "pid": get_pid(unit),
            "runnable": run_script.exists(),
            "unit": unit,
            "log": get_last_log(unit),
            "path": str(organ_dir),
        })

    return organs

app = FastAPI(title="Veil Supervisor")

@app.get("/organs", response_class=JSONResponse)
def api_organs():
    return list_organs()

def main():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8085)
    return 0

if __name__ == "__main__":
    main()
