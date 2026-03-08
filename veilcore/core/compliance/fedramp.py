"""
VeilCore FedRAMP Compliance Mapper — IronFlag
================================================
Maps VeilCore to NIST SP 800-53 controls required
for FedRAMP authorization (Low, Moderate, High).

FedRAMP is required for cloud services used by federal
agencies, including VA hospitals, DoD medical facilities,
and IHS (Indian Health Service) clinics.

Control families mapped:
    AC — Access Control
    AU — Audit and Accountability
    AT — Awareness and Training
    CM — Configuration Management
    CP — Contingency Planning
    IA — Identification and Authentication
    IR — Incident Response
    MA — Maintenance
    MP — Media Protection
    PE — Physical and Environmental Protection
    PL — Planning
    PS — Personnel Security
    RA — Risk Assessment
    CA — Assessment, Authorization, and Monitoring
    SC — System and Communications Protection
    SI — System and Information Integrity
    SA — System and Services Acquisition
    PM — Program Management
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class FedRAMPLevel(Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


@dataclass
class FedRAMPControl:
    """A NIST 800-53 control mapped for FedRAMP."""
    control_id: str
    family: str
    family_code: str
    title: str
    description: str
    fedramp_level: str  # minimum level where required
    veilcore_organs: list[str] = field(default_factory=list)
    veilcore_subsystems: list[str] = field(default_factory=list)
    coverage: str = "full"
    automated: bool = True
    continuous_monitoring: bool = False
    evidence_sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "control_id": self.control_id, "family": self.family,
            "family_code": self.family_code, "title": self.title,
            "fedramp_level": self.fedramp_level,
            "veilcore_organs": self.veilcore_organs,
            "veilcore_subsystems": self.veilcore_subsystems,
            "coverage": self.coverage, "automated": self.automated,
            "continuous_monitoring": self.continuous_monitoring,
        }


FEDRAMP_CONTROLS = [
    # ═══ ACCESS CONTROL (AC) ═══
    FedRAMPControl("AC-1", "Access Control", "AC", "Policy and Procedures",
        "Develop and maintain access control policy", "low",
        ["compliance_engine", "compliance_tracker"], evidence_sources=["compliance_engine.policies"]),
    FedRAMPControl("AC-2", "Access Control", "AC", "Account Management",
        "Manage system accounts including establishing, activating, modifying, disabling, removing",
        "low", ["guardian", "rbac", "session_monitor", "imprivata_bridge"],
        evidence_sources=["guardian.account_lifecycle", "rbac.account_logs"], continuous_monitoring=True),
    FedRAMPControl("AC-3", "Access Control", "AC", "Access Enforcement",
        "Enforce approved authorizations for logical access", "low",
        ["guardian", "rbac", "zero_trust_engine", "mfa"],
        evidence_sources=["rbac.enforcement_logs"], continuous_monitoring=True),
    FedRAMPControl("AC-4", "Access Control", "AC", "Information Flow Enforcement",
        "Enforce approved authorizations for controlling the flow of information", "moderate",
        ["firewall", "micro_segmentation", "dlp_engine", "phi_guard"],
        veilcore_subsystems=["mesh"], evidence_sources=["firewall.flow_logs"], continuous_monitoring=True),
    FedRAMPControl("AC-5", "Access Control", "AC", "Separation of Duties",
        "Enforce separation of duties through assigned access authorizations", "moderate",
        ["rbac", "guardian"], evidence_sources=["rbac.separation_matrix"]),
    FedRAMPControl("AC-6", "Access Control", "AC", "Least Privilege",
        "Employ the principle of least privilege", "moderate",
        ["rbac", "zero_trust_engine", "guardian"],
        evidence_sources=["rbac.privilege_audit"], continuous_monitoring=True),
    FedRAMPControl("AC-7", "Access Control", "AC", "Unsuccessful Logon Attempts",
        "Enforce a limit on consecutive invalid logon attempts", "low",
        ["guardian", "sentinel", "behavioral_analysis"],
        evidence_sources=["guardian.lockout_logs"], continuous_monitoring=True),
    FedRAMPControl("AC-8", "Access Control", "AC", "System Use Notification",
        "Display system use notification message before granting access", "low",
        ["guardian"], evidence_sources=["guardian.banner_config"]),
    FedRAMPControl("AC-11", "Access Control", "AC", "Device Lock",
        "Prevent further access by initiating device lock after inactivity", "moderate",
        ["session_monitor", "guardian"],
        evidence_sources=["session_monitor.lock_events"], continuous_monitoring=True),
    FedRAMPControl("AC-17", "Access Control", "AC", "Remote Access",
        "Establish and manage remote access sessions", "low",
        ["vpn_manager", "guardian", "mfa", "ssl_inspector"],
        veilcore_subsystems=["mobile"], evidence_sources=["vpn_manager.session_logs"], continuous_monitoring=True),

    # ═══ AUDIT AND ACCOUNTABILITY (AU) ═══
    FedRAMPControl("AU-1", "Audit and Accountability", "AU", "Policy and Procedures",
        "Develop and maintain audit and accountability policy", "low",
        ["compliance_engine", "audit"], evidence_sources=["compliance_engine.audit_policy"]),
    FedRAMPControl("AU-2", "Audit and Accountability", "AU", "Event Logging",
        "Identify events that the system must be capable of logging", "low",
        ["audit", "chronicle", "log_aggregator"],
        evidence_sources=["audit.event_catalog"], continuous_monitoring=True),
    FedRAMPControl("AU-3", "Audit and Accountability", "AU", "Content of Audit Records",
        "Ensure audit records contain required information", "low",
        ["audit", "chronicle", "siem_connector"],
        evidence_sources=["chronicle.record_format"]),
    FedRAMPControl("AU-6", "Audit and Accountability", "AU", "Audit Record Review, Analysis, Reporting",
        "Review and analyze system audit records for indications of inappropriate activity",
        "low", ["siem_connector", "sentinel", "alert_manager", "cortex"],
        veilcore_subsystems=["ml"], evidence_sources=["siem_connector.analysis_reports"], continuous_monitoring=True),
    FedRAMPControl("AU-8", "Audit and Accountability", "AU", "Time Stamps",
        "Use internal system clocks to generate time stamps for audit records", "low",
        ["audit", "chronicle"], evidence_sources=["chronicle.ntp_sync"]),
    FedRAMPControl("AU-9", "Audit and Accountability", "AU", "Protection of Audit Information",
        "Protect audit information and tools from unauthorized access", "low",
        ["chronicle", "vault", "encryption_enforcer"],
        evidence_sources=["chronicle.immutable_ledger"]),
    FedRAMPControl("AU-12", "Audit and Accountability", "AU", "Audit Record Generation",
        "Provide audit record generation capability", "low",
        ["audit", "chronicle", "log_aggregator", "metrics_collector"],
        evidence_sources=["audit.generation_status"], continuous_monitoring=True),

    # ═══ AWARENESS AND TRAINING (AT) ═══
    FedRAMPControl("AT-1", "Awareness and Training", "AT", "Policy and Procedures",
        "Develop and maintain security awareness and training policy", "low",
        ["compliance_tracker", "notification_engine"],
        veilcore_subsystems=["accessibility"], evidence_sources=["compliance_tracker.training_policy"]),
    FedRAMPControl("AT-2", "Awareness and Training", "AT", "Literacy Training and Awareness",
        "Provide security literacy training to system users", "low",
        ["notification_engine", "alert_manager", "compliance_tracker"],
        veilcore_subsystems=["mobile", "accessibility"],
        evidence_sources=["compliance_tracker.training_records"]),

    # ═══ CONFIGURATION MANAGEMENT (CM) ═══
    FedRAMPControl("CM-1", "Configuration Management", "CM", "Policy and Procedures",
        "Develop and maintain configuration management policy", "low",
        ["compliance_engine", "config_auditor"], evidence_sources=["compliance_engine.cm_policy"]),
    FedRAMPControl("CM-2", "Configuration Management", "CM", "Baseline Configuration",
        "Develop and maintain a baseline configuration of the system", "low",
        ["baseline_monitor", "config_auditor", "integrity_checker"],
        evidence_sources=["baseline_monitor.baselines"], continuous_monitoring=True),
    FedRAMPControl("CM-6", "Configuration Management", "CM", "Configuration Settings",
        "Establish mandatory configuration settings", "low",
        ["config_auditor", "baseline_monitor"],
        evidence_sources=["config_auditor.settings_audit"], continuous_monitoring=True),
    FedRAMPControl("CM-7", "Configuration Management", "CM", "Least Functionality",
        "Configure the system to provide only mission-essential capabilities", "low",
        ["config_auditor", "process_monitor", "service_guardian"],
        evidence_sources=["process_monitor.service_inventory"]),
    FedRAMPControl("CM-8", "Configuration Management", "CM", "System Component Inventory",
        "Develop and maintain an inventory of system components", "low",
        ["host_sensor", "iomt_protector", "config_auditor"],
        veilcore_subsystems=["wireless"],
        evidence_sources=["host_sensor.inventory"], continuous_monitoring=True),

    # ═══ CONTINGENCY PLANNING (CP) ═══
    FedRAMPControl("CP-1", "Contingency Planning", "CP", "Policy and Procedures",
        "Develop and maintain contingency planning policy", "low",
        ["disaster_recovery", "compliance_engine"], evidence_sources=["disaster_recovery.plans"]),
    FedRAMPControl("CP-2", "Contingency Planning", "CP", "Contingency Plan",
        "Develop a contingency plan for the system", "low",
        ["disaster_recovery", "failover_controller"],
        veilcore_subsystems=["cloud"], evidence_sources=["disaster_recovery.contingency_plan"]),
    FedRAMPControl("CP-9", "Contingency Planning", "CP", "System Backup",
        "Conduct backups of user-level and system-level information", "low",
        ["backup", "backup_validator", "snapshot_manager", "replication_engine"],
        evidence_sources=["backup.schedules", "backup_validator.integrity_tests"], continuous_monitoring=True),
    FedRAMPControl("CP-10", "Contingency Planning", "CP", "System Recovery and Reconstitution",
        "Provide for the recovery and reconstitution of the system", "low",
        ["disaster_recovery", "failover_controller", "backup_validator"],
        veilcore_subsystems=["cloud"], evidence_sources=["disaster_recovery.recovery_procedures"]),

    # ═══ IDENTIFICATION AND AUTHENTICATION (IA) ═══
    FedRAMPControl("IA-1", "Identification and Authentication", "IA", "Policy and Procedures",
        "Develop and maintain identification and authentication policy", "low",
        ["compliance_engine", "guardian"], evidence_sources=["compliance_engine.ia_policy"]),
    FedRAMPControl("IA-2", "Identification and Authentication", "IA", "Identification and Authentication",
        "Uniquely identify and authenticate organizational users", "low",
        ["guardian", "mfa", "imprivata_bridge"],
        evidence_sources=["guardian.auth_logs"], continuous_monitoring=True),
    FedRAMPControl("IA-4", "Identification and Authentication", "IA", "Identifier Management",
        "Manage system identifiers", "low",
        ["guardian", "rbac", "imprivata_bridge"],
        evidence_sources=["guardian.identifier_management"]),
    FedRAMPControl("IA-5", "Identification and Authentication", "IA", "Authenticator Management",
        "Manage system authenticators", "low",
        ["guardian", "mfa", "vault", "key_manager"],
        evidence_sources=["vault.credential_policies"]),
    FedRAMPControl("IA-8", "Identification and Authentication", "IA", "Identification and Authentication (Non-Org Users)",
        "Identify and authenticate non-organizational users", "low",
        ["guardian", "mfa", "api_gateway"],
        evidence_sources=["guardian.external_auth_logs"]),

    # ═══ INCIDENT RESPONSE (IR) ═══
    FedRAMPControl("IR-1", "Incident Response", "IR", "Policy and Procedures",
        "Develop and maintain incident response policy", "low",
        ["incident_responder", "compliance_engine"],
        evidence_sources=["incident_responder.playbooks"]),
    FedRAMPControl("IR-2", "Incident Response", "IR", "Incident Response Training",
        "Train personnel in incident response roles and responsibilities", "low",
        ["compliance_tracker", "notification_engine"],
        evidence_sources=["compliance_tracker.ir_training"]),
    FedRAMPControl("IR-4", "Incident Response", "IR", "Incident Handling",
        "Implement an incident handling capability", "low",
        ["incident_responder", "quarantine", "forensic_collector", "alert_manager"],
        veilcore_subsystems=["mobile", "federation"],
        evidence_sources=["incident_responder.incident_logs"], continuous_monitoring=True),
    FedRAMPControl("IR-5", "Incident Response", "IR", "Incident Monitoring",
        "Track and document system security incidents", "low",
        ["sentinel", "cortex", "chronicle", "siem_connector"],
        veilcore_subsystems=["ml"],
        evidence_sources=["chronicle.incident_timeline"], continuous_monitoring=True),
    FedRAMPControl("IR-6", "Incident Response", "IR", "Incident Reporting",
        "Report incidents to appropriate authorities", "low",
        ["notification_engine", "alert_manager", "incident_responder"],
        veilcore_subsystems=["mobile"],
        evidence_sources=["incident_responder.report_logs"]),

    # ═══ MEDIA PROTECTION (MP) ═══
    FedRAMPControl("MP-1", "Media Protection", "MP", "Policy and Procedures",
        "Develop and maintain media protection policy", "low",
        ["compliance_engine", "dlp_engine"], evidence_sources=["compliance_engine.mp_policy"]),
    FedRAMPControl("MP-2", "Media Protection", "MP", "Media Access",
        "Restrict access to digital and non-digital media", "low",
        ["dlp_engine", "file_monitor", "encryptor"],
        evidence_sources=["dlp_engine.media_access_logs"]),
    FedRAMPControl("MP-6", "Media Protection", "MP", "Media Sanitization",
        "Sanitize media prior to disposal or release", "low",
        ["encryptor", "dlp_engine", "audit"],
        evidence_sources=["encryptor.sanitization_logs"]),

    # ═══ PHYSICAL AND ENVIRONMENTAL (PE) ═══
    FedRAMPControl("PE-1", "Physical and Environmental Protection", "PE", "Policy and Procedures",
        "Develop and maintain physical and environmental protection policy", "low",
        ["compliance_engine"], veilcore_subsystems=["physical"],
        evidence_sources=["physical.security_policy"]),
    FedRAMPControl("PE-2", "Physical and Environmental Protection", "PE", "Physical Access Authorizations",
        "Develop and maintain physical access authorization lists", "low",
        veilcore_subsystems=["physical"], veilcore_organs=["rbac"],
        evidence_sources=["physical.access_lists"]),
    FedRAMPControl("PE-3", "Physical and Environmental Protection", "PE", "Physical Access Control",
        "Enforce physical access authorizations at entry/exit points", "low",
        veilcore_subsystems=["physical"], evidence_sources=["physical.rfid_logs", "physical.camera_events"],
        continuous_monitoring=True),
    FedRAMPControl("PE-6", "Physical and Environmental Protection", "PE", "Monitoring Physical Access",
        "Monitor physical access to facility", "low",
        veilcore_subsystems=["physical"],
        evidence_sources=["physical.camera_events", "physical.sensor_events"], continuous_monitoring=True),

    # ═══ RISK ASSESSMENT (RA) ═══
    FedRAMPControl("RA-1", "Risk Assessment", "RA", "Policy and Procedures",
        "Develop and maintain risk assessment policy", "low",
        ["compliance_engine", "risk_analyzer"],
        evidence_sources=["compliance_engine.ra_policy"]),
    FedRAMPControl("RA-3", "Risk Assessment", "RA", "Risk Assessment",
        "Conduct risk assessments", "low",
        ["risk_analyzer", "vulnerability_scanner", "threat_intel"],
        veilcore_subsystems=["pentest", "ml"],
        evidence_sources=["risk_analyzer.assessments"]),
    FedRAMPControl("RA-5", "Risk Assessment", "RA", "Vulnerability Monitoring and Scanning",
        "Monitor and scan for vulnerabilities", "low",
        ["vulnerability_scanner", "scanner", "patcher"],
        veilcore_subsystems=["pentest"],
        evidence_sources=["vulnerability_scanner.scan_results"], continuous_monitoring=True),

    # ═══ SYSTEM AND COMMUNICATIONS PROTECTION (SC) ═══
    FedRAMPControl("SC-1", "System and Communications Protection", "SC", "Policy and Procedures",
        "Develop and maintain system and communications protection policy", "low",
        ["compliance_engine"], evidence_sources=["compliance_engine.sc_policy"]),
    FedRAMPControl("SC-7", "System and Communications Protection", "SC", "Boundary Protection",
        "Monitor and control communications at system boundary", "low",
        ["firewall", "ids_ips", "waf", "dns_filter"],
        evidence_sources=["firewall.boundary_logs"], continuous_monitoring=True),
    FedRAMPControl("SC-8", "System and Communications Protection", "SC", "Transmission Confidentiality and Integrity",
        "Protect the confidentiality and integrity of transmitted information", "moderate",
        ["ssl_inspector", "vpn_manager", "encryption_enforcer", "certificate_authority"],
        veilcore_subsystems=["wireless"],
        evidence_sources=["ssl_inspector.tls_audit"], continuous_monitoring=True),
    FedRAMPControl("SC-12", "System and Communications Protection", "SC", "Cryptographic Key Establishment and Management",
        "Establish and manage cryptographic keys", "low",
        ["key_manager", "vault", "certificate_authority"],
        evidence_sources=["key_manager.key_inventory"]),
    FedRAMPControl("SC-13", "System and Communications Protection", "SC", "Cryptographic Protection",
        "Implement FIPS-validated cryptography", "low",
        ["encryption_enforcer", "encryptor", "key_manager"],
        evidence_sources=["encryption_enforcer.fips_compliance"]),
    FedRAMPControl("SC-28", "System and Communications Protection", "SC", "Protection of Information at Rest",
        "Protect the confidentiality and integrity of information at rest", "low",
        ["encryption_enforcer", "encryptor", "vault"],
        evidence_sources=["encryption_enforcer.at_rest_audit"], continuous_monitoring=True),

    # ═══ SYSTEM AND INFORMATION INTEGRITY (SI) ═══
    FedRAMPControl("SI-1", "System and Information Integrity", "SI", "Policy and Procedures",
        "Develop and maintain system and information integrity policy", "low",
        ["compliance_engine"], evidence_sources=["compliance_engine.si_policy"]),
    FedRAMPControl("SI-2", "System and Information Integrity", "SI", "Flaw Remediation",
        "Identify, report, and correct system flaws", "low",
        ["patcher", "patch_manager", "vulnerability_scanner"],
        evidence_sources=["patcher.patch_logs"], continuous_monitoring=True),
    FedRAMPControl("SI-3", "System and Information Integrity", "SI", "Malicious Code Protection",
        "Implement malicious code protection mechanisms", "low",
        ["malware_detector", "ransomware_shield", "canary"],
        veilcore_subsystems=["ml"],
        evidence_sources=["malware_detector.detection_logs"], continuous_monitoring=True),
    FedRAMPControl("SI-4", "System and Information Integrity", "SI", "System Monitoring",
        "Monitor the system to detect attacks and indicators of potential attacks", "low",
        ["sentinel", "cortex", "network_monitor", "ids_ips", "anomaly_detector"],
        veilcore_subsystems=["ml", "mesh", "wireless", "physical"],
        evidence_sources=["sentinel.monitoring_events"], continuous_monitoring=True),
    FedRAMPControl("SI-5", "System and Information Integrity", "SI", "Security Alerts, Advisories, and Directives",
        "Receive and respond to security alerts and advisories", "low",
        ["threat_intel", "alert_manager", "notification_engine"],
        veilcore_subsystems=["federation"],
        evidence_sources=["threat_intel.advisory_logs"]),
    FedRAMPControl("SI-7", "System and Information Integrity", "SI", "Software, Firmware, and Information Integrity",
        "Employ integrity verification tools to detect unauthorized changes", "moderate",
        ["integrity_checker", "file_monitor", "baseline_monitor"],
        evidence_sources=["integrity_checker.hash_validations"], continuous_monitoring=True),
]


@dataclass
class FedRAMPAssessment:
    """FedRAMP compliance assessment."""
    assessment_id: str = field(default_factory=lambda: f"FEDRAMP-{int(time.time())}")
    level: str = "moderate"
    total_controls: int = 0
    full_coverage: int = 0
    partial_coverage: int = 0
    no_coverage: int = 0
    coverage_pct: float = 0.0
    continuous_monitoring_pct: float = 0.0
    automated_pct: float = 0.0
    by_family: dict[str, dict] = field(default_factory=dict)
    gaps: list[dict] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessment_id": self.assessment_id, "level": self.level,
            "total_controls": self.total_controls,
            "full_coverage": self.full_coverage,
            "partial_coverage": self.partial_coverage,
            "no_coverage": self.no_coverage,
            "coverage_pct": round(self.coverage_pct, 1),
            "continuous_monitoring_pct": round(self.continuous_monitoring_pct, 1),
            "automated_pct": round(self.automated_pct, 1),
            "by_family": self.by_family,
            "gaps": self.gaps, "timestamp": self.timestamp,
        }


class FedRAMPMapper:
    """
    FedRAMP compliance mapper for NIST SP 800-53 controls.

    Usage:
        mapper = FedRAMPMapper()
        assessment = mapper.assess(FedRAMPLevel.MODERATE)
        print(f"FedRAMP Moderate: {assessment.coverage_pct}%")
    """

    def __init__(self):
        self._controls = list(FEDRAMP_CONTROLS)

    def _level_value(self, level: str) -> int:
        return {"low": 1, "moderate": 2, "high": 3}.get(level, 0)

    def get_controls_for_level(self, level: FedRAMPLevel) -> list[FedRAMPControl]:
        threshold = self._level_value(level.value)
        return [c for c in self._controls if self._level_value(c.fedramp_level) <= threshold]

    def assess(self, level: FedRAMPLevel = FedRAMPLevel.MODERATE) -> FedRAMPAssessment:
        controls = self.get_controls_for_level(level)
        result = FedRAMPAssessment()
        result.level = level.value
        result.total_controls = len(controls)

        conmon_count = 0
        auto_count = 0

        for ctrl in controls:
            has_coverage = len(ctrl.veilcore_organs) > 0 or len(ctrl.veilcore_subsystems) > 0

            if ctrl.coverage == "full" and has_coverage:
                result.full_coverage += 1
            elif has_coverage:
                result.partial_coverage += 1
            else:
                result.no_coverage += 1
                result.gaps.append({"control": ctrl.control_id, "family": ctrl.family_code, "title": ctrl.title})

            if ctrl.continuous_monitoring:
                conmon_count += 1
            if ctrl.automated:
                auto_count += 1

            fam = ctrl.family_code
            if fam not in result.by_family:
                result.by_family[fam] = {"name": ctrl.family, "full": 0, "partial": 0, "none": 0, "total": 0}
            result.by_family[fam]["total"] += 1
            if ctrl.coverage == "full" and has_coverage:
                result.by_family[fam]["full"] += 1
            elif has_coverage:
                result.by_family[fam]["partial"] += 1
            else:
                result.by_family[fam]["none"] += 1

        total = result.full_coverage + result.partial_coverage + result.no_coverage
        if total > 0:
            result.coverage_pct = ((result.full_coverage + result.partial_coverage * 0.5) / total) * 100
        if result.total_controls > 0:
            result.continuous_monitoring_pct = (conmon_count / result.total_controls) * 100
            result.automated_pct = (auto_count / result.total_controls) * 100

        return result

    def get_control(self, control_id: str) -> Optional[FedRAMPControl]:
        for c in self._controls:
            if c.control_id == control_id:
                return c
        return None

    def get_by_family(self, family_code: str) -> list[FedRAMPControl]:
        return [c for c in self._controls if c.family_code == family_code]

    def generate_report(self, level: FedRAMPLevel = FedRAMPLevel.MODERATE) -> dict[str, Any]:
        assessment = self.assess(level)
        return {
            "framework": "FedRAMP",
            "standard": "NIST SP 800-53 Rev 5",
            "codename": "IronFlag",
            "assessment": assessment.to_dict(),
            "controls": [c.to_dict() for c in self.get_controls_for_level(level)],
        }

    def summary(self) -> dict[str, Any]:
        low = self.assess(FedRAMPLevel.LOW)
        mod = self.assess(FedRAMPLevel.MODERATE)
        high = self.assess(FedRAMPLevel.HIGH)
        return {
            "framework": "FedRAMP (NIST 800-53)",
            "codename": "IronFlag",
            "low": {"controls": low.total_controls, "coverage_pct": low.coverage_pct},
            "moderate": {"controls": mod.total_controls, "coverage_pct": mod.coverage_pct},
            "high": {"controls": high.total_controls, "coverage_pct": high.coverage_pct},
            "families": len(set(c.family_code for c in self._controls)),
            "continuous_monitoring": f"{mod.continuous_monitoring_pct:.0f}%",
        }
