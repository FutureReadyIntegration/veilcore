"""
VeilCore WebSocket Manager
============================
Real-time push communication to mobile clients.

Streams:
    - Live threat alerts
    - Organ status changes
    - ML predictions
    - Command execution results
    - Federation events
    - Mesh health updates
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, Set

from aiohttp import web, WSMsgType

logger = logging.getLogger("veilcore.mobile.websocket")


@dataclass
class WSClient:
    """Connected WebSocket client."""
    client_id: str
    ws: web.WebSocketResponse
    connected_at: float = field(default_factory=time.monotonic)
    messages_sent: int = 0
    subscriptions: set = field(default_factory=lambda: {"all"})
    operator: str = "unknown"

    @property
    def uptime(self) -> float:
        return time.monotonic() - self.connected_at


class WebSocketManager:
    """
    Manages real-time WebSocket connections.

    Usage:
        ws_mgr = WebSocketManager()
        # Register as aiohttp handler
        app.router.add_get("/ws", ws_mgr.handle_websocket)
        # Broadcast to all clients
        await ws_mgr.broadcast({"type": "alert", "data": {...}})
    """

    def __init__(self):
        self._clients: dict[str, WSClient] = {}
        self._client_counter = 0
        self._total_messages_sent = 0

    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """Handle incoming WebSocket connection."""
        ws = web.WebSocketResponse(heartbeat=30.0)
        await ws.prepare(request)

        self._client_counter += 1
        client_id = f"ws-{self._client_counter}"
        operator = request.get("operator", "unknown")

        client = WSClient(
            client_id=client_id, ws=ws, operator=operator,
        )
        self._clients[client_id] = client

        logger.info(f"WebSocket client connected: {client_id} (operator: {operator})")

        # Send welcome
        await self._send(client, {
            "type": "connected",
            "client_id": client_id,
            "message": "VeilCore Watchtower — live feed active",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    await self._handle_message(client, msg.data)
                elif msg.type == WSMsgType.ERROR:
                    logger.warning(f"WebSocket error for {client_id}: {ws.exception()}")
        except Exception as e:
            logger.debug(f"WebSocket disconnected: {client_id}: {e}")
        finally:
            del self._clients[client_id]
            logger.info(
                f"WebSocket client disconnected: {client_id} | "
                f"Uptime: {client.uptime:.0f}s | "
                f"Messages sent: {client.messages_sent}"
            )

        return ws

    async def _handle_message(self, client: WSClient, raw: str) -> None:
        """Handle incoming message from client."""
        try:
            data = json.loads(raw)
            msg_type = data.get("type", "")

            if msg_type == "subscribe":
                topics = data.get("topics", [])
                client.subscriptions.update(topics)
                await self._send(client, {
                    "type": "subscribed",
                    "topics": list(client.subscriptions),
                })

            elif msg_type == "unsubscribe":
                topics = data.get("topics", [])
                client.subscriptions -= set(topics)
                await self._send(client, {
                    "type": "unsubscribed",
                    "topics": list(client.subscriptions),
                })

            elif msg_type == "ping":
                await self._send(client, {
                    "type": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

        except json.JSONDecodeError:
            await self._send(client, {
                "type": "error",
                "message": "Invalid JSON",
            })

    async def broadcast(self, data: dict[str, Any], topic: str = "all") -> int:
        """Broadcast message to all subscribed clients."""
        data["broadcast_at"] = datetime.now(timezone.utc).isoformat()
        sent = 0
        for client in list(self._clients.values()):
            if topic in client.subscriptions or "all" in client.subscriptions:
                try:
                    await self._send(client, data)
                    sent += 1
                except Exception:
                    pass
        return sent

    async def send_to_client(self, client_id: str, data: dict[str, Any]) -> bool:
        """Send message to specific client."""
        client = self._clients.get(client_id)
        if not client:
            return False
        await self._send(client, data)
        return True

    async def _send(self, client: WSClient, data: dict[str, Any]) -> None:
        """Send data to a WebSocket client."""
        try:
            await client.ws.send_json(data)
            client.messages_sent += 1
            self._total_messages_sent += 1
        except Exception as e:
            logger.debug(f"Failed to send to {client.client_id}: {e}")

    @property
    def client_count(self) -> int:
        return len(self._clients)

    @property
    def total_messages(self) -> int:
        return self._total_messages_sent

    def get_clients(self) -> list[dict[str, Any]]:
        """Get connected client info."""
        return [
            {
                "client_id": c.client_id,
                "operator": c.operator,
                "uptime_seconds": round(c.uptime, 1),
                "messages_sent": c.messages_sent,
                "subscriptions": list(c.subscriptions),
            }
            for c in self._clients.values()
        ]

    def summary(self) -> dict[str, Any]:
        return {
            "connected_clients": self.client_count,
            "total_messages_sent": self._total_messages_sent,
            "clients": self.get_clients(),
        }
