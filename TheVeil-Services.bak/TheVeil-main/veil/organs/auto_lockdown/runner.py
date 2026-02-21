#!/usr/bin/env python3
"""
Auto-Lockdown Engine - Standalone Service
==========================================
"Swift response. Measured force."

Automated threat response with graduated escalation.
"""

import time
import signal
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
import os

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from veil.organs.auto_lockdown.engine import (
    AutoLockdown, AutoLockdownConfig, ResponseLevel
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [AutoLockdown] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/veil/auto_lockdown.log')
    ]
)
log = logging.getLogger(__name__)

running = True
engine = None

def shutdown(signum, frame):
    global running
    log.info("Shutdown signal received")
    running = False

def write_status(status: dict):
    status_file = Path("/var/lib/veil/lockdown/status.json")
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status["updated_at"] = datetime.utcnow().isoformat()
    status_file.write_text(json.dumps(status, indent=2))

def main():
    global running, engine
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    
    log.info("="*60)
    log.info("  AUTO-LOCKDOWN ENGINE")
    log.info("  'Swift response. Measured force.'")
    log.info("="*60)
    
    try:
        config = AutoLockdownConfig(
            storage_path=Path("/var/lib/veil/lockdown"),
            warning_threshold=30,
            restriction_threshold=50,
            suspension_threshold=70,
            lockdown_threshold=90,
        )
        
        engine = AutoLockdown(config)
        log.info(f"Storage: {config.storage_path}")
        log.info(f"Thresholds: warn={config.warning_threshold}, "
                f"restrict={config.restriction_threshold}, "
                f"suspend={config.suspension_threshold}, "
                f"lockdown={config.lockdown_threshold}")
        
        write_status({
            "running": True,
            "healthy": True,
            "active_lockdowns": 0,
            "actions_taken": 0,
            "message": "Ready"
        })
        
        log.info("Ready. Awaiting threat events...")
        
        check_interval = 5  # Check more frequently for response
        stats_interval = 60
        last_stats = 0
        
        while running:
            now = time.time()
            
            try:
                lockdowns = engine.get_active_lockdowns()
                expired = engine.check_expirations()
                
                if expired:
                    for ld in expired:
                        log.info(f"Lockdown expired: {ld.target_type}:{ld.target_id}")
                
                if now - last_stats > stats_interval:
                    log.info(f"Status: {len(lockdowns)} active lockdowns")
                    for ld in lockdowns:
                        log.info(f"  - {ld.target_type}:{ld.target_id} @ {ld.level.value}")
                    
                    write_status({
                        "running": True,
                        "healthy": True,
                        "active_lockdowns": len(lockdowns),
                        "message": f"{len(lockdowns)} active lockdowns"
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
        os._exit(0)

        return 0
        
    except Exception as e:
        log.error(f"Fatal error: {e}")
        write_status({"running": False, "healthy": False, "error": str(e)})
        return 1

if __name__ == "__main__":
    sys.exit(main())
