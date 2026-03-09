from __future__ import annotations

import json
from pathlib import Path

from veilcore.core.response.orchestrator import ResponseOrchestrator


DEMO_EVENTS = [
    {
        "id": "demo-physical-1",
        "ts": "2026-03-08T18:00:00",
        "type": "physical.sensor_triggered",
        "source": "physical",
        "target": "MOTION-SR1",
        "level": "critical",
        "message": "motion triggered at Server Room A [server_room]",
        "payload": {
            "sensor_id": "MOTION-SR1",
            "sensor_type": "motion",
            "zone": "server_room",
            "location": "Server Room A",
        },
    },
    {
        "id": "demo-camera-1",
        "ts": "2026-03-08T18:00:05",
        "type": "physical.camera_feed_lost",
        "source": "physical",
        "target": "CAM-SR01",
        "level": "critical",
        "message": "Feed lost from Server Room A",
        "payload": {
            "camera_id": "CAM-SR01",
            "zone": "server_room",
            "location": "Server Room A",
        },
    },
]


def main() -> None:
    store = str(Path.home() / "veilcore" / "data" / "events.json")
    orch = ResponseOrchestrator(event_store=store)

    print("== VeilCore Response Chain Demo ==")
    for event in DEMO_EVENTS:
        result = orch.process_event(event)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
