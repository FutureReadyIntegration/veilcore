from fastapi import FastAPI
from veil.dashboard.veil_dashboard_routes import router
import uvicorn

app = FastAPI()
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(
        "veil.dashboard.service:app",
        host="0.0.0.0",
        port=8090,
        reload=False
    )
