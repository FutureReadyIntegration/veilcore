#!/usr/bin/env python3
"""Build standalone Veil Hospital GUI executable"""
import subprocess
import sys

def build():
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "VeilHospital",
        "--onefile",
        "--add-data", "veil/hospital_gui/templates:veil/hospital_gui/templates",
        "--add-data", "veil/hospital_gui/static:veil/hospital_gui/static",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "veil.hospital_gui.database",
        "veil/hospital_gui/__main__.py"
    ]
    subprocess.run(cmd, check=True)
    print("\n✅ Built: dist/VeilHospital")

if __name__ == "__main__":
    build()
