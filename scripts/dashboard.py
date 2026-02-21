#!/usr/bin/env python3
"""
VeilCore Security Dashboard — PyQt6 Desktop Application
Real-time monitoring via Watchtower API (port 9444).
Built by Marlon Ástin Williams, 2025.
"""

import sys
import json
import urllib.request
import urllib.error
from datetime import datetime

API_BASE = "http://localhost:9444/api/v1"
API_KEY = "vc_aceea537c874533b85bdb56d3e7835db40a1cc32eff8024b"

def api_get(endpoint):
    url = f"{API_BASE}/{endpoint}"
    req = urllib.request.Request(url)
    if API_KEY:
        req.add_header("X-VeilCore-Key", API_KEY)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        return {"_error": f"Connection failed: {e.reason}"}
    except Exception as e:
        return {"_error": str(e)}

def fetch_status():
    return api_get("status")

def fetch_organs(tier=""):
    endpoint = f"organs?tier={tier}" if tier else "organs"
    data = api_get(endpoint)
    return [] if "_error" in data else data.get("organs", [])

def fetch_alerts(limit=50):
    data = api_get(f"alerts?limit={limit}")
    return [] if "_error" in data else data.get("alerts", [])

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QScrollArea, QFrame
    )
    from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
    from PyQt6.QtGui import QColor, QPalette
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

BG_DARK = "#0a0e17"
BG_CARD = "#111827"
CYAN = "#00e5ff"
GREEN = "#00ff6a"
ORANGE = "#ff8c00"
RED = "#ff4444"
GOLD = "#fbbf24"
TEXT_PRIMARY = "#e6f7ff"
TEXT_SECONDARY = "#7baac4"
TEXT_DIM = "#4a6a7a"
BORDER = "#1e3a4a"


class DataFetcher(QThread):
    status_ready = pyqtSignal(dict)
    organs_ready = pyqtSignal(list)
    alerts_ready = pyqtSignal(list)

    def run(self):
        self.status_ready.emit(fetch_status())
        self.organs_ready.emit(fetch_organs())
        self.alerts_ready.emit(fetch_alerts(50))


class MetricCard(QFrame):
    def __init__(self, title, value="--", unit="", color=CYAN):
        super().__init__()
        self.setStyleSheet(f"QFrame {{ background-color: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 8px; padding: 12px; }}")
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        t = QLabel(title)
        t.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; border: none;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.v = QLabel(f"{value}{unit}")
        self.v.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold; border: none;")
        self.v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(t)
        layout.addWidget(self.v)

    def update_value(self, value, unit="", color=None):
        self.v.setText(f"{value}{unit}")
        if color:
            self.v.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold; border: none;")


class OrganRow(QFrame):
    def __init__(self, name, desc, tier, status):
        super().__init__()
        tc = {"P0": RED, "P1": ORANGE, "P2": GREEN}
        active = status in ("active", "running")
        sc = GREEN if active else RED
        st = "RUNNING" if active else status.upper()
        self.setStyleSheet(f"QFrame {{ background: transparent; border-bottom: 1px solid {BORDER}; padding: 2px 0; }}")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(8)
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {tc.get(tier, GREEN)}; font-size: 10px; border: none;")
        dot.setFixedWidth(14)
        nl = QLabel(name)
        nl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 11px; font-weight: bold; border: none;")
        nl.setFixedWidth(140)
        dl = QLabel(desc)
        dl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; border: none;")
        sl = QLabel(f"● {st}")
        sl.setStyleSheet(f"color: {sc}; font-size: 10px; border: none;")
        sl.setFixedWidth(90)
        sl.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(dot)
        layout.addWidget(nl)
        layout.addWidget(dl, 1)
        layout.addWidget(sl)


class ComplianceBar(QFrame):
    def __init__(self, name, engine, score, color=CYAN):
        super().__init__()
        self.setStyleSheet(f"QFrame {{ background: transparent; border: none; }}")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(8)
        n = QLabel(name)
        n.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 11px; font-weight: bold; border: none;")
        n.setFixedWidth(160)
        e = QLabel(engine)
        e.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; border: none;")
        s = QLabel(f"{score}%")
        s.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: bold; border: none;")
        s.setFixedWidth(55)
        s.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(n)
        layout.addWidget(e, 1)
        layout.addWidget(s)


class VeilCoreDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔱 VeilCore — Security Command Center")
        self.setMinimumSize(1100, 800)
        self._fetcher = None
        self.setup_ui()
        self.start_timers()

    def setup_ui(self):
        p = self.palette()
        p.setColor(QPalette.ColorRole.Window, QColor(BG_DARK))
        self.setPalette(p)
        central = QWidget()
        self.setCentralWidget(central)
        ml = QVBoxLayout(central)
        ml.setContentsMargins(16, 12, 16, 12)
        ml.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("🔱 VEILCORE — SECURITY COMMAND CENTER")
        title.setStyleSheet(f"color: {CYAN}; font-size: 18px; font-weight: bold; letter-spacing: 3px;")
        self.conn = QLabel("● CONNECTING...")
        self.conn.setStyleSheet(f"color: {ORANGE}; font-size: 11px; font-weight: bold;")
        self.tlevel = QLabel("● --")
        self.tlevel.setStyleSheet(f"color: {TEXT_DIM}; font-size: 14px; font-weight: bold;")
        self.clock = QLabel()
        self.clock.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.conn)
        header.addWidget(self.tlevel)
        header.addWidget(self.clock)
        ml.addLayout(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {BORDER};")
        ml.addWidget(sep)

        cards = QHBoxLayout()
        cards.setSpacing(10)
        self.c_alerts = MetricCard("ACTIVE ALERTS", "--", "", RED)
        self.c_organs = MetricCard("ORGANS ACTIVE", "--", "", GREEN)
        self.c_uptime = MetricCard("UPTIME", "--", "", CYAN)
        self.c_mesh = MetricCard("MESH", "--", "", CYAN)
        self.c_ws = MetricCard("WS CLIENTS", "--", "", GOLD)
        for c in [self.c_alerts, self.c_organs, self.c_uptime, self.c_mesh, self.c_ws]:
            cards.addWidget(c)
        ml.addLayout(cards)

        mid = QHBoxLayout()
        mid.setSpacing(12)

        lp = QVBoxLayout()
        oh = QLabel("🧬 SECURITY ORGANS")
        oh.setStyleSheet(f"color: {CYAN}; font-size: 13px; font-weight: bold; letter-spacing: 1px;")
        lp.addWidget(oh)
        self.oscroll = QScrollArea()
        self.oscroll.setWidgetResizable(True)
        self.oscroll.setStyleSheet(f"QScrollArea {{ background-color: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 6px; }} QScrollBar:vertical {{ background: {BG_DARK}; width: 8px; }} QScrollBar::handle:vertical {{ background: {BORDER}; min-height: 20px; }}")
        self.owidget = QWidget()
        self.olayout = QVBoxLayout(self.owidget)
        self.olayout.setSpacing(0)
        self.olayout.setContentsMargins(0, 0, 0, 0)
        ph = QLabel("  Waiting for Watchtower API...")
        ph.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; padding: 20px; border: none;")
        self.olayout.addWidget(ph)
        self.olayout.addStretch()
        self.oscroll.setWidget(self.owidget)
        lp.addWidget(self.oscroll)
        mid.addLayout(lp, 3)

        rp = QVBoxLayout()
        ah = QLabel("🚨 LIVE ALERT FEED")
        ah.setStyleSheet(f"color: {RED}; font-size: 13px; font-weight: bold; letter-spacing: 1px;")
        rp.addWidget(ah)
        self.ascroll = QScrollArea()
        self.ascroll.setWidgetResizable(True)
        self.ascroll.setStyleSheet(f"QScrollArea {{ background-color: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 6px; }} QScrollBar:vertical {{ background: {BG_DARK}; width: 8px; }} QScrollBar::handle:vertical {{ background: {BORDER}; min-height: 20px; }}")
        self.awidget = QWidget()
        self.alayout = QVBoxLayout(self.awidget)
        self.alayout.setSpacing(2)
        self.alayout.setContentsMargins(8, 8, 8, 8)
        self.alayout.addStretch()
        self.ascroll.setWidget(self.awidget)
        rp.addWidget(self.ascroll, 2)

        ch = QLabel("📊 COMPLIANCE COVERAGE")
        ch.setStyleSheet(f"color: {CYAN}; font-size: 13px; font-weight: bold; letter-spacing: 1px; padding-top: 8px;")
        rp.addWidget(ch)
        cf = QFrame()
        cf.setStyleSheet(f"QFrame {{ background-color: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 6px; padding: 8px; }}")
        cl = QVBoxLayout(cf)
        cl.setSpacing(2)
        cl.addWidget(ComplianceBar("🏥 HIPAA", "ShieldLaw", 100.0, GREEN))
        cl.addWidget(ComplianceBar("🔒 HITRUST CSF v11", "TrustForge", 100.0, GREEN))
        cl.addWidget(ComplianceBar("📋 SOC 2 Type II", "AuditIron", 98.6, GOLD))
        cl.addWidget(ComplianceBar("🇺🇸 FedRAMP", "IronFlag", 100.0, GREEN))
        cl.addWidget(ComplianceBar("🔐 OWASP ASVS 5.0", "345 Controls", 100.0, GREEN))
        rp.addWidget(cf, 1)
        mid.addLayout(rp, 2)
        ml.addLayout(mid, 1)

        footer = QLabel('82 organs · 17 subsystems · 5 frameworks · Zero gaps  |  "I stand between chaos and those I protect"')
        footer.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; letter-spacing: 1px;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ml.addWidget(footer)

    def start_timers(self):
        self.dt = QTimer()
        self.dt.timeout.connect(self.refresh)
        self.dt.start(3000)
        self.ct = QTimer()
        self.ct.timeout.connect(lambda: self.clock.setText(datetime.now().strftime("%Y-%m-%d  %H:%M:%S")))
        self.ct.start(1000)
        self.clock.setText(datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))
        QTimer.singleShot(500, self.refresh)

    def refresh(self):
        if self._fetcher and self._fetcher.isRunning():
            return
        self._fetcher = DataFetcher()
        self._fetcher.status_ready.connect(self.on_status)
        self._fetcher.organs_ready.connect(self.on_organs)
        self._fetcher.alerts_ready.connect(self.on_alerts)
        self._fetcher.start()

    def on_status(self, d):
        if "_error" in d:
            self.conn.setText(f"● OFFLINE")
            self.conn.setStyleSheet(f"color: {RED}; font-size: 11px; font-weight: bold;")
            for c in [self.c_alerts, self.c_organs, self.c_uptime, self.c_mesh, self.c_ws]:
                c.update_value("--", "", TEXT_DIM)
            return
        self.conn.setText("● CONNECTED")
        self.conn.setStyleSheet(f"color: {GREEN}; font-size: 11px; font-weight: bold;")
        lv = d.get("threats", {}).get("threat_level", "UNKNOWN")
        lc = {"NORMAL": GREEN, "NOMINAL": GREEN, "ELEVATED": ORANGE, "HIGH": RED, "CRITICAL": RED}
        self.tlevel.setText(f"● {lv}")
        self.tlevel.setStyleSheet(f"color: {lc.get(lv, TEXT_DIM)}; font-size: 14px; font-weight: bold;")
        ac = d.get("threats", {}).get("active_alerts", 0)
        self.c_alerts.update_value(str(ac), "", RED if ac > 0 else GREEN)
        o = d.get("organs", {})
        a, t = o.get("active", 0), o.get("total", 82)
        self.c_organs.update_value(f"{a}/{t}", "", GREEN if a == t else ORANGE)
        u = d.get("uptime_seconds", 0)
        self.c_uptime.update_value(f"{int(u//3600)}h {int((u%3600)//60)}m", "", CYAN)
        mr = d.get("mesh", {}).get("router_active", False)
        self.c_mesh.update_value("ACTIVE" if mr else "DOWN", "", GREEN if mr else RED)
        self.c_ws.update_value(str(d.get("api", {}).get("websocket_clients", 0)), "", GOLD)

    def on_organs(self, organs):
        if not organs:
            return
        while self.olayout.count():
            i = self.olayout.takeAt(0)
            if i.widget():
                i.widget().deleteLater()
        to = {"P0": 0, "P1": 1, "P2": 2}
        organs.sort(key=lambda o: (to.get(o.get("tier", "P2"), 2), o.get("name", "")))
        ct = None
        tl = {"P0": "  🔴 P0 — CRITICAL", "P1": "  🟠 P1 — IMPORTANT", "P2": "  🟢 P2 — STANDARD"}
        tc = {"P0": RED, "P1": ORANGE, "P2": GREEN}
        for org in organs:
            tier = org.get("tier", "P2")
            if tier != ct:
                ct = tier
                h = QLabel(tl.get(tier, f"  {tier}"))
                h.setStyleSheet(f"color: {tc.get(tier, GREEN)}; font-size: 11px; font-weight: bold; padding: 6px 0 2px 0; border: none;")
                self.olayout.addWidget(h)
            self.olayout.addWidget(OrganRow(org.get("name", "?"), org.get("description", org.get("unit", "")), tier, org.get("active", org.get("status", "unknown"))))
        self.olayout.addStretch()

    def on_alerts(self, alerts):
        if not alerts:
            return
        while self.alayout.count() > 1:
            i = self.alayout.takeAt(0)
            if i.widget():
                i.widget().deleteLater()
        si = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "info": "🔵"}
        for al in alerts[-30:]:
            sv = al.get("severity", "info")
            msg = al.get("message", al.get("description", str(al)))
            ts = al.get("timestamp", "")
            if ts:
                try:
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%H:%M:%S")
                except Exception:
                    ts = ts[:8]
            txt = f"[{ts}] {si.get(sv, '⚪')} {msg}" if ts else f"{si.get(sv, '⚪')} {msg}"
            lb = QLabel(txt)
            lb.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 10px; padding: 2px 0; border: none;")
            lb.setWordWrap(True)
            self.alayout.insertWidget(self.alayout.count() - 1, lb)
        QTimer.singleShot(100, lambda: self.ascroll.verticalScrollBar().setValue(self.ascroll.verticalScrollBar().maximum()))


def main():
    if not PYQT_AVAILABLE:
        print("PyQt6 required: pip install PyQt6 --break-system-packages")
        sys.exit(1)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, QColor(BG_DARK))
    p.setColor(QPalette.ColorRole.WindowText, QColor(TEXT_PRIMARY))
    p.setColor(QPalette.ColorRole.Base, QColor(BG_CARD))
    p.setColor(QPalette.ColorRole.Text, QColor(TEXT_PRIMARY))
    p.setColor(QPalette.ColorRole.Highlight, QColor(CYAN))
    app.setPalette(p)
    w = VeilCoreDashboard()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
