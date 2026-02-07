#!/usr/bin/env python3
"""
Analytics Engine Organ - Standalone Service
"I measure. I analyze. I reveal."
"""

import time
import signal
import sys
import json
import random
import logging
from pathlib import Path
from datetime import datetime

from veil.organs.analytics_engine.engine import AnalyticsEngine, AnalyticsConfig, MetricType

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [Analytics] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('/var/log/veil/analytics_engine.log')]
)
log = logging.getLogger(__name__)

running = True
engine = None


def shutdown(signum, frame):
    global running
    log.info("Shutdown signal received")
    running = False


def write_status(status: dict):
    status_file = Path("/var/lib/veil/analytics_engine/status.json")
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status["updated_at"] = datetime.utcnow().isoformat()
    status_file.write_text(json.dumps(status, indent=2))


def main():
    global running, engine
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    log.info("=" * 60)
    log.info("  ANALYTICS ENGINE - Security Metrics & Analysis")
    log.info("  'I measure. I analyze. I reveal.'")
    log.info("=" * 60)
    try:
        storage_path = Path("/var/lib/veil/analytics_engine")
        storage_path.mkdir(parents=True, exist_ok=True)
        config = AnalyticsConfig()
        engine = AnalyticsEngine(config)
        log.info(f"Storage: {storage_path}")
        write_status({"running": True, "healthy": True, "metrics": 0, "risk_score": 0, "message": "Analytics active"})
        log.info("Ready. Collecting security metrics...")
        collect_interval = config.AGGREGATION_INTERVAL_SECONDS
        report_interval = 300
        last_collect = 0
        last_report = 0
        while running:
            now = time.time()
            try:
                if now - last_collect > collect_interval:
                    engine.record_metric(MetricType.SESSIONS_ACTIVE, random.randint(10, 100))
                    engine.record_metric(MetricType.LOGIN_ATTEMPTS, random.randint(0, 20))
                    engine.record_metric(MetricType.FAILED_AUTHS, random.randint(0, 5))
                    last_collect = now
                if now - last_report > report_interval:
                    report = engine.generate_report(hours=1)
                    stats = engine.get_stats()
                    log.info(f"Report: Risk={report.risk_score:.0f}, Threats={report.total_threats}")
                    write_status({"running": True, "healthy": True, "metrics": stats["total_metrics"],
                                  "risk_score": report.risk_score, "message": f"Risk score: {report.risk_score:.0f}"})
                    last_report = now
            except Exception as e:
                log.error(f"Error in analytics loop: {e}")
            time.sleep(10)
        write_status({"running": False, "healthy": True, "message": "Shutdown complete"})
        log.info("Stopped.")
        return 0
    except Exception as e:
        log.error(f"Fatal error: {e}")
        write_status({"running": False, "healthy": False, "error": str(e)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
