#!/usr/bin/env python3
"""
Generic Veil organ runner.

Runs a module that exposes:
  - ORGAN_NAME: str (optional)
  - run(stop_event, log, state_dir): function (required)

The organ's run() should block until stop_event is set.
"""
import importlib
import json
import logging
import os
import signal
import sys
import time
from pathlib import Path
from datetime import datetime
import threading

def safe_file_handler(path: str):
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        return logging.FileHandler(path)
    except Exception:
        try:
            return logging.FileHandler("/tmp/veilcore-organs.log")
        except Exception:
            return None

def main():
    if len(sys.argv) != 2:
        print("Usage: python -m veil.organ_runner_generic <module.path>", file=sys.stderr)
        return 2

    mod_path = sys.argv[1]

    # Logging
    handlers = [logging.StreamHandler()]
    fh = safe_file_handler("/var/log/veil/veilcore-organs.log")
    if fh:
        handlers.append(fh)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [VeilCore] %(levelname)s: %(message)s",
        handlers=handlers
    )
    log = logging.getLogger("veilcore")

    stop_event = threading.Event()

    def _shutdown(signum, frame):
        log.info("Shutdown signal received")
        stop_event.set()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    # Import organ module
    try:
        organ_mod = importlib.import_module(mod_path)
    except Exception as e:
        log.exception(f"Failed to import organ module {mod_path}: {e}")
        return 1

    organ_name = getattr(organ_mod, "ORGAN_NAME", mod_path.split(".")[-2] if "." in mod_path else mod_path)

    # State directory for organ
    state_dir = Path(f"/var/lib/veil/{organ_name}")
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        # fallback
        state_dir = Path(f"/tmp/veil-{organ_name}")
        state_dir.mkdir(parents=True, exist_ok=True)

    status_file = state_dir / "status.json"

    def write_status(**fields):
        payload = {
            "name": organ_name,
            "updated_at": datetime.utcnow().isoformat(),
            **fields
        }
        try:
            status_file.write_text(json.dumps(payload, indent=2))
        except Exception:
            pass

    log.info(f"Starting organ: {organ_name} ({mod_path})")
    write_status(status="starting", healthy=True)

    run_fn = getattr(organ_mod, "run", None)
    if not callable(run_fn):
        log.error(f"{mod_path} does not define a callable run(stop_event, log, state_dir)")
        write_status(status="error", healthy=False, error="missing run()")
        return 1

    # Run organ (must block until stop_event is set)
    try:
        write_status(status="running", healthy=True, pid=os.getpid())
        run_fn(stop_event=stop_event, log=log, state_dir=state_dir)
        write_status(status="stopped", healthy=True)
        log.info("Stopped.")
        os._exit(0)
    except Exception as e:
        log.exception(f"Fatal error in organ {organ_name}: {e}")
        write_status(status="fatal", healthy=False, error=str(e))
        return 1

if __name__ == "__main__":
    sys.exit(main())
