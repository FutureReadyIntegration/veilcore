from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone

from veil.core.eventbus import EventBus, Event
from veil.veil_organs import get_organ, label


def main() -> None:
    ap = argparse.ArgumentParser(description="Veil Organ Service Runner")
    ap.add_argument("name", help="Organ name")
    ap.add_argument("--interval", type=float, default=5.0, help="Heartbeat interval seconds")
    args = ap.parse_args()

    org = get_organ(args.name)
    if not org:
        raise SystemExit(f"❌ Unknown organ: {args.name}")

    bus = EventBus()

    print(f"🫀 START organ={label(args.name)} ts={datetime.now(timezone.utc).isoformat()}")
    bus.emit(Event(prefix="organ", name="start", payload={"name": args.name, "tier": org.get("tier")}))

    # Minimal “service” loop (hospital-safe baseline): heartbeat + status
    try:
        while True:
            bus.emit(
                Event(
                    prefix="organ",
                    name="heartbeat",
                    payload={"name": args.name, "ts": datetime.now(timezone.utc).isoformat()},
                )
            )
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        bus.emit(Event(prefix="organ", name="stop", payload={"name": args.name}))
        print(f"🫀 STOP organ={label(args.name)}")


if __name__ == "__main__":
    main()
