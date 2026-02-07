#!/usr/bin/env python3
"""
Zero-Trust Engine - Standalone Service
======================================
"Never trust. Always verify."

Continuous verification, device posture assessment, context-aware access.
"""

import time
import signal
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from veil.organs.zero_trust.engine import (
    ZeroTrust, ZeroTrustConfig, TrustLevel, DevicePosture
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [ZeroTrust] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/veil/zero_trust.log')
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
    status_file = Path("/var/lib/veil/zero_trust/status.json")
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status["updated_at"] = datetime.utcnow().isoformat()
    status_file.write_text(json.dumps(status, indent=2))

def main():
    global running, engine
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    
    log.info("="*60)
    log.info("  ZERO-TRUST ENGINE")
    log.info("  'Never trust. Always verify.'")
    log.info("="*60)
    
    try:
        config = ZeroTrustConfig(
            storage_path=Path("/var/lib/veil/zero_trust"),
            session_timeout=3600,
            max_trust_level=TrustLevel.HIGH,
            require_device_compliance=True,
        )
        
        engine = ZeroTrust(config)
        log.info(f"Storage: {config.storage_path}")
        log.info(f"Session timeout: {config.session_timeout}s")
        log.info(f"Device compliance required: {config.require_device_compliance}")
        
        write_status({
            "running": True,
            "healthy": True,
            "active_sessions": 0,
            "devices_registered": 0,
            "denials": 0,
            "message": "Enforcing"
        })
        
        log.info("Ready. Enforcing zero-trust policies...")
        
        check_interval = 10
        stats_interval = 60
        last_stats = 0
        
        while running:
            now = time.time()
            
            try:
                # Cleanup expired sessions
                expired = engine.cleanup_expired_sessions()
                if expired:
                    log.info(f"Cleaned up {expired} expired sessions")
                
                sessions = len(engine.sessions) if hasattr(engine, 'sessions') else 0
                devices = len(engine.devices) if hasattr(engine, 'devices') else 0
                
                if now - last_stats > stats_interval:
                    log.info(f"Status: {sessions} sessions, {devices} devices")
                    write_status({
                        "running": True,
                        "healthy": True,
                        "active_sessions": sessions,
                        "devices_registered": devices,
                        "message": f"{sessions} sessions, {devices} devices"
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
