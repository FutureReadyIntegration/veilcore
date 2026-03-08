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
    source: str = ""
    event_type: str = ""
    severity: str = "info"
    zone: str = ""
    location: str = ""
    details: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "event_type": self.event_type,
            "severity": self.severity,
            "zone": self.zone,
            "location": self.location,
            "details": self.details,
            "timestamp": self.timestamp,
        }

@dataclass
class CorrelatedEvent:
    correlation_id: str = field(default_factory=lambda: f"CORR-{int(time.time() * 1000)}")
    pattern: str = ""
    severity: str = "critical"
    events: list[FusionEvent] = field(default_factory=list)
    description: str = ""
    recommended_action: str = ""
    confidence: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "pattern": self.pattern,
            "severity": self.severity,
            "event_count": len(self.events),
            "events": [e.to_dict() for e in self.events],
            "description": self.description,
            "recommended_action": self.recommended_action,
            "confidence": round(self.confidence, 2),
            "timestamp": self.timestamp,
        }

CORRELATION_PATTERNS = [
    {
        "name": "physical_intrusion",
        "description": "Camera disabled followed by door/motion trigger — possible intrusion",
        "requires": [
            {"source": "camera", "event_type": "feed_lost"},
            {"source": "sensor", "event_type": "triggered"},
        ],
        "time_window": 120,
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
]

class SensorFusionEngine:
    WINDOW_SIZE = 10000

    def __init__(self):
        self._events: deque[FusionEvent] = deque(maxlen=self.WINDOW_SIZE)
        self._correlations: list[CorrelatedEvent] = []
        self._analysis_count = 0

    def ingest(self, event: FusionEvent) -> None:
        self._events.append(event)

    def ingest_sensor_alert(self, alert) -> None:
        self._events.append(FusionEvent(
            source="sensor", event_type=alert.alert_type,
            severity=alert.severity, zone=alert.zone,
            location=alert.location, details=alert.message,
        ))

    def ingest_camera_event(self, event) -> None:
        self._events.append(FusionEvent(
            source="camera", event_type=event.event_type,
            severity=event.severity, zone=event.zone,
            location=event.location, details=event.details,
        ))

    def ingest_cyber_event(self, event_type: str, severity: str = "high",
                           zone: str = "", details: str = "") -> None:
        self._events.append(FusionEvent(
            source="cyber", event_type=event_type,
            severity=severity, zone=zone, details=details,
        ))

    def analyze(self) -> list[CorrelatedEvent]:
        self._analysis_count += 1
        return []

    def summary(self) -> dict[str, Any]:
        return {
            "events_in_buffer": len(self._events),
            "total_correlations": len(self._correlations),
            "analyses_run": self._analysis_count,
            "patterns_loaded": len(CORRELATION_PATTERNS),
        }
