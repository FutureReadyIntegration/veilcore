from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from PyQt5.QtCore import Qt, QProcess, QTimer, QSize
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon, QTextCharFormat, QTextCursor
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QMessageBox,
    QSplitter,
    QFrame,
    QHeaderView,
    QStatusBar,
    QToolButton,
    QSizePolicy,
)

# We keep this GUI "thin": it shells out to the authoritative CLI.
CMD_LIST = "veil orchestrator list"
CMD_START = "veil orchestrator start {name}"
CMD_STOP = "veil orchestrator stop {name}"


@dataclass
class ServiceRow:
    name: str
    running: bool
    pid: Optional[int]
    log: str
    tier: str = "—"  # optional/unknown for now


LIST_RE = re.compile(
    r"^(?P<name>\S+)\s+running=(?P<running>True|False)\s+pid=(?P<pid>\S+)\s+log=(?P<log>.+)$"
)


def parse_list(text: str) -> List[ServiceRow]:
    rows: List[ServiceRow] = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        m = LIST_RE.match(ln)
        if not m:
            continue
        name = m.group("name")
        running = (m.group("running") == "True")
        pid_s = m.group("pid")
        pid = int(pid_s) if pid_s.isdigit() else None
        log = m.group("log").strip()
        rows.append(ServiceRow(name=name, running=running, pid=pid, log=log))
    rows.sort(key=lambda r: r.name)
    return rows


def _style() -> str:
    return """
    /* Main window */
    QWidget { 
        background: #0a0d14; 
        color: #e8eaf0; 
        font-size: 13px; 
        font-family: 'Segoe UI', 'Inter', system-ui, sans-serif;
    }
    
    /* Title */
    QLabel#Title { 
        font-size: 24px; 
        font-weight: 700; 
        color: #ffffff;
        padding: 8px 0px;
    }
    
    /* Subtitle */
    QLabel#Sub { 
        color: #8b95b3; 
        font-size: 12px;
        padding-bottom: 12px;
    }
    
    /* Input fields */
    QLineEdit { 
        background: #141824; 
        border: 1px solid #2a3552; 
        padding: 8px 12px; 
        border-radius: 6px;
        selection-background-color: #2a3552;
    }
    QLineEdit:focus {
        border: 1px solid #4a5a7a;
        background: #1a1f2e;
    }
    
    /* Buttons */
    QPushButton { 
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #2a3552, stop:1 #1f2a44);
        border: 1px solid #3a4562; 
        padding: 10px 16px; 
        border-radius: 6px;
        font-weight: 500;
        min-width: 80px;
    }
    QPushButton:hover { 
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #3a4562, stop:1 #2a3552);
        border: 1px solid #4a5a7a;
    }
    QPushButton:pressed {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #1f2a44, stop:1 #2a3552);
    }
    QPushButton:disabled { 
        background: #0f1419; 
        color: #5a6578; 
        border: 1px solid #1a1f2e;
    }
    
    /* Play button (green accent) */
    QPushButton#PlayButton {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #2d7a4f, stop:1 #1e5a3a);
        border: 1px solid #3d8a5f;
    }
    QPushButton#PlayButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #3d8a5f, stop:1 #2d7a4f);
        border: 1px solid #4d9a6f;
    }
    
    /* Stop button (red accent) */
    QPushButton#StopButton {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #7a2d2d, stop:1 #5a1e1e);
        border: 1px solid #8a3d3d;
    }
    QPushButton#StopButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #8a3d3d, stop:1 #7a2d2d);
        border: 1px solid #9a4d4d;
    }
    
    /* Refresh button (blue accent) */
    QPushButton#RefreshButton {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #2d4a7a, stop:1 #1e355a);
        border: 1px solid #3d5a8a;
    }
    QPushButton#RefreshButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #3d5a8a, stop:1 #2d4a7a);
        border: 1px solid #4d6a9a;
    }
    
    /* Text edit */
    QTextEdit { 
        background: #0b0e14; 
        border: 1px solid #2a3552; 
        border-radius: 8px;
        padding: 8px;
        selection-background-color: #2a3552;
    }
    
    /* Frames */
    QFrame { 
        background: #141824; 
        border: 1px solid #232a3d; 
        border-radius: 10px;
        padding: 8px;
    }
    
    /* Table */
    QTableWidget { 
        background: #0b0e14; 
        border: 1px solid #2a3552; 
        border-radius: 8px;
        gridline-color: #1a1f2e;
        selection-background-color: #2a3552;
        selection-color: #ffffff;
        alternate-background-color: #0f1116;
    }
    QTableWidget::item {
        padding: 4px;
    }
    QTableWidget::item:selected {
        background: #2a3552;
        color: #ffffff;
    }
    
    /* Table header */
    QHeaderView::section { 
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #1a1f2e, stop:1 #141824);
        color: #a8b3cf; 
        border: 1px solid #232a3d; 
        padding: 8px;
        font-weight: 600;
    }
    
    /* Status bar */
    QStatusBar {
        background: #141824;
        border-top: 1px solid #232a3d;
        color: #8b95b3;
    }
    QStatusBar::item {
        border: none;
    }
    """


class VeilHospitalConsole(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Veil OS — Hospital Operator Console")
        self.setMinimumSize(1200, 750)

        # Runner process (async; doesn't freeze UI)
        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._on_proc_out)
        self.proc.finished.connect(self._on_proc_done)
        self._proc_buf: List[str] = []
        self._current_cmd: Optional[str] = None
        self._last_refresh: Optional[datetime] = None

        # Header
        header_frame = QFrame()
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(16, 16, 16, 8)
        
        title = QLabel("Veil OS — Hospital Operator Console")
        title.setObjectName("Title")
        sub = QLabel("Services • Actions • Logs • Operator-safe controls")
        sub.setObjectName("Sub")
        
        header_layout.addWidget(title)
        header_layout.addWidget(sub)
        header_frame.setLayout(header_layout)

        # Controls toolbar
        toolbar = QFrame()
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(12, 8, 12, 8)
        toolbar_layout.setSpacing(12)
        
        toolbar_layout.addWidget(QLabel("🔍 Filter:"))
        
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search services by name...")
        self.search.setMinimumWidth(200)
        toolbar_layout.addWidget(self.search, 1)
        
        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setObjectName("RefreshButton")
        self.btn_refresh.setToolTip("Refresh service list (F5)")
        toolbar_layout.addWidget(self.btn_refresh)
        
        toolbar_layout.addSpacing(8)
        
        self.btn_play = QPushButton("▶ Start")
        self.btn_play.setObjectName("PlayButton")
        self.btn_play.setToolTip("Start selected service (Ctrl+S)")
        toolbar_layout.addWidget(self.btn_play)
        
        self.btn_stop = QPushButton("■ Stop")
        self.btn_stop.setObjectName("StopButton")
        self.btn_stop.setToolTip("Stop selected service (Ctrl+X)")
        toolbar_layout.addWidget(self.btn_stop)
        
        toolbar_layout.addSpacing(8)
        
        self.btn_cancel = QPushButton("✖ Cancel")
        self.btn_cancel.setToolTip("Cancel running command (Esc)")
        self.btn_cancel.setEnabled(False)
        toolbar_layout.addWidget(self.btn_cancel)
        
        toolbar.setLayout(toolbar_layout)

        # Table with improved styling
        self.table = QTableWidget(0, 5, self)
        self.table.setHorizontalHeaderLabels(["Name", "Tier", "Status", "PID", "Log Path"])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setStretchLastSection(True)
        
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        
        # Set row height
        self.table.verticalHeader().setDefaultSectionSize(32)

        # Details panel with better formatting
        details_label = QLabel("📋 Details & Output")
        details_label.setObjectName("Sub")
        
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setFont(QFont("Consolas", 10) if QFont("Consolas").exactMatch() else QFont("Courier New", 10))
        self.details.setLineWrapMode(QTextEdit.NoWrap)
        self.details.setPlaceholderText("Select a service to view details, or run a command to see output...")

        # Layout frames
        left_frame = QFrame()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)
        left_layout.addWidget(toolbar)
        left_layout.addWidget(self.table, 1)
        left_frame.setLayout(left_layout)

        right_frame = QFrame()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(8)
        right_layout.addWidget(details_label)
        right_layout.addWidget(self.details, 1)
        right_frame.setLayout(right_layout)

        split = QSplitter(Qt.Horizontal)
        split.addWidget(left_frame)
        split.addWidget(right_frame)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        split.setSizes([700, 400])

        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("Ready")

        # Root layout
        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(header_frame)
        root.addWidget(split, 1)
        root.addWidget(self.status_bar)
        self.setLayout(root)

        # State
        self._rows: List[ServiceRow] = []
        self._row_by_name: Dict[str, ServiceRow] = {}

        # Signals
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_play.clicked.connect(self.play_selected)
        self.btn_stop.clicked.connect(self.stop_selected)
        self.btn_cancel.clicked.connect(self.cancel_command)
        self.search.textChanged.connect(self._render)
        self.table.itemSelectionChanged.connect(self._update_details_from_selection)
        self.table.itemDoubleClicked.connect(self._on_row_double_click)

        # Keyboard shortcuts
        from PyQt5.QtWidgets import QShortcut
        from PyQt5.QtGui import QKeySequence
        QShortcut(QKeySequence("F5"), self, self.refresh)
        QShortcut(QKeySequence("Ctrl+S"), self, self.play_selected)
        QShortcut(QKeySequence("Ctrl+X"), self, self.stop_selected)
        QShortcut(QKeySequence("Escape"), self, self.cancel_command)
        QShortcut(QKeySequence("Ctrl+F"), self, lambda: self.search.setFocus())

        # Initial load
        self.refresh()

        # Auto-refresh timer
        self.timer = QTimer(self)
        self.timer.setInterval(3000)  # 3 seconds
        self.timer.timeout.connect(self._auto_refresh_tick)
        self.timer.start()

    # --------------------
    # Command runner
    # --------------------
    def _run(self, cmd: str) -> None:
        if self.proc.state() != QProcess.NotRunning:
            QMessageBox.information(self, "Busy", "A command is already running. Cancel it or wait.")
            return
        self._proc_buf.clear()
        self._current_cmd = cmd
        self._append_output(f"\n{'='*60}\n▶ {cmd}\n{'='*60}\n", is_command=True)
        self.btn_cancel.setEnabled(True)
        self.status_bar.showMessage(f"Running: {cmd}...")
        self.proc.start("/bin/bash", ["-lc", cmd])

    def cancel_command(self) -> None:
        if self.proc.state() == QProcess.NotRunning:
            return
        self._append_output("\n✖ Cancel requested...\n", is_error=True)
        self.proc.terminate()
        self.btn_cancel.setEnabled(False)
        self.status_bar.showMessage("Command cancelled")

    def _append_output(self, text: str, is_command: bool = False, is_error: bool = False) -> None:
        cursor = self.details.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        if is_command:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor("#4a9eff"))
            fmt.setFontWeight(700)
            cursor.setCharFormat(fmt)
        elif is_error:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor("#ff6b6b"))
            cursor.setCharFormat(fmt)
        
        cursor.insertText(text)
        self.details.setTextCursor(cursor)
        self.details.ensureCursorVisible()

    def _on_proc_out(self) -> None:
        data = bytes(self.proc.readAllStandardOutput()).decode(errors="replace")
        if data:
            self._proc_buf.append(data)
            self._append_output(data)

    def _on_proc_done(self, code: int, _status) -> None:
        status_color = "#4ade80" if code == 0 else "#ff6b6b"
        status_text = "✓ Success" if code == 0 else "✗ Failed"
        self._append_output(f"\n{'─'*60}\n{status_text} (exit code: {code})\n{'─'*60}\n\n", 
                          is_error=(code != 0))
        
        # If the command was a list, update table from its captured output
        if self._current_cmd and self._current_cmd.strip() == CMD_LIST:
            txt = "".join(self._proc_buf)
            self._rows = parse_list(txt)
            self._row_by_name = {r.name: r for r in self._rows}
            self._last_refresh = datetime.now()
            self._render()
            self._update_status_bar()
        
        self._current_cmd = None
        self.btn_cancel.setEnabled(False)
        self.status_bar.showMessage("Ready" if code == 0 else f"Command failed (exit {code})")

    # --------------------
    # UI actions
    # --------------------
    def refresh(self) -> None:
        self._run(CMD_LIST)

    def _auto_refresh_tick(self) -> None:
        # Only refresh if we're idle; prevents fighting operator actions.
        if self.proc.state() == QProcess.NotRunning:
            self.refresh()

    def _selected_name(self) -> Optional[str]:
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            return None
        r = sel[0].row()
        item = self.table.item(r, 0)
        return item.text() if item else None

    def _on_row_double_click(self, item: QTableWidgetItem) -> None:
        # Double-click to start/stop
        name = self._selected_name()
        if not name:
            return
        row = self._row_by_name.get(name)
        if row:
            if row.running:
                self.stop_selected()
            else:
                self.play_selected()

    def play_selected(self) -> None:
        name = self._selected_name()
        if not name:
            QMessageBox.information(self, "Select service", "Please select a service row first.")
            return
        self._run(CMD_START.format(name=name))

    def stop_selected(self) -> None:
        name = self._selected_name()
        if not name:
            QMessageBox.information(self, "Select service", "Please select a service row first.")
            return
        self._run(CMD_STOP.format(name=name))

    def _update_status_bar(self) -> None:
        running_count = sum(1 for r in self._rows if r.running)
        total_count = len(self._rows)
        filtered_count = self.table.rowCount()
        
        status_parts = [
            f"Services: {total_count} total",
            f"{running_count} running",
            f"{filtered_count} shown"
        ]
        
        if self._last_refresh:
            elapsed = (datetime.now() - self._last_refresh).total_seconds()
            status_parts.append(f"Updated {elapsed:.0f}s ago")
        
        self.status_bar.showMessage(" • ".join(status_parts))

    # --------------------
    # Rendering
    # --------------------
    def _render(self) -> None:
        keep = self._selected_name()
        q = self.search.text().strip().lower()

        shown = []
        for r in self._rows:
            if q and q not in r.name.lower():
                continue
            shown.append(r)

        self.table.blockSignals(True)
        self.table.setRowCount(len(shown))

        for i, r in enumerate(shown):
            # Name
            it_name = QTableWidgetItem(r.name)
            it_name.setFont(QFont("", -1, QFont.Bold))
            
            # Tier
            it_tier = QTableWidgetItem(r.tier)
            
            # Status with better formatting
            status_text = "● Running" if r.running else "○ Stopped"
            it_run = QTableWidgetItem(status_text)
            it_run.setTextAlignment(Qt.AlignCenter)
            
            # PID
            pid_text = str(r.pid) if r.pid is not None else "—"
            it_pid = QTableWidgetItem(pid_text)
            it_pid.setTextAlignment(Qt.AlignCenter)
            
            # Log path
            it_log = QTableWidgetItem(r.log)

            # Color coding
            if r.running:
                # Green tint for running services
                running_color = QColor(30, 60, 40)  # Dark green
                text_color = QColor(100, 200, 120)  # Light green
                for it in (it_name, it_tier, it_run, it_pid, it_log):
                    it.setBackground(running_color)
                    it.setForeground(text_color)
                it_run.setForeground(QColor(80, 220, 120))  # Bright green for status
            else:
                # Darker for stopped services
                stopped_color = QColor(20, 20, 20)
                text_color = QColor(140, 140, 140)
                for it in (it_name, it_tier, it_run, it_pid, it_log):
                    it.setBackground(stopped_color)
                    it.setForeground(text_color)
                it_run.setForeground(QColor(180, 180, 180))

            self.table.setItem(i, 0, it_name)
            self.table.setItem(i, 1, it_tier)
            self.table.setItem(i, 2, it_run)
            self.table.setItem(i, 3, it_pid)
            self.table.setItem(i, 4, it_log)

        # Restore selection by name
        if keep:
            for i in range(self.table.rowCount()):
                if self.table.item(i, 0) and self.table.item(i, 0).text() == keep:
                    self.table.selectRow(i)
                    break

        self.table.blockSignals(False)
        self._update_details_from_selection()
        self._update_status_bar()

    def _update_details_from_selection(self) -> None:
        name = self._selected_name()
        if not name:
            self.details.setPlainText("")
            return
        
        r = self._row_by_name.get(name)
        if not r:
            return
        
        # Format details nicely
        details_text = f"""
╔═══════════════════════════════════════════════════════════╗
║  Service Details                                          ║
╠═══════════════════════════════════════════════════════════╣
║  Name:     {r.name:<45} ║
║  Status:   {'● RUNNING' if r.running else '○ STOPPED':<45} ║
║  PID:      {str(r.pid) if r.pid else '—':<45} ║
║  Tier:     {r.tier:<45} ║
║  Log Path: {r.log:<45} ║
╚═══════════════════════════════════════════════════════════╝

💡 Tip: Double-click a row to start/stop the service
"""
        
        # Store current scroll position
        scrollbar = self.details.verticalScrollBar()
        scroll_pos = scrollbar.value()
        
        # Get current text and append if there's command output
        current_text = self.details.toPlainText()
        if "╔═══════════════════════════════════════════════════════════╗" not in current_text:
            # No details yet, replace
            self.details.setPlainText(details_text)
        else:
            # Has command output, update just the details section
            lines = current_text.split('\n')
            start_idx = None
            end_idx = None
            for i, line in enumerate(lines):
                if "╔═══════════════════════════════════════════════════════════╗" in line:
                    start_idx = i
                if start_idx and "╚═══════════════════════════════════════════════════════════╝" in line:
                    end_idx = i + 1
                    break
            
            if start_idx is not None and end_idx is not None:
                new_lines = lines[:start_idx] + details_text.strip().split('\n') + lines[end_idx:]
                self.details.setPlainText('\n'.join(new_lines))
            else:
                # Fallback: prepend
                self.details.setPlainText(details_text + current_text)
        
        # Restore scroll position
        scrollbar.setValue(scroll_pos)


def main() -> None:
    import sys
    app = QApplication(sys.argv)
    app.setStyleSheet(_style())
    
    # Set application properties
    app.setApplicationName("Veil OS Hospital Console")
    app.setOrganizationName("Veil OS")
    
    w = VeilHospitalConsole()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
