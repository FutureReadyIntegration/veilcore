from __future__ import annotations

from pathlib import Path
from datetime import datetime
import json
import importlib.util


ROOT = Path(__file__).resolve().parent.parent
CONFIGS = ROOT / "configs"
ENGINES_PATH = CONFIGS / "engines.json"

# Load NerveBridge explicitly by file path
_NB_PATH = ROOT / "core" / "nervebridge.py"
_nb_spec = importlib.util.spec_from_file_location("veilcore_nervebridge", _NB_PATH)
if _nb_spec is None or _nb_spec.loader is None:
    raise RuntimeError(f"Could not load NerveBridge from {_NB_PATH}")

_nb_mod = importlib.util.module_from_spec(_nb_spec)
_nb_spec.loader.exec_module(_nb_mod)

NerveBridge = _nb_mod.NerveBridge


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _default_engines():
    return {
        "engines": [
            {"id":"mesh","name":"NerveBridge","desc":"Organ Mesh Communication","enabled":True,"state":"running","health":100,"service":"veilcore-mesh","last_error":"","updated_at":_now()},
            {"id":"ml","name":"DeepSentinel","desc":"ML Threat Prediction","enabled":True,"state":"running","health":100,"service":"veilcore-ml","last_error":"","updated_at":_now()},
            {"id":"federation","name":"AllianceNet","desc":"Multi-Site Federation","enabled":True,"state":"running","health":100,"service":"veilcore-federation","last_error":"","updated_at":_now()},
            {"id":"pentest","name":"RedVeil","desc":"Automated Penetration Testing","enabled":True,"state":"running","health":100,"service":"veilcore-pentest","last_error":"","updated_at":_now()},
            {"id":"mobile","name":"Watchtower","desc":"Mobile Security API","enabled":True,"state":"running","health":100,"service":"veilcore-mobile","last_error":"","updated_at":_now()},
            {"id":"accessibility","name":"EqualShield","desc":"Accessibility Engine","enabled":True,"state":"running","health":100,"service":"veilcore-accessibility","last_error":"","updated_at":_now()},
            {"id":"wireless","name":"AirShield","desc":"Wireless Guardian","enabled":True,"state":"running","health":100,"service":"veilcore-wireless","last_error":"","updated_at":_now()},
            {"id":"physical","name":"IronWatch","desc":"Physical Security","enabled":True,"state":"running","health":100,"service":"veilcore-physical","last_error":"","updated_at":_now()},
            {"id":"deployer","name":"Genesis","desc":"Deployment Engine","enabled":True,"state":"running","health":100,"service":"veilcore-deployer","last_error":"","updated_at":_now()},
            {"id":"hitrust","name":"TrustForge","desc":"HITRUST CSF Mapper","enabled":True,"state":"running","health":100,"service":"veilcore-hitrust","last_error":"","updated_at":_now()},
            {"id":"soc2","name":"AuditIron","desc":"SOC 2 Type II Mapper","enabled":True,"state":"running","health":100,"service":"veilcore-soc2","last_error":"","updated_at":_now()},
            {"id":"cloud","name":"SkyVeil","desc":"Cloud-Hybrid Engine","enabled":True,"state":"running","health":100,"service":"veilcore-cloud","last_error":"","updated_at":_now()},
            {"id":"dashboard","name":"Prism","desc":"Unified Dashboard API","enabled":True,"state":"running","health":100,"service":"veilcore-dashboard","last_error":"","updated_at":_now()}
        ]
    }


class EngineManager:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else ENGINES_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.bridge = NerveBridge()
        self._data = self._load()

    def _load(self):
        if not self.path.exists():
            data = _default_engines()
            self.path.write_text(json.dumps(data, indent=2))
            return data
        try:
            data = json.loads(self.path.read_text() or "{}")
        except Exception:
            data = _default_engines()
        data.setdefault("engines", [])
        return data

    def save(self):
        self.path.write_text(json.dumps(self._data, indent=2))

    def list_engines(self):
        return list(self._data.get("engines", []))

    def get_engine(self, engine_id: str):
        for eng in self._data.get("engines", []):
            if eng.get("id") == engine_id:
                return eng
        return None

    def require_engine(self, engine_id: str):
        eng = self.get_engine(engine_id)
        if not eng:
            raise KeyError(f"engine not found: {engine_id}")
        return eng

    def _publish(self, event_type: str, eng: dict, message: str = "", level: str = "info"):
        self.bridge.publish(
            event_type=event_type,
            source=eng.get("id", "unknown"),
            level=level,
            message=message,
            payload={
                "name": eng.get("name"),
                "desc": eng.get("desc", ""),
                "state": eng.get("state"),
                "health": eng.get("health"),
                "enabled": eng.get("enabled", True),
                "service": eng.get("service", ""),
                "last_error": eng.get("last_error", ""),
                "updated_at": eng.get("updated_at", ""),
            },
        )

    def start(self, engine_id: str):
        eng = self.require_engine(engine_id)
        if not eng.get("enabled", True):
            eng["enabled"] = True
        eng["state"] = "running"
        eng["health"] = max(int(eng.get("health", 100)), 90)
        eng["last_error"] = ""
        eng["updated_at"] = _now()
        self.save()
        self._publish("engine.started", eng, message=f"{eng.get('name')} started")
        return eng

    def stop(self, engine_id: str):
        eng = self.require_engine(engine_id)
        eng["state"] = "stopped"
        eng["updated_at"] = _now()
        self.save()
        self._publish("engine.stopped", eng, message=f"{eng.get('name')} stopped", level="warning")
        return eng

    def restart(self, engine_id: str):
        eng = self.require_engine(engine_id)
        eng["state"] = "running"
        eng["health"] = max(int(eng.get("health", 100)), 90)
        eng["last_error"] = ""
        eng["updated_at"] = _now()
        self.save()
        self._publish("engine.restarted", eng, message=f"{eng.get('name')} restarted")
        return eng

    def fail(self, engine_id: str, message: str, health: int | float = 40):
        eng = self.require_engine(engine_id)
        h = max(0, min(100, int(round(float(health)))))
        eng["state"] = "degraded" if h > 0 else "crashed"
        eng["health"] = h
        eng["last_error"] = str(message)
        eng["updated_at"] = _now()
        self.save()
        self._publish("engine.degraded", eng, message=message, level="critical" if h <= 20 else "warning")
        return eng


if __name__ == "__main__":
    mgr = EngineManager()
    print(json.dumps(mgr.list_engines(), indent=2))
