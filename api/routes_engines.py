"""VeilCore Engine API Routes"""
import sys
sys.path.insert(0, "/home/user/veilcore")
from core.engine_manager import EngineManager

mgr = EngineManager()

def list_engines():
    return {"engines": mgr.list_engines(), "summary": mgr.summary()}

def get_engine(engine_id):
    eng = mgr.get_engine(engine_id)
    if not eng:
        return {"error": f"engine not found: {engine_id}"}, 404
    return eng

if __name__ == "__main__":
    import json
    print(json.dumps(list_engines(), indent=2))
