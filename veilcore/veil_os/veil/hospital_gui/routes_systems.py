"""Systems routes"""

from fastapi import APIRouter
from .api_systems import get_system_health, get_all_organs_status, get_patient_counts

router = APIRouter()

@router.get("/api/systems/live")
async def api_systems_live():
    return get_system_health()

@router.get("/api/systems/organs")
async def api_organs_status():
    return get_all_organs_status()

@router.get("/api/systems/patients")
async def api_patients_count():
    return get_patient_counts()
