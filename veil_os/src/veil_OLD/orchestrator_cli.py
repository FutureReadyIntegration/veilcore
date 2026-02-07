from __future__ import annotations

from .orchestrator import list_services, start_service, stop_service, status


def _print_status(s) -> None:
    print(f"{s.name} running={s.running} pid={s.pid} log={s.log_path}")


def cmd_list(args) -> int:
    services = list_services()
    for s in services:
        _print_status(s)
    return 0


def cmd_status(args) -> int:
    s = status(args.name)
    _print_status(s)
    return 0


def cmd_start(args) -> int:
    s = start_service(args.name, dry_run=args.dry_run)
    # start_service(dry_run=True) intentionally does not mutate; status may remain False
    _print_status(s)
    return 0


def cmd_stop(args) -> int:
    s = stop_service(args.name, dry_run=args.dry_run)
    _print_status(s)
    return 0
