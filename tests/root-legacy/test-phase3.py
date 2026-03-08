#!/usr/bin/env python3
"""VeilCore Phase 3 Smoke Test"""
import sys, os, json, logging, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("phase3-test")

def run():
    logger.info("=" * 60)
    logger.info("  VEILCORE PHASE 3 SMOKE TEST")
    logger.info("=" * 60)

    logger.info("\n-- Test 1: Genesis (Deployment Engine)")
    from core.deployer.engine import DeploymentEngine, DeploymentManifest
    e = DeploymentEngine()
    pf = e.preflight_check()
    logger.info(f"  Preflight: passed={pf.passed}, Python={pf.python_version}")
    m = DeploymentManifest(hospital_name="Test Hospital", install_path="/tmp/vc-test", data_path="/tmp/vc-data", log_path="/tmp/vc-logs", config_path="/tmp/vc-conf")
    r = e.deploy(m)
    assert r.success, f"Deploy failed: {r.errors}"
    assert r.organs_deployed == 82, f"Expected 82, got {r.organs_deployed}"
    assert r.subsystems_deployed == 8, f"Expected 8, got {r.subsystems_deployed}"
    assert r.services_created == 82, f"Expected 82 services, got {r.services_created}"
    logger.info(f"  Deploy: {r.organs_deployed} organs, {r.subsystems_deployed} subsystems, {r.services_created} services")
    s = e.summary()
    assert s["codename"] == "Genesis"
    assert s["total_organs"] == 82
    logger.info("  PASS: Genesis")

    logger.info("\n-- Test 2: TrustForge (HITRUST CSF)")
    from core.compliance.hitrust import HITRUSTMapper
    h = HITRUSTMapper()
    a = h.assess()
    assert a.total_controls > 0
    assert a.domains_covered > 0
    assert a.coverage_pct > 0
    gc = h.get_organ_controls("guardian")
    assert len(gc) > 0
    logger.info(f"  Controls: {a.total_controls}, Coverage: {a.coverage_pct:.1f}%, Domains: {a.domains_covered}/{a.total_domains}")
    logger.info("  PASS: TrustForge")

    logger.info("\n-- Test 3: AuditIron (SOC 2 Type II)")
    from core.compliance.soc2 import SOC2Mapper
    s2 = SOC2Mapper()
    a2 = s2.assess()
    assert a2.total_criteria > 0
    assert a2.coverage_pct > 0
    ev = s2.get_evidence_map()
    assert len(ev) > 0
    logger.info(f"  Criteria: {a2.total_criteria}, Coverage: {a2.coverage_pct:.1f}%, Automated: {a2.automated_pct:.1f}%, Type2Ready: {a2.type2_ready}")
    logger.info("  PASS: AuditIron")

    logger.info("\n-- Test 4: SkyVeil (Cloud-Hybrid)")
    from core.cloud.hybrid import CloudHybridEngine, SyncPolicy
    c = CloudHybridEngine()
    c.register_node("ONPREM-1", provider="on_prem", role="primary", organs=["guardian","sentinel","cortex","phi_classifier","epic_connector","imprivata_bridge"], data_classes=["phi","pii","operational"])
    c.register_node("AWS-1", provider="aws", role="analytics", region="us-east-1", organs=["threat_intel","metrics_collector","anomaly_detector"], data_classes=["threat_intel","metrics"])
    c.register_node("AZURE-1", provider="azure", role="failover", region="us-central1", organs=["log_aggregator","performance_monitor"], data_classes=["logs","metrics"])
    try:
        c.register_node("BAD", provider="aws", organs=["guardian"])
        assert False, "Should block PHI organs in cloud"
    except ValueError:
        logger.info("  PHI organ block: PASS")
    try:
        c.register_node("BAD2", provider="gcp", data_classes=["phi"])
        assert False, "Should block PHI data in cloud"
    except ValueError:
        logger.info("  PHI data block: PASS")
    sync = c.sync("ONPREM-1", "AWS-1", policy_id="SYNC-THREAT")
    assert sync.success and sync.encrypted
    fo = c.failover("ONPREM-1", "AZURE-1")
    assert len(fo["organs_blocked"]) > 0
    logger.info(f"  Failover: moved {len(fo['organs_moved'])}, blocked {len(fo['organs_blocked'])}")
    logger.info("  PASS: SkyVeil")

    logger.info("\n-- Test 5: Prism (Unified Dashboard)")
    from dashboard.unified import UnifiedDashboard
    d = UnifiedDashboard()
    d.update_subsystem("mesh", metrics={"connected_organs":82})
    d.update_subsystem("ml", metrics={"predictions":1247})
    d.update_subsystem("hitrust", metrics={"coverage_pct":96.8})
    d.update_subsystem("soc2", metrics={"coverage_pct":94.3,"type2_ready":True})
    o = d.get_overview()
    assert o["overall_status"] == "NOMINAL"
    assert o["organs"] == 82
    assert o["subsystems"]["operational"] == 12
    routes = d.generate_api_routes()
    assert len(routes) >= 16
    logger.info(f"  Status: {o['overall_status']}, Subsystems: {o['subsystems']['operational']}/12, Routes: {len(routes)}")
    logger.info("  PASS: Prism")

    for d in ["/tmp/vc-test","/tmp/vc-data","/tmp/vc-logs","/tmp/vc-conf"]:
        shutil.rmtree(d, ignore_errors=True)

    logger.info("\n" + "=" * 60)
    logger.info("  ALL PHASE 3 TESTS PASSED")
    logger.info("=" * 60)
    logger.info("  Genesis / TrustForge / AuditIron / SkyVeil / Prism")
    logger.info("  82 organs. 13 subsystems. One Veil.")

if __name__ == "__main__":
    try: run()
    except AssertionError as e: logger.error(f"FAILED: {e}"); import traceback; traceback.print_exc(); sys.exit(1)
