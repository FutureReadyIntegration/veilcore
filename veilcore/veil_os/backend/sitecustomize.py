# sitecustomize.py
# Auto-imported by Python on startup (if on sys.path).
# Goal: define `orch` inside veil.hospital_gui.main without editing main.py.

try:
    import veil.hospital_gui.main as m
    from veil.orchestrator import list_services, start, stop

    class OrchShim:
        def list(self):
            return list_services()

        def start(self, name):
            return start(name, dry_run=False)

        def stop(self, name):
            return stop(name, dry_run=False)

    # Force inject into module globals so `orch` exists for route handlers.
    m.__dict__["orch"] = OrchShim()

except Exception:
    # Never break interpreter startup
    pass
