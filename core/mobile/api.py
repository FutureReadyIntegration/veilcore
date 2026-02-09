"""
VeilCore Mobile API Server
============================
Async HTTP + WebSocket server for remote VeilCore monitoring.

Endpoints:
    GET  /api/v1/status          — System overview
    GET  /api/v1/organs          — All organ statuses
    GET  /api/v1/organs/{name}   — Single organ detail
    GET  /api/v1/threats         — Active threat feed
    GET  /api/v1/alerts          — Recent alerts
    GET  /api/v1/federation      — Federation status
    GET  /api/v1/ml/predictions  — ML prediction stream
    GET  /api/v1/pentest/latest  — Latest pentest report
    POST /api/v1/commands        — Execute remote command
    GET  /api/v1/mesh/stats      — Mesh network statistics
    WS   /api/v1/ws/live         — Real-time WebSocket feed
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Optional

from aiohttp import web

from core.mobile.auth import AuthManager
from core.mobile.alerts import AlertManager
from core.mobile.commands import CommandRouter
from core.mobile.websocket import WebSocketManager

logger = logging.getLogger("veilcore.mobile.api")


class MobileAPI:
    """
    VeilCore Mobile API Server.

    Usage:
        api = MobileAPI()
        await api.start()
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 9444,
                 enable_websocket: bool = True):
        self.host = host
        self.port = port
        self._app = web.Application(middlewares=[self._auth_middleware])
        self._runner: Optional[web.AppRunner] = None
        self._auth = AuthManager()
        self._alerts = AlertManager()
        self._commands = CommandRouter()
        self._ws_manager = WebSocketManager()
        self._enable_ws = enable_websocket
        self._started_at: Optional[str] = None
        self._request_count = 0
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Register all API routes."""
        self._app.router.add_get("/api/v1/status", self._handle_status)
        self._app.router.add_get("/api/v1/organs", self._handle_organs)
        self._app.router.add_get("/api/v1/organs/{name}", self._handle_organ_detail)
        self._app.router.add_get("/api/v1/threats", self._handle_threats)
        self._app.router.add_get("/api/v1/alerts", self._handle_alerts)
        self._app.router.add_get("/api/v1/federation", self._handle_federation)
        self._app.router.add_get("/api/v1/ml/predictions", self._handle_ml)
        self._app.router.add_get("/api/v1/pentest/latest", self._handle_pentest)
        self._app.router.add_post("/api/v1/commands", self._handle_command)
        self._app.router.add_get("/api/v1/mesh/stats", self._handle_mesh_stats)
        self._app.router.add_get("/api/v1/health", self._handle_health)
        if self._enable_ws:
            self._app.router.add_get("/api/v1/ws/live", self._ws_manager.handle_websocket)

    @web.middleware
    async def _auth_middleware(self, request: web.Request, handler) -> web.Response:
        """Authenticate all requests except health check."""
        self._request_count += 1

        # Health check is unauthenticated
        if request.path == "/api/v1/health":
            return await handler(request)

        # Extract API key
        api_key = request.headers.get("X-VeilCore-Key", "")
        if not api_key:
            api_key = request.query.get("api_key", "")

        if not self._auth.validate_key(api_key):
            logger.warning(f"Unauthorized request from {request.remote}: {request.path}")
            return web.json_response(
                {"error": "unauthorized", "message": "Invalid or missing API key"},
                status=401,
            )

        # Rate limiting
        if not self._auth.check_rate_limit(api_key):
            return web.json_response(
                {"error": "rate_limited", "message": "Too many requests"},
                status=429,
            )

        request["api_key"] = api_key
        request["operator"] = self._auth.get_operator(api_key)
        return await handler(request)

    async def _handle_status(self, request: web.Request) -> web.Response:
        """GET /api/v1/status — System overview."""
        organs = self._get_organ_summary()
        uptime = self._calculate_uptime()

        status = {
            "system": "VeilCore",
            "version": "1.0.0",
            "codename": "The Veil",
            "status": "operational",
            "uptime_seconds": uptime,
            "started_at": self._started_at,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "organs": organs,
            "mesh": self._get_mesh_summary(),
            "threats": {
                "active_alerts": self._alerts.active_count,
                "threat_level": self._calculate_threat_level(),
            },
            "federation": self._get_federation_summary(),
            "api": {
                "total_requests": self._request_count,
                "websocket_clients": self._ws_manager.client_count,
            },
        }
        return web.json_response(status)

    async def _handle_organs(self, request: web.Request) -> web.Response:
        """GET /api/v1/organs — All organ statuses."""
        tier = request.query.get("tier", "")
        status_filter = request.query.get("status", "")

        organs = self._discover_organs()

        if tier:
            organs = [o for o in organs if o.get("tier", "").lower() == tier.lower()]
        if status_filter:
            organs = [o for o in organs if o.get("status", "").lower() == status_filter.lower()]

        return web.json_response({
            "total": len(organs),
            "organs": organs,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def _handle_organ_detail(self, request: web.Request) -> web.Response:
        """GET /api/v1/organs/{name} — Single organ detail."""
        name = request.match_info["name"]
        organs = self._discover_organs()
        organ = next((o for o in organs if o["name"].lower() == name.lower()), None)

        if not organ:
            return web.json_response(
                {"error": "not_found", "message": f"Organ '{name}' not found"},
                status=404,
            )
        return web.json_response(organ)

    async def _handle_threats(self, request: web.Request) -> web.Response:
        """GET /api/v1/threats — Active threat feed."""
        limit = int(request.query.get("limit", "20"))
        severity = request.query.get("severity", "")

        threats = self._get_active_threats(limit, severity)
        return web.json_response({
            "threat_level": self._calculate_threat_level(),
            "active_threats": len(threats),
            "threats": threats,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def _handle_alerts(self, request: web.Request) -> web.Response:
        """GET /api/v1/alerts — Recent alerts."""
        limit = int(request.query.get("limit", "50"))
        alerts = self._alerts.get_recent(limit)
        return web.json_response({
            "total": len(alerts),
            "alerts": [a.to_dict() for a in alerts],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def _handle_federation(self, request: web.Request) -> web.Response:
        """GET /api/v1/federation — Federation status."""
        federation = self._get_federation_summary()
        return web.json_response({
            "federation": federation,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def _handle_ml(self, request: web.Request) -> web.Response:
        """GET /api/v1/ml/predictions — ML prediction data."""
        predictions = self._get_ml_summary()
        return web.json_response({
            "ml_engine": predictions,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def _handle_pentest(self, request: web.Request) -> web.Response:
        """GET /api/v1/pentest/latest — Latest pentest report."""
        report = self._get_latest_pentest()
        return web.json_response({
            "pentest": report,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def _handle_command(self, request: web.Request) -> web.Response:
        """POST /api/v1/commands — Execute remote command."""
        try:
            body = await request.json()
        except Exception:
            return web.json_response(
                {"error": "bad_request", "message": "Invalid JSON body"},
                status=400,
            )

        operator = request.get("operator", "unknown")
        command = body.get("command", "")
        target = body.get("target", "")
        params = body.get("params", {})

        if not command:
            return web.json_response(
                {"error": "bad_request", "message": "Missing 'command' field"},
                status=400,
            )

        result = await self._commands.execute(
            command=command, target=target,
            params=params, operator=operator,
        )

        # Push to WebSocket clients
        if self._enable_ws:
            await self._ws_manager.broadcast({
                "type": "command_executed",
                "command": command,
                "target": target,
                "operator": operator,
                "result": result.to_dict(),
            })

        return web.json_response(result.to_dict())

    async def _handle_mesh_stats(self, request: web.Request) -> web.Response:
        """GET /api/v1/mesh/stats — Mesh network statistics."""
        stats = self._get_mesh_summary()
        return web.json_response({
            "mesh": stats,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def _handle_health(self, request: web.Request) -> web.Response:
        """GET /api/v1/health — Health check (unauthenticated)."""
        return web.json_response({
            "status": "healthy",
            "system": "VeilCore Mobile API",
            "version": "1.0.0",
        })

    # ── Data providers ──

    def _discover_organs(self) -> list[dict[str, Any]]:
        """Discover organ statuses from systemd."""
        import subprocess
        organs = []
        try:
            result = subprocess.run(
                ["systemctl", "list-units", "veilcore-*", "--no-legend", "--plain"],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 4:
                    name = parts[0].replace("veilcore-", "").replace(".service", "")
                    organs.append({
                        "name": name,
                        "unit": parts[0],
                        "load": parts[1],
                        "active": parts[2],
                        "status": parts[3],
                        "tier": self._get_organ_tier(name),
                    })
        except Exception:
            pass

        # If no systemd services found, return catalog
        if not organs:
            from core.mesh.discovery import ORGAN_CATALOG
            for org_id, info in ORGAN_CATALOG.items():
                organs.append({
                    "name": info.get("name", org_id),
                    "unit": f"veilcore-{org_id}.service",
                    "load": "loaded",
                    "active": "inactive",
                    "status": "dead",
                    "tier": info.get("tier", "P2"),
                    "description": info.get("description", ""),
                })
        return organs

    def _get_organ_tier(self, name: str) -> str:
        """Look up organ tier."""
        try:
            from core.mesh.discovery import ORGAN_CATALOG
            for org_id, info in ORGAN_CATALOG.items():
                if org_id == name or info.get("name", "").lower() == name.lower():
                    return info.get("tier", "P2")
        except Exception:
            pass
        return "P2"

    def _get_organ_summary(self) -> dict[str, Any]:
        """Get organ status summary."""
        organs = self._discover_organs()
        active = sum(1 for o in organs if o.get("active") == "active")
        return {
            "total": len(organs),
            "active": active,
            "inactive": len(organs) - active,
            "by_tier": {
                "P0_critical": sum(1 for o in organs if o.get("tier") == "P0"),
                "P1_important": sum(1 for o in organs if o.get("tier") == "P1"),
                "P2_standard": sum(1 for o in organs if o.get("tier") == "P2"),
            },
        }

    def _get_mesh_summary(self) -> dict[str, Any]:
        """Get mesh network summary."""
        socket_path = "/run/veilcore/mesh.sock"
        return {
            "router_active": os.path.exists(socket_path),
            "socket_path": socket_path,
        }

    def _get_federation_summary(self) -> dict[str, Any]:
        """Get federation status."""
        try:
            from core.federation.site import SiteRegistry
            registry = SiteRegistry()
            return registry.summary()
        except Exception:
            return {"status": "not_configured", "total_sites": 0}

    def _get_ml_summary(self) -> dict[str, Any]:
        """Get ML engine status."""
        model_path = "/var/lib/veilcore/models"
        has_anomaly = os.path.exists(os.path.join(model_path, "anomaly_detector.joblib"))
        has_classifier = os.path.exists(os.path.join(model_path, "threat_classifier.joblib"))
        return {
            "anomaly_detector": "loaded" if has_anomaly else "not_found",
            "threat_classifier": "loaded" if has_classifier else "not_found",
            "threat_classes": [
                "benign", "brute_force", "ransomware", "exfiltration",
                "lateral_movement", "insider_threat", "phishing",
                "port_scan", "credential_stuffing", "privilege_escalation",
            ],
            "feature_dimensions": 48,
        }

    def _get_active_threats(self, limit: int = 20, severity: str = "") -> list[dict]:
        """Get active threats from alerts."""
        alerts = self._alerts.get_recent(limit)
        threats = [a.to_dict() for a in alerts if a.severity in ("critical", "high")]
        if severity:
            threats = [t for t in threats if t.get("severity") == severity]
        return threats[:limit]

    def _get_latest_pentest(self) -> dict[str, Any]:
        """Load latest pentest report."""
        report_dir = "/var/lib/veilcore/pentest/reports"
        if not os.path.exists(report_dir):
            return {"status": "no_reports"}
        reports = sorted(
            [f for f in os.listdir(report_dir) if f.endswith(".json")],
            reverse=True,
        )
        if not reports:
            return {"status": "no_reports"}
        try:
            with open(os.path.join(report_dir, reports[0])) as f:
                return json.load(f)
        except Exception:
            return {"status": "error_loading"}

    def _calculate_threat_level(self) -> str:
        """Calculate overall threat level."""
        critical = sum(1 for a in self._alerts.get_recent(100) if a.severity == "critical")
        high = sum(1 for a in self._alerts.get_recent(100) if a.severity == "high")
        if critical > 0:
            return "CRITICAL"
        if high > 2:
            return "HIGH"
        if high > 0:
            return "ELEVATED"
        return "NORMAL"

    def _calculate_uptime(self) -> float:
        """Calculate API uptime in seconds."""
        if not self._started_at:
            return 0.0
        try:
            started = datetime.fromisoformat(self._started_at)
            return (datetime.now(timezone.utc) - started).total_seconds()
        except Exception:
            return 0.0

    # ── Server lifecycle ──

    async def start(self) -> None:
        """Start the Mobile API server."""
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self.host, self.port)
        await site.start()

        logger.info("╔══════════════════════════════════════════════════╗")
        logger.info("║    VEILCORE MOBILE API — WATCHTOWER ONLINE      ║")
        logger.info("║    Remote monitoring. Secure command. No PHI.    ║")
        logger.info("╚══════════════════════════════════════════════════╝")
        logger.info(f"Listening on {self.host}:{self.port}")
        logger.info(f"WebSocket: {'enabled' if self._enable_ws else 'disabled'}")

    async def stop(self) -> None:
        """Stop the Mobile API server."""
        if self._runner:
            await self._runner.cleanup()
        logger.info("Mobile API stopped.")

    async def __aenter__(self) -> MobileAPI:
        await self.start()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.stop()

    @property
    def auth_manager(self) -> AuthManager:
        return self._auth

    @property
    def alert_manager(self) -> AlertManager:
        return self._alerts

    @property
    def command_router(self) -> CommandRouter:
        return self._commands

    @property
    def ws_manager(self) -> WebSocketManager:
        return self._ws_manager

    @property
    def app(self) -> web.Application:
        return self._app
