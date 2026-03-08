from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from veil.core.eventbus import Event, EventBus


@dataclass(frozen=True)
class RepairResult:
    ok: bool
    message: str


RepairFn = Callable[[EventBus], RepairResult]


@dataclass(frozen=True)
class RepairRoutine:
    name: str
    description: str
    fn: RepairFn


_REGISTRY: Dict[str, RepairRoutine] = {}


def register(r: RepairRoutine) -> None:
    _REGISTRY[r.name] = r


def list_repairs() -> List[str]:
    return sorted(_REGISTRY.keys())


def run(name: str, *, bus: Optional[EventBus] = None) -> RepairResult:
    bus = bus or EventBus()
    if name not in _REGISTRY:
        return RepairResult(ok=False, message=f"Unknown repair routine: {name}")

    r = _REGISTRY[name]
    bus.emit(Event(prefix="recovery", name="repair.start", payload={"name": r.name}))
    res = r.fn(bus)
    bus.emit(Event(prefix="recovery", name="repair.end", payload={"name": r.name, "ok": res.ok, "message": res.message}))
    return res


# ---- Built-in safe routines (minimal, deterministic) ----

def _noop_health(bus: EventBus) -> RepairResult:
    # placeholder: confirms recovery engine runs
    return RepairResult(ok=True, message="Recovery system operational.")


register(RepairRoutine(
    name="health_check",
    description="Verify recovery subsystem is operational (no changes).",
    fn=_noop_health,
))
