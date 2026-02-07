from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Any, Callable, Dict, List


@dataclass(frozen=True)
class Event:
    prefix: str                # e.g. "bios", "cmos", "panic"
    name: str                  # e.g. "stage.start", "tamper.detected"
    payload: Dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time)


Subscriber = Callable[[Event], None]


class EventBus:
    """
    Simple synchronous EventBus:
      - structured events
      - prefix dispatch
    Later we’ll upgrade to persistent/queued bus (tracker pending items).
    """

    def __init__(self) -> None:
        self._subs: Dict[str, List[Subscriber]] = {}

    def subscribe(self, prefix: str, fn: Subscriber) -> None:
        self._subs.setdefault(prefix, []).append(fn)

    def emit(self, event: Event) -> None:
        # Deliver to subscribers whose prefix matches the event prefix.
        for pfx, subs in self._subs.items():
            if event.prefix.startswith(pfx):
                for fn in subs:
                    fn(event)
