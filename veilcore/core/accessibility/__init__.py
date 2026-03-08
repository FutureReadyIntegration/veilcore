"""
VeilCore Accessibility Engine
================================
Assistive interface layer for VeilCore operators with
visual impairments or accessibility needs.

Provides:
    - Braille encoding and formatting for refreshable displays
    - Screen reader integration (ARIA-style structured output)
    - Audio alert system with severity-mapped tones
    - Tactile display protocol support
    - High-contrast / large-text dashboard transforms

Every security operator deserves full situational awareness.
The Veil protects everyone — including those who protect it.

No other hospital cybersecurity system has this.
We built it because it's right.

Author: Future Ready
System: VeilCore Hospital Cybersecurity Defense
"""

__version__ = "1.0.0"
__codename__ = "EqualShield"

from core.accessibility.braille import BrailleEncoder, BrailleFormatter
from core.accessibility.screen_reader import ScreenReaderOutput, AlertNarrator
from core.accessibility.audio import AudioAlertSystem, ToneProfile
from core.accessibility.engine import AccessibilityEngine

__all__ = [
    "BrailleEncoder",
    "BrailleFormatter",
    "ScreenReaderOutput",
    "AlertNarrator",
    "AudioAlertSystem",
    "ToneProfile",
    "AccessibilityEngine",
]
