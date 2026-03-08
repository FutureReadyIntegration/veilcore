"""
VeilCore Physical Security Monitor
======================================
Bridges cybersecurity with physical security for
comprehensive hospital protection.

Covers:
    - Camera feed monitoring and tamper detection
    - Motion/IR/door sensor integration
    - Environmental monitoring (temperature, humidity, power)
    - Sensor fusion — correlating physical and cyber events
    - Physical-cyber attack correlation
    - Server room and network closet protection

The attack doesn't always start on the network.
Sometimes it starts at the door.

Author: Future Ready
System: VeilCore Hospital Cybersecurity Defense
"""

__version__ = "1.0.0"
__codename__ = "IronWatch"

from core.physical.sensors import (
    SensorManager,
    Sensor,
    SensorReading,
    SensorAlert,
)
from core.physical.cameras import (
    CameraMonitor,
    Camera,
    CameraEvent,
)
from core.physical.fusion import (
    SensorFusionEngine,
    CorrelatedEvent,
)
from core.physical.engine import PhysicalSecurityEngine

__all__ = [
    "SensorManager",
    "Sensor",
    "SensorReading",
    "SensorAlert",
    "CameraMonitor",
    "Camera",
    "CameraEvent",
    "SensorFusionEngine",
    "CorrelatedEvent",
    "PhysicalSecurityEngine",
]
