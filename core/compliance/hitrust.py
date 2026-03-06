"""VeilCore HITRUST CSF Mapper — TrustForge"""
from __future__ import annotations
import json, logging, time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
logger = logging.getLogger("veilcore.compliance.hitrust")

@dataclass
class HITRUSTControl:
    control_id: str; domain: str; domain_id: str; title: str; description: str
    implementation_level: int = 1
    veilcore_organs: list[str] = field(default_factory=list)
    veilcore_subsystems: list[str] = field(default_factory=list)
    coverage: str = "full"
    evidence_sources: list[str] = field(default_factory=list)
    automated: bool = True
    def to_dict(self):
        return {"control_id":self.control_id,"domain":self.domain,"domain_id":self.domain_id,"title":self.title,"description":self.description,"implementation_level":self.implementation_level,"veilcore_organs":self.veilcore_organs,"veilcore_subsystems":self.veilcore_subsystems,"coverage":self.coverage,"evidence_sources":self.evidence_sources,"automated":self.automated}

HITRUST_CONTROLS = [
    HITRUSTControl("01.a","Information Protection Program","01","Security Management Program","Establish information security management program",veilcore_organs=["cortex","compliance_engine","risk_analyzer"],veilcore_subsystems=["mesh"],evidence_sources=["compliance_engine.reports"]),
    HITRUSTControl("01.b","Information Protection Program","01","Risk Management Program","Implement comprehensive risk management",veilcore_organs=["risk_analyzer","vulnerability_scanner","threat_intel"],veilcore_subsystems=["ml","pentest"],evidence_sources=["risk_analyzer.assessments"]),
    HITRUSTControl("02.a","Endpoint Protection","02","Endpoint Security Controls","Implement endpoint detection and response",veilcore_organs=["host_sensor","malware_detector","process_monitor"],evidence_sources=["host_sensor.logs"]),
    HITRUSTControl("02.b","Endpoint Protection","02","Anti-Malware Protection","Deploy anti-malware solutions",veilcore_organs=["malware_detector","ransomware_shield","file_monitor"],evidence_sources=["malware_detector.signatures"]),
    HITRUSTControl("02.c","Endpoint Protection","02","Medical Device Security","Secure IoMT devices",veilcore_organs=["iomt_protector","host_sensor","network_monitor"],veilcore_subsystems=["wireless"],evidence_sources=["iomt_protector.inventory"]),
    HITRUSTControl("03.a","Portable Media Security","03","Media Protection","Control removable media",veilcore_organs=["dlp_engine","encryptor","file_monitor"],evidence_sources=["dlp_engine.scans"]),
    HITRUSTControl("04.a","Mobile Device Security","04","Mobile Device Management","Manage mobile devices",veilcore_organs=["session_monitor","mfa","zero_trust_engine"],veilcore_subsystems=["mobile"],evidence_sources=["session_monitor.sessions"]),
    HITRUSTControl("05.a","Wireless Security","05","Wireless Network Protection","Secure wireless networks",veilcore_organs=["network_monitor","firewall"],veilcore_subsystems=["wireless"],evidence_sources=["wireless.scan_results"]),
    HITRUSTControl("05.b","Wireless Security","05","Wireless Authentication","Enforce wireless auth",veilcore_organs=["guardian","mfa","rbac"],veilcore_subsystems=["wireless"],evidence_sources=["guardian.auth_logs"]),
    HITRUSTControl("06.a","Configuration Management","06","Configuration Standards","Enforce secure baselines",veilcore_organs=["config_auditor","baseline_monitor","integrity_checker"],evidence_sources=["config_auditor.diffs"]),
    HITRUSTControl("06.b","Configuration Management","06","Patch Management","Timely patching",veilcore_organs=["patcher","patch_manager","vulnerability_scanner"],veilcore_subsystems=["pentest"],evidence_sources=["patch_manager.status"]),
    HITRUSTControl("07.a","Vulnerability Management","07","Vulnerability Scanning","Regular vulnerability assessments",veilcore_organs=["scanner","vulnerability_scanner","port_scanner"],veilcore_subsystems=["pentest"],evidence_sources=["scanner.results"]),
    HITRUSTControl("08.a","Network Protection","08","Network Segmentation","Isolate critical systems",veilcore_organs=["firewall","micro_segmentation","traffic_shaper"],evidence_sources=["firewall.rules"]),
    HITRUSTControl("08.b","Network Protection","08","Intrusion Detection","Deploy IDS/IPS",veilcore_organs=["ids_ips","network_monitor","sentinel"],veilcore_subsystems=["ml"],evidence_sources=["ids_ips.alerts"]),
    HITRUSTControl("08.c","Network Protection","08","Network Monitoring","Continuous traffic monitoring",veilcore_organs=["network_monitor","bandwidth_monitor","dns_filter"],veilcore_subsystems=["mesh"],evidence_sources=["network_monitor.flows"]),
    HITRUSTControl("09.a","Transmission Protection","09","Encryption in Transit","Encrypt data in transit",veilcore_organs=["encryption_enforcer","ssl_inspector","vpn_manager","certificate_authority"],evidence_sources=["encryption_enforcer.audits"]),
    HITRUSTControl("09.b","Transmission Protection","09","Clinical Data Transmission","Secure HL7/FHIR/DICOM",veilcore_organs=["hl7_filter","fhir_gateway","dicom_shield"],evidence_sources=["hl7_filter.scans"]),
    HITRUSTControl("10.a","Access Control","10","Identity and Access Management","Implement IAM",veilcore_organs=["guardian","rbac","mfa","zero_trust_engine"],evidence_sources=["guardian.auth_logs"]),
    HITRUSTControl("10.b","Access Control","10","Privileged Access Management","Control privileged access",veilcore_organs=["vault","insider_threat","session_monitor"],evidence_sources=["vault.access_logs"]),
    HITRUSTControl("10.c","Access Control","10","Physical Access Controls","Physical access control",veilcore_subsystems=["physical"],evidence_sources=["physical.sensor_alerts"]),
    HITRUSTControl("11.a","Audit Logging","11","Audit Trail","Comprehensive audit trails",veilcore_organs=["audit","chronicle","log_aggregator"],evidence_sources=["chronicle.timeline"]),
    HITRUSTControl("11.b","Audit Logging","11","Security Monitoring","Continuous monitoring",veilcore_organs=["sentinel","siem_connector","metrics_collector","alert_manager"],veilcore_subsystems=["mesh","ml"],evidence_sources=["sentinel.anomalies"]),
    HITRUSTControl("12.a","Education and Awareness","12","Security Awareness","Security training",coverage="partial",veilcore_organs=["notification_engine"],evidence_sources=["notification_engine.alerts"]),
    HITRUSTControl("13.a","Third Party Assurance","13","Third Party Risk","Assess third-party security",veilcore_organs=["threat_intel","api_gateway"],veilcore_subsystems=["federation"],evidence_sources=["threat_intel.feeds"]),
    HITRUSTControl("14.a","Business Continuity","14","Disaster Recovery","Maintain DR capabilities",veilcore_organs=["disaster_recovery","backup","backup_validator","failover_controller","snapshot_manager","replication_engine"],evidence_sources=["backup_validator.tests"]),
    HITRUSTControl("15.a","Risk Management","15","Risk Assessment","Regular risk assessments",veilcore_organs=["risk_analyzer","compliance_engine"],veilcore_subsystems=["pentest","ml"],evidence_sources=["risk_analyzer.assessments"]),
    HITRUSTControl("16.a","Incident Management","16","Incident Response","Incident response capabilities",veilcore_organs=["incident_responder","forensic_collector","quarantine","alert_manager"],veilcore_subsystems=["mobile"],evidence_sources=["incident_responder.playbooks"]),
    HITRUSTControl("16.b","Incident Management","16","Breach Notification","Breach notification procedures",veilcore_organs=["notification_engine","sms_notifier","email_gateway","compliance_tracker"],veilcore_subsystems=["mobile","federation"],evidence_sources=["notification_engine.logs"]),
    HITRUSTControl("17.a","Data Protection","17","PHI Protection","Protect PHI",veilcore_organs=["phi_classifier","phi_guard","dlp_engine","encryption_enforcer"],evidence_sources=["phi_classifier.tags"]),
    HITRUSTControl("17.b","Data Protection","17","Data Loss Prevention","Prevent data exfiltration",veilcore_organs=["dlp_engine","content_filter","web_proxy","email_gateway"],evidence_sources=["dlp_engine.incidents"]),
    HITRUSTControl("18.a","Password Management","18","Authentication Mechanisms","Enforce strong auth",veilcore_organs=["guardian","mfa","imprivata_bridge","key_manager"],evidence_sources=["guardian.auth_logs"]),
    HITRUSTControl("19.a","Physical Security","19","Physical Security Controls","Protect physical infrastructure",veilcore_subsystems=["physical","wireless"],evidence_sources=["physical.sensor_alerts"]),
]

@dataclass
class HITRUSTAssessment:
    assessment_id: str = field(default_factory=lambda: f"HITRUST-{int(time.time())}")
    total_controls: int = 0; full_coverage: int = 0; partial_coverage: int = 0; no_coverage: int = 0
    coverage_pct: float = 0.0; domains_covered: int = 0; total_domains: int = 19
    by_domain: dict[str, dict] = field(default_factory=dict)
    gaps: list[dict] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    def to_dict(self):
        return {"assessment_id":self.assessment_id,"total_controls":self.total_controls,"full_coverage":self.full_coverage,"partial_coverage":self.partial_coverage,"no_coverage":self.no_coverage,"coverage_pct":round(self.coverage_pct,1),"domains_covered":self.domains_covered,"total_domains":self.total_domains,"by_domain":self.by_domain,"gaps":self.gaps,"timestamp":self.timestamp}

class HITRUSTMapper:
    def __init__(self): self._controls = list(HITRUST_CONTROLS)
    def assess(self):
        r = HITRUSTAssessment(); r.total_controls = len(self._controls); doms = set()
        for c in self._controls:
            doms.add(c.domain_id); has = len(c.veilcore_organs) > 0 or len(c.veilcore_subsystems) > 0
            dk = f"{c.domain_id} - {c.domain}"
            if dk not in r.by_domain: r.by_domain[dk] = {"full":0,"partial":0,"none":0,"total":0}
            r.by_domain[dk]["total"] += 1
            if c.coverage == "full" and has: r.full_coverage += 1; r.by_domain[dk]["full"] += 1
            elif has: r.partial_coverage += 1; r.by_domain[dk]["partial"] += 1
            else: r.no_coverage += 1; r.by_domain[dk]["none"] += 1; r.gaps.append({"control_id":c.control_id,"domain":c.domain,"title":c.title})
        r.domains_covered = len(doms)
        tot = r.full_coverage + r.partial_coverage + r.no_coverage
        if tot > 0: r.coverage_pct = ((r.full_coverage + r.partial_coverage * 0.5) / tot) * 100
        return r
    def get_control(self, cid):
        for c in self._controls:
            if c.control_id == cid: return c
        return None
    def get_gaps(self): return [c for c in self._controls if not c.veilcore_organs and not c.veilcore_subsystems]
    def get_by_domain(self, did): return [c for c in self._controls if c.domain_id == did]
    def get_organ_controls(self, organ): return [c for c in self._controls if organ in c.veilcore_organs]
    def get_subsystem_controls(self, sub): return [c for c in self._controls if sub in c.veilcore_subsystems]
    def generate_report(self):
        a = self.assess(); return {"framework":"HITRUST CSF v11","codename":"TrustForge","assessment":a.to_dict(),"controls":[c.to_dict() for c in self._controls]}
    def summary(self):
        a = self.assess(); return {"framework":"HITRUST CSF v11","codename":"TrustForge","total_controls":a.total_controls,"coverage_pct":a.coverage_pct,"domains_covered":f"{a.domains_covered}/{a.total_domains}","gaps":len(a.gaps)}
