from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, Money


class AccountType(StrEnum):
    CASH = "cash"
    BANK = "bank"
    CARD = "card"
    OTHER = "other"


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (CheckConstraint("opening_balance >= 0", name="ck_accounts_opening_balance_non_negative"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    type: Mapped[AccountType] = mapped_column(Enum(AccountType), default=AccountType.CASH, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    opening_balance: Mapped[Decimal] = mapped_column(Money, default=Decimal("0.00"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    transactions = relationship("Transaction", back_populates="account")

