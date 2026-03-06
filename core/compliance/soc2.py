"""VeilCore SOC 2 Type II Mapper — AuditIron"""
from __future__ import annotations
import json, logging, time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
logger = logging.getLogger("veilcore.compliance.soc2")

@dataclass
class SOC2Criterion:
    criterion_id: str; category: str; title: str; description: str
    veilcore_organs: list[str] = field(default_factory=list)
    veilcore_subsystems: list[str] = field(default_factory=list)
    coverage: str = "full"
    evidence_type: str = "automated"
    evidence_sources: list[str] = field(default_factory=list)
    continuous_monitoring: bool = True
    def to_dict(self):
        return {"criterion_id":self.criterion_id,"category":self.category,"title":self.title,"description":self.description,"veilcore_organs":self.veilcore_organs,"veilcore_subsystems":self.veilcore_subsystems,"coverage":self.coverage,"evidence_type":self.evidence_type,"evidence_sources":self.evidence_sources,"continuous_monitoring":self.continuous_monitoring}

SOC2_CRITERIA = [
    SOC2Criterion("CC1.1","Security","Integrity and Ethics","Demonstrates commitment to integrity",veilcore_organs=["audit","chronicle","compliance_engine"],evidence_sources=["chronicle.timeline"]),
    SOC2Criterion("CC1.2","Security","Board Oversight","Board exercises oversight",veilcore_organs=["compliance_tracker","risk_analyzer"],veilcore_subsystems=["mobile"],evidence_sources=["compliance_tracker.dashboards"]),
    SOC2Criterion("CC1.3","Security","Management Structure","Management establishes structures",veilcore_organs=["cortex","alert_manager","notification_engine"],evidence_sources=["cortex.organ_hierarchy"]),
    SOC2Criterion("CC2.1","Security","Internal Communication","Generates relevant security info",veilcore_organs=["sentinel","cortex","siem_connector","metrics_collector"],veilcore_subsystems=["mesh","ml"],evidence_sources=["mesh.message_logs"]),
    SOC2Criterion("CC2.2","Security","External Communication","Communicates to external parties",veilcore_organs=["notification_engine","email_gateway","sms_notifier","webhook_handler"],veilcore_subsystems=["federation","mobile"],evidence_sources=["notification_engine.external_alerts"]),
    SOC2Criterion("CC3.1","Security","Risk Identification","Identifies and assesses risks",veilcore_organs=["risk_analyzer","threat_intel","vulnerability_scanner"],veilcore_subsystems=["pentest","ml"],evidence_sources=["risk_analyzer.assessments"]),
    SOC2Criterion("CC3.2","Security","Fraud Risk","Assesses fraud and insider threats",veilcore_organs=["insider_threat","behavioral_analysis","anomaly_detector"],evidence_sources=["insider_threat.detections"]),
    SOC2Criterion("CC3.3","Security","Change Impact Analysis","Assesses changes impacting controls",veilcore_organs=["config_auditor","baseline_monitor","file_monitor"],evidence_sources=["config_auditor.change_logs"]),
    SOC2Criterion("CC4.1","Security","Ongoing Monitoring","Performs ongoing evaluations",veilcore_organs=["sentinel","watchdog","health_checker","uptime_tracker"],veilcore_subsystems=["mesh","ml"],evidence_sources=["watchdog.heartbeats"]),
    SOC2Criterion("CC4.2","Security","Deficiency Communication","Communicates control deficiencies",veilcore_organs=["alert_manager","compliance_engine","notification_engine"],veilcore_subsystems=["mobile"],evidence_sources=["alert_manager.escalations"]),
    SOC2Criterion("CC5.1","Security","Control Selection","Selects control activities",veilcore_organs=["cortex","compliance_engine","risk_analyzer"],veilcore_subsystems=["pentest"],evidence_sources=["compliance_engine.control_matrix"]),
    SOC2Criterion("CC5.2","Security","Technology Controls","Technology-based controls",veilcore_organs=["firewall","ids_ips","waf","dns_filter","ssl_inspector"],evidence_sources=["firewall.rule_sets"]),
    SOC2Criterion("CC5.3","Security","Policy Controls","Deploys policy-based controls",veilcore_organs=["rbac","zero_trust_engine","session_monitor"],evidence_sources=["rbac.policies"]),
    SOC2Criterion("CC6.1","Security","Logical Access","Logical access security",veilcore_organs=["guardian","rbac","mfa","vault"],evidence_sources=["guardian.access_logs"]),
    SOC2Criterion("CC6.2","Security","Access Registration","Registers new users",veilcore_organs=["guardian","rbac","imprivata_bridge"],evidence_sources=["guardian.registrations"]),
    SOC2Criterion("CC6.3","Security","Access Modification","Manages access changes",veilcore_organs=["rbac","session_monitor","audit"],evidence_sources=["rbac.permission_changes"]),
    SOC2Criterion("CC6.4","Security","Physical Access","Restricts physical access",veilcore_subsystems=["physical"],evidence_sources=["physical.sensor_events"]),
    SOC2Criterion("CC6.5","Security","Access Deprovisioning","Removes access when unneeded",veilcore_organs=["rbac","guardian","session_monitor"],evidence_sources=["rbac.deprovisioning_logs"]),
    SOC2Criterion("CC6.6","Security","Boundary Protection","Prevents unauthorized boundary access",veilcore_organs=["firewall","micro_segmentation","api_gateway","web_proxy"],veilcore_subsystems=["wireless"],evidence_sources=["firewall.boundary_rules"]),
    SOC2Criterion("CC6.7","Security","Data Transmission","Restricts data transmission",veilcore_organs=["dlp_engine","encryption_enforcer","content_filter","email_gateway"],evidence_sources=["dlp_engine.incidents"]),
    SOC2Criterion("CC6.8","Security","Malware Prevention","Prevents malicious software",veilcore_organs=["malware_detector","ransomware_shield","canary"],veilcore_subsystems=["ml"],evidence_sources=["malware_detector.scan_results"]),
    SOC2Criterion("CC7.1","Security","Anomaly Detection","Detects threat anomalies",veilcore_organs=["sentinel","anomaly_detector","behavioral_analysis"],veilcore_subsystems=["ml","mesh"],evidence_sources=["sentinel.anomaly_feed"]),
    SOC2Criterion("CC7.2","Security","Event Evaluation","Evaluates security events",veilcore_organs=["cortex","alert_manager","siem_connector"],veilcore_subsystems=["mesh"],evidence_sources=["cortex.correlations"]),
    SOC2Criterion("CC7.3","Security","Incident Response","Responds to incidents",veilcore_organs=["incident_responder","quarantine","forensic_collector"],veilcore_subsystems=["mobile","federation"],evidence_sources=["incident_responder.actions"]),
    SOC2Criterion("CC7.4","Security","Incident Recovery","Recovers from incidents",veilcore_organs=["disaster_recovery","backup","failover_controller","backup_validator"],evidence_sources=["disaster_recovery.restorations"]),
    SOC2Criterion("CC8.1","Security","Change Management","Manages infrastructure changes",veilcore_organs=["config_auditor","baseline_monitor","integrity_checker","patcher"],evidence_sources=["config_auditor.changes"]),
    SOC2Criterion("CC9.1","Security","Risk Mitigation","Mitigates business disruption",veilcore_organs=["risk_analyzer","disaster_recovery","failover_controller"],veilcore_subsystems=["pentest"],evidence_sources=["risk_analyzer.mitigation_plans"]),
    SOC2Criterion("A1.1","Availability","Capacity Planning","Maintains processing capacity",veilcore_organs=["performance_monitor","resource_limiter","load_balancer"],evidence_sources=["performance_monitor.capacity_reports"]),
    SOC2Criterion("A1.2","Availability","Recovery Infrastructure","Manages recovery infrastructure",veilcore_organs=["backup","disaster_recovery","replication_engine","snapshot_manager","failover_controller"],evidence_sources=["backup_validator.recovery_tests"]),
    SOC2Criterion("A1.3","Availability","Recovery Testing","Tests recovery procedures",veilcore_organs=["backup_validator","disaster_recovery"],veilcore_subsystems=["pentest"],evidence_sources=["backup_validator.test_results"]),
    SOC2Criterion("PI1.1","Processing Integrity","Data Quality","Uses relevant quality data",veilcore_organs=["hl7_filter","fhir_gateway","dicom_shield","phi_classifier"],evidence_sources=["hl7_filter.validation_logs"]),
    SOC2Criterion("C1.1","Confidentiality","Information Identification","Classifies confidential info",veilcore_organs=["phi_classifier","phi_guard","dlp_engine"],evidence_sources=["phi_classifier.classifications"]),
    SOC2Criterion("C1.2","Confidentiality","Information Disposal","Disposes confidential info",veilcore_organs=["encryptor","file_monitor"],evidence_sources=["encryptor.disposal_logs"]),
    SOC2Criterion("P1.1","Privacy","Privacy Notice","Provides privacy notices",veilcore_organs=["compliance_tracker"],coverage="partial",evidence_sources=["compliance_tracker.privacy_notices"]),
    SOC2Criterion("P1.2","Privacy","PHI Access and Consent","Manages PHI consent",veilcore_organs=["phi_guard","rbac","audit"],evidence_sources=["phi_guard.consent_logs"]),
]

@dataclass
class SOC2Assessment:
    assessment_id: str = field(default_factory=lambda: f"SOC2-{int(time.time())}")
    total_criteria: int = 0; full_coverage: int = 0; partial_coverage: int = 0; no_coverage: int = 0
    coverage_pct: float = 0.0; automated_pct: float = 0.0
    by_category: dict[str, dict] = field(default_factory=dict)
    gaps: list[dict] = field(default_factory=list)
    type2_ready: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    def to_dict(self):
        return {"assessment_id":self.assessment_id,"total_criteria":self.total_criteria,"full_coverage":self.full_coverage,"partial_coverage":self.partial_coverage,"no_coverage":self.no_coverage,"coverage_pct":round(self.coverage_pct,1),"automated_pct":round(self.automated_pct,1),"by_category":self.by_category,"gaps":self.gaps,"type2_ready":self.type2_ready,"timestamp":self.timestamp}

class SOC2Mapper:
    def __init__(self): self._criteria = list(SOC2_CRITERIA)
    def assess(self):
        r = SOC2Assessment(); r.total_criteria = len(self._criteria); auto = 0
        for c in self._criteria:
            has = len(c.veilcore_organs) > 0 or len(c.veilcore_subsystems) > 0
            cat = c.category
            if cat not in r.by_category: r.by_category[cat] = {"full":0,"partial":0,"none":0,"total":0}
            r.by_category[cat]["total"] += 1
            if c.coverage == "full" and has: r.full_coverage += 1; r.by_category[cat]["full"] += 1
            elif has: r.partial_coverage += 1; r.by_category[cat]["partial"] += 1
            else: r.no_coverage += 1; r.by_category[cat]["none"] += 1; r.gaps.append({"criterion_id":c.criterion_id,"category":c.category,"title":c.title})
            if c.evidence_type == "automated": auto += 1
        tot = r.full_coverage + r.partial_coverage + r.no_coverage
        if tot > 0: r.coverage_pct = ((r.full_coverage + r.partial_coverage * 0.5) / tot) * 100; r.automated_pct = (auto / tot) * 100
        r.type2_ready = r.coverage_pct >= 90 and r.automated_pct >= 80
        return r
    def get_criterion(self, cid):
        for c in self._criteria:
            if c.criterion_id == cid: return c
        return None
    def get_by_category(self, cat): return [c for c in self._criteria if c.category == cat]
    def get_evidence_map(self):
        return {c.criterion_id: c.evidence_sources for c in self._criteria}
    def generate_report(self):
        a = self.assess(); return {"framework":"SOC 2 Type II","codename":"AuditIron","assessment":a.to_dict(),"criteria":[c.to_dict() for c in self._criteria]}
    def summary(self):
        a = self.assess(); return {"framework":"SOC 2 Type II","codename":"AuditIron","total_criteria":a.total_criteria,"coverage_pct":a.coverage_pct,"automated_pct":a.automated_pct,"type2_ready":a.type2_ready,"by_category":{k:f"{v['full']}/{v['total']} full" for k,v in a.by_category.items()},"gaps":len(a.gaps)}
