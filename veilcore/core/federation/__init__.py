"""
VeilCore Multi-Site Hospital Federation
=========================================
Connects multiple hospitals running VeilCore into a unified
threat intelligence network. Sites share IOCs, blocklists,
threat signatures, and coordinated response actions — but
NEVER share PHI. Patient data stays local by design.

Architecture:
    FederationHub (coordinator) <-> FederationSite (per hospital)
    - TLS-encrypted TCP transport between sites
    - Certificate-based mutual authentication
    - Selective intel sharing (IOCs, signatures, blocklists)
    - Coordinated incident response across sites
    - Distributed threat scoring with local autonomy
    - HIPAA-compliant: PHI never crosses site boundaries

Author: Future Ready
System: VeilCore Hospital Cybersecurity Defense
"""

__version__ = "1.0.0"
__codename__ = "Federation"

from core.federation.protocol import (
    FederationMessage,
    FederationMessageType,
    FederationEnvelope,
)
from core.federation.hub import FederationHub
from core.federation.site import SiteRegistry, SiteInfo
from core.federation.intel import ThreatIntelStore, IOC, ThreatBulletin
from core.federation.sync import SyncEngine

__all__ = [
    "FederationMessage",
    "FederationMessageType",
    "FederationEnvelope",
    "FederationHub",
    "SiteRegistry",
    "SiteInfo",
    "ThreatIntelStore",
    "IOC",
    "ThreatBulletin",
    "SyncEngine",
]
