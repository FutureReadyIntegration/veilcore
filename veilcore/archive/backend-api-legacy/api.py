from veil.dashboard import router as dashboard_router
app.include_router(dashboard_router)

from veil.dashboard.root import router as dashboard_root_router
app.include_router(dashboard_root_router)
