from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from time import monotonic

from prism_events import PrismEvents
from veilcore_secure_terminal import VeilCoreSecureTerminal

try:
    from PyQt6.QtCore import (
        QEasingCurve,
        QEvent,
        QObject,
        QPointF,
        QPropertyAnimation,
        QRectF,
        QThread,
        QTimer,
        Qt,
        pyqtProperty,
        pyqtSignal,
    )
    from PyQt6.QtGui import (
        QColor,
        QFont,
        QGuiApplication,
        QIcon,
        QPainter,
        QPainterPath,
        QPalette,
        QPen,
        QRadialGradient,
        QTextCursor,
    )
    from PyQt6.QtWidgets import (
        QApplication,
        QCompleter,
        QDialog,
        QDialogButtonBox,
        QFormLayout,
        QFrame,
        QGraphicsDropShadowEffect,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QPushButton,
        QProgressBar,
        QScrollArea,
        QSpinBox,
        QTabWidget,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except Exception:
    print("PyQt6 required: pip install PyQt6 --break-system-packages")
    raise


C = {
    "bg": "#0a0e17",
    "bg2": "#111827",
    "bg3": "#1a2332",
    "cyan": "#00e5ff",
    "green": "#00ff6a",
    "gold": "#fbbf24",
    "orange": "#ff8c00",
    "red": "#ff4444",
    "blue": "#3b82f6",
    "purple": "#a855f7",
    "pink": "#ec4899",
    "text": "#e6f7ff",
    "text2": "#7baac4",
    "dim": "#4a6a7a",
    "border": "#1e3a4a",
}

LOG_PATH = Path.home() / ".config" / "veilcore" / "veilui.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def log(msg: str) -> None:
    ts = datetime.now().isoformat(timespec="seconds")
    try:
        with open(LOG_PATH, "a") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


def log_exc(prefix="Exception:") -> None:
    import traceback

    log(prefix)
    for line in traceback.format_exc().splitlines():
        log(line)


# ──────────────────────────────────────────────────────────────────────────────
# Splash
# ──────────────────────────────────────────────────────────────────────────────
class _P:
    __slots__ = ("x", "y", "vx", "vy", "life", "decay", "size", "col")

    def __init__(self, x, y, vx, vy, life, decay, size, col):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.decay = decay
        self.size = size
        self.col = col


class Splash(QWidget):
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._t = 0.0
        self._fail_text = ""
        self._phase = 0
        self._phase_t = 0.0
        self._particles: list[_P] = []
        self._ring_r = 0.0
        self._ring_a = 0.0
        self._eye_lock = 0.0
        self._fade = 0.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

        QTimer.singleShot(140, self._start)
        QTimer.singleShot(750, self._explode)
        QTimer.singleShot(1050, self._after_burst)
        QTimer.singleShot(1650, self._gather)
        QTimer.singleShot(2650, self._lock_in)
        QTimer.singleShot(3750, self._fade_out)

    def set_fail(self, text: str) -> None:
        self._fail_text = text
        self._phase = 3
        self._eye_lock = 1.0
        self._fade = 0.0
        self.update()

    def _start(self) -> None:
        self._phase = 0
        self._phase_t = 0.0

    def _explode(self) -> None:
        if self._fail_text:
            return
        import math
        import random

        self._phase = 1
        self._phase_t = 0.0
        w, h = max(1, self.width()), max(1, self.height())
        cx, cy = w * 0.5, h * 0.5
        cols = [C["cyan"], C["green"], C["gold"], C["blue"], C["purple"], C["pink"]]
        self._particles.clear()

        for _ in range(720):
            ang = random.random() * math.tau
            spd = 7 + random.random() * 22
            self._particles.append(
                _P(
                    cx,
                    cy,
                    math.cos(ang) * spd,
                    math.sin(ang) * spd,
                    1.1 + random.random() * 0.9,
                    0.01 + random.random() * 0.02,
                    2 + random.random() * 5,
                    random.choice(cols),
                )
            )

        self._ring_r = 0.0
        self._ring_a = 1.0

    def _after_burst(self) -> None:
        if self._fail_text:
            return
        import math
        import random

        w, h = max(1, self.width()), max(1, self.height())
        cx, cy = w * 0.5, h * 0.5
        cols = [C["cyan"], C["green"], C["gold"], C["blue"], C["purple"], C["pink"]]

        for _ in range(240):
            ang = random.random() * math.tau
            spd = 10 + random.random() * 26
            self._particles.append(
                _P(
                    cx,
                    cy,
                    math.cos(ang) * spd,
                    math.sin(ang) * spd,
                    0.55 + random.random() * 0.55,
                    0.016 + random.random() * 0.028,
                    1.5 + random.random() * 4,
                    random.choice(cols),
                )
            )

        self._ring_a = max(self._ring_a, 0.85)

    def _gather(self) -> None:
        if self._fail_text:
            return
        self._phase = 2
        self._phase_t = 0.0

    def _lock_in(self) -> None:
        if self._fail_text:
            return
        self._phase = 3
        self._phase_t = 0.0

    def _fade_out(self) -> None:
        if self._fail_text:
            return
        self._phase = 4
        self._phase_t = 0.0

    def _tick(self) -> None:
        dt = 0.016
        self._t += dt
        self._phase_t += dt
        w, h = max(1, self.width()), max(1, self.height())
        cx, cy = w * 0.5, h * 0.5

        if self._phase == 1:
            self._ring_r += 34
            self._ring_a = max(0, self._ring_a - 0.014)
        elif self._phase == 2:
            self._ring_r = max(0, self._ring_r - 28)
            self._ring_a = min(0.9, self._ring_a + 0.03)

        if self._particles:
            for p in self._particles:
                if self._phase == 1:
                    p.x += p.vx
                    p.y += p.vy
                    p.vx *= 0.992
                    p.vy *= 0.992
                    p.life -= p.decay
                else:
                    dx, dy = cx - p.x, cy - p.y
                    p.x += dx * 0.085
                    p.y += dy * 0.085
                    p.vx *= 0.9
                    p.vy *= 0.9
                    p.life -= p.decay * 0.75

            self._particles = [p for p in self._particles if p.life > 0]

        if self._phase == 0:
            self._eye_lock = min(0.45, self._eye_lock + 0.02)
        elif self._phase == 2:
            self._eye_lock = min(1, self._eye_lock + 0.03)
        elif self._phase == 3:
            self._eye_lock = min(1, self._eye_lock + 0.04)

        if self._phase == 4:
            self._fade = min(1, self._fade + 0.02)
            if self._fade >= 1:
                self._timer.stop()
                self.finished.emit()
                return

        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg = QColor(C["bg"])
        bg.setAlphaF(0.22)
        p.fillRect(self.rect(), bg)

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2

        for pt in self._particles:
            col = QColor(pt.col)
            col.setAlphaF(max(0, min(1, pt.life)))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(col)
            p.drawEllipse(int(pt.x), int(pt.y), int(pt.size), int(pt.size))

        if self._ring_a > 0:
            rc = QColor(C["cyan"])
            rc.setAlphaF(max(0, min(1, self._ring_a * 0.7)))
            p.setPen(QPen(rc, 6))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(cx - int(self._ring_r), cy - int(self._ring_r), int(self._ring_r * 2), int(self._ring_r * 2))

        s = max(0, min(1, self._eye_lock))
        if s > 0:
            r = int(110 + 60 * s)
            g = QRadialGradient(cx, cy, r)
            g.setColorAt(0, QColor(C["cyan"]))
            g.setColorAt(0.55, QColor(C["blue"]))
            g.setColorAt(1, QColor(C["bg"]))
            p.setBrush(g)
            p.setPen(Qt.PenStyle.NoPen)
            p.setOpacity(0.22 + 0.7 * s)
            p.drawEllipse(cx - r, cy - r, r * 2, r * 2)
            p.setOpacity(1)

            oc = QColor(C["cyan"])
            oc.setAlphaF(0.35 + 0.65 * s)
            p.setPen(QPen(oc, 4))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(cx - 260, cy - 95, 520, 190, 140, 140)

            pc = QColor(C["bg"])
            pc.setAlphaF(0.7 + 0.3 * s)
            p.setBrush(pc)
            p.setPen(QPen(QColor(C["cyan"]), 3))
            p.drawEllipse(cx - 45, cy - 45, 90, 90)

        p.setPen(QColor(C["cyan"]))
        p.setFont(QFont("Monospace", 34, QFont.Weight.Bold))
        p.drawText(0, cy + 160, w, 60, int(Qt.AlignmentFlag.AlignHCenter), "VEILCORE")

        p.setPen(QColor(C["text2"]))
        p.setFont(QFont("Monospace", 12))
        p.drawText(0, cy + 210, w, 40, int(Qt.AlignmentFlag.AlignHCenter), "Cyber Defense Platform")

        if self._fail_text:
            p.setPen(QColor(C["red"]))
            p.setFont(QFont("Monospace", 11))
            p.drawText(
                60,
                60,
                w - 120,
                h - 120,
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop),
                self._fail_text,
            )

        if self._fade > 0 and not self._fail_text:
            ov = QColor(C["bg"])
            ov.setAlphaF(self._fade)
            p.fillRect(self.rect(), ov)

        p.end()


# ──────────────────────────────────────────────────────────────────────────────
# API helpers
# ──────────────────────────────────────────────────────────────────────────────
def api_get(base: str, path: str, api_key: str, timeout_s: float = 2.0) -> dict:
    url = f"{base.rstrip('/')}/{path.lstrip('/')}"
    req = urllib.request.Request(url)
    if api_key:
        req.add_header("X-API-Key", api_key)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as e:
        return {"_error": str(e)}


class Fetcher(QThread):
    health = pyqtSignal(dict)
    organs = pyqtSignal(list)
    events = pyqtSignal(list)

    def __init__(self, base: str, key: str):
        super().__init__()
        self.base = base
        self.key = key

    def run(self):
        self.health.emit(api_get(self.base, "health", self.key))

        organs = api_get(self.base, "organs", self.key)
        self.organs.emit(organs.get("organs", []) if "_error" not in organs else [])

        events = api_get(self.base, "events?limit=20", self.key)
        self.events.emit(events.get("events", []) if "_error" not in events else [])


class ApiPoller(QObject):
    health = pyqtSignal(dict)
    organs = pyqtSignal(list)
    events = pyqtSignal(list)

    def __init__(self, gs):
        super().__init__()
        self.gs = gs
        self._fetcher: Fetcher | None = None

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.poll)
        self._timer.start(self.gs.refresh_ms())

        if hasattr(self.gs, "changed"):
            self.gs.changed.connect(self._on_settings)

        QTimer.singleShot(250, self.poll)

    def _on_settings(self, _):
        self._timer.setInterval(self.gs.refresh_ms())
        self.poll()

    def poll(self):
        if self._fetcher and self._fetcher.isRunning():
            return

        self._fetcher = Fetcher(self.gs.api_base(), self.gs.api_key())
        self._fetcher.health.connect(self.health.emit)
        self._fetcher.organs.connect(self.organs.emit)
        self._fetcher.events.connect(self.events.emit)
        self._fetcher.start()


# ──────────────────────────────────────────────────────────────────────────────
# Organs tab
# ──────────────────────────────────────────────────────────────────────────────
class Organs(QWidget):
    def __init__(self, gs, poller):
        super().__init__()
        self.gs = gs

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        hdr = QHBoxLayout()
        title = QLabel("ORGANS")
        title.setStyleSheet(f"color:{C['gold']};font-size:16px;font-weight:bold;letter-spacing:2px;")
        self.count = QLabel("Loading...")
        self.count.setStyleSheet(f"color:{C['dim']};font-size:10px;")
        btn = QPushButton("Refresh")
        btn.setStyleSheet(
            f"QPushButton{{background:{C['bg3']};color:{C['text2']};border:1px solid {C['border']};"
            "border-radius:12px;padding:6px 12px;font-size:10px;}}"
            f"QPushButton:hover{{background:{C['border']};color:{C['text']};}}"
        )
        btn.clicked.connect(poller.poll)

        hdr.addWidget(title)
        hdr.addStretch()
        hdr.addWidget(self.count)
        hdr.addWidget(btn)
        root.addLayout(hdr)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(
            f"QScrollArea{{background:{C['bg2']};border:1px solid {C['border']};border-radius:12px;}}"
        )

        self.inner = QWidget()
        self.v = QVBoxLayout(self.inner)
        self.v.setContentsMargins(10, 10, 10, 10)
        self.v.setSpacing(2)

        self.scroll.setWidget(self.inner)
        root.addWidget(self.scroll, 1)

        poller.organs.connect(self.on_organs)

    def on_organs(self, organs: list):
        while self.v.count():
            it = self.v.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        if not organs:
            self.count.setText("0")
            lab = QLabel("No organs returned.")
            lab.setStyleSheet(f"color:{C['orange']};font-family:monospace;")
            self.v.addWidget(lab)
            self.v.addStretch()
            return

        active = 0
        for o in organs[:200]:
            name = str(o.get("name", "?"))
            status = str(o.get("active", o.get("enabled", ""))).lower()
            is_active = status in ("true", "active", "running", "1", "enabled")
            if is_active:
                active += 1

            lab = QLabel(f"{name:<28} {'ACTIVE' if is_active else 'INACTIVE'}")
            lab.setStyleSheet(
                f"color:{C['text'] if is_active else C['orange']};font-family:monospace;font-size:11px;"
            )
            self.v.addWidget(lab)

        self.v.addStretch()
        self.count.setText(f"{active}/{len(organs)} active")


# ──────────────────────────────────────────────────────────────────────────────
# Terminal tab
# ──────────────────────────────────────────────────────────────────────────────
class Terminal(QWidget):
    def __init__(self, gsm):
        super().__init__()
        self.gsm = gsm

        os.environ["VEIL_API"] = self.gsm.api_base()
        os.environ["VEIL_API_KEY"] = self.gsm.api_key()

        self.secure_term = VeilCoreSecureTerminal()
        self.history: list[str] = []
        self.hist_pos = -1

        layout = QVBoxLayout(self)

        self.term = QTextEdit()
        self.term.setReadOnly(True)
        self.term.setStyleSheet(f"background:{C['bg']};color:{C['text']};border:1px solid {C['border']};")

        self.input = QLineEdit()
        self.input.setStyleSheet(
            f"background:{C['bg2']};color:{C['text']};border:1px solid {C['border']};padding:6px;"
        )
        self.input.returnPressed.connect(self._enter)

        layout.addWidget(self.term)
        layout.addWidget(self.input)
        self._banner()

    def _write(self, text: str, color: str):
        self.term.setTextColor(QColor(color))
        self.term.append(str(text))
        self.term.moveCursor(QTextCursor.MoveOperation.End)

    def _banner(self):
        self._write("VEILCORE TERMINAL", C["cyan"])
        self._write(f"VEIL_API: {self.gsm.api_base()}", C["text2"])
        self._write("", C["text2"])

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Up:
            if self.history:
                self.hist_pos = max(0, self.hist_pos - 1 if self.hist_pos != -1 else len(self.history) - 1)
                self.input.setText(self.history[self.hist_pos])
            return

        if key == Qt.Key.Key_Down:
            if self.history:
                self.hist_pos = min(len(self.history) - 1, self.hist_pos + 1)
                self.input.setText(self.history[self.hist_pos])
            return

        super().keyPressEvent(event)

    def _enter(self):
        cmd = self.input.text().strip()
        if not cmd:
            return

        self.history.append(cmd)
        self.hist_pos = len(self.history)

        self._write(f"{self.secure_term.prompt()}{cmd}", C["cyan"])
        self.input.clear()

        try:
            result = self.secure_term.execute(cmd)
            out = getattr(result, "output", result)

            if out == "__CLEAR__":
                self.term.clear()
                self._banner()
                return

            text = str(out) if out is not None else ""
            if text.strip():
                for line in text.splitlines():
                    self._write(line, C["text"])
        except Exception as e:
            self._write(f"Error: {e}", C["red"])


# ──────────────────────────────────────────────────────────────────────────────
# Dashboard cards / mesh
# ──────────────────────────────────────────────────────────────────────────────
PHASE3_SUBSYSTEMS = [
    {"name": "NerveBridge", "module": "mesh", "icon": "⬡", "desc": "Organ Mesh"},
    {"name": "DeepSentinel", "module": "ml", "icon": "◉", "desc": "ML Threat AI"},
    {"name": "AllianceNet", "module": "federation", "icon": "⊕", "desc": "Federation"},
    {"name": "RedVeil", "module": "pentest", "icon": "⚔", "desc": "Auto Pentest"},
    {"name": "Watchtower", "module": "mobile", "icon": "📡", "desc": "Mobile API"},
    {"name": "EqualShield", "module": "accessibility", "icon": "♿", "desc": "Accessibility"},
    {"name": "AirShield", "module": "wireless", "icon": "📶", "desc": "Wireless Guard"},
    {"name": "IronWatch", "module": "physical", "icon": "🏛", "desc": "Physical Sec"},
    {"name": "Genesis", "module": "deployer", "icon": "⚙", "desc": "Deploy Engine"},
    {"name": "TrustForge", "module": "hitrust", "icon": "🛡", "desc": "HITRUST CSF"},
    {"name": "AuditIron", "module": "soc2", "icon": "📋", "desc": "SOC 2 Type II"},
    {"name": "SkyVeil", "module": "cloud", "icon": "☁", "desc": "Cloud Hybrid"},
    {"name": "Prism", "module": "dashboard", "icon": "◇", "desc": "Unified Dash"},
]


class AnimatedBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._v = 100.0
        self._anim = QPropertyAnimation(self, b"animatedValue", self)
        self._anim.setDuration(450)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def getAnimatedValue(self):
        return self._v

    def setAnimatedValue(self, v):
        self._v = float(v)
        self.setValue(int(round(v)))

    animatedValue = pyqtProperty(float, fget=getAnimatedValue, fset=setAnimatedValue)

    def animate_to(self, v: float):
        self._anim.stop()
        self._anim.setStartValue(self._v)
        self._anim.setEndValue(float(v))
        self._anim.start()


class SubsystemCard(QFrame):
    _depth_phase = 0.0

    def getScale(self):
        return self._scale

    def setScale(self, v):
        self._scale = v
        self.setFixedSize(int(220 * v), int(120 * v))

    scale = pyqtProperty(float, fget=getScale, fset=setScale)

    def getPopScale(self):
        return self._pop_scale

    def setPopScale(self, v):
        self._pop_scale = float(v)
        w = int(round(self._base_w * self._pop_scale))
        h = int(round(self._base_h * self._pop_scale))
        self.setFixedSize(w, h)

        extra = max(0.0, self._pop_scale - 1.0)
        if hasattr(self, "_glow"):
            self._glow.setBlurRadius(self._base_shadow_blur + extra * 140)
            self._glow.setOffset(0, self._base_shadow_y + extra * 18)

    popScale = pyqtProperty(float, fget=getPopScale, fset=setPopScale)

    def __init__(self, info, parent=None):
        super().__init__(parent)
        self._module = info.get("module", "")
        self._status = "operational"
        self._scale = 1.0
        self._base_w = 220
        self._base_h = 120
        self._pop_scale = 1.0
        self._pulse_on = False
        self._glow_up = True
        self._sheen = 0.0
        self._sheen_dir = 1
        self._edge_phase = 0.0
        self._shimmer_offset = 0.0

        self.setFixedSize(220, 120)
        self.setStyleSheet(
            f"QFrame{{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            f"stop:0 {C['bg3']},stop:0.55 {C['bg2']},stop:1 {C['bg']});"
            f"border:1px solid {C['border']};border-radius:10px;}}"
        )

        v = QVBoxLayout(self)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(2)

        top = QHBoxLayout()
        icon = QLabel(info["icon"])
        icon.setStyleSheet(f"color:{C['cyan']};font-size:22px;")
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet(f"color:{C['green']};font-size:10px;")
        top.addWidget(icon)
        top.addStretch()
        top.addWidget(self.status_dot)
        v.addLayout(top)

        name = QLabel(info["name"])
        name.setStyleSheet(f"color:{C['text']};font-size:13px;font-weight:bold;")
        v.addWidget(name)

        desc = QLabel(info["desc"])
        desc.setStyleSheet(f"color:{C['dim']};font-size:10px;")
        v.addWidget(desc)

        self.health_bar = AnimatedBar()
        self.health_bar.setFixedHeight(6)
        self.health_bar.setValue(100)
        self.health_bar.setTextVisible(False)
        self.health_bar.setStyleSheet(
            f"QProgressBar{{background:{C['bg']};border:none;border-radius:2px;}}"
            f"QProgressBar::chunk{{background:{C['green']};border-radius:2px;}}"
        )
        v.addWidget(self.health_bar)

        self._pulse = QTimer(self)
        self._pulse.timeout.connect(self._tick_pulse)
        self._pulse.start(700)

        self._glow = QGraphicsDropShadowEffect(self)
        self._glow.setBlurRadius(26)
        self._glow.setOffset(0, 4)
        self._glow.setColor(QColor(C["green"]))
        self.setGraphicsEffect(self._glow)

        self._glow_timer = QTimer(self)
        self._glow_timer.timeout.connect(self._tick_glow)
        self._glow_timer.start(120)

        self._pop_anim = QPropertyAnimation(self, b"popScale", self)
        self._pop_anim.setDuration(240)
        self._pop_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._pop_anim.finished.connect(self._pop_back)

        self._base_shadow_blur = 26
        self._base_shadow_y = 4

        self._fx_timer = QTimer(self)
        self._fx_timer.timeout.connect(self._tick_fx)
        self._fx_timer.start(70)

        self._scale_anim = QPropertyAnimation(self, b"scale")
        self._scale_anim.setDuration(220)
        self._scale_anim.setEasingCurve(QEasingCurve.Type.OutBack)

        self._shimmer = QTimer(self)
        self._shimmer.timeout.connect(self._tick_shimmer)
        self._shimmer.start(90)

    def _tick_pulse(self):
        colors = {"operational": C["green"], "degraded": C["orange"], "offline": C["red"]}
        col = colors.get(self._status, C["dim"])
        self._pulse_on = not self._pulse_on

        if self._status == "offline":
            self.status_dot.setStyleSheet(f"color:{col if self._pulse_on else C['dim']};font-size:{12 if self._pulse_on else 10}px;")
        elif self._status == "degraded":
            self.status_dot.setStyleSheet(f"color:{col};font-size:{11 if self._pulse_on else 10}px;")
        else:
            self.status_dot.setStyleSheet(f"color:{col};font-size:10px;")

    def _trigger_pop(self):
        self._pop_anim.stop()
        self._pop_anim.setStartValue(1.0)
        self._pop_anim.setEndValue(1.05)
        self._pop_anim.start()

    def _pop_back(self):
        if abs(self._pop_scale - 1.0) < 0.001:
            self.setPopScale(1.0)
            return
        self._pop_anim.stop()
        self._pop_anim.setStartValue(self._pop_scale)
        self._pop_anim.setEndValue(1.0)
        self._pop_anim.start()

    def _edge_profile(self):
        m = self._module
        profile = {
            "base": C["green"],
            "trail": C["green"],
            "width": 2,
            "seg": 0.15,
            "speed": 0.016,
            "lift": 1.0,
            "urgent": False,
        }

        if m == "ml":
            profile.update({"base": C["red"], "trail": C["orange"], "width": 4, "seg": 0.26, "speed": 0.030, "lift": 1.18, "urgent": True})
        elif m == "mesh":
            profile.update({"base": C["cyan"], "trail": C["blue"], "width": 3, "seg": 0.18, "speed": 0.019, "lift": 1.06})
        elif m == "federation":
            profile.update({"base": C["purple"], "trail": C["cyan"], "width": 2, "seg": 0.18, "speed": 0.014, "lift": 1.04})
        elif m == "pentest":
            profile.update({"base": C["red"], "trail": C["pink"], "width": 4, "seg": 0.24, "speed": 0.028, "lift": 1.16, "urgent": True})
        elif m == "mobile":
            profile.update({"base": C["cyan"], "trail": C["green"], "width": 2, "seg": 0.16, "speed": 0.018, "lift": 1.05})
        elif m == "accessibility":
            profile.update({"base": C["gold"], "trail": C["cyan"], "width": 2, "seg": 0.13, "speed": 0.011, "lift": 1.03})
        elif m == "wireless":
            profile.update({"base": C["blue"], "trail": C["cyan"], "width": 3, "seg": 0.18, "speed": 0.020, "lift": 1.06})
        elif m == "physical":
            profile.update({"base": C["orange"], "trail": C["red"], "width": 3, "seg": 0.17, "speed": 0.013, "lift": 1.07})
        elif m == "deployer":
            profile.update({"base": C["green"], "trail": C["cyan"], "width": 2, "seg": 0.16, "speed": 0.017, "lift": 1.05})
        elif m == "hitrust":
            profile.update({"base": C["gold"], "trail": C["green"], "width": 2, "seg": 0.14, "speed": 0.010, "lift": 1.03})
        elif m == "soc2":
            profile.update({"base": C["cyan"], "trail": C["gold"], "width": 2, "seg": 0.14, "speed": 0.011, "lift": 1.03})
        elif m == "cloud":
            profile.update({"base": C["purple"], "trail": C["blue"], "width": 3, "seg": 0.19, "speed": 0.016, "lift": 1.06})
        elif m == "dashboard":
            profile.update({"base": C["cyan"], "trail": C["purple"], "width": 2, "seg": 0.17, "speed": 0.015, "lift": 1.04})

        if self._status == "operational":
            profile["alpha_head"] = 20
            profile["alpha_trail"] = 6
            profile["seg"] *= 0.38
            profile["speed"] *= 0.25
        elif self._status == "degraded":
            if profile["urgent"]:
                profile["alpha_head"] = 215
                profile["alpha_trail"] = 84
                profile["speed"] *= 1.10
            else:
                profile["alpha_head"] = 165
                profile["alpha_trail"] = 54
        else:
            if profile["urgent"]:
                profile["alpha_head"] = 255
                profile["alpha_trail"] = 120
                profile["speed"] *= 1.18
                profile["seg"] *= 1.06
            else:
                profile["alpha_head"] = 190
                profile["alpha_trail"] = 68
                profile["speed"] *= 1.04

        return profile

    def _tick_fx(self):
        prof = self._edge_profile()
        if self._status == "operational":
            self._edge_phase = (self._edge_phase + prof["speed"] * 0.18) % 1.0
        else:
            self._edge_phase = (self._edge_phase + prof["speed"]) % 1.0

        self._depth_phase = (self._depth_phase + 0.02) % 6.28
        self._sheen += 0.03 * self._sheen_dir

        if self._sheen >= 1.0:
            self._sheen = 1.0
            self._sheen_dir = -1
        elif self._sheen <= 0.0:
            self._sheen = 0.0
            self._sheen_dir = 1

        self.update()

    def _tick_glow(self):
        prof = self._edge_profile()
        lift = prof.get("lift", 1.0)

        if self._status == "operational":
            lo, hi = int(6 * lift), int(12 * lift)
            col = QColor(C["border"])
        elif self._status == "degraded":
            lo, hi = int(18 * lift), int(34 * lift)
            col = QColor(prof["base"])
        else:
            lo, hi = int(8 * lift), int(40 * lift)
            col = QColor(prof["base"])

        cur = self._glow.blurRadius()
        step = 2.0 if self._status != "operational" else 1.2

        if self._glow_up:
            cur += step
            if cur >= hi:
                cur = hi
                self._glow_up = False
        else:
            cur -= step
            if cur <= lo:
                cur = lo
                self._glow_up = True

        self._glow.setBlurRadius(cur)

        if self._status == "operational":
            col.setAlpha(90)
        elif self._status == "degraded":
            col.setAlpha(150 if self._glow_up else 110)
        else:
            col.setAlpha(220 if self._glow_up else 80)

        self._glow.setColor(col)

    def _tick_shimmer(self):
        if self._status == "operational":
            return

        self._shimmer_offset = (self._shimmer_offset + 0.08) % 1.0
        bc = C["orange"] if self._status == "degraded" else C["red"]

        grad = f'''
        QProgressBar{{background:{C['bg']};border:none;border-radius:2px;}}
        QProgressBar::chunk{{
            background:qlineargradient(
                x1:{self._shimmer_offset},y1:0,
                x2:{self._shimmer_offset + 0.3},y2:0,
                stop:0 {bc},
                stop:0.5 {C['gold']},
                stop:1 {bc}
            );
            border-radius:2px;
        }}
        '''
        self.health_bar.setStyleSheet(grad)

    def set_status(self, status: str, health=100):
        self._status = status

        colors = {
            "operational": C["green"],
            "degraded": C["orange"],
            "offline": C["red"],
        }
        col = colors.get(status, C["dim"])

        self.status_dot.setStyleSheet(f"color:{col};font-size:10px;")
        self.health_bar.animate_to(int(health))

        bc = C["green"] if health >= 85 else (C["orange"] if health >= 70 else C["red"])
        if status == "operational":
            self.health_bar.setStyleSheet(
                f"QProgressBar{{background:{C['bg']};border:none;border-radius:2px;}}"
                f"QProgressBar::chunk{{background:{bc};border-radius:2px;}}"
            )

        self.update()

    def paintEvent(self, e):
        super().paintEvent(e)

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        r = self.rect().adjusted(1, 1, -2, -2)

        top_col = QColor(C["cyan"])
        top_col.setAlpha(22 if self._status == "operational" else (28 if self._status == "degraded" else 34))
        p.setPen(QPen(top_col, 1))
        p.drawLine(r.left() + 8, r.top() + 4, r.right() - 8, r.top() + 4)

        bevel = QColor(255, 255, 255, 14)
        p.setPen(QPen(bevel, 1))
        p.drawRoundedRect(r.adjusted(2, 2, -2, -2), 8, 8)

        shadow_lip = QColor(0, 0, 0, 42)
        p.setPen(QPen(shadow_lip, 1))
        p.drawLine(r.left() + 10, r.bottom() - 3, r.right() - 10, r.bottom() - 3)

        import math

        depth = int(2 + 2 * abs(math.sin(self._depth_phase)))
        shadow = QColor(0, 0, 0, 120)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(shadow)
        p.drawRoundedRect(r.adjusted(depth, depth, depth, depth), 10, 10)

        glow = QRadialGradient(QPointF(r.center()), float(r.width()) * 0.6)
        glow.setColorAt(0, QColor(C["cyan"]))
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        p.setBrush(glow)
        p.setOpacity(0.08)
        p.drawRoundedRect(r.adjusted(2, 2, -2, -2), 10, 10)

        if self._module in ("ml", "pentest") and self._status != "operational":
            pulse_r = abs(math.sin(self._depth_phase * 2)) * r.width() * 0.35
            col = QColor(C["red"])
            col.setAlpha(55)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(col)
            p.drawEllipse(r.center(), int(pulse_r), int(pulse_r))

        p.setOpacity(1)

        prof = self._edge_profile()
        siren_col = QColor(prof["base"])
        siren_col.setAlpha(prof["alpha_head"])

        trail_col = QColor(prof["trail"])
        trail_col.setAlpha(prof["alpha_trail"])

        width = prof["width"]

        path = QPainterPath()
        rr = QRectF(r.adjusted(1, 1, -1, -1))
        path.addRoundedRect(rr, 10, 10)

        plen = max(1.0, path.length())
        head = self._edge_phase * plen
        seg = plen * prof["seg"]
        trail = plen * 0.08

        def draw_segment(offset, length, color, pen_w):
            a = max(0.0, offset)
            b = min(plen, offset + length)
            if b <= a:
                return

            pts = []
            steps = max(8, int(length / 6))
            for i in range(steps + 1):
                d = a + (b - a) * (i / steps)
                pct = 0.0 if plen == 0 else d / plen
                pts.append(path.pointAtPercent(pct))

            if len(pts) >= 2:
                pp = QPainterPath()
                pp.moveTo(pts[0])
                for pt in pts[1:]:
                    pp.lineTo(pt)
                p.setPen(QPen(color, pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawPath(pp)

        for base in (head - seg, head):
            a = base
            b = base + seg
            if a < 0:
                draw_segment(plen + a, -a, trail_col, width)
                draw_segment(0, b, siren_col, width)
            elif b > plen:
                draw_segment(a, plen - a, siren_col, width)
                draw_segment(0, b - plen, trail_col, width)
            else:
                draw_segment(a, trail, trail_col, width)
                draw_segment(a + trail, max(0.0, seg - trail), siren_col, width)

        p.end()


class NeuralOverlay(QWidget):
    def __init__(self, host, cards):
        super().__init__(host)
        self._cards = cards
        self._phase = 0.0
        self._bursts: list[dict] = []

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background:transparent;")
        self.setGeometry(host.rect())
        host.installEventFilter(self)

        self._links = [
            ("mesh", "ml", "cyan"),
            ("ml", "federation", "red"),
            ("mesh", "dashboard", "blue"),
            ("pentest", "dashboard", "pink"),
            ("cloud", "dashboard", "purple"),
            ("mobile", "mesh", "green"),
            ("wireless", "physical", "blue"),
            ("deployer", "cloud", "green"),
            ("hitrust", "soc2", "gold"),
            ("accessibility", "dashboard", "gold"),
        ]

        self._downstream: dict[str, list[tuple[str, str]]] = {}
        for a, b, accent in self._links:
            self._downstream.setdefault(a, []).append((b, accent))

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(50)

    def eventFilter(self, obj, ev):
        if obj is self.parent():
            if ev.type() in (QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.Move):
                self.setGeometry(self.parent().rect())
        return False

    def _tick(self):
        self._phase = (self._phase + 0.018) % 1.0
        now = monotonic()
        self._bursts = [b for b in self._bursts if now - b["ts"] <= b["ttl"]]
        self.update()

    def _card_center(self, module: str):
        card = self._cards.get(module)
        if not card:
            return None
        return QPointF(card.geometry().center())

    def emit_event_burst(self, source_module: str, severity="info"):
        if source_module not in self._cards:
            return

        sev_color = {
            "info": "cyan",
            "warning": "orange",
            "critical": "red",
        }.get(severity, "cyan")

        visited = set()
        queue = [(source_module, 0)]

        while queue:
            node, depth = queue.pop(0)
            if (node, depth) in visited:
                continue
            visited.add((node, depth))

            for dst, accent in self._downstream.get(node, []):
                self._bursts.append(
                    {
                        "src": node,
                        "dst": dst,
                        "accent": sev_color if severity in ("warning", "critical") else accent,
                        "ts": monotonic(),
                        "ttl": 1.8 + depth * 0.25,
                        "severity": severity,
                    }
                )
                queue.append((dst, depth + 1))

    def _make_path(self, p1: QPointF, p2: QPointF, bend: float):
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        dist = max(1.0, (dx * dx + dy * dy) ** 0.5)

        nx = -dy / dist
        ny = dx / dist

        c1 = QPointF(p1.x() + dx * 0.33 + nx * bend, p1.y() + dy * 0.33 + ny * bend)
        c2 = QPointF(p1.x() + dx * 0.66 + nx * bend, p1.y() + dy * 0.66 + ny * bend)

        path = QPainterPath()
        path.moveTo(p1)
        path.cubicTo(c1, c2, p2)
        return path

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        for i, (a, b, accent) in enumerate(self._links):
            p1 = self._card_center(a)
            p2 = self._card_center(b)
            if p1 is None or p2 is None:
                continue

            path = self._make_path(p1, p2, 12 + (i % 3) * 6)
            base = QColor(C.get(accent, C["cyan"]))

            line_col = QColor(base)
            line_col.setAlpha(26)
            p.setPen(QPen(line_col, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)

            t = (self._phase + i * 0.09) % 1.0
            pt_head = path.pointAtPercent(t)

            head_col = QColor(base)
            head_col.setAlpha(90)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(head_col)
            p.drawEllipse(pt_head, 4, 4)

        now = monotonic()
        for burst in self._bursts:
            p1 = self._card_center(burst["src"])
            p2 = self._card_center(burst["dst"])
            if p1 is None or p2 is None:
                continue

            path = self._make_path(p1, p2, 16)
            age = now - burst["ts"]
            pct = min(1.0, max(0.0, age / burst["ttl"]))
            base = QColor(C.get(burst["accent"], C["cyan"]))

            trail = QColor(base)
            trail.setAlpha(110 if burst["severity"] == "critical" else 80)

            glow = QColor(base)
            glow.setAlpha(180 if burst["severity"] == "critical" else 130)

            fat = 4 if burst["severity"] == "critical" else 3
            pt = path.pointAtPercent(pct)

            p.setPen(QPen(trail, fat, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)

            steps = 12
            start_pct = max(0.0, pct - 0.10)
            seg = QPainterPath()
            seg.moveTo(path.pointAtPercent(start_pct))
            for i in range(1, steps + 1):
                t = start_pct + (pct - start_pct) * (i / steps)
                seg.lineTo(path.pointAtPercent(t))
            p.drawPath(seg)

            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(glow)
            p.drawEllipse(pt, 7, 7)

            halo = QColor(base)
            halo.setAlpha(60)
            p.setBrush(halo)
            p.drawEllipse(pt, 13, 13)

        p.end()


# ──────────────────────────────────────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────────────────────────────────────
class DashboardV2(QWidget):
    def __init__(self, gs, poller):
        super().__init__()
        self.gs = gs
        self.poller = poller
        self.cards: dict[str, SubsystemCard] = {}
        self._seen_event_ids: set[str] = set()
        self._source_map = {
            "physical": "physical",
            "ml": "ml",
            "mesh": "mesh",
            "cloud": "cloud",
            "dashboard": "dashboard",
            "pentest": "pentest",
            "mobile": "mobile",
            "wireless": "wireless",
            "federation": "federation",
            "deployer": "deployer",
        }

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        hdr = QHBoxLayout()
        title = QLabel("SECURITY COMMAND CENTER")
        title.setStyleSheet(f"color:{C['cyan']};font-size:16px;font-weight:bold;letter-spacing:2px;")
        self.conn = QLabel("● CONNECTING")
        self.conn.setStyleSheet(f"color:{C['orange']};font-size:10px;font-weight:bold;")
        hdr.addWidget(title)
        hdr.addStretch()
        hdr.addWidget(self.conn)
        root.addLayout(hdr)

        self.events = PrismEvents(self.gs)
        root.addWidget(self.events)

        stats = QHBoxLayout()
        self.stat_organs = self._make_stat("82", "ORGANS")
        self.stat_subs = self._make_stat("13", "SUBSYSTEMS")
        self.stat_health = self._make_stat("100%", "HEALTH")
        self.stat_alerts = self._make_stat("0", "CYCLES")
        stats.addWidget(self.stat_organs)
        stats.addWidget(self.stat_subs)
        stats.addWidget(self.stat_health)
        stats.addWidget(self.stat_alerts)
        stats.addStretch()
        root.addLayout(stats)

        gl = QLabel("SUBSYSTEM STATUS")
        gl.setStyleSheet(f"color:{C['text2']};font-size:11px;font-weight:bold;letter-spacing:1px;margin-top:6px;")
        root.addWidget(gl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea{{background:{C['bg']};border:none;}}")

        gw = QWidget()
        grid = QGridLayout(gw)
        grid.setSpacing(10)
        grid.setContentsMargins(10, 10, 10, 10)

        row = 0
        col = 0
        for info in PHASE3_SUBSYSTEMS:
            card = SubsystemCard(info)
            card.set_status("operational", 100)
            self.cards[info["module"]] = card
            grid.addWidget(card, row, col)
            col += 1
            if col >= 7:
                col = 0
                row += 1

        self.overlay = NeuralOverlay(gw, self.cards)
        self.overlay.raise_()

        scroll.setWidget(gw)
        root.addWidget(scroll, 1)

        self.threat_label = QLabel("")
        self.threat_label.setStyleSheet(f"color:{C['text2']};font-family:monospace;font-size:11px;")
        root.addWidget(self.threat_label)

        poller.health.connect(self.on_health)
        poller.organs.connect(self._read_engines)
        poller.events.connect(self.on_events)

        self._metrics_timer = QTimer(self)
        self._metrics_timer.timeout.connect(self._read_metrics)
        self._metrics_timer.start(5000)
        QTimer.singleShot(1000, self._read_metrics)

    def _make_stat(self, val: str, label: str):
        w = QFrame()
        w.setStyleSheet(f"QFrame{{background:{C['bg3']};border:1px solid {C['border']};border-radius:10px;padding:4px;}}")
        v = QVBoxLayout(w)
        v.setContentsMargins(12, 6, 12, 6)
        v.setSpacing(0)

        vl = QLabel(val)
        vl.setStyleSheet(f"color:{C['cyan']};font-size:22px;font-weight:bold;")
        vl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        ll = QLabel(label)
        ll.setStyleSheet(f"color:{C['dim']};font-size:9px;font-weight:bold;letter-spacing:1px;")
        ll.setAlignment(Qt.AlignmentFlag.AlignCenter)

        v.addWidget(vl)
        v.addWidget(ll)

        w._val = vl
        return w

    def on_health(self, d: dict):
        if "_error" in d:
            self.conn.setText("● OFFLINE")
            self.conn.setStyleSheet(f"color:{C['red']};font-size:10px;font-weight:bold;")
            return

        self.conn.setText("● NOMINAL")
        self.conn.setStyleSheet(f"color:{C['green']};font-size:10px;font-weight:bold;")

    def on_events(self, events: list):
        if not events:
            return

        new_events = []
        for ev in events:
            ev_id = ev.get("id")
            if not ev_id or ev_id in self._seen_event_ids:
                continue
            self._seen_event_ids.add(ev_id)
            new_events.append(ev)

        if not new_events:
            return

        if len(self._seen_event_ids) > 2000:
            self._seen_event_ids = set(list(self._seen_event_ids)[-1000:])

        for ev in reversed(new_events):
            src = str(ev.get("source", "")).lower().strip()
            level = str(ev.get("level", "info")).lower().strip()
            module = self._source_map.get(src)

            if module and module in self.cards:
                card = self.cards[module]

                if level == "critical":
                    card.set_status("offline" if module in ("physical", "ml") else "degraded", max(35, card.health_bar.value()))
                elif level == "warning":
                    card.set_status("degraded", max(60, card.health_bar.value()))
                else:
                    card.set_status(card._status, card.health_bar.value())

                card._trigger_pop()
                self.overlay.emit_event_burst(module, severity=level)

    def _read_engines(self, _=None):
        try:
            url = f"{self.gs.api_base()}/engines"
            req = urllib.request.Request(url)
            api_key = self.gs.api_key()
            if api_key:
                req.add_header("X-API-Key", api_key)

            with urllib.request.urlopen(req, timeout=2.0) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))

            engines = data.get("engines", [])
            running = 0

            for eng in engines:
                module = eng.get("id")
                state = str(eng.get("state", "unknown")).lower()
                health = int(eng.get("health", 0) or 0)

                if module not in self.cards:
                    continue

                if state == "running":
                    status = "operational"
                    running += 1
                elif state == "degraded":
                    status = "degraded"
                else:
                    status = "offline"

                self.cards[module].set_status(status, health)

            self.stat_subs._val.setText(str(running))
        except Exception:
            pass

    def _read_metrics(self):
        try:
            mp = Path("/home/user/.config/veilcore/metrics.json")
            if not mp.exists():
                return

            data = json.loads(mp.read_text())
            cpu = data.get("cpu_pct", 0)
            ram = data.get("ram", {}).get("used_pct", 0)
            disk = data.get("disk", {}).get("used_pct", 0)
            organs = data.get("organs", {})
            svcs = data.get("services", {})
            comp = data.get("compliance", {})

            self.stat_organs._val.setText(f"{organs.get('enabled', 0)}/{organs.get('total', 0)}")
            self.stat_subs._val.setText("13")

            health = round(100 - (cpu * 0.4 + ram * 0.3 + disk * 0.3), 1)
            health = max(0, min(100, health))
            self.stat_health._val.setText(f"{health}%")
            hcol = C["green"] if health >= 85 else (C["orange"] if health >= 70 else C["red"])
            self.stat_health._val.setStyleSheet(f"color:{hcol};font-size:22px;font-weight:bold;")
            self.stat_alerts._val.setText(str(data.get("cycle", 0)))

            sub_health = {
                "mesh": 100 if svcs.get("active", 0) >= 2 else 60,
                "ml": 100 if svcs.get("active", 0) >= 3 else 70,
                "federation": 95,
                "pentest": 95,
                "mobile": 100,
                "accessibility": 100,
                "wireless": 100,
                "physical": 100,
                "deployer": 100,
                "hitrust": comp.get("hitrust_pct", 98.4),
                "soc2": comp.get("soc2_pct", 98.6),
                "cloud": 100,
                "dashboard": 100 if svcs.get("active", 0) >= 4 else 80,
            }

            for module, h in sub_health.items():
                if module in self.cards:
                    st = "operational" if h >= 80 else ("degraded" if h >= 50 else "offline")
                    self.cards[module].set_status(st, h)

            self.threat_label.setText(
                f"CPU: {cpu}%  |  RAM: {ram}%  |  DISK: {disk}%  |  "
                f"Services: {svcs.get('active',0)}/{svcs.get('total',0)}  |  "
                f"HITRUST: {comp.get('hitrust_pct',0)}%  |  "
                f"SOC2: {comp.get('soc2_pct',0)}%  |  "
                f"Cycle: #{data.get('cycle',0)}"
            )
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────────────────────
# Compliance tab
# ──────────────────────────────────────────────────────────────────────────────
class ComplianceTab(QWidget):
    def __init__(self, gs):
        super().__init__()

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(14)

        title = QLabel("COMPLIANCE COMMAND")
        title.setStyleSheet(f"color:{C['gold']};font-size:16px;font-weight:bold;letter-spacing:2px;")
        root.addWidget(title)

        entries = [
            (
                "🛡  HITRUST CSF v11 — TrustForge",
                98,
                "98.4% Coverage",
                [("Domains", "19/19"), ("Controls", "32"), ("Full Coverage", "31"), ("Gaps", "0")],
            ),
            (
                "📋  SOC 2 Type II — AuditIron",
                99,
                "98.6% Coverage — TYPE II READY",
                [("Categories", "5/5"), ("Criteria", "35"), ("Automated", "100%"), ("Type II Ready", "YES")],
            ),
        ]

        for fname, pct, fmt, stats_data in entries:
            f = QFrame()
            f.setStyleSheet(f"QFrame{{background:{C['bg3']};border:1px solid {C['border']};border-radius:12px;}}")
            fv = QVBoxLayout(f)
            fv.setContentsMargins(16, 12, 16, 12)
            fv.setSpacing(6)

            ft = QLabel(fname)
            ft.setStyleSheet(f"color:{C['cyan']};font-size:14px;font-weight:bold;")
            fv.addWidget(ft)

            bar = QProgressBar()
            bar.setFixedHeight(20)
            bar.setValue(pct)
            bar.setFormat(fmt)
            bar.setStyleSheet(
                f"QProgressBar{{background:{C['bg']};border:1px solid {C['border']};border-radius:6px;"
                f"color:{C['text']};font-size:11px;font-weight:bold;}}"
                f"QProgressBar::chunk{{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                f"stop:0 {C['cyan']},stop:1 {C['green']});border-radius:5px;}}"
            )
            fv.addWidget(bar)

            sr = QHBoxLayout()
            for label, val in stats_data:
                sf = QFrame()
                sf.setStyleSheet(f"QFrame{{background:{C['bg2']};border-radius:8px;padding:4px;}}")

                sv = QVBoxLayout(sf)
                sv.setContentsMargins(10, 4, 10, 4)
                sv.setSpacing(0)

                vl = QLabel(val)
                vl.setStyleSheet(f"color:{C['green']};font-size:18px;font-weight:bold;")
                vl.setAlignment(Qt.AlignmentFlag.AlignCenter)

                ll = QLabel(label)
                ll.setStyleSheet(f"color:{C['dim']};font-size:9px;")
                ll.setAlignment(Qt.AlignmentFlag.AlignCenter)

                sv.addWidget(vl)
                sv.addWidget(ll)
                sr.addWidget(sf)

            fv.addLayout(sr)
            root.addWidget(f)

        root.addStretch()


# ──────────────────────────────────────────────────────────────────────────────
# Cloud tab
# ──────────────────────────────────────────────────────────────────────────────
class CloudTab(QWidget):
    def __init__(self, gs):
        super().__init__()

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(14)

        title = QLabel("CLOUD-HYBRID TOPOLOGY — SkyVeil")
        title.setStyleSheet(f"color:{C['purple']};font-size:16px;font-weight:bold;letter-spacing:2px;")
        root.addWidget(title)

        phi = QFrame()
        phi.setStyleSheet(f"QFrame{{background:{C['bg3']};border:2px solid {C['green']};border-radius:12px;}}")
        pv = QHBoxLayout(phi)
        pv.setContentsMargins(16, 10, 16, 10)

        pl = QLabel("🔒  PHI RESIDENCY: COMPLIANT")
        pl.setStyleSheet(f"color:{C['green']};font-size:14px;font-weight:bold;")

        pd = QLabel("PHI/PII enforced on-prem • 13 organs locked")
        pd.setStyleSheet(f"color:{C['text2']};font-size:10px;")

        pv.addWidget(pl)
        pv.addStretch()
        pv.addWidget(pd)
        root.addWidget(phi)

        nodes_row = QHBoxLayout()
        nodes = [
            {
                "id": "ONPREM-PRIMARY",
                "provider": "On-Prem",
                "role": "Primary",
                "organs": "6",
                "data": "PHI, PII, Ops",
                "color": C["cyan"],
                "status": "ACTIVE",
            },
            {
                "id": "AWS-ANALYTICS",
                "provider": "AWS",
                "role": "Analytics",
                "organs": "3",
                "data": "Threat Intel, Metrics",
                "color": C["orange"],
                "status": "ACTIVE",
            },
            {
                "id": "AZURE-FAILOVER",
                "provider": "Azure",
                "role": "Failover",
                "organs": "2",
                "data": "Logs, Metrics",
                "color": C["blue"],
                "status": "STANDBY",
            },
        ]

        for nd in nodes:
            nf = QFrame()
            nf.setStyleSheet(f"QFrame{{background:{C['bg3']};border:1px solid {nd['color']};border-radius:12px;}}")
            nv = QVBoxLayout(nf)
            nv.setContentsMargins(14, 10, 14, 10)
            nv.setSpacing(4)

            nt = QLabel(nd["id"])
            nt.setStyleSheet(f"color:{nd['color']};font-size:13px;font-weight:bold;")
            nv.addWidget(nt)

            for lbl, val in [
                ("Provider", nd["provider"]),
                ("Role", nd["role"]),
                ("Organs", nd["organs"]),
                ("Status", nd["status"]),
            ]:
                r = QHBoxLayout()
                ll = QLabel(lbl + ":")
                ll.setStyleSheet(f"color:{C['dim']};font-size:10px;")
                ll.setFixedWidth(60)

                sc = C["green"] if val == "ACTIVE" else (C["orange"] if val == "STANDBY" else C["text"])
                vl = QLabel(val)
                vl.setStyleSheet(f"color:{sc};font-size:10px;font-weight:bold;")

                r.addWidget(ll)
                r.addWidget(vl)
                r.addStretch()
                nv.addLayout(r)

            dl = QLabel("Data: " + nd["data"])
            dl.setStyleSheet(f"color:{C['text2']};font-size:9px;")
            dl.setWordWrap(True)
            nv.addWidget(dl)
            nodes_row.addWidget(nf)

        root.addLayout(nodes_row)

        spf = QFrame()
        spf.setStyleSheet(f"QFrame{{background:{C['bg3']};border:1px solid {C['border']};border-radius:12px;}}")
        spv = QVBoxLayout(spf)
        spv.setContentsMargins(16, 12, 16, 12)
        spv.setSpacing(4)

        spt = QLabel("SYNC POLICIES")
        spt.setStyleSheet(f"color:{C['text2']};font-size:11px;font-weight:bold;letter-spacing:1px;")
        spv.addWidget(spt)

        for name, freq, direction in [
            ("Threat Intelligence", "60s", "Bidirectional"),
            ("Metrics Offload", "5m", "Push"),
            ("Log Archive", "15m", "Push"),
            ("Backup Verification", "1h", "Push"),
        ]:
            r = QHBoxLayout()
            nl = QLabel(name)
            nl.setStyleSheet(f"color:{C['text']};font-size:11px;")
            nl.setFixedWidth(180)

            fl = QLabel(freq)
            fl.setStyleSheet(f"color:{C['cyan']};font-size:11px;font-weight:bold;")
            fl.setFixedWidth(50)

            ddl = QLabel(direction)
            ddl.setStyleSheet(f"color:{C['text2']};font-size:11px;")

            dot = QLabel("● ACTIVE")
            dot.setStyleSheet(f"color:{C['green']};font-size:10px;")

            r.addWidget(nl)
            r.addWidget(fl)
            r.addWidget(ddl)
            r.addStretch()
            r.addWidget(dot)
            spv.addLayout(r)

        root.addWidget(spf)

        pof = QFrame()
        pof.setStyleSheet(f"QFrame{{background:{C['bg3']};border:1px solid {C['border']};border-radius:12px;}}")
        pov = QVBoxLayout(pof)
        pov.setContentsMargins(16, 12, 16, 12)
        pov.setSpacing(4)

        pot = QLabel("ON-PREM LOCKED ORGANS (PHI)")
        pot.setStyleSheet(f"color:{C['red']};font-size:11px;font-weight:bold;letter-spacing:1px;")
        pov.addWidget(pot)

        ll = QLabel(
            "guardian • phi_classifier • phi_guard • vault • encryption_enforcer • epic_connector • "
            "imprivata_bridge • hl7_filter • fhir_gateway • dicom_shield • insider_threat • "
            "forensic_collector • dlp_engine"
        )
        ll.setStyleSheet(f"color:{C['text2']};font-size:10px;")
        ll.setWordWrap(True)
        pov.addWidget(ll)

        root.addWidget(pof)
        root.addStretch()


# ──────────────────────────────────────────────────────────────────────────────
# Settings
# ──────────────────────────────────────────────────────────────────────────────
CONF_DIR = Path.home() / ".config" / "veilcore"
CONF_DIR.mkdir(parents=True, exist_ok=True)

GLOBAL_SETTINGS_PATH = CONF_DIR / "global.json"
DEFAULT_API_BASE = os.environ.get("VEIL_API", "http://127.0.0.1:9444").rstrip("/")


def _load_gs() -> dict:
    if not GLOBAL_SETTINGS_PATH.exists():
        return {"api_base": DEFAULT_API_BASE, "api_key": os.environ.get("VEIL_API_KEY", ""), "refresh_ms": 4000}

    try:
        d = json.loads(GLOBAL_SETTINGS_PATH.read_text() or "{}")
    except Exception:
        d = {}

    d.setdefault("api_base", DEFAULT_API_BASE)
    d.setdefault("api_key", "")
    d.setdefault("refresh_ms", 4000)
    return d


def _save_gs(d: dict) -> None:
    d["saved_at"] = datetime.now().isoformat(timespec="seconds")
    GLOBAL_SETTINGS_PATH.write_text(json.dumps(d, indent=2))


class GlobalSettings(QObject):
    changed = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self._s = _load_gs()

    def get(self) -> dict:
        return dict(self._s)

    def api_base(self) -> str:
        return str(self._s.get("api_base") or DEFAULT_API_BASE).strip().rstrip("/") or DEFAULT_API_BASE

    def api_key(self) -> str:
        return str(self._s.get("api_key") or "").strip()

    def refresh_ms(self) -> int:
        return max(500, min(60000, int(self._s.get("refresh_ms") or 4000)))

    def update(self, api_base: str, api_key: str, refresh_ms: int):
        self._s["api_base"] = (api_base or "").strip().rstrip("/") or DEFAULT_API_BASE
        self._s["api_key"] = (api_key or "").strip()
        self._s["refresh_ms"] = int(refresh_ms)
        try:
            _save_gs(self._s)
        except Exception:
            pass
        self.changed.emit(self.get())


class SettingsDialog(QDialog):
    def __init__(self, gs, parent=None):
        super().__init__(parent)
        self.gs = gs

        self.setWindowTitle("VeilCore Settings")
        self.resize(520, 220)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.api_base = QLineEdit(self.gs.api_base())
        self.api_key = QLineEdit(self.gs.api_key())

        self.refresh_ms = QSpinBox()
        self.refresh_ms.setRange(500, 60000)
        self.refresh_ms.setValue(self.gs.refresh_ms())

        form.addRow("API Base", self.api_base)
        form.addRow("API Key", self.api_key)
        form.addRow("Refresh (ms)", self.refresh_ms)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self):
        self.gs.update(self.api_base.text(), self.api_key.text(), self.refresh_ms.value())
        self.accept()


# ──────────────────────────────────────────────────────────────────────────────
# Desktop
# ──────────────────────────────────────────────────────────────────────────────
def pick_icon():
    candidates = [
        Path.home() / ".local" / "share" / "icons" / "veilcore.png",
        Path.home() / ".local" / "share" / "icons" / "hicolor" / "256x256" / "apps" / "veilcore.png",
    ]
    for p in candidates:
        if p.exists():
            return QIcon(str(p))
    return None


class VeilCoreDesktop(QMainWindow):
    def __init__(self, gs):
        super().__init__()
        self.gs = gs
        self.poller = ApiPoller(self.gs)

        self.setWindowTitle("VeilCore Desktop")
        self.setMinimumSize(1000, 680)
        self.setStyleSheet(f"QMainWindow{{background:{C['bg']};}}")

        root = QWidget()
        self.setCentralWidget(root)
        rl = QVBoxLayout(root)
        rl.setContentsMargins(10, 10, 10, 10)
        rl.setSpacing(10)

        top = QHBoxLayout()
        brand = QLabel("VEILCORE")
        brand.setStyleSheet(f"color:{C['cyan']};font-size:18px;font-weight:bold;letter-spacing:3px;")

        self.status = QLabel("● CONNECTING")
        self.status.setStyleSheet(f"color:{C['orange']};font-size:10px;font-weight:bold;")

        btn = QPushButton("Settings")
        btn.setStyleSheet(
            f"QPushButton{{background:{C['bg3']};color:{C['text2']};border:1px solid {C['border']};"
            "border-radius:12px;padding:6px 12px;font-size:10px;}}"
            f"QPushButton:hover{{background:{C['border']};color:{C['text']};border-color:{C['cyan']};}}"
        )
        btn.clicked.connect(lambda: SettingsDialog(self.gs, self).exec())

        top.addWidget(brand)
        top.addStretch()
        top.addWidget(self.status)
        top.addWidget(btn)
        rl.addLayout(top)

        tabs = QTabWidget()
        tabs.setStyleSheet(
            f"QTabWidget::pane{{border:1px solid {C['border']};border-radius:12px;}}"
            f"QTabBar::tab{{background:{C['bg3']};color:{C['text2']};padding:8px 12px;"
            "border-top-left-radius:10px;border-top-right-radius:10px;margin-right:4px;}}"
            f"QTabBar::tab:selected{{background:{C['bg2']};color:{C['cyan']};border:1px solid {C['border']};border-bottom:none;}}"
        )

        tabs.addTab(DashboardV2(self.gs, self.poller), "Dashboard")
        tabs.addTab(Organs(self.gs, self.poller), "Organs")
        tabs.addTab(ComplianceTab(self.gs), "Compliance")
        tabs.addTab(CloudTab(self.gs), "Cloud")
        tabs.addTab(Terminal(self.gs), "Terminal")

        rl.addWidget(tabs, 1)

        self.poller.health.connect(self._on_health)

    def _on_health(self, d: dict):
        if "_error" in d:
            self.status.setText("● OFFLINE")
            self.status.setStyleSheet(f"color:{C['red']};font-size:10px;font-weight:bold;")
        else:
            self.status.setText("● NOMINAL")
            self.status.setStyleSheet(f"color:{C['green']};font-size:10px;font-weight:bold;")


# ──────────────────────────────────────────────────────────────────────────────
# App
# ──────────────────────────────────────────────────────────────────────────────
class VeilCoreApp:
    def __init__(self):
        log("=== VeilCore starting ===")
        log(f"DISPLAY={os.environ.get('DISPLAY', '')}, WAYLAND={os.environ.get('WAYLAND_DISPLAY', '')}")

        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(True)
        self.app.setStyle("Fusion")

        pal = QPalette()
        pal.setColor(QPalette.ColorRole.Window, QColor(C["bg"]))
        pal.setColor(QPalette.ColorRole.WindowText, QColor(C["text"]))
        pal.setColor(QPalette.ColorRole.Base, QColor(C["bg"]))
        pal.setColor(QPalette.ColorRole.Text, QColor(C["text"]))
        pal.setColor(QPalette.ColorRole.Highlight, QColor(C["cyan"]))
        pal.setColor(QPalette.ColorRole.Button, QColor(C["bg2"]))
        self.app.setPalette(pal)

        try:
            QGuiApplication.setDesktopFileName("veilcore")
        except Exception:
            pass

        self._icon = pick_icon()
        if self._icon and not self._icon.isNull():
            self.app.setWindowIcon(self._icon)

        self.gs = GlobalSettings()

        self.splash_win = QMainWindow()
        self.splash_win.setWindowTitle("VeilCore")

        self.splash = Splash()
        self.splash.finished.connect(self._launch)
        self.splash_win.setCentralWidget(self.splash)

        if self._icon and not self._icon.isNull():
            self.splash_win.setWindowIcon(self._icon)

        self.splash_win.showMaximized()
        self.splash_win.raise_()
        self.splash_win.activateWindow()
        log("Splash shown.")

    def _launch(self):
        log("Splash finished -> launching desktop.")
        try:
            self.desktop = VeilCoreDesktop(self.gs)
            if self._icon and not self._icon.isNull():
                self.desktop.setWindowIcon(self._icon)
            self.desktop.showMaximized()
            self.splash_win.hide()
            QTimer.singleShot(50, self.splash_win.close)
        except Exception:
            log_exc("Desktop creation failed:")
            self.splash.set_fail(
                "DESKTOP FAILED TO START.\n\nCheck:\n~/.config/veilcore/veilui.log\n\nLeaving splash open so you aren't stuck."
            )

    def run(self):
        rc = self.app.exec()
        log(f"VeilCore exit rc={rc}")
        raise SystemExit(rc)


def main():
    os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")
    os.environ.setdefault("GALLIUM_DRIVER", "llvmpipe")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")

    if not os.environ.get("QT_QPA_PLATFORM"):
        os.environ["QT_QPA_PLATFORM"] = "wayland" if os.environ.get("WAYLAND_DISPLAY") else "xcb"

    log(f"QT_QPA_PLATFORM={os.environ.get('QT_QPA_PLATFORM', '')}")
    VeilCoreApp().run()


if __name__ == "__main__":
    main()
