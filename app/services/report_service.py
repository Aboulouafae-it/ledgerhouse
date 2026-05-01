from __future__ import annotations

import csv
from datetime import date, datetime
from decimal import Decimal
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
from app.core.config import APP_LOGO_PATH
from app.core.session import current_session

from app.models.debt import DebtDirection
from app.utils.money import money


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
        data = self._report_data(start, end)
        shared_service = SharedLivingService(self.session)
        path = generator.full_financial_report(
            output_path=output_path,
            owner_name=owner_name,
            period=(start, end),
            summary=data["summary"],
            transactions=data["transactions"],
            debts=data["debts"],
            shared_expenses=data["shared_expenses"],
            settlements=shared_service.settlements(data["shared_expenses"]),
        )
        self._record_export(ReportType.FULL, path, start, end)
        return path

    def generate_report(self, report_type: str, output_path: Path, start: date, end: date, owner_name: str = "") -> Path:
        data = self._report_data(start, end)
        return self._generate_report_from_data(report_type, output_path, start, end, owner_name, data)

    def generate_report_with_preview(self, report_type: str, output_path: Path, start: date, end: date, owner_name: str = "") -> tuple[Path, dict[str, object]]:
        if start > end:
            raise ValueError("Start date must not be after end date.")
        data = self._report_data(start, end)
        preview = self._build_preview(report_type, start, end, owner_name, data)
        path = self._generate_report_from_data(report_type, output_path, start, end, owner_name, data)
        return path, preview

    def _generate_report_from_data(self, report_type: str, output_path: Path, start: date, end: date, owner_name: str, data: dict[str, object]) -> Path:
        generator, owner_name = self._generator(owner_name)
        shared = SharedLivingService(self.session)
        if report_type == ReportType.INCOME:
            rows = [tx for tx in data["transactions"] if tx.type == TransactionType.INCOME]
            path = generator.income_report(output_path=output_path, owner_name=owner_name, period=(start, end), transactions=rows)
            self._record_export(report_type, path, start, end)
            return path
        if report_type == ReportType.EXPENSE:
            rows = [
                tx for tx in data["transactions"] if tx.type in {TransactionType.EXPENSE, TransactionType.SHARED_EXPENSE}
            ]
            path = generator.expense_report(output_path=output_path, owner_name=owner_name, period=(start, end), transactions=rows)
            self._record_export(report_type, path, start, end)
            return path
        if report_type == ReportType.DEBT:
            path = generator.debt_report(output_path=output_path, owner_name=owner_name, period=(start, end), debts=data["debts"])
            self._record_export(report_type, path, start, end)
            return path
        if report_type == ReportType.SHARED:
            path = generator.shared_living_report(
                output_path=output_path,
                owner_name=owner_name,
                period=(start, end),
                expenses=data["shared_expenses"],
                balances=shared.balances(data["shared_expenses"]),
                settlements=shared.settlements(data["shared_expenses"]),
            )
            self._record_export(report_type, path, start, end)
            return path
        return self.generate_full_report(output_path, start, end, owner_name)

    def preview_report(self, report_type: str, start: date, end: date, owner_name: str = "") -> dict[str, object]:
        if start > end:
            raise ValueError("Start date must not be after end date.")
        data = self._report_data(start, end)
        return self._build_preview(report_type, start, end, owner_name, data)

    def _build_preview(self, report_type: str, start: date, end: date, owner_name: str, data: dict[str, object]) -> dict[str, object]:
        _generator, resolved_owner = self._generator(owner_name)
        transactions = data["transactions"]
        debts = data["debts"]
        shared_expenses = data["shared_expenses"]
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        preview: dict[str, object] = {
            "title": report_type,
            "owner": resolved_owner or "Not specified",
            "period": f"{start.isoformat()} to {end.isoformat()}",
            "generated_at": generated_at,
            "summary": [],
            "tables": [],
        }
        if report_type == ReportType.INCOME:
            rows = [tx for tx in transactions if tx.type == TransactionType.INCOME]
            total = sum((tx.amount for tx in rows), Decimal("0.00"))
            preview["summary"] = [("Income total", money(total)), ("Entries", str(len(rows))), ("Categories", str(len({tx.category.name for tx in rows if tx.category})))]
            preview["tables"] = [
                self._category_table("Income by category", rows),
                self._transaction_preview_table("Income transactions", rows),
            ]
        elif report_type == ReportType.EXPENSE:
            rows = [tx for tx in transactions if tx.type in {TransactionType.EXPENSE, TransactionType.SHARED_EXPENSE}]
            total = sum((tx.amount for tx in rows), Decimal("0.00"))
            preview["summary"] = [("Expense total", money(total)), ("Entries", str(len(rows))), ("Categories", str(len({tx.category.name for tx in rows if tx.category})))]
            preview["tables"] = [
                self._category_table("Expense by category", rows),
                self._transaction_preview_table("Expense transactions", rows),
            ]
        elif report_type == ReportType.DEBT:
            owed_to_me = sum((debt.remaining_amount for debt in debts if debt.direction == DebtDirection.HE_OWES_ME), Decimal("0.00"))
            i_owe = sum((debt.remaining_amount for debt in debts if debt.direction == DebtDirection.I_OWE_HIM), Decimal("0.00"))
            paid = sum((debt.original_amount - debt.remaining_amount for debt in debts), Decimal("0.00"))
            preview["summary"] = [("Debts I owe", money(i_owe)), ("Debts owed to me", money(owed_to_me)), ("Partial payments", money(paid))]
            preview["tables"] = [self._debt_preview_table("Debt status", debts)]
        elif report_type == ReportType.SHARED:
            shared_service = SharedLivingService(self.session)
            total = sum((expense.amount for expense in shared_expenses), Decimal("0.00"))
            members = {participant.person.name for expense in shared_expenses for participant in expense.participants}
            balances = shared_service.balances(shared_expenses)
            settlements = shared_service.settlements(shared_expenses)
            preview["summary"] = [("Shared expenses", money(total)), ("Members", str(len(members))), ("Settlements", str(len(settlements)))]
            preview["tables"] = [
                self._shared_preview_table("Shared expense details", shared_expenses),
                {"title": "Who owes whom", "headers": ["Person", "Balance"], "rows": [[name, money(value)] for name, value in sorted(balances.items())]},
                {"title": "Settlement suggestions", "headers": ["From", "To", "Amount"], "rows": [[row.from_person, row.to_person, money(row.amount)] for row in settlements]},
            ]
        else:
            summary = data["summary"]
            shared_summary = SharedLivingService(self.session).summary(shared_expenses)
            preview["summary"] = [
                ("Total income", money(summary.get("income", Decimal("0.00")))),
                ("Total expenses", money(summary.get("expenses", Decimal("0.00")))),
                ("Net balance", money(summary.get("net_balance", Decimal("0.00")))),
                ("Savings", money(summary.get("savings", Decimal("0.00")))),
                ("Debts owed to me", money(summary.get("owed_to_me", Decimal("0.00")))),
                ("Debts I owe", money(summary.get("i_owe", Decimal("0.00")))),
                ("Shared receivable", money(shared_summary.get("receivable", Decimal("0.00")))),
                ("Shared payable", money(shared_summary.get("payable", Decimal("0.00")))),
            ]
            preview["tables"] = [
                self._transaction_preview_table("Transaction register", transactions),
                self._debt_preview_table("Debt register", debts),
                self._shared_preview_table("Shared living summary", shared_expenses),
            ]
        preview["is_empty"] = not any(table["rows"] for table in preview["tables"])  # type: ignore[index]
        return preview

    def _shared_expenses_for_period(self, service: SharedLivingService, start: date, end: date):
        return [expense for expense in service.list_expenses() if start <= expense.date <= end]

    def _report_data(self, start: date, end: date) -> dict[str, object]:
        shared_service = SharedLivingService(self.session)
        debts = self._debts_for_period(start, end)
        shared_expenses = self._shared_expenses_for_period(shared_service, start, end)
        summary = self._numeric_summary(DashboardService(self.session).summary(start, end))
        owed_to_me = sum((debt.remaining_amount for debt in debts if debt.direction == DebtDirection.HE_OWES_ME), Decimal("0.00"))
        i_owe = sum((debt.remaining_amount for debt in debts if debt.direction == DebtDirection.I_OWE_HIM), Decimal("0.00"))
        shared_summary = shared_service.summary(shared_expenses)
        summary.update(
            {
                "owed_to_me": owed_to_me,
                "i_owe": i_owe,
                "shared_receivable": shared_summary["receivable"],
                "shared_payable": shared_summary["payable"],
            }
        )
        return {
            "summary": summary,
            "transactions": TransactionService(self.session).list_transactions(start=start, end=end),
            "debts": debts,
            "shared_expenses": shared_expenses,
        }

    def _debts_for_period(self, start: date, end: date):
        rows = []
        for debt in DebtService(self.session).list_debts():
            created = debt.created_at.date() if debt.created_at else None
            payment_in_period = any(start <= payment.date <= end for payment in debt.payments)
            due_in_period = debt.due_date is not None and start <= debt.due_date <= end
            created_in_period = created is not None and start <= created <= end
            if created_in_period or payment_in_period or due_in_period:
                rows.append(debt)
        return rows

    def _numeric_summary(self, summary: dict[str, object]) -> dict[str, Decimal]:
        return {key: value for key, value in summary.items() if isinstance(value, Decimal)}

    def _generator(self, owner_name: str) -> tuple[ReportGenerator, str]:
        settings = SettingsService(self.session)
        return (
            ReportGenerator(
                settings.get("report_title_prefix", "Personal Ledger Pro"),
                settings.get("report_footer_text", "Administrative financial report"),
                settings.get("report_logo_path", str(APP_LOGO_PATH)),
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

    def export_preview_csv(self, output_path: Path, preview: dict[str, object]) -> Path:
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow([preview["title"], preview["owner"], preview["period"], preview["generated_at"]])
            for table in preview["tables"]:  # type: ignore[assignment]
                writer.writerow([])
                writer.writerow([table["title"]])
                writer.writerow(table["headers"])
                writer.writerows(table["rows"])
        return output_path

    def export_transactions_csv(self, output_path: Path, report_type: str | None = None, start: date | None = None, end: date | None = None, owner_name: str = "") -> Path:
        if report_type and start and end:
            preview = self.preview_report(report_type, start, end, owner_name)
            return self.export_preview_csv(output_path, preview)
        rows = TransactionService(self.session).list_transactions()
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Date", "Type", "Amount", "Currency", "Category", "Person", "Payment Method", "Note"])
            for tx in rows:
                payment_method = tx.payment_method_ref.name if tx.payment_method_ref else tx.payment_method or ""
                writer.writerow([tx.date, tx.type.value, tx.amount, tx.currency, tx.category.name if tx.category else "", tx.person.name if tx.person else "", payment_method, tx.note or ""])
        return output_path

    def _category_table(self, title: str, transactions: list) -> dict[str, object]:
        totals: dict[str, Decimal] = {}
        for tx in transactions:
            category = tx.category.name if tx.category else "Uncategorized"
            totals[category] = totals.get(category, Decimal("0.00")) + tx.amount
        return {"title": title, "headers": ["Category", "Total"], "rows": [[name, money(value)] for name, value in sorted(totals.items())]}

    def _transaction_preview_table(self, title: str, transactions: list) -> dict[str, object]:
        rows = []
        for tx in transactions:
            payment_method = tx.payment_method_ref.name if tx.payment_method_ref else tx.payment_method or ""
            rows.append([tx.date.isoformat(), tx.type.value, money(tx.amount, tx.currency), tx.category.name if tx.category else "", tx.person.name if tx.person else "", payment_method, tx.note or ""])
        return {"title": title, "headers": ["Date", "Type", "Amount", "Category", "Person", "Payment", "Note"], "rows": rows}

    def _debt_preview_table(self, title: str, debts: list) -> dict[str, object]:
        rows = []
        for debt in debts:
            paid = debt.original_amount - debt.remaining_amount
            rows.append([debt.person.name, debt.direction.value, money(debt.original_amount, debt.currency), money(paid, debt.currency), money(debt.remaining_amount, debt.currency), debt.status.value, debt.due_date.isoformat() if debt.due_date else "", debt.note or ""])
        return {"title": title, "headers": ["Person", "Direction", "Original", "Paid", "Remaining", "Status", "Due", "Note"], "rows": rows}

    def _shared_preview_table(self, title: str, expenses: list) -> dict[str, object]:
        rows = []
        for expense in expenses:
            participant_names = ", ".join(participant.person.name for participant in expense.participants)
            rows.append([expense.date.isoformat(), expense.title, money(expense.amount, expense.currency), expense.paid_by.name, participant_names, expense.note or ""])
        return {"title": title, "headers": ["Date", "Title", "Amount", "Paid by", "Participants", "Note"], "rows": rows}
