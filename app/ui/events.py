from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class AppEvents(QObject):
    settings_changed = Signal()
    people_changed = Signal()
    categories_changed = Signal()
    payment_methods_changed = Signal()
    transactions_changed = Signal()
    debts_changed = Signal()
    shared_living_changed = Signal()


events = AppEvents()
