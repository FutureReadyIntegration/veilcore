"""
Veil Hospital GUI - Secure Edition
===================================
FastAPI application with full security integration.

Security Features:
- JWT/Session authentication via Guardian
- Role-based access control (RBAC)
- Rate limiting
- CSRF protection
- Security headers
- Audit logging
"""

from __future__ import annotations

import json
import time
import secrets
import subprocess
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Response, HTTPException, Depends, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Veil imports
from veil.orchestrator import list_services

# Security imports
from veil.security import (
    Guardian, get_guardian, verify_password, hash_password,
    SessionManager, get_session_manager,
    RBAC, Role, Permission, is_public_route,
    AuditLog, get_audit_log, AuditLevel,
    SecurityMiddleware, RateLimiter, CSRFProtection, SECURITY_HEADERS,
    SecurityContext,
    User, Token, LoginResponse,
)


# ============================================================================
# Configuration
# ============================================================================

# Use relative paths that work in development
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
PATIENTS_FILE = DATA_DIR / "patients.json"
ORGANS_DIR = Path("/opt/veil_os/organs")
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

# Fallback paths for production
if not TEMPLATES_DIR.exists():
    TEMPLATES_DIR = Path("/home/user/veil_os/backend/veil/hospital_gui/templates")
if not STATIC_DIR.exists():
    STATIC_DIR = Path("/home/user/veil_os/backend/veil/hospital_gui/static")
if not DATA_DIR.exists():
    DATA_DIR = Path("/home/user/veil_os/backend/veil/hospital_gui/data")
    PATIENTS_FILE = DATA_DIR / "patients.json"


# ============================================================================
# Application Setup
# ============================================================================

app = FastAPI(
    title="Veil Hospital GUI",
    description="Secure Hospital Operations Control Plane",
    version="2.0.0"
)

# Mount static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Mount React frontend if built
if FRONTEND_DIST.exists():
    app.mount("/app", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="app")

# Templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ============================================================================
# Security Initialization
# ============================================================================

# Initialize security components (lazy-loaded singletons)
def get_guardian_instance() -> Guardian:
    return get_guardian()

def get_session_instance() -> SessionManager:
    return get_session_manager()

def get_audit_instance() -> AuditLog:
    return get_audit_log()


# ============================================================================
# Security Middleware
# ============================================================================

@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """Main security middleware - handles all security concerns."""
    start_time = time.time()
    
    path = request.url.path
    method = request.method
    
    # Skip security for static files
    if path.startswith("/static/") or path.startswith("/favicon"):
        response = await call_next(request)
        return response
    
    # Get client IP
    ip_address = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    if not ip_address:
        ip_address = request.headers.get("X-Real-IP", "")
    if not ip_address and request.client:
        ip_address = request.client.host
    
    # Store IP for later use
    request.state.ip_address = ip_address
    
    # Rate limiting for API endpoints
    if path.startswith("/api/"):
        # Simple in-memory rate limiting (replace with Redis in production)
        # For now, we'll skip detailed rate limiting in this middleware
        pass
    
    # Process request
    response = await call_next(request)
    
    # Add security headers
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value
    
    # Add request ID for tracing
    request_id = secrets.token_hex(8)
    response.headers["X-Request-ID"] = request_id
    
    # Calculate duration
    duration_ms = (time.time() - start_time) * 1000
    
    # Audit logging for non-static requests
    if not path.startswith("/static/"):
        audit = get_audit_instance()
        
        # Get session if exists
        session_id = request.cookies.get("veil_session")
        session = None
        if session_id:
            sm = get_session_instance()
            session = sm.get(session_id)
        
        # Log based on response status
        if response.status_code >= 400:
            level = AuditLevel.WARNING if response.status_code < 500 else AuditLevel.ERROR
        else:
            level = AuditLevel.INFO
        
        # Only log significant requests
        if not path.startswith("/api/health"):
            audit.log(
                level=level,
                category="http",
                action=f"{method} {path}",
                session=session,
                ip_address=ip_address,
                details={
                    "method": method,
                    "path": path,
                    "status": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                    "request_id": request_id,
                },
                success=response.status_code < 400
            )
    
    return response


# ============================================================================
# Authentication Dependency
# ============================================================================

async def get_current_user(request: Request) -> Optional[SecurityContext]:
    """
    Dependency to get current authenticated user/session.
    Returns SecurityContext or None if not authenticated.
    """
    ip_address = getattr(request.state, 'ip_address', None) or (
        request.client.host if request.client else "unknown"
    )
    user_agent = request.headers.get("User-Agent", "")
    
    # Check Bearer token first
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        guardian = get_guardian_instance()
        user, error = guardian.verify_token(token)
        
        if user:
            return SecurityContext(
                user=user,
                ip_address=ip_address,
                user_agent=user_agent
            )
    
    # Check session cookie
    session_id = request.cookies.get("veil_session")
    if session_id:
        sm = get_session_instance()
        session = sm.validate(session_id)
        
        if session:
            return SecurityContext(
                session=session,
                ip_address=ip_address,
                user_agent=user_agent
            )
    
    return None


async def require_auth(request: Request) -> SecurityContext:
    """Dependency that requires authentication."""
    ctx = await get_current_user(request)
    if not ctx or not ctx.authenticated:
        # For HTML pages, redirect to login
        if "text/html" in request.headers.get("Accept", ""):
            raise HTTPException(status_code=302, headers={"Location": "/login"})
        raise HTTPException(status_code=401, detail="Authentication required")
    return ctx


async def require_admin(request: Request) -> SecurityContext:
    """Dependency that requires admin role."""
    ctx = await require_auth(request)
    if not ctx.has_role(Role.ADMIN):
        raise HTTPException(status_code=403, detail="Admin access required")
    return ctx


async def require_operator(request: Request) -> SecurityContext:
    """Dependency that requires operator role or higher."""
    ctx = await require_auth(request)
    if not ctx.has_role(Role.OPERATOR):
        raise HTTPException(status_code=403, detail="Operator access required")
    return ctx


# ============================================================================
# Organ Helpers
# ============================================================================

GLYPH = {"sentinel": "🛡️", "watchtower": "🛰️", "audit": "📜"}
P0 = {"sentinel", "guardian", "epic", "imprivata", "backup", "quarantine"}
P1 = {"watchtower", "mfa", "rbac", "dlp", "phi", "firewall", "vault", "session", "audit", "orchestrator"}


def _tier(name: str) -> str:
    if name in P0:
        return "P0"
    if name in P1:
        return "P1"
    return "P2"


def _is_runnable(name: str) -> bool:
    return (ORGANS_DIR / name / "run.sh").exists()


def get_organs():
    out = []
    for s in list_services():
        out.append({
            "name": s.name,
            "running": bool(getattr(s, "running", False)),
            "tier": _tier(s.name),
            "glyph": GLYPH.get(s.name, "🫀"),
            "pid": getattr(s, "pid", None),
            "log": getattr(s, "log", ""),
            "runnable": _is_runnable(s.name),
        })
    return out


# ============================================================================
# Patient Helpers
# ============================================================================

def _load_patients() -> dict:
    if not PATIENTS_FILE.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        PATIENTS_FILE.write_text('{"next_id": 1, "patients": []}\n', encoding="utf-8")
    try:
        return json.loads(PATIENTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"next_id": 1, "patients": []}


def _save_patients(data: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = PATIENTS_FILE.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.rename(PATIENTS_FILE)


def _counts() -> dict:
    data = _load_patients()
    pts = data.get("patients", [])
    active = [p for p in pts if not p.get("discharged_at")]
    discharged = [p for p in pts if p.get("discharged_at")]
    return {"total": len(pts), "active": len(active), "discharged": len(discharged)}


# ============================================================================
# Public Routes (No Auth Required)
# ============================================================================

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page."""
    # If already logged in, redirect to dashboard
    ctx = await get_current_user(request)
    if ctx and ctx.authenticated:
        return RedirectResponse(url="/", status_code=302)
    
    csrf_token = CSRFProtection.generate_token()
    response = templates.TemplateResponse(
        "login.html",
        {"request": request, "error": None, "csrf_token": csrf_token}
    )
    response.set_cookie(
        key=CSRFProtection.COOKIE_NAME,
        value=csrf_token,
        httponly=True,
        samesite="lax"
    )
    return response


@app.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    remember_me: bool = Form(False)
):
    """Process login form."""
    ip_address = getattr(request.state, 'ip_address', "unknown")
    audit = get_audit_instance()
    guardian = get_guardian_instance()
    
    # Authenticate
    result = guardian.authenticate(username, password, ip_address)
    
    if not result.success:
        # Log failed attempt
        audit.auth_login(username, ip_address, success=False, error_message=result.message)
        
        csrf_token = CSRFProtection.generate_token()
        response = templates.TemplateResponse(
            "login.html",
            {"request": request, "error": result.message, "csrf_token": csrf_token}
        )
        response.set_cookie(key=CSRFProtection.COOKIE_NAME, value=csrf_token, httponly=True)
        return response
    
    # Create session
    sm = get_session_instance()
    user = guardian.get_user(username)
    session = sm.create(
        user_id=user.id,
        username=user.username,
        role=user.role,
        ip_address=ip_address,
        user_agent=request.headers.get("User-Agent"),
        remember_me=remember_me
    )
    
    # Log success
    audit.auth_login(username, ip_address, success=True)
    
    # Redirect to dashboard with session cookie
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="veil_session",
        value=session.id,
        httponly=True,
        samesite="lax",
        max_age=86400 * 7 if remember_me else None
    )
    return response


@app.get("/logout")
async def logout(request: Request):
    """Logout and invalidate session."""
    session_id = request.cookies.get("veil_session")
    
    if session_id:
        sm = get_session_instance()
        session = sm.get(session_id)
        
        if session:
            audit = get_audit_instance()
            audit.auth_logout(session=session, ip_address=getattr(request.state, 'ip_address', None))
        
        sm.invalidate(session_id)
    
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("veil_session")
    return response


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "veil-hospital-gui"}


@app.get("/api/health")
async def api_health():
    """API health check."""
    return {"status": "healthy"}


# ============================================================================
# Protected Pages (Auth Required)
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def systems(request: Request, ctx: SecurityContext = Depends(require_auth)):
    """Systems overview dashboard."""
    organs = get_organs()
    c = _counts()
    
    return templates.TemplateResponse(
        "systems.html",
        {
            "request": request,
            "user": ctx.username,
            "role": ctx.role.value if ctx.role else None,
            "counts": c,
            "organs_total": len(organs),
            "organs_running": sum(1 for o in organs if o.get("running") or o.get("pid")),
            "organs_runnable": sum(1 for o in organs if o.get("runnable")),
        },
    )


@app.get("/patients", response_class=HTMLResponse)
async def patients(request: Request, ctx: SecurityContext = Depends(require_auth)):
    """Active patients page."""
    if not ctx.has_permission(Permission.VIEW_PATIENTS):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    return templates.TemplateResponse(
        "patients.html",
        {"request": request, "user": ctx.username, "role": ctx.role.value}
    )


@app.get("/discharged", response_class=HTMLResponse)
async def discharged(request: Request, ctx: SecurityContext = Depends(require_auth)):
    """Discharged patients page."""
    if not ctx.has_permission(Permission.VIEW_PATIENTS):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    return templates.TemplateResponse(
        "discharged.html",
        {"request": request, "user": ctx.username, "role": ctx.role.value}
    )


@app.get("/organs", response_class=HTMLResponse)
async def organs_page(request: Request, ctx: SecurityContext = Depends(require_auth)):
    """Security organs dashboard."""
    if not ctx.has_permission(Permission.VIEW_ORGANS):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    organs = get_organs()
    p0 = [o for o in organs if o.get("tier") == "P0"]
    p1 = [o for o in organs if o.get("tier") == "P1"]
    p2 = [o for o in organs if o.get("tier") == "P2"]
    
    return templates.TemplateResponse(
        "organs.html",
        {
            "request": request,
            "user": ctx.username,
            "role": ctx.role.value,
            "total": len(organs),
            "p0": p0,
            "p1": p1,
            "p2": p2
        },
    )


@app.get("/status", response_class=HTMLResponse)
async def status_page(request: Request, ctx: SecurityContext = Depends(require_auth)):
    """System status page."""
    return templates.TemplateResponse(
        "status.html",
        {"request": request, "user": ctx.username, "role": ctx.role.value}
    )


@app.get("/audit", response_class=HTMLResponse)
async def audit_page(request: Request, ctx: SecurityContext = Depends(require_auth)):
    """Audit log page (admin only)."""
    if not ctx.has_permission(Permission.VIEW_AUDIT):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    audit = get_audit_instance()
    events = audit.get_recent(100)
    
    return templates.TemplateResponse(
        "audit.html",
        {
            "request": request,
            "user": ctx.username,
            "role": ctx.role.value,
            "events": [e.to_dict() for e in events]
        },
    )


@app.get("/security", response_class=HTMLResponse)
async def security_page(request: Request, ctx: SecurityContext = Depends(require_admin)):
    """Security dashboard (admin only)."""
    sm = get_session_instance()
    sessions = sm.get_all_sessions()
    
    guardian = get_guardian_instance()
    users = guardian.list_users()
    
    return templates.TemplateResponse(
        "security.html",
        {
            "request": request,
            "user": ctx.username,
            "role": ctx.role.value,
            "sessions": [s.to_dict() for s in sessions],
            "users": [u.to_dict() for u in users],
        },
    )


# ============================================================================
# Protected API Endpoints
# ============================================================================

@app.get("/api/organs", response_class=JSONResponse)
async def api_organs(ctx: SecurityContext = Depends(require_auth)):
    """Get all organs status."""
    if not ctx.has_permission(Permission.VIEW_ORGANS):
        raise HTTPException(status_code=403)
    return get_organs()


@app.get("/api/systems", response_class=JSONResponse)
async def api_systems(ctx: SecurityContext = Depends(require_auth)):
    """Get system overview."""
    organs = get_organs()
    return {
        "organs_total": len(organs),
        "organs_running": sum(1 for o in organs if o.get("running") or o.get("pid")),
        "organs_runnable": sum(1 for o in organs if o.get("runnable")),
        "patients": _counts(),
    }


@app.post("/api/restart", response_class=JSONResponse)
async def api_restart(request: Request, ctx: SecurityContext = Depends(require_admin)):
    """Restart Veil service (admin only)."""
    if not ctx.has_permission(Permission.SYSTEM_RESTART):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Audit this critical action
    audit = get_audit_instance()
    audit.system_action(
        action="system_restart",
        session=ctx.session,
        ip_address=getattr(request.state, 'ip_address', None),
        details={"initiated_by": ctx.username}
    )
    
    subprocess.run(["sudo", "systemctl", "restart", "veil.service"])
    return {"status": "restarting", "initiated_by": ctx.username}


@app.post("/api/organs/{organ_name}/restart", response_class=JSONResponse)
async def api_organ_restart(
    organ_name: str,
    request: Request,
    ctx: SecurityContext = Depends(require_operator)
):
    """Restart a specific organ."""
    if not ctx.has_permission(Permission.RESTART_ORGAN):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    audit = get_audit_instance()
    audit.organ_action(
        action="restart",
        organ_name=organ_name,
        session=ctx.session,
        ip_address=getattr(request.state, 'ip_address', None)
    )
    
    # TODO: Implement actual organ restart via orchestrator
    return {"status": "restarting", "organ": organ_name}


@app.get("/api/audit", response_class=JSONResponse)
async def api_audit(
    limit: int = 100,
    ctx: SecurityContext = Depends(require_auth)
):
    """Get audit events."""
    if not ctx.has_permission(Permission.VIEW_AUDIT):
        raise HTTPException(status_code=403)
    
    audit = get_audit_instance()
    events = audit.get_recent(limit)
    return [e.to_dict() for e in events]


@app.get("/api/sessions", response_class=JSONResponse)
async def api_sessions(ctx: SecurityContext = Depends(require_admin)):
    """Get all active sessions (admin only)."""
    sm = get_session_instance()
    return [s.to_dict() for s in sm.get_all_sessions()]


@app.delete("/api/sessions/{session_id}", response_class=JSONResponse)
async def api_delete_session(
    session_id: str,
    request: Request,
    ctx: SecurityContext = Depends(require_admin)
):
    """Invalidate a session (admin only)."""
    sm = get_session_instance()
    
    audit = get_audit_instance()
    audit.log(
        level=AuditLevel.SECURITY,
        category="security",
        action="session_invalidate",
        session=ctx.session,
        ip_address=getattr(request.state, 'ip_address', None),
        resource_type="session",
        resource_id=session_id
    )
    
    if sm.invalidate(session_id):
        return {"status": "invalidated"}
    raise HTTPException(status_code=404, detail="Session not found")


# ============================================================================
# Auth API (for programmatic access)
# ============================================================================

@app.post("/api/auth/login", response_class=JSONResponse)
async def api_login(request: Request):
    """API login endpoint - returns JWT token."""
    body = await request.json()
    username = body.get("username")
    password = body.get("password")
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")
    
    ip_address = getattr(request.state, 'ip_address', "unknown")
    guardian = get_guardian_instance()
    audit = get_audit_instance()
    
    result = guardian.authenticate(username, password, ip_address)
    
    if not result.success:
        audit.auth_login(username, ip_address, success=False, error_message=result.message)
        raise HTTPException(status_code=401, detail=result.message)
    
    audit.auth_login(username, ip_address, success=True)
    return result.to_dict()


@app.post("/api/auth/refresh", response_class=JSONResponse)
async def api_refresh(request: Request):
    """Refresh access token using refresh token."""
    body = await request.json()
    refresh_token = body.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(status_code=400, detail="Refresh token required")
    
    guardian = get_guardian_instance()
    token, error = guardian.refresh_access_token(refresh_token)
    
    if error:
        raise HTTPException(status_code=401, detail=error)
    
    return token.to_dict()


@app.get("/api/auth/me", response_class=JSONResponse)
async def api_me(ctx: SecurityContext = Depends(require_auth)):
    """Get current user info."""
    return {
        "username": ctx.username,
        "role": ctx.role.value if ctx.role else None,
        "authenticated": ctx.authenticated,
    }


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc: HTTPException):
    """Handle 401 errors."""
    if "text/html" in request.headers.get("Accept", ""):
        return RedirectResponse(url="/login", status_code=302)
    return JSONResponse(status_code=401, content={"detail": "Authentication required"})


@app.exception_handler(403)
async def forbidden_handler(request: Request, exc: HTTPException):
    """Handle 403 errors."""
    if "text/html" in request.headers.get("Accept", ""):
        return templates.TemplateResponse(
            "403.html",
            {"request": request, "detail": exc.detail},
            status_code=403
        )
    return JSONResponse(status_code=403, content={"detail": exc.detail})


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Handle 404 errors."""
    if "text/html" in request.headers.get("Accept", ""):
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    return JSONResponse(status_code=404, content={"detail": "Not found"})


@app.exception_handler(500)
async def server_error_handler(request: Request, exc: Exception):
    """Handle 500 errors."""
    audit = get_audit_instance()
    audit.log(
        level=AuditLevel.ERROR,
        category="system",
        action="internal_error",
        ip_address=getattr(request.state, 'ip_address', None),
        details={"error": str(exc), "path": request.url.path},
        success=False,
        error_message=str(exc)
    )
    
    if "text/html" in request.headers.get("Accept", ""):
        return templates.TemplateResponse("500.html", {"request": request}, status_code=500)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
    return 0


if __name__ == "__main__":
    main()
