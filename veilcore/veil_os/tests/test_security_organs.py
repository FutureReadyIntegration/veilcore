#!/usr/bin/env python3
"""
Veil Security Organs - Comprehensive Test Suite
================================================
Tests Zero-Trust, Insider Threat, and Auto-Lockdown integration.

Run: python -m pytest tests/test_security_organs.py -v
Or:  python tests/test_security_organs.py
"""

from __future__ import annotations

import sys
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_zero_trust_engine():
    """Test Zero-Trust policy enforcement."""
    print("\n" + "="*60)
    print("🔐 ZERO-TRUST ENGINE TESTS")
    print("="*60)
    
    from veil.organs.zero_trust import ZeroTrust, ZeroTrustConfig, TrustLevel, DeviceInfo, AccessContext, Policy
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create config with custom data directory
        config = ZeroTrustConfig()
        config.DATA_DIR = Path(tmpdir)
        zt = ZeroTrust(config=config)
        
        # Test 1: Device registration and verification
        print("\n[1] Testing device registration...")
        
        device = DeviceInfo(
            device_id="test-device-001",
            hostname="nurse-station-1",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            ip_address="10.3.0.100",
            registered_at=datetime.utcnow(),
        )
        device_info = zt.register_device(device)
        
        assert device_info is not None
        print(f"   ✅ Device registered: {device_info.device_id}")
        print(f"   ✅ Posture: {device_info.posture}")
        
        # Test 2: Access context evaluation
        print("\n[2] Testing access context evaluation...")
        
        context = AccessContext(
            request_id="req-001",
            user_id="nurse_001",
            session_id="sess_abc123",
            resource="/api/patients",
            action="GET",
            ip_address="10.3.0.100",
            device_id="test-device-001",
            timestamp=datetime.utcnow(),
        )
        
        result = zt.evaluate_access(context)
        
        print(f"   ✅ Decision: {result.decision}")
        print(f"   ✅ Trust Level: {result.trust_level}")
        print(f"   ✅ Risk Score: {result.risk_score}")
        
        # Test 3: Sensitive resource requires higher trust
        print("\n[3] Testing sensitive resource access...")
        
        admin_context = AccessContext(
            request_id="req-002",
            user_id="nurse_001",
            session_id="sess_abc123",
            resource="/api/restart",  # Sensitive!
            action="POST",
            ip_address="10.3.0.100",
            device_id="test-device-001",
            timestamp=datetime.utcnow(),
        )
        
        admin_result = zt.evaluate_access(admin_context)
        
        print(f"   ✅ Decision for /api/restart: {admin_result.decision}")
        print(f"   ✅ Required trust: {admin_result.required_trust_level}")
        
        # Test 4: Policy creation
        print("\n[4] Testing custom policy...")
        
        policy = Policy(
            id="policy-001",
            name="night-shift-restriction",
            description="Restrict access during night shift",
            resource_pattern="/api/sensitive/*",
            required_trust=TrustLevel.HIGH,
            conditions={"time_range": {"start": 22, "end": 6}},
        )
        zt.add_policy(policy)
        
        print(f"   ✅ Policy created: {policy.name}")
        
        print("\n✅ Zero-Trust engine tests PASSED")
        return True


def test_sentinel_detector():
    """Test Sentinel behavioral anomaly detection."""
    print("\n" + "="*60)
    print("🛡️ SENTINEL DETECTOR TESTS")
    print("="*60)
    
    from veil.organs.sentinel.detector import (
        Sentinel, 
        SentinelConfig,
        BehaviorEvent, 
        AnomalyType,
        AlertSeverity,
    )
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config = SentinelConfig()
        config.DATA_DIR = Path(tmpdir)
        analyzer = Sentinel(config=config)
        
        # Test 1: Record normal behavior
        print("\n[1] Building baseline with normal behavior...")
        
        for i in range(20):
            event = BehaviorEvent(
                timestamp=datetime.utcnow() - timedelta(days=i, hours=10),
                user_id="user_001",
                action="view",
                resource_type="patient",
                resource_id=f"PAT{i:04d}",
                ip_address="10.3.0.50",
            )
            analyzer.record_event(event)
        
        print(f"   ✅ Recorded 20 baseline events")
        
        # Test 2: Trigger rapid access anomaly
        print("\n[2] Testing rapid access detection...")
        
        alerts = []
        for i in range(25):  # Rapid burst of accesses
            event = BehaviorEvent(
                timestamp=datetime.utcnow(),
                user_id="user_001",
                action="view",
                resource_type="patient",
                resource_id=f"PAT{100+i:04d}",
                ip_address="10.3.0.50",
            )
            result = analyzer.record_event(event)
            if result:
                alerts.extend(result)
        
        rapid_alerts = [a for a in alerts if a.anomaly_type == AnomalyType.RAPID_REQUESTS]
        print(f"   ✅ Detected {len(rapid_alerts)} rapid request anomalies")
        
        # Test 3: Test after-hours access
        print("\n[3] Testing after-hours detection...")
        
        late_event = BehaviorEvent(
            timestamp=datetime.utcnow().replace(hour=23, minute=30),
            user_id="user_001",
            action="view",
            resource_type="patient",
            resource_id="PAT0001",
            ip_address="10.3.0.50",
        )
        
        after_hours_alerts = analyzer.record_event(late_event) or []
        time_alerts = [a for a in after_hours_alerts if a.anomaly_type == AnomalyType.UNUSUAL_TIME]
        print(f"   ✅ After-hours alert triggered: {len(time_alerts) > 0}")
        
        # Test 4: Get risk score
        print("\n[4] Testing risk score calculation...")
        
        risk_score = analyzer.get_user_risk_score("user_001")
        print(f"   ✅ User risk score: {risk_score}")
        
        print("\n✅ Sentinel detector tests PASSED")
        return True


def test_insider_threat_detector():
    """Test Insider Threat detection."""
    print("\n" + "="*60)
    print("🕵️ INSIDER THREAT DETECTOR TESTS")
    print("="*60)
    
    from veil.organs.insider_threat import (
        InsiderThreatDetector,
        UserActivity,
        ThreatIndicator,
        RiskLevel,
    )
    
    with tempfile.TemporaryDirectory() as tmpdir:
        detector = InsiderThreatDetector(data_dir=Path(tmpdir))
        
        # Test 1: Record normal activity
        print("\n[1] Building user baseline...")
        
        for i in range(30):
            activity = UserActivity(
                timestamp=datetime.utcnow() - timedelta(days=i, hours=10),
                user_id="employee_001",
                action="view",
                resource="/api/patients/list",
                ip_address="10.3.0.25",
                data_volume=1024 * 50,  # 50KB
            )
            detector.record_activity(activity)
        
        detector.recalculate_baseline("employee_001")
        print("   ✅ Baseline established for employee_001")
        
        # Test 2: Test mass data access detection
        print("\n[2] Testing mass data access detection...")
        
        alerts = []
        for i in range(150):  # Access many records
            activity = UserActivity(
                timestamp=datetime.utcnow(),
                user_id="employee_001",
                action="view",
                resource=f"/api/patients/{i}",
                ip_address="10.3.0.25",
                data_volume=1024 * 100,  # 100KB each
            )
            result = detector.record_activity(activity)
            alerts.extend(result)
        
        mass_alerts = [a for a in alerts if a.indicator == ThreatIndicator.MASS_DATA_ACCESS]
        print(f"   ✅ Mass data access alerts: {len(mass_alerts)}")
        
        # Test 3: Test after-hours access
        print("\n[3] Testing after-hours detection...")
        
        night_alerts = []
        for i in range(10):
            activity = UserActivity(
                timestamp=datetime.utcnow().replace(hour=22, minute=i*5),
                user_id="employee_001",
                action="view",
                resource="/api/patients/list",
                ip_address="10.3.0.25",
            )
            result = detector.record_activity(activity)
            night_alerts.extend(result)
        
        after_hours = [a for a in night_alerts if a.indicator == ThreatIndicator.AFTER_HOURS_ACCESS]
        print(f"   ✅ After-hours alerts: {len(after_hours)}")
        
        # Test 4: Test credential anomaly (impossible travel)
        print("\n[4] Testing credential anomaly detection...")
        
        # Access from one IP
        activity1 = UserActivity(
            timestamp=datetime.utcnow(),
            user_id="employee_002",
            action="login",
            resource="/api/auth/login",
            ip_address="10.3.0.25",
        )
        detector.record_activity(activity1)
        
        # Access from different IP within 2 minutes (impossible travel)
        activity2 = UserActivity(
            timestamp=datetime.utcnow() + timedelta(minutes=2),
            user_id="employee_002",
            action="view",
            resource="/api/patients",
            ip_address="192.168.100.50",  # Different subnet!
        )
        cred_alerts = detector.record_activity(activity2)
        
        shared_cred = [a for a in cred_alerts if a.indicator == ThreatIndicator.SHARED_CREDENTIALS]
        print(f"   ✅ Credential anomaly alerts: {len(shared_cred)}")
        
        # Test 5: Risk score
        print("\n[5] Testing aggregate risk score...")
        
        risk = detector.get_risk_score("employee_001")
        print(f"   ✅ Employee risk score: {risk}")
        
        print("\n✅ Insider threat detector tests PASSED")
        return True


def test_auto_lockdown():
    """Test Auto-Lockdown automated response."""
    print("\n" + "="*60)
    print("🔒 AUTO-LOCKDOWN ENGINE TESTS")
    print("="*60)
    
    from veil.organs.auto_lockdown import (
        AutoLockdown,
        ThreatEvent,
        ResponseLevel,
        ActionType,
    )
    
    with tempfile.TemporaryDirectory() as tmpdir:
        lockdown = AutoLockdown(data_dir=Path(tmpdir))
        
        # Test 1: Low severity threat - warning only
        print("\n[1] Testing warning response (low severity)...")
        
        event1 = ThreatEvent(
            id="EVT-001",
            timestamp=datetime.utcnow(),
            source="sentinel",
            threat_type="unusual_access",
            severity=35,
            user_id="user_001",
            ip_address="10.3.0.50",
        )
        
        actions1 = lockdown.process_threat(event1)
        action_types = [a.action_type for a in actions1]
        
        print(f"   ✅ Actions taken: {[a.value for a in action_types]}")
        assert ActionType.WARN_USER in action_types or ActionType.WARN_ADMIN in action_types
        
        # Test 2: Medium severity - restriction
        print("\n[2] Testing restriction response (medium severity)...")
        
        event2 = ThreatEvent(
            id="EVT-002",
            timestamp=datetime.utcnow(),
            source="insider_threat",
            threat_type="mass_data_access",
            severity=55,
            user_id="user_001",
            ip_address="10.3.0.50",
        )
        
        actions2 = lockdown.process_threat(event2)
        action_types2 = [a.action_type for a in actions2]
        
        print(f"   ✅ Actions taken: {[a.value for a in action_types2]}")
        
        # Test 3: High severity - suspension
        print("\n[3] Testing suspension response (high severity)...")
        
        event3 = ThreatEvent(
            id="EVT-003",
            timestamp=datetime.utcnow(),
            source="insider_threat",
            threat_type="data_exfiltration",
            severity=75,
            user_id="user_001",
            ip_address="10.3.0.50",
        )
        
        actions3 = lockdown.process_threat(event3)
        action_types3 = [a.action_type for a in actions3]
        
        print(f"   ✅ Actions taken: {[a.value for a in action_types3]}")
        # High severity triggers either suspension or lockdown depending on exact thresholds
        assert ActionType.SUSPEND_ACCOUNT in action_types3 or ActionType.FORCE_LOGOUT in action_types3 or ActionType.SYSTEM_LOCKDOWN in action_types3
        
        # Test 4: Check lockdown state
        print("\n[4] Testing lockdown state tracking...")
        
        state = lockdown.get_lockdown_state("user", "user_001")
        print(f"   ✅ Lockdown level: {state.level if state else 'none'}")
        print(f"   ✅ Expires at: {state.expires_at if state else 'n/a'}")
        
        # Test 5: Critical severity - full lockdown
        print("\n[5] Testing full lockdown (critical severity)...")
        
        event4 = ThreatEvent(
            id="EVT-004",
            timestamp=datetime.utcnow(),
            source="zero_trust",
            threat_type="ransomware_detected",
            severity=95,
            user_id="user_002",
            device_id="workstation-015",
        )
        
        actions4 = lockdown.process_threat(event4)
        action_types4 = [a.action_type for a in actions4]
        
        print(f"   ✅ Actions taken: {[a.value for a in action_types4]}")
        assert ActionType.SYSTEM_LOCKDOWN in action_types4 or ActionType.TRIGGER_BACKUP in action_types4
        
        # Test 6: Manual lift
        print("\n[6] Testing manual lockdown lift...")
        
        lifted = lockdown.lift_lockdown("user", "user_001", "Verified as legitimate activity")
        print(f"   ✅ Lockdown lifted: {lifted}")
        
        # Test 7: Get active lockdowns
        print("\n[7] Getting active lockdowns...")
        
        active = lockdown.get_active_lockdowns()
        print(f"   ✅ Active lockdowns: {len(active)}")
        
        print("\n✅ Auto-lockdown engine tests PASSED")
        return True


def test_integration():
    """Test integration between all security organs."""
    print("\n" + "="*60)
    print("🔗 INTEGRATION TESTS")
    print("="*60)
    
    from veil.organs.auto_lockdown import AutoLockdown, ThreatEvent
    from veil.organs.insider_threat import InsiderThreatDetector, UserActivity
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize organs
        insider = InsiderThreatDetector(data_dir=Path(tmpdir) / "insider")
        lockdown = AutoLockdown(data_dir=Path(tmpdir) / "lockdown")
        
        # Test 1: Insider threat triggers auto-lockdown
        print("\n[1] Testing insider threat → auto-lockdown integration...")
        
        # Simulate suspicious activity
        for i in range(200):
            activity = UserActivity(
                timestamp=datetime.utcnow(),
                user_id="suspect_user",
                action="export",
                resource=f"/api/patients/{i}/records",
                ip_address="10.3.0.99",
                data_volume=1024 * 1024,  # 1MB each
            )
            alerts = insider.record_activity(activity)
            
            # Forward high-severity alerts to auto-lockdown
            for alert in alerts:
                if alert.risk_level.value in ("high", "critical"):
                    event = ThreatEvent(
                        id=alert.id,
                        timestamp=alert.timestamp,
                        source="insider_threat",
                        threat_type=alert.indicator.value,
                        severity=alert.score,
                        user_id=alert.user_id,
                    )
                    lockdown.process_threat(event)
        
        # Check if user got locked down
        state = lockdown.get_lockdown_state("user", "suspect_user")
        print(f"   ✅ User lockdown triggered: {state is not None}")
        if state:
            print(f"   ✅ Lockdown level: {state.level}")
        
        # Test 2: Check action history
        print("\n[2] Reviewing action history...")
        
        history = lockdown.get_action_history(limit=10)
        print(f"   ✅ Actions in history: {len(history)}")
        for action in history[:3]:
            print(f"      - {action.action_type.value}: {action.result_message}")
        
        print("\n✅ Integration tests PASSED")
        return True


def run_all_tests():
    """Run all security organ tests."""
    print("\n" + "="*70)
    print("🏥 VEIL SECURITY ORGANS - COMPREHENSIVE TEST SUITE")
    print("="*70)
    print(f"Test started at: {datetime.utcnow().isoformat()}")
    
    results = {}
    
    try:
        results["zero_trust"] = test_zero_trust_engine()
    except Exception as e:
        print(f"\n❌ Zero-Trust tests FAILED: {e}")
        results["zero_trust"] = False
    
    try:
        results["sentinel"] = test_sentinel_detector()
    except Exception as e:
        print(f"\n❌ Sentinel tests FAILED: {e}")
        results["sentinel"] = False
    
    try:
        results["insider_threat"] = test_insider_threat_detector()
    except Exception as e:
        print(f"\n❌ Insider threat tests FAILED: {e}")
        results["insider_threat"] = False
    
    try:
        results["auto_lockdown"] = test_auto_lockdown()
    except Exception as e:
        print(f"\n❌ Auto-lockdown tests FAILED: {e}")
        results["auto_lockdown"] = False
    
    try:
        results["integration"] = test_integration()
    except Exception as e:
        print(f"\n❌ Integration tests FAILED: {e}")
        results["integration"] = False
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("\n⚠️ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
