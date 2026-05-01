from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.transaction import Transaction
from app.models.transaction import TransactionType
from decimal import Decimal


class TransactionRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_transaction(self, **values) -> Transaction:  # type: ignore[no-untyped-def]
        tx = Transaction(**values)
        self.session.add(tx)
        self.session.flush()
        return tx

    def update_transaction(self, tx: Transaction, **values) -> Transaction:  # type: ignore[no-untyped-def]
        for key, value in values.items():
            setattr(tx, key, value)
        self.session.flush()
        return tx

    def get_by_id(self, transaction_id: int) -> Transaction | None:
        return self.session.get(Transaction, transaction_id)

    def deactivate_transaction(self, transaction_id: int) -> None:
        tx = self.get_by_id(transaction_id)
        if tx:
            tx.is_active = False
            tx.deleted_at = datetime.utcnow()
            self.session.flush()

    def list_transactions(self, limit: int | None = None, start: date | None = None, end: date | None = None, active_only: bool = True) -> list[Transaction]:
        stmt = (
            select(Transaction)
            .options(joinedload(Transaction.category), joinedload(Transaction.person), joinedload(Transaction.payment_method_ref))
            .order_by(Transaction.date.desc(), Transaction.id.desc())
        )
        if active_only:
            stmt = stmt.where(Transaction.is_active.is_(True))
        if start:
            stmt = stmt.where(Transaction.date >= start)
        if end:
            stmt = stmt.where(Transaction.date <= end)
        if limit:
            stmt = stmt.limit(limit)
        return list(self.session.scalars(stmt))

    def totals_by_type(self, start: date | None = None, end: date | None = None) -> dict[TransactionType, Decimal]:
        stmt = select(Transaction.type, func.coalesce(func.sum(Transaction.amount), 0)).where(Transaction.is_active.is_(True))
        if start is not None:
            stmt = stmt.where(Transaction.date >= start)
        if end is not None:
            stmt = stmt.where(Transaction.date <= end)
        rows = self.session.execute(stmt.group_by(Transaction.type)).all()
        return {kind: Decimal(total or 0) for kind, total in rows}

    def sum_for_type(self, type_: TransactionType, start: date, end_exclusive: date) -> Decimal:
        total = self.session.scalar(select(func.coalesce(func.sum(Transaction.amount), 0)).where(Transaction.type == type_, Transaction.is_active.is_(True), Transaction.date >= start, Transaction.date < end_exclusive))
        return Decimal(total or 0)
