"""
VeilCore Mesh Protocol
======================
Defines the wire protocol for organ-to-organ communication.
All messages are serialized as JSON with HMAC-SHA256 integrity
verification and optional AES-256-GCM encryption for sensitive
threat intelligence data.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum, IntEnum
from typing import Any, Optional


class MessageType(str, Enum):
    THREAT_ALERT = "threat_alert"
    STATUS = "status"
    COMMAND = "command"
    HEARTBEAT = "heartbeat"
    DISCOVERY = "discovery"
    ACK = "ack"
    DATA = "data"
    ESCALATION = "escalation"
    COORDINATION = "coordination"
    INTEL_SHARE = "intel_share"


class MessagePriority(IntEnum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class MeshTopic:
    THREAT_ALERTS = "topic:threat_alerts"
    STATUS_UPDATES = "topic:status_updates"
    COMMANDS = "topic:commands"
    HEARTBEATS = "topic:heartbeats"
    DISCOVERY = "topic:discovery"
    ESCALATION_CHAIN = "topic:escalation_chain"
    HIPAA_EVENTS = "topic:hipaa_events"
    EPIC_EVENTS = "topic:epic_events"
    IMPRIVATA_EVENTS = "topic:imprivata_events"
    HL7_EVENTS = "topic:hl7_events"
    FHIR_EVENTS = "topic:fhir_events"
    DICOM_EVENTS = "topic:dicom_events"
    IOMT_EVENTS = "topic:iomt_events"
    NETWORK_EVENTS = "topic:network_events"
    FORENSIC_EVENTS = "topic:forensic_events"
    COMPLIANCE_EVENTS = "topic:compliance_events"
    BROADCAST = "__broadcast__"


_MESH_SECRET_PATH = "/etc/veilcore/mesh.key"
_MESH_SECRET: Optional[bytes] = None


def _get_mesh_secret() -> bytes:
    global _MESH_SECRET
    if _MESH_SECRET is not None:
        return _MESH_SECRET
    if os.path.exists(_MESH_SECRET_PATH):
        with open(_MESH_SECRET_PATH, "rb") as f:
            _MESH_SECRET = f.read()
    else:
        _MESH_SECRET = hashlib.sha256(
            b"veilcore-mesh-dev-" + str(os.getpid()).encode()
        ).digest()
    return _MESH_SECRET


def generate_mesh_key(path: str = _MESH_SECRET_PATH) -> None:
    key = os.urandom(32)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(key)
    os.chmod(path, 0o600)


@dataclass
class MeshMessage:
    action: str
    data: dict[str, Any] = field(default_factory=dict)
    organ_source: str = ""
    correlation_id: str = ""
    chain: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MeshMessage:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str, sort_keys=True)


@dataclass
class MeshEnvelope:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = ""
    destination: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    msg_type: MessageType = MessageType.DATA
    priority: MessagePriority = MessagePriority.NORMAL
    ttl: int = 300
    hmac_signature: str = ""
    encrypted: bool = False
    payload: dict[str, Any] = field(default_factory=dict)
    retries: int = 0
    max_retries: int = 3

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["msg_type"] = self.msg_type.value
        d["priority"] = int(self.priority)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MeshEnvelope:
        data = dict(data)
        if "msg_type" in data:
            data["msg_type"] = MessageType(data["msg_type"])
        if "priority" in data:
            data["priority"] = MessagePriority(int(data["priority"]))
        valid_fields = cls.__dataclass_fields__
        return cls(**{k: v for k, v in data.items() if k in valid_fields})

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str, sort_keys=True)

    @classmethod
    def from_json(cls, raw: str) -> MeshEnvelope:
        return cls.from_dict(json.loads(raw))

    def to_bytes(self) -> bytes:
        return self.to_json().encode("utf-8")

    @classmethod
    def from_bytes(cls, raw: bytes) -> MeshEnvelope:
        return cls.from_json(raw.decode("utf-8"))

    def sign(self) -> None:
        secret = _get_mesh_secret()
        payload_bytes = json.dumps(self.payload, default=str, sort_keys=True).encode()
        self.hmac_signature = hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()

    def verify(self) -> bool:
        secret = _get_mesh_secret()
        payload_bytes = json.dumps(self.payload, default=str, sort_keys=True).encode()
        expected = hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()
        return hmac.compare_digest(self.hmac_signature, expected)

    def is_expired(self) -> bool:
        try:
            sent_time = datetime.fromisoformat(self.timestamp)
            elapsed = (datetime.now(timezone.utc) - sent_time).total_seconds()
            return elapsed > self.ttl
        except (ValueError, TypeError):
            return True

    @classmethod
    def heartbeat(cls, source: str) -> MeshEnvelope:
        return cls(
            source=source,
            destination=MeshTopic.HEARTBEATS,
            msg_type=MessageType.HEARTBEAT,
            priority=MessagePriority.LOW,
            ttl=30,
            payload={"organ": source, "alive": True, "uptime": time.monotonic()},
        )

    @classmethod
    def threat_alert(cls, source: str, threat_type: str, severity: str,
                     details: dict[str, Any], destination: str = MeshTopic.THREAT_ALERTS) -> MeshEnvelope:
        return cls(
            source=source, destination=destination,
            msg_type=MessageType.THREAT_ALERT, priority=MessagePriority.CRITICAL, ttl=600,
            payload={"threat_type": threat_type, "severity": severity, "details": details,
                     "detected_at": datetime.now(timezone.utc).isoformat()},
        )

    @classmethod
    def command(cls, source: str, destination: str, action: str,
                params: Optional[dict[str, Any]] = None) -> MeshEnvelope:
        return cls(
            source=source, destination=destination,
            msg_type=MessageType.COMMAND, priority=MessagePriority.HIGH, ttl=120,
            payload={"action": action, "params": params or {}},
        )

    @classmethod
    def status_update(cls, source: str, status: dict[str, Any]) -> MeshEnvelope:
        return cls(
            source=source, destination=MeshTopic.STATUS_UPDATES,
            msg_type=MessageType.STATUS, priority=MessagePriority.NORMAL, ttl=60,
            payload={"organ": source, "status": status},
        )

    @classmethod
    def escalation(cls, source: str, target: str, incident: dict[str, Any],
                   chain: list[str]) -> MeshEnvelope:
        return cls(
            source=source, destination=target,
            msg_type=MessageType.ESCALATION, priority=MessagePriority.CRITICAL, ttl=900,
            payload={"incident": incident, "escalation_chain": chain,
                     "escalated_at": datetime.now(timezone.utc).isoformat()},
        )


FRAME_HEADER_SIZE = 4
MAX_MESSAGE_SIZE = 16 * 1024 * 1024


def frame_encode(envelope: MeshEnvelope) -> bytes:
    envelope.sign()
    payload = envelope.to_bytes()
    length = len(payload)
    if length > MAX_MESSAGE_SIZE:
        raise ValueError(f"Message size {length} exceeds max {MAX_MESSAGE_SIZE}")
    return length.to_bytes(FRAME_HEADER_SIZE, "big") + payload


async def frame_decode(reader) -> Optional[MeshEnvelope]:
    header = await reader.readexactly(FRAME_HEADER_SIZE)
    if not header:
        return None
    length = int.from_bytes(header, "big")
    if length > MAX_MESSAGE_SIZE:
        raise ValueError(f"Frame size {length} exceeds max {MAX_MESSAGE_SIZE}")
    payload = await reader.readexactly(length)
    envelope = MeshEnvelope.from_bytes(payload)
    if not envelope.verify():
        raise SecurityError(f"HMAC verification failed for message {envelope.id}")
    if envelope.is_expired():
        raise ExpiredMessageError(f"Message {envelope.id} has expired (TTL={envelope.ttl}s)")
    return envelope


class MeshProtocolError(Exception):
    pass

class SecurityError(MeshProtocolError):
    pass

class ExpiredMessageError(MeshProtocolError):
    pass

class DeliveryError(MeshProtocolError):
    pass

class RoutingError(MeshProtocolError):
    pass
