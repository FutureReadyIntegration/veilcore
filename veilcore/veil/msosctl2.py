import json, os, socket, sys

HOST = os.environ.get("VEIL_MSOS_HOST", "127.0.0.1")
PORT = int(os.environ.get("VEIL_MSOS_PORT", "5510"))

def call(req: dict):
    data = (json.dumps(req) + "\n").encode()
    with socket.create_connection((HOST, PORT), timeout=2.0) as s:
        s.sendall(data)
        out = b""
        while not out.endswith(b"\n"):
            chunk = s.recv(4096)
            if not chunk:
                break
            out += chunk
    return json.loads(out.decode().strip() or "{}")

def _j(s, default):
    if s is None:
        return default
    s = s.strip()
    if not s:
        return default
    return json.loads(s)

def main(argv):
    if len(argv) < 2:
        cmd = "ping"
        req = {"cmd": cmd}
        print(json.dumps(call(req), indent=2))
        return 0

    cmd = argv[1]

    if cmd in ("ping", "list"):
        req = {"cmd": cmd}
        print(json.dumps(call(req), indent=2))
        return 0

    if cmd == "register":
        if len(argv) < 4:
            raise SystemExit("usage: msosctl2.py register <name> <module>")
        req = {"cmd": "register", "name": argv[2], "module": argv[3]}
        print(json.dumps(call(req), indent=2))
        return 0

    if cmd in ("enable", "disable"):
        if len(argv) < 3:
            raise SystemExit(f"usage: msosctl2.py {cmd} <name>")
        req = {"cmd": cmd, "name": argv[2]}
        print(json.dumps(call(req), indent=2))
        return 0

    if cmd == "invoke":
        if len(argv) < 4:
            raise SystemExit("usage: msosctl2.py invoke <name> <method> [args_json] [kwargs_json]")
        name = argv[2]
        method = argv[3]
        args = _j(argv[4] if len(argv) > 4 else None, [])
        kwargs = _j(argv[5] if len(argv) > 5 else None, {})
        req = {"cmd": "invoke", "name": name, "method": method, "args": args, "kwargs": kwargs}
        print(json.dumps(call(req), indent=2))
        return 0

    # fallback
    req = {"cmd": cmd, "args": argv[2:]}
    print(json.dumps(call(req), indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv)) 
