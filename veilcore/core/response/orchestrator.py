from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .actions import ACTION_MAP, ActionResult
from .policies import match_policy


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class ResponseContext:
    event: Dict[str, Any]
    chain_id: str
    policy_name: str


class ResponseOrchestrator:
    def __init__(self, event_store: Optional[str] = None, ledger_path: Optional[str] = None):
        self.event_store = Path(
            event_store
            or os.environ.get("VEIL_EVENT_STORE")
            or str(Path.home() / "veilcore" / "data" / "events.json")
        )
        self.ledger_path = Path(
            ledger_path
            or os.environ.get("VEIL_RESPONSE_LEDGER")
            or str(Path.home() / ".config" / "veilcore" / "response_chains.jsonl")
        )
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)

    def process_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        policy = match_policy(event)
        if not policy:
            return {"ok": False, "reason": "no_matching_policy", "event_type": event.get("type")}

        chain_id = str(uuid.uuid4())
        ctx = ResponseContext(
            event=event,
            chain_id=chain_id,
            policy_name=policy.description,
        )

        emitted: List[Dict[str, Any]] = []
        action_results: List[Dict[str, Any]] = []

        emitted.append(self._make_event(
            event_type="response.chain_started",
            level="info",
            message=f"Response chain started: {policy.description}",
            source="response",
            target=event.get("target"),
            payload={
                "chain_id": chain_id,
                "trigger_event_id": event.get("id"),
                "trigger_event_type": event.get("type"),
                "actions": policy.actions,
                "policy": policy.description,
            },
        ))

        for action_name in policy.actions:
            fn = ACTION_MAP.get(action_name)
            if not fn:
                result = {
                    "ok": False,
                    "action": action_name,
                    "message": "unknown action",
                    "payload": {},
                }
                emitted.append(self._make_event(
                    event_type="response.action_failed",
                    level="warning",
                    message=f"Unknown response action: {action_name}",
                    source="response",
                    target=event.get("target"),
                    payload={"chain_id": chain_id, "action": action_name},
                ))
                action_results.append(result)
                continue

            try:
                ar: ActionResult = fn(event)
                result = {
                    "ok": ar.ok,
                    "action": ar.action,
                    "message": ar.message,
                    "payload": ar.payload,
                }
                emitted.append(self._make_event(
                    event_type="response.action_executed" if ar.ok else "response.action_failed",
                    level="info" if ar.ok else "warning",
                    message=ar.message,
                    source="response",
                    target=event.get("target"),
                    payload={"chain_id": chain_id, "action": ar.action, **ar.payload},
                ))
                action_results.append(result)
            except Exception as e:
                result = {
                    "ok": False,
                    "action": action_name,
                    "message": f"exception: {e}",
                    "payload": {},
                }
                emitted.append(self._make_event(
                    event_type="response.action_failed",
                    level="warning",
                    message=f"{action_name} failed: {e}",
                    source="response",
                    target=event.get("target"),
                    payload={"chain_id": chain_id, "action": action_name},
                ))
                action_results.append(result)

        emitted.append(self._make_event(
            event_type="response.chain_completed",
            level="info",
            message=f"Response chain completed: {policy.description}",
            source="response",
            target=event.get("target"),
            payload={
                "chain_id": chain_id,
                "trigger_event_id": event.get("id"),
                "trigger_event_type": event.get("type"),
                "policy": policy.description,
                "results": action_results,
            },
        ))

        self._append_events(emitted)
        self._append_ledger({
            "ts": _now(),
            "chain_id": chain_id,
            "policy": policy.description,
            "trigger_event": event,
            "results": action_results,
        })

        return {
            "ok": True,
            "chain_id": chain_id,
            "policy": policy.description,
            "emitted_count": len(emitted),
            "results": action_results,
        }

    def _make_event(
        self,
        event_type: str,
        level: str,
        message: str,
        source: str,
        target: Optional[str],
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "id": str(uuid.uuid4()),
            "ts": _now(),
            "type": event_type,
            "source": source,
            "target": target,
            "level": level,
            "message": message,
            "payload": payload,
        }

    def _append_events(self, new_events: List[Dict[str, Any]]) -> None:
        self.event_store.parent.mkdir(parents=True, exist_ok=True)

        if self.event_store.exists():
            try:
                data = json.loads(self.event_store.read_text())
            except Exception:
                data = {"events": []}
        else:
            data = {"events": []}

        if not isinstance(data, dict):
            data = {"events": []}
        if "events" not in data or not isinstance(data["events"], list):
            data["events"] = []

        data["events"] = list(new_events) + data["events"]
        self.event_store.write_text(json.dumps(data, indent=2))

    def _append_ledger(self, row: Dict[str, Any]) -> None:
        with self.ledger_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
