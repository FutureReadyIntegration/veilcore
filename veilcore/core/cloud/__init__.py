"""
VeilCore Cloud-Hybrid Engine
================================
On-prem + cloud orchestration.
Codename: SkyVeil
"""
__version__ = "1.0.0"
__codename__ = "SkyVeil"

from core.cloud.hybrid import CloudHybridEngine, CloudNode, SyncPolicy

__all__ = ["CloudHybridEngine", "CloudNode", "SyncPolicy"]
