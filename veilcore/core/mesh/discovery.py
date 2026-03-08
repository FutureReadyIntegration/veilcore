"""
VeilCore Organ Discovery
=========================
Auto-discovers all 82 VeilCore security organs by scanning systemd
service files and tracking their mesh registration state.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("veilcore.mesh.discovery")


class OrganState(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    STARTING = "starting"
    STOPPING = "stopping"
    DEGRADED = "degraded"
    UNRESPONSIVE = "unresponsive"
    UNKNOWN = "unknown"


class OrganTier(str, Enum):
    P0_CRITICAL = "P0"
    P1_IMPORTANT = "P1"
    P2_STANDARD = "P2"


@dataclass
class OrganInfo:
    name: str
    display_name: str
    tier: OrganTier
    state: OrganState = OrganState.UNKNOWN
    service_name: str = ""
    service_active: bool = False
    mesh_connected: bool = False
    last_heartbeat: Optional[str] = None
    last_state_change: Optional[str] = None
    subscriptions: list[str] = field(default_factory=list)
    error_count: int = 0
    uptime_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name, "display_name": self.display_name,
            "tier": self.tier.value, "state": self.state.value,
            "service_name": self.service_name, "service_active": self.service_active,
            "mesh_connected": self.mesh_connected, "last_heartbeat": self.last_heartbeat,
            "last_state_change": self.last_state_change,
            "subscriptions": self.subscriptions,
            "error_count": self.error_count,
            "uptime_seconds": round(self.uptime_seconds, 2),
        }


ORGAN_CATALOG: list[dict[str, str]] = [
    # P0 Critical (14)
    {"name": "guardian", "display": "Guardian", "tier": "P0"},
    {"name": "sentinel", "display": "Sentinel", "tier": "P0"},
    {"name": "audit", "display": "Audit", "tier": "P0"},
    {"name": "chronicle", "display": "Chronicle", "tier": "P0"},
    {"name": "cortex", "display": "Cortex", "tier": "P0"},
    {"name": "insider-threat", "display": "Insider Threat", "tier": "P0"},
    {"name": "phi-classifier", "display": "PHI Classifier", "tier": "P0"},
    {"name": "encryption-enforcer", "display": "Encryption Enforcer", "tier": "P0"},
    {"name": "watchdog", "display": "Watchdog", "tier": "P0"},
    {"name": "firewall", "display": "Firewall", "tier": "P0"},
    {"name": "backup", "display": "Backup", "tier": "P0"},
    {"name": "quarantine", "display": "Quarantine", "tier": "P0"},
    {"name": "vault", "display": "Vault", "tier": "P0"},
    {"name": "mfa", "display": "MFA", "tier": "P0"},
    # P1 Important (14)
    {"name": "rbac", "display": "RBAC", "tier": "P1"},
    {"name": "host-sensor", "display": "Host Sensor", "tier": "P1"},
    {"name": "network-monitor", "display": "Network Monitor", "tier": "P1"},
    {"name": "threat-intel", "display": "Threat Intel", "tier": "P1"},
    {"name": "phi-guard", "display": "PHI Guard", "tier": "P1"},
    {"name": "epic-connector", "display": "Epic Connector", "tier": "P1"},
    {"name": "imprivata-bridge", "display": "Imprivata Bridge", "tier": "P1"},
    {"name": "hl7-filter", "display": "HL7 Filter", "tier": "P1"},
    {"name": "fhir-gateway", "display": "FHIR Gateway", "tier": "P1"},
    {"name": "dicom-shield", "display": "DICOM Shield", "tier": "P1"},
    {"name": "iomt-protector", "display": "IoMT Protector", "tier": "P1"},
    {"name": "canary", "display": "Canary", "tier": "P1"},
    {"name": "scanner", "display": "Scanner", "tier": "P1"},
    {"name": "patcher", "display": "Patcher", "tier": "P1"},
    # P2 Standard (54)
    {"name": "encryptor", "display": "Encryptor", "tier": "P2"},
    {"name": "dlp-engine", "display": "DLP Engine", "tier": "P2"},
    {"name": "behavioral-analysis", "display": "Behavioral Analysis", "tier": "P2"},
    {"name": "anomaly-detector", "display": "Anomaly Detector", "tier": "P2"},
    {"name": "vpn-manager", "display": "VPN Manager", "tier": "P2"},
    {"name": "certificate-authority", "display": "Certificate Authority", "tier": "P2"},
    {"name": "key-manager", "display": "Key Manager", "tier": "P2"},
    {"name": "session-monitor", "display": "Session Monitor", "tier": "P2"},
    {"name": "compliance-engine", "display": "Compliance Engine", "tier": "P2"},
    {"name": "risk-analyzer", "display": "Risk Analyzer", "tier": "P2"},
    {"name": "forensic-collector", "display": "Forensic Collector", "tier": "P2"},
    {"name": "incident-responder", "display": "Incident Responder", "tier": "P2"},
    {"name": "malware-detector", "display": "Malware Detector", "tier": "P2"},
    {"name": "ransomware-shield", "display": "Ransomware Shield", "tier": "P2"},
    {"name": "zero-trust-engine", "display": "Zero Trust Engine", "tier": "P2"},
    {"name": "micro-segmentation", "display": "Micro-segmentation", "tier": "P2"},
    {"name": "api-gateway", "display": "API Gateway", "tier": "P2"},
    {"name": "load-balancer", "display": "Load Balancer", "tier": "P2"},
    {"name": "waf", "display": "WAF", "tier": "P2"},
    {"name": "ids-ips", "display": "IDS/IPS", "tier": "P2"},
    {"name": "siem-connector", "display": "SIEM Connector", "tier": "P2"},
    {"name": "log-aggregator", "display": "Log Aggregator", "tier": "P2"},
    {"name": "metrics-collector", "display": "Metrics Collector", "tier": "P2"},
    {"name": "alert-manager", "display": "Alert Manager", "tier": "P2"},
    {"name": "notification-engine", "display": "Notification Engine", "tier": "P2"},
    {"name": "email-gateway", "display": "Email Gateway", "tier": "P2"},
    {"name": "sms-notifier", "display": "SMS Notifier", "tier": "P2"},
    {"name": "webhook-handler", "display": "Webhook Handler", "tier": "P2"},
    {"name": "dns-filter", "display": "DNS Filter", "tier": "P2"},
    {"name": "web-proxy", "display": "Web Proxy", "tier": "P2"},
    {"name": "content-filter", "display": "Content Filter", "tier": "P2"},
    {"name": "ssl-inspector", "display": "SSL Inspector", "tier": "P2"},
    {"name": "traffic-shaper", "display": "Traffic Shaper", "tier": "P2"},
    {"name": "bandwidth-monitor", "display": "Bandwidth Monitor", "tier": "P2"},
    {"name": "port-scanner", "display": "Port Scanner", "tier": "P2"},
    {"name": "vulnerability-scanner", "display": "Vulnerability Scanner", "tier": "P2"},
    {"name": "patch-manager", "display": "Patch Manager", "tier": "P2"},
    {"name": "config-auditor", "display": "Config Auditor", "tier": "P2"},
    {"name": "baseline-monitor", "display": "Baseline Monitor", "tier": "P2"},
    {"name": "integrity-checker", "display": "Integrity Checker", "tier": "P2"},
    {"name": "file-monitor", "display": "File Monitor", "tier": "P2"},
    {"name": "registry-watcher", "display": "Registry Watcher", "tier": "P2"},
    {"name": "process-monitor", "display": "Process Monitor", "tier": "P2"},
    {"name": "service-guardian", "display": "Service Guardian", "tier": "P2"},
    {"name": "resource-limiter", "display": "Resource Limiter", "tier": "P2"},
    {"name": "performance-monitor", "display": "Performance Monitor", "tier": "P2"},
    {"name": "health-checker", "display": "Health Checker", "tier": "P2"},
    {"name": "uptime-tracker", "display": "Uptime Tracker", "tier": "P2"},
    {"name": "disaster-recovery", "display": "Disaster Recovery", "tier": "P2"},
    {"name": "snapshot-manager", "display": "Snapshot Manager", "tier": "P2"},
    {"name": "replication-engine", "display": "Replication Engine", "tier": "P2"},
    {"name": "failover-controller", "display": "Failover Controller", "tier": "P2"},
    {"name": "backup-validator", "display": "Backup Validator", "tier": "P2"},
    {"name": "compliance-tracker", "display": "Compliance Tracker", "tier": "P2"},
]

assert len(ORGAN_CATALOG) == 82, f"Expected 82 organs, got {len(ORGAN_CATALOG)}"


class OrganDiscovery:
    def __init__(self, systemd_prefix: str = "veilcore-"):
        self.systemd_prefix = systemd_prefix
        self._registry: dict[str, OrganInfo] = {}
        self._last_scan: Optional[str] = None
        for entry in ORGAN_CATALOG:
            name = entry["name"]
            self._registry[name] = OrganInfo(
                name=name, display_name=entry["display"],
                tier=OrganTier(entry["tier"]),
                service_name=f"veilcore-{name}.service",
            )

    @property
    def registry(self) -> dict[str, OrganInfo]:
        return dict(self._registry)

    @property
    def total_count(self) -> int:
        return len(self._registry)

    @property
    def online_count(self) -> int:
        return sum(1 for o in self._registry.values() if o.state == OrganState.ONLINE)

    @property
    def offline_count(self) -> int:
        return sum(1 for o in self._registry.values()
                   if o.state in (OrganState.OFFLINE, OrganState.UNKNOWN))

    @property
    def degraded_count(self) -> int:
        return sum(1 for o in self._registry.values()
                   if o.state in (OrganState.DEGRADED, OrganState.UNRESPONSIVE))

    def get_by_tier(self, tier: OrganTier) -> list[OrganInfo]:
        return [o for o in self._registry.values() if o.tier == tier]

    def get_by_state(self, state: OrganState) -> list[OrganInfo]:
        return [o for o in self._registry.values() if o.state == state]

    async def scan(self) -> dict[str, OrganInfo]:
        logger.info("Running organ discovery scan...")
        await self._scan_systemd()
        self._last_scan = datetime.now(timezone.utc).isoformat()
        logger.info(
            f"Discovery scan complete | Online: {self.online_count} | "
            f"Degraded: {self.degraded_count} | Offline: {self.offline_count} | "
            f"Total: {self.total_count}"
        )
        return self._registry

    async def _scan_systemd(self) -> None:
        for name, organ in self._registry.items():
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", organ.service_name],
                    capture_output=True, text=True, timeout=5,
                )
                status = result.stdout.strip()
                organ.service_active = (status == "active")
                organ.state = OrganState.ONLINE if organ.service_active else OrganState.OFFLINE
            except subprocess.TimeoutExpired:
                organ.state = OrganState.UNKNOWN
            except FileNotFoundError:
                organ.state = OrganState.UNKNOWN
            except Exception as e:
                logger.debug(f"systemd check failed for {name}: {e}")
                organ.state = OrganState.UNKNOWN

    def update_from_mesh_status(self, mesh_status: dict[str, Any]) -> None:
        connected = mesh_status.get("organs", {}).get("connected", {})
        for name, organ in self._registry.items():
            if name in connected:
                mesh_data = connected[name]
                organ.mesh_connected = True
                organ.last_heartbeat = str(mesh_data.get("last_heartbeat", ""))
                organ.subscriptions = mesh_data.get("subscriptions", [])
                organ.uptime_seconds = mesh_data.get("uptime_seconds", 0)
                organ.error_count = mesh_data.get("errors", 0)
                organ.state = OrganState.ONLINE if mesh_data.get("is_alive", True) else OrganState.UNRESPONSIVE
            else:
                organ.mesh_connected = False

    def summary(self) -> dict[str, Any]:
        return {
            "total": self.total_count, "online": self.online_count,
            "offline": self.offline_count, "degraded": self.degraded_count,
            "by_tier": {
                "P0_critical": {"total": len(self.get_by_tier(OrganTier.P0_CRITICAL)),
                                "online": len([o for o in self.get_by_tier(OrganTier.P0_CRITICAL)
                                               if o.state == OrganState.ONLINE])},
                "P1_important": {"total": len(self.get_by_tier(OrganTier.P1_IMPORTANT)),
                                 "online": len([o for o in self.get_by_tier(OrganTier.P1_IMPORTANT)
                                                if o.state == OrganState.ONLINE])},
                "P2_standard": {"total": len(self.get_by_tier(OrganTier.P2_STANDARD)),
                                "online": len([o for o in self.get_by_tier(OrganTier.P2_STANDARD)
                                               if o.state == OrganState.ONLINE])},
            },
            "last_scan": self._last_scan,
        }

    def to_dict(self) -> dict[str, Any]:
        return {"summary": self.summary(),
                "organs": {name: organ.to_dict() for name, organ in self._registry.items()}}

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)
