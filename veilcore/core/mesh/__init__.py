"""
VeilCore Organ Mesh Communication System
=========================================
The nervous system of VeilCore — enables all 82 security organs
to communicate, share threat intelligence, and coordinate responses
in real-time via encrypted pub/sub messaging over Unix domain sockets.

Author: Future Ready
System: VeilCore Hospital Cybersecurity Defense
"""

__version__ = "1.0.0"
__codename__ = "NervousSystem"

from core.mesh.protocol import (
    MeshMessage,
    MessageType,
    MessagePriority,
    MeshEnvelope,
)
from core.mesh.router import MeshRouter
from core.mesh.client import MeshClient
from core.mesh.discovery import OrganDiscovery
from core.mesh.monitor import MeshMonitor

__all__ = [
    "MeshMessage",
    "MessageType",
    "MessagePriority",
    "MeshEnvelope",
    "MeshRouter",
    "MeshClient",
    "OrganDiscovery",
    "MeshMonitor",
]
