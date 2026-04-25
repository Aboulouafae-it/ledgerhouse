from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.category import CategoryType
from app.models.transaction import Transaction, TransactionType
from app.repositories.category_repository import CategoryRepository
from app.repositories.payment_method_repository import PaymentMethodRepository
from app.repositories.person_repository import PersonRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services.audit_log_service import AuditLogService
from app.services.exceptions import NotFoundError, ValidationError
from app.utils.money import validate_positive_money


class TransactionService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = TransactionRepository(session)
        self.category_repo = CategoryRepository(session)
        self.person_repo = PersonRepository(session)
        self.payment_repo = PaymentMethodRepository(session)

    def list_transactions(self, limit: int | None = None, start: date | None = None, end: date | None = None) -> list[Transaction]:
        return self.repo.list_transactions(limit=limit, start=start, end=end)

    def add_transaction(
        self,
        *,
        type_: TransactionType,
        amount: Decimal | str,
        date_: date,
        currency: str = "EUR",
        category_id: int | None = None,
        person_id: int | None = None,
        payment_method: str | None = None,
        payment_method_id: int | None = None,
        note: str | None = None,
        is_shared: bool = False,
    ) -> Transaction:
        amount_dec = validate_positive_money(amount)
        currency = currency.strip().upper()
        if len(currency) != 3:
            raise ValidationError("Currency must be a 3-letter code.")
        if category_id is not None:
            category = self.category_repo.get_by_id(category_id)
            if category is None or not category.is_active:
                raise NotFoundError("Category not found.")
        if payment_method_id is not None:
            method = self.payment_repo.get_by_id(payment_method_id)
            if method is None or not method.is_active:
                raise NotFoundError("Payment method not found.")
        if person_id is not None:
            person = self.person_repo.get_by_id(person_id)
            if person is None or not person.is_active:
                raise NotFoundError("Person not found.")
        tx = self.repo.create_transaction(
            type=type_,
            amount=amount_dec,
            currency=currency,
            category_id=category_id,
            person_id=person_id,
            payment_method_id=payment_method_id,
            payment_method=payment_method,
            date=date_,
            note=note,
            is_shared=is_shared,
        )
        AuditLogService(self.session).record("create transaction", "Transaction", tx.id, new_value={"type": tx.type.value, "amount": str(tx.amount)})
        return tx

    def delete_transaction(self, transaction_id: int) -> None:
        self.repo.delete_transaction(transaction_id)

    def categories(self) -> list[Category]:
        return self.category_repo.list_categories(active_only=True)

    def categories_for_transaction_type(self, type_: TransactionType) -> list[Category]:
        if type_ == TransactionType.INCOME:
            kinds = [CategoryType.INCOME]
        elif type_ == TransactionType.SAVING:
            kinds = [CategoryType.SAVING]
        elif type_ in {TransactionType.DEBT_IN, TransactionType.DEBT_OUT, TransactionType.DEBT_PAYMENT}:
            kinds = [CategoryType.DEBT]
        elif type_ == TransactionType.SHARED_EXPENSE:
            kinds = [CategoryType.SHARED, CategoryType.EXPENSE]
        else:
            kinds = [CategoryType.EXPENSE]
        return self.category_repo.get_active_by_type(kinds)

    def people(self) -> list[Person]:
        return self.person_repo.get_active_people()

    def payment_methods(self) -> list[PaymentMethod]:
        return self.payment_repo.get_active_methods()
