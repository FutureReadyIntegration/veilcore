"""
VeilCore Mesh Client
====================
Drop-in library for any VeilCore organ to join the mesh network.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional

from core.mesh.protocol import (
    MeshEnvelope, MeshTopic, MessageType, MessagePriority,
    frame_encode, frame_decode, MeshProtocolError, FRAME_HEADER_SIZE,
)

logger = logging.getLogger("veilcore.mesh.client")
MessageHandler = Callable[[MeshEnvelope], Awaitable[None]]


@dataclass
class ClientConfig:
    socket_path: str = "/run/veilcore/mesh.sock"
    heartbeat_interval: int = 10
    reconnect_delay: float = 1.0
    reconnect_max_delay: float = 30.0
    reconnect_max_attempts: int = 0
    receive_timeout: float = 60.0
    send_timeout: float = 5.0


class MeshClient:
    def __init__(self, organ_name: str, subscriptions: Optional[list[str]] = None,
                 config: Optional[ClientConfig] = None):
        self.organ_name = organ_name
        self._initial_subscriptions = subscriptions or []
        self.config = config or ClientConfig()
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._connected = False
        self._running = False
        self._handlers: dict[MessageType, list[MessageHandler]] = defaultdict(list)
        self._global_handlers: list[MessageHandler] = []
        self._topic_handlers: dict[str, list[MessageHandler]] = defaultdict(list)
        self._tasks: list[asyncio.Task] = []
        self.stats = {
            "messages_sent": 0, "messages_received": 0,
            "bytes_sent": 0, "bytes_received": 0,
            "reconnections": 0, "errors": 0, "connected_at": None,
        }

    async def connect(self) -> bool:
        if self._connected:
            return True
        try:
            logger.info(f"[{self.organ_name}] Connecting to mesh router at {self.config.socket_path}...")
            self._reader, self._writer = await asyncio.open_unix_connection(self.config.socket_path)
            registration = MeshEnvelope(
                source=self.organ_name, destination="mesh-router",
                msg_type=MessageType.DISCOVERY,
                payload={"organ": self.organ_name, "subscriptions": self._initial_subscriptions,
                         "pid": os.getpid(), "registered_at": datetime.now(timezone.utc).isoformat()},
            )
            await self._send_envelope(registration)
            ack = await asyncio.wait_for(frame_decode(self._reader), timeout=10.0)
            if ack is None or ack.msg_type != MessageType.ACK:
                logger.error(f"[{self.organ_name}] Registration rejected by router")
                return False
            self._connected = True
            self._running = True
            self.stats["connected_at"] = datetime.now(timezone.utc).isoformat()
            self._tasks = [
                asyncio.create_task(self._receive_loop(), name=f"{self.organ_name}-recv"),
                asyncio.create_task(self._heartbeat_loop(), name=f"{self.organ_name}-hb"),
            ]
            connected_organs = ack.payload.get("connected_organs", [])
            logger.info(f"[{self.organ_name}] ✓ Connected to mesh | Peers: {len(connected_organs)} organs online")
            return True
        except FileNotFoundError:
            logger.error(f"[{self.organ_name}] Mesh router socket not found. Is the router running?")
            return False
        except asyncio.TimeoutError:
            logger.error(f"[{self.organ_name}] Connection timed out")
            return False
        except Exception as e:
            logger.error(f"[{self.organ_name}] Connection failed: {e}")
            return False

    async def connect_with_retry(self) -> bool:
        delay = self.config.reconnect_delay
        attempts = 0
        while True:
            if await self.connect():
                return True
            attempts += 1
            if self.config.reconnect_max_attempts > 0 and attempts >= self.config.reconnect_max_attempts:
                logger.error(f"[{self.organ_name}] Max reconnect attempts reached")
                return False
            logger.info(f"[{self.organ_name}] Retrying in {delay:.1f}s (attempt {attempts})...")
            await asyncio.sleep(delay)
            delay = min(delay * 2, self.config.reconnect_max_delay)
            self.stats["reconnections"] += 1

    async def disconnect(self) -> None:
        self._running = False
        self._connected = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
            self._reader = None
        logger.info(f"[{self.organ_name}] Disconnected from mesh")

    async def __aenter__(self) -> MeshClient:
        await self.connect_with_retry()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.disconnect()

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def _send_envelope(self, envelope: MeshEnvelope) -> bool:
        if not self._writer:
            logger.warning(f"[{self.organ_name}] Cannot send: not connected")
            return False
        try:
            data = frame_encode(envelope)
            self._writer.write(data)
            await asyncio.wait_for(self._writer.drain(), timeout=self.config.send_timeout)
            self.stats["messages_sent"] += 1
            self.stats["bytes_sent"] += len(data)
            return True
        except (ConnectionError, OSError) as e:
            logger.error(f"[{self.organ_name}] Send failed: {e}")
            self.stats["errors"] += 1
            self._connected = False
            asyncio.create_task(self._auto_reconnect())
            return False
        except asyncio.TimeoutError:
            logger.warning(f"[{self.organ_name}] Send timed out")
            self.stats["errors"] += 1
            return False

    async def send(self, destination: str, msg_type: MessageType, payload: dict[str, Any],
                   priority: MessagePriority = MessagePriority.NORMAL, ttl: int = 300) -> bool:
        envelope = MeshEnvelope(
            source=self.organ_name, destination=destination,
            msg_type=msg_type, priority=priority, ttl=ttl, payload=payload,
        )
        return await self._send_envelope(envelope)

    async def send_to_organ(self, target: str, action: str, data: dict[str, Any] = None) -> bool:
        return await self.send(destination=target, msg_type=MessageType.DATA,
                               payload={"action": action, "data": data or {}})

    async def publish(self, topic: str, payload: dict[str, Any],
                      priority: MessagePriority = MessagePriority.NORMAL) -> bool:
        return await self.send(destination=topic, msg_type=MessageType.DATA,
                               priority=priority, payload=payload)

    async def broadcast(self, payload: dict[str, Any],
                        priority: MessagePriority = MessagePriority.NORMAL) -> bool:
        return await self.send(destination=MeshTopic.BROADCAST, msg_type=MessageType.DATA,
                               priority=priority, payload=payload)

    async def send_threat_alert(self, threat_type: str, severity: str, details: dict[str, Any],
                                 target: str = MeshTopic.THREAT_ALERTS) -> bool:
        envelope = MeshEnvelope.threat_alert(source=self.organ_name, threat_type=threat_type,
                                              severity=severity, details=details, destination=target)
        return await self._send_envelope(envelope)

    async def send_status_update(self, status: dict[str, Any]) -> bool:
        envelope = MeshEnvelope.status_update(source=self.organ_name, status=status)
        return await self._send_envelope(envelope)

    async def send_command(self, target: str, action: str, params: dict[str, Any] = None) -> bool:
        envelope = MeshEnvelope.command(source=self.organ_name, destination=target,
                                        action=action, params=params)
        return await self._send_envelope(envelope)

    async def escalate(self, target: str, incident: dict[str, Any], chain: list[str] = None) -> bool:
        if chain is None:
            chain = [self.organ_name]
        elif self.organ_name not in chain:
            chain.append(self.organ_name)
        envelope = MeshEnvelope.escalation(source=self.organ_name, target=target,
                                            incident=incident, chain=chain)
        return await self._send_envelope(envelope)

    async def request_mesh_status(self) -> bool:
        return await self.send(destination="mesh-router", msg_type=MessageType.COMMAND,
                               payload={"action": "get_mesh_status"})

    async def subscribe(self, topic: str) -> bool:
        return await self.send(destination="mesh-router", msg_type=MessageType.COMMAND,
                               payload={"action": "subscribe", "topic": topic})

    async def unsubscribe(self, topic: str) -> bool:
        return await self.send(destination="mesh-router", msg_type=MessageType.COMMAND,
                               payload={"action": "unsubscribe", "topic": topic})

    def on_message(self, handler: MessageHandler) -> None:
        self._global_handlers.append(handler)

    def on_type(self, msg_type: MessageType, handler: MessageHandler) -> None:
        self._handlers[msg_type].append(handler)

    def on_topic(self, topic: str, handler: MessageHandler) -> None:
        self._topic_handlers[topic].append(handler)

    def on_threat(self, handler: MessageHandler) -> None:
        self.on_type(MessageType.THREAT_ALERT, handler)

    def on_command(self, handler: MessageHandler) -> None:
        self.on_type(MessageType.COMMAND, handler)

    def on_escalation(self, handler: MessageHandler) -> None:
        self.on_type(MessageType.ESCALATION, handler)

    def on_status(self, handler: MessageHandler) -> None:
        self.on_type(MessageType.STATUS, handler)

    async def _dispatch_to_handlers(self, envelope: MeshEnvelope) -> None:
        for handler in self._handlers.get(envelope.msg_type, []):
            try:
                await handler(envelope)
            except Exception as e:
                logger.error(f"[{self.organ_name}] Handler error ({envelope.msg_type}): {e}")
        if envelope.destination.startswith("topic:"):
            for handler in self._topic_handlers.get(envelope.destination, []):
                try:
                    await handler(envelope)
                except Exception as e:
                    logger.error(f"[{self.organ_name}] Topic handler error: {e}")
        for handler in self._global_handlers:
            try:
                await handler(envelope)
            except Exception as e:
                logger.error(f"[{self.organ_name}] Global handler error: {e}")

    async def _receive_loop(self) -> None:
        while self._running and self._reader:
            try:
                envelope = await asyncio.wait_for(frame_decode(self._reader),
                                                   timeout=self.config.receive_timeout)
                if envelope is None:
                    logger.warning(f"[{self.organ_name}] Connection closed by router")
                    self._connected = False
                    asyncio.create_task(self._auto_reconnect())
                    break
                self.stats["messages_received"] += 1
                await self._dispatch_to_handlers(envelope)
            except asyncio.TimeoutError:
                continue
            except asyncio.IncompleteReadError:
                logger.warning(f"[{self.organ_name}] Connection lost")
                self._connected = False
                asyncio.create_task(self._auto_reconnect())
                break
            except asyncio.CancelledError:
                break
            except MeshProtocolError as e:
                logger.warning(f"[{self.organ_name}] Protocol error: {e}")
                self.stats["errors"] += 1
            except Exception as e:
                logger.error(f"[{self.organ_name}] Receive error: {e}")
                self.stats["errors"] += 1

    async def _heartbeat_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(self.config.heartbeat_interval)
                if self._connected:
                    heartbeat = MeshEnvelope.heartbeat(self.organ_name)
                    await self._send_envelope(heartbeat)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"[{self.organ_name}] Heartbeat error: {e}")

    async def _auto_reconnect(self) -> None:
        if not self._running:
            return
        logger.info(f"[{self.organ_name}] Attempting auto-reconnect...")
        await self.disconnect()
        await asyncio.sleep(self.config.reconnect_delay)
        await self.connect_with_retry()
