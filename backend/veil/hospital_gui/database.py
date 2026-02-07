import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path.home() / "veil_os/backend/data/hospital.db"

def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            dob TEXT,
            status TEXT DEFAULT 'active',
            admitted_at TEXT,
            discharged_at TEXT,
            notes TEXT
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            patient_id INTEGER,
            timestamp TEXT,
            details TEXT
        );
    ''')
    conn.commit()
    conn.close()

def get_patients(status=None):
    conn = get_db()
    if status:
        rows = conn.execute("SELECT * FROM patients WHERE status=? ORDER BY id DESC", (status,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM patients ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_patient(pid):
    conn = get_db()
    row = conn.execute("SELECT * FROM patients WHERE id=?", (pid,)).fetchone()
    conn.close()
    return dict(row) if row else None

def add_patient(name, dob=None, notes=None):
    conn = get_db()
    now = datetime.now().isoformat()
    cur = conn.execute("INSERT INTO patients (name, dob, notes, admitted_at) VALUES (?,?,?,?)", (name, dob, notes, now))
    pid = cur.lastrowid
    conn.execute("INSERT INTO audit_log (action, patient_id, timestamp) VALUES (?,?,?)", ("admit", pid, now))
    conn.commit()
    conn.close()
    return pid

def update_patient(pid, name=None, dob=None, notes=None):
    conn = get_db()
    if name:
        conn.execute("UPDATE patients SET name=? WHERE id=?", (name, pid))
    if dob:
        conn.execute("UPDATE patients SET dob=? WHERE id=?", (dob, pid))
    if notes is not None:
        conn.execute("UPDATE patients SET notes=? WHERE id=?", (notes, pid))
    conn.execute("INSERT INTO audit_log (action, patient_id, timestamp) VALUES (?,?,?)", ("update", pid, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def discharge_patient(pid):
    conn = get_db()
    now = datetime.now().isoformat()
    conn.execute("UPDATE patients SET status='discharged', discharged_at=? WHERE id=?", (now, pid))
    conn.execute("INSERT INTO audit_log (action, patient_id, timestamp) VALUES (?,?,?)", ("discharge", pid, now))
    conn.commit()
    conn.close()

init_db()
