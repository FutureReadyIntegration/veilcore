from __future__ import annotations

import importlib.util
from pathlib import Path
import uvicorn
from fastapi import HTTPException
from pydantic import BaseModel

# Load the existing VeilCore API app from api.py
API_PATH = Path(__file__).resolve().with_name("api.py")
api_spec = importlib.util.spec_from_file_location("veilcore_base_api", API_PATH)
if api_spec is None or api_spec.loader is None:
    raise RuntimeError(f"Could not load base API from {API_PATH}")

api_mod = importlib.util.module_from_spec(api_spec)
api_spec.loader.exec_module(api_mod)

app = api_mod.app

# Load EngineManager from repo root
ROOT = Path(__file__).resolve().parents[2]
ENGINE_MANAGER_PATH = ROOT / "core" / "engine_manager.py"

mgr_spec = importlib.util.spec_from_file_location("veilcore_engine_manager", ENGINE_MANAGER_PATH)
if mgr_spec is None or mgr_spec.loader is None:
    raise RuntimeError(f"Could not load EngineManager from {ENGINE_MANAGER_PATH}")

mgr_mod = importlib.util.module_from_spec(mgr_spec)
mgr_spec.loader.exec_module(mgr_mod)

EngineManager = mgr_mod.EngineManager
_ENGINE_MGR = EngineManager()


class EngineFailReq(BaseModel):
    message: str = "manual failure"
    health: int = 40


@app.get("/engines")
def engines():
    return {"engines": _ENGINE_MGR.list_engines()}


@app.get("/engines/{engine_id}")
def engine_get(engine_id: str):
    eng = _ENGINE_MGR.get_engine(engine_id)
    if not eng:
        raise HTTPException(status_code=404, detail=f"engine not found: {engine_id}")
    return eng


@app.post("/engines/{engine_id}/start")
def engine_start(engine_id: str):
    try:
        eng = _ENGINE_MGR.start(engine_id)
        return {"ok": True, "engine": eng}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/engines/{engine_id}/stop")
def engine_stop(engine_id: str):
    try:
        eng = _ENGINE_MGR.stop(engine_id)
        return {"ok": True, "engine": eng}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/engines/{engine_id}/restart")
def engine_restart(engine_id: str):
    try:
        eng = _ENGINE_MGR.restart(engine_id)
        return {"ok": True, "engine": eng}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/engines/{engine_id}/fail")
def engine_fail(engine_id: str, req: EngineFailReq):
    try:
        eng = _ENGINE_MGR.fail(engine_id, req.message, req.health)
        return {"ok": True, "engine": eng}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9444, log_level="info")
