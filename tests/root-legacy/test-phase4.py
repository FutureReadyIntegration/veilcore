"""VeilCore Phase 4 Test Suite — Unleashed, Pilot, CertForge, IronFlag"""
import sys, time
sys.path.insert(0, "/opt/veilcore")

PASS = 0
FAIL = 0

def check(name, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}")

print("=" * 60)
print("VeilCore Phase 4 — Final Roadmap Tests")
print("=" * 60)

# ═══ TEST 1: VeilUnleashed ═══
print("\n🔧 Test 1: VeilUnleashed (Bare-Metal Deployment)")
from core.unleashed.engine import UnleashedEngine, ServerRole, NetworkConfig
engine = UnleashedEngine()

hw = engine.discover_hardware()
check("Hardware discovery", hw.cpu_cores > 0 and hw.ram_total_gb > 0)
check("Hardware tier detected", hw.tier in ["community", "standard", "enterprise", "insufficient"])
check("Meets minimum specs", hw.meets_minimum)

result = engine.deploy("Test Hospital", ServerRole.STANDALONE, NetworkConfig())
check("Deploy completed", result.success)
check("All 8 phases completed", len(result.phases_completed) == 8)
check("82 organs deployed", result.organs_deployed == 82)
check("Hardening rules applied", result.hardening_rules_applied == 27)
check("Firewall rules configured", result.firewall_rules == 8)
check("Health checks passed", result.health_checks_passed == 15)
check("Certificates generated", result.certificates_generated == 8)

script = engine.generate_install_script("Test Hospital", ServerRole.PRIMARY)
check("Install script generated", "VeilCore Unleashed" in script and "Phase 1" in script)

s = engine.summary()
check("Summary valid", s["hardening_rules"] == 27 and s["health_checks"] == 15)

# ═══ TEST 2: Pilot Program ═══
print("\n🏥 Test 2: Pilot Program (Hospital Onboarding)")
from core.pilot.program import PilotProgram

pilot = PilotProgram()
assessment = pilot.assess("Memorial General", beds=200, ehr="epic",
    security_staff=0, has_ciso=False, previous_incidents=2,
    network_segments=1, iot_devices=150, hipaa_findings=4)

check("Assessment completed", assessment.hospital_name == "Memorial General")
check("Risk evaluated", assessment.risk_score > 0)
check("Risk level detected", assessment.overall_risk in ["critical", "high", "moderate", "low"])
check("Risk factors identified", len(assessment.risk_factors) > 0)
check("Hospital size: regional", assessment.hospital_size == "regional")

plan = pilot.create_plan(assessment)
check("Deployment plan generated", plan.total_weeks > 0)
check("Plan has phases", len(plan.phases) == 4)
check("Success criteria defined", len(plan.success_criteria) > 0)

tracks = pilot.get_training_tracks()
check("Training tracks available", len(tracks) == 5)
check("Security admin track exists", any(t["role"] == "security_admin" for t in tracks))
check("Accessibility track exists", any(t["role"] == "accessibility_operator" for t in tracks))

detail = pilot.get_training_detail("security_admin")
check("Training detail has modules", detail and len(detail["modules"]) > 0)

checklist = pilot.generate_onboarding_checklist(assessment)
check("Onboarding checklist generated", len(checklist) == 4)

result = pilot.start_pilot(assessment)
check("Pilot started", result.hospital_name == "Memorial General")

s = pilot.summary()
check("Summary valid", s["training_tracks"] == 5)

# ═══ TEST 3: HITRUST Submission Engine ═══
print("\n📋 Test 3: HITRUST CertForge (Certification Submission)")
from core.certification.hitrust_submission import HITRUSTSubmissionEngine, CertLevel

cert = HITRUSTSubmissionEngine()

# e1
e1 = cert.prepare_submission("Test Hospital", CertLevel.E1)
check(f"e1: {e1.total_controls} controls assessed", e1.total_controls == 44)
check(f"e1: {e1.readiness_pct:.0f}% ready", e1.readiness_pct > 80)
check("e1: evidence collected", e1.evidence_items > 0)

# i1
i1 = cert.prepare_submission("Test Hospital", CertLevel.I1)
check(f"i1: {i1.total_controls} controls assessed", i1.total_controls > e1.total_controls)
check(f"i1: {i1.readiness_pct:.0f}% ready", i1.readiness_pct > 70)

# r2
r2 = cert.prepare_submission("Test Hospital", CertLevel.R2)
check(f"r2: {r2.total_controls} controls assessed", r2.total_controls > i1.total_controls)
check(f"r2: {r2.readiness_pct:.0f}% ready", r2.readiness_pct > 60)
check("r2: narratives generated", r2.narratives_generated > 0)
check("r2: domains assessed", r2.domains_assessed > 20)

compare = cert.compare_levels()
check("Level comparison available", len(compare) == 3)

s = cert.summary()
check("Summary valid", s["levels_supported"] == ["e1", "i1", "r2"])

# ═══ TEST 4: FedRAMP IronFlag ═══
print("\n🇺🇸 Test 4: FedRAMP IronFlag (Federal Compliance)")
from core.compliance.fedramp import FedRAMPMapper, FedRAMPLevel

fed = FedRAMPMapper()

low = fed.assess(FedRAMPLevel.LOW)
check(f"Low: {low.total_controls} controls, {low.coverage_pct:.1f}%", low.coverage_pct > 80)
check("Low: zero gaps", len(low.gaps) == 0)

mod = fed.assess(FedRAMPLevel.MODERATE)
check(f"Moderate: {mod.total_controls} controls, {mod.coverage_pct:.1f}%", mod.coverage_pct > 80)
check(f"Moderate: {mod.continuous_monitoring_pct:.0f}% continuous monitoring", mod.continuous_monitoring_pct > 30)

high = fed.assess(FedRAMPLevel.HIGH)
check(f"High: {high.total_controls} controls, {high.coverage_pct:.1f}%", high.coverage_pct > 80)

by_fam = mod.by_family
check(f"Families covered: {len(by_fam)}", len(by_fam) >= 12)
check("AC family present", "AC" in by_fam)
check("SC family present", "SC" in by_fam)
check("SI family present", "SI" in by_fam)

report = fed.generate_report(FedRAMPLevel.MODERATE)
check("Report generated", report["codename"] == "IronFlag")

s = fed.summary()
check("Summary valid", s["codename"] == "IronFlag")

# ═══ FULL COMPLIANCE SUMMARY ═══
print("\n" + "=" * 60)
print("📊 Complete Compliance Dashboard")
print("=" * 60)

from core.compliance.hipaa import HIPAAMapper
from core.compliance.hitrust import HITRUSTMapper
from core.compliance.soc2 import SOC2Mapper

hipaa = HIPAAMapper().assess()
hitrust = HITRUSTMapper().assess()
soc2 = SOC2Mapper().assess()

print(f"  HIPAA Security Rule:  {hipaa.coverage_pct:.1f}%  ({hipaa.full_coverage}/{hipaa.total_requirements})")
print(f"  HITRUST CSF v11:      {hitrust.coverage_pct:.1f}%  ({hitrust.full_coverage}/{hitrust.total_controls})")
print(f"  SOC 2 Type II:        {soc2.coverage_pct:.1f}%  ({soc2.full_coverage}/{soc2.total_criteria})")
print(f"  FedRAMP Low:          {low.coverage_pct:.1f}%  ({low.full_coverage}/{low.total_controls})")
print(f"  FedRAMP Moderate:     {mod.coverage_pct:.1f}%  ({mod.full_coverage}/{mod.total_controls})")
print(f"  FedRAMP High:         {high.coverage_pct:.1f}%  ({high.full_coverage}/{high.total_controls})")
print(f"  HITRUST e1 Ready:     {e1.readiness_pct:.1f}%  ({e1.controls_ready}/{e1.total_controls})")
print(f"  HITRUST i1 Ready:     {i1.readiness_pct:.1f}%  ({i1.controls_ready}/{i1.total_controls})")
print(f"  HITRUST r2 Ready:     {r2.readiness_pct:.1f}%  ({r2.controls_ready}/{r2.total_controls})")

print(f"\n{'=' * 60}")
print(f"Phase 4 Results: {PASS} passed, {FAIL} failed")
if FAIL == 0:
    print("✅ ALL TESTS PASSED — ROADMAP COMPLETE")
else:
    print(f"❌ {FAIL} FAILURES")
print("=" * 60)
