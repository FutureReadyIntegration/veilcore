#!/usr/bin/env python3
"""
VeilCore Physical Security Monitor — Smoke Test
===================================================
Tests:
    1. Sensor registration and readings
    2. Sensor triggers and tamper detection
    3. Camera monitoring and tamper detection
    4. Sensor fusion — physical intrusion correlation
    5. Sensor fusion — camera sabotage
    6. Full Physical Security Engine

Usage:
    sudo python3 /opt/veilcore/test-physical.py
"""

import sys
import os
import json
import logging
import time

sys.path.insert(0, "/opt/veilcore")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("physical-test")


def run_test():
    logger.info("=" * 60)
    logger.info("  VEILCORE PHYSICAL SECURITY MONITOR — SMOKE TEST")
    logger.info("=" * 60)

    # ── Test 1: Sensor Registration & Readings
    logger.info("\n── Test 1: Sensor Registration & Readings")
    from core.physical.sensors import SensorManager

    mgr = SensorManager()

    mgr.register_sensor("TEMP-SR1", "temperature", "Server Room A",
                         zone="server_room", threshold_high=85.0, threshold_low=50.0)
    mgr.register_sensor("HUMID-SR1", "humidity", "Server Room A",
                         zone="server_room", threshold_high=80.0, threshold_low=20.0)
    mgr.register_sensor("MOTION-SR1", "motion", "Server Room A", zone="server_room")
    mgr.register_sensor("DOOR-SR1", "door", "Server Room A", zone="server_room")
    mgr.register_sensor("MOTION-NC1", "motion", "Network Closet B2", zone="network_closet")
    mgr.register_sensor("WATER-DC1", "water_leak", "Data Center", zone="data_center")
    mgr.register_sensor("POWER-DC1", "power", "Data Center", zone="data_center",
                         threshold_low=110.0)

    assert mgr.sensor_count == 7, f"Expected 7 sensors, got {mgr.sensor_count}"

    # Normal reading
    alerts = mgr.process_reading("TEMP-SR1", 72.5, unit="°F")
    assert len(alerts) == 0, "Normal temp should not trigger alert"

    # High temperature breach
    alerts = mgr.process_reading("TEMP-SR1", 88.5, unit="°F")
    assert len(alerts) == 1, "High temp should trigger alert"
    assert alerts[0].severity == "critical"  # server_room = critical
    assert alerts[0].alert_type == "threshold_breach"
    logger.info(f"  Temp breach: {alerts[0].message}")

    # Low voltage
    alerts = mgr.process_reading("POWER-DC1", 105.0, unit="V")
    assert len(alerts) == 1, "Low voltage should trigger alert"
    logger.info(f"  Voltage alert: {alerts[0].message}")

    logger.info(f"  Sensors: {mgr.sensor_count}, Alerts: {mgr.alert_count}")
    logger.info("✓ Sensor readings: registration, thresholds, zone-based severity")

    # ── Test 2: Sensor Triggers & Tamper Detection
    logger.info("\n── Test 2: Sensor Triggers & Tamper Detection")

    alerts = mgr.process_trigger("MOTION-SR1")
    assert len(alerts) >= 1
    assert alerts[0].severity == "critical"  # server_room
    logger.info(f"  Motion trigger: {alerts[0].message}")

    # Rapid triggering (tamper detection)
    for _ in range(6):
        alerts = mgr.process_trigger("DOOR-SR1")
    assert any(a.alert_type == "tamper" for a in alerts), "Should detect tamper"
    tamper = [a for a in alerts if a.alert_type == "tamper"][0]
    logger.info(f"  Tamper detected: {tamper.message}")

    # Sensor offline
    offline_alert = mgr.mark_offline("MOTION-NC1")
    assert offline_alert is not None
    assert offline_alert.alert_type == "offline"
    logger.info(f"  Offline: {offline_alert.message}")

    # Zone status
    zone = mgr.get_zone_status("server_room")
    logger.info(f"  Server room: {zone['sensor_count']} sensors, "
                f"{zone['triggered']} triggered, {zone['tampered']} tampered")

    logger.info("✓ Triggers: motion detection, tamper detection, offline monitoring")

    # ── Test 3: Camera Monitoring
    logger.info("\n── Test 3: Camera Monitoring & Tamper Detection")
    from core.physical.cameras import CameraMonitor

    cam_mon = CameraMonitor()
    cam_mon.register_camera("CAM-SR01", "Server Room A", "server_room",
                             ip_address="10.1.1.100", firmware="v2.1.0")
    cam_mon.register_camera("CAM-SR02", "Server Room A", "server_room",
                             ip_address="10.1.1.101", firmware="v2.1.0")
    cam_mon.register_camera("CAM-NC01", "Network Closet B2", "network_closet",
                             ip_address="10.1.2.100")
    cam_mon.register_camera("CAM-LOBBY", "Main Lobby", "lobby")

    # Feed lost in server room
    events = cam_mon.report_feed_lost("CAM-SR01")
    assert len(events) == 1
    assert events[0].severity == "critical"  # server_room feed_lost = critical
    logger.info(f"  Feed lost: {events[0].details} [{events[0].severity}]")

    # Camera tamper
    events = cam_mon.report_tamper("CAM-SR02", "Camera physically rotated")
    assert events[0].severity == "critical"
    logger.info(f"  Tamper: {events[0].details}")

    # Obstruction
    events = cam_mon.report_obstruction("CAM-NC01")
    logger.info(f"  Obstructed: {events[0].details}")

    # Firmware mismatch
    events = cam_mon.check_firmware("CAM-SR01", "v1.9.0")
    assert len(events) == 1
    assert events[0].event_type == "firmware_mismatch"
    logger.info(f"  Firmware mismatch: {events[0].details}")

    # Recording failure
    events = cam_mon.report_recording_failure("CAM-LOBBY")
    logger.info(f"  Recording failure: {events[0].details}")

    cam_summary = cam_mon.summary()
    logger.info(f"  Cameras: {cam_summary['total_cameras']}, "
                f"Recording: {cam_summary['recording']}, "
                f"Events: {cam_summary['total_events']}")

    logger.info("✓ Cameras: feed monitoring, tamper detection, firmware audit")

    # ── Test 4: Sensor Fusion — Physical Intrusion
    logger.info("\n── Test 4: Sensor Fusion — Physical Intrusion Correlation")
    from core.physical.fusion import SensorFusionEngine, FusionEvent

    fusion = SensorFusionEngine()

    # Camera goes dark in server room
    fusion.ingest(FusionEvent(
        source="camera", event_type="feed_lost",
        severity="critical", zone="server_room",
        location="Server Room A", details="CAM-SR01 feed lost",
    ))

    # Motion detected in same zone
    fusion.ingest(FusionEvent(
        source="sensor", event_type="triggered",
        severity="critical", zone="server_room",
        location="Server Room A", details="Motion detected",
    ))

    correlations = fusion.analyze()
    assert len(correlations) > 0, "Should detect physical intrusion pattern"

    intrusion = [c for c in correlations if c.pattern == "physical_intrusion"]
    assert len(intrusion) > 0, "Should match physical_intrusion pattern"
    logger.info(f"  Correlated: {intrusion[0].pattern}")
    logger.info(f"  Confidence: {intrusion[0].confidence}")
    logger.info(f"  Events: {len(intrusion[0].events)}")
    logger.info(f"  Action: {intrusion[0].recommended_action}")

    logger.info("✓ Fusion: camera + motion = physical intrusion detected")

    # ── Test 5: Sensor Fusion — Camera Sabotage
    logger.info("\n── Test 5: Sensor Fusion — Camera Sabotage")

    fusion2 = SensorFusionEngine()

    # Multiple cameras tampered
    fusion2.ingest(FusionEvent(
        source="camera", event_type="tamper_detected",
        severity="critical", zone="server_room",
        details="CAM-SR01 tampered",
    ))
    fusion2.ingest(FusionEvent(
        source="camera", event_type="tamper_detected",
        severity="critical", zone="network_closet",
        details="CAM-NC01 tampered",
    ))

    correlations = fusion2.analyze()
    sabotage = [c for c in correlations if c.pattern == "camera_sabotage"]
    assert len(sabotage) > 0, "Should detect camera sabotage"
    logger.info(f"  Correlated: {sabotage[0].pattern}")
    logger.info(f"  Confidence: {sabotage[0].confidence}")
    logger.info(f"  Action: {sabotage[0].recommended_action}")

    logger.info("✓ Fusion: multiple camera tampers = sabotage detected")

    # ── Test 6: Full Physical Security Engine
    logger.info("\n── Test 6: Full Physical Security Engine")
    from core.physical.engine import PhysicalSecurityEngine

    engine = PhysicalSecurityEngine()
    engine.configure_hospital("Memorial General Hospital")

    # Setup infrastructure
    engine.add_sensor("MOTION-SR1", "motion", "Server Room A", "server_room")
    engine.add_sensor("TEMP-SR1", "temperature", "Server Room A", "server_room",
                       threshold_high=85.0)
    engine.add_sensor("DOOR-SR1", "door", "Server Room A", "server_room")
    engine.add_camera("CAM-SR01", "Server Room A", "server_room", ip="10.1.1.100")
    engine.add_camera("CAM-SR02", "Server Room A", "server_room", ip="10.1.1.101")

    # Simulate attack sequence
    engine.camera_feed_lost("CAM-SR01")
    engine.sensor_trigger("MOTION-SR1")
    engine.sensor_trigger("DOOR-SR1")
    engine.sensor_reading("TEMP-SR1", 92.0, "°F")

    # Inject cyber event for correlation
    engine.cyber_event("network_anomaly", severity="high",
                        zone="server_room", details="Unusual traffic from server room switch")

    # Analyze
    correlations = engine.analyze()
    logger.info(f"  Correlations found: {len(correlations)}")
    for c in correlations:
        logger.info(f"    [{c.severity}] {c.pattern}: {c.description[:60]}")

    # Full assessment
    assessment = engine.full_assessment()
    logger.info(f"  Hospital: {assessment['hospital']}")
    logger.info(f"  Sensors: {assessment['sensors']['total_sensors']}")
    logger.info(f"  Cameras: {assessment['cameras']['total_cameras']}")
    logger.info(f"  Fusion events: {assessment['fusion']['events_in_buffer']}")
    logger.info(f"  Duration: {assessment['duration_ms']:.1f}ms")

    # Summary
    summary = engine.summary()
    assert summary["codename"] == "IronWatch"
    logger.info(f"  Engine: {json.dumps(summary, indent=2)}")

    logger.info("✓ Engine: full lifecycle, fusion analysis, hospital configuration")

    # ── Final Summary
    logger.info("\n" + "=" * 60)
    logger.info("  ✅ ALL PHYSICAL SECURITY TESTS PASSED")
    logger.info("=" * 60)
    logger.info("")
    logger.info("  ✓ Sensors — 7 types, thresholds, zone severity, tamper detection")
    logger.info("  ✓ Cameras — feed monitoring, tamper, firmware audit, recording")
    logger.info("  ✓ Fusion — physical intrusion correlation (camera + motion)")
    logger.info("  ✓ Fusion — camera sabotage detection (multi-camera tamper)")
    logger.info("  ✓ Engine — full assessment, cyber-physical correlation")
    logger.info("")
    logger.info("  IronWatch: The attack doesn't always start on the network.")
    logger.info("  Sometimes it starts at the door. The Veil watches both.")
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
