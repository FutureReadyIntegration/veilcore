"""
Zero-Trust Middleware - FastAPI Integration
============================================
Integrates Zero-Trust policy enforcement with FastAPI routes.
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime
from functools import wraps
from typing import Optional, Callable, Any

from fastapi import Request, Response, HTTPException, Depends
from fastapi.responses import JSONResponse

from .engine import (
    ZeroTrust, 
    get_zero_trust, 
    AccessContext, 
    AccessResult,
    AccessDecision,
    TrustLevel,
    DeviceInfo,
    DevicePosture,
)


# ============================================================================
# Device Fingerprinting
# ============================================================================

def generate_device_id(request: Request) -> str:
    """Generate a device fingerprint from request headers."""
    components = [
        request.headers.get("user-agent", ""),
        request.headers.get("accept-language", ""),
        request.headers.get("accept-encoding", ""),
        str(request.client.host) if request.client else "",
    ]
    fingerprint = "|".join(components)
    return hashlib.sha256(fingerprint.encode()).hexdigest()[:16]


def extract_device_info(request: Request) -> DeviceInfo:
    """Extract device information from request."""
    device_id = request.headers.get("X-Device-ID") or generate_device_id(request)
    
    return DeviceInfo(
        device_id=device_id,
        hostname=request.headers.get("X-Device-Hostname", "unknown"),
        ip_address=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent"),
        os_type=_parse_os_from_ua(request.headers.get("user-agent", "")),
    )


def _parse_os_from_ua(user_agent: str) -> Optional[str]:
    """Parse OS type from user agent string."""
    ua_lower = user_agent.lower()
    if "windows" in ua_lower:
        return "Windows"
    elif "mac os" in ua_lower or "macos" in ua_lower:
        return "macOS"
    elif "linux" in ua_lower:
        return "Linux"
    elif "android" in ua_lower:
        return "Android"
    elif "iphone" in ua_lower or "ipad" in ua_lower:
        return "iOS"
    return None


# ============================================================================
# Context Building
# ============================================================================

def build_access_context(
    request: Request,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    role: Optional[str] = None,
    session_id: Optional[str] = None,
    mfa_verified: bool = False,
    session_created: Optional[datetime] = None,
) -> AccessContext:
    """Build access context from request and user info."""
    # Calculate session age
    session_age = 0
    if session_created:
        session_age = int((datetime.utcnow() - session_created).total_seconds() / 60)
    
    # Parse resource from path
    path_parts = request.url.path.strip("/").split("/")
    resource_type = path_parts[1] if len(path_parts) > 1 and path_parts[0] == "api" else path_parts[0]
    resource_id = path_parts[2] if len(path_parts) > 2 else None
    action = path_parts[3] if len(path_parts) > 3 else request.method.lower()
    
    return AccessContext(
        user_id=user_id,
        username=username,
        role=role,
        session_id=session_id,
        device_id=request.headers.get("X-Device-ID") or generate_device_id(request),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        timestamp=datetime.utcnow(),
        mfa_verified=mfa_verified,
        session_age_minutes=session_age,
    )


# ============================================================================
# Middleware
# ============================================================================

class ZeroTrustMiddleware:
    """
    FastAPI middleware for Zero-Trust policy enforcement.
    
    Evaluates every request against Zero-Trust policies and:
    - Allows compliant requests
    - Challenges requests that need additional verification
    - Denies non-compliant requests
    """
    
    def __init__(
        self,
        app,
        zero_trust: Optional[ZeroTrust] = None,
        excluded_paths: Optional[list] = None,
    ):
        self.app = app
        self.zt = zero_trust or get_zero_trust()
        self.excluded_paths = excluded_paths or [
            "/health",
            "/api/health",
            "/login",
            "/static",
            "/favicon.ico",
        ]
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Check if path is excluded
        path = scope.get("path", "")
        if any(path.startswith(exc) for exc in self.excluded_paths):
            await self.app(scope, receive, send)
            return
        
        # Create request object for context building
        request = Request(scope, receive, send)
        
        # Get user context from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None) if hasattr(request, "state") else None
        username = getattr(request.state, "username", None) if hasattr(request, "state") else None
        role = getattr(request.state, "role", None) if hasattr(request, "state") else None
        session_id = getattr(request.state, "session_id", None) if hasattr(request, "state") else None
        mfa_verified = getattr(request.state, "mfa_verified", False) if hasattr(request, "state") else False
        session_created = getattr(request.state, "session_created", None) if hasattr(request, "state") else None
        
        # Build context
        context = build_access_context(
            request=request,
            user_id=user_id,
            username=username,
            role=role,
            session_id=session_id,
            mfa_verified=mfa_verified,
            session_created=session_created,
        )
        
        # Evaluate access
        result = self.zt.evaluate_access(context)
        
        # Store result in request state for downstream use
        if hasattr(request, "state"):
            request.state.zero_trust_result = result
            request.state.trust_level = result.trust_level
        
        # Handle decision
        if result.decision == AccessDecision.DENY:
            response = JSONResponse(
                status_code=403,
                content={
                    "error": "Access denied by Zero-Trust policy",
                    "decision": result.decision.value,
                    "reasons": result.reasons,
                    "risk_score": result.risk_score,
                },
                headers={"X-Zero-Trust-Decision": "DENY"}
            )
            await response(scope, receive, send)
            return
        
        elif result.decision == AccessDecision.CHALLENGE:
            # For challenges, we add headers but allow the request
            # The application can check these and prompt for MFA
            async def send_with_challenge(message):
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    headers.append((b"X-Zero-Trust-Decision", b"CHALLENGE"))
                    headers.append((b"X-Zero-Trust-Required", ",".join(result.required_actions).encode()))
                    message["headers"] = headers
                await send(message)
            
            await self.app(scope, receive, send_with_challenge)
            return
        
        # ALLOW - add trust level header
        async def send_with_trust(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"X-Zero-Trust-Decision", b"ALLOW"))
                headers.append((b"X-Trust-Level", result.trust_level.value.encode()))
                message["headers"] = headers
            await send(message)
        
        await self.app(scope, receive, send_with_trust)


# ============================================================================
# Dependency Injection
# ============================================================================

async def get_zero_trust_context(request: Request) -> AccessContext:
    """FastAPI dependency to get Zero-Trust context."""
    user_id = getattr(request.state, "user_id", None) if hasattr(request, "state") else None
    username = getattr(request.state, "username", None) if hasattr(request, "state") else None
    role = getattr(request.state, "role", None) if hasattr(request, "state") else None
    session_id = getattr(request.state, "session_id", None) if hasattr(request, "state") else None
    mfa_verified = getattr(request.state, "mfa_verified", False) if hasattr(request, "state") else False
    session_created = getattr(request.state, "session_created", None) if hasattr(request, "state") else None
    
    return build_access_context(
        request=request,
        user_id=user_id,
        username=username,
        role=role,
        session_id=session_id,
        mfa_verified=mfa_verified,
        session_created=session_created,
    )


async def get_zero_trust_result(request: Request) -> Optional[AccessResult]:
    """FastAPI dependency to get Zero-Trust evaluation result."""
    if hasattr(request, "state") and hasattr(request.state, "zero_trust_result"):
        return request.state.zero_trust_result
    return None


def require_trust_level(min_level: TrustLevel):
    """
    Decorator/dependency to require minimum trust level.
    
    Usage:
        @app.get("/sensitive")
        async def sensitive_endpoint(trust=Depends(require_trust_level(TrustLevel.HIGH))):
            ...
    """
    async def check_trust_level(request: Request):
        result = await get_zero_trust_result(request)
        if not result:
            raise HTTPException(status_code=403, detail="Zero-Trust evaluation required")
        
        trust_hierarchy = [TrustLevel.NONE, TrustLevel.LOW, TrustLevel.MEDIUM, TrustLevel.HIGH, TrustLevel.FULL]
        
        try:
            current_idx = trust_hierarchy.index(result.trust_level)
            required_idx = trust_hierarchy.index(min_level)
            
            if current_idx < required_idx:
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient trust level. Required: {min_level.value}, Current: {result.trust_level.value}"
                )
        except ValueError:
            raise HTTPException(status_code=403, detail="Invalid trust level")
        
        return result.trust_level
    
    return check_trust_level


def require_mfa():
    """
    Dependency to require MFA verification.
    
    Usage:
        @app.post("/critical-action")
        async def critical_action(mfa=Depends(require_mfa())):
            ...
    """
    async def check_mfa(request: Request):
        context = await get_zero_trust_context(request)
        if not context.mfa_verified:
            raise HTTPException(
                status_code=403,
                detail="MFA verification required",
                headers={"X-MFA-Required": "true"}
            )
        return True
    
    return check_mfa


# ============================================================================
# Device Registration Endpoints Helper
# ============================================================================

class DeviceRegistrationHelper:
    """Helper for device registration endpoints."""
    
    def __init__(self, zero_trust: Optional[ZeroTrust] = None):
        self.zt = zero_trust or get_zero_trust()
    
    def register_device(self, request: Request, user_id: str, **kwargs) -> DeviceInfo:
        """Register device from request."""
        device_info = extract_device_info(request)
        device_info.registered_user_id = user_id
        
        # Apply additional attributes
        for key, value in kwargs.items():
            if hasattr(device_info, key):
                setattr(device_info, key, value)
        
        return self.zt.register_device(device_info)
    
    def get_device(self, request: Request) -> Optional[DeviceInfo]:
        """Get device info for current request."""
        device_id = request.headers.get("X-Device-ID") or generate_device_id(request)
        return self.zt.get_device(device_id)
    
    def is_registered(self, request: Request) -> bool:
        """Check if device is registered."""
        device = self.get_device(request)
        return device is not None and device.posture != DevicePosture.QUARANTINED
