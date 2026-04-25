from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.debt import Debt, DebtDirection, DebtStatus
from app.models.debt_payment import DebtPayment
from app.models.person import Person
from app.repositories.debt_repository import DebtRepository
from app.repositories.person_repository import PersonRepository
from app.services.audit_log_service import AuditLogService
from app.services.debt_rules import calculate_debt_status, calculate_remaining
from app.services.exceptions import NotFoundError, ValidationError
from app.utils.money import to_decimal, validate_positive_money


class DebtService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = DebtRepository(session)
        self.person_repo = PersonRepository(session)

    def list_debts(self) -> list[Debt]:
        debts = self.repo.list_debts()
        for debt in debts:
            self.recalculate_debt(debt)
        return debts

    def people_for_direction(self, direction: DebtDirection) -> list[Person]:
        if direction == DebtDirection.I_OWE_HIM:
            return self.person_repo.get_creditors()
        else:
            return self.person_repo.get_debtors()

    def payment_history(self, debt_id: int) -> list[DebtPayment]:
        return self.repo.payment_history(debt_id)

    def add_debt(
        self,
        *,
        person_id: int,
        direction: DebtDirection,
        amount: Decimal | str,
        due_date: date | None = None,
        note: str | None = None,
        currency: str = "EUR",
    ) -> Debt:
        person = self.person_repo.get_by_id(person_id)
        if person is None or not person.is_active:
            raise NotFoundError("Person not found.")
        if direction == DebtDirection.I_OWE_HIM and not person.is_creditor:
            raise ValidationError("Select an active creditor for debts you owe.")
        if direction == DebtDirection.HE_OWES_ME and not person.is_debtor:
            raise ValidationError("Select an active debtor for debts owed to you.")
        original = validate_positive_money(amount)
        debt = self.repo.create_debt(
            person_id=person_id,
            direction=direction,
            original_amount=original,
            remaining_amount=original,
            currency=currency,
            status=DebtStatus.OPEN,
            due_date=due_date,
            note=note,
        )
        AuditLogService(self.session).record("create debt", "Debt", debt.id, new_value={"person_id": person_id, "amount": str(original)})
        return debt

    def register_payment(self, debt_id: int, amount: Decimal | str, payment_date: date, note: str | None = None, payment_method_id: int | None = None) -> Debt:
        debt = self.repo.get_by_id(debt_id)
        if not debt:
            raise NotFoundError("Debt not found.")
        self.recalculate_debt(debt)
        if debt.remaining_amount <= 0:
            raise ValidationError("This debt is already paid.")
        amount_dec = validate_positive_money(amount)
        if amount_dec > debt.remaining_amount:
            raise ValidationError(f"Payment cannot exceed the remaining amount ({debt.remaining_amount}).")
        self.repo.add_payment(debt_id=debt_id, amount=amount_dec, currency=debt.currency, payment_method_id=payment_method_id, date=payment_date, note=note)
        self.recalculate_debt(debt)
        AuditLogService(self.session).record("add debt payment", "Debt", debt.id, new_value={"amount": str(amount_dec)})
        return debt

    def recalculate_debt(self, debt: Debt) -> None:
        paid = to_decimal(self.repo.total_payments(debt.id))
        debt.remaining_amount = calculate_remaining(debt.original_amount, paid)
        debt.status = calculate_debt_status(debt.original_amount, paid, debt.due_date)

    def totals(self) -> tuple[Decimal, Decimal]:
        owed_to_me = Decimal("0.00")
        i_owe = Decimal("0.00")
        for debt in self.list_debts():
            self.recalculate_debt(debt)
            if debt.status == DebtStatus.PAID:
                continue
            if debt.direction == DebtDirection.HE_OWES_ME:
                owed_to_me += debt.remaining_amount
            else:
                i_owe += debt.remaining_amount
        return owed_to_me, i_owe
