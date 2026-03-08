from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI()

# Static + templates
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# -----------------
# ROUTES
# -----------------

@app.get("/", response_class=HTMLResponse)
def systems(request: Request):
    return templates.TemplateResponse("systems.html", {"request": request})


@app.get("/patients", response_class=HTMLResponse)
def patients(request: Request):
    return templates.TemplateResponse("patients.html", {"request": request})


@app.get("/discharged", response_class=HTMLResponse)
def discharged(request: Request):
    return templates.TemplateResponse("discharged.html", {"request": request})


@app.get("/organs", response_class=HTMLResponse)
def organs(request: Request):
    return templates.TemplateResponse("organs.html", {"request": request})


@app.get("/status", response_class=HTMLResponse)
def status(request: Request):
    return templates.TemplateResponse("status.html", {"request": request})
