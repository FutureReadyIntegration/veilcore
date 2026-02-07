#!/usr/bin/env python3
"""
Veil Hospital GUI (Qt) — clean baseline.

- Lists orchestrator services
- Shows status/pid/log
- Play (start), Stop, Cancel (kill/force stop if available)
- Tail log preview
- Refresh loop

No prototype baggage.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import asdict, is_dataclass
from typing import Any, Optional

# Qt imports
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QMessageBox,
    QSplitter,
)

APP_TITLE = "Veil — Hospital Console"
REFRESH_MS = 1500


def _to_dict(obj: Any) -> dict:
    """Accept dict, dataclass, or object with attributes."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if is_dataclass(obj):
        return asdict(obj)
    # fallback: attribute bag
    d = {}
    for k in ("name", "running", "pid", "log", "tier"):
        if hasattr(obj, k):
            d[k] = getattr(obj, k)
    return d


def _safe_read_tail(path: str, max_bytes: int = 6000) -> str:
    try:
        if not path or not os.path.exists(path):
            return ""
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            start = max(0, size - max_bytes)
            f.seek(start)
            data = f.read()
        try:
            return data.decode("utf-8", errors="replace")
        except Exception:
            return data.decode(errors="replace")
    except Exception as e:
        return f"[log read error] {e}"


class VeilHospitalGUI(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1200, 720)

        self.selected_name: Optional[str] = None
        self.services: list[dict] = []

        # ---- Top bar ----
        title = QLabel("Veil Security & Hardening Tracker — Hospital Console")
        title.setFont(QFont("Arial", 14, QFont.Bold))

        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter services… (type to search)")
        self.search.textChanged.connect(self.refresh_table)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.refresh_from_orchestrator)

        top = QHBoxLayout()
        top.addWidget(title, 2)
        top.addWidget(self.search, 2)
        top.addWidget(self.btn_refresh, 0)

        # ---- Table ----
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Name", "Status", "PID", "Tier", "Log"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.cellClicked.connect(self.on_row_selected)
        self.table.cellDoubleClicked.connect(self.on_row_double_clicked)

        # ---- Controls ----
        self.btn_play = QPushButton("▶ Play")
        self.btn_stop = QPushButton("■ Stop")
        self.btn_cancel = QPushButton("✕ Cancel")

        self.btn_play.clicked.connect(self.do_start)
        self.btn_stop.clicked.connect(self.do_stop)
        self.btn_cancel.clicked.connect(self.do_cancel)

        controls = QHBoxLayout()
        controls.addWidget(self.btn_play)
        controls.addWidget(self.btn_stop)
        controls.addWidget(self.btn_cancel)
        controls.addStretch(1)

        # ---- Details + Log ----
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setPlaceholderText("Select a service…")

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Log tail…")

        right = QWidget()
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Service Details"))
        right_layout.addWidget(self.details, 1)
        right_layout.addWidget(QLabel("Log Tail"))
        right_layout.addWidget(self.log_view, 2)
        right.setLayout(right_layout)

        splitter = QSplitter(Qt.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.table, 1)
        left_layout.addLayout(controls)
        left.setLayout(left_layout)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        # ---- Main layout ----
        root = QVBoxLayout()
        root.addLayout(top)
        root.addWidget(splitter, 1)
        self.setLayout(root)

        # ---- Styling (dark cathedral) ----
        self.setStyleSheet(
            """
            QWidget { background: #120808; color: #d6c7c7; }
            QLineEdit { background:#1a0a0a; border:1px solid #331111; padding:6px; border-radius:6px; }
            QPushButton { background:#1a0a0a; border:1px solid #331111; padding:8px 10px; border-radius:8px; }
            QPushButton:hover { border:1px solid #553333; }
            QTableWidget { background:#160909; gridline-color:#331111; }
            QHeaderView::section { background:#1a0a0a; border:1px solid #331111; padding:6px; }
            QTextEdit { background:#1a0a0a; border:1px solid #331111; border-radius:6px; }
            """
        )

        # Refresh loop
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_from_orchestrator)
        self.timer.start(REFRESH_MS)

        self.refresh_from_orchestrator()

    # ---------- orchestrator glue ----------
    def _orch_list(self) -> list[dict]:
        # We keep imports lazy so GUI loads even if orchestrator is mid-refactor.
        from veil import orchestrator as orch  # type: ignore

        raw = orch.list_services()  # returns list[ServiceStatus] or list[dict]
        out: list[dict] = []
        for item in raw:
            d = _to_dict(item)
            # normalize keys
            d.setdefault("pid", None)
            d.setdefault("tier", "—")
            d.setdefault("log", "")
            d.setdefault("running", False)
            out.append(d)
        out.sort(key=lambda x: x.get("name", ""))
        return out

    def _orch_start(self, name: str) -> None:
        from veil import orchestrator as orch  # type: ignore
        orch.start_service(name)

    def _orch_stop(self, name: str, force: bool = False) -> None:
        from veil import orchestrator as orch  # type: ignore
        # support either stop_service(name) or stop_service(name, force=?)
        try:
            orch.stop_service(name, force=force)
        except TypeError:
            orch.stop_service(name)

    def _orch_status(self, name: str) -> dict:
        from veil import orchestrator as orch  # type: ignore
        # support either status(name) or get_status(name) patterns
        if hasattr(orch, "status"):
            return _to_dict(orch.status(name))
        if hasattr(orch, "service_status"):
            return _to_dict(orch.service_status(name))
        # fall back: search from list
        for s in self.services:
            if s.get("name") == name:
                return s
        return {"name": name, "running": False, "pid": None, "tier": "—", "log": ""}

    # ---------- UI ----------
    def refresh_from_orchestrator(self) -> None:
        try:
            self.services = self._orch_list()
            self.refresh_table()
            self.refresh_details_and_log()
        except Exception as e:
            # do not spam modal popups; show in details panel
            self.details.setPlainText(f"[orchestrator error]\n{e}")

    def refresh_table(self) -> None:
        q = (self.search.text() or "").strip().lower()
        rows = [s for s in self.services if (q in s.get("name", "").lower())]

        self.table.setRowCount(len(rows))
        for r, s in enumerate(rows):
            name = s.get("name", "")
            running = bool(s.get("running"))
            pid = s.get("pid", None)
            tier = s.get("tier", "—")
            logp = s.get("log", "")

            status_txt = "● RUNNING" if running else "○ STOPPED"

            self.table.setItem(r, 0, QTableWidgetItem(name))
            self.table.setItem(r, 1, QTableWidgetItem(status_txt))
            self.table.setItem(r, 2, QTableWidgetItem("" if pid in (None, "None") else str(pid)))
            self.table.setItem(r, 3, QTableWidgetItem(str(tier) if tier else "—"))
            self.table.setItem(r, 4, QTableWidgetItem(logp))

        self.table.resizeColumnsToContents()

    def on_row_selected(self, row: int, col: int) -> None:
        item = self.table.item(row, 0)
        if not item:
            return
        self.selected_name = item.text()
        self.refresh_details_and_log()

    def on_row_double_clicked(self, row: int, col: int) -> None:
        # Double-click toggles start/stop
        item = self.table.item(row, 0)
        if not item:
            return
        name = item.text()
        s = self._orch_status(name)
        if bool(s.get("running")):
            self._confirm_and_stop(name, force=False)
        else:
            self._confirm_and_start(name)

    def refresh_details_and_log(self) -> None:
        if not self.selected_name:
            return
        s = self._orch_status(self.selected_name)
        name = s.get("name", self.selected_name)
        running = bool(s.get("running"))
        pid = s.get("pid", None)
        tier = s.get("tier", "—")
        logp = s.get("log", "")

        status_txt = "● RUNNING" if running else "○ STOPPED"
        pid_txt = "" if pid in (None, "None") else str(pid)

        self.details.setPlainText(
            "\n".join(
                [
                    f"Name:   {name}",
                    f"Status: {status_txt}",
                    f"PID:    {pid_txt}",
                    f"Tier:   {tier}",
                    f"Log:    {logp}",
                ]
            )
        )
        if logp:
            self.log_view.setPlainText(_safe_read_tail(logp))
        else:
            self.log_view.setPlainText("")

    def _need_selection(self) -> Optional[str]:
        if not self.selected_name:
            QMessageBox.information(self, "Veil", "Select a service first.")
            return None
        return self.selected_name

    def _confirm_and_start(self, name: str) -> None:
        res = QMessageBox.question(self, "Start service", f"Start '{name}'?")
        if res != QMessageBox.Yes:
            return
        try:
            self._orch_start(name)
        except Exception as e:
            QMessageBox.critical(self, "Start failed", str(e))
        self.refresh_from_orchestrator()

    def _confirm_and_stop(self, name: str, force: bool) -> None:
        label = "Cancel (force stop)" if force else "Stop"
        res = QMessageBox.question(self, label, f"{label} '{name}'?")
        if res != QMessageBox.Yes:
            return
        try:
            self._orch_stop(name, force=force)
        except Exception as e:
            QMessageBox.critical(self, f"{label} failed", str(e))
        self.refresh_from_orchestrator()

    def do_start(self) -> None:
        name = self._need_selection()
        if not name:
            return
        self._confirm_and_start(name)

    def do_stop(self) -> None:
        name = self._need_selection()
        if not name:
            return
        self._confirm_and_stop(name, force=False)

    def do_cancel(self) -> None:
        name = self._need_selection()
        if not name:
            return
        self._confirm_and_stop(name, force=True)


def main() -> int:
    app = QApplication(sys.argv)
    w = VeilHospitalGUI()
    w.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
