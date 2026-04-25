from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.person import Person
from app.models.shared_expense import SharedExpense, SplitType
from app.models.shared_expense_participant import SharedExpenseParticipant
from app.repositories.person_repository import PersonRepository
from app.repositories.shared_expense_repository import SharedExpenseRepository
from app.services.audit_log_service import AuditLogService
from app.services.settlement_service import Settlement, SettlementService
from app.services.exceptions import NotFoundError, ValidationError
from app.services.settings_service import SettingsService
from app.services.shared_split_rules import equal_split
from app.utils.money import to_decimal, validate_positive_money


class SharedLivingService:
    def __init__(self, session: Session):
        self.session = session
        self.settlement_service = SettlementService()
        self.people_repo = PersonRepository(session)
        self.repo = SharedExpenseRepository(session)

    def house_members(self) -> list[Person]:
        return self.people_repo.get_house_members()

    def active_people(self) -> list[Person]:
        return sorted(self.people_repo.get_active_people(), key=lambda person: (not person.is_house_member, person.name))

    def list_expenses(self) -> list[SharedExpense]:
        return self.repo.list_expenses()

    def add_equal_expense(
        self,
        *,
        title: str,
        amount: Decimal | str,
        paid_by_person_id: int,
        participant_ids: list[int],
        date_: date,
        category_id: int | None = None,
        note: str | None = None,
        payment_method_id: int | None = None,
    ) -> SharedExpense:
        amount_dec = validate_positive_money(amount)
        title = title.strip()
        if not title:
            raise ValidationError("Shared expense title is required.")
        participant_ids = list(dict.fromkeys(participant_ids))
        if not participant_ids:
            raise ValidationError("At least one participant is required.")
        existing_ids = self.people_repo.existing_active_ids(participant_ids)
        if existing_ids != set(participant_ids):
            raise NotFoundError("One or more participants no longer exist.")
        payer = self.people_repo.get_by_id(paid_by_person_id)
        if payer is None or not payer.is_active:
            raise NotFoundError("Payer not found.")
        shares = equal_split(amount_dec, len(participant_ids))
        expense = self.repo.create_shared_expense(
            title=title,
            amount=amount_dec,
            paid_by_person_id=paid_by_person_id,
            category_id=category_id,
            payment_method_id=payment_method_id,
            date=date_,
            split_type=SplitType.EQUAL,
            note=note,
        )
        for person_id, share in zip(participant_ids, shares, strict=True):
            paid = amount_dec if person_id == paid_by_person_id else Decimal("0.00")
            self.repo.add_participant(
                shared_expense_id=expense.id,
                person_id=person_id,
                share_amount=share,
                paid_amount=paid,
                balance=to_decimal(paid - share),
            )
        if paid_by_person_id not in participant_ids:
            self.repo.add_participant(
                shared_expense_id=expense.id,
                person_id=paid_by_person_id,
                share_amount=Decimal("0.00"),
                paid_amount=amount_dec,
                balance=amount_dec,
            )
        AuditLogService(self.session).record("create shared expense", "SharedExpense", expense.id, new_value={"title": title, "amount": str(amount_dec)})
        return expense

    def balances(self) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = {}
        for expense in self.list_expenses():
            for participant in expense.participants:
                totals[participant.person.name] = totals.get(participant.person.name, Decimal("0.00")) + participant.balance
        return {name: to_decimal(value) for name, value in totals.items()}

    def balance_by_person_id(self) -> dict[int, Decimal]:
        totals: dict[int, Decimal] = {}
        for expense in self.list_expenses():
            for participant in expense.participants:
                totals[participant.person_id] = totals.get(participant.person_id, Decimal("0.00")) + participant.balance
        return {person_id: to_decimal(value) for person_id, value in totals.items()}

    def owner_balance(self) -> Decimal:
        owner_id = SettingsService(self.session).owner_person_id()
        if owner_id is None:
            return Decimal("0.00")
        return self.balance_by_person_id().get(owner_id, Decimal("0.00"))

    def summary(self) -> dict[str, Decimal]:
        owner_balance = self.owner_balance()
        receivable = owner_balance if owner_balance > 0 else Decimal("0.00")
        payable = -owner_balance if owner_balance < 0 else Decimal("0.00")
        return {"receivable": to_decimal(receivable), "payable": to_decimal(payable)}

    def settlements(self) -> list[Settlement]:
        return self.settlement_service.optimize(self.balances())
