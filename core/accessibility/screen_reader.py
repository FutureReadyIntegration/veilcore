"""
VeilCore Screen Reader Integration
=====================================
Generates structured, screen-reader-friendly output
for VeilCore data. Designed for compatibility with:
    - JAWS (Windows)
    - NVDA (Windows)
    - VoiceOver (macOS/iOS)
    - Orca (Linux)
    - TalkBack (Android)

Output follows ARIA-inspired semantic structure with
landmarks, roles, and live region announcements.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("veilcore.accessibility.screen_reader")


class Urgency(str, Enum):
    """Announcement urgency levels (maps to aria-live)."""
    ASSERTIVE = "assertive"    # Interrupts immediately (critical alerts)
    POLITE = "polite"          # Announces at next pause (status updates)
    OFF = "off"                # Silent (background data)


class SemanticRole(str, Enum):
    """Semantic roles for structured output."""
    ALERT = "alert"
    STATUS = "status"
    LOG = "log"
    TIMER = "timer"
    NAVIGATION = "navigation"
    TABLE = "table"
    LIST = "list"
    HEADING = "heading"
    REGION = "region"


@dataclass
class ScreenReaderBlock:
    """A block of screen-reader-friendly output."""
    content: str
    role: str = "status"
    urgency: str = "polite"
    label: str = ""
    level: int = 2            # Heading level (1-6)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content, "role": self.role,
            "urgency": self.urgency, "label": self.label,
            "level": self.level, "metadata": self.metadata,
            "timestamp": self.timestamp,
        }

    def to_ssml(self) -> str:
        """Convert to SSML (Speech Synthesis Markup Language)."""
        rate = "fast" if self.urgency == "assertive" else "medium"
        emphasis = "strong" if self.urgency == "assertive" else "moderate"
        return (
            f'<speak>'
            f'<prosody rate="{rate}">'
            f'<emphasis level="{emphasis}">{self.content}</emphasis>'
            f'</prosody>'
            f'</speak>'
        )


class ScreenReaderOutput:
    """
    Generates screen-reader-optimized output for VeilCore.

    Design principles:
        - Lead with the most critical information
        - Use consistent structure for navigation
        - Announce changes, not static state
        - Keep announcements concise
        - Provide drill-down paths
    """

    def format_system_status(self, status: dict[str, Any]) -> list[ScreenReaderBlock]:
        """Format system status for screen reader."""
        blocks = []

        # System heading
        organs = status.get("organs", {})
        threat = status.get("threats", {})
        threat_level = threat.get("threat_level", "NORMAL")

        # Lead with threat level (most critical info first)
        urgency = "assertive" if threat_level in ("CRITICAL", "HIGH") else "polite"
        blocks.append(ScreenReaderBlock(
            content=f"VeilCore threat level: {threat_level}. "
                    f"{threat.get('active_alerts', 0)} active alerts.",
            role="alert" if urgency == "assertive" else "status",
            urgency=urgency,
            label="Threat Level",
            level=1,
        ))

        # Organ summary
        blocks.append(ScreenReaderBlock(
            content=f"Organs: {organs.get('active', 0)} of {organs.get('total', 0)} active. "
                    f"{organs.get('inactive', 0)} inactive.",
            role="status", urgency="polite",
            label="Organ Status", level=2,
        ))

        # Tier breakdown
        by_tier = organs.get("by_tier", {})
        blocks.append(ScreenReaderBlock(
            content=f"Priority zero critical: {by_tier.get('P0_critical', 0)}. "
                    f"Priority one important: {by_tier.get('P1_important', 0)}. "
                    f"Priority two standard: {by_tier.get('P2_standard', 0)}.",
            role="status", urgency="polite",
            label="Organ Tiers", level=3,
        ))

        return blocks

    def format_alert(self, alert: dict[str, Any]) -> ScreenReaderBlock:
        """Format a single alert for screen reader announcement."""
        severity = alert.get("severity", "info")
        title = alert.get("title", "Unknown alert")
        message = alert.get("message", "")
        source = alert.get("source_organ", "system")

        urgency = "assertive" if severity in ("critical", "high") else "polite"

        # Concise announcement format
        content = (
            f"{'CRITICAL alert' if severity == 'critical' else severity.capitalize() + ' alert'}: "
            f"{title}. {message}. Source: {source}."
        )

        return ScreenReaderBlock(
            content=content,
            role="alert",
            urgency=urgency,
            label=f"{severity.upper()} Alert",
            metadata={"alert_id": alert.get("alert_id", ""), "severity": severity},
        )

    def format_organ_list(self, organs: list[dict[str, Any]]) -> list[ScreenReaderBlock]:
        """Format organ list for screen reader navigation."""
        blocks = []

        blocks.append(ScreenReaderBlock(
            content=f"Organ list. {len(organs)} organs total.",
            role="heading", urgency="polite",
            label="Organ List", level=2,
        ))

        # Group by status for efficiency
        failed = [o for o in organs if o.get("status") in ("failed", "dead")]
        active = [o for o in organs if o.get("active") == "active"]
        inactive = [o for o in organs if o.get("active") != "active"
                    and o.get("status") not in ("failed", "dead")]

        # Failed organs first (most critical)
        if failed:
            blocks.append(ScreenReaderBlock(
                content=f"Warning: {len(failed)} failed organs. " +
                        ", ".join(o.get("name", "unknown") for o in failed) + ".",
                role="alert", urgency="assertive",
                label="Failed Organs", level=3,
            ))

        # Active count
        blocks.append(ScreenReaderBlock(
            content=f"{len(active)} organs running normally.",
            role="status", urgency="polite",
            label="Active Organs", level=3,
        ))

        # Inactive
        if inactive:
            blocks.append(ScreenReaderBlock(
                content=f"{len(inactive)} organs inactive.",
                role="status", urgency="polite",
                label="Inactive Organs", level=3,
            ))

        return blocks

    def format_command_result(self, result: dict[str, Any]) -> ScreenReaderBlock:
        """Format command result for screen reader."""
        status = result.get("status", "unknown")
        command = result.get("command", "unknown")
        message = result.get("message", "")

        if status == "denied":
            content = f"Command denied. {command}: {message}"
            urgency = "assertive"
        elif status == "error":
            content = f"Command error. {command}: {message}"
            urgency = "assertive"
        else:
            content = f"Command completed. {command}: {message}"
            urgency = "polite"

        return ScreenReaderBlock(
            content=content, role="status", urgency=urgency,
            label="Command Result",
        )

    def format_threat_feed(self, threats: list[dict[str, Any]]) -> list[ScreenReaderBlock]:
        """Format threat feed for screen reader."""
        blocks = []

        if not threats:
            blocks.append(ScreenReaderBlock(
                content="No active threats. System secure.",
                role="status", urgency="polite",
                label="Threat Feed",
            ))
            return blocks

        blocks.append(ScreenReaderBlock(
            content=f"Active threat feed. {len(threats)} threats detected.",
            role="alert", urgency="assertive" if len(threats) > 3 else "polite",
            label="Threat Feed", level=2,
        ))

        for i, threat in enumerate(threats[:5], 1):
            blocks.append(ScreenReaderBlock(
                content=f"Threat {i}: {threat.get('title', 'Unknown')}. "
                        f"Severity: {threat.get('severity', 'unknown')}. "
                        f"Source: {threat.get('source_organ', 'system')}.",
                role="log", urgency="polite",
                label=f"Threat {i}",
            ))

        return blocks


class AlertNarrator:
    """
    Converts alerts to natural language narration
    optimized for speech synthesis.

    Handles:
        - Abbreviation expansion (IP → I P, SSH → S S H)
        - Number pronunciation
        - Technical term pronunciation hints
        - Pause insertion for comprehension
    """

    # Technical abbreviations to expand
    EXPANSIONS = {
        "IP": "I P", "SSH": "S S H", "SSL": "S S L", "TLS": "T L S",
        "TCP": "T C P", "UDP": "U D P", "DNS": "D N S", "HTTP": "H T T P",
        "HTTPS": "H T T P S", "FHIR": "fire", "HL7": "H L 7",
        "DICOM": "die-com", "EHR": "E H R", "PHI": "P H I",
        "HIPAA": "hip-ah", "CVSS": "C V S S", "CVE": "C V E",
        "IoMT": "I o M T", "MFA": "M F A", "SSO": "single sign on",
        "API": "A P I", "CPU": "C P U", "RAM": "ram", "OS": "O S",
        "SQL": "sequel", "LDAP": "L dap", "NFC": "N F C",
        "RFID": "R F I D", "TPM": "T P M", "HMAC": "H mac",
        "AES": "A E S", "SHA": "shaw", "RSA": "R S A",
        "IOC": "I O C", "C2": "C 2", "APT": "A P T",
        "ML": "M L", "AI": "A I",
    }

    def narrate_alert(self, alert: dict[str, Any]) -> str:
        """Convert alert to natural speech."""
        severity = alert.get("severity", "info")
        title = alert.get("title", "Unknown alert")
        message = alert.get("message", "")
        source = alert.get("source_organ", "system")

        # Severity preamble
        preambles = {
            "critical": "Attention. Critical security alert.",
            "high": "High priority alert.",
            "medium": "Medium priority notice.",
            "low": "Low priority information.",
            "info": "Information update.",
        }
        preamble = preambles.get(severity, "Alert.")

        # Expand abbreviations
        title = self._expand(title)
        message = self._expand(message)
        source = self._expand(source)

        return f"{preamble} {title}. {message}. Source organ: {source}."

    def narrate_status(self, threat_level: str, active_organs: int,
                       total_organs: int, active_alerts: int) -> str:
        """Create status narration."""
        return (
            f"VeilCore status report. "
            f"Threat level is {threat_level}. "
            f"{active_organs} of {total_organs} organs are running. "
            f"{active_alerts} alerts require attention."
        )

    def _expand(self, text: str) -> str:
        """Expand abbreviations for speech."""
        words = text.split()
        result = []
        for word in words:
            # Strip punctuation for lookup
            clean = word.strip('.,!?;:()[]{}')
            if clean.upper() in self.EXPANSIONS:
                # Preserve punctuation
                suffix = word[len(clean):] if len(word) > len(clean) else ""
                result.append(self.EXPANSIONS[clean.upper()] + suffix)
            else:
                # Expand IP addresses
                if self._is_ip(clean):
                    result.append(clean.replace(".", " dot "))
                else:
                    result.append(word)
        return " ".join(result)

    def _is_ip(self, text: str) -> bool:
        """Check if text looks like an IP address."""
        parts = text.split(".")
        if len(parts) == 4:
            return all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)
        return False
