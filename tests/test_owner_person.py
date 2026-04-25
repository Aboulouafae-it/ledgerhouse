from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models import account, app_setting, app_user, audit_log, category, debt, debt_payment, payment_method, person, report_export, settlement, shared_expense, shared_expense_participant, transaction  # noqa: F401
from app.models.person import Person
from app.services.dashboard_service import DashboardService
from app.services.person_service import PersonService
from app.services.settings_service import SettingsService
from app.services.shared_living_service import SharedLivingService


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


def test_owner_creation_from_settings(session):
    owner = SettingsService(session).set_owner_name("Maya Owner")

    assert owner is not None
    assert owner.id is not None
    assert owner.normalized_name == "maya owner"
    assert owner.is_house_member is True
    assert owner.is_active is True
    assert SettingsService(session).get("owner_person_id") == str(owner.id)


def test_owner_appears_in_shared_living_members(session):
    owner = SettingsService(session).set_owner_name("Maya Owner")

    members = SharedLivingService(session).house_members()

    assert [member.id for member in members] == [owner.id]


def test_owner_participates_in_equal_split(session):
    owner = SettingsService(session).set_owner_name("Maya Owner")
    roommate = PersonService(session).add_person(name="Roommate", is_house_member=True)

    expense = SharedLivingService(session).add_equal_expense(
        title="Internet",
        amount=Decimal("90.00"),
        paid_by_person_id=roommate.id,
        participant_ids=[owner.id, roommate.id],
        date_=date(2026, 4, 25),
    )

    shares = {participant.person_id: participant.share_amount for participant in expense.participants}
    assert shares == {owner.id: Decimal("45.00"), roommate.id: Decimal("45.00")}


def test_owner_paid_amount_is_counted_in_balances_and_dashboard(session):
    owner = SettingsService(session).set_owner_name("Maya Owner")
    roommate = PersonService(session).add_person(name="Roommate", is_house_member=True)

    SharedLivingService(session).add_equal_expense(
        title="Groceries",
        amount=Decimal("90.00"),
        paid_by_person_id=owner.id,
        participant_ids=[owner.id, roommate.id],
        date_=date(2026, 4, 25),
    )

    balances = SharedLivingService(session).balance_by_person_id()
    dashboard = DashboardService(session).summary(date(2026, 4, 1), date(2026, 4, 30))

    assert balances[owner.id] == Decimal("45.00")
    assert balances[roommate.id] == Decimal("-45.00")
    assert dashboard["shared_receivable"] == Decimal("45.00")
    assert dashboard["shared_payable"] == Decimal("0.00")


def test_no_duplicate_owner_is_created_for_existing_normalized_name(session):
    existing = PersonService(session).add_person(name="Maya Owner")

    owner = SettingsService(session).set_owner_name(" maya owner ")

    people = list(session.scalars(select(Person)).all())
    assert owner.id == existing.id
    assert len(people) == 1
    assert people[0].is_house_member is True
    assert SettingsService(session).get("owner_person_id") == str(existing.id)


def test_owner_name_change_updates_same_person_when_possible(session):
    owner = SettingsService(session).set_owner_name("Maya Owner")

    updated = SettingsService(session).set_owner_name("Maya Ledger")

    people = list(session.scalars(select(Person)).all())
    assert updated.id == owner.id
    assert len(people) == 1
    assert people[0].name == "Maya Ledger"
    assert people[0].normalized_name == "maya ledger"
