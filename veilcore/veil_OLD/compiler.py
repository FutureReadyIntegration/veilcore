from pathlib import Path
from .organ import Organ
from .ledger import append_ledger_entry

SPECS = Path(__file__).parent / "specs"

def compile_p0():
    print("🚨 Compiling P0 Critical Organs...")

    for spec in SPECS.glob("*.yaml"):
        organ = Organ.from_yaml(spec)
        print(f"→ {organ.name}")
        append_ledger_entry(organ.name)
        organ.activate()

    print("✅ P0 organs deployed.")

def compile_all():
    compile_p0()
