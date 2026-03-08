"""
VeilCore Accessibility Engine
================================
Unified accessibility interface that coordinates Braille,
screen reader, and audio systems.

Provides:
    - Automatic output formatting for all accessibility modes
    - Event-driven alert delivery across all channels
    - User preference profiles (display width, grade, verbosity)
    - Integration hooks for the Mobile API and Dashboard
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from core.accessibility.braille import BrailleEncoder, BrailleFormatter, BrailleOutput
from core.accessibility.screen_reader import ScreenReaderOutput, AlertNarrator, ScreenReaderBlock
from core.accessibility.audio import AudioAlertSystem, ToneProfile

logger = logging.getLogger("veilcore.accessibility.engine")

PREFS_PATH = "/var/lib/veilcore/accessibility/preferences.json"


class OutputMode(str, Enum):
    """Accessibility output modes."""
    BRAILLE = "braille"
    SCREEN_READER = "screen_reader"
    AUDIO = "audio"
    ALL = "all"


@dataclass
class AccessibilityPreferences:
    """User accessibility preferences."""
    braille_enabled: bool = True
    braille_grade: int = 1
    braille_display_width: int = 40
    screen_reader_enabled: bool = True
    screen_reader_verbosity: str = "normal"   # brief, normal, verbose
    audio_enabled: bool = True
    audio_volume: float = 0.8
    high_contrast: bool = False
    large_text: bool = False
    text_scale: float = 1.0
    announce_all_alerts: bool = True
    announce_organ_changes: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "braille_enabled": self.braille_enabled,
            "braille_grade": self.braille_grade,
            "braille_display_width": self.braille_display_width,
            "screen_reader_enabled": self.screen_reader_enabled,
            "screen_reader_verbosity": self.screen_reader_verbosity,
            "audio_enabled": self.audio_enabled,
            "audio_volume": self.audio_volume,
            "high_contrast": self.high_contrast,
            "large_text": self.large_text,
            "text_scale": self.text_scale,
            "announce_all_alerts": self.announce_all_alerts,
            "announce_organ_changes": self.announce_organ_changes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AccessibilityPreferences:
        valid = cls.__dataclass_fields__
        return cls(**{k: v for k, v in data.items() if k in valid})


@dataclass
class AccessibleOutput:
    """
    Multi-modal accessible output bundle.
    Contains Braille, screen reader, and audio data
    for a single event or data view.
    """
    braille: Optional[BrailleOutput] = None
    screen_reader: Optional[list[ScreenReaderBlock]] = None
    narration: Optional[str] = None
    audio_tone: Optional[str] = None
    audio_spec: Optional[dict[str, Any]] = None
    source_event: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "braille": self.braille.to_dict() if self.braille else None,
            "screen_reader": [b.to_dict() for b in self.screen_reader] if self.screen_reader else None,
            "narration": self.narration,
            "audio_tone": self.audio_tone,
            "audio_spec": self.audio_spec,
            "source_event": self.source_event,
            "timestamp": self.timestamp,
        }


class AccessibilityEngine:
    """
    Unified accessibility engine for VeilCore.

    Usage:
        engine = AccessibilityEngine()

        # Process an alert
        output = engine.process_alert(alert_dict)

        # Process system status
        output = engine.process_status(status_dict)

        # Process organ list
        output = engine.process_organs(organ_list)

        # Generate all audio alert files
        engine.generate_audio_pack()
    """

    def __init__(self, prefs: Optional[AccessibilityPreferences] = None):
        self._prefs = prefs or self._load_prefs()
        self._braille_encoder = BrailleEncoder()
        self._braille_formatter = BrailleFormatter(
            display_width=self._prefs.braille_display_width,
            grade=self._prefs.braille_grade,
        )
        self._screen_reader = ScreenReaderOutput()
        self._narrator = AlertNarrator()
        self._audio = AudioAlertSystem()
        self._events_processed = 0

    def process_alert(self, alert: dict[str, Any]) -> AccessibleOutput:
        """
        Process an alert through all accessibility channels.

        Args:
            alert: Alert dictionary with title, message, severity, source_organ

        Returns:
            AccessibleOutput with Braille, screen reader, and audio data
        """
        self._events_processed += 1
        severity = alert.get("severity", "info")

        output = AccessibleOutput(source_event="alert")

        # Braille
        if self._prefs.braille_enabled:
            output.braille = self._braille_formatter.format_alert(
                title=alert.get("title", "Alert"),
                message=alert.get("message", ""),
                severity=severity,
                source=alert.get("source_organ", ""),
            )

        # Screen reader
        if self._prefs.screen_reader_enabled:
            block = self._screen_reader.format_alert(alert)
            output.screen_reader = [block]
            output.narration = self._narrator.narrate_alert(alert)

        # Audio
        if self._prefs.audio_enabled:
            output.audio_tone = severity
            output.audio_spec = self._audio.get_web_audio_spec(severity)

        return output

    def process_status(self, status: dict[str, Any]) -> AccessibleOutput:
        """Process system status through all accessibility channels."""
        self._events_processed += 1
        output = AccessibleOutput(source_event="status")

        threat_level = status.get("threats", {}).get("threat_level", "NORMAL")
        organs = status.get("organs", {})
        alerts_count = status.get("threats", {}).get("active_alerts", 0)

        # Braille
        if self._prefs.braille_enabled:
            text = (
                f"VeilCore {threat_level} "
                f"Organs: {organs.get('active', 0)}/{organs.get('total', 0)} "
                f"Alerts: {alerts_count}"
            )
            output.braille = self._braille_formatter.format_text(text)

        # Screen reader
        if self._prefs.screen_reader_enabled:
            output.screen_reader = self._screen_reader.format_system_status(status)
            output.narration = self._narrator.narrate_status(
                threat_level=threat_level,
                active_organs=organs.get("active", 0),
                total_organs=organs.get("total", 0),
                active_alerts=alerts_count,
            )

        # Audio tone based on threat level
        if self._prefs.audio_enabled:
            tone_map = {
                "CRITICAL": "critical", "HIGH": "high",
                "ELEVATED": "medium", "NORMAL": "all_clear",
            }
            tone_name = tone_map.get(threat_level, "info")
            output.audio_tone = tone_name
            output.audio_spec = self._audio.get_web_audio_spec(tone_name)

        return output

    def process_organs(self, organs: list[dict[str, Any]]) -> AccessibleOutput:
        """Process organ list through all accessibility channels."""
        self._events_processed += 1
        output = AccessibleOutput(source_event="organ_list")

        # Braille
        if self._prefs.braille_enabled:
            output.braille = self._braille_formatter.format_organ_status(organs)

        # Screen reader
        if self._prefs.screen_reader_enabled:
            output.screen_reader = self._screen_reader.format_organ_list(organs)

        # Audio if any failures
        failed = [o for o in organs if o.get("status") in ("failed", "dead")]
        if failed and self._prefs.audio_enabled:
            output.audio_tone = "organ_failure"
            output.audio_spec = self._audio.get_web_audio_spec("organ_failure")

        return output

    def process_threats(self, threat_level: str, threats: list[dict[str, Any]]) -> AccessibleOutput:
        """Process threat feed through all accessibility channels."""
        self._events_processed += 1
        output = AccessibleOutput(source_event="threat_feed")

        # Braille
        if self._prefs.braille_enabled:
            top_names = [t.get("title", "Unknown") for t in threats[:5]]
            output.braille = self._braille_formatter.format_threat_summary(
                threat_level=threat_level,
                active_count=len(threats),
                top_threats=top_names,
            )

        # Screen reader
        if self._prefs.screen_reader_enabled:
            output.screen_reader = self._screen_reader.format_threat_feed(threats)

        # Audio
        if self._prefs.audio_enabled and threats:
            max_severity = "info"
            for t in threats:
                sev = t.get("severity", "info")
                if sev == "critical":
                    max_severity = "critical"
                    break
                if sev == "high" and max_severity != "critical":
                    max_severity = "high"
            output.audio_tone = max_severity
            output.audio_spec = self._audio.get_web_audio_spec(max_severity)

        return output

    def process_command_result(self, result: dict[str, Any]) -> AccessibleOutput:
        """Process command result through accessibility channels."""
        self._events_processed += 1
        output = AccessibleOutput(source_event="command_result")

        # Screen reader
        if self._prefs.screen_reader_enabled:
            block = self._screen_reader.format_command_result(result)
            output.screen_reader = [block]
            output.narration = block.content

        # Braille
        if self._prefs.braille_enabled:
            text = f"{result.get('command', '?')}: {result.get('message', '')}"
            output.braille = self._braille_formatter.format_text(text)

        # Audio for errors/denials
        if self._prefs.audio_enabled and result.get("status") in ("error", "denied"):
            output.audio_tone = "high"
            output.audio_spec = self._audio.get_web_audio_spec("high")

        return output

    def generate_audio_pack(self, output_dir: Optional[str] = None) -> dict[str, str]:
        """Generate all WAV alert files."""
        paths = self._audio.generate_all_wavs(output_dir)
        logger.info(f"Generated {len(paths)} audio alert files")
        return paths

    def get_web_audio_pack(self) -> dict[str, dict[str, Any]]:
        """Get all Web Audio API specs for dashboard integration."""
        return self._audio.get_all_web_audio_specs()

    def update_preferences(self, updates: dict[str, Any]) -> None:
        """Update accessibility preferences."""
        for key, value in updates.items():
            if hasattr(self._prefs, key):
                setattr(self._prefs, key, value)

        # Reconfigure formatters
        self._braille_formatter = BrailleFormatter(
            display_width=self._prefs.braille_display_width,
            grade=self._prefs.braille_grade,
        )
        self._save_prefs()

    @property
    def preferences(self) -> AccessibilityPreferences:
        return self._prefs

    @property
    def events_processed(self) -> int:
        return self._events_processed

    def summary(self) -> dict[str, Any]:
        return {
            "engine": "AccessibilityEngine",
            "codename": "EqualShield",
            "version": "1.0.0",
            "events_processed": self._events_processed,
            "preferences": self._prefs.to_dict(),
            "audio_tones_available": len(self._audio.list_tones()),
            "braille_contractions": "grade2" if self._prefs.braille_grade == 2 else "grade1",
        }

    def _load_prefs(self) -> AccessibilityPreferences:
        """Load preferences from disk."""
        if os.path.exists(PREFS_PATH):
            try:
                with open(PREFS_PATH) as f:
                    return AccessibilityPreferences.from_dict(json.load(f))
            except Exception:
                pass
        return AccessibilityPreferences()

    def _save_prefs(self) -> None:
        """Save preferences to disk."""
        try:
            os.makedirs(os.path.dirname(PREFS_PATH), exist_ok=True)
            with open(PREFS_PATH, "w") as f:
                json.dump(self._prefs.to_dict(), f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save preferences: {e}")
