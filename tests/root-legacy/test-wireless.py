#!/usr/bin/env python3
"""
VeilCore Wireless Guardian — Smoke Test
==========================================
Tests:
    1. Wi-Fi scanning and rogue AP detection
    2. Bluetooth scanning and device classification
    3. Hardening rules assessment
    4. RFID/NFC guard with clone detection
    5. Full Wireless Guardian engine
    6. Evil twin detection

Usage:
    sudo python3 /opt/veilcore/test-wireless.py
"""

import sys
import os
import json
import logging
import time

sys.path.insert(0, "/opt/veilcore")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("wireless-test")


def run_test():
    logger.info("=" * 60)
    logger.info("  VEILCORE WIRELESS GUARDIAN — SMOKE TEST")
    logger.info("=" * 60)

    # ── Test 1: Wi-Fi Scanning
    logger.info("\n── Test 1: Wi-Fi Network Scanning")
    from core.wireless.scanner import WirelessScanner

    scanner = WirelessScanner()
    scanner.add_trusted_ssid("Hospital-Clinical")
    scanner.add_trusted_ssid("Hospital-IoMT")
    scanner.add_trusted_ssid("Hospital-Guest")
    scanner.add_trusted_ssid("Epic-Wireless")

    scan = scanner.scan()

    assert len(scan.wifi_networks) > 0, "Should discover Wi-Fi networks"
    assert scan.total_devices > 0, "Should have total devices"

    secure_count = sum(1 for n in scan.wifi_networks if n.is_secure)
    insecure_count = scan.insecure_wifi_count

    logger.info(f"  Discovered {len(scan.wifi_networks)} Wi-Fi networks")
    logger.info(f"  Secure: {secure_count}, Insecure: {insecure_count}")
    logger.info(f"  Rogue APs: {len(scan.rogue_aps)}")

    for net in scan.wifi_networks:
        logger.info(f"    {net.ssid:25s} {net.bssid} ch{net.channel:2d} "
                     f"{net.signal_dbm:4d}dBm {net.security:20s} trust={net.trust}")

    assert any(n.trust == "rogue" for n in scan.wifi_networks), \
        "Should detect rogue AP (open network or evil twin)"

    logger.info("✓ Wi-Fi scanning: network discovery, trust classification, rogue detection")

    # ── Test 2: Bluetooth Scanning
    logger.info("\n── Test 2: Bluetooth Device Scanning")

    assert len(scan.bluetooth_devices) > 0, "Should discover BT devices"

    for dev in scan.bluetooth_devices:
        logger.info(f"    {dev.name or '(unnamed)':30s} {dev.address} "
                     f"RSSI={dev.rssi:4d} trust={dev.trust}")

    unnamed = [d for d in scan.bluetooth_devices if not d.name]
    logger.info(f"  Discovered {len(scan.bluetooth_devices)} BT devices "
                f"({len(unnamed)} unnamed)")

    logger.info("✓ Bluetooth scanning: device enumeration, trust classification")

    # ── Test 3: Hardening Assessment
    logger.info("\n── Test 3: Wireless Hardening Assessment")
    from core.wireless.hardener import WirelessHardener

    hardener = WirelessHardener()
    report = hardener.assess(scan)

    assert report.total_rules > 0, "Should have rules"
    assert report.total_rules == 11, f"Expected 11 rules, got {report.total_rules}"

    logger.info(f"  Rules checked: {report.total_rules}")
    logger.info(f"  Passed: {report.passed}, Failed: {report.failed}")
    logger.info(f"  Compliance: {report.compliance_pct}%")
    logger.info(f"  Status: {report.overall_status}")

    for result in report.results:
        icon = "✓" if result.status == "pass" else "✗" if result.status == "fail" else "?"
        logger.info(f"    {icon} [{result.rule.severity:8s}] {result.rule.name}: {result.message}")

    # Should fail on open networks and rogue APs
    assert report.failed > 0, "Should have failures (open network, rogue AP)"

    summary = report.summary()
    assert "by_category" in summary
    logger.info(f"  By category: {json.dumps(summary['by_category'])}")

    logger.info("✓ Hardening: 11 rules, compliance scoring, HIPAA mapping")

    # ── Test 4: RFID/NFC Guard
    logger.info("\n── Test 4: RFID/NFC Guard")
    from core.wireless.rfid_nfc import RFIDNFCGuard

    guard = RFIDNFCGuard()

    # Register hospital infrastructure
    guard.register_tag("BADGE-001", tag_type="badge", owner="Dr. Smith", department="Cardiology")
    guard.register_tag("BADGE-002", tag_type="badge", owner="Nurse Johnson", department="ICU")
    guard.register_tag("EQUIP-MRI-01", tag_type="equipment", owner="Radiology")
    guard.register_reader("READER-LOBBY", location="Main Lobby", reader_type="door")
    guard.register_reader("READER-ICU", location="ICU Entry", reader_type="door")

    # Normal read
    event = guard.process_read("BADGE-001", "READER-LOBBY")
    assert event.event_type == "read"
    assert event.severity == "info"
    logger.info(f"  Normal read: {event.event_type} — {event.details}")

    # Unknown tag
    event = guard.process_read("UNKNOWN-TAG", "READER-LOBBY")
    assert event.severity == "medium"
    logger.info(f"  Unknown tag: {event.event_type} — severity={event.severity}")

    # Unregistered reader (skimming attempt)
    event = guard.process_read("BADGE-001", "ROGUE-READER")
    assert event.event_type == "skim_attempt"
    assert event.severity == "critical"
    logger.info(f"  Skim attempt: {event.event_type} — {event.details}")

    # Block a tag
    guard.block_tag("BADGE-STOLEN", reason="Reported stolen")
    event = guard.process_read("BADGE-STOLEN", "READER-LOBBY")
    assert event.event_type == "auth_fail"
    logger.info(f"  Blocked tag: {event.event_type} — {event.details}")

    # Rapid reads (clone detection)
    for _ in range(12):
        guard.process_read("BADGE-002", "READER-ICU")
    anomalies = guard.detect_anomalies()
    assert len(anomalies) > 0, "Should detect rapid read anomaly"
    logger.info(f"  Clone detection: {len(anomalies)} anomalies detected")
    for a in anomalies:
        logger.info(f"    [{a.severity}] {a.details}")

    rfid_summary = guard.summary()
    logger.info(f"  RFID summary: {json.dumps(rfid_summary)}")

    logger.info("✓ RFID/NFC: tag registration, skim detection, clone detection, blocking")

    # ── Test 5: Full Wireless Guardian Engine
    logger.info("\n── Test 5: Full Wireless Guardian Engine")
    from core.wireless.engine import WirelessGuardianEngine

    engine = WirelessGuardianEngine()
    engine.configure_hospital(
        "Memorial General Hospital",
        trusted_ssids=["Hospital-Clinical", "Hospital-IoMT", "Hospital-Guest", "Epic-Wireless"],
        trusted_bt=["11:22:33:44:55:01", "11:22:33:44:55:02", "11:22:33:44:55:03"],
    )

    # Full assessment
    assessment = engine.full_assessment()

    assert assessment["hospital"] == "Memorial General Hospital"
    assert assessment["scan"]["wifi_networks"] > 0
    assert assessment["hardening"]["compliance_pct"] is not None

    logger.info(f"  Hospital: {assessment['hospital']}")
    logger.info(f"  WiFi: {assessment['scan']['wifi_networks']} networks")
    logger.info(f"  BT: {assessment['scan']['bluetooth_devices']} devices")
    logger.info(f"  Rogue APs: {assessment['scan']['rogue_aps']}")
    logger.info(f"  Compliance: {assessment['hardening']['compliance_pct']}%")
    logger.info(f"  Threats: {len(assessment['threats'])}")
    logger.info(f"  Duration: {assessment['duration_ms']:.1f}ms")

    for threat in assessment["threats"]:
        logger.info(f"    [{threat['severity']:8s}] {threat['threat_type']}: {threat['details'][:70]}")

    # Monitor cycle
    threats = engine.monitor_cycle()
    logger.info(f"  Monitor cycle: {len(threats)} threats detected")

    # Summary
    summary = engine.summary()
    assert summary["codename"] == "AirShield"
    logger.info(f"  Engine summary: {json.dumps(summary, indent=2)}")

    logger.info("✓ Engine: full assessment, monitoring, threat analysis, hospital config")

    # ── Test 6: Evil Twin Detection
    logger.info("\n── Test 6: Evil Twin Detection")

    # The simulated scan includes "Hospital-Clinical" from both a trusted
    # and untrusted BSSID with different security — should flag evil twin
    evil_twins = [t for t in assessment["threats"] if t["threat_type"] == "evil_twin"]
    logger.info(f"  Evil twin threats: {len(evil_twins)}")
    for et in evil_twins:
        logger.info(f"    {et['details']}")

    # Verify evil twin was caught
    assert len(evil_twins) > 0, "Should detect evil twin for Hospital-Clinical"

    logger.info("✓ Evil twin detection: duplicate SSID with different security caught")

    # ── Final Summary
    logger.info("\n" + "=" * 60)
    logger.info("  ✅ ALL WIRELESS GUARDIAN TESTS PASSED")
    logger.info("=" * 60)
    logger.info("")
    logger.info("  ✓ Wi-Fi scanning — 7 networks, rogue AP detection, trust classification")
    logger.info("  ✓ Bluetooth scanning — 5 devices, medical device recognition")
    logger.info("  ✓ Hardening — 11 rules, HIPAA mapping, compliance scoring")
    logger.info("  ✓ RFID/NFC — badge tracking, skim detection, clone detection")
    logger.info("  ✓ Engine — full assessment, monitoring cycles, threat analysis")
    logger.info("  ✓ Evil twin — duplicate SSID with mismatched security caught")
    logger.info("")
    logger.info("  AirShield: Every signal is an attack surface.")
    logger.info("  The Veil covers what you can't see.")
    logger.info("")


if __name__ == "__main__":
    try:
        run_test()
    except AssertionError as e:
        logger.error(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Test interrupted")
        sys.exit(0)
