from fastapi import APIRouter
from veil.organ_metadata import describe_organ, is_allowed

router = APIRouter()

@router.get("/organs")
def list_organs():
    """
    Return a standardized organ list for the cockpit UI.

    Each organ includes:
    - name
    - tier (P0/P1/P2)
    - glyph (hospital‑grade symbol)
    - allowed (whitelist enforcement)
    - status (running/stopped)
    """

    # Your orchestrator or supervisor should already know the running organs.
    # Example: supervisor.list_organs() → ["sentinel", "guardian", ...]
    running = supervisor.list_organs()

    organs = []
    for name in running:
        meta = describe_organ(name)
        meta["status"] = "running" if supervisor.is_running(name) else "stopped"
        organs.append(meta)

    # Add any allowed organs that are not running (optional)
    for name in sorted(ALLOWED_ORGANS):
        if name not in running:
            meta = describe_organ(name)
            meta["status"] = "stopped"
            organs.append(meta)

    return {"organs": organs}
