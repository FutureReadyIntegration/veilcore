"""
VeilCore Mobile Alert Manager
================================
Manages alert routing, prioritization, and delivery
for the mobile interface.
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

logger = logging.getLogger("veilcore.mobile.alerts")


class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertCategory(str, Enum):
    THREAT = "threat"
    ORGAN_FAILURE = "organ_failure"
    MESH_DISRUPTION = "mesh_disruption"
    FEDERATION = "federation"
    COMPLIANCE = "compliance"
    PENTEST = "pentest"
    SYSTEM = "system"
    ML_PREDICTION = "ml_prediction"


@dataclass
class MobileAlert:
    """Alert payload for mobile delivery."""
    alert_id: str = field(default_factory=lambda: f"ALERT-{int(time.time() * 1000)}")
    title: str = ""
    message: str = ""
    severity: str = "info"
    category: str = "system"
    source_organ: str = ""
    target: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    actions: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id, "title": self.title,
            "message": self.message, "severity": self.severity,
            "category": self.category, "source_organ": self.source_organ,
            "target": self.target, "timestamp": self.timestamp,
            "acknowledged": self.acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "actions": self.actions, "data": self.data,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MobileAlert:
        valid = cls.__dataclass_fields__
        return cls(**{k: v for k, v in data.items() if k in valid})

    @classmethod
    def threat_alert(cls, title: str, message: str, severity: str = "high",
                     source: str = "", **kwargs) -> MobileAlert:
        return cls(
            title=title, message=message, severity=severity,
            category="threat", source_organ=source,
            actions=["investigate", "isolate", "escalate"], **kwargs,
        )

    @classmethod
    def organ_alert(cls, organ_name: str, status: str, **kwargs) -> MobileAlert:
        return cls(
            title=f"Organ Status Change: {organ_name}",
            message=f"Organ '{organ_name}' status changed to: {status}",
            severity="high" if status in ("failed", "dead") else "medium",
            category="organ_failure", source_organ=organ_name,
            actions=["restart_organ", "check_logs", "escalate"], **kwargs,
        )

    @classmethod
    def ml_alert(cls, threat_type: str, confidence: float, score: float,
                 **kwargs) -> MobileAlert:
        severity = "critical" if score >= 80 else "high" if score >= 60 else "medium"
        return cls(
            title=f"ML Threat Detected: {threat_type}",
            message=f"ML engine classified threat as '{threat_type}' "
                    f"with {confidence:.0%} confidence (score: {score:.1f}/100)",
            severity=severity, category="ml_prediction",
            source_organ="ml_predictor",
            actions=["investigate", "block_source", "full_scan"], **kwargs,
        )


class AlertManager:
    """
    Manages mobile alerts with priority queuing and persistence.

    Usage:
        mgr = AlertManager()
        mgr.push(MobileAlert.threat_alert("Ransomware Detected", "..."))
        recent = mgr.get_recent(10)
    """

    MAX_ALERTS = 10000
    LOG_PATH = "/var/log/veilcore/mobile-alerts.jsonl"

    def __init__(self, max_alerts: int = MAX_ALERTS):
        self._alerts: deque[MobileAlert] = deque(maxlen=max_alerts)
        self._by_id: dict[str, MobileAlert] = {}
        self._subscribers: list = []

    def push(self, alert: MobileAlert) -> None:
        """Push a new alert."""
        self._alerts.appendleft(alert)
        self._by_id[alert.alert_id] = alert
        self._log_alert(alert)

        # Notify subscribers
        for callback in self._subscribers:
            try:
                callback(alert)
            except Exception:
                pass

        logger.info(
            f"Alert [{alert.severity.upper()}] {alert.title} "
            f"(source: {alert.source_organ or 'system'})"
        )

    def get_recent(self, limit: int = 50) -> list[MobileAlert]:
        """Get most recent alerts."""
        return list(self._alerts)[:limit]

    def get_by_severity(self, severity: str, limit: int = 50) -> list[MobileAlert]:
        """Get alerts filtered by severity."""
        return [a for a in self._alerts if a.severity == severity][:limit]

    def get_unacknowledged(self, limit: int = 50) -> list[MobileAlert]:
        """Get unacknowledged alerts."""
        return [a for a in self._alerts if not a.acknowledged][:limit]

    def acknowledge(self, alert_id: str, operator: str) -> bool:
        """Acknowledge an alert."""
        alert = self._by_id.get(alert_id)
        if alert:
            alert.acknowledged = True
            alert.acknowledged_by = operator
            return True
        return False

    def subscribe(self, callback) -> None:
        """Subscribe to new alerts."""
        self._subscribers.append(callback)

    @property
    def active_count(self) -> int:
        return sum(1 for a in self._alerts if not a.acknowledged)

    @property
    def total_count(self) -> int:
        return len(self._alerts)

    def summary(self) -> dict[str, Any]:
        by_severity = {}
        for sev in AlertSeverity:
            count = sum(1 for a in self._alerts if a.severity == sev.value)
            if count > 0:
                by_severity[sev.value] = count
        return {
            "total": self.total_count,
            "active": self.active_count,
            "by_severity": by_severity,
        }

    def _log_alert(self, alert: MobileAlert) -> None:
        """Append alert to log file."""
        try:
            os.makedirs(os.path.dirname(self.LOG_PATH), exist_ok=True)
            with open(self.LOG_PATH, "a") as f:
                f.write(json.dumps(alert.to_dict(), default=str) + "\n")
        except Exception:
            pass
