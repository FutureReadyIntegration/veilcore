"""
VeilCore SOC 2 Type II Mapper — AuditIron
============================================
Maps VeilCore to AICPA SOC 2 Type II Trust Services
Criteria across all five categories.

SOC 2 Type II evaluates the OPERATING EFFECTIVENESS of
controls over time — not just design. VeilCore's continuous
monitoring, automated testing, and immutable audit trails
provide the evidence SOC 2 auditors need.

5 Trust Services Categories. 35+ criteria mapped.
"""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("veilcore.compliance.soc2")


class TrustCategory(str):
    SECURITY = "Security"
    AVAILABILITY = "Availability"
    PROCESSING_INTEGRITY = "Processing Integrity"
    CONFIDENTIALITY = "Confidentiality"
    PRIVACY = "Privacy"


@dataclass
class SOC2Criterion:
    """A SOC 2 Trust Services Criterion."""
    criterion_id: str
    category: str
    title: str
    description: str
    veilcore_organs: list[str] = field(default_factory=list)
    veilcore_subsystems: list[str] = field(default_factory=list)
    coverage: str = "full"
    evidence_type: str = "automated"  # automated, manual, hybrid
    evidence_sources: list[str] = field(default_factory=list)
    continuous_monitoring: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "criterion_id": self.criterion_id,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "veilcore_organs": self.veilcore_organs,
            "veilcore_subsystems": self.veilcore_subsystems,
            "coverage": self.coverage,
            "evidence_type": self.evidence_type,
            "evidence_sources": self.evidence_sources,
            "continuous_monitoring": self.continuous_monitoring,
        }


# ── SOC 2 Trust Services Criteria Mapping ──
SOC2_CRITERIA = [
    # CC1 — Control Environment
    SOC2Criterion("CC1.1", "Security", "COSO Principle 1: Integrity & Ethics",
        "Demonstrates commitment to integrity and ethical values",
        veilcore_organs=["audit", "chronicle", "compliance_engine"],
        evidence_sources=["chronicle.immutable_timeline", "audit.records"]),

    SOC2Criterion("CC1.2", "Security", "COSO Principle 2: Board Oversight",
        "Board exercises oversight of security controls",
        veilcore_organs=["compliance_tracker", "risk_analyzer"],
        veilcore_subsystems=["mobile"],
        evidence_sources=["compliance_tracker.dashboards", "mobile.status_reports"]),

    SOC2Criterion("CC1.3", "Security", "COSO Principle 3: Management Structure",
        "Management establishes structures and reporting lines",
        veilcore_organs=["cortex", "alert_manager", "notification_engine"],
        evidence_sources=["cortex.organ_hierarchy", "alert_manager.escalation_chains"]),

    # CC2 — Communication & Information
    SOC2Criterion("CC2.1", "Security", "Internal Communication",
        "Generates and uses relevant security information",
        veilcore_organs=["sentinel", "cortex", "siem_connector", "metrics_collector"],
        veilcore_subsystems=["mesh", "ml"],
        evidence_sources=["mesh.message_logs", "siem_connector.events"]),

    SOC2Criterion("CC2.2", "Security", "External Communication",
        "Communicates security matters to external parties",
        veilcore_organs=["notification_engine", "email_gateway", "sms_notifier", "webhook_handler"],
        veilcore_subsystems=["federation", "mobile"],
        evidence_sources=["notification_engine.external_alerts"]),

    # CC3 — Risk Assessment
    SOC2Criterion("CC3.1", "Security", "Risk Identification",
        "Identifies and assesses risks to objectives",
        veilcore_organs=["risk_analyzer", "threat_intel", "vulnerability_scanner"],
        veilcore_subsystems=["pentest", "ml"],
        evidence_sources=["risk_analyzer.assessments", "pentest.vulnerability_reports"]),

    SOC2Criterion("CC3.2", "Security", "Fraud Risk",
        "Assesses fraud risk including insider threats",
        veilcore_organs=["insider_threat", "behavioral_analysis", "anomaly_detector"],
        evidence_sources=["insider_threat.detections", "behavioral_analysis.profiles"]),

    SOC2Criterion("CC3.3", "Security", "Change Impact Analysis",
        "Identifies and assesses changes that could impact controls",
        veilcore_organs=["config_auditor", "baseline_monitor", "file_monitor"],
        evidence_sources=["config_auditor.change_logs", "baseline_monitor.drifts"]),

    # CC4 — Monitoring Activities
    SOC2Criterion("CC4.1", "Security", "Ongoing Monitoring",
        "Selects, develops, and performs ongoing evaluations",
        veilcore_organs=["sentinel", "watchdog", "health_checker", "uptime_tracker"],
        veilcore_subsystems=["mesh", "ml"],
        evidence_sources=["watchdog.heartbeats", "health_checker.reports"]),

    SOC2Criterion("CC4.2", "Security", "Deficiency Communication",
        "Evaluates and communicates control deficiencies",
        veilcore_organs=["alert_manager", "compliance_engine", "notification_engine"],
        veilcore_subsystems=["mobile"],
        evidence_sources=["alert_manager.escalations", "compliance_engine.gaps"]),

    # CC5 — Control Activities
    SOC2Criterion("CC5.1", "Security", "Control Selection & Development",
        "Selects and develops control activities to mitigate risk",
        veilcore_organs=["cortex", "compliance_engine", "risk_analyzer"],
        veilcore_subsystems=["pentest"],
        evidence_sources=["compliance_engine.control_matrix"]),

    SOC2Criterion("CC5.2", "Security", "Technology Controls",
        "Selects and develops technology-based controls",
        veilcore_organs=["firewall", "ids_ips", "waf", "dns_filter", "ssl_inspector"],
        evidence_sources=["firewall.rule_sets", "ids_ips.signatures"]),

    SOC2Criterion("CC5.3", "Security", "Policy-Based Controls",
        "Deploys controls through policies and procedures",
        veilcore_organs=["rbac", "zero_trust_engine", "session_monitor"],
        evidence_sources=["rbac.policies", "zero_trust_engine.posture_checks"]),

    # CC6 — Logical & Physical Access
    SOC2Criterion("CC6.1", "Security", "Logical Access Security",
        "Implements logical access security over protected assets",
        veilcore_organs=["guardian", "rbac", "mfa", "vault"],
        evidence_sources=["guardian.access_logs", "vault.secret_access"]),

    SOC2Criterion("CC6.2", "Security", "Access Registration",
        "Registers and authorizes new users",
        veilcore_organs=["guardian", "rbac", "imprivata_bridge"],
        evidence_sources=["guardian.registrations", "rbac.role_assignments"]),

    SOC2Criterion("CC6.3", "Security", "Access Modification",
        "Manages changes to access permissions",
        veilcore_organs=["rbac", "session_monitor", "audit"],
        evidence_sources=["rbac.permission_changes", "audit.access_modifications"]),

    SOC2Criterion("CC6.4", "Security", "Physical Access Restriction",
        "Restricts physical access to facilities and assets",
        veilcore_subsystems=["physical"],
        evidence_sources=["physical.sensor_events", "physical.camera_events",
                          "physical.rfid_logs"]),

    SOC2Criterion("CC6.5", "Security", "Access Deprovisioning",
        "Removes access when no longer needed",
        veilcore_organs=["rbac", "guardian", "session_monitor"],
        evidence_sources=["rbac.deprovisioning_logs"]),

    SOC2Criterion("CC6.6", "Security", "System Boundary Protection",
        "Implements controls to prevent unauthorized access through system boundaries",
        veilcore_organs=["firewall", "micro_segmentation", "api_gateway", "web_proxy"],
        veilcore_subsystems=["wireless"],
        evidence_sources=["firewall.boundary_rules", "wireless.scan_reports"]),

    SOC2Criterion("CC6.7", "Security", "Data Transmission Protection",
        "Restricts transmission, movement, and removal of information",
        veilcore_organs=["dlp_engine", "encryption_enforcer", "content_filter", "email_gateway"],
        evidence_sources=["dlp_engine.incidents", "encryption_enforcer.audits"]),

    SOC2Criterion("CC6.8", "Security", "Malicious Software Prevention",
        "Implements controls to prevent and detect malicious software",
        veilcore_organs=["malware_detector", "ransomware_shield", "canary"],
        veilcore_subsystems=["ml"],
        evidence_sources=["malware_detector.scan_results", "ransomware_shield.detections"]),

    # CC7 — System Operations
    SOC2Criterion("CC7.1", "Security", "Anomaly Detection",
        "Detects and monitors for anomalies indicative of threats",
        veilcore_organs=["sentinel", "anomaly_detector", "behavioral_analysis"],
        veilcore_subsystems=["ml", "mesh"],
        evidence_sources=["sentinel.anomaly_feed", "ml.predictions"]),

    SOC2Criterion("CC7.2", "Security", "Event Evaluation",
        "Monitors for and evaluates security events",
        veilcore_organs=["cortex", "alert_manager", "siem_connector"],
        veilcore_subsystems=["mesh"],
        evidence_sources=["cortex.correlations", "alert_manager.evaluations"]),

    SOC2Criterion("CC7.3", "Security", "Incident Response",
        "Responds to identified security incidents",
        veilcore_organs=["incident_responder", "quarantine", "forensic_collector"],
        veilcore_subsystems=["mobile", "federation"],
        evidence_sources=["incident_responder.actions", "quarantine.isolations"]),

    SOC2Criterion("CC7.4", "Security", "Incident Recovery",
        "Recovers from identified security incidents",
        veilcore_organs=["disaster_recovery", "backup", "failover_controller", "backup_validator"],
        evidence_sources=["disaster_recovery.restorations", "backup_validator.tests"]),

    # CC8 — Change Management
    SOC2Criterion("CC8.1", "Security", "Infrastructure & Software Changes",
        "Manages changes to infrastructure and software",
        veilcore_organs=["config_auditor", "baseline_monitor", "integrity_checker", "patcher"],
        evidence_sources=["config_auditor.changes", "patcher.patch_logs"]),

    # CC9 — Risk Mitigation
    SOC2Criterion("CC9.1", "Security", "Risk Mitigation",
        "Identifies and mitigates business disruption risks",
        veilcore_organs=["risk_analyzer", "disaster_recovery", "failover_controller"],
        veilcore_subsystems=["pentest"],
        evidence_sources=["risk_analyzer.mitigation_plans"]),

    # A1 — Availability
    SOC2Criterion("A1.1", "Availability", "Capacity Planning",
        "Maintains processing capacity to meet availability commitments",
        veilcore_organs=["performance_monitor", "resource_limiter", "load_balancer"],
        evidence_sources=["performance_monitor.capacity_reports"]),

    SOC2Criterion("A1.2", "Availability", "Recovery Infrastructure",
        "Manages recovery infrastructure to support system availability",
        veilcore_organs=["backup", "disaster_recovery", "replication_engine",
                         "snapshot_manager", "failover_controller"],
        evidence_sources=["backup_validator.recovery_tests"]),

    SOC2Criterion("A1.3", "Availability", "Recovery Testing",
        "Tests recovery plan procedures",
        veilcore_organs=["backup_validator", "disaster_recovery"],
        veilcore_subsystems=["pentest"],
        evidence_sources=["backup_validator.test_results", "pentest.availability_tests"]),

    # PI1 — Processing Integrity
    SOC2Criterion("PI1.1", "Processing Integrity", "Data Quality",
        "Obtains or generates, uses relevant quality data",
        veilcore_organs=["hl7_filter", "fhir_gateway", "dicom_shield", "phi_classifier"],
        evidence_sources=["hl7_filter.validation_logs", "fhir_gateway.integrity_checks"]),

    # C1 — Confidentiality
    SOC2Criterion("C1.1", "Confidentiality", "Confidential Information Identification",
        "Identifies and classifies confidential information",
        veilcore_organs=["phi_classifier", "phi_guard", "dlp_engine"],
        evidence_sources=["phi_classifier.classifications", "phi_guard.access_logs"]),

    SOC2Criterion("C1.2", "Confidentiality", "Confidential Information Disposal",
        "Disposes of confidential information to meet objectives",
        veilcore_organs=["encryptor", "file_monitor"],
        evidence_sources=["encryptor.disposal_logs"]),

    # P1 — Privacy
    SOC2Criterion("P1.1", "Privacy", "Privacy Notice",
        "Provides notice about privacy practices",
        veilcore_organs=["compliance_tracker"],
        coverage="partial",
        evidence_sources=["compliance_tracker.privacy_notices"]),

    SOC2Criterion("P1.2", "Privacy", "PHI Access & Consent",
        "Manages consent and access to personal health information",
        veilcore_organs=["phi_guard", "rbac", "audit"],
        evidence_sources=["phi_guard.consent_logs", "audit.phi_access"]),
]


@dataclass
class SOC2Assessment:
    """SOC 2 Type II assessment result."""
    assessment_id: str = field(default_factory=lambda: f"SOC2-{int(time.time())}")
    total_criteria: int = 0
    full_coverage: int = 0
    partial_coverage: int = 0
    no_coverage: int = 0
    coverage_pct: float = 0.0
    automated_pct: float = 0.0
    by_category: dict[str, dict] = field(default_factory=dict)
    gaps: list[dict] = field(default_factory=list)
    type2_ready: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "total_criteria": self.total_criteria,
            "full_coverage": self.full_coverage,
            "partial_coverage": self.partial_coverage,
            "no_coverage": self.no_coverage,
            "coverage_pct": round(self.coverage_pct, 1),
            "automated_pct": round(self.automated_pct, 1),
            "by_category": self.by_category,
            "gaps": self.gaps,
            "type2_ready": self.type2_ready,
            "timestamp": self.timestamp,
        }


class SOC2Mapper:
    """
    Maps VeilCore to SOC 2 Type II criteria.

    Usage:
        mapper = SOC2Mapper()
        assessment = mapper.assess()
        report = mapper.generate_report()
    """

    def __init__(self):
        self._criteria = list(SOC2_CRITERIA)

    def assess(self) -> SOC2Assessment:
        """Run full SOC 2 assessment."""
        result = SOC2Assessment()
        result.total_criteria = len(self._criteria)

        automated_count = 0

        for criterion in self._criteria:
            has_coverage = len(criterion.veilcore_organs) > 0 or len(criterion.veilcore_subsystems) > 0

            if criterion.coverage == "full" and has_coverage:
                result.full_coverage += 1
            elif has_coverage:
                result.partial_coverage += 1
            else:
                result.no_coverage += 1
                result.gaps.append({
                    "criterion_id": criterion.criterion_id,
                    "category": criterion.category,
                    "title": criterion.title,
                })

            if criterion.evidence_type == "automated":
                automated_count += 1

            cat = criterion.category
            if cat not in result.by_category:
                result.by_category[cat] = {"full": 0, "partial": 0, "none": 0, "total": 0}
            result.by_category[cat]["total"] += 1

            if criterion.coverage == "full" and has_coverage:
                result.by_category[cat]["full"] += 1
            elif has_coverage:
                result.by_category[cat]["partial"] += 1
            else:
                result.by_category[cat]["none"] += 1

        checked = result.full_coverage + result.partial_coverage + result.no_coverage
        if checked > 0:
            result.coverage_pct = ((result.full_coverage + result.partial_coverage * 0.5) / checked) * 100
            result.automated_pct = (automated_count / checked) * 100

        # Type II readiness: need >90% coverage and >80% automated
        result.type2_ready = result.coverage_pct >= 90 and result.automated_pct >= 80

        return result

    def get_criterion(self, criterion_id: str) -> Optional[SOC2Criterion]:
        for c in self._criteria:
            if c.criterion_id == criterion_id:
                return c
        return None

    def get_by_category(self, category: str) -> list[SOC2Criterion]:
        return [c for c in self._criteria if c.category == category]

    def get_evidence_map(self) -> dict[str, list[str]]:
        evidence = {}
        for c in self._criteria:
            evidence[c.criterion_id] = c.evidence_sources
        return evidence

    def generate_report(self) -> dict[str, Any]:
        assessment = self.assess()
        return {
            "framework": "SOC 2 Type II",
            "codename": "AuditIron",
            "assessment": assessment.to_dict(),
            "criteria": [c.to_dict() for c in self._criteria],
        }

    def summary(self) -> dict[str, Any]:
        assessment = self.assess()
        return {
            "framework": "SOC 2 Type II",
            "codename": "AuditIron",
            "total_criteria": assessment.total_criteria,
            "coverage_pct": assessment.coverage_pct,
            "automated_pct": assessment.automated_pct,
            "type2_ready": assessment.type2_ready,
            "by_category": {k: f"{v['full']}/{v['total']} full"
                            for k, v in assessment.by_category.items()},
            "gaps": len(assessment.gaps),
        }
