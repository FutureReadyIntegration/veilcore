import os
import time

NAME = "fabric"
LOG_PATH = f"/opt/veil_os/var/log/fabric.log"

_running = False
_pid = None

def start():
    global _running, _pid
    if _running:
        return False
    _running = True
    _pid = os.getpid()
    log(f"{NAME} started")
    return True

def stop():
    global _running
    if not _running:
        return False
    _running = False
    log(f"{NAME} stopped")
    return True

def status():
    return {
        "name": NAME,
        "running": _running,
        "pid": _pid,
        "log": LOG_PATH,
    }

def log(msg):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(f"[{time.strftime('%F %T')}] {msg}\n")
