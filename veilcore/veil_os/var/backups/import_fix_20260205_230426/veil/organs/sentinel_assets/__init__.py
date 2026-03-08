"""
Sentinel Organ - Veil OS Security
==================================
"I watch. I learn. I protect."

This organ implements behavioral anomaly detection:
- User behavior profiling
- Anomaly scoring
- Deviation detection  
- Automated alerting
"""

from .detector import (
    Sentinel,
    SentinelConfig,
    BehaviorEvent,
    UserProfile,
    Anomaly,
    Alert,
    AnomalyType,
    AlertSeverity,
)

__all__ = [
    "Sentinel",
    "SentinelConfig",
    "BehaviorEvent",
    "UserProfile",
    "Anomaly",
    "Alert",
    "AnomalyType",
    "AlertSeverity",
]

__version__ = "1.0.0"
__affirmation__ = "I watch. I learn. I protect."
