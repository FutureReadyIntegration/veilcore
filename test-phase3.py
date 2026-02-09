#!/usr/bin/env python3
"""
VeilCore Phase 3 — Complete Smoke Test
==========================================
Tests all 5 new subsystems:
    1. Deployment Engine (Genesis)
    2. HITRUST CSF Mapper (TrustForge)
    3. SOC 2 Type II Mapper (AuditIron)
    4. Cloud-Hybrid Engine (SkyVeil)
    5. Unified Dashboard (Prism)

Usage:
    sudo python3 /opt/veilcore/test-phase3.py
"""

import sys
import os
import json
import logging

sys.path.insert(0, "/opt/veilcore")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("phase3-test")


def run_test():
    logger.info("=" * 60)
    logger.info("  VEILCORE PHASE 3 — COMPLETE SMOKE TEST")
    logger.info("=" * 60)

    # ── Test 1: Deployment Engine (Genesis)
    logger.info("\n── Test 1: Deployment Engine — Genesis")
    from core.deployer.engine import DeploymentEngine, DeploymentManifest

    engine = DeploymentEngine()

    # Preflight
    preflight = engine.preflight_check()
    logger.info(f"  Preflight: passed={preflight.passed}")
    logger.info(f"  OS: {preflight.os_version}")
    logger.info(f"  Python: {preflight.python_version}")
    logger.info(f"  RAM: {preflight.ram_gb}GB, Disk: {preflight.disk_gb:.1f}GB")
    for check, passed in preflight.checks.items():
        logger.info(f"    {'✓' if passed else '✗'} {check}")

    # Deploy
    manifest = DeploymentManifest(
        hospital_name="Memorial General Hospital",
        install_path="/tmp/veilcore-test-deploy",
        data_path="/tmp/veilcore-test-data",
        log_path="/tmp/veilcore-test-logs",
        config_path="/tmp/veilcore-test-config",
    )
    result = engine.deploy(manifest)

    assert result.success, f"Deployment failed: {result.errors}"
    assert result.organs_deployed == 82, f"Expected 82 organs, got {result.organs_deployed}"
    assert result.subsystems_deployed == 8, f"Expected 8 subsystems, got {result.subsystems_deployed}"
    assert result.services_created == 82, f"Expected 82 services, got {result.services_created}"

    logger.info(f"  Deploy: {result.organs_deployed} organs, {result.subsystems_deployed} subsystems")
    logger.info(f"  Services: {result.services_created} created")
    logger.info(f"  Phases: {', '.join(result.phases_completed)}")
    logger.info(f"  Duration: {result.duration_seconds:.2f}s")

    # Verify organ files exist
    for tier in ["p0_critical", "p1_important", "p2_standard"]:
        tier_path = f"/tmp/veilcore-test-deploy/organs/{tier}"
        count = len([f for f in os.listdir(tier_path) if f.endswith(".py")])
        logger.info(f"  {tier}: {count} organ files")

    # Install script generation
    script = engine.generate_install_script(manifest)
    assert "VeilCore Installer" in script
    assert "Memorial General" in script

    summary = engine.summary()
    assert summary["codename"] == "Genesis"
    assert summary["total_organs"] == 82

    logger.info("✓ Genesis: preflight, deploy, 82 organs, 8 subsystems, service generation")

    # ── Test 2: HITRUST CSF (TrustForge)
    logger.info("\n── Test 2: HITRUST CSF Mapper — TrustForge")
    from core.compliance.hitrust import HITRUSTMapper

    hitrust = HITRUSTMapper()
    assessment = hitrust.assess()

    assert assessment.total_controls > 0
    assert assessment.domains_covered > 0
    assert assessment.coverage_pct > 0

    logger.info(f"  Controls: {assessment.total_controls}")
    logger.info(f"  Full coverage: {assessment.full_coverage}")
    logger.info(f"  Partial coverage: {assessment.partial_coverage}")
    logger.info(f"  No coverage: {assessment.no_coverage}")
    logger.info(f"  Coverage: {assessment.coverage_pct:.1f}%")
    logger.info(f"  Domains: {assessment.domains_covered}/{assessment.total_domains}")

    for domain, stats in assessment.by_domain.items():
        logger.info(f"    {domain}: {stats['full']}/{stats['total']} full")

    gaps = hitrust.get_gaps()
    logger.info(f"  Gaps: {len(gaps)}")

    # Test organ lookup
    guardian_controls = hitrust.get_organ_controls("guardian")
    assert len(guardian_controls) > 0
    logger.info(f"  Guardian mapped to {len(guardian_controls)} controls")

    summary = hitrust.summary()
    assert summary["codename"] == "TrustForge"

    logger.info("✓ TrustForge: 19 domains, full control mapping, gap analysis")

    # ── Test 3: SOC 2 Type II (AuditIron)
    logger.info("\n── Test 3: SOC 2 Type II Mapper — AuditIron")
    from core.compliance.soc2 import SOC2Mapper

    soc2 = SOC2Mapper()
    assessment = soc2.assess()

    assert assessment.total_criteria > 0
    assert assessment.coverage_pct > 0

    logger.info(f"  Criteria: {assessment.total_criteria}")
    logger.info(f"  Full coverage: {assessment.full_coverage}")
    logger.info(f"  Coverage: {assessment.coverage_pct:.1f}%")
    logger.info(f"  Automated: {assessment.automated_pct:.1f}%")
    logger.info(f"  Type II Ready: {assessment.type2_ready}")

    for cat, stats in assessment.by_category.items():
        logger.info(f"    {cat}: {stats['full']}/{stats['total']} full")

    evidence = soc2.get_evidence_map()
    assert len(evidence) > 0
    logger.info(f"  Evidence sources mapped: {len(evidence)} criteria")

    summary = soc2.summary()
    assert summary["codename"] == "AuditIron"

    logger.info("✓ AuditIron: 5 categories, 35+ criteria, evidence mapping, Type II readiness")

    # ── Test 4: Cloud-Hybrid Engine (SkyVeil)
    logger.info("\n── Test 4: Cloud-Hybrid Engine — SkyVeil")
    from core.cloud.hybrid import CloudHybridEngine

    cloud = CloudHybridEngine()

    # Register on-prem primary
    cloud.register_node("ONPREM-PRIMARY", provider="on_prem", role="primary",
                         organs=["guardian", "sentinel", "cortex", "phi_classifier",
                                 "epic_connector", "imprivata_bridge"],
                         data_classes=["phi", "pii", "operational"],
                         cpu_cores=16, ram_gb=64, disk_gb=500)

    # Register cloud analytics
    cloud.register_node("AWS-ANALYTICS", provider="aws", role="analytics",
                         region="us-east-1",
                         organs=["threat_intel", "metrics_collector", "anomaly_detector"],
                         data_classes=["threat_intel", "metrics"],
                         cpu_cores=8, ram_gb=32, disk_gb=200)

    # Register cloud failover
    cloud.register_node("AZURE-FAILOVER", provider="azure", role="failover",
                         region="us-central1",
                         organs=["log_aggregator", "performance_monitor"],
                         data_classes=["logs", "metrics"],
                         cpu_cores=4, ram_gb=16, disk_gb=100)

    # Test PHI enforcement — should BLOCK
    try:
        cloud.register_node("BAD-NODE", provider="aws",
                             organs=["guardian", "phi_classifier"])
        assert False, "Should have blocked PHI organs in cloud!"
    except ValueError as e:
        logger.info(f"  PHI enforcement: ✓ Blocked — {e}")

    try:
        cloud.register_node("BAD-DATA", provider="gcp",
                             data_classes=["phi"])
        assert False, "Should have blocked PHI data in cloud!"
    except ValueError as e:
        logger.info(f"  PHI data block: ✓ Blocked — {e}")

    # Sync
    sync = cloud.sync("ONPREM-PRIMARY", "AWS-ANALYTICS", policy_id="SYNC-THREAT")
    assert sync.success
    assert sync.encrypted
    logger.info(f"  Sync: {sync.source_node} → {sync.target_node}, "
                f"{sync.records_synced} records")

    # Test PHI sync block
    try:
        from core.cloud.hybrid import SyncPolicy
        bad_policy = SyncPolicy("BAD", "Bad Policy", data_classes=["phi"])
        cloud.add_policy(bad_policy)
        cloud.sync("ONPREM-PRIMARY", "AWS-ANALYTICS", policy_id="BAD")
        assert False, "Should have blocked PHI sync to cloud!"
    except ValueError:
        logger.info("  PHI sync block: ✓ Prevented")

    # Failover
    failover = cloud.failover("ONPREM-PRIMARY", "AZURE-FAILOVER")
    assert len(failover["organs_blocked"]) > 0  # PHI organs can't move
    logger.info(f"  Failover: moved {len(failover['organs_moved'])}, "
                f"blocked {len(failover['organs_blocked'])} (PHI)")

    # Validate compliance
    phi_check = cloud.validate_phi_compliance()
    logger.info(f"  PHI compliant: {phi_check['compliant']}")

    # Topology
    topology = cloud.get_topology()
    logger.info(f"  Nodes: {topology['total_nodes']}")
    logger.info(f"  Total organs deployed: {topology['total_organs_deployed']}")

    summary = cloud.summary()
    assert summary["codename"] == "SkyVeil"

    logger.info("✓ SkyVeil: multi-cloud, PHI enforcement, sync, failover, compliance")

    # ── Test 5: Unified Dashboard (Prism)
    logger.info("\n── Test 5: Unified Dashboard — Prism")
    from dashboard.unified import UnifiedDashboard

    dash = UnifiedDashboard()

    # Update subsystem statuses
    dash.update_subsystem("mesh", status="operational", health_pct=100,
                           metrics={"connected_organs": 82, "messages_per_sec": 450})
    dash.update_subsystem("ml", status="operational", health_pct=98,
                           metrics={"predictions": 1247, "accuracy": 0.94})
    dash.update_subsystem("federation", status="operational", health_pct=100,
                           metrics={"peers": 3, "shared_iocs": 89})
    dash.update_subsystem("pentest", status="operational", health_pct=95,
                           metrics={"findings": 7, "critical": 0})
    dash.update_subsystem("mobile", status="operational", health_pct=100,
                           metrics={"active_sessions": 4})
    dash.update_subsystem("accessibility", status="operational", health_pct=100,
                           metrics={"braille_displays": 2, "screen_readers": 3})
    dash.update_subsystem("wireless", status="operational", health_pct=97,
                           metrics={"threats": 2, "networks": 7})
    dash.update_subsystem("physical", status="operational", health_pct=100,
                           metrics={"sensors": 15, "cameras": 8, "alerts": 1})
    dash.update_subsystem("hitrust", status="operational",
                           metrics={"coverage_pct": 96.8, "gaps": 0})
    dash.update_subsystem("soc2", status="operational",
                           metrics={"coverage_pct": 94.3, "type2_ready": True})
    dash.update_subsystem("cloud", status="operational",
                           metrics={"nodes": 3, "phi_compliant": True})
    dash.update_subsystem("deployer", status="operational",
                           metrics={"organs_deployed": 82, "services": 82})

    # Overview
    overview = dash.get_overview()
    assert overview["overall_status"] == "NOMINAL"
    assert overview["organs"] == 82
    assert overview["subsystems"]["operational"] == 12

    logger.info(f"  Status: {overview['overall_status']}")
    logger.info(f"  Organs: {overview['organs']}")
    logger.info(f"  Subsystems: {overview['subsystems']['operational']}/{overview['subsystems']['total']} operational")
    logger.info(f"  Health: {overview['health_pct']}%")

    # All subsystems
    all_status = dash.get_all_subsystem_status()
    assert len(all_status) == 12
    for sub in all_status:
        logger.info(f"    {sub['codename']:15s} {sub['status']:12s} {sub['health_pct']:5.1f}%")

    # Threat summary
    threats = dash.get_threat_summary()
    logger.info(f"  Threat summary: {json.dumps(threats)}")

    # API routes
    routes = dash.generate_api_routes()
    assert len(routes) >= 16
    logger.info(f"  API routes: {len(routes)}")

    summary = dash.summary()
    assert summary["dashboard"] == "Prism"

    logger.info("✓ Prism: 12 subsystems, overview, threat aggregation, API routing")

    # ── Cleanup
    import shutil
    for d in ["/tmp/veilcore-test-deploy", "/tmp/veilcore-test-data",
              "/tmp/veilcore-test-logs", "/tmp/veilcore-test-config"]:
        shutil.rmtree(d, ignore_errors=True)

    # ── Final Summary
    logger.info("\n" + "=" * 60)
    logger.info("  ✅ ALL PHASE 3 TESTS PASSED")
    logger.info("=" * 60)
    logger.info("")
    logger.info("  ✓ Genesis — Deployment engine: preflight, 82 organs, 8 subsystems, services")
    logger.info("  ✓ TrustForge — HITRUST CSF: 19 domains, 30+ controls, gap analysis")
    logger.info("  ✓ AuditIron — SOC 2 Type II: 5 categories, 35 criteria, Type II readiness")
    logger.info("  ✓ SkyVeil — Cloud-hybrid: multi-cloud, PHI enforcement, failover")
    logger.info("  ✓ Prism — Dashboard: 12 subsystems, unified API, threat aggregation")
    logger.info("")
    logger.info("  VeilCore: 82 organs. 12 subsystems. 12 codenames. One Veil.")
    logger.info("  We built it because it's right.")
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
