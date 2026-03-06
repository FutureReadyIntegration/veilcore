#!/usr/bin/env python3
import os, subprocess, sys
from pathlib import Path

home = Path.home()
repo = home / "veilcore"

env = os.environ.copy()
env.setdefault("VEILCORE_IDENTITY_DIR", str(home / ".veilcore" / "identity"))
env.setdefault("PYTHONPATH", str(repo))

# 1) Ensure VeilCore API is up (detached + logfile)
subprocess.call([sys.executable, str(repo / "scripts" / "veilcore_launcher.py")], env=env)

# 2) Launch the VeilOS UI (splash + OE)
os.execvpe(sys.executable, [sys.executable, str(repo / "scripts" / "veilos_desktop.py")], env)
