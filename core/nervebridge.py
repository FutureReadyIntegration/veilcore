from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
import json
import uuid


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
EVENTS_PATH = DATA_DIR / "events.json"
MAX_EVENTS = 1000


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _default_store() -> Dict[str, Any]:
    return {
        "events": []
    }


class NerveBridge:
    """
    NerveBridge = VeilCore internal transport/event layer.

    First implementation is file-backed so it is:
    - easy to test
    - safe to inspect
    - easy to wire into API/Desktop
    """

    def __init__(self, path: Path | None = None, max_events: int = MAX_EVENTS):
        self.path = Path(path) if path else EVENTS_PATH
        self.max_events = int(max_events)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._store = self._load()

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            data = _default_store()
            self.path.write_text(json.dumps(data, indent=2))
            return data
        try:
            data = json.loads(self.path.read_text() or "{}")
        except Exception:
            data = _default_store()
        data.setdefault("events", [])
        return data

    def save(self) -> None:
        self.path.write_text(json.dumps(self._store, indent=2))

    def publish(
        self,
        event_type: str,
        source: str,
        level: str = "info",
        message: str = "",
        payload: Optional[Dict[str, Any]] = None,
        target: Optional[str] = None,
    ) -> Dict[str, Any]:
        evt = {
            "id": str(uuid.uuid4()),
            "ts": _now(),
            "type": str(event_type),
            "source": str(source),
            "target": str(target) if target else None,
            "level": str(level).lower(),
            "message": str(message or ""),
            "payload": payload or {},
        }

        events = self._store.setdefault("events", [])
        events.append(evt)

        if len(events) > self.max_events:
            self._store["events"] = events[-self.max_events :]

        self.save()
        return evt

    def recent_events(
        self,
        limit: int = 50,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        level: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        items = list(self._store.get("events", []))

        if event_type:
            items = [e for e in items if e.get("type") == event_type]
        if source:
            items = [e for e in items if e.get("source") == source]
        if level:
            items = [e for e in items if e.get("level") == str(level).lower()]

        return items[-max(1, int(limit)) :]

    def last_event(self) -> Optional[Dict[str, Any]]:
        events = self._store.get("events", [])
        return events[-1] if events else None

    def clear_events(self) -> Dict[str, Any]:
        self._store = _default_store()
        self.save()
        return {"ok": True, "cleared": True}

    def count(self) -> int:
        return len(self._store.get("events", []))


if __name__ == "__main__":
    nb = NerveBridge()
    nb.publish(
        event_type="engine.started",
        source="ml",
        level="info",
        message="DeepSentinel started",
        payload={"state": "running", "health": 100},
    )
    print(json.dumps(nb.recent_events(limit=5), indent=2))
