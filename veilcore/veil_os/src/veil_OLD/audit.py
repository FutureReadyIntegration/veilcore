from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .ledger import iter_entries, default_ledger_path


def _parse_day(s: str) -> datetime:
    # YYYY-MM-DD (UTC)
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def _safe_event(obj: Dict[str, Any]) -> Dict[str, Any]:
    ev = obj.get("event")
    return ev if isinstance(ev, dict) else {}


def _parse_ts_utc(obj: Dict[str, Any]) -> Optional[datetime]:
    ts = obj.get("ts_utc")
    if not isinstance(ts, str):
        return None
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _match(
    obj: Dict[str, Any],
    *,
    user: Optional[str],
    method: Optional[str],
    day_from: Optional[datetime],
    day_to: Optional[datetime],
) -> bool:
    if user and str(obj.get("user", "")).lower() != user.lower():
        return False

    ev = _safe_event(obj)
    if method and str(ev.get("method", "")).lower() != method.lower():
        return False

    dt = _parse_ts_utc(obj)
    if dt is not None:
        if day_from and dt < day_from:
            return False
        if day_to:
            end = day_to.replace(hour=23, minute=59, second=59)
            if dt > end:
                return False

    return True


def list_events(
    *,
    ledger_path: Optional[Path] = None,
    user: Optional[str] = None,
    method: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Read-only listing of ledger events (most recent first).

    Filters:
      - user: OS username that executed the event
      - method: override method (manual, qr, biometric...) (Phase 1 is manual)
      - date_from/date_to: YYYY-MM-DD (UTC), inclusive
      - limit: max results
    """
    lp = ledger_path or default_ledger_path()

    day_from = _parse_day(date_from) if date_from else None
    day_to = _parse_day(date_to) if date_to else None

    matches: List[Dict[str, Any]] = []
    for obj in iter_entries(lp):
        if _match(obj, user=user, method=method, day_from=day_from, day_to=day_to):
            matches.append(obj)

    # most recent first
    matches = matches[-max(0, int(limit)) :]
    matches.reverse()
    return matches


def format_event_line(obj: Dict[str, Any]) -> str:
    """
    Human-readable one-line output for operators.
    """
    ev = _safe_event(obj)
    return (
        f'{obj.get("ts_utc","")} '
        f'user={obj.get("user","")} '
        f'method={ev.get("method","")} '
        f'event_id={obj.get("event_id","")} '
        f'reason="{ev.get("reason","")}"'
    )


def format_event_json(obj: Dict[str, Any]) -> str:
    """
    Machine-readable JSON output (one JSON per line).
    """
    return json.dumps(obj, ensure_ascii=False)
