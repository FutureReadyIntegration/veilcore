from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from veil.core.panic import PanicCode


@dataclass(frozen=True)
class PanicGuide:
    code: PanicCode
    title: str
    operator_steps: List[str]
    notes: List[str]


_GUIDES: Dict[PanicCode, PanicGuide] = {
    PanicCode.BIOS_STAGE_FAILED: PanicGuide(
        code=PanicCode.BIOS_STAGE_FAILED,
        title="BIOS stage failed",
        operator_steps=[
            "Open the Veil GUI and review Output for the failing stage name.",
            "Run: veil audit list --limit 25 (check recent actions).",
            "Run: veil ledger verify (ensure integrity chain is valid).",
            "If failure persists, enter recovery and run guided repairs.",
        ],
        notes=["This is a boot integrity failure. Treat as high severity."],
    ),
    PanicCode.CMOS_TAMPER: PanicGuide(
        code=PanicCode.CMOS_TAMPER,
        title="CMOS tamper detected",
        operator_steps=[
            "Do NOT proceed with Apply mode.",
            "Capture evidence: hash + config file snapshot.",
            "Verify filesystem permissions and recent changes.",
            "If confirmed malicious, quarantine the node and escalate incident response.",
        ],
        notes=["Integrity failure — treat as potential compromise."],
    ),
    PanicCode.POST_FAILURE: PanicGuide(
        code=PanicCode.POST_FAILURE,
        title="POST failure",
        operator_steps=[
            "Review POST events in logs/output to identify missing path/module/runtime mismatch.",
            "Confirm the venv is active and Veil installed editable.",
            "Re-run: veil compile --dry-run --no-input (to reproduce safely).",
        ],
        notes=["POST is designed to fail-safe into Recovery."],
    ),
    PanicCode.CMOS_LOCKED: PanicGuide(
        code=PanicCode.CMOS_LOCKED,
        title="CMOS locked",
        operator_steps=[
            "Confirm whether a config change is authorized.",
            "If authorized, use override process and then unlock via guided repair routine.",
            "If unauthorized, keep locked and escalate to security owner.",
        ],
        notes=["Lock exists to prevent accidental/malicious config writes."],
    ),
}


def lookup(code: PanicCode) -> Optional[PanicGuide]:
    return _GUIDES.get(code)


def list_codes() -> List[PanicCode]:
    return sorted(_GUIDES.keys(), key=lambda c: c.value)
