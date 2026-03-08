#!/usr/bin/env python3
"""
Zombie Sweeper Organ - Standalone Service
"I hunt the dead. I clean the forgotten."
"""

import time
import signal
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
import os

from veil.organs.zombie_sweeper.sweeper import ZombieSweeper, SweeperConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [ZombieSweeper] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('/var/log/veil/zombie_sweeper.log')]
)
log = logging.getLogger(__name__)

running = True
sweeper = None


def shutdown(signum, frame):
    global running
    log.info("Shutdown signal received")
    running = False


def write_status(status: dict):
    status_file = Path("/var/lib/veil/zombie_sweeper/status.json")
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status["updated_at"] = datetime.utcnow().isoformat()
    status_file.write_text(json.dumps(status, indent=2))


def main():
    global running, sweeper
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    log.info("=" * 60)
    log.info("  ZOMBIE SWEEPER - Resource Cleanup Engine")
    log.info("  'I hunt the dead. I clean the forgotten.'")
    log.info("=" * 60)
    try:
        storage_path = Path("/var/lib/veil/zombie_sweeper")
        storage_path.mkdir(parents=True, exist_ok=True)
        config = SweeperConfig()
        sweeper = ZombieSweeper(config)
        log.info(f"Storage: {storage_path}")
        log.info(f"Sweep interval: {config.SWEEP_INTERVAL_SECONDS}s")
        write_status({"running": True, "healthy": True, "zombies": 0, "cleaned": 0, "message": "Sweeper active"})
        log.info("Ready. Hunting for zombies...")
        sweep_interval = config.SWEEP_INTERVAL_SECONDS
        last_sweep = 0
        while running:
            now = time.time()
            try:
                if now - last_sweep > sweep_interval:
                    result = sweeper.sweep(clean=True)
                    stats = sweeper.get_stats()
                    log.info(f"Sweep: {result.zombies_found} zombies, {result.sessions_found} stale sessions")
                    write_status({
                        "running": True, "healthy": True,
                        "zombies": stats["zombie_processes"],
                        "total_cleaned": stats["total_cleaned"],
                        "message": f"Cleaned {stats['total_cleaned']} total"
                    })
                    last_sweep = now
            except Exception as e:
                log.error(f"Error in sweep loop: {e}")
            time.sleep(10)
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
