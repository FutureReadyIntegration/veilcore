"""Live system status API"""

import subprocess
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

ORGANS = [
    ("veil", "Main API", "🛡️"),
    ("veil-sentinel", "Anomaly Detection", "👁️"),
    ("veil-insider-threat", "Insider Threat", "🕵️"),
    ("veil-auto-lockdown", "Auto Response", "🔒"),
    ("veil-zero-trust", "Zero Trust", "🔐"),
    ("veil-guardian", "Guardian Auth", "⚔️"),
    ("veil-rbac", "Access Control", "🎭"),
    ("veil-cockpit-backend", "Cockpit API", "🎛️"),
    ("veil-intrusion", "Intrusion Detection", "🚨"),
    ("veil-zombiesweeper", "Zombie Sweeper", "🧹"),
]

PATIENTS_FILE = Path("/opt/veil_os/veil/hospital_gui/data/patients.json")

def _run(cmd: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=5)

def get_service_status(service: str) -> Dict[str, Any]:
    try:
        r = _run(["systemctl", "is-active", f"{service}.service"])
        is_active = (r.stdout.strip() == "active")

        uptime = None
        if is_active:
            r2 = _run(["systemctl", "show", f"{service}.service", "--property=ActiveEnterTimestamp"])
            if r2.returncode == 0 and "=" in r2.stdout:
                uptime = r2.stdout.strip().split("=", 1)[1].strip() or None

        return {"running": is_active, "status": "active" if is_active else "inactive", "uptime": uptime}
    except Exception as e:
        return {"running": False, "status": "error", "error": str(e)}

def get_all_organs_status() -> List[Dict[str, Any]]:
    out = []
    for service, name, glyph in ORGANS:
        s = get_service_status(service)
        out.append(
            {
                "service": service,
                "name": name,
                "glyph": glyph,
                "running": s["running"],
                "status": s["status"],
                "uptime": s.get("uptime"),
            }
        )
    return out

def get_patient_counts() -> Dict[str, int]:
    try:
        if PATIENTS_FILE.exists():
            data = json.loads(PATIENTS_FILE.read_text())
            patients = data.get("patients", [])
            active = sum(1 for p in patients if not p.get("discharged_at"))
            discharged = sum(1 for p in patients if p.get("discharged_at"))
            return {"total": len(patients), "active": active, "discharged": discharged}
    except Exception:
        pass
    return {"total": 0, "active": 0, "discharged": 0}

def get_system_health() -> Dict[str, Any]:
    organs = get_all_organs_status()
    patients = get_patient_counts()

    running = sum(1 for o in organs if o["running"])
    total = len(organs)

    if total == 0:
        health, health_pct = "CRITICAL", 0
    elif running == total:
        health, health_pct = "HEALTHY", 100
    elif running >= total * 0.8:
        health, health_pct = "DEGRADED", int((running / total) * 100)
    elif running >= total * 0.5:
        health, health_pct = "WARNING", int((running / total) * 100)
    else:
        health, health_pct = "CRITICAL", int((running / total) * 100)

    return {
        "health": health,
        "health_pct": health_pct,
        "organs_running": running,
        "organs_total": total,
        "patients": patients,
        "organs": organs,
        "timestamp": datetime.utcnow().isoformat(),
    }
