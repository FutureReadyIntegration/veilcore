from __future__ import annotations

import json
import os
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from veil.veil_organs import get_organ, list_organs


RUN_DIR = Path(os.environ.get("VEIL_RUN_DIR", "/opt/veil_os/var/run"))
LOG_DIR = Path(os.environ.get("VEIL_LOG_DIR", "/opt/veil_os/var/log"))


@dataclass(frozen=True)
class ServiceStatus:
    name: str
    running: bool
    pid: Optional[int]
    log_path: Path
    meta_path: Path


def _meta_path(name: str) -> Path:
    return RUN_DIR / f"{name}.json"


def _log_path(name: str) -> Path:
    return LOG_DIR / f"{name}.log"


def _read_meta(name: str) -> Dict:
    p = _meta_path(name)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _write_meta(name: str, meta: Dict) -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    _meta_path(name).write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def status(name: str) -> ServiceStatus:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    meta = _read_meta(name)
    pid = meta.get("pid")
    if isinstance(pid, int) and pid > 0 and _pid_alive(pid):
        return ServiceStatus(name=name, running=True, pid=pid, log_path=_log_path(name), meta_path=_meta_path(name))
    return ServiceStatus(name=name, running=False, pid=pid if isinstance(pid, int) else None, log_path=_log_path(name), meta_path=_meta_path(name))


def start(name: str, *, module: Optional[str] = None) -> ServiceStatus:
    """
    Starts an organ as a supervised subprocess.

    Default:
      python -m veil.organs.runner <name>
    Override:
      python -m <module> <name>
    """
    org = get_organ(name)
    if not org:
        raise SystemExit(f"❌ Unknown organ: {name}")

    st = status(name)
    if st.running:
        return st

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)

    logp = _log_path(name)
    logf = logp.open("a", encoding="utf-8")

    mod = module or "veil.organs.runner"

    proc = subprocess.Popen(
        ["/srv/veil_os/api_venv/bin/python", "-m", mod, name],
        stdout=logf,
        stderr=subprocess.STDOUT,
        cwd="/opt/veil_os",
        start_new_session=True,
        env={**os.environ},
    )

    _write_meta(
        name,
        {
            "name": name,
            "pid": proc.pid,
            "module": mod,
            "log_path": str(logp),
        },
    )
    return status(name)


def stop(name: str, *, force: bool = False) -> ServiceStatus:
    st = status(name)
    if not st.pid or not st.running:
        return st

    try:
        os.killpg(st.pid, signal.SIGTERM)
    except Exception:
        pass

    st2 = status(name)
    if st2.running and force:
        try:
            os.killpg(st.pid, signal.SIGKILL)
        except Exception:
            pass
        st2 = status(name)

    return st2


def list_status() -> Dict[str, ServiceStatus]:
    out: Dict[str, ServiceStatus] = {}
    for n in list_organs():
        out[n] = status(n)
    return out
