# 🔱 Veil API - Main Application
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from veil_os.app.veilcore_signature_routes import router as veilcore_signature_router
import logging
import json
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime

logger = logging.getLogger("veil.app")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

router = APIRouter()

ORGANS = {
    "sentinel": {"description": "Behavioral anomaly detection", "tier": "P1", "glyph": "👁️"},
    "insider_threat": {"description": "Privilege abuse & exfiltration detection", "tier": "P1", "glyph": "🕵️"},
    "auto_lockdown": {"description": "Automated threat response", "tier": "P0", "glyph": "🔒"},
    "zero_trust": {"description": "Continuous verification engine", "tier": "P1", "glyph": "🔐"},
    "zombie_sweeper": {"description": "Stale resource cleanup", "tier": "P2", "glyph": "🧹"},
    "analytics_engine": {"description": "Security metrics & analysis", "tier": "P1", "glyph": "📊"},
    "telemetry_engine": {"description": "System resource monitoring", "tier": "P1", "glyph": "📡"},
    "guardian": {"description": "Authentication gateway", "tier": "P0", "glyph": "🛡️"},
    "audit": {"description": "Tamper-proof logging", "tier": "P1", "glyph": "📜"},
}

STATUS_DIR = Path("/var/lib/veil")


def get_organ_status(organ_name: str) -> dict:
    status_paths = [
        STATUS_DIR / organ_name / "status.json",
        STATUS_DIR / "lockdown" / "status.json" if organ_name == "auto_lockdown" else None,
    ]
    for path in status_paths:
        if path and path.exists():
            try:
                data = json.loads(path.read_text())
                if "updated_at" in data:
                    updated = datetime.fromisoformat(data["updated_at"])
                    age = (datetime.utcnow() - updated).total_seconds()
                    data["stale"] = age > 120
                return data
            except Exception:
                pass
    return {"running": False, "healthy": False, "message": "No status"}


@router.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok"}


@router.get("/api/organs/status", tags=["organs"])
async def organs_status():
    results = {}
    for name, info in ORGANS.items():
        status = get_organ_status(name)
        results[name] = {
            "name": name,
            "description": info["description"],
            "tier": info["tier"],
            "glyph": info["glyph"],
            "running": status.get("running", False),
            "healthy": status.get("healthy", False),
            "message": status.get("message", "Unknown"),
            "stale": status.get("stale", False),
        }
    return {"organs": results}


@router.get("/api/organs/{organ_name}", tags=["organs"])
async def organ_detail(organ_name: str):
    if organ_name not in ORGANS:
        return {"error": f"Unknown organ: {organ_name}"}
    info = ORGANS[organ_name]
    status = get_organ_status(organ_name)
    return {
        "name": organ_name,
        "description": info["description"],
        "tier": info["tier"],
        "glyph": info["glyph"],
        **status
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🔱 Veil app starting up")
    try:
        yield
    finally:
        logger.info("🔱 Veil app shutting down")


app = FastAPI(
    title="Veil Service",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(veilcore_signature_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
