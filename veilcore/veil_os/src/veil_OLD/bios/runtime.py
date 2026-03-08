from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from veil.core.eventbus import Event, EventBus
from veil.core.panic import PanicExit, PanicCode, raise_panic
from veil.recovery.shell import RecoveryShell


@dataclass(frozen=True)
class BootStage:
    name: str
    fn: Callable[[], None]


class BIOS:
    """
    BIOS = deterministic staged boot coordinator.
    """

    def __init__(
        self,
        *,
        bus: Optional[EventBus] = None,
        recovery: Optional[RecoveryShell] = None,
    ) -> None:
        self.bus = bus or EventBus()
        self.recovery = recovery or RecoveryShell(self.bus)

        # Deterministic stage ordering: do not mutate at runtime.
        self._stages: List[BootStage] = [
            BootStage("init", self._stage_init),
            BootStage("wire", self._stage_wire),
            BootStage("ready", self._stage_ready),
        ]

    def boot(self) -> None:
        self.bus.emit(Event(prefix="bios", name="boot.start", payload={}))

        try:
            for s in self._stages:
                self.bus.emit(Event(prefix="bios", name="stage.start", payload={"stage": s.name}))
                try:
                    s.fn()
                except Exception as e:
                    # unify all exceptions into a panic path
                    raise_panic(
                        PanicCode.BIOS_STAGE_FAILED,
                        f"Stage '{s.name}' failed: {e}",
                        subsystem="bios",
                        details={"stage": s.name},
                    )
                finally:
                    self.bus.emit(Event(prefix="bios", name="stage.end", payload={"stage": s.name}))

            self.bus.emit(Event(prefix="bios", name="boot.ready", payload={}))

        except PanicExit as pe:
            # Panic propagation + deterministic recovery fallback
            self.bus.emit(
                Event(
                    prefix="panic",
                    name="panic",
                    payload={
                        "code": str(pe.panic.code),
                        "subsystem": pe.panic.subsystem,
                        "message": pe.panic.message,
                        "details": pe.panic.details,
                    },
                )
            )
            self.recovery.enter(pe.panic)
            # re-raise so callers can test/observe a true failure
            raise

    # ---- stages (safe defaults; later wired to subsystems) ----
    def _stage_init(self) -> None:
        self.bus.emit(Event(prefix="bios", name="init", payload={}))

    def _stage_wire(self) -> None:
        self.bus.emit(Event(prefix="bios", name="wire", payload={}))

    def _stage_ready(self) -> None:
        self.bus.emit(Event(prefix="bios", name="ready", payload={}))
