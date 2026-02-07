"""
Auto-Lockdown Organ - Veil OS Security
=======================================
"When threats emerge, I respond without hesitation."

This organ implements automated threat response:
- Graduated response levels (warn → restrict → suspend → lockdown)
- Automatic account suspension
- Network isolation triggers
- Incident recording and recovery
"""

from .engine import (
    AutoLockdown,
    LockdownConfig,
    ResponseLevel,
    ActionType,
    ThreatEvent,
    ResponseAction,
    LockdownState,
    get_auto_lockdown,
    ORGAN_METADATA,
)

__all__ = [
    "AutoLockdown",
    "LockdownConfig",
    "ResponseLevel",
    "ActionType",
    "ThreatEvent",
    "ResponseAction",
    "LockdownState",
    "get_auto_lockdown",
    "ORGAN_METADATA",
]

__version__ = "1.0.0"
__affirmation__ = "When threats emerge, I respond without hesitation."
