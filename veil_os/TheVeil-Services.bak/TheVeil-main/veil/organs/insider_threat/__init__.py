"""
Insider Threat Detection Organ - Veil OS Security
==================================================
"The greatest threats often come from within."

This organ implements insider threat detection:
- Privilege abuse detection
- Data exfiltration monitoring
- Credential anomaly detection
- Peer deviation analysis
- After-hours access monitoring
"""

from .detector import (
    InsiderThreatDetector,
    InsiderThreatConfig,
    ThreatIndicator,
    RiskLevel,
    ThreatAlert,
    UserActivity,
    UserProfile,
    get_insider_threat_detector,
    ORGAN_METADATA,
)

__all__ = [
    "InsiderThreatDetector",
    "InsiderThreatConfig",
    "ThreatIndicator",
    "RiskLevel",
    "ThreatAlert",
    "UserActivity",
    "UserProfile",
    "get_insider_threat_detector",
    "ORGAN_METADATA",
]

__version__ = "1.0.0"
__affirmation__ = "I protect against the threats that wear friendly faces."

from .runner import start, stop, status
