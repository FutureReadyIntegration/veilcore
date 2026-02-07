#!/usr/bin/env python3
"""
Telemetry Engine Organ - Standalone Service
"I sense. I report. I inform."
"""

import time
import signal
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

from veil.organs.telemetry_engine.telemetry import TelemetryEngine, TelemetryConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [Telemetry] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('/var/log/veil/telemetry_engine.log')]
)
log = logging.getLogger(__name__)

running = True
engine = None


def shutdown(signum, frame):
    global running
    log.info("Shutdown signal received")
    running = False


def write_status(status: dict):
    status_file = Path("/var/lib/veil/telemetry_engine/status.json")
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status["updated_at"] = datetime.utcnow().isoformat()
    status_file.write_text(json.dumps(status, indent=2))


def main():
    global running, engine
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    log.info("=" * 60)
    log.info("  TELEMETRY ENGINE - System Resource Monitoring")
    log.info("  'I sense. I report. I inform.'")
    log.info("=" * 60)
    try:
        storage_path = Path("/var/lib/veil/telemetry_engine")
        storage_path.mkdir(parents=True, exist_ok=True)
        config = TelemetryConfig()
        engine = TelemetryEngine(config)
        log.info(f"Storage: {storage_path}")
        write_status({"running": True, "healthy": True, "cpu": 0, "memory": 0, "disk": 0, "message": "Telemetry active"})
        log.info("Ready. Monitoring system resources...")
        poll_interval = config.POLL_INTERVAL_SECONDS
        last_poll = 0
        while running:
            now = time.time()
            try:
                if now - last_poll > poll_interval:
                    metrics = engine.collect_system_metrics()
                    network = engine.collect_network_stats()
                    stats = engine.get_stats()
                    log.info(f"System: CPU={metrics.cpu_percent:.1f}%, Mem={metrics.memory_percent:.1f}%, Disk={metrics.disk_percent:.1f}%")
                    write_status({"running": True, "healthy": True, "cpu": metrics.cpu_percent,
                                  "memory": metrics.memory_percent, "disk": metrics.disk_percent,
                                  "load_1m": metrics.load_avg_1m, "processes": metrics.process_count,
                                  "message": f"CPU {metrics.cpu_percent:.0f}% | Mem {metrics.memory_percent:.0f}%"})
                    last_poll = now
            except Exception as e:
                log.error(f"Error in telemetry loop: {e}")
            time.sleep(5)
        write_status({"running": False, "healthy": True, "message": "Shutdown complete"})
        log.info("Stopped.")
        return 0
    except Exception as e:
        log.error(f"Fatal error: {e}")
        write_status({"running": False, "healthy": False, "error": str(e)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
