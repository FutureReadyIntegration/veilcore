import time
import json
import socket
from datetime import datetime

try:
    import psutil
except ImportError:
    psutil = None

from veil.organ_base import OrganBase, OrganConfig
from veil.hybrid import organ_display_name


class TelemetryOrgan(OrganBase):
    """
    Hybrid telemetry organ:
    - System metrics (CPU, memory, disk, load, uptime, network)
    - Organ health aggregation (placeholder, ready to wire)
    - Event-based telemetry (threshold crossings)
    - JSON payloads ready for dashboards
    - Configurable intervals via config
    """

    def __init__(self, config: OrganConfig):
        super().__init__(config)

        self.display = organ_display_name(self.config.name)

        # Configurable intervals (seconds)
        self.system_interval = getattr(self.config, "system_interval", 30)
        self.organ_interval = getattr(self.config, "organ_interval", 60)
        self.event_interval = getattr(self.config, "event_interval", 15)

        # Thresholds for event-based telemetry
        self.cpu_warn_threshold = getattr(self.config, "cpu_warn_threshold", 75.0)
        self.cpu_crit_threshold = getattr(self.config, "cpu_crit_threshold", 90.0)
        self.mem_warn_threshold = getattr(self.config, "mem_warn_threshold", 75.0)
        self.mem_crit_threshold = getattr(self.config, "mem_crit_threshold", 90.0)

        # Internal state
        self._last_system_heartbeat = 0.0
        self._last_organ_heartbeat = 0.0
        self._last_event_scan = 0.0

        # Host identity
        self.hostname = socket.gethostname()

    def run(self):
        self.start_health_loop()
        self.logger.info("%s online. Hybrid telemetry subsystem active.", self.display)

        while not self.killer.stop:
            now = time.time()

            if now - self._last_system_heartbeat >= self.system_interval:
                self._emit_system_telemetry()
                self._last_system_heartbeat = now

            if now - self._last_organ_heartbeat >= self.organ_interval:
                self._emit_organ_telemetry()
                self._last_organ_heartbeat = now

            if now - self._last_event_scan >= self.event_interval:
                self._emit_event_telemetry()
                self._last_event_scan = now

            time.sleep(1)

    # -------------------------
    # System metrics telemetry
    # -------------------------

    def _emit_system_telemetry(self):
        payload = {
            "type": "system_telemetry",
            "timestamp": self._now_iso(),
            "host": self.hostname,
            "organ": self.config.name,
            "metrics": {}
        }

        if psutil is None:
            payload["metrics"]["psutil_available"] = False
            self.logger.warning(
                "%s: psutil not available; system metrics limited.",
                self.display
            )
        else:
            payload["metrics"]["psutil_available"] = True

            try:
                payload["metrics"]["cpu_percent"] = psutil.cpu_percent(interval=None)

                vm = psutil.virtual_memory()
                payload["metrics"]["memory_percent"] = vm.percent
                payload["metrics"]["memory_used"] = vm.used
                payload["metrics"]["memory_total"] = vm.total

                du = psutil.disk_usage("/")
                payload["metrics"]["disk_percent"] = du.percent
                payload["metrics"]["disk_used"] = du.used
                payload["metrics"]["disk_total"] = du.total

                try:
                    load1, load5, load15 = psutil.getloadavg()
                    payload["metrics"]["load_1"] = load1
                    payload["metrics"]["load_5"] = load5
                    payload["metrics"]["load_15"] = load15
                except (AttributeError, OSError):
                    payload["metrics"]["load_1"] = None
                    payload["metrics"]["load_5"] = None
                    payload["metrics"]["load_15"] = None

                boot_time = psutil.boot_time()
                payload["metrics"]["uptime_seconds"] = int(time.time() - boot_time)

                net = psutil.net_io_counters()
                payload["metrics"]["net_bytes_sent"] = net.bytes_sent
                payload["metrics"]["net_bytes_recv"] = net.bytes_recv

            except Exception as e:
                self.logger.exception(
                    "%s: error collecting system metrics: %s",
                    self.display,
                    e
                )

        self._log_json("system_telemetry", payload)

    # -------------------------
    # Organ health telemetry
    # -------------------------

    def _emit_organ_telemetry(self):
        payload = {
            "type": "organ_telemetry",
            "timestamp": self._now_iso(),
            "host": self.hostname,
            "organ": self.config.name,
            "cluster": {
                "status": "unknown",
                "organs": []
            }
        }

        self._log_json("organ_telemetry", payload)

    # -------------------------
    # Event-based telemetry
    # -------------------------

    def _emit_event_telemetry(self):
        if psutil is None:
            return

        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
        except Exception as e:
            self.logger.exception(
                "%s: error collecting event metrics: %s",
                self.display,
                e
            )
            return

        events = []

        if cpu >= self.cpu_crit_threshold:
            events.append(self._build_event(
                category="cpu",
                severity="critical",
                message=f"CPU usage {cpu:.1f}% >= critical threshold {self.cpu_crit_threshold:.1f}%"
            ))
        elif cpu >= self.cpu_warn_threshold:
            events.append(self._build_event(
                category="cpu",
                severity="warning",
                message=f"CPU usage {cpu:.1f}% >= warning threshold {self.cpu_warn_threshold:.1f}%"
            ))

        if mem >= self.mem_crit_threshold:
            events.append(self._build_event(
                category="memory",
                severity="critical",
                message=f"Memory usage {mem:.1f}% >= critical threshold {self.mem_crit_threshold:.1f}%"
            ))
        elif mem >= self.mem_warn_threshold:
            events.append(self._build_event(
                category="memory",
                severity="warning",
                message=f"Memory usage {mem:.1f}% >= warning threshold {self.mem_warn_threshold:.1f}%"
            ))

        if not events:
            return

        payload = {
            "type": "event_telemetry",
            "timestamp": self._now_iso(),
            "host": self.hostname,
            "organ": self.config.name,
            "events": events
        }

        self._log_json("event_telemetry", payload)

    def _build_event(self, category: str, severity: str, message: str) -> dict:
        return {
            "timestamp": self._now_iso(),
            "category": category,
            "severity": severity,
            "message": message
        }

    # -------------------------
    # Helpers
    # -------------------------

    def _now_iso(self) -> str:
        return datetime.utcnow().isoformat() + "Z"

    def _log_json(self, label: str, payload: dict):
        try:
            text = json.dumps(payload, sort_keys=True)
        except Exception as e:
            self.logger.exception(
                "%s: error serializing %s payload: %s",
                self.display,
                label,
                e
            )
            return

        self.logger.info("%s: %s", self.display, text)


def create_organ(config: OrganConfig) -> TelemetryOrgan:
    return TelemetryOrgan(config)
