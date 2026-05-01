from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMenu, QMessageBox, QTextEdit, QTableWidgetItem, QVBoxLayout, QWidget

from app.core.database import session_scope
from app.services.person_service import PersonService
from app.ui.events import events
from app.ui.helpers import show_error
from app.ui.widgets import FormDialog, ModernTable, PrimaryButton, SecondaryButton, SectionCard


ROLE_FILTERS = ["All", "House members", "Creditors", "Debtors", "Employers", "Service providers", "Active", "Inactive"]


class PeoplePage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(18)
        title = QLabel("People")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Manage contacts, house members, and financial relationships.")
        subtitle.setObjectName("pageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        form_card = SectionCard("New Person", "Add relationship details and financial roles")
        form = QFormLayout()
        form.setSpacing(12)
        self.name = QLineEdit()
        self.phone = QLineEdit()
        self.email = QLineEdit()
        self.note = QTextEdit()
        self.note.setMaximumHeight(72)
        self.house = QCheckBox("House member")
        self.creditor = QCheckBox("Creditor")
        self.debtor = QCheckBox("Debtor")
        self.employer = QCheckBox("Employer / income source")
        self.provider = QCheckBox("Service provider")
        self.family = QCheckBox("Family / friend")
        self.active = QCheckBox("Active")
        self.active.setChecked(True)
        roles = QHBoxLayout()
        for checkbox in (self.house, self.creditor, self.debtor, self.employer, self.provider, self.family, self.active):
            roles.addWidget(checkbox)
        roles.addStretch(1)
        form.addRow("Name", self.name)
        form.addRow("Phone", self.phone)
        form.addRow("Email", self.email)
        form.addRow("Roles", roles)
        form.addRow("Note", self.note)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        add = PrimaryButton("Add person")
        add.clicked.connect(self.add_person)
        refresh = SecondaryButton("Refresh")
        refresh.clicked.connect(self.refresh)
        buttons.addWidget(add)
        buttons.addWidget(refresh)
        form_card.layout.addLayout(form)
        form_card.layout.addLayout(buttons)

        table_card = SectionCard("People Directory", "Contacts, roles, status, and relationship balances")
        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search people")
        self.role_filter = QComboBox()
        self.role_filter.addItems(ROLE_FILTERS)
        filters.addWidget(self.search, 1)
        filters.addWidget(self.role_filter)
        table_card.layout.addLayout(filters)
        self.table = ModernTable(["ID", "Name", "Roles", "Phone", "Email", "Active", "Shared", "Debt relation"])
        self.table.doubleClicked.connect(self._edit_selected)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        table_card.layout.addWidget(self.table)
        layout.addWidget(form_card)
        layout.addWidget(table_card, 1)
        self.search.textChanged.connect(self.refresh)
        self.role_filter.currentTextChanged.connect(self.refresh)
        self.refresh()
        events.people_changed.connect(self.refresh)

    def add_person(self) -> None:
        try:
            with session_scope() as session:
                PersonService(session).add_person(
                    name=self.name.text(),
                    phone=self.phone.text(),
                    email=self.email.text(),
                    is_house_member=self.house.isChecked(),
                    is_creditor=self.creditor.isChecked(),
                    is_debtor=self.debtor.isChecked(),
                    is_employer=self.employer.isChecked(),
                    is_service_provider=self.provider.isChecked(),
                    is_family_friend=self.family.isChecked(),
                    is_active=self.active.isChecked(),
                    note=self.note.toPlainText(),
                )
            self._clear_form()
            self.refresh()
            events.people_changed.emit()
        except Exception as exc:
            show_error(self, "Person not saved", exc)

    def refresh(self) -> None:
        with session_scope() as session:
            service = PersonService(session)
            people = service.filtered(self.search.text(), self.role_filter.currentText())
            debts = service.debt_summary_by_person()
            self.table.setRowCount(len(people))
            for row, person in enumerate(people):
                vals = [
                    person.id,
                    person.name,
                    self._roles(person),
                    person.phone or "",
                    person.email or "",
                    "Active" if person.is_active else "Inactive",
                    "Yes" if person.is_house_member else "No",
                    debts.get(person.id, ""),
                ]
                for col, val in enumerate(vals):
                    item = QTableWidgetItem(str(val))
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.table.setItem(row, col, item)
            self.table.resizeColumnsToContents()

    def edit_person(self, person_id: int) -> None:
        try:
            with session_scope() as session:
                person = PersonService(session).get_person(person_id)
                data = {
                    "name": person.name,
                    "phone": person.phone or "",
                    "email": person.email or "",
                    "note": person.note or "",
                    "house": person.is_house_member,
                    "creditor": person.is_creditor,
                    "debtor": person.is_debtor,
                    "employer": person.is_employer,
                    "provider": person.is_service_provider,
                    "family": person.is_family_friend,
                    "active": person.is_active,
                }
        except Exception as exc:
            show_error(self, "Person not loaded", exc)
            return

        dialog = FormDialog("Edit person", self)
        dialog.resize(620, 520)
        form = QFormLayout()
        name = QLineEdit(data["name"])
        phone = QLineEdit(data["phone"])
        email = QLineEdit(data["email"])
        note = QTextEdit(data["note"])
        note.setMaximumHeight(90)
        checks = {
            "house": QCheckBox("House member"),
            "creditor": QCheckBox("Creditor"),
            "debtor": QCheckBox("Debtor"),
            "employer": QCheckBox("Employer / income source"),
            "provider": QCheckBox("Service provider"),
            "family": QCheckBox("Family / friend"),
            "active": QCheckBox("Active"),
        }
        roles = QHBoxLayout()
        for key, checkbox in checks.items():
            checkbox.setChecked(bool(data[key]))
            roles.addWidget(checkbox)
        roles.addStretch(1)
        form.addRow("Name", name)
        form.addRow("Phone", phone)
        form.addRow("Email", email)
        form.addRow("Roles", roles)
        form.addRow("Note", note)
        dialog.content.addLayout(form)
        cancel = SecondaryButton("Cancel")
        save = PrimaryButton("Save")
        cancel.clicked.connect(dialog.reject)
        save.clicked.connect(dialog.accept)
        dialog.actions.addWidget(cancel)
        dialog.actions.addWidget(save)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            with session_scope() as session:
                PersonService(session).update_person(
                    person_id,
                    name=name.text(),
                    phone=phone.text(),
                    email=email.text(),
                    is_house_member=checks["house"].isChecked(),
                    is_creditor=checks["creditor"].isChecked(),
                    is_debtor=checks["debtor"].isChecked(),
                    is_employer=checks["employer"].isChecked(),
                    is_service_provider=checks["provider"].isChecked(),
                    is_family_friend=checks["family"].isChecked(),
                    is_active=checks["active"].isChecked(),
                    note=note.toPlainText(),
                )
            self.refresh()
            events.people_changed.emit()
        except Exception as exc:
            show_error(self, "Person not updated", exc)

    def deactivate_person(self, person_id: int) -> None:
        if QMessageBox.question(self, "Deactivate person", "Deactivate this person? Historical records will remain linked.") != QMessageBox.Yes:
            return
        try:
            with session_scope() as session:
                PersonService(session).update_roles(person_id, is_active=False)
            self.refresh()
            events.people_changed.emit()
        except Exception as exc:
            show_error(self, "Person not deactivated", exc)

    def _show_context_menu(self, position) -> None:
        row = self.table.rowAt(position.y())
        if row < 0:
            return
        self.table.selectRow(row)
        person_id = self._selected_person_id()
        if person_id is None:
            return
        menu = QMenu(self)
        edit = menu.addAction("Edit person")
        deactivate = menu.addAction("Deactivate person")
        selected = menu.exec(self.table.viewport().mapToGlobal(position))
        if selected == edit:
            self.edit_person(person_id)
        elif selected == deactivate:
            self.deactivate_person(person_id)

    def _edit_selected(self, _index=None) -> None:
        person_id = self._selected_person_id()
        if person_id is not None:
            self.edit_person(person_id)

    def _selected_person_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return int(item.text()) if item else None

    def _clear_form(self) -> None:
        self.name.clear()
        self.phone.clear()
        self.email.clear()
        self.note.clear()
        for checkbox in (self.house, self.creditor, self.debtor, self.employer, self.provider, self.family):
            checkbox.setChecked(False)
        self.active.setChecked(True)

    def _roles(self, person) -> str:
        roles = []
        if person.is_house_member:
            roles.append("House")
        if person.is_creditor:
            roles.append("Creditor")
        if person.is_debtor:
            roles.append("Debtor")
        if person.is_employer:
            roles.append("Employer")
        if person.is_service_provider:
            roles.append("Provider")
        if person.is_family_friend:
            roles.append("Family/Friend")
        return ", ".join(roles) or "Contact"
