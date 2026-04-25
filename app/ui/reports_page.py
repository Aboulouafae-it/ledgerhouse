from __future__ import annotations

from datetime import date
from pathlib import Path

from PySide6.QtWidgets import QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from app.core.database import session_scope
from app.services.report_service import ReportService, ReportType
from app.ui.helpers import show_error
from app.ui.widgets import PrimaryButton, SecondaryButton, SectionCard


class ReportsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(18)
        title = QLabel("Reports")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Generate administrative PDF reports and CSV exports.")
        subtitle.setObjectName("pageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        report_card = SectionCard("Report Generator", "Choose a reporting period and export format")
        self.status = QLabel("")
        self.status.setObjectName("pageSubtitle")
        self.owner = QLineEdit()
        self.owner.setPlaceholderText("Owner name")
        self.report_type = QComboBox()
        self.report_type.addItems([ReportType.FULL, ReportType.INCOME, ReportType.EXPENSE, ReportType.DEBT, ReportType.SHARED])
        form = QFormLayout()
        form.setSpacing(12)
        self.start_date = QLineEdit(date.today().replace(day=1).isoformat())
        self.end_date = QLineEdit(date.today().isoformat())
        form.addRow("Owner", self.owner)
        form.addRow("Report type", self.report_type)
        form.addRow("Start YYYY-MM-DD", self.start_date)
        form.addRow("End YYYY-MM-DD", self.end_date)
        pdf = PrimaryButton("Generate PDF report")
        pdf.clicked.connect(self.generate_pdf)
        csv = SecondaryButton("Export transactions CSV")
        csv.clicked.connect(self.export_csv)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(pdf)
        buttons.addWidget(csv)
        report_card.layout.addLayout(form)
        report_card.layout.addLayout(buttons)
        report_card.layout.addWidget(self.status)
        layout.addWidget(report_card)
        layout.addStretch(1)

    def generate_pdf(self) -> None:
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Save PDF report", "full_financial_report.pdf", "PDF files (*.pdf)")
            if not path:
                return
            start = date.fromisoformat(self.start_date.text().strip())
            end = date.fromisoformat(self.end_date.text().strip())
            if start > end:
                raise ValueError("Start date must be before end date.")
            with session_scope() as session:
                ReportService(session).generate_report(self.report_type.currentText(), Path(path), start, end, self.owner.text().strip())
            self.status.setText(f"Generated {path}")
        except Exception as exc:
            show_error(self, "Report not generated", exc)

    def export_csv(self) -> None:
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "transactions.csv", "CSV files (*.csv)")
            if not path:
                return
            with session_scope() as session:
                ReportService(session).export_transactions_csv(Path(path))
            self.status.setText(f"Exported {path}")
        except Exception as exc:
            show_error(self, "CSV not exported", exc)
