"""
VeilCore Federation Site Registry
===================================
Manages known federation sites, their capabilities,
trust levels, and connection state.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("veilcore.federation.site")


class TrustLevel(str, Enum):
    FULL = "full"                # Share all non-PHI intel
    STANDARD = "standard"        # Share IOCs and bulletins
    LIMITED = "limited"          # Share only critical bulletins
    UNTRUSTED = "untrusted"      # No sharing
    PENDING = "pending"          # Awaiting approval


class SiteCapability(str, Enum):
    THREAT_INTEL = "threat_intel"
    IOC_SHARING = "ioc_sharing"
    COORDINATED_RESPONSE = "coordinated_response"
    ML_PREDICTIONS = "ml_predictions"
    FORENSIC_DATA = "forensic_data"
    COMPLIANCE_REPORTS = "compliance_reports"
    VULNERABILITY_SCANS = "vulnerability_scans"


@dataclass
class SiteInfo:
    """Information about a federation site (hospital)."""
    site_id: str
    site_name: str
    trust_level: TrustLevel = TrustLevel.STANDARD
    capabilities: list[str] = field(default_factory=list)
    contact_host: str = ""
    contact_port: int = 9443
    organ_count: int = 82
    is_connected: bool = False
    last_seen: Optional[str] = None
    joined_at: Optional[str] = None
    intel_received: int = 0
    intel_sent: int = 0
    threat_bulletins_received: int = 0
    threat_bulletins_sent: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "site_id": self.site_id, "site_name": self.site_name,
            "trust_level": self.trust_level.value,
            "capabilities": self.capabilities,
            "contact_host": self.contact_host,
            "contact_port": self.contact_port,
            "organ_count": self.organ_count,
            "is_connected": self.is_connected,
            "last_seen": self.last_seen, "joined_at": self.joined_at,
            "intel_received": self.intel_received,
            "intel_sent": self.intel_sent,
            "threat_bulletins_received": self.threat_bulletins_received,
            "threat_bulletins_sent": self.threat_bulletins_sent,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SiteInfo:
        data = dict(data)
        if "trust_level" in data:
            data["trust_level"] = TrustLevel(data["trust_level"])
        valid = cls.__dataclass_fields__
        return cls(**{k: v for k, v in data.items() if k in valid})


class SiteRegistry:
    """
    Registry of known federation sites.

    Manages site information, trust levels, and persistence.

    Usage:
        registry = SiteRegistry()
        registry.register_site("hospital-a", "Memorial Hospital", host="10.0.1.1")
        registry.set_trust_level("hospital-a", TrustLevel.FULL)
        sites = registry.get_trusted_sites()
    """

    REGISTRY_PATH = "/var/lib/veilcore/federation/sites.json"

    def __init__(self, registry_path: Optional[str] = None):
        self._path = registry_path or self.REGISTRY_PATH
        self._sites: dict[str, SiteInfo] = {}
        self._load()

    def register_site(
        self,
        site_id: str,
        site_name: str,
        host: str = "",
        port: int = 9443,
        trust_level: TrustLevel = TrustLevel.PENDING,
        capabilities: Optional[list[str]] = None,
    ) -> SiteInfo:
        """Register a new federation site."""
        site = SiteInfo(
            site_id=site_id, site_name=site_name,
            contact_host=host, contact_port=port,
            trust_level=trust_level,
            capabilities=capabilities or [],
            joined_at=datetime.now(timezone.utc).isoformat(),
        )
        self._sites[site_id] = site
        self._save()
        logger.info(f"Registered site '{site_name}' ({site_id}) — trust: {trust_level.value}")
        return site

    def remove_site(self, site_id: str) -> bool:
        """Remove a site from the registry."""
        if site_id in self._sites:
            site = self._sites.pop(site_id)
            self._save()
            logger.info(f"Removed site '{site.site_name}' ({site_id})")
            return True
        return False

    def get_site(self, site_id: str) -> Optional[SiteInfo]:
        """Get site information."""
        return self._sites.get(site_id)

    def set_trust_level(self, site_id: str, level: TrustLevel) -> bool:
        """Update a site's trust level."""
        site = self._sites.get(site_id)
        if not site:
            return False
        old_level = site.trust_level
        site.trust_level = level
        self._save()
        logger.info(f"Trust level for '{site.site_name}': {old_level.value} → {level.value}")
        return True

    def mark_connected(self, site_id: str) -> None:
        """Mark a site as connected."""
        site = self._sites.get(site_id)
        if site:
            site.is_connected = True
            site.last_seen = datetime.now(timezone.utc).isoformat()
            self._save()

    def mark_disconnected(self, site_id: str) -> None:
        """Mark a site as disconnected."""
        site = self._sites.get(site_id)
        if site:
            site.is_connected = False
            self._save()

    def get_trusted_sites(self, min_trust: TrustLevel = TrustLevel.LIMITED) -> list[SiteInfo]:
        """Get sites at or above the given trust level."""
        trust_order = [TrustLevel.UNTRUSTED, TrustLevel.PENDING, TrustLevel.LIMITED,
                       TrustLevel.STANDARD, TrustLevel.FULL]
        min_index = trust_order.index(min_trust)
        return [
            s for s in self._sites.values()
            if trust_order.index(s.trust_level) >= min_index
        ]

    def get_connected_sites(self) -> list[SiteInfo]:
        """Get currently connected sites."""
        return [s for s in self._sites.values() if s.is_connected]

    @property
    def total_count(self) -> int:
        return len(self._sites)

    @property
    def connected_count(self) -> int:
        return sum(1 for s in self._sites.values() if s.is_connected)

    def summary(self) -> dict[str, Any]:
        """Get registry summary."""
        by_trust = {}
        for level in TrustLevel:
            by_trust[level.value] = sum(
                1 for s in self._sites.values() if s.trust_level == level
            )
        return {
            "total_sites": self.total_count,
            "connected": self.connected_count,
            "by_trust_level": by_trust,
            "total_intel_exchanged": sum(
                s.intel_sent + s.intel_received for s in self._sites.values()
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "sites": {sid: s.to_dict() for sid, s in self._sites.items()},
        }

    def _save(self) -> None:
        """Persist registry to disk."""
        try:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            with open(self._path, "w") as f:
                json.dump(
                    {sid: s.to_dict() for sid, s in self._sites.items()},
                    f, indent=2, default=str,
                )
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")

    def _load(self) -> None:
        """Load registry from disk."""
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path) as f:
                data = json.load(f)
            for sid, sdata in data.items():
                self._sites[sid] = SiteInfo.from_dict(sdata)
            logger.info(f"Loaded {len(self._sites)} sites from registry")
        except Exception as e:
            logger.warning(f"Failed to load registry: {e}")
