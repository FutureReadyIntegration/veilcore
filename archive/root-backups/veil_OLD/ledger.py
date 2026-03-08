import hashlib
import json
import time
from pathlib import Path

LEDGER_PATH = Path("/opt/veil_os/ledger.json")

def hash_block(block):
    return hashlib.sha256(json.dumps(block, sort_keys=True).encode()).hexdigest()

def load_ledger():
    if LEDGER_PATH.exists():
        return json.loads(LEDGER_PATH.read_text())
    return []

def save_ledger(ledger):
    LEDGER_PATH.write_text(json.dumps(ledger, indent=2))

def append_ledger_entry(organ_name, tier="support"):
    ledger = load_ledger()
    prev_hash = ledger[-1].get("hash", "GENESIS") if ledger else "GENESIS"
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
        # Skip blocks without proper chain structure (legacy entries)
        if "index" not in block:
            continue
        expected_hash = hash_block({
            "index": block["index"],
            "organ": block["organ"],
            "tier": block.get("tier", "support"),
            "timestamp": block["timestamp"],
            "prev_hash": block["prev_hash"],
        })
        if block["hash"] != expected_hash:
            print(f"❌ Ledger tampering detected at index {i}.")
            return False
        if i > 0 and "prev_hash" in ledger[i-1]:
            if block["prev_hash"] != ledger[i-1]["hash"]:
                print(f"❌ Broken chain at index {i}.")
                return False
    print(f"🟢 Ledger integrity verified. {len(ledger)} entries.")
    return True

def ledger_stats():
    ledger = load_ledger()
    organs = set(b.get("organ") for b in ledger)
    print(f"📊 Ledger: {len(ledger)} entries, {len(organs)} unique organs")
    return {"entries": len(ledger), "organs": len(organs)}
