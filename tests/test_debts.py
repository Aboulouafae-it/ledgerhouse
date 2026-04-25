from datetime import date, timedelta
from decimal import Decimal

from app.models.debt import DebtStatus
from app.services.debt_rules import calculate_debt_status, calculate_remaining


def test_debt_remaining_and_status_paid():
    assert calculate_remaining(Decimal("100.00"), Decimal("100.00")) == Decimal("0.00")
    assert calculate_debt_status(Decimal("100.00"), Decimal("100.00"), None) == DebtStatus.PAID


def test_debt_status_partial_and_overdue():
    assert calculate_debt_status(Decimal("100.00"), Decimal("40.00"), None) == DebtStatus.PARTIAL
    assert calculate_debt_status(Decimal("100.00"), Decimal("0.00"), date.today() - timedelta(days=1)) == DebtStatus.OVERDUE

