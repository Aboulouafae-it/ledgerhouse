from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QTableWidgetItem, QVBoxLayout, QWidget

from app.core.database import session_scope
from app.services.person_service import PersonService
from app.ui.helpers import show_error
from app.ui.widgets import ModernTable, PrimaryButton, SecondaryButton, SectionCard


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
        form_card = SectionCard("New Person", "Add contacts and mark shared living members")
        form = QFormLayout()
        form.setSpacing(12)
        self.name = QLineEdit()
        self.phone = QLineEdit()
        self.email = QLineEdit()
        self.house = QCheckBox("House member")
        form.addRow("Name", self.name)
        form.addRow("Phone", self.phone)
        form.addRow("Email", self.email)
        form.addRow("", self.house)
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
        table_card = SectionCard("People Directory", "House members are available for shared expense splits")
        self.table = ModernTable(["ID", "Name", "Phone", "Email", "House Member"])
        table_card.layout.addWidget(self.table)
        layout.addWidget(form_card)
        layout.addWidget(table_card, 1)
        self.refresh()

    def add_person(self) -> None:
        try:
            with session_scope() as session:
                PersonService(session).add_person(
                    name=self.name.text(),
                    phone=self.phone.text(),
                    email=self.email.text(),
                    is_house_member=self.house.isChecked(),
                )
            self.name.clear()
            self.phone.clear()
            self.email.clear()
            self.house.setChecked(False)
            self.refresh()
        except Exception as exc:
            show_error(self, "Person not saved", exc)

    def refresh(self) -> None:
        with session_scope() as session:
            people = PersonService(session).list_people()
            self.table.setRowCount(len(people))
            for row, person in enumerate(people):
                vals = [person.id, person.name, person.phone or "", person.email or "", "Yes" if person.is_house_member else "No"]
                for col, val in enumerate(vals):
                    item = QTableWidgetItem(str(val))
                    item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                    self.table.setItem(row, col, item)
