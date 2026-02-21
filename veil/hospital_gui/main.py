from __future__ import annotations

import json
import subprocess
from pathlib import Path

import httpx
from fastapi import FastAPI, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE = Path("/opt/veil_os/backend/veil/hospital_gui")
TEMPLATES_DIR = BASE / "templates"
BASE_DIR = Path(__file__).resolve().parents[2]
STATIC_DIR = BASE_DIR / "backend" / "veil" / "hospital_gui" / "static"
DATA_DIR = BASE / "data"
PATIENTS_FILE = DATA_DIR / "patients.json"
FRONTEND_DIST = BASE / "frontend" / "dist"

SUPERVISOR_URL = "http://127.0.0.1:8085/organs"

app = FastAPI(title="Veil Hospital GUI")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
if FRONTEND_DIST.exists():
    app.mount("/app", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="app")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

def get_organs():
    try:
        r = httpx.get(SUPERVISOR_URL, timeout=2.0)
        data = r.json()
        return data if isinstance(data, list) else []
    except Exception:
        return []

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
            "organs_running": sum(1 for o in organs if o.get("status") == "active"),
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
def organs_page(request: Request):
    organs = get_organs()
    p0 = [o for o in organs if o.get("tier") == "P0"]
    p1 = [o for o in organs if o.get("tier") == "P1"]
    p2 = [o for o in organs if o.get("tier") == "P2"]
    return templates.TemplateResponse(
        "organs.html",
        {"request": request, "total": len(organs), "p0": p0, "p1": p1, "p2": p2},
    )

@app.get("/status", response_class=HTMLResponse)
def status_page(request: Request):
    return templates.TemplateResponse("status.html", {"request": request})

@app.get("/api/organs", response_class=JSONResponse)
def api_organs():
    return get_organs()

@app.get("/api/systems", response_class=JSONResponse)
def api_systems():
    organs = get_organs()
    return {
        "organs_total": len(organs),
        "organs_running": sum(1 for o in organs if o.get("status") == "active"),
        "organs_runnable": sum(1 for o in organs if o.get("runnable")),
        "patients": _counts(),
    }

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
    return JSONResponse(status_code=404, content={"error": "Not found"})

