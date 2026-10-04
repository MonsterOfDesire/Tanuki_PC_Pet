from __future__ import annotations

from datetime import date, datetime


def normalize_local_date(value, *, fallback=None):
    """Return a valid local ISO date without allowing future start dates."""
    today = _coerce_date(fallback) or date.today()
    parsed = _coerce_date(value)
    if parsed is None or parsed > today:
        parsed = today
    return parsed.isoformat()


def play_day_number(started_on, *, today=None):
    """Count elapsed local calendar days, with the starting date as day one."""
    current = _coerce_date(today) or date.today()
    started = _coerce_date(started_on) or current
    if started > current:
        started = current
    return max(1, (current - started).days + 1)


def _coerce_date(value):
    if isinstance(value, datetime):
        return value.astimezone().date() if value.tzinfo else value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except (TypeError, ValueError):
        return None
