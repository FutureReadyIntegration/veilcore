"""
VeilCore Physical Security Engine
=====================================
Orchestrates all physical security subsystems.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from core.physical.sensors import SensorManager, SensorAlert
from core.physical.cameras import CameraMonitor, CameraEvent
from core.physical.fusion import SensorFusionEngine, CorrelatedEvent

logger = logging.getLogger("veilcore.physical.engine")


class PhysicalSecurityEngine:
    """
    Unified physical security engine.

    Usage:
        engine = PhysicalSecurityEngine()
        engine.configure_hospital("Memorial General")

        # Register infrastructure
        engine.add_sensor("MOTION-SR1", "motion", "Server Room A", "server_room")
        engine.add_camera("CAM-SR01", "Server Room A", "server_room", ip="10.1.1.100")

        # Process events
        alerts = engine.sensor_trigger("MOTION-SR1")
        alerts = engine.camera_feed_lost("CAM-SR01")

        # Run fusion analysis
        correlated = engine.analyze()
    """

    def __init__(self):
        self._sensors = SensorManager()
        self._cameras = CameraMonitor()
        self._fusion = SensorFusionEngine()
        self._hospital_name = "Unknown Hospital"

    def configure_hospital(self, name: str) -> None:
        self._hospital_name = name
        logger.info(f"Physical Security Engine configured for: {name}")

    def add_sensor(self, sensor_id: str, sensor_type: str,
                   location: str = "", zone: str = "general",
                   threshold_high: Optional[float] = None,
                   threshold_low: Optional[float] = None) -> None:
        """Register a sensor."""
        self._sensors.register_sensor(
            sensor_id, sensor_type, location, zone,
            threshold_high=threshold_high, threshold_low=threshold_low,
        )

    def add_camera(self, camera_id: str, location: str = "",
                   zone: str = "general", camera_type: str = "fixed",
                   ip: str = "", firmware: str = "") -> None:
        """Register a camera."""
        self._cameras.register_camera(
            camera_id, location, zone, camera_type,
            ip_address=ip, firmware=firmware,
            expected_firmware=firmware,
        )

    def sensor_reading(self, sensor_id: str, value: float,
                       unit: str = "") -> list[SensorAlert]:
        """Process a sensor reading."""
        alerts = self._sensors.process_reading(sensor_id, value, unit)
        for alert in alerts:
            self._fusion.ingest_sensor_alert(alert)
        return alerts

    def sensor_trigger(self, sensor_id: str) -> list[SensorAlert]:
        """Process a sensor trigger."""
        alerts = self._sensors.process_trigger(sensor_id)
        for alert in alerts:
            self._fusion.ingest_sensor_alert(alert)
        return alerts

    def sensor_offline(self, sensor_id: str) -> Optional[SensorAlert]:
        """Mark sensor offline."""
        alert = self._sensors.mark_offline(sensor_id)
        if alert:
            self._fusion.ingest_sensor_alert(alert)
        return alert

    def camera_feed_lost(self, camera_id: str) -> list[CameraEvent]:
        """Report camera feed loss."""
        events = self._cameras.report_feed_lost(camera_id)
        for event in events:
            self._fusion.ingest_camera_event(event)
        return events

    def camera_tamper(self, camera_id: str,
                      details: str = "") -> list[CameraEvent]:
        """Report camera tampering."""
        events = self._cameras.report_tamper(camera_id, details)
        for event in events:
            self._fusion.ingest_camera_event(event)
        return events

    def camera_heartbeat(self, camera_id: str) -> None:
        """Process camera heartbeat."""
        self._cameras.heartbeat(camera_id)

    def cyber_event(self, event_type: str, severity: str = "high",
                    zone: str = "", details: str = "") -> None:
        """Inject a cyber event for correlation."""
        self._fusion.ingest_cyber_event(event_type, severity, zone, details)

    def analyze(self) -> list[CorrelatedEvent]:
        """Run fusion analysis."""
        return self._fusion.analyze()

    def full_assessment(self) -> dict[str, Any]:
        """Complete physical security assessment."""
        start = time.monotonic()

        # Camera health check
        camera_events = self._cameras.check_all_cameras()
        for event in camera_events:
            self._fusion.ingest_camera_event(event)

        # Fusion analysis
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
