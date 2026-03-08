from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routers import (
    health,
    state,
    organs,
    telemetry,
    chronicle,
    timeline,
    analytics,
    operator_presence,
    sweeper,
)

app = FastAPI(title="Veil Unleashed Backend")

# CORS (optional but helpful)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static UI
app.mount("/ui", StaticFiles(directory="backend/app/static"), name="ui")

# Routers
app.include_router(health.router)
app.include_router(state.router)
app.include_router(organs.router)
app.include_router(telemetry.router)
app.include_router(chronicle.router)
app.include_router(timeline.router)
app.include_router(analytics.router)
app.include_router(operator_presence.router)
app.include_router(sweeper.router)
