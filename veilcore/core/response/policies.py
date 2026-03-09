from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ResponsePolicy:
    event_type: str
    min_level: str
    actions: List[str]
    description: str


_LEVEL_ORDER = {
    "info": 10,
    "warning": 20,
    "critical": 30,
}


def level_value(level: str) -> int:
    return _LEVEL_ORDER.get(str(level or "").lower(), 0)


POLICIES: Dict[str, ResponsePolicy] = {
    "physical.sensor_triggered": ResponsePolicy(
        event_type="physical.sensor_triggered",
        min_level="critical",
        actions=[
            "lock_badge",
            "isolate_vlan",
            "revoke_session",
            "sinkhole_connection",
            "capture_injected_artifacts",
            "snapshot_host",
            "alert_operator",
        ],
        description="Physical intrusion containment chain",
    ),
    "physical.camera_feed_lost": ResponsePolicy(
        event_type="physical.camera_feed_lost",
        min_level="critical",
        actions=[
            "lock_badge",
            "revoke_session",
            "sinkhole_connection",
            "capture_injected_artifacts",
            "alert_operator",
        ],
        description="Camera loss containment chain",
    ),
    "engine.degraded": ResponsePolicy(
        event_type="engine.degraded",
        min_level="warning",
        actions=[
            "capture_injected_artifacts",
            "snapshot_host",
            "alert_operator",
        ],
        description="Engine degradation containment chain",
    ),
}


def match_policy(event: dict) -> Optional[ResponsePolicy]:
    event_type = str(event.get("type", "")).strip()
    level = str(event.get("level", "")).strip().lower()
    policy = POLICIES.get(event_type)
    if not policy:
        return None
    if level_value(level) < level_value(policy.min_level):
        return None
    return policy
