"""
VeilCore Cloud-Hybrid Engine — SkyVeil
=========================================
Manages hybrid deployment across on-premises and cloud
infrastructure.

Capabilities:
    - Multi-cloud orchestration (AWS, Azure, GCP)
    - On-prem to cloud failover
    - Selective organ cloud offloading
    - PHI-aware data residency enforcement
    - Cloud node health monitoring
    - Encrypted sync between on-prem and cloud
    - Burst scaling for threat response
    - Cloud-based backup verification
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("veilcore.cloud.hybrid")


class CloudProvider(str, Enum):
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    PRIVATE = "private"
    ON_PREM = "on_prem"


class NodeRole(str, Enum):
    PRIMARY = "primary"
    REPLICA = "replica"
    FAILOVER = "failover"
    BURST = "burst"
    BACKUP = "backup"
    ANALYTICS = "analytics"


class NodeState(str, Enum):
    ACTIVE = "active"
    STANDBY = "standby"
    SYNCING = "syncing"
    FAILED = "failed"
    PROVISIONING = "provisioning"
    DECOMMISSIONED = "decommissioned"


class DataClass(str, Enum):
    PHI = "phi"
    PII = "pii"
    OPERATIONAL = "operational"
    THREAT_INTEL = "threat_intel"
    METRICS = "metrics"
    LOGS = "logs"


@dataclass
class SyncPolicy:
    """Data synchronization policy between nodes."""
    policy_id: str
    name: str
    data_classes: list[str] = field(default_factory=list)
    direction: str = "bidirectional"  # push, pull, bidirectional
    frequency_seconds: int = 300
    encryption_required: bool = True
    phi_allowed: bool = False  # PHI NEVER leaves on-prem by default
    compression: bool = True
    max_batch_mb: int = 100
    retention_days: int = 90

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id, "name": self.name,
            "data_classes": self.data_classes, "direction": self.direction,
            "frequency_seconds": self.frequency_seconds,
            "encryption_required": self.encryption_required,
            "phi_allowed": self.phi_allowed,
            "compression": self.compression,
            "max_batch_mb": self.max_batch_mb,
            "retention_days": self.retention_days,
        }


@dataclass
class CloudNode:
    """A node in the hybrid deployment."""
    node_id: str
    provider: str = "on_prem"
    role: str = "primary"
    state: str = "active"
    region: str = ""
    endpoint: str = ""
    organs_hosted: list[str] = field(default_factory=list)
    data_classes: list[str] = field(default_factory=list)
    cpu_cores: int = 0
    ram_gb: float = 0.0
    disk_gb: float = 0.0
    last_heartbeat: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    registered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def is_cloud(self) -> bool:
        return self.provider != "on_prem"

    @property
    def hosts_phi(self) -> bool:
        return "phi" in self.data_classes

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id, "provider": self.provider,
            "role": self.role, "state": self.state,
            "region": self.region, "endpoint": self.endpoint,
            "organs_hosted": self.organs_hosted,
            "data_classes": self.data_classes,
            "cpu_cores": self.cpu_cores, "ram_gb": self.ram_gb,
            "disk_gb": round(self.disk_gb, 1),
            "is_cloud": self.is_cloud, "hosts_phi": self.hosts_phi,
            "last_heartbeat": self.last_heartbeat,
        }


@dataclass
class SyncEvent:
    """Record of a data sync between nodes."""
    sync_id: str = field(default_factory=lambda: f"SYNC-{int(time.time() * 1000)}")
    source_node: str = ""
    target_node: str = ""
    policy_id: str = ""
    data_classes: list[str] = field(default_factory=list)
    records_synced: int = 0
    bytes_transferred: int = 0
    encrypted: bool = True
    success: bool = True
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "sync_id": self.sync_id, "source": self.source_node,
            "target": self.target_node, "policy": self.policy_id,
            "data_classes": self.data_classes,
            "records": self.records_synced,
            "bytes": self.bytes_transferred,
            "encrypted": self.encrypted,
            "success": self.success,
            "duration_ms": round(self.duration_ms, 2),
            "timestamp": self.timestamp,
        }


# ── PHI-Safe Data Residency Rules ──
PHI_RESIDENCY_RULES = {
    "phi": {"cloud_allowed": False, "encryption": "AES-256-GCM",
            "regions": ["on_prem_only"]},
    "pii": {"cloud_allowed": False, "encryption": "AES-256-GCM",
            "regions": ["on_prem_only"]},
    "operational": {"cloud_allowed": True, "encryption": "AES-256-GCM",
                    "regions": ["us-east-1", "us-west-2", "us-central1"]},
    "threat_intel": {"cloud_allowed": True, "encryption": "TLS-1.3",
                     "regions": ["any"]},
    "metrics": {"cloud_allowed": True, "encryption": "TLS-1.3",
                "regions": ["any"]},
    "logs": {"cloud_allowed": True, "encryption": "AES-256-GCM",
             "regions": ["us-east-1", "us-west-2", "us-central1"]},
}

# ── Default Sync Policies ──
DEFAULT_POLICIES = [
    SyncPolicy("SYNC-THREAT", "Threat Intelligence Sync",
               data_classes=["threat_intel"], direction="bidirectional",
               frequency_seconds=60, phi_allowed=False),
    SyncPolicy("SYNC-METRICS", "Metrics Offload",
               data_classes=["metrics"], direction="push",
               frequency_seconds=300, phi_allowed=False),
    SyncPolicy("SYNC-LOGS", "Log Archive",
               data_classes=["logs"], direction="push",
               frequency_seconds=900, phi_allowed=False),
    SyncPolicy("SYNC-BACKUP", "Cloud Backup Verification",
               data_classes=["operational"], direction="push",
               frequency_seconds=3600, phi_allowed=False),
]

# ── Organs safe for cloud offloading ──
CLOUD_SAFE_ORGANS = [
    "threat_intel", "metrics_collector", "log_aggregator",
    "performance_monitor", "bandwidth_monitor", "uptime_tracker",
    "vulnerability_scanner", "compliance_tracker", "risk_analyzer",
    "anomaly_detector", "behavioral_analysis",
]

# ── Organs that MUST stay on-prem (handle PHI/PII) ──
ON_PREM_ONLY_ORGANS = [
    "guardian", "phi_classifier", "phi_guard", "vault",
    "encryption_enforcer", "epic_connector", "imprivata_bridge",
    "hl7_filter", "fhir_gateway", "dicom_shield",
    "insider_threat", "forensic_collector", "dlp_engine",
]


class CloudHybridEngine:
    """
    Orchestrates hybrid on-prem/cloud deployment.

    Usage:
        engine = CloudHybridEngine()

        # Register nodes
        engine.register_node("ONPREM-1", provider="on_prem",
            role="primary", organs=["guardian", "sentinel", ...])
        engine.register_node("AWS-ANALYTICS", provider="aws",
            role="analytics", region="us-east-1",
            organs=["threat_intel", "metrics_collector"])

        # Sync data
        engine.sync("ONPREM-1", "AWS-ANALYTICS", policy_id="SYNC-THREAT")

        # Failover
        engine.failover("ONPREM-1", "AWS-FAILOVER")
    """

    def __init__(self):
        self._nodes: dict[str, CloudNode] = {}
        self._policies: dict[str, SyncPolicy] = {p.policy_id: p for p in DEFAULT_POLICIES}
        self._sync_history: list[SyncEvent] = []
        self._failover_log: list[dict] = []

    def register_node(self, node_id: str, provider: str = "on_prem",
                      role: str = "primary", region: str = "",
                      endpoint: str = "", organs: Optional[list[str]] = None,
                      data_classes: Optional[list[str]] = None,
                      cpu_cores: int = 0, ram_gb: float = 0.0,
                      disk_gb: float = 0.0) -> CloudNode:
        """Register a deployment node."""
        # Enforce PHI residency
        organ_list = organs or []
        data_list = data_classes or []

        if provider != "on_prem":
            # Block PHI-handling organs from cloud
            phi_violations = [o for o in organ_list if o in ON_PREM_ONLY_ORGANS]
            if phi_violations:
                raise ValueError(
                    f"PHI-handling organs cannot be deployed to cloud: {phi_violations}")

            # Block PHI data class from cloud
            if "phi" in data_list or "pii" in data_list:
                raise ValueError("PHI/PII data classes cannot be hosted in cloud nodes")

        node = CloudNode(
            node_id=node_id, provider=provider, role=role,
            state="active", region=region, endpoint=endpoint,
            organs_hosted=organ_list, data_classes=data_list,
            cpu_cores=cpu_cores, ram_gb=ram_gb, disk_gb=disk_gb,
        )
        self._nodes[node_id] = node
        logger.info(f"Registered node: {node_id} ({provider}/{role}) "
                    f"with {len(organ_list)} organs")
        return node

    def add_policy(self, policy: SyncPolicy) -> None:
        """Add a sync policy."""
        if policy.phi_allowed:
            logger.warning(f"Policy {policy.policy_id} allows PHI sync — "
                           f"ensure HIPAA compliance!")
        self._policies[policy.policy_id] = policy

    def sync(self, source_id: str, target_id: str,
             policy_id: str = "") -> SyncEvent:
        """Synchronize data between two nodes."""
        source = self._nodes.get(source_id)
        target = self._nodes.get(target_id)

        if not source or not target:
            raise ValueError(f"Unknown node: {source_id if not source else target_id}")

        policy = self._policies.get(policy_id, DEFAULT_POLICIES[0])

        # PHI check
        if not policy.phi_allowed:
            for dc in policy.data_classes:
                rule = PHI_RESIDENCY_RULES.get(dc, {})
                if not rule.get("cloud_allowed", True) and target.is_cloud:
                    raise ValueError(
                        f"Data class '{dc}' cannot be synced to cloud node {target_id}")

        start = time.monotonic()

        # Simulate sync
        records = len(source.organs_hosted) * 100
        bytes_transferred = records * 256

        event = SyncEvent(
            source_node=source_id, target_node=target_id,
            policy_id=policy.policy_id,
            data_classes=policy.data_classes,
            records_synced=records,
            bytes_transferred=bytes_transferred,
            encrypted=policy.encryption_required,
            success=True,
            duration_ms=(time.monotonic() - start) * 1000,
        )

        self._sync_history.append(event)
        logger.info(f"Sync complete: {source_id} → {target_id} "
                    f"({records} records, {bytes_transferred} bytes)")
        return event

    def failover(self, failed_node_id: str,
                 failover_node_id: str) -> dict[str, Any]:
        """Failover from one node to another."""
        failed = self._nodes.get(failed_node_id)
        target = self._nodes.get(failover_node_id)

        if not failed or not target:
            raise ValueError("Unknown node in failover pair")

        # Move non-PHI organs to failover
        moveable = [o for o in failed.organs_hosted
                    if o not in ON_PREM_ONLY_ORGANS or not target.is_cloud]
        blocked = [o for o in failed.organs_hosted if o not in moveable]

        failed.state = "failed"
        target.state = "active"
        target.organs_hosted.extend(moveable)

        record = {
            "event": "failover",
            "failed_node": failed_node_id,
            "failover_node": failover_node_id,
            "organs_moved": moveable,
            "organs_blocked": blocked,
            "blocked_reason": "PHI-handling organs cannot move to cloud" if blocked else "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._failover_log.append(record)

        logger.warning(f"FAILOVER: {failed_node_id} → {failover_node_id}, "
                       f"moved {len(moveable)} organs, {len(blocked)} blocked")
        return record

    def heartbeat(self, node_id: str) -> None:
        """Process node heartbeat."""
        node = self._nodes.get(node_id)
        if node:
            node.last_heartbeat = datetime.now(timezone.utc).isoformat()
            if node.state == "failed":
                node.state = "active"

    def validate_phi_compliance(self) -> dict[str, Any]:
        """Validate that PHI residency rules are enforced."""
        violations = []
        for node in self._nodes.values():
            if node.is_cloud:
                # Check for PHI organs
                phi_organs = [o for o in node.organs_hosted if o in ON_PREM_ONLY_ORGANS]
                if phi_organs:
                    violations.append({
                        "node": node.node_id, "type": "phi_organ_in_cloud",
                        "organs": phi_organs,
                    })
                # Check for PHI data
                if "phi" in node.data_classes or "pii" in node.data_classes:
                    violations.append({
                        "node": node.node_id, "type": "phi_data_in_cloud",
                        "data_classes": [d for d in node.data_classes if d in ("phi", "pii")],
                    })

        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "cloud_nodes": sum(1 for n in self._nodes.values() if n.is_cloud),
            "onprem_nodes": sum(1 for n in self._nodes.values() if not n.is_cloud),
            "phi_protected_organs": len(ON_PREM_ONLY_ORGANS),
        }

    def get_topology(self) -> dict[str, Any]:
        """Get the full deployment topology."""
        by_provider = defaultdict(list)
        for node in self._nodes.values():
            by_provider[node.provider].append(node.to_dict())

        return {
            "total_nodes": len(self._nodes),
            "by_provider": dict(by_provider),
            "total_organs_deployed": sum(len(n.organs_hosted) for n in self._nodes.values()),
            "sync_policies": len(self._policies),
            "sync_events": len(self._sync_history),
            "failovers": len(self._failover_log),
        }

    def get_node(self, node_id: str) -> Optional[CloudNode]:
        return self._nodes.get(node_id)

    def summary(self) -> dict[str, Any]:
        phi_check = self.validate_phi_compliance()
        return {
            "engine": "CloudHybrid",
            "codename": "SkyVeil",
            "nodes": len(self._nodes),
            "cloud_nodes": sum(1 for n in self._nodes.values() if n.is_cloud),
            "onprem_nodes": sum(1 for n in self._nodes.values() if not n.is_cloud),
            "sync_policies": len(self._policies),
            "phi_compliant": phi_check["compliant"],
            "cloud_safe_organs": len(CLOUD_SAFE_ORGANS),
            "onprem_only_organs": len(ON_PREM_ONLY_ORGANS),
        }
