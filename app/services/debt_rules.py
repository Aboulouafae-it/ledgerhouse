from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.models.debt import DebtStatus
from app.utils.money import to_decimal


def calculate_remaining(original_amount: Decimal, payments_total: Decimal) -> Decimal:
    return max(Decimal("0.00"), to_decimal(original_amount - payments_total))


def calculate_debt_status(original_amount: Decimal, payments_total: Decimal, due_date: date | None, today: date | None = None) -> DebtStatus:
    today = today or date.today()
    remaining = calculate_remaining(original_amount, payments_total)
    if remaining <= 0:
        return DebtStatus.PAID
    if due_date and due_date < today:
        return DebtStatus.OVERDUE
    if payments_total > 0:
        return DebtStatus.PARTIAL
    return DebtStatus.OPEN

