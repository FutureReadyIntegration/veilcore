from __future__ import annotations

import json
import subprocess
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# -------------------------------------------------------------------
# Fallback imports (prevents crashes if orchestrator/systemd missing)
# -------------------------------------------------------------------
try:
    from veil.orchestrator import list_services
except Exception:
    def list_services():
        return []

try:
    from veil.hospital_gui.systemd import list_veil_units
except Exception:
    def list_veil_units():
        return []

# -------------------------------------------------------------------
# Paths (normalized)
# -------------------------------------------------------------------
BASE = Path("/opt/veil_os/backend/veil/hospital_gui")
TEMPLATES_DIR = BASE / "templates"
STATIC_DIR = BASE / "static"
DATA_DIR = BASE / "data"
PATIENTS_FILE = DATA_DIR / "patients.json"
FRONTEND_DIST = BASE / "frontend" / "dist"

ORGANS_DIR = Path("/opt/veil_os/organs")

# -------------------------------------------------------------------
# FastAPI app
# -------------------------------------------------------------------
app = FastAPI(title="Veil Hospital GUI")

# Static + frontend
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
if FRONTEND_DIST.exists():
    app.mount("/app", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="app")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# -------------------------------------------------------------------
# Organs logic
# -------------------------------------------------------------------
GLYPH = {"sentinel": "🛡️", "watchtower": "🛰️", "audit": "📜"}
P0 = {"sentinel"}
P1 = {"watchtower"}

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

# -------------------------------------------------------------------
# Patients data helpers
# -------------------------------------------------------------------
def _load_patients() -> dict:
    if not PATIENTS_FILE.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        PATIENTS_FILE.write_text('{"next_id": 1, "patients": []}', encoding="utf-8")
    try:
        return json.loads(PATIENTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"next_id": 1, "patients": []}

def _save_patients(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PATIENTS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

def _counts() -> dict:
    data = _load_patients()
    pts = data.get("patients", [])
    active = [p for p in pts if not p.get("discharged_at")]
    discharged = [p for p in pts if p.get("discharged_at")]
    return {"total": len(pts), "active": len(active), "discharged": len(discharged)}

# -------------------------------------------------------------------
# HTML PAGES
# -------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def systems(request: Request):
    organs = get_organs()
    c = _counts()
    return templates.TemplateResponse(
        "systems.html",
        {
            "request": request,
            "counts": c,
            "organs_total": len(organs),
            "organs_running": sum(1 for o in organs if o.get("running") or o.get("pid")),
            "organs_runnable": sum(1 for o in organs if o.get("runnable")),
        },
    )

@app.get("/patients", response_class=HTMLResponse)
def patients(request: Request):
    return templates.TemplateResponse("patients.html", {"request": request})

@app.get("/discharged", response_class=HTMLResponse)
def discharged(request: Request):
    return templates.TemplateResponse("discharged.html", {"request": request})

@app.get("/organs", response_class=HTMLResponse)
def organs(request: Request):
    organs = get_organs()
    p0 = [o for o in organs if o["tier"] == "P0"]
    p1 = [o for o in organs if o["tier"] == "P1"]
    p2 = [o for o in organs if o["tier"] == "P2"]
    return templates.TemplateResponse(
        "organs.html",
        {"request": request, "total": len(organs), "p0": p0, "p1": p1, "p2": p2},
    )

@app.get("/status", response_class=HTMLResponse)
def status_page(request: Request):
    return templates.TemplateResponse("status.html", {"request": request})

# -------------------------------------------------------------------
# API: ORGANS + SYSTEMS
# -------------------------------------------------------------------
@app.get("/api/organs", response_class=JSONResponse)
def api_organs():
    return get_organs()

@app.get("/api/systems", response_class=JSONResponse)
def api_systems():
    organs = get_organs()
    return {
        "organs_total": len(organs),
        "organs_running": sum(1 for o in organs if o.get("running") or o.get("pid")),
        "organs_runnable": sum(1 for o in organs if o.get("runnable")),
        "patients": _counts(),
    }

# -------------------------------------------------------------------
# API: PATIENTS (FULL PROTOTYPE)
# -------------------------------------------------------------------
@app.get("/api/patients", response_class=JSONResponse)
def api_list_patients():
    data = _load_patients()
    return {"patients": data["patients"], "total": len(data["patients"])}

@app.post("/api/patients", response_class=JSONResponse, status_code=201)
def api_create_patient(payload: dict):
    data = _load_patients()
    next_id = data["next_id"]
    patient = {
        "id": next_id,
        "name": payload.get("name"),
        "dob": payload.get("dob"),
        "meta": payload.get("meta", {}),
        "discharged_at": None,
    }
    data["patients"].append(patient)
    data["next_id"] = next_id + 1
    _save_patients(data)
    return {"ok": True, "patient": patient}

@app.get("/api/patients/{patient_id}", response_class=JSONResponse)
def api_get_patient(patient_id: int):
    data = _load_patients()
    for p in data["patients"]:
        if p["id"] == patient_id:
            return {"patient": p}
    return JSONResponse(status_code=404, content={"detail": "Patient not found"})

@app.put("/api/patients/{patient_id}", response_class=JSONResponse)
def api_update_patient(patient_id: int, payload: dict):
    data = _load_patients()
    for idx, p in enumerate(data["patients"]):
        if p["id"] == patient_id:
            p.update(payload)
            data["patients"][idx] = p
            _save_patients(data)
            return {"ok": True, "patient": p}
    return JSONResponse(status_code=404, content={"detail": "Patient not found"})

# -------------------------------------------------------------------
# API: SYSTEMD UNITS
# -------------------------------------------------------------------
@app.get("/systems", response_class=HTMLResponse)
def systems_units(request: Request):
    systems = list_veil_units()
    running = [s for s in systems if s.get("running")]
    return templates.TemplateResponse(
        "systems.html",
        {"request": request, "systems": systems, "total": len(systems), "running": len(running)},
    )

@app.get("/api/veil-units", response_class=JSONResponse)
def api_veil_units():
    return list_veil_units()

# -------------------------------------------------------------------
# Restart API
# -------------------------------------------------------------------
@app.post("/api/restart")
def api_restart():
    subprocess.run(["sudo", "systemctl", "restart", "veil.service"])
    return {"status": "restarting"}

# -------------------------------------------------------------------
# Main entry
# -------------------------------------------------------------------
def main():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
    return 0

if __name__ == "__main__":
    main()

import httpx

@app.get("/api/organs")
async def api_organs():
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("http://localhost:8085/organs")
            return r.json()
    except Exception as e:
        return {"error": str(e), "organs": []}

import httpx

@app.get("/api/organs")
async def api_organs():
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("http://localhost:8085/organs")
            return r.json()
    except Exception as e:
        return {"error": str(e), "organs": []}
