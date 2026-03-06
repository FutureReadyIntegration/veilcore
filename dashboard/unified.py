"""VeilCore Unified Dashboard API — Prism"""
from __future__ import annotations
import json, logging, time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
logger = logging.getLogger("veilcore.dashboard.unified")

@dataclass
class SubsystemStatus:
    name: str; codename: str; status: str = "operational"; health_pct: float = 100.0
    last_update: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metrics: dict[str, Any] = field(default_factory=dict); alerts: int = 0
    def to_dict(self):
        return {"name":self.name,"codename":self.codename,"status":self.status,"health_pct":self.health_pct,"last_update":self.last_update,"metrics":self.metrics,"alerts":self.alerts}

SUBSYSTEM_REGISTRY = [
    {"name":"Organ Mesh","codename":"NerveBridge","module":"mesh"},
    {"name":"ML Threat Prediction","codename":"DeepSentinel","module":"ml"},
    {"name":"Multi-Site Federation","codename":"AllianceNet","module":"federation"},
    {"name":"Auto Penetration Testing","codename":"RedVeil","module":"pentest"},
    {"name":"Mobile API","codename":"Watchtower","module":"mobile"},
    {"name":"Accessibility Engine","codename":"EqualShield","module":"accessibility"},
    {"name":"Wireless Guardian","codename":"AirShield","module":"wireless"},
    {"name":"Physical Security","codename":"IronWatch","module":"physical"},
    {"name":"HITRUST Compliance","codename":"TrustForge","module":"hitrust"},
    {"name":"SOC 2 Type II","codename":"AuditIron","module":"soc2"},
    {"name":"Cloud Hybrid","codename":"SkyVeil","module":"cloud"},
    {"name":"Deployment Engine","codename":"Genesis","module":"deployer"},
]

class UnifiedDashboard:
    def __init__(self):
        self._subsystems = {}
        self._boot_time = datetime.now(timezone.utc).isoformat()
        for sub in SUBSYSTEM_REGISTRY:
            self._subsystems[sub["module"]] = SubsystemStatus(name=sub["name"], codename=sub["codename"])

    def update_subsystem(self, module, status="operational", health_pct=100.0, metrics=None, alerts=0):
        if module in self._subsystems:
            s = self._subsystems[module]; s.status = status; s.health_pct = health_pct
            s.last_update = datetime.now(timezone.utc).isoformat()
            if metrics: s.metrics = metrics
            s.alerts = alerts

    def get_overview(self):
        op = sum(1 for s in self._subsystems.values() if s.status == "operational")
        dg = sum(1 for s in self._subsystems.values() if s.status == "degraded")
        of = sum(1 for s in self._subsystems.values() if s.status == "offline")
        ta = sum(s.alerts for s in self._subsystems.values())
        ah = sum(s.health_pct for s in self._subsystems.values()) / max(len(self._subsystems), 1)
        overall = "DEGRADED" if of > 0 else ("ADVISORY" if dg > 0 else "NOMINAL")
        return {"system":"VeilCore","version":"1.0.0","overall_status":overall,"organs":82,"subsystems":{"total":len(self._subsystems),"operational":op,"degraded":dg,"offline":of},"health_pct":round(ah,1),"total_alerts":ta,"uptime_since":self._boot_time,"timestamp":datetime.now(timezone.utc).isoformat()}

    def get_all_subsystem_status(self):
        return [s.to_dict() for s in self._subsystems.values()]

    def get_subsystem(self, module):
        s = self._subsystems.get(module)
        return s.to_dict() if s else None

    def get_threat_summary(self):
        return {"ml_predictions":self._subsystems.get("ml",SubsystemStatus("","")).metrics.get("predictions",0),"wireless_threats":self._subsystems.get("wireless",SubsystemStatus("","")).metrics.get("threats",0),"physical_alerts":self._subsystems.get("physical",SubsystemStatus("","")).metrics.get("alerts",0),"pentest_findings":self._subsystems.get("pentest",SubsystemStatus("","")).metrics.get("findings",0),"federation_shared":self._subsystems.get("federation",SubsystemStatus("","")).metrics.get("shared_iocs",0)}

    def get_compliance_summary(self):
        return {"hitrust":self._subsystems.get("hitrust",SubsystemStatus("","")).metrics,"soc2":self._subsystems.get("soc2",SubsystemStatus("","")).metrics}

    def generate_api_routes(self):
        routes = [{"method":"GET","path":"/api/dashboard/overview","description":"Full system overview"},{"method":"GET","path":"/api/dashboard/subsystems","description":"All subsystem statuses"},{"method":"GET","path":"/api/dashboard/threats","description":"Aggregated threat summary"},{"method":"GET","path":"/api/dashboard/compliance","description":"HITRUST + SOC2 compliance"}]
        for sub in SUBSYSTEM_REGISTRY:
            routes.append({"method":"GET","path":f"/api/dashboard/{sub['module']}","description":f"{sub['name']} ({sub['codename']}) status"})
        return routes

    def summary(self):
        o = self.get_overview()
        return {"dashboard":"Prism","overall":o["overall_status"],"subsystems":f"{o['subsystems']['operational']}/{o['subsystems']['total']} operational","health":f"{o['health_pct']}%","api_routes":len(self.generate_api_routes())}
