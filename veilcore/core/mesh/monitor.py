"""
VeilCore Mesh Monitor
=====================
Real-time health monitoring, metrics collection, and alerting
for the organ mesh network.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable, Optional

from core.mesh.protocol import (
    MeshEnvelope, MeshTopic, MessageType, MessagePriority,
)
from core.mesh.client import MeshClient
from core.mesh.discovery import OrganDiscovery, OrganState, OrganTier

logger = logging.getLogger("veilcore.mesh.monitor")


class AlertLevel:
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class MeshAlert:
    level: str
    title: str
    message: str
    organ: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {"level": self.level, "title": self.title, "message": self.message,
                "organ": self.organ, "timestamp": self.timestamp}


class RateTracker:
    def __init__(self, window_seconds: float = 60.0):
        self._window = window_seconds
        self._events: deque[float] = deque()

    def record(self) -> None:
        now = time.monotonic()
        self._events.append(now)
        self._prune(now)

    def rate(self) -> float:
        now = time.monotonic()
        self._prune(now)
        if not self._events:
            return 0.0
        elapsed = now - self._events[0]
        return len(self._events) / elapsed if elapsed > 0 else float(len(self._events))

    def count(self) -> int:
        self._prune(time.monotonic())
        return len(self._events)

    def _prune(self, now: float) -> None:
        cutoff = now - self._window
        while self._events and self._events[0] < cutoff:
            self._events.popleft()


class MeshMonitor:
    def __init__(self, mesh_client: Optional[MeshClient] = None,
                 discovery: Optional[OrganDiscovery] = None,
                 check_interval: float = 15.0,
                 alert_callback: Optional[Callable[[MeshAlert], Awaitable[None]]] = None):
        self._client = mesh_client or MeshClient(
            organ_name="mesh-monitor",
            subscriptions=[MeshTopic.THREAT_ALERTS, MeshTopic.STATUS_UPDATES,
                           MeshTopic.DISCOVERY, MeshTopic.ESCALATION_CHAIN,
                           MeshTopic.HEARTBEATS, MeshTopic.HIPAA_EVENTS,
                           MeshTopic.EPIC_EVENTS, MeshTopic.NETWORK_EVENTS],
        )
        self._discovery = discovery or OrganDiscovery()
        self._check_interval = check_interval
        self._alert_callback = alert_callback
        self._running = False
        self._message_rate = RateTracker(window_seconds=60.0)
        self._threat_rate = RateTracker(window_seconds=300.0)
        self._error_rate = RateTracker(window_seconds=300.0)
        self._organ_message_counts: dict[str, int] = {}
        self._alerts: deque[MeshAlert] = deque(maxlen=1000)
        self._latencies: deque[float] = deque(maxlen=1000)
        self._mesh_status: dict[str, Any] = {}
        self._last_status_update: float = 0
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        logger.info("Starting mesh monitor...")
        connected = await self._client.connect_with_retry()
        if not connected:
            logger.error("Mesh monitor failed to connect")
            return
        self._client.on_message(self._on_any_message)
        self._client.on_type(MessageType.THREAT_ALERT, self._on_threat)
        self._client.on_type(MessageType.DISCOVERY, self._on_discovery)
        self._client.on_type(MessageType.STATUS, self._on_status)
        self._client.on_type(MessageType.ESCALATION, self._on_escalation)
        self._running = True
        self._tasks = [
            asyncio.create_task(self._health_check_loop(), name="health-check"),
            asyncio.create_task(self._discovery_scan_loop(), name="discovery-scan"),
        ]
        logger.info("Mesh monitor active — watching all 82 organs")

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        await self._client.disconnect()
        logger.info("Mesh monitor stopped")

    async def _on_any_message(self, envelope: MeshEnvelope) -> None:
        self._message_rate.record()
        source = envelope.source
        self._organ_message_counts[source] = self._organ_message_counts.get(source, 0) + 1
        try:
            sent = datetime.fromisoformat(envelope.timestamp)
            now = datetime.now(timezone.utc)
            latency_ms = (now - sent).total_seconds() * 1000
            self._latencies.append(latency_ms)
        except (ValueError, TypeError):
            pass

    async def _on_threat(self, envelope: MeshEnvelope) -> None:
        self._threat_rate.record()
        threat_type = envelope.payload.get("threat_type", "unknown")
        severity = envelope.payload.get("severity", "unknown")
        alert = MeshAlert(
            level=AlertLevel.CRITICAL if severity == "critical" else AlertLevel.WARNING,
            title=f"Threat Alert: {threat_type}",
            message=f"Organ '{envelope.source}' detected {threat_type} (severity: {severity})",
            organ=envelope.source,
        )
        await self._emit_alert(alert)

    async def _on_discovery(self, envelope: MeshEnvelope) -> None:
        event = envelope.payload.get("event", "")
        organ = envelope.payload.get("organ", "")
        total = envelope.payload.get("total_connected", 0)
        if event == "organ_connected":
            logger.info(f"📡 Organ '{organ}' joined mesh ({total}/82)")
        elif event == "organ_disconnected":
            alert = MeshAlert(level=AlertLevel.WARNING,
                              title=f"Organ Disconnected: {organ}",
                              message=f"Organ '{organ}' left the mesh ({total}/82 remaining)",
                              organ=organ)
            await self._emit_alert(alert)

    async def _on_status(self, envelope: MeshEnvelope) -> None:
        event = envelope.payload.get("event", "")
        organ = envelope.payload.get("organ", "")
        if event == "organ_unresponsive":
            self._error_rate.record()
            alert = MeshAlert(level=AlertLevel.CRITICAL,
                              title=f"Organ Unresponsive: {organ}",
                              message=f"Organ '{organ}' has stopped responding to heartbeats",
                              organ=organ)
            await self._emit_alert(alert)

    async def _on_escalation(self, envelope: MeshEnvelope) -> None:
        chain = envelope.payload.get("escalation_chain", [])
        alert = MeshAlert(level=AlertLevel.CRITICAL, title="Threat Escalation",
                          message=f"Escalation chain: {' -> '.join(chain)}",
                          organ=envelope.source)
        await self._emit_alert(alert)

    async def _emit_alert(self, alert: MeshAlert) -> None:
        self._alerts.append(alert)
        logger.warning(f"🚨 [{alert.level.upper()}] {alert.title}: {alert.message}")
        if self._alert_callback:
            try:
                await self._alert_callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

    async def _health_check_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(self._check_interval)
                await self._client.request_mesh_status()
                threat_count = self._threat_rate.count()
                if threat_count > 10:
                    alert = MeshAlert(level=AlertLevel.CRITICAL, title="High Threat Volume",
                                      message=f"{threat_count} threats detected in last 5 minutes")
                    await self._emit_alert(alert)
                error_count = self._error_rate.count()
                if error_count > 20:
                    alert = MeshAlert(level=AlertLevel.WARNING, title="Elevated Error Rate",
                                      message=f"{error_count} errors in last 5 minutes")
                    await self._emit_alert(alert)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def _discovery_scan_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(60)
                await self._discovery.scan()
                p0_organs = self._discovery.get_by_tier(OrganTier.P0_CRITICAL)
                offline_p0 = [o for o in p0_organs if o.state == OrganState.OFFLINE]
                if offline_p0:
                    names = ", ".join(o.display_name for o in offline_p0)
                    alert = MeshAlert(level=AlertLevel.CRITICAL, title="Critical Organs Offline",
                                      message=f"P0 critical organs down: {names}")
                    await self._emit_alert(alert)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Discovery scan error: {e}")

    def get_metrics(self) -> dict[str, Any]:
        latencies = list(self._latencies)
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        max_latency = max(latencies) if latencies else 0
        min_latency = min(latencies) if latencies else 0
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 20 else max_latency
        return {
            "mesh": {"message_rate_per_sec": round(self._message_rate.rate(), 2),
                     "threat_rate_5min": self._threat_rate.count(),
                     "error_rate_5min": self._error_rate.count(),
                     "total_messages_observed": sum(self._organ_message_counts.values())},
            "latency_ms": {"average": round(avg_latency, 2), "min": round(min_latency, 2),
                           "max": round(max_latency, 2), "p95": round(p95_latency, 2)},
            "organs": self._discovery.summary(),
            "alerts": {"total": len(self._alerts),
                       "recent": [a.to_dict() for a in list(self._alerts)[-10:]]},
            "per_organ_activity": dict(
                sorted(self._organ_message_counts.items(), key=lambda x: x[1], reverse=True)[:20]),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_alerts(self, limit: int = 50) -> list[dict[str, Any]]:
        return [a.to_dict() for a in list(self._alerts)[-limit:]]
