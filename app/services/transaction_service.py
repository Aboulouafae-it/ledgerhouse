from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.category import Category, CategoryType
from app.models.payment_method import PaymentMethod
from app.models.person import Person
from app.models.transaction import Transaction, TransactionType
from app.repositories.category_repository import CategoryRepository
from app.repositories.payment_method_repository import PaymentMethodRepository
from app.repositories.person_repository import PersonRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services.audit_log_service import AuditLogService
from app.services.exceptions import NotFoundError, ValidationError
from app.services.settings_service import SettingsService
from app.utils.dates import coerce_date
from app.utils.money import validate_positive_money


class TransactionService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = TransactionRepository(session)
        self.category_repo = CategoryRepository(session)
        self.person_repo = PersonRepository(session)
        self.payment_repo = PaymentMethodRepository(session)

    def list_transactions(self, limit: int | None = None, start: date | None = None, end: date | None = None, active_only: bool = True) -> list[Transaction]:
        return self.repo.list_transactions(limit=limit, start=start, end=end, active_only=active_only)

    def get_transaction(self, transaction_id: int) -> Transaction:
        tx = self.repo.get_by_id(transaction_id)
        if tx is None or not tx.is_active:
            raise NotFoundError("Transaction not found.")
        return tx

    def add_transaction(
        self,
        *,
        type_: TransactionType,
        amount: Decimal | str,
        date_: date,
        currency: str | None = None,
        category_id: int | None = None,
        person_id: int | None = None,
        payment_method: str | None = None,
        payment_method_id: int | None = None,
        note: str | None = None,
        is_shared: bool = False,
    ) -> Transaction:
        amount_dec = validate_positive_money(amount)
        date_value = self._validate_date(date_)
        currency = self._validate_currency(currency)
        self._validate_references(category_id, person_id, payment_method_id)
        tx = self.repo.create_transaction(
            type=type_,
            amount=amount_dec,
            currency=currency,
            category_id=category_id,
            person_id=person_id,
            payment_method_id=payment_method_id,
            payment_method=payment_method,
            date=date_value,
            note=note,
            is_shared=is_shared,
        )
        AuditLogService(self.session).record("create transaction", "Transaction", tx.id, new_value={"type": tx.type.value, "amount": str(tx.amount)})
        return tx

    def duplicate_transaction(self, transaction_id: int, *, date_: date | None = None) -> Transaction:
        tx = self.get_transaction(transaction_id)
        return self.add_transaction(
            type_=tx.type,
            amount=tx.amount,
            currency=tx.currency,
            date_=date_ or date.today(),
            category_id=tx.category_id,
            person_id=tx.person_id,
            payment_method=tx.payment_method,
            payment_method_id=tx.payment_method_id,
            note=tx.note,
            is_shared=tx.is_shared,
        )

    def update_transaction(
        self,
        transaction_id: int,
        *,
        type_: TransactionType,
        amount: Decimal | str,
        date_: date | str,
        category_id: int | None = None,
        person_id: int | None = None,
        payment_method: str | None = None,
        payment_method_id: int | None = None,
        note: str | None = None,
    ) -> Transaction:
        tx = self.get_transaction(transaction_id)
        if self.is_linked(tx) and self._unsafe_linked_change(tx, type_, amount, date_, category_id, person_id):
            raise ValidationError("This transaction is linked to debt/shared living records. Only note and payment method can be changed safely here.")
        amount_dec = validate_positive_money(amount)
        date_value = self._validate_date(date_)
        self._validate_references(category_id, person_id, payment_method_id)
        updated = self.repo.update_transaction(
            tx,
            type=type_,
            amount=amount_dec,
            category_id=category_id,
            person_id=person_id,
            payment_method_id=payment_method_id,
            payment_method=payment_method,
            date=date_value,
            note=note,
            is_shared=type_ == TransactionType.SHARED_EXPENSE,
        )
        AuditLogService(self.session).record("update transaction", "Transaction", updated.id, new_value={"type": updated.type.value, "amount": str(updated.amount)})
        return updated

    def deactivate_transaction(self, transaction_id: int) -> None:
        tx = self.get_transaction(transaction_id)
        if self.is_linked(tx):
            raise ValidationError("This transaction is linked to debt/shared living records and cannot be deactivated from Transactions.")
        self.repo.deactivate_transaction(transaction_id)
        AuditLogService(self.session).record("deactivate transaction", "Transaction", transaction_id)

    def linked_warning(self, transaction_id: int) -> str | None:
        tx = self.repo.get_by_id(transaction_id)
        if tx is None:
            return None
        if self.is_linked(tx):
            return "This transaction is linked to debt/shared living records. Unsafe edits or deletion are blocked."
        return None

    def is_linked(self, tx: Transaction) -> bool:
        return bool(tx.reference_type or tx.reference_id or tx.type in {TransactionType.DEBT_IN, TransactionType.DEBT_OUT, TransactionType.DEBT_PAYMENT, TransactionType.SHARED_EXPENSE} or tx.is_shared)

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

    def people_for_transaction_type(self, type_: TransactionType) -> list[Person]:
        people = self.person_repo.get_active_people()
        if type_ == TransactionType.INCOME:
            return sorted(people, key=lambda person: (not person.is_employer, person.name.casefold()))
        if type_ == TransactionType.SHARED_EXPENSE:
            return sorted(people, key=lambda person: (not person.is_house_member, person.name.casefold()))
        return people

    def payment_methods(self) -> list[PaymentMethod]:
        return self.payment_repo.get_active_methods()

    def default_currency(self) -> str:
        return self._validate_currency(None)

    def _validate_currency(self, currency: str | None) -> str:
        code = (currency or SettingsService(self.session).get("default_currency", "EUR")).strip().upper()
        if len(code) != 3 or not code.isalpha():
            raise ValidationError("Currency must be a 3-letter code.")
        return code

    def _validate_date(self, value: date | str) -> date:
        try:
            return coerce_date(value)
        except Exception as exc:
            raise ValidationError("Use date format YYYY-MM-DD.") from exc

    def _validate_references(self, category_id: int | None, person_id: int | None, payment_method_id: int | None) -> None:
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

    def _unsafe_linked_change(self, tx: Transaction, type_: TransactionType, amount: Decimal | str, date_: date | str, category_id: int | None, person_id: int | None) -> bool:
        try:
            amount_dec = validate_positive_money(amount)
            date_value = self._validate_date(date_)
        except ValidationError:
            return True
        return any(
            [
                tx.type != type_,
                tx.amount != amount_dec,
                tx.date != date_value,
                tx.category_id != category_id,
                tx.person_id != person_id,
            ]
        )
