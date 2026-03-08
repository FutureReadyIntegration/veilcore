"""
VeilCore HIPAA Security Rule Mapper — ShieldLaw
===================================================
Complete mapping of VeilCore to every HIPAA Security Rule
requirement under 45 CFR Part 164 Subpart C.

100% coverage across all three safeguard categories:
    - Administrative Safeguards (§164.308)
    - Physical Safeguards (§164.310)
    - Technical Safeguards (§164.312)

Plus:
    - Organizational Requirements (§164.314)
    - Policies & Documentation (§164.316)

Every single standard and implementation specification
mapped to specific VeilCore organs and subsystems.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("veilcore.compliance.hipaa")


@dataclass
class HIPAARequirement:
    """A HIPAA Security Rule requirement."""
    section: str
    standard: str
    spec_type: str  # required, addressable
    category: str   # administrative, physical, technical, organizational, policies
    title: str
    description: str
    veilcore_organs: list[str] = field(default_factory=list)
    veilcore_subsystems: list[str] = field(default_factory=list)
    coverage: str = "full"
    evidence_sources: list[str] = field(default_factory=list)
    automated: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "section": self.section, "standard": self.standard,
            "spec_type": self.spec_type, "category": self.category,
            "title": self.title, "description": self.description,
            "veilcore_organs": self.veilcore_organs,
            "veilcore_subsystems": self.veilcore_subsystems,
            "coverage": self.coverage,
            "evidence_sources": self.evidence_sources,
            "automated": self.automated,
        }


# ═══════════════════════════════════════════════════════════════
#  COMPLETE HIPAA SECURITY RULE MAPPING
#  45 CFR Part 164, Subpart C — §164.302 through §164.318
# ═══════════════════════════════════════════════════════════════

HIPAA_REQUIREMENTS = [

    # ───────────────────────────────────────────────────────────
    #  ADMINISTRATIVE SAFEGUARDS — §164.308
    # ───────────────────────────────────────────────────────────

    # §164.308(a)(1) — Security Management Process
    HIPAARequirement("§164.308(a)(1)(i)", "Security Management Process", "required",
        "administrative", "Security Management Process",
        "Implement policies and procedures to prevent, detect, contain, and correct security violations",
        veilcore_organs=["cortex", "compliance_engine", "sentinel", "incident_responder"],
        veilcore_subsystems=["mesh", "ml"],
        evidence_sources=["cortex.policies", "compliance_engine.reports"]),

    HIPAARequirement("§164.308(a)(1)(ii)(A)", "Risk Analysis", "required",
        "administrative", "Risk Analysis",
        "Conduct an accurate and thorough assessment of potential risks and vulnerabilities to ePHI",
        veilcore_organs=["risk_analyzer", "vulnerability_scanner", "threat_intel"],
        veilcore_subsystems=["pentest", "ml"],
        evidence_sources=["risk_analyzer.assessments", "pentest.vulnerability_reports"]),

    HIPAARequirement("§164.308(a)(1)(ii)(B)", "Risk Management", "required",
        "administrative", "Risk Management",
        "Implement security measures sufficient to reduce risks and vulnerabilities to a reasonable level",
        veilcore_organs=["risk_analyzer", "firewall", "ids_ips", "zero_trust_engine"],
        veilcore_subsystems=["pentest"],
        evidence_sources=["risk_analyzer.mitigation_plans", "pentest.remediation_tracking"]),

    HIPAARequirement("§164.308(a)(1)(ii)(C)", "Sanction Policy", "required",
        "administrative", "Sanction Policy",
        "Apply appropriate sanctions against workforce members who fail to comply with security policies",
        veilcore_organs=["insider_threat", "audit", "compliance_tracker"],
        evidence_sources=["insider_threat.violations", "audit.policy_violations"]),

    HIPAARequirement("§164.308(a)(1)(ii)(D)", "Information System Activity Review", "required",
        "administrative", "Information System Activity Review",
        "Implement procedures to regularly review records of information system activity",
        veilcore_organs=["audit", "chronicle", "log_aggregator", "siem_connector"],
        evidence_sources=["chronicle.timeline", "audit.review_logs"]),

    # §164.308(a)(2) — Assigned Security Responsibility
    HIPAARequirement("§164.308(a)(2)", "Assigned Security Responsibility", "required",
        "administrative", "Assigned Security Responsibility",
        "Identify the security official responsible for developing and implementing security policies",
        veilcore_organs=["cortex", "compliance_tracker", "alert_manager"],
        veilcore_subsystems=["mobile"],
        evidence_sources=["compliance_tracker.security_officer_designation"]),

    # §164.308(a)(3) — Workforce Security
    HIPAARequirement("§164.308(a)(3)(i)", "Workforce Security", "required",
        "administrative", "Workforce Security",
        "Implement policies to ensure all workforce members have appropriate access to ePHI",
        veilcore_organs=["rbac", "guardian", "insider_threat", "session_monitor"],
        evidence_sources=["rbac.policies", "guardian.access_logs"]),

    HIPAARequirement("§164.308(a)(3)(ii)(A)", "Authorization and/or Supervision", "addressable",
        "administrative", "Authorization and/or Supervision",
        "Implement procedures for authorizing and supervising workforce access to ePHI",
        veilcore_organs=["rbac", "guardian", "session_monitor", "behavioral_analysis"],
        evidence_sources=["rbac.authorization_logs", "session_monitor.activity"]),

    HIPAARequirement("§164.308(a)(3)(ii)(B)", "Workforce Clearance Procedure", "addressable",
        "administrative", "Workforce Clearance Procedure",
        "Implement procedures to determine that workforce access is appropriate",
        veilcore_organs=["rbac", "guardian", "compliance_engine"],
        evidence_sources=["rbac.clearance_checks", "guardian.provisioning_logs"]),

    HIPAARequirement("§164.308(a)(3)(ii)(C)", "Termination Procedures", "addressable",
        "administrative", "Termination Procedures",
        "Implement procedures for terminating access when employment ends",
        veilcore_organs=["rbac", "guardian", "session_monitor", "vault"],
        evidence_sources=["rbac.deprovisioning_logs", "guardian.termination_logs"]),

    # §164.308(a)(4) — Information Access Management
    HIPAARequirement("§164.308(a)(4)(i)", "Information Access Management", "required",
        "administrative", "Information Access Management",
        "Implement policies for authorizing access to ePHI",
        veilcore_organs=["rbac", "guardian", "phi_guard", "zero_trust_engine"],
        evidence_sources=["rbac.access_policies", "phi_guard.access_controls"]),

    HIPAARequirement("§164.308(a)(4)(ii)(A)", "Isolating Healthcare Clearinghouse Functions", "required",
        "administrative", "Isolating Clearinghouse Functions",
        "If a clearinghouse is part of a larger organization, implement policies to protect ePHI",
        veilcore_organs=["micro_segmentation", "firewall", "phi_guard"],
        evidence_sources=["micro_segmentation.isolation_rules"]),

    HIPAARequirement("§164.308(a)(4)(ii)(B)", "Access Authorization", "addressable",
        "administrative", "Access Authorization",
        "Implement policies for granting access to ePHI",
        veilcore_organs=["rbac", "guardian", "mfa"],
        evidence_sources=["rbac.authorization_policies", "guardian.grant_logs"]),

    HIPAARequirement("§164.308(a)(4)(ii)(C)", "Access Establishment and Modification", "addressable",
        "administrative", "Access Establishment and Modification",
        "Implement policies for establishing and modifying access to ePHI",
        veilcore_organs=["rbac", "guardian", "audit"],
        evidence_sources=["rbac.modification_logs", "audit.access_changes"]),

    # §164.308(a)(5) — Security Awareness and Training
    HIPAARequirement("§164.308(a)(5)(i)", "Security Awareness and Training", "required",
        "administrative", "Security Awareness and Training",
        "Implement security awareness and training program for all workforce members",
        veilcore_organs=["notification_engine", "alert_manager", "compliance_tracker"],
        veilcore_subsystems=["mobile", "accessibility"],
        evidence_sources=["notification_engine.training_alerts", "compliance_tracker.training_records"]),

    HIPAARequirement("§164.308(a)(5)(ii)(A)", "Security Reminders", "addressable",
        "administrative", "Security Reminders",
        "Periodic security updates and reminders",
        veilcore_organs=["notification_engine", "email_gateway", "sms_notifier"],
        veilcore_subsystems=["mobile"],
        evidence_sources=["notification_engine.reminder_logs"]),

    HIPAARequirement("§164.308(a)(5)(ii)(B)", "Protection from Malicious Software", "addressable",
        "administrative", "Protection from Malicious Software",
        "Procedures for guarding against, detecting, and reporting malicious software",
        veilcore_organs=["malware_detector", "ransomware_shield", "canary"],
        veilcore_subsystems=["ml"],
        evidence_sources=["malware_detector.detection_logs", "ransomware_shield.alerts"]),

    HIPAARequirement("§164.308(a)(5)(ii)(C)", "Log-in Monitoring", "addressable",
        "administrative", "Log-in Monitoring",
        "Procedures for monitoring log-in attempts and reporting discrepancies",
        veilcore_organs=["guardian", "sentinel", "behavioral_analysis", "anomaly_detector"],
        evidence_sources=["guardian.login_attempts", "sentinel.anomalous_logins"]),

    HIPAARequirement("§164.308(a)(5)(ii)(D)", "Password Management", "addressable",
        "administrative", "Password Management",
        "Procedures for creating, changing, and safeguarding passwords",
        veilcore_organs=["guardian", "mfa", "vault", "key_manager"],
        evidence_sources=["guardian.password_policies", "vault.credential_management"]),

    # §164.308(a)(6) — Security Incident Procedures
    HIPAARequirement("§164.308(a)(6)(i)", "Security Incident Procedures", "required",
        "administrative", "Security Incident Procedures",
        "Implement policies to address security incidents",
        veilcore_organs=["incident_responder", "forensic_collector", "alert_manager"],
        veilcore_subsystems=["mobile", "federation"],
        evidence_sources=["incident_responder.playbooks", "incident_responder.incident_logs"]),

    HIPAARequirement("§164.308(a)(6)(ii)", "Response and Reporting", "required",
        "administrative", "Response and Reporting",
        "Identify and respond to suspected or known security incidents; mitigate and document",
        veilcore_organs=["incident_responder", "quarantine", "forensic_collector", "notification_engine"],
        veilcore_subsystems=["mesh", "mobile"],
        evidence_sources=["incident_responder.response_logs", "quarantine.actions", "forensic_collector.evidence_chain"]),

    # §164.308(a)(7) — Contingency Plan
    HIPAARequirement("§164.308(a)(7)(i)", "Contingency Plan", "required",
        "administrative", "Contingency Plan",
        "Establish policies for responding to emergencies or other occurrences that damage ePHI systems",
        veilcore_organs=["disaster_recovery", "backup", "failover_controller"],
        veilcore_subsystems=["cloud"],
        evidence_sources=["disaster_recovery.plans", "disaster_recovery.drill_results"]),

    HIPAARequirement("§164.308(a)(7)(ii)(A)", "Data Backup Plan", "required",
        "administrative", "Data Backup Plan",
        "Establish procedures to create and maintain retrievable exact copies of ePHI",
        veilcore_organs=["backup", "backup_validator", "snapshot_manager", "replication_engine"],
        evidence_sources=["backup.schedules", "backup_validator.integrity_tests"]),

    HIPAARequirement("§164.308(a)(7)(ii)(B)", "Disaster Recovery Plan", "required",
        "administrative", "Disaster Recovery Plan",
        "Establish procedures to restore any loss of data",
        veilcore_organs=["disaster_recovery", "failover_controller", "backup_validator"],
        veilcore_subsystems=["cloud"],
        evidence_sources=["disaster_recovery.recovery_procedures", "failover_controller.failover_logs"]),

    HIPAARequirement("§164.308(a)(7)(ii)(C)", "Emergency Mode Operation Plan", "required",
        "administrative", "Emergency Mode Operation Plan",
        "Establish procedures to enable continuation of critical business processes during emergency",
        veilcore_organs=["disaster_recovery", "failover_controller", "load_balancer"],
        veilcore_subsystems=["cloud"],
        evidence_sources=["disaster_recovery.emergency_procedures"]),

    HIPAARequirement("§164.308(a)(7)(ii)(D)", "Testing and Revision Procedures", "addressable",
        "administrative", "Testing and Revision Procedures",
        "Implement procedures for periodic testing and revision of contingency plans",
        veilcore_organs=["backup_validator", "disaster_recovery"],
        veilcore_subsystems=["pentest"],
        evidence_sources=["backup_validator.test_results", "pentest.dr_test_reports"]),

    HIPAARequirement("§164.308(a)(7)(ii)(E)", "Applications and Data Criticality Analysis", "addressable",
        "administrative", "Applications and Data Criticality Analysis",
        "Assess the relative criticality of specific applications and data in support of contingency plans",
        veilcore_organs=["risk_analyzer", "phi_classifier", "compliance_engine"],
        evidence_sources=["risk_analyzer.criticality_analysis", "phi_classifier.data_inventory"]),

    # §164.308(a)(8) — Evaluation
    HIPAARequirement("§164.308(a)(8)", "Evaluation", "required",
        "administrative", "Evaluation",
        "Perform periodic technical and nontechnical evaluation of security controls",
        veilcore_organs=["compliance_engine", "config_auditor", "vulnerability_scanner"],
        veilcore_subsystems=["pentest"],
        evidence_sources=["compliance_engine.evaluations", "pentest.assessment_reports"]),

    # ───────────────────────────────────────────────────────────
    #  PHYSICAL SAFEGUARDS — §164.310
    # ───────────────────────────────────────────────────────────

    # §164.310(a) — Facility Access Controls
    HIPAARequirement("§164.310(a)(1)", "Facility Access Controls", "required",
        "physical", "Facility Access Controls",
        "Implement policies to limit physical access to electronic information systems",
        veilcore_subsystems=["physical"],
        veilcore_organs=["compliance_engine"],
        evidence_sources=["physical.sensor_events", "physical.camera_events", "physical.rfid_logs"]),

    HIPAARequirement("§164.310(a)(2)(i)", "Contingency Operations", "addressable",
        "physical", "Contingency Operations",
        "Establish procedures for facility access during disaster recovery",
        veilcore_organs=["disaster_recovery"],
        veilcore_subsystems=["physical"],
        evidence_sources=["physical.emergency_access_logs", "disaster_recovery.facility_procedures"]),

    HIPAARequirement("§164.310(a)(2)(ii)", "Facility Security Plan", "addressable",
        "physical", "Facility Security Plan",
        "Implement policies to safeguard the facility and equipment from unauthorized access and theft",
        veilcore_subsystems=["physical", "wireless"],
        evidence_sources=["physical.security_plan", "physical.sensor_coverage_map"]),

    HIPAARequirement("§164.310(a)(2)(iii)", "Access Control and Validation Procedures", "addressable",
        "physical", "Access Control and Validation Procedures",
        "Implement procedures to control and validate a person's access to facilities based on role",
        veilcore_subsystems=["physical"],
        veilcore_organs=["rbac"],
        evidence_sources=["physical.rfid_logs", "physical.badge_validations"]),

    HIPAARequirement("§164.310(a)(2)(iv)", "Maintenance Records", "addressable",
        "physical", "Maintenance Records",
        "Document repairs and modifications to the physical components of a facility related to security",
        veilcore_organs=["chronicle", "audit"],
        veilcore_subsystems=["physical"],
        evidence_sources=["chronicle.maintenance_records", "physical.camera_firmware_logs"]),

    # §164.310(b) — Workstation Use
    HIPAARequirement("§164.310(b)", "Workstation Use", "required",
        "physical", "Workstation Use",
        "Implement policies specifying the proper functions, manner of use, and physical attributes of workstations",
        veilcore_organs=["host_sensor", "session_monitor", "zero_trust_engine"],
        evidence_sources=["host_sensor.workstation_inventory", "session_monitor.workstation_policies"]),

    # §164.310(c) — Workstation Security
    HIPAARequirement("§164.310(c)", "Workstation Security", "required",
        "physical", "Workstation Security",
        "Implement physical safeguards that restrict access to authorized users",
        veilcore_organs=["host_sensor", "zero_trust_engine"],
        veilcore_subsystems=["physical"],
        evidence_sources=["host_sensor.device_posture", "physical.workstation_monitoring"]),

    # §164.310(d) — Device and Media Controls
    HIPAARequirement("§164.310(d)(1)", "Device and Media Controls", "required",
        "physical", "Device and Media Controls",
        "Implement policies governing receipt and removal of hardware and electronic media",
        veilcore_organs=["dlp_engine", "file_monitor", "encryptor"],
        veilcore_subsystems=["wireless"],
        evidence_sources=["dlp_engine.media_controls", "wireless.device_inventory"]),

    HIPAARequirement("§164.310(d)(2)(i)", "Disposal", "required",
        "physical", "Disposal",
        "Implement policies for final disposal of ePHI and the hardware or media on which it is stored",
        veilcore_organs=["encryptor", "dlp_engine", "audit"],
        evidence_sources=["encryptor.disposal_certificates", "audit.disposal_logs"]),

    HIPAARequirement("§164.310(d)(2)(ii)", "Media Re-use", "required",
        "physical", "Media Re-use",
        "Implement procedures for removal of ePHI from media before reuse",
        veilcore_organs=["encryptor", "integrity_checker", "dlp_engine"],
        evidence_sources=["encryptor.wipe_logs", "integrity_checker.media_verification"]),

    HIPAARequirement("§164.310(d)(2)(iii)", "Accountability", "addressable",
        "physical", "Accountability",
        "Maintain records of movements of hardware and electronic media",
        veilcore_organs=["audit", "chronicle"],
        veilcore_subsystems=["physical", "wireless"],
        evidence_sources=["chronicle.asset_tracking", "wireless.device_movement_logs"]),

    HIPAARequirement("§164.310(d)(2)(iv)", "Data Backup and Storage", "addressable",
        "physical", "Data Backup and Storage",
        "Create a retrievable exact copy of ePHI before moving equipment",
        veilcore_organs=["backup", "backup_validator", "snapshot_manager"],
        evidence_sources=["backup.pre_move_backups", "backup_validator.integrity_checks"]),

    # ───────────────────────────────────────────────────────────
    #  TECHNICAL SAFEGUARDS — §164.312
    # ───────────────────────────────────────────────────────────

    # §164.312(a) — Access Control
    HIPAARequirement("§164.312(a)(1)", "Access Control", "required",
        "technical", "Access Control",
        "Implement technical policies to allow access only to authorized persons or software programs",
        veilcore_organs=["guardian", "rbac", "mfa", "zero_trust_engine"],
        evidence_sources=["guardian.access_logs", "rbac.policy_enforcement"]),

    HIPAARequirement("§164.312(a)(2)(i)", "Unique User Identification", "required",
        "technical", "Unique User Identification",
        "Assign a unique name and/or number for identifying and tracking user identity",
        veilcore_organs=["guardian", "imprivata_bridge", "audit"],
        evidence_sources=["guardian.user_registry", "imprivata_bridge.identity_logs"]),

    HIPAARequirement("§164.312(a)(2)(ii)", "Emergency Access Procedure", "required",
        "technical", "Emergency Access Procedure",
        "Establish procedures for obtaining necessary ePHI during an emergency",
        veilcore_organs=["guardian", "disaster_recovery", "vault"],
        evidence_sources=["guardian.emergency_access_logs", "disaster_recovery.break_glass_procedures"]),

    HIPAARequirement("§164.312(a)(2)(iii)", "Automatic Logoff", "addressable",
        "technical", "Automatic Logoff",
        "Implement procedures that terminate an electronic session after a period of inactivity",
        veilcore_organs=["session_monitor", "guardian"],
        evidence_sources=["session_monitor.timeout_logs", "guardian.session_policies"]),

    HIPAARequirement("§164.312(a)(2)(iv)", "Encryption and Decryption", "addressable",
        "technical", "Encryption and Decryption",
        "Implement a mechanism to encrypt and decrypt ePHI",
        veilcore_organs=["encryption_enforcer", "encryptor", "key_manager", "vault"],
        evidence_sources=["encryption_enforcer.encryption_status", "key_manager.key_inventory"]),

    # §164.312(b) — Audit Controls
    HIPAARequirement("§164.312(b)", "Audit Controls", "required",
        "technical", "Audit Controls",
        "Implement hardware, software, and/or procedures to record and examine activity in systems containing ePHI",
        veilcore_organs=["audit", "chronicle", "log_aggregator", "siem_connector", "metrics_collector"],
        evidence_sources=["chronicle.immutable_timeline", "audit.activity_records", "siem_connector.correlated_events"]),

    # §164.312(c) — Integrity
    HIPAARequirement("§164.312(c)(1)", "Integrity", "required",
        "technical", "Integrity",
        "Implement policies to protect ePHI from improper alteration or destruction",
        veilcore_organs=["integrity_checker", "file_monitor", "encryption_enforcer"],
        evidence_sources=["integrity_checker.hash_validations", "file_monitor.change_alerts"]),

    HIPAARequirement("§164.312(c)(2)", "Mechanism to Authenticate ePHI", "addressable",
        "technical", "Mechanism to Authenticate ePHI",
        "Implement electronic mechanisms to corroborate that ePHI has not been altered or destroyed",
        veilcore_organs=["integrity_checker", "chronicle", "encryption_enforcer"],
        evidence_sources=["integrity_checker.authentication_hashes", "chronicle.blockchain_ledger"]),

    # §164.312(d) — Person or Entity Authentication
    HIPAARequirement("§164.312(d)", "Person or Entity Authentication", "required",
        "technical", "Person or Entity Authentication",
        "Implement procedures to verify that a person or entity seeking access to ePHI is who they claim to be",
        veilcore_organs=["guardian", "mfa", "imprivata_bridge", "zero_trust_engine"],
        evidence_sources=["guardian.authentication_logs", "mfa.verification_logs", "imprivata_bridge.sso_logs"]),

    # §164.312(e) — Transmission Security
    HIPAARequirement("§164.312(e)(1)", "Transmission Security", "required",
        "technical", "Transmission Security",
        "Implement technical security measures to guard against unauthorized access to ePHI transmitted over networks",
        veilcore_organs=["ssl_inspector", "vpn_manager", "certificate_authority", "encryption_enforcer"],
        veilcore_subsystems=["wireless"],
        evidence_sources=["ssl_inspector.tls_audit", "vpn_manager.tunnel_logs"]),

    HIPAARequirement("§164.312(e)(2)(i)", "Integrity Controls (Transmission)", "addressable",
        "technical", "Integrity Controls for Transmission",
        "Implement security measures to ensure ePHI is not improperly modified during transmission",
        veilcore_organs=["ssl_inspector", "hl7_filter", "fhir_gateway", "dicom_shield"],
        evidence_sources=["hl7_filter.integrity_checks", "fhir_gateway.message_validation"]),

    HIPAARequirement("§164.312(e)(2)(ii)", "Encryption (Transmission)", "addressable",
        "technical", "Encryption for Transmission",
        "Implement a mechanism to encrypt ePHI whenever deemed appropriate",
        veilcore_organs=["encryption_enforcer", "ssl_inspector", "vpn_manager"],
        veilcore_subsystems=["wireless", "federation"],
        evidence_sources=["encryption_enforcer.transit_encryption_audit"]),

    # ───────────────────────────────────────────────────────────
    #  ORGANIZATIONAL REQUIREMENTS — §164.314
    # ───────────────────────────────────────────────────────────

    HIPAARequirement("§164.314(a)(1)", "Business Associate Contracts", "required",
        "organizational", "Business Associate Contracts",
        "Require satisfactory assurances from business associates to safeguard ePHI",
        veilcore_organs=["compliance_tracker", "api_gateway", "audit"],
        veilcore_subsystems=["federation"],
        evidence_sources=["compliance_tracker.ba_agreements", "api_gateway.third_party_audit"]),

    HIPAARequirement("§164.314(a)(2)", "Business Associate Requirements", "required",
        "organizational", "Business Associate Implementation",
        "Business associates must comply with applicable Security Rule requirements",
        veilcore_organs=["compliance_tracker", "threat_intel"],
        veilcore_subsystems=["federation"],
        evidence_sources=["compliance_tracker.ba_compliance_status", "federation.peer_compliance"]),

    # ───────────────────────────────────────────────────────────
    #  POLICIES AND DOCUMENTATION — §164.316
    # ───────────────────────────────────────────────────────────

    HIPAARequirement("§164.316(a)", "Policies and Procedures", "required",
        "policies", "Policies and Procedures",
        "Implement reasonable and appropriate policies and procedures to comply with Security Rule",
        veilcore_organs=["compliance_engine", "compliance_tracker", "cortex"],
        evidence_sources=["compliance_engine.policy_repository", "compliance_tracker.policy_index"]),

    HIPAARequirement("§164.316(b)(1)", "Documentation", "required",
        "policies", "Documentation",
        "Maintain written policies, procedures, actions, activities, and assessments required by the Security Rule",
        veilcore_organs=["chronicle", "audit", "compliance_tracker", "forensic_collector"],
        evidence_sources=["chronicle.immutable_timeline", "audit.documentation_index"]),

    HIPAARequirement("§164.316(b)(2)(i)", "Time Limit", "required",
        "policies", "Documentation Retention — Time Limit",
        "Retain documentation for 6 years from date of creation or last effective date",
        veilcore_organs=["chronicle", "audit", "backup", "replication_engine"],
        evidence_sources=["chronicle.retention_policy", "backup.retention_schedules"]),

    HIPAARequirement("§164.316(b)(2)(ii)", "Availability", "required",
        "policies", "Documentation Availability",
        "Make documentation available to those persons responsible for implementing the procedures",
        veilcore_organs=["compliance_tracker", "notification_engine"],
        veilcore_subsystems=["mobile", "accessibility"],
        evidence_sources=["compliance_tracker.document_access_logs"]),

    HIPAARequirement("§164.316(b)(2)(iii)", "Updates", "required",
        "policies", "Documentation Updates",
        "Review documentation periodically and update as needed in response to changes",
        veilcore_organs=["compliance_engine", "config_auditor", "compliance_tracker"],
        evidence_sources=["compliance_engine.review_schedule", "config_auditor.policy_change_logs"]),
]


@dataclass
class HIPAAAssessment:
    """HIPAA Security Rule compliance assessment."""
    assessment_id: str = field(default_factory=lambda: f"HIPAA-{int(time.time())}")
    total_requirements: int = 0
    full_coverage: int = 0
    partial_coverage: int = 0
    no_coverage: int = 0
    coverage_pct: float = 0.0
    required_met: int = 0
    required_total: int = 0
    addressable_met: int = 0
    addressable_total: int = 0
    by_category: dict[str, dict] = field(default_factory=dict)
    by_section: dict[str, dict] = field(default_factory=dict)
    gaps: list[dict] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "total_requirements": self.total_requirements,
            "full_coverage": self.full_coverage,
            "partial_coverage": self.partial_coverage,
            "no_coverage": self.no_coverage,
            "coverage_pct": round(self.coverage_pct, 1),
            "required": f"{self.required_met}/{self.required_total}",
            "addressable": f"{self.addressable_met}/{self.addressable_total}",
            "by_category": self.by_category,
            "by_section": self.by_section,
            "gaps": self.gaps,
            "timestamp": self.timestamp,
        }


class HIPAAMapper:
    """
    Complete HIPAA Security Rule compliance mapper.

    Usage:
        mapper = HIPAAMapper()
        assessment = mapper.assess()
        print(f"HIPAA Coverage: {assessment.coverage_pct}%")
        print(f"Required: {assessment.required_met}/{assessment.required_total}")
    """

    def __init__(self):
        self._requirements = list(HIPAA_REQUIREMENTS)

    def assess(self) -> HIPAAAssessment:
        result = HIPAAAssessment()
        result.total_requirements = len(self._requirements)

        for req in self._requirements:
            has_coverage = len(req.veilcore_organs) > 0 or len(req.veilcore_subsystems) > 0

            if req.spec_type == "required":
                result.required_total += 1
                if has_coverage:
                    result.required_met += 1
            else:
                result.addressable_total += 1
                if has_coverage:
                    result.addressable_met += 1

            if req.coverage == "full" and has_coverage:
                result.full_coverage += 1
            elif has_coverage:
                result.partial_coverage += 1
            else:
                result.no_coverage += 1
                result.gaps.append({"section": req.section, "title": req.title, "type": req.spec_type})

            # By category
            cat = req.category
            if cat not in result.by_category:
                result.by_category[cat] = {"full": 0, "partial": 0, "none": 0, "total": 0}
            result.by_category[cat]["total"] += 1
            if req.coverage == "full" and has_coverage:
                result.by_category[cat]["full"] += 1
            elif has_coverage:
                result.by_category[cat]["partial"] += 1
            else:
                result.by_category[cat]["none"] += 1

            # By section (top level)
            sec = req.section.split("(")[0] + "(" + req.section.split("(")[1].split(")")[0] + ")" if "(" in req.section else req.section
            if sec not in result.by_section:
                result.by_section[sec] = {"met": 0, "total": 0}
            result.by_section[sec]["total"] += 1
            if has_coverage:
                result.by_section[sec]["met"] += 1

        total = result.full_coverage + result.partial_coverage + result.no_coverage
        if total > 0:
            result.coverage_pct = ((result.full_coverage + result.partial_coverage * 0.5) / total) * 100

        return result

    def get_requirement(self, section: str) -> Optional[HIPAARequirement]:
        for r in self._requirements:
            if r.section == section:
                return r
        return None

    def get_by_category(self, category: str) -> list[HIPAARequirement]:
        return [r for r in self._requirements if r.category == category]

    def get_organ_requirements(self, organ: str) -> list[HIPAARequirement]:
        return [r for r in self._requirements if organ in r.veilcore_organs]

    def get_gaps(self) -> list[HIPAARequirement]:
        return [r for r in self._requirements
                if not r.veilcore_organs and not r.veilcore_subsystems]

    def generate_report(self) -> dict[str, Any]:
        assessment = self.assess()
        return {
            "framework": "HIPAA Security Rule",
            "regulation": "45 CFR Part 164, Subpart C",
            "codename": "ShieldLaw",
            "assessment": assessment.to_dict(),
            "requirements": [r.to_dict() for r in self._requirements],
        }

    def summary(self) -> dict[str, Any]:
        a = self.assess()
        return {
            "framework": "HIPAA Security Rule",
            "codename": "ShieldLaw",
            "total_requirements": a.total_requirements,
            "coverage_pct": a.coverage_pct,
            "required": f"{a.required_met}/{a.required_total}",
            "addressable": f"{a.addressable_met}/{a.addressable_total}",
            "gaps": len(a.gaps),
            "categories": {k: f"{v['full']}/{v['total']} full" for k, v in a.by_category.items()},
        }
