from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

from app.models.debt import DebtDirection, DebtStatus
from app.reports.report_generator import ReportGenerator
from app.services.debt_rules import calculate_debt_status, calculate_remaining


def test_debt_remaining_and_status_paid():
    assert calculate_remaining(Decimal("100.00"), Decimal("100.00")) == Decimal("0.00")
    assert calculate_debt_status(Decimal("100.00"), Decimal("100.00"), None) == DebtStatus.PAID


def test_debt_status_partial_and_overdue():
    assert calculate_debt_status(Decimal("100.00"), Decimal("40.00"), None) == DebtStatus.PARTIAL
    assert calculate_debt_status(Decimal("100.00"), Decimal("0.00"), date.today() - timedelta(days=1)) == DebtStatus.OVERDUE


def test_debt_report_summarizes_both_directions_by_person():
    debts = [
        SimpleNamespace(person=SimpleNamespace(name="Ali"), direction=DebtDirection.I_OWE_HIM, remaining_amount=Decimal("10.00"), currency="EUR"),
        SimpleNamespace(person=SimpleNamespace(name="Ali"), direction=DebtDirection.I_OWE_HIM, remaining_amount=Decimal("2.50"), currency="EUR"),
        SimpleNamespace(person=SimpleNamespace(name="Sara"), direction=DebtDirection.HE_OWES_ME, remaining_amount=Decimal("7.00"), currency="EUR"),
        SimpleNamespace(person=SimpleNamespace(name="Sara"), direction=DebtDirection.I_OWE_HIM, remaining_amount=Decimal("1.00"), currency="EUR"),
        SimpleNamespace(person=SimpleNamespace(name="Omar"), direction=DebtDirection.I_OWE_HIM, remaining_amount=Decimal("0.00"), currency="EUR"),
    ]

    rows = ReportGenerator()._debt_summary_by_person_rows(debts)

    assert rows == [
        ["Person", "I owe them", "They owe me", "Net"],
        ["Ali", "12.50 EUR", "0.00 EUR", "-12.50 EUR"],
        ["Sara", "1.00 EUR", "7.00 EUR", "6.00 EUR"],
    ]
