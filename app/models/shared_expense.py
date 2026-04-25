from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import CheckConstraint, Date, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, Money


class SplitType(StrEnum):
    EQUAL = "equal"
    PERCENTAGE = "percentage"
    CUSTOM_AMOUNT = "custom_amount"


class SharedExpense(Base):
    __tablename__ = "shared_expenses"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_shared_expenses_amount_positive"),
        Index("ix_shared_expenses_date", "date"),
        Index("ix_shared_expenses_paid_by_person_id", "paid_by_person_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    paid_by_person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="RESTRICT"), nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    payment_method_id: Mapped[int | None] = mapped_column(ForeignKey("payment_methods.id", ondelete="SET NULL"))
    date: Mapped[date] = mapped_column(Date, nullable=False)
    split_type: Mapped[SplitType] = mapped_column(Enum(SplitType), default=SplitType.EQUAL, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    paid_by = relationship("Person", back_populates="paid_shared_expenses", foreign_keys=[paid_by_person_id])
    category = relationship("Category", back_populates="shared_expenses")
    payment_method = relationship("PaymentMethod")
    transaction = relationship("Transaction")
    participants = relationship("SharedExpenseParticipant", back_populates="shared_expense", cascade="all, delete-orphan")
