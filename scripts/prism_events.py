from __future__ import annotations

import json
import urllib.request
from collections import OrderedDict
from typing import Any

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


C = {
    "bg": "#0a0e17",
    "bg2": "#111827",
    "bg3": "#1a2332",
    "cyan": "#00e5ff",
    "green": "#00ff6a",
    "gold": "#fbbf24",
    "orange": "#ff8c00",
    "red": "#ff4d6d",
    "blue": "#3b82f6",
    "purple": "#a855f7",
    "text": "#e6f7ff",
    "text2": "#7baac4",
    "dim": "#4a6a7a",
    "border": "#1e3a4a",
}


def api_get(base: str, path: str, api_key: str, timeout_s: float = 2.0) -> dict:
    url = f"{base.rstrip('/')}/{path.lstrip('/')}"
    req = urllib.request.Request(url)
    if api_key:
        req.add_header("X-API-Key", api_key)
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def level_color(level: str) -> str:
    level = str(level or "").lower()
    if level == "critical":
        return C["red"]
    if level == "warning":
        return C["gold"]
    if level == "info":
        return C["green"]
    return C["dim"]


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


class EventRow(QFrame):
    def __init__(self, event: dict, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame{{background:{C['bg3']};border:1px solid {C['border']};border-radius:12px;}}"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(4)

        top = QHBoxLayout()
        ts = QLabel(safe_text(event.get("ts", "")))
        ts.setStyleSheet(f"color:{C['dim']};font-size:10px;font-family:monospace;")

        lvl = QLabel(safe_text(event.get("level", "")).upper())
        lvl.setStyleSheet(
            f"color:{level_color(event.get('level'))};font-size:10px;font-weight:bold;font-family:monospace;"
        )

        et = QLabel(safe_text(event.get("type", "")))
        et.setStyleSheet(f"color:{C['cyan']};font-size:11px;font-weight:bold;font-family:monospace;")

        top.addWidget(ts)
        top.addSpacing(10)
        top.addWidget(lvl)
        top.addSpacing(10)
        top.addWidget(et)
        top.addStretch()
        root.addLayout(top)

        msg = QLabel(safe_text(event.get("message", "")))
        msg.setWordWrap(True)
        msg.setStyleSheet(f"color:{C['text']};font-size:12px;")
        root.addWidget(msg)

        meta = []
        if event.get("source"):
            meta.append(f"src={event['source']}")
        if event.get("target"):
            meta.append(f"target={event['target']}")
        if meta:
            md = QLabel(" • ".join(meta))
            md.setStyleSheet(f"color:{C['text2']};font-size:10px;font-family:monospace;")
            root.addWidget(md)


class ActionRow(QFrame):
    def __init__(self, event: dict, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame{{background:{C['bg2']};border:1px solid {C['border']};border-radius:10px;}}"
        )
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(8)

        etype = safe_text(event.get("type", ""))
        payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
        action = safe_text(payload.get("action", "chain"))
        level = safe_text(event.get("level", "")).upper()

        dot = QLabel("●")
        dot.setStyleSheet(f"color:{level_color(event.get('level'))};font-size:12px;")

        ts = QLabel(safe_text(event.get("ts", "")))
        ts.setStyleSheet(f"color:{C['dim']};font-size:10px;font-family:monospace;")

        title = QLabel(action if etype != "response.chain_started" else "chain_started")
        title.setStyleSheet(f"color:{C['cyan']};font-size:11px;font-weight:bold;font-family:monospace;")

        msg = QLabel(safe_text(event.get("message", "")))
        msg.setStyleSheet(f"color:{C['text']};font-size:11px;")
        msg.setWordWrap(True)

        lvl = QLabel(level)
        lvl.setStyleSheet(f"color:{level_color(event.get('level'))};font-size:10px;font-weight:bold;font-family:monospace;")

        root.addWidget(dot)
        root.addWidget(ts)
        root.addWidget(title)
        root.addWidget(lvl)
        root.addWidget(msg, 1)


class ChainCard(QFrame):
    def __init__(self, chain_id: str, events: list[dict], parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame{{background:{C['bg3']};border:2px solid {C['cyan']};border-radius:14px;}}"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(6)

        first = events[0]
        payload = first.get("payload", {}) if isinstance(first.get("payload"), dict) else {}

        top = QHBoxLayout()
        badge = QLabel("RESPONSE CHAIN")
        badge.setStyleSheet(f"color:{C['gold']};font-size:11px;font-weight:bold;letter-spacing:1px;")

        cid = QLabel(chain_id)
        cid.setStyleSheet(f"color:{C['dim']};font-size:10px;font-family:monospace;")

        top.addWidget(badge)
        top.addStretch()
        top.addWidget(cid)
        root.addLayout(top)

        title = QLabel(safe_text(payload.get("policy", "Autonomous containment chain")))
        title.setStyleSheet(f"color:{C['text']};font-size:13px;font-weight:bold;")
        root.addWidget(title)

        trigger = QLabel(
            f"trigger={safe_text(payload.get('trigger_event_type', 'unknown'))}  target={safe_text(first.get('target', ''))}"
        )
        trigger.setStyleSheet(f"color:{C['text2']};font-size:10px;font-family:monospace;")
        root.addWidget(trigger)

        for ev in events:
            root.addWidget(ActionRow(ev))

        completed = any(e.get("type") == "response.chain_completed" for e in events)
        foot = QLabel("COMPLETED" if completed else "IN PROGRESS")
        foot.setStyleSheet(
            f"color:{C['green'] if completed else C['gold']};font-size:10px;font-weight:bold;font-family:monospace;"
        )
        root.addWidget(foot)


class PrismEvents(QWidget):
    def __init__(self, gs, parent: QWidget | None = None):
        super().__init__(parent)
        self.gs = gs
        self._last_signature = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        hdr = QHBoxLayout()
        title = QLabel("PRISM EVENT TIMELINE")
        title.setStyleSheet(f"color:{C['cyan']};font-size:14px;font-weight:bold;letter-spacing:2px;")
        self.status = QLabel("CONNECTING")
        self.status.setStyleSheet(f"color:{C['gold']};font-size:10px;font-weight:bold;font-family:monospace;")
        hdr.addWidget(title)
        hdr.addStretch()
        hdr.addWidget(self.status)
        root.addLayout(hdr)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(
            f"QScrollArea{{background:{C['bg2']};border:1px solid {C['border']};border-radius:12px;}}"
        )

        self.inner = QWidget()
        self.vbox = QVBoxLayout(self.inner)
        self.vbox.setContentsMargins(10, 10, 10, 10)
        self.vbox.setSpacing(8)
        self.scroll.setWidget(self.inner)
        root.addWidget(self.scroll, 1)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(2500)
        QTimer.singleShot(400, self.refresh)

    def refresh(self) -> None:
        try:
            data = api_get(self.gs.api_base(), "events", self.gs.api_key())
            events = data.get("events", [])
            if not isinstance(events, list):
                events = []
            self.status.setText("LIVE")
            self.status.setStyleSheet(f"color:{C['green']};font-size:10px;font-weight:bold;font-family:monospace;")
            self._render(events[:60])
        except Exception as e:
            self.status.setText("OFFLINE")
            self.status.setStyleSheet(f"color:{C['red']};font-size:10px;font-weight:bold;font-family:monospace;")
            self._render_error(str(e))

    def _render_error(self, message: str) -> None:
        while self.vbox.count():
            item = self.vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        box = QFrame()
        box.setStyleSheet(
            f"QFrame{{background:{C['bg3']};border:1px solid {C['border']};border-radius:12px;}}"
        )
        lay = QVBoxLayout(box)
        lay.setContentsMargins(12, 10, 12, 10)

        t = QLabel("Unable to read /events")
        t.setStyleSheet(f"color:{C['red']};font-size:12px;font-weight:bold;")
        lay.addWidget(t)

        m = QLabel(message)
        m.setWordWrap(True)
        m.setStyleSheet(f"color:{C['text2']};font-size:11px;")
        lay.addWidget(m)

        self.vbox.addWidget(box)
        self.vbox.addStretch()

    def _render(self, events: list[dict]) -> None:
        sig = "|".join(f"{e.get('id','')}:{e.get('type','')}" for e in events[:20])
        if sig == self._last_signature:
            return
        self._last_signature = sig

        while self.vbox.count():
            item = self.vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        chain_groups: "OrderedDict[str, list[dict]]" = OrderedDict()
        singles: list[dict] = []

        for ev in events:
            et = safe_text(ev.get("type", ""))
            payload = ev.get("payload", {}) if isinstance(ev.get("payload"), dict) else {}
            chain_id = safe_text(payload.get("chain_id", ""))

            if et.startswith("response.") and chain_id:
                if chain_id not in chain_groups:
                    chain_groups[chain_id] = []
                chain_groups[chain_id].append(ev)
            else:
                singles.append(ev)

        rendered_chain_ids = set()
        rendered_single_ids = set()

        for ev in events:
            eid = safe_text(ev.get("id", ""))
            et = safe_text(ev.get("type", ""))
            payload = ev.get("payload", {}) if isinstance(ev.get("payload"), dict) else {}
            chain_id = safe_text(payload.get("chain_id", ""))

            if et.startswith("response.") and chain_id:
                if chain_id in rendered_chain_ids:
                    continue
                rendered_chain_ids.add(chain_id)
                self.vbox.addWidget(ChainCard(chain_id, chain_groups.get(chain_id, [])))
                continue

            if eid in rendered_single_ids:
                continue
            rendered_single_ids.add(eid)
            self.vbox.addWidget(EventRow(ev))

        self.vbox.addStretch()
