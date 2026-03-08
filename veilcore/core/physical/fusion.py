"""
VeilCore Sensor Fusion Engine
================================
Correlates physical and cyber events to detect
coordinated attacks.

Attack patterns detected:
    - Camera disabled + door opened = physical intrusion
    - Sensor offline + network anomaly = coordinated attack
    - Multiple zone triggers = sweep attack
    - Environmental anomaly + system failure = sabotage
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("veilcore.physical.fusion")


@dataclass
class FusionEvent:
    """Any event from any source for correlation."""
    source: str = ""        # sensor, camera, cyber, rfid
    event_type: str = ""
    severity: str = "info"
    zone: str = ""
    location: str = ""
    details: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source, "event_type": self.event_type,
            "severity": self.severity, "zone": self.zone,
            "location": self.location, "details": self.details,
            "timestamp": self.timestamp,
        }


@dataclass
class CorrelatedEvent:
    """Correlated multi-source security event."""
    correlation_id: str = field(default_factory=lambda: f"CORR-{int(time.time() * 1000)}")
    pattern: str = ""
    severity: str = "critical"
    events: list[FusionEvent] = field(default_factory=list)
    description: str = ""
    recommended_action: str = ""
    confidence: float = 0.0     # 0.0 - 1.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "pattern": self.pattern, "severity": self.severity,
            "event_count": len(self.events),
            "events": [e.to_dict() for e in self.events],
            "description": self.description,
            "recommended_action": self.recommended_action,
            "confidence": round(self.confidence, 2),
            "timestamp": self.timestamp,
        }


# ── Correlation patterns ──
CORRELATION_PATTERNS = [
    {
        "name": "physical_intrusion",
        "description": "Camera disabled followed by door/motion trigger — possible intrusion",
        "requires": [
            {"source": "camera", "event_type": "feed_lost"},
            {"source": "sensor", "event_type": "triggered", "sensor_type": ["door", "motion"]},
        ],
        "time_window": 120,  # seconds
        "same_zone": True,
        "severity": "critical",
        "confidence": 0.85,
        "action": "Dispatch security to zone, lock down network segments",
    },
    {
        "name": "coordinated_attack",
        "description": "Physical sensor offline + network anomaly — coordinated cyber-physical attack",
        "requires": [
            {"source": "sensor", "event_type": "offline"},
            {"source": "cyber", "event_type": "network_anomaly"},
        ],
        "time_window": 300,
        "same_zone": False,
        "severity": "critical",
        "confidence": 0.80,
        "action": "Activate kill switch for affected segments, alert SOC and physical security",
    },
    {
        "name": "sweep_attack",
        "description": "Multiple zones triggered in sequence — area sweep",
        "requires": [
            {"source": "sensor", "event_type": "triggered", "min_zones": 3},
        ],
        "time_window": 180,
        "same_zone": False,
        "severity": "critical",
        "confidence": 0.75,
        "action": "Full facility alert, lock all doors, notify law enforcement",
    },
    {
        "name": "camera_sabotage",
        "description": "Multiple cameras tampered or obstructed",
        "requires": [
            {"source": "camera", "event_type": "tamper_detected", "min_count": 2},
        ],
        "time_window": 300,
        "same_zone": False,
        "severity": "critical",
        "confidence": 0.90,
        "action": "Assume intrusion in progress, dispatch security, enable all backup cameras",
    },
    {
        "name": "environmental_sabotage",
        "description": "Temperature spike + system failure — possible HVAC sabotage or fire",
        "requires": [
            {"source": "sensor", "event_type": "threshold_breach", "sensor_type": ["temperature"]},
            {"source": "sensor", "event_type": "triggered", "sensor_type": ["smoke"]},
        ],
        "time_window": 300,
        "same_zone": True,
        "severity": "critical",
        "confidence": 0.85,
        "action": "Emergency: evacuate zone, shut down equipment, activate fire suppression",
    },
]


class SensorFusionEngine:
    """
    Correlates events from multiple sources to detect
    coordinated attacks.

    Usage:
        fusion = SensorFusionEngine()

        # Feed events from various sources
        fusion.ingest(FusionEvent(source="camera", event_type="feed_lost",
                                  zone="server_room"))
        fusion.ingest(FusionEvent(source="sensor", event_type="triggered",
                                  zone="server_room"))

        # Check for correlations
        correlated = fusion.analyze()
    """

    WINDOW_SIZE = 10000

    def __init__(self):
        self._events: deque[FusionEvent] = deque(maxlen=self.WINDOW_SIZE)
        self._correlations: list[CorrelatedEvent] = []
        self._analysis_count = 0

    def ingest(self, event: FusionEvent) -> None:
        """Add an event to the fusion pipeline."""
        self._events.append(event)

    def ingest_sensor_alert(self, alert) -> None:
        """Ingest a SensorAlert as a FusionEvent."""
        self._events.append(FusionEvent(
            source="sensor", event_type=alert.alert_type,
            severity=alert.severity, zone=alert.zone,
            location=alert.location, details=alert.message,
        ))

    def ingest_camera_event(self, event) -> None:
        """Ingest a CameraEvent as a FusionEvent."""
        self._events.append(FusionEvent(
            source="camera", event_type=event.event_type,
            severity=event.severity, zone=event.zone,
            location=event.location, details=event.details,
        ))

    def ingest_cyber_event(self, event_type: str, severity: str = "high",
                           zone: str = "", details: str = "") -> None:
        """Ingest a cyber security event."""
        self._events.append(FusionEvent(
            source="cyber", event_type=event_type,
            severity=severity, zone=zone, details=details,
        ))

    def analyze(self) -> list[CorrelatedEvent]:
        """Analyze events for correlation patterns."""
        self._analysis_count += 1
        now = time.time()
        new_correlations = []

        for pattern in CORRELATION_PATTERNS:
            matched = self._check_pattern(pattern, now)
            if matched:
                new_correlations.append(matched)

        self._correlations.extend(new_correlations)

        if new_correlations:
            logger.warning(
                f"Fusion analysis #{self._analysis_count}: "
                f"{len(new_correlations)} correlated events detected"
            )
        return new_correlations

    def _check_pattern(self, pattern: dict, now: float) -> Optional[CorrelatedEvent]:
        """Check if events match a correlation pattern."""
        window = pattern["time_window"]
        recent = [e for e in self._events if now - e.timestamp < window]

        if not recent:
            return None

        requires = pattern["requires"]
        matched_events = []

        for req in requires:
            matching = [e for e in recent if e.source == req["source"]]

            if "event_type" in req:
                matching = [e for e in matching if e.event_type == req["event_type"]]

            # Check minimum zones
            if "min_zones" in req:
                zones = set(e.zone for e in matching)
                if len(zones) < req["min_zones"]:
                    return None

            # Check minimum count
            if "min_count" in req:
                if len(matching) < req["min_count"]:
                    return None

            if not matching:
                return None

            matched_events.extend(matching)

        # Check same-zone constraint
        if pattern.get("same_zone"):
            zones = [e.zone for e in matched_events if e.zone]
            if zones and len(set(zones)) > 1:
                return None

        if not matched_events:
            return None

        return CorrelatedEvent(
            pattern=pattern["name"],
            severity=pattern["severity"],
            events=matched_events,
            description=pattern["description"],
            recommended_action=pattern["action"],
            confidence=pattern["confidence"],
        )

    def get_correlations(self, limit: int = 20) -> list[CorrelatedEvent]:
        return self._correlations[-limit:]

    @property
    def event_count(self) -> int:
        return len(self._events)

    @property
    def correlation_count(self) -> int:
        return len(self._correlations)

    @property
    def analysis_count(self) -> int:
        return self._analysis_count

    def summary(self) -> dict[str, Any]:
        return {
            "events_in_buffer": len(self._events),
            "total_correlations": len(self._correlations),
            "analyses_run": self._analysis_count,
            "patterns_loaded": len(CORRELATION_PATTERNS),
        }
