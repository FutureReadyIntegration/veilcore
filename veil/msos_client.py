import json
import os
import socket
from typing import Any, Dict, List, Optional

MSOS_HOST = os.environ.get("VEIL_MSOS_HOST", "127.0.0.1")
MSOS_PORT = int(os.environ.get("VEIL_MSOS_PORT", "5510"))
MSOS_TIMEOUT = float(os.environ.get("VEIL_MSOS_TIMEOUT_SEC", "2.0"))

def _send_recv(req: Dict[str, Any]) -> Dict[str, Any]:
    data = (json.dumps(req) + "\n").encode("utf-8", errors="replace")
    with socket.create_connection((MSOS_HOST, MSOS_PORT), timeout=MSOS_TIMEOUT) as s:
        s.sendall(data)
        s.settimeout(MSOS_TIMEOUT)
        out = b""
        while not out.endswith(b"\n"):
            chunk = s.recv(4096)
            if not chunk:
                break
            out += chunk
    if not out:
        return {"ok": False, "error": "msos_empty_response"}
    try:
        return json.loads(out.decode("utf-8", errors="replace").strip())
    except Exception as e:
        return {"ok": False, "error": f"msos_bad_json:{e}", "raw": out[:200].decode("utf-8", errors="replace")}

def ping() -> Dict[str, Any]:
    return _send_recv({"cmd": "ping"})

def list_organs() -> Dict[str, Any]:
    return _send_recv({"cmd": "list"})

def invoke(name: str, method: str, args: Optional[List[Any]] = None, kwargs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return _send_recv({
        "cmd": "invoke",
        "name": name,
        "method": method,
        "args": args or [],
        "kwargs": kwargs or {},
    })
