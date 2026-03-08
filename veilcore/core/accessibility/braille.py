"""
VeilCore Braille Encoder & Formatter
=======================================
Converts VeilCore output to Grade 1 and Grade 2 Braille
for refreshable Braille displays and embossed output.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("veilcore.accessibility.braille")

# ── Braille Unicode Mapping (Grade 1) ──

BRAILLE_MAP = {
    'a': '⠁', 'b': '⠃', 'c': '⠉', 'd': '⠙', 'e': '⠑',
    'f': '⠋', 'g': '⠛', 'h': '⠓', 'i': '⠊', 'j': '⠚',
    'k': '⠅', 'l': '⠇', 'm': '⠍', 'n': '⠝', 'o': '⠕',
    'p': '⠏', 'q': '⠟', 'r': '⠗', 's': '⠎', 't': '⠞',
    'u': '⠥', 'v': '⠧', 'w': '⠺', 'x': '⠭', 'y': '⠽',
    'z': '⠵',
    '1': '⠼⠁', '2': '⠼⠃', '3': '⠼⠉', '4': '⠼⠙', '5': '⠼⠑',
    '6': '⠼⠋', '7': '⠼⠛', '8': '⠼⠓', '9': '⠼⠊', '0': '⠼⠚',
    ' ': '⠀', '.': '⠲', ',': '⠂', ';': '⠆', ':': '⠒',
    '!': '⠖', '?': '⠦', '-': '⠤', '/': '⠌', '(': '⠐⠣',
    ')': '⠐⠜', '@': '⠈⠁', '#': '⠼', '*': '⠔', '_': '⠸⠤',
    '"': '⠐⠂', "'": '⠄', '&': '⠈⠯', '+': '⠬', '=': '⠐⠶',
    '<': '⠈⠣', '>': '⠈⠜', '[': '⠨⠣', ']': '⠨⠜',
    '{': '⠸⠣', '}': '⠸⠜', '%': '⠸⠴',
    '\n': '\n',
}

BRAILLE_CAPITAL = '⠠'
BRAILLE_NUMBER = '⠼'

# ── Grade 2 Contractions (Security Domain) ──
GRADE2_CONTRACTIONS = {
    'the': '⠮', 'and': '⠯', 'for': '⠿', 'of': '⠷',
    'with': '⠾', 'in': '⠔', 'was': '⠴', 'to': '⠖',
    'but': '⠃', 'not': '⠝', 'you': '⠽', 'that': '⠞',
    'can': '⠉', 'had': '⠓', 'are': '⠜', 'from': '⠋',
    'this': '⠹', 'which': '⠱', 'will': '⠺', 'have': '⠓',
    'alert': '⠁⠇⠞',
    'threat': '⠹⠗⠞',
    'critical': '⠉⠗⠞',
    'ransomware': '⠗⠝⠺',
    'firewall': '⠋⠺⠇',
    'guardian': '⠛⠗⠙',
    'sentinel': '⠎⠝⠞',
    'organ': '⠕⠗⠛',
    'veilcore': '⠧⠉',
    'secure': '⠎⠉⠗',
    'breach': '⠃⠗⠉',
    'malware': '⠍⠺⠗',
    'network': '⠝⠞⠺',
    'patient': '⠏⠞⠝',
    'hospital': '⠓⠎⠏',
    'isolation': '⠊⠎⠇',
}


class DisplayWidth(int, Enum):
    NARROW = 20
    STANDARD = 40
    WIDE = 80


@dataclass
class BrailleOutput:
    lines: list[str] = field(default_factory=list)
    display_width: int = 40
    grade: int = 1
    source: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def total_cells(self) -> int:
        return sum(len(line) for line in self.lines)

    @property
    def line_count(self) -> int:
        return len(self.lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "lines": self.lines, "display_width": self.display_width,
            "grade": self.grade, "source": self.source,
            "total_cells": self.total_cells, "line_count": self.line_count,
            "timestamp": self.timestamp,
        }


class BrailleEncoder:
    """Encodes text to Braille Unicode patterns."""

    def encode(self, text: str, grade: int = 1) -> str:
        if grade == 2:
            return self._encode_grade2(text)
        return self._encode_grade1(text)

    def _encode_grade1(self, text: str) -> str:
        result = []
        for char in text:
            if char.isupper():
                result.append(BRAILLE_CAPITAL)
                result.append(BRAILLE_MAP.get(char.lower(), char))
            elif char.lower() in BRAILLE_MAP:
                result.append(BRAILLE_MAP[char.lower()])
            else:
                result.append(char)
        return ''.join(result)

    def _encode_grade2(self, text: str) -> str:
        words = text.split(' ')
        result = []
        for word in words:
            clean = word.lower().strip('.,!?;:()[]{}')
            punctuation_after = ''
            if word and word[-1] in '.,!?;:':
                punctuation_after = BRAILLE_MAP.get(word[-1], word[-1])

            if clean in GRADE2_CONTRACTIONS:
                if word and word[0].isupper():
                    result.append(BRAILLE_CAPITAL + GRADE2_CONTRACTIONS[clean])
                else:
                    result.append(GRADE2_CONTRACTIONS[clean])
            else:
                result.append(self._encode_grade1(word))

            if punctuation_after:
                result.append(punctuation_after)

        return '⠀'.join(result)

    def decode_to_text(self, braille: str) -> str:
        reverse_map = {v: k for k, v in BRAILLE_MAP.items() if len(v) == 1}
        result = []
        capitalize_next = False
        for char in braille:
            if char == BRAILLE_CAPITAL:
                capitalize_next = True
                continue
            decoded = reverse_map.get(char, char)
            if capitalize_next:
                decoded = decoded.upper()
                capitalize_next = False
            result.append(decoded)
        return ''.join(result)


class BrailleFormatter:
    """Formats VeilCore data for Braille displays."""

    def __init__(self, display_width: int = 40, grade: int = 1):
        self._encoder = BrailleEncoder()
        self._width = display_width
        self._grade = grade

    def format_alert(self, title: str, message: str, severity: str,
                     source: str = "") -> BrailleOutput:
        severity_prefix = {
            "critical": "⠿⠿⠿",
            "high":     "⠿⠿⠀",
            "medium":   "⠿⠀⠀",
            "low":      "⠤⠀⠀",
            "info":     "⠊⠀⠀",
        }

        prefix = severity_prefix.get(severity, "⠀⠀⠀")
        lines = []

        lines.append(prefix + "⠀" + self._encoder.encode(severity.upper(), self._grade))
        title_braille = self._encoder.encode(title, self._grade)
        lines.extend(self._wrap(title_braille))
        lines.append("⠤" * min(self._width, 20))
        msg_braille = self._encoder.encode(message, self._grade)
        lines.extend(self._wrap(msg_braille))

        if source:
            source_line = self._encoder.encode(f"Source: {source}", self._grade)
            lines.append(source_line)

        return BrailleOutput(
            lines=lines, display_width=self._width,
            grade=self._grade, source="alert",
        )

    def format_organ_status(self, organs: list[dict[str, Any]]) -> BrailleOutput:
        lines = []
        header = self._encoder.encode("ORGAN STATUS", self._grade)
        lines.append(header)
        lines.append("⠤" * min(self._width, 20))

        for organ in organs:
            name = organ.get("name", "unknown")
            status = organ.get("status", "unknown")
            tier = organ.get("tier", "P2")

            if status in ("running", "active"):
                indicator = "⠿"
            elif status in ("failed", "dead"):
                indicator = "⠿⠿⠿"
            else:
                indicator = "⠤"

            line = f"{indicator}⠀{self._encoder.encode(f'{name} [{tier}] {status}', self._grade)}"
            lines.extend(self._wrap(line))

        return BrailleOutput(
            lines=lines, display_width=self._width,
            grade=self._grade, source="organ_status",
        )

    def format_threat_summary(self, threat_level: str, active_count: int,
                              top_threats: list[str]) -> BrailleOutput:
        lines = []

        level_indicators = {
            "CRITICAL": "⠿⠿⠿⠿⠿",
            "HIGH": "⠿⠿⠿⠀⠀",
            "ELEVATED": "⠿⠿⠀⠀⠀",
            "NORMAL": "⠿⠀⠀⠀⠀",
        }
        indicator = level_indicators.get(threat_level, "⠀⠀⠀⠀⠀")

        lines.append(indicator + "⠀" + self._encoder.encode(f"THREAT: {threat_level}", self._grade))
        lines.append(self._encoder.encode(f"Active: {active_count}", self._grade))
        lines.append("⠤" * min(self._width, 20))

        for i, threat in enumerate(top_threats[:5], 1):
            line = self._encoder.encode(f"{i}. {threat}", self._grade)
            lines.extend(self._wrap(line))

        return BrailleOutput(
            lines=lines, display_width=self._width,
            grade=self._grade, source="threat_summary",
        )

    def format_text(self, text: str) -> BrailleOutput:
        braille = self._encoder.encode(text, self._grade)
        lines = self._wrap(braille)
        return BrailleOutput(
            lines=lines, display_width=self._width,
            grade=self._grade, source="text",
        )

    def _wrap(self, text: str) -> list[str]:
        if len(text) <= self._width:
            return [text]
        lines = []
        while text:
            lines.append(text[:self._width])
            text = text[self._width:]
        return lines

    @property
    def display_width(self) -> int:
        return self._width

    @display_width.setter
    def display_width(self, width: int) -> None:
        self._width = width
