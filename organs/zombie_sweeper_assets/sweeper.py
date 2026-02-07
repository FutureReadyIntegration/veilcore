"""
Zombie Sweeper Core Logic
=========================
Detects and cleans stale processes, sessions, and connections.
"""

import os
import time
import psutil
import logging
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from pathlib import Path

log = logging.getLogger(__name__)


class ZombieType(Enum):
    ORPHAN_PROCESS = "orphan_process"
    STALE_SESSION = "stale_session"
    DEAD_CONNECTION = "dead_connection"
    RESOURCE_LEAK = "resource_leak"


@dataclass
class SweeperConfig:
    SESSION_TIMEOUT_HOURS: int = 24
    PROCESS_TIMEOUT_HOURS: int = 48
    CONNECTION_TIMEOUT_MINUTES: int = 30
    SWEEP_INTERVAL_SECONDS: int = 300
    DRY_RUN: bool = False
    PROTECTED_PROCESSES: Set[str] = field(default_factory=lambda: {
        "systemd", "init", "kernel", "veil", "python", "uvicorn"
    })


@dataclass
class ZombieProcess:
    pid: int
    name: str
    ppid: int
    status: str
    cpu_percent: float
    memory_mb: float
    create_time: datetime
    detected_at: datetime = field(default_factory=datetime.utcnow)
    terminated: bool = False


@dataclass
class StaleSession:
    session_id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    ip_address: str
    detected_at: datetime = field(default_factory=datetime.utcnow)
    cleaned: bool = False


@dataclass
class DeadConnection:
    local_addr: str
    remote_addr: str
    status: str
    pid: Optional[int]
    detected_at: datetime = field(default_factory=datetime.utcnow)
    closed: bool = False


@dataclass
class SweepResult:
    sweep_time: datetime
    zombies_found: int
    zombies_cleaned: int
    sessions_found: int
    sessions_cleaned: int
    connections_found: int
    connections_closed: int
    errors: List[str] = field(default_factory=list)


class ZombieSweeper:
    def __init__(self, config: Optional[SweeperConfig] = None):
        self.config = config or SweeperConfig()
        self.zombie_processes: List[ZombieProcess] = []
        self.stale_sessions: List[StaleSession] = []
        self.dead_connections: List[DeadConnection] = []
        self.sweep_history: List[SweepResult] = []
        self.total_cleaned = 0
        self._session_store: Dict[str, StaleSession] = {}

    def scan_zombie_processes(self) -> List[ZombieProcess]:
        zombies = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'ppid', 'status', 'cpu_percent', 'memory_info', 'create_time']):
                try:
                    info = proc.info
                    if any(p in info['name'].lower() for p in self.config.PROTECTED_PROCESSES):
                        continue
                    is_zombie = info['status'] == psutil.STATUS_ZOMBIE
                    create_time = datetime.fromtimestamp(info['create_time'])
                    age_hours = (datetime.utcnow() - create_time).total_seconds() / 3600
                    is_orphan = info['ppid'] == 1 and age_hours > self.config.PROCESS_TIMEOUT_HOURS
                    if is_zombie or is_orphan:
                        mem_mb = info['memory_info'].rss / (1024 * 1024) if info['memory_info'] else 0
                        zombie = ZombieProcess(
                            pid=info['pid'], name=info['name'], ppid=info['ppid'],
                            status=info['status'], cpu_percent=info['cpu_percent'] or 0,
                            memory_mb=mem_mb, create_time=create_time,
                        )
                        zombies.append(zombie)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            log.error(f"Error scanning processes: {e}")
        self.zombie_processes = zombies
        return zombies

    def scan_dead_connections(self) -> List[DeadConnection]:
        dead = []
        try:
            connections = psutil.net_connections(kind='tcp')
            for conn in connections:
                if conn.status in ('CLOSE_WAIT', 'FIN_WAIT2', 'TIME_WAIT'):
                    local = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "unknown"
                    remote = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "unknown"
                    dead_conn = DeadConnection(local_addr=local, remote_addr=remote, status=conn.status, pid=conn.pid)
                    dead.append(dead_conn)
        except (psutil.AccessDenied, Exception) as e:
            log.error(f"Error scanning connections: {e}")
        self.dead_connections = dead
        return dead

    def scan_stale_sessions(self) -> List[StaleSession]:
        stale = []
        cutoff = datetime.utcnow() - timedelta(hours=self.config.SESSION_TIMEOUT_HOURS)
        for session in self._session_store.values():
            if session.last_activity < cutoff:
                session.detected_at = datetime.utcnow()
                stale.append(session)
        self.stale_sessions = stale
        return stale

    def sweep(self, clean: bool = False) -> SweepResult:
        log.info("Starting sweep...")
        zombies = self.scan_zombie_processes()
        sessions = self.scan_stale_sessions()
        connections = self.scan_dead_connections()
        zombies_cleaned = 0
        sessions_cleaned = 0
        connections_closed = 0
        errors = []
        if clean and not self.config.DRY_RUN:
            for zombie in zombies:
                try:
                    proc = psutil.Process(zombie.pid)
                    proc.terminate()
                    zombie.terminated = True
                    zombies_cleaned += 1
                    log.info(f"Terminated zombie process: {zombie.pid} ({zombie.name})")
                except Exception as e:
                    errors.append(f"Failed to terminate {zombie.pid}: {e}")
            for session in sessions:
                try:
                    del self._session_store[session.session_id]
                    session.cleaned = True
                    sessions_cleaned += 1
                except Exception as e:
                    errors.append(f"Failed to clean session {session.session_id}: {e}")
        result = SweepResult(
            sweep_time=datetime.utcnow(), zombies_found=len(zombies), zombies_cleaned=zombies_cleaned,
            sessions_found=len(sessions), sessions_cleaned=sessions_cleaned,
            connections_found=len(connections), connections_closed=connections_closed, errors=errors,
        )
        self.sweep_history.append(result)
        self.total_cleaned += zombies_cleaned + sessions_cleaned
        log.info(f"Sweep complete: {len(zombies)} zombies, {len(sessions)} stale sessions, {len(connections)} dead connections")
        return result

    def get_stats(self) -> Dict:
        return {
            "zombie_processes": len(self.zombie_processes),
            "stale_sessions": len(self.stale_sessions),
            "dead_connections": len(self.dead_connections),
            "total_cleaned": self.total_cleaned,
            "sweeps_performed": len(self.sweep_history),
            "tracked_sessions": len(self._session_store),
        }
