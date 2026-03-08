from __future__ import annotations
import importlib, inspect, sys

ORGANS = {
    "sentinel": "veil.organs.sentinel.runner",
    "insider_threat": "veil.organs.insider_threat.runner",
    "auto_lockdown": "veil.organs.auto_lockdown.runner",
    "zero_trust": "veil.organs.zero_trust.runner",
}

CANDIDATE_FUNCS = ["main","run","start","serve","entrypoint","run_service","run_server"]

def _call(fn):
    try:
        sig = inspect.signature(fn)
        if len(sig.parameters) == 0:
            return fn()
        if len(sig.parameters) == 1:
            return fn(sys.argv[2:])
    except Exception:
        pass
    return fn()
def run_module(modname: str) -> int:
    mod = importlib.import_module(modname)

    for name in CANDIDATE_FUNCS:
        fn = getattr(mod, name, None)
        if callable(fn):
            rv = _call(fn)

            # If the function returned immediately,
            # assume it is a setup function and keep process alive
            import time
            while True:
                time.sleep(60)

    raise SystemExit(f"{modname} has no callable entrypoint")

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m veil.organ_runner <sentinel|insider_threat|auto_lockdown|zero_trust|module.path>")
        return 2

    organ = sys.argv[1].strip()
    modname = ORGANS.get(organ, organ if organ.startswith("veil.") else None)
    if not modname:
        raise SystemExit(f"Unknown organ '{organ}'. Known: {', '.join(sorted(ORGANS.keys()))}")

    return run_module(modname)

if __name__ == "__main__":
    raise SystemExit(main())
