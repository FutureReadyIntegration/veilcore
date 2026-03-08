#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import os
import signal
import subprocess


DEFAULT_ORGANS_DIR = Path("/opt/veil_os/organs")
DEFAULT_LOG_DIR = Path("/opt/veil_os/var/log")

# systemd naming
# Default assumes services like: veil-sentinel.service
SYSTEMD_PREFIX = os.environ.get("VEIL_SYSTEMD_PREFIX", "veil-")


@dataclass(frozen=True)
class ServiceStatus:
    name: str
    running: bool
    pid: Optional[int]
    log: str


def _organ_dir(name: str, organs_dir: Path) -> Path:
    return organs_dir / name


def _pid_path(name: str, organs_dir: Path) -> Path:
    return _organ_dir(name, organs_dir) / "run.pid"


def _log_path(name: str, log_dir: Path) -> Path:
    return log_dir / f"{name}.log"


def _read_pid(pidfile: Path) -> Optional[int]:
    try:
        s = pidfile.read_text(encoding="utf-8").strip()
        if not s:
            return None
        return int(s)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def _pid_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # If we can't signal it, assume alive rather than lying.
        return True


def _systemd_unit_candidates(name: str) -> list[str]:
    # Try both patterns:
    #   veil-<name>.service  (default)
    #   <name>.service       (fallback)
    a = f"{SYSTEMD_PREFIX}{name}.service" if SYSTEMD_PREFIX else f"{name}.service"
    b = f"{name}.service"
    # de-dupe while preserving order
    out: list[str] = []
    for u in (a, b):
        if u not in out:
            out.append(u)
    return out


def _systemd_is_active(unit: str) -> bool:
    # systemctl is-active --quiet <unit>
    r = subprocess.run(
        ["systemctl", "is-active", "--quiet", unit],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return r.returncode == 0


def _systemd_main_pid(unit: str) -> Optional[int]:
    # systemctl show -p MainPID --value <unit>
    try:
        r = subprocess.run(
            ["systemctl", "show", "-p", "MainPID", "--value", unit],
            capture_output=True,
            text=True,
            check=False,
        )
        s = (r.stdout or "").strip()
        if not s:
            return None
        pid = int(s)
        return pid if pid > 0 else None
    except Exception:
        return None


def _systemd_status(name: str) -> tuple[bool, Optional[int]]:
    # Find first candidate unit that is active
    for unit in _systemd_unit_candidates(name):
        if _systemd_is_active(unit):
            return True, _systemd_main_pid(unit)
    return False, None


def list_services(organs_dir: Path = DEFAULT_ORGANS_DIR, log_dir: Path = DEFAULT_LOG_DIR) -> list[ServiceStatus]:
    if not organs_dir.exists():
        return []

    names = sorted([p.name for p in organs_dir.iterdir() if p.is_dir() and not p.name.startswith(".")])
    out: list[ServiceStatus] = []
    for name in names:
        out.append(status(name, organs_dir=organs_dir, log_dir=log_dir))
    return out


def status(name: str, organs_dir: Path = DEFAULT_ORGANS_DIR, log_dir: Path = DEFAULT_LOG_DIR) -> ServiceStatus:
    # 1) PID-file truth if present
    pidfile = _pid_path(name, organs_dir)
    pid = _read_pid(pidfile)
    if pid and _pid_is_alive(pid):
        return ServiceStatus(name=name, running=True, pid=pid, log=str(_log_path(name, log_dir)))

    # 2) systemd truth (Option C)
    active, spid = _systemd_status(name)
    return ServiceStatus(name=name, running=active, pid=spid, log=str(_log_path(name, log_dir)))


def start(name: str, dry_run: bool = True, organs_dir: Path = DEFAULT_ORGANS_DIR, log_dir: Path = DEFAULT_LOG_DIR) -> ServiceStatus:
    """
    Start order:
      1) If organ has run.sh, run it (legacy model).
      2) Else try systemd: systemctl start veil-<name>.service (or <name>.service)
    """
    s = status(name, organs_dir=organs_dir, log_dir=log_dir)
    if s.running:
        return s

    run_sh = _organ_dir(name, organs_dir) / "run.sh"
    if run_sh.exists():
        if dry_run:
            return ServiceStatus(name=name, running=True, pid=s.pid, log=str(_log_path(name, log_dir)))

        log_dir.mkdir(parents=True, exist_ok=True)
        organs_dir.mkdir(parents=True, exist_ok=True)

        logfile = open(_log_path(name, log_dir), "ab", buffering=0)
        p = subprocess.Popen(
            ["bash", str(run_sh)],
            stdout=logfile,
            stderr=logfile,
            cwd=str(_organ_dir(name, organs_dir)),
            start_new_session=True,
        )
        _pid_path(name, organs_dir).write_text(str(p.pid), encoding="utf-8")
        return status(name, organs_dir=organs_dir, log_dir=log_dir)

    # systemd start
    unit = _systemd_unit_candidates(name)[0]
    if dry_run:
        return ServiceStatus(name=name, running=True, pid=None, log=str(_log_path(name, log_dir)))

    subprocess.run(["systemctl", "start", unit], check=False)
    return status(name, organs_dir=organs_dir, log_dir=log_dir)


def stop(name: str, dry_run: bool = True, force: bool = False, organs_dir: Path = DEFAULT_ORGANS_DIR, log_dir: Path = DEFAULT_LOG_DIR) -> ServiceStatus:
    """
    Stop order:
      1) If we have run.pid, signal it (legacy model).
      2) Else systemd stop veil-<name>.service (or <name>.service)
    """
    s = status(name, organs_dir=organs_dir, log_dir=log_dir)

    # If PID-file exists, stop that process
    pidfile = _pid_path(name, organs_dir)
    pid = _read_pid(pidfile)
    if pid:
        if dry_run:
            return ServiceStatus(name=name, running=False, pid=pid, log=s.log)

        sig = signal.SIGKILL if force else signal.SIGTERM
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            pass

        try:
            pidfile.unlink(missing_ok=True)
        except Exception:
            pass

        return status(name, organs_dir=organs_dir, log_dir=log_dir)

    # systemd stop
    unit = _systemd_unit_candidates(name)[0]
    if dry_run:
        return ServiceStatus(name=name, running=False, pid=s.pid, log=s.log)

    subprocess.run(["systemctl", "stop", unit], check=False)
    return status(name, organs_dir=organs_dir, log_dir=log_dir)
