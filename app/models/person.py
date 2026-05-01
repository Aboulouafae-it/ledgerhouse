from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Person(Base):
    __tablename__ = "people"
    __table_args__ = (Index("ix_people_normalized_name", "normalized_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(140), nullable=False, default="")
    phone: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(180))
    note: Mapped[str | None] = mapped_column(Text)
    is_creditor: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_debtor: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_employer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_service_provider: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_family_friend: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_house_member: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    transactions = relationship("Transaction", back_populates="person")
    debts = relationship("Debt", back_populates="person")
    paid_shared_expenses = relationship("SharedExpense", back_populates="paid_by", foreign_keys="SharedExpense.paid_by_person_id")
    shared_expense_participations = relationship("SharedExpenseParticipant", back_populates="person")
    settlements_from = relationship("Settlement", back_populates="from_person", foreign_keys="Settlement.from_person_id")
    settlements_to = relationship("Settlement", back_populates="to_person", foreign_keys="Settlement.to_person_id")

    def __repr__(self) -> str:
        return f"Person(id={self.id!r}, name={self.name!r})"
