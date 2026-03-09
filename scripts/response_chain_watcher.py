from __future__ import annotations

import json
import time
from pathlib import Path

from veilcore.core.response.orchestrator import ResponseOrchestrator


EVENT_STORE = Path.home() / "veilcore" / "data" / "events.json"
STATE_FILE = Path.home() / ".config" / "veilcore" / "response_watcher_state.json"


TRIGGER_TYPES = {
    "physical.sensor_triggered",
    "physical.camera_feed_lost",
    "engine.degraded",
}


def load_events() -> list[dict]:
    if not EVENT_STORE.exists():
        return []
    try:
        data = json.loads(EVENT_STORE.read_text())
    except Exception:
        return []
    events = data.get("events", [])
    return events if isinstance(events, list) else []


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {"processed_ids": []}
    try:
        data = json.loads(STATE_FILE.read_text())
    except Exception:
        return {"processed_ids": []}
    if not isinstance(data, dict):
        return {"processed_ids": []}
    if "processed_ids" not in data or not isinstance(data["processed_ids"], list):
        data["processed_ids"] = []
    return data


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    trimmed = state.get("processed_ids", [])[-2000:]
    STATE_FILE.write_text(json.dumps({"processed_ids": trimmed}, indent=2))


def should_process(event: dict, processed_ids: set[str]) -> bool:
    event_id = str(event.get("id") or "").strip()
    event_type = str(event.get("type") or "").strip()
    level = str(event.get("level") or "").strip().lower()

    if not event_id:
        return False
    if event_id in processed_ids:
        return False
    if event_type.startswith("response."):
        return False
    if event_type not in TRIGGER_TYPES:
        return False
    if level not in {"warning", "critical"}:
        return False
    return True


def main() -> None:
    orch = ResponseOrchestrator(event_store=str(EVENT_STORE))
    state = load_state()
    processed_ids = set(state.get("processed_ids", []))

    print("== VeilCore Response Chain Watcher ==")
    print(f"Watching: {EVENT_STORE}")
    print(f"State:    {STATE_FILE}")

    while True:
        changed = False
        events = load_events()

        # oldest -> newest so chains follow original order
        for event in reversed(events):
            if not should_process(event, processed_ids):
                continue

            result = orch.process_event(event)
            event_id = str(event.get("id"))
            processed_ids.add(event_id)
            state["processed_ids"] = sorted(processed_ids)
            changed = True

            print(json.dumps({
                "processed_event_id": event_id,
                "event_type": event.get("type"),
                "result": result,
            }, indent=2))

        if changed:
            save_state(state)

        time.sleep(2.0)


if __name__ == "__main__":
    main()
