from pathlib import Path
from .organ import Organ
from .ledger import append_ledger_entry, verify_ledger

SPECS = Path(__file__).parent / "specs"


def _load_organs():
    organs = []
    for spec in SPECS.glob("*.yaml"):
        organ = Organ.from_yaml(spec)
        organs.append(organ)
    return organs


def compile_p0():
    print("🚨 Compiling P0 Critical Organs...")

    organs = [o for o in _load_organs() if o.tier == "P0"]

    for organ in organs:
        print(f"→ {organ.name}")
        append_ledger_entry(organ.name, organ.tier)
        organ.activate()

    print("✅ P0 organs deployed.")
    verify_ledger()


def compile_p1():
    print("🚨 Compiling P1 Support Organs...")

    organs = [o for o in _load_organs() if o.tier == "P1"]

    for organ in organs:
        print(f"→ {organ.name}")
        append_ledger_entry(organ.name, organ.tier)
        organ.activate()

    print("✅ P1 organs deployed.")
    verify_ledger()


def compile_all():
    compile_p0()
    compile_p1()
