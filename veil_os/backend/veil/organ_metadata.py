"""
Veil OS — Organ Metadata

This module defines:
- Tier classification (P0 / P1 / P2)
- Hospital-grade glyphs
- A strict whitelist of known organs

It is designed to be:
- Readable by auditors
- Safe for clinical environments
- Easy to extend without breaking tier logic
"""

from enum import Enum
from typing import Literal


class Tier(str, Enum):
    P0 = "P0"  # Life support — catastrophic if down
    P1 = "P1"  # Primary — core operational backbone
    P2 = "P2"  # Secondary — modular / non-critical


# --- Whitelist of known organs ---------------------------------------------

# This is your explicit, auditable organ whitelist.
# Anything outside this list should be treated as suspicious / unsupported.
ALLOWED_ORGANS = {
    # P0
    "sentinel",

    # P1 — Security & Integrity
    "guardian",
    "audit_log",
    "vault",
    "firewall",

    # P1 — Core Clinical & System Logic
    "hospital",
    "api",
    "engine",
    "cockpit_backend",

    # P1 — Monitoring & Reliability
    "watchdog",
    "scheduler",
    "dispatcher",

    # P1 — Identity & Registry
    "roster",

    # P2 — Secondary / supporting organs (examples)
    "rbac",
    "mail_relay",
    "metrics",
    "telemetry",
    "logger",
    "journal",
    "queue",
    "bridge",
    "gateway",
    "relay",
    "fabric",
    "switch",
    "harbor",
    "inlet",
    "collector",
    "indexer",
    "codec",
    "keystore",
    "entropy",
    "entropy_pool",
    "signal",
    "driver",
    "dock",
    "matrix",
    "patcher",
    "session",
    "socket",
    "spooler",
    "vessel",
    "zombie_sweeper",
    "cockpit_backend",  # already listed as P1, but allowed here for clarity
}


# --- Tier classification ----------------------------------------------------

P0_ORGANS = {
    "sentinel",
}

P1_ORGANS = {
    # Security & Integrity
    "guardian",
    "audit_log",
    "vault",
    "firewall",

    # Core Clinical & System Logic
    "hospital",
    "api",
    "engine",
    "cockpit_backend",

    # Monitoring & Reliability
    "watchdog",
    "scheduler",
    "dispatcher",

    # Identity & Registry
    "roster",
}

# Everything allowed but not in P0/P1 is implicitly P2.
def get_tier(name: str) -> Tier:
    """
    Return the tier for a given organ name.

    P0 — Life support
    P1 — Primary operational backbone
    P2 — Secondary / supporting
    """
    if name in P0_ORGANS:
        return Tier.P0
    if name in P1_ORGANS:
        return Tier.P1
    return Tier.P2


# --- Hospital-grade glyph mapping ------------------------------------------

GLYPHS: dict[str, str] = {
    # P0
    "sentinel": "🛡️",  # perimeter defense / life support

    # P1 — Security & Integrity
    "guardian": "🛡️",     # protection / enforcement
    "audit_log": "📘",     # clinical documentation / records
    "vault": "🔒",         # secure storage
    "firewall": "⛔",      # boundary / block

    # P1 — Core Clinical & System Logic
    "hospital": "🏥",          # clinical engine
    "api": "🔗",               # linkage / interoperability
    "engine": "⚙️",           # core processing
    "cockpit_backend": "🖥️",  # interface engine

    # P1 — Monitoring & Reliability
    "watchdog": "👁️",   # monitoring / observation
    "scheduler": "⏱️",   # timed tasks / rounds
    "dispatcher": "📨",  # routing / messaging

    # P1 — Identity & Registry
    "roster": "🧑‍⚕️",   # staff registry / identity
}


def get_glyph(name: str) -> str:
    """
    Return the glyph for a given organ.

    Falls back to a neutral symbol if unknown,
    which is safer than guessing.
    """
    return GLYPHS.get(name, "◻️")


# --- Safety helpers ---------------------------------------------------------

def is_allowed(name: str) -> bool:
    """
    Enforce a strict whitelist of organs.

    This is a security boundary:
    - prevents arbitrary process names from being treated as valid organs
    - supports auditability and change control
    """
    return name in ALLOWED_ORGANS


def describe_organ(name: str) -> dict[str, str | Tier | bool]:
    """
    Return a standardized description object for templates / APIs.

    This keeps your frontend and logs consistent and auditable.
    """
    return {
        "name": name,
        "tier": get_tier(name),
        "glyph": get_glyph(name),
        "allowed": is_allowed(name),
    }
