from __future__ import annotations

from veil.core.panic import PanicCode
from .panic_codes import lookup, list_codes
from .repairs import list_repairs, run as run_repair


def cmd_list_codes() -> int:
    for c in list_codes():
        print(c.value)
    return 0


def cmd_lookup(code_str: str) -> int:
    try:
        code = PanicCode(code_str)
    except Exception:
        print("Unknown code")
        return 2

    g = lookup(code)
    if not g:
        print("No guide available")
        return 1

    print(g.title)
    for i, step in enumerate(g.operator_steps, 1):
        print(f"{i}. {step}")
    if g.notes:
        print("Notes:")
        for n in g.notes:
            print(f"- {n}")
    return 0


def cmd_repairs() -> int:
    for r in list_repairs():
        print(r)
    return 0


def cmd_repair_run(name: str) -> int:
    res = run_repair(name)
    print(f"ok={res.ok} msg={res.message}")
    return 0 if res.ok else 1
