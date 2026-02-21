import json, os, socket, sys

HOST = os.environ.get("VEIL_MSOS_CONTROL_HOST", "127.0.0.1")
PORT = int(os.environ.get("VEIL_MSOS_CONTROL_PORT", "9089"))

def call(payload: dict) -> dict:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    s.sendall(json.dumps(payload).encode("utf-8"))
    resp = s.recv(65536)
    s.close()
    return json.loads(resp.decode("utf-8"))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: msosctl.py ping|list|status|start <name>|stop <name>|restart <name>")
        raise SystemExit(2)

    action = sys.argv[1]
    req = {"action": action}
    if action in ("start","stop","restart"):
        req["name"] = sys.argv[2]
    print(json.dumps(call(req), indent=2))
