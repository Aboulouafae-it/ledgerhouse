from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.person import Person
from app.models.category import Category, CategoryType
from app.models.payment_method import PaymentMethod
from app.repositories.category_repository import CategoryRepository
from app.repositories.payment_method_repository import PaymentMethodRepository
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
        self.category_repo = CategoryRepository(session)
        self.payment_repo = PaymentMethodRepository(session)
        self.repo = SharedExpenseRepository(session)

    def house_members(self) -> list[Person]:
        return self.people_repo.get_house_members()

    def active_people(self) -> list[Person]:
        return sorted(self.people_repo.get_active_people(), key=lambda person: (not person.is_house_member, person.name))

    def shared_categories(self) -> list[Category]:
        return self.category_repo.get_active_by_type([CategoryType.SHARED, CategoryType.EXPENSE])

    def payment_methods(self) -> list[PaymentMethod]:
        return self.payment_repo.get_active_methods()

    def list_expenses(self) -> list[SharedExpense]:
        return self.repo.list_expenses()

    def get_expense(self, expense_id: int) -> SharedExpense:
        expense = self.repo.get_by_id(expense_id)
        if expense is None:
            raise NotFoundError("Shared expense not found.")
        return expense

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
        currency: str | None = None,
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
        if category_id is not None:
            category = self.category_repo.get_by_id(category_id)
            if category is None or not category.is_active or category.type not in {CategoryType.SHARED, CategoryType.EXPENSE}:
                raise NotFoundError("Shared category not found.")
        if payment_method_id is not None:
            method = self.payment_repo.get_by_id(payment_method_id)
            if method is None or not method.is_active:
                raise NotFoundError("Payment method not found.")
        currency_code = (currency or SettingsService(self.session).get("default_currency", "EUR")).strip().upper()
        if len(currency_code) != 3 or not currency_code.isalpha():
            raise ValidationError("Currency must be a 3-letter code.")
        shares = equal_split(amount_dec, len(participant_ids))
        expense = self.repo.create_shared_expense(
            title=title,
            amount=amount_dec,
            currency=currency_code,
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

    def update_equal_expense(
        self,
        expense_id: int,
        *,
        title: str,
        amount: Decimal | str,
        paid_by_person_id: int,
        participant_ids: list[int],
        date_: date,
        note: str | None = None,
        category_id: int | None = None,
        payment_method_id: int | None = None,
    ) -> SharedExpense:
        expense = self.get_expense(expense_id)
        self.repo.delete_expense(expense)
        updated = self.add_equal_expense(
            title=title,
            amount=amount,
            paid_by_person_id=paid_by_person_id,
            participant_ids=participant_ids,
            date_=date_,
            note=note,
            category_id=category_id,
            payment_method_id=payment_method_id,
        )
        AuditLogService(self.session).record("update shared expense", "SharedExpense", updated.id, old_value={"id": expense_id}, new_value={"title": title})
        return updated

    def delete_expense(self, expense_id: int) -> None:
        expense = self.get_expense(expense_id)
        title = expense.title
        self.repo.delete_expense(expense)
        AuditLogService(self.session).record("delete shared expense", "SharedExpense", expense_id, old_value={"title": title})

    def member_month_details(self, person_id: int, today: date | None = None) -> dict[str, object]:
        today = today or date.today()
        start = date(today.year, today.month, 1)
        paid_total = Decimal("0.00")
        share_total = Decimal("0.00")
        balance_total = Decimal("0.00")
        paid_items: list[tuple[date, str, Decimal]] = []
        participated_items: list[tuple[date, str, Decimal, Decimal, Decimal]] = []
        for expense in self.list_expenses():
            if not (start <= expense.date <= today):
                continue
            if expense.paid_by_person_id == person_id:
                paid_total += expense.amount
                paid_items.append((expense.date, expense.title, expense.amount))
            for participant in expense.participants:
                if participant.person_id == person_id:
                    share_total += participant.share_amount
                    balance_total += participant.balance
                    participated_items.append((expense.date, expense.title, participant.share_amount, participant.paid_amount, participant.balance))
        return {
            "paid_total": to_decimal(paid_total),
            "share_total": to_decimal(share_total),
            "balance_total": to_decimal(balance_total),
            "paid_items": paid_items,
            "participated_items": participated_items,
        }

    def balances(self, expenses: list[SharedExpense] | None = None) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = {}
        for expense in expenses if expenses is not None else self.list_expenses():
            for participant in expense.participants:
                totals[participant.person.name] = totals.get(participant.person.name, Decimal("0.00")) + participant.balance
        return {name: to_decimal(value) for name, value in totals.items()}

    def balance_by_person_id(self, expenses: list[SharedExpense] | None = None) -> dict[int, Decimal]:
        totals: dict[int, Decimal] = {}
        for expense in expenses if expenses is not None else self.list_expenses():
            for participant in expense.participants:
                totals[participant.person_id] = totals.get(participant.person_id, Decimal("0.00")) + participant.balance
        return {person_id: to_decimal(value) for person_id, value in totals.items()}

    def owner_balance(self) -> Decimal:
        owner_id = SettingsService(self.session).owner_person_id()
        if owner_id is None:
            return Decimal("0.00")
        return self.balance_by_person_id().get(owner_id, Decimal("0.00"))

    def summary(self, expenses: list[SharedExpense] | None = None) -> dict[str, Decimal]:
        owner_balance = self.owner_balance()
        if expenses is not None:
            owner_id = SettingsService(self.session).owner_person_id()
            owner_balance = self.balance_by_person_id(expenses).get(owner_id, Decimal("0.00")) if owner_id is not None else Decimal("0.00")
        receivable = owner_balance if owner_balance > 0 else Decimal("0.00")
        payable = -owner_balance if owner_balance < 0 else Decimal("0.00")
        return {"receivable": to_decimal(receivable), "payable": to_decimal(payable)}

    def settlements(self, expenses: list[SharedExpense] | None = None) -> list[Settlement]:
        return self.settlement_service.optimize(self.balances(expenses))
