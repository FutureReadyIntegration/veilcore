"""VeilCore Cloud-Hybrid Engine — SkyVeil"""
from __future__ import annotations
import json, logging, os, time, hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
logger = logging.getLogger("veilcore.cloud.hybrid")

@dataclass
class SyncPolicy:
    policy_id: str; name: str
    data_classes: list[str] = field(default_factory=list)
    direction: str = "bidirectional"
    frequency_seconds: int = 300
    encryption_required: bool = True
    phi_allowed: bool = False
    compression: bool = True
    max_batch_mb: int = 100
    retention_days: int = 90
    def to_dict(self):
        return {"policy_id":self.policy_id,"name":self.name,"data_classes":self.data_classes,"direction":self.direction,"frequency_seconds":self.frequency_seconds,"encryption_required":self.encryption_required,"phi_allowed":self.phi_allowed}

@dataclass
class CloudNode:
    node_id: str; provider: str = "on_prem"; role: str = "primary"; state: str = "active"
    region: str = ""; endpoint: str = ""
    organs_hosted: list[str] = field(default_factory=list)
    data_classes: list[str] = field(default_factory=list)
    cpu_cores: int = 0; ram_gb: float = 0.0; disk_gb: float = 0.0
    last_heartbeat: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    @property
    def is_cloud(self): return self.provider != "on_prem"
    @property
    def hosts_phi(self): return "phi" in self.data_classes
    def to_dict(self):
        return {"node_id":self.node_id,"provider":self.provider,"role":self.role,"state":self.state,"region":self.region,"organs_hosted":self.organs_hosted,"data_classes":self.data_classes,"is_cloud":self.is_cloud,"hosts_phi":self.hosts_phi,"last_heartbeat":self.last_heartbeat}

@dataclass
class SyncEvent:
    sync_id: str = field(default_factory=lambda: f"SYNC-{int(time.time()*1000)}")
    source_node: str = ""; target_node: str = ""; policy_id: str = ""
    data_classes: list[str] = field(default_factory=list)
    records_synced: int = 0; bytes_transferred: int = 0
    encrypted: bool = True; success: bool = True; duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    def to_dict(self):
        return {"sync_id":self.sync_id,"source":self.source_node,"target":self.target_node,"policy":self.policy_id,"records":self.records_synced,"bytes":self.bytes_transferred,"encrypted":self.encrypted,"success":self.success,"timestamp":self.timestamp}

PHI_RESIDENCY_RULES = {
    "phi":{"cloud_allowed":False},"pii":{"cloud_allowed":False},
    "operational":{"cloud_allowed":True},"threat_intel":{"cloud_allowed":True},
    "metrics":{"cloud_allowed":True},"logs":{"cloud_allowed":True},
}

DEFAULT_POLICIES = [
    SyncPolicy("SYNC-THREAT","Threat Intelligence Sync",data_classes=["threat_intel"],direction="bidirectional",frequency_seconds=60),
    SyncPolicy("SYNC-METRICS","Metrics Offload",data_classes=["metrics"],direction="push",frequency_seconds=300),
    SyncPolicy("SYNC-LOGS","Log Archive",data_classes=["logs"],direction="push",frequency_seconds=900),
    SyncPolicy("SYNC-BACKUP","Cloud Backup Verification",data_classes=["operational"],direction="push",frequency_seconds=3600),
]

ON_PREM_ONLY_ORGANS = ["guardian","phi_classifier","phi_guard","vault","encryption_enforcer","epic_connector","imprivata_bridge","hl7_filter","fhir_gateway","dicom_shield","insider_threat","forensic_collector","dlp_engine"]
CLOUD_SAFE_ORGANS = ["threat_intel","metrics_collector","log_aggregator","performance_monitor","bandwidth_monitor","uptime_tracker","vulnerability_scanner","compliance_tracker","risk_analyzer","anomaly_detector","behavioral_analysis"]

class CloudHybridEngine:
    def __init__(self):
        self._nodes = {}
        self._policies = {p.policy_id: p for p in DEFAULT_POLICIES}
        self._sync_history = []
        self._failover_log = []

    def register_node(self, node_id, provider="on_prem", role="primary", region="", endpoint="", organs=None, data_classes=None, cpu_cores=0, ram_gb=0.0, disk_gb=0.0):
        organ_list = organs or []; data_list = data_classes or []
        if provider != "on_prem":
            phi_violations = [o for o in organ_list if o in ON_PREM_ONLY_ORGANS]
            if phi_violations: raise ValueError(f"PHI-handling organs cannot be deployed to cloud: {phi_violations}")
            if "phi" in data_list or "pii" in data_list: raise ValueError("PHI/PII data classes cannot be hosted in cloud nodes")
        node = CloudNode(node_id=node_id, provider=provider, role=role, state="active", region=region, endpoint=endpoint, organs_hosted=organ_list, data_classes=data_list, cpu_cores=cpu_cores, ram_gb=ram_gb, disk_gb=disk_gb)
        self._nodes[node_id] = node; return node

    def add_policy(self, policy):
        self._policies[policy.policy_id] = policy

    def sync(self, source_id, target_id, policy_id=""):
        source = self._nodes.get(source_id); target = self._nodes.get(target_id)
        if not source or not target: raise ValueError(f"Unknown node: {source_id if not source else target_id}")
        policy = self._policies.get(policy_id, DEFAULT_POLICIES[0])
        if not policy.phi_allowed:
            for dc in policy.data_classes:
                rule = PHI_RESIDENCY_RULES.get(dc, {})
                if not rule.get("cloud_allowed", True) and target.is_cloud:
                    raise ValueError(f"Data class '{dc}' cannot be synced to cloud node {target_id}")
        start = time.monotonic(); records = len(source.organs_hosted) * 100; bytes = records * 256
        event = SyncEvent(source_node=source_id, target_node=target_id, policy_id=policy.policy_id, data_classes=policy.data_classes, records_synced=records, bytes_transferred=bytes, encrypted=policy.encryption_required, success=True, duration_ms=(time.monotonic()-start)*1000)
        self._sync_history.append(event); return event

    def failover(self, failed_id, failover_id):
        failed = self._nodes.get(failed_id); target = self._nodes.get(failover_id)
        if not failed or not target: raise ValueError("Unknown node in failover pair")
        moveable = [o for o in failed.organs_hosted if o not in ON_PREM_ONLY_ORGANS or not target.is_cloud]
        blocked = [o for o in failed.organs_hosted if o not in moveable]
        failed.state = "failed"; target.state = "active"; target.organs_hosted.extend(moveable)
        record = {"event":"failover","failed_node":failed_id,"failover_node":failover_id,"organs_moved":moveable,"organs_blocked":blocked,"blocked_reason":"PHI organs cannot move to cloud" if blocked else "","timestamp":datetime.now(timezone.utc).isoformat()}
        self._failover_log.append(record); return record

    def heartbeat(self, node_id):
        node = self._nodes.get(node_id)
        if node: node.last_heartbeat = datetime.now(timezone.utc).isoformat()

    def validate_phi_compliance(self):
        violations = []
        for node in self._nodes.values():
            if node.is_cloud:
                phi_organs = [o for o in node.organs_hosted if o in ON_PREM_ONLY_ORGANS]
                if phi_organs: violations.append({"node":node.node_id,"type":"phi_organ_in_cloud","organs":phi_organs})
                if "phi" in node.data_classes or "pii" in node.data_classes: violations.append({"node":node.node_id,"type":"phi_data_in_cloud"})
        return {"compliant":len(violations)==0,"violations":violations,"cloud_nodes":sum(1 for n in self._nodes.values() if n.is_cloud),"onprem_nodes":sum(1 for n in self._nodes.values() if not n.is_cloud),"phi_protected_organs":len(ON_PREM_ONLY_ORGANS)}

    def get_topology(self):
        by_provider = defaultdict(list)
        for node in self._nodes.values(): by_provider[node.provider].append(node.to_dict())
        return {"total_nodes":len(self._nodes),"by_provider":dict(by_provider),"total_organs_deployed":sum(len(n.organs_hosted) for n in self._nodes.values()),"sync_policies":len(self._policies),"sync_events":len(self._sync_history),"failovers":len(self._failover_log)}

    def get_node(self, node_id): return self._nodes.get(node_id)

    def summary(self):
        phi = self.validate_phi_compliance()
        return {"engine":"CloudHybrid","codename":"SkyVeil","nodes":len(self._nodes),"cloud_nodes":sum(1 for n in self._nodes.values() if n.is_cloud),"onprem_nodes":sum(1 for n in self._nodes.values() if not n.is_cloud),"sync_policies":len(self._policies),"phi_compliant":phi["compliant"],"cloud_safe_organs":len(CLOUD_SAFE_ORGANS),"onprem_only_organs":len(ON_PREM_ONLY_ORGANS)}
