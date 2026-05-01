from __future__ import annotations

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.database import session_scope
from app.services.shared_living_service import SharedLivingService
from app.ui.events import events
from app.ui.helpers import qdate_to_date, show_error, spinbox_money
from app.ui.widgets import FormDialog, ModernTable, PrimaryButton, SecondaryButton, SectionCard, StatCard
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
        self.category = QComboBox()
        self.payment = QComboBox()
        self.date = QDateEdit(QDate.currentDate())
        self.date.setCalendarPopup(True)
        form.addRow("Title", self.title)
        form.addRow("Amount", self.amount)
        form.addRow("Paid by", self.payer)
        form.addRow("Category", self.category)
        form.addRow("Payment", self.payment)
        form.addRow("Date", self.date)
        members_box = QGroupBox("Participants")
        members_box.setMaximumHeight(132)
        self.members_layout = QVBoxLayout(members_box)
        add = PrimaryButton("Add equal split expense")
        add.clicked.connect(self.add_expense)
        form_card.layout.addLayout(form)
        form_card.layout.addWidget(members_box)
        form_card.layout.addWidget(add)
        expenses_card = SectionCard("Shared Expenses", "Household costs paid by members")
        self.expenses = ModernTable(["Date", "Title", "Amount", "Paid By", "Participants"])
        self.expenses.setMinimumHeight(230)
        self.expenses.setWordWrap(False)
        self.expenses.setContextMenuPolicy(Qt.CustomContextMenu)
        self.expenses.customContextMenuRequested.connect(self._expense_context_menu)
        self.expenses.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.expenses.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.expenses.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.expenses.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.expenses.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        expenses_card.layout.addWidget(self.expenses)
        settlements_card = SectionCard("Settlement Suggestions", "Minimum practical payments between members")
        self.settlements = ModernTable(["From", "To", "Amount"])
        self.settlements.setMinimumHeight(170)
        self.settlements.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        settlements_card.layout.addWidget(self.settlements)
        layout.addWidget(form_card)
        lower = QHBoxLayout()
        lower.setSpacing(16)
        lower.addWidget(expenses_card, 3)
        lower.addWidget(settlements_card, 2)
        layout.addLayout(lower, 1)
        self.refresh()
        events.people_changed.connect(self.refresh)
        events.categories_changed.connect(self.refresh)
        events.payment_methods_changed.connect(self.refresh)
        events.settings_changed.connect(self.refresh)

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
            self.category.clear()
            self.category.addItem("None", None)
            for category in service.shared_categories():
                self.category.addItem(category.name, category.id)
            self.payment.clear()
            self.payment.addItem("None", None)
            for method in service.payment_methods():
                self.payment.addItem(method.name, method.id)
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
                    item.setData(Qt.UserRole, expense.id)
                    item.setToolTip(str(value))
                    self.expenses.setItem(row, col, item)
            self.expenses.resizeRowsToContents()
            settlements = service.settlements()
            self.settlements.setRowCount(len(settlements))
            for row, settlement in enumerate(settlements):
                for col, value in enumerate([settlement.from_person, settlement.to_person, money(settlement.amount)]):
                    item = QTableWidgetItem(str(value))
                    item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                    item.setToolTip(str(value))
                    self.settlements.setItem(row, col, item)
            self.settlements.resizeRowsToContents()

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
                    category_id=self.category.currentData(),
                    payment_method_id=self.payment.currentData(),
                )
            self.title.clear()
            self.amount.setValue(0)
            self.refresh()
            events.shared_living_changed.emit()
        except Exception as exc:
            show_error(self, "Shared expense not saved", exc)

    def _selected_expense_id(self, row: int | None = None) -> int | None:
        row = self.expenses.currentRow() if row is None else row
        if row < 0:
            return None
        item = self.expenses.item(row, 0)
        return int(item.data(Qt.UserRole)) if item else None

    def _expense_context_menu(self, position) -> None:  # type: ignore[no-untyped-def]
        row = self.expenses.rowAt(position.y())
        if row < 0:
            return
        self.expenses.selectRow(row)
        menu = QMenu(self)
        details = menu.addAction("More details")
        edit = menu.addAction("Edit")
        delete = menu.addAction("Delete")
        action = menu.exec(self.expenses.viewport().mapToGlobal(position))
        expense_id = self._selected_expense_id(row)
        if expense_id is None:
            return
        if action == details:
            self._show_expense_details(expense_id)
        elif action == edit:
            self._edit_expense(expense_id)
        elif action == delete:
            self._delete_expense(expense_id)

    def _delete_expense(self, expense_id: int) -> None:
        if QMessageBox.question(self, "Delete shared expense", "Delete this shared expense and its participant balances?") != QMessageBox.Yes:
            return
        try:
            with session_scope() as session:
                SharedLivingService(session).delete_expense(expense_id)
            self.refresh()
            events.shared_living_changed.emit()
        except Exception as exc:
            show_error(self, "Shared expense not deleted", exc)

    def _edit_expense(self, expense_id: int) -> None:
        try:
            with session_scope() as session:
                service = SharedLivingService(session)
                expense = service.get_expense(expense_id)
                members = service.house_members()
                active_people = service.active_people()
                data = {
                    "title": expense.title,
                    "amount": str(expense.amount),
                    "paid_by_person_id": expense.paid_by_person_id,
                    "category_id": expense.category_id,
                    "payment_method_id": expense.payment_method_id,
                    "date": expense.date,
                    "participants": {participant.person_id for participant in expense.participants if participant.share_amount > 0},
                    "members": [(person.id, person.name) for person in members],
                    "payers": [(person.id, person.name) for person in active_people],
                    "categories": [(category.id, category.name) for category in service.shared_categories()],
                    "payment_methods": [(method.id, method.name) for method in service.payment_methods()],
                }
        except Exception as exc:
            show_error(self, "Shared expense not loaded", exc)
            return
        dialog = FormDialog("Edit shared expense", self)
        dialog.resize(540, 460)
        form = QFormLayout()
        title = QLineEdit(data["title"])
        amount = QLineEdit(data["amount"])
        payer = QComboBox()
        for person_id, name in data["payers"]:
            payer.addItem(name, person_id)
        payer.setCurrentIndex(max(0, payer.findData(data["paid_by_person_id"])))
        category = QComboBox()
        category.addItem("None", None)
        for category_id, name in data["categories"]:
            category.addItem(name, category_id)
        category.setCurrentIndex(max(0, category.findData(data["category_id"])))
        payment = QComboBox()
        payment.addItem("None", None)
        for method_id, name in data["payment_methods"]:
            payment.addItem(name, method_id)
        payment.setCurrentIndex(max(0, payment.findData(data["payment_method_id"])))
        date_edit = QDateEdit(QDate(data["date"].year, data["date"].month, data["date"].day))
        date_edit.setCalendarPopup(True)
        form.addRow("Title", title)
        form.addRow("Amount", amount)
        form.addRow("Paid by", payer)
        form.addRow("Category", category)
        form.addRow("Payment", payment)
        form.addRow("Date", date_edit)
        participants_box = QGroupBox("Participants")
        participants_layout = QVBoxLayout(participants_box)
        checks: list[QCheckBox] = []
        for person_id, name in data["members"]:
            check = QCheckBox(name)
            check.setProperty("person_id", person_id)
            check.setChecked(person_id in data["participants"])
            checks.append(check)
            participants_layout.addWidget(check)
        dialog.content.addLayout(form)
        dialog.content.addWidget(participants_box)
        save = PrimaryButton("Save")
        cancel = SecondaryButton("Cancel")
        save.clicked.connect(dialog.accept)
        cancel.clicked.connect(dialog.reject)
        dialog.actions.addWidget(cancel)
        dialog.actions.addWidget(save)
        if dialog.exec() != QDialog.Accepted:
            return
        participant_ids = [check.property("person_id") for check in checks if check.isChecked()]
        try:
            with session_scope() as session:
                SharedLivingService(session).update_equal_expense(
                    expense_id,
                    title=title.text().strip(),
                    amount=amount.text().strip(),
                    paid_by_person_id=payer.currentData(),
                    participant_ids=participant_ids,
                    date_=qdate_to_date(date_edit.date()),
                    category_id=category.currentData(),
                    payment_method_id=payment.currentData(),
                )
            self.refresh()
            events.shared_living_changed.emit()
        except Exception as exc:
            show_error(self, "Shared expense not updated", exc)

    def _show_expense_details(self, expense_id: int) -> None:
        try:
            with session_scope() as session:
                service = SharedLivingService(session)
                expense = service.get_expense(expense_id)
                participants = [
                    (p.person_id, p.person.name, p.share_amount, p.paid_amount, p.balance)
                    for p in sorted(expense.participants, key=lambda item: item.person.name)
                ]
                monthly = {person_id: service.member_month_details(person_id, expense.date) for person_id, *_ in participants}
                details = {
                    "title": expense.title,
                    "amount": expense.amount,
                    "date": expense.date,
                    "paid_by": expense.paid_by.name,
                    "participants": participants,
                    "monthly": monthly,
                }
        except Exception as exc:
            show_error(self, "Shared expense details not loaded", exc)
            return
        dialog = QDialog(self)
        dialog.setObjectName("formDialog")
        dialog.setWindowTitle("Shared expense details")
        dialog.resize(760, 520)
        root = QVBoxLayout(dialog)
        title = QLabel(details["title"])
        title.setObjectName("dialogTitle")
        subtitle = QLabel(f"{details['date']} • {money(details['amount'])} • Paid by {details['paid_by']}")
        subtitle.setObjectName("sectionSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)
        tabs = QTabWidget()
        overview = QWidget()
        grid = QGridLayout(overview)
        grid.setSpacing(12)
        grid.addWidget(StatCard("Amount", money(details["amount"])), 0, 0)
        grid.addWidget(StatCard("Paid by", details["paid_by"]), 0, 1)
        grid.addWidget(StatCard("Participants", str(len(details["participants"]))), 0, 2)
        participants_tab = QWidget()
        participants_layout = QVBoxLayout(participants_tab)
        table = ModernTable(["Person", "Share", "Paid", "Balance", "Paid this month"])
        rows = []
        for person_id, name, share, paid, balance in details["participants"]:
            rows.append([name, money(share), money(paid), money(balance), money(details["monthly"][person_id]["paid_total"])])
        table.set_readonly_rows(rows)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        participants_layout.addWidget(table)
        purchases_tab = QWidget()
        purchases_layout = QVBoxLayout(purchases_tab)
        purchases = ModernTable(["Person", "Date", "What they paid for", "Amount"])
        purchase_rows = []
        for person_id, name, *_ in details["participants"]:
            for paid_date, paid_title, paid_amount in details["monthly"][person_id]["paid_items"]:
                purchase_rows.append([name, paid_date, paid_title, money(paid_amount)])
        purchases.set_readonly_rows(purchase_rows or [["No monthly paid items", "", "", ""]])
        purchases.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        purchases_layout.addWidget(purchases)
        tabs.addTab(overview, "Overview")
        tabs.addTab(participants_tab, "Participants")
        tabs.addTab(purchases_tab, "This month")
        root.addWidget(tabs, 1)
        close = PrimaryButton("Close")
        close.clicked.connect(dialog.accept)
        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addWidget(close)
        root.addLayout(actions)
        dialog.exec()
