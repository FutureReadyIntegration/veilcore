from fastapi import APIRouter

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/status")
def dashboard_status():
    return {
        "organ": "veil-dashboard",
        "status": "online",
        "message": "Operator UI backend responding"
    }
