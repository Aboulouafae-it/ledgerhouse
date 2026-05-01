from __future__ import annotations

from datetime import date
from pathlib import Path

from PySide6.QtWidgets import QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from app.core.database import session_scope
from app.services.report_service import ReportService, ReportType
from app.services.settings_service import SettingsService
from app.ui.events import events
from app.ui.helpers import show_error
from app.ui.report_preview_widget import ReportPreviewWidget
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
        self._has_preview = False
        self._last_preview: dict[str, object] | None = None
        self._last_preview_signature: tuple[str, str, str, str] | None = None
        form = QFormLayout()
        form.setSpacing(12)
        self.start_date = QLineEdit(date.today().replace(day=1).isoformat())
        self.end_date = QLineEdit(date.today().isoformat())
        form.addRow("Owner", self.owner)
        form.addRow("Report type", self.report_type)
        form.addRow("Start YYYY-MM-DD", self.start_date)
        form.addRow("End YYYY-MM-DD", self.end_date)
        preview = SecondaryButton("Preview report")
        preview.clicked.connect(self.preview_report)
        pdf = PrimaryButton("Generate PDF report")
        pdf.clicked.connect(self.generate_pdf)
        csv = SecondaryButton("Export transactions CSV")
        csv.clicked.connect(self.export_csv)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(preview)
        buttons.addWidget(pdf)
        buttons.addWidget(csv)
        report_card.layout.addLayout(form)
        report_card.layout.addLayout(buttons)
        report_card.layout.addWidget(self.status)
        layout.addWidget(report_card)
        self.preview = ReportPreviewWidget()
        layout.addWidget(self.preview, 1)
        self.report_type.currentTextChanged.connect(self._preview_if_ready)
        self.owner.editingFinished.connect(self._preview_if_ready)
        self.start_date.editingFinished.connect(self._preview_if_ready)
        self.end_date.editingFinished.connect(self._preview_if_ready)
        events.settings_changed.connect(self.refresh)
        events.transactions_changed.connect(self.refresh)
        events.debts_changed.connect(self.refresh)
        events.shared_living_changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        with session_scope() as session:
            self.owner.setText(SettingsService(session).get("owner_name", ""))
        self._preview_if_ready()

    def preview_report(self) -> None:
        try:
            start, end = self._validated_period()
            with session_scope() as session:
                preview = ReportService(session).preview_report(self.report_type.currentText(), start, end, self.owner.text().strip())
            self.preview.show_preview(preview)
            self._cache_preview(preview, start, end)
            self._has_preview = True
            self.status.setText("Preview ready.")
        except Exception as exc:
            show_error(self, "Report preview not loaded", exc)

    def _preview_if_ready(self) -> None:
        if self._has_preview:
            self.preview_report()

    def generate_pdf(self) -> None:
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Save PDF report", "full_financial_report.pdf", "PDF files (*.pdf)")
            if not path:
                return
            start, end = self._validated_period()
            with session_scope() as session:
                generated_path, preview = ReportService(session).generate_report_with_preview(self.report_type.currentText(), Path(path), start, end, self.owner.text().strip())
            self.preview.show_preview(preview)
            self._cache_preview(preview, start, end)
            self._has_preview = True
            self.status.setText(f"Generated {generated_path}")
        except Exception as exc:
            show_error(self, "Report not generated", exc)

    def export_csv(self) -> None:
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "transactions.csv", "CSV files (*.csv)")
            if not path:
                return
            start, end = self._validated_period()
            with session_scope() as session:
                service = ReportService(session)
                preview = self._last_preview if self._preview_signature(start, end) == self._last_preview_signature else service.preview_report(self.report_type.currentText(), start, end, self.owner.text().strip())
                service.export_preview_csv(Path(path), preview)
            self.preview.show_preview(preview)
            self._cache_preview(preview, start, end)
            self._has_preview = True
            self.status.setText(f"Exported {path}")
        except Exception as exc:
            show_error(self, "CSV not exported", exc)

    def _validated_period(self) -> tuple[date, date]:
        start_text = self.start_date.text().strip()
        end_text = self.end_date.text().strip()
        if not start_text:
            raise ValueError("Start date is required.")
        if not end_text:
            raise ValueError("End date is required.")
        start = date.fromisoformat(start_text)
        end = date.fromisoformat(end_text)
        if start > end:
            raise ValueError("Start date must not be after end date.")
        return start, end

    def _preview_signature(self, start: date, end: date) -> tuple[str, str, str, str]:
        return (self.report_type.currentText(), start.isoformat(), end.isoformat(), self.owner.text().strip())

    def _cache_preview(self, preview: dict[str, object], start: date, end: date) -> None:
        self._last_preview = preview
        self._last_preview_signature = self._preview_signature(start, end)
