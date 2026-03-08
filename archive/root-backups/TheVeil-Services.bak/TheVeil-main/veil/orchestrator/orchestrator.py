import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

@dataclass
class ServiceStatus:
    name: str
    running: bool
    pid: Optional[int]
    log: str
    tier: str = "P2"

_organs: Dict[str, Dict[str, Any]] = {}

def _discover():
    global _organs
    if _organs:
        return _organs
    specs = Path.home() / "veil_os/backend/veil/specs"
    if specs.exists():
        for f in specs.glob("*.yaml"):
            try:
                for doc in yaml.safe_load_all(f.read_text()):
                    if doc and "name" in doc:
                        n = doc["name"]
                        _organs[n] = {
                            "name": n,
                            "tier": doc.get("tier", "P2"),
                            "glyph": doc.get("glyph", "🔷"),
                            "running": False,
                            "pid": None,
                            "log": f"/opt/veil_os/var/log/{n}.log"
                        }
            except Exception:
                pass
    return _organs

def _to_status(name: str) -> ServiceStatus:
    d = _organs.get(name, {"name": name, "running": False, "pid": None, "log": "", "tier": "P2"})
    return ServiceStatus(name=d["name"], running=d["running"], pid=d["pid"], log=d["log"], tier=d.get("tier", "P2"))

def list_statuses() -> List[ServiceStatus]:
    _discover()
    return [_to_status(n) for n in _organs]

def list() -> List[Dict[str, Any]]:
    return [v for v in _discover().values()]

def list_services() -> List[ServiceStatus]:
    return list_statuses()

def status(name: str) -> ServiceStatus:
    _discover()
    return _to_status(name)

def get_status(name: str) -> ServiceStatus:
    return status(name)

def start(name: str, dry_run: bool = False) -> ServiceStatus:
    _discover()
    if name in _organs and not dry_run:
        _organs[name]["running"] = True
    return _to_status(name)

def start_service(name: str, dry_run: bool = False) -> ServiceStatus:
    return start(name, dry_run)

def stop(name: str, force: bool = False, dry_run: bool = False) -> ServiceStatus:
    _discover()
    if name in _organs and not dry_run:
        _organs[name]["running"] = False
        _organs[name]["pid"] = None
    return _to_status(name)

def stop_service(name: str, dry_run: bool = False) -> ServiceStatus:
    return stop(name, force=False, dry_run=dry_run)
