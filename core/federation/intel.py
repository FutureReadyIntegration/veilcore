"""
VeilCore Threat Intelligence Store
====================================
Stores and manages shared threat intelligence across the federation.

Intel types:
    - IOCs (Indicators of Compromise): IPs, domains, file hashes, URLs
    - Threat Bulletins: Coordinated alerts about active campaigns
    - Blocklists: Aggregated block rules from all sites
    - Signatures: Detection patterns and YARA rules
    - TTPs: Tactics, Techniques, and Procedures

All intel is stored locally and NEVER contains PHI.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("veilcore.federation.intel")


class IOCType(str, Enum):
    IP_ADDRESS = "ip_address"
    DOMAIN = "domain"
    URL = "url"
    FILE_HASH_MD5 = "file_hash_md5"
    FILE_HASH_SHA256 = "file_hash_sha256"
    EMAIL_ADDRESS = "email_address"
    CVE = "cve"
    USER_AGENT = "user_agent"
    MUTEX = "mutex"
    REGISTRY_KEY = "registry_key"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IntelConfidence(str, Enum):
    CONFIRMED = "confirmed"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNVERIFIED = "unverified"


@dataclass
class IOC:
    """Indicator of Compromise."""
    ioc_type: IOCType
    value: str
    severity: Severity = Severity.MEDIUM
    confidence: IntelConfidence = IntelConfidence.MEDIUM
    source_site: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    first_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expiry: Optional[str] = None
    related_threats: list[str] = field(default_factory=list)
    sightings: int = 1

    @property
    def id(self) -> str:
        return f"{self.ioc_type.value}:{self.value}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "ioc_type": self.ioc_type.value,
            "value": self.value, "severity": self.severity.value,
            "confidence": self.confidence.value,
            "source_site": self.source_site, "description": self.description,
            "tags": self.tags, "first_seen": self.first_seen,
            "last_seen": self.last_seen, "expiry": self.expiry,
            "related_threats": self.related_threats, "sightings": self.sightings,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IOC:
        data = dict(data)
        data.pop("id", None)
        if "ioc_type" in data:
            data["ioc_type"] = IOCType(data["ioc_type"])
        if "severity" in data:
            data["severity"] = Severity(data["severity"])
        if "confidence" in data:
            data["confidence"] = IntelConfidence(data["confidence"])
        valid = cls.__dataclass_fields__
        return cls(**{k: v for k, v in data.items() if k in valid})


@dataclass
class ThreatBulletin:
    """Coordinated threat notification shared across the federation."""
    bulletin_id: str = field(default_factory=lambda: f"TB-{int(time.time())}")
    title: str = ""
    threat_type: str = ""
    severity: Severity = Severity.HIGH
    source_site: str = ""
    description: str = ""
    iocs: list[dict[str, Any]] = field(default_factory=list)
    affected_systems: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    ttps: list[str] = field(default_factory=list)
    issued_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: Optional[str] = None
    acknowledged_by: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "bulletin_id": self.bulletin_id, "title": self.title,
            "threat_type": self.threat_type, "severity": self.severity.value,
            "source_site": self.source_site, "description": self.description,
            "iocs": self.iocs, "affected_systems": self.affected_systems,
            "recommended_actions": self.recommended_actions,
            "ttps": self.ttps, "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "acknowledged_by": self.acknowledged_by,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ThreatBulletin:
        data = dict(data)
        if "severity" in data:
            data["severity"] = Severity(data["severity"])
        valid = cls.__dataclass_fields__
        return cls(**{k: v for k, v in data.items() if k in valid})


class ThreatIntelStore:
    """
    Local threat intelligence database.

    Stores IOCs, bulletins, and blocklists received from the federation.
    All data is persisted to /var/lib/veilcore/federation/.

    Usage:
        store = ThreatIntelStore()
        store.add_ioc(IOC(ioc_type=IOCType.IP_ADDRESS, value="192.168.1.99",
                          severity=Severity.HIGH, source_site="hospital-a"))
        matches = store.lookup_ip("192.168.1.99")
        blocklist = store.get_blocklist()
    """

    STORE_PATH = "/var/lib/veilcore/federation/intel"

    def __init__(self, store_path: Optional[str] = None):
        self._path = store_path or self.STORE_PATH
        self._iocs: dict[str, IOC] = {}
        self._bulletins: dict[str, ThreatBulletin] = {}
        self._blocklist_ips: set[str] = set()
        self._blocklist_domains: set[str] = set()
        self._tags_index: dict[str, set[str]] = defaultdict(set)
        self._type_index: dict[IOCType, set[str]] = defaultdict(set)
        os.makedirs(self._path, exist_ok=True)
        self._load()

    def add_ioc(self, ioc: IOC) -> None:
        """Add or update an IOC."""
        existing = self._iocs.get(ioc.id)
        if existing:
            existing.sightings += 1
            existing.last_seen = datetime.now(timezone.utc).isoformat()
            if ioc.severity.value > existing.severity.value:
                existing.severity = ioc.severity
            if ioc.confidence.value > existing.confidence.value:
                existing.confidence = ioc.confidence
            for tag in ioc.tags:
                if tag not in existing.tags:
                    existing.tags.append(tag)
        else:
            self._iocs[ioc.id] = ioc
            self._type_index[ioc.ioc_type].add(ioc.id)
            for tag in ioc.tags:
                self._tags_index[tag].add(ioc.id)

        # Update blocklists
        if ioc.ioc_type == IOCType.IP_ADDRESS and ioc.severity in (Severity.HIGH, Severity.CRITICAL):
            self._blocklist_ips.add(ioc.value)
        elif ioc.ioc_type == IOCType.DOMAIN and ioc.severity in (Severity.HIGH, Severity.CRITICAL):
            self._blocklist_domains.add(ioc.value)

    def add_iocs_bulk(self, iocs: list[IOC]) -> int:
        """Add multiple IOCs. Returns count added."""
        for ioc in iocs:
            self.add_ioc(ioc)
        self._save_iocs()
        return len(iocs)

    def add_bulletin(self, bulletin: ThreatBulletin) -> None:
        """Add a threat bulletin."""
        self._bulletins[bulletin.bulletin_id] = bulletin
        # Extract and add IOCs from bulletin
        for ioc_data in bulletin.iocs:
            try:
                ioc = IOC.from_dict(ioc_data)
                ioc.related_threats.append(bulletin.threat_type)
                self.add_ioc(ioc)
            except Exception as e:
                logger.debug(f"Failed to parse IOC from bulletin: {e}")
        self._save_bulletins()

    def lookup_ip(self, ip: str) -> Optional[IOC]:
        """Look up an IP address in the IOC database."""
        return self._iocs.get(f"ip_address:{ip}")

    def lookup_domain(self, domain: str) -> Optional[IOC]:
        """Look up a domain in the IOC database."""
        return self._iocs.get(f"domain:{domain}")

    def lookup_hash(self, file_hash: str) -> Optional[IOC]:
        """Look up a file hash (MD5 or SHA256)."""
        result = self._iocs.get(f"file_hash_sha256:{file_hash}")
        if not result:
            result = self._iocs.get(f"file_hash_md5:{file_hash}")
        return result

    def is_blocked_ip(self, ip: str) -> bool:
        """Check if an IP is on the blocklist."""
        return ip in self._blocklist_ips

    def is_blocked_domain(self, domain: str) -> bool:
        """Check if a domain is on the blocklist."""
        return domain in self._blocklist_domains

    def get_blocklist(self) -> dict[str, list[str]]:
        """Get current blocklists."""
        return {
            "ips": sorted(self._blocklist_ips),
            "domains": sorted(self._blocklist_domains),
        }

    def get_by_type(self, ioc_type: IOCType) -> list[IOC]:
        """Get all IOCs of a given type."""
        ids = self._type_index.get(ioc_type, set())
        return [self._iocs[ioc_id] for ioc_id in ids if ioc_id in self._iocs]

    def get_by_tag(self, tag: str) -> list[IOC]:
        """Get all IOCs with a given tag."""
        ids = self._tags_index.get(tag, set())
        return [self._iocs[ioc_id] for ioc_id in ids if ioc_id in self._iocs]

    def get_recent_bulletins(self, limit: int = 20) -> list[ThreatBulletin]:
        """Get most recent threat bulletins."""
        sorted_bulletins = sorted(
            self._bulletins.values(),
            key=lambda b: b.issued_at, reverse=True,
        )
        return sorted_bulletins[:limit]

    def get_active_bulletins(self) -> list[ThreatBulletin]:
        """Get non-expired bulletins."""
        now = datetime.now(timezone.utc).isoformat()
        return [
            b for b in self._bulletins.values()
            if not b.expires_at or b.expires_at > now
        ]

    def summary(self) -> dict[str, Any]:
        """Get intel store summary."""
        by_type = {}
        for ioc_type in IOCType:
            count = len(self._type_index.get(ioc_type, set()))
            if count > 0:
                by_type[ioc_type.value] = count
        by_severity = {}
        for sev in Severity:
            count = sum(1 for i in self._iocs.values() if i.severity == sev)
            if count > 0:
                by_severity[sev.value] = count
        return {
            "total_iocs": len(self._iocs),
            "total_bulletins": len(self._bulletins),
            "blocked_ips": len(self._blocklist_ips),
            "blocked_domains": len(self._blocklist_domains),
            "by_type": by_type,
            "by_severity": by_severity,
            "unique_sources": len(set(i.source_site for i in self._iocs.values())),
        }

    def _save_iocs(self) -> None:
        """Persist IOCs to disk."""
        try:
            path = os.path.join(self._path, "iocs.json")
            with open(path, "w") as f:
                json.dump(
                    [ioc.to_dict() for ioc in self._iocs.values()],
                    f, indent=2, default=str,
                )
        except Exception as e:
            logger.error(f"Failed to save IOCs: {e}")

    def _save_bulletins(self) -> None:
        """Persist bulletins to disk."""
        try:
            path = os.path.join(self._path, "bulletins.json")
            with open(path, "w") as f:
                json.dump(
                    [b.to_dict() for b in self._bulletins.values()],
                    f, indent=2, default=str,
                )
        except Exception as e:
            logger.error(f"Failed to save bulletins: {e}")

    def _load(self) -> None:
        """Load persisted intel from disk."""
        # Load IOCs
        ioc_path = os.path.join(self._path, "iocs.json")
        if os.path.exists(ioc_path):
            try:
                with open(ioc_path) as f:
                    for ioc_data in json.load(f):
                        ioc = IOC.from_dict(ioc_data)
                        self._iocs[ioc.id] = ioc
                        self._type_index[ioc.ioc_type].add(ioc.id)
                        for tag in ioc.tags:
                            self._tags_index[tag].add(ioc.id)
                        if ioc.ioc_type == IOCType.IP_ADDRESS and ioc.severity in (Severity.HIGH, Severity.CRITICAL):
                            self._blocklist_ips.add(ioc.value)
                        elif ioc.ioc_type == IOCType.DOMAIN and ioc.severity in (Severity.HIGH, Severity.CRITICAL):
                            self._blocklist_domains.add(ioc.value)
                logger.info(f"Loaded {len(self._iocs)} IOCs from store")
            except Exception as e:
                logger.warning(f"Failed to load IOCs: {e}")

        # Load bulletins
        bulletin_path = os.path.join(self._path, "bulletins.json")
        if os.path.exists(bulletin_path):
            try:
                with open(bulletin_path) as f:
                    for b_data in json.load(f):
                        bulletin = ThreatBulletin.from_dict(b_data)
                        self._bulletins[bulletin.bulletin_id] = bulletin
                logger.info(f"Loaded {len(self._bulletins)} bulletins from store")
            except Exception as e:
                logger.warning(f"Failed to load bulletins: {e}")

    def save(self) -> None:
        """Save all data to disk."""
        self._save_iocs()
        self._save_bulletins()
