from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.transaction import TransactionType
from app.repositories.transaction_repository import TransactionRepository
from app.services.debt_service import DebtService
from app.services.shared_living_service import SharedLivingService
from app.utils.money import to_decimal


class DashboardService:
    def __init__(self, session: Session):
        self.session = session
        self.transactions = TransactionRepository(session)

    def summary(self, start: date | None = None, end: date | None = None) -> dict[str, Decimal]:
        start = start or date(date.today().year, date.today().month, 1)
        end = end or date.today()
        by_type = self.transactions.totals_by_type(start, end)
        income = by_type.get(TransactionType.INCOME, Decimal("0.00"))
        expenses = by_type.get(TransactionType.EXPENSE, Decimal("0.00")) + by_type.get(TransactionType.SHARED_EXPENSE, Decimal("0.00"))
        savings = by_type.get(TransactionType.SAVING, Decimal("0.00"))
        owed_to_me, i_owe = DebtService(self.session).totals()
        shared = SharedLivingService(self.session).summary()
        return {
            "income": to_decimal(income),
            "expenses": to_decimal(expenses),
            "net_balance": to_decimal(income - expenses),
            "savings": to_decimal(savings),
            "owed_to_me": to_decimal(owed_to_me),
            "i_owe": to_decimal(i_owe),
            "shared_receivable": to_decimal(shared["receivable"]),
            "shared_payable": to_decimal(shared["payable"]),
        }

    def monthly_income_expenses(self, months: int = 6) -> list[tuple[str, Decimal, Decimal]]:
        today = date.today()
        results: list[tuple[str, Decimal, Decimal]] = []
        for offset in range(months - 1, -1, -1):
            month = today.month - offset
            year = today.year
            while month <= 0:
                month += 12
                year -= 1
            start = date(year, month, 1)
            end = date(year + (month // 12), (month % 12) + 1, 1) if month < 12 else date(year + 1, 1, 1)
            income = self._sum_for(TransactionType.INCOME, start, end)
            expense = self._sum_for(TransactionType.EXPENSE, start, end) + self._sum_for(TransactionType.SHARED_EXPENSE, start, end)
            results.append((start.strftime("%b"), income, expense))
        return results

    def _sum_for(self, type_: TransactionType, start: date, end_exclusive: date) -> Decimal:
        return to_decimal(self.transactions.sum_for_type(type_, start, end_exclusive))
