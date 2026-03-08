import os
import socket
import threading
import time

LISTEN_HOST = os.environ.get("VEIL_RESOLVER_LISTEN_HOST", "127.0.0.1")
LISTEN_PORT = int(os.environ.get("VEIL_RESOLVER_LISTEN_PORT", "5354"))

UPSTREAM_HOST = os.environ.get("VEIL_RESOLVER_UPSTREAM_HOST", "127.0.0.1")
UPSTREAM_PORT = int(os.environ.get("VEIL_RESOLVER_UPSTREAM_PORT", "5353"))

SOCKET_TIMEOUT = float(os.environ.get("VEIL_RESOLVER_TIMEOUT_SEC", "2.0"))

def _udp_worker(sock: socket.socket):
    # Forward raw UDP DNS packets (works for standard UDP DNS queries)
    while True:
        data, client_addr = sock.recvfrom(4096)
        try:
            upstream = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            upstream.settimeout(SOCKET_TIMEOUT)
            upstream.sendto(data, (UPSTREAM_HOST, UPSTREAM_PORT))
            resp, _ = upstream.recvfrom(4096)
            sock.sendto(resp, client_addr)
        except Exception:
            # Best-effort: drop on errors (upstream down, timeout, etc.)
            pass
        finally:
            try:
                upstream.close()
            except Exception:
                pass

def main():
    print(f"[resolver] starting udp forwarder {LISTEN_HOST}:{LISTEN_PORT} -> {UPSTREAM_HOST}:{UPSTREAM_PORT}", flush=True)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((LISTEN_HOST, LISTEN_PORT))

    t = threading.Thread(target=_udp_worker, args=(sock,), daemon=True)
    t.start()

    # keep alive
    while True:
        time.sleep(60)

if __name__ == "__main__":
    main()
