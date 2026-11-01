from datetime import date

from cloudshift.utils.dates import day_bounds, parse_date, parse_datetime, safe_pct, today_in_tz


def test_today_in_kolkata():
    d = today_in_tz("Asia/Kolkata")
    assert isinstance(d, date)


def test_parse_date_and_datetime():
    assert parse_date("2026-07-23") == date(2026, 7, 23)
    dt = parse_datetime("2026-07-23T08:00:00Z")
    assert dt is not None
    assert dt.tzinfo is not None


def test_safe_pct_divide_by_zero():
    assert safe_pct(5, 0) == 0.0
    assert safe_pct(1, 4) == 25.0


def test_day_bounds():
    start, end = day_bounds(date(2026, 7, 23), "Asia/Kolkata")
    assert start.tzinfo is not None
    assert (end - start).days == 1
