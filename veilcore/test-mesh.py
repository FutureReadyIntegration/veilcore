#!/usr/bin/env python3
"""
VeilCore Mesh — Quick Smoke Test
=================================
Starts the router, connects 3 test organs, sends messages, verifies delivery.

Usage:
    sudo python3 /opt/veilcore/test-mesh.py
"""

import asyncio
import sys
import os
import logging

sys.path.insert(0, "/opt/veilcore")

from core.mesh.router import MeshRouter, RouterConfig
from core.mesh.client import MeshClient, ClientConfig
from core.mesh.protocol import MeshTopic, MessageType, MessagePriority

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("mesh-test")

SOCKET = "/tmp/veilcore-mesh-test.sock"
received_messages = []


async def test_handler(envelope):
    received_messages.append(envelope)
    logger.info(f"  📨 {envelope.destination} received {envelope.msg_type.value} from {envelope.source}")


async def run_test():
    logger.info("=" * 60)
    logger.info("  VEILCORE MESH — SMOKE TEST")
    logger.info("=" * 60)

    config = RouterConfig(
        socket_path=SOCKET,
        ledger_path="/tmp/veilcore-mesh-test-ledger.jsonl",
        dead_letter_path="/tmp/veilcore-mesh-test-dead.jsonl",
        pid_file="/tmp/veilcore-mesh-test.pid",
        stats_interval=999,
    )
    router = MeshRouter(config)
    await router.start()
    logger.info("✓ Router started")

    client_config = ClientConfig(socket_path=SOCKET)

    guardian = MeshClient("guardian", [MeshTopic.THREAT_ALERTS, MeshTopic.COMMANDS], client_config)
    sentinel = MeshClient("sentinel", [MeshTopic.THREAT_ALERTS], client_config)
    firewall = MeshClient("firewall", [MeshTopic.COMMANDS], client_config)

    guardian.on_message(test_handler)
    sentinel.on_message(test_handler)
    firewall.on_message(test_handler)

    assert await guardian.connect(), "Guardian failed to connect"
    logger.info("✓ Guardian connected")

    assert await sentinel.connect(), "Sentinel failed to connect"
    logger.info("✓ Sentinel connected")

    assert await firewall.connect(), "Firewall failed to connect"
    logger.info("✓ Firewall connected")

    assert router.organ_count == 3, f"Expected 3 organs, got {router.organ_count}"
    logger.info(f"✓ Router sees {router.organ_count}/82 organs")

    await asyncio.sleep(0.5)

    # Test 1: Point-to-point
    logger.info("\n── Test 1: Point-to-point (Guardian → Firewall)")
    received_messages.clear()
    await guardian.send_command("firewall", "block_ip", {"ip": "10.0.0.99"})
    await asyncio.sleep(0.5)
    p2p = [m for m in received_messages if m.source == "guardian" and m.msg_type == MessageType.COMMAND]
    assert len(p2p) >= 1, f"Expected 1 point-to-point message, got {len(p2p)}"
    logger.info(f"✓ Point-to-point delivery confirmed ({len(p2p)} message)")

    # Test 2: Pub/sub
    logger.info("\n── Test 2: Pub/sub (Guardian → topic:threat_alerts)")
    received_messages.clear()
    await guardian.send_threat_alert("ransomware", "critical", {"file": "patient_records.db"})
    await asyncio.sleep(0.5)
    threats = [m for m in received_messages if m.msg_type == MessageType.THREAT_ALERT]
    assert len(threats) >= 1, f"Expected threat alert delivery, got {len(threats)}"
    logger.info(f"✓ Pub/sub delivery confirmed ({len(threats)} subscribers received)")

    # Test 3: Broadcast
    logger.info("\n── Test 3: Broadcast (Sentinel → all organs)")
    received_messages.clear()
    await sentinel.broadcast({"event": "lockdown", "severity": "critical"}, MessagePriority.CRITICAL)
    await asyncio.sleep(0.5)
    broadcasts = [m for m in received_messages if m.source == "sentinel"]
    assert len(broadcasts) >= 2, f"Expected 2+ broadcast recipients, got {len(broadcasts)}"
    logger.info(f"✓ Broadcast delivery confirmed ({len(broadcasts)} organs received)")

    # Test 4: Status update
    logger.info("\n── Test 4: Status update")
    await guardian.send_status_update({"state": "active", "blocked_ips": 42})
    await asyncio.sleep(0.3)
    logger.info("✓ Status update sent")

    # Test 5: Escalation chain
    logger.info("\n── Test 5: Escalation chain (Guardian → Sentinel)")
    received_messages.clear()
    await guardian.escalate("sentinel", {"type": "breach", "target": "epic-ehr"}, ["guardian"])
    await asyncio.sleep(0.5)
    escalations = [m for m in received_messages if m.msg_type == MessageType.ESCALATION]
    assert len(escalations) >= 1, f"Expected escalation delivery, got {len(escalations)}"
    logger.info(f"✓ Escalation chain delivery confirmed")

    # Cleanup
    logger.info("\n── Cleanup")
    await guardian.disconnect()
    await sentinel.disconnect()
    await firewall.disconnect()
    await router.stop()

    for f in [SOCKET, config.ledger_path, config.dead_letter_path, config.pid_file]:
        if os.path.exists(f):
            os.unlink(f)

    logger.info("\n" + "=" * 60)
    logger.info("  ✅ ALL TESTS PASSED — MESH IS OPERATIONAL")
    logger.info("=" * 60)
    logger.info("")
    logger.info("  Next: sudo systemctl enable --now veilcore-mesh")
    logger.info("  Logs: journalctl -u veilcore-mesh -f")
    logger.info("")


if __name__ == "__main__":
    try:
        asyncio.run(run_test())
    except AssertionError as e:
        logger.error(f"❌ TEST FAILED: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Test interrupted")
        sys.exit(0)
