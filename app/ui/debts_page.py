from __future__ import annotations

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QComboBox, QDateEdit, QDoubleSpinBox, QFormLayout, QHBoxLayout, QInputDialog, QLabel, QTableWidgetItem, QVBoxLayout, QWidget

from app.core.database import session_scope
from app.models.debt import DebtDirection
from app.services.debt_service import DebtService
from app.services.person_service import PersonService
from app.ui.helpers import qdate_to_date, show_error, spinbox_money
from app.ui.widgets import ModernTable, PrimaryButton, SecondaryButton, SectionCard
from app.utils.money import money, validate_money_input


class DebtsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(18)
        title = QLabel("Debts")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Track debts, partial payments, remaining balances, and status changes.")
        subtitle.setObjectName("pageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        form_card = SectionCard("New Debt", "Create a receivable or payable relationship")
        form = QFormLayout()
        form.setSpacing(12)
        self.person = QComboBox()
        self.direction = QComboBox()
        self.direction.addItems([DebtDirection.HE_OWES_ME.value, DebtDirection.I_OWE_HIM.value])
        self.direction.currentTextChanged.connect(self._reload_people)
        self.amount = QDoubleSpinBox()
        self.amount.setMaximum(1_000_000)
        self.amount.setDecimals(2)
        self.due = QDateEdit(QDate.currentDate())
        self.due.setCalendarPopup(True)
        form.addRow("Person", self.person)
        form.addRow("Direction", self.direction)
        form.addRow("Amount", self.amount)
        form.addRow("Due date", self.due)
        add = PrimaryButton("Add debt")
        add.clicked.connect(self.add_debt)
        pay = SecondaryButton("Register partial payment")
        pay.clicked.connect(self.pay_selected)
        quick_add = SecondaryButton("Quick add person")
        quick_add.clicked.connect(self._quick_add_person)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(add)
        buttons.addWidget(pay)
        buttons.addWidget(quick_add)
        form_card.layout.addLayout(form)
        form_card.layout.addLayout(buttons)
        debt_card = SectionCard("Debt Register", "Select a debt to view payment history")
        self.table = ModernTable(["ID", "Person", "Direction", "Original", "Remaining", "Status", "Due"])
        self.table.itemSelectionChanged.connect(self.refresh_payments)
        debt_card.layout.addWidget(self.table)
        payment_card = SectionCard("Payment History", "Recorded payments for the selected debt")
        self.payments = ModernTable(["Date", "Amount", "Note", "Created"])
        payment_card.layout.addWidget(self.payments)
        layout.addWidget(form_card)
        layout.addWidget(debt_card, 1)
        layout.addWidget(payment_card, 1)
        self.refresh()

    def refresh(self) -> None:
        with session_scope() as session:
            self.person.clear()
            for person in DebtService(session).people_for_direction(DebtDirection(self.direction.currentText())):
                self.person.addItem(person.name, person.id)
            debts = DebtService(session).list_debts()
            self.table.setRowCount(len(debts))
            for row, debt in enumerate(debts):
                values = [debt.id, debt.person.name, debt.direction.value, money(debt.original_amount), money(debt.remaining_amount), debt.status.value, debt.due_date or ""]
                for col, value in enumerate(values):
                    item = QTableWidgetItem(str(value))
                    item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                    self.table.setItem(row, col, item)
        self.refresh_payments()

    def refresh_payments(self) -> None:
        row = self.table.currentRow()
        if row < 0 or not self.table.item(row, 0):
            self.payments.setRowCount(0)
            return
        debt_id = int(self.table.item(row, 0).text())
        with session_scope() as session:
            payments = DebtService(session).payment_history(debt_id)
            self.payments.setRowCount(len(payments))
            for payment_row, payment in enumerate(payments):
                values = [payment.date, money(payment.amount), payment.note or "", payment.created_at.strftime("%Y-%m-%d %H:%M")]
                for col, value in enumerate(values):
                    item = QTableWidgetItem(str(value))
                    item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                    self.payments.setItem(payment_row, col, item)

    def add_debt(self) -> None:
        try:
            with session_scope() as session:
                DebtService(session).add_debt(
                    person_id=self.person.currentData(),
                    direction=DebtDirection(self.direction.currentText()),
                    amount=spinbox_money(self.amount.value()),
                    due_date=qdate_to_date(self.due.date()),
                )
            self.amount.setValue(0)
            self.refresh()
        except Exception as exc:
            show_error(self, "Debt not saved", exc)

    def _reload_people(self) -> None:
        with session_scope() as session:
            self.person.clear()
            for person in DebtService(session).people_for_direction(DebtDirection(self.direction.currentText())):
                self.person.addItem(person.name, person.id)

    def _quick_add_person(self) -> None:
        name, ok = QInputDialog.getText(self, "Quick add person", "Name")
        if not ok or not name.strip():
            return
        direction = DebtDirection(self.direction.currentText())
        try:
            with session_scope() as session:
                PersonService(session).add_or_update_person(
                    name=name,
                    is_creditor=direction == DebtDirection.I_OWE_HIM,
                    is_debtor=direction == DebtDirection.HE_OWES_ME,
                )
            self._reload_people()
        except Exception as exc:
            show_error(self, "Person not saved", exc)

    def pay_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            show_error(self, "No debt selected", "Select a debt before registering a payment.")
            return
        debt_id = int(self.table.item(row, 0).text())
        remaining_text = self.table.item(row, 4).text().split()[0].replace(",", "")
        default_value = "1.00" if validate_money_input(remaining_text) > validate_money_input("1.00") else remaining_text
        value, ok = QInputDialog.getText(self, "Register payment", "Amount", text=default_value)
        if not ok:
            return
        try:
            with session_scope() as session:
                DebtService(session).register_payment(debt_id, validate_money_input(value), qdate_to_date(QDate.currentDate()))
            self.refresh()
        except Exception as exc:
            show_error(self, "Payment not registered", exc)
