import os
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn

from veil.cockpit.renderer import router as cockpit_router


print("### VEIL COCKPIT DESKTOP SERVER LOADED ###")


STATIC_DIR = "hospital_gui/static"


def now_hhmmss():
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%H:%M:%S")


app = FastAPI(title="Veil Cockpit Desktop")

# --- Static desktop assets ---
app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static",
)

# --- Cockpit desktop WebSocket ---
app.include_router(cockpit_router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "time": now_hhmmss(),
    }


if __name__ == "__main__":
    uvicorn.run(
        "dashboard_server:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info",
    )
