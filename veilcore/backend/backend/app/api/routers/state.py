from fastapi import APIRouter, HTTPException

from backend.app.api.services.state_vector import load_state_vector
from backend.app.models.state_vector import StateVector

router = APIRouter(prefix="/state", tags=["state"])


@router.get("/", response_model=StateVector)
def get_state_vector():
    try:
        state = load_state_vector()
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load state vector: {e}")
    return state
