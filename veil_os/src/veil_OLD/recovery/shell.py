from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from veil.core.eventbus import Event, EventBus
from veil.core.panic import Panic, PanicCode

from .panic_codes import lookup as lookup_panic
from .repairs import list_repairs, run as run_repair


@dataclass(frozen=True)
class RecoveryContext:
    reason_code: str
    subsystem: str
    message: str
    details: Dict[str, Any]


class RecoveryShell:
    """
    Deterministic Recovery Shell:
      - minimal dependencies
      - operator-grade messaging
      - panic code lookup
      - guided repair routines (safe, bounded)
    """

    def __init__(self, bus: Optional[EventBus] = None) -> None:
        self.bus = bus

    def enter(self, panic: Panic) -> None:
        ctx = RecoveryContext(
            reason_code=str(panic.code),
            subsystem=panic.subsystem,
            message=panic.message,
            details=panic.details,
        )

        if self.bus:
            self.bus.emit(
                Event(
                    prefix="recovery",
                    name="enter",
                    payload={
                        "reason_code": ctx.reason_code,
                        "subsystem": ctx.subsystem,
                        "message": ctx.message,
                        "details": ctx.details,
                    },
                )
            )

        # Operator output (stable format)
        print("=== VEIL RECOVERY SHELL ===")
        print(f"Reason: {ctx.reason_code}")
        print(f"Subsystem: {ctx.subsystem}")
        print(f"Message: {ctx.message}")
        if ctx.details:
            print("Details:")
            for k, v in ctx.details.items():
                print(f" - {k}: {v}")

        # Panic lookup guidance
        try:
            guide = lookup_panic(panic.code)
        except Exception:
            guide = None

        if guide:
            print("")
            print(f"Guide: {guide.title}")
            print("Operator Steps:")
            for i, step in enumerate(guide.operator_steps, 1):
                print(f"  {i}. {step}")
            if guide.notes:
                print("Notes:")
                for n in guide.notes:
                    print(f" - {n}")

        print("")
        print("Guided Repairs Available:")
        reps = list_repairs()
        if not reps:
            print(" (none registered)")
        else:
            for r in reps:
                print(f" - {r}")

        print("===========================")

    def run_repair(self, name: str) -> bool:
        """
        Run a repair routine in a bounded, auditable way.
        """
        bus = self.bus or EventBus()
        res = run_repair(name, bus=bus)
        print(f"REPAIR: {name} -> ok={res.ok} msg={res.message}")
        return bool(res.ok)
