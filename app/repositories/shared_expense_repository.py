from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.shared_expense import SharedExpense
from app.models.shared_expense_participant import SharedExpenseParticipant


class SharedExpenseRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_shared_expense(self, **values) -> SharedExpense:  # type: ignore[no-untyped-def]
        expense = SharedExpense(**values)
        self.session.add(expense)
        self.session.flush()
        return expense

    def add_participant(self, **values) -> SharedExpenseParticipant:  # type: ignore[no-untyped-def]
        participant = SharedExpenseParticipant(**values)
        self.session.add(participant)
        self.session.flush()
        return participant

    def list_expenses(self) -> list[SharedExpense]:
        return list(self.session.scalars(select(SharedExpense).options(joinedload(SharedExpense.paid_by), joinedload(SharedExpense.participants).joinedload(SharedExpenseParticipant.person)).order_by(SharedExpense.date.desc(), SharedExpense.id.desc())).unique())

    def get_by_id(self, expense_id: int) -> SharedExpense | None:
        return self.session.scalar(
            select(SharedExpense)
            .where(SharedExpense.id == expense_id)
            .options(joinedload(SharedExpense.paid_by), joinedload(SharedExpense.participants).joinedload(SharedExpenseParticipant.person))
        )

    def delete_expense(self, expense: SharedExpense) -> None:
        self.session.delete(expense)
        self.session.flush()

    def get_expenses_by_period(self, start: date, end: date) -> list[SharedExpense]:
        return [expense for expense in self.list_expenses() if start <= expense.date <= end]
