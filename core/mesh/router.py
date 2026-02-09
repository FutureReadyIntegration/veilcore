"""
VeilCore Mesh Router
====================
The central nervous system hub of VeilCore. All 82 security organs
connect to the MeshRouter via Unix domain sockets.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import time
from asyncio import PriorityQueue, StreamReader, StreamWriter
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from core.mesh.protocol import (
    MeshEnvelope, MeshTopic, MessageType, MessagePriority,
    frame_encode, frame_decode, MeshProtocolError, SecurityError,
    ExpiredMessageError, RoutingError, FRAME_HEADER_SIZE,
)

logger = logging.getLogger("veilcore.mesh.router")


@dataclass
class RouterConfig:
    socket_path: str = "/run/veilcore/mesh.sock"
    ledger_path: str = "/var/log/veilcore/mesh-ledger.jsonl"
    dead_letter_path: str = "/var/log/veilcore/mesh-dead-letters.jsonl"
    max_connections: int = 128
    heartbeat_interval: int = 15
    heartbeat_timeout: int = 45
    max_queue_size: int = 10_000
    rate_limit_per_organ: int = 500
    rate_limit_window: float = 1.0
    cleanup_interval: int = 60
    stats_interval: int = 30
    enable_ledger: bool = True
    socket_permissions: int = 0o770
    pid_file: str = "/run/veilcore/mesh-router.pid"

    @classmethod
    def from_yaml(cls, path: str) -> RouterConfig:
        try:
            import yaml
        except ImportError:
            logger.warning("PyYAML not installed, using defaults")
            return cls()
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        mesh_cfg = data.get("mesh", data)
        return cls(**{k: v for k, v in mesh_cfg.items() if k in cls.__dataclass_fields__})


@dataclass
class ConnectedOrgan:
    name: str
    writer: StreamWriter
    connected_at: float = field(default_factory=time.monotonic)
    last_heartbeat: float = field(default_factory=time.monotonic)
    subscriptions: set[str] = field(default_factory=set)
    messages_sent: int = 0
    messages_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    errors: int = 0
    _rate_window_start: float = field(default_factory=time.monotonic)
    _rate_count: int = 0

    @property
    def is_alive(self) -> bool:
        return (time.monotonic() - self.last_heartbeat) < 45

    @property
    def uptime(self) -> float:
        return time.monotonic() - self.connected_at

    def check_rate_limit(self, limit: int, window: float) -> bool:
        now = time.monotonic()
        if now - self._rate_window_start > window:
            self._rate_window_start = now
            self._rate_count = 0
        self._rate_count += 1
        return self._rate_count <= limit

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name, "connected_at": self.connected_at,
            "last_heartbeat": self.last_heartbeat,
            "subscriptions": list(self.subscriptions),
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "bytes_sent": self.bytes_sent, "bytes_received": self.bytes_received,
            "errors": self.errors, "is_alive": self.is_alive,
            "uptime_seconds": round(self.uptime, 2),
        }


@dataclass(order=True)
class PrioritizedEnvelope:
    sort_key: int
    timestamp: float = field(compare=True)
    envelope: MeshEnvelope = field(compare=False)

    @classmethod
    def from_envelope(cls, env: MeshEnvelope) -> PrioritizedEnvelope:
        return cls(sort_key=-int(env.priority), timestamp=time.monotonic(), envelope=env)


class MeshRouter:
    def __init__(self, config: Optional[RouterConfig] = None):
        self.config = config or RouterConfig()
        self._server: Optional[asyncio.AbstractServer] = None
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._organs: dict[str, ConnectedOrgan] = {}
        self._writer_to_organ: dict[StreamWriter, str] = {}
        self._subscriptions: dict[str, set[str]] = defaultdict(set)
        self._dispatch_queue: PriorityQueue[PrioritizedEnvelope] = PriorityQueue(
            maxsize=self.config.max_queue_size
        )
        self._dead_letters: list[dict[str, Any]] = []
        self._stats = {
            "total_messages_routed": 0, "total_messages_dropped": 0,
            "total_messages_dead_lettered": 0, "total_bytes_routed": 0,
            "total_connections": 0, "total_disconnections": 0,
            "total_security_violations": 0, "started_at": None,
        }
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        if self._running:
            return
        logger.info("╔══════════════════════════════════════════════════╗")
        logger.info("║        VEILCORE MESH ROUTER — STARTING          ║")
        logger.info("║     The nervous system of hospital defense       ║")
        logger.info("╚══════════════════════════════════════════════════╝")

        socket_dir = os.path.dirname(self.config.socket_path)
        os.makedirs(socket_dir, exist_ok=True)
        if os.path.exists(self.config.socket_path):
            os.unlink(self.config.socket_path)
        for path in [self.config.ledger_path, self.config.dead_letter_path]:
            os.makedirs(os.path.dirname(path), exist_ok=True)

        self._server = await asyncio.start_unix_server(
            self._handle_connection, path=self.config.socket_path,
        )
        os.chmod(self.config.socket_path, self.config.socket_permissions)
        self._running = True
        self._stats["started_at"] = datetime.now(timezone.utc).isoformat()

        pid_dir = os.path.dirname(self.config.pid_file)
        os.makedirs(pid_dir, exist_ok=True)
        with open(self.config.pid_file, "w") as f:
            f.write(str(os.getpid()))

        self._tasks = [
            asyncio.create_task(self._dispatch_loop(), name="dispatch"),
            asyncio.create_task(self._heartbeat_monitor(), name="heartbeat_monitor"),
            asyncio.create_task(self._cleanup_loop(), name="cleanup"),
            asyncio.create_task(self._stats_logger(), name="stats_logger"),
        ]
        logger.info(f"Mesh router listening on {self.config.socket_path}")
        logger.info("Awaiting organ connections...")

    async def stop(self) -> None:
        if not self._running:
            return
        logger.info("Mesh router shutting down...")
        self._running = False
        self._shutdown_event.set()
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        for organ in list(self._organs.values()):
            try:
                organ.writer.close()
                await organ.writer.wait_closed()
            except Exception:
                pass
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        for path in [self.config.socket_path, self.config.pid_file]:
            if os.path.exists(path):
                os.unlink(path)
        if self._dead_letters:
            await self._flush_dead_letters()
        logger.info("Mesh router stopped.")

    async def __aenter__(self) -> MeshRouter:
        await self.start()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.stop()

    async def wait_shutdown(self) -> None:
        await self._shutdown_event.wait()

    async def _handle_connection(self, reader: StreamReader, writer: StreamWriter) -> None:
        organ_name = None
        try:
            envelope = await asyncio.wait_for(frame_decode(reader), timeout=10.0)
            if envelope is None or envelope.msg_type != MessageType.DISCOVERY:
                logger.warning("Connection rejected: first message must be DISCOVERY registration")
                writer.close()
                await writer.wait_closed()
                return
            organ_name = envelope.source
            if not organ_name:
                logger.warning("Connection rejected: empty organ name")
                writer.close()
                await writer.wait_closed()
                return
            if organ_name in self._organs:
                old = self._organs[organ_name]
                logger.info(f"Organ '{organ_name}' reconnecting, closing old connection")
                try:
                    old.writer.close()
                    await old.writer.wait_closed()
                except Exception:
                    pass
            organ = ConnectedOrgan(name=organ_name, writer=writer)
            self._organs[organ_name] = organ
            self._writer_to_organ[writer] = organ_name
            self._stats["total_connections"] += 1
            subs = envelope.payload.get("subscriptions", [])
            for topic in subs:
                self._subscriptions[topic].add(organ_name)
                organ.subscriptions.add(topic)
            logger.info(
                f"✓ Organ '{organ_name}' connected | "
                f"Subscriptions: {subs} | Total connected: {len(self._organs)}/82"
            )
            ack = MeshEnvelope(
                source="mesh-router", destination=organ_name,
                msg_type=MessageType.ACK, priority=MessagePriority.NORMAL,
                payload={"status": "registered", "organ": organ_name,
                         "connected_organs": list(self._organs.keys())},
            )
            await self._send_to_writer(writer, ack)
            discovery_notice = MeshEnvelope(
                source="mesh-router", destination=MeshTopic.DISCOVERY,
                msg_type=MessageType.DISCOVERY,
                payload={"event": "organ_connected", "organ": organ_name,
                         "total_connected": len(self._organs)},
            )
            await self._enqueue(discovery_notice)
            while self._running:
                try:
                    envelope = await asyncio.wait_for(frame_decode(reader), timeout=60.0)
                    if envelope is None:
                        break
                    await self._process_message(organ_name, envelope)
                except asyncio.TimeoutError:
                    continue
                except asyncio.IncompleteReadError:
                    break
                except (SecurityError, ExpiredMessageError) as e:
                    organ.errors += 1
                    self._stats["total_security_violations"] += 1
                    logger.warning(f"Security violation from '{organ_name}': {e}")
                except MeshProtocolError as e:
                    organ.errors += 1
                    logger.error(f"Protocol error from '{organ_name}': {e}")
        except asyncio.TimeoutError:
            logger.warning("Connection timed out waiting for registration")
        except Exception as e:
            logger.error(f"Connection handler error for '{organ_name}': {e}")
        finally:
            await self._disconnect_organ(organ_name, writer)

    async def _disconnect_organ(self, organ_name: Optional[str], writer: StreamWriter) -> None:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
        if writer in self._writer_to_organ:
            del self._writer_to_organ[writer]
        if organ_name and organ_name in self._organs:
            organ = self._organs.pop(organ_name)
            self._stats["total_disconnections"] += 1
            for topic in organ.subscriptions:
                self._subscriptions[topic].discard(organ_name)
            logger.info(
                f"✗ Organ '{organ_name}' disconnected | "
                f"Uptime: {organ.uptime:.1f}s | "
                f"Messages: sent={organ.messages_sent} recv={organ.messages_received} | "
                f"Total connected: {len(self._organs)}/82"
            )
            notice = MeshEnvelope(
                source="mesh-router", destination=MeshTopic.DISCOVERY,
                msg_type=MessageType.DISCOVERY,
                payload={"event": "organ_disconnected", "organ": organ_name,
                         "total_connected": len(self._organs)},
            )
            await self._enqueue(notice)

    async def _process_message(self, source: str, envelope: MeshEnvelope) -> None:
        organ = self._organs.get(source)
        if not organ:
            return
        if not organ.check_rate_limit(self.config.rate_limit_per_organ, self.config.rate_limit_window):
            logger.warning(f"Rate limit exceeded for organ '{source}', dropping message")
            self._stats["total_messages_dropped"] += 1
            return
        organ.messages_received += 1
        if envelope.msg_type == MessageType.HEARTBEAT:
            organ.last_heartbeat = time.monotonic()
            return
        if envelope.msg_type == MessageType.COMMAND:
            action = envelope.payload.get("action")
            if action == "subscribe":
                topic = envelope.payload.get("topic", "")
                if topic:
                    self._subscriptions[topic].add(source)
                    organ.subscriptions.add(topic)
                return
            elif action == "unsubscribe":
                topic = envelope.payload.get("topic", "")
                if topic:
                    self._subscriptions[topic].discard(source)
                    organ.subscriptions.discard(topic)
                return
            elif action == "get_mesh_status":
                status = self._get_mesh_status()
                reply = MeshEnvelope(source="mesh-router", destination=source,
                                     msg_type=MessageType.DATA, payload=status)
                await self._send_to_organ(source, reply)
                return
        await self._enqueue(envelope)
        if self.config.enable_ledger:
            await self._log_to_ledger(envelope)

    async def _enqueue(self, envelope: MeshEnvelope) -> None:
        try:
            prioritized = PrioritizedEnvelope.from_envelope(envelope)
            self._dispatch_queue.put_nowait(prioritized)
        except asyncio.QueueFull:
            logger.error("Dispatch queue full, dropping message")
            self._stats["total_messages_dropped"] += 1

    async def _dispatch_loop(self) -> None:
        logger.info("Dispatch engine started")
        while self._running:
            try:
                prioritized = await asyncio.wait_for(self._dispatch_queue.get(), timeout=1.0)
                envelope = prioritized.envelope
                await self._route_message(envelope)
                self._stats["total_messages_routed"] += 1
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Dispatch error: {e}")

    async def _route_message(self, envelope: MeshEnvelope) -> None:
        dest = envelope.destination
        if dest == MeshTopic.BROADCAST:
            for name in self._organs:
                if name != envelope.source:
                    await self._send_to_organ(name, envelope)
            return
        if dest.startswith("topic:"):
            subscribers = self._subscriptions.get(dest, set())
            for name in subscribers:
                if name != envelope.source:
                    await self._send_to_organ(name, envelope)
            return
        if dest in self._organs:
            await self._send_to_organ(dest, envelope)
            return
        logger.warning(f"No route for message {envelope.id} -> '{dest}'")
        await self._dead_letter(envelope, reason=f"No route to '{dest}'")

    async def _send_to_organ(self, name: str, envelope: MeshEnvelope) -> None:
        organ = self._organs.get(name)
        if not organ:
            await self._dead_letter(envelope, reason=f"Organ '{name}' not connected")
            return
        try:
            data = frame_encode(envelope)
            organ.writer.write(data)
            await organ.writer.drain()
            organ.messages_sent += 1
            organ.bytes_sent += len(data)
            self._stats["total_bytes_routed"] += len(data)
        except (ConnectionError, OSError) as e:
            logger.warning(f"Failed to send to '{name}': {e}")
            if envelope.retries < envelope.max_retries:
                envelope.retries += 1
                await self._enqueue(envelope)
            else:
                await self._dead_letter(envelope, reason=f"Delivery failed after {envelope.max_retries} retries")

    async def _send_to_writer(self, writer: StreamWriter, envelope: MeshEnvelope) -> None:
        try:
            data = frame_encode(envelope)
            writer.write(data)
            await writer.drain()
        except Exception as e:
            logger.warning(f"Failed to send to writer: {e}")

    async def _dead_letter(self, envelope: MeshEnvelope, reason: str) -> None:
        entry = {
            "message_id": envelope.id, "source": envelope.source,
            "destination": envelope.destination, "msg_type": envelope.msg_type.value,
            "priority": int(envelope.priority), "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload_summary": str(envelope.payload)[:500],
        }
        self._dead_letters.append(entry)
        self._stats["total_messages_dead_lettered"] += 1
        if len(self._dead_letters) >= 50:
            await self._flush_dead_letters()

    async def _flush_dead_letters(self) -> None:
        if not self._dead_letters:
            return
        try:
            with open(self.config.dead_letter_path, "a") as f:
                for entry in self._dead_letters:
                    f.write(json.dumps(entry, default=str) + "\n")
            self._dead_letters.clear()
        except Exception as e:
            logger.error(f"Failed to flush dead letters: {e}")

    async def _log_to_ledger(self, envelope: MeshEnvelope) -> None:
        try:
            entry = {
                "id": envelope.id, "source": envelope.source,
                "destination": envelope.destination, "msg_type": envelope.msg_type.value,
                "priority": int(envelope.priority), "timestamp": envelope.timestamp,
                "logged_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(self.config.ledger_path, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            logger.error(f"Ledger write failed: {e}")

    async def _heartbeat_monitor(self) -> None:
        logger.info("Heartbeat monitor started")
        while self._running:
            try:
                await asyncio.sleep(self.config.heartbeat_interval)
                now = time.monotonic()
                for name, organ in list(self._organs.items()):
                    silence = now - organ.last_heartbeat
                    if silence > self.config.heartbeat_timeout:
                        logger.warning(
                            f"⚠ Organ '{name}' missed heartbeat "
                            f"({silence:.0f}s since last) — marking unresponsive"
                        )
                        alert = MeshEnvelope(
                            source="mesh-router", destination=MeshTopic.STATUS_UPDATES,
                            msg_type=MessageType.STATUS, priority=MessagePriority.HIGH,
                            payload={"event": "organ_unresponsive", "organ": name,
                                     "silent_seconds": round(silence, 1)},
                        )
                        await self._enqueue(alert)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat monitor error: {e}")

    async def _cleanup_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                empty_topics = [t for t, s in self._subscriptions.items() if not s]
                for topic in empty_topics:
                    del self._subscriptions[topic]
                await self._flush_dead_letters()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

    async def _stats_logger(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(self.config.stats_interval)
                connected = len(self._organs)
                queued = self._dispatch_queue.qsize()
                total = self._stats["total_messages_routed"]
                logger.info(
                    f"📊 Mesh stats | Organs: {connected}/82 | "
                    f"Queued: {queued} | Routed: {total} | "
                    f"Dead: {self._stats['total_messages_dead_lettered']}"
                )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Stats logger error: {e}")

    def _get_mesh_status(self) -> dict[str, Any]:
        return {
            "router": {
                "running": self._running, "started_at": self._stats["started_at"],
                "socket_path": self.config.socket_path,
                "queue_size": self._dispatch_queue.qsize(),
                "max_queue_size": self.config.max_queue_size,
            },
            "organs": {
                "total_connected": len(self._organs), "target": 82,
                "connected": {name: organ.to_dict() for name, organ in self._organs.items()},
            },
            "subscriptions": {topic: list(subs) for topic, subs in self._subscriptions.items()},
            "statistics": dict(self._stats),
            "dead_letters_pending": len(self._dead_letters),
        }

    @property
    def connected_organs(self) -> list[str]:
        return list(self._organs.keys())

    @property
    def organ_count(self) -> int:
        return len(self._organs)

    @property
    def is_running(self) -> bool:
        return self._running


async def _run_router() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="VeilCore Mesh Router")
    parser.add_argument("--config", "-c", default="/etc/veilcore/mesh.yaml")
    parser.add_argument("--socket", "-s", default=None)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    if os.path.exists(args.config):
        config = RouterConfig.from_yaml(args.config)
    else:
        config = RouterConfig()
    if args.socket:
        config.socket_path = args.socket
    loop = asyncio.get_running_loop()
    router = MeshRouter(config)
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(router.stop()))
    async with router:
        await router.wait_shutdown()


def main() -> None:
    asyncio.run(_run_router())


if __name__ == "__main__":
    main()
