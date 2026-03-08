"""
Zero-Trust Organ - The Veil Policy Enforcement Engine
======================================================
P0 Security Organ: "Never trust, always verify."

Implements Zero-Trust Architecture principles:
- Continuous verification of every request
- Least privilege access
- Device posture assessment
- Context-aware access decisions
- Micro-segmentation enforcement
- Assume breach mentality

This organ integrates with Guardian (auth), RBAC, and Audit.
"""

from __future__ import annotations

import hashlib
import json
import re
import socket
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from threading import Lock


# ============================================================================
# Configuration
# ============================================================================

class ZeroTrustConfig:
    """Zero-Trust configuration."""
    # Policy settings
    REQUIRE_MFA_FOR_SENSITIVE: bool = True
    SESSION_REVALIDATION_MINUTES: int = 15
    DEVICE_POSTURE_CHECK: bool = True
    CONTEXT_AWARE_ACCESS: bool = True
    
    # Risk thresholds
    HIGH_RISK_SCORE: int = 70
    MEDIUM_RISK_SCORE: int = 40
    MAX_FAILED_VERIFICATIONS: int = 3
    
    # Network segmentation
    TRUSTED_NETWORKS: List[str] = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
    SECURE_ZONES: Dict[str, List[str]] = {
        "epic": ["10.1.1.0/24"],      # Epic EHR servers
        "imprivata": ["10.1.2.0/24"], # Imprivata SSO servers
        "medical_devices": ["10.2.0.0/16"],
        "workstations": ["10.3.0.0/16"],
        "guest": ["10.100.0.0/16"],
    }
    
    # Storage
    DATA_DIR: Path = Path("/var/lib/veil/zero_trust")
    POLICY_FILE: Path = DATA_DIR / "policies.json"
    DEVICE_REGISTRY: Path = DATA_DIR / "devices.json"


# ============================================================================
# Data Models
# ============================================================================

class TrustLevel(str, Enum):
    """Trust levels for access decisions."""
    NONE = "none"           # No trust - deny all
    LOW = "low"             # Limited access, read-only
    MEDIUM = "medium"       # Standard access
    HIGH = "high"           # Elevated access
    FULL = "full"           # Full administrative access


class DevicePosture(str, Enum):
    """Device security posture states."""
    UNKNOWN = "unknown"
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    COMPROMISED = "compromised"
    QUARANTINED = "quarantined"


class AccessDecision(str, Enum):
    """Access decision outcomes."""
    ALLOW = "allow"
    DENY = "deny"
    CHALLENGE = "challenge"   # Require additional verification
    QUARANTINE = "quarantine" # Isolate and investigate


@dataclass
class DeviceInfo:
    """Device information for posture assessment."""
    device_id: str
    hostname: str
    ip_address: str
    mac_address: Optional[str] = None
    os_type: Optional[str] = None
    os_version: Optional[str] = None
    last_seen: datetime = field(default_factory=datetime.utcnow)
    posture: DevicePosture = DevicePosture.UNKNOWN
    trust_score: int = 0
    is_managed: bool = False
    is_encrypted: bool = False
    has_antivirus: bool = False
    last_patch_date: Optional[datetime] = None
    registered_user_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "hostname": self.hostname,
            "ip_address": self.ip_address,
            "mac_address": self.mac_address,
            "os_type": self.os_type,
            "os_version": self.os_version,
            "last_seen": self.last_seen.isoformat(),
            "posture": self.posture.value,
            "trust_score": self.trust_score,
            "is_managed": self.is_managed,
            "is_encrypted": self.is_encrypted,
            "has_antivirus": self.has_antivirus,
            "last_patch_date": self.last_patch_date.isoformat() if self.last_patch_date else None,
            "registered_user_id": self.registered_user_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DeviceInfo:
        return cls(
            device_id=data["device_id"],
            hostname=data["hostname"],
            ip_address=data["ip_address"],
            mac_address=data.get("mac_address"),
            os_type=data.get("os_type"),
            os_version=data.get("os_version"),
            last_seen=datetime.fromisoformat(data["last_seen"]) if data.get("last_seen") else datetime.utcnow(),
            posture=DevicePosture(data.get("posture", "unknown")),
            trust_score=data.get("trust_score", 0),
            is_managed=data.get("is_managed", False),
            is_encrypted=data.get("is_encrypted", False),
            has_antivirus=data.get("has_antivirus", False),
            last_patch_date=datetime.fromisoformat(data["last_patch_date"]) if data.get("last_patch_date") else None,
            registered_user_id=data.get("registered_user_id"),
        )


@dataclass
class AccessContext:
    """Context for access request evaluation."""
    user_id: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None
    session_id: Optional[str] = None
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    mfa_verified: bool = False
    session_age_minutes: int = 0
    failed_attempts: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "role": self.role,
            "session_id": self.session_id,
            "device_id": self.device_id,
            "ip_address": self.ip_address,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "timestamp": self.timestamp.isoformat(),
            "mfa_verified": self.mfa_verified,
            "session_age_minutes": self.session_age_minutes,
            "failed_attempts": self.failed_attempts,
        }


@dataclass
class AccessResult:
    """Result of access decision."""
    decision: AccessDecision
    trust_level: TrustLevel
    risk_score: int
    reasons: List[str]
    required_actions: List[str]
    context: Optional[AccessContext] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision.value,
            "trust_level": self.trust_level.value,
            "risk_score": self.risk_score,
            "reasons": self.reasons,
            "required_actions": self.required_actions,
        }


@dataclass
class Policy:
    """Access control policy."""
    id: str
    name: str
    description: str
    resource_pattern: str  # Regex pattern for resource matching
    required_role: Optional[str] = None
    required_trust_level: TrustLevel = TrustLevel.MEDIUM
    require_mfa: bool = False
    require_managed_device: bool = False
    require_encryption: bool = False
    allowed_networks: Optional[List[str]] = None
    allowed_hours: Optional[Tuple[int, int]] = None  # (start_hour, end_hour)
    max_session_age: Optional[int] = None  # minutes
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "resource_pattern": self.resource_pattern,
            "required_role": self.required_role,
            "required_trust_level": self.required_trust_level.value,
            "require_mfa": self.require_mfa,
            "require_managed_device": self.require_managed_device,
            "require_encryption": self.require_encryption,
            "allowed_networks": self.allowed_networks,
            "allowed_hours": self.allowed_hours,
            "max_session_age": self.max_session_age,
            "enabled": self.enabled,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Policy:
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            resource_pattern=data["resource_pattern"],
            required_role=data.get("required_role"),
            required_trust_level=TrustLevel(data.get("required_trust_level", "medium")),
            require_mfa=data.get("require_mfa", False),
            require_managed_device=data.get("require_managed_device", False),
            require_encryption=data.get("require_encryption", False),
            allowed_networks=data.get("allowed_networks"),
            allowed_hours=tuple(data["allowed_hours"]) if data.get("allowed_hours") else None,
            max_session_age=data.get("max_session_age"),
            enabled=data.get("enabled", True),
        )


# ============================================================================
# Zero-Trust Policy Engine
# ============================================================================

class ZeroTrust:
    """
    Zero-Trust Policy Enforcement Engine.
    
    Core principle: Never trust, always verify.
    
    Every access request is evaluated based on:
    1. Identity verification (who are you?)
    2. Device posture (is your device secure?)
    3. Context (is this normal behavior?)
    4. Resource sensitivity (what are you accessing?)
    5. Network location (where are you connecting from?)
    """
    
    def __init__(self, config: ZeroTrustConfig = None):
        self.config = config or ZeroTrustConfig()
        self._policies: Dict[str, Policy] = {}
        self._devices: Dict[str, DeviceInfo] = {}
        self._verification_failures: Dict[str, int] = {}  # user_id -> count
        self._lock = Lock()
        self._init_storage()
        self._load_data()
        self._init_default_policies()
    
    def _init_storage(self):
        """Initialize storage directories."""
        self.config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    def _load_data(self):
        """Load policies and devices from storage."""
        # Load policies
        if self.config.POLICY_FILE.exists():
            try:
                data = json.loads(self.config.POLICY_FILE.read_text())
                for policy_data in data.get("policies", []):
                    policy = Policy.from_dict(policy_data)
                    self._policies[policy.id] = policy
            except Exception:
                pass
        
        # Load devices
        if self.config.DEVICE_REGISTRY.exists():
            try:
                data = json.loads(self.config.DEVICE_REGISTRY.read_text())
                for device_data in data.get("devices", []):
                    device = DeviceInfo.from_dict(device_data)
                    self._devices[device.device_id] = device
            except Exception:
                pass
    
    def _save_data(self):
        """Save policies and devices to storage."""
        # Save policies
        policy_data = {
            "version": "1.0",
            "updated_at": datetime.utcnow().isoformat(),
            "policies": [p.to_dict() for p in self._policies.values()]
        }
        tmp = self.config.POLICY_FILE.with_suffix('.tmp')
        tmp.write_text(json.dumps(policy_data, indent=2))
        tmp.rename(self.config.POLICY_FILE)
        
        # Save devices
        device_data = {
            "version": "1.0",
            "updated_at": datetime.utcnow().isoformat(),
            "devices": [d.to_dict() for d in self._devices.values()]
        }
        tmp = self.config.DEVICE_REGISTRY.with_suffix('.tmp')
        tmp.write_text(json.dumps(device_data, indent=2))
        tmp.rename(self.config.DEVICE_REGISTRY)
    
    def _init_default_policies(self):
        """Initialize default hospital security policies."""
        default_policies = [
            Policy(
                id="epic-access",
                name="Epic EHR Access",
                description="Strict access control for Epic electronic health records",
                resource_pattern=r"^/api/epic/.*|^/epic/.*",
                required_role="operator",
                required_trust_level=TrustLevel.HIGH,
                require_mfa=True,
                require_managed_device=True,
                require_encryption=True,
            ),
            Policy(
                id="imprivata-admin",
                name="Imprivata SSO Administration",
                description="Administrative access to Imprivata SSO system",
                resource_pattern=r"^/api/imprivata/admin.*|^/imprivata/admin.*",
                required_role="admin",
                required_trust_level=TrustLevel.FULL,
                require_mfa=True,
                require_managed_device=True,
            ),
            Policy(
                id="patient-data",
                name="Patient Data Access",
                description="Access to patient records and PHI",
                resource_pattern=r"^/api/patients.*|^/patients.*",
                required_role="operator",
                required_trust_level=TrustLevel.MEDIUM,
                require_mfa=False,
                require_managed_device=False,
            ),
            Policy(
                id="organ-control",
                name="Security Organ Control",
                description="Start/stop/restart security organs",
                resource_pattern=r"^/api/organs/.*/start|^/api/organs/.*/stop|^/api/organs/.*/restart",
                required_role="admin",
                required_trust_level=TrustLevel.HIGH,
                require_mfa=True,
            ),
            Policy(
                id="system-restart",
                name="System Restart",
                description="Full system restart capability",
                resource_pattern=r"^/api/restart$",
                required_role="admin",
                required_trust_level=TrustLevel.FULL,
                require_mfa=True,
                require_managed_device=True,
            ),
            Policy(
                id="audit-access",
                name="Audit Log Access",
                description="View security audit logs",
                resource_pattern=r"^/api/audit.*|^/audit.*",
                required_role="admin",
                required_trust_level=TrustLevel.HIGH,
            ),
        ]
        
        for policy in default_policies:
            if policy.id not in self._policies:
                self._policies[policy.id] = policy
        
        self._save_data()
    
    # ========================================================================
    # Device Management
    # ========================================================================
    
    def register_device(self, device: DeviceInfo) -> DeviceInfo:
        """Register a device in the trusted device registry."""
        with self._lock:
            device.last_seen = datetime.utcnow()
            device.trust_score = self._calculate_device_trust(device)
            device.posture = self._assess_device_posture(device)
            self._devices[device.device_id] = device
            self._save_data()
        return device
    
    def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        """Get a registered device."""
        return self._devices.get(device_id)
    
    def update_device_posture(self, device_id: str, **kwargs) -> Optional[DeviceInfo]:
        """Update device posture information."""
        device = self._devices.get(device_id)
        if not device:
            return None
        
        for key, value in kwargs.items():
            if hasattr(device, key):
                setattr(device, key, value)
        
        device.last_seen = datetime.utcnow()
        device.trust_score = self._calculate_device_trust(device)
        device.posture = self._assess_device_posture(device)
        self._save_data()
        return device
    
    def quarantine_device(self, device_id: str, reason: str = None) -> bool:
        """Quarantine a device - mark as compromised."""
        device = self._devices.get(device_id)
        if not device:
            return False
        
        device.posture = DevicePosture.QUARANTINED
        device.trust_score = 0
        self._save_data()
        return True
    
    def _calculate_device_trust(self, device: DeviceInfo) -> int:
        """Calculate device trust score (0-100)."""
        score = 0
        
        # Managed device bonus
        if device.is_managed:
            score += 30
        
        # Encryption bonus
        if device.is_encrypted:
            score += 25
        
        # Antivirus bonus
        if device.has_antivirus:
            score += 20
        
        # Recent patches bonus
        if device.last_patch_date:
            days_since_patch = (datetime.utcnow() - device.last_patch_date).days
            if days_since_patch <= 7:
                score += 25
            elif days_since_patch <= 30:
                score += 15
            elif days_since_patch <= 90:
                score += 5
        
        return min(100, score)
    
    def _assess_device_posture(self, device: DeviceInfo) -> DevicePosture:
        """Assess device security posture."""
        if device.posture == DevicePosture.QUARANTINED:
            return DevicePosture.QUARANTINED
        
        score = device.trust_score
        
        if score >= 70:
            return DevicePosture.COMPLIANT
        elif score >= 40:
            return DevicePosture.NON_COMPLIANT
        else:
            return DevicePosture.UNKNOWN
    
    # ========================================================================
    # Policy Management
    # ========================================================================
    
    def add_policy(self, policy: Policy) -> Policy:
        """Add or update a policy."""
        self._policies[policy.id] = policy
        self._save_data()
        return policy
    
    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get a policy by ID."""
        return self._policies.get(policy_id)
    
    def list_policies(self) -> List[Policy]:
        """List all policies."""
        return list(self._policies.values())
    
    def delete_policy(self, policy_id: str) -> bool:
        """Delete a policy."""
        if policy_id in self._policies:
            del self._policies[policy_id]
            self._save_data()
            return True
        return False
    
    def find_matching_policies(self, resource: str) -> List[Policy]:
        """Find all policies that match a resource."""
        matching = []
        for policy in self._policies.values():
            if policy.enabled:
                try:
                    if re.match(policy.resource_pattern, resource):
                        matching.append(policy)
                except re.error:
                    pass
        return matching
    
    # ========================================================================
    # Access Decision Engine
    # ========================================================================
    
    def evaluate_access(self, context: AccessContext) -> AccessResult:
        """
        Evaluate an access request using Zero-Trust principles.
        
        This is the core decision engine that:
        1. Finds matching policies
        2. Evaluates each policy condition
        3. Calculates risk score
        4. Returns access decision
        """
        reasons = []
        required_actions = []
        risk_score = 0
        
        # Build resource path
        resource = f"/api/{context.resource_type}"
        if context.resource_id:
            resource += f"/{context.resource_id}"
        if context.action:
            resource += f"/{context.action}"
        
        # Find matching policies
        policies = self.find_matching_policies(resource)
        
        if not policies:
            # No specific policy - apply default restrictions
            policies = [Policy(
                id="default",
                name="Default Policy",
                description="Default access policy",
                resource_pattern=".*",
                required_trust_level=TrustLevel.LOW,
            )]
        
        # Evaluate each policy
        for policy in policies:
            policy_result = self._evaluate_policy(policy, context)
            risk_score = max(risk_score, policy_result["risk_score"])
            reasons.extend(policy_result["reasons"])
            required_actions.extend(policy_result["required_actions"])
        
        # Determine trust level based on context
        trust_level = self._calculate_trust_level(context, risk_score)
        
        # Check for too many verification failures
        if context.user_id:
            failures = self._verification_failures.get(context.user_id, 0)
            if failures >= self.config.MAX_FAILED_VERIFICATIONS:
                risk_score = 100
                reasons.append("Too many failed verification attempts")
        
        # Make final decision
        if risk_score >= self.config.HIGH_RISK_SCORE:
            decision = AccessDecision.DENY
            reasons.append("Risk score exceeds threshold")
        elif risk_score >= self.config.MEDIUM_RISK_SCORE:
            if required_actions:
                decision = AccessDecision.CHALLENGE
            else:
                decision = AccessDecision.ALLOW
        else:
            decision = AccessDecision.ALLOW
        
        return AccessResult(
            decision=decision,
            trust_level=trust_level,
            risk_score=risk_score,
            reasons=list(set(reasons)),
            required_actions=list(set(required_actions)),
            context=context,
        )
    
    def _evaluate_policy(self, policy: Policy, context: AccessContext) -> Dict[str, Any]:
        """Evaluate a single policy against context."""
        reasons = []
        required_actions = []
        risk_score = 0
        
        # Check role requirement
        if policy.required_role:
            if not context.role or context.role.lower() not in [policy.required_role.lower(), "admin", "system"]:
                risk_score += 50
                reasons.append(f"Required role: {policy.required_role}")
        
        # Check MFA requirement
        if policy.require_mfa and not context.mfa_verified:
            risk_score += 30
            reasons.append("MFA verification required")
            required_actions.append("complete_mfa")
        
        # Check managed device requirement
        if policy.require_managed_device:
            device = self._devices.get(context.device_id) if context.device_id else None
            if not device or not device.is_managed:
                risk_score += 25
                reasons.append("Managed device required")
        
        # Check encryption requirement
        if policy.require_encryption:
            device = self._devices.get(context.device_id) if context.device_id else None
            if not device or not device.is_encrypted:
                risk_score += 20
                reasons.append("Encrypted device required")
        
        # Check network restrictions
        if policy.allowed_networks and context.ip_address:
            if not self._is_ip_in_networks(context.ip_address, policy.allowed_networks):
                risk_score += 35
                reasons.append("Access from unauthorized network")
        
        # Check time restrictions
        if policy.allowed_hours:
            current_hour = datetime.utcnow().hour
            start, end = policy.allowed_hours
            if not (start <= current_hour < end):
                risk_score += 20
                reasons.append(f"Access outside allowed hours ({start}:00-{end}:00)")
        
        # Check session age
        if policy.max_session_age:
            if context.session_age_minutes > policy.max_session_age:
                risk_score += 15
                reasons.append("Session requires revalidation")
                required_actions.append("revalidate_session")
        
        return {
            "risk_score": risk_score,
            "reasons": reasons,
            "required_actions": required_actions,
        }
    
    def _calculate_trust_level(self, context: AccessContext, risk_score: int) -> TrustLevel:
        """Calculate trust level based on context and risk."""
        base_trust = TrustLevel.NONE
        
        # Authenticated user
        if context.user_id:
            base_trust = TrustLevel.LOW
        
        # Known role
        if context.role:
            if context.role.lower() == "admin":
                base_trust = TrustLevel.HIGH
            elif context.role.lower() == "operator":
                base_trust = TrustLevel.MEDIUM
            else:
                base_trust = TrustLevel.LOW
        
        # MFA verified
        if context.mfa_verified:
            if base_trust == TrustLevel.HIGH:
                base_trust = TrustLevel.FULL
            elif base_trust == TrustLevel.MEDIUM:
                base_trust = TrustLevel.HIGH
        
        # Adjust for risk
        if risk_score >= self.config.HIGH_RISK_SCORE:
            return TrustLevel.NONE
        elif risk_score >= self.config.MEDIUM_RISK_SCORE:
            # Downgrade one level
            levels = [TrustLevel.NONE, TrustLevel.LOW, TrustLevel.MEDIUM, TrustLevel.HIGH, TrustLevel.FULL]
            idx = levels.index(base_trust)
            return levels[max(0, idx - 1)]
        
        return base_trust
    
    def _is_ip_in_networks(self, ip: str, networks: List[str]) -> bool:
        """Check if IP is in any of the specified networks."""
        try:
            import ipaddress
            ip_obj = ipaddress.ip_address(ip)
            for network in networks:
                try:
                    if ip_obj in ipaddress.ip_network(network, strict=False):
                        return True
                except ValueError:
                    continue
        except Exception:
            pass
        return False
    
    # ========================================================================
    # Verification Tracking
    # ========================================================================
    
    def record_verification_failure(self, user_id: str):
        """Record a failed verification attempt."""
        with self._lock:
            self._verification_failures[user_id] = self._verification_failures.get(user_id, 0) + 1
    
    def clear_verification_failures(self, user_id: str):
        """Clear verification failures after successful auth."""
        with self._lock:
            if user_id in self._verification_failures:
                del self._verification_failures[user_id]
    
    def get_verification_failures(self, user_id: str) -> int:
        """Get number of verification failures for a user."""
        return self._verification_failures.get(user_id, 0)


# ============================================================================
# Singleton Instance
# ============================================================================

_zero_trust: Optional[ZeroTrust] = None


def get_zero_trust() -> ZeroTrust:
    """Get the ZeroTrust singleton instance."""
    global _zero_trust
    if _zero_trust is None:
        _zero_trust = ZeroTrust()
    return _zero_trust
