#!/usr/bin/env python3
"""
VeilOS Desktop Environment v2.2.1 (GLOBAL SETTINGS + FIXED SPLASH/DESKTOP FAILOVER)
==================================================================================

Fixes:
  - Fix NameError (VeilOSDesktop always defined before use)
  - Robust logging to ~/.config/veilcore/veilui.log
  - If desktop creation fails after splash, show error on splash + log traceback
  - Compliance Hub / DeepSentinel / RedVeil / Federation Mesh are distinct apps,
    each with their own Settings dialog (module flags) like Command Center.

Built by Marlon Astin Williams, 2025-2026.
"""

import sys
import os
import json
import math
import random
import subprocess
import traceback
import urllib.request
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────
# PyQt6 Imports
# ─────────────────────────────────────────────────────────────────────
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QScrollArea, QFrame, QPushButton, QGridLayout,
        QTextEdit, QLineEdit, QMdiArea, QMdiSubWindow,
        QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
        QMenu, QDialog, QFormLayout, QSpinBox, QCheckBox, QDialogButtonBox,
        QTabWidget,
    )
    from PyQt6.QtCore import (
        Qt, QTimer, QThread, pyqtSignal, QPoint, QPointF, QObject
    )
    from PyQt6.QtGui import (
        QColor, QPalette, QPainter, QBrush, QPen, QFont, QRadialGradient,
        QPainterPath, QKeySequence, QShortcut, QTextCursor
    )
except ImportError:
    print("PyQt6 required: pip install PyQt6 --break-system-packages")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────
# Paths + Logging
# ─────────────────────────────────────────────────────────────────────
GLOBAL_DIR = os.path.join(str(Path.home()), ".config", "veilcore")
GLOBAL_SETTINGS_PATH = os.path.join(GLOBAL_DIR, "global.json")
LOG_PATH = os.path.join(GLOBAL_DIR, "veilui.log")

def _ensure_global_dir():
    os.makedirs(GLOBAL_DIR, exist_ok=True)

def log(msg: str):
    _ensure_global_dir()
    ts = datetime.now().isoformat(timespec="seconds")
    line = f"[{ts}] {msg}"
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    # also stdout for interactive runs
    print(line, flush=True)

def log_exc(prefix: str):
    tb = traceback.format_exc()
    log(prefix)
    for ln in tb.rstrip().splitlines():
        log(ln)

# ─────────────────────────────────────────────────────────────────────
# Defaults
# ─────────────────────────────────────────────────────────────────────
DEFAULT_API_BASE = "http://localhost:9444"
DEFAULT_REFRESH_MS = 4000

def _detect_api_key():
    key = os.environ.get("VEIL_API_KEY", "")
    if key:
        return key
    try:
        out = subprocess.check_output(
            ["systemctl", "show", "-p", "Environment", "veil-api.service"],
            stderr=subprocess.DEVNULL, timeout=3
        ).decode()
        for part in out.split():
            if "VEIL_API_KEY=" in part:
                return part.split("=", 2)[-1].strip('"').strip("'")
    except Exception:
        pass
    return "vc_aceea537c874533b85bdb56d3e7835db40a1cc32eff8024b"

DEFAULT_API_KEY = _detect_api_key()

# Theme
C = {
    "bg": "#0a0e17", "bg2": "#111827", "bg3": "#1a2332", "bg4": "#0d1420",
    "cyan": "#00e5ff", "green": "#00ff6a", "orange": "#ff8c00",
    "red": "#ff4444", "gold": "#fbbf24", "purple": "#a855f7",
    "blue": "#3b82f6", "pink": "#ec4899",
    "text": "#e6f7ff", "text2": "#7baac4", "dim": "#4a6a7a",
    "border": "#1e3a4a", "border2": "#2a4a5a",
}

# ─────────────────────────────────────────────────────────────────────
# Global Settings Manager
# ─────────────────────────────────────────────────────────────────────
def load_global_settings() -> dict:
    _ensure_global_dir()
    if not os.path.exists(GLOBAL_SETTINGS_PATH):
        return {
            "api_base": DEFAULT_API_BASE,
            "api_key": DEFAULT_API_KEY,
            "refresh_ms": DEFAULT_REFRESH_MS,
            "modules": {},
        }
    try:
        with open(GLOBAL_SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
    except Exception:
        data = {}
    data.setdefault("api_base", DEFAULT_API_BASE)
    data.setdefault("api_key", DEFAULT_API_KEY)
    data.setdefault("refresh_ms", DEFAULT_REFRESH_MS)
    data.setdefault("modules", {})
    if not isinstance(data["modules"], dict):
        data["modules"] = {}
    return data

def save_global_settings(data: dict) -> bool:
    _ensure_global_dir()
    try:
        d = dict(data)
        d["saved_at"] = datetime.now().isoformat(timespec="seconds")
        with open(GLOBAL_SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2)
        return True
    except Exception:
        return False

class GlobalSettingsManager(QObject):
    settings_changed = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self._settings = load_global_settings()

    def get(self) -> dict:
        return dict(self._settings)

    def api_base(self) -> str:
        v = str(self._settings.get("api_base") or DEFAULT_API_BASE).strip()
        return v or DEFAULT_API_BASE

    def api_key(self) -> str:
        v = str(self._settings.get("api_key") or DEFAULT_API_KEY).strip()
        return v or DEFAULT_API_KEY

    def refresh_ms(self) -> int:
        try:
            v = int(self._settings.get("refresh_ms") or DEFAULT_REFRESH_MS)
            return max(500, min(60000, v))
        except Exception:
            return DEFAULT_REFRESH_MS

    def module_flags(self, module_id: str, defaults: dict = None) -> dict:
        defaults = defaults or {}
        mods = self._settings.get("modules", {}) or {}
        m = mods.get(module_id, {}) or {}
        flags = m.get("feature_flags", {}) or {}
        merged = dict(defaults)
        if isinstance(flags, dict):
            merged.update(flags)
        return merged

    def update_global(self, *, api_base: str, api_key: str, refresh_ms: int):
        s = dict(self._settings)
        s["api_base"] = (api_base or "").strip() or DEFAULT_API_BASE
        s["api_key"] = (api_key or "").strip() or DEFAULT_API_KEY
        try:
            s["refresh_ms"] = int(refresh_ms)
        except Exception:
            s["refresh_ms"] = DEFAULT_REFRESH_MS
        if save_global_settings(s):
            self._settings = s
            self.settings_changed.emit(self.get())

    def update_module_flags(self, module_id: str, flags: dict):
        s = dict(self._settings)
        mods = dict(s.get("modules", {}) or {})
        m = dict(mods.get(module_id, {}) or {})
        m["feature_flags"] = dict(flags or {})
        mods[module_id] = m
        s["modules"] = mods
        if save_global_settings(s):
            self._settings = s
            self.settings_changed.emit(self.get())

# ─────────────────────────────────────────────────────────────────────
# API (short timeouts)
# ─────────────────────────────────────────────────────────────────────
def api_get(endpoint, base, key):
    url = f"{base}/{endpoint.lstrip('/')}"
    req = urllib.request.Request(url)
    if key:
        req.add_header("X-API-Key", key)
    try:
        with urllib.request.urlopen(req, timeout=2) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"_error": str(e)}

class DataFetcher(QThread):
    health_ready = pyqtSignal(dict)
    organs_ready = pyqtSignal(list)

    def __init__(self, base, key):
        super().__init__()
        self.base = base
        self.key = key

    def run(self):
        self.health_ready.emit(api_get("health", self.base, self.key))
        data = api_get("organs", self.base, self.key)
        if "_error" not in data:
            organs = data.get("organs", [])
            self.organs_ready.emit(organs if isinstance(organs, list) else [])
        else:
            self.organs_ready.emit([])


class SharedApiPoller(QObject):
    """Single poller shared by all apps. One timer, one thread, two signals."""
    health_ready = pyqtSignal(dict)
    organs_ready = pyqtSignal(list)

    def __init__(self, gsm):
        super().__init__()
        self.gsm = gsm
        self._fetcher = None
        self._last_health = {}
        self._last_organs = []

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.poll)
        self._timer.start(gsm.refresh_ms())

        gsm.settings_changed.connect(self._on_settings)
        QTimer.singleShot(300, self.poll)

    def _on_settings(self, _s):
        self._timer.setInterval(self.gsm.refresh_ms())
        self.poll()

    def poll(self):
        if self._fetcher and self._fetcher.isRunning():
            return
        self._fetcher = DataFetcher(self.gsm.api_base(), self.gsm.api_key())
        self._fetcher.health_ready.connect(self._on_health)
        self._fetcher.organs_ready.connect(self._on_organs)
        self._fetcher.start()

    def _on_health(self, d):
        self._last_health = d
        self.health_ready.emit(d)

    def _on_organs(self, organs):
        self._last_organs = organs
        self.organs_ready.emit(organs)

    def last_health(self):
        return dict(self._last_health)

    def last_organs(self):
        return list(self._last_organs)

# ─────────────────────────────────────────────────────────────────────
# Splash Particles
# ─────────────────────────────────────────────────────────────────────
class Particle:
    def __init__(self, x, y):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2, 12)
        self.x, self.y = x, y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.uniform(0.5, 1.0)
        self.decay = random.uniform(0.008, 0.025)
        self.size = random.uniform(2, 6)
        self.color = QColor(random.choice([C["cyan"], C["green"], C["gold"], C["blue"], C["purple"]]))

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.1
        self.vx *= 0.99
        self.life -= self.decay
        return self.life > 0

# ─────────────────────────────────────────────────────────────────────
# Splash Screen (now shows fail text if desktop fails)
# ─────────────────────────────────────────────────────────────────────
class SplashScreen(QWidget):
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background-color: {C['bg']};")
        self.particles = []
        self.phase = 0
        self.alpha = 0.0
        self.text_alpha = 0.0
        self.ring_radius = 0
        self.ring_alpha = 1.0
        self.frame = 0
        self.eye_scale = 0.0
        self.fail_text = ""  # if desktop creation fails

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(16)

        # important: delay sequence until widget is actually shown & sized
        QTimer.singleShot(150, self.start_seq)

    def start_seq(self):
        self.phase = 0
        self.frame = 0
        QTimer.singleShot(850, self.do_explode)
        QTimer.singleShot(1850, self.show_text)
        QTimer.singleShot(3850, self.fade_out)

    def do_explode(self):
        self.phase = 1
        cx, cy = max(1, self.width() // 2), max(1, self.height() // 2)
        for _ in range(220):
            self.particles.append(Particle(cx, cy))
        self.ring_radius = 0
        self.ring_alpha = 1.0

    def show_text(self):
        self.phase = 2

    def fade_out(self):
        self.phase = 3

    def tick(self):
        self.frame += 1
        if self.phase == 0:
            self.eye_scale = min(1.0, self.frame / 50.0)
        if self.phase >= 1:
            self.particles = [p for p in self.particles if p.update()]
            self.ring_radius += 8
            self.ring_alpha = max(0, self.ring_alpha - 0.015)
        if self.phase == 2:
            self.text_alpha = min(1.0, self.text_alpha + 0.03)
        if self.phase == 3:
            self.alpha += 0.02
            if self.alpha >= 1.0:
                self.timer.stop()
                self.finished.emit()
                return
        self.update()

    def set_fail(self, text: str):
        self.fail_text = text
        # stop fade-out so user can read it
        self.phase = 2
        self.text_alpha = 1.0
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        p.fillRect(self.rect(), QColor(C["bg"]))

        # Eye
        if self.phase == 0 and self.eye_scale > 0:
            s = self.eye_scale
            ew, eh = int(120 * s), int(50 * s)
            p.setPen(QPen(QColor(C["cyan"]), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            path = QPainterPath()
            path.moveTo(cx - ew, cy)
            path.cubicTo(cx - ew // 2, cy - eh, cx + ew // 2, cy - eh, cx + ew, cy)
            path.cubicTo(cx + ew // 2, cy + eh, cx - ew // 2, cy + eh, cx - ew, cy)
            p.drawPath(path)

            ir = int(25 * s)
            grad = QRadialGradient(QPointF(cx, cy), ir)
            grad.setColorAt(0, QColor(C["cyan"]))
            grad.setColorAt(0.7, QColor(C["blue"]))
            grad.setColorAt(1, QColor(0, 0, 0, 0))
            p.setBrush(QBrush(grad))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPoint(cx, cy), ir, ir)

        # Ring
        if self.phase >= 1 and self.ring_alpha > 0:
            rc = QColor(C["cyan"])
            rc.setAlphaF(self.ring_alpha * 0.6)
            p.setPen(QPen(rc, 3))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPoint(cx, cy), self.ring_radius, self.ring_radius)

        # Particles
        for pt in self.particles:
            pc = QColor(pt.color)
            pc.setAlphaF(max(0, pt.life))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(pc))
            p.drawEllipse(QPointF(pt.x, pt.y), pt.size, pt.size)

        # Title text
        if self.phase >= 2:
            tc = QColor(C["cyan"])
            tc.setAlphaF(self.text_alpha)
            p.setPen(tc)
            p.setFont(QFont("Monospace", 42, QFont.Weight.Bold))
            p.drawText(self.rect().adjusted(0, -60, 0, 0), Qt.AlignmentFlag.AlignCenter, "V E I L O S")

            sc = QColor(C["text2"])
            sc.setAlphaF(self.text_alpha * 0.9)
            p.setPen(sc)
            p.setFont(QFont("Monospace", 14))
            p.drawText(self.rect().adjusted(0, 30, 0, 0), Qt.AlignmentFlag.AlignCenter,
                       "Hospital Cybersecurity Defense Platform")

        # Failure text overlay
        if self.fail_text:
            p.setPen(QColor(C["red"]))
            p.setFont(QFont("Monospace", 11))
            p.drawText(self.rect().adjusted(60, 120, -60, -60),
                       Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter,
                       self.fail_text)

        # Fade overlay
        if self.phase == 3 and not self.fail_text:
            ov = QColor(C["bg"])
            ov.setAlphaF(min(1.0, self.alpha))
            p.fillRect(self.rect(), ov)
        p.end()

# ─────────────────────────────────────────────────────────────────────
# Toast
# ─────────────────────────────────────────────────────────────────────
class NotificationToast(QFrame):
    def __init__(self, parent, title, message, severity="info", duration=4000):
        super().__init__(parent)
        sev_colors = {
            "critical": C["red"], "high": C["orange"],
            "medium": C["gold"], "low": C["green"], "info": C["cyan"],
        }
        color = sev_colors.get(severity, C["cyan"])
        self.setFixedSize(320, 72)
        self.setStyleSheet(f"""
            QFrame {{
                background: {C['bg2']}; border: 1px solid {color};
                border-left: 4px solid {color}; border-radius: 10px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)
        t = QLabel(title)
        t.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold; border: none;")
        m = QLabel(message)
        m.setStyleSheet(f"color: {C['text2']}; font-size: 10px; border: none;")
        m.setWordWrap(True)
        layout.addWidget(t)
        layout.addWidget(m)
        self.show()
        self.raise_()
        QTimer.singleShot(duration, self._fade)

    def _fade(self):
        self.hide()
        self.deleteLater()

# ─────────────────────────────────────────────────────────────────────
# Desktop Icon
# ─────────────────────────────────────────────────────────────────────
class DesktopIcon(QWidget):
    double_clicked = pyqtSignal()

    def __init__(self, icon_char, label, color):
        super().__init__()
        self.setFixedSize(90, 85)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hovered = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ic = QLabel(icon_char)
        ic.setStyleSheet(f"color: {color}; font-size: 32px; background: transparent;")
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lb = QLabel(label)
        lb.setStyleSheet(f"color: {C['text']}; font-size: 10px; background: transparent;")
        lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lb.setWordWrap(True)
        layout.addWidget(ic)
        layout.addWidget(lb)

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit()

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def paintEvent(self, event):
        if self._hovered:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            c = QColor(C["cyan"])
            c.setAlphaF(0.12)
            p.setBrush(QBrush(c))
            p.setPen(QPen(QColor(C["cyan"]), 1))
            p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 10, 10)
            p.end()

# ─────────────────────────────────────────────────────────────────────
# Global Settings Dialog
# ─────────────────────────────────────────────────────────────────────
class GlobalSettingsDialog(QDialog):
    def __init__(self, gsm, module_id=None, module_title=None,
                 module_accent=None, module_default_flags=None, parent=None):
        super().__init__(parent)
        self.gsm = gsm
        self.module_id = module_id
        self.module_title = module_title or "SYSTEM SETTINGS"
        self.module_accent = module_accent or C["cyan"]
        self.module_default_flags = module_default_flags or {}
        self.flag_widgets = {}

        self.setModal(True)
        self.setFixedSize(560, 420)
        self.setWindowTitle(f"{self.module_title} — Settings")
        self.setStyleSheet(f"""
            QDialog {{ background: {C['bg2']}; color: {C['text']}; border: 1px solid {C['border']}; }}
            QLabel {{ border: none; }}
            QLineEdit {{
                background: {C['bg3']}; color: {C['text']};
                border: 1px solid {C['border']}; border-radius: 10px; padding: 7px 10px; font-size: 11px;
            }}
            QSpinBox {{
                background: {C['bg3']}; color: {C['text']};
                border: 1px solid {C['border']}; border-radius: 10px; padding: 4px 10px; font-size: 11px;
            }}
            QCheckBox {{ color: {C['text']}; font-size: 11px; }}
        """)

        s = self.gsm.get()
        ml = QVBoxLayout(self)
        ml.setContentsMargins(14, 12, 14, 12)
        ml.setSpacing(10)

        hdr = QLabel("GLOBAL SETTINGS")
        hdr.setStyleSheet(f"color: {self.module_accent}; font-size: 15px; font-weight: bold; letter-spacing: 2px;")
        ml.addWidget(hdr)

        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {C['border']}; border-radius: 12px; }}
            QTabBar::tab {{
                background: {C['bg3']}; color: {C['text2']}; padding: 8px 12px;
                border-top-left-radius: 10px; border-top-right-radius: 10px; margin-right: 4px;
            }}
            QTabBar::tab:selected {{
                background: {C['bg2']}; color: {self.module_accent};
                border: 1px solid {C['border']}; border-bottom: none;
            }}
        """)

        # General
        general = QWidget()
        gl = QVBoxLayout(general)
        gl.setContentsMargins(14, 14, 14, 14)
        gl.setSpacing(10)
        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)

        self.api_base = QLineEdit(str(s.get("api_base") or DEFAULT_API_BASE))
        self.api_base.setPlaceholderText(DEFAULT_API_BASE)
        form.addRow(QLabel("API Endpoint"), self.api_base)

        self.api_key = QLineEdit(str(s.get("api_key") or DEFAULT_API_KEY))
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("vc_*")
        form.addRow(QLabel("API Key"), self.api_key)

        self.refresh_ms = QSpinBox()
        self.refresh_ms.setRange(500, 60000)
        self.refresh_ms.setSingleStep(250)
        self.refresh_ms.setValue(int(s.get("refresh_ms") or DEFAULT_REFRESH_MS))
        form.addRow(QLabel("Default Refresh (ms)"), self.refresh_ms)

        gl.addLayout(form)
        file_note = QLabel(f"File: {GLOBAL_SETTINGS_PATH}")
        file_note.setStyleSheet(f"color: {C['dim']}; font-size: 10px;")
        gl.addWidget(file_note)
        gl.addStretch()
        tabs.addTab(general, "General")

        # Module flags
        if self.module_id:
            mod = QWidget()
            ml2 = QVBoxLayout(mod)
            ml2.setContentsMargins(14, 14, 14, 14)
            ml2.setSpacing(10)
            t = QLabel(f"MODULE FLAGS — {self.module_id}")
            t.setStyleSheet(f"color: {C['text2']}; font-size: 12px; font-weight: bold;")
            ml2.addWidget(t)

            flags = self.gsm.module_flags(self.module_id, self.module_default_flags)
            for k, v in sorted(flags.items()):
                cb = QCheckBox(k)
                cb.setChecked(bool(v))
                self.flag_widgets[k] = cb
                ml2.addWidget(cb)

            ml2.addStretch()
            tabs.addTab(mod, "Module Flags")

        ml.addWidget(tabs, 1)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Reset
        )
        btns.setStyleSheet(f"""
            QDialogButtonBox QPushButton {{
                background: {C['bg3']}; color: {C['text2']};
                border: 1px solid {C['border']}; border-radius: 12px; padding: 7px 16px; font-size: 11px;
            }}
            QDialogButtonBox QPushButton:hover {{
                background: {C['border']}; color: {C['text']}; border-color: {self.module_accent};
            }}
        """)
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        btns.button(QDialogButtonBox.StandardButton.Reset).clicked.connect(self._reset)
        ml.addWidget(btns)

    def _reset(self):
        self.api_base.setText(DEFAULT_API_BASE)
        self.api_key.setText(DEFAULT_API_KEY)
        self.refresh_ms.setValue(DEFAULT_REFRESH_MS)
        for k, cb in self.flag_widgets.items():
            cb.setChecked(bool(self.module_default_flags.get(k, False)))

    def _save(self):
        self.gsm.update_global(
            api_base=self.api_base.text().strip(),
            api_key=self.api_key.text().strip(),
            refresh_ms=int(self.refresh_ms.value())
        )
        if self.module_id and self.flag_widgets:
            flags = {k: bool(cb.isChecked()) for k, cb in self.flag_widgets.items()}
            self.gsm.update_module_flags(self.module_id, flags)
        self.accept()

# ─────────────────────────────────────────────────────────────────────
# Home Screen (quick-launch)
# ─────────────────────────────────────────────────────────────────────
class HomeScreen(QWidget):
    open_app = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        ml = QVBoxLayout(self)
        ml.setContentsMargins(24, 16, 24, 16)
        ml.setSpacing(16)

        hdr = QHBoxLayout()
        hdr.setSpacing(16)
        logo_text = QLabel("\U0001f531")
        logo_text.setStyleSheet(f"color: {C['cyan']}; font-size: 48px; background: transparent;")
        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        t1 = QLabel("VEILOS")
        t1.setStyleSheet(f"color: {C['cyan']}; font-size: 28px; font-weight: bold; letter-spacing: 6px;")
        t2 = QLabel("Hospital Cybersecurity Defense Platform")
        t2.setStyleSheet(f"color: {C['text2']}; font-size: 12px;")
        title_col.addWidget(t1)
        title_col.addWidget(t2)
        hdr.addWidget(logo_text)
        hdr.addLayout(title_col)
        hdr.addStretch()

        status = QLabel("\u25cf  READY")
        status.setStyleSheet(
            f"color: {C['green']}; font-size: 11px; font-weight: bold; "
            f"background: {C['bg3']}; border: 1px solid {C['green']}; "
            "border-radius: 12px; padding: 4px 16px;"
        )
        hdr.addWidget(status)
        ml.addLayout(hdr)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background: {C['border']};")
        ml.addWidget(div)

        ql_frame = QFrame()
        ql_frame.setStyleSheet(f"QFrame {{ background: {C['bg2']}; border: 1px solid {C['border']}; border-radius: 12px; }}")
        ql_layout = QVBoxLayout(ql_frame)
        ql_layout.setContentsMargins(16, 12, 16, 12)
        ql_layout.setSpacing(12)
        ql_title = QLabel("QUICK LAUNCH")
        ql_title.setStyleSheet(f"color: {C['cyan']}; font-size: 13px; font-weight: bold; border: none;")
        ql_layout.addWidget(ql_title)

        tiles = QGridLayout()
        tiles.setSpacing(10)
        apps = [
            ("\U0001f4ca", "Security\nDashboard", C["cyan"], "dashboard"),
            ("\u2328", "Terminal", C["green"], "terminal"),
            ("\U0001f9ec", "Process\nManager", C["gold"], "process_mgr"),
            ("\u2699", "Settings", C["text2"], "settings"),
            ("\U0001f4cb", "Compliance\nHub", C["purple"], "compliance"),
            ("\U0001f916", "DeepSentinel\nML", C["pink"], "deepsentinel"),
            ("\u2694", "RedVeil\nPenTest", C["red"], "redveil"),
            ("\U0001f310", "Federation\nMesh", C["blue"], "federation"),
        ]
        for i, (icon, label, color, app_id) in enumerate(apps):
            btn = QPushButton()
            btn.setFixedSize(120, 90)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{ background: {C['bg3']}; border: 1px solid {C['border']}; border-radius: 12px; }}
                QPushButton:hover {{ background: {C['border']}; border-color: {color}; }}
            """)
            bl = QVBoxLayout(btn)
            bl.setContentsMargins(4, 8, 4, 4)
            bl.setSpacing(2)
            bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ic = QLabel(icon)
            ic.setStyleSheet(f"color: {color}; font-size: 26px; background: transparent; border: none;")
            ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lb = QLabel(label)
            lb.setStyleSheet(f"color: {C['text']}; font-size: 10px; background: transparent; border: none;")
            lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            bl.addWidget(ic)
            bl.addWidget(lb)
            btn.clicked.connect(lambda _, a=app_id: self.open_app.emit(a))
            tiles.addWidget(btn, i // 4, i % 4)

        ql_layout.addLayout(tiles)
        ql_layout.addStretch()
        ml.addWidget(ql_frame, 1)

# ─────────────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────────────
class MetricCard(QFrame):
    def __init__(self, title, value="--", color="#00e5ff"):
        super().__init__()
        self.setStyleSheet(f"QFrame {{ background: {C['bg2']}; border: 1px solid {C['border']}; border-radius: 12px; padding: 10px; }}")
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        t = QLabel(title)
        t.setStyleSheet(f"color: {C['text2']}; font-size: 10px; border: none;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.v = QLabel(value)
        self.v.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold; border: none;")
        self.v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(t)
        layout.addWidget(self.v)

    def set(self, value, color=None):
        self.v.setText(str(value))
        if color:
            self.v.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold; border: none;")

class DashboardApp(QWidget):
    status_text = pyqtSignal(str, str)

    def __init__(self, gsm, poller):
        super().__init__()
        self.gsm = gsm
        self.poller = poller

        self.setup_ui()

        self.poller.health_ready.connect(self.on_health)
        self.poller.organs_ready.connect(self.on_organs)

    def setup_ui(self):
        ml = QVBoxLayout(self)
        ml.setContentsMargins(12, 8, 12, 8)
        ml.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("SECURITY COMMAND CENTER")
        title.setStyleSheet(f"color: {C['cyan']}; font-size: 16px; font-weight: bold; letter-spacing: 2px;")
        self.conn = QLabel("\u25cf CONNECTING...")
        self.conn.setStyleSheet(f"color: {C['orange']}; font-size: 10px; font-weight: bold;")

        settings_btn = QPushButton("Settings")
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setStyleSheet(f"""
            QPushButton {{ background: {C['bg3']}; color: {C['text2']}; border: 1px solid {C['border']};
                          border-radius: 12px; padding: 4px 12px; font-size: 10px; }}
            QPushButton:hover {{ background: {C['border']}; color: {C['text']}; border-color: {C['cyan']}; }}
        """)
        settings_btn.clicked.connect(lambda: GlobalSettingsDialog(self.gsm, parent=self).exec())

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.conn)
        header.addWidget(settings_btn)
        ml.addLayout(header)

        cards = QHBoxLayout()
        cards.setSpacing(8)
        self.c_alerts = MetricCard("ACTIVE ALERTS", "--", C["red"])
        self.c_organs = MetricCard("ORGANS ONLINE", "--", C["green"])
        self.c_uptime = MetricCard("API STATUS", "--", C["cyan"])
        self.c_msos = MetricCard("MSOS MESH", "--", C["cyan"])
        self.c_version = MetricCard("API VERSION", "--", C["gold"])
        for c in [self.c_alerts, self.c_organs, self.c_uptime, self.c_msos, self.c_version]:
            cards.addWidget(c)
        ml.addLayout(cards)

        self.oscroll = QScrollArea()
        self.oscroll.setWidgetResizable(True)
        self.oscroll.setStyleSheet(f"""
            QScrollArea {{ background: {C['bg2']}; border: 1px solid {C['border']}; border-radius: 12px; }}
            QScrollBar:vertical {{ background: {C['bg']}; width: 6px; }}
            QScrollBar::handle:vertical {{ background: {C['border']}; min-height: 20px; border-radius: 3px; }}
        """)
        self.ow = QWidget()
        self.ol = QVBoxLayout(self.ow)
        self.ol.setSpacing(2)
        self.ol.setContentsMargins(10, 10, 10, 10)
        w = QLabel("Connecting to Watchtower...")
        w.setStyleSheet(f"color:{C['dim']};")
        self.ol.addWidget(w)
        self.ol.addStretch()
        self.oscroll.setWidget(self.ow)
        ml.addWidget(self.oscroll, 1)


    def on_health(self, d):
        if "_error" in d:
            self.conn.setText("\u25cf OFFLINE")
            self.conn.setStyleSheet(f"color: {C['red']}; font-size: 10px; font-weight: bold;")
            self.status_text.emit("OFFLINE", C["red"])
            self.c_uptime.set("DOWN", C["red"])
            self.c_msos.set("DOWN", C["red"])
            self.c_version.set("--", C["orange"])
            return
        self.conn.setText("\u25cf CONNECTED")
        self.conn.setStyleSheet(f"color: {C['green']}; font-size: 10px; font-weight: bold;")
        self.status_text.emit("NOMINAL", C["green"])
        self.c_uptime.set("LIVE", C["green"])
        self.c_msos.set("ACTIVE" if d.get("msos_ok") else "DOWN",
                        C["green"] if d.get("msos_ok") else C["red"])
        self.c_version.set(d.get("version", "v0.2.0"), C["gold"])
        self.c_alerts.set("0", C["green"])

    def on_organs(self, organs):
        while self.ol.count():
            it = self.ol.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        if not organs:
            self.ol.addWidget(QLabel("No organs returned."))
            self.ol.addStretch()
            self.c_organs.set("0/0", C["orange"])
            return
        active = 0
        for o in organs[:50]:
            status = str(o.get("active", o.get("status", ""))).lower()
            is_active = status in ("true", "active", "running", "1", "enabled")
            if is_active:
                active += 1
            lab = QLabel(f"{o.get('name','?'):<26}  {'ACTIVE' if is_active else 'INACTIVE'}")
            lab.setStyleSheet(f"color: {C['text'] if is_active else C['orange']}; font-family: monospace; font-size: 11px;")
            self.ol.addWidget(lab)
        self.ol.addStretch()
        self.c_organs.set(f"{active}/{len(organs)}", C["green"] if active == len(organs) else C["orange"])

# ─────────────────────────────────────────────────────────────────────
# Terminal (simple)
# ─────────────────────────────────────────────────────────────────────
class CmdRunner(QThread):
    output_ready = pyqtSignal(str)
    finished_sig = pyqtSignal(int)

    def __init__(self, cmd, cwd, env):
        super().__init__()
        self.cmd = cmd
        self.cwd = cwd
        self.env = env
        self.proc = None

    def run(self):
        full_env = os.environ.copy()
        full_env.update(self.env)
        try:
            self.proc = subprocess.Popen(
                self.cmd, shell=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, cwd=self.cwd, env=full_env,
            )
            for line in iter(self.proc.stdout.readline, b""):
                self.output_ready.emit(line.decode(errors="replace").rstrip("\n"))
            self.proc.wait()
            self.finished_sig.emit(self.proc.returncode)
        except Exception as e:
            self.output_ready.emit(f"Error: {e}")
            self.finished_sig.emit(1)

    def kill(self):
        if self.proc:
            try:
                self.proc.kill()
            except Exception:
                pass

class TerminalApp(QWidget):
    def __init__(self, gsm):
        super().__init__()
        self.gsm = gsm
        self.cwd = str(Path.home())
        self.history = []
        self.hist_idx = -1
        self.running = False
        self.runner = None
        self.env = {
            "TERM": "dumb", "COLUMNS": "120",
            "VEIL_HOME": "/opt/veilcore",
            "VEIL_API": self.gsm.api_base(),
            "VEIL_VERSION": "2.0.0",
        }
        self.setup_ui()
        self.gsm.settings_changed.connect(self.on_global_settings_changed)
        QTimer.singleShot(100, self._motd)

    def on_global_settings_changed(self, _s):
        self.env["VEIL_API"] = self.gsm.api_base()
        self._appendc(f"[GLOBAL] VEIL_API -> {self.env['VEIL_API']}", C["gold"])

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet(f"""
            QTextEdit {{
                background: {C['bg']}; color: {C['green']};
                font-family: 'Courier New', monospace; font-size: 12px;
                border: none; padding: 8px;
                selection-background-color: {C['cyan']}; selection-color: {C['bg']};
            }}
        """)
        layout.addWidget(self.output)

        row = QHBoxLayout()
        row.setContentsMargins(8, 4, 8, 6)
        row.setSpacing(4)
        self.prompt_label = QLabel(self._prompt())
        self.prompt_label.setStyleSheet(f"color:{C['cyan']}; font-family:'Courier New', monospace; font-size:12px;")
        self.input = QLineEdit()
        self.input.setStyleSheet(f"QLineEdit{{background:transparent;color:{C['green']};font-family:'Courier New', monospace;font-size:12px;border:none;}}")
        self.input.returnPressed.connect(self.on_enter)
        self.input.installEventFilter(self)
        row.addWidget(self.prompt_label)
        row.addWidget(self.input, 1)
        layout.addLayout(row)

    def _prompt(self):
        home = str(Path.home())
        d = self.cwd.replace(home, "~") if self.cwd.startswith(home) else self.cwd
        user = os.environ.get("USER", "veilcore")
        return f"{user}@hospital:{d}$ "

    def _appendc(self, text, color):
        import html as _html
        safe = _html.escape(text)
        self.output.append(f'<pre style="margin:0; color:{color}; font-family: monospace;">{safe}</pre>')
        self.output.moveCursor(QTextCursor.MoveOperation.End)

    def _motd(self):
        self._appendc("VEILOS TERMINAL", C["cyan"])
        self._appendc(f"VEIL_API (global): {self.env['VEIL_API']}", C["dim"])
        self._appendc("", C["dim"])

    def _cd(self, path):
        if not path:
            path = "~"
        target = os.path.expanduser(path)
        if not os.path.isabs(target):
            target = os.path.join(self.cwd, target)
        target = os.path.normpath(target)
        if os.path.isdir(target):
            self.cwd = target
            self.prompt_label.setText(self._prompt())
        else:
            self._appendc(f"cd: {path}: No such file or directory", C["red"])

    def on_enter(self):
        raw = self.input.text()
        self.input.clear()
        cmd = raw.strip()
        if not cmd:
            return
        self.history.append(cmd)
        self.hist_idx = -1
        self._appendc(self._prompt() + cmd, C["cyan"])

        if cmd in ("clear", "cls"):
            self.output.clear()
            return
        if cmd.startswith("cd ") or cmd == "cd":
            self._cd(cmd[3:].strip() if cmd.startswith("cd ") else "~")
            return

        if self.running:
            self._appendc("Command already running... (Ctrl+C)", C["orange"])
            return

        self.running = True
        self.input.setEnabled(False)
        self.runner = CmdRunner(cmd, self.cwd, self.env)
        self.runner.output_ready.connect(lambda line: self._appendc(line, C["green"]))
        self.runner.finished_sig.connect(self._on_done)
        self.runner.start()

    def _on_done(self, code):
        self.running = False
        self.input.setEnabled(True)
        self.input.setFocus()
        if code != 0:
            self._appendc(f"[exit {code}]", C["red"])
        self.prompt_label.setText(self._prompt())

    def eventFilter(self, obj, event):
        if obj == self.input and event.type() == event.Type.KeyPress:
            key = event.key()
            mods = event.modifiers()
            ctrl = mods & Qt.KeyboardModifier.ControlModifier

            if ctrl and key == Qt.Key.Key_L:
                self.output.clear()
                return True

            if ctrl and key == Qt.Key.Key_C:
                if self.running and self.runner:
                    self.runner.kill()
                    self._appendc("^C", C["red"])
                    self.running = False
                    self.input.setEnabled(True)
                return True

            if key == Qt.Key.Key_Up:
                if self.history:
                    if self.hist_idx == -1:
                        self.hist_idx = len(self.history) - 1
                    elif self.hist_idx > 0:
                        self.hist_idx -= 1
                    self.input.setText(self.history[self.hist_idx])
                return True

            if key == Qt.Key.Key_Down:
                if self.hist_idx >= 0:
                    self.hist_idx += 1
                    if self.hist_idx >= len(self.history):
                        self.hist_idx = -1
                        self.input.clear()
                    else:
                        self.input.setText(self.history[self.hist_idx])
                return True

        return super().eventFilter(obj, event)

# ─────────────────────────────────────────────────────────────────────
# Process Manager
# ─────────────────────────────────────────────────────────────────────
class ProcessManagerApp(QWidget):
    def __init__(self, gsm, poller):
        super().__init__()
        self.gsm = gsm
        self.poller = poller
        self.setup_ui()

        self.poller.organs_ready.connect(self._on_organs)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("ORGAN PROCESS MANAGER")
        title.setStyleSheet(f"color: {C['cyan']}; font-size: 14px; font-weight: bold; letter-spacing: 2px;")
        self.count_label = QLabel("Loading...")
        self.count_label.setStyleSheet(f"color: {C['dim']}; font-size: 10px;")

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setStyleSheet(f"""
            QPushButton {{ background: {C['bg3']}; color: {C['cyan']}; border: 1px solid {C['border']};
                          border-radius: 12px; padding: 4px 12px; font-size: 10px; }}
            QPushButton:hover {{ background: {C['border']}; }}
        """)
        btn_refresh.clicked.connect(self.poller.poll)

        settings_btn = QPushButton("Settings")
        settings_btn.setStyleSheet(btn_refresh.styleSheet())
        settings_btn.clicked.connect(lambda: GlobalSettingsDialog(self.gsm, parent=self).exec())

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.count_label)
        header.addWidget(btn_refresh)
        header.addWidget(settings_btn)
        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Organ", "Tier", "Status", "Type", "Description"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background: {C['bg2']}; color: {C['text']}; border: 1px solid {C['border']};
                gridline-color: {C['border']}; font-size: 11px; border-radius: 12px;
            }}
            QTableWidget::item {{ padding: 4px; }}
            QTableWidget::item:selected {{ background: {C['bg3']}; }}
            QHeaderView::section {{
                background: {C['bg3']}; color: {C['cyan']}; border: 1px solid {C['border']};
                padding: 4px; font-weight: bold; font-size: 10px;
            }}
        """)
        layout.addWidget(self.table)

    def _on_organs(self, organs):
        if not organs:
            self.count_label.setText("API Offline / No Data")
            self.table.setRowCount(0)
            return

        self.table.setRowCount(len(organs))
        active = 0
        tc = {"P0": C["red"], "P1": C["orange"], "P2": C["green"]}

        for i, org in enumerate(organs):
            name = org.get("name", org.get("display", "?"))
            tier = org.get("tier", "P2")
            status = str(org.get("active", org.get("status", org.get("enabled", "?"))))
            otype = org.get("type", org.get("category", "security"))
            desc = org.get("description", org.get("unit", ""))

            is_active = status.lower() in ("true", "active", "running", "1", "enabled")
            if is_active:
                active += 1

            items = [name, tier, "ACTIVE" if is_active else "INACTIVE", otype, desc]
            colors = [C["text"], tc.get(tier, C["text"]),
                      C["green"] if is_active else C["red"], C["text2"], C["dim"]]
            for j, (val, col) in enumerate(zip(items, colors)):
                item = QTableWidgetItem(val)
                item.setForeground(QColor(col))
                self.table.setItem(i, j, item)

        self.count_label.setText(f"{active}/{len(organs)} active")

# ─────────────────────────────────────────────────────────────────────
# Settings App (global editor)
# ─────────────────────────────────────────────────────────────────────
class SettingsApp(QWidget):
    def __init__(self, gsm):
        super().__init__()
        self.gsm = gsm
        self.setup_ui()
        self.gsm.settings_changed.connect(self._sync)
        self._sync(self.gsm.get())

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("SYSTEM SETTINGS (GLOBAL)")
        title.setStyleSheet(f"color: {C['cyan']}; font-size: 16px; font-weight: bold; letter-spacing: 2px;")
        layout.addWidget(title)

        frame = QFrame()
        frame.setStyleSheet(f"QFrame {{ background: {C['bg2']}; border: 1px solid {C['border']}; border-radius: 12px; }}")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(14, 12, 14, 12)
        fl.setSpacing(10)

        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)

        self.api_base = QLineEdit()
        self.api_base.setPlaceholderText(DEFAULT_API_BASE)
        form.addRow(QLabel("API Endpoint"), self.api_base)

        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("vc_*")
        form.addRow(QLabel("API Key"), self.api_key)

        self.refresh_ms = QSpinBox()
        self.refresh_ms.setRange(500, 60000)
        self.refresh_ms.setSingleStep(250)
        form.addRow(QLabel("Default Refresh (ms)"), self.refresh_ms)

        fl.addLayout(form)

        btnrow = QHBoxLayout()
        btnrow.addStretch()

        open_dialog_btn = QPushButton("Open Dialog")
        open_dialog_btn.setStyleSheet(f"QPushButton{{background:{C['bg3']};color:{C['text2']};border:1px solid {C['border']};border-radius:12px;padding:8px 16px;font-size:11px;font-weight:bold;}}")
        open_dialog_btn.clicked.connect(lambda: GlobalSettingsDialog(self.gsm, parent=self).exec())

        apply_btn = QPushButton("Apply & Save")
        apply_btn.setStyleSheet(open_dialog_btn.styleSheet())
        apply_btn.clicked.connect(self._apply)

        btnrow.addWidget(open_dialog_btn)
        btnrow.addWidget(apply_btn)
        fl.addLayout(btnrow)

        note = QLabel(f"Saved to: {GLOBAL_SETTINGS_PATH}")
        note.setStyleSheet(f"color: {C['dim']}; font-size: 10px;")
        fl.addWidget(note)

        layout.addWidget(frame)
        layout.addStretch()

    def _sync(self, _s):
        self.api_base.setText(self.gsm.api_base())
        self.api_key.setText(self.gsm.api_key())
        self.refresh_ms.setValue(self.gsm.refresh_ms())

    def _apply(self):
        self.gsm.update_global(
            api_base=self.api_base.text().strip(),
            api_key=self.api_key.text().strip(),
            refresh_ms=int(self.refresh_ms.value())
        )

# ─────────────────────────────────────────────────────────────────────
# Simple Module Apps (Compliance / DeepSentinel / RedVeil / Federation)
# ─────────────────────────────────────────────────────────────────────
class SimpleModuleApp(QWidget):
    status_text = pyqtSignal(str, str)

    def __init__(self, gsm, module_id, title, accent, default_flags, body_text, poller=None):
        super().__init__()
        self.gsm = gsm
        self.poller = poller
        self.module_id = module_id
        self.title_text = title
        self.accent = accent
        self.default_flags = default_flags or {}
        self.body_text = body_text
        self.feature_flags = self.gsm.module_flags(self.module_id, self.default_flags)

        self.setup_ui()

        if self.poller:
            self.poller.health_ready.connect(self.on_health)
        self.gsm.settings_changed.connect(self.on_global_settings_changed)

    def setup_ui(self):
        ml = QVBoxLayout(self)
        ml.setContentsMargins(12, 10, 12, 10)
        ml.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel(self.title_text)
        title.setStyleSheet(f"color: {self.accent}; font-size: 16px; font-weight: bold; letter-spacing: 2px;")
        self.conn = QLabel("\u25cf CONNECTING...")
        self.conn.setStyleSheet(f"color: {C['orange']}; font-size: 10px; font-weight: bold;")

        settings_btn = QPushButton("Settings")
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setStyleSheet(f"""
            QPushButton {{ background: {C['bg3']}; color: {C['text2']}; border: 1px solid {C['border']};
                          border-radius: 12px; padding: 4px 12px; font-size: 10px; }}
            QPushButton:hover {{ background: {C['border']}; color: {C['text']}; border-color: {self.accent}; }}
        """)
        settings_btn.clicked.connect(self.open_settings)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.conn)
        header.addWidget(settings_btn)
        ml.addLayout(header)

        body = QFrame()
        body.setStyleSheet(f"QFrame {{ background: {C['bg2']}; border: 1px solid {C['border']}; border-radius: 12px; }}")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(14, 12, 14, 12)
        bl.setSpacing(10)

        self.body_label = QLabel(self.body_text)
        self.body_label.setStyleSheet(f"color: {C['text2']}; font-size: 11px;")
        self.body_label.setWordWrap(True)

        self.endpoint_label = QLabel(f"Endpoint (global): {self.gsm.api_base()}")
        self.endpoint_label.setStyleSheet(f"color: {C['dim']}; font-size: 10px;")

        enabled = [k for k, v in self.feature_flags.items() if v]
        self.flags_label = QLabel(f"Flags: {', '.join(enabled) or '(none)'}")
        self.flags_label.setStyleSheet(f"color: {C['dim']}; font-size: 10px;")

        bl.addWidget(self.body_label)
        bl.addWidget(self.endpoint_label)
        bl.addWidget(self.flags_label)
        bl.addStretch()

        ml.addWidget(body, 1)

    def open_settings(self):
        GlobalSettingsDialog(
            self.gsm,
            module_id=self.module_id,
            module_title=self.title_text,
            module_accent=self.accent,
            module_default_flags=self.default_flags,
            parent=self
        ).exec()

    def on_global_settings_changed(self, _s):
        self.feature_flags = self.gsm.module_flags(self.module_id, self.default_flags)
        self.endpoint_label.setText(f"Endpoint (global): {self.gsm.api_base()}")
        enabled = [k for k, v in self.feature_flags.items() if v]
        self.flags_label.setText(f"Flags: {', '.join(enabled) or '(none)'}")

    def on_health(self, d):
        if "_error" in d:
            self.conn.setText("\u25cf OFFLINE")
            self.conn.setStyleSheet(f"color: {C['red']}; font-size: 10px; font-weight: bold;")
            self.status_text.emit("OFFLINE", C["red"])
            return
        self.conn.setText("\u25cf CONNECTED")
        self.conn.setStyleSheet(f"color: {C['green']}; font-size: 10px; font-weight: bold;")
        self.status_text.emit("NOMINAL", C["green"])

class ComplianceHubApp(SimpleModuleApp):
    def __init__(self, gsm, poller):
        super().__init__(
            gsm=gsm, module_id="compliance", title="COMPLIANCE HUB",
            accent=C["purple"],
            default_flags={"Auto Evidence Packs": True, "SOC2 Delta Report": False, "FedRAMP Export": True},
            body_text="Compliance mappings and evidence export.\n\nPlanned: Framework coverage, control mapping, evidence packs.",
            poller=poller
        )

class DeepSentinelApp(SimpleModuleApp):
    def __init__(self, gsm, poller):
        super().__init__(
            gsm=gsm, module_id="deepsentinel", title="DEEPSENTINEL ML",
            accent=C["pink"],
            default_flags={"Anomaly Stream": True, "Drift Monitor": True, "Auto Triage": False},
            body_text="Anomaly detection & ML triage.\n\nPlanned: Live anomaly stream, baselines, model drift.",
            poller=poller
        )

class RedVeilApp(SimpleModuleApp):
    def __init__(self, gsm, poller):
        super().__init__(
            gsm=gsm, module_id="redveil", title="REDVEIL PENTEST",
            accent=C["red"],
            default_flags={"Safe Mode": True, "Auth-required scans": True, "Report Generator": True},
            body_text="Pen-testing toolkit.\n\nPlanned: Safe checks, authorized scans, reporting.",
            poller=poller
        )

class FederationMeshApp(SimpleModuleApp):
    def __init__(self, gsm, poller):
        super().__init__(
            gsm=gsm, module_id="federation", title="FEDERATION MESH",
            accent=C["blue"],
            default_flags={"Site Heartbeats": True, "Tunnel Monitor": True, "Auto Re-route": False},
            body_text="Multi-site federation.\n\nPlanned: Site status, secure tunnels, replication.",
            poller=poller
        )

# ─────────────────────────────────────────────────────────────────────
# MDI Sub-Window Guard (prevents maximize-gets-stuck)
# ─────────────────────────────────────────────────────────────────────
class MdiSubWindowGuard(QObject):
    """Event filter: if a sub-window enters maximized state, revert to normal."""
    def eventFilter(self, obj, event):
        if event.type() == event.Type.WindowStateChange:
            if isinstance(obj, QMdiSubWindow) and obj.isMaximized():
                QTimer.singleShot(0, obj.showNormal)
        return False

# ─────────────────────────────────────────────────────────────────────
# VeilOS Desktop (QMdiArea window manager)
# ─────────────────────────────────────────────────────────────────────
class VeilOSDesktop(QMainWindow):
    def __init__(self, gsm):
        super().__init__()
        self.gsm = gsm
        self.setWindowTitle("VeilOS - Hospital Cybersecurity Platform")
        self.setMinimumSize(900, 650)

        self.menu_open = False
        self._notif_y = 10
        self._window_buttons = {}
        self._open_apps = {}
        self._sub_guard = MdiSubWindowGuard()
        self.poller = SharedApiPoller(self.gsm)
        self.setup_ui()
        self.setup_shortcuts()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        central.setStyleSheet(f"background-color: {C['bg']};")
        main = QVBoxLayout(central)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        self.mdi = QMdiArea()
        self.mdi.setStyleSheet(f"""
            QMdiArea {{ background-color: {C['bg']}; border: none; }}
            QMdiSubWindow {{ background: {C['bg2']}; border: 1px solid {C['border2']}; border-radius: 12px; }}
            QMdiSubWindow::title {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1a2332, stop:1 #111827);
                color: {C['cyan']}; font-weight: bold; font-size: 11px; height: 26px; padding-left: 8px;
            }}
        """)
        self.mdi.setOption(QMdiArea.AreaOption.DontMaximizeSubWindowOnActivation)
        self.mdi.setBackground(QBrush(QColor(C["bg"])))

        self.desktop_widget = QWidget(self.mdi.viewport())
        self.desktop_widget.setStyleSheet("background: transparent;")
        self.desktop_widget.lower()
        self._setup_desktop_icons()

        main.addWidget(self.mdi, 1)

        # Taskbar
        taskbar = QFrame()
        taskbar.setFixedHeight(42)
        taskbar.setStyleSheet(f"QFrame {{ background-color: {C['bg2']}; border-top: 1px solid {C['border']}; }}")
        tb = QHBoxLayout(taskbar)
        tb.setContentsMargins(4, 0, 8, 0)
        tb.setSpacing(4)

        self.start_btn = QPushButton("\U0001f531 VeilOS")
        self.start_btn.setFixedSize(110, 34)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00394d, stop:1 #002233);
                color: {C['cyan']}; border: 1px solid {C['border']}; border-radius: 12px;
                font-size: 12px; font-weight: bold; letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #004d66, stop:1 #003344);
                border-color: {C['cyan']};
            }}
        """)
        self.start_btn.clicked.connect(self.toggle_menu)
        tb.addWidget(self.start_btn)

        sep = QFrame()
        sep.setFixedSize(1, 28)
        sep.setStyleSheet(f"background: {C['border']};")
        tb.addWidget(sep)

        self.window_list = QHBoxLayout()
        self.window_list.setSpacing(2)
        tb.addLayout(self.window_list)
        tb.addStretch()

        self.tray_status = QLabel("\u25cf NOMINAL")
        self.tray_status.setStyleSheet(f"color: {C['green']}; font-size: 10px; font-weight: bold;")
        self.clock = QLabel()
        self.clock.setStyleSheet(f"color: {C['text2']}; font-size: 11px;")

        tb.addWidget(self.tray_status)
        sep2 = QFrame()
        sep2.setFixedSize(1, 28)
        sep2.setStyleSheet(f"background: {C['border']};")
        tb.addWidget(sep2)
        tb.addWidget(self.clock)

        main.addWidget(taskbar)

        # Start menu
        self.start_menu = QFrame(central)
        self.start_menu.setFixedSize(320, 540)
        self.start_menu.hide()
        self.start_menu.setStyleSheet(f"QFrame {{ background-color: {C['bg2']}; border: 1px solid {C['cyan']}; border-radius: 14px; }}")
        self._build_start_menu()

        self.ctimer = QTimer(self)
        self.ctimer.timeout.connect(self.tick)
        self.ctimer.start(1000)
        self.tick()

        self.mdi.subWindowActivated.connect(self._on_window_activated)

    def _setup_desktop_icons(self):
        icons = [
            ("\U0001f3e0", "Home", C["cyan"], self.open_home),
            ("\U0001f4ca", "Dashboard", C["cyan"], self.open_dashboard),
            ("\u2328", "Terminal", C["green"], self.open_terminal),
            ("\U0001f9ec", "Organs", C["gold"], self.open_process_mgr),
            ("\U0001f4cb", "Compliance", C["purple"], self.open_compliance),
            ("\U0001f916", "DeepSentinel", C["pink"], self.open_deepsentinel),
            ("\u2694", "RedVeil", C["red"], self.open_redveil),
            ("\U0001f310", "Federation", C["blue"], self.open_federation),
            ("\u2699", "Settings", C["text2"], self.open_settings),
        ]
        grid = QGridLayout(self.desktop_widget)
        grid.setContentsMargins(20, 20, 20, 20)
        grid.setSpacing(10)
        grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        for i, (ic, label, color, cb) in enumerate(icons):
            icon = DesktopIcon(ic, label, color)
            icon.double_clicked.connect(cb)
            grid.addWidget(icon, i % 6, i // 6)

    def _build_start_menu(self):
        sm = QVBoxLayout(self.start_menu)
        sm.setContentsMargins(8, 12, 8, 8)
        sm.setSpacing(2)

        smh = QLabel("\U0001f531 VEILOS APPLICATIONS")
        smh.setStyleSheet(f"color: {C['cyan']}; font-size: 13px; font-weight: bold; letter-spacing: 2px; padding: 4px 8px; border: none;")
        sm.addWidget(smh)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {C['border']}; border: none;")
        sm.addWidget(sep)

        apps = [
            ("\U0001f3e0", "Home", "System overview", C["cyan"], self.open_home),
            ("\U0001f4ca", "Security Dashboard", "Real-time monitoring", C["cyan"], self.open_dashboard),
            ("\u2328", "Terminal", "Linux shell", C["green"], self.open_terminal),
            ("\U0001f9ec", "Process Manager", "82 security organs", C["gold"], self.open_process_mgr),
            ("\u2699", "Settings", "Global API settings", C["text2"], self.open_settings),
            ("\U0001f4cb", "Compliance Hub", "Framework evidence", C["purple"], self.open_compliance),
            ("\U0001f310", "Federation", "Multi-site mesh", C["blue"], self.open_federation),
            ("\U0001f916", "DeepSentinel ML", "Anomaly detection", C["pink"], self.open_deepsentinel),
            ("\u2694", "RedVeil", "Pen testing", C["red"], self.open_redveil),
        ]
        for icon, name, desc, color, cb in apps:
            btn = QPushButton()
            btn.setFixedHeight(44)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"QPushButton{{background:transparent;border:none;border-radius:10px;padding:4px 8px;}} QPushButton:hover{{background:{C['bg3']};}}")
            bl = QHBoxLayout(btn)
            bl.setContentsMargins(8, 2, 8, 2)
            bl.setSpacing(10)
            il = QLabel(icon)
            il.setStyleSheet(f"color:{color};font-size:22px;")
            il.setFixedWidth(32)
            il.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tl = QVBoxLayout()
            tl.setSpacing(0)
            n = QLabel(name)
            n.setStyleSheet(f"color:{C['text']};font-size:12px;font-weight:bold;")
            d = QLabel(desc)
            d.setStyleSheet(f"color:{C['dim']};font-size:9px;")
            tl.addWidget(n); tl.addWidget(d)
            bl.addWidget(il); bl.addLayout(tl, 1)

            def make_handler(callback):
                def handler():
                    callback()
                    self.toggle_menu()
                return handler
            btn.clicked.connect(make_handler(cb))
            sm.addWidget(btn)

        sm.addStretch()

        wm_row = QHBoxLayout()
        for label, action in [("Tile", self.mdi.tileSubWindows),
                             ("Cascade", self.mdi.cascadeSubWindows),
                             ("Close All", self._close_all_windows)]:
            b = QPushButton(label)
            b.setStyleSheet(f"QPushButton{{background:{C['bg3']};color:{C['text2']};border:1px solid {C['border']};border-radius:10px;padding:3px 10px;font-size:10px;}} QPushButton:hover{{background:{C['border']};color:{C['text']};}}")
            b.clicked.connect(action)
            wm_row.addWidget(b)
        sm.addLayout(wm_row)

        footer = QLabel("Global settings propagate to ALL apps + terminal.")
        footer.setStyleSheet(f"color:{C['dim']};font-size:9px;padding:6px;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sm.addWidget(footer)

    # ── Window management (singleton + taskbar button)
    def _add_mdi_window(self, widget, title, size=(900, 600), app_type=None):
        if app_type and app_type in self._open_apps:
            existing = self._open_apps[app_type]
            try:
                if existing and existing.widget():
                    self._activate_window(existing)
                    return existing
            except RuntimeError:
                self._open_apps.pop(app_type, None)

        sub = QMdiSubWindow()
        sub.setWidget(widget)
        sub.setWindowTitle(title)
        sub.resize(*size)
        sub.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.mdi.addSubWindow(sub)
        sub.installEventFilter(self._sub_guard)  # prevent maximize-gets-stuck
        sub.show()
        sub.raise_()
        self.desktop_widget.lower()

        self._add_taskbar_button(sub, title)

        if app_type:
            self._open_apps[app_type] = sub

        def _on_destroyed():
            self._remove_taskbar_button(sub)
            for k in list(self._open_apps):
                if self._open_apps.get(k) is sub:
                    self._open_apps.pop(k, None)
                    break
        sub.destroyed.connect(_on_destroyed)
        return sub

    def _add_taskbar_button(self, sub, title):
        ctr = QWidget()
        ctr.setFixedHeight(28)
        hl = QHBoxLayout(ctr)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)

        btn = QPushButton(title[:18])
        btn.setFixedHeight(28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ background:{C['bg3']}; color:{C['text2']}; border:1px solid {C['border']};
                           border-radius:10px; padding:0 8px; font-size:10px;
                           border-top-right-radius:0; border-bottom-right-radius:0; }}
            QPushButton:hover {{ background:{C['border']}; color:{C['text']}; }}
        """)
        btn.clicked.connect(lambda: self._toggle_window(sub))

        xb = QPushButton("\u2715")
        xb.setFixedSize(24, 28)
        xb.setCursor(Qt.CursorShape.PointingHandCursor)
        xb.setStyleSheet(f"""
            QPushButton {{ background:{C['bg3']}; color:{C['dim']}; border:1px solid {C['border']}; border-left:none;
                           font-size:11px; font-weight:bold; border-top-right-radius:10px; border-bottom-right-radius:10px; }}
            QPushButton:hover {{ background:{C['red']}; color:white; }}
        """)
        xb.clicked.connect(lambda: sub.close())

        hl.addWidget(btn)
        hl.addWidget(xb)
        self.window_list.addWidget(ctr)
        self._window_buttons[id(sub)] = ctr

    def _remove_taskbar_button(self, sub):
        w = self._window_buttons.pop(id(sub), None)
        if w:
            self.window_list.removeWidget(w)
            w.deleteLater()

    def _activate_window(self, sub):
        if sub.isMinimized():
            sub.showNormal()
        if sub.isHidden():
            sub.show()
        sub.raise_()
        self.mdi.setActiveSubWindow(sub)
        sub.setFocus()

    def _toggle_window(self, sub):
        """Taskbar click: if active & visible → minimize; otherwise → activate."""
        if sub.isMinimized() or sub.isHidden():
            self._activate_window(sub)
        elif self.mdi.activeSubWindow() is sub:
            sub.showMinimized()
        else:
            self._activate_window(sub)

    def _on_window_activated(self, sub):
        for sid, ctr in list(self._window_buttons.items()):
            try:
                btns = ctr.findChildren(QPushButton)
                btn = btns[0] if btns else None
            except Exception:
                continue
            if not btn:
                continue
            if sub and sid == id(sub):
                btn.setStyleSheet(f"""
                    QPushButton {{ background:{C['border']}; color:{C['cyan']}; border:1px solid {C['cyan']};
                                   border-radius:10px; padding:0 8px; font-size:10px; font-weight:bold;
                                   border-top-right-radius:0; border-bottom-right-radius:0; }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{ background:{C['bg3']}; color:{C['text2']}; border:1px solid {C['border']};
                                   border-radius:10px; padding:0 8px; font-size:10px;
                                   border-top-right-radius:0; border-bottom-right-radius:0; }}
                    QPushButton:hover {{ background:{C['border']}; color:{C['text']}; }}
                """)

    # ── Launchers
    def open_home(self):
        home = HomeScreen()
        home.open_app.connect(self._home_launch)
        w = max(self.mdi.width() - 20, 900)
        h = max(self.mdi.height() - 20, 600)
        self._add_mdi_window(home, "\U0001f3e0 Home", (w, h), app_type="home")

    def _home_launch(self, app_id):
        dispatch = {
            "dashboard": self.open_dashboard,
            "terminal": self.open_terminal,
            "process_mgr": self.open_process_mgr,
            "settings": self.open_settings,
            "compliance": self.open_compliance,
            "deepsentinel": self.open_deepsentinel,
            "redveil": self.open_redveil,
            "federation": self.open_federation,
        }
        dispatch.get(app_id, self.open_dashboard)()

    def open_dashboard(self):
        dash = DashboardApp(self.gsm, self.poller)
        dash.status_text.connect(self._update_tray)
        self._add_mdi_window(dash, "Security Dashboard", (980, 640), app_type="dashboard")

    def open_terminal(self):
        self._add_mdi_window(TerminalApp(self.gsm), "Terminal", (820, 520), app_type="terminal")

    def open_process_mgr(self):
        self._add_mdi_window(ProcessManagerApp(self.gsm, self.poller), "Process Manager", (980, 560), app_type="process_mgr")

    def open_settings(self):
        self._add_mdi_window(SettingsApp(self.gsm), "Settings", (760, 480), app_type="settings")

    def open_compliance(self):
        app = ComplianceHubApp(self.gsm, self.poller)
        app.status_text.connect(self._update_tray)
        self._add_mdi_window(app, "Compliance Hub", (980, 640), app_type="compliance")

    def open_deepsentinel(self):
        app = DeepSentinelApp(self.gsm, self.poller)
        app.status_text.connect(self._update_tray)
        self._add_mdi_window(app, "DeepSentinel ML", (980, 640), app_type="deepsentinel")

    def open_redveil(self):
        app = RedVeilApp(self.gsm, self.poller)
        app.status_text.connect(self._update_tray)
        self._add_mdi_window(app, "RedVeil", (980, 640), app_type="redveil")

    def open_federation(self):
        app = FederationMeshApp(self.gsm, self.poller)
        app.status_text.connect(self._update_tray)
        self._add_mdi_window(app, "Federation Mesh", (980, 640), app_type="federation")

    def _update_tray(self, text, color):
        self.tray_status.setText(f"\u25cf {text}")
        self.tray_status.setStyleSheet(f"color:{color}; font-size:10px; font-weight:bold;")

    # ── Notifications
    def notify(self, title, message, severity="info"):
        toast = NotificationToast(self.centralWidget(), title, message, severity)
        toast.move(self.centralWidget().width() - 330, self._notif_y)
        self._notif_y += 80
        if self._notif_y > 400:
            self._notif_y = 10
        QTimer.singleShot(4500, lambda: setattr(self, "_notif_y", max(10, self._notif_y - 80)))

    # ── Shortcuts
    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Alt+H"), self, self.open_home)
        QShortcut(QKeySequence("Ctrl+Alt+T"), self, self.open_terminal)
        QShortcut(QKeySequence("Ctrl+Alt+D"), self, self.open_dashboard)
        QShortcut(QKeySequence("Ctrl+Alt+P"), self, self.open_process_mgr)
        QShortcut(QKeySequence("F11"), self, self.toggle_fullscreen)
        QShortcut(QKeySequence("Ctrl+W"), self, self._close_active)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _close_active(self):
        sub = self.mdi.activeSubWindow()
        if sub:
            sub.close()

    def _close_all_windows(self):
        for sub in list(self.mdi.subWindowList()):
            sub.close()
        self._open_apps.clear()

    # ── Context menu
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background:{C['bg2']}; color:{C['text']}; border:1px solid {C['border']}; padding:4px; font-size:11px; }}
            QMenu::item {{ padding:6px 24px; border-radius:10px; }}
            QMenu::item:selected {{ background:{C['bg3']}; color:{C['cyan']}; }}
            QMenu::separator {{ height:1px; background:{C['border']}; margin:4px 8px; }}
        """)
        menu.addAction("Home", self.open_home)
        menu.addAction("Dashboard", self.open_dashboard)
        menu.addAction("Terminal", self.open_terminal)
        menu.addAction("Process Manager", self.open_process_mgr)
        menu.addSeparator()
        menu.addAction("Compliance Hub", self.open_compliance)
        menu.addAction("DeepSentinel ML", self.open_deepsentinel)
        menu.addAction("RedVeil", self.open_redveil)
        menu.addAction("Federation Mesh", self.open_federation)
        menu.addSeparator()
        menu.addAction("Global Settings", lambda: GlobalSettingsDialog(self.gsm, parent=self).exec())
        menu.addSeparator()
        menu.addAction("Tile Windows", self.mdi.tileSubWindows)
        menu.addAction("Cascade Windows", self.mdi.cascadeSubWindows)
        menu.addAction("Close All Windows", self._close_all_windows)
        menu.exec(event.globalPos())

    # ── Start menu
    def toggle_menu(self):
        if self.menu_open:
            self.start_menu.hide()
        else:
            x = 4
            y = self.centralWidget().height() - 42 - self.start_menu.height() - 4
            self.start_menu.move(x, y)
            self.start_menu.show()
            self.start_menu.raise_()
        self.menu_open = not self.menu_open

    # ── Clock
    def tick(self):
        self.clock.setText(datetime.now().strftime("%a %b %d  %H:%M:%S"))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "desktop_widget"):
            vp = self.mdi.viewport()
            self.desktop_widget.setGeometry(0, 0, vp.width(), vp.height())

# ─────────────────────────────────────────────────────────────────────
# Main App (Splash -> Desktop) with robust failure logging
# ─────────────────────────────────────────────────────────────────────
class VeilOSApp:
    def __init__(self):
        _ensure_global_dir()
        log("=== VeilOS starting ===")
        log(f"DISPLAY={os.environ.get('DISPLAY','')}, WAYLAND_DISPLAY={os.environ.get('WAYLAND_DISPLAY','')}, QT_QPA_PLATFORM={os.environ.get('QT_QPA_PLATFORM','')}")
        log(f"LOG_PATH={LOG_PATH}")

        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setStyle("Fusion")

        # palette
        p = QPalette()
        p.setColor(QPalette.ColorRole.Window, QColor(C["bg"]))
        p.setColor(QPalette.ColorRole.WindowText, QColor(C["text"]))
        p.setColor(QPalette.ColorRole.Base, QColor(C["bg"]))
        p.setColor(QPalette.ColorRole.Text, QColor(C["text"]))
        p.setColor(QPalette.ColorRole.Highlight, QColor(C["cyan"]))
        p.setColor(QPalette.ColorRole.HighlightedText, QColor(C["bg"]))
        p.setColor(QPalette.ColorRole.Button, QColor(C["bg2"]))
        p.setColor(QPalette.ColorRole.ButtonText, QColor(C["text"]))
        self.app.setPalette(p)

        self.gsm = GlobalSettingsManager()

        # Screen sizing
        screen = self.app.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            self._sw, self._sh = geom.width(), geom.height()
        else:
            self._sw, self._sh = 1280, 720

        # Splash window
        self.splash_win = QMainWindow()
        self.splash_win.setWindowTitle("VeilOS")
        self.splash_win.resize(self._sw, self._sh)

        self.splash = SplashScreen()
        self.splash.finished.connect(self._on_splash_done)
        self.splash_win.setCentralWidget(self.splash)
        self.splash_win.show()

        log("Splash shown.")

    def _on_splash_done(self):
        log("Splash finished -> launching desktop.")
        try:
            self.desktop = VeilOSDesktop(self.gsm)
            self.desktop.resize(self._sw, self._sh)
            self.desktop.show()

            # Close splash after desktop is visible
            self.splash_win.hide()
            QTimer.singleShot(150, self.splash_win.close)

            # Auto-open Home
            QTimer.singleShot(250, self.desktop.open_home)

            # Welcome notification
            QTimer.singleShot(800, lambda: self.desktop.notify(
                "VeilOS Initialized",
                f"Global settings: {GLOBAL_SETTINGS_PATH}",
                "info"
            ))

        except Exception:
            # keep splash visible and show error text
            log_exc("Desktop creation failed:")
            self.splash.set_fail("DESKTOP FAILED TO START.\n\nCheck:\n~/.config/veilcore/veilui.log\n\nMost recent error was logged.")
            # do NOT exit; keep UI visible so user isn't stuck “loading”

    def run(self):
        rc = self.app.exec()
        log(f"VeilOS exit rc={rc}")
        sys.exit(rc)

# ─────────────────────────────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Make Qt behave on minimal GPU setups
    os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")
    os.environ.setdefault("GALLIUM_DRIVER", "llvmpipe")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")

    # If user is on Wayland, don't force xcb unless they already set it.
    # (Your logs show WAYLAND_DISPLAY=wayland-0 sometimes.)
    if "QT_QPA_PLATFORM" not in os.environ or not os.environ.get("QT_QPA_PLATFORM"):
        if os.environ.get("WAYLAND_DISPLAY"):
            os.environ["QT_QPA_PLATFORM"] = "wayland"
        else:
            os.environ["QT_QPA_PLATFORM"] = "xcb"

    log(f"QT_QPA_PLATFORM(selected)={os.environ.get('QT_QPA_PLATFORM','')}")
    VeilOSApp().run()#!/usr/bin/env python3
"""
VeilOS Desktop Environment v2.2.1 (GLOBAL SETTINGS + FIXED SPLASH/DESKTOP FAILOVER)
==================================================================================

Fixes:
  - Fix NameError (VeilOSDesktop always defined before use)
  - Robust logging to ~/.config/veilcore/veilui.log
  - If desktop creation fails after splash, show error on splash + log traceback
  - Compliance Hub / DeepSentinel / RedVeil / Federation Mesh are distinct apps,
    each with their own Settings dialog (module flags) like Command Center.

Built by Marlon Astin Williams, 2025-2026.
"""

import sys
import os
import json
import math
import random
import subprocess
import traceback
import urllib.request
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────
# PyQt6 Imports
# ─────────────────────────────────────────────────────────────────────
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QScrollArea, QFrame, QPushButton, QGridLayout,
        QTextEdit, QLineEdit, QMdiArea, QMdiSubWindow,
        QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
        QMenu, QDialog, QFormLayout, QSpinBox, QCheckBox, QDialogButtonBox,
        QTabWidget,
    )
    from PyQt6.QtCore import (
        Qt, QTimer, QThread, pyqtSignal, QPoint, QPointF, QObject
    )
    from PyQt6.QtGui import (
        QColor, QPalette, QPainter, QBrush, QPen, QFont, QRadialGradient,
        QPainterPath, QKeySequence, QShortcut, QTextCursor
    )
except ImportError:
    print("PyQt6 required: pip install PyQt6 --break-system-packages")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────
# Paths + Logging
# ─────────────────────────────────────────────────────────────────────
GLOBAL_DIR = os.path.join(str(Path.home()), ".config", "veilcore")
GLOBAL_SETTINGS_PATH = os.path.join(GLOBAL_DIR, "global.json")
LOG_PATH = os.path.join(GLOBAL_DIR, "veilui.log")

def _ensure_global_dir():
    os.makedirs(GLOBAL_DIR, exist_ok=True)

def log(msg: str):
    _ensure_global_dir()
    ts = datetime.now().isoformat(timespec="seconds")
    line = f"[{ts}] {msg}"
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    # also stdout for interactive runs
    print(line, flush=True)

def log_exc(prefix: str):
    tb = traceback.format_exc()
    log(prefix)
    for ln in tb.rstrip().splitlines():
        log(ln)

# ─────────────────────────────────────────────────────────────────────
# Defaults
# ─────────────────────────────────────────────────────────────────────
DEFAULT_API_BASE = "http://localhost:9444"
DEFAULT_REFRESH_MS = 4000

def _detect_api_key():
    key = os.environ.get("VEIL_API_KEY", "")
    if key:
        return key
    try:
        out = subprocess.check_output(
            ["systemctl", "show", "-p", "Environment", "veil-api.service"],
            stderr=subprocess.DEVNULL, timeout=3
        ).decode()
        for part in out.split():
            if "VEIL_API_KEY=" in part:
                return part.split("=", 2)[-1].strip('"').strip("'")
    except Exception:
        pass
    return "vc_aceea537c874533b85bdb56d3e7835db40a1cc32eff8024b"

DEFAULT_API_KEY = _detect_api_key()

# Theme
C = {
    "bg": "#0a0e17", "bg2": "#111827", "bg3": "#1a2332", "bg4": "#0d1420",
    "cyan": "#00e5ff", "green": "#00ff6a", "orange": "#ff8c00",
    "red": "#ff4444", "gold": "#fbbf24", "purple": "#a855f7",
    "blue": "#3b82f6", "pink": "#ec4899",
    "text": "#e6f7ff", "text2": "#7baac4", "dim": "#4a6a7a",
    "border": "#1e3a4a", "border2": "#2a4a5a",
}

# ─────────────────────────────────────────────────────────────────────
# Global Settings Manager
# ─────────────────────────────────────────────────────────────────────
def load_global_settings() -> dict:
    _ensure_global_dir()
    if not os.path.exists(GLOBAL_SETTINGS_PATH):
        return {
            "api_base": DEFAULT_API_BASE,
            "api_key": DEFAULT_API_KEY,
            "refresh_ms": DEFAULT_REFRESH_MS,
            "modules": {},
        }
    try:
        with open(GLOBAL_SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
    except Exception:
        data = {}
    data.setdefault("api_base", DEFAULT_API_BASE)
    data.setdefault("api_key", DEFAULT_API_KEY)
    data.setdefault("refresh_ms", DEFAULT_REFRESH_MS)
    data.setdefault("modules", {})
    if not isinstance(data["modules"], dict):
        data["modules"] = {}
    return data

def save_global_settings(data: dict) -> bool:
    _ensure_global_dir()
    try:
        d = dict(data)
        d["saved_at"] = datetime.now().isoformat(timespec="seconds")
        with open(GLOBAL_SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2)
        return True
    except Exception:
        return False

class GlobalSettingsManager(QObject):
    settings_changed = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self._settings = load_global_settings()

    def get(self) -> dict:
        return dict(self._settings)

    def api_base(self) -> str:
        v = str(self._settings.get("api_base") or DEFAULT_API_BASE).strip()
        return v or DEFAULT_API_BASE

    def api_key(self) -> str:
        v = str(self._settings.get("api_key") or DEFAULT_API_KEY).strip()
        return v or DEFAULT_API_KEY

    def refresh_ms(self) -> int:
        try:
            v = int(self._settings.get("refresh_ms") or DEFAULT_REFRESH_MS)
            return max(500, min(60000, v))
        except Exception:
            return DEFAULT_REFRESH_MS

    def module_flags(self, module_id: str, defaults: dict = None) -> dict:
        defaults = defaults or {}
        mods = self._settings.get("modules", {}) or {}
        m = mods.get(module_id, {}) or {}
        flags = m.get("feature_flags", {}) or {}
        merged = dict(defaults)
        if isinstance(flags, dict):
            merged.update(flags)
        return merged

    def update_global(self, *, api_base: str, api_key: str, refresh_ms: int):
        s = dict(self._settings)
        s["api_base"] = (api_base or "").strip() or DEFAULT_API_BASE
        s["api_key"] = (api_key or "").strip() or DEFAULT_API_KEY
        try:
            s["refresh_ms"] = int(refresh_ms)
        except Exception:
            s["refresh_ms"] = DEFAULT_REFRESH_MS
        if save_global_settings(s):
            self._settings = s
            self.settings_changed.emit(self.get())

    def update_module_flags(self, module_id: str, flags: dict):
        s = dict(self._settings)
        mods = dict(s.get("modules", {}) or {})
        m = dict(mods.get(module_id, {}) or {})
        m["feature_flags"] = dict(flags or {})
        mods[module_id] = m
        s["modules"] = mods
        if save_global_settings(s):
            self._settings = s
            self.settings_changed.emit(self.get())

# ─────────────────────────────────────────────────────────────────────
# API (short timeouts)
# ─────────────────────────────────────────────────────────────────────
def api_get(endpoint, base, key):
    url = f"{base}/{endpoint.lstrip('/')}"
    req = urllib.request.Request(url)
    if key:
        req.add_header("X-API-Key", key)
    try:
        with urllib.request.urlopen(req, timeout=2) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"_error": str(e)}

class DataFetcher(QThread):
    health_ready = pyqtSignal(dict)
    organs_ready = pyqtSignal(list)

    def __init__(self, base, key):
        super().__init__()
        self.base = base
        self.key = key

    def run(self):
        self.health_ready.emit(api_get("health", self.base, self.key))
        data = api_get("organs", self.base, self.key)
        if "_error" not in data:
            organs = data.get("organs", [])
            self.organs_ready.emit(organs if isinstance(organs, list) else [])
        else:
            self.organs_ready.emit([])


class SharedApiPoller(QObject):
    """Single poller shared by all apps. One timer, one thread, two signals."""
    health_ready = pyqtSignal(dict)
    organs_ready = pyqtSignal(list)

    def __init__(self, gsm):
        super().__init__()
        self.gsm = gsm
        self._fetcher = None
        self._last_health = {}
        self._last_organs = []

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.poll)
        self._timer.start(gsm.refresh_ms())

        gsm.settings_changed.connect(self._on_settings)
        QTimer.singleShot(300, self.poll)

    def _on_settings(self, _s):
        self._timer.setInterval(self.gsm.refresh_ms())
        self.poll()

    def poll(self):
        if self._fetcher and self._fetcher.isRunning():
            return
        self._fetcher = DataFetcher(self.gsm.api_base(), self.gsm.api_key())
        self._fetcher.health_ready.connect(self._on_health)
        self._fetcher.organs_ready.connect(self._on_organs)
        self._fetcher.start()

    def _on_health(self, d):
        self._last_health = d
        self.health_ready.emit(d)

    def _on_organs(self, organs):
        self._last_organs = organs
        self.organs_ready.emit(organs)

    def last_health(self):
        return dict(self._last_health)

    def last_organs(self):
        return list(self._last_organs)

# ─────────────────────────────────────────────────────────────────────
# Splash Particles
# ─────────────────────────────────────────────────────────────────────
class Particle:
    def __init__(self, x, y):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2, 12)
        self.x, self.y = x, y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.uniform(0.5, 1.0)
        self.decay = random.uniform(0.008, 0.025)
        self.size = random.uniform(2, 6)
        self.color = QColor(random.choice([C["cyan"], C["green"], C["gold"], C["blue"], C["purple"]]))

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.1
        self.vx *= 0.99
        self.life -= self.decay
        return self.life > 0

# ─────────────────────────────────────────────────────────────────────
# Splash Screen (now shows fail text if desktop fails)
# ─────────────────────────────────────────────────────────────────────
class SplashScreen(QWidget):
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background-color: {C['bg']};")
        self.particles = []
        self.phase = 0
        self.alpha = 0.0
        self.text_alpha = 0.0
        self.ring_radius = 0
        self.ring_alpha = 1.0
        self.frame = 0
        self.eye_scale = 0.0
        self.fail_text = ""  # if desktop creation fails

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(16)

        # important: delay sequence until widget is actually shown & sized
        QTimer.singleShot(150, self.start_seq)

    def start_seq(self):
        self.phase = 0
        self.frame = 0
        QTimer.singleShot(850, self.do_explode)
        QTimer.singleShot(1850, self.show_text)
        QTimer.singleShot(3850, self.fade_out)

    def do_explode(self):
        self.phase = 1
        cx, cy = max(1, self.width() // 2), max(1, self.height() // 2)
        for _ in range(220):
            self.particles.append(Particle(cx, cy))
        self.ring_radius = 0
        self.ring_alpha = 1.0

    def show_text(self):
        self.phase = 2

    def fade_out(self):
        self.phase = 3

    def tick(self):
        self.frame += 1
        if self.phase == 0:
            self.eye_scale = min(1.0, self.frame / 50.0)
        if self.phase >= 1:
            self.particles = [p for p in self.particles if p.update()]
            self.ring_radius += 8
            self.ring_alpha = max(0, self.ring_alpha - 0.015)
        if self.phase == 2:
            self.text_alpha = min(1.0, self.text_alpha + 0.03)
        if self.phase == 3:
            self.alpha += 0.02
            if self.alpha >= 1.0:
                self.timer.stop()
                self.finished.emit()
                return
        self.update()

    def set_fail(self, text: str):
        self.fail_text = text
        # stop fade-out so user can read it
        self.phase = 2
        self.text_alpha = 1.0
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        p.fillRect(self.rect(), QColor(C["bg"]))

        # Eye
        if self.phase == 0 and self.eye_scale > 0:
            s = self.eye_scale
            ew, eh = int(120 * s), int(50 * s)
            p.setPen(QPen(QColor(C["cyan"]), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            path = QPainterPath()
            path.moveTo(cx - ew, cy)
            path.cubicTo(cx - ew // 2, cy - eh, cx + ew // 2, cy - eh, cx + ew, cy)
            path.cubicTo(cx + ew // 2, cy + eh, cx - ew // 2, cy + eh, cx - ew, cy)
            p.drawPath(path)

            ir = int(25 * s)
            grad = QRadialGradient(QPointF(cx, cy), ir)
            grad.setColorAt(0, QColor(C["cyan"]))
            grad.setColorAt(0.7, QColor(C["blue"]))
            grad.setColorAt(1, QColor(0, 0, 0, 0))
            p.setBrush(QBrush(grad))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPoint(cx, cy), ir, ir)

        # Ring
        if self.phase >= 1 and self.ring_alpha > 0:
            rc = QColor(C["cyan"])
            rc.setAlphaF(self.ring_alpha * 0.6)
            p.setPen(QPen(rc, 3))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPoint(cx, cy), self.ring_radius, self.ring_radius)

        # Particles
        for pt in self.particles:
            pc = QColor(pt.color)
            pc.setAlphaF(max(0, pt.life))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(pc))
            p.drawEllipse(QPointF(pt.x, pt.y), pt.size, pt.size)

        # Title text
        if self.phase >= 2:
            tc = QColor(C["cyan"])
            tc.setAlphaF(self.text_alpha)
            p.setPen(tc)
            p.setFont(QFont("Monospace", 42, QFont.Weight.Bold))
            p.drawText(self.rect().adjusted(0, -60, 0, 0), Qt.AlignmentFlag.AlignCenter, "V E I L O S")

            sc = QColor(C["text2"])
            sc.setAlphaF(self.text_alpha * 0.9)
            p.setPen(sc)
            p.setFont(QFont("Monospace", 14))
            p.drawText(self.rect().adjusted(0, 30, 0, 0), Qt.AlignmentFlag.AlignCenter,
                       "Hospital Cybersecurity Defense Platform")

        # Failure text overlay
        if self.fail_text:
            p.setPen(QColor(C["red"]))
            p.setFont(QFont("Monospace", 11))
            p.drawText(self.rect().adjusted(60, 120, -60, -60),
                       Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter,
                       self.fail_text)

        # Fade overlay
        if self.phase == 3 and not self.fail_text:
            ov = QColor(C["bg"])
            ov.setAlphaF(min(1.0, self.alpha))
            p.fillRect(self.rect(), ov)
        p.end()

# ─────────────────────────────────────────────────────────────────────
# Toast
# ─────────────────────────────────────────────────────────────────────
class NotificationToast(QFrame):
    def __init__(self, parent, title, message, severity="info", duration=4000):
        super().__init__(parent)
        sev_colors = {
            "critical": C["red"], "high": C["orange"],
            "medium": C["gold"], "low": C["green"], "info": C["cyan"],
        }
        color = sev_colors.get(severity, C["cyan"])
        self.setFixedSize(320, 72)
        self.setStyleSheet(f"""
            QFrame {{
                background: {C['bg2']}; border: 1px solid {color};
                border-left: 4px solid {color}; border-radius: 10px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)
        t = QLabel(title)
        t.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold; border: none;")
        m = QLabel(message)
        m.setStyleSheet(f"color: {C['text2']}; font-size: 10px; border: none;")
        m.setWordWrap(True)
        layout.addWidget(t)
        layout.addWidget(m)
        self.show()
        self.raise_()
        QTimer.singleShot(duration, self._fade)

    def _fade(self):
        self.hide()
        self.deleteLater()

# ─────────────────────────────────────────────────────────────────────
# Desktop Icon
# ─────────────────────────────────────────────────────────────────────
class DesktopIcon(QWidget):
    double_clicked = pyqtSignal()

    def __init__(self, icon_char, label, color):
        super().__init__()
        self.setFixedSize(90, 85)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hovered = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ic = QLabel(icon_char)
        ic.setStyleSheet(f"color: {color}; font-size: 32px; background: transparent;")
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lb = QLabel(label)
        lb.setStyleSheet(f"color: {C['text']}; font-size: 10px; background: transparent;")
        lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lb.setWordWrap(True)
        layout.addWidget(ic)
        layout.addWidget(lb)

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit()

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def paintEvent(self, event):
        if self._hovered:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            c = QColor(C["cyan"])
            c.setAlphaF(0.12)
            p.setBrush(QBrush(c))
            p.setPen(QPen(QColor(C["cyan"]), 1))
            p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 10, 10)
            p.end()

# ─────────────────────────────────────────────────────────────────────
# Global Settings Dialog
# ─────────────────────────────────────────────────────────────────────
class GlobalSettingsDialog(QDialog):
    def __init__(self, gsm, module_id=None, module_title=None,
                 module_accent=None, module_default_flags=None, parent=None):
        super().__init__(parent)
        self.gsm = gsm
        self.module_id = module_id
        self.module_title = module_title or "SYSTEM SETTINGS"
        self.module_accent = module_accent or C["cyan"]
        self.module_default_flags = module_default_flags or {}
        self.flag_widgets = {}

        self.setModal(True)
        self.setFixedSize(560, 420)
        self.setWindowTitle(f"{self.module_title} — Settings")
        self.setStyleSheet(f"""
            QDialog {{ background: {C['bg2']}; color: {C['text']}; border: 1px solid {C['border']}; }}
            QLabel {{ border: none; }}
            QLineEdit {{
                background: {C['bg3']}; color: {C['text']};
                border: 1px solid {C['border']}; border-radius: 10px; padding: 7px 10px; font-size: 11px;
            }}
            QSpinBox {{
                background: {C['bg3']}; color: {C['text']};
                border: 1px solid {C['border']}; border-radius: 10px; padding: 4px 10px; font-size: 11px;
            }}
            QCheckBox {{ color: {C['text']}; font-size: 11px; }}
        """)

        s = self.gsm.get()
        ml = QVBoxLayout(self)
        ml.setContentsMargins(14, 12, 14, 12)
        ml.setSpacing(10)

        hdr = QLabel("GLOBAL SETTINGS")
        hdr.setStyleSheet(f"color: {self.module_accent}; font-size: 15px; font-weight: bold; letter-spacing: 2px;")
        ml.addWidget(hdr)

        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {C['border']}; border-radius: 12px; }}
            QTabBar::tab {{
                background: {C['bg3']}; color: {C['text2']}; padding: 8px 12px;
                border-top-left-radius: 10px; border-top-right-radius: 10px; margin-right: 4px;
            }}
            QTabBar::tab:selected {{
                background: {C['bg2']}; color: {self.module_accent};
                border: 1px solid {C['border']}; border-bottom: none;
            }}
        """)

        # General
        general = QWidget()
        gl = QVBoxLayout(general)
        gl.setContentsMargins(14, 14, 14, 14)
        gl.setSpacing(10)
        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)

        self.api_base = QLineEdit(str(s.get("api_base") or DEFAULT_API_BASE))
        self.api_base.setPlaceholderText(DEFAULT_API_BASE)
        form.addRow(QLabel("API Endpoint"), self.api_base)

        self.api_key = QLineEdit(str(s.get("api_key") or DEFAULT_API_KEY))
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("vc_*")
        form.addRow(QLabel("API Key"), self.api_key)

        self.refresh_ms = QSpinBox()
        self.refresh_ms.setRange(500, 60000)
        self.refresh_ms.setSingleStep(250)
        self.refresh_ms.setValue(int(s.get("refresh_ms") or DEFAULT_REFRESH_MS))
        form.addRow(QLabel("Default Refresh (ms)"), self.refresh_ms)

        gl.addLayout(form)
        file_note = QLabel(f"File: {GLOBAL_SETTINGS_PATH}")
        file_note.setStyleSheet(f"color: {C['dim']}; font-size: 10px;")
        gl.addWidget(file_note)
        gl.addStretch()
        tabs.addTab(general, "General")

        # Module flags
        if self.module_id:
            mod = QWidget()
            ml2 = QVBoxLayout(mod)
            ml2.setContentsMargins(14, 14, 14, 14)
            ml2.setSpacing(10)
            t = QLabel(f"MODULE FLAGS — {self.module_id}")
            t.setStyleSheet(f"color: {C['text2']}; font-size: 12px; font-weight: bold;")
            ml2.addWidget(t)

            flags = self.gsm.module_flags(self.module_id, self.module_default_flags)
            for k, v in sorted(flags.items()):
                cb = QCheckBox(k)
                cb.setChecked(bool(v))
                self.flag_widgets[k] = cb
                ml2.addWidget(cb)

            ml2.addStretch()
            tabs.addTab(mod, "Module Flags")

        ml.addWidget(tabs, 1)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Reset
        )
        btns.setStyleSheet(f"""
            QDialogButtonBox QPushButton {{
                background: {C['bg3']}; color: {C['text2']};
                border: 1px solid {C['border']}; border-radius: 12px; padding: 7px 16px; font-size: 11px;
            }}
            QDialogButtonBox QPushButton:hover {{
                background: {C['border']}; color: {C['text']}; border-color: {self.module_accent};
            }}
        """)
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        btns.button(QDialogButtonBox.StandardButton.Reset).clicked.connect(self._reset)
        ml.addWidget(btns)

    def _reset(self):
        self.api_base.setText(DEFAULT_API_BASE)
        self.api_key.setText(DEFAULT_API_KEY)
        self.refresh_ms.setValue(DEFAULT_REFRESH_MS)
        for k, cb in self.flag_widgets.items():
            cb.setChecked(bool(self.module_default_flags.get(k, False)))

    def _save(self):
        self.gsm.update_global(
            api_base=self.api_base.text().strip(),
            api_key=self.api_key.text().strip(),
            refresh_ms=int(self.refresh_ms.value())
        )
        if self.module_id and self.flag_widgets:
            flags = {k: bool(cb.isChecked()) for k, cb in self.flag_widgets.items()}
            self.gsm.update_module_flags(self.module_id, flags)
        self.accept()

# ─────────────────────────────────────────────────────────────────────
# Home Screen (quick-launch)
# ─────────────────────────────────────────────────────────────────────
class HomeScreen(QWidget):
    open_app = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        ml = QVBoxLayout(self)
        ml.setContentsMargins(24, 16, 24, 16)
        ml.setSpacing(16)

        hdr = QHBoxLayout()
        hdr.setSpacing(16)
        logo_text = QLabel("\U0001f531")
        logo_text.setStyleSheet(f"color: {C['cyan']}; font-size: 48px; background: transparent;")
        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        t1 = QLabel("VEILOS")
        t1.setStyleSheet(f"color: {C['cyan']}; font-size: 28px; font-weight: bold; letter-spacing: 6px;")
        t2 = QLabel("Hospital Cybersecurity Defense Platform")
        t2.setStyleSheet(f"color: {C['text2']}; font-size: 12px;")
        title_col.addWidget(t1)
        title_col.addWidget(t2)
        hdr.addWidget(logo_text)
        hdr.addLayout(title_col)
        hdr.addStretch()

        status = QLabel("\u25cf  READY")
        status.setStyleSheet(
            f"color: {C['green']}; font-size: 11px; font-weight: bold; "
            f"background: {C['bg3']}; border: 1px solid {C['green']}; "
            "border-radius: 12px; padding: 4px 16px;"
        )
        hdr.addWidget(status)
        ml.addLayout(hdr)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background: {C['border']};")
        ml.addWidget(div)

        ql_frame = QFrame()
        ql_frame.setStyleSheet(f"QFrame {{ background: {C['bg2']}; border: 1px solid {C['border']}; border-radius: 12px; }}")
        ql_layout = QVBoxLayout(ql_frame)
        ql_layout.setContentsMargins(16, 12, 16, 12)
        ql_layout.setSpacing(12)
        ql_title = QLabel("QUICK LAUNCH")
        ql_title.setStyleSheet(f"color: {C['cyan']}; font-size: 13px; font-weight: bold; border: none;")
        ql_layout.addWidget(ql_title)

        tiles = QGridLayout()
        tiles.setSpacing(10)
        apps = [
            ("\U0001f4ca", "Security\nDashboard", C["cyan"], "dashboard"),
            ("\u2328", "Terminal", C["green"], "terminal"),
            ("\U0001f9ec", "Process\nManager", C["gold"], "process_mgr"),
            ("\u2699", "Settings", C["text2"], "settings"),
            ("\U0001f4cb", "Compliance\nHub", C["purple"], "compliance"),
            ("\U0001f916", "DeepSentinel\nML", C["pink"], "deepsentinel"),
            ("\u2694", "RedVeil\nPenTest", C["red"], "redveil"),
            ("\U0001f310", "Federation\nMesh", C["blue"], "federation"),
        ]
        for i, (icon, label, color, app_id) in enumerate(apps):
            btn = QPushButton()
            btn.setFixedSize(120, 90)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{ background: {C['bg3']}; border: 1px solid {C['border']}; border-radius: 12px; }}
                QPushButton:hover {{ background: {C['border']}; border-color: {color}; }}
            """)
            bl = QVBoxLayout(btn)
            bl.setContentsMargins(4, 8, 4, 4)
            bl.setSpacing(2)
            bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ic = QLabel(icon)
            ic.setStyleSheet(f"color: {color}; font-size: 26px; background: transparent; border: none;")
            ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lb = QLabel(label)
            lb.setStyleSheet(f"color: {C['text']}; font-size: 10px; background: transparent; border: none;")
            lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            bl.addWidget(ic)
            bl.addWidget(lb)
            btn.clicked.connect(lambda _, a=app_id: self.open_app.emit(a))
            tiles.addWidget(btn, i // 4, i % 4)

        ql_layout.addLayout(tiles)
        ql_layout.addStretch()
        ml.addWidget(ql_frame, 1)

# ─────────────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────────────
class MetricCard(QFrame):
    def __init__(self, title, value="--", color="#00e5ff"):
        super().__init__()
        self.setStyleSheet(f"QFrame {{ background: {C['bg2']}; border: 1px solid {C['border']}; border-radius: 12px; padding: 10px; }}")
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        t = QLabel(title)
        t.setStyleSheet(f"color: {C['text2']}; font-size: 10px; border: none;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.v = QLabel(value)
        self.v.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold; border: none;")
        self.v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(t)
        layout.addWidget(self.v)

    def set(self, value, color=None):
        self.v.setText(str(value))
        if color:
            self.v.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold; border: none;")

class DashboardApp(QWidget):
    status_text = pyqtSignal(str, str)

    def __init__(self, gsm, poller):
        super().__init__()
        self.gsm = gsm
        self.poller = poller

        self.setup_ui()

        self.poller.health_ready.connect(self.on_health)
        self.poller.organs_ready.connect(self.on_organs)

    def setup_ui(self):
        ml = QVBoxLayout(self)
        ml.setContentsMargins(12, 8, 12, 8)
        ml.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("SECURITY COMMAND CENTER")
        title.setStyleSheet(f"color: {C['cyan']}; font-size: 16px; font-weight: bold; letter-spacing: 2px;")
        self.conn = QLabel("\u25cf CONNECTING...")
        self.conn.setStyleSheet(f"color: {C['orange']}; font-size: 10px; font-weight: bold;")

        settings_btn = QPushButton("Settings")
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setStyleSheet(f"""
            QPushButton {{ background: {C['bg3']}; color: {C['text2']}; border: 1px solid {C['border']};
                          border-radius: 12px; padding: 4px 12px; font-size: 10px; }}
            QPushButton:hover {{ background: {C['border']}; color: {C['text']}; border-color: {C['cyan']}; }}
        """)
        settings_btn.clicked.connect(lambda: GlobalSettingsDialog(self.gsm, parent=self).exec())

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.conn)
        header.addWidget(settings_btn)
        ml.addLayout(header)

        cards = QHBoxLayout()
        cards.setSpacing(8)
        self.c_alerts = MetricCard("ACTIVE ALERTS", "--", C["red"])
        self.c_organs = MetricCard("ORGANS ONLINE", "--", C["green"])
        self.c_uptime = MetricCard("API STATUS", "--", C["cyan"])
        self.c_msos = MetricCard("MSOS MESH", "--", C["cyan"])
        self.c_version = MetricCard("API VERSION", "--", C["gold"])
        for c in [self.c_alerts, self.c_organs, self.c_uptime, self.c_msos, self.c_version]:
            cards.addWidget(c)
        ml.addLayout(cards)

        self.oscroll = QScrollArea()
        self.oscroll.setWidgetResizable(True)
        self.oscroll.setStyleSheet(f"""
            QScrollArea {{ background: {C['bg2']}; border: 1px solid {C['border']}; border-radius: 12px; }}
            QScrollBar:vertical {{ background: {C['bg']}; width: 6px; }}
            QScrollBar::handle:vertical {{ background: {C['border']}; min-height: 20px; border-radius: 3px; }}
        """)
        self.ow = QWidget()
        self.ol = QVBoxLayout(self.ow)
        self.ol.setSpacing(2)
        self.ol.setContentsMargins(10, 10, 10, 10)
        w = QLabel("Connecting to Watchtower...")
        w.setStyleSheet(f"color:{C['dim']};")
        self.ol.addWidget(w)
        self.ol.addStretch()
        self.oscroll.setWidget(self.ow)
        ml.addWidget(self.oscroll, 1)


    def on_health(self, d):
        if "_error" in d:
            self.conn.setText("\u25cf OFFLINE")
            self.conn.setStyleSheet(f"color: {C['red']}; font-size: 10px; font-weight: bold;")
            self.status_text.emit("OFFLINE", C["red"])
            self.c_uptime.set("DOWN", C["red"])
            self.c_msos.set("DOWN", C["red"])
            self.c_version.set("--", C["orange"])
            return
        self.conn.setText("\u25cf CONNECTED")
        self.conn.setStyleSheet(f"color: {C['green']}; font-size: 10px; font-weight: bold;")
        self.status_text.emit("NOMINAL", C["green"])
        self.c_uptime.set("LIVE", C["green"])
        self.c_msos.set("ACTIVE" if d.get("msos_ok") else "DOWN",
                        C["green"] if d.get("msos_ok") else C["red"])
        self.c_version.set(d.get("version", "v0.2.0"), C["gold"])
        self.c_alerts.set("0", C["green"])

    def on_organs(self, organs):
        while self.ol.count():
            it = self.ol.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        if not organs:
            self.ol.addWidget(QLabel("No organs returned."))
            self.ol.addStretch()
            self.c_organs.set("0/0", C["orange"])
            return
        active = 0
        for o in organs[:50]:
            status = str(o.get("active", o.get("status", ""))).lower()
            is_active = status in ("true", "active", "running", "1", "enabled")
            if is_active:
                active += 1
            lab = QLabel(f"{o.get('name','?'):<26}  {'ACTIVE' if is_active else 'INACTIVE'}")
            lab.setStyleSheet(f"color: {C['text'] if is_active else C['orange']}; font-family: monospace; font-size: 11px;")
            self.ol.addWidget(lab)
        self.ol.addStretch()
        self.c_organs.set(f"{active}/{len(organs)}", C["green"] if active == len(organs) else C["orange"])

# ─────────────────────────────────────────────────────────────────────
# Terminal (simple)
# ─────────────────────────────────────────────────────────────────────
class CmdRunner(QThread):
    output_ready = pyqtSignal(str)
    finished_sig = pyqtSignal(int)

    def __init__(self, cmd, cwd, env):
        super().__init__()
        self.cmd = cmd
        self.cwd = cwd
        self.env = env
        self.proc = None

    def run(self):
        full_env = os.environ.copy()
        full_env.update(self.env)
        try:
            self.proc = subprocess.Popen(
                self.cmd, shell=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, cwd=self.cwd, env=full_env,
            )
            for line in iter(self.proc.stdout.readline, b""):
                self.output_ready.emit(line.decode(errors="replace").rstrip("\n"))
            self.proc.wait()
            self.finished_sig.emit(self.proc.returncode)
        except Exception as e:
            self.output_ready.emit(f"Error: {e}")
            self.finished_sig.emit(1)

    def kill(self):
        if self.proc:
            try:
                self.proc.kill()
            except Exception:
                pass

class TerminalApp(QWidget):
    def __init__(self, gsm):
        super().__init__()
        self.gsm = gsm
        self.cwd = str(Path.home())
        self.history = []
        self.hist_idx = -1
        self.running = False
        self.runner = None
        self.env = {
            "TERM": "dumb", "COLUMNS": "120",
            "VEIL_HOME": "/opt/veilcore",
            "VEIL_API": self.gsm.api_base(),
            "VEIL_VERSION": "2.0.0",
        }
        self.setup_ui()
        self.gsm.settings_changed.connect(self.on_global_settings_changed)
        QTimer.singleShot(100, self._motd)

    def on_global_settings_changed(self, _s):
        self.env["VEIL_API"] = self.gsm.api_base()
        self._appendc(f"[GLOBAL] VEIL_API -> {self.env['VEIL_API']}", C["gold"])

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet(f"""
            QTextEdit {{
                background: {C['bg']}; color: {C['green']};
                font-family: 'Courier New', monospace; font-size: 12px;
                border: none; padding: 8px;
                selection-background-color: {C['cyan']}; selection-color: {C['bg']};
            }}
        """)
        layout.addWidget(self.output)

        row = QHBoxLayout()
        row.setContentsMargins(8, 4, 8, 6)
        row.setSpacing(4)
        self.prompt_label = QLabel(self._prompt())
        self.prompt_label.setStyleSheet(f"color:{C['cyan']}; font-family:'Courier New', monospace; font-size:12px;")
        self.input = QLineEdit()
        self.input.setStyleSheet(f"QLineEdit{{background:transparent;color:{C['green']};font-family:'Courier New', monospace;font-size:12px;border:none;}}")
        self.input.returnPressed.connect(self.on_enter)
        self.input.installEventFilter(self)
        row.addWidget(self.prompt_label)
        row.addWidget(self.input, 1)
        layout.addLayout(row)

    def _prompt(self):
        home = str(Path.home())
        d = self.cwd.replace(home, "~") if self.cwd.startswith(home) else self.cwd
        user = os.environ.get("USER", "veilcore")
        return f"{user}@hospital:{d}$ "

    def _appendc(self, text, color):
        import html as _html
        safe = _html.escape(text)
        self.output.append(f'<pre style="margin:0; color:{color}; font-family: monospace;">{safe}</pre>')
        self.output.moveCursor(QTextCursor.MoveOperation.End)

    def _motd(self):
        self._appendc("VEILOS TERMINAL", C["cyan"])
        self._appendc(f"VEIL_API (global): {self.env['VEIL_API']}", C["dim"])
        self._appendc("", C["dim"])

    def _cd(self, path):
        if not path:
            path = "~"
        target = os.path.expanduser(path)
        if not os.path.isabs(target):
            target = os.path.join(self.cwd, target)
        target = os.path.normpath(target)
        if os.path.isdir(target):
            self.cwd = target
            self.prompt_label.setText(self._prompt())
        else:
            self._appendc(f"cd: {path}: No such file or directory", C["red"])

    def on_enter(self):
        raw = self.input.text()
        self.input.clear()
        cmd = raw.strip()
        if not cmd:
            return
        self.history.append(cmd)
        self.hist_idx = -1
        self._appendc(self._prompt() + cmd, C["cyan"])

        if cmd in ("clear", "cls"):
            self.output.clear()
            return
        if cmd.startswith("cd ") or cmd == "cd":
            self._cd(cmd[3:].strip() if cmd.startswith("cd ") else "~")
            return

        if self.running:
            self._appendc("Command already running... (Ctrl+C)", C["orange"])
            return

        self.running = True
        self.input.setEnabled(False)
        self.runner = CmdRunner(cmd, self.cwd, self.env)
        self.runner.output_ready.connect(lambda line: self._appendc(line, C["green"]))
        self.runner.finished_sig.connect(self._on_done)
        self.runner.start()

    def _on_done(self, code):
        self.running = False
        self.input.setEnabled(True)
        self.input.setFocus()
        if code != 0:
            self._appendc(f"[exit {code}]", C["red"])
        self.prompt_label.setText(self._prompt())

    def eventFilter(self, obj, event):
        if obj == self.input and event.type() == event.Type.KeyPress:
            key = event.key()
            mods = event.modifiers()
            ctrl = mods & Qt.KeyboardModifier.ControlModifier

            if ctrl and key == Qt.Key.Key_L:
                self.output.clear()
                return True

            if ctrl and key == Qt.Key.Key_C:
                if self.running and self.runner:
                    self.runner.kill()
                    self._appendc("^C", C["red"])
                    self.running = False
                    self.input.setEnabled(True)
                return True

            if key == Qt.Key.Key_Up:
                if self.history:
                    if self.hist_idx == -1:
                        self.hist_idx = len(self.history) - 1
                    elif self.hist_idx > 0:
                        self.hist_idx -= 1
                    self.input.setText(self.history[self.hist_idx])
                return True

            if key == Qt.Key.Key_Down:
                if self.hist_idx >= 0:
                    self.hist_idx += 1
                    if self.hist_idx >= len(self.history):
                        self.hist_idx = -1
                        self.input.clear()
                    else:
                        self.input.setText(self.history[self.hist_idx])
                return True

        return super().eventFilter(obj, event)

# ─────────────────────────────────────────────────────────────────────
# Process Manager
# ─────────────────────────────────────────────────────────────────────
class ProcessManagerApp(QWidget):
    def __init__(self, gsm, poller):
        super().__init__()
        self.gsm = gsm
        self.poller = poller
        self.setup_ui()

        self.poller.organs_ready.connect(self._on_organs)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("ORGAN PROCESS MANAGER")
        title.setStyleSheet(f"color: {C['cyan']}; font-size: 14px; font-weight: bold; letter-spacing: 2px;")
        self.count_label = QLabel("Loading...")
        self.count_label.setStyleSheet(f"color: {C['dim']}; font-size: 10px;")

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setStyleSheet(f"""
            QPushButton {{ background: {C['bg3']}; color: {C['cyan']}; border: 1px solid {C['border']};
                          border-radius: 12px; padding: 4px 12px; font-size: 10px; }}
            QPushButton:hover {{ background: {C['border']}; }}
        """)
        btn_refresh.clicked.connect(self.poller.poll)

        settings_btn = QPushButton("Settings")
        settings_btn.setStyleSheet(btn_refresh.styleSheet())
        settings_btn.clicked.connect(lambda: GlobalSettingsDialog(self.gsm, parent=self).exec())

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.count_label)
        header.addWidget(btn_refresh)
        header.addWidget(settings_btn)
        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Organ", "Tier", "Status", "Type", "Description"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background: {C['bg2']}; color: {C['text']}; border: 1px solid {C['border']};
                gridline-color: {C['border']}; font-size: 11px; border-radius: 12px;
            }}
            QTableWidget::item {{ padding: 4px; }}
            QTableWidget::item:selected {{ background: {C['bg3']}; }}
            QHeaderView::section {{
                background: {C['bg3']}; color: {C['cyan']}; border: 1px solid {C['border']};
                padding: 4px; font-weight: bold; font-size: 10px;
            }}
        """)
        layout.addWidget(self.table)

    def _on_organs(self, organs):
        if not organs:
            self.count_label.setText("API Offline / No Data")
            self.table.setRowCount(0)
            return

        self.table.setRowCount(len(organs))
        active = 0
        tc = {"P0": C["red"], "P1": C["orange"], "P2": C["green"]}

        for i, org in enumerate(organs):
            name = org.get("name", org.get("display", "?"))
            tier = org.get("tier", "P2")
            status = str(org.get("active", org.get("status", org.get("enabled", "?"))))
            otype = org.get("type", org.get("category", "security"))
            desc = org.get("description", org.get("unit", ""))

            is_active = status.lower() in ("true", "active", "running", "1", "enabled")
            if is_active:
                active += 1

            items = [name, tier, "ACTIVE" if is_active else "INACTIVE", otype, desc]
            colors = [C["text"], tc.get(tier, C["text"]),
                      C["green"] if is_active else C["red"], C["text2"], C["dim"]]
            for j, (val, col) in enumerate(zip(items, colors)):
                item = QTableWidgetItem(val)
                item.setForeground(QColor(col))
                self.table.setItem(i, j, item)

        self.count_label.setText(f"{active}/{len(organs)} active")

# ─────────────────────────────────────────────────────────────────────
# Settings App (global editor)
# ─────────────────────────────────────────────────────────────────────
class SettingsApp(QWidget):
    def __init__(self, gsm):
        super().__init__()
        self.gsm = gsm
        self.setup_ui()
        self.gsm.settings_changed.connect(self._sync)
        self._sync(self.gsm.get())

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("SYSTEM SETTINGS (GLOBAL)")
        title.setStyleSheet(f"color: {C['cyan']}; font-size: 16px; font-weight: bold; letter-spacing: 2px;")
        layout.addWidget(title)

        frame = QFrame()
        frame.setStyleSheet(f"QFrame {{ background: {C['bg2']}; border: 1px solid {C['border']}; border-radius: 12px; }}")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(14, 12, 14, 12)
        fl.setSpacing(10)

        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)

        self.api_base = QLineEdit()
        self.api_base.setPlaceholderText(DEFAULT_API_BASE)
        form.addRow(QLabel("API Endpoint"), self.api_base)

        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("vc_*")
        form.addRow(QLabel("API Key"), self.api_key)

        self.refresh_ms = QSpinBox()
        self.refresh_ms.setRange(500, 60000)
        self.refresh_ms.setSingleStep(250)
        form.addRow(QLabel("Default Refresh (ms)"), self.refresh_ms)

        fl.addLayout(form)

        btnrow = QHBoxLayout()
        btnrow.addStretch()

        open_dialog_btn = QPushButton("Open Dialog")
        open_dialog_btn.setStyleSheet(f"QPushButton{{background:{C['bg3']};color:{C['text2']};border:1px solid {C['border']};border-radius:12px;padding:8px 16px;font-size:11px;font-weight:bold;}}")
        open_dialog_btn.clicked.connect(lambda: GlobalSettingsDialog(self.gsm, parent=self).exec())

        apply_btn = QPushButton("Apply & Save")
        apply_btn.setStyleSheet(open_dialog_btn.styleSheet())
        apply_btn.clicked.connect(self._apply)

        btnrow.addWidget(open_dialog_btn)
        btnrow.addWidget(apply_btn)
        fl.addLayout(btnrow)

        note = QLabel(f"Saved to: {GLOBAL_SETTINGS_PATH}")
        note.setStyleSheet(f"color: {C['dim']}; font-size: 10px;")
        fl.addWidget(note)

        layout.addWidget(frame)
        layout.addStretch()

    def _sync(self, _s):
        self.api_base.setText(self.gsm.api_base())
        self.api_key.setText(self.gsm.api_key())
        self.refresh_ms.setValue(self.gsm.refresh_ms())

    def _apply(self):
        self.gsm.update_global(
            api_base=self.api_base.text().strip(),
            api_key=self.api_key.text().strip(),
            refresh_ms=int(self.refresh_ms.value())
        )

# ─────────────────────────────────────────────────────────────────────
# Simple Module Apps (Compliance / DeepSentinel / RedVeil / Federation)
# ─────────────────────────────────────────────────────────────────────
class SimpleModuleApp(QWidget):
    status_text = pyqtSignal(str, str)

    def __init__(self, gsm, module_id, title, accent, default_flags, body_text, poller=None):
        super().__init__()
        self.gsm = gsm
        self.poller = poller
        self.module_id = module_id
        self.title_text = title
        self.accent = accent
        self.default_flags = default_flags or {}
        self.body_text = body_text
        self.feature_flags = self.gsm.module_flags(self.module_id, self.default_flags)

        self.setup_ui()

        if self.poller:
            self.poller.health_ready.connect(self.on_health)
        self.gsm.settings_changed.connect(self.on_global_settings_changed)

    def setup_ui(self):
        ml = QVBoxLayout(self)
        ml.setContentsMargins(12, 10, 12, 10)
        ml.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel(self.title_text)
        title.setStyleSheet(f"color: {self.accent}; font-size: 16px; font-weight: bold; letter-spacing: 2px;")
        self.conn = QLabel("\u25cf CONNECTING...")
        self.conn.setStyleSheet(f"color: {C['orange']}; font-size: 10px; font-weight: bold;")

        settings_btn = QPushButton("Settings")
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setStyleSheet(f"""
            QPushButton {{ background: {C['bg3']}; color: {C['text2']}; border: 1px solid {C['border']};
                          border-radius: 12px; padding: 4px 12px; font-size: 10px; }}
            QPushButton:hover {{ background: {C['border']}; color: {C['text']}; border-color: {self.accent}; }}
        """)
        settings_btn.clicked.connect(self.open_settings)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.conn)
        header.addWidget(settings_btn)
        ml.addLayout(header)

        body = QFrame()
        body.setStyleSheet(f"QFrame {{ background: {C['bg2']}; border: 1px solid {C['border']}; border-radius: 12px; }}")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(14, 12, 14, 12)
        bl.setSpacing(10)

        self.body_label = QLabel(self.body_text)
        self.body_label.setStyleSheet(f"color: {C['text2']}; font-size: 11px;")
        self.body_label.setWordWrap(True)

        self.endpoint_label = QLabel(f"Endpoint (global): {self.gsm.api_base()}")
        self.endpoint_label.setStyleSheet(f"color: {C['dim']}; font-size: 10px;")

        enabled = [k for k, v in self.feature_flags.items() if v]
        self.flags_label = QLabel(f"Flags: {', '.join(enabled) or '(none)'}")
        self.flags_label.setStyleSheet(f"color: {C['dim']}; font-size: 10px;")

        bl.addWidget(self.body_label)
        bl.addWidget(self.endpoint_label)
        bl.addWidget(self.flags_label)
        bl.addStretch()

        ml.addWidget(body, 1)

    def open_settings(self):
        GlobalSettingsDialog(
            self.gsm,
            module_id=self.module_id,
            module_title=self.title_text,
            module_accent=self.accent,
            module_default_flags=self.default_flags,
            parent=self
        ).exec()

    def on_global_settings_changed(self, _s):
        self.feature_flags = self.gsm.module_flags(self.module_id, self.default_flags)
        self.endpoint_label.setText(f"Endpoint (global): {self.gsm.api_base()}")
        enabled = [k for k, v in self.feature_flags.items() if v]
        self.flags_label.setText(f"Flags: {', '.join(enabled) or '(none)'}")

    def on_health(self, d):
        if "_error" in d:
            self.conn.setText("\u25cf OFFLINE")
            self.conn.setStyleSheet(f"color: {C['red']}; font-size: 10px; font-weight: bold;")
            self.status_text.emit("OFFLINE", C["red"])
            return
        self.conn.setText("\u25cf CONNECTED")
        self.conn.setStyleSheet(f"color: {C['green']}; font-size: 10px; font-weight: bold;")
        self.status_text.emit("NOMINAL", C["green"])

class ComplianceHubApp(SimpleModuleApp):
    def __init__(self, gsm, poller):
        super().__init__(
            gsm=gsm, module_id="compliance", title="COMPLIANCE HUB",
            accent=C["purple"],
            default_flags={"Auto Evidence Packs": True, "SOC2 Delta Report": False, "FedRAMP Export": True},
            body_text="Compliance mappings and evidence export.\n\nPlanned: Framework coverage, control mapping, evidence packs.",
            poller=poller
        )

class DeepSentinelApp(SimpleModuleApp):
    def __init__(self, gsm, poller):
        super().__init__(
            gsm=gsm, module_id="deepsentinel", title="DEEPSENTINEL ML",
            accent=C["pink"],
            default_flags={"Anomaly Stream": True, "Drift Monitor": True, "Auto Triage": False},
            body_text="Anomaly detection & ML triage.\n\nPlanned: Live anomaly stream, baselines, model drift.",
            poller=poller
        )

class RedVeilApp(SimpleModuleApp):
    def __init__(self, gsm, poller):
        super().__init__(
            gsm=gsm, module_id="redveil", title="REDVEIL PENTEST",
            accent=C["red"],
            default_flags={"Safe Mode": True, "Auth-required scans": True, "Report Generator": True},
            body_text="Pen-testing toolkit.\n\nPlanned: Safe checks, authorized scans, reporting.",
            poller=poller
        )

class FederationMeshApp(SimpleModuleApp):
    def __init__(self, gsm, poller):
        super().__init__(
            gsm=gsm, module_id="federation", title="FEDERATION MESH",
            accent=C["blue"],
            default_flags={"Site Heartbeats": True, "Tunnel Monitor": True, "Auto Re-route": False},
            body_text="Multi-site federation.\n\nPlanned: Site status, secure tunnels, replication.",
            poller=poller
        )

# ─────────────────────────────────────────────────────────────────────
# MDI Sub-Window Guard (prevents maximize-gets-stuck)
# ─────────────────────────────────────────────────────────────────────
class MdiSubWindowGuard(QObject):
    """Event filter: if a sub-window enters maximized state, revert to normal."""
    def eventFilter(self, obj, event):
        if event.type() == event.Type.WindowStateChange:
            if isinstance(obj, QMdiSubWindow) and obj.isMaximized():
                QTimer.singleShot(0, obj.showNormal)
        return False

# ─────────────────────────────────────────────────────────────────────
# VeilOS Desktop (QMdiArea window manager)
# ─────────────────────────────────────────────────────────────────────
class VeilOSDesktop(QMainWindow):
    def __init__(self, gsm):
        super().__init__()
        self.gsm = gsm
        self.setWindowTitle("VeilOS - Hospital Cybersecurity Platform")
        self.setMinimumSize(900, 650)

        self.menu_open = False
        self._notif_y = 10
        self._window_buttons = {}
        self._open_apps = {}
        self._sub_guard = MdiSubWindowGuard()
        self.poller = SharedApiPoller(self.gsm)
        self.setup_ui()
        self.setup_shortcuts()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        central.setStyleSheet(f"background-color: {C['bg']};")
        main = QVBoxLayout(central)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        self.mdi = QMdiArea()
        self.mdi.setStyleSheet(f"""
            QMdiArea {{ background-color: {C['bg']}; border: none; }}
            QMdiSubWindow {{ background: {C['bg2']}; border: 1px solid {C['border2']}; border-radius: 12px; }}
            QMdiSubWindow::title {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1a2332, stop:1 #111827);
                color: {C['cyan']}; font-weight: bold; font-size: 11px; height: 26px; padding-left: 8px;
            }}
        """)
        self.mdi.setOption(QMdiArea.AreaOption.DontMaximizeSubWindowOnActivation)
        self.mdi.setBackground(QBrush(QColor(C["bg"])))

        self.desktop_widget = QWidget(self.mdi.viewport())
        self.desktop_widget.setStyleSheet("background: transparent;")
        self.desktop_widget.lower()
        self._setup_desktop_icons()

        main.addWidget(self.mdi, 1)

        # Taskbar
        taskbar = QFrame()
        taskbar.setFixedHeight(42)
        taskbar.setStyleSheet(f"QFrame {{ background-color: {C['bg2']}; border-top: 1px solid {C['border']}; }}")
        tb = QHBoxLayout(taskbar)
        tb.setContentsMargins(4, 0, 8, 0)
        tb.setSpacing(4)

        self.start_btn = QPushButton("\U0001f531 VeilOS")
        self.start_btn.setFixedSize(110, 34)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00394d, stop:1 #002233);
                color: {C['cyan']}; border: 1px solid {C['border']}; border-radius: 12px;
                font-size: 12px; font-weight: bold; letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #004d66, stop:1 #003344);
                border-color: {C['cyan']};
            }}
        """)
        self.start_btn.clicked.connect(self.toggle_menu)
        tb.addWidget(self.start_btn)

        sep = QFrame()
        sep.setFixedSize(1, 28)
        sep.setStyleSheet(f"background: {C['border']};")
        tb.addWidget(sep)

        self.window_list = QHBoxLayout()
        self.window_list.setSpacing(2)
        tb.addLayout(self.window_list)
        tb.addStretch()

        self.tray_status = QLabel("\u25cf NOMINAL")
        self.tray_status.setStyleSheet(f"color: {C['green']}; font-size: 10px; font-weight: bold;")
        self.clock = QLabel()
        self.clock.setStyleSheet(f"color: {C['text2']}; font-size: 11px;")

        tb.addWidget(self.tray_status)
        sep2 = QFrame()
        sep2.setFixedSize(1, 28)
        sep2.setStyleSheet(f"background: {C['border']};")
        tb.addWidget(sep2)
        tb.addWidget(self.clock)

        main.addWidget(taskbar)

        # Start menu
        self.start_menu = QFrame(central)
        self.start_menu.setFixedSize(320, 540)
        self.start_menu.hide()
        self.start_menu.setStyleSheet(f"QFrame {{ background-color: {C['bg2']}; border: 1px solid {C['cyan']}; border-radius: 14px; }}")
        self._build_start_menu()

        self.ctimer = QTimer(self)
        self.ctimer.timeout.connect(self.tick)
        self.ctimer.start(1000)
        self.tick()

        self.mdi.subWindowActivated.connect(self._on_window_activated)

    def _setup_desktop_icons(self):
        icons = [
            ("\U0001f3e0", "Home", C["cyan"], self.open_home),
            ("\U0001f4ca", "Dashboard", C["cyan"], self.open_dashboard),
            ("\u2328", "Terminal", C["green"], self.open_terminal),
            ("\U0001f9ec", "Organs", C["gold"], self.open_process_mgr),
            ("\U0001f4cb", "Compliance", C["purple"], self.open_compliance),
            ("\U0001f916", "DeepSentinel", C["pink"], self.open_deepsentinel),
            ("\u2694", "RedVeil", C["red"], self.open_redveil),
            ("\U0001f310", "Federation", C["blue"], self.open_federation),
            ("\u2699", "Settings", C["text2"], self.open_settings),
        ]
        grid = QGridLayout(self.desktop_widget)
        grid.setContentsMargins(20, 20, 20, 20)
        grid.setSpacing(10)
        grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        for i, (ic, label, color, cb) in enumerate(icons):
            icon = DesktopIcon(ic, label, color)
            icon.double_clicked.connect(cb)
            grid.addWidget(icon, i % 6, i // 6)

    def _build_start_menu(self):
        sm = QVBoxLayout(self.start_menu)
        sm.setContentsMargins(8, 12, 8, 8)
        sm.setSpacing(2)

        smh = QLabel("\U0001f531 VEILOS APPLICATIONS")
        smh.setStyleSheet(f"color: {C['cyan']}; font-size: 13px; font-weight: bold; letter-spacing: 2px; padding: 4px 8px; border: none;")
        sm.addWidget(smh)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {C['border']}; border: none;")
        sm.addWidget(sep)

        apps = [
            ("\U0001f3e0", "Home", "System overview", C["cyan"], self.open_home),
            ("\U0001f4ca", "Security Dashboard", "Real-time monitoring", C["cyan"], self.open_dashboard),
            ("\u2328", "Terminal", "Linux shell", C["green"], self.open_terminal),
            ("\U0001f9ec", "Process Manager", "82 security organs", C["gold"], self.open_process_mgr),
            ("\u2699", "Settings", "Global API settings", C["text2"], self.open_settings),
            ("\U0001f4cb", "Compliance Hub", "Framework evidence", C["purple"], self.open_compliance),
            ("\U0001f310", "Federation", "Multi-site mesh", C["blue"], self.open_federation),
            ("\U0001f916", "DeepSentinel ML", "Anomaly detection", C["pink"], self.open_deepsentinel),
            ("\u2694", "RedVeil", "Pen testing", C["red"], self.open_redveil),
        ]
        for icon, name, desc, color, cb in apps:
            btn = QPushButton()
            btn.setFixedHeight(44)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"QPushButton{{background:transparent;border:none;border-radius:10px;padding:4px 8px;}} QPushButton:hover{{background:{C['bg3']};}}")
            bl = QHBoxLayout(btn)
            bl.setContentsMargins(8, 2, 8, 2)
            bl.setSpacing(10)
            il = QLabel(icon)
            il.setStyleSheet(f"color:{color};font-size:22px;")
            il.setFixedWidth(32)
            il.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tl = QVBoxLayout()
            tl.setSpacing(0)
            n = QLabel(name)
            n.setStyleSheet(f"color:{C['text']};font-size:12px;font-weight:bold;")
            d = QLabel(desc)
            d.setStyleSheet(f"color:{C['dim']};font-size:9px;")
            tl.addWidget(n); tl.addWidget(d)
            bl.addWidget(il); bl.addLayout(tl, 1)

            def make_handler(callback):
                def handler():
                    callback()
                    self.toggle_menu()
                return handler
            btn.clicked.connect(make_handler(cb))
            sm.addWidget(btn)

        sm.addStretch()

        wm_row = QHBoxLayout()
        for label, action in [("Tile", self.mdi.tileSubWindows),
                             ("Cascade", self.mdi.cascadeSubWindows),
                             ("Close All", self._close_all_windows)]:
            b = QPushButton(label)
            b.setStyleSheet(f"QPushButton{{background:{C['bg3']};color:{C['text2']};border:1px solid {C['border']};border-radius:10px;padding:3px 10px;font-size:10px;}} QPushButton:hover{{background:{C['border']};color:{C['text']};}}")
            b.clicked.connect(action)
            wm_row.addWidget(b)
        sm.addLayout(wm_row)

        footer = QLabel("Global settings propagate to ALL apps + terminal.")
        footer.setStyleSheet(f"color:{C['dim']};font-size:9px;padding:6px;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sm.addWidget(footer)

    # ── Window management (singleton + taskbar button)
    def _add_mdi_window(self, widget, title, size=(900, 600), app_type=None):
        if app_type and app_type in self._open_apps:
            existing = self._open_apps[app_type]
            try:
                if existing and existing.widget():
                    self._activate_window(existing)
                    return existing
            except RuntimeError:
                self._open_apps.pop(app_type, None)

        sub = QMdiSubWindow()
        sub.setWidget(widget)
        sub.setWindowTitle(title)
        sub.resize(*size)
        sub.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.mdi.addSubWindow(sub)
        sub.installEventFilter(self._sub_guard)  # prevent maximize-gets-stuck
        sub.show()
        sub.raise_()
        self.desktop_widget.lower()

        self._add_taskbar_button(sub, title)

        if app_type:
            self._open_apps[app_type] = sub

        def _on_destroyed():
            self._remove_taskbar_button(sub)
            for k in list(self._open_apps):
                if self._open_apps.get(k) is sub:
                    self._open_apps.pop(k, None)
                    break
        sub.destroyed.connect(_on_destroyed)
        return sub

    def _add_taskbar_button(self, sub, title):
        ctr = QWidget()
        ctr.setFixedHeight(28)
        hl = QHBoxLayout(ctr)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)

        btn = QPushButton(title[:18])
        btn.setFixedHeight(28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{ background:{C['bg3']}; color:{C['text2']}; border:1px solid {C['border']};
                           border-radius:10px; padding:0 8px; font-size:10px;
                           border-top-right-radius:0; border-bottom-right-radius:0; }}
            QPushButton:hover {{ background:{C['border']}; color:{C['text']}; }}
        """)
        btn.clicked.connect(lambda: self._toggle_window(sub))

        xb = QPushButton("\u2715")
        xb.setFixedSize(24, 28)
        xb.setCursor(Qt.CursorShape.PointingHandCursor)
        xb.setStyleSheet(f"""
            QPushButton {{ background:{C['bg3']}; color:{C['dim']}; border:1px solid {C['border']}; border-left:none;
                           font-size:11px; font-weight:bold; border-top-right-radius:10px; border-bottom-right-radius:10px; }}
            QPushButton:hover {{ background:{C['red']}; color:white; }}
        """)
        xb.clicked.connect(lambda: sub.close())

        hl.addWidget(btn)
        hl.addWidget(xb)
        self.window_list.addWidget(ctr)
        self._window_buttons[id(sub)] = ctr

    def _remove_taskbar_button(self, sub):
        w = self._window_buttons.pop(id(sub), None)
        if w:
            self.window_list.removeWidget(w)
            w.deleteLater()

    def _activate_window(self, sub):
        if sub.isMinimized():
            sub.showNormal()
        if sub.isHidden():
            sub.show()
        sub.raise_()
        self.mdi.setActiveSubWindow(sub)
        sub.setFocus()

    def _toggle_window(self, sub):
        """Taskbar click: if active & visible → minimize; otherwise → activate."""
        if sub.isMinimized() or sub.isHidden():
            self._activate_window(sub)
        elif self.mdi.activeSubWindow() is sub:
            sub.showMinimized()
        else:
            self._activate_window(sub)

    def _on_window_activated(self, sub):
        for sid, ctr in list(self._window_buttons.items()):
            try:
                btns = ctr.findChildren(QPushButton)
                btn = btns[0] if btns else None
            except Exception:
                continue
            if not btn:
                continue
            if sub and sid == id(sub):
                btn.setStyleSheet(f"""
                    QPushButton {{ background:{C['border']}; color:{C['cyan']}; border:1px solid {C['cyan']};
                                   border-radius:10px; padding:0 8px; font-size:10px; font-weight:bold;
                                   border-top-right-radius:0; border-bottom-right-radius:0; }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{ background:{C['bg3']}; color:{C['text2']}; border:1px solid {C['border']};
                                   border-radius:10px; padding:0 8px; font-size:10px;
                                   border-top-right-radius:0; border-bottom-right-radius:0; }}
                    QPushButton:hover {{ background:{C['border']}; color:{C['text']}; }}
                """)

    # ── Launchers
    def open_home(self):
        home = HomeScreen()
        home.open_app.connect(self._home_launch)
        w = max(self.mdi.width() - 20, 900)
        h = max(self.mdi.height() - 20, 600)
        self._add_mdi_window(home, "\U0001f3e0 Home", (w, h), app_type="home")

    def _home_launch(self, app_id):
        dispatch = {
            "dashboard": self.open_dashboard,
            "terminal": self.open_terminal,
            "process_mgr": self.open_process_mgr,
            "settings": self.open_settings,
            "compliance": self.open_compliance,
            "deepsentinel": self.open_deepsentinel,
            "redveil": self.open_redveil,
            "federation": self.open_federation,
        }
        dispatch.get(app_id, self.open_dashboard)()

    def open_dashboard(self):
        dash = DashboardApp(self.gsm, self.poller)
        dash.status_text.connect(self._update_tray)
        self._add_mdi_window(dash, "Security Dashboard", (980, 640), app_type="dashboard")

    def open_terminal(self):
        self._add_mdi_window(TerminalApp(self.gsm), "Terminal", (820, 520), app_type="terminal")

    def open_process_mgr(self):
        self._add_mdi_window(ProcessManagerApp(self.gsm, self.poller), "Process Manager", (980, 560), app_type="process_mgr")

    def open_settings(self):
        self._add_mdi_window(SettingsApp(self.gsm), "Settings", (760, 480), app_type="settings")

    def open_compliance(self):
        app = ComplianceHubApp(self.gsm, self.poller)
        app.status_text.connect(self._update_tray)
        self._add_mdi_window(app, "Compliance Hub", (980, 640), app_type="compliance")

    def open_deepsentinel(self):
        app = DeepSentinelApp(self.gsm, self.poller)
        app.status_text.connect(self._update_tray)
        self._add_mdi_window(app, "DeepSentinel ML", (980, 640), app_type="deepsentinel")

    def open_redveil(self):
        app = RedVeilApp(self.gsm, self.poller)
        app.status_text.connect(self._update_tray)
        self._add_mdi_window(app, "RedVeil", (980, 640), app_type="redveil")

    def open_federation(self):
        app = FederationMeshApp(self.gsm, self.poller)
        app.status_text.connect(self._update_tray)
        self._add_mdi_window(app, "Federation Mesh", (980, 640), app_type="federation")

    def _update_tray(self, text, color):
        self.tray_status.setText(f"\u25cf {text}")
        self.tray_status.setStyleSheet(f"color:{color}; font-size:10px; font-weight:bold;")

    # ── Notifications
    def notify(self, title, message, severity="info"):
        toast = NotificationToast(self.centralWidget(), title, message, severity)
        toast.move(self.centralWidget().width() - 330, self._notif_y)
        self._notif_y += 80
        if self._notif_y > 400:
            self._notif_y = 10
        QTimer.singleShot(4500, lambda: setattr(self, "_notif_y", max(10, self._notif_y - 80)))

    # ── Shortcuts
    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Alt+H"), self, self.open_home)
        QShortcut(QKeySequence("Ctrl+Alt+T"), self, self.open_terminal)
        QShortcut(QKeySequence("Ctrl+Alt+D"), self, self.open_dashboard)
        QShortcut(QKeySequence("Ctrl+Alt+P"), self, self.open_process_mgr)
        QShortcut(QKeySequence("F11"), self, self.toggle_fullscreen)
        QShortcut(QKeySequence("Ctrl+W"), self, self._close_active)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _close_active(self):
        sub = self.mdi.activeSubWindow()
        if sub:
            sub.close()

    def _close_all_windows(self):
        for sub in list(self.mdi.subWindowList()):
            sub.close()
        self._open_apps.clear()

    # ── Context menu
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background:{C['bg2']}; color:{C['text']}; border:1px solid {C['border']}; padding:4px; font-size:11px; }}
            QMenu::item {{ padding:6px 24px; border-radius:10px; }}
            QMenu::item:selected {{ background:{C['bg3']}; color:{C['cyan']}; }}
            QMenu::separator {{ height:1px; background:{C['border']}; margin:4px 8px; }}
        """)
        menu.addAction("Home", self.open_home)
        menu.addAction("Dashboard", self.open_dashboard)
        menu.addAction("Terminal", self.open_terminal)
        menu.addAction("Process Manager", self.open_process_mgr)
        menu.addSeparator()
        menu.addAction("Compliance Hub", self.open_compliance)
        menu.addAction("DeepSentinel ML", self.open_deepsentinel)
        menu.addAction("RedVeil", self.open_redveil)
        menu.addAction("Federation Mesh", self.open_federation)
        menu.addSeparator()
        menu.addAction("Global Settings", lambda: GlobalSettingsDialog(self.gsm, parent=self).exec())
        menu.addSeparator()
        menu.addAction("Tile Windows", self.mdi.tileSubWindows)
        menu.addAction("Cascade Windows", self.mdi.cascadeSubWindows)
        menu.addAction("Close All Windows", self._close_all_windows)
        menu.exec(event.globalPos())

    # ── Start menu
    def toggle_menu(self):
        if self.menu_open:
            self.start_menu.hide()
        else:
            x = 4
            y = self.centralWidget().height() - 42 - self.start_menu.height() - 4
            self.start_menu.move(x, y)
            self.start_menu.show()
            self.start_menu.raise_()
        self.menu_open = not self.menu_open

    # ── Clock
    def tick(self):
        self.clock.setText(datetime.now().strftime("%a %b %d  %H:%M:%S"))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "desktop_widget"):
            vp = self.mdi.viewport()
            self.desktop_widget.setGeometry(0, 0, vp.width(), vp.height())

# ─────────────────────────────────────────────────────────────────────
# Main App (Splash -> Desktop) with robust failure logging
# ─────────────────────────────────────────────────────────────────────
class VeilOSApp:
    def __init__(self):
        _ensure_global_dir()
        log("=== VeilOS starting ===")
        log(f"DISPLAY={os.environ.get('DISPLAY','')}, WAYLAND_DISPLAY={os.environ.get('WAYLAND_DISPLAY','')}, QT_QPA_PLATFORM={os.environ.get('QT_QPA_PLATFORM','')}")
        log(f"LOG_PATH={LOG_PATH}")

        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setStyle("Fusion")

        # palette
        p = QPalette()
        p.setColor(QPalette.ColorRole.Window, QColor(C["bg"]))
        p.setColor(QPalette.ColorRole.WindowText, QColor(C["text"]))
        p.setColor(QPalette.ColorRole.Base, QColor(C["bg"]))
        p.setColor(QPalette.ColorRole.Text, QColor(C["text"]))
        p.setColor(QPalette.ColorRole.Highlight, QColor(C["cyan"]))
        p.setColor(QPalette.ColorRole.HighlightedText, QColor(C["bg"]))
        p.setColor(QPalette.ColorRole.Button, QColor(C["bg2"]))
        p.setColor(QPalette.ColorRole.ButtonText, QColor(C["text"]))
        self.app.setPalette(p)

        self.gsm = GlobalSettingsManager()

        # Screen sizing
        screen = self.app.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            self._sw, self._sh = geom.width(), geom.height()
        else:
            self._sw, self._sh = 1280, 720

        # Splash window
        self.splash_win = QMainWindow()
        self.splash_win.setWindowTitle("VeilOS")
        self.splash_win.resize(self._sw, self._sh)

        self.splash = SplashScreen()
        self.splash.finished.connect(self._on_splash_done)
        self.splash_win.setCentralWidget(self.splash)
        self.splash_win.show()

        log("Splash shown.")

    def _on_splash_done(self):
        log("Splash finished -> launching desktop.")
        try:
            self.desktop = VeilOSDesktop(self.gsm)
            self.desktop.resize(self._sw, self._sh)
            self.desktop.show()

            # Close splash after desktop is visible
            self.splash_win.hide()
            QTimer.singleShot(150, self.splash_win.close)

            # Auto-open Home
            QTimer.singleShot(250, self.desktop.open_home)

            # Welcome notification
            QTimer.singleShot(800, lambda: self.desktop.notify(
                "VeilOS Initialized",
                f"Global settings: {GLOBAL_SETTINGS_PATH}",
                "info"
            ))

        except Exception:
            # keep splash visible and show error text
            log_exc("Desktop creation failed:")
            self.splash.set_fail("DESKTOP FAILED TO START.\n\nCheck:\n~/.config/veilcore/veilui.log\n\nMost recent error was logged.")
            # do NOT exit; keep UI visible so user isn't stuck “loading”

    def run(self):
        rc = self.app.exec()
        log(f"VeilOS exit rc={rc}")
        sys.exit(rc)

# ─────────────────────────────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Make Qt behave on minimal GPU setups
    os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")
    os.environ.setdefault("GALLIUM_DRIVER", "llvmpipe")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")

    # If user is on Wayland, don't force xcb unless they already set it.
    # (Your logs show WAYLAND_DISPLAY=wayland-0 sometimes.)
    if "QT_QPA_PLATFORM" not in os.environ or not os.environ.get("QT_QPA_PLATFORM"):
        if os.environ.get("WAYLAND_DISPLAY"):
            os.environ["QT_QPA_PLATFORM"] = "wayland"
        else:
            os.environ["QT_QPA_PLATFORM"] = "xcb"

    log(f"QT_QPA_PLATFORM(selected)={os.environ.get('QT_QPA_PLATFORM','')}")
    VeilOSApp().run()
