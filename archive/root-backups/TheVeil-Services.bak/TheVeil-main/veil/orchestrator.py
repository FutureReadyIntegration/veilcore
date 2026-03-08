#!/usr/bin/env python3
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

DEFAULT_LOG_DIR = Path("/opt/veil_os/var/log")
DEFAULT_PID_DIR = Path("/opt/veil_os/var/run")
DEFAULT_ORGANS_DIR = Path("/opt/veil_os/organs")


@dataclass(frozen=True)
class ServiceStatus:
    name: str
    running: bool
    pid: Optional[int]
    log: str
    tier: str = "—"


def _ensure_dirs() -> None:
    DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_PID_DIR.mkdir(parents=True, exist_ok=True)


def _pid_file(name: str) -> Path:
    return DEFAULT_PID_DIR / f"{name}.pid"


def _log_file(name: str) -> Path:
    return DEFAULT_LOG_DIR / f"{name}.log"


def _dry_run_env() -> bool:
    v = os.environ.get("VEIL_DRY_RUN", "").strip().lower()
    return v in ("1", "true", "yes", "y", "on")


def set_dry_run(enabled: bool) -> None:
    os.environ["VEIL_DRY_RUN"] = "1" if enabled else "0"


def _read_pid(name: str) -> Optional[int]:
    p = _pid_file(name)
    if not p.exists():
        return None
    try:
        return int(p.read_text().strip())
    except Exception:
        return None


def _process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def list_services() -> List[str]:
    """
    Discover services from /opt/veil_os/organs (folder names).
    Fallback: pidfiles.
    """
    names: List[str] = []
    if DEFAULT_ORGANS_DIR.exists() and DEFAULT_ORGANS_DIR.is_dir():
        for d in sorted(DEFAULT_ORGANS_DIR.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                names.append(d.name)
        return names

    _ensure_dirs()
    for p in sorted(DEFAULT_PID_DIR.glob("*.pid")):
        names.append(p.stem)
    return names


def status(name: str) -> ServiceStatus:
    _ensure_dirs()
    pid = _read_pid(name)
    running = bool(pid) and _process_alive(pid)

    # clean stale pid
    if pid and not running:
        try:
            _pid_file(name).unlink(missing_ok=True)
        except Exception:
            pass
        pid = None

    return ServiceStatus(
        name=name,
        running=running,
        pid=pid,
        log=str(_log_file(name)),
        tier="—",
    )


def list_statuses() -> List[ServiceStatus]:
    return [status(n) for n in list_services()]


def start(name: str, dry_run: Optional[bool] = None) -> ServiceStatus:
    """
    Compatible with:
      start(name)
      start(name, True)
      start(name, dry_run=True)
    """
    _ensure_dirs()
    if dry_run is None:
        dry_run = _dry_run_env()
    dry_run = bool(dry_run)

    if dry_run:
        fake = (os.getpid() * 1000) + (abs(hash(name)) % 900) + 100
        return ServiceStatus(name=name, running=True, pid=fake, log=str(_log_file(name)), tier="—")

    # Placeholder "real" start: mark pidfile (swap later for daemon spawn)
    pid = os.getpid()
    try:
        _pid_file(name).write_text(str(pid))
    except Exception:
        pass
    return status(name)


def stop(name: str, force: bool = False, dry_run: Optional[bool] = None) -> ServiceStatus:
    _ensure_dirs()
    if dry_run is None:
        dry_run = _dry_run_env()
    dry_run = bool(dry_run)

    s = status(name)

    if dry_run:
        return ServiceStatus(name=name, running=False, pid=s.pid, log=s.log, tier=s.tier)

    pid = s.pid
    if pid:
        try:
            os.kill(pid, 9 if force else 15)
        except Exception:
            pass

    try:
        _pid_file(name).unlink(missing_ok=True)
    except Exception:
        pass

    return status(name)
