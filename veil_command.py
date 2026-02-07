#!/usr/bin/env python3
import sys,os,json,subprocess,time
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

LEDGER="/opt/veil_os/ledger.json"
RUN="/opt/veil_os/var/run"
GLYPHS={'epic':'🏥','imprivata':'🔐','guardian':'🛡️','backup':'💾','quarantine':'🔒','firewall':'🔥','vault':'🏦','sentinel':'🗼','cortex':'🧠','mfa':'🔑','audit':'📋','canary':'🐤','forensic':'🔬','watchdog':'🐕','gateway':'🚪','scheduler':'📅','keystore':'🗝️','router':'🔀','monitor':'👁️','logger':'📝','journal':'📔','init':'🌅','bios':'⚡','engine':'⚙️','daemon':'👻','auth':'🔑'}

def get_organs():
    with open(LEDGER) as f:return sorted([e.get("organ")for e in json.load(f)if e.get("organ")])
def is_running(n):
    pf=f"{RUN}/{n}.pid"
    if os.path.exists(pf):
        try:
            with open(pf)as f:pid=int(f.read().strip())
            os.kill(pid,0);return True
        except:pass
    return False

class OrganWidget(QFrame):
    def __init__(s,name):
        super().__init__();s.name=name;s.setFixedSize(85,65)
        l=QVBoxLayout(s);l.setContentsMargins(3,3,3,3);l.setSpacing(1)
        s.glyph=QLabel(GLYPHS.get(name,'⚙️'));s.glyph.setAlignment(Qt.AlignCenter);s.glyph.setFont(QFont('Segoe UI Emoji',16))
        s.lbl=QLabel(name[:9]);s.lbl.setAlignment(Qt.AlignCenter);s.lbl.setFont(QFont('Consolas',7))
        l.addWidget(s.glyph);l.addWidget(s.lbl);s.set_status(False)
    def set_status(s,on):
        if on:s.setStyleSheet("QFrame{background:#002211;border:2px solid #00ff88;border-radius:5px}QLabel{color:#00ff88}")
        else:s.setStyleSheet("QFrame{background:#1a0808;border:1px solid #331111;border-radius:5px}QLabel{color:#442222}")

class StartWorker(QThread):
    started=pyqtSignal(str);done=pyqtSignal()
    def run(s):
        for n in get_organs():
            if not is_running(n):subprocess.run(['veil','start',n],capture_output=True);s.started.emit(n);time.sleep(0.2)
        s.done.emit()

class VeilCommand(QMainWindow):
    def __init__(s):
        super().__init__();s.setWindowTitle("🔱 VEIL OS");s.setMinimumSize(1200,800);s.setStyleSheet("QMainWindow{background:#0a0a0f}")
        c=QWidget();s.setCentralWidget(c);m=QVBoxLayout(c)
        h=QLabel("🔱 VEIL OS");h.setFont(QFont('Arial',28,QFont.Bold));h.setStyleSheet("color:#00ff88");h.setAlignment(Qt.AlignCenter);m.addWidget(h)
        t=QLabel("Living Hospital Cybersecurity");t.setStyleSheet("color:#555");t.setAlignment(Qt.AlignCenter);m.addWidget(t)
        st=QHBoxLayout();s.on_l=QLabel("0");s.on_l.setFont(QFont('Arial',36,QFont.Bold));s.on_l.setStyleSheet("color:#00ff88")
        s.off_l=QLabel("0");s.off_l.setFont(QFont('Arial',36,QFont.Bold));s.off_l.setStyleSheet("color:#ff4444")
        s.tot_l=QLabel("0");s.tot_l.setFont(QFont('Arial',36,QFont.Bold));s.tot_l.setStyleSheet("color:#4488ff")
        for w,tx in[(s.on_l,"ONLINE"),(s.off_l,"OFFLINE"),(s.tot_l,"TOTAL")]:
            f=QFrame();f.setStyleSheet("background:#111;border:1px solid #333;border-radius:8px");fl=QVBoxLayout(f);w.setAlignment(Qt.AlignCenter);fl.addWidget(w);lb=QLabel(tx);lb.setStyleSheet("color:#666");lb.setAlignment(Qt.AlignCenter);fl.addWidget(lb);st.addWidget(f)
        m.addLayout(st)
        s.prog=QProgressBar();s.prog.setFixedHeight(20);s.prog.setStyleSheet("QProgressBar{background:#111;border:none;border-radius:10px}QProgressBar::chunk{background:#00ff88;border-radius:10px}");m.addWidget(s.prog)
        bt=QHBoxLayout();s.start_b=QPushButton("⚡ ACTIVATE ALL");s.start_b.setStyleSheet("background:#00ff88;color:#000;padding:10px 20px;border-radius:5px;font-weight:bold");s.start_b.clicked.connect(s.start_all)
        s.stop_b=QPushButton("🛑 SHUTDOWN");s.stop_b.setStyleSheet("background:#ff4444;color:#fff;padding:10px 20px;border-radius:5px;font-weight:bold");s.stop_b.clicked.connect(s.stop_all)
        bt.addStretch();bt.addWidget(s.start_b);bt.addWidget(s.stop_b);bt.addStretch();m.addLayout(bt)
        sc=QScrollArea();sc.setWidgetResizable(True);sc.setStyleSheet("border:none");gw=QWidget();s.grid=QGridLayout(gw);s.grid.setSpacing(5);sc.setWidget(gw);m.addWidget(sc)
        s.organs={};[s.organs.__setitem__(n,OrganWidget(n))or s.grid.addWidget(s.organs[n],i//10,i%10)for i,n in enumerate(get_organs())]
        s.timer=QTimer();s.timer.timeout.connect(s.refresh);s.timer.start(500);s.refresh()
    def refresh(s):
        on=sum(1 for n,w in s.organs.items()if is_running(n)and(w.set_status(True)or True)or not w.set_status(False))
        s.on_l.setText(str(on));s.off_l.setText(str(len(s.organs)-on));s.tot_l.setText(str(len(s.organs)));s.prog.setValue(int(on/len(s.organs)*100))
    def start_all(s):s.start_b.setEnabled(False);s.w=StartWorker();s.w.started.connect(lambda n:s.refresh());s.w.done.connect(lambda:s.start_b.setEnabled(True));s.w.start()
    def stop_all(s):subprocess.run(['veil','stop-all']);s.refresh()

if __name__=='__main__':app=QApplication(sys.argv);w=VeilCommand();w.show();sys.exit(app.exec_())
