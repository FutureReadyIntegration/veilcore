from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from veil.core.eventbus import Event, EventBus
from veil.core.panic import PanicExit
from veil.recovery.shell import RecoveryShell

from .checks import PostConfig, check_filesystem, check_imports, check_runtime


@dataclass(frozen=True)
class PostResult:
    ok: bool


class POST:
    """
    POST = deterministic boot-time checks:
      - filesystem checks
      - module import checks
      - runtime sanity
    On Panic: emits panic event and enters RecoveryShell.
    """

    def __init__(self, *, bus: Optional[EventBus] = None, recovery: Optional[RecoveryShell] = None) -> None:
        self.bus = bus or EventBus()
        self.recovery = recovery or RecoveryShell(self.bus)

    def run(self, cfg: PostConfig) -> PostResult:
        self.bus.emit(Event(prefix="post", name="post.start", payload={}))

        try:
            # Deterministic order
            check_filesystem(cfg, bus=self.bus)
            check_imports(cfg, bus=self.bus)
            check_runtime(cfg, bus=self.bus)

            self.bus.emit(Event(prefix="post", name="post.ok", payload={}))
            return PostResult(ok=True)

        except PanicExit as pe:
            # propagate panic on EventBus
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
            # deterministic recovery fallback
            self.recovery.enter(pe.panic)
            raise
