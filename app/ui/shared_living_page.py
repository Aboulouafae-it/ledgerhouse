from __future__ import annotations

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QDateEdit, QDoubleSpinBox, QFormLayout, QGroupBox, QLabel, QLineEdit, QTableWidgetItem, QVBoxLayout, QWidget

from app.core.database import session_scope
from app.services.shared_living_service import SharedLivingService
from app.ui.helpers import qdate_to_date, show_error, spinbox_money
from app.ui.widgets import ModernTable, PrimaryButton, SectionCard
from app.utils.money import money


class SharedLivingPage(QWidget):
    def __init__(self):
        super().__init__()
        self.member_checks: list[QCheckBox] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(18)
        title = QLabel("Shared Living")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Split household expenses and generate settlement suggestions.")
        subtitle.setObjectName("pageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        form_card = SectionCard("New Shared Expense", "Equal split support with optimized settlements")
        form = QFormLayout()
        form.setSpacing(12)
        self.title = QLineEdit()
        self.amount = QDoubleSpinBox()
        self.amount.setMaximum(1_000_000)
        self.amount.setDecimals(2)
        self.payer = QComboBox()
        self.date = QDateEdit(QDate.currentDate())
        self.date.setCalendarPopup(True)
        form.addRow("Title", self.title)
        form.addRow("Amount", self.amount)
        form.addRow("Paid by", self.payer)
        form.addRow("Date", self.date)
        members_box = QGroupBox("Participants")
        self.members_layout = QVBoxLayout(members_box)
        add = PrimaryButton("Add equal split expense")
        add.clicked.connect(self.add_expense)
        form_card.layout.addLayout(form)
        form_card.layout.addWidget(members_box)
        form_card.layout.addWidget(add)
        expenses_card = SectionCard("Shared Expenses", "Household costs paid by members")
        self.expenses = ModernTable(["Date", "Title", "Amount", "Paid By", "Participants"])
        expenses_card.layout.addWidget(self.expenses)
        settlements_card = SectionCard("Settlement Suggestions", "Minimum practical payments between members")
        self.settlements = ModernTable(["From", "To", "Amount"])
        settlements_card.layout.addWidget(self.settlements)
        layout.addWidget(form_card)
        layout.addWidget(expenses_card, 1)
        layout.addWidget(settlements_card, 1)
        self.refresh()

    def refresh(self) -> None:
        with session_scope() as session:
            service = SharedLivingService(session)
            members = service.house_members()
            self.payer.clear()
            for person in members:
                self.payer.addItem(person.name, person.id)
            member_ids = {person.id for person in members}
            for person in service.active_people():
                if person.id not in member_ids:
                    self.payer.addItem(f"{person.name} (other)", person.id)
            while self.members_layout.count():
                item = self.members_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.member_checks = []
            for person in members:
                check = QCheckBox(person.name)
                check.setProperty("person_id", person.id)
                check.setChecked(True)
                self.member_checks.append(check)
                self.members_layout.addWidget(check)
            expenses = service.list_expenses()
            self.expenses.setRowCount(len(expenses))
            for row, expense in enumerate(expenses):
                participant_names = ", ".join(p.person.name for p in expense.participants)
                values = [expense.date, expense.title, money(expense.amount), expense.paid_by.name, participant_names]
                for col, value in enumerate(values):
                    item = QTableWidgetItem(str(value))
                    item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                    self.expenses.setItem(row, col, item)
            settlements = service.settlements()
            self.settlements.setRowCount(len(settlements))
            for row, settlement in enumerate(settlements):
                for col, value in enumerate([settlement.from_person, settlement.to_person, money(settlement.amount)]):
                    item = QTableWidgetItem(str(value))
                    item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                    self.settlements.setItem(row, col, item)

    def add_expense(self) -> None:
        participant_ids = [check.property("person_id") for check in self.member_checks if check.isChecked()]
        try:
            with session_scope() as session:
                SharedLivingService(session).add_equal_expense(
                    title=self.title.text().strip(),
                    amount=spinbox_money(self.amount.value()),
                    paid_by_person_id=self.payer.currentData(),
                    participant_ids=participant_ids,
                    date_=qdate_to_date(self.date.date()),
                )
            self.title.clear()
            self.amount.setValue(0)
            self.refresh()
        except Exception as exc:
            show_error(self, "Shared expense not saved", exc)
