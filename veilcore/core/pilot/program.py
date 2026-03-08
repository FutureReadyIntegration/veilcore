"""
VeilCore Pilot Program — Hospital Onboarding Toolkit
======================================================
Everything needed to take a hospital from "interested"
to "fully protected" in a structured, repeatable process.

Phases:
    1. Assessment — evaluate current security posture
    2. Planning — deployment plan, timeline, resource allocation
    3. Deployment — staged rollout with validation gates
    4. Training — staff training program with role-based tracks
    5. Validation — full system verification and compliance check
    6. Handoff — operational handoff with documentation
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class PilotPhase(Enum):
    ASSESSMENT = "assessment"
    PLANNING = "planning"
    DEPLOYMENT = "deployment"
    TRAINING = "training"
    VALIDATION = "validation"
    HANDOFF = "handoff"


class HospitalSize(Enum):
    COMMUNITY = "community"       # <100 beds
    REGIONAL = "regional"         # 100-500 beds
    ACADEMIC = "academic"         # 500+ beds
    CRITICAL_ACCESS = "critical_access"  # Rural <25 beds


class RiskLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


@dataclass
class SecurityAssessment:
    """Current security posture assessment."""
    hospital_name: str = ""
    hospital_size: str = "community"
    total_beds: int = 0
    total_endpoints: int = 0
    ehr_system: str = "epic"
    sso_system: str = "imprivata"
    existing_security_tools: list[str] = field(default_factory=list)
    annual_security_budget: float = 0.0
    it_staff_count: int = 0
    security_staff_count: int = 0
    has_ciso: bool = False
    previous_incidents: int = 0
    last_pentest_date: Optional[str] = None
    hipaa_audit_findings: int = 0
    network_segments: int = 1
    iot_devices: int = 0
    remote_sites: int = 0

    # Risk scoring
    risk_factors: list[dict] = field(default_factory=list)
    overall_risk: str = "moderate"
    risk_score: float = 0.0

    def evaluate_risk(self):
        score = 0.0
        self.risk_factors = []

        if self.previous_incidents > 0:
            score += 25.0
            self.risk_factors.append({"factor": "Previous incidents", "impact": "high", "detail": f"{self.previous_incidents} incidents"})

        if self.security_staff_count == 0:
            score += 20.0
            self.risk_factors.append({"factor": "No dedicated security staff", "impact": "high"})

        if not self.has_ciso:
            score += 10.0
            self.risk_factors.append({"factor": "No CISO", "impact": "moderate"})

        if self.network_segments <= 1:
            score += 15.0
            self.risk_factors.append({"factor": "Flat network (no segmentation)", "impact": "high"})

        if self.iot_devices > 100:
            score += 15.0
            self.risk_factors.append({"factor": f"High IoMT count ({self.iot_devices})", "impact": "moderate"})

        if self.last_pentest_date is None:
            score += 10.0
            self.risk_factors.append({"factor": "No penetration testing history", "impact": "moderate"})

        if self.hipaa_audit_findings > 3:
            score += 15.0
            self.risk_factors.append({"factor": f"HIPAA findings ({self.hipaa_audit_findings})", "impact": "high"})

        if len(self.existing_security_tools) < 3:
            score += 10.0
            self.risk_factors.append({"factor": "Minimal existing security tools", "impact": "moderate"})

        self.risk_score = min(score, 100.0)
        if score >= 60:
            self.overall_risk = "critical"
        elif score >= 40:
            self.overall_risk = "high"
        elif score >= 20:
            self.overall_risk = "moderate"
        else:
            self.overall_risk = "low"

    def to_dict(self) -> dict[str, Any]:
        return {
            "hospital": self.hospital_name, "size": self.hospital_size,
            "beds": self.total_beds, "endpoints": self.total_endpoints,
            "ehr": self.ehr_system, "sso": self.sso_system,
            "existing_tools": self.existing_security_tools,
            "staff": {"it": self.it_staff_count, "security": self.security_staff_count, "ciso": self.has_ciso},
            "risk": {"score": self.risk_score, "level": self.overall_risk, "factors": self.risk_factors},
        }


@dataclass
class DeploymentPlan:
    """Staged deployment plan."""
    hospital_name: str = ""
    total_weeks: int = 4
    phases: list[dict] = field(default_factory=list)
    resource_requirements: dict = field(default_factory=dict)
    rollback_plan: str = ""
    success_criteria: list[str] = field(default_factory=list)

    def generate(self, assessment: SecurityAssessment):
        self.hospital_name = assessment.hospital_name

        # Scale timeline to hospital size
        if assessment.hospital_size == "academic":
            self.total_weeks = 8
        elif assessment.hospital_size == "regional":
            self.total_weeks = 6
        elif assessment.hospital_size == "critical_access":
            self.total_weeks = 3
        else:
            self.total_weeks = 4

        self.phases = [
            {"week": 1, "phase": "P0 Critical Organs",
             "tasks": ["Deploy Guardian, Sentinel, Cortex, Audit", "Configure Epic/Imprivata integration",
                       "Establish baseline behavioral profiles", "Verify dashboard access"],
             "gate": "14/14 P0 organs online, dashboard accessible"},
            {"week": 2, "phase": "P1 Important Organs + NerveBridge",
             "tasks": ["Deploy clinical connectors (Epic, HL7, FHIR, DICOM)", "Enable mesh communication",
                       "Activate network monitoring", "Deploy honeypots"],
             "gate": "28/28 P0+P1 organs online, mesh active"},
            {"week": 3, "phase": "P2 Standard Organs + Subsystems",
             "tasks": ["Deploy all P2 organs", "Enable DeepSentinel ML", "Configure AllianceNet federation",
                       "Activate AirShield wireless monitoring", "Deploy IronWatch sensors"],
             "gate": "82/82 organs online, all subsystems operational"},
            {"week": 4, "phase": "Validation + Hardening",
             "tasks": ["Run RedVeil penetration test", "HIPAA compliance validation",
                       "Staff training completion", "Incident response drill",
                       "Performance optimization"],
             "gate": "100% HIPAA, pentest passed, staff certified"},
        ]

        self.resource_requirements = {
            "server": {"min_cores": 4, "min_ram_gb": 8, "min_disk_gb": 100,
                       "recommended_cores": 8, "recommended_ram_gb": 32},
            "network": {"dedicated_management_port": True, "span_port_for_monitoring": True,
                        "vlans_recommended": True},
            "staff_time": {"it_admin_hours": self.total_weeks * 10,
                           "security_staff_hours": self.total_weeks * 5,
                           "training_hours_per_person": 4},
        }

        self.rollback_plan = (
            "Each phase has an independent rollback. Organs can be disabled individually "
            "via systemctl. Full rollback removes all VeilCore services and restores original "
            "firewall rules. Patient care systems are never modified — VeilCore monitors "
            "and protects without altering clinical workflows."
        )

        self.success_criteria = [
            "82/82 organs operational and reporting healthy",
            "HIPAA Security Rule: 100% coverage validated",
            "Zero patient care system disruptions during deployment",
            "All critical staff complete security awareness training",
            "RedVeil pentest: all critical findings remediated",
            "Incident response drill completed successfully",
            f"Full deployment within {self.total_weeks} weeks",
        ]


@dataclass
class TrainingTrack:
    """Role-based training track."""
    role: str
    title: str
    duration_hours: float
    modules: list[dict]
    certification_required: bool = False


TRAINING_TRACKS = [
    TrainingTrack("security_admin", "VeilCore Security Administrator", 8.0, [
        {"module": "VeilCore Architecture", "duration": 1.0, "topics": ["82 organs overview", "priority tiers", "subsystem functions"]},
        {"module": "Dashboard Operations", "duration": 1.5, "topics": ["real-time monitoring", "threat visualization", "alert management"]},
        {"module": "Incident Response", "duration": 2.0, "topics": ["quarantine procedures", "forensic collection", "escalation paths"]},
        {"module": "Compliance Management", "duration": 1.5, "topics": ["HIPAA dashboard", "HITRUST mapping", "audit evidence"]},
        {"module": "Advanced Operations", "duration": 2.0, "topics": ["RedVeil pentest", "ML tuning", "federation management"]},
    ], certification_required=True),

    TrainingTrack("it_admin", "VeilCore IT Administration", 4.0, [
        {"module": "System Overview", "duration": 0.5, "topics": ["architecture", "organ roles", "service management"]},
        {"module": "Service Management", "duration": 1.0, "topics": ["systemctl operations", "log review", "health monitoring"]},
        {"module": "Troubleshooting", "duration": 1.5, "topics": ["organ restart", "mesh diagnostics", "backup verification"]},
        {"module": "Updates & Maintenance", "duration": 1.0, "topics": ["patching", "upgrades", "backup procedures"]},
    ]),

    TrainingTrack("clinical_staff", "VeilCore Security Awareness", 1.0, [
        {"module": "Why VeilCore Matters", "duration": 0.25, "topics": ["ransomware impact on care", "real-world examples"]},
        {"module": "What You'll Notice", "duration": 0.25, "topics": ["login changes", "session timeouts", "alert notifications"]},
        {"module": "Reporting Suspicious Activity", "duration": 0.25, "topics": ["who to call", "what to report", "phishing recognition"]},
        {"module": "Emergency Procedures", "duration": 0.25, "topics": ["system down procedures", "communication protocols"]},
    ]),

    TrainingTrack("executive", "VeilCore Executive Briefing", 0.5, [
        {"module": "Business Case", "duration": 0.15, "topics": ["cost comparison", "risk reduction", "compliance posture"]},
        {"module": "Dashboard Overview", "duration": 0.2, "topics": ["executive dashboard", "compliance metrics", "threat trends"]},
        {"module": "Incident Communication", "duration": 0.15, "topics": ["breach notification", "PR coordination", "regulatory reporting"]},
    ]),

    TrainingTrack("accessibility_operator", "VeilCore Accessibility Operations", 2.0, [
        {"module": "EqualShield Overview", "duration": 0.5, "topics": ["Braille output", "screen reader integration", "audio alerts"]},
        {"module": "Accessible Monitoring", "duration": 0.75, "topics": ["keyboard navigation", "severity audio mapping", "SSML alerts"]},
        {"module": "Incident Response (Accessible)", "duration": 0.75, "topics": ["accessible escalation", "Braille incident reports"]},
    ]),
]


@dataclass
class PilotResult:
    """Pilot program tracking."""
    pilot_id: str = field(default_factory=lambda: f"pilot-{int(time.time())}")
    hospital_name: str = ""
    start_date: str = ""
    current_phase: str = "assessment"
    phases_completed: list[str] = field(default_factory=list)
    assessment: Optional[SecurityAssessment] = None
    plan: Optional[DeploymentPlan] = None
    organs_online: int = 0
    staff_trained: int = 0
    compliance_score: float = 0.0
    incidents_during_pilot: int = 0
    success: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "pilot_id": self.pilot_id, "hospital": self.hospital_name,
            "start_date": self.start_date, "current_phase": self.current_phase,
            "phases_completed": self.phases_completed,
            "organs_online": self.organs_online, "staff_trained": self.staff_trained,
            "compliance_score": self.compliance_score,
            "incidents_during_pilot": self.incidents_during_pilot,
            "success": self.success,
        }


class PilotProgram:
    """
    Hospital onboarding toolkit.

    Usage:
        pilot = PilotProgram()

        # Assess
        assessment = pilot.assess("Memorial General", beds=150, ehr="epic")

        # Plan
        plan = pilot.create_plan(assessment)

        # Get training tracks
        tracks = pilot.get_training_tracks()
    """

    def __init__(self):
        self._training_tracks = list(TRAINING_TRACKS)

    def assess(self, hospital_name: str, beds: int = 100, ehr: str = "epic",
               sso: str = "imprivata", existing_tools: Optional[list[str]] = None,
               security_staff: int = 0, has_ciso: bool = False,
               previous_incidents: int = 0, iot_devices: int = 50,
               network_segments: int = 1, hipaa_findings: int = 0) -> SecurityAssessment:

        size = "critical_access" if beds < 25 else "community" if beds < 100 else "regional" if beds < 500 else "academic"

        assessment = SecurityAssessment(
            hospital_name=hospital_name, hospital_size=size,
            total_beds=beds, total_endpoints=beds * 3,
            ehr_system=ehr, sso_system=sso,
            existing_security_tools=existing_tools or [],
            security_staff_count=security_staff, has_ciso=has_ciso,
            previous_incidents=previous_incidents, iot_devices=iot_devices,
            network_segments=network_segments, hipaa_audit_findings=hipaa_findings,
        )
        assessment.evaluate_risk()
        return assessment

    def create_plan(self, assessment: SecurityAssessment) -> DeploymentPlan:
        plan = DeploymentPlan()
        plan.generate(assessment)
        return plan

    def get_training_tracks(self) -> list[dict]:
        return [
            {"role": t.role, "title": t.title, "duration_hours": t.duration_hours,
             "modules": len(t.modules), "certification": t.certification_required}
            for t in self._training_tracks
        ]

    def get_training_detail(self, role: str) -> Optional[dict]:
        for t in self._training_tracks:
            if t.role == role:
                return {
                    "role": t.role, "title": t.title,
                    "duration_hours": t.duration_hours,
                    "modules": t.modules,
                    "certification_required": t.certification_required,
                }
        return None

    def start_pilot(self, assessment: SecurityAssessment) -> PilotResult:
        plan = self.create_plan(assessment)
        return PilotResult(
            hospital_name=assessment.hospital_name,
            start_date=datetime.now(timezone.utc).isoformat(),
            current_phase="assessment",
            phases_completed=["assessment"],
            assessment=assessment, plan=plan,
        )

    def generate_onboarding_checklist(self, assessment: SecurityAssessment) -> list[dict]:
        return [
            {"category": "Pre-Deployment", "items": [
                {"task": "Server hardware provisioned and racked", "required": True},
                {"task": "Ubuntu 24.04 LTS installed", "required": True},
                {"task": "Network ports allocated (8443, 8444, 9000-9100)", "required": True},
                {"task": "SPAN/mirror port configured for monitoring", "required": True},
                {"task": f"{assessment.ehr_system.title()} API credentials obtained", "required": True},
                {"task": f"{assessment.sso_system.title()} integration endpoint documented", "required": True},
                {"task": "VeilCore service account created in AD/LDAP", "required": True},
                {"task": "Backup storage location provisioned", "required": True},
            ]},
            {"category": "Deployment", "items": [
                {"task": "VeilCore Unleashed installer executed", "required": True},
                {"task": "P0 organs verified online", "required": True},
                {"task": "P1 organs verified online", "required": True},
                {"task": "P2 organs verified online", "required": True},
                {"task": "Dashboard accessible via HTTPS", "required": True},
                {"task": "EHR connector verified", "required": True},
                {"task": "SSO bridge verified", "required": True},
            ]},
            {"category": "Validation", "items": [
                {"task": "HIPAA compliance check: 100%", "required": True},
                {"task": "RedVeil penetration test executed", "required": True},
                {"task": "Incident response drill completed", "required": True},
                {"task": "Backup and restore test passed", "required": True},
                {"task": "Staff training completed", "required": True},
            ]},
            {"category": "Handoff", "items": [
                {"task": "Operations manual delivered", "required": True},
                {"task": "Emergency contact list documented", "required": True},
                {"task": "Escalation procedures signed off", "required": True},
                {"task": "30-day post-deployment review scheduled", "required": True},
            ]},
        ]

    def summary(self) -> dict[str, Any]:
        return {
            "program": "VeilCore Pilot Program",
            "codename": "Pilot",
            "phases": [p.value for p in PilotPhase],
            "training_tracks": len(self._training_tracks),
            "total_training_hours": sum(t.duration_hours for t in self._training_tracks),
            "roles_covered": [t.role for t in self._training_tracks],
            "hospital_sizes_supported": [s.value for s in HospitalSize],
        }
