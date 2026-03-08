"""
VeilCore Federation Hub
========================
Central coordinator for multi-site hospital federation.

The hub manages site connections, routes intel between sites,
and coordinates distributed incident response. It can run as
a dedicated service or be embedded in any VeilCore site.

Architecture:
    - Accepts TCP connections from federation sites
    - Mutual authentication via handshake protocol
    - Routes intel_share and threat_bulletin messages
    - Tracks site health via heartbeats
    - Maintains federation-wide threat picture
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from asyncio import StreamReader, StreamWriter
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from core.federation.protocol import (
    FederationEnvelope, FederationMessageType,
    FederationSecurityError, FederationExpiredError,
    FederationError, sanitize_phi,
)

logger = logging.getLogger("veilcore.federation.hub")


@dataclass
class ConnectedSite:
    """Represents a connected federation site."""
    site_id: str
    site_name: str
    writer: StreamWriter
    connected_at: float = field(default_factory=time.monotonic)
    last_heartbeat: float = field(default_factory=time.monotonic)
    capabilities: list[str] = field(default_factory=list)
    organ_count: int = 82
    messages_sent: int = 0
    messages_received: int = 0
    intel_shared: int = 0
    bulletins_sent: int = 0
    errors: int = 0
    status: dict[str, Any] = field(default_factory=dict)

    @property
    def is_alive(self) -> bool:
        return (time.monotonic() - self.last_heartbeat) < 120

    @property
    def uptime(self) -> float:
        return time.monotonic() - self.connected_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "site_id": self.site_id, "site_name": self.site_name,
            "connected_at": self.connected_at,
            "last_heartbeat": self.last_heartbeat,
            "capabilities": self.capabilities,
            "organ_count": self.organ_count,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "intel_shared": self.intel_shared,
            "bulletins_sent": self.bulletins_sent,
            "errors": self.errors, "is_alive": self.is_alive,
            "uptime_seconds": round(self.uptime, 2),
            "status": self.status,
        }


@dataclass
class HubConfig:
    """Federation hub configuration."""
    host: str = "0.0.0.0"
    port: int = 9443
    heartbeat_interval: int = 30
    heartbeat_timeout: int = 120
    max_sites: int = 100
    enable_logging: bool = True
    log_path: str = "/var/log/veilcore/federation.jsonl"
    stats_interval: int = 60

    @classmethod
    def from_yaml(cls, path: str) -> HubConfig:
        try:
            import yaml
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            cfg = data.get("federation", data)
            return cls(**{k: v for k, v in cfg.items() if k in cls.__dataclass_fields__})
        except Exception:
            return cls()


class FederationHub:
    """
    Central coordinator for the VeilCore hospital federation.

    Usage:
        hub = FederationHub()
        await hub.start()
        await hub.wait_shutdown()
    """

    def __init__(self, config: Optional[HubConfig] = None):
        self.config = config or HubConfig()
        self._server: Optional[asyncio.AbstractServer] = None
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._sites: dict[str, ConnectedSite] = {}
        self._writer_to_site: dict[StreamWriter, str] = {}
        self._tasks: list[asyncio.Task] = []
        self._stats = {
            "total_intel_shared": 0,
            "total_bulletins": 0,
            "total_messages_routed": 0,
            "total_connections": 0,
            "total_disconnections": 0,
            "total_phi_blocks": 0,
            "started_at": None,
        }
        self._intel_log: list[dict[str, Any]] = []

    async def start(self) -> None:
        """Start the federation hub."""
        if self._running:
            return

        logger.info("╔══════════════════════════════════════════════════╗")
        logger.info("║    VEILCORE FEDERATION HUB — STARTING           ║")
        logger.info("║    Connecting hospitals. Sharing intel. No PHI.  ║")
        logger.info("╚══════════════════════════════════════════════════╝")

        os.makedirs(os.path.dirname(self.config.log_path), exist_ok=True)

        self._server = await asyncio.start_server(
            self._handle_connection,
            host=self.config.host,
            port=self.config.port,
        )

        self._running = True
        self._stats["started_at"] = datetime.now(timezone.utc).isoformat()

        self._tasks = [
            asyncio.create_task(self._heartbeat_monitor(), name="federation-heartbeat"),
            asyncio.create_task(self._stats_logger(), name="federation-stats"),
        ]

        logger.info(f"Federation hub listening on {self.config.host}:{self.config.port}")
        logger.info("Awaiting site connections...")

    async def stop(self) -> None:
        """Stop the federation hub."""
        if not self._running:
            return
        logger.info("Federation hub shutting down...")
        self._running = False
        self._shutdown_event.set()
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        for site in list(self._sites.values()):
            try:
                site.writer.close()
                await site.writer.wait_closed()
            except Exception:
                pass
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        logger.info("Federation hub stopped.")

    async def __aenter__(self) -> FederationHub:
        await self.start()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.stop()

    async def wait_shutdown(self) -> None:
        await self._shutdown_event.wait()

    async def _handle_connection(self, reader: StreamReader, writer: StreamWriter) -> None:
        """Handle an incoming site connection."""
        site_id = None
        try:
            # First message must be HANDSHAKE
            envelope = await asyncio.wait_for(
                FederationEnvelope.read_from_stream(reader), timeout=15.0
            )
            if envelope is None or envelope.msg_type != FederationMessageType.HANDSHAKE:
                logger.warning("Connection rejected: expected HANDSHAKE")
                writer.close()
                await writer.wait_closed()
                return

            site_id = envelope.payload.get("site_id", envelope.source_site)
            site_name = envelope.payload.get("site_name", site_id)
            capabilities = envelope.payload.get("capabilities", [])
            organ_count = envelope.payload.get("organ_count", 82)

            if not site_id:
                logger.warning("Connection rejected: empty site_id")
                writer.close()
                await writer.wait_closed()
                return

            # Handle reconnection
            if site_id in self._sites:
                old = self._sites[site_id]
                logger.info(f"Site '{site_id}' reconnecting, closing old connection")
                try:
                    old.writer.close()
                    await old.writer.wait_closed()
                except Exception:
                    pass

            site = ConnectedSite(
                site_id=site_id, site_name=site_name, writer=writer,
                capabilities=capabilities, organ_count=organ_count,
            )
            self._sites[site_id] = site
            self._writer_to_site[writer] = site_id
            self._stats["total_connections"] += 1

            # Send handshake ACK
            ack = FederationEnvelope(
                source_site="federation-hub", dest_site=site_id,
                msg_type=FederationMessageType.HANDSHAKE_ACK,
                payload={
                    "status": "accepted", "site_id": site_id,
                    "connected_sites": [s.site_id for s in self._sites.values()],
                    "federation_size": len(self._sites),
                },
            )
            await self._send_to_writer(writer, ack)

            logger.info(
                f"✓ Site '{site_name}' ({site_id}) joined federation | "
                f"Organs: {organ_count} | "
                f"Federation size: {len(self._sites)} sites"
            )

            # Notify other sites
            await self._broadcast(
                FederationEnvelope(
                    source_site="federation-hub",
                    msg_type=FederationMessageType.SITE_STATUS,
                    payload={"event": "site_joined", "site_id": site_id,
                             "site_name": site_name,
                             "federation_size": len(self._sites)},
                ),
                exclude=site_id,
            )

            # Message loop
            while self._running:
                try:
                    envelope = await asyncio.wait_for(
                        FederationEnvelope.read_from_stream(reader), timeout=90.0
                    )
                    if envelope is None:
                        break
                    await self._process_message(site_id, envelope)
                except asyncio.TimeoutError:
                    continue
                except asyncio.IncompleteReadError:
                    break
                except (FederationSecurityError, FederationExpiredError) as e:
                    site.errors += 1
                    logger.warning(f"Security issue from '{site_id}': {e}")
                except FederationError as e:
                    site.errors += 1
                    logger.error(f"Federation error from '{site_id}': {e}")

        except asyncio.TimeoutError:
            logger.warning("Connection timed out during handshake")
        except Exception as e:
            logger.error(f"Connection error for site '{site_id}': {e}")
        finally:
            await self._disconnect_site(site_id, writer)

    async def _disconnect_site(self, site_id: Optional[str], writer: StreamWriter) -> None:
        """Clean up a disconnected site."""
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
        if writer in self._writer_to_site:
            del self._writer_to_site[writer]
        if site_id and site_id in self._sites:
            site = self._sites.pop(site_id)
            self._stats["total_disconnections"] += 1
            logger.info(
                f"✗ Site '{site.site_name}' ({site_id}) left federation | "
                f"Uptime: {site.uptime:.0f}s | "
                f"Intel shared: {site.intel_shared} | "
                f"Federation size: {len(self._sites)} sites"
            )
            await self._broadcast(
                FederationEnvelope(
                    source_site="federation-hub",
                    msg_type=FederationMessageType.SITE_STATUS,
                    payload={"event": "site_left", "site_id": site_id,
                             "federation_size": len(self._sites)},
                ),
            )

    async def _process_message(self, source_id: str, envelope: FederationEnvelope) -> None:
        """Process a message from a connected site."""
        site = self._sites.get(source_id)
        if not site:
            return

        site.messages_received += 1

        if envelope.msg_type == FederationMessageType.HEARTBEAT:
            site.last_heartbeat = time.monotonic()
            site.status = envelope.payload.get("status", {})
            return

        if envelope.msg_type == FederationMessageType.DISCONNECT:
            return  # will be handled by connection close

        if envelope.msg_type == FederationMessageType.INTEL_SHARE:
            site.intel_shared += 1
            self._stats["total_intel_shared"] += 1
            await self._log_intel(source_id, envelope)

            if envelope.dest_site:
                await self._send_to_site(envelope.dest_site, envelope)
            else:
                await self._broadcast(envelope, exclude=source_id)
            return

        if envelope.msg_type == FederationMessageType.THREAT_BULLETIN:
            site.bulletins_sent += 1
            self._stats["total_bulletins"] += 1
            await self._log_intel(source_id, envelope)
            await self._broadcast(envelope, exclude=source_id)
            logger.warning(
                f"🚨 THREAT BULLETIN from '{site.site_name}': "
                f"{envelope.payload.get('threat_type', 'unknown')} "
                f"(severity: {envelope.payload.get('severity', 'unknown')})"
            )
            return

        if envelope.msg_type in (FederationMessageType.COMMAND, FederationMessageType.COMMAND_ACK):
            if envelope.dest_site:
                await self._send_to_site(envelope.dest_site, envelope)
            else:
                await self._broadcast(envelope, exclude=source_id)
            return

        if envelope.msg_type in (FederationMessageType.SYNC_REQUEST, FederationMessageType.SYNC_RESPONSE):
            if envelope.dest_site:
                await self._send_to_site(envelope.dest_site, envelope)
            return

        self._stats["total_messages_routed"] += 1

    async def _send_to_site(self, site_id: str, envelope: FederationEnvelope) -> None:
        """Send an envelope to a specific site."""
        site = self._sites.get(site_id)
        if not site:
            logger.debug(f"Cannot send to '{site_id}': not connected")
            return
        try:
            data = envelope.prepare_for_send()
            site.writer.write(data)
            await site.writer.drain()
            site.messages_sent += 1
        except Exception as e:
            logger.warning(f"Failed to send to '{site_id}': {e}")
            site.errors += 1

    async def _send_to_writer(self, writer: StreamWriter, envelope: FederationEnvelope) -> None:
        """Send directly to a writer."""
        try:
            data = envelope.prepare_for_send()
            writer.write(data)
            await writer.drain()
        except Exception as e:
            logger.warning(f"Send to writer failed: {e}")

    async def _broadcast(self, envelope: FederationEnvelope, exclude: str = "") -> None:
        """Broadcast to all connected sites except excluded."""
        for site_id, site in self._sites.items():
            if site_id != exclude:
                await self._send_to_site(site_id, envelope)

    async def _log_intel(self, source_id: str, envelope: FederationEnvelope) -> None:
        """Log shared intel for audit trail."""
        if not self.config.enable_logging:
            return
        entry = {
            "id": envelope.id, "source_site": source_id,
            "msg_type": envelope.msg_type.value,
            "intel_type": envelope.payload.get("intel_type", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            with open(self.config.log_path, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            logger.error(f"Intel log write failed: {e}")

    async def _heartbeat_monitor(self) -> None:
        """Monitor site heartbeats."""
        while self._running:
            try:
                await asyncio.sleep(self.config.heartbeat_interval)
                now = time.monotonic()
                for site_id, site in list(self._sites.items()):
                    silence = now - site.last_heartbeat
                    if silence > self.config.heartbeat_timeout:
                        logger.warning(
                            f"⚠ Site '{site.site_name}' ({site_id}) "
                            f"unresponsive ({silence:.0f}s)"
                        )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat monitor error: {e}")

    async def _stats_logger(self) -> None:
        """Log federation statistics periodically."""
        while self._running:
            try:
                await asyncio.sleep(self.config.stats_interval)
                logger.info(
                    f"📊 Federation | Sites: {len(self._sites)} | "
                    f"Intel shared: {self._stats['total_intel_shared']} | "
                    f"Bulletins: {self._stats['total_bulletins']}"
                )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Stats logger error: {e}")

    def get_status(self) -> dict[str, Any]:
        """Get federation hub status."""
        return {
            "hub": {
                "running": self._running,
                "started_at": self._stats["started_at"],
                "host": self.config.host,
                "port": self.config.port,
            },
            "sites": {
                "total_connected": len(self._sites),
                "max_sites": self.config.max_sites,
                "connected": {sid: s.to_dict() for sid, s in self._sites.items()},
            },
            "statistics": dict(self._stats),
        }

    @property
    def site_count(self) -> int:
        return len(self._sites)

    @property
    def connected_sites(self) -> list[str]:
        return list(self._sites.keys())
