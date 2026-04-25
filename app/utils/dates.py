from __future__ import annotations

from datetime import date, datetime


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def today_range() -> tuple[date, date]:
    today = date.today()
    return today.replace(day=1), today

