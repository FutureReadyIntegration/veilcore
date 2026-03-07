"""VeilCore Engine Manager — reads live engine state"""
import json, subprocess
from pathlib import Path

ENGINES_CONFIG = Path.home() / "veilcore" / "configs" / "engines.json"

SERVICE_MAP = {
    "mesh": "veilcore-nervebridge",
    "ml": "veilcore-deepsentinel",
    "federation": "veilcore-alliancenet",
    "pentest": "veilcore-redveil",
    "mobile": "veilcore-watchtower",
    "accessibility": "veilcore-equalshield",
    "wireless": "veilcore-airshield",
    "physical": "veilcore-ironwatch",
    "deployer": "veilcore-genesis",
    "hitrust": "veilcore-trustforge",
    "soc2": "veilcore-auditiron",
    "cloud": "veilcore-skyveil",
    "dashboard": "veilcore-prism",
}

class EngineManager:
    def __init__(self):
        self._config = self._load_config()

    def _load_config(self):
        try:
            return json.loads(ENGINES_CONFIG.read_text())
        except Exception:
            return {"engines": []}

    def _service_active(self, svc_name):
        try:
            r = subprocess.run(
                ["systemctl", "is-active", f"{svc_name}.service"],
                capture_output=True, text=True, timeout=5
            )
            return r.stdout.strip() == "active"
        except Exception:
            return False

    def list_engines(self):
        engines = []
        for eng in self._config.get("engines", []):
            eid = eng["id"]
            svc = SERVICE_MAP.get(eid, "")
            is_active = self._service_active(svc) if svc else False
            engines.append({
                "id": eid,
                "name": eng["name"],
                "desc": eng["desc"],
                "state": "running" if is_active else "stopped",
                "health": 100 if is_active else 0,
                "service": svc,
            })
        return engines

    def get_engine(self, engine_id):
        for eng in self.list_engines():
            if eng["id"] == engine_id:
                return eng
        return None

    def start_engine(self, engine_id):
        svc = SERVICE_MAP.get(engine_id)
        if not svc:
            return False, "unknown engine"
        try:
            subprocess.run(["systemctl", "start", f"{svc}.service"], timeout=10)
            return True, "started"
        except Exception as e:
            return False, str(e)

    def stop_engine(self, engine_id):
        svc = SERVICE_MAP.get(engine_id)
        if not svc:
            return False, "unknown engine"
        try:
            subprocess.run(["systemctl", "stop", f"{svc}.service"], timeout=10)
            return True, "stopped"
        except Exception as e:
            return False, str(e)

    def summary(self):
        engines = self.list_engines()
        running = sum(1 for e in engines if e["state"] == "running")
        return {"total": len(engines), "running": running, "stopped": len(engines) - running}
