"""
Veil Insider Threat Detection Organ
====================================
P1 Security Organ: "The greatest threats often come from within."

Detects internal security threats:
- Privilege abuse patterns
- Data exfiltration attempts
- Credential sharing/compromise
- Policy violations
- After-hours suspicious activity
- Peer deviation analysis

Uses statistical analysis and rule-based detection (no ML dependencies).
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, List, Any, Set
import hashlib


# ============================================================================
# Configuration
# ============================================================================

class InsiderThreatConfig:
    """
    Configuration for insider threat detection.

    Instance-based, so the runner can override values if needed.
    """

    def __init__(
        self,
        storage_path: Path = Path("/var/lib/veil/insider_threat"),
        baseline_days: int = 30,
        mass_access_threshold: int = 100,
        after_hours_start: int = 20,
        after_hours_end: int = 6,
        deviation_threshold: float = 2.5,
        high_risk_threshold: int = 80,
        medium_risk_threshold: int = 50,
        min_peers_for_comparison: int = 3,
        peer_deviation_multiplier: float = 3.0,
        analysis_window_hours: int = 24,
    ):
        # Detection windows
        self.ANALYSIS_WINDOW_HOURS: int = analysis_window_hours
        self.BASELINE_WINDOW_DAYS: int = baseline_days

        # Thresholds
        self.DEVIATION_THRESHOLD: float = deviation_threshold
        self.HIGH_RISK_THRESHOLD: int = high_risk_threshold
        self.MEDIUM_RISK_THRESHOLD: int = medium_risk_threshold

        # Activity limits
        self.MAX_FAILED_LOGINS_PER_HOUR: int = 5
        self.MAX_SENSITIVE_ACCESS_PER_DAY: int = 50
        self.MAX_RECORDS_VIEWED_PER_HOUR: int = mass_access_threshold
        self.AFTER_HOURS_START: int = after_hours_start
        self.AFTER_HOURS_END: int = after_hours_end

        # Peer comparison
        self.MIN_PEERS_FOR_COMPARISON: int = min_peers_for_comparison
        self.PEER_DEVIATION_MULTIPLIER: float = peer_deviation_multiplier

        # Storage
        self.DATA_DIR: Path = storage_path

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_window_hours": self.ANALYSIS_WINDOW_HOURS,
            "baseline_window_days": self.BASELINE_WINDOW_DAYS,
            "deviation_threshold": self.DEVIATION_THRESHOLD,
            "high_risk_threshold": self.HIGH_RISK_THRESHOLD,
            "medium_risk_threshold": self.MEDIUM_RISK_THRESHOLD,
            "max_failed_logins_per_hour": self.MAX_FAILED_LOGINS_PER_HOUR,
            "max_sensitive_access_per_day": self.MAX_SENSITIVE_ACCESS_PER_DAY,
            "max_records_viewed_per_hour": self.MAX_RECORDS_VIEWED_PER_HOUR,
            "after_hours_start": self.AFTER_HOURS_START,
            "after_hours_end": self.AFTER_HOURS_END,
            "min_peers_for_comparison": self.MIN_PEERS_FOR_COMPARISON,
            "peer_deviation_multiplier": self.PEER_DEVIATION_MULTIPLIER,
            "data_dir": str(self.DATA_DIR),
        }


# ============================================================================
# Data Models
# ============================================================================

class ThreatIndicator(str, Enum):
    """Types of insider threat indicators."""
    PRIVILEGE_ABUSE = "privilege_abuse"
    DATA_EXFILTRATION = "data_exfiltration"
    CREDENTIAL_ANOMALY = "credential_anomaly"
    POLICY_VIOLATION = "policy_violation"
    AFTER_HOURS_ACCESS = "after_hours_access"
    PEER_DEVIATION = "peer_deviation"
    ACCESS_ESCALATION = "access_escalation"
    MASS_DATA_ACCESS = "mass_data_access"
    TERMINATED_USER = "terminated_user"
    SHARED_CREDENTIALS = "shared_credentials"


class RiskLevel(str, Enum):
    """Risk assessment levels."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class UserActivity:
    """Tracked user activity."""
    timestamp: datetime
    user_id: str
    action: str
    resource: str
    ip_address: Optional[str] = None
    success: bool = True
    data_volume: int = 0  # bytes accessed
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ThreatAlert:
    """Insider threat alert."""
    id: str
    timestamp: datetime
    user_id: str
    indicator: ThreatIndicator
    risk_level: RiskLevel
    score: int
    description: str
    evidence: List[str]
    recommended_actions: List[str]
    acknowledged: bool = False
    resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "indicator": self.indicator.value,
            "risk_level": self.risk_level.value,
            "score": self.score,
            "description": self.description,
            "evidence": self.evidence,
            "recommended_actions": self.recommended_actions,
            "acknowledged": self.acknowledged,
            "resolved": self.resolved,
        }


@dataclass
class UserProfile:
    """User behavior profile for baseline comparison."""
    user_id: str
    role: str
    department: str
    avg_daily_logins: float = 0.0
    avg_daily_access_count: float = 0.0
    avg_daily_data_volume: float = 0.0
    typical_hours: List[int] = field(default_factory=lambda: list(range(8, 18)))
    typical_resources: Set[str] = field(default_factory=set)
    typical_ips: Set[str] = field(default_factory=set)
    peer_group: str = "default"
    last_updated: datetime = field(default_factory=datetime.utcnow)


# ============================================================================
# Detection Engine
# ============================================================================

class InsiderThreatDetector:
    """
    Insider Threat Detection Engine.

    Uses behavioral analysis and rule-based detection to identify
    potential insider threats without ML dependencies.
    """

    def __init__(self, config: InsiderThreatConfig):
        self.config = config
        self.data_dir = config.DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # In-memory state
        self._user_profiles: Dict[str, UserProfile] = {}
        self._user_activities: Dict[str, List[UserActivity]] = defaultdict(list)
        self._alerts: List[ThreatAlert] = []
        self._peer_groups: Dict[str, List[str]] = defaultdict(list)

        self._load_state()

    # ----------------------------------------------------------------------
    # Persistence
    # ----------------------------------------------------------------------
    def _load_state(self):
        """Load persisted state."""
        profiles_file = self.data_dir / "profiles.json"
        if profiles_file.exists():
            try:
                data = json.loads(profiles_file.read_text())
                for user_id, profile_data in data.items():
                    self._user_profiles[user_id] = UserProfile(
                        user_id=user_id,
                        role=profile_data.get("role", "unknown"),
                        department=profile_data.get("department", "unknown"),
                        avg_daily_logins=profile_data.get("avg_daily_logins", 0),
                        avg_daily_access_count=profile_data.get("avg_daily_access_count", 0),
                        avg_daily_data_volume=profile_data.get("avg_daily_data_volume", 0),
                        typical_hours=profile_data.get("typical_hours", list(range(8, 18))),
                        typical_resources=set(profile_data.get("typical_resources", [])),
                        typical_ips=set(profile_data.get("typical_ips", [])),
                        peer_group=profile_data.get("peer_group", "default"),
                    )
            except Exception:
                # Corrupt or unreadable state should not kill the organ
                pass

    def _save_state(self):
        """Save state to disk."""
        profiles_file = self.data_dir / "profiles.json"
        data = {}
        for user_id, profile in self._user_profiles.items():
            data[user_id] = {
                "role": profile.role,
                "department": profile.department,
                "avg_daily_logins": profile.avg_daily_logins,
                "avg_daily_access_count": profile.avg_daily_access_count,
                "avg_daily_data_volume": profile.avg_daily_data_volume,
                "typical_hours": profile.typical_hours,
                "typical_resources": list(profile.typical_resources),
                "typical_ips": list(profile.typical_ips),
                "peer_group": profile.peer_group,
            }
        profiles_file.write_text(json.dumps(data, indent=2))

    # ----------------------------------------------------------------------
    # Activity + Alerts
    # ----------------------------------------------------------------------
    def record_activity(self, activity: UserActivity):
        """Record a user activity for analysis."""
        self._user_activities[activity.user_id].append(activity)

        cutoff = datetime.utcnow() - timedelta(days=self.config.BASELINE_WINDOW_DAYS)
        self._user_activities[activity.user_id] = [
            a for a in self._user_activities[activity.user_id] if a.timestamp >= cutoff
        ]

    def get_alerts(self, unresolved_only: bool = False) -> List[ThreatAlert]:
        if unresolved_only:
            return [a for a in self._alerts if not a.resolved]
        return list(self._alerts)

    # ----------------------------------------------------------------------
    # (Placeholder) Detection hooks
    # ----------------------------------------------------------------------
    def _generate_alert_id(self, user_id: str, indicator: ThreatIndicator) -> str:
        base = f"{user_id}-{indicator.value}-{datetime.utcnow().isoformat()}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]

    def _add_alert(
        self,
        user_id: str,
        indicator: ThreatIndicator,
        risk_level: RiskLevel,
        score: int,
        description: str,
        evidence: List[str],
        recommended_actions: Optional[List[str]] = None,
    ):
        alert = ThreatAlert(
            id=self._generate_alert_id(user_id, indicator),
            timestamp=datetime.utcnow(),
            user_id=user_id,
            indicator=indicator,
            risk_level=risk_level,
            score=score,
            description=description,
            evidence=evidence,
            recommended_actions=recommended_actions or [],
        )
        self._alerts.append(alert)

    # You can extend here with:
    # - privilege abuse detection
    # - mass access detection
    # - after-hours anomalies
    # - peer deviation scoring
