"""
Full host sensor implementation with psutil integration and smoothing.
Replace the entire file at /opt/veil_os/organs/host_sensor.py with this content.
"""

from __future__ import annotations
import time
import threading
import random
from typing import Any, Optional
from collections import deque

# Guarded import of psutil so the module still works if psutil is missing
try:
    import psutil as _psutil  # type: ignore
except Exception:
    _psutil = None

class Organ:
    """
    Host sensor that populates telemetry.metrics and security.events.
    - Uses psutil when available for real CPU/memory metrics.
    - Applies a short moving average to smooth values.
    - Keeps internal locks and bounds lists to avoid unbounded growth.
    - Designed to be resilient to runtime errors and non-writable contexts.
    """

    def __init__(self, eventbus: Optional[Any], telemetry: Any, security: Any) -> None:
        self.eventbus = eventbus
        self.telemetry = telemetry
        self.security = security
        self._running = False
        self._lock = threading.Lock()
        # smoothing windows
        self._cpu_window = deque(maxlen=5)
        self._mem_window = deque(maxlen=5)
        # psutil cpu_percent may need an initial call on some platforms
        if _psutil:
            try:
                _psutil.cpu_percent(interval=None)
            except Exception:
                pass

    def _ensure_structures(self) -> None:
        """Ensure telemetry.metrics and security.events exist and are lists."""
        try:
            if not hasattr(self.telemetry, "metrics") or not isinstance(self.telemetry.metrics, list):
                self.telemetry.metrics = []
        except Exception:
            pass
        try:
            if not hasattr(self.security, "events") or not isinstance(self.security.events, list):
                self.security.events = []
        except Exception:
            pass

    def _get_system_metrics(self) -> tuple[float, float]:
        """
        Return (cpu_percent, memory_percent).
        Uses psutil when available; otherwise returns simulated values.
        """
        if _psutil:
            try:
                cpu = round(float(_psutil.cpu_percent(interval=None)), 2)
                mem = round(float(_psutil.virtual_memory().percent), 2)
                cpu = max(0.0, min(cpu, 100.0))
                mem = max(0.0, min(mem, 100.0))
                return cpu, mem
            except Exception:
                pass
        cpu = round(random.uniform(0.1, 8.0), 2)
        mem = round(random.uniform(5.0, 90.0), 2)
        return cpu, mem

    def _emit_telemetry(self) -> None:
        """Append smoothed telemetry metrics to telemetry.metrics and publish to eventbus if present."""
        try:
            self._ensure_structures()
            ts = time.time()
            cpu, mem = self._get_system_metrics()
            # update smoothing windows
            self._cpu_window.append(cpu)
            self._mem_window.append(mem)
            avg_cpu = round(sum(self._cpu_window) / len(self._cpu_window), 2)
            avg_mem = round(sum(self._mem_window) / len(self._mem_window), 2)
            with self._lock:
                self.telemetry.metrics.append({"name": "cpu", "value": avg_cpu, "ts": ts})
                self.telemetry.metrics.append({"name": "memory", "value": avg_mem, "ts": ts})
                if len(self.telemetry.metrics) > 2000:
                    self.telemetry.metrics = self.telemetry.metrics[-2000:]
            if self.eventbus and hasattr(self.eventbus, "publish"):
                try:
                    self.eventbus.publish("host_sensor.tick", {"cpu": avg_cpu, "memory": avg_mem, "ts": ts})
                except Exception:
                    pass
        except Exception:
            return

    def _record_security_event(self) -> None:
        """Record a periodic security heartbeat event; keep list bounded."""
        try:
            self._ensure_structures()
            with self._lock:
                self.security.events.append({"source": "host_sensor", "ts": time.time(), "note": "heartbeat"})
                if len(self.security.events) > 5000:
                    self.security.events = self.security.events[-5000:]
        except Exception:
            pass

    def start(self) -> None:
        """
        Start the sensor loop. Intended to run in a daemon thread.
        Continues emitting telemetry and security heartbeats until stop() is called.
        """
        if self._running:
            return
        self._running = True
        try:
            while self._running:
                self._emit_telemetry()
                self._record_security_event()
                time.sleep(1.0)
        finally:
            self._running = False

    def stop(self) -> None:
        """Signal the loop to stop; thread will exit shortly."""
        self._running = False
