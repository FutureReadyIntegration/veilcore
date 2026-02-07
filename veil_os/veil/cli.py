import argparse
import os
import signal
import sys
from pathlib import Path

from .compiler import (
    compile_p0,
    compile_all,
    harden_service,
)

# Kill BrokenPipe spam when piping to head/grep
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

BANNER_PREVIEW = "🔱 Veil OS — PREVIEW (dry-run)"
BANNER_APPLY = "🔱 Veil OS — APPLY (real writes)"


# ----------------------------
# Guardrails for high-stakes ops
# ----------------------------

def _ensure_dir(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise argparse.ArgumentTypeError(f"Target does not exist: {path}")
    if not p.is_dir():
        raise argparse.ArgumentTypeError(f"Target is not a directory: {path}")
    return str(p)


def _confirm_or_exit(action: str, target: str | None, yes: bool, no_input: bool, dry_run: bool) -> None:
    if dry_run:
        return
    if yes:
        return
    if no_input:
        raise SystemExit(f"❌ Refusing to run '{action}' without --yes in --no-input mode.")

    msg = f"\n⚠️  You are about to run '{action}'"
    if target:
        msg += f" on target: {target}"
    msg += "\nThis may modify files.\nType 'YES' to proceed: "

    if input(msg).strip() != "YES":
        raise SystemExit("✅ Cancelled.")


def _banner(dry_run: bool) -> str:
    return BANNER_PREVIEW if dry_run else BANNER_APPLY


def _set_dry_run_env(dry_run: bool) -> None:
    os.environ["VEIL_DRY_RUN"] = "1" if dry_run else "0"


# ----------------------------
# Compile / Harden handlers
# ----------------------------

def handle_compile(args: argparse.Namespace) -> int:
    _confirm_or_exit("compile", None, args.yes, args.no_input, args.dry_run)
    print(_banner(args.dry_run))
    try:
        compile_all(dry_run=args.dry_run)
    except TypeError:
        if args.dry_run:
            raise SystemExit("❌ compile_all() does not support dry-run in this version.")
        compile_all()
    return 0


def handle_compile_p0(args: argparse.Namespace) -> int:
    _confirm_or_exit("compile-p0", None, args.yes, args.no_input, args.dry_run)
    print(_banner(args.dry_run))
    try:
        compile_p0(dry_run=args.dry_run)
    except TypeError:
        if args.dry_run:
            raise SystemExit("❌ compile_p0() does not support dry-run in this version.")
        compile_p0()
    return 0


def handle_compile_all(args: argparse.Namespace) -> int:
    _confirm_or_exit("compile-all", args.target, args.yes, args.no_input, args.dry_run)
    print(_banner(args.dry_run))
    compile_all(target=args.target, harden=args.harden, dry_run=args.dry_run)
    return 0


def handle_harden(args: argparse.Namespace) -> int:
    _confirm_or_exit("harden", args.target, args.yes, args.no_input, args.dry_run)
    print(_banner(args.dry_run))
    harden_service(args.target, dry_run=args.dry_run)
    return 0


# ----------------------------
# Orchestrator handlers
# ----------------------------

def orch_list(args: argparse.Namespace) -> int:
    _set_dry_run_env(args.dry_run)
    print(_banner(args.dry_run))

    from . import orchestrator as orch
    for s in orch.list_statuses():
        print(f"{s.name} running={s.running} pid={s.pid} log={s.log}", flush=True)
    return 0


def orch_status(args: argparse.Namespace) -> int:
    _set_dry_run_env(args.dry_run)
    print(_banner(args.dry_run))

    from . import orchestrator as orch
    s = orch.status(args.name)
    print(f"{s.name} running={s.running} pid={s.pid} log={s.log}", flush=True)
    return 0


def orch_start(args: argparse.Namespace) -> int:
    _confirm_or_exit("orchestrator start", None, args.yes, args.no_input, args.dry_run)
    _set_dry_run_env(args.dry_run)
    print(_banner(args.dry_run))

    from . import orchestrator as orch
    s = orch.start(args.name, dry_run=args.dry_run)
    print(f"OK start: {s.name} running={s.running} pid={s.pid} log={s.log}", flush=True)
    return 0


def orch_stop(args: argparse.Namespace) -> int:
    _confirm_or_exit("orchestrator stop", None, args.yes, args.no_input, args.dry_run)
    _set_dry_run_env(args.dry_run)
    print(_banner(args.dry_run))

    from . import orchestrator as orch
    s = orch.stop(args.name, force=bool(args.force), dry_run=args.dry_run)
    print(f"OK stop: {s.name} running={s.running} pid={s.pid} log={s.log}", flush=True)
    return 0


# ----------------------------
# Parser
# ----------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="veil",
        description="Veil OS Organ Engine (hospital-safe CLI)",
    )

    parser.add_argument("--dry-run", action="store_true", help="Show planned changes without writing files.")
    parser.add_argument("--yes", action="store_true", help="Skip interactive confirmation (use with care).")
    parser.add_argument("--no-input", action="store_true", help="Do not prompt. Fails unless --yes for non-dry-run.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # compile
    p_compile = subparsers.add_parser("compile", help="Compile (legacy default).")
    p_compile.set_defaults(func=handle_compile)

    # compile-p0
    p_p0 = subparsers.add_parser("compile-p0", help="Compile Phase 0 only.")
    p_p0.set_defaults(func=handle_compile_p0)

    # compile-all
    p_all = subparsers.add_parser("compile-all", help="Compile everything for a target directory.")
    p_all.add_argument("--target", required=True, type=_ensure_dir, help="Target service directory for compilation.")
    p_all.add_argument("--harden", action="store_true", help="Also run hardening as part of compile-all.")
    p_all.set_defaults(func=handle_compile_all)

    # harden
    p_harden = subparsers.add_parser("harden", help="Harden a specific target directory.")
    p_harden.add_argument("--target", required=True, type=_ensure_dir, help="Target service directory to harden.")
    p_harden.set_defaults(func=handle_harden)

    # orchestrator
    p_orch = subparsers.add_parser("orchestrator", help="Service orchestrator (list/start/stop/status).")
    orch_sub = p_orch.add_subparsers(dest="orch_cmd", required=True)

    p_ol = orch_sub.add_parser("list", help="List services")
    p_ol.set_defaults(func=orch_list)

    p_os = orch_sub.add_parser("status", help="Status for one service")
    p_os.add_argument("name")
    p_os.set_defaults(func=orch_status)

    p_ost = orch_sub.add_parser("start", help="Start a service")
    p_ost.add_argument("name")
    p_ost.set_defaults(func=orch_start)

    p_osp = orch_sub.add_parser("stop", help="Stop a service")
    p_osp.add_argument("name")
    p_osp.add_argument("--force", action="store_true")
    p_osp.set_defaults(func=orch_stop)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Safety: prevent accidental real ops in no-input mode
    if args.no_input and not args.yes and not args.dry_run:
        raise SystemExit("❌ In --no-input mode, use --dry-run or add --yes.")

    try:
        rc = args.func(args)
        raise SystemExit(0 if rc is None else int(rc))
    except BrokenPipeError:
        raise SystemExit(0)


if __name__ == "__main__":
    main()
