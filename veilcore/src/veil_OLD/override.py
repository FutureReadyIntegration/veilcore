from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

# Phase 1: only manual is “live”. Others come in later milestones.
ALLOWED_METHODS = {"manual"}

GLYPHS = {
    "manual": "🔱",
}

AFFIRMATIONS = {
    "en": "I act with care, traceability, and integrity.",
    "fr": "J’agis avec soin, traçabilité et intégrité.",
}

@dataclass(frozen=True)
class OverridePayload:
    method: str
    lang: str
    reason: str
    glyph: str
    affirmation: str

def build_override_payload(method: str, lang: str, reason: str) -> OverridePayload:
    m = method.strip().lower()
    if m not in ALLOWED_METHODS:
        raise ValueError(f"Unsupported method '{method}'. Phase 1 supports: {sorted(ALLOWED_METHODS)}")

    l = lang.strip().lower()
    if l not in AFFIRMATIONS:
        raise ValueError(f"Unsupported lang '{lang}'. Phase 1 supports: {sorted(AFFIRMATIONS.keys())}")

    glyph = GLYPHS[m]
    affirmation = AFFIRMATIONS[l]

    return OverridePayload(
        method=m,
        lang=l,
        reason=reason.strip(),
        glyph=glyph,
        affirmation=affirmation,
    )

def payload_to_event(p: OverridePayload) -> Dict:
    return {
        "type": "override",
        "method": p.method,
        "lang": p.lang,
        "reason": p.reason,
        "glyph": p.glyph,
        "affirmation": p.affirmation,
        "severity": "standard",  # Phase 2 will add "emergency"
    }
