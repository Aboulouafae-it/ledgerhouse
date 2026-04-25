from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session

from app.reports.report_generator import ReportGenerator
from app.models.transaction import TransactionType
from app.services.dashboard_service import DashboardService
from app.services.debt_service import DebtService
from app.services.shared_living_service import SharedLivingService
from app.services.settings_service import SettingsService
from app.services.transaction_service import TransactionService
from app.services.audit_log_service import AuditLogService
from app.repositories.report_repository import ReportRepository
from app.repositories.user_repository import UserRepository
from app.core.session import current_session


class ReportType:
    INCOME = "Income report"
    EXPENSE = "Expense report"
    DEBT = "Debt report"
    SHARED = "Shared living report"
    FULL = "Full financial report"


class ReportService:
    def __init__(self, session: Session):
        self.session = session

    def generate_full_report(self, output_path: Path, start: date, end: date, owner_name: str = "") -> Path:
        generator, owner_name = self._generator(owner_name)
        shared_service = SharedLivingService(self.session)
        path = generator.full_financial_report(
            output_path=output_path,
            owner_name=owner_name,
            period=(start, end),
            summary=DashboardService(self.session).summary(start, end),
            transactions=TransactionService(self.session).list_transactions(start=start, end=end),
            debts=DebtService(self.session).list_debts(),
            shared_expenses=self._shared_expenses_for_period(shared_service, start, end),
            settlements=shared_service.settlements(),
        )
        self._record_export(ReportType.FULL, path, start, end)
        return path

    def generate_report(self, report_type: str, output_path: Path, start: date, end: date, owner_name: str = "") -> Path:
        generator, owner_name = self._generator(owner_name)
        transactions = TransactionService(self.session)
        debts = DebtService(self.session)
        shared = SharedLivingService(self.session)
        if report_type == ReportType.INCOME:
            rows = [tx for tx in transactions.list_transactions(start=start, end=end) if tx.type == TransactionType.INCOME]
            path = generator.income_report(output_path=output_path, owner_name=owner_name, period=(start, end), transactions=rows)
            self._record_export(report_type, path, start, end)
            return path
        if report_type == ReportType.EXPENSE:
            rows = [
                tx
                for tx in transactions.list_transactions(start=start, end=end)
                if tx.type in {TransactionType.EXPENSE, TransactionType.SHARED_EXPENSE}
            ]
            path = generator.expense_report(output_path=output_path, owner_name=owner_name, period=(start, end), transactions=rows)
            self._record_export(report_type, path, start, end)
            return path
        if report_type == ReportType.DEBT:
            path = generator.debt_report(output_path=output_path, owner_name=owner_name, period=(start, end), debts=debts.list_debts())
            self._record_export(report_type, path, start, end)
            return path
        if report_type == ReportType.SHARED:
            path = generator.shared_living_report(
                output_path=output_path,
                owner_name=owner_name,
                period=(start, end),
                expenses=self._shared_expenses_for_period(shared, start, end),
                balances=shared.balances(),
                settlements=shared.settlements(),
            )
            self._record_export(report_type, path, start, end)
            return path
        return self.generate_full_report(output_path, start, end, owner_name)

    def _shared_expenses_for_period(self, service: SharedLivingService, start: date, end: date):
        return [expense for expense in service.list_expenses() if start <= expense.date <= end]

    def _generator(self, owner_name: str) -> tuple[ReportGenerator, str]:
        settings = SettingsService(self.session)
        return (
            ReportGenerator(
                settings.get("report_title_prefix", "Personal Ledger Pro"),
                settings.get("report_footer_text", "Administrative financial report"),
            ),
            owner_name or settings.get("owner_name", ""),
        )

    def _record_export(self, report_type: str, path: Path, start: date, end: date) -> None:
        try:
            generated_by_user_id = current_session.user_id
            if generated_by_user_id is not None and UserRepository(self.session).get_by_id(generated_by_user_id) is None:
                generated_by_user_id = None
            export = ReportRepository(self.session).create_export(
                report_type=report_type,
                period_start=start,
                period_end=end,
                file_path=str(path),
                generated_by_user_id=generated_by_user_id,
            )
            AuditLogService(self.session).record("generate PDF report", "ReportExport", export.id, new_value={"type": report_type, "path": str(path)})
        except Exception:
            return

    def export_transactions_csv(self, output_path: Path) -> Path:
        rows = TransactionService(self.session).list_transactions()
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Date", "Type", "Amount", "Currency", "Category", "Person", "Payment Method", "Note"])
            for tx in rows:
                payment_method = tx.payment_method_ref.name if tx.payment_method_ref else tx.payment_method or ""
                writer.writerow([tx.date, tx.type.value, tx.amount, tx.currency, tx.category.name if tx.category else "", tx.person.name if tx.person else "", payment_method, tx.note or ""])
        return output_path
