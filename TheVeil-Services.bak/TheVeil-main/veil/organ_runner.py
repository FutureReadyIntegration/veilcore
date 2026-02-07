#!/usr/bin/env python3
"""
Veil Organ Runner
=================
Universal runner for all Veil organs.

Usage:
    python -m veil.organ_runner <organ_name>
    python -m veil.organ_runner --list
    python -m veil.organ_runner --status
"""

import sys
import importlib
import json
from pathlib import Path
from datetime import datetime

ORGANS = {
    "sentinel": {
        "module": "veil.organs.sentinel.runner",
        "description": "Behavioral anomaly detection",
        "tier": "P1",
        "glyph": "👁️",
    },
    "insider_threat": {
        "module": "veil.organs.insider_threat.runner",
        "description": "Privilege abuse & exfiltration detection",
        "tier": "P1",
        "glyph": "🕵️",
    },
    "auto_lockdown": {
        "module": "veil.organs.auto_lockdown.runner",
        "description": "Automated threat response",
        "tier": "P0",
        "glyph": "🔒",
    },
    "zero_trust": {
        "module": "veil.organs.zero_trust.runner",
        "description": "Continuous verification engine",
        "tier": "P1",
        "glyph": "🔐",
    },
    "guardian": {
        "module": "veil.security.guardian",
        "description": "Authentication gateway",
        "tier": "P0",
        "glyph": "🛡️",
        "library": True,  # Not a standalone service
    },
    "audit": {
        "module": "veil.security.audit",
        "description": "Tamper-proof logging",
        "tier": "P1",
        "glyph": "📜",
        "library": True,
    },
}

STATUS_DIR = Path("/var/lib/veil")

def get_organ_status(organ_name: str) -> dict:
    """Get status from organ's status.json file."""
    status_paths = [
        STATUS_DIR / organ_name / "status.json",
        STATUS_DIR / "lockdown" / "status.json" if organ_name == "auto_lockdown" else None,
    ]
    
    for path in status_paths:
        if path and path.exists():
            try:
                data = json.loads(path.read_text())
                # Check if status is stale (>2 minutes old)
                if "updated_at" in data:
                    updated = datetime.fromisoformat(data["updated_at"])
                    age = (datetime.utcnow() - updated).total_seconds()
                    data["stale"] = age > 120
                return data
            except Exception:
                pass
    
    return {"running": False, "healthy": False, "message": "No status"}

def list_organs():
    """List all available organs."""
    print("\n" + "="*70)
    print("  THE VEIL - Available Organs")
    print("="*70 + "\n")
    
    for tier in ["P0", "P1", "P2"]:
        tier_organs = [(k, v) for k, v in ORGANS.items() if v.get("tier") == tier]
        if tier_organs:
            print(f"  {tier} ({'Critical' if tier == 'P0' else 'Essential' if tier == 'P1' else 'Supporting'}):")
            for name, info in tier_organs:
                lib = " (library)" if info.get("library") else ""
                print(f"    {info['glyph']} {name:20} - {info['description']}{lib}")
            print()
    
    print("  Run with: python -m veil.organ_runner <organ_name>")
    print("  Status:   python -m veil.organ_runner --status")
    print()

def show_status():
    """Show status of all organs."""
    print("\n" + "="*70)
    print("  THE VEIL - Organ Status")
    print("="*70 + "\n")
    
    running_count = 0
    total_count = 0
    
    for name, info in ORGANS.items():
        if info.get("library"):
            continue
        
        total_count += 1
        status = get_organ_status(name)
        
        if status.get("running"):
            running_count += 1
            health = "✅" if status.get("healthy") else "⚠️"
            stale = " (stale)" if status.get("stale") else ""
            msg = status.get("message", "")
            print(f"  {health} {info['glyph']} {name:20} RUNNING{stale} - {msg}")
        else:
            print(f"  ❌ {info['glyph']} {name:20} STOPPED - {status.get('message', 'Not running')}")
    
    print()
    print(f"  Summary: {running_count}/{total_count} organs running")
    print()

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m veil.organ_runner <organ_name>")
        print("       python -m veil.organ_runner --list")
        print("       python -m veil.organ_runner --status")
        return 1
    
    arg = sys.argv[1]
    
    if arg == "--list":
        list_organs()
        return 0
    
    if arg == "--status":
        show_status()
        return 0
    
    organ_name = arg
    
    if organ_name not in ORGANS:
        print(f"Unknown organ: {organ_name}")
        print(f"Available: {', '.join(ORGANS.keys())}")
        return 1
    
    info = ORGANS[organ_name]
    
    if info.get("library"):
        print(f"{organ_name} is a library module, not a standalone service.")
        print("It runs as part of the main Veil API.")
        return 1
    
    try:
        module = importlib.import_module(info["module"])
        return module.main()
    except ImportError as e:
        print(f"Failed to import {organ_name}: {e}")
        return 1
    except Exception as e:
        print(f"Error running {organ_name}: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
