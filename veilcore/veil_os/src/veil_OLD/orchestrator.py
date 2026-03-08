from __future__ import annotations

import os
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

# --- Paths (single source of truth) -----------------------------------------

VAR_DIR = Path("/opt/veil_os/var")
RUN_DIR = VAR_DIR / "run" / "veil_services"
LOG_DIR = VAR_DIR / "log"

RUN_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)


# --- Models ------------------------------------------------------------------

@dataclass(frozen=True)
class ServiceStatus:
    name: str
    running: bool
    pid: Optional[int]
    log_path: Path


# --- Organ discovery ----------------------------------------------------------

def _load_organs() -> list[str]:
    """
    Returns list of organ/service names.
    Tries veil_organs / veil_organs_v2; falls back to reading organs.json if present.
    """
    # 1) Try your organ modules if they exist
    for mod_name in ("veil.veil_organs", "veil.veil_organs_v2"):
        try:
            mod = __import__(mod_name, fromlist=["list_organs"])
            if hasattr(mod, "list_organs"):
                organs = mod.list_organs()
                # allow list of dicts or list of names
                if organs and isinstance(organs[0], dict):
                    return [o.get("name", "") for o in organs if o.get("name")]
                return [str(x) for x in organs]
        except Exception:
            pass

    # 2) Fallback: /opt/veil_os/data/organs.json
    data_path = Path("/opt/veil_os/data/organs.json")
    if data_path.exists():
        import json
        try:
            data = json.loads(data_path.read_text(encoding="utf-8"))
            return [o["name"] for o in data if isinstance(o, dict) and "name" in o]
        except Exception:
            pass

    return []


# --- PID + process checks -----------------------------------------------------

def _pidfile(name: str) -> Path:
    return RUN_DIR / f"{name}.pid"

def _read_pid(name: str) -> Optional[int]:
    p = _pidfile(name)
    if not p.exists():
        return None
    try:
        txt = p.read_text(encoding="utf-8").strip()
        return int(txt)
    except Exception:
        return None

def _is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # If we can't signal it, assume alive (common in restricted envs)
        return True

def _write_pid(name: str, pid: int) -> None:
    _pidfile(name).write_text(str(pid), encoding="utf-8")

def _clear_pid(name: str) -> None:
    try:
        _pidfile(name).unlink()
    except FileNotFoundError:
        pass


# --- Service commands ---------------------------------------------------------

def _service_log(name: str) -> Path:
    return LOG_DIR / f"{name}.log"

def _resolve_service_command(name: str) -> list[str]:
    """
    Hospital-grade rule: if a real service exists, run it.
    Otherwise run a safe placeholder daemon so the orchestrator + GUI are correct.

    Preferred hooks (first match wins):
      1) /opt/veil_os/services/<name>.sh
      2) /opt/veil_os/services/<name>.py
      3) python -m veil.services.<name>
      4) placeholder loop (keeps process alive, writes to log)
    """
    sh = Path("/opt/veil_os/services") / f"{name}.sh"
    if sh.exists() and os.access(sh, os.X_OK):
        return [str(sh)]

    py = Path("/opt/veil_os/services") / f"{name}.py"
    if py.exists():
        return [sys_python(), str(py)]

    # try python module hook (optional)
    try:
        __import__(f"veil.services.{name}")
        return [sys_python(), "-m", f"veil.services.{name}"]
    except Exception:
        pass

    # placeholder (safe + deterministic)
    return [
        sys_python(),
        "-c",
        (
            "import os,time,datetime\n"
            f"name={name!r}\n"
            "print(datetime.datetime.utcnow().isoformat()+'Z', 'veil-service', name, 'started', flush=True)\n"
            "while True:\n"
            "    time.sleep(5)\n"
        ),
    ]

def sys_python() -> str:
    # Prefer venv python when available
    venv_py = Path("/srv/veil_os/api_venv/bin/python")
    if venv_py.exists():
        return str(venv_py)
    return "python3"


# --- Public API ---------------------------------------------------------------

def status(name: str) -> ServiceStatus:
    pid = _read_pid(name)
    log_path = _service_log(name)
    if pid is None:
        return ServiceStatus(name=name, running=False, pid=None, log_path=log_path)

    alive = _is_pid_alive(pid)
    if not alive:
        _clear_pid(name)
        return ServiceStatus(name=name, running=False, pid=None, log_path=log_path)

    return ServiceStatus(name=name, running=True, pid=pid, log_path=log_path)


def list_services(names: Optional[Iterable[str]] = None) -> list[ServiceStatus]:
    if names is None:
        names = _load_organs()
    return [status(n) for n in names]


def start_service(name: str, *, dry_run: bool = True) -> ServiceStatus:
    s = status(name)
    if s.running:
        return s

    if dry_run:
        # Preview: do not mutate system
        return ServiceStatus(name=name, running=False, pid=s.pid, log_path=s.log_path)

    log_path = _service_log(name)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = _resolve_service_command(name)

    # spawn as its own process group so stop can kill the whole tree
    with open(log_path, "ab", buffering=0) as lf:
        p = subprocess.Popen(
            cmd,
            stdout=lf,
            stderr=lf,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            env={**os.environ, "VEIL_SERVICE": name},
        )

    _write_pid(name, p.pid)
    return status(name)


def stop_service(name: str, *, dry_run: bool = True, timeout_sec: float = 2.0) -> ServiceStatus:
    s = status(name)
    if not s.running or s.pid is None:
        _clear_pid(name)
        return ServiceStatus(name=name, running=False, pid=None, log_path=s.log_path)

    if dry_run:
        return s

    pid = s.pid

    # Kill whole process group first (best for subprocess trees)
    try:
        os.killpg(pid, signal.SIGTERM)
    except Exception:
        # fallback: kill pid
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass

    # wait briefly
    import time
    t0 = time.time()
    while time.time() - t0 < timeout_sec:
        if not _is_pid_alive(pid):
            break
        time.sleep(0.05)

    # force kill if needed
    if _is_pid_alive(pid):
        try:
            os.killpg(pid, signal.SIGKILL)
        except Exception:
            try:
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass

    _clear_pid(name)
    return status(name)
