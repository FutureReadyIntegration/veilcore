import hashlib
import json
import time
from pathlib import Path

# Anchor ledger to the installed package directory
PACKAGE_ROOT = Path(__file__).resolve().parent
LEDGER_PATH = Path("/opt/veil_os/ledger.json")

def hash_block(block):
    return hashlib.sha256(json.dumps(block, sort_keys=True).encode()).hexdigest()


def load_ledger():
    if LEDGER_PATH.exists():
        return json.loads(LEDGER_PATH.read_text())
    return []


def save_ledger(ledger):
    LEDGER_PATH.write_text(json.dumps(ledger, indent=2))


def append_ledger_entry(organ_name, tier):
    ledger = load_ledger()

    prev_hash = ledger[-1]["hash"] if ledger else "GENESIS"
    index = len(ledger)
    timestamp = time.time()

    block = {
        "index": index,
        "organ": organ_name,
        "tier": tier,
        "timestamp": timestamp,
        "prev_hash": prev_hash,
    }
    block["hash"] = hash_block(block)

    ledger.append(block)
    save_ledger(ledger)

    print(f"✅ Organ '{organ_name}' recorded in ledger (index={index}).")


def verify_ledger():
    ledger = load_ledger()
    if not ledger:
        print("ℹ️ Ledger is empty.")
        return True

    for i, block in enumerate(ledger):
        expected_hash = hash_block(
            {
                "index": block["index"],
                "organ": block["organ"],
                "tier": block["tier"],
                "timestamp": block["timestamp"],
                "prev_hash": block["prev_hash"],
            }
        )
        if block["hash"] != expected_hash:
            print(f"❌ Ledger tampering detected at index {i}.")
            return False

        if i == 0:
            if block["prev_hash"] != "GENESIS":
                print("❌ Invalid genesis block.")
                return False
        else:
            if block["prev_hash"] != ledger[i - 1]["hash"]:
                print(f"❌ Broken chain at index {i}.")
                return False

    print("🟢 Ledger integrity verified.")
    return True
