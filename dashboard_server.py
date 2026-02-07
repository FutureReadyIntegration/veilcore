from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
import secrets
import psutil
import sys

sys.path.insert(0, str(Path(__file__).parent / "organs" / "righteousness_engine"))

try:
    from righteousness import righteousness_engine, Action
    RIGHTEOUSNESS_AVAILABLE = True
except ImportError:
    RIGHTEOUSNESS_AVAILABLE = False
    print("WARNING: Righteousness Engine not available")

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "cockpit-frontend"

app = FastAPI(title="VeilCore Security Platform", version="1.0.0")

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Request-ID"] = secrets.token_hex(8)
    response.headers["X-Protected-By"] = "VeilCore"
    return response

@app.get("/", response_class=HTMLResponse)
async def root():
    standalone = STATIC_DIR / "standalone.html"
    if standalone.exists():
        return HTMLResponse(content=standalone.read_text(), status_code=200)
    return JSONResponse({"error": "Dashboard not found"}, status_code=404)

@app.get("/api/status")
async def api_status():
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory().percent
    return {"cpu": cpu, "memory": mem, "lockdown": False, "security_events": 0}

@app.get("/api/organs")
async def api_organs():
    sys.path.insert(0, str(Path(__file__).parent / "organs"))
    
    try:
        import importlib
        if 'orchestrator' in sys.modules:
            importlib.reload(sys.modules['orchestrator'])
        
        from orchestrator import orchestrator
        scan_result = orchestrator.run_full_scan()
        organ_statuses = orchestrator.get_organ_status()
        
        return {
            "organs": organ_statuses,
            "total": len(organ_statuses),
            "running": len(organ_statuses),
            "threats_found": scan_result.get('critical', 0) + scan_result.get('warnings', 0)
        }
    except Exception as e:
        print(f"Orchestrator error: {e}")
        import traceback
        traceback.print_exc()
        return {"organs": [], "total": 0, "running": 0, "threats_found": 0}

@app.get("/api/threats")
async def api_threats():
    sys.path.insert(0, str(Path(__file__).parent / "organs"))
    
    try:
        import importlib
        if 'orchestrator' in sys.modules:
            importlib.reload(sys.modules['orchestrator'])
        
        from orchestrator import orchestrator
        scan_result = orchestrator.run_full_scan()
        
        detailed_threats = []
        for finding in scan_result.get('findings', []):
            detailed_threats.append({
                'organ': finding.get('organ'),
                'severity': finding.get('severity'),
                'message': finding.get('message'),
                'timestamp': finding.get('timestamp'),
                'details': finding.get('details', {})
            })
        
        return {
            'total_threats': len(detailed_threats),
            'critical': scan_result.get('critical', 0),
            'warnings': scan_result.get('warnings', 0),
            'threats': detailed_threats[:20]
        }
    except Exception as e:
        print(f"Threats API error: {e}")
        import traceback
        traceback.print_exc()
        return {'total_threats': 0, 'critical': 0, 'warnings': 0, 'threats': []}

@app.get("/api/righteousness/report")
async def righteousness_report():
    if not RIGHTEOUSNESS_AVAILABLE:
        return {"error": "Righteousness Engine not available"}
    return righteousness_engine.get_righteousness_report()

@app.get("/api/righteousness/recent")
async def righteousness_recent():
    if not RIGHTEOUSNESS_AVAILABLE:
        return {"decisions": []}
    
    ledger_path = Path("/opt/veil_os/ledger.json")
    if not ledger_path.exists():
        return {"decisions": []}
    
    import json
    ledger = json.loads(ledger_path.read_text())
    recent = ledger[-10:] if len(ledger) > 10 else ledger
    return {"decisions": recent}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "veilcore"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
