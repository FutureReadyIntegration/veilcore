#!/usr/bin/env python3
"""Veil OS - PyQt Dashboard"""

import sys, os, json, subprocess, time
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

LEDGER = "/opt/veil_os/ledger.json"
RUN_DIR = "/opt/veil_os/var/run"

GLYPHS = {
    'epic':'🏥','imprivata':'🔐','guardian':'🛡️','backup':'💾','quarantine':'🔒',
    'firewall':'🔥','vault':'🏦','sentinel':'🗼','cortex':'🧠','mfa':'🔑',
    'audit':'📋','canary':'🐤','forensic':'🔬','watchdog':'🐕','gateway':'🚪',
    'portal':'🌀','scheduler':'📅','keystore':'🗝️','router':'🔀','monitor':'👁️',
    'logger':'📝','journal':'📔','init':'🌅','bios':'⚡','engine':'⚙️',
    'queue':'📬','relay':'📡','bridge':'🌉','fabric':'🕸️','daemon':'👻',
    'loader':'📦','socket':'🔌','cache':'💨','clock':'🕐','auth':'🔑'
}

def get_organs():
    with open(LEDGER) as f:
        return [e.get("organ") for e in json.load(f) if e.get("organ")]

def is_running(name):
    pf = f"{RUN_DIR}/{name}.pid"
    if os.path.exists(pf):
        try:
            with open(pf) as f: pid = int(f.read().strip())
            os.kill(pid, 0)
            return True
        except: pass
    return False

class OrganWidget(QFrame):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.setFixedSize(100, 80)
        self.setFrameStyle(QFrame.Box)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5,5,5,5)
        self.glyph = QLabel(GLYPHS.get(name, '⚙️'))
        self.glyph.setAlignment(Qt.AlignCenter)
        self.glyph.setFont(QFont('Segoe UI Emoji', 20))
        self.label = QLabel(name[:10])
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFont(QFont('Consolas', 8))
        layout.addWidget(self.glyph)
        layout.addWidget(self.label)
        self.set_status(False)
    
    def set_status(self, running):
        if running:
            self.setStyleSheet("QFrame{background:#003322;border:2px solid #00ff88;border-radius:8px}")
            self.label.setStyleSheet("color:#00ff88")
        else:
            self.setStyleSheet("QFrame{background:#220000;border:2px solid #442222;border-radius:8px}")
            self.label.setStyleSheet("color:#664444")

class StartWorker(QThread):
    progress = pyqtSignal(str)
    def run(self):
        for name in sorted(get_organs()):
            if not is_running(name):
                subprocess.run(['veil', 'start', name])
                self.progress.emit(name)
                time.sleep(0.3)

class VeilDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔱 VEIL OS - Hospital Cybersecurity")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet("QMainWindow{background:#0a0a0f}")
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(20)
        
        # Header
        title = QLabel("🔱 VEIL OS")
        title.setFont(QFont('Arial', 36, QFont.Bold))
        title.setStyleSheet("color:#00ff88")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        sub = QLabel("Living Hospital Cybersecurity System")
        sub.setStyleSheet("color:#666")
        sub.setAlignment(Qt.AlignCenter)
        layout.addWidget(sub)
        
        # Stats
        stats = QHBoxLayout()
        self.running_label = self.make_stat("ONLINE", "#00ff88")
        self.stopped_label = self.make_stat("OFFLINE", "#ff4444")
        self.total_label = self.make_stat("TOTAL", "#4488ff")
        stats.addStretch()
        stats.addWidget(self.running_label[0])
        stats.addWidget(self.stopped_label[0])
        stats.addWidget(self.total_label[0])
        stats.addStretch()
        layout.addLayout(stats)
        
        # Progress
        self.progress = QProgressBar()
        self.progress.setStyleSheet("""
            QProgressBar{background:#111;border:none;height:25px;border-radius:12px}
            QProgressBar::chunk{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #00ff88,stop:1 #00ffcc);border-radius:12px}
        """)
        layout.addWidget(self.progress)
        
        # Buttons
        btns = QHBoxLayout()
        self.start_btn = QPushButton("⚡ ACTIVATE ALL ORGANS")
        self.start_btn.setFont(QFont('Arial', 14, QFont.Bold))
        self.start_btn.setStyleSheet("QPushButton{background:#00ff88;color:#000;padding:15px 30px;border-radius:8px}QPushButton:hover{background:#00ffaa}")
        self.start_btn.clicked.connect(self.start_all)
        
        self.stop_btn = QPushButton("🛑 SHUTDOWN ALL")
        self.stop_btn.setFont(QFont('Arial', 14, QFont.Bold))
        self.stop_btn.setStyleSheet("QPushButton{background:#ff4444;color:#fff;padding:15px 30px;border-radius:8px}QPushButton:hover{background:#ff6666}")
        self.stop_btn.clicked.connect(self.stop_all)
        
        btns.addStretch()
        btns.addWidget(self.start_btn)
        btns.addWidget(self.stop_btn)
        btns.addStretch()
        layout.addLayout(btns)
        
        # Grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none}")
        grid_widget = QWidget()
        self.grid = QGridLayout(grid_widget)
        self.grid.setSpacing(10)
        scroll.setWidget(grid_widget)
        layout.addWidget(scroll)
        
        # Create organ widgets
        self.organs = {}
        organs = sorted(get_organs())
        cols = 10
        for i, name in enumerate(organs):
            w = OrganWidget(name)
            self.organs[name] = w
            self.grid.addWidget(w, i // cols, i % cols)
        
        # Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1000)
        self.refresh()
    
    def make_stat(self, label, color):
        frame = QFrame()
        frame.setStyleSheet(f"QFrame{{background:#111;border:1px solid {color}44;border-radius:10px;padding:10px}}")
        layout = QVBoxLayout(frame)
        num = QLabel("0")
        num.setFont(QFont('Arial', 32, QFont.Bold))
        num.setStyleSheet(f"color:{color}")
        num.setAlignment(Qt.AlignCenter)
        lbl = QLabel(label)
        lbl.setStyleSheet("color:#888")
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(num)
        layout.addWidget(lbl)
        return frame, num
    
    def refresh(self):
        running = 0
        total = len(self.organs)
        for name, widget in self.organs.items():
            r = is_running(name)
            widget.set_status(r)
            if r: running += 1
        self.running_label[1].setText(str(running))
        self.stopped_label[1].setText(str(total - running))
        self.total_label[1].setText(str(total))
        self.progress.setValue(int(running / total * 100) if total else 0)
    
    def start_all(self):
        self.start_btn.setEnabled(False)
        self.worker = StartWorker()
        self.worker.progress.connect(lambda n: self.refresh())
        self.worker.finished.connect(lambda: self.start_btn.setEnabled(True))
        self.worker.start()
    
    def stop_all(self):
        subprocess.run(['veil', 'stop-all'])
        self.refresh()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = VeilDashboard()
    win.show()
    sys.exit(app.exec_())
