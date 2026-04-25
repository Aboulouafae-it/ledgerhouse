from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, Money


class SharedExpenseParticipant(Base):
    __tablename__ = "shared_expense_participants"
    __table_args__ = (
        UniqueConstraint("shared_expense_id", "person_id", name="uq_shared_expense_participant_person"),
        CheckConstraint("share_amount >= 0", name="ck_shared_participants_share_non_negative"),
        CheckConstraint("paid_amount >= 0", name="ck_shared_participants_paid_non_negative"),
        Index("ix_shared_expense_participants_person_id", "person_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    shared_expense_id: Mapped[int] = mapped_column(ForeignKey("shared_expenses.id", ondelete="CASCADE"), nullable=False)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="RESTRICT"), nullable=False)
    share_amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    balance: Mapped[Decimal] = mapped_column(Money, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    shared_expense = relationship("SharedExpense", back_populates="participants")
    person = relationship("Person", back_populates="shared_expense_participations")
