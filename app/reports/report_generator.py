from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Sequence

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.debt import Debt
from app.models.shared_expense import SharedExpense
from app.models.transaction import Transaction
from app.services.settlement_service import Settlement
from app.utils.money import money, to_decimal


BRAND = colors.HexColor("#111827")
INK = colors.HexColor("#111827")
MUTED = colors.HexColor("#6B7280")
BORDER = colors.HexColor("#D1D5DB")
PANEL = colors.HexColor("#F3F4F6")
PANEL_ALT = colors.HexColor("#F9FAFB")
INCOME = colors.HexColor("#15803D")
EXPENSE = colors.HexColor("#B91C1C")
INFO = colors.HexColor("#1D4ED8")
GOLD = colors.HexColor("#A16207")


@dataclass(frozen=True)
class ReportContext:
    title: str
    owner_name: str
    period: tuple[date, date]
    generated_at: datetime
    accent: colors.Color = INFO
    title_prefix: str = "Personal Ledger Pro"
    footer_text: str = "Administrative financial report"


class ReportGenerator:
    def __init__(
        self,
        title_prefix: str = "Personal Ledger Pro",
        footer_text: str = "Administrative financial report",
        logo_path: str = "",
    ):
        self.title_prefix = title_prefix or "Personal Ledger Pro"
        self.footer_text = footer_text or "Administrative financial report"
        self.logo_path = Path(logo_path) if logo_path else None

    def income_report(self, *, output_path: Path, owner_name: str, period: tuple[date, date], transactions: Sequence[Transaction]) -> Path:
        total = sum((tx.amount for tx in transactions), Decimal("0.00"))
        rows = [["Date", "Category", "Amount", "Method", "Note"]]
        for tx in transactions:
            rows.append([tx.date, tx.category.name if tx.category else "", money(tx.amount, tx.currency), self._payment_method_name(tx), tx.note or ""])
        story = self._base_story(
            self._context("Income Report", owner_name, period, INCOME),
            [("Total Income", money(total)), ("Entries", str(len(transactions))), ("Average", money(total / len(transactions)) if transactions else money(0))],
        )
        story += [
            self._section("Income Details"),
            self._table(rows, [2.5 * cm, 4.2 * cm, 3 * cm, 3 * cm, 5 * cm], numeric_cols={2}),
            self._total_bar("Total income", money(total)),
        ]
        return self._build(output_path, story)

    def expense_report(self, *, output_path: Path, owner_name: str, period: tuple[date, date], transactions: Sequence[Transaction]) -> Path:
        total = sum((tx.amount for tx in transactions), Decimal("0.00"))
        by_category: dict[str, Decimal] = {}
        rows = [["Date", "Category", "Amount", "Method", "Note"]]
        for tx in transactions:
            category = tx.category.name if tx.category else "Uncategorized"
            by_category[category] = by_category.get(category, Decimal("0.00")) + tx.amount
            rows.append([tx.date, category, money(tx.amount, tx.currency), self._payment_method_name(tx), tx.note or ""])
        subtotals = [["Category", "Subtotal"]] + [[name, money(value)] for name, value in sorted(by_category.items())]
        story = self._base_story(
            self._context("Expense Report", owner_name, period, EXPENSE),
            [("Total Expenses", money(total)), ("Entries", str(len(transactions))), ("Categories", str(len(by_category)))],
        )
        story += [
            self._section("Expense Subtotals"),
            self._table(subtotals, [10 * cm, 5 * cm], numeric_cols={1}),
            self._section("Expense Details"),
            self._table(rows, [2.5 * cm, 4.2 * cm, 3 * cm, 3 * cm, 5 * cm], numeric_cols={2}),
            self._total_bar("Total expenses", money(total)),
        ]
        return self._build(output_path, story)

    def debt_report(self, *, output_path: Path, owner_name: str, period: tuple[date, date], debts: Sequence[Debt]) -> Path:
        original = sum((debt.original_amount for debt in debts), Decimal("0.00"))
        remaining = sum((debt.remaining_amount for debt in debts), Decimal("0.00"))
        rows = [["Person", "Direction", "Original", "Remaining", "Status", "Due Date", "Note"]]
        for debt in debts:
            rows.append([debt.person.name, debt.direction.value, money(debt.original_amount), money(debt.remaining_amount), debt.status.value, debt.due_date or "", debt.note or ""])
        story = self._base_story(
            self._context("Debt Report", owner_name, period, GOLD),
            [("Original Total", money(original)), ("Remaining", money(remaining)), ("Closed", money(original - remaining))],
        )
        story += [
            self._section("Debt Register"),
            self._table(rows, [2.8 * cm, 3.1 * cm, 2.6 * cm, 2.8 * cm, 2.2 * cm, 2.3 * cm, 3 * cm], numeric_cols={2, 3}),
            self._total_bar("Remaining debt balance", money(remaining)),
        ]
        return self._build(output_path, story)

    def shared_living_report(
        self,
        *,
        output_path: Path,
        owner_name: str,
        period: tuple[date, date],
        expenses: Sequence[SharedExpense],
        balances: dict[str, Decimal],
        settlements: Sequence[Settlement],
    ) -> Path:
        total = sum((expense.amount for expense in expenses), Decimal("0.00"))
        expense_rows = [["Date", "Title", "Amount", "Paid By", "Participants"]]
        for expense in expenses:
            participant_names = ", ".join(participant.person.name for participant in expense.participants)
            expense_rows.append([expense.date, expense.title, money(expense.amount, expense.currency), expense.paid_by.name, participant_names])
        balance_rows = [["Person", "Balance"]] + [[name, money(value)] for name, value in sorted(balances.items())]
        settlement_rows = [["From", "To", "Amount"]] + [[row.from_person, row.to_person, money(row.amount)] for row in settlements]
        receivable = sum((amount for amount in balances.values() if amount > 0), Decimal("0.00"))
        payable = sum((-amount for amount in balances.values() if amount < 0), Decimal("0.00"))
        story = self._base_story(
            self._context("Shared Living Report", owner_name, period, INFO),
            [("Shared Expenses", money(total)), ("To Collect", money(receivable)), ("To Pay", money(payable))],
        )
        story += [
            self._section("Shared Expense Details"),
            self._table(expense_rows, [2.4 * cm, 4 * cm, 2.8 * cm, 3 * cm, 6 * cm], numeric_cols={2}),
            self._section("Member Balances"),
            self._table(balance_rows, [9 * cm, 5 * cm], numeric_cols={1}),
            self._section("Settlement Suggestions"),
            self._table(settlement_rows, [5 * cm, 5 * cm, 4 * cm], numeric_cols={2}),
            self._total_bar("Total shared expenses", money(total)),
        ]
        return self._build(output_path, story)

    def full_financial_report(
        self,
        *,
        output_path: Path,
        owner_name: str,
        period: tuple[date, date],
        summary: dict[str, Decimal],
        transactions: Iterable[Transaction],
        debts: Iterable[Debt],
        shared_expenses: Iterable[SharedExpense],
        settlements: Iterable[Settlement],
    ) -> Path:
        transactions = list(transactions)
        debts = list(debts)
        shared_expenses = list(shared_expenses)
        settlements = list(settlements)
        story = self._base_story(
            self._context("Full Financial Report", owner_name, period, INFO),
            [(key.replace("_", " ").title(), money(value)) for key, value in summary.items()],
        )
        story += [
            self._section("Financial Summary"),
            self._table([["Metric", "Amount"]] + [[key.replace("_", " ").title(), money(value)] for key, value in summary.items()], [10 * cm, 5 * cm], numeric_cols={1}),
            self._section("Transaction Register"),
            self._transaction_table(transactions),
            self._section("Debt Register"),
            self._debt_table(debts),
            self._section("Shared Living Expenses"),
            self._shared_table(shared_expenses),
            self._section("Settlement Suggestions"),
            self._table([["From", "To", "Amount"]] + [[row.from_person, row.to_person, money(row.amount)] for row in settlements], [5 * cm, 5 * cm, 4 * cm], numeric_cols={2}),
        ]
        return self._build(output_path, story)

    def _base_story(self, context: ReportContext, summary_cards: Sequence[tuple[str, str]]) -> list[object]:
        return [
            self._report_header(context),
            Spacer(1, 0.34 * cm),
            self._summary_cards(summary_cards[:6], context.accent),
            Spacer(1, 0.2 * cm),
        ]

    def _context(self, title: str, owner_name: str, period: tuple[date, date], accent: colors.Color) -> ReportContext:
        return ReportContext(title, owner_name, period, datetime.now(), accent, self.title_prefix, self.footer_text)

    def _report_header(self, context: ReportContext) -> object:
        period = f"{context.period[0].isoformat()} to {context.period[1].isoformat()}"
        generated = context.generated_at.strftime("%Y-%m-%d %H:%M")
        owner = context.owner_name or "Not specified"
        details = f"<b>Owner:</b> {owner} &nbsp;&nbsp; <b>Period:</b> {period} &nbsp;&nbsp; <b>Generated:</b> {generated}"
        title = Paragraph(context.title, self._styles()["headerTitle"])
        brand = Paragraph(context.title_prefix, self._styles()["headerBrand"])
        subtitle = Paragraph("Administrative financial document suitable for printing, archiving, and review.", self._styles()["headerSubtitle"])
        meta = Paragraph(details, self._styles()["headerMeta"])
        if self.logo_path and self.logo_path.exists():
            logo = Image(str(self.logo_path), width=1.55 * cm, height=1.55 * cm, kind="proportional")
        else:
            logo = Paragraph("PL", self._styles()["headerInitials"])
        table = Table(
            [[logo, brand], ["", title], ["", subtitle], ["", meta]],
            colWidths=[2.0 * cm, 14.5 * cm],
            hAlign="CENTER",
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), PANEL_ALT),
                    ("BOX", (0, 0), (-1, -1), 0.8, BORDER),
                    ("LINEBELOW", (0, -1), (-1, -1), 2.2, context.accent),
                    ("SPAN", (0, 0), (0, -1)),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (0, -1), "CENTER"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, 0), 11),
                    ("BOTTOMPADDING", (0, -1), (-1, -1), 11),
                    ("TOPPADDING", (0, 1), (-1, 2), 1),
                    ("BOTTOMPADDING", (0, 1), (-1, 2), 1),
                ]
            )
        )
        return table

    def _transaction_table(self, transactions: Sequence[Transaction]) -> Table:
        rows = [["Date", "Type", "Category", "Amount", "Person", "Note"]]
        for tx in transactions:
            rows.append([tx.date, tx.type.value, tx.category.name if tx.category else "", money(tx.amount, tx.currency), tx.person.name if tx.person else "", tx.note or ""])
        return self._table(rows, [2.2 * cm, 2.8 * cm, 3.3 * cm, 2.8 * cm, 2.7 * cm, 4.2 * cm], numeric_cols={3})

    def _payment_method_name(self, tx: Transaction) -> str:
        return tx.payment_method_ref.name if tx.payment_method_ref else tx.payment_method or ""

    def _debt_table(self, debts: Sequence[Debt]) -> Table:
        rows = [["Person", "Direction", "Original", "Remaining", "Status", "Due"]]
        for debt in debts:
            rows.append([debt.person.name, debt.direction.value, money(debt.original_amount), money(debt.remaining_amount), debt.status.value, debt.due_date or ""])
        return self._table(rows, [3 * cm, 3.6 * cm, 2.7 * cm, 2.8 * cm, 2.3 * cm, 2.5 * cm], numeric_cols={2, 3})

    def _shared_table(self, expenses: Sequence[SharedExpense]) -> Table:
        rows = [["Date", "Title", "Amount", "Paid By", "Participants"]]
        for expense in expenses:
            rows.append([expense.date, expense.title, money(expense.amount, expense.currency), expense.paid_by.name, ", ".join(p.person.name for p in expense.participants)])
        return self._table(rows, [2.3 * cm, 4 * cm, 2.8 * cm, 3 * cm, 5.8 * cm], numeric_cols={2})

    def _styles(self) -> dict[str, ParagraphStyle]:
        styles = getSampleStyleSheet()
        return {
            "brand": ParagraphStyle("Brand", parent=styles["Title"], fontSize=13, textColor=MUTED, alignment=TA_CENTER, spaceAfter=3),
            "title": ParagraphStyle("ReportTitle", parent=styles["Title"], fontSize=24, textColor=INK, alignment=TA_CENTER, spaceAfter=5),
            "subtitle": ParagraphStyle("Subtitle", parent=styles["BodyText"], fontSize=9, textColor=MUTED, alignment=TA_CENTER, spaceAfter=12),
            "headerBrand": ParagraphStyle("HeaderBrand", parent=styles["BodyText"], fontSize=10, leading=12, textColor=MUTED, alignment=TA_LEFT, spaceAfter=1),
            "headerTitle": ParagraphStyle("HeaderTitle", parent=styles["Title"], fontSize=22, leading=26, textColor=INK, alignment=TA_LEFT, spaceAfter=1),
            "headerSubtitle": ParagraphStyle("HeaderSubtitle", parent=styles["BodyText"], fontSize=8.5, leading=10.5, textColor=MUTED, alignment=TA_LEFT, spaceAfter=3),
            "headerMeta": ParagraphStyle("HeaderMeta", parent=styles["BodyText"], fontSize=7.8, leading=10, textColor=INK, alignment=TA_LEFT),
            "headerInitials": ParagraphStyle("HeaderInitials", parent=styles["Title"], fontSize=18, textColor=INFO, alignment=TA_CENTER),
            "section": ParagraphStyle("Section", parent=styles["Heading2"], fontSize=13, textColor=INK, spaceBefore=15, spaceAfter=7),
            "cell": ParagraphStyle("Cell", parent=styles["BodyText"], fontSize=7.6, leading=9.5, textColor=INK),
        }

    def _section(self, title: str) -> Paragraph:
        return Paragraph(title, self._styles()["section"])

    def _meta_table(self, context: ReportContext) -> Table:
        rows = [
            ["Owner", context.owner_name or "Not specified", "Generated", context.generated_at.strftime("%Y-%m-%d %H:%M")],
            ["Period", f"{context.period[0].isoformat()} to {context.period[1].isoformat()}", "Report", context.title],
        ]
        table = Table(rows, colWidths=[2.2 * cm, 6.4 * cm, 2.5 * cm, 5.3 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), PANEL),
                    ("TEXTCOLOR", (0, 0), (-1, -1), INK),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                    ("BOX", (0, 0), (-1, -1), 0.8, BORDER),
                    ("INNERGRID", (0, 0), (-1, -1), 0.35, BORDER),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ]
            )
        )
        return table

    def _summary_cards(self, cards: Sequence[tuple[str, str]], accent: colors.Color) -> Table:
        if not cards:
            cards = [("No summary", "0.00 EUR")]
        cells: list[list[object]] = []
        row: list[object] = []
        for label, value in cards:
            row.append(Paragraph(f"<font color='#6B7280' size='7'>{label}</font><br/><font color='#111827' size='13'><b>{value}</b></font>", self._styles()["cell"]))
            if len(row) == 3:
                cells.append(row)
                row = []
        if row:
            row += [""] * (3 - len(row))
            cells.append(row)
        table = Table(cells, colWidths=[5.45 * cm, 5.45 * cm, 5.45 * cm], hAlign="CENTER")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                    ("BOX", (0, 0), (-1, -1), 0.55, BORDER),
                    ("INNERGRID", (0, 0), (-1, -1), 0.35, BORDER),
                    ("LINEABOVE", (0, 0), (-1, 0), 2, accent),
                    ("LEFTPADDING", (0, 0), (-1, -1), 9),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                    ("TOPPADDING", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        return table

    def _table(self, rows: list[list[object]], widths: list[float], numeric_cols: set[int] | None = None) -> Table:
        if len(rows) == 1:
            rows.append(["No records available"] + [""] * (len(rows[0]) - 1))
        wrapped = [[self._wrap_cell(cell) for cell in row] for row in rows]
        table = Table(wrapped, colWidths=widths, repeatRows=1)
        commands = [
            ("BACKGROUND", (0, 0), (-1, 0), BRAND),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.6),
            ("GRID", (0, 0), (-1, -1), 0.35, BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PANEL_ALT]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
        for col in numeric_cols or set():
            commands.append(("ALIGN", (col, 1), (col, -1), "RIGHT"))
        table.setStyle(TableStyle(commands))
        return table

    def _wrap_cell(self, value: object) -> object:
        if isinstance(value, Paragraph):
            return value
        text = str(value)
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return Paragraph(escaped, self._styles()["cell"])

    def _total_bar(self, label: str, amount: str) -> Table:
        table = Table([[label, amount]], colWidths=[11.5 * cm, 5 * cm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), PANEL),
                    ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        return table

    def _build(self, output_path: Path, story: list[object]) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc = SimpleDocTemplate(str(output_path), pagesize=A4, rightMargin=1.35 * cm, leftMargin=1.35 * cm, topMargin=1.65 * cm, bottomMargin=1.35 * cm)
        doc.footer_text = self.footer_text  # type: ignore[attr-defined]
        doc.title_prefix = self.title_prefix  # type: ignore[attr-defined]
        doc.logo_path = str(self.logo_path) if self.logo_path and self.logo_path.exists() else ""  # type: ignore[attr-defined]
        doc.build(story, onFirstPage=self._footer, onLaterPages=self._footer)
        return output_path

    def _footer(self, canvas, doc) -> None:  # type: ignore[no-untyped-def]
        canvas.saveState()
        canvas.setFillColor(BRAND)
        canvas.rect(0, A4[1] - 0.72 * cm, A4[0], 0.72 * cm, stroke=0, fill=1)
        logo_path = getattr(doc, "logo_path", "")
        title_x = 1.35 * cm
        if logo_path:
            canvas.drawImage(logo_path, 1.35 * cm, A4[1] - 0.64 * cm, width=0.5 * cm, height=0.5 * cm, preserveAspectRatio=True, mask="auto")
            title_x = 2.02 * cm
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(title_x, A4[1] - 0.46 * cm, getattr(doc, "title_prefix", "Personal Ledger Pro"))
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.line(1.35 * cm, 1.03 * cm, A4[0] - 1.35 * cm, 1.03 * cm)
        canvas.drawString(1.35 * cm, 0.7 * cm, getattr(doc, "footer_text", "Administrative financial report"))
        canvas.drawRightString(A4[0] - 1.35 * cm, 0.7 * cm, f"Page {doc.page}")
        canvas.restoreState()
