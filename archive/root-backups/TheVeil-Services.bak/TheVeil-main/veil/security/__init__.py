"""
Veil Security Layer
====================
Hospital-grade security for The Veil OS.

This module provides:
- Guardian: JWT-based authentication gateway
- Session: Secure session management
- RBAC: Role-based access control
- Audit: Tamper-proof audit logging
- Middleware: Rate limiting, CSRF, security headers
"""

from .guardian import Guardian, verify_password, hash_password, get_guardian
from .session import SessionManager, Session, get_session_manager
from .rbac import RBAC, Role, Permission, require_permission, require_role, is_public_route
from .audit import AuditLog, AuditEvent, AuditLevel, get_audit_log
from .middleware import SecurityMiddleware, RateLimiter, CSRFProtection, SECURITY_HEADERS, SecurityContext
from .models import User, Token, LoginRequest, LoginResponse

__all__ = [
    # Guardian
    "Guardian",
    "get_guardian",
    "verify_password", 
    "hash_password",
    # Session
    "SessionManager",
    "Session",
    "get_session_manager",
    # RBAC
    "RBAC",
    "Role",
    "Permission",
    "require_permission",
    "require_role",
    "is_public_route",
    # Audit
    "AuditLog",
    "AuditEvent",
    "AuditLevel",
    "get_audit_log",
    # Middleware
    "SecurityMiddleware",
    "RateLimiter",
    "CSRFProtection",
    "SECURITY_HEADERS",
    "SecurityContext",
    # Models
    "User",
    "Token",
    "LoginRequest",
    "LoginResponse",
]

__version__ = "1.0.0"
