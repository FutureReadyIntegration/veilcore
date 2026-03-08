from __future__ import annotations
from veil.core.eventbus import Event, EventBus


class Sentinel:
    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        bus.subscribe("", self.observe)

    def observe(self, event: Event) -> None:
        # TODO: scoring, quarantine, restart logic
        if event.name == "panic":
            print("SENTINEL: panic observed", event)
