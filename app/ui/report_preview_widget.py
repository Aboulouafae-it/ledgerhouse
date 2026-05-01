from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QScrollArea, QTableWidgetItem, QVBoxLayout, QWidget

from app.ui.widgets import EmptyState, ModernTable, SectionCard, StatCard


class ReportPreviewWidget(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(0)
        self.empty = EmptyState("Report preview", "Choose a report period and press Preview report.")
        self.root.addWidget(self.empty, 1)

    def show_preview(self, preview: dict[str, object]) -> None:
        self._clear()
        if preview.get("is_empty"):
            self.root.addWidget(EmptyState("No report data found for the selected period.", "Try a wider date range or a different report type."), 1)
            return

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        body = SectionCard(str(preview["title"]), "")
        meta = QLabel(f"Owner: {preview['owner']}    Period: {preview['period']}    Generated: {preview['generated_at']}")
        meta.setObjectName("pageSubtitle")
        body.layout.addWidget(meta)

        summary = QGridLayout()
        summary.setSpacing(10)
        for index, (label, value) in enumerate(preview.get("summary", [])):
            summary.addWidget(StatCard(str(label), str(value)), index // 4, index % 4)
        body.layout.addLayout(summary)

        for table in preview.get("tables", []):
            title = QLabel(str(table["title"]))
            title.setObjectName("sectionTitle")
            body.layout.addWidget(title)
            grid = ModernTable([str(header) for header in table["headers"]])
            rows = table["rows"]
            grid.setRowCount(len(rows))
            for row_index, row_values in enumerate(rows):
                for col_index, value in enumerate(row_values):
                    item = QTableWidgetItem(str(value))
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    grid.setItem(row_index, col_index, item)
            grid.resizeColumnsToContents()
            grid.setMinimumHeight(min(280, max(120, 46 + len(rows) * 42)))
            body.layout.addWidget(grid)
        scroll.setWidget(body)
        self.root.addWidget(scroll, 1)

    def _clear(self) -> None:
        while self.root.count():
            item = self.root.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
