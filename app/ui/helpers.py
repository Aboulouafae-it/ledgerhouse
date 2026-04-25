from __future__ import annotations

from datetime import date
from decimal import Decimal

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QMessageBox, QTableWidget, QTableWidgetItem

from app.utils.money import to_decimal


def qdate_to_date(value: QDate) -> date:
    return date(value.year(), value.month(), value.day())


def spinbox_money(value: object) -> Decimal:
    return to_decimal(f"{value:.2f}")


def show_error(parent, title: str, error: Exception | str) -> None:  # type: ignore[no-untyped-def]
    QMessageBox.warning(parent, title, str(error))


def readonly_item(value: object) -> QTableWidgetItem:
    item = QTableWidgetItem(str(value))
    item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # type: ignore[name-defined]
    return item
