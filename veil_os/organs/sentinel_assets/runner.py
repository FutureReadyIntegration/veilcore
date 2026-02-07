#!/usr/bin/env python3
"""
Sentinel Organ - Standalone Service
"I watch. I learn. I protect."
"""

import time
import signal
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

from veil.organs.sentinel.detector import Sentinel, SentinelConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [Sentinel] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('/var/log/veil/sentinel.log')]
)
log = logging.getLogger(__name__)

running = True
sentinel = None

def shutdown(signum, frame):
    global running
    log.info("Shutdown signal received")
    running = False

def write_status(status: dict):
    status_file = Path("/var/lib/veil/sentinel/status.json")
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status["updated_at"] = datetime.utcnow().isoformat()
    status_file.write_text(json.dumps(status, indent=2))

def main():
    global running, sentinel
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    log.info("=" * 60)
    log.info("  SENTINEL - Behavioral Anomaly Detection")
    log.info("  'I watch. I learn. I protect.'")
    log.info("=" * 60)

    try:
        storage_path = Path("/var/lib/veil/sentinel")
        storage_path.mkdir(parents=True, exist_ok=True)

        config = SentinelConfig()
        sentinel = Sentinel()

        log.info(f"Storage: {storage_path}")
        log.info(f"Anomaly threshold: {config.ANOMALY_THRESHOLD} std devs")

        write_status({"running": True, "healthy": True, "alerts": 0, "profiles": 0, "message": "Monitoring active"})
        log.info("Ready. Monitoring for behavioral anomalies...")

        check_interval = 10
        stats_interval = 60
        last_stats = 0

        while running:
            now = time.time()
            try:
                alerts = sentinel.get_alerts(unresolved_only=True) if hasattr(sentinel, 'get_alerts') else []
                alerts = alerts or []
                profiles = len(sentinel.profiles) if hasattr(sentinel, 'profiles') else 0

                if alerts:
                    for alert in alerts[:5]:
                        log.warning(f"ALERT: {alert.anomaly_type.value} - User: {alert.user_id} - Score: {alert.score:.2f}")

                if now - last_stats > stats_interval:
                    log.info(f"Status: {len(alerts)} alerts, {profiles} profiles")
                    write_status({"running": True, "healthy": True, "alerts": len(alerts), "profiles": profiles, "message": f"{len(alerts)} alerts, {profiles} profiles"})
                    last_stats = now

            except Exception as e:
                log.error(f"Error in loop: {e}")

            time.sleep(check_interval)

        write_status({"running": False, "healthy": True, "message": "Shutdown complete"})
        log.info("Stopped.")
        return 0

    except Exception as e:
        log.error(f"Fatal error: {e}")
        write_status({"running": False, "healthy": False, "error": str(e)})
        return 1

if __name__ == "__main__":
    sys.exit(main())
