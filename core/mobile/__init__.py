"""
VeilCore Mobile API
====================
Secure remote monitoring and control interface for VeilCore.

Provides authenticated REST + WebSocket endpoints for:
    - Real-time organ status and health monitoring
    - Push alert delivery with severity routing
    - Remote command execution (authorized operators only)
    - Threat dashboard data feeds
    - Federation status overview
    - ML prediction stream

Security:
    - API key + HMAC request signing
    - Rate limiting per endpoint
    - IP allowlisting (optional)
    - All responses stripped of PHI
    - Audit trail for every command
    - Session tokens with expiry

No patient data ever touches this API.
The Veil protects what matters.

Author: Future Ready
System: VeilCore Hospital Cybersecurity Defense
"""

__version__ = "1.0.0"
__codename__ = "Watchtower"

from core.mobile.api import MobileAPI
from core.mobile.auth import AuthManager, APIToken
from core.mobile.alerts import AlertManager, MobileAlert
from core.mobile.commands import CommandRouter, RemoteCommand
from core.mobile.websocket import WebSocketManager

__all__ = [
    "MobileAPI",
    "AuthManager",
    "APIToken",
    "AlertManager",
    "MobileAlert",
    "CommandRouter",
    "RemoteCommand",
    "WebSocketManager",
]
