from __future__ import annotations

import importlib.util
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[2]
ENGINE_PATH = ROOT / "core" / "physical" / "engine.py"
EVENTS_PATH = ROOT / "data" / "events.json"

def _load(name: str, fp: Path):
    spec = importlib.util.spec_from_file_location(name, fp)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {name} from {fp}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

_engine_mod = _load("veilcore_physical_engine", ENGINE_PATH)
PhysicalSecurityEngine = _engine_mod.PhysicalSecurityEngine

router = APIRouter()

_ENGINE = PhysicalSecurityEngine()
_ENGINE.configure_hospital("Memorial General")
_ENGINE.add_sensor("MOTION-SR1", "motion", "Server Room A", "server_room")
_ENGINE.add_sensor("TEMP-SR1", "temperature", "Server Room A", "server_room", threshold_high=85.0)
_ENGINE.add_camera("CAM-SR01", "Server Room A", "server_room", ip="10.1.1.100")


class PhysicalTestReq(BaseModel):
    mode: str = "intrusion"


def _load_events_store():
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not EVENTS_PATH.exists():
        return {"events": []}
    try:
        data = json.loads(EVENTS_PATH.read_text() or "{}")
    except Exception:
        data = {"events": []}
    data.setdefault("events", [])
    return data


def _save_events_store(data):
    EVENTS_PATH.write_text(json.dumps(data, indent=2))


def _publish(event_type: str, message: str, payload: dict, level: str = "warning", target: str | None = None):
    data = _load_events_store()
    data["events"].append({
        "id": str(uuid.uuid4()),
        "ts": datetime.now().isoformat(timespec="seconds"),
        "type": event_type,
        "source": "physical",
        "target": target,
        "level": level,
        "message": message,
        "payload": payload,
    })
    data["events"] = data["events"][-1000:]
    _save_events_store(data)


@router.get("/physical/summary")
def physical_summary():
    try:
        return _ENGINE.summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/physical/alerts")
def physical_alerts(limit: int = 20):
    try:
        alerts = [a.to_dict() for a in _ENGINE.sensors.get_alerts(limit=limit)]
        return {"alerts": alerts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/physical/test")
def physical_test(req: PhysicalTestReq):
    try:
        mode = (req.mode or "intrusion").strip().lower()

        if mode == "intrusion":
            _publish(
                "physical.api_hit",
                "physical intrusion route entered",
                {"mode": mode},
                level="warning",
                target="api_physical",
            )
            sensor_alerts = _ENGINE.sensor_trigger("MOTION-SR1")
            camera_events = _ENGINE.camera_feed_lost("CAM-SR01")
            correlations = _ENGINE.analyze()

            sensor_alert_dicts = [a.to_dict() for a in sensor_alerts]
            camera_event_dicts = [e.to_dict() for e in camera_events]
            correlation_dicts = [c.to_dict() for c in correlations]

            for a in sensor_alert_dicts:
                _publish(
                    "physical.sensor_triggered" if a.get("alert_type") == "triggered" else "physical.alert",
                    a.get("message", ""),
                    a,
                    level="critical" if a.get("severity") == "critical" else "warning",
                    target=a.get("sensor_id"),
                )

            for e in camera_event_dicts:
                _publish(
                    "physical.camera_feed_lost" if e.get("event_type") == "feed_lost" else "physical.camera_event",
                    e.get("details", ""),
                    e,
                    level="critical" if e.get("severity") == "critical" else "warning",
                    target=e.get("camera_id"),
                )

            for c in correlation_dicts:
                _publish(
                    "physical.correlation",
                    c.get("description", c.get("pattern", "physical correlation")),
                    c,
                    level="critical" if c.get("severity") == "critical" else "warning",
                )

            return {
                "ok": True,
                "mode": mode,
                "sensor_alerts": sensor_alert_dicts,
                "camera_events": camera_event_dicts,
                "correlations": correlation_dicts,
            }

        if mode == "temperature":
            alerts = _ENGINE.sensor_reading("TEMP-SR1", 92.0, "°F")
            correlations = _ENGINE.analyze()

            alert_dicts = [a.to_dict() for a in alerts]
            correlation_dicts = [c.to_dict() for c in correlations]

            for a in alert_dicts:
                _publish(
                    "physical.alert",
                    a.get("message", ""),
                    a,
                    level="critical" if a.get("severity") == "critical" else "warning",
                    target=a.get("sensor_id"),
                )

            for c in correlation_dicts:
                _publish(
                    "physical.correlation",
                    c.get("description", c.get("pattern", "physical correlation")),
                    c,
                    level="critical" if c.get("severity") == "critical" else "warning",
                )

            return {
                "ok": True,
                "mode": mode,
                "sensor_alerts": alert_dicts,
                "correlations": correlation_dicts,
            }

        raise HTTPException(status_code=400, detail=f"unknown test mode: {mode}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
