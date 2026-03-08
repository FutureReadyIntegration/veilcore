from __future__ import annotations

import json
import urllib.request

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
from PyQt6.QtCore import QTimer


C = {
    "bg": "#0a0e17",
    "bg2": "#111827",
    "border": "#1e3a4a",
    "cyan": "#00e5ff",
    "green": "#00ff6a",
    "orange": "#ff8c00",
    "red": "#ff4444",
    "text": "#e6f7ff",
    "dim": "#4a6a7a",
}


class PrismEvents(QWidget):
    def __init__(self, gs, parent=None):
        super().__init__(parent)
        self.gs = gs
        self._seen = set()

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        title = QLabel("PRISM EVENT FEED")
        title.setStyleSheet(
            f"color:{C['cyan']};font-size:11px;font-weight:bold;letter-spacing:1px;"
        )
        root.addWidget(title)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(
            f"QScrollArea{{background:{C['bg2']};border:1px solid {C['border']};border-radius:10px;}}"
        )

        self.inner = QWidget()
        self.v = QVBoxLayout(self.inner)
        self.v.setContentsMargins(8, 8, 8, 8)
        self.v.setSpacing(4)
        self.scroll.setWidget(self.inner)

        root.addWidget(self.scroll)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(1500)

        self._poll()

    def _poll(self):
        try:
            url = f"{self.gs.api_base()}/events?limit=20"
            req = urllib.request.Request(url)
            api_key = self.gs.api_key()
            if api_key:
                req.add_header("X-API-Key", api_key)

            with urllib.request.urlopen(req, timeout=2.0) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))

            events = data.get("events", [])

            for ev in reversed(events):
                eid = ev.get("id")
                if not eid or eid in self._seen:
                    continue
                self._seen.add(eid)

                ts = ev.get("ts", "")
                src = ev.get("source", "?")
                msg = ev.get("message", "")
                level = str(ev.get("level", "info")).lower()

                line = QLabel(f"{ts}  |  {src:<12}  |  {msg}")
                if level in ("critical", "error"):
                    col = C["red"]
                elif level in ("warning", "warn"):
                    col = C["orange"]
                elif level == "info":
                    col = C["green"]
                else:
                    col = C["text"]

                line.setStyleSheet(f"color:{col};font-family:monospace;font-size:10px;")
                line.setWordWrap(True)
                self.v.insertWidget(0, line)

            while self.v.count() > 30:
                it = self.v.takeAt(self.v.count() - 1)
                if it and it.widget():
                    it.widget().deleteLater()

        except Exception:
            pass
