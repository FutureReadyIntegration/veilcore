"""
Zero-Trust Organ - Veil OS Security
====================================
"Never trust, always verify."

This organ implements Zero-Trust Architecture for hospital security:
- Continuous verification of every request
- Device posture assessment
- Context-aware access decisions
- Micro-segmentation enforcement
- Behavioral anomaly detection integration
"""

from .engine import (
    ZeroTrust,
    ZeroTrustConfig,
    get_zero_trust,
    TrustLevel,
    DevicePosture,
    AccessDecision,
    DeviceInfo,
    AccessContext,
    AccessResult,
    Policy,
)

__all__ = [
    "ZeroTrust",
    "ZeroTrustConfig",
    "get_zero_trust",
    "TrustLevel",
    "DevicePosture",
    "AccessDecision",
    "DeviceInfo",
    "AccessContext",
    "AccessResult",
    "Policy",
]

__version__ = "1.0.0"
__affirmation__ = "I verify every request. Trust is earned, never assumed."

from .runner import start, stop, status
