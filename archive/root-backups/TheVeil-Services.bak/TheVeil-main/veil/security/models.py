"""
Veil Security Models
====================
Data models for authentication, authorization, and auditing.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any


class Role(str, Enum):
    """User roles with increasing privilege levels."""
    VIEWER = "viewer"       # Read-only access to dashboards
    OPERATOR = "operator"   # Can manage patients, view organs
    ADMIN = "admin"         # Full access including organ control & user management
    SYSTEM = "system"       # Internal system accounts (organs)


class Permission(str, Enum):
    """Fine-grained permissions for RBAC."""
    # Dashboard
    VIEW_DASHBOARD = "view_dashboard"
    VIEW_STATUS = "view_status"
    
    # Patient Management
    VIEW_PATIENTS = "view_patients"
    CREATE_PATIENT = "create_patient"
    UPDATE_PATIENT = "update_patient"
    DISCHARGE_PATIENT = "discharge_patient"
    DELETE_PATIENT = "delete_patient"
    
    # Organ Management
    VIEW_ORGANS = "view_organs"
    START_ORGAN = "start_organ"
    STOP_ORGAN = "stop_organ"
    RESTART_ORGAN = "restart_organ"
    CONFIGURE_ORGAN = "configure_organ"
    
    # System Administration
    VIEW_AUDIT = "view_audit"
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"
    SYSTEM_RESTART = "system_restart"
    SYSTEM_CONFIGURE = "system_configure"
    
    # Security
    VIEW_SECURITY = "view_security"
    MANAGE_SESSIONS = "manage_sessions"


# Role -> Permissions mapping
ROLE_PERMISSIONS: Dict[Role, List[Permission]] = {
    Role.VIEWER: [
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_STATUS,
        Permission.VIEW_PATIENTS,
        Permission.VIEW_ORGANS,
    ],
    Role.OPERATOR: [
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_STATUS,
        Permission.VIEW_PATIENTS,
        Permission.CREATE_PATIENT,
        Permission.UPDATE_PATIENT,
        Permission.DISCHARGE_PATIENT,
        Permission.VIEW_ORGANS,
        Permission.RESTART_ORGAN,
    ],
    Role.ADMIN: [
        # All permissions
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_STATUS,
        Permission.VIEW_PATIENTS,
        Permission.CREATE_PATIENT,
        Permission.UPDATE_PATIENT,
        Permission.DISCHARGE_PATIENT,
        Permission.DELETE_PATIENT,
        Permission.VIEW_ORGANS,
        Permission.START_ORGAN,
        Permission.STOP_ORGAN,
        Permission.RESTART_ORGAN,
        Permission.CONFIGURE_ORGAN,
        Permission.VIEW_AUDIT,
        Permission.MANAGE_USERS,
        Permission.MANAGE_ROLES,
        Permission.SYSTEM_RESTART,
        Permission.SYSTEM_CONFIGURE,
        Permission.VIEW_SECURITY,
        Permission.MANAGE_SESSIONS,
    ],
    Role.SYSTEM: [
        # System accounts have all permissions
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_STATUS,
        Permission.VIEW_PATIENTS,
        Permission.VIEW_ORGANS,
        Permission.VIEW_AUDIT,
        Permission.VIEW_SECURITY,
    ],
}


@dataclass
class User:
    """Veil user account."""
    id: str
    username: str
    password_hash: str
    role: Role
    email: Optional[str] = None
    full_name: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    is_active: bool = True
    is_locked: bool = False
    failed_attempts: int = 0
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        return permission in ROLE_PERMISSIONS.get(self.role, [])
    
    def has_role(self, role: Role) -> bool:
        """Check if user has at least the given role level."""
        role_hierarchy = [Role.VIEWER, Role.OPERATOR, Role.ADMIN, Role.SYSTEM]
        try:
            user_level = role_hierarchy.index(self.role)
            required_level = role_hierarchy.index(role)
            return user_level >= required_level
        except ValueError:
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excludes sensitive fields)."""
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role.value,
            "email": self.email,
            "full_name": self.full_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "is_active": self.is_active,
            "mfa_enabled": self.mfa_enabled,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> User:
        """Create User from dictionary."""
        return cls(
            id=data["id"],
            username=data["username"],
            password_hash=data["password_hash"],
            role=Role(data["role"]) if isinstance(data["role"], str) else data["role"],
            email=data.get("email"),
            full_name=data.get("full_name"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow(),
            last_login=datetime.fromisoformat(data["last_login"]) if data.get("last_login") else None,
            is_active=data.get("is_active", True),
            is_locked=data.get("is_locked", False),
            failed_attempts=data.get("failed_attempts", 0),
            mfa_enabled=data.get("mfa_enabled", False),
            mfa_secret=data.get("mfa_secret"),
        )


@dataclass
class Token:
    """JWT token data."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600  # seconds
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "access_token": self.access_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
            "refresh_token": self.refresh_token,
            "scope": self.scope,
        }


@dataclass
class Session:
    """User session data."""
    id: str
    user_id: str
    username: str
    role: Role
    created_at: datetime
    expires_at: datetime
    last_activity: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_valid: bool = True
    
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "role": self.role.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "is_valid": self.is_valid,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Session:
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            username=data["username"],
            role=Role(data["role"]) if isinstance(data["role"], str) else data["role"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            last_activity=datetime.fromisoformat(data["last_activity"]),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            is_valid=data.get("is_valid", True),
        )


@dataclass
class LoginRequest:
    """Login request data."""
    username: str
    password: str
    mfa_code: Optional[str] = None
    remember_me: bool = False


@dataclass
class LoginResponse:
    """Login response data."""
    success: bool
    message: str
    token: Optional[Token] = None
    user: Optional[Dict[str, Any]] = None
    requires_mfa: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "token": self.token.to_dict() if self.token else None,
            "user": self.user,
            "requires_mfa": self.requires_mfa,
        }


class AuditLevel(str, Enum):
    """Audit event severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    SECURITY = "security"


@dataclass
class AuditEvent:
    """Audit log event."""
    id: str
    timestamp: datetime
    level: AuditLevel
    category: str  # auth, patient, organ, system, security
    action: str
    user_id: Optional[str] = None
    username: Optional[str] = None
    ip_address: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    success: bool = True
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "category": self.category,
            "action": self.action,
            "user_id": self.user_id,
            "username": self.username,
            "ip_address": self.ip_address,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "success": self.success,
            "error_message": self.error_message,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AuditEvent:
        return cls(
            id=data["id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            level=AuditLevel(data["level"]),
            category=data["category"],
            action=data["action"],
            user_id=data.get("user_id"),
            username=data.get("username"),
            ip_address=data.get("ip_address"),
            resource_type=data.get("resource_type"),
            resource_id=data.get("resource_id"),
            details=data.get("details"),
            success=data.get("success", True),
            error_message=data.get("error_message"),
        )
