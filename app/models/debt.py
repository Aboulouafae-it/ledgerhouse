from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import CheckConstraint, Date, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, Money


class DebtDirection(StrEnum):
    I_OWE_HIM = "I_OWE_HIM"
    HE_OWES_ME = "HE_OWES_ME"


class DebtStatus(StrEnum):
    OPEN = "open"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"


class Debt(Base):
    __tablename__ = "debts"
    __table_args__ = (
        CheckConstraint("original_amount > 0", name="ck_debts_original_amount_positive"),
        CheckConstraint("remaining_amount >= 0", name="ck_debts_remaining_amount_non_negative"),
        Index("ix_debts_person_id", "person_id"),
        Index("ix_debts_status", "status"),
        Index("ix_debts_due_date", "due_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="RESTRICT"), nullable=False)
    direction: Mapped[DebtDirection] = mapped_column(Enum(DebtDirection), nullable=False)
    original_amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    remaining_amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    status: Mapped[DebtStatus] = mapped_column(Enum(DebtStatus), default=DebtStatus.OPEN, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(Text)
    created_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    person = relationship("Person", back_populates="debts")
    payments = relationship("DebtPayment", back_populates="debt", cascade="all, delete-orphan")
    created_transaction = relationship("Transaction")
