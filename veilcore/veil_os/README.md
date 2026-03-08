# The Veil - Hospital Cybersecurity Platform

> **"I stand between chaos and those I protect."**

Hospital-grade cybersecurity for Epic EHR and Imprivata SSO. Protects healthcare infrastructure from ransomware with 78 security organs working in concert.

## 🚀 Quick Start

```bash
sudo ./install.sh
# Access: http://localhost:8000
# Login: admin / VeilAdmin2024!
# ⚠️ CHANGE PASSWORD IMMEDIATELY
```

## 🛡️ Security Architecture

| Tier | Organ | Function |
|------|-------|----------|
| P0 | 🛡️ Guardian | JWT auth, password hashing, brute-force protection |
| P0 | 🔒 Auto-Lockdown | Graduated threat response |
| P1 | 🔐 Zero-Trust | Continuous verification, device posture |
| P1 | 👁️ Sentinel | Behavioral anomaly detection |
| P1 | 🕵️ Insider Threat | Privilege abuse, exfiltration detection |
| P1 | 📜 Audit | Tamper-proof logging (SHA-256 hash chain) |

## 📊 Role Permissions

| Role | View | Create | Delete | Admin |
|------|------|--------|--------|-------|
| Viewer | ✅ | ❌ | ❌ | ❌ |
| Operator | ✅ | ✅ | ❌ | ❌ |
| Admin | ✅ | ✅ | ✅ | ✅ |

## 🔐 API Authentication

```bash
# Get token
curl -X POST localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"VeilAdmin2024!"}'

# Use token
curl localhost:8000/api/organs -H "Authorization: Bearer <token>"
```

## ⚙️ Operations

```bash
systemctl status veil      # Status
systemctl restart veil     # Restart
journalctl -u veil -f      # Logs
```

## 📁 Structure

```
/opt/veil_os/veil/
├── security/          # Guardian, Session, RBAC, Audit
├── organs/            # Zero-Trust, Sentinel, Insider Threat, Auto-Lockdown
└── hospital_gui/      # FastAPI application

/var/lib/veil/         # Runtime data (users, sessions, audit)
/etc/veil/config.env   # Configuration
```

## 🏥 HIPAA Compliance

- ✅ Access Control (§164.312(a)(1))
- ✅ Audit Controls (§164.312(b))
- ✅ Integrity (§164.312(c)(1))
- ✅ Authentication (§164.312(d))

---

**The Veil** - *When ransomware comes for your hospital, I'll be waiting.*
