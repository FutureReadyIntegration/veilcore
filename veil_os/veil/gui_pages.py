from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="veil/templates")

# Fake in-memory data for now (swap with DB later)
PATIENTS = [
    {"id": 1, "name": "Ava Johnson", "age": 34, "status": "Admitted"},
    {"id": 2, "name": "Noah Smith", "age": 52, "status": "Discharged"},
]

@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@router.get("/patients", response_class=HTMLResponse)
def patients(request: Request):
    return templates.TemplateResponse(
        "patients.html",
        {"request": request, "patients": PATIENTS}
    )

@router.get("/patients/new", response_class=HTMLResponse)
def patient_new_form(request: Request):
    return templates.TemplateResponse("patient_new.html", {"request": request})

@router.post("/patients/new")
def patient_new_submit(name: str = Form(...), age: int = Form(...)):
    new_id = max([p["id"] for p in PATIENTS], default=0) + 1
    PATIENTS.append({"id": new_id, "name": name, "age": age, "status": "Admitted"})
    return RedirectResponse(url="/patients", status_code=303)
