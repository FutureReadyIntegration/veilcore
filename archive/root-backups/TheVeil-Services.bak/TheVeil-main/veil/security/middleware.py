"""
Security Middleware - The Veil FastAPI Security Integration
==========================================================
Integrates all security components into FastAPI.

Provides:
- Authentication middleware
- Rate limiting
- CSRF protection
- Security headers
- Request/response logging
"""

from __future__ import annotations

import time
import secrets
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional, Dict, Callable, List, Any
from functools import wraps

from .models import User, Session, Role, Permission
from .guardian import Guardian, get_guardian
from .session import SessionManager, get_session_manager
from .rbac import RBAC, is_public_route, get_route_permissions, AuthorizationError
from .audit import AuditLog, get_audit_log, AuditLevel


# ============================================================================
# Rate Limiter
# ============================================================================

class RateLimiter:
    """
    Token bucket rate limiter for API protection.
    """
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_size: int = 10
    ):
        self.rate = requests_per_minute / 60.0  # tokens per second
        self.burst_size = burst_size
        self._buckets: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"tokens": burst_size, "last_update": time.time()}
        )
    
    def _get_tokens(self, key: str) -> float:
        """Get current token count for a key."""
        bucket = self._buckets[key]
        now = time.time()
        elapsed = now - bucket["last_update"]
        
        # Add tokens based on elapsed time
        bucket["tokens"] = min(
            self.burst_size,
            bucket["tokens"] + elapsed * self.rate
        )
        bucket["last_update"] = now
        
        return bucket["tokens"]
    
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed and consume a token."""
        tokens = self._get_tokens(key)
        
        if tokens >= 1:
            self._buckets[key]["tokens"] -= 1
            return True
        
        return False
    
    def get_retry_after(self, key: str) -> int:
        """Get seconds until next request is allowed."""
        tokens = self._get_tokens(key)
        if tokens >= 1:
            return 0
        
        tokens_needed = 1 - tokens
        return int(tokens_needed / self.rate) + 1
    
    def reset(self, key: str):
        """Reset rate limit for a key."""
        if key in self._buckets:
            del self._buckets[key]


class RateLimitConfig:
    """Rate limit configuration per endpoint type."""
    
    # Default limits
    DEFAULT_RPM = 60  # requests per minute
    DEFAULT_BURST = 10
    
    # Endpoint-specific limits
    LIMITS = {
        # Auth endpoints (stricter to prevent brute force)
        "/api/auth/login": {"rpm": 5, "burst": 3},
        "/api/auth/refresh": {"rpm": 10, "burst": 5},
        
        # Write operations
        "/api/restart": {"rpm": 1, "burst": 1},
        "/api/organs/*/start": {"rpm": 5, "burst": 2},
        "/api/organs/*/stop": {"rpm": 5, "burst": 2},
        "/api/organs/*/restart": {"rpm": 5, "burst": 2},
        
        # Read operations (more relaxed)
        "/api/organs": {"rpm": 30, "burst": 10},
        "/api/systems": {"rpm": 30, "burst": 10},
        "/api/patients": {"rpm": 30, "burst": 10},
    }
    
    @classmethod
    def get_limit(cls, path: str) -> Dict[str, int]:
        """Get rate limit for a path."""
        # Exact match
        if path in cls.LIMITS:
            return cls.LIMITS[path]
        
        # Wildcard match
        for pattern, limit in cls.LIMITS.items():
            if '*' in pattern:
                pattern_parts = pattern.split('/')
                path_parts = path.split('/')
                
                if len(pattern_parts) == len(path_parts):
                    match = True
                    for pp, pathp in zip(pattern_parts, path_parts):
                        if pp != '*' and pp != pathp:
                            match = False
                            break
                    if match:
                        return limit
        
        return {"rpm": cls.DEFAULT_RPM, "burst": cls.DEFAULT_BURST}


# ============================================================================
# CSRF Protection
# ============================================================================

class CSRFProtection:
    """
    CSRF token generation and validation.
    Uses double-submit cookie pattern.
    """
    
    COOKIE_NAME = "veil_csrf"
    HEADER_NAME = "X-CSRF-Token"
    TOKEN_LENGTH = 32
    
    @staticmethod
    def generate_token() -> str:
        """Generate a new CSRF token."""
        return secrets.token_urlsafe(CSRFProtection.TOKEN_LENGTH)
    
    @staticmethod
    def validate(cookie_token: str, header_token: str) -> bool:
        """Validate CSRF tokens match."""
        if not cookie_token or not header_token:
            return False
        return secrets.compare_digest(cookie_token, header_token)


# ============================================================================
# Security Headers
# ============================================================================

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    ),
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


# ============================================================================
# Security Context
# ============================================================================

class SecurityContext:
    """
    Request-scoped security context.
    Holds user, session, and request metadata.
    """
    
    def __init__(
        self,
        user: Optional[User] = None,
        session: Optional[Session] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        self.user = user
        self.session = session
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.request_id = request_id or secrets.token_hex(8)
        self.authenticated = user is not None or session is not None
    
    @property
    def username(self) -> Optional[str]:
        if self.user:
            return self.user.username
        if self.session:
            return self.session.username
        return None
    
    @property
    def role(self) -> Optional[Role]:
        if self.user:
            return self.user.role
        if self.session:
            return self.session.role
        return None
    
    def has_permission(self, permission: Permission) -> bool:
        if self.user:
            return RBAC.has_permission(self.user, permission)
        if self.session:
            return RBAC.has_permission(self.session, permission)
        return False
    
    def has_role(self, role: Role) -> bool:
        if self.user:
            return RBAC.has_role(self.user, role)
        if self.session:
            return RBAC.has_role(self.session, role)
        return False


# ============================================================================
# Security Middleware
# ============================================================================

class SecurityMiddleware:
    """
    FastAPI security middleware.
    
    Handles:
    - Authentication (JWT/Session)
    - Authorization (RBAC)
    - Rate limiting
    - CSRF protection
    - Security headers
    - Audit logging
    """
    
    def __init__(
        self,
        guardian: Guardian = None,
        session_manager: SessionManager = None,
        audit_log: AuditLog = None,
        enable_rate_limiting: bool = True,
        enable_csrf: bool = True,
        enable_audit: bool = True
    ):
        self.guardian = guardian or get_guardian()
        self.session_manager = session_manager or get_session_manager()
        self.audit = audit_log or get_audit_log()
        
        self.enable_rate_limiting = enable_rate_limiting
        self.enable_csrf = enable_csrf
        self.enable_audit = enable_audit
        
        self._rate_limiters: Dict[str, RateLimiter] = {}
    
    def _get_rate_limiter(self, path: str) -> RateLimiter:
        """Get or create rate limiter for a path."""
        if path not in self._rate_limiters:
            config = RateLimitConfig.get_limit(path)
            self._rate_limiters[path] = RateLimiter(
                requests_per_minute=config["rpm"],
                burst_size=config["burst"]
            )
        return self._rate_limiters[path]
    
    def _get_client_ip(self, request) -> str:
        """Extract client IP from request."""
        # Check forwarded headers
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct connection
        if hasattr(request, 'client') and request.client:
            return request.client.host
        
        return "unknown"
    
    def authenticate_request(self, request) -> SecurityContext:
        """
        Authenticate a request and return security context.
        
        Checks:
        1. Bearer token in Authorization header
        2. Session cookie
        """
        ip_address = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")
        
        # Check Bearer token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            user, error = self.guardian.verify_token(token)
            
            if user:
                return SecurityContext(
                    user=user,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
        
        # Check session cookie
        session_id = request.cookies.get(self.session_manager.config.COOKIE_NAME)
        if session_id:
            session = self.session_manager.validate(session_id)
            
            if session:
                return SecurityContext(
                    session=session,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
        
        # Not authenticated
        return SecurityContext(
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def check_rate_limit(self, request) -> tuple[bool, int]:
        """
        Check if request is within rate limits.
        Returns: (is_allowed, retry_after_seconds)
        """
        if not self.enable_rate_limiting:
            return True, 0
        
        path = request.url.path
        ip = self._get_client_ip(request)
        
        # Rate limit key: IP + path
        key = f"{ip}:{path}"
        
        limiter = self._get_rate_limiter(path)
        
        if limiter.is_allowed(key):
            return True, 0
        
        return False, limiter.get_retry_after(key)
    
    def check_csrf(self, request) -> bool:
        """
        Validate CSRF token for state-changing requests.
        """
        if not self.enable_csrf:
            return True
        
        # Only check for state-changing methods
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        
        cookie_token = request.cookies.get(CSRFProtection.COOKIE_NAME)
        header_token = request.headers.get(CSRFProtection.HEADER_NAME)
        
        return CSRFProtection.validate(cookie_token, header_token)
    
    def authorize_request(
        self,
        request,
        context: SecurityContext
    ) -> tuple[bool, str]:
        """
        Check if request is authorized.
        Returns: (is_authorized, error_message)
        """
        path = request.url.path
        method = request.method
        
        # Public routes don't need auth
        if is_public_route(path):
            return True, ""
        
        # Must be authenticated
        if not context.authenticated:
            return False, "Authentication required"
        
        # Check permissions for route
        required_permissions = get_route_permissions(path, method)
        
        for perm in required_permissions:
            if context.has_permission(perm):
                return True, ""
        
        perm_names = ", ".join(p.value for p in required_permissions)
        return False, f"Permission denied. Required: {perm_names}"
    
    def add_security_headers(self, response) -> None:
        """Add security headers to response."""
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
    
    def log_request(
        self,
        request,
        context: SecurityContext,
        response_status: int,
        duration_ms: float
    ):
        """Log request to audit log."""
        if not self.enable_audit:
            return
        
        # Determine audit level based on response
        if response_status >= 500:
            level = AuditLevel.ERROR
        elif response_status >= 400:
            level = AuditLevel.WARNING
        else:
            level = AuditLevel.INFO
        
        # Determine category
        path = request.url.path
        if "/auth/" in path:
            category = "auth"
        elif "/patient" in path:
            category = "patient"
        elif "/organ" in path:
            category = "organ"
        else:
            category = "system"
        
        self.audit.log(
            level=level,
            category=category,
            action=f"{request.method} {path}",
            session=context.session,
            ip_address=context.ip_address,
            details={
                "method": request.method,
                "path": path,
                "status": response_status,
                "duration_ms": duration_ms,
                "user_agent": context.user_agent,
                "request_id": context.request_id,
            },
            success=response_status < 400
        )


# ============================================================================
# FastAPI Dependency Injection Helpers
# ============================================================================

def get_security_middleware() -> SecurityMiddleware:
    """Get security middleware instance."""
    return SecurityMiddleware()


def create_security_context(request) -> SecurityContext:
    """Create security context from request (for FastAPI dependency)."""
    middleware = get_security_middleware()
    return middleware.authenticate_request(request)


# ============================================================================
# Decorators for Route Handlers
# ============================================================================

def authenticated(func: Callable) -> Callable:
    """
    Decorator to require authentication for a route.
    The decorated function receives 'security_context' kwarg.
    """
    @wraps(func)
    async def wrapper(*args, request=None, **kwargs):
        middleware = get_security_middleware()
        context = middleware.authenticate_request(request)
        
        if not context.authenticated:
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Authentication required")
        
        kwargs['security_context'] = context
        return await func(*args, request=request, **kwargs)
    
    return wrapper


def require_permissions(*permissions: Permission):
    """
    Decorator to require specific permissions for a route.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, request=None, **kwargs):
            middleware = get_security_middleware()
            context = middleware.authenticate_request(request)
            
            if not context.authenticated:
                from fastapi import HTTPException
                raise HTTPException(status_code=401, detail="Authentication required")
            
            for perm in permissions:
                if not context.has_permission(perm):
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=403,
                        detail=f"Permission denied: {perm.value}"
                    )
            
            kwargs['security_context'] = context
            return await func(*args, request=request, **kwargs)
        
        return wrapper
    return decorator
