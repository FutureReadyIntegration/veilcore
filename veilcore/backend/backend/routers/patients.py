from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter()

class PatientIn(BaseModel):
    name: str
    dob: str

# simple in-memory store for development
_patients = []

@router.post("/patients", status_code=status.HTTP_201_CREATED)
def create_patient(payload: PatientIn):
    _patients.append(payload.dict())
    return {"ok": True}

@router.get("/patients")
def list_patients():
    return {"patients": _patients, "total": len(_patients)}
