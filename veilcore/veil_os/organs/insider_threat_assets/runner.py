#!/usr/bin/env python3
"""
Insider Threat Detector - Standalone Service
"Trust, but verify. Then verify again."
"""

import time
import signal
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
import os

from veil.organs.insider_threat.detector import (
    InsiderThreatDetector,
    InsiderThreatConfig
)

# ---------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [InsiderThreat] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/veil/insider_threat.log')
    ]
)
log = logging.getLogger(__name__)

running = True
detector = None


# ---------------------------------------------------------
# Graceful Shutdown Handler
# ---------------------------------------------------------
def shutdown(signum, frame):
    global running
    log.info("Shutdown signal received")
    running = False


# ---------------------------------------------------------
# Status Writer
# ---------------------------------------------------------
def write_status(status: dict):
    status_file = Path("/var/lib/veil/insider_threat/status.json")
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status["updated_at"] = datetime.utcnow().isoformat()
    status_file.write_text(json.dumps(status, indent=2))


# ---------------------------------------------------------
# Main Service Loop
# ---------------------------------------------------------
def main():
    global running, detector

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    log.info("=" * 60)
    log.info("  INSIDER THREAT DETECTOR")
    log.info("  'Trust, but verify. Then verify again.'")
    log.info("=" * 60)

    try:
        # Ensure storage directory exists
        storage_path = Path("/var/lib/veil/insider_threat")
        storage_path.mkdir(parents=True, exist_ok=True)

        # -------------------------------------------------
        # CONFIG + DETECTOR INITIALIZATION (NO ARGS)
        # -------------------------------------------------
        config = InsiderThreatConfig()
        detector = InsiderThreatDetector(config)

        log.info(f"Storage: {storage_path}")
        log.info(f"Analysis window: {getattr(config, 'ANALYSIS_WINDOW_HOURS', 'N/A')} hours")
        log.info(f"Risk threshold: {getattr(config, 'HIGH_RISK_THRESHOLD', 'N/A')}")

        write_status({
            "running": True,
            "healthy": True,
            "alerts": 0,
            "high_risk_users": 0,
            "message": "Monitoring active"
        })

        log.info("Ready. Monitoring for insider threats...")

        # -------------------------------------------------
        # LOOP SETTINGS
        # -------------------------------------------------
        check_interval = 10
        stats_interval = 60
        last_stats = 0

        # -------------------------------------------------
        # MAIN LOOP
        # -------------------------------------------------
        while running:
            now = time.time()

            try:
                alerts = detector.get_alerts(unresolved_only=True)
                high_risk = [
                    a for a in alerts
                    if hasattr(a, "score") and a.score >= getattr(config, "HIGH_RISK_THRESHOLD", 70)
                ]

                # Log high-risk alerts
                for alert in high_risk[:5]:
                    log.warning(
                        f"HIGH RISK: User {alert.user_id} - Risk: {alert.score}"
                    )

                # Periodic status update
                if now - last_stats > stats_interval:
                    log.info(f"Status: {len(alerts)} alerts, {len(high_risk)} high-risk")

                    write_status({
                        "running": True,
                        "healthy": True,
                        "alerts": len(alerts),
                        "high_risk_users": len(high_risk),
                        "message": f"{len(alerts)} alerts, {len(high_risk)} high-risk"
                    })

                    last_stats = now

            except Exception as e:
                log.error(f"Error in monitoring loop: {e}")
                write_status({
                    "running": True,
                    "healthy": False,
                    "error": str(e)
                })

            time.sleep(check_interval)

        # Shutdown complete
        write_status({
            "running": False,
            "healthy": True,
            "message": "Shutdown complete"
        })
        log.info("Stopped.")
        os._exit(0)

        return 0

    except Exception as e:
        log.error(f"Fatal error: {e}")
        write_status({
            "running": False,
            "healthy": False,
            "error": str(e)
        })
        return 1


if __name__ == "__main__":
    sys.exit(main())
