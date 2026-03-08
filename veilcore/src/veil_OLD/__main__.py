from __future__ import annotations

import argparse
import sys

from .compiler import compile_p0, compile_all, harden_service
from .ledger import append_event, verify_chain
from .override import build_override_payload, payload_to_event


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Veil OS Organ Engine"
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    # -------------------------
    # Compile / Harden
    # -------------------------
    sub.add_parser("compile", help="Run default compilation")

    sub.add_parser("compile-p0", help="Run phase-0 compilation")

    p_all = sub.add_parser("compile-all", help="Compile all with optional hardening")
    p_all.add_argument("--target")
    p_all.add_argument("--dry-run", action="store_true")

    p_harden = sub.add_parser("harden", help="Harden a target directory")
    p_harden.add_argument("--target", required=True)
    p_harden.add_argument("--dry-run", action="store_true")

    # -------------------------
    # Override (Phase 1)
    # -------------------------
    p_override = sub.add_parser("override", help="Create an override event")
    p_override.add_argument("--method", default="manual")
    p_override.add_argument("--lang", default="en")
    p_override.add_argument("--reason", required=True)

    # -------------------------
    # Ledger
    # -------------------------
    p_ledger = sub.add_parser("ledger", help="Ledger operations")
    ledger_sub = p_ledger.add_subparsers(dest="ledger_cmd", required=True)
    ledger_sub.add_parser("verify", help="Verify ledger integrity")

    args = parser.parse_args()

    # -------------------------
    # Dispatch
    # -------------------------
    if args.cmd == "compile":
        compile_all()
        return

    if args.cmd == "compile-p0":
        compile_p0()
        return

    if args.cmd == "compile-all":
        compile_all(
            target=args.target,
            harden=True,
            dry_run=args.dry_run,
        )
        return

    if args.cmd == "harden":
        harden_service(
            args.target,
            dry_run=args.dry_run,
        )
        return

    if args.cmd == "override":
        payload = build_override_payload(
            args.method,
            args.lang,
            args.reason,
        )
        event = payload_to_event(payload)
        res = append_event(event)

        print(payload.glyph, payload.affirmation)
        print(f"ledger={res.ledger_path}")
        print(f"index={res.index} hash={res.entry_hash}")
        return

    if args.cmd == "ledger":
        if args.ledger_cmd == "verify":
            ok, msg, _count = verify_chain()
            print(msg)
            sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
