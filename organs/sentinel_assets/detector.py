"""
Sentinel Organ - Behavioral Anomaly Detection
==============================================
P1 Security Organ: "I watch. I learn. I protect."

Implements real-time behavioral analysis:
- User behavior profiling
- Anomaly scoring
- Deviation detection
- Automated alerting
- Integration with Zero-Trust decisions

No ML dependencies - uses statistical methods for lightweight deployment.
"""

from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Optional, Dict, List, Any, Tuple


# ============================================================================
# Configuration
# ============================================================================

class SentinelConfig:
    """Sentinel configuration."""
    # Behavior tracking
    PROFILE_WINDOW_DAYS: int = 30
    ANOMALY_THRESHOLD: float = 2.5  # Standard deviations
    MIN_SAMPLES_FOR_BASELINE: int = 10
    DATA_DIR: Path = Path("/var/lib/veil/sentinel")    
    # Alert thresholds
    HIGH_RISK_SCORE: int = 80
    MEDIUM_RISK_SCORE: int = 50
    LOW_RISK_SCORE: int = 30
    
    # Rate limiting for detection
    MAX_EVENTS_PER_MINUTE: int = 100
    BURST_DETECTION_WINDOW: int = 60  # seconds
    BURST_THRESHOLD: int = 20  # events in window
    
    # Storage
    DATA_DIR: Path = Path("/var/lib/veil/sentinel")
    PROFILES_FILE: Path = DATA_DIR / "profiles.json"
    ALERTS_FILE: Path = DATA_DIR / "alerts.json"
    EVENTS_FILE: Path = DATA_DIR / "events.json"


# ============================================================================
# Data Models
# ============================================================================

class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnomalyType(str, Enum):
    """Types of detected anomalies."""
    UNUSUAL_TIME = "unusual_time"
    UNUSUAL_LOCATION = "unusual_location"
    UNUSUAL_RESOURCE = "unusual_resource"
    RAPID_REQUESTS = "rapid_requests"
    FAILED_AUTH_SPIKE = "failed_auth_spike"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    UNUSUAL_PATTERN = "unusual_pattern"


@dataclass
class BehaviorEvent:
    """A single behavior event for tracking."""
    timestamp: datetime
    user_id: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "ip_address": self.ip_address,
            "success": self.success,
            "metadata": self.metadata,
        }


@dataclass
class UserProfile:
    """User behavior profile for baseline comparison."""
    user_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Time patterns (hour -> event count)
    hourly_activity: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    
    # Resource patterns (resource_type -> count)
    resource_access: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # IP patterns (ip -> count)
    ip_addresses: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Action patterns (action -> count)
    actions: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Statistics
    total_events: int = 0
    avg_daily_events: float = 0.0
    std_daily_events: float = 0.0
    last_activity: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "hourly_activity": dict(self.hourly_activity),
            "resource_access": dict(self.resource_access),
            "ip_addresses": dict(self.ip_addresses),
            "actions": dict(self.actions),
            "total_events": self.total_events,
            "avg_daily_events": self.avg_daily_events,
            "std_daily_events": self.std_daily_events,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> UserProfile:
        profile = cls(
            user_id=data["user_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            total_events=data.get("total_events", 0),
            avg_daily_events=data.get("avg_daily_events", 0.0),
            std_daily_events=data.get("std_daily_events", 0.0),
            last_activity=datetime.fromisoformat(data["last_activity"]) if data.get("last_activity") else None,
        )
        profile.hourly_activity = defaultdict(int, {int(k): v for k, v in data.get("hourly_activity", {}).items()})
        profile.resource_access = defaultdict(int, data.get("resource_access", {}))
        profile.ip_addresses = defaultdict(int, data.get("ip_addresses", {}))
        profile.actions = defaultdict(int, data.get("actions", {}))
        return profile


@dataclass
class Anomaly:
    """Detected anomaly."""
    id: str
    timestamp: datetime
    user_id: str
    anomaly_type: AnomalyType
    severity: AlertSeverity
    score: float
    description: str
    evidence: Dict[str, Any]
    related_events: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "anomaly_type": self.anomaly_type.value,
            "severity": self.severity.value,
            "score": self.score,
            "description": self.description,
            "evidence": self.evidence,
            "related_events": self.related_events,
        }


@dataclass 
class Alert:
    """Security alert."""
    id: str
    timestamp: datetime
    severity: AlertSeverity
    title: str
    description: str
    user_id: Optional[str] = None
    anomalies: List[str] = field(default_factory=list)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved: bool = False
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "user_id": self.user_id,
            "anomalies": self.anomalies,
            "acknowledged": self.acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolved": self.resolved,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


# ============================================================================
# Sentinel - Behavioral Anomaly Detection Engine
# ============================================================================

class Sentinel:
    """
    Behavioral anomaly detection engine.
    
    "I watch. I learn. I protect."
    
    Uses statistical methods (no ML) for:
    - User behavior profiling
    - Anomaly detection
    - Alert generation
    """
    
    def __init__(self, config: SentinelConfig = None):
        self.config = config or SentinelConfig()
        self._profiles: Dict[str, UserProfile] = {}
        self._recent_events: Dict[str, List[BehaviorEvent]] = defaultdict(list)
        self._alerts: Dict[str, Alert] = {}
        self._event_counts: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))  # user -> {timestamp_minute -> count}
        self._lock = Lock()
        self._init_storage()
        self._load_data()
    
    def _init_storage(self):
        """Initialize storage directories."""
        self.config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    def _load_data(self):
        """Load profiles and alerts from storage."""
        if self.config.PROFILES_FILE.exists():
            try:
                data = json.loads(self.config.PROFILES_FILE.read_text())
                for profile_data in data.get("profiles", []):
                    profile = UserProfile.from_dict(profile_data)
                    self._profiles[profile.user_id] = profile
            except Exception:
                pass
    
    def _save_data(self):
        """Save profiles to storage."""
        profile_data = {
            "version": "1.0",
            "updated_at": datetime.utcnow().isoformat(),
            "profiles": [p.to_dict() for p in self._profiles.values()]
        }
        tmp = self.config.PROFILES_FILE.with_suffix('.tmp')
        tmp.write_text(json.dumps(profile_data, indent=2))
        tmp.rename(self.config.PROFILES_FILE)
    
    # ========================================================================
    # Event Processing
    # ========================================================================
    
    def record_event(self, event: BehaviorEvent) -> List[Anomaly]:
        """
        Record a behavior event and check for anomalies.
        
        Returns list of detected anomalies.
        """
        with self._lock:
            # Get or create user profile
            profile = self._get_or_create_profile(event.user_id)
            
            # Store recent event
            self._recent_events[event.user_id].append(event)
            
            # Trim old events (keep last 1000 per user)
            if len(self._recent_events[event.user_id]) > 1000:
                self._recent_events[event.user_id] = self._recent_events[event.user_id][-1000:]
            
            # Track event rate
            minute_key = int(event.timestamp.timestamp() // 60)
            self._event_counts[event.user_id][minute_key] += 1
            
            # Update profile
            self._update_profile(profile, event)
            
            # Detect anomalies
            anomalies = self._detect_anomalies(profile, event)
            
            # Generate alerts if needed
            self._process_anomalies(anomalies)
            
            return anomalies
    
    def _get_or_create_profile(self, user_id: str) -> UserProfile:
        """Get existing profile or create new one."""
        if user_id not in self._profiles:
            self._profiles[user_id] = UserProfile(user_id=user_id)
        return self._profiles[user_id]
    
    def _update_profile(self, profile: UserProfile, event: BehaviorEvent):
        """Update profile with new event data."""
        profile.updated_at = datetime.utcnow()
        profile.last_activity = event.timestamp
        profile.total_events += 1
        
        # Update hourly activity
        hour = event.timestamp.hour
        profile.hourly_activity[hour] += 1
        
        # Update resource access
        profile.resource_access[event.resource_type] += 1
        
        # Update IP addresses
        if event.ip_address:
            profile.ip_addresses[event.ip_address] += 1
        
        # Update actions
        profile.actions[event.action] += 1
        
        # Recalculate daily statistics periodically
        if profile.total_events % 100 == 0:
            self._recalculate_statistics(profile)
        
        # Save periodically
        if profile.total_events % 50 == 0:
            self._save_data()
    
    def _recalculate_statistics(self, profile: UserProfile):
        """Recalculate profile statistics."""
        events = self._recent_events.get(profile.user_id, [])
        if len(events) < 2:
            return
        
        # Group events by day
        daily_counts = defaultdict(int)
        for event in events:
            day_key = event.timestamp.strftime("%Y-%m-%d")
            daily_counts[day_key] += 1
        
        counts = list(daily_counts.values())
        if counts:
            profile.avg_daily_events = statistics.mean(counts)
            profile.std_daily_events = statistics.stdev(counts) if len(counts) > 1 else 0.0
    
    # ========================================================================
    # Anomaly Detection
    # ========================================================================
    
    def _detect_anomalies(self, profile: UserProfile, event: BehaviorEvent) -> List[Anomaly]:
        """Detect anomalies in the current event."""
        anomalies = []
        
        # Only detect if we have enough baseline data
        if profile.total_events < self.config.MIN_SAMPLES_FOR_BASELINE:
            return anomalies
        
        # Check for unusual time
        time_anomaly = self._check_unusual_time(profile, event)
        if time_anomaly:
            anomalies.append(time_anomaly)
        
        # Check for unusual location (IP)
        location_anomaly = self._check_unusual_location(profile, event)
        if location_anomaly:
            anomalies.append(location_anomaly)
        
        # Check for unusual resource access
        resource_anomaly = self._check_unusual_resource(profile, event)
        if resource_anomaly:
            anomalies.append(resource_anomaly)
        
        # Check for rapid requests (burst detection)
        burst_anomaly = self._check_rapid_requests(profile, event)
        if burst_anomaly:
            anomalies.append(burst_anomaly)
        
        # Check for failed auth spike
        if not event.success and event.action in ["login", "auth", "authenticate"]:
            auth_anomaly = self._check_failed_auth_spike(profile, event)
            if auth_anomaly:
                anomalies.append(auth_anomaly)
        
        return anomalies
    
    def _check_unusual_time(self, profile: UserProfile, event: BehaviorEvent) -> Optional[Anomaly]:
        """Check if access time is unusual for this user."""
        hour = event.timestamp.hour
        hour_count = profile.hourly_activity.get(hour, 0)
        total_hours = sum(profile.hourly_activity.values())
        
        if total_hours < self.config.MIN_SAMPLES_FOR_BASELINE:
            return None
        
        # Calculate expected probability for this hour
        expected_prob = hour_count / total_hours if total_hours > 0 else 0
        
        # Flag if this hour represents less than 1% of activity
        if expected_prob < 0.01 and profile.total_events > 100:
            import uuid
            return Anomaly(
                id=str(uuid.uuid4()),
                timestamp=event.timestamp,
                user_id=event.user_id,
                anomaly_type=AnomalyType.UNUSUAL_TIME,
                severity=AlertSeverity.MEDIUM,
                score=60.0,
                description=f"Access at unusual hour ({hour}:00) - only {expected_prob*100:.1f}% of historical activity",
                evidence={
                    "hour": hour,
                    "hour_count": hour_count,
                    "total_hours": total_hours,
                    "expected_probability": expected_prob,
                }
            )
        return None
    
    def _check_unusual_location(self, profile: UserProfile, event: BehaviorEvent) -> Optional[Anomaly]:
        """Check if IP address is unusual for this user."""
        if not event.ip_address:
            return None
        
        ip_count = profile.ip_addresses.get(event.ip_address, 0)
        total_ips = sum(profile.ip_addresses.values())
        
        # New IP that's never been seen
        if ip_count == 0 and total_ips >= self.config.MIN_SAMPLES_FOR_BASELINE:
            import uuid
            return Anomaly(
                id=str(uuid.uuid4()),
                timestamp=event.timestamp,
                user_id=event.user_id,
                anomaly_type=AnomalyType.UNUSUAL_LOCATION,
                severity=AlertSeverity.HIGH,
                score=75.0,
                description=f"Access from new IP address: {event.ip_address}",
                evidence={
                    "ip_address": event.ip_address,
                    "known_ips": list(profile.ip_addresses.keys())[:10],
                    "total_known_ips": len(profile.ip_addresses),
                }
            )
        return None
    
    def _check_unusual_resource(self, profile: UserProfile, event: BehaviorEvent) -> Optional[Anomaly]:
        """Check if resource access is unusual for this user."""
        resource_count = profile.resource_access.get(event.resource_type, 0)
        total_resources = sum(profile.resource_access.values())
        
        # New resource type never accessed before
        if resource_count == 0 and total_resources >= self.config.MIN_SAMPLES_FOR_BASELINE:
            # Check if it's a sensitive resource
            sensitive_resources = ["epic", "imprivata", "admin", "security", "audit"]
            is_sensitive = any(s in event.resource_type.lower() for s in sensitive_resources)
            
            import uuid
            return Anomaly(
                id=str(uuid.uuid4()),
                timestamp=event.timestamp,
                user_id=event.user_id,
                anomaly_type=AnomalyType.UNUSUAL_RESOURCE,
                severity=AlertSeverity.HIGH if is_sensitive else AlertSeverity.MEDIUM,
                score=80.0 if is_sensitive else 50.0,
                description=f"First-time access to resource type: {event.resource_type}",
                evidence={
                    "resource_type": event.resource_type,
                    "is_sensitive": is_sensitive,
                    "known_resources": list(profile.resource_access.keys()),
                }
            )
        return None
    
    def _check_rapid_requests(self, profile: UserProfile, event: BehaviorEvent) -> Optional[Anomaly]:
        """Check for burst of rapid requests."""
        current_minute = int(event.timestamp.timestamp() // 60)
        
        # Count events in the last window
        recent_count = 0
        for minute_offset in range(self.config.BURST_DETECTION_WINDOW // 60):
            recent_count += self._event_counts[event.user_id].get(current_minute - minute_offset, 0)
        
        if recent_count > self.config.BURST_THRESHOLD:
            import uuid
            return Anomaly(
                id=str(uuid.uuid4()),
                timestamp=event.timestamp,
                user_id=event.user_id,
                anomaly_type=AnomalyType.RAPID_REQUESTS,
                severity=AlertSeverity.HIGH,
                score=85.0,
                description=f"Rapid request burst detected: {recent_count} requests in {self.config.BURST_DETECTION_WINDOW}s",
                evidence={
                    "request_count": recent_count,
                    "window_seconds": self.config.BURST_DETECTION_WINDOW,
                    "threshold": self.config.BURST_THRESHOLD,
                }
            )
        return None
    
    def _check_failed_auth_spike(self, profile: UserProfile, event: BehaviorEvent) -> Optional[Anomaly]:
        """Check for spike in failed authentication attempts."""
        # Count recent failed auths
        recent_events = self._recent_events.get(event.user_id, [])
        cutoff = event.timestamp - timedelta(minutes=5)
        
        failed_auths = [
            e for e in recent_events
            if e.timestamp > cutoff 
            and not e.success 
            and e.action in ["login", "auth", "authenticate"]
        ]
        
        if len(failed_auths) >= 3:
            import uuid
            return Anomaly(
                id=str(uuid.uuid4()),
                timestamp=event.timestamp,
                user_id=event.user_id,
                anomaly_type=AnomalyType.FAILED_AUTH_SPIKE,
                severity=AlertSeverity.CRITICAL,
                score=95.0,
                description=f"Multiple failed authentication attempts: {len(failed_auths)} in 5 minutes",
                evidence={
                    "failed_count": len(failed_auths),
                    "window_minutes": 5,
                    "ips_involved": list(set(e.ip_address for e in failed_auths if e.ip_address)),
                }
            )
        return None
    
    # ========================================================================
    # Alert Processing
    # ========================================================================
    
    def _process_anomalies(self, anomalies: List[Anomaly]):
        """Process anomalies and generate alerts."""
        for anomaly in anomalies:
            if anomaly.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]:
                self._create_alert(anomaly)
    
    def _create_alert(self, anomaly: Anomaly):
        """Create an alert from an anomaly."""
        import uuid
        alert = Alert(
            id=str(uuid.uuid4()),
            timestamp=anomaly.timestamp,
            severity=anomaly.severity,
            title=f"{anomaly.anomaly_type.value.replace('_', ' ').title()} Detected",
            description=anomaly.description,
            user_id=anomaly.user_id,
            anomalies=[anomaly.id],
        )
        self._alerts[alert.id] = alert
        
        # Log critical alerts
        if anomaly.severity == AlertSeverity.CRITICAL:
            print(f"🚨 CRITICAL ALERT: {alert.title} - {alert.description}")
    
    # ========================================================================
    # Query Methods
    # ========================================================================
    
    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user behavior profile."""
        return self._profiles.get(user_id)
    
    def get_alerts(
        self,
        user_id: Optional[str] = None,
        severity: Optional[AlertSeverity] = None,
        unresolved_only: bool = False,
        limit: int = 100,
    ) -> List[Alert]:
        """Get alerts with optional filtering."""
        alerts = list(self._alerts.values())
        
        if user_id:
            alerts = [a for a in alerts if a.user_id == user_id]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        if unresolved_only:
            alerts = [a for a in alerts if not a.resolved]
        
        # Sort by timestamp descending
        alerts.sort(key=lambda a: a.timestamp, reverse=True)
        
        return alerts[:limit]
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert."""
        alert = self._alerts.get(alert_id)
        if not alert:
            return False
        
        alert.acknowledged = True
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = datetime.utcnow()
        return True
    
    def resolve_alert(self, alert_id: str, resolved_by: str) -> bool:
        """Resolve an alert."""
        alert = self._alerts.get(alert_id)
        if not alert:
            return False
        
        alert.resolved = True
        alert.resolved_by = resolved_by
        alert.resolved_at = datetime.utcnow()
        return True
    
    def get_risk_score(self, user_id: str) -> int:
        """Get current risk score for a user (0-100)."""
        alerts = self.get_alerts(user_id=user_id, unresolved_only=True)
        
        if not alerts:
            return 0
        
        # Weight by severity
        severity_weights = {
            AlertSeverity.INFO: 5,
            AlertSeverity.LOW: 15,
            AlertSeverity.MEDIUM: 30,
            AlertSeverity.HIGH: 50,
            AlertSeverity.CRITICAL: 80,
        }
        
        total_weight = sum(severity_weights.get(a.severity, 0) for a in alerts)
        return min(100, total_weight)


# ============================================================================
# Singleton Instance
# ============================================================================

_sentinel: Optional[Sentinel] = None


def get_sentinel() -> Sentinel:
    """Get the Sentinel singleton instance."""
    global _sentinel
    if _sentinel is None:
        _sentinel = Sentinel()
    return _sentinel
