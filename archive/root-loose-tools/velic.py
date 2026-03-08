#!/usr/bin/env python3

import sys
import os
import yaml
import json
from datetime import datetime

def load_yaml(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def write_chart(organ, data):
    chart_path = f"/opt/veil_os/organs/{organ}.chart"
    with open(chart_path, 'w') as f:
        yaml.dump(data, f)

def write_state(organ, status, error=None):
    state_path = f"/opt/veil_os/state/{organ}.state"
    state = {"status": status}
    if error:
        state["error"] = error
    with open(state_path, 'w') as f:
        json.dump(state, f)

def log_activation(organ):
    log_path = "/opt/veil_os/ledger/activation.log"
    with open(log_path, "a") as f:
        f.write(f"{datetime.now().isoformat()} - Activated {organ}\n")

def activate_organ(organ):
    chart_path = f"/opt/veil_os/organs/{organ}.chart"
    if not os.path.exists(chart_path):
        print(f"❌ Organ '{organ}' not found.")
        return False

    try:
        # Simulate activation
        write_state(organ, "active")
        log_activation(organ)
        print(f"⚡ Organ '{organ}' activated.")
        return True
    except Exception as e:
        write_state(organ, "failed", str(e))
        print(f"❌ Activation failed: {organ}")
        return False

def show_status():
    chart_dir = "/opt/veil_os/organs/"
    state_dir = "/opt/veil_os/state/"

    charts = [f for f in os.listdir(chart_dir) if f.endswith(".chart")]
    if not charts:
        print("⚠️  No compiled organs found.")
        return

    print("📊 Organ Status:")
    for chart in charts:
        name = chart.replace(".chart", "")
        state_file = os.path.join(state_dir, f"{name}.state")

        if not os.path.exists(state_file):
            status = "idle"
        else:
            with open(state_file) as f:
                state = json.load(f)
                status = state.get("status", "unknown")

        print(f" - {name}: {status}")

def diagnose():
    state_dir = "/opt/veil_os/state/"
    log_dir = "/opt/veil_os/logs/"

    print("🩺 Diagnosing failed organs...")

    for state_file in os.listdir(state_dir):
        if not state_file.endswith(".state"):
            continue

        with open(os.path.join(state_dir, state_file)) as f:
            state = json.load(f)
            if state.get("status") == "failed":
                name = state_file.replace(".state", "")
                print(f"\n❌ {name} failed.")
                reason = state.get("error", "Unknown error")
                print(f"   Reason: {reason}")

                log_path = os.path.join(log_dir, f"{name}.log")
                if os.path.exists(log_path):
                    print(f"   → Check logs: {log_path}")
                else:
                    print(f"   → No log file found.")

                print(f"   Suggestion: Try `veilc activate {name}` again.")

def help_menu():
    print("""
🧠 veilc — Veil OS Compiler

Usage:
  veilc create <spec.yaml>     Compile an organ spec into a chart
  veilc activate <organ>       Activate a compiled organ
  veilc status                 Show status of all compiled organs
  veilc diagnose               Diagnose failed organs
  veilc help                   Show this help menu
""")

# Entry point
if __name__ == "__main__":
    if len(sys.argv) < 2:
        help_menu()
        sys.exit(1)

    command = sys.argv[1]

    if command == "create":
        if len(sys.argv) != 3:
            print("Usage: veilc create <spec.yaml>")
            sys.exit(1)

        spec_path = sys.argv[2]
        try:
            spec = load_yaml(spec_path)
            organ = spec.get("organ")
            if not organ:
                raise ValueError("Missing 'organ' field in spec.")

            write_chart(organ, spec)
            print(f"✅ Organ '{organ}' created and recorded in ledger.")
        except Exception as e:
            print(f"❌ Failed to compile: {e}")
            sys.exit(1)

    elif command == "activate":
        if len(sys.argv) != 3:
            print("Usage: veilc activate <organ>")
            sys.exit(1)

        organ = sys.argv[2]
        if not activate_organ(organ):
            sys.exit(1)

    elif command == "status":
        show_status()

    elif command == "diagnose":
        diagnose()

    elif command == "help":
        help_menu()

    else:
        print(f"Unknown command: {command}")
        help_menu()
        sys.exit(1)
