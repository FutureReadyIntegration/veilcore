"""
VeilCore Wireless Guardian Engine
====================================
Orchestrates all wireless security subsystems into a
unified protection layer.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from core.wireless.scanner import WirelessScanner, WirelessScanResult
from core.wireless.hardener import WirelessHardener, HardeningReport
from core.wireless.rfid_nfc import RFIDNFCGuard, NFCEvent

logger = logging.getLogger("veilcore.wireless.engine")


@dataclass
class WirelessThreat:
    """Detected wireless threat."""
    threat_id: str = field(default_factory=lambda: f"WTHREAT-{int(time.time() * 1000)}")
    threat_type: str = ""       # rogue_ap, evil_twin, rogue_bt, rfid_clone, skim_attempt
    severity: str = "medium"
    source: str = ""
    details: str = ""
    recommended_action: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "threat_id": self.threat_id, "threat_type": self.threat_type,
            "severity": self.severity, "source": self.source,
            "details": self.details,
            "recommended_action": self.recommended_action,
            "timestamp": self.timestamp,
        }


class WirelessGuardianEngine:
    """
    Unified wireless security engine.

    Usage:
        engine = WirelessGuardianEngine()
        engine.configure_hospital("Memorial General")

        # Full assessment
        report = engine.full_assessment()

        # Continuous monitoring
        threats = engine.monitor_cycle()
    """

    def __init__(self):
        self._scanner = WirelessScanner()
        self._hardener = WirelessHardener()
        self._rfid_guard = RFIDNFCGuard()
        self._threats: list[WirelessThreat] = []
        self._assessment_count = 0
        self._hospital_name = "Unknown Hospital"

    def configure_hospital(self, name: str,
                           trusted_ssids: Optional[list[str]] = None,
                           trusted_bt: Optional[list[str]] = None) -> None:
        """Configure for a specific hospital."""
        self._hospital_name = name
        if trusted_ssids:
            for ssid in trusted_ssids:
                self._scanner.add_trusted_ssid(ssid)
        if trusted_bt:
            for addr in trusted_bt:
                self._scanner.add_trusted_bt(addr)
        logger.info(f"Wireless Guardian configured for: {name}")

    def full_assessment(self) -> dict[str, Any]:
        """Run complete wireless security assessment."""
        start = time.monotonic()
        self._assessment_count += 1

        # Scan wireless environment
        scan = self._scanner.scan()

        # Run hardening checks
        hardening = self._hardener.assess(scan)

        # Detect threats
        threats = self._analyze_threats(scan, hardening)
        self._threats.extend(threats)

        # RFID anomaly check
        rfid_anomalies = self._rfid_guard.detect_anomalies()
        for anomaly in rfid_anomalies:
            threats.append(WirelessThreat(
                threat_type="rfid_anomaly", severity=anomaly.severity,
                source=anomaly.reader_id, details=anomaly.details,
                recommended_action="Investigate RFID reader and tag",
            ))

        duration_ms = (time.monotonic() - start) * 1000

        report = {
            "hospital": self._hospital_name,
            "assessment_id": f"WGA-{self._assessment_count}",
            "scan": {
                "wifi_networks": len(scan.wifi_networks),
                "bluetooth_devices": len(scan.bluetooth_devices),
                "rogue_aps": len(scan.rogue_aps),
                "rogue_bt": len(scan.rogue_bt),
                "overall_risk": scan.overall_risk,
            },
            "hardening": hardening.summary(),
            "threats": [t.to_dict() for t in threats],
            "rfid_nfc": self._rfid_guard.summary(),
            "duration_ms": round(duration_ms, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(
            f"Full wireless assessment #{self._assessment_count}: "
            f"{scan.total_devices} devices, {hardening.compliance_pct}% compliant, "
            f"{len(threats)} threats"
        )

        return report

    def monitor_cycle(self) -> list[WirelessThreat]:
        """Run a single monitoring cycle (lighter than full assessment)."""
        scan = self._scanner.scan()
        threats = []

        # Check for rogue APs
        for ap in scan.rogue_aps:
            threats.append(WirelessThreat(
                threat_type="rogue_ap", severity="critical",
                source=ap.bssid,
                details=f"Rogue AP: '{ap.ssid}' on channel {ap.channel} ({ap.security})",
                recommended_action="Locate and remove, add to banned list",
            ))

        # Check for rogue BT
        for dev in scan.rogue_bt:
            threats.append(WirelessThreat(
                threat_type="rogue_bt", severity="high",
                source=dev.address,
                details=f"Suspicious BT device: '{dev.name or 'unnamed'}' (RSSI: {dev.rssi})",
                recommended_action="Investigate device, block if unauthorized",
            ))

        # Check for evil twins
        seen: dict[str, list] = {}
        for net in scan.wifi_networks:
            if net.ssid not in seen:
                seen[net.ssid] = []
            seen[net.ssid].append(net)
        for ssid, nets in seen.items():
            if len(nets) > 1:
                secs = set(n.security for n in nets)
                if len(secs) > 1:
                    threats.append(WirelessThreat(
                        threat_type="evil_twin", severity="critical",
                        source=ssid,
                        details=f"Evil twin: '{ssid}' seen with different security: {secs}",
                        recommended_action="Block rogue BSSID, alert security team",
                    ))

        # RFID anomalies
        for anomaly in self._rfid_guard.detect_anomalies():
            threats.append(WirelessThreat(
                threat_type="rfid_anomaly", severity=anomaly.severity,
                source=anomaly.tag_id, details=anomaly.details,
                recommended_action="Investigate tag and reader",
            ))

        self._threats.extend(threats)
        return threats

    def _analyze_threats(self, scan: WirelessScanResult,
                         hardening: HardeningReport) -> list[WirelessThreat]:
        """Analyze scan and hardening results for threats."""
        threats = []

        for ap in scan.rogue_aps:
            threats.append(WirelessThreat(
                threat_type="rogue_ap", severity="critical",
                source=ap.bssid,
                details=f"Rogue AP: '{ap.ssid}' ({ap.security}) at {ap.signal_dbm}dBm",
                recommended_action="Locate, remove, add BSSID to banned list",
            ))

        for dev in scan.rogue_bt:
            threats.append(WirelessThreat(
                threat_type="rogue_bt", severity="high",
                source=dev.address,
                details=f"Rogue BT: '{dev.name or 'unnamed'}' RSSI={dev.rssi}",
                recommended_action="Block device address",
            ))

        # Evil twin detection
        seen: dict[str, list] = {}
        for net in scan.wifi_networks:
            if net.ssid not in seen:
                seen[net.ssid] = []
            seen[net.ssid].append(net)
        for ssid, nets in seen.items():
            if len(nets) > 1 and len(set(n.security for n in nets)) > 1:
                threats.append(WirelessThreat(
                    threat_type="evil_twin", severity="critical",
                    source=ssid,
                    details=f"Evil twin detected for '{ssid}'",
                    recommended_action="Identify rogue BSSID and block immediately",
                ))

        # Critical hardening failures
        for result in hardening.results:
            if result.status == "fail" and result.rule.severity == "critical":
                threats.append(WirelessThreat(
                    threat_type="hardening_failure", severity="high",
                    source=result.rule.rule_id,
                    details=f"Failed: {result.rule.name} — {result.message}",
                    recommended_action=result.rule.remediation,
                ))

        return threats

    @property
    def scanner(self) -> WirelessScanner:
        return self._scanner

    @property
    def hardener(self) -> WirelessHardener:
        return self._hardener

    @property
    def rfid_guard(self) -> RFIDNFCGuard:
        return self._rfid_guard

    @property
    def threat_count(self) -> int:
        return len(self._threats)

    @property
    def assessment_count(self) -> int:
        return self._assessment_count

    def summary(self) -> dict[str, Any]:
        return {
            "engine": "WirelessGuardian",
            "codename": "AirShield",
            "hospital": self._hospital_name,
            "assessments": self._assessment_count,
            "total_threats": len(self._threats),
            "scanner_scans": self._scanner.scan_count,
            "known_networks": self._scanner.known_network_count,
            "known_bt": self._scanner.known_bt_count,
            "hardening_rules": self._hardener.rule_count,
            "rfid": self._rfid_guard.summary(),
        }
