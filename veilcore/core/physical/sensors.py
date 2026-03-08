"""
VeilCore Sensor Manager
==========================
Manages physical security sensors throughout the hospital.

Sensor types:
    - Motion/PIR: Detects movement in restricted areas
    - Door contact: Open/close state for server rooms, closets
    - Temperature: Server room thermal monitoring
    - Humidity: Environmental protection for equipment
    - Power: UPS status, voltage monitoring
    - Vibration: Tamper detection on cabinets/racks
    - Water leak: Data center flood detection
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("veilcore.physical.sensors")


class SensorType(str, Enum):
    MOTION = "motion"
    DOOR = "door"
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    POWER = "power"
    VIBRATION = "vibration"
    WATER_LEAK = "water_leak"
    GLASS_BREAK = "glass_break"
    SMOKE = "smoke"


class SensorState(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    TRIGGERED = "triggered"
    TAMPERED = "tampered"
    LOW_BATTERY = "low_battery"
    ERROR = "error"


class ZoneType(str, Enum):
    SERVER_ROOM = "server_room"
    NETWORK_CLOSET = "network_closet"
    DATA_CENTER = "data_center"
    PHARMACY = "pharmacy"
    NURSING_STATION = "nursing_station"
    LOBBY = "lobby"
    PARKING = "parking"
    GENERAL = "general"


@dataclass
class Sensor:
    """Physical security sensor."""
    sensor_id: str
    sensor_type: str = "motion"
    location: str = ""
    zone: str = "general"
    state: str = "online"
    battery_pct: Optional[float] = None
    last_reading: Optional[float] = None
    last_triggered: Optional[str] = None
    installed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Thresholds
    threshold_high: Optional[float] = None
    threshold_low: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sensor_id": self.sensor_id, "sensor_type": self.sensor_type,
            "location": self.location, "zone": self.zone,
            "state": self.state, "battery_pct": self.battery_pct,
            "last_reading": self.last_reading,
            "last_triggered": self.last_triggered,
            "threshold_high": self.threshold_high,
            "threshold_low": self.threshold_low,
        }


@dataclass
class SensorReading:
    """A single sensor reading."""
    sensor_id: str
    value: float
    unit: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_alert: bool = False
    raw: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sensor_id": self.sensor_id, "value": self.value,
            "unit": self.unit, "timestamp": self.timestamp,
            "is_alert": self.is_alert,
        }


@dataclass
class SensorAlert:
    """Alert triggered by sensor."""
    alert_id: str = field(default_factory=lambda: f"PHYS-{int(time.time() * 1000)}")
    sensor_id: str = ""
    sensor_type: str = ""
    zone: str = ""
    location: str = ""
    severity: str = "medium"
    alert_type: str = ""    # threshold_breach, tamper, offline, triggered
    message: str = ""
    value: Optional[float] = None
    threshold: Optional[float] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    acknowledged: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id, "sensor_id": self.sensor_id,
            "sensor_type": self.sensor_type, "zone": self.zone,
            "location": self.location, "severity": self.severity,
            "alert_type": self.alert_type, "message": self.message,
            "value": self.value, "threshold": self.threshold,
            "timestamp": self.timestamp, "acknowledged": self.acknowledged,
        }


# ── Zone severity mapping ──
ZONE_SEVERITY = {
    "server_room": "critical",
    "data_center": "critical",
    "network_closet": "high",
    "pharmacy": "high",
    "nursing_station": "medium",
    "lobby": "low",
    "parking": "low",
    "general": "medium",
}


class SensorManager:
    """
    Manages all physical security sensors.

    Usage:
        mgr = SensorManager()
        mgr.register_sensor("MOTION-SR1", "motion", "Server Room A", zone="server_room")
        mgr.register_sensor("TEMP-SR1", "temperature", "Server Room A",
                            zone="server_room", threshold_high=85.0, threshold_low=50.0)

        alerts = mgr.process_reading("TEMP-SR1", 88.5, unit="°F")
        alerts = mgr.process_trigger("MOTION-SR1")
    """

    HISTORY_SIZE = 10000
    LOG_PATH = "/var/log/veilcore/physical-sensors.jsonl"

    def __init__(self):
        self._sensors: dict[str, Sensor] = {}
        self._readings: deque[SensorReading] = deque(maxlen=self.HISTORY_SIZE)
        self._alerts: deque[SensorAlert] = deque(maxlen=5000)
        self._trigger_history: dict[str, list[float]] = defaultdict(list)

    def register_sensor(self, sensor_id: str, sensor_type: str,
                        location: str = "", zone: str = "general",
                        threshold_high: Optional[float] = None,
                        threshold_low: Optional[float] = None,
                        battery_pct: Optional[float] = None) -> Sensor:
        """Register a physical sensor."""
        sensor = Sensor(
            sensor_id=sensor_id, sensor_type=sensor_type,
            location=location, zone=zone,
            threshold_high=threshold_high, threshold_low=threshold_low,
            battery_pct=battery_pct,
        )
        self._sensors[sensor_id] = sensor
        logger.info(f"Registered sensor: {sensor_id} ({sensor_type}) at {location} [{zone}]")
        return sensor

    def process_reading(self, sensor_id: str, value: float,
                        unit: str = "") -> list[SensorAlert]:
        """Process a sensor reading and check thresholds."""
        sensor = self._sensors.get(sensor_id)
        if not sensor:
            logger.warning(f"Reading from unknown sensor: {sensor_id}")
            return []

        reading = SensorReading(sensor_id=sensor_id, value=value, unit=unit)
        sensor.last_reading = value
        alerts = []

        # Check high threshold
        if sensor.threshold_high is not None and value > sensor.threshold_high:
            reading.is_alert = True
            alert = SensorAlert(
                sensor_id=sensor_id, sensor_type=sensor.sensor_type,
                zone=sensor.zone, location=sensor.location,
                severity=ZONE_SEVERITY.get(sensor.zone, "medium"),
                alert_type="threshold_breach",
                message=f"{sensor.sensor_type} HIGH at {sensor.location}: "
                        f"{value}{unit} > {sensor.threshold_high}{unit}",
                value=value, threshold=sensor.threshold_high,
            )
            alerts.append(alert)
            self._alerts.append(alert)
            self._log_alert(alert)

        # Check low threshold
        if sensor.threshold_low is not None and value < sensor.threshold_low:
            reading.is_alert = True
            alert = SensorAlert(
                sensor_id=sensor_id, sensor_type=sensor.sensor_type,
                zone=sensor.zone, location=sensor.location,
                severity=ZONE_SEVERITY.get(sensor.zone, "medium"),
                alert_type="threshold_breach",
                message=f"{sensor.sensor_type} LOW at {sensor.location}: "
                        f"{value}{unit} < {sensor.threshold_low}{unit}",
                value=value, threshold=sensor.threshold_low,
            )
            alerts.append(alert)
            self._alerts.append(alert)
            self._log_alert(alert)

        self._readings.append(reading)
        return alerts

    def process_trigger(self, sensor_id: str) -> list[SensorAlert]:
        """Process a binary sensor trigger (motion, door, glass break, etc.)."""
        sensor = self._sensors.get(sensor_id)
        if not sensor:
            logger.warning(f"Trigger from unknown sensor: {sensor_id}")
            return []

        now = time.time()
        sensor.state = "triggered"
        sensor.last_triggered = datetime.now(timezone.utc).isoformat()

        self._trigger_history[sensor_id].append(now)
        # Keep last 100
        self._trigger_history[sensor_id] = self._trigger_history[sensor_id][-100:]

        alerts = []

        # Always alert for critical zones
        severity = ZONE_SEVERITY.get(sensor.zone, "medium")
        alert = SensorAlert(
            sensor_id=sensor_id, sensor_type=sensor.sensor_type,
            zone=sensor.zone, location=sensor.location,
            severity=severity, alert_type="triggered",
            message=f"{sensor.sensor_type} triggered at {sensor.location} [{sensor.zone}]",
        )
        alerts.append(alert)
        self._alerts.append(alert)
        self._log_alert(alert)

        # Check for rapid triggering (tamper or sustained intrusion)
        recent = [t for t in self._trigger_history[sensor_id] if now - t < 30]
        if len(recent) > 5:
            tamper_alert = SensorAlert(
                sensor_id=sensor_id, sensor_type=sensor.sensor_type,
                zone=sensor.zone, location=sensor.location,
                severity="critical", alert_type="tamper",
                message=f"Rapid triggering on {sensor_id} at {sensor.location}: "
                        f"{len(recent)} triggers in 30s",
            )
            alerts.append(tamper_alert)
            self._alerts.append(tamper_alert)
            self._log_alert(tamper_alert)
            sensor.state = "tampered"

        return alerts

    def mark_offline(self, sensor_id: str) -> Optional[SensorAlert]:
        """Mark a sensor as offline (heartbeat missed)."""
        sensor = self._sensors.get(sensor_id)
        if not sensor:
            return None

        sensor.state = "offline"
        alert = SensorAlert(
            sensor_id=sensor_id, sensor_type=sensor.sensor_type,
            zone=sensor.zone, location=sensor.location,
            severity="high" if sensor.zone in ("server_room", "data_center") else "medium",
            alert_type="offline",
            message=f"Sensor offline: {sensor_id} at {sensor.location}",
        )
        self._alerts.append(alert)
        self._log_alert(alert)
        return alert

    def get_zone_status(self, zone: str) -> dict[str, Any]:
        """Get all sensors in a zone."""
        zone_sensors = [s for s in self._sensors.values() if s.zone == zone]
        return {
            "zone": zone,
            "sensor_count": len(zone_sensors),
            "online": sum(1 for s in zone_sensors if s.state == "online"),
            "triggered": sum(1 for s in zone_sensors if s.state == "triggered"),
            "offline": sum(1 for s in zone_sensors if s.state == "offline"),
            "tampered": sum(1 for s in zone_sensors if s.state == "tampered"),
            "sensors": [s.to_dict() for s in zone_sensors],
        }

    def get_alerts(self, limit: int = 50,
                   severity: Optional[str] = None,
                   zone: Optional[str] = None) -> list[SensorAlert]:
        """Get recent alerts with optional filtering."""
        alerts = list(self._alerts)
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if zone:
            alerts = [a for a in alerts if a.zone == zone]
        return alerts[-limit:]

    def summary(self) -> dict[str, Any]:
        by_type = defaultdict(int)
        by_state = defaultdict(int)
        by_zone = defaultdict(int)
        for s in self._sensors.values():
            by_type[s.sensor_type] += 1
            by_state[s.state] += 1
            by_zone[s.zone] += 1

        return {
            "total_sensors": len(self._sensors),
            "total_readings": len(self._readings),
            "total_alerts": len(self._alerts),
            "by_type": dict(by_type),
            "by_state": dict(by_state),
            "by_zone": dict(by_zone),
        }

    def _log_alert(self, alert: SensorAlert) -> None:
        try:
            os.makedirs(os.path.dirname(self.LOG_PATH), exist_ok=True)
            with open(self.LOG_PATH, "a") as f:
                f.write(json.dumps(alert.to_dict(), default=str) + "\n")
        except Exception:
            pass

    @property
    def sensor_count(self) -> int:
        return len(self._sensors)

    @property
    def alert_count(self) -> int:
        return len(self._alerts)
