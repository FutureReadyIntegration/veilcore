#!/usr/bin/env python3
"""
VeilCore API Gateway  v0.3.0
────────────────────────────────────────────────────────────────
Zero-dependency HTTP server (stdlib only).
Serves  GET /health   and   GET /organs   on port 9444.
The VeilOS Desktop polls both endpoints via SharedApiPoller.

Usage:
    python3 veilcore_gateway.py              # foreground
    python3 veilcore_gateway.py --daemon     # background (writes PID to ~/.config/veilcore/gateway.pid)
    python3 veilcore_gateway.py --stop       # kills running daemon

(c) 2025-2026 FutureReadyIntegration — Apache 2.0
"""

import json, os, sys, time, signal, random, hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────
PORT        = int(os.environ.get("VEIL_PORT", 9444))
API_KEY     = os.environ.get("VEIL_API_KEY",
                             "vc_aceea537c874533b85bdb56d3e7835db40a1cc32eff8024b")
VERSION     = "0.3.0"
PID_DIR     = Path.home() / ".config" / "veilcore"
PID_FILE    = PID_DIR / "gateway.pid"
START_TIME  = time.time()

# ── Organ Registry ──────────────────────────────────────────────────
# 14 P0  +  14 P1  +  54 P2  =  82 total
P0_ORGANS = [
    ("Guardian",            "Authentication gateway — the front door to everything",                "auth"),
    ("Sentinel",            "Behavioral anomaly detection across all systems",                      "detection"),
    ("Cortex",              "Central intelligence — correlates data from all organs",               "intelligence"),
    ("Audit",               "Comprehensive security audit logging",                                 "logging"),
    ("Chronicle",           "Immutable event history and forensic timeline",                        "logging"),
    ("Insider Threat",      "Detects privilege abuse and data exfiltration",                        "detection"),
    ("PHI Classifier",      "Identifies and tags Protected Health Information",                     "compliance"),
    ("Encryption Enforcer", "Ensures data-at-rest and data-in-transit encryption",                  "encryption"),
    ("Watchdog",            "System health monitoring and heartbeat verification",                  "monitoring"),
    ("Firewall",            "Network perimeter defense and traffic filtering",                      "network"),
    ("Backup",              "Automated encrypted backups with integrity verification",              "recovery"),
    ("Quarantine",          "Threat isolation and containment",                                     "response"),
    ("Vault",               "Secrets management and credential storage",                            "encryption"),
    ("MFA",                 "Multi-factor authentication enforcement",                              "auth"),
]

P1_ORGANS = [
    ("RBAC",                "Role-based access control enforcement",                                "auth"),
    ("Host Sensor",         "Endpoint detection on every connected device",                         "detection"),
    ("Network Monitor",     "Real-time network traffic analysis",                                   "monitoring"),
    ("Threat Intel",        "External threat intelligence feed integration",                        "intelligence"),
    ("PHI Guard",           "PHI access monitoring and leak prevention",                            "compliance"),
    ("Epic Connector",      "Epic EHR integration and protection layer",                            "integration"),
    ("Imprivata Bridge",    "Imprivata SSO authentication bridge",                                  "integration"),
    ("HL7 Filter",          "HL7 message inspection and sanitization",                              "integration"),
    ("FHIR Gateway",        "FHIR API security gateway",                                           "integration"),
    ("DICOM Shield",        "Medical imaging data protection",                                      "integration"),
    ("IoMT Protector",      "Internet of Medical Things device security",                           "detection"),
    ("Canary",              "Honeypot deployment and early warning",                                "detection"),
    ("Scanner",             "Vulnerability and configuration scanning",                             "scanning"),
    ("Patcher",             "Automated security patch deployment",                                  "maintenance"),
]

P2_ORGANS = [
    ("Encryptor",           "File and volume encryption services",                                  "encryption"),
    ("DLP Engine",          "Data loss prevention scanning",                                        "compliance"),
    ("Behavioral Analysis", "Deep behavioral pattern modeling",                                     "detection"),
    ("Anomaly Detector",    "Statistical anomaly detection engine",                                 "detection"),
    ("VPN Manager",         "Secure tunnel management",                                             "network"),
    ("Certificate Authority","Internal PKI and certificate lifecycle",                              "encryption"),
    ("Key Manager",         "Cryptographic key management",                                         "encryption"),
    ("Session Monitor",     "Active session tracking and timeout enforcement",                      "monitoring"),
    ("Compliance Engine",   "Continuous compliance verification",                                   "compliance"),
    ("Risk Analyzer",       "Quantitative risk scoring",                                            "intelligence"),
    ("Forensic Collector",  "Evidence collection and chain-of-custody",                             "logging"),
    ("Incident Responder",  "Automated incident response playbooks",                                "response"),
    ("Malware Detector",    "Signature and heuristic malware detection",                            "detection"),
    ("Ransomware Shield",   "Ransomware-specific behavioral detection",                             "detection"),
    ("Zero Trust Engine",   "Continuous verification and device posture",                           "auth"),
    ("Micro-segmentation",  "Network micro-segmentation enforcement",                               "network"),
    ("API Gateway",         "API traffic management and security",                                  "network"),
    ("Load Balancer",       "Service load distribution",                                            "network"),
    ("WAF",                 "Web application firewall",                                             "network"),
    ("IDS/IPS",             "Intrusion detection and prevention",                                   "detection"),
    ("SIEM Connector",      "Security event management integration",                                "integration"),
    ("Log Aggregator",      "Centralized log collection",                                           "logging"),
    ("Metrics Collector",   "System and security metrics aggregation",                              "monitoring"),
    ("Alert Manager",       "Alert routing, dedup, and escalation",                                 "response"),
    ("Notification Engine", "Multi-channel notification delivery",                                  "response"),
    ("Email Gateway",       "Email security scanning and filtering",                                "network"),
    ("SMS Notifier",        "SMS-based critical alert delivery",                                    "response"),
    ("Webhook Handler",     "External webhook integration",                                         "integration"),
    ("DNS Filter",          "DNS-level threat filtering",                                           "network"),
    ("Web Proxy",           "Secure web proxy with content inspection",                             "network"),
    ("Content Filter",      "Content classification and filtering",                                 "compliance"),
    ("SSL Inspector",       "TLS/SSL traffic inspection",                                           "encryption"),
    ("Traffic Shaper",      "Network traffic prioritization",                                       "network"),
    ("Bandwidth Monitor",   "Bandwidth usage tracking and alerting",                                "monitoring"),
    ("Port Scanner",        "Network port discovery and monitoring",                                "scanning"),
    ("Vulnerability Scanner","Continuous vulnerability assessment",                                 "scanning"),
    ("Patch Manager",       "Patch tracking and deployment scheduling",                             "maintenance"),
    ("Config Auditor",      "Configuration drift detection",                                        "compliance"),
    ("Baseline Monitor",    "System baseline comparison",                                           "monitoring"),
    ("Integrity Checker",   "File and system integrity verification",                               "compliance"),
    ("File Monitor",        "Real-time file change detection",                                      "monitoring"),
    ("Registry Watcher",    "System registry monitoring",                                           "monitoring"),
    ("Process Monitor",     "Running process analysis and control",                                 "monitoring"),
    ("Service Guardian",    "Service availability and restart management",                          "maintenance"),
    ("Resource Limiter",    "Resource consumption limits and throttling",                            "maintenance"),
    ("Performance Monitor", "System performance tracking",                                          "monitoring"),
    ("Health Checker",      "Component health verification",                                        "monitoring"),
    ("Uptime Tracker",      "Service uptime SLA monitoring",                                        "monitoring"),
    ("Disaster Recovery",   "DR plan execution and testing",                                        "recovery"),
    ("Snapshot Manager",    "System state snapshots",                                               "recovery"),
    ("Replication Engine",  "Data replication across sites",                                         "recovery"),
    ("Failover Controller", "Automated failover orchestration",                                     "recovery"),
    ("Backup Validator",    "Backup integrity and restore testing",                                 "recovery"),
    ("Compliance Tracker",  "Compliance status dashboard and reporting",                             "compliance"),
]


def _build_organ_list():
    """Build the canonical 82-organ list with stable fake PIDs."""
    organs = []
    pid_base = 4400
    for i, (name, desc, cat) in enumerate(P0_ORGANS):
        organs.append({
            "name": name, "tier": "P0", "active": True,
            "type": cat, "description": desc,
            "pid": pid_base + i, "enabled": True, "status": "running",
        })
    pid_base += len(P0_ORGANS)
    for i, (name, desc, cat) in enumerate(P1_ORGANS):
        organs.append({
            "name": name, "tier": "P1", "active": True,
            "type": cat, "description": desc,
            "pid": pid_base + i, "enabled": True, "status": "running",
        })
    pid_base += len(P1_ORGANS)
    for i, (name, desc, cat) in enumerate(P2_ORGANS):
        organs.append({
            "name": name, "tier": "P2", "active": True,
            "type": cat, "description": desc,
            "pid": pid_base + i, "enabled": True, "status": "running",
        })
    return organs


ORGAN_LIST = _build_organ_list()
assert len(ORGAN_LIST) == 82, f"Expected 82 organs, got {len(ORGAN_LIST)}"


# ── Request Handler ─────────────────────────────────────────────────
class VeilHandler(BaseHTTPRequestHandler):
    """Minimal REST handler for the two endpoints the desktop needs."""

    def log_message(self, fmt, *args):
        ts = datetime.now().strftime("%H:%M:%S")
        sys.stderr.write(f"  [{ts}] {fmt % args}\n")

    def _send_json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _check_key(self):
        """Validate API key if one is configured. Returns True if OK."""
        if not API_KEY:
            return True
        client_key = self.headers.get("X-API-Key", "")
        if client_key == API_KEY:
            return True
        self._send_json({"error": "unauthorized"}, 401)
        return False

    def do_GET(self):
        path = self.path.rstrip("/").split("?")[0]

        if path == "/health":
            if not self._check_key():
                return
            uptime_s = int(time.time() - START_TIME)
            self._send_json({
                "status":    "ok",
                "version":   VERSION,
                "msos_ok":   True,
                "uptime":    uptime_s,
                "organs":    len(ORGAN_LIST),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        elif path == "/organs":
            if not self._check_key():
                return
            self._send_json({"organs": ORGAN_LIST})

        elif path == "/invoke":
            # Placeholder — the desktop doesn't call this yet
            self._send_json({"error": "invoke requires POST"}, 405)

        elif path == "/" or path == "":
            self._send_json({
                "service": "VeilCore Gateway",
                "version": VERSION,
                "endpoints": ["/health", "/organs", "/invoke"],
            })
        else:
            self._send_json({"error": "not found"}, 404)

    def do_OPTIONS(self):
        """CORS preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "X-API-Key, Content-Type")
        self.end_headers()


# ── Daemon helpers ──────────────────────────────────────────────────
def _write_pid():
    PID_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))

def _read_pid():
    try:
        return int(PID_FILE.read_text().strip())
    except Exception:
        return None

def _stop_daemon():
    pid = _read_pid()
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Stopped gateway (PID {pid})")
        except ProcessLookupError:
            print(f"PID {pid} not running")
        PID_FILE.unlink(missing_ok=True)
    else:
        print("No gateway PID found")


# ── Main ────────────────────────────────────────────────────────────
def main():
    if "--stop" in sys.argv:
        _stop_daemon()
        return

    if "--daemon" in sys.argv:
        if os.fork():
            sys.exit(0)
        os.setsid()
        if os.fork():
            sys.exit(0)
        sys.stdout = open(os.devnull, "w")
        sys.stderr = open(PID_DIR / "gateway.log", "a")

    _write_pid()

    server = HTTPServer(("0.0.0.0", PORT), VeilHandler)
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  VeilCore Gateway  v{VERSION:<40s}║
║  Listening on 0.0.0.0:{PORT:<38}║
║  Organs registered: {len(ORGAN_LIST):<38}║
║  PID: {os.getpid():<52}║
╚══════════════════════════════════════════════════════════════╝
""", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down …")
    finally:
        server.server_close()
        PID_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    main()#!/usr/bin/env python3
"""
VeilCore API Gateway  v0.3.0
────────────────────────────────────────────────────────────────
Zero-dependency HTTP server (stdlib only).
Serves  GET /health   and   GET /organs   on port 9444.
The VeilOS Desktop polls both endpoints via SharedApiPoller.

Usage:
    python3 veilcore_gateway.py              # foreground
    python3 veilcore_gateway.py --daemon     # background (writes PID to ~/.config/veilcore/gateway.pid)
    python3 veilcore_gateway.py --stop       # kills running daemon

(c) 2025-2026 FutureReadyIntegration — Apache 2.0
"""

import json, os, sys, time, signal, random, hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────
PORT        = int(os.environ.get("VEIL_PORT", 9444))
API_KEY     = os.environ.get("VEIL_API_KEY",
                             "vc_aceea537c874533b85bdb56d3e7835db40a1cc32eff8024b")
VERSION     = "0.3.0"
PID_DIR     = Path.home() / ".config" / "veilcore"
PID_FILE    = PID_DIR / "gateway.pid"
START_TIME  = time.time()

# ── Organ Registry ──────────────────────────────────────────────────
# 14 P0  +  14 P1  +  54 P2  =  82 total
P0_ORGANS = [
    ("Guardian",            "Authentication gateway — the front door to everything",                "auth"),
    ("Sentinel",            "Behavioral anomaly detection across all systems",                      "detection"),
    ("Cortex",              "Central intelligence — correlates data from all organs",               "intelligence"),
    ("Audit",               "Comprehensive security audit logging",                                 "logging"),
    ("Chronicle",           "Immutable event history and forensic timeline",                        "logging"),
    ("Insider Threat",      "Detects privilege abuse and data exfiltration",                        "detection"),
    ("PHI Classifier",      "Identifies and tags Protected Health Information",                     "compliance"),
    ("Encryption Enforcer", "Ensures data-at-rest and data-in-transit encryption",                  "encryption"),
    ("Watchdog",            "System health monitoring and heartbeat verification",                  "monitoring"),
    ("Firewall",            "Network perimeter defense and traffic filtering",                      "network"),
    ("Backup",              "Automated encrypted backups with integrity verification",              "recovery"),
    ("Quarantine",          "Threat isolation and containment",                                     "response"),
    ("Vault",               "Secrets management and credential storage",                            "encryption"),
    ("MFA",                 "Multi-factor authentication enforcement",                              "auth"),
]

P1_ORGANS = [
    ("RBAC",                "Role-based access control enforcement",                                "auth"),
    ("Host Sensor",         "Endpoint detection on every connected device",                         "detection"),
    ("Network Monitor",     "Real-time network traffic analysis",                                   "monitoring"),
    ("Threat Intel",        "External threat intelligence feed integration",                        "intelligence"),
    ("PHI Guard",           "PHI access monitoring and leak prevention",                            "compliance"),
    ("Epic Connector",      "Epic EHR integration and protection layer",                            "integration"),
    ("Imprivata Bridge",    "Imprivata SSO authentication bridge",                                  "integration"),
    ("HL7 Filter",          "HL7 message inspection and sanitization",                              "integration"),
    ("FHIR Gateway",        "FHIR API security gateway",                                           "integration"),
    ("DICOM Shield",        "Medical imaging data protection",                                      "integration"),
    ("IoMT Protector",      "Internet of Medical Things device security",                           "detection"),
    ("Canary",              "Honeypot deployment and early warning",                                "detection"),
    ("Scanner",             "Vulnerability and configuration scanning",                             "scanning"),
    ("Patcher",             "Automated security patch deployment",                                  "maintenance"),
]

P2_ORGANS = [
    ("Encryptor",           "File and volume encryption services",                                  "encryption"),
    ("DLP Engine",          "Data loss prevention scanning",                                        "compliance"),
    ("Behavioral Analysis", "Deep behavioral pattern modeling",                                     "detection"),
    ("Anomaly Detector",    "Statistical anomaly detection engine",                                 "detection"),
    ("VPN Manager",         "Secure tunnel management",                                             "network"),
    ("Certificate Authority","Internal PKI and certificate lifecycle",                              "encryption"),
    ("Key Manager",         "Cryptographic key management",                                         "encryption"),
    ("Session Monitor",     "Active session tracking and timeout enforcement",                      "monitoring"),
    ("Compliance Engine",   "Continuous compliance verification",                                   "compliance"),
    ("Risk Analyzer",       "Quantitative risk scoring",                                            "intelligence"),
    ("Forensic Collector",  "Evidence collection and chain-of-custody",                             "logging"),
    ("Incident Responder",  "Automated incident response playbooks",                                "response"),
    ("Malware Detector",    "Signature and heuristic malware detection",                            "detection"),
    ("Ransomware Shield",   "Ransomware-specific behavioral detection",                             "detection"),
    ("Zero Trust Engine",   "Continuous verification and device posture",                           "auth"),
    ("Micro-segmentation",  "Network micro-segmentation enforcement",                               "network"),
    ("API Gateway",         "API traffic management and security",                                  "network"),
    ("Load Balancer",       "Service load distribution",                                            "network"),
    ("WAF",                 "Web application firewall",                                             "network"),
    ("IDS/IPS",             "Intrusion detection and prevention",                                   "detection"),
    ("SIEM Connector",      "Security event management integration",                                "integration"),
    ("Log Aggregator",      "Centralized log collection",                                           "logging"),
    ("Metrics Collector",   "System and security metrics aggregation",                              "monitoring"),
    ("Alert Manager",       "Alert routing, dedup, and escalation",                                 "response"),
    ("Notification Engine", "Multi-channel notification delivery",                                  "response"),
    ("Email Gateway",       "Email security scanning and filtering",                                "network"),
    ("SMS Notifier",        "SMS-based critical alert delivery",                                    "response"),
    ("Webhook Handler",     "External webhook integration",                                         "integration"),
    ("DNS Filter",          "DNS-level threat filtering",                                           "network"),
    ("Web Proxy",           "Secure web proxy with content inspection",                             "network"),
    ("Content Filter",      "Content classification and filtering",                                 "compliance"),
    ("SSL Inspector",       "TLS/SSL traffic inspection",                                           "encryption"),
    ("Traffic Shaper",      "Network traffic prioritization",                                       "network"),
    ("Bandwidth Monitor",   "Bandwidth usage tracking and alerting",                                "monitoring"),
    ("Port Scanner",        "Network port discovery and monitoring",                                "scanning"),
    ("Vulnerability Scanner","Continuous vulnerability assessment",                                 "scanning"),
    ("Patch Manager",       "Patch tracking and deployment scheduling",                             "maintenance"),
    ("Config Auditor",      "Configuration drift detection",                                        "compliance"),
    ("Baseline Monitor",    "System baseline comparison",                                           "monitoring"),
    ("Integrity Checker",   "File and system integrity verification",                               "compliance"),
    ("File Monitor",        "Real-time file change detection",                                      "monitoring"),
    ("Registry Watcher",    "System registry monitoring",                                           "monitoring"),
    ("Process Monitor",     "Running process analysis and control",                                 "monitoring"),
    ("Service Guardian",    "Service availability and restart management",                          "maintenance"),
    ("Resource Limiter",    "Resource consumption limits and throttling",                            "maintenance"),
    ("Performance Monitor", "System performance tracking",                                          "monitoring"),
    ("Health Checker",      "Component health verification",                                        "monitoring"),
    ("Uptime Tracker",      "Service uptime SLA monitoring",                                        "monitoring"),
    ("Disaster Recovery",   "DR plan execution and testing",                                        "recovery"),
    ("Snapshot Manager",    "System state snapshots",                                               "recovery"),
    ("Replication Engine",  "Data replication across sites",                                         "recovery"),
    ("Failover Controller", "Automated failover orchestration",                                     "recovery"),
    ("Backup Validator",    "Backup integrity and restore testing",                                 "recovery"),
    ("Compliance Tracker",  "Compliance status dashboard and reporting",                             "compliance"),
]


def _build_organ_list():
    """Build the canonical 82-organ list with stable fake PIDs."""
    organs = []
    pid_base = 4400
    for i, (name, desc, cat) in enumerate(P0_ORGANS):
        organs.append({
            "name": name, "tier": "P0", "active": True,
            "type": cat, "description": desc,
            "pid": pid_base + i, "enabled": True, "status": "running",
        })
    pid_base += len(P0_ORGANS)
    for i, (name, desc, cat) in enumerate(P1_ORGANS):
        organs.append({
            "name": name, "tier": "P1", "active": True,
            "type": cat, "description": desc,
            "pid": pid_base + i, "enabled": True, "status": "running",
        })
    pid_base += len(P1_ORGANS)
    for i, (name, desc, cat) in enumerate(P2_ORGANS):
        organs.append({
            "name": name, "tier": "P2", "active": True,
            "type": cat, "description": desc,
            "pid": pid_base + i, "enabled": True, "status": "running",
        })
    return organs


ORGAN_LIST = _build_organ_list()
assert len(ORGAN_LIST) == 82, f"Expected 82 organs, got {len(ORGAN_LIST)}"


# ── Request Handler ─────────────────────────────────────────────────
class VeilHandler(BaseHTTPRequestHandler):
    """Minimal REST handler for the two endpoints the desktop needs."""

    def log_message(self, fmt, *args):
        ts = datetime.now().strftime("%H:%M:%S")
        sys.stderr.write(f"  [{ts}] {fmt % args}\n")

    def _send_json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _check_key(self):
        """Validate API key if one is configured. Returns True if OK."""
        if not API_KEY:
            return True
        client_key = self.headers.get("X-API-Key", "")
        if client_key == API_KEY:
            return True
        self._send_json({"error": "unauthorized"}, 401)
        return False

    def do_GET(self):
        path = self.path.rstrip("/").split("?")[0]

        if path == "/health":
            if not self._check_key():
                return
            uptime_s = int(time.time() - START_TIME)
            self._send_json({
                "status":    "ok",
                "version":   VERSION,
                "msos_ok":   True,
                "uptime":    uptime_s,
                "organs":    len(ORGAN_LIST),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        elif path == "/organs":
            if not self._check_key():
                return
            self._send_json({"organs": ORGAN_LIST})

        elif path == "/invoke":
            # Placeholder — the desktop doesn't call this yet
            self._send_json({"error": "invoke requires POST"}, 405)

        elif path == "/" or path == "":
            self._send_json({
                "service": "VeilCore Gateway",
                "version": VERSION,
                "endpoints": ["/health", "/organs", "/invoke"],
            })
        else:
            self._send_json({"error": "not found"}, 404)

    def do_OPTIONS(self):
        """CORS preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "X-API-Key, Content-Type")
        self.end_headers()


# ── Daemon helpers ──────────────────────────────────────────────────
def _write_pid():
    PID_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))

def _read_pid():
    try:
        return int(PID_FILE.read_text().strip())
    except Exception:
        return None

def _stop_daemon():
    pid = _read_pid()
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Stopped gateway (PID {pid})")
        except ProcessLookupError:
            print(f"PID {pid} not running")
        PID_FILE.unlink(missing_ok=True)
    else:
        print("No gateway PID found")


# ── Main ────────────────────────────────────────────────────────────
def main():
    if "--stop" in sys.argv:
        _stop_daemon()
        return

    if "--daemon" in sys.argv:
        if os.fork():
            sys.exit(0)
        os.setsid()
        if os.fork():
            sys.exit(0)
        sys.stdout = open(os.devnull, "w")
        sys.stderr = open(PID_DIR / "gateway.log", "a")

    _write_pid()

    server = HTTPServer(("0.0.0.0", PORT), VeilHandler)
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  VeilCore Gateway  v{VERSION:<40s}║
║  Listening on 0.0.0.0:{PORT:<38}║
║  Organs registered: {len(ORGAN_LIST):<38}║
║  PID: {os.getpid():<52}║
╚══════════════════════════════════════════════════════════════╝
""", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down …")
    finally:
        server.server_close()
        PID_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
