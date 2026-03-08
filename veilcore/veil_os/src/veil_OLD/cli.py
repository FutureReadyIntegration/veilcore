#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys


BANNER_PREVIEW = "🔱 Veil OS — PREVIEW (dry-run)"
BANNER_APPLY = "🔱 Veil OS — APPLY (real writes)"


# ---------- helpers ----------

def _banner(dry_run: bool) -> str:
    return BANNER_PREVIEW if dry_run else BANNER_APPLY


def _as_field(obj, name: str, default=None):
    """
    Support ServiceStatus objects *or* dicts.
    """
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _print_service_line(s) -> None:
    name = _as_field(s, "name", "unknown")
    running = _as_field(s, "running", False)
    pid = _as_field(s, "pid", None)
    log = _as_field(s, "log", None)
    print(f"{name} running={running} pid={pid} log={log}")


def _require_yes_for_real_writes(args) -> None:
    # Dry-run always allowed
    if args.dry_run:
        return
    # Real writes require explicit --yes, and if --no-input is set, we must not prompt
    if not args.yes:
        if args.no_input:
            raise SystemExit("❌ Refusing real writes without --yes (and --no-input set).")
        raise SystemExit("❌ Refusing real writes without --yes.")


# ---------- orchestrator commands ----------

def orch_list(args) -> int:
    from veil.orchestrator import list_services  # safe lazy import
    print(_banner(args.dry_run))
    services = list_services()
    for s in services:
        _print_service_line(s)
    return 0


def orch_status(args) -> int:
    # orchestrator.py may expose status() not service_status()
    import veil.orchestrator as orch
    fn = getattr(orch, "service_status", None) or getattr(orch, "status", None)
    if fn is None:
        raise SystemExit("❌ Orchestrator has no service_status() or status()")

    print(_banner(args.dry_run))
    s = fn(args.name)
    _print_service_line(s)
    return 0


def orch_start(args) -> int:
    _require_yes_for_real_writes(args)

    import veil.orchestrator as orch
    fn = getattr(orch, "start_service", None) or getattr(orch, "start", None)
    if fn is None:
        raise SystemExit("❌ Orchestrator has no start_service() or start()")

    print(_banner(args.dry_run))
    # Support both signatures: start(name, dry_run=bool) OR start(name)
    try:
        s = fn(args.name, dry_run=bool(args.dry_run))
    except TypeError:
        s = fn(args.name)
    _print_service_line(s)
    return 0


def orch_stop(args) -> int:
    _require_yes_for_real_writes(args)

    import veil.orchestrator as orch
    fn = getattr(orch, "stop_service", None) or getattr(orch, "stop", None)
    if fn is None:
        raise SystemExit("❌ Orchestrator has no stop_service() or stop()")

    print(_banner(args.dry_run))
    # Support both signatures: stop(name, dry_run=bool, force=bool) OR stop(name)
    try:
        s = fn(args.name, dry_run=bool(args.dry_run), force=bool(getattr(args, "force", False)))
    except TypeError:
        try:
            s = fn(args.name, dry_run=bool(args.dry_run))
        except TypeError:
            s = fn(args.name)
    _print_service_line(s)
    return 0


# ---------- compile/harden/override/ledger placeholders ----------
# (Leave your existing implementations if you already have them elsewhere.)
# If you already had these wired, keep them. This file focuses on fixing orchestrator.


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    p = argparse.ArgumentParser(prog="veil")
    p.add_argument("--dry-run", action="store_true", help="Preview only (no writes)")
    p.add_argument("--yes", action="store_true", help="Allow real writes (no confirmation)")
    p.add_argument("--no-input", action="store_true", help="Never prompt; fail without --yes on real writes")
    p.add_argument("--target", default=None, help="Target service directory (where applicable)")

    sub = p.add_subparsers(dest="cmd", required=True)

    # orchestrator
    po = sub.add_parser("orchestrator", help="Manage Veil services")
    so = po.add_subparsers(dest="orch_cmd", required=True)

    pol = so.add_parser("list", help="List services")
    pol.set_defaults(func=orch_list)

    pos = so.add_parser("status", help="Show one service")
    pos.add_argument("name")
    pos.set_defaults(func=orch_status)

    pst = so.add_parser("start", help="Start a service")
    pst.add_argument("name")
    pst.set_defaults(func=orch_start)

    psp = so.add_parser("stop", help="Stop a service")
    psp.add_argument("name")
    psp.add_argument("--force", action="store_true", help="Force stop (if supported)")
    psp.set_defaults(func=orch_stop)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
