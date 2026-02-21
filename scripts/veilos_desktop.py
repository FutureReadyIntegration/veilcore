#!/usr/bin/env python3

"""
Veil OS Desktop Generator
Creates/updates the live cockpit desktop scaffold.
"""

from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
STATIC = BASE / "backend" / "veil" / "hospital_gui" / "static"

STATIC.mkdir(parents=True, exist_ok=True)

files = {
    "desktop.html": """<!DOCTYPE html>
<html>
<head>
<link rel="stylesheet" href="desktop.css">
</head>
<body>
<div id="taskbar"></div>
<div id="desktop"></div>
<script type="module" src="desktop.js"></script>
</body>
</html>
""",

    "desktop.css": """body{
  margin:0;
  background:#0b0f13;
  color:white;
  font-family:sans-serif;
}
.window{
  position:absolute;
  width:320px;
  background:#161b22;
  border:1px solid #333;
  border-radius:8px;
}
.titlebar{
  background:#21262d;
  padding:8px;
  cursor:move;
}
""",

    "desktop.js": """console.log("Veil desktop loaded");"""
}

for name, content in files.items():
    dst = STATIC / name
    dst.write_text(content)
    print(f"Created: {dst}")

print("\nDesktop scaffold generated.")
