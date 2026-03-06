#!/usr/bin/env python3
"""
VeilCore Desktop Launcher (Option 2)
===================================

- If API is not running, start uvicorn (veil.api:app) detached
- Log uvicorn output to ~/.config/veilcore/uvicorn-9444.log
- Print VeilCore attestation (/signature) + liveness (/signature/challenge)
- Exit cleanly (does NOT keep a PIPE or kill uvicorn on exit)
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


VEIL_API = os.environ.get("VEIL_API", "http://127.0.0.1:9444").rstrip("/")
REPO_ROOT = Path.home() / "veilcore"
VENV_PY = Path("/opt/veil_os/venv/bin/python")

LOG_DIR = Path.home() / ".config" / "veilcore"
UVICORN_LOG = LOG_DIR / "uvicorn-9444.log"


def _http_get_json(url: str, timeout: float = 2.5) -> dict:
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        data = resp.read().decode("utf-8", errors="replace")
        return json.loads(data)


def _tcp_port_open(host: str, port: int, timeout: float = 0.35) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _wait_for_health(base_url: str, timeout_s: float = 20.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            _http_get_json(f"{base_url}/health", timeout=2.0)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def _parse_host_port(base_url: str) -> tuple[str, int]:
    host = "127.0.0.1"
    port = 9444
    s = base_url.replace("http://", "").replace("https://", "")
    s = s.split("/", 1)[0]
    if ":" in s:
        host, p = s.rsplit(":", 1)
        port = int(p)
    else:
        host = s
    return host, port


def _ensure_identity_dir() -> Path:
    identity_dir = Path(os.environ.get("VEILCORE_IDENTITY_DIR", str(Path.home() / ".veilcore" / "identity")))
    identity_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(identity_dir, 0o700)
    except PermissionError:
        pass
    return identity_dir



def _pid_listening_on(port: int) -> str | None:
    # Linux-only, but you're on Ubuntu/WSL
    try:
        import subprocess, re
        out = subprocess.check_output(["bash", "-lc", f"sudo ss -lntp | awk '/:{port}/ {{print}}'"], text=True).strip()
        if "pid=" not in out:
            return None
        m = re.search(r"pid=(\d+)", out)
        return m.group(1) if m else None
    except Exception:
        return None


def _restart_if_unhealthy(base_url: str) -> None:
    host, port = _parse_host_port(base_url)
    if not _tcp_port_open(host, port):
        return
    # Port is open; ensure API is responsive
    try:
        _http_get_json(f"{base_url}/health", timeout=1.5)
        return
    except Exception:
        pass

    pid = _pid_listening_on(port)
    if pid:
        # best effort
        try:
            subprocess.call(["sudo", "kill", pid])
            time.sleep(0.75)
        except Exception:
            pass


def _start_api_detached_if_needed(base_url: str) -> None:
    host, port = _parse_host_port(base_url)
    if _tcp_port_open(host, port):
        return  # already running

    identity_dir = _ensure_identity_dir()

    env = os.environ.copy()
    env["VEIL_API"] = base_url
    env["VEILCORE_IDENTITY_DIR"] = str(identity_dir)
    env["PYTHONPATH"] = f"{REPO_ROOT}:{env.get('PYTHONPATH','')}".strip(":")

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(VENV_PY),
        "-m",
        "uvicorn",
        "veil.api:app",
        "--host",
        host,
        "--port",
        str(port),
        "--log-level",
        "info",
    ]

    # Open logfile (line-buffered). No PIPE -> no deadlock.
    f = open(UVICORN_LOG, "a", buffering=1)

    # Detach: new session so launcher stop/exit doesn't wedge/kill server.
    subprocess.Popen(
        cmd,
        cwd=str(REPO_ROOT),
        env=env,
        stdout=f,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )


def _print_splash(base_url: str) -> None:
    print("=" * 56)
    print("                 VEILCORE DEFENSE PLATFORM")
    print(f"                 API: {base_url}")
    print("=" * 56)


def _print_proofs(base_url: str) -> None:
    sig = _http_get_json(f"{base_url}/signature", timeout=3.0)
    nonce = f"veilcore-{int(time.time())}"
    chal = _http_get_json(f"{base_url}/signature/challenge?nonce={nonce}", timeout=3.0)

    def pick(d: dict, k: str) -> str:
        v = d.get(k)
        return "" if v is None else str(v)

    print("\n[VeilCore Attestation]")
    print(f" product:        {pick(sig, 'product')}")
    print(f" node:           {pick(sig, 'node')}")
    print(f" component:      {pick(sig, 'component')}")
    print(f" build_id:       {pick(sig, 'build_id')}")
    print(f" pubkey_fpr16:   {pick(sig, 'pubkey_fpr16')}")
    print(f" manifest_sha16: {pick(sig, 'manifest_sha16')}")
    print(f" eye_svg_sha16:  {pick(sig, 'eye_svg_sha16')}")
    print(f" sig_b64u:       {pick(sig, 'sig_b64u')[:24]}...")

    print("\n[VeilCore Liveness]")
    print(f" nonce:          {pick(chal, 'nonce')}")
    print(f" ts:             {pick(chal, 'ts')}")
    print(f" sig_b64u:       {pick(chal, 'sig_b64u')[:24]}...\n")


def main() -> int:
    base_url = VEIL_API
    _print_splash(base_url)

    try:
        _restart_if_unhealthy(base_url)
        _start_api_detached_if_needed(base_url)

        if not _wait_for_health(base_url, timeout_s=25.0):
            print(f"⟡ VeilCore Launcher: API not healthy yet. Check log: {UVICORN_LOG}")
            return 1

        _print_proofs(base_url)
        print(f"⟡ Uvicorn log: {UVICORN_LOG}")
        return 0

    except (HTTPError, URLError) as e:
        print(f"⟡ VeilCore Launcher: HTTP error: {e}")
        return 2
    except Exception as e:
        print(f"⟡ VeilCore Launcher: error: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
