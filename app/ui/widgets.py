from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from app.ui.theme import Theme


class PrimaryButton(QPushButton):
    def __init__(self, text: str, parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setObjectName("primaryButton")
        self.setCursor(Qt.PointingHandCursor)


class DangerButton(QPushButton):
    def __init__(self, text: str, parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setObjectName("dangerButton")
        self.setCursor(Qt.PointingHandCursor)


class SecondaryButton(QPushButton):
    def __init__(self, text: str, parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setObjectName("secondaryButton")
        self.setCursor(Qt.PointingHandCursor)


class StatCard(QFrame):
    def __init__(self, title: str, value: str, accent: str = Theme.INFO, caption: str | None = None):
        super().__init__()
        self.setObjectName("statCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(7)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("statTitle")
        self.value_label = QLabel(value)
        self.value_label.setObjectName("statValue")
        self.value_label.setProperty("accent", accent)
        self.value_label.setStyleSheet(f"color: {accent};")
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        if caption:
            caption_label = QLabel(caption)
            caption_label.setObjectName("statCaption")
            layout.addWidget(caption_label)


MetricCard = StatCard


class SectionCard(QFrame):
    def __init__(self, title: str | None = None, subtitle: str | None = None):
        super().__init__()
        self.setObjectName("sectionCard")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(18, 18, 18, 18)
        self.layout.setSpacing(14)
        if title:
            header = QVBoxLayout()
            header.setSpacing(3)
            title_label = QLabel(title)
            title_label.setObjectName("sectionTitle")
            header.addWidget(title_label)
            if subtitle:
                subtitle_label = QLabel(subtitle)
                subtitle_label.setObjectName("sectionSubtitle")
                header.addWidget(subtitle_label)
            self.layout.addLayout(header)


class ModernTable(QTableWidget):
    def __init__(self, columns: list[str], parent: QWidget | None = None):
        super().__init__(0, len(columns), parent)
        self.setObjectName("modernTable")
        self.setHorizontalHeaderLabels(columns)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setDefaultSectionSize(42)

    def set_readonly_rows(self, rows: list[list[object]]) -> None:
        self.setRowCount(len(rows))
        for row_index, values in enumerate(rows):
            for col_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.setItem(row_index, col_index, item)


class EmptyState(QFrame):
    def __init__(self, title: str, message: str = ""):
        super().__init__()
        self.setObjectName("emptyState")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignCenter)
        title_label = QLabel(title)
        title_label.setObjectName("emptyTitle")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        if message:
            message_label = QLabel(message)
            message_label.setObjectName("emptyMessage")
            message_label.setAlignment(Qt.AlignCenter)
            message_label.setWordWrap(True)
            layout.addWidget(message_label)


class FormDialog(QDialog):
    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("formDialog")
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(460, 320)
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(22, 22, 22, 22)
        self.root_layout.setSpacing(16)
        heading = QLabel(title)
        heading.setObjectName("dialogTitle")
        self.root_layout.addWidget(heading)
        self.content = QVBoxLayout()
        self.content.setSpacing(12)
        self.root_layout.addLayout(self.content, 1)
        self.actions = QHBoxLayout()
        self.actions.addStretch(1)
        self.root_layout.addLayout(self.actions)
