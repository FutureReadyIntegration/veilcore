#!/usr/bin/env python3
"""
veilc - Veil OS Organ Compiler
Creates and manages organs from YAML spec files.
"""

import sys
import yaml
import json
import os
from pathlib import Path
from datetime import datetime, UTC

VEIL_ROOT = Path("/opt/veil_os")
ORGANS_DIR = VEIL_ROOT / "organs"
LEDGER_FILE = VEIL_ROOT / "ledger.json"

def load_spec(spec_path: str) -> dict:
    """Load and validate a YAML spec file."""
    with open(spec_path, 'r') as f:
        spec = yaml.safe_load(f)

    if not spec:
        raise ValueError("Empty spec file")

    # Accept 'organ' or 'name' field
    if 'organ' not in spec:
        if 'name' in spec and spec['name']:
            spec['organ'] = spec['name']
        else:
            raise ValueError("Spec missing 'organ' or 'name' field")

    if not spec['organ']:
        raise ValueError("Organ name cannot be empty")

    return spec

def record_ledger(organ_name: str, spec: dict, action: str = "created"):
    """Record organ action in the ledger."""
    LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)

    ledger = []
    if LEDGER_FILE.exists():
        try:
            with open(LEDGER_FILE, 'r') as f:
                ledger = json.load(f)
        except json.JSONDecodeError:
            ledger = []

    entry = {
        "organ": organ_name,
        "action": action,
        "timestamp": datetime.now(UTC).isoformat(),
        "spec_hash": hash(json.dumps(spec, sort_keys=True)) & 0xFFFFFFFF,
    }

    ledger.append(entry)

    with open(LEDGER_FILE, 'w') as f:
        json.dump(ledger, f, indent=2)

def create_organ(spec_path: str):
    """Create an organ from a spec file."""
    try:
        spec = load_spec(spec_path)
    except Exception as e:
        print(f"❌ {e}")
        return False

    organ_name = spec['organ']
    organ_dir = ORGANS_DIR / organ_name

    # Create organ directory
    organ_dir.mkdir(parents=True, exist_ok=True)

    # Save processed spec
    spec_out = organ_dir / "spec.yaml"
    with open(spec_out, 'w') as f:
        yaml.dump(spec, f, default_flow_style=False)

    # Create config.json
    config = {
        "name": organ_name,
        "version": spec.get("version", "1.0"),
        "description": spec.get("description", ""),
        "tier": spec.get("tier", "support"),
        "glyph": spec.get("glyph", "⚙️"),
        "technical_role": spec.get("technical_role", "unknown"),
        "status": "inactive",
        "created_at": datetime.now(UTC).isoformat(),
    }

    config_out = organ_dir / "config.json"
    with open(config_out, 'w') as f:
        json.dump(config, f, indent=2)

    # Record in ledger
    record_ledger(organ_name, spec, "created")

    print(f"✅ Organ '{organ_name}' created and recorded in ledger.")
    return True

def activate_organ(organ_name: str):
    """Activate an organ."""
    organ_dir = ORGANS_DIR / organ_name
    config_file = organ_dir / "config.json"

    if not config_file.exists():
        print(f"❌ Organ '{organ_name}' not found. Run 'veilc create' first.")
        return False

    # Load config
    with open(config_file, 'r') as f:
        config = json.load(f)

    # Update status
    config['status'] = 'active'
    config['activated_at'] = datetime.now(UTC).isoformat()

    # Save config
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

    # Load spec for ledger
    spec_file = organ_dir / "spec.yaml"
    spec = {}
    if spec_file.exists():
        with open(spec_file, 'r') as f:
            spec = yaml.safe_load(f) or {}

    # Record in ledger
    record_ledger(organ_name, spec, "activated")

    print(f"⚡ Organ '{organ_name}' activated.")
    return True

def deactivate_organ(organ_name: str):
    """Deactivate an organ."""
    organ_dir = ORGANS_DIR / organ_name
    config_file = organ_dir / "config.json"

    if not config_file.exists():
        print(f"❌ Organ '{organ_name}' not found.")
        return False

    with open(config_file, 'r') as f:
        config = json.load(f)

    config['status'] = 'inactive'
    config['deactivated_at'] = datetime.now(UTC).isoformat()

    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

    spec_file = organ_dir / "spec.yaml"
    spec = {}
    if spec_file.exists():
        with open(spec_file, 'r') as f:
            spec = yaml.safe_load(f) or {}

    record_ledger(organ_name, spec, "deactivated")

    print(f"💤 Organ '{organ_name}' deactivated.")
    return True

def show_usage():
    print("""
veilc - Veil OS Organ Compiler

Usage:
  veilc create <spec.yaml>   Create organ from spec
  veilc activate <organ>     Activate an organ
  veilc deactivate <organ>   Deactivate an organ
  veilc list                 List all organs
  veilc info <organ>         Show organ info
  veilc help                 Show this help
""")

def list_organs():
    """List all created organs."""
    if not ORGANS_DIR.exists():
        print("No organs directory found.")
        return

    organs = [d.name for d in ORGANS_DIR.iterdir() if d.is_dir()]

    if not organs:
        print("No organs created yet.")
        return

    active = 0
    inactive = 0

    print(f"📦 {len(organs)} organs:\n")
    for organ in sorted(organs):
        config_file = ORGANS_DIR / organ / "config.json"
        glyph = "⚙️"
        status = "inactive"
        if config_file.exists():
            with open(config_file) as f:
                config = json.load(f)
                glyph = config.get("glyph", "⚙️")
                status = config.get("status", "inactive")
        
        if status == "active":
            active += 1
            status_icon = "🟢"
        else:
            inactive += 1
            status_icon = "⚫"
        
        print(f"  {status_icon} {glyph} {organ}")
    
    print(f"\n  Active: {active} | Inactive: {inactive}")

def organ_info(organ_name: str):
    """Show info about an organ."""
    organ_dir = ORGANS_DIR / organ_name
    config_file = organ_dir / "config.json"

    if not config_file.exists():
        print(f"❌ Organ '{organ_name}' not found.")
        return

    with open(config_file) as f:
        config = json.load(f)

    status = config.get('status', 'inactive')
    status_icon = "🟢" if status == "active" else "⚫"

    print(f"\n{config.get('glyph', '⚙️')} {organ_name} {status_icon}")
    print(f"  Status: {status}")
    print(f"  Version: {config.get('version', 'unknown')}")
    print(f"  Tier: {config.get('tier', 'unknown')}")
    print(f"  Role: {config.get('technical_role', 'unknown')}")
    print(f"  Created: {config.get('created_at', 'unknown')}")
    if config.get('activated_at'):
        print(f"  Activated: {config.get('activated_at')}")
    if config.get('description'):
        desc = config.get('description', '').strip()
        print(f"  Description: {desc[:80]}{'...' if len(desc) > 80 else ''}")

def main():
    if len(sys.argv) < 2:
        show_usage()
        sys.exit(1)

    command = sys.argv[1]

    if command == "create":
        if len(sys.argv) < 3:
            print("❌ Usage: veilc create <spec.yaml>")
            sys.exit(1)
        success = create_organ(sys.argv[2])
        sys.exit(0 if success else 1)

    elif command == "activate":
        if len(sys.argv) < 3:
            print("❌ Usage: veilc activate <organ_name>")
            sys.exit(1)
        success = activate_organ(sys.argv[2])
        sys.exit(0 if success else 1)

    elif command == "deactivate":
        if len(sys.argv) < 3:
            print("❌ Usage: veilc deactivate <organ_name>")
            sys.exit(1)
        success = deactivate_organ(sys.argv[2])
        sys.exit(0 if success else 1)

    elif command == "list":
        list_organs()

    elif command == "info":
        if len(sys.argv) < 3:
            print("❌ Usage: veilc info <organ_name>")
            sys.exit(1)
        organ_info(sys.argv[2])

    elif command in ("help", "-h", "--help"):
        show_usage()

    else:
        print(f"❌ Unknown command: {command}")
        show_usage()
        sys.exit(1)

if __name__ == "__main__":
    main()
