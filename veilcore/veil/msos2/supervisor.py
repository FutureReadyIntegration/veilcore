import importlib
import json
import os
import socket
import threading
import time
import traceback
from typing import Any, Dict

HOST = os.environ.get("VEIL_MSOS_HOST", "127.0.0.1")
PORT = int(os.environ.get("VEIL_MSOS_PORT", "5510"))

STATE_FILE = os.environ.get("VEIL_MSOS_STATE_FILE", "/var/lib/veil/msos/organs.json")
STATE_DIR = os.path.dirname(STATE_FILE) if STATE_FILE else ""

# In-memory organ registry
# name -> {name,module,enabled,created_at,updated_at,last_error}
ORGANS: Dict[str, Dict[str, Any]] = {}

_LOCK = threading.RLock()


def _now() -> float:
    return time.time()


def _json_send(conn: socket.socket, obj: dict) -> None:
    data = (json.dumps(obj, default=str) + "\n").encode("utf-8", errors="replace")
    conn.sendall(data)


def _org_snapshot() -> list:
    with _LOCK:
        return [ORGANS[k] for k in sorted(ORGANS.keys())]


def _import_module(modname: str):
    return importlib.import_module(modname)


def _get_organ(name: str) -> Dict[str, Any]:
    with _LOCK:
        if name not in ORGANS:
            raise KeyError(f"organ_not_registered:{name}")
        return ORGANS[name]


def _set_last_error(name: str, err: str | None) -> None:
    with _LOCK:
        if name in ORGANS:
            ORGANS[name]["last_error"] = err
            ORGANS[name]["updated_at"] = _now()


def _safe_load_state() -> None:
    if not STATE_FILE:
        return
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return
        organs = data.get("organs")
        if not isinstance(organs, list):
            return

        loaded: Dict[str, Dict[str, Any]] = {}
        for o in organs:
            if not isinstance(o, dict):
                continue
            name = o.get("name")
            module = o.get("module")
            if not isinstance(name, str) or not name:
                continue
            if not isinstance(module, str) or not module:
                continue

            # Keep fields stable; fill defaults
            created_at = float(o.get("created_at", _now()))
            updated_at = float(o.get("updated_at", created_at))
            enabled = bool(o.get("enabled", True))
            last_error = o.get("last_error", None)

            loaded[name] = {
                "name": name,
                "module": module,
                "enabled": enabled,
                "created_at": created_at,
                "updated_at": updated_at,
                "last_error": last_error,
            }

        with _LOCK:
            ORGANS.clear()
            ORGANS.update(loaded)

        print(f"[msos2] loaded {len(ORGANS)} organs from {STATE_FILE}", flush=True)
    except FileNotFoundError:
        # first boot
        return
    except Exception as e:
        print(f"[msos2] state load failed: {e}", flush=True)


def _safe_save_state() -> None:
    if not STATE_FILE:
        return

    try:
        if STATE_DIR:
            os.makedirs(STATE_DIR, exist_ok=True)
        tmp = f"{STATE_FILE}.tmp.{os.getpid()}"
        payload = {"ts": _now(), "organs": _org_snapshot()}

        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True, default=str)
            f.write("\n")

        os.replace(tmp, STATE_FILE)  # atomic on POSIX
    except Exception as e:
        print(f"[msos2] state save failed: {e}", flush=True)


def _handle_invoke(req: dict) -> dict:
    """
    invoke request shape:
      {
        "cmd": "invoke",
        "name": "audit",
        "method": "status",
        "args": [...],    # optional
        "kwargs": {...},  # optional
      }
    """
    name = req.get("name")
    method = req.get("method")
    args = req.get("args", []) or []
    kwargs = req.get("kwargs", {}) or {}

    if not isinstance(name, str) or not name:
        return {"ok": False, "error": "invoke_missing_name", "ts": _now()}
    if not isinstance(method, str) or not method:
        return {"ok": False, "error": "invoke_missing_method", "ts": _now()}
    if not isinstance(args, list):
        return {"ok": False, "error": "invoke_args_must_be_list", "ts": _now()}
    if not isinstance(kwargs, dict):
        return {"ok": False, "error": "invoke_kwargs_must_be_dict", "ts": _now()}

    organ = _get_organ(name)
    if not organ.get("enabled", True):
        return {"ok": False, "error": f"organ_disabled:{name}", "ts": _now()}

    modname = organ["module"]

    try:
        mod = _import_module(modname)
        fn = getattr(mod, method, None)
        if fn is None or not callable(fn):
            raise AttributeError(f"missing_method:{method}")

        result = fn(*args, **kwargs)

        _set_last_error(name, None)
        return {"ok": True, "name": name, "method": method, "result": result}

    except Exception as e:
        tb = traceback.format_exc()
        _set_last_error(name, str(e))
        return {
            "ok": False,
            "name": name,
            "method": method,
            "error": f"invoke_failed:{e}",
            "traceback": tb,
        }


def _handle_client(conn: socket.socket) -> None:
    conn.settimeout(15.0)
    buf = b""

    try:
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                return
            buf += chunk

            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                line = line.strip()
                if not line:
                    continue

                try:
                    req = json.loads(line.decode("utf-8", errors="replace"))
                except Exception as e:
                    _json_send(conn, {"ok": False, "error": f"bad_json:{e}", "ts": _now()})
                    continue

                cmd = (req.get("cmd") or "ping").strip() if isinstance(req.get("cmd"), str) else req.get("cmd", "ping")

                if cmd == "ping":
                    _json_send(conn, {"ok": True, "pong": True, "ts": _now()})
                    continue

                if cmd == "list":
                    _json_send(conn, {"ok": True, "organs": _org_snapshot(), "ts": _now()})
                    continue

                if cmd == "register":
                    name = req.get("name")
                    module = req.get("module")
                    if not isinstance(name, str) or not name:
                        _json_send(conn, {"ok": False, "error": "register_missing_name", "ts": _now()})
                        continue
                    if not isinstance(module, str) or not module:
                        _json_send(conn, {"ok": False, "error": "register_missing_module", "ts": _now()})
                        continue

                    try:
                        _import_module(module)
                    except Exception as e:
                        _json_send(conn, {"ok": False, "error": f"register_import_failed:{e}", "ts": _now()})
                        continue

                    with _LOCK:
                        ts = _now()
                        if name in ORGANS:
                            ORGANS[name]["module"] = module
                            ORGANS[name]["updated_at"] = ts
                            ORGANS[name]["enabled"] = True
                            ORGANS[name]["last_error"] = None
                        else:
                            ORGANS[name] = {
                                "name": name,
                                "module": module,
                                "enabled": True,
                                "created_at": ts,
                                "updated_at": ts,
                                "last_error": None,
                            }

                    _safe_save_state()
                    _json_send(conn, {"ok": True, "name": name, "module": module, "ts": _now()})
                    continue

                if cmd in ("enable", "disable"):
                    name = req.get("name")
                    if not isinstance(name, str) or not name:
                        _json_send(conn, {"ok": False, "error": f"{cmd}_missing_name", "ts": _now()})
                        continue
                    try:
                        with _LOCK:
                            if name not in ORGANS:
                                raise KeyError(f"organ_not_registered:{name}")
                            ORGANS[name]["enabled"] = (cmd == "enable")
                            ORGANS[name]["updated_at"] = _now()
                        _safe_save_state()
                        _json_send(conn, {"ok": True, "name": name, "enabled": (cmd == "enable"), "ts": _now()})
                    except Exception as e:
                        _json_send(conn, {"ok": False, "error": str(e), "ts": _now()})
                    continue

                if cmd == "unregister":
                    name = req.get("name")
                    if not isinstance(name, str) or not name:
                        _json_send(conn, {"ok": False, "error": "unregister_missing_name", "ts": _now()})
                        continue
                    with _LOCK:
                        existed = name in ORGANS
                        if existed:
                            ORGANS.pop(name, None)
                    _safe_save_state()
                    _json_send(conn, {"ok": True, "name": name, "removed": bool(existed), "ts": _now()})
                    continue

                if cmd == "invoke":
                    try:
                        resp = _handle_invoke(req)
                    except Exception as e:
                        resp = {
                            "ok": False,
                            "error": f"invoke_dispatch_failed:{e}",
                            "traceback": traceback.format_exc(),
                            "ts": _now(),
                        }
                    resp.setdefault("ts", _now())
                    _json_send(conn, resp)
                    continue

                _json_send(conn, {"ok": False, "error": f"unknown_cmd:{cmd}", "ts": _now()})

    except socket.timeout:
        return
    finally:
        try:
            conn.close()
        except Exception:
            pass


def main() -> int:
    _safe_load_state()

    print(f"[msos2] starting control socket on {HOST}:{PORT}", flush=True)
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(128)

    while True:
        conn, _addr = srv.accept()
        threading.Thread(target=_handle_client, args=(conn,), daemon=True).start()


if __name__ == "__main__":
    raise SystemExit(main())
