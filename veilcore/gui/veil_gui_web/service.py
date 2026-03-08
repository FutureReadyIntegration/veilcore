import os
import base64
import time
import httpx
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from auth import router as auth_router

SUPERVISOR_SOCK = os.getenv("SUPERVISOR_SOCK", "/run/veil/supervisor.sock")
SUPERVISOR_BASE = "http://supervisor"
VEIL_SUPERVISOR_TOKEN = os.getenv("VEIL_SUPERVISOR_TOKEN", "")
VEIL_SUPERVISOR_BASIC_USER = os.getenv("VEIL_SUPERVISOR_BASIC_USER", "")
VEIL_SUPERVISOR_BASIC_PASS = os.getenv("VEIL_SUPERVISOR_BASIC_PASS", "")

def _auth_headers() -> dict:
    if VEIL_SUPERVISOR_BASIC_USER and VEIL_SUPERVISOR_BASIC_PASS:
        token = base64.b64encode(
            f"{VEIL_SUPERVISOR_BASIC_USER}:{VEIL_SUPERVISOR_BASIC_PASS}".encode("utf-8")
        ).decode("ascii")
        return {"authorization": f"Basic {token}"}
    if VEIL_SUPERVISOR_TOKEN:
        return {"authorization": f"Bearer {VEIL_SUPERVISOR_TOKEN}"}
    return {}

def uds_client(sock: str | None = None, timeout: float = 2.0) -> httpx.Client:
    transport = httpx.HTTPTransport(uds=(sock or SUPERVISOR_SOCK))
    return httpx.Client(
        transport=transport,
        base_url=SUPERVISOR_BASE,
        headers=_auth_headers(),
        timeout=timeout,
    )

app = FastAPI()
app.include_router(auth_router, prefix="/api/auth")
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(

    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["GET","POST","PUT","DELETE","OPTIONS"],

    allow_headers=["*"],

)


# Serve static frontend at root

# Sub-app for cockpit status
gui_app = FastAPI()
app.include_router(auth_router, prefix="/api/auth")
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(

    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["GET","POST","PUT","DELETE","OPTIONS"],

    allow_headers=["*"],

)


@gui_app.get("/status")
def gui_status():
    return {"gui": "ready"}

app.mount("/gui", gui_app)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/secure")
def secure(request: Request):
    auth = request.headers.get("authorization")
    if VEIL_SUPERVISOR_BASIC_USER and VEIL_SUPERVISOR_BASIC_PASS:
        expected = "Basic " + base64.b64encode(
            f"{VEIL_SUPERVISOR_BASIC_USER}:{VEIL_SUPERVISOR_BASIC_PASS}".encode("utf-8")
        ).decode("ascii")
        if auth != expected:
            raise HTTPException(status_code=401, detail="Unauthorized")
    return {"message": "Authenticated access granted"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("service:app", host="0.0.0.0", port=8147)
