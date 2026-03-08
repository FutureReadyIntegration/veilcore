"""
VeilCore RFID/NFC Guard
==========================
Monitors and protects RFID badge systems and NFC
equipment tracking in hospital environments.

Covers:
    - RFID badge access monitoring (Imprivata, HID)
    - NFC equipment tag inventory
    - Unauthorized RFID reader detection
    - Badge cloning attempt detection
    - NFC skimming prevention
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("veilcore.wireless.rfid_nfc")


class RFIDFrequency(str, Enum):
    LF_125KHZ = "125kHz"       # Proximity cards (HID)
    HF_13_56MHZ = "13.56MHz"   # Smart cards, NFC
    UHF_860MHZ = "860-960MHz"  # Equipment tracking


class TagTrust(str, Enum):
    TRUSTED = "trusted"
    KNOWN = "known"
    UNKNOWN = "unknown"
    CLONED = "cloned"
    BLOCKED = "blocked"


@dataclass
class RFIDTag:
    """Tracked RFID/NFC tag."""
    tag_id: str
    frequency: str = "13.56MHz"
    tag_type: str = "badge"     # badge, equipment, asset, unknown
    owner: str = ""
    department: str = ""
    trust: str = "unknown"
    last_reader: str = ""
    last_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    first_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    read_count: int = 0
    is_active: bool = True

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.tag_id.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "tag_id": self.tag_id, "frequency": self.frequency,
            "tag_type": self.tag_type, "owner": self.owner,
            "department": self.department, "trust": self.trust,
            "last_reader": self.last_reader,
            "last_seen": self.last_seen, "first_seen": self.first_seen,
            "read_count": self.read_count, "is_active": self.is_active,
            "fingerprint": self.fingerprint,
        }


@dataclass
class NFCEvent:
    """NFC/RFID event record."""
    event_id: str = field(default_factory=lambda: f"NFC-{int(time.time() * 1000)}")
    event_type: str = "read"    # read, write, auth_fail, clone_attempt, skim_attempt
    tag_id: str = ""
    reader_id: str = ""
    location: str = ""
    severity: str = "info"
    details: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id, "event_type": self.event_type,
            "tag_id": self.tag_id, "reader_id": self.reader_id,
            "location": self.location, "severity": self.severity,
            "details": self.details, "timestamp": self.timestamp,
        }


class RFIDNFCGuard:
    """
    Monitors and protects RFID/NFC systems.

    Usage:
        guard = RFIDNFCGuard()
        guard.register_tag("BADGE-001", tag_type="badge", owner="Dr. Smith")
        guard.register_reader("READER-LOBBY", location="Main Lobby")

        event = guard.process_read("BADGE-001", "READER-LOBBY")
        threats = guard.detect_anomalies()
    """

    EVENT_HISTORY_SIZE = 10000
    LOG_PATH = "/var/log/veilcore/rfid-nfc.jsonl"

    def __init__(self):
        self._tags: dict[str, RFIDTag] = {}
        self._readers: dict[str, dict[str, str]] = {}
        self._blocked_tags: set[str] = set()
        self._events: deque[NFCEvent] = deque(maxlen=self.EVENT_HISTORY_SIZE)
        self._read_patterns: dict[str, list[float]] = defaultdict(list)

    def register_tag(self, tag_id: str, tag_type: str = "badge",
                     owner: str = "", department: str = "",
                     frequency: str = "13.56MHz") -> RFIDTag:
        """Register a known RFID/NFC tag."""
        tag = RFIDTag(
            tag_id=tag_id, tag_type=tag_type, owner=owner,
            department=department, frequency=frequency, trust="trusted",
        )
        self._tags[tag_id] = tag
        logger.info(f"Registered RFID tag: {tag_id} ({tag_type}, owner: {owner})")
        return tag

    def register_reader(self, reader_id: str, location: str = "",
                        reader_type: str = "door") -> None:
        """Register an authorized RFID reader."""
        self._readers[reader_id] = {
            "reader_id": reader_id, "location": location,
            "reader_type": reader_type,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(f"Registered reader: {reader_id} at {location}")

    def block_tag(self, tag_id: str, reason: str = "") -> None:
        """Block a tag from access."""
        self._blocked_tags.add(tag_id)
        if tag_id in self._tags:
            self._tags[tag_id].trust = "blocked"
            self._tags[tag_id].is_active = False
        self._log_event(NFCEvent(
            event_type="block", tag_id=tag_id,
            severity="high", details=f"Tag blocked: {reason}",
        ))
        logger.warning(f"Blocked RFID tag: {tag_id} — {reason}")

    def process_read(self, tag_id: str, reader_id: str) -> NFCEvent:
        """Process an RFID/NFC read event."""
        now = time.time()

        # Check blocked
        if tag_id in self._blocked_tags:
            event = NFCEvent(
                event_type="auth_fail", tag_id=tag_id, reader_id=reader_id,
                location=self._readers.get(reader_id, {}).get("location", ""),
                severity="high",
                details="Blocked tag attempted access",
            )
            self._log_event(event)
            return event

        # Check if reader is authorized
        if reader_id not in self._readers:
            event = NFCEvent(
                event_type="skim_attempt", tag_id=tag_id, reader_id=reader_id,
                severity="critical",
                details=f"Read from unregistered reader: {reader_id}",
            )
            self._log_event(event)
            return event

        # Track read pattern for clone detection
        self._read_patterns[tag_id].append(now)
        # Keep last 100 reads
        self._read_patterns[tag_id] = self._read_patterns[tag_id][-100:]

        # Update or create tag
        if tag_id in self._tags:
            tag = self._tags[tag_id]
            tag.last_reader = reader_id
            tag.last_seen = datetime.now(timezone.utc).isoformat()
            tag.read_count += 1
        else:
            tag = RFIDTag(
                tag_id=tag_id, trust="unknown",
                last_reader=reader_id,
            )
            self._tags[tag_id] = tag

        event = NFCEvent(
            event_type="read", tag_id=tag_id, reader_id=reader_id,
            location=self._readers.get(reader_id, {}).get("location", ""),
            severity="info" if tag.trust == "trusted" else "medium",
            details=f"Tag read (trust: {tag.trust})",
        )
        self._log_event(event)
        return event

    def detect_anomalies(self) -> list[NFCEvent]:
        """Detect RFID/NFC anomalies."""
        anomalies = []
        now = time.time()

        for tag_id, reads in self._read_patterns.items():
            recent = [t for t in reads if now - t < 60]  # Last 60 seconds

            # Rapid read detection (possible cloning/replay)
            if len(recent) > 10:
                event = NFCEvent(
                    event_type="clone_attempt", tag_id=tag_id,
                    severity="critical",
                    details=f"Rapid reads detected: {len(recent)} in 60s (possible clone/replay)",
                )
                anomalies.append(event)
                self._log_event(event)

            # Simultaneous location detection (impossible travel)
            tag = self._tags.get(tag_id)
            if tag and len(recent) >= 2:
                # Check if tag was read at multiple readers in very short time
                recent_events = [e for e in self._events
                                 if e.tag_id == tag_id and e.event_type == "read"]
                if len(recent_events) >= 2:
                    last_two = list(recent_events)[-2:]
                    if (last_two[0].reader_id != last_two[1].reader_id and
                            len(recent) > 3):
                        event = NFCEvent(
                            event_type="clone_attempt", tag_id=tag_id,
                            severity="high",
                            details=f"Tag at multiple readers rapidly: "
                                    f"{last_two[0].reader_id} → {last_two[1].reader_id}",
                        )
                        anomalies.append(event)

        return anomalies

    def get_events(self, limit: int = 50,
                   event_type: Optional[str] = None) -> list[NFCEvent]:
        """Get recent events."""
        events = list(self._events)
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[:limit]

    def get_tag(self, tag_id: str) -> Optional[RFIDTag]:
        return self._tags.get(tag_id)

    def summary(self) -> dict[str, Any]:
        by_trust = defaultdict(int)
        for tag in self._tags.values():
            by_trust[tag.trust] += 1

        return {
            "total_tags": len(self._tags),
            "total_readers": len(self._readers),
            "blocked_tags": len(self._blocked_tags),
            "total_events": len(self._events),
            "by_trust": dict(by_trust),
        }

    def _log_event(self, event: NFCEvent) -> None:
        """Log event to history and disk."""
        self._events.append(event)
        try:
            os.makedirs(os.path.dirname(self.LOG_PATH), exist_ok=True)
            with open(self.LOG_PATH, "a") as f:
                f.write(json.dumps(event.to_dict(), default=str) + "\n")
        except Exception:
            pass
