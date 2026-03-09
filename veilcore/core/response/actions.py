from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict


@dataclass
class ActionResult:
    ok: bool
    action: str
    message: str
    payload: Dict[str, Any]


def _ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _payload_dict(ctx: dict) -> dict:
    p = ctx.get("payload", {})
    return p if isinstance(p, dict) else {}


def lock_badge(ctx: dict) -> ActionResult:
    target = ctx.get("target") or _payload_dict(ctx).get("location") or "unknown_target"
    return ActionResult(
        ok=True,
        action="lock_badge",
        message=f"Badge system locked for {target}",
        payload={"target": target, "locked_at": _ts(), "mode": "simulated"},
    )


def isolate_vlan(ctx: dict) -> ActionResult:
    zone = _payload_dict(ctx).get("zone") or "unknown_zone"
    return ActionResult(
        ok=True,
        action="isolate_vlan",
        message=f"VLAN isolated for zone={zone}",
        payload={"zone": zone, "isolated_at": _ts(), "mode": "simulated"},
    )


def revoke_session(ctx: dict) -> ActionResult:
    payload = _payload_dict(ctx)
    session_ref = (
        payload.get("session_id")
        or payload.get("token_id")
        or ctx.get("target")
        or "unknown_session"
    )
    return ActionResult(
        ok=True,
        action="revoke_session",
        message=f"Unauthorized session revoked for {session_ref}",
        payload={"session_ref": session_ref, "revoked_at": _ts(), "mode": "simulated"},
    )


def sinkhole_connection(ctx: dict) -> ActionResult:
    payload = _payload_dict(ctx)
    zone = payload.get("zone") or "unknown_zone"
    target = ctx.get("target") or payload.get("camera_id") or payload.get("sensor_id") or payload.get("name") or "unknown_target"
    return ActionResult(
        ok=True,
        action="sinkhole_connection",
        message=f"Hostile path sinkholed away from core for {target}",
        payload={
            "target": target,
            "zone": zone,
            "sinkhole": "quarantine-net",
            "sinkholed_at": _ts(),
            "mode": "simulated",
        },
    )


def capture_injected_artifacts(ctx: dict) -> ActionResult:
    payload = _payload_dict(ctx)
    artifact_blob = {
        "event_id": ctx.get("id"),
        "event_type": ctx.get("type"),
        "source": ctx.get("source"),
        "target": ctx.get("target"),
        "level": ctx.get("level"),
        "message": ctx.get("message"),
        "payload": payload,
    }
    raw = json.dumps(artifact_blob, sort_keys=True).encode("utf-8", errors="replace")
    digest = hashlib.sha256(raw).hexdigest()
    indicators = sorted(payload.keys())
    return ActionResult(
        ok=True,
        action="capture_injected_artifacts",
        message=f"Hostile artifacts captured and hashed ({digest[:12]})",
        payload={
            "sha256": digest,
            "captured_at": _ts(),
            "indicator_keys": indicators,
            "bytes": len(raw),
            "mode": "simulated",
        },
    )


def snapshot_host(ctx: dict) -> ActionResult:
    payload = _payload_dict(ctx)
    target = (
        ctx.get("target")
        or payload.get("camera_id")
        or payload.get("sensor_id")
        or payload.get("name")
        or payload.get("service")
        or ctx.get("source")
        or "unknown_host"
    )
    return ActionResult(
        ok=True,
        action="snapshot_host",
        message=f"Snapshot captured for {target}",
        payload={"target": target, "snapshot_at": _ts(), "mode": "simulated"},
    )


def alert_operator(ctx: dict) -> ActionResult:
    event_type = ctx.get("type", "unknown_event")
    level = ctx.get("level", "unknown_level")
    return ActionResult(
        ok=True,
        action="alert_operator",
        message=f"Operator alerted for {event_type} ({level})",
        payload={"event_type": event_type, "level": level, "alerted_at": _ts(), "mode": "simulated"},
    )


ACTION_MAP = {
    "lock_badge": lock_badge,
    "isolate_vlan": isolate_vlan,
    "revoke_session": revoke_session,
    "sinkhole_connection": sinkhole_connection,
    "capture_injected_artifacts": capture_injected_artifacts,
    "snapshot_host": snapshot_host,
    "alert_operator": alert_operator,
}
