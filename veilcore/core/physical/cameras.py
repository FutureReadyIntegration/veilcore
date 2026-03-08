"""
VeilCore Camera Monitor
==========================
Monitors security camera infrastructure for tamper
detection and integration with physical security events.

NOTE: VeilCore does NOT process video feeds or perform
facial recognition. It monitors camera system health,
detects tampering, and correlates camera events with
other physical/cyber security events.

Privacy by design — The Veil sees threats, not people.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("veilcore.physical.cameras")


class CameraState(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    TAMPERED = "tampered"
    OBSTRUCTED = "obstructed"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class CameraEventType(str, Enum):
    FEED_LOST = "feed_lost"
    FEED_RESTORED = "feed_restored"
    TAMPER_DETECTED = "tamper_detected"
    VIEW_OBSTRUCTED = "view_obstructed"
    MOTION_DETECTED = "motion_detected"
    NIGHT_MODE = "night_mode"
    PTZ_OVERRIDE = "ptz_override"
    FIRMWARE_MISMATCH = "firmware_mismatch"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    RECORDING_FAILURE = "recording_failure"


@dataclass
class Camera:
    """Security camera being monitored."""
    camera_id: str
    location: str = ""
    zone: str = "general"
    camera_type: str = "fixed"   # fixed, ptz, dome, thermal
    ip_address: str = ""
    firmware_version: str = ""
    state: str = "online"
    is_recording: bool = True
    last_heartbeat: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    installed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Expected firmware (for mismatch detection)
    expected_firmware: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "camera_id": self.camera_id, "location": self.location,
            "zone": self.zone, "camera_type": self.camera_type,
            "ip_address": self.ip_address,
            "firmware_version": self.firmware_version,
            "state": self.state, "is_recording": self.is_recording,
            "last_heartbeat": self.last_heartbeat,
        }


@dataclass
class CameraEvent:
    """Camera-related security event."""
    event_id: str = field(default_factory=lambda: f"CAM-{int(time.time() * 1000)}")
    camera_id: str = ""
    event_type: str = "feed_lost"
    severity: str = "medium"
    location: str = ""
    zone: str = ""
    details: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id, "camera_id": self.camera_id,
            "event_type": self.event_type, "severity": self.severity,
            "location": self.location, "zone": self.zone,
            "details": self.details, "timestamp": self.timestamp,
        }


# ── Severity by event type and zone ──
EVENT_SEVERITY = {
    ("feed_lost", "server_room"): "critical",
    ("feed_lost", "data_center"): "critical",
    ("feed_lost", "network_closet"): "high",
    ("tamper_detected", "server_room"): "critical",
    ("tamper_detected", "data_center"): "critical",
    ("ptz_override", "server_room"): "critical",
    ("firmware_mismatch", "server_room"): "critical",
    ("unauthorized_access", "server_room"): "critical",
    ("recording_failure", "server_room"): "critical",
}
DEFAULT_SEVERITY = {
    "feed_lost": "high",
    "tamper_detected": "high",
    "view_obstructed": "medium",
    "motion_detected": "low",
    "ptz_override": "high",
    "firmware_mismatch": "high",
    "unauthorized_access": "critical",
    "recording_failure": "high",
    "feed_restored": "info",
    "night_mode": "info",
}


class CameraMonitor:
    """
    Monitors security camera health and detects tampering.

    Usage:
        monitor = CameraMonitor()
        monitor.register_camera("CAM-SR01", location="Server Room",
                                zone="server_room", ip="10.1.1.100")

        events = monitor.report_feed_lost("CAM-SR01")
        events = monitor.report_tamper("CAM-SR01", "Camera physically moved")
    """

    EVENT_HISTORY = 10000
    LOG_PATH = "/var/log/veilcore/camera-events.jsonl"

    def __init__(self):
        self._cameras: dict[str, Camera] = {}
        self._events: deque[CameraEvent] = deque(maxlen=self.EVENT_HISTORY)

    def register_camera(self, camera_id: str, location: str = "",
                        zone: str = "general", camera_type: str = "fixed",
                        ip_address: str = "", firmware: str = "",
                        expected_firmware: str = "") -> Camera:
        """Register a security camera."""
        cam = Camera(
            camera_id=camera_id, location=location, zone=zone,
            camera_type=camera_type, ip_address=ip_address,
            firmware_version=firmware, expected_firmware=expected_firmware or firmware,
        )
        self._cameras[camera_id] = cam
        logger.info(f"Registered camera: {camera_id} at {location} [{zone}]")
        return cam

    def heartbeat(self, camera_id: str) -> None:
        """Process camera heartbeat."""
        cam = self._cameras.get(camera_id)
        if cam:
            cam.last_heartbeat = datetime.now(timezone.utc).isoformat()
            if cam.state == "offline":
                cam.state = "online"
                self._create_event(camera_id, "feed_restored",
                                   "Camera feed restored")

    def report_feed_lost(self, camera_id: str) -> list[CameraEvent]:
        """Report camera feed loss."""
        cam = self._cameras.get(camera_id)
        if not cam:
            return []
        cam.state = "offline"
        cam.is_recording = False
        return [self._create_event(camera_id, "feed_lost",
                                   f"Feed lost from {cam.location}")]

    def report_tamper(self, camera_id: str, details: str = "") -> list[CameraEvent]:
        """Report camera tampering."""
        cam = self._cameras.get(camera_id)
        if not cam:
            return []
        cam.state = "tampered"
        return [self._create_event(camera_id, "tamper_detected",
                                   details or f"Tamper detected at {cam.location}")]

    def report_obstruction(self, camera_id: str) -> list[CameraEvent]:
        """Report camera view obstruction (spray, cover, etc.)."""
        cam = self._cameras.get(camera_id)
        if not cam:
            return []
        cam.state = "obstructed"
        return [self._create_event(camera_id, "view_obstructed",
                                   f"View obstructed at {cam.location}")]

    def report_ptz_override(self, camera_id: str,
                            details: str = "") -> list[CameraEvent]:
        """Report unauthorized PTZ (pan-tilt-zoom) movement."""
        cam = self._cameras.get(camera_id)
        if not cam:
            return []
        return [self._create_event(camera_id, "ptz_override",
                                   details or f"Unauthorized PTZ at {cam.location}")]

    def check_firmware(self, camera_id: str,
                       current_firmware: str) -> list[CameraEvent]:
        """Check firmware version against expected."""
        cam = self._cameras.get(camera_id)
        if not cam:
            return []
        cam.firmware_version = current_firmware
        if cam.expected_firmware and current_firmware != cam.expected_firmware:
            return [self._create_event(
                camera_id, "firmware_mismatch",
                f"Firmware mismatch: expected {cam.expected_firmware}, "
                f"got {current_firmware}"
            )]
        return []

    def report_recording_failure(self, camera_id: str) -> list[CameraEvent]:
        """Report recording system failure."""
        cam = self._cameras.get(camera_id)
        if not cam:
            return []
        cam.is_recording = False
        return [self._create_event(camera_id, "recording_failure",
                                   f"Recording failure at {cam.location}")]

    def check_all_cameras(self) -> list[CameraEvent]:
        """Health check all cameras, detect offline ones."""
        events = []
        now = datetime.now(timezone.utc)
        for cam in self._cameras.values():
            if cam.state == "online":
                try:
                    hb = datetime.fromisoformat(cam.last_heartbeat.replace('Z', '+00:00'))
                    delta = (now - hb).total_seconds()
                    if delta > 300:  # 5 minutes no heartbeat
                        cam.state = "offline"
                        events.append(self._create_event(
                            cam.camera_id, "feed_lost",
                            f"No heartbeat for {int(delta)}s from {cam.location}"
                        ))
                except Exception:
                    pass
        return events

    def get_events(self, limit: int = 50,
                   event_type: Optional[str] = None,
                   zone: Optional[str] = None) -> list[CameraEvent]:
        """Get recent camera events."""
        events = list(self._events)
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if zone:
            events = [e for e in events if e.zone == zone]
        return events[-limit:]

    def summary(self) -> dict[str, Any]:
        from collections import defaultdict
        by_state = defaultdict(int)
        by_zone = defaultdict(int)
        for cam in self._cameras.values():
            by_state[cam.state] += 1
            by_zone[cam.zone] += 1
        return {
            "total_cameras": len(self._cameras),
            "total_events": len(self._events),
            "recording": sum(1 for c in self._cameras.values() if c.is_recording),
            "by_state": dict(by_state),
            "by_zone": dict(by_zone),
        }

    def _create_event(self, camera_id: str, event_type: str,
                      details: str) -> CameraEvent:
        cam = self._cameras.get(camera_id)
        zone = cam.zone if cam else "general"
        location = cam.location if cam else ""

        severity = EVENT_SEVERITY.get((event_type, zone),
                                      DEFAULT_SEVERITY.get(event_type, "medium"))

        event = CameraEvent(
            camera_id=camera_id, event_type=event_type,
            severity=severity, location=location,
            zone=zone, details=details,
        )
        self._events.append(event)
        self._log_event(event)

        if severity in ("critical", "high"):
            logger.warning(f"Camera event [{severity}]: {details}")
        else:
            logger.info(f"Camera event [{severity}]: {details}")

        return event

    def _log_event(self, event: CameraEvent) -> None:
        try:
            os.makedirs(os.path.dirname(self.LOG_PATH), exist_ok=True)
            with open(self.LOG_PATH, "a") as f:
                f.write(json.dumps(event.to_dict(), default=str) + "\n")
        except Exception:
            pass
