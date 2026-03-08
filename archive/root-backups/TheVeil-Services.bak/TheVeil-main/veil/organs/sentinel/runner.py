#!/usr/bin/env python3
"""
Sentinel Organ - Standalone Service
====================================
"I watch. I learn. I protect."

Behavioral anomaly detection engine that runs as a systemd service.
Monitors user activity patterns and detects deviations.
"""

import time
import signal
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
import os

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from veil.organs.sentinel.detector import Sentinel, SentinelConfig, AnomalyType

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [Sentinel] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/veil/sentinel.log')
    ]
)
log = logging.getLogger(__name__)

running = True
sentinel = None

def shutdown(signum, frame):
    global running
    log.info("Shutdown signal received")
    running = False

def write_status(status: dict):
    """Write status file for dashboard."""
    status_file = Path("/var/lib/veil/sentinel/status.json")
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status["updated_at"] = datetime.utcnow().isoformat()
    status_file.write_text(json.dumps(status, indent=2))

def main():
    global running, sentinel
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    
    log.info("="*60)
    log.info("  SENTINEL - Behavioral Anomaly Detection")
    log.info("  'I watch. I learn. I protect.'")
    log.info("="*60)
    
    try:
        config = SentinelConfig(
            storage_path=Path("/var/lib/veil/sentinel"),
            baseline_window_days=30,
            anomaly_threshold=2.0,
        )
        
        sentinel = Sentinel(config)
        log.info(f"Storage: {config.storage_path}")
        log.info(f"Anomaly threshold: {config.anomaly_threshold} std devs")
        
        write_status({
            "running": True,
            "healthy": True,
            "alerts": 0,
            "profiles": 0,
            "message": "Monitoring active"
        })
        
        log.info("Ready. Monitoring for behavioral anomalies...")
        
        check_interval = 10  # seconds
        stats_interval = 60  # seconds
        last_stats = 0
        
        while running:
            now = time.time()
            
            # Check for alerts
            try:
                alerts = sentinel.get_alerts(unacknowledged_only=True)
                profiles = len(sentinel.profiles) if hasattr(sentinel, 'profiles') else 0
                
                if alerts:
                    for alert in alerts[:5]:
                        log.warning(f"ALERT: {alert.anomaly_type.value} - User: {alert.user_id} - Score: {alert.score:.2f}")
                
                # Periodic stats
                if now - last_stats > stats_interval:
                    log.info(f"Status: {len(alerts)} alerts, {profiles} user profiles tracked")
                    write_status({
                        "running": True,
                        "healthy": True,
                        "alerts": len(alerts),
                        "profiles": profiles,
                        "message": f"{len(alerts)} alerts, {profiles} profiles"
                    })
                    last_stats = now
                    
            except Exception as e:
                log.error(f"Error in monitoring loop: {e}")
                write_status({
                    "running": True,
                    "healthy": False,
                    "error": str(e),
                    "message": f"Error: {e}"
                })
            
            time.sleep(check_interval)
        
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
            "error": str(e),
            "message": f"Fatal: {e}"
        })
        return 1

if __name__ == "__main__":
    sys.exit(main())
