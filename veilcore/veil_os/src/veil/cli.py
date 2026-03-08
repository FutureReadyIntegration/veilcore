#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from veil.compiler import compile_all, compile_p0


BANNER_PREVIEW = "🔱 Veil OS — PREVIEW (dry-run)"
BANNER_APPLY = "🔱 Veil OS — APPLY (real writes)"


def _banner(dry_run: bool) -> str:
    return BANNER_PREVIEW if dry_run else BANNER_APPLY


def _confirm_or_exit(action: str, yes: bool, no_input: bool, dry_run: bool) -> None:
    if dry_run:
        return
    if yes:
        return
    if no_input:
        raise SystemExit(f"❌ Refusing to run '{action}' without --yes in --no-input mode.")
    if input(f"\n⚠️  Run '{action}' with real writes?\nType 'YES' to proceed: ").strip() != "YES":
        raise SystemExit("✅ Cancelled.")


def _safe_print(line: str) -> None:
    # Avoid crashing when piping to head/grep
    try:
        print(line, flush=True)
    except BrokenPipeError:
        raise SystemExit(0)


# ----------------------------
# compile handlers
# ----------------------------
def handle_compile(args: argparse.Namespace) -> int:
    _confirm_or_exit("compile", args.yes, args.no_input, args.dry_run)
    _safe_print(_banner(args.dry_run))
    try:
        compile_all(dry_run=args.dry_run)
    except TypeError:
        if args.dry_run:
            raise SystemExit("❌ compile_all() does not support --dry-run in this version.")
        compile_all()
    return 0


def handle_compile_p0(args: argparse.Namespace) -> int:
    _confirm_or_exit("compile-p0", args.yes, args.no_input, args.dry_run)
    _safe_print(_banner(args.dry_run))
    try:
        compile_p0(dry_run=args.dry_run)
    except TypeError:
        if args.dry_run:
            raise SystemExit("❌ compile_p0() does not support --dry-run in this version.")
        compile_p0()
    return 0


# ----------------------------
# orchestrator handlers
# ----------------------------
def orch_list(args: argparse.Namespace) -> int:
    import veil.orchestrator as orch

    _safe_print(_banner(args.dry_run))
    for s in orch.list_services():
        _safe_print(f"{s.name} running={s.running} pid={s.pid} log={s.log}")
    return 0


def orch_status(args: argparse.Namespace) -> int:
    import veil.orchestrator as orch

    _safe_print(_banner(args.dry_run))
    s = orch.status(args.name)
    _safe_print(f"{s.name} running={s.running} pid={s.pid} log={s.log}")
    return 0


def orch_start(args: argparse.Namespace) -> int:
    import veil.orchestrator as orch

    _confirm_or_exit(f"orchestrator start {args.name}", args.yes, args.no_input, args.dry_run)
    _safe_print(_banner(args.dry_run))
    s = orch.start(args.name, dry_run=args.dry_run)
    _safe_print(f"OK start: {s.name} running={s.running} pid={s.pid} log={s.log}")
    return 0


def orch_stop(args: argparse.Namespace) -> int:
    import veil.orchestrator as orch

    _confirm_or_exit(f"orchestrator stop {args.name}", args.yes, args.no_input, args.dry_run)
    _safe_print(_banner(args.dry_run))
    s = orch.stop(args.name, dry_run=args.dry_run, force=bool(args.force))
    _safe_print(f"OK stop: {s.name} running={s.running} pid={s.pid} log={s.log}")
    return 0


# ----------------------------
# parser
# ----------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="veil", description="Veil OS CLI (safe)")
    p.add_argument("--dry-run", action="store_true", help="Preview only (no writes)")
    p.add_argument("--yes", action="store_true", help="Allow real writes (no confirmation)")
    p.add_argument("--no-input", action="store_true", help="Never prompt; fail without --yes on real writes")

    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("compile", help="Compile everything (default compile)")
    c.set_defaults(func=handle_compile)

    cp0 = sub.add_parser("compile-p0", help="Compile Phase 0 only")
    cp0.set_defaults(func=handle_compile_p0)

    o = sub.add_parser("orchestrator", help="Service control plane")
    osub = o.add_subparsers(dest="ocmd", required=True)

    ol = osub.add_parser("list", help="List services")
    ol.set_defaults(func=orch_list)

    ost = osub.add_parser("status", help="Show status of one service")
    ost.add_argument("name")
    ost.set_defaults(func=orch_status)

    osa = osub.add_parser("start", help="Start a service")
    osa.add_argument("name")
    osa.set_defaults(func=orch_start)

    oso = osub.add_parser("stop", help="Stop a service")
    oso.add_argument("name")
    oso.add_argument("--force", action="store_true", help="SIGKILL instead of SIGTERM")
    oso.set_defaults(func=orch_stop)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # Safety: --no-input must be paired with --dry-run or --yes
    if args.no_input and (not args.yes) and (not args.dry_run):
        raise SystemExit("❌ In --no-input mode, use --dry-run or add --yes.")

    try:
        return int(args.func(args))
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
