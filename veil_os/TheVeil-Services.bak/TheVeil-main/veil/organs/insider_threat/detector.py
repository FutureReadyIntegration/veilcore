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
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple, Set
import hashlib


# ============================================================================
# Configuration
# ============================================================================

class InsiderThreatConfig:
    """Configuration for insider threat detection."""
    # Detection windows
    ANALYSIS_WINDOW_HOURS: int = 24
    BASELINE_WINDOW_DAYS: int = 30
    
    # Thresholds
    DEVIATION_THRESHOLD: float = 2.5  # Standard deviations
    HIGH_RISK_THRESHOLD: int = 80
    MEDIUM_RISK_THRESHOLD: int = 50
    
    # Activity limits
    MAX_FAILED_LOGINS_PER_HOUR: int = 5
    MAX_SENSITIVE_ACCESS_PER_DAY: int = 50
    MAX_RECORDS_VIEWED_PER_HOUR: int = 100
    AFTER_HOURS_START: int = 20  # 8 PM
    AFTER_HOURS_END: int = 6     # 6 AM
    
    # Peer comparison
    MIN_PEERS_FOR_COMPARISON: int = 3
    PEER_DEVIATION_MULTIPLIER: float = 3.0
    
    # Storage
    DATA_DIR: Path = Path("/var/lib/veil/insider_threat")


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
    
    def __init__(self, data_dir: Path = None):
        self.config = InsiderThreatConfig()
        self.data_dir = data_dir or self.config.DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory state
        self._user_profiles: Dict[str, UserProfile] = {}
        self._user_activities: Dict[str, List[UserActivity]] = defaultdict(list)
        self._alerts: List[ThreatAlert] = []
        self._peer_groups: Dict[str, List[str]] = defaultdict(list)  # group -> user_ids
        
        self._load_state()
    
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
    
    def record_activity(self, activity: UserActivity):
        """Record a user activity for analysis."""
        self._user_activities[activity.user_id].append(activity)
        
        # Keep only recent activities
        cutoff = datetime.utcnow() - timedelta(days=self.config.BASELINE_WINDOW_DAYS)
        self._user_activities[activity.user_id] = [
            a for a in self._user_activities[activity.user_id]
            if a.timestamp > cutoff
        ]
        
        # Run detection
        alerts = self.analyze_user(activity.user_id)
        self._alerts.extend(alerts)
        
        return alerts
    
    def analyze_user(self, user_id: str) -> List[ThreatAlert]:
        """Run all threat detection checks for a user."""
        alerts = []
        
        activities = self._user_activities.get(user_id, [])
        if not activities:
            return alerts
        
        profile = self._get_or_create_profile(user_id)
        recent = self._get_recent_activities(user_id, hours=24)
        
        # Run detection rules
        alerts.extend(self._check_after_hours_access(user_id, recent, profile))
        alerts.extend(self._check_mass_data_access(user_id, recent, profile))
        alerts.extend(self._check_failed_logins(user_id, recent))
        alerts.extend(self._check_privilege_abuse(user_id, recent, profile))
        alerts.extend(self._check_peer_deviation(user_id, recent, profile))
        alerts.extend(self._check_unusual_resources(user_id, recent, profile))
        alerts.extend(self._check_credential_anomaly(user_id, recent, profile))
        
        return alerts
    
    def _get_or_create_profile(self, user_id: str) -> UserProfile:
        """Get or create a user profile."""
        if user_id not in self._user_profiles:
            self._user_profiles[user_id] = UserProfile(
                user_id=user_id,
                role="unknown",
                department="unknown",
            )
        return self._user_profiles[user_id]
    
    def _get_recent_activities(self, user_id: str, hours: int = 24) -> List[UserActivity]:
        """Get activities from the last N hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [
            a for a in self._user_activities.get(user_id, [])
            if a.timestamp > cutoff
        ]
    
    def _check_after_hours_access(
        self, 
        user_id: str, 
        activities: List[UserActivity],
        profile: UserProfile
    ) -> List[ThreatAlert]:
        """Detect suspicious after-hours access."""
        alerts = []
        
        after_hours = [
            a for a in activities
            if (a.timestamp.hour >= self.config.AFTER_HOURS_START or 
                a.timestamp.hour < self.config.AFTER_HOURS_END)
        ]
        
        if len(after_hours) > 5:  # More than 5 after-hours activities
            # Check if this is normal for the user
            if not any(h >= 20 or h < 6 for h in profile.typical_hours):
                alert = ThreatAlert(
                    id=self._generate_alert_id(),
                    timestamp=datetime.utcnow(),
                    user_id=user_id,
                    indicator=ThreatIndicator.AFTER_HOURS_ACCESS,
                    risk_level=RiskLevel.MEDIUM,
                    score=55,
                    description=f"Unusual after-hours access: {len(after_hours)} activities outside normal hours",
                    evidence=[
                        f"Activity at {a.timestamp.strftime('%H:%M')} accessing {a.resource}"
                        for a in after_hours[:5]
                    ],
                    recommended_actions=[
                        "Verify with user or their manager",
                        "Review accessed resources for sensitivity",
                        "Consider temporary access restrictions",
                    ],
                )
                alerts.append(alert)
        
        return alerts
    
    def _check_mass_data_access(
        self,
        user_id: str,
        activities: List[UserActivity],
        profile: UserProfile
    ) -> List[ThreatAlert]:
        """Detect potential data exfiltration via mass access."""
        alerts = []
        
        # Count patient/record accesses
        record_accesses = [a for a in activities if "patient" in a.resource.lower()]
        
        if len(record_accesses) > self.config.MAX_RECORDS_VIEWED_PER_HOUR:
            # Check deviation from baseline
            if len(record_accesses) > profile.avg_daily_access_count * 3:
                alert = ThreatAlert(
                    id=self._generate_alert_id(),
                    timestamp=datetime.utcnow(),
                    user_id=user_id,
                    indicator=ThreatIndicator.MASS_DATA_ACCESS,
                    risk_level=RiskLevel.HIGH,
                    score=75,
                    description=f"Potential data exfiltration: {len(record_accesses)} records accessed (3x normal)",
                    evidence=[
                        f"Accessed {a.resource} at {a.timestamp.strftime('%H:%M:%S')}"
                        for a in record_accesses[:10]
                    ],
                    recommended_actions=[
                        "Immediately review accessed records",
                        "Check for data exports or downloads",
                        "Consider temporary account suspension",
                        "Interview user about access purpose",
                    ],
                )
                alerts.append(alert)
        
        # Check data volume
        total_volume = sum(a.data_volume for a in activities)
        if total_volume > profile.avg_daily_data_volume * 5:
            alert = ThreatAlert(
                id=self._generate_alert_id(),
                timestamp=datetime.utcnow(),
                user_id=user_id,
                indicator=ThreatIndicator.DATA_EXFILTRATION,
                risk_level=RiskLevel.HIGH,
                score=80,
                description=f"Data volume anomaly: {total_volume:,} bytes (5x normal baseline)",
                evidence=[
                    f"Total data accessed: {total_volume:,} bytes",
                    f"Normal baseline: {profile.avg_daily_data_volume:,.0f} bytes",
                ],
                recommended_actions=[
                    "Review data access logs immediately",
                    "Check for file downloads or exports",
                    "Suspend data export privileges",
                ],
            )
            alerts.append(alert)
        
        return alerts
    
    def _check_failed_logins(self, user_id: str, activities: List[UserActivity]) -> List[ThreatAlert]:
        """Detect brute force or credential attacks."""
        alerts = []
        
        failed_logins = [
            a for a in activities
            if a.action == "login" and not a.success
        ]
        
        # Check for spike in failed logins
        if len(failed_logins) >= self.config.MAX_FAILED_LOGINS_PER_HOUR:
            # Check if from multiple IPs (credential stuffing)
            unique_ips = set(a.ip_address for a in failed_logins if a.ip_address)
            
            if len(unique_ips) > 3:
                risk = RiskLevel.CRITICAL
                score = 90
                description = f"Credential stuffing attack: {len(failed_logins)} failed logins from {len(unique_ips)} IPs"
            else:
                risk = RiskLevel.HIGH
                score = 70
                description = f"Brute force attempt: {len(failed_logins)} failed logins"
            
            alert = ThreatAlert(
                id=self._generate_alert_id(),
                timestamp=datetime.utcnow(),
                user_id=user_id,
                indicator=ThreatIndicator.CREDENTIAL_ANOMALY,
                risk_level=risk,
                score=score,
                description=description,
                evidence=[
                    f"Failed login from {a.ip_address} at {a.timestamp.strftime('%H:%M:%S')}"
                    for a in failed_logins[:5]
                ],
                recommended_actions=[
                    "Temporarily lock the account",
                    "Force password reset",
                    "Block suspicious IP addresses",
                    "Enable MFA if not already enabled",
                ],
            )
            alerts.append(alert)
        
        return alerts
    
    def _check_privilege_abuse(
        self,
        user_id: str,
        activities: List[UserActivity],
        profile: UserProfile
    ) -> List[ThreatAlert]:
        """Detect privilege abuse patterns."""
        alerts = []
        
        # Check for admin/sensitive resource access
        sensitive_actions = [
            a for a in activities
            if any(s in a.resource.lower() for s in ['admin', 'config', 'system', 'user', 'role'])
        ]
        
        if len(sensitive_actions) > self.config.MAX_SENSITIVE_ACCESS_PER_DAY:
            alert = ThreatAlert(
                id=self._generate_alert_id(),
                timestamp=datetime.utcnow(),
                user_id=user_id,
                indicator=ThreatIndicator.PRIVILEGE_ABUSE,
                risk_level=RiskLevel.HIGH,
                score=72,
                description=f"Excessive sensitive resource access: {len(sensitive_actions)} admin actions",
                evidence=[
                    f"Accessed {a.resource} ({a.action}) at {a.timestamp.strftime('%H:%M:%S')}"
                    for a in sensitive_actions[:5]
                ],
                recommended_actions=[
                    "Review administrative access logs",
                    "Verify actions were authorized",
                    "Consider temporary privilege reduction",
                ],
            )
            alerts.append(alert)
        
        return alerts
    
    def _check_peer_deviation(
        self,
        user_id: str,
        activities: List[UserActivity],
        profile: UserProfile
    ) -> List[ThreatAlert]:
        """Compare user behavior to peers in same role/department."""
        alerts = []
        
        # Get peers
        peers = self._peer_groups.get(profile.peer_group, [])
        peers = [p for p in peers if p != user_id]
        
        if len(peers) < self.config.MIN_PEERS_FOR_COMPARISON:
            return alerts  # Not enough peers for comparison
        
        # Calculate peer baseline
        peer_access_counts = []
        for peer_id in peers:
            peer_activities = self._get_recent_activities(peer_id, hours=24)
            peer_access_counts.append(len(peer_activities))
        
        if not peer_access_counts:
            return alerts
        
        peer_mean = statistics.mean(peer_access_counts)
        peer_std = statistics.stdev(peer_access_counts) if len(peer_access_counts) > 1 else 0
        
        user_count = len(activities)
        
        # Check if user deviates significantly from peers
        if peer_std > 0:
            z_score = (user_count - peer_mean) / peer_std
            if z_score > self.config.PEER_DEVIATION_MULTIPLIER:
                alert = ThreatAlert(
                    id=self._generate_alert_id(),
                    timestamp=datetime.utcnow(),
                    user_id=user_id,
                    indicator=ThreatIndicator.PEER_DEVIATION,
                    risk_level=RiskLevel.MEDIUM,
                    score=55,
                    description=f"Activity {z_score:.1f}x higher than peer average ({user_count} vs {peer_mean:.0f})",
                    evidence=[
                        f"User activities: {user_count}",
                        f"Peer average: {peer_mean:.0f}",
                        f"Peer std dev: {peer_std:.1f}",
                        f"Z-score: {z_score:.2f}",
                    ],
                    recommended_actions=[
                        "Review user's recent activities",
                        "Compare with historical baseline",
                        "Verify with manager if behavior is expected",
                    ],
                )
                alerts.append(alert)
        
        return alerts
    
    def _check_unusual_resources(
        self,
        user_id: str,
        activities: List[UserActivity],
        profile: UserProfile
    ) -> List[ThreatAlert]:
        """Detect access to unusual resources."""
        alerts = []
        
        if not profile.typical_resources:
            return alerts  # No baseline yet
        
        unusual = [
            a for a in activities
            if a.resource not in profile.typical_resources
        ]
        
        unusual_ratio = len(unusual) / len(activities) if activities else 0
        
        if unusual_ratio > 0.5 and len(unusual) > 10:
            alert = ThreatAlert(
                id=self._generate_alert_id(),
                timestamp=datetime.utcnow(),
                user_id=user_id,
                indicator=ThreatIndicator.PEER_DEVIATION,
                risk_level=RiskLevel.MEDIUM,
                score=50,
                description=f"Unusual resource access pattern: {len(unusual)} new resources ({unusual_ratio:.0%} of activity)",
                evidence=[
                    f"New resource: {a.resource}" for a in unusual[:5]
                ],
                recommended_actions=[
                    "Verify user has legitimate need for access",
                    "Review job responsibilities",
                    "Check for role changes",
                ],
            )
            alerts.append(alert)
        
        return alerts
    
    def _check_credential_anomaly(
        self,
        user_id: str,
        activities: List[UserActivity],
        profile: UserProfile
    ) -> List[ThreatAlert]:
        """Detect potential credential sharing or compromise."""
        alerts = []
        
        # Check for multiple simultaneous IPs
        recent = [a for a in activities if a.ip_address]
        if len(recent) < 2:
            return alerts
        
        # Get activities within 5 minute windows
        time_sorted = sorted(recent, key=lambda a: a.timestamp)
        for i in range(len(time_sorted) - 1):
            a1 = time_sorted[i]
            a2 = time_sorted[i + 1]
            
            time_diff = (a2.timestamp - a1.timestamp).total_seconds()
            if time_diff < 300 and a1.ip_address != a2.ip_address:  # Within 5 minutes
                # Check if IPs are very different (different subnets)
                if not self._same_subnet(a1.ip_address, a2.ip_address):
                    alert = ThreatAlert(
                        id=self._generate_alert_id(),
                        timestamp=datetime.utcnow(),
                        user_id=user_id,
                        indicator=ThreatIndicator.SHARED_CREDENTIALS,
                        risk_level=RiskLevel.HIGH,
                        score=78,
                        description="Impossible travel: Access from different networks within 5 minutes",
                        evidence=[
                            f"Access from {a1.ip_address} at {a1.timestamp.strftime('%H:%M:%S')}",
                            f"Access from {a2.ip_address} at {a2.timestamp.strftime('%H:%M:%S')}",
                            f"Time difference: {time_diff:.0f} seconds",
                        ],
                        recommended_actions=[
                            "Force re-authentication",
                            "Check for credential compromise",
                            "Review session logs",
                            "Consider password reset",
                        ],
                    )
                    alerts.append(alert)
                    break  # One alert per analysis
        
        return alerts
    
    def _same_subnet(self, ip1: str, ip2: str) -> bool:
        """Check if two IPs are in the same /24 subnet."""
        try:
            parts1 = ip1.split('.')[:3]
            parts2 = ip2.split('.')[:3]
            return parts1 == parts2
        except Exception:
            return False
    
    def _generate_alert_id(self) -> str:
        """Generate unique alert ID."""
        import uuid
        return f"ITD-{uuid.uuid4().hex[:8].upper()}"
    
    def update_profile(self, user_id: str, role: str = None, department: str = None, peer_group: str = None):
        """Update user profile information."""
        profile = self._get_or_create_profile(user_id)
        
        if role:
            profile.role = role
        if department:
            profile.department = department
        if peer_group:
            # Remove from old group
            for group, members in self._peer_groups.items():
                if user_id in members:
                    members.remove(user_id)
            # Add to new group
            profile.peer_group = peer_group
            self._peer_groups[peer_group].append(user_id)
        
        profile.last_updated = datetime.utcnow()
        self._save_state()
    
    def recalculate_baseline(self, user_id: str):
        """Recalculate behavioral baseline for a user."""
        activities = self._user_activities.get(user_id, [])
        if not activities:
            return
        
        profile = self._get_or_create_profile(user_id)
        
        # Group by day
        by_day = defaultdict(list)
        for a in activities:
            day = a.timestamp.date()
            by_day[day].append(a)
        
        if by_day:
            # Calculate averages
            daily_counts = [len(acts) for acts in by_day.values()]
            daily_volumes = [sum(a.data_volume for a in acts) for acts in by_day.values()]
            
            profile.avg_daily_access_count = statistics.mean(daily_counts)
            profile.avg_daily_data_volume = statistics.mean(daily_volumes) if daily_volumes else 0
            
            # Calculate typical hours
            hours = defaultdict(int)
            for a in activities:
                hours[a.timestamp.hour] += 1
            
            # Top hours (80% of activity)
            sorted_hours = sorted(hours.items(), key=lambda x: -x[1])
            total = sum(hours.values())
            cumulative = 0
            typical = []
            for hour, count in sorted_hours:
                cumulative += count
                typical.append(hour)
                if cumulative >= total * 0.8:
                    break
            profile.typical_hours = sorted(typical)
            
            # Typical resources (80% of access)
            resources = defaultdict(int)
            for a in activities:
                resources[a.resource] += 1
            
            sorted_resources = sorted(resources.items(), key=lambda x: -x[1])
            total = sum(resources.values())
            cumulative = 0
            typical_res = set()
            for resource, count in sorted_resources:
                cumulative += count
                typical_res.add(resource)
                if cumulative >= total * 0.8:
                    break
            profile.typical_resources = typical_res
            
            # Typical IPs
            profile.typical_ips = set(a.ip_address for a in activities if a.ip_address)
        
        profile.last_updated = datetime.utcnow()
        self._save_state()
    
    def get_alerts(self, user_id: str = None, unresolved_only: bool = True) -> List[ThreatAlert]:
        """Get threat alerts, optionally filtered."""
        alerts = self._alerts
        
        if user_id:
            alerts = [a for a in alerts if a.user_id == user_id]
        
        if unresolved_only:
            alerts = [a for a in alerts if not a.resolved]
        
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge a threat alert."""
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve a threat alert."""
        for alert in self._alerts:
            if alert.id == alert_id:
                alert.resolved = True
                return True
        return False
    
    def get_risk_score(self, user_id: str) -> int:
        """Get aggregate risk score for a user."""
        alerts = self.get_alerts(user_id=user_id, unresolved_only=True)
        
        if not alerts:
            return 0
        
        # Weighted by recency
        now = datetime.utcnow()
        weighted_scores = []
        for alert in alerts:
            age_hours = (now - alert.timestamp).total_seconds() / 3600
            recency_weight = max(0.2, 1 - (age_hours / 24))  # Decay over 24 hours
            weighted_scores.append(alert.score * recency_weight)
        
        return min(100, int(sum(weighted_scores) / len(weighted_scores) * 1.2))


# Singleton instance
_detector: Optional[InsiderThreatDetector] = None

def get_insider_threat_detector() -> InsiderThreatDetector:
    """Get the singleton InsiderThreatDetector instance."""
    global _detector
    if _detector is None:
        _detector = InsiderThreatDetector()
    return _detector


# Organ metadata
ORGAN_METADATA = {
    "name": "insider_threat",
    "tier": "P1",
    "glyph": "🕵️",
    "description": "Insider Threat Detection - The enemy within",
    "affirmation": "I protect against the threats that wear friendly faces.",
    "dependencies": ["guardian", "audit", "sentinel"],
    "provides": ["insider_threat_detection", "peer_analysis", "exfiltration_detection"],
}
