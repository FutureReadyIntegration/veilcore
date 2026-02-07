#!/usr/bin/env python3
import json
import subprocess
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

MANIFEST = "/opt/veil_os/supervisor/organs.json"

def get_systemd_status(unit):
    if unit is None or unit == "null":
        return "no-unit"

    try:
        result = subprocess.run(
            ["systemctl", "is-active", unit],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/organs":
            if os.path.exists(MANIFEST):
                with open(MANIFEST, "r") as f:
                    data = json.load(f)
            else:
                data = {"organs": []}

            # Enrich with live systemd status
            for organ in data.get("organs", []):
                unit = organ.get("unit")
                organ["status"] = get_systemd_status(unit)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        else:
            self.send_response(404)
            self.end_headers()

def run():
    server = HTTPServer(("0.0.0.0", 8085), Handler)
    print("Supervisor running on port 8085")
    server.serve_forever()

if __name__ == "__main__":
    run()
