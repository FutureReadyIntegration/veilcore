from __future__ import annotations

import sys
from typing import List

from PySide6.QtCore import Qt, QProcess
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QTextEdit,
    QListWidget,
    QListWidgetItem,
    QComboBox,
    QMessageBox,
    QFileDialog,
)

from .veil_organs import load_organs, list_organs, get_organ, filter_by_tier

VEIL_BIN = "/srv/veil_os/api_venv/bin/veil"


def _s(x) -> str:
    return "" if x is None else str(x)


def _clean_glyph(g: str) -> str:
    # Strip common variation selector that causes tofu in some render paths
    return _s(g).replace("\ufe0f", "").strip()


class OrgRow(QWidget):
    """
    List row widget that renders the glyph using an emoji font, while keeping
    name/tier in a normal UI font.
    """

    def __init__(self, glyph: str, name: str, tier: str) -> None:
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(10)

        self.glyph = QLabel(_clean_glyph(glyph))
        self.glyph.setFixedWidth(30)
        self.glyph.setAlignment(Qt.AlignCenter)
        self.glyph.setFont(QFont("Noto Color Emoji", 13))
        lay.addWidget(self.glyph)

        self.name = QLabel(name)
        self.name.setFont(QFont("DejaVu Sans", 10))
        lay.addWidget(self.name, 1)

        self.tier = QLabel(tier)
        self.tier.setAlignment(Qt.AlignCenter)
        self.tier.setFixedWidth(44)
        self.tier.setFont(QFont("DejaVu Sans", 9, QFont.Bold))
        self.tier.setStyleSheet("padding:2px 6px; border:1px solid #C9C9C9; border-radius:8px;")
        lay.addWidget(self.tier)


class Main(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Veil OS — Hospital Command Center")
        self.setMinimumSize(1200, 720)

        load_organs()
        self._names: List[str] = []
        self.cmd = "compile"

        # Subprocess controller (non-blocking, streams output)
        self.proc = QProcess(self)
        self.proc.readyReadStandardOutput.connect(self._on_stdout)
        self.proc.readyReadStandardError.connect(self._on_stderr)
        self.proc.finished.connect(self._on_finished)

        root = QHBoxLayout(self)

        # ---------------- LEFT: Actions + Safety ----------------
        left = QVBoxLayout()
        root.addLayout(left, 1)

        title = QLabel("VEIL OS")
        title.setFont(QFont("DejaVu Sans", 18, QFont.Bold))
        left.addWidget(title)

        subtitle = QLabel("Hospital Command Center • Operator-safe workflows • Auditable actions")
        subtitle.setFont(QFont("DejaVu Sans", 10))
        subtitle.setStyleSheet("color:#444;")
        left.addWidget(subtitle)

        self.mode = QLabel("MODE: PREVIEW")
        self._set_mode_preview()
        left.addWidget(self.mode)

        for label, cmd in [
            ("Compile", "compile"),
            ("Compile P0", "compile-p0"),
            ("Compile All", "compile-all"),
            ("Harden", "harden"),
        ]:
            b = QPushButton(label)
            b.clicked.connect(lambda _=False, c=cmd: self.select_cmd(c))
            left.addWidget(b)

        left.addSpacing(10)
        left.addWidget(QLabel("Target directory"))
        self.target = QLineEdit()
        left.addWidget(self.target)

        browse = QPushButton("Browse…")
        browse.clicked.connect(self.browse_target)
        left.addWidget(browse)

        left.addSpacing(10)
        self.apply_mode = QComboBox()
        self.apply_mode.addItems(["Preview (dry-run)", "Apply (requires YES)"])
        self.apply_mode.currentIndexChanged.connect(self.update_preview)
        left.addWidget(self.apply_mode)

        self.confirm = QLineEdit()
        self.confirm.setPlaceholderText("Type YES to apply")
        self.confirm.textChanged.connect(self.update_preview)
        left.addWidget(self.confirm)

        left.addStretch(1)

        # ---------------- MIDDLE: Organs ----------------
        mid = QVBoxLayout()
        root.addLayout(mid, 2)

        hdr = QLabel("Organs (Service Modules)")
        hdr.setFont(QFont("DejaVu Sans", 13, QFont.Bold))
        mid.addWidget(hdr)

        controls = QHBoxLayout()
        mid.addLayout(controls)

        self.tier = QComboBox()
        self.tier.addItems(["ALL", "P0", "P1", "P2"])
        self.tier.currentIndexChanged.connect(self.refresh_list)
        controls.addWidget(QLabel("Tier"))
        controls.addWidget(self.tier)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search…")
        self.search.textChanged.connect(self.refresh_list)
        controls.addWidget(self.search, 1)

        self.listw = QListWidget()
        self.listw.currentRowChanged.connect(self.on_select)
        mid.addWidget(self.listw, 2)

        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setFont(QFont("DejaVu Sans Mono", 10))
        mid.addWidget(self.detail, 1)

        # ---------------- RIGHT: Run + Output + Transport ----------------
        right = QVBoxLayout()
        root.addLayout(right, 2)

        self.preview = QLabel("")
        self.preview.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.preview.setFont(QFont("DejaVu Sans Mono", 9))
        right.addWidget(self.preview)

        transport = QHBoxLayout()
        right.addLayout(transport)

        self.btn_play = QPushButton("▶ Play")
        self.btn_play.clicked.connect(self.run_cmd)
        transport.addWidget(self.btn_play)

        self.btn_stop = QPushButton("⏹ Stop")
        self.btn_stop.clicked.connect(self.stop_cmd)
        self.btn_stop.setEnabled(False)
        transport.addWidget(self.btn_stop)

        self.btn_cancel = QPushButton("✖ Cancel")
        self.btn_cancel.clicked.connect(self.cancel_run)
        transport.addWidget(self.btn_cancel)

        transport.addStretch(1)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("DejaVu Sans Mono", 10))
        right.addWidget(self.output, 1)

        # init
        self.refresh_list()
        self.update_preview()

    # ---------------- UI helpers ----------------
    def _set_mode_preview(self) -> None:
        self.mode.setText("MODE: PREVIEW")
        self.mode.setStyleSheet("padding:6px; background:#0E9384; color:white; border-radius:8px;")

    def _set_mode_apply(self) -> None:
        self.mode.setText("MODE: APPLY")
        self.mode.setStyleSheet("padding:6px; background:#EF4444; color:white; border-radius:8px;")

    def _set_running(self, running: bool) -> None:
        self.btn_play.setEnabled(not running)
        self.btn_stop.setEnabled(running)

    # ---------------- Command assembly ----------------
    def select_cmd(self, cmd: str) -> None:
        self.cmd = cmd
        self.update_preview()

    def browse_target(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select target directory")
        if d:
            self.target.setText(d)
            self.update_preview()

    def build_cmd(self) -> List[str]:
        args = [VEIL_BIN, self.cmd]

        if self.cmd in {"compile-all", "harden"}:
            if not self.target.text().strip():
                raise ValueError("Target required for compile-all/harden")
            args += ["--target", self.target.text().strip()]

        apply_mode = (self.apply_mode.currentIndex() == 1)
        if apply_mode:
            if self.confirm.text().strip() != "YES":
                raise ValueError("Type YES to apply")
            args += ["--yes"]
        else:
            args += ["--dry-run"]

        args += ["--no-input"]
        return args

    def update_preview(self) -> None:
        try:
            cmd = self.build_cmd()
            self.preview.setText(" ".join(cmd))
            if self.apply_mode.currentIndex() == 1:
                self._set_mode_apply()
            else:
                self._set_mode_preview()
        except Exception as e:
            self.preview.setText(f"(incomplete) {e}")
            # Keep mode indicator honest
            if self.apply_mode.currentIndex() == 1:
                self._set_mode_apply()
            else:
                self._set_mode_preview()

    # ---------------- Organs list ----------------
    def refresh_list(self) -> None:
        tier = self.tier.currentText()
        search = self.search.text().strip().lower()

        if tier == "ALL":
            names = list_organs()
        else:
            names = filter_by_tier(tier)

        if search:
            names = [n for n in names if search in n.lower()]

        self._names = names
        self.listw.clear()

        for n in names:
            o = get_organ(n) or {}
            glyph = _s(o.get("glyph"))
            name = _s(o.get("name", n))
            t = _s(o.get("tier"))

            item = QListWidgetItem()
            widget = OrgRow(glyph, name, t)
            item.setSizeHint(widget.sizeHint())
            self.listw.addItem(item)
            self.listw.setItemWidget(item, widget)

        if names:
            self.listw.setCurrentRow(0)
        else:
            self.detail.setPlainText("(no matching organs)")

    def on_select(self, row: int) -> None:
        if row < 0 or row >= len(self._names):
            return
        name = self._names[row]
        o = get_organ(name) or {}
        self.detail.setPlainText(
            f'{_clean_glyph(_s(o.get("glyph")))}  {_s(o.get("name", name))}\n'
            f'TIER: {_s(o.get("tier"))}\n\n'
            f'AFFIRMATION:\n{_s(o.get("affirmation"))}\n'
        )

    # ---------------- Process controls ----------------
    def run_cmd(self) -> None:
        if self.proc.state() != QProcess.NotRunning:
            QMessageBox.warning(self, "Busy", "A command is already running. Stop it first.")
            return

        try:
            cmd = self.build_cmd()
        except Exception as e:
            QMessageBox.critical(self, "Blocked", str(e))
            return

        self.output.append("▶ " + " ".join(cmd))
        self.output.append("")

        self.proc.setProgram(cmd[0])
        self.proc.setArguments(cmd[1:])
        self.proc.start()

        if not self.proc.waitForStarted(2000):
            QMessageBox.critical(self, "Failed", "Could not start process.")
            return

        self._set_running(True)

    def stop_cmd(self) -> None:
        if self.proc.state() == QProcess.NotRunning:
            return
        self.output.append("⏹ Stop requested…")
        self.proc.terminate()
        if not self.proc.waitForFinished(1500):
            self.output.append("⛔ Force kill…")
            self.proc.kill()

    def cancel_run(self) -> None:
        # Cancel = stop (if running) + clear output
        if self.proc.state() != QProcess.NotRunning:
            self.stop_cmd()
        self.output.clear()
        self.output.append("✖ Canceled. Output cleared.")
        self.output.append("")
        self.update_preview()

    def _on_stdout(self) -> None:
        data = bytes(self.proc.readAllStandardOutput()).decode("utf-8", errors="replace")
        if data:
            self.output.append(data.rstrip("\n"))

    def _on_stderr(self) -> None:
        data = bytes(self.proc.readAllStandardError()).decode("utf-8", errors="replace")
        if data:
            self.output.append(data.rstrip("\n"))

    def _on_finished(self, code: int, _status) -> None:
        self.output.append("")
        self.output.append(f"⟡ exit={code}")
        self.output.append("")
        self._set_running(False)


def main() -> None:
    app = QApplication(sys.argv)
    w = Main()
    w.show()
    sys.exit(app.exec())
