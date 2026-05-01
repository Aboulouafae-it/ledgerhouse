from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.transaction import TransactionType
from app.repositories.transaction_repository import TransactionRepository
from app.services.settings_service import SettingsService
from app.services.debt_service import DebtService
from app.services.shared_living_service import SharedLivingService
from app.utils.money import to_decimal

logger = logging.getLogger(__name__)


class DashboardService:
    def __init__(self, session: Session):
        self.session = session
        self.transactions = TransactionRepository(session)

    def summary(self, start: date | None = None, end: date | None = None, period: str | None = None) -> dict[str, Decimal | str | date | None]:
        start, end, label = self.period_range(period, start, end)
        try:
            by_type = self.transactions.totals_by_type(start, end)
            income = by_type.get(TransactionType.INCOME, Decimal("0.00"))
            expenses = by_type.get(TransactionType.EXPENSE, Decimal("0.00"))
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
                "period_label": label,
                "start": start,
                "end": end,
                "currency": SettingsService(self.session).get("default_currency", "EUR"),
            }
        except Exception:
            logger.exception("Dashboard aggregation failed for period=%s start=%s end=%s", period, start, end)
            raise

    def period_range(self, period: str | None = None, start: date | None = None, end: date | None = None) -> tuple[date | None, date | None, str]:
        if start is not None or end is not None:
            return start, end, "Custom"
        selected = (period or SettingsService(self.session).get("default_dashboard_period", "this month")).strip().lower()
        today = date.today()
        if selected == "last month":
            first_this_month = date(today.year, today.month, 1)
            last_month_end = first_this_month - timedelta(days=1)
            return date(last_month_end.year, last_month_end.month, 1), last_month_end, "Last month"
        if selected == "this year":
            return date(today.year, 1, 1), today, "This year"
        if selected == "all time":
            return None, None, "All time"
        return date(today.year, today.month, 1), today, "This month"

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
            expense = self._sum_for(TransactionType.EXPENSE, start, end)
            results.append((start.strftime("%b"), income, expense))
        return results

    def _sum_for(self, type_: TransactionType, start: date, end_exclusive: date) -> Decimal:
        return to_decimal(self.transactions.sum_for_type(type_, start, end_exclusive))
