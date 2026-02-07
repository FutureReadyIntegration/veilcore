#!/usr/bin/env python3
"""
Insider Threat Detector - Standalone Service
=============================================
"Trust, but verify. Then verify again."

Detects privilege abuse, data exfiltration, and credential anomalies.
"""

import time
import signal
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from veil.organs.insider_threat.detector import (
    InsiderThreatDetector, InsiderThreatConfig, ThreatIndicator
)

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

def shutdown(signum, frame):
    global running
    log.info("Shutdown signal received")
    running = False

def write_status(status: dict):
    status_file = Path("/var/lib/veil/insider_threat/status.json")
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status["updated_at"] = datetime.utcnow().isoformat()
    status_file.write_text(json.dumps(status, indent=2))

def main():
    global running, detector
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    
    log.info("="*60)
    log.info("  INSIDER THREAT DETECTOR")
    log.info("  'Trust, but verify. Then verify again.'")
    log.info("="*60)
    
    try:
        config = InsiderThreatConfig(
            storage_path=Path("/var/lib/veil/insider_threat"),
            baseline_days=30,
            mass_access_threshold=100,
            after_hours_start=22,
            after_hours_end=6,
        )
        
        detector = InsiderThreatDetector(config)
        log.info(f"Storage: {config.storage_path}")
        log.info(f"Mass access threshold: {config.mass_access_threshold} records/hour")
        log.info(f"After hours: {config.after_hours_start}:00 - {config.after_hours_end}:00")
        
        write_status({
            "running": True,
            "healthy": True,
            "alerts": 0,
            "high_risk_users": 0,
            "message": "Monitoring active"
        })
        
        log.info("Ready. Monitoring for insider threats...")
        
        check_interval = 10
        stats_interval = 60
        last_stats = 0
        
        while running:
            now = time.time()
            
            try:
                alerts = detector.get_alerts(unresolved_only=True)
                high_risk = [a for a in alerts if a.risk_score >= 70]
                
                if high_risk:
                    for alert in high_risk[:5]:
                        log.warning(
                            f"HIGH RISK: {alert.indicator.value} - "
                            f"User: {alert.user_id} - Risk: {alert.risk_score}"
                        )
                
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
        
        write_status({"running": False, "healthy": True, "message": "Shutdown complete"})
        log.info("Stopped.")
        return 0
        
    except Exception as e:
        log.error(f"Fatal error: {e}")
        write_status({"running": False, "healthy": False, "error": str(e)})
        return 1

if __name__ == "__main__":
    sys.exit(main())
