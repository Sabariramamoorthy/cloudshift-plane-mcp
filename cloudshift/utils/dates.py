"""Timezone-aware date helpers for CloudShift reports."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def get_tz(name: str) -> ZoneInfo | timezone:
    try:
        return ZoneInfo(name)
    except Exception:
        return timezone.utc


def now_tz(tz_name: str) -> datetime:
    return datetime.now(tz=get_tz(tz_name))


def today_in_tz(tz_name: str) -> date:
    return now_tz(tz_name).date()


def parse_date(value: str | date | datetime | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    # date-only
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            pass
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt.date()
    except ValueError:
        return None


def parse_datetime(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def day_bounds(day: date, tz_name: str) -> tuple[datetime, datetime]:
    tz = get_tz(tz_name)
    start = datetime(day.year, day.month, day.day, 0, 0, 0, tzinfo=tz)
    end = start + timedelta(days=1)
    return start, end


def safe_pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100.0, 2)
