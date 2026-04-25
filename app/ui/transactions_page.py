from __future__ import annotations

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QComboBox, QDateEdit, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QTableWidgetItem, QVBoxLayout, QWidget

from app.core.database import session_scope
from app.models.transaction import TransactionType
from app.services.transaction_service import TransactionService
from app.ui.helpers import qdate_to_date, show_error, spinbox_money
from app.ui.widgets import ModernTable, PrimaryButton, SecondaryButton, SectionCard
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
        self.table = ModernTable(["ID", "Date", "Type", "Amount", "Category", "Person", "Note"])
        table_card.layout.addWidget(self.table)
        layout.addWidget(form_card)
        layout.addWidget(table_card, 1)
        self.refresh()
        self.type.currentTextChanged.connect(self._reload_categories)

    def refresh(self) -> None:
        with session_scope() as session:
            service = TransactionService(session)
            self._populate_categories(service)
            self.person.clear()
            self.person.addItem("None", None)
            for person in service.people():
                self.person.addItem(person.name, person.id)
            self.payment.clear()
            self.payment.addItem("None", None)
            for method in service.payment_methods():
                self.payment.addItem(method.name, method.id)
            rows = service.list_transactions()
            self.table.setRowCount(len(rows))
            for row, tx in enumerate(rows):
                values = [tx.id, tx.date, tx.type.value, money(tx.amount, tx.currency), tx.category.name if tx.category else "", tx.person.name if tx.person else "", tx.note or ""]
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
        except Exception as exc:
            show_error(self, "Transaction not saved", exc)

    def _reload_categories(self) -> None:
        with session_scope() as session:
            self._populate_categories(TransactionService(session))

    def _populate_categories(self, service: TransactionService) -> None:
        current_type = TransactionType(self.type.currentText())
        self.category.clear()
        self.category.addItem("None", None)
        for cat in service.categories_for_transaction_type(current_type):
            self.category.addItem(cat.name, cat.id)
