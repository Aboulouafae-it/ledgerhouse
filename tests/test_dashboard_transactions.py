from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models import account, app_setting, app_user, audit_log, category, debt, debt_payment, payment_method, person, report_export, settlement, shared_expense, shared_expense_participant, transaction  # noqa: F401
from app.models.debt import DebtDirection
from app.models.category import CategoryType
from app.models.payment_method import PaymentMethodType
from app.models.transaction import TransactionType
from app.services.category_service import CategoryService
from app.services.dashboard_service import DashboardService
from app.services.debt_service import DebtService
from app.services.payment_method_service import PaymentMethodService
from app.services.person_service import PersonService
from app.services.report_service import ReportService
from app.services.settings_service import SettingsService
from app.services.shared_living_service import SharedLivingService
from app.services.transaction_service import TransactionService


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def _this_month_day(day: int = 1) -> date:
    today = date.today()
    return date(today.year, today.month, min(day, today.day))


def test_income_counted_in_current_period(session):
    TransactionService(session).add_transaction(type_=TransactionType.INCOME, amount=Decimal("100.00"), date_=_this_month_day())

    summary = DashboardService(session).summary(period="this month")

    assert summary["income"] == Decimal("100.00")


def test_income_counted_with_person(session):
    person = PersonService(session).add_person(name="Client")
    TransactionService(session).add_transaction(type_=TransactionType.INCOME, amount=Decimal("125.00"), date_=_this_month_day(), person_id=person.id)

    summary = DashboardService(session).summary(period="this month")

    assert summary["income"] == Decimal("125.00")


def test_income_counted_without_person(session):
    TransactionService(session).add_transaction(type_=TransactionType.INCOME, amount=Decimal("75.00"), date_=_this_month_day(), person_id=None)

    summary = DashboardService(session).summary(period="this month")

    assert summary["income"] == Decimal("75.00")


def test_income_outside_period_is_excluded(session):
    old_date = date.today().replace(day=1) - timedelta(days=1)
    TransactionService(session).add_transaction(type_=TransactionType.INCOME, amount=Decimal("250.00"), date_=old_date)

    summary = DashboardService(session).summary(period="this month")

    assert summary["income"] == Decimal("0.00")


def test_all_time_includes_old_income(session):
    old_date = date(date.today().year - 1, 1, 15)
    TransactionService(session).add_transaction(type_=TransactionType.INCOME, amount=Decimal("300.00"), date_=old_date)

    summary = DashboardService(session).summary(period="all time")

    assert summary["income"] == Decimal("300.00")


def test_dashboard_refresh_reflects_updated_transaction(session):
    tx = TransactionService(session).add_transaction(type_=TransactionType.INCOME, amount=Decimal("100.00"), date_=_this_month_day())

    TransactionService(session).update_transaction(tx.id, type_=TransactionType.INCOME, amount=Decimal("225.00"), date_=_this_month_day())
    summary = DashboardService(session).summary(period="this month")

    assert summary["income"] == Decimal("225.00")


def test_dashboard_excludes_deactivated_transaction(session):
    tx = TransactionService(session).add_transaction(type_=TransactionType.INCOME, amount=Decimal("100.00"), date_=_this_month_day())

    TransactionService(session).deactivate_transaction(tx.id)
    summary = DashboardService(session).summary(period="this month")

    assert summary["income"] == Decimal("0.00")


def test_report_transaction_source_excludes_deactivated_transaction(tmp_path, session):
    tx = TransactionService(session).add_transaction(type_=TransactionType.INCOME, amount=Decimal("100.00"), date_=_this_month_day())
    TransactionService(session).deactivate_transaction(tx.id)

    output = ReportService(session).export_transactions_csv(tmp_path / "transactions.csv")

    assert "100.00" not in output.read_text(encoding="utf-8")


def test_default_currency_applies_to_new_financial_records(session):
    SettingsService(session).set("default_currency", "USD", "str")
    person = PersonService(session).add_person(name="Roommate", is_house_member=True, is_creditor=True)

    tx = TransactionService(session).add_transaction(type_=TransactionType.INCOME, amount=Decimal("100.00"), date_=_this_month_day())
    debt = DebtService(session).add_debt(person_id=person.id, direction=DebtDirection.I_OWE_HIM, amount=Decimal("20.00"))
    shared = SharedLivingService(session).add_equal_expense(title="Groceries", amount=Decimal("40.00"), paid_by_person_id=person.id, participant_ids=[person.id], date_=_this_month_day())

    assert tx.currency == "USD"
    assert debt.currency == "USD"
    assert shared.currency == "USD"


def test_settings_categories_and_payment_methods_are_available_to_shared_living(session):
    category = CategoryService(session).add_category("Household", CategoryType.SHARED)
    method = PaymentMethodService(session).add_method("Joint Card", PaymentMethodType.CARD)
    person = PersonService(session).add_person(name="Roommate", is_house_member=True)

    service = SharedLivingService(session)
    expense = service.add_equal_expense(
        title="Internet",
        amount=Decimal("40.00"),
        paid_by_person_id=person.id,
        participant_ids=[person.id],
        date_=_this_month_day(),
        category_id=category.id,
        payment_method_id=method.id,
    )

    assert category.id in [item.id for item in service.shared_categories()]
    assert method.id in [item.id for item in service.payment_methods()]
    assert expense.category_id == category.id
    assert expense.payment_method_id == method.id


def test_settings_payment_methods_are_available_to_debt_payments(session):
    method = PaymentMethodService(session).add_method("Debt Transfer", PaymentMethodType.TRANSFER)
    person = PersonService(session).add_person(name="Creditor", is_creditor=True)
    debt = DebtService(session).add_debt(person_id=person.id, direction=DebtDirection.I_OWE_HIM, amount=Decimal("50.00"))

    DebtService(session).register_payment(debt.id, Decimal("10.00"), _this_month_day(), payment_method_id=method.id)

    payment = DebtService(session).payment_history(debt.id)[0]
    assert method.id in [item.id for item in DebtService(session).payment_methods()]
    assert payment.payment_method_id == method.id
