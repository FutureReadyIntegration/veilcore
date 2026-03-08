from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from veil.core.eventbus import Event, EventBus
from veil.chronicle.runtime import append_event


@dataclass(frozen=True)
class BridgeConfig:
    enabled: bool = True


class SentinelChronicleBridge:
    """
    Subscribes to EventBus and writes a Cathedral Chronicle entry for key events.
    """

    def __init__(self, bus: EventBus, *, cfg: Optional[BridgeConfig] = None) -> None:
        self.bus = bus
        self.cfg = cfg or BridgeConfig()
        bus.subscribe("", self.observe)

    def observe(self, e: Event) -> None:
        if not self.cfg.enabled:
            return

        # Filter: keep Chronicle high-signal by default (expand later).
        # We capture panic, post, bios, cmos, recovery events.
        if e.prefix not in {"panic", "post", "bios", "cmos", "recovery"}:
            return

        # Normalize into a Chronicle event
        payload: Dict[str, Any] = {
            "prefix": e.prefix,
            "name": e.name,
            "payload": e.payload,
            "ts": e.ts,
        }

        append_event({"type": f"{e.prefix}.{e.name}", "payload": payload})
