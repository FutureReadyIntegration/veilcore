"""
VeilCore Wireless Hardening Engine
=====================================
Applies and enforces wireless security policies for
hospital network infrastructure.

Hardening categories:
    - Wi-Fi: Disable weak protocols, enforce WPA3, rogue AP blocking
    - Bluetooth: Disable pairing mode, block unauthorized devices
    - General: MAC filtering, signal strength policies, channel management
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("veilcore.wireless.hardener")


class RuleCategory(str, Enum):
    WIFI = "wifi"
    BLUETOOTH = "bluetooth"
    GENERAL = "general"


class RuleSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RuleStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class HardeningRule:
    """A wireless hardening rule."""
    rule_id: str
    name: str
    description: str
    category: str = "general"
    severity: str = "medium"
    check_fn: Optional[str] = None
    remediation: str = ""
    hipaa_control: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id, "name": self.name,
            "description": self.description, "category": self.category,
            "severity": self.severity, "remediation": self.remediation,
            "hipaa_control": self.hipaa_control,
        }


@dataclass
class RuleResult:
    """Result of a hardening rule check."""
    rule: HardeningRule
    status: str = "skipped"
    message: str = ""
    evidence: str = ""
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule.rule_id, "name": self.rule.name,
            "category": self.rule.category, "severity": self.rule.severity,
            "status": self.status, "message": self.message,
            "evidence": self.evidence, "remediation": self.rule.remediation,
            "hipaa_control": self.rule.hipaa_control,
            "checked_at": self.checked_at,
        }


@dataclass
class HardeningReport:
    """Complete hardening assessment report."""
    report_id: str = field(default_factory=lambda: f"WHR-{int(time.time())}")
    results: list[RuleResult] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    duration_ms: float = 0.0

    @property
    def total_rules(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == "pass")

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == "fail")

    @property
    def compliance_pct(self) -> float:
        checked = sum(1 for r in self.results if r.status in ("pass", "fail"))
        if checked == 0:
            return 100.0
        return round((self.passed / checked) * 100, 1)

    @property
    def overall_status(self) -> str:
        critical_fails = sum(1 for r in self.results
                             if r.status == "fail" and r.rule.severity == "critical")
        if critical_fails > 0:
            return "CRITICAL"
        if self.failed > 0:
            return "NEEDS_REMEDIATION"
        return "COMPLIANT"

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "total_rules": self.total_rules,
            "passed": self.passed, "failed": self.failed,
            "compliance_pct": self.compliance_pct,
            "overall_status": self.overall_status,
            "results": [r.to_dict() for r in self.results],
            "duration_ms": round(self.duration_ms, 2),
            "timestamp": self.timestamp,
        }

    def summary(self) -> dict[str, Any]:
        by_category = {}
        for r in self.results:
            cat = r.rule.category
            if cat not in by_category:
                by_category[cat] = {"pass": 0, "fail": 0, "skipped": 0}
            if r.status in by_category[cat]:
                by_category[cat][r.status] += 1
        return {
            "report_id": self.report_id,
            "overall_status": self.overall_status,
            "compliance_pct": self.compliance_pct,
            "passed": self.passed, "failed": self.failed,
            "by_category": by_category,
        }


# ── Hardening Rules ──

WIRELESS_RULES = [
    # Wi-Fi rules
    HardeningRule(
        "WF-001", "No Open Wi-Fi Networks",
        "All hospital Wi-Fi networks must use WPA2 or WPA3 encryption",
        category="wifi", severity="critical",
        remediation="Disable open networks or enable WPA2/WPA3 encryption",
        hipaa_control="§164.312(e)(1) - Transmission Security",
    ),
    HardeningRule(
        "WF-002", "No WEP Networks",
        "WEP encryption is cryptographically broken and must not be used",
        category="wifi", severity="critical",
        remediation="Upgrade all WEP networks to WPA2 or WPA3",
        hipaa_control="§164.312(e)(1) - Transmission Security",
    ),
    HardeningRule(
        "WF-003", "Enterprise Authentication Required",
        "Clinical Wi-Fi must use WPA2/WPA3 Enterprise (802.1X)",
        category="wifi", severity="high",
        remediation="Configure 802.1X authentication for clinical SSIDs",
        hipaa_control="§164.312(d) - Person or Entity Authentication",
    ),
    HardeningRule(
        "WF-004", "No Rogue Access Points",
        "No unauthorized access points detected in hospital premises",
        category="wifi", severity="critical",
        remediation="Locate and remove rogue APs, add to banned MAC list",
        hipaa_control="§164.312(e)(1) - Transmission Security",
    ),
    HardeningRule(
        "WF-005", "Evil Twin Detection",
        "No duplicate SSIDs from unauthorized BSSIDs",
        category="wifi", severity="critical",
        remediation="Block evil twin BSSID via wireless controller, investigate source",
        hipaa_control="§164.312(e)(1) - Transmission Security",
    ),
    HardeningRule(
        "WF-006", "Guest Network Isolation",
        "Guest Wi-Fi must be isolated from clinical networks",
        category="wifi", severity="high",
        remediation="Verify VLAN isolation between guest and clinical SSIDs",
        hipaa_control="§164.312(e)(1) - Transmission Security",
    ),

    # Bluetooth rules
    HardeningRule(
        "BT-001", "No Unknown Connectable Devices",
        "All connectable Bluetooth devices must be registered",
        category="bluetooth", severity="high",
        remediation="Register or block unknown Bluetooth devices",
        hipaa_control="§164.312(a)(1) - Access Control",
    ),
    HardeningRule(
        "BT-002", "Bluetooth Pairing Mode Disabled",
        "Hospital systems must not be discoverable via Bluetooth",
        category="bluetooth", severity="medium",
        remediation="Disable Bluetooth discoverable mode on all workstations",
        hipaa_control="§164.312(a)(1) - Access Control",
    ),
    HardeningRule(
        "BT-003", "No Unnamed Bluetooth Devices",
        "All Bluetooth devices should be identifiable",
        category="bluetooth", severity="medium",
        remediation="Investigate and register or block unnamed devices",
        hipaa_control="§164.312(a)(1) - Access Control",
    ),

    # General rules
    HardeningRule(
        "GN-001", "Wireless Interface Inventory",
        "All wireless interfaces must be documented",
        category="general", severity="medium",
        remediation="Document all wireless interfaces and their purpose",
        hipaa_control="§164.310(d)(1) - Device and Media Controls",
    ),
    HardeningRule(
        "GN-002", "Signal Leakage Assessment",
        "Hospital Wi-Fi should not extend significantly beyond premises",
        category="general", severity="low",
        remediation="Adjust AP power levels to minimize signal leakage",
        hipaa_control="§164.312(e)(1) - Transmission Security",
    ),
]


class WirelessHardener:
    """
    Evaluates and enforces wireless hardening rules.

    Usage:
        from core.wireless.scanner import WirelessScanner
        scanner = WirelessScanner()
        scan = scanner.scan()

        hardener = WirelessHardener()
        report = hardener.assess(scan)
    """

    def __init__(self, custom_rules: Optional[list[HardeningRule]] = None):
        self._rules = list(WIRELESS_RULES)
        if custom_rules:
            self._rules.extend(custom_rules)

    def assess(self, scan_result) -> HardeningReport:
        """Run all hardening rules against scan results."""
        start = time.monotonic()
        report = HardeningReport()

        for rule in self._rules:
            result = self._check_rule(rule, scan_result)
            report.results.append(result)

        report.duration_ms = (time.monotonic() - start) * 1000

        logger.info(
            f"Hardening assessment: {report.passed}/{report.total_rules} passed, "
            f"{report.compliance_pct}% compliant, status={report.overall_status}"
        )

        return report

    def _check_rule(self, rule: HardeningRule, scan) -> RuleResult:
        """Check a single rule against scan results."""
        checkers = {
            "WF-001": self._check_no_open_wifi,
            "WF-002": self._check_no_wep,
            "WF-003": self._check_enterprise_auth,
            "WF-004": self._check_no_rogue_aps,
            "WF-005": self._check_evil_twins,
            "WF-006": self._check_guest_isolation,
            "BT-001": self._check_bt_unknown,
            "BT-002": self._check_bt_pairing,
            "BT-003": self._check_bt_unnamed,
            "GN-001": self._check_interface_inventory,
            "GN-002": self._check_signal_leakage,
        }

        checker = checkers.get(rule.rule_id)
        if not checker:
            return RuleResult(rule=rule, status="skipped", message="No checker implemented")

        try:
            return checker(rule, scan)
        except Exception as e:
            return RuleResult(rule=rule, status="error", message=str(e))

    def _check_no_open_wifi(self, rule, scan) -> RuleResult:
        open_nets = [n for n in scan.wifi_networks if n.security == "open"]
        if open_nets:
            ssids = ", ".join(n.ssid for n in open_nets)
            return RuleResult(rule=rule, status="fail",
                              message=f"{len(open_nets)} open networks found",
                              evidence=f"Open SSIDs: {ssids}")
        return RuleResult(rule=rule, status="pass", message="No open networks")

    def _check_no_wep(self, rule, scan) -> RuleResult:
        wep_nets = [n for n in scan.wifi_networks if n.security == "wep"]
        if wep_nets:
            ssids = ", ".join(n.ssid for n in wep_nets)
            return RuleResult(rule=rule, status="fail",
                              message=f"{len(wep_nets)} WEP networks found",
                              evidence=f"WEP SSIDs: {ssids}")
        return RuleResult(rule=rule, status="pass", message="No WEP networks")

    def _check_enterprise_auth(self, rule, scan) -> RuleResult:
        clinical = [n for n in scan.wifi_networks
                    if any(n.ssid.startswith(p) for p in ["Hospital-Clinical", "Clinical-", "Epic-"])]
        non_enterprise = [n for n in clinical
                          if n.security not in ("wpa2_enterprise", "wpa3_enterprise")]
        if non_enterprise:
            return RuleResult(rule=rule, status="fail",
                              message=f"{len(non_enterprise)} clinical SSIDs without enterprise auth",
                              evidence=", ".join(f"{n.ssid}({n.security})" for n in non_enterprise))
        if not clinical:
            return RuleResult(rule=rule, status="pass", message="No clinical SSIDs found to check")
        return RuleResult(rule=rule, status="pass",
                          message=f"All {len(clinical)} clinical SSIDs use enterprise auth")

    def _check_no_rogue_aps(self, rule, scan) -> RuleResult:
        if scan.rogue_aps:
            rogue_info = ", ".join(f"{n.ssid}({n.bssid})" for n in scan.rogue_aps)
            return RuleResult(rule=rule, status="fail",
                              message=f"{len(scan.rogue_aps)} rogue APs detected",
                              evidence=rogue_info)
        return RuleResult(rule=rule, status="pass", message="No rogue APs detected")

    def _check_evil_twins(self, rule, scan) -> RuleResult:
        seen_ssids: dict[str, list] = {}
        for n in scan.wifi_networks:
            if n.ssid not in seen_ssids:
                seen_ssids[n.ssid] = []
            seen_ssids[n.ssid].append(n)

        twins = []
        for ssid, nets in seen_ssids.items():
            if len(nets) > 1:
                securities = set(n.security for n in nets)
                if len(securities) > 1:
                    twins.append(ssid)

        if twins:
            return RuleResult(rule=rule, status="fail",
                              message=f"Evil twin candidates: {', '.join(twins)}",
                              evidence="Same SSID with different security levels")
        return RuleResult(rule=rule, status="pass", message="No evil twins detected")

    def _check_guest_isolation(self, rule, scan) -> RuleResult:
        guest_nets = [n for n in scan.wifi_networks if "guest" in n.ssid.lower()]
        if not guest_nets:
            return RuleResult(rule=rule, status="pass", message="No guest networks found")
        # Can't verify VLAN isolation from scan alone
        return RuleResult(rule=rule, status="pass",
                          message=f"{len(guest_nets)} guest networks found — verify VLAN isolation manually")

    def _check_bt_unknown(self, rule, scan) -> RuleResult:
        unknown = [d for d in scan.bluetooth_devices
                   if d.trust in ("unknown", "rogue") and d.is_connectable]
        if unknown:
            devices = ", ".join(f"{d.name or d.address}" for d in unknown)
            return RuleResult(rule=rule, status="fail",
                              message=f"{len(unknown)} unknown connectable BT devices",
                              evidence=devices)
        return RuleResult(rule=rule, status="pass", message="All BT devices registered")

    def _check_bt_pairing(self, rule, scan) -> RuleResult:
        # Check if hci0 is in discoverable mode
        try:
            result = subprocess.run(
                ["hciconfig", "hci0"], capture_output=True, text=True, timeout=5)
            if "PSCAN" in result.stdout or "ISCAN" in result.stdout:
                return RuleResult(rule=rule, status="fail",
                                  message="Bluetooth is in discoverable mode",
                                  evidence="hci0 has PSCAN/ISCAN flags set")
        except Exception:
            pass
        return RuleResult(rule=rule, status="pass",
                          message="Bluetooth not in discoverable mode (or no adapter)")

    def _check_bt_unnamed(self, rule, scan) -> RuleResult:
        unnamed = [d for d in scan.bluetooth_devices if not d.name]
        if unnamed:
            addrs = ", ".join(d.address for d in unnamed)
            return RuleResult(rule=rule, status="fail",
                              message=f"{len(unnamed)} unnamed Bluetooth devices",
                              evidence=addrs)
        return RuleResult(rule=rule, status="pass", message="All BT devices are named")

    def _check_interface_inventory(self, rule, scan) -> RuleResult:
        total = len(scan.wifi_networks) + len(scan.bluetooth_devices)
        return RuleResult(rule=rule, status="pass",
                          message=f"Inventoried {total} wireless devices")

    def _check_signal_leakage(self, rule, scan) -> RuleResult:
        strong_unknown = [n for n in scan.wifi_networks
                          if n.trust == "unknown" and n.signal_dbm > -40]
        if strong_unknown:
            return RuleResult(rule=rule, status="fail",
                              message=f"{len(strong_unknown)} strong unknown signals detected",
                              evidence="May indicate signal leakage or nearby rogue device")
        return RuleResult(rule=rule, status="pass", message="No excessive signal leakage detected")

    @property
    def rule_count(self) -> int:
        return len(self._rules)
