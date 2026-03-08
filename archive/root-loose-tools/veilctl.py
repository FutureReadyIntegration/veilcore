#!/usr/bin/env python3

import sys
import os
import json
from datetime import datetime

def load_state(organ):
    path = f"/opt/veil_os/state/{organ}.state"
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None

def list_active_organs():
    state_dir = "/opt/veil_os/state/"
    active = []
    for file in os.listdir(state_dir):
        if file.endswith(".state"):
            with open(os.path.join(state_dir, file)) as f:
                state = json.load(f)
                if state.get("status") == "active":
                    active.append(file.replace(".state", ""))
    return active

def broadcast(message):
    active_organs = list_active_organs()
    if not active_organs:
        print("⚠️  No active organs to broadcast to.")
        return

    print(f"📡 Broadcasting: '{message}'")
    for organ in active_organs:
        print(f" → Sent to {organ}")
        # Simulate delivery here

def ping():
    active_organs = list_active_organs()
    if not active_organs:
        print("⚠️  No active organs.")
        return

    print("📶 Ping Results:")
    for organ in active_organs:
        print(f" ✅ {organ} is responsive")

def help_menu():
    print("""
📡 veilctl — Veil OS Control Interface

Usage:
  veilctl broadcast <message>   → Send message to all active organs
  veilctl ping                  → Check which organs are responsive
  veilctl help                  → Show this help menu
""")

# Entry point
if __name__ == "__main__":
    if len(sys.argv) < 2:
        help_menu()
        sys.exit(1)

    command = sys.argv[1]

    if command == "broadcast":
        if len(sys.argv) < 3:
            print("Usage: veilctl broadcast <message>")
            sys.exit(1)
        message = " ".join(sys.argv[2:])
        broadcast(message)

    elif command == "ping":
        ping()

    elif command == "help":
        help_menu()

    else:
        print(f"Unknown command: {command}")
        help_menu()
        sys.exit(1)
