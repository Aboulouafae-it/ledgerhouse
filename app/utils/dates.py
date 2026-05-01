from __future__ import annotations

from datetime import date, datetime


def coerce_date(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = value.strip()
    if not text:
        raise ValueError("Date is required.")
    return datetime.strptime(text, "%Y-%m-%d").date()


def parse_date(value: str) -> date:
    return coerce_date(value)


def today_range() -> tuple[date, date]:
    today = date.today()
    return today.replace(day=1), today
