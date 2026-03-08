from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, NoReturn


class PanicCode(str, Enum):
    # BIOS
    BIOS_STAGE_FAILED = "BIOS_STAGE_FAILED"

    # CMOS
    CMOS_TAMPER = "CMOS_TAMPER"
    CMOS_LOCKED = "CMOS_LOCKED"
    CMOS_SCHEMA = "CMOS_SCHEMA"

    # POST
    POST_FAILURE = "POST_FAILURE"

    # Recovery / Sentinel hooks (expanded later)
    RECOVERY_ENTERED = "RECOVERY_ENTERED"
    SENTINEL_ESCALATION = "SENTINEL_ESCALATION"


@dataclass(frozen=True)
class Panic:
    code: PanicCode
    message: str
    subsystem: str
    details: Dict[str, Any]


class PanicExit(SystemExit):
    """
    Unified panic exception. Raising this is a deliberate fail-safe.
    """

    def __init__(self, panic: Panic):
        super().__init__(f"PANIC[{panic.code}] {panic.subsystem}: {panic.message}")
        self.panic = panic


def raise_panic(
    code: PanicCode,
    message: str,
    *,
    subsystem: str,
    details: Optional[Dict[str, Any]] = None,
) -> NoReturn:
    raise PanicExit(
        Panic(
            code=code,
            message=message,
            subsystem=subsystem,
            details=details or {},
        )
    )

