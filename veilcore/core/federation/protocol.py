"""
VeilCore Federation Protocol
==============================
Wire protocol for inter-hospital communication.

All federation traffic is:
    - TLS 1.3 encrypted (in production)
    - Certificate-authenticated (mutual TLS)
    - PHI-stripped (payload sanitizer enforces this)
    - Signed with site-specific HMAC for integrity
    - Timestamped and TTL-bounded

Message types cover the full federation lifecycle:
    - HANDSHAKE: Site registration and capability exchange
    - INTEL_SHARE: IOCs, signatures, blocklists
    - THREAT_BULLETIN: Coordinated threat notifications
    - SYNC_REQUEST/RESPONSE: State synchronization
    - HEARTBEAT: Liveness monitoring
    - COMMAND: Coordinated response actions
    - REVOKE: Credential/cert/IOC revocation
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class FederationMessageType(str, Enum):
    HANDSHAKE = "handshake"
    HANDSHAKE_ACK = "handshake_ack"
    INTEL_SHARE = "intel_share"
    THREAT_BULLETIN = "threat_bulletin"
    SYNC_REQUEST = "sync_request"
    SYNC_RESPONSE = "sync_response"
    HEARTBEAT = "heartbeat"
    COMMAND = "command"
    COMMAND_ACK = "command_ack"
    REVOKE = "revoke"
    SITE_STATUS = "site_status"
    DISCONNECT = "disconnect"


# PHI patterns to strip from all outbound federation messages
PHI_PATTERNS = [
    re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),                    # SSN
    re.compile(r'\b[A-Z]{1,2}\d{6,10}\b'),                    # MRN patterns
    re.compile(r'\bPAT-\d+\b', re.IGNORECASE),                # Patient IDs
    re.compile(r'\bMRN[:\s-]?\d+\b', re.IGNORECASE),          # MRN labels
    re.compile(r'\b\d{3}-\d{3}-\d{4}\b'),                     # Phone numbers
    re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),  # Email
    re.compile(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b'),               # DOB patterns
    re.compile(r'\b(?:patient|pt)\s*(?:name|nm)[:\s]+\S+', re.IGNORECASE),  # Patient name labels
]

# Keys that should never appear in federation messages
PHI_KEYS = {
    "patient_name", "patient_dob", "patient_ssn", "patient_address",
    "patient_phone", "patient_email", "mrn", "medical_record_number",
    "date_of_birth", "social_security", "ssn", "insurance_id",
    "guarantor", "next_of_kin", "emergency_contact", "employer",
    "mothers_maiden", "drivers_license", "passport_number",
}

_FEDERATION_SECRET_PATH = "/etc/veilcore/federation/federation.key"
_FEDERATION_SECRET: Optional[bytes] = None


def _get_federation_secret() -> bytes:
    global _FEDERATION_SECRET
    if _FEDERATION_SECRET is not None:
        return _FEDERATION_SECRET
    if os.path.exists(_FEDERATION_SECRET_PATH):
        with open(_FEDERATION_SECRET_PATH, "rb") as f:
            _FEDERATION_SECRET = f.read()
    else:
        _FEDERATION_SECRET = hashlib.sha256(
            b"veilcore-federation-dev-" + str(os.getpid()).encode()
        ).digest()
    return _FEDERATION_SECRET


def sanitize_phi(data: Any, path: str = "") -> Any:
    """
    Recursively strip PHI from data before federation transmission.
    This is the CRITICAL safety boundary — PHI must never cross sites.
    """
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if key.lower() in PHI_KEYS:
                sanitized[key] = "[PHI_REDACTED]"
                continue
            sanitized[key] = sanitize_phi(value, f"{path}.{key}")
        return sanitized
    elif isinstance(data, list):
        return [sanitize_phi(item, f"{path}[]") for item in data]
    elif isinstance(data, str):
        result = data
        for pattern in PHI_PATTERNS:
            result = pattern.sub("[PHI_REDACTED]", result)
        return result
    return data


@dataclass
class FederationMessage:
    """Inner message payload for federation communication."""
    action: str
    data: dict[str, Any] = field(default_factory=dict)
    site_source: str = ""
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FederationMessage:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class FederationEnvelope:
    """Outer envelope for all federation wire messages."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_site: str = ""
    dest_site: str = ""          # empty = broadcast to all sites
    msg_type: FederationMessageType = FederationMessageType.INTEL_SHARE
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ttl: int = 3600
    hmac_signature: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    federation_version: str = "1.0"
    phi_sanitized: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["msg_type"] = self.msg_type.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FederationEnvelope:
        data = dict(data)
        if "msg_type" in data:
            data["msg_type"] = FederationMessageType(data["msg_type"])
        valid = cls.__dataclass_fields__
        return cls(**{k: v for k, v in data.items() if k in valid})

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str, sort_keys=True)

    @classmethod
    def from_json(cls, raw: str) -> FederationEnvelope:
        return cls.from_dict(json.loads(raw))

    def to_bytes(self) -> bytes:
        return self.to_json().encode("utf-8")

    @classmethod
    def from_bytes(cls, raw: bytes) -> FederationEnvelope:
        return cls.from_json(raw.decode("utf-8"))

    def sanitize(self) -> None:
        """Strip all PHI from payload before transmission."""
        self.payload = sanitize_phi(self.payload)
        self.phi_sanitized = True

    def sign(self) -> None:
        """HMAC-sign the envelope."""
        secret = _get_federation_secret()
        payload_bytes = json.dumps(self.payload, default=str, sort_keys=True).encode()
        self.hmac_signature = hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()

    def verify(self) -> bool:
        """Verify HMAC signature."""
        secret = _get_federation_secret()
        payload_bytes = json.dumps(self.payload, default=str, sort_keys=True).encode()
        expected = hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()
        return hmac.compare_digest(self.hmac_signature, expected)

    def is_expired(self) -> bool:
        try:
            sent = datetime.fromisoformat(self.timestamp)
            elapsed = (datetime.now(timezone.utc) - sent).total_seconds()
            return elapsed > self.ttl
        except (ValueError, TypeError):
            return True

    def prepare_for_send(self) -> bytes:
        """Sanitize, sign, and serialize for transmission."""
        if not self.phi_sanitized:
            self.sanitize()
        self.sign()
        payload = self.to_bytes()
        length = len(payload)
        return length.to_bytes(4, "big") + payload

    @classmethod
    async def read_from_stream(cls, reader) -> Optional[FederationEnvelope]:
        """Read a length-prefixed envelope from an async stream."""
        header = await reader.readexactly(4)
        if not header:
            return None
        length = int.from_bytes(header, "big")
        if length > 16 * 1024 * 1024:
            raise ValueError(f"Message too large: {length}")
        payload = await reader.readexactly(length)
        envelope = cls.from_bytes(payload)
        if not envelope.verify():
            raise FederationSecurityError(f"HMAC verification failed for {envelope.id}")
        if not envelope.phi_sanitized:
            raise FederationSecurityError(f"Message {envelope.id} not PHI-sanitized")
        if envelope.is_expired():
            raise FederationExpiredError(f"Message {envelope.id} expired")
        return envelope

    @classmethod
    def handshake(cls, site_id: str, site_name: str, capabilities: list[str],
                  organ_count: int = 82) -> FederationEnvelope:
        return cls(
            source_site=site_id, msg_type=FederationMessageType.HANDSHAKE,
            payload={
                "site_id": site_id, "site_name": site_name,
                "capabilities": capabilities, "organ_count": organ_count,
                "federation_version": "1.0",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @classmethod
    def heartbeat(cls, site_id: str, status: dict[str, Any]) -> FederationEnvelope:
        return cls(
            source_site=site_id, msg_type=FederationMessageType.HEARTBEAT, ttl=60,
            payload={"site_id": site_id, "status": status,
                     "timestamp": datetime.now(timezone.utc).isoformat()},
        )

    @classmethod
    def intel_share(cls, site_id: str, intel_type: str,
                    intel_data: dict[str, Any], dest: str = "") -> FederationEnvelope:
        return cls(
            source_site=site_id, dest_site=dest,
            msg_type=FederationMessageType.INTEL_SHARE, ttl=86400,
            payload={"intel_type": intel_type, "data": intel_data,
                     "shared_at": datetime.now(timezone.utc).isoformat()},
        )

    @classmethod
    def threat_bulletin(cls, site_id: str, threat_type: str, severity: str,
                        details: dict[str, Any]) -> FederationEnvelope:
        return cls(
            source_site=site_id, msg_type=FederationMessageType.THREAT_BULLETIN,
            ttl=86400,
            payload={"threat_type": threat_type, "severity": severity,
                     "details": details, "reporting_site": site_id,
                     "issued_at": datetime.now(timezone.utc).isoformat()},
        )


class FederationError(Exception):
    pass

class FederationSecurityError(FederationError):
    pass

class FederationExpiredError(FederationError):
    pass

class FederationConnectionError(FederationError):
    pass
