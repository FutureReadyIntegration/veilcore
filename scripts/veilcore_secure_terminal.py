"""
VeilCore / VeilOS Secure Terminal
"""

import os
import json
import subprocess
import hashlib
import base64
import time
from pathlib import Path
from urllib.request import Request, urlopen

CONFIG_DIR = Path.home() / ".config" / "veilcore"
STATE_DIR = CONFIG_DIR / "terminal"
STATE_DIR.mkdir(parents=True, exist_ok=True)


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


class VeilCoreAPI:

    def __init__(self, api_base, api_key):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key

    def get(self, route):
        req = Request(
            f"{self.api_base}{route}",
            headers={"X-API-Key": self.api_key}
        )

        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())


class Shell:

    def __init__(self, api_base=None, api_key=None, passphrase=None):
        self.cwd = Path.home()

    def run(self, command):

        if command.startswith("cd "):
            target = command[3:].strip()
            path = Path(target).expanduser()

            if not path.is_absolute():
                path = (self.cwd / path).resolve()

            if path.exists() and path.is_dir():
                self.cwd = path
                return str(self.cwd)

            return f"cd: no such directory: {target}"

        proc = subprocess.run(
            command,
            shell=True,
            cwd=str(self.cwd),
            capture_output=True,
            text=True
        )

        return proc.stdout + proc.stderr


class SecureLayer:

    def __init__(self, key="veilcore"):
        self.key = hashlib.sha256(key.encode()).digest()

    def encrypt(self, data):

        raw = data.encode()
        out = bytes(a ^ self.key[i % len(self.key)] for i, a in enumerate(raw))

        return base64.b64encode(out).decode()

    def decrypt(self, data):

        raw = base64.b64decode(data)

        out = bytes(a ^ self.key[i % len(self.key)] for i, a in enumerate(raw))

        return out.decode()


class VeilCoreSecureTerminal:

    def __init__(self, api_base=None, api_key=None, passphrase=None):

        api_base = api_base or os.getenv("VEIL_API", "http://localhost:9444")
        api_key = api_key or os.getenv("VEIL_API_KEY", "devkey123")

        self.api = VeilCoreAPI(api_base, api_key)
        self.shell = Shell()

        self.secure = False
        self.crypto = SecureLayer(passphrase or "veilcore")

    def prompt(self):

        mode = "secure" if self.secure else "standard"

        return f"[{mode}] user@veilcore:{self.shell.cwd}$ "

    def run_veil_command(self, cmd):

        if cmd == "health":
            return json.dumps(self.api.get("/health"), indent=2)

        if cmd == "organs":
            return json.dumps(self.api.get("/organs"), indent=2)

        if cmd == "status":

            h = self.api.get("/health")
            o = self.api.get("/organs")

            active = len([x for x in o.get("organs", []) if x.get("enabled")])

            return json.dumps({
                "api_ok": h.get("ok"),
                "organs_total": len(o.get("organs", [])),
                "organs_active": active,
                "secure_mode": self.secure
            }, indent=2)

        return None

    def execute(self, command):

        command = command.strip()

        if command == "":
            return ""

        if command == "secure on":
            self.secure = True
            return "secure mode enabled"

        if command == "secure off":
            self.secure = False
            return "secure mode disabled"

        if command == "clear":
            return "__CLEAR__"

        if command == "help":

            return """
VeilCore Commands

health
organs
status
secure on
secure off

Linux commands also supported.
"""

        veil = self.run_veil_command(command)

        if veil:
            return veil

        if command == "dir":
            command = "ls"

        return self.shell.run(command)


if __name__ == "__main__":

    term = VeilCoreSecureTerminal()

    print("VEILCORE TERMINAL")
    print("Linux + VeilCore commands available")
    print("type 'help' for commands\n")

    while True:

        try:
            cmd = input(term.prompt())
        except KeyboardInterrupt:
            print()
            continue
        except EOFError:
            break

        if cmd in ["exit", "quit"]:
            break

        out = term.execute(cmd)

        if out:
            print(out)
