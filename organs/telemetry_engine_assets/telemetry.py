"""
Telemetry Engine Core Logic
"""

import psutil
import logging
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional

log = logging.getLogger(__name__)


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class TelemetryConfig:
    POLL_INTERVAL_SECONDS: int = 30
    CPU_WARNING_PERCENT: float = 80.0
    CPU_CRITICAL_PERCENT: float = 95.0
    MEMORY_WARNING_PERCENT: float = 80.0
    MEMORY_CRITICAL_PERCENT: float = 95.0
    DISK_WARNING_PERCENT: float = 85.0
    DISK_CRITICAL_PERCENT: float = 95.0


@dataclass
class SystemMetrics:
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    load_avg_1m: float
    load_avg_5m: float
    load_avg_15m: float
    process_count: int
    uptime_seconds: float


@dataclass
class ServiceHealth:
    name: str
    running: bool
    pid: Optional[int]
    cpu_percent: float
    memory_mb: float
    checked_at: datetime


@dataclass
class NetworkStats:
    timestamp: datetime
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    errors_in: int
    errors_out: int
    connections_active: int


@dataclass
class ResourceAlert:
    alert_type: str
    level: AlertLevel
    message: str
    value: float
    threshold: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


class TelemetryEngine:
    def __init__(self, config: Optional[TelemetryConfig] = None):
        self.config = config or TelemetryConfig()
        self._metrics_history: List[SystemMetrics] = []
        self._network_history: List[NetworkStats] = []
        self._alerts: List[ResourceAlert] = []
        self._services: Dict[str, ServiceHealth] = {}
        self._boot_time = psutil.boot_time()

    def collect_system_metrics(self) -> SystemMetrics:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        load = psutil.getloadavg()
        metrics = SystemMetrics(
            timestamp=datetime.utcnow(), cpu_percent=cpu, memory_percent=mem.percent,
            memory_used_gb=mem.used / (1024**3), memory_total_gb=mem.total / (1024**3),
            disk_percent=disk.percent, disk_used_gb=disk.used / (1024**3), disk_total_gb=disk.total / (1024**3),
            load_avg_1m=load[0], load_avg_5m=load[1], load_avg_15m=load[2],
            process_count=len(psutil.pids()), uptime_seconds=datetime.utcnow().timestamp() - self._boot_time,
        )
        self._metrics_history.append(metrics)
        if len(self._metrics_history) > 1000:
            self._metrics_history = self._metrics_history[-1000:]
        self._check_thresholds(metrics)
        return metrics

    def collect_network_stats(self) -> NetworkStats:
        net = psutil.net_io_counters()
        conns = len(psutil.net_connections())
        stats = NetworkStats(
            timestamp=datetime.utcnow(), bytes_sent=net.bytes_sent, bytes_recv=net.bytes_recv,
            packets_sent=net.packets_sent, packets_recv=net.packets_recv,
            errors_in=net.errin, errors_out=net.errout, connections_active=conns,
        )
        self._network_history.append(stats)
        if len(self._network_history) > 1000:
            self._network_history = self._network_history[-1000:]
        return stats

    def _check_thresholds(self, metrics: SystemMetrics):
        if metrics.cpu_percent >= self.config.CPU_CRITICAL_PERCENT:
            self._add_alert("cpu", AlertLevel.CRITICAL, f"CPU at {metrics.cpu_percent:.1f}%", metrics.cpu_percent, self.config.CPU_CRITICAL_PERCENT)
        elif metrics.cpu_percent >= self.config.CPU_WARNING_PERCENT:
            self._add_alert("cpu", AlertLevel.WARNING, f"CPU at {metrics.cpu_percent:.1f}%", metrics.cpu_percent, self.config.CPU_WARNING_PERCENT)
        if metrics.memory_percent >= self.config.MEMORY_CRITICAL_PERCENT:
            self._add_alert("memory", AlertLevel.CRITICAL, f"Memory at {metrics.memory_percent:.1f}%", metrics.memory_percent, self.config.MEMORY_CRITICAL_PERCENT)
        elif metrics.memory_percent >= self.config.MEMORY_WARNING_PERCENT:
            self._add_alert("memory", AlertLevel.WARNING, f"Memory at {metrics.memory_percent:.1f}%", metrics.memory_percent, self.config.MEMORY_WARNING_PERCENT)
        if metrics.disk_percent >= self.config.DISK_CRITICAL_PERCENT:
            self._add_alert("disk", AlertLevel.CRITICAL, f"Disk at {metrics.disk_percent:.1f}%", metrics.disk_percent, self.config.DISK_CRITICAL_PERCENT)
        elif metrics.disk_percent >= self.config.DISK_WARNING_PERCENT:
            self._add_alert("disk", AlertLevel.WARNING, f"Disk at {metrics.disk_percent:.1f}%", metrics.disk_percent, self.config.DISK_WARNING_PERCENT)

    def _add_alert(self, alert_type: str, level: AlertLevel, message: str, value: float, threshold: float):
        alert = ResourceAlert(alert_type=alert_type, level=level, message=message, value=value, threshold=threshold)
        self._alerts.append(alert)
        log.warning(f"ALERT [{level.value}]: {message}")

    def get_alerts(self, level: AlertLevel = None) -> List[ResourceAlert]:
        if level:
            return [a for a in self._alerts if a.level == level]
        return self._alerts

    def clear_alerts(self):
        self._alerts = []

    def get_stats(self) -> Dict:
        latest = self._metrics_history[-1] if self._metrics_history else None
        return {"cpu_percent": latest.cpu_percent if latest else 0, "memory_percent": latest.memory_percent if latest else 0,
                "disk_percent": latest.disk_percent if latest else 0, "alerts_count": len(self._alerts),
                "samples_collected": len(self._metrics_history), "services_tracked": len(self._services)}
