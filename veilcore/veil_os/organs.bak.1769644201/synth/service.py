#!/usr/bin/env python3
"""
Veil OS - Synth Organ Service
Auto-generated service module
"""

import os
import sys
import json
import time
import signal
import socket
import logging
from datetime import datetime

# Configuration
ORGAN_NAME = "synth"
SOCKETS_DIR = os.environ.get("VEIL_SOCKETS_DIR", "/opt/veil_os/sockets")
LEDGER_DIR = os.environ.get("VEIL_LEDGER_DIR", "/opt/veil_os/ledger")
LOG_DIR = os.environ.get("VEIL_LOG_DIR", "/opt/veil_os/var/log")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format=f'%(asctime)s [{ORGAN_NAME}] %(levelname)s: %(message)s'
)
log = logging.getLogger(ORGAN_NAME)

# Graceful shutdown
running = True

def signal_handler(signum, frame):
    global running
    log.info(f"Received signal {signum}, shutting down...")
    running = False

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


class OrganService:
    """Base organ service"""
    
    def __init__(self):
        self.name = ORGAN_NAME
        self.socket_path = os.path.join(SOCKETS_DIR, f"{self.name}.sock")
        self.log_path = os.path.join(LEDGER_DIR, f"{self.name}.log")
        self.sock = None
        self.stats = {
            "started_at": datetime.now().isoformat(),
            "events_processed": 0,
            "errors": 0
        }
    
    def setup_socket(self):
        """Create Unix socket for IPC"""
        try:
            if os.path.exists(self.socket_path):
                os.unlink(self.socket_path)
            
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.bind(self.socket_path)
            self.sock.listen(5)
            self.sock.setblocking(False)
            os.chmod(self.socket_path, 0o666)
            log.info(f"Socket: {self.socket_path}")
            return True
        except Exception as e:
            log.warning(f"Could not create socket: {e}")
            return False
    
    def handle_connection(self, conn):
        """Handle incoming connection"""
        try:
            data = conn.recv(4096)
            if data:
                request = json.loads(data.decode())
                response = self.process_request(request)
                conn.send(json.dumps(response).encode())
                self.stats["events_processed"] += 1
        except Exception as e:
            log.error(f"Connection error: {e}")
            self.stats["errors"] += 1
        finally:
            conn.close()
    
    def process_request(self, request):
        """Process incoming request - override in subclass"""
        action = request.get("action", "status")
        
        if action == "status":
            return {
                "organ": self.name,
                "status": "active",
                "stats": self.stats
            }
        elif action == "ping":
            return {"pong": True, "organ": self.name}
        else:
            return {"error": f"Unknown action: {action}"}
    
    def log_event(self, event_type, data):
        """Log event to ledger"""
        try:
            os.makedirs(LEDGER_DIR, exist_ok=True)
            entry = {
                "timestamp": datetime.now().isoformat(),
                "organ": self.name,
                "type": event_type,
                "data": data
            }
            with open(self.log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            log.error(f"Could not log event: {e}")
    
    def tick(self):
        """Called each loop iteration - override for custom logic"""
        pass
    
    def run(self):
        """Main run loop"""
        global running
        
        log.info(f"═══════════════════════════════════════")
        log.info(f"  {self.name.upper()} organ starting")
        log.info(f"═══════════════════════════════════════")
        
        self.setup_socket()
        self.log_event("startup", {"status": "started"})
        
        while running:
            try:
                # Check for socket connections
                if self.sock:
                    try:
                        conn, _ = self.sock.accept()
                        self.handle_connection(conn)
                    except BlockingIOError:
                        pass
                
                # Run organ-specific logic
                self.tick()
                
                time.sleep(1)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                log.error(f"Error in main loop: {e}")
                self.stats["errors"] += 1
                time.sleep(1)
        
        # Cleanup
        log.info(f"{self.name} shutting down")
        self.log_event("shutdown", {"status": "stopped", "stats": self.stats})
        
        if self.sock:
            self.sock.close()
        if os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except:
                pass


def main():
    service = OrganService()
    service.run()


if __name__ == "__main__":
    main()
