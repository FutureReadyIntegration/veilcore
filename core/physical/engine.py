from __future__ import annotations

import importlib.util
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("veilcore.physical.engine")

# Load sibling modules by file path
BASE = Path(__file__).resolve().parent

def _load(name: str, filename: str):
    fp = BASE / filename
    spec = importlib.util.spec_from_file_location(name, fp)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {name} from {fp}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

_sensors_mod = _load("veilcore_physical_sensors", "sensors.py")
_cameras_mod = _load("veilcore_physical_cameras", "cameras.py")
_fusion_mod = _load("veilcore_physical_fusion", "fusion.py")

SensorManager = _sensors_mod.SensorManager
SensorAlert = _sensors_mod.SensorAlert
CameraMonitor = _cameras_mod.CameraMonitor
CameraEvent = _cameras_mod.CameraEvent
SensorFusionEngine = _fusion_mod.SensorFusionEngine
CorrelatedEvent = _fusion_mod.CorrelatedEvent


class PhysicalSecurityEngine:
    def __init__(self):
        self._sensors = SensorManager()
        self._cameras = CameraMonitor()
        self._fusion = SensorFusionEngine()
        self._hospital_name = "Unknown Hospital"

    def configure_hospital(self, name: str) -> None:
        self._hospital_name = name

    def add_sensor(self, sensor_id: str, sensor_type: str,
                   location: str = "", zone: str = "general",
                   threshold_high: Optional[float] = None,
                   threshold_low: Optional[float] = None) -> None:
        self._sensors.register_sensor(
            sensor_id, sensor_type, location, zone,
            threshold_high=threshold_high, threshold_low=threshold_low,
        )

    def add_camera(self, camera_id: str, location: str = "",
                   zone: str = "general", camera_type: str = "fixed",
                   ip: str = "", firmware: str = "") -> None:
        self._cameras.register_camera(
            camera_id, location, zone, camera_type,
            ip_address=ip, firmware=firmware,
            expected_firmware=firmware,
        )

    def sensor_reading(self, sensor_id: str, value: float, unit: str = "") -> list[SensorAlert]:
        alerts = self._sensors.process_reading(sensor_id, value, unit)
        for alert in alerts:
            self._fusion.ingest_sensor_alert(alert)
        return alerts

    def sensor_trigger(self, sensor_id: str) -> list[SensorAlert]:
        alerts = self._sensors.process_trigger(sensor_id)
        for alert in alerts:
            self._fusion.ingest_sensor_alert(alert)
        return alerts

    def sensor_offline(self, sensor_id: str) -> Optional[SensorAlert]:
        alert = self._sensors.mark_offline(sensor_id)
        if alert:
            self._fusion.ingest_sensor_alert(alert)
        return alert

    def camera_feed_lost(self, camera_id: str) -> list[CameraEvent]:
        events = self._cameras.report_feed_lost(camera_id)
        for event in events:
            self._fusion.ingest_camera_event(event)
        return events

    def camera_tamper(self, camera_id: str, details: str = "") -> list[CameraEvent]:
        events = self._cameras.report_tamper(camera_id, details)
        for event in events:
            self._fusion.ingest_camera_event(event)
        return events

    def camera_heartbeat(self, camera_id: str) -> None:
        self._cameras.heartbeat(camera_id)

    def cyber_event(self, event_type: str, severity: str = "high",
                    zone: str = "", details: str = "") -> None:
        self._fusion.ingest_cyber_event(event_type, severity, zone, details)

    def analyze(self) -> list[CorrelatedEvent]:
        return self._fusion.analyze()

    def full_assessment(self) -> dict[str, Any]:
        start = time.monotonic()
        camera_events = self._cameras.check_all_cameras()
        for event in camera_events:
            self._fusion.ingest_camera_event(event)
        correlations = self._fusion.analyze()
        duration_ms = (time.monotonic() - start) * 1000

        return {
            "hospital": self._hospital_name,
            "sensors": self._sensors.summary(),
            "cameras": self._cameras.summary(),
            "fusion": self._fusion.summary(),
            "correlations": [c.to_dict() for c in correlations],
            "duration_ms": round(duration_ms, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @property
    def sensors(self) -> SensorManager:
        return self._sensors

    @property
    def cameras(self) -> CameraMonitor:
        return self._cameras

    @property
    def fusion(self) -> SensorFusionEngine:
        return self._fusion

    def summary(self) -> dict[str, Any]:
        return {
            "engine": "PhysicalSecurity",
            "codename": "IronWatch",
            "hospital": self._hospital_name,
            "sensors": self._sensors.summary(),
            "cameras": self._cameras.summary(),
            "fusion": self._fusion.summary(),
        }
