# The Veil 🛡️  
**Hospital Security & Operations Control Plane**

The Veil is a continuously running, security-first hospital operations system designed to **monitor, protect, and coordinate critical services (“organs”)** while providing clear, auditable visibility into patient state and system health.

Built **solo**, with **zero funding**, The Veil focuses on correctness, persistence, and operational realism over demos or mockups.

---

## ✨ Core Features

### 🧠 Systems Overview
- Real-time visibility into all registered security and infrastructure services (“organs”)
- Clear separation between:
  - **Total services**
  - **Running services (PID-verified)**
- Designed for 24/7 operation

### 🛡️ Security Organs
- Organ-based architecture (each service is isolated and observable)
- Restart-only controls (no start/stop toggles by design)
  - Reduces attack surface
  - Prevents accidental or malicious shutdowns
- Tiered classification (P0 / P1 / P2)

### 🏥 Patient State Management
- Persistent patient records (JSON-backed, atomic writes)
- Clear lifecycle:
  - Active
  - Discharged
  - Restored
- Counts and views update automatically

### 📊 System Status
- Dedicated system health page
- Designed to expand with real metrics (CPU, memory, load, audits)

### 🧪 Testing & Evidence
- Automated smoke tests using `pytest`
- All primary routes verified to load successfully
- Test output captured for audit and demonstration

---

## 🧱 Architecture

- **Backend:** FastAPI (ASGI)
- **Templating:** Jinja2
- **Frontend:**  
  - Server-rendered HTML for operations
  - Optional React/Vite dashboard served at `/app`
- **Process Control:**  
  - PID-based truth (`run.pid`)
  - Explicit separation between *runnable* and *running*
- **Persistence:**  
  - JSON files with atomic write safety
- **OS:** Linux (Ubuntu-based deployment)

---

## 🌐 Routes Overview

| Route | Purpose |
|-----|--------|
| `/` | Systems overview |
| `/patients` | Active patients |
| `/discharged` | Discharged patients |
| `/organs` | Security organs dashboard |
| `/status` | System status |
| `/app` | React dashboard (optional build) |

---

## 🚀 Running Locally

```bash
uvicorn veil.hospital_gui.main:app --reload --host 127.0.0.1 --port 8000
 
