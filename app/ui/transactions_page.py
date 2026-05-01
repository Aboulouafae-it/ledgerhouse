from __future__ import annotations

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QComboBox, QDateEdit, QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMenu, QMessageBox, QTableWidgetItem, QVBoxLayout, QWidget

from app.core.database import session_scope
from app.models.transaction import TransactionType
from app.services.transaction_service import TransactionService
from app.ui.events import events
from app.ui.helpers import qdate_to_date, show_error, spinbox_money
from app.ui.widgets import FormDialog, ModernTable, PrimaryButton, SecondaryButton, SectionCard
from app.utils.money import money


class TransactionsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(18)
        title = QLabel("Transactions")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Capture income, expenses, savings, debt activity, and shared costs.")
        subtitle.setObjectName("pageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        form_card = SectionCard("New Transaction", "Record a money movement in the local ledger")
        form = QFormLayout()
        form.setSpacing(12)
        self.date = QDateEdit(QDate.currentDate())
        self.date.setCalendarPopup(True)
        self.type = QComboBox()
        self.type.addItems([t.value for t in TransactionType])
        self.amount = QDoubleSpinBox()
        self.amount.setMaximum(1_000_000)
        self.amount.setDecimals(2)
        self.category = QComboBox()
        self.person = QComboBox()
        self.payment = QComboBox()
        self.note = QLineEdit()
        for label, widget in [("Date", self.date), ("Type", self.type), ("Amount", self.amount), ("Category", self.category), ("Person", self.person), ("Payment", self.payment), ("Note", self.note)]:
            form.addRow(label, widget)
        add = PrimaryButton("Add transaction")
        add.clicked.connect(self.add_transaction)
        refresh = SecondaryButton("Refresh")
        refresh.clicked.connect(self.refresh)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(add)
        buttons.addWidget(refresh)
        form_card.layout.addLayout(form)
        form_card.layout.addLayout(buttons)
        table_card = SectionCard("Ledger", "Most recent transactions first")
        self.table = ModernTable(["ID", "Date", "Type", "Amount", "Category", "Person", "Payment", "Note"])
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(7, QHeaderView.Stretch)
        self.table.doubleClicked.connect(self._edit_selected_transaction)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.keyPressEvent = self._table_key_press
        table_card.layout.addWidget(self.table)
        layout.addWidget(form_card)
        layout.addWidget(table_card, 1)
        self.refresh()
        self.type.currentTextChanged.connect(self._reload_categories)
        self.type.currentTextChanged.connect(self._reload_people)
        events.people_changed.connect(self.refresh)
        events.categories_changed.connect(self.refresh)
        events.payment_methods_changed.connect(self.refresh)
        events.settings_changed.connect(self.refresh)

    def refresh(self) -> None:
        with session_scope() as session:
            service = TransactionService(session)
            self._populate_categories(service)
            self._populate_people(service)
            self.payment.clear()
            self.payment.addItem("None", None)
            for method in service.payment_methods():
                self.payment.addItem(method.name, method.id)
            rows = service.list_transactions()
            self.table.setRowCount(len(rows))
            for row, tx in enumerate(rows):
                values = [tx.id, tx.date, tx.type.value, money(tx.amount, tx.currency), tx.category.name if tx.category else "", tx.person.name if tx.person else "", tx.payment_method_ref.name if tx.payment_method_ref else tx.payment_method or "", tx.note or ""]
                for col, value in enumerate(values):
                    item = QTableWidgetItem(str(value))
                    item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                    self.table.setItem(row, col, item)

    def add_transaction(self) -> None:
        try:
            with session_scope() as session:
                service = TransactionService(session)
                service.add_transaction(
                    type_=TransactionType(self.type.currentText()),
                    amount=spinbox_money(self.amount.value()),
                    date_=qdate_to_date(self.date.date()),
                    category_id=self.category.currentData(),
                    person_id=self.person.currentData(),
                    payment_method=self.payment.currentText() if self.payment.currentData() else "",
                    payment_method_id=self.payment.currentData(),
                    note=self.note.text().strip(),
                    is_shared=self.type.currentText() == TransactionType.SHARED_EXPENSE.value,
                )
            self.amount.setValue(0)
            self.note.clear()
            self.refresh()
            events.transactions_changed.emit()
            QMessageBox.information(self, "Transactions", "Transaction added.")
        except Exception as exc:
            show_error(self, "Transaction not saved", exc)

    def edit_transaction(self, transaction_id: int) -> None:
        try:
            with session_scope() as session:
                service = TransactionService(session)
                tx = service.get_transaction(transaction_id)
                warning = service.linked_warning(transaction_id)
                data = {
                    "type": tx.type,
                    "amount": str(tx.amount),
                    "date": tx.date,
                    "category_id": tx.category_id,
                    "person_id": tx.person_id,
                    "payment_method_id": tx.payment_method_id,
                    "note": tx.note or "",
                    "warning": warning,
                }
        except Exception as exc:
            show_error(self, "Transaction not loaded", exc)
            return
        if data["warning"]:
            QMessageBox.warning(self, "Linked transaction", data["warning"])
        dialog = FormDialog("Edit transaction", self)
        form = QFormLayout()
        date_edit = QDateEdit(QDate(data["date"].year, data["date"].month, data["date"].day))
        date_edit.setCalendarPopup(True)
        type_combo = QComboBox()
        type_combo.addItems([t.value for t in TransactionType])
        type_combo.setCurrentText(data["type"].value)
        amount = QLineEdit(data["amount"])
        category = QComboBox()
        person = QComboBox()
        payment = QComboBox()
        note = QLineEdit(data["note"])

        def populate_categories() -> None:
            with session_scope() as session:
                category.clear()
                category.addItem("None", None)
                for cat in TransactionService(session).categories_for_transaction_type(TransactionType(type_combo.currentText())):
                    category.addItem(cat.name, cat.id)
                category.setCurrentIndex(max(0, category.findData(data["category_id"])))

        def populate_people() -> None:
            with session_scope() as session:
                person.clear()
                person.addItem("None", None)
                for item in TransactionService(session).people_for_transaction_type(TransactionType(type_combo.currentText())):
                    person.addItem(item.name, item.id)
                person.setCurrentIndex(max(0, person.findData(data["person_id"])))

        with session_scope() as session:
            service = TransactionService(session)
            populate_people()
            payment.addItem("None", None)
            for item in service.payment_methods():
                payment.addItem(item.name, item.id)
            payment.setCurrentIndex(max(0, payment.findData(data["payment_method_id"])))
        populate_categories()
        type_combo.currentTextChanged.connect(populate_categories)
        type_combo.currentTextChanged.connect(populate_people)
        for label, widget in [("Date", date_edit), ("Type", type_combo), ("Amount", amount), ("Category", category), ("Person", person), ("Payment", payment), ("Note", note)]:
            form.addRow(label, widget)
        dialog.content.addLayout(form)
        save = PrimaryButton("Save")
        cancel = SecondaryButton("Cancel")
        save.clicked.connect(dialog.accept)
        cancel.clicked.connect(dialog.reject)
        dialog.actions.addWidget(cancel)
        dialog.actions.addWidget(save)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            with session_scope() as session:
                service = TransactionService(session)
                service.update_transaction(
                    transaction_id,
                    type_=TransactionType(type_combo.currentText()),
                    amount=amount.text().strip(),
                    date_=qdate_to_date(date_edit.date()),
                    category_id=category.currentData(),
                    person_id=person.currentData(),
                    payment_method=payment.currentText() if payment.currentData() else "",
                    payment_method_id=payment.currentData(),
                    note=note.text().strip(),
                )
            self.refresh()
            events.transactions_changed.emit()
            QMessageBox.information(self, "Transactions", "Transaction updated.")
        except Exception as exc:
            show_error(self, "Transaction not updated", exc)

    def duplicate_transaction(self, transaction_id: int) -> None:
        try:
            with session_scope() as session:
                TransactionService(session).duplicate_transaction(transaction_id)
            self.refresh()
            events.transactions_changed.emit()
            QMessageBox.information(self, "Transactions", "Transaction duplicated with today's date.")
        except Exception as exc:
            show_error(self, "Transaction not duplicated", exc)

    def view_transaction_details(self, transaction_id: int) -> None:
        try:
            with session_scope() as session:
                tx = TransactionService(session).get_transaction(transaction_id)
                data = [
                    ("ID", tx.id),
                    ("Date", tx.date.isoformat()),
                    ("Type", tx.type.value),
                    ("Amount", money(tx.amount, tx.currency)),
                    ("Category", tx.category.name if tx.category else ""),
                    ("Person", tx.person.name if tx.person else ""),
                    ("Payment method", tx.payment_method_ref.name if tx.payment_method_ref else tx.payment_method or ""),
                    ("Note", tx.note or ""),
                    ("Created at", tx.created_at),
                    ("Updated at", tx.updated_at),
                    ("Reference type", tx.reference_type or ""),
                    ("Reference ID", tx.reference_id or ""),
                ]
        except Exception as exc:
            show_error(self, "Transaction details not loaded", exc)
            return
        dialog = FormDialog("Transaction details", self)
        form = QFormLayout()
        for label, value in data:
            field = QLineEdit(str(value))
            field.setReadOnly(True)
            form.addRow(label, field)
        dialog.content.addLayout(form)
        close = PrimaryButton("Close")
        close.clicked.connect(dialog.accept)
        dialog.actions.addWidget(close)
        dialog.exec()

    def deactivate_transaction(self, transaction_id: int) -> None:
        try:
            with session_scope() as session:
                warning = TransactionService(session).linked_warning(transaction_id)
            if warning:
                QMessageBox.warning(self, "Linked transaction", warning)
                return
            if QMessageBox.question(self, "Deactivate transaction", "Deactivate this transaction? Dashboard and reports will ignore it.") != QMessageBox.Yes:
                return
            with session_scope() as session:
                TransactionService(session).deactivate_transaction(transaction_id)
            self.refresh()
            events.transactions_changed.emit()
            QMessageBox.information(self, "Transactions", "Transaction deactivated.")
        except Exception as exc:
            show_error(self, "Transaction not deactivated", exc)

    def _reload_categories(self) -> None:
        with session_scope() as session:
            self._populate_categories(TransactionService(session))

    def _reload_people(self) -> None:
        with session_scope() as session:
            self._populate_people(TransactionService(session))

    def _populate_categories(self, service: TransactionService) -> None:
        current_type = TransactionType(self.type.currentText())
        self.category.clear()
        self.category.addItem("None", None)
        for cat in service.categories_for_transaction_type(current_type):
            self.category.addItem(cat.name, cat.id)

    def _populate_people(self, service: TransactionService) -> None:
        self.person.clear()
        self.person.addItem("None", None)
        for person in service.people_for_transaction_type(TransactionType(self.type.currentText())):
            self.person.addItem(person.name, person.id)

    def _show_context_menu(self, position) -> None:
        row = self.table.rowAt(position.y())
        if row < 0:
            return
        self.table.selectRow(row)
        transaction_id = self._selected_transaction_id()
        if transaction_id is None:
            return
        menu = QMenu(self)
        edit = menu.addAction("Edit transaction")
        duplicate = menu.addAction("Duplicate transaction")
        deactivate = menu.addAction("Deactivate transaction")
        details = menu.addAction("View details")
        selected = menu.exec(self.table.viewport().mapToGlobal(position))
        if selected == edit:
            self.edit_transaction(transaction_id)
        elif selected == duplicate:
            self.duplicate_transaction(transaction_id)
        elif selected == deactivate:
            self.deactivate_transaction(transaction_id)
        elif selected == details:
            self.view_transaction_details(transaction_id)

    def _selected_transaction_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return int(item.text()) if item else None

    def _edit_selected_transaction(self, _index=None) -> None:
        transaction_id = self._selected_transaction_id()
        if transaction_id is not None:
            self.edit_transaction(transaction_id)

    def _table_key_press(self, event) -> None:
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._edit_selected_transaction()
            return
        if event.key() == Qt.Key_Delete:
            transaction_id = self._selected_transaction_id()
            if transaction_id is not None:
                self.deactivate_transaction(transaction_id)
            return
        ModernTable.keyPressEvent(self.table, event)
