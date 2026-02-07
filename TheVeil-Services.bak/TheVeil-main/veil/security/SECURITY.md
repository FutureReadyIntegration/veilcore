# Veil Security Layer

**Hospital-grade security for The Veil OS**

## Overview

The Veil Security Layer provides comprehensive protection for your hospital operations:

| Component | Tier | Description |
|-----------|------|-------------|
| **Guardian** | P0 | JWT-based authentication gateway |
| **Session** | P1 | Secure session management |
| **RBAC** | P1 | Role-based access control |
| **Audit** | P1 | Tamper-proof audit logging |
| **Middleware** | - | Rate limiting, CSRF, security headers |

## Quick Start

### 1. Replace main.py with main_secure.py

```bash
cd veil/hospital_gui
mv main.py main_insecure.py.bak
mv main_secure.py main.py
```

### 2. Initialize Security Data Directory

```bash
sudo mkdir -p /var/lib/veil/security
sudo mkdir -p /var/lib/veil/audit
sudo chown -R $USER:$USER /var/lib/veil
```

### 3. Start the Application

```bash
python -m uvicorn veil.hospital_gui.main:app --host 127.0.0.1 --port 8000
```

### 4. Login

Navigate to `http://localhost:8000/login`

**Default Admin Credentials:**
- Username: `admin`
- Password: `VeilAdmin2024!`

⚠️ **CHANGE THIS PASSWORD IMMEDIATELY AFTER FIRST LOGIN**

## Roles & Permissions

### Role Hierarchy

```
SYSTEM > ADMIN > OPERATOR > VIEWER
```

### Permission Matrix

| Permission | Viewer | Operator | Admin | System |
|------------|--------|----------|-------|--------|
| View Dashboard | ✅ | ✅ | ✅ | ✅ |
| View Patients | ✅ | ✅ | ✅ | ✅ |
| View Organs | ✅ | ✅ | ✅ | ✅ |
| Create Patient | ❌ | ✅ | ✅ | ❌ |
| Update Patient | ❌ | ✅ | ✅ | ❌ |
| Discharge Patient | ❌ | ✅ | ✅ | ❌ |
| Delete Patient | ❌ | ❌ | ✅ | ❌ |
| Restart Organ | ❌ | ✅ | ✅ | ❌ |
| Start/Stop Organ | ❌ | ❌ | ✅ | ❌ |
| System Restart | ❌ | ❌ | ✅ | ❌ |
| View Audit | ❌ | ❌ | ✅ | ✅ |
| Manage Users | ❌ | ❌ | ✅ | ❌ |

## Security Features

### 1. Authentication

- **JWT Tokens** for API access
- **Session Cookies** for browser access
- **Password Hashing** with PBKDF2-SHA256 (100k iterations)
- **Brute Force Protection**: 5 attempts, 15-minute lockout

### 2. Session Management

- Server-side session storage
- Configurable session duration (default: 60 minutes)
- "Remember Me" option (7 days)
- Activity timeout (30 minutes of inactivity)
- Maximum 5 concurrent sessions per user

### 3. RBAC (Role-Based Access Control)

- Fine-grained permissions
- Route-level protection
- Decorator-based authorization

### 4. Audit Logging

- **Tamper-proof** with SHA-256 hash chains
- All security events logged
- Failed login tracking
- Session management events
- Critical action logging

### 5. Security Headers

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000
Content-Security-Policy: default-src 'self'
Referrer-Policy: strict-origin-when-cross-origin
```

### 6. Rate Limiting

| Endpoint | Limit |
|----------|-------|
| `/api/auth/login` | 5/minute |
| `/api/restart` | 1/minute |
| `/api/organs/*/restart` | 5/minute |
| Default API | 60/minute |

### 7. CSRF Protection

- Double-submit cookie pattern
- Token-based validation for state-changing requests

## API Authentication

### JWT Token Authentication

```bash
# Login to get token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "VeilAdmin2024!"}'

# Response:
{
  "success": true,
  "token": {
    "access_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 3600,
    "refresh_token": "eyJ..."
  },
  "user": {...}
}

# Use token in requests
curl http://localhost:8000/api/organs \
  -H "Authorization: Bearer eyJ..."
```

### Refresh Token

```bash
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJ..."}'
```

## File Structure

```
veil/security/
├── __init__.py      # Package exports
├── models.py        # User, Role, Permission, Session, Token, AuditEvent
├── guardian.py      # JWT auth, password hashing, user management
├── session.py       # Session creation, validation, cleanup
├── rbac.py          # Permission checking, route protection
├── audit.py         # Tamper-proof audit logging
└── middleware.py    # FastAPI middleware, rate limiting, CSRF

veil/hospital_gui/
├── main_secure.py   # Secure FastAPI application
└── templates/
    ├── login.html       # Login page
    ├── base_secure.html # Secure base template
    ├── security.html    # Security dashboard (admin)
    ├── audit.html       # Audit log viewer (admin)
    └── 403.html         # Access denied page
```

## Configuration

### Environment Variables (Optional)

```bash
export VEIL_SECRET_KEY="your-256-bit-secret"
export VEIL_DATA_DIR="/var/lib/veil"
export VEIL_SESSION_TIMEOUT=60
export VEIL_MAX_FAILED_ATTEMPTS=5
```

### Default Paths

- **User Data**: `/var/lib/veil/security/users.json`
- **Sessions**: `/var/lib/veil/security/sessions.json`
- **Secret Key**: `/var/lib/veil/security/guardian.key`
- **Audit Log**: `/var/lib/veil/audit/audit.log`

## Verifying Audit Integrity

```python
from veil.security import get_audit_log

audit = get_audit_log()
result = audit.verify_integrity()

if result["verified"]:
    print(f"✅ Audit log verified: {result['events']} events")
else:
    print(f"❌ Integrity errors: {result['errors']}")
```

## HIPAA Compliance Notes

This security layer addresses several HIPAA Security Rule requirements:

- **§164.312(d)** - Person/Entity Authentication ✅
- **§164.312(a)(1)** - Access Control ✅
- **§164.312(b)** - Audit Controls ✅
- **§164.312(c)(1)** - Integrity (hash chain) ✅
- **§164.312(e)(1)** - Transmission Security (headers) ✅

## Support

For issues or questions about the security layer, contact the Veil OS development team.

---

*"I stand between chaos and those I protect." - Guardian Affirmation*
