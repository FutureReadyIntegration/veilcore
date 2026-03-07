from pathlib import Path
import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor

C = {
    "bg": "#0a0e17",
    "bg2": "#111827",
    "border": "#1e3a4a",
    "cyan": "#00e5ff",
    "green": "#00ff6a",
    "orange": "#ff8c00",
    "red": "#ff4444",
    "text": "#e6f7ff",
    "dim": "#4a6a7a"
}

EVENT_FILE = Path.home() / "veilcore" / "data" / "events.json"


class PrismEvents(QWidget):

    def __init__(self):
        super().__init__()

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)

        title = QLabel("PRISM EVENT FEED")
        title.setStyleSheet(f"color:{C['cyan']};font-size:12px;font-weight:bold;")
        root.addWidget(title)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(
            f"QScrollArea{{background:{C['bg2']};border:1px solid {C['border']};}}"
        )

        self.inner = QWidget()
        self.v = QVBoxLayout(self.inner)
        self.v.setContentsMargins(8, 8, 8, 8)

        self.scroll.setWidget(self.inner)
        root.addWidget(self.scroll)

        self._seen = set()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll)
        self.timer.start(2000)

        self._poll()

    def _poll(self):

        if not EVENT_FILE.exists():
            return

        try:
            data = json.loads(EVENT_FILE.read_text())
        except Exception:
            return

        events = data.get("events", [])

        for e in events[::-1]:

            if e["id"] in self._seen:
                continue

            self._seen.add(e["id"])

            line = QLabel(
                f"{e['ts']}  |  {e['source']}  |  {e['message']}"
            )

            color = C["text"]

            if e["level"] == "error":
                color = C["red"]

            elif e["level"] == "warn":
                color = C["orange"]

            elif e["level"] == "info":
                color = C["green"]

            line.setStyleSheet(
                f"color:{color};font-family:monospace;font-size:11px;"
            )

            self.v.insertWidget(0, line)

        if self.v.count() > 100:
            w = self.v.takeAt(100).widget()
            if w:
                w.deleteLater()
