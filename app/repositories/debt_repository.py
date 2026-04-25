from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.debt import Debt
from app.models.debt_payment import DebtPayment


class DebtRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_debt(self, **values) -> Debt:  # type: ignore[no-untyped-def]
        debt = Debt(**values)
        self.session.add(debt)
        self.session.flush()
        return debt

    def get_by_id(self, debt_id: int) -> Debt | None:
        return self.session.get(Debt, debt_id)

    def add_payment(self, **values) -> DebtPayment:  # type: ignore[no-untyped-def]
        payment = DebtPayment(**values)
        self.session.add(payment)
        self.session.flush()
        return payment

    def list_debts(self) -> list[Debt]:
        return list(self.session.scalars(select(Debt).options(joinedload(Debt.person), joinedload(Debt.payments)).order_by(Debt.created_at.desc())).unique())

    def total_payments(self, debt_id: int) -> Decimal:
        return Decimal(self.session.scalar(select(func.coalesce(func.sum(DebtPayment.amount), 0)).where(DebtPayment.debt_id == debt_id)) or 0)

    def payment_history(self, debt_id: int) -> list[DebtPayment]:
        return list(self.session.scalars(select(DebtPayment).where(DebtPayment.debt_id == debt_id).order_by(DebtPayment.date.desc(), DebtPayment.id.desc())))
