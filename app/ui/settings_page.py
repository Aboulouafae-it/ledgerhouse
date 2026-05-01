from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.backup import restore_database
from app.core.config import APP_LOGO_PATH, BACKUP_DIR
from app.core.database import init_db, session_scope
from app.core.i18n import apply_translations
from app.models.category import CategoryType
from app.models.payment_method import PaymentMethodType
from app.services.auth_service import AuthService
from app.services.category_service import CategoryService
from app.services.payment_method_service import PaymentMethodService
from app.services.person_service import PersonService
from app.services.settings_service import SettingsService
from app.services.backup_service import BackupService
from app.ui.events import events
from app.ui.helpers import show_error
from app.ui.widgets import ModernTable, PrimaryButton, SecondaryButton, SectionCard, StatCard


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 26, 28, 26)
        root.setSpacing(18)
        title = QLabel("Settings")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Central control panel for security, people, reports, backup, and appearance.")
        subtitle.setObjectName("pageSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        splitter = QSplitter(Qt.Horizontal)
        self.menu = QListWidget()
        self.menu.setFixedWidth(235)
        self.stack = QStackedWidget()
        self.sections = [
            ("Language", self._language_section()),
            ("General Settings", self._general_section()),
            ("Security & Login", self._security_section()),
            ("People Management", self._people_section()),
            ("Creditors & Debtors", self._creditors_section()),
            ("Shared Living Members", self._shared_members_section()),
            ("Categories", self._categories_section()),
            ("Payment Methods", self._payment_methods_section()),
            ("Reports & PDF Identity", self._reports_section()),
            ("Backup & Restore", self._backup_section()),
            ("Appearance", self._appearance_section()),
        ]
        for name, widget in self.sections:
            self.menu.addItem(QListWidgetItem(name))
            self.stack.addWidget(widget)
        self.menu.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.menu.setCurrentRow(0)
        splitter.addWidget(self.menu)
        splitter.addWidget(self.stack)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)
        self.refresh()

    def refresh(self) -> None:
        self._load_settings()
        self._refresh_people_tables()
        self._refresh_categories()
        self._refresh_payment_methods()

    def _language_section(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        card = SectionCard("Language", "Choose the application language")
        form = QFormLayout()
        self.app_language = QComboBox()
        self.app_language.addItems(["English", "Italian", "Arabic"])
        self.language_hint = QLabel("Save and restart the app to apply the language across all screens.")
        self.language_hint.setObjectName("sectionSubtitle")
        form.addRow("Language", self.app_language)
        save = PrimaryButton("Save language")
        save.clicked.connect(self._save_language)
        card.layout.addLayout(form)
        card.layout.addWidget(self.language_hint)
        card.layout.addWidget(save)
        layout.addWidget(card)
        layout.addStretch(1)
        return page

    def _general_section(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        card = SectionCard("General Settings", "Default workspace behavior")
        form = QFormLayout()
        self.owner_name = QLineEdit()
        self.default_currency = QLineEdit("EUR")
        self.default_language = QComboBox()
        self.default_language.addItems(["English", "Italian", "Arabic"])
        self.date_format = QComboBox()
        self.date_format.addItems(["YYYY-MM-DD", "DD/MM/YYYY", "MM/DD/YYYY"])
        self.first_day = QComboBox()
        self.first_day.addItems(["Monday", "Sunday", "Saturday"])
        self.dashboard_period = QComboBox()
        self.dashboard_period.addItems(["this month", "last month", "this year", "all time"])
        for label, widget in [
            ("Owner name", self.owner_name),
            ("Default currency", self.default_currency),
            ("Language", self.default_language),
            ("Date format", self.date_format),
            ("First day of week", self.first_day),
            ("Dashboard period", self.dashboard_period),
        ]:
            form.addRow(label, widget)
        save = PrimaryButton("Save general settings")
        save.clicked.connect(self._save_general)
        card.layout.addLayout(form)
        card.layout.addWidget(save)
        layout.addWidget(card)
        layout.addStretch(1)
        return page

    def _security_section(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        card = SectionCard("Security & Login", "Local password protection")
        form = QFormLayout()
        self.login_enabled = QCheckBox("Require login when the app starts")
        self.remember_username = QCheckBox("Remember username on login screen")
        self.username = QLineEdit()
        self.current_password = QLineEdit()
        self.current_password.setEchoMode(QLineEdit.Password)
        self.new_password = QLineEdit()
        self.new_password.setEchoMode(QLineEdit.Password)
        self.confirm_password = QLineEdit()
        self.confirm_password.setEchoMode(QLineEdit.Password)
        self.auto_lock = QComboBox()
        self.auto_lock.addItems(["disabled", "after 5 minutes", "after 15 minutes", "after 30 minutes"])
        self.default_password_warning = QLabel("")
        self.default_password_warning.setObjectName("loginError")
        form.addRow("", self.login_enabled)
        form.addRow("", self.remember_username)
        form.addRow("Username", self.username)
        form.addRow("Current password", self.current_password)
        form.addRow("New password", self.new_password)
        form.addRow("Confirm password", self.confirm_password)
        form.addRow("Auto-lock", self.auto_lock)
        save = PrimaryButton("Save security settings")
        save.clicked.connect(self._save_security)
        card.layout.addWidget(self.default_password_warning)
        card.layout.addLayout(form)
        card.layout.addWidget(save)
        layout.addWidget(card)
        layout.addStretch(1)
        return page

    def _people_section(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        card = SectionCard("People Management", "One central people table used across the app")
        filters = QHBoxLayout()
        self.people_search = QLineEdit()
        self.people_search.setPlaceholderText("Search people")
        self.people_filter = QComboBox()
        self.people_filter.addItems(["All", "Creditors", "Debtors", "House members", "Active", "Inactive"])
        self.people_search.textChanged.connect(self._refresh_people_tables)
        self.people_filter.currentTextChanged.connect(self._refresh_people_tables)
        add = PrimaryButton("Add person")
        add.clicked.connect(self._quick_add_person)
        deactivate = SecondaryButton("Deactivate selected")
        deactivate.clicked.connect(self._deactivate_selected_person)
        filters.addWidget(self.people_search, 1)
        filters.addWidget(self.people_filter)
        filters.addWidget(add)
        filters.addWidget(deactivate)
        self.people_table = ModernTable(["ID", "Name", "Roles", "Phone", "Email", "Status"])
        card.layout.addLayout(filters)
        card.layout.addWidget(self.people_table)
        layout.addWidget(card)
        return page

    def _creditors_section(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        card = SectionCard("Creditors & Debtors", "Define who can appear in Debt forms")
        self.creditor_count = QLabel("")
        self.debtor_count = QLabel("")
        stats = QHBoxLayout()
        self.creditor_stat = StatCard("Creditors", "0")
        self.debtor_stat = StatCard("Debtors", "0")
        stats.addWidget(self.creditor_stat)
        stats.addWidget(self.debtor_stat)
        add = PrimaryButton("Add creditor/debtor")
        add.clicked.connect(lambda: self._quick_add_person(creditor=True, debtor=True))
        self.creditor_table = ModernTable(["ID", "Name", "Creditor", "Debtor", "Phone", "Email"])
        card.layout.addLayout(stats)
        card.layout.addWidget(add)
        card.layout.addWidget(self.creditor_table)
        layout.addWidget(card)
        return page

    def _shared_members_section(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        card = SectionCard("Shared Living Members", "Active house members used in shared expense splits")
        self.house_count = QLabel("")
        add = PrimaryButton("Add shared living member")
        add.clicked.connect(lambda: self._quick_add_person(house=True))
        self.house_table = ModernTable(["ID", "Name", "Phone", "Email", "Status"])
        card.layout.addWidget(self.house_count)
        card.layout.addWidget(add)
        card.layout.addWidget(self.house_table)
        layout.addWidget(card)
        return page

    def _categories_section(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        card = SectionCard("Categories", "Transaction, debt, saving, and shared categories")
        form = QHBoxLayout()
        self.cat_name = QLineEdit()
        self.cat_name.setPlaceholderText("Category name")
        self.cat_type = QComboBox()
        self.cat_type.addItems([kind.value for kind in CategoryType])
        self.cat_color = QLineEdit("#3B82F6")
        add = PrimaryButton("Add category")
        add.clicked.connect(self._add_category)
        deactivate = SecondaryButton("Deactivate selected")
        deactivate.clicked.connect(self._deactivate_selected_category)
        form.addWidget(self.cat_name)
        form.addWidget(self.cat_type)
        form.addWidget(self.cat_color)
        form.addWidget(add)
        form.addWidget(deactivate)
        self.category_table = ModernTable(["ID", "Name", "Type", "Color", "Active"])
        card.layout.addLayout(form)
        card.layout.addWidget(self.category_table)
        layout.addWidget(card)
        return page

    def _payment_methods_section(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        card = SectionCard("Payment Methods", "Used by transaction forms")
        form = QHBoxLayout()
        self.method_name = QLineEdit()
        self.method_name.setPlaceholderText("Payment method")
        self.method_type = QComboBox()
        self.method_type.addItems([kind.value for kind in PaymentMethodType])
        add = PrimaryButton("Add method")
        add.clicked.connect(self._add_payment_method)
        deactivate = SecondaryButton("Deactivate selected")
        deactivate.clicked.connect(self._deactivate_selected_method)
        form.addWidget(self.method_name)
        form.addWidget(self.method_type)
        form.addWidget(add)
        form.addWidget(deactivate)
        self.payment_table = ModernTable(["ID", "Name", "Type", "Active"])
        card.layout.addLayout(form)
        card.layout.addWidget(self.payment_table)
        layout.addWidget(card)
        return page

    def _reports_section(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        card = SectionCard("Reports & PDF Identity", "Identity and layout defaults used in generated PDFs")
        form = QFormLayout()
        self.report_owner = QLineEdit()
        self.report_prefix = QLineEdit()
        self.report_footer = QLineEdit()
        self.logo_path = QLineEdit()
        self.report_language = QComboBox()
        self.report_language.addItems(["English", "Italian", "Arabic"])
        self.include_charts = QCheckBox("Include charts in PDF reports")
        self.include_signature = QCheckBox("Include signature area")
        for label, widget in [
            ("Owner name", self.report_owner),
            ("Title prefix", self.report_prefix),
            ("Footer text", self.report_footer),
            ("Logo path", self.logo_path),
            ("Language", self.report_language),
            ("", self.include_charts),
            ("", self.include_signature),
        ]:
            form.addRow(label, widget)
        save = PrimaryButton("Save report identity")
        save.clicked.connect(self._save_reports)
        card.layout.addLayout(form)
        card.layout.addWidget(save)
        layout.addWidget(card)
        layout.addStretch(1)
        return page

    def _backup_section(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        card = SectionCard("Backup & Restore", "Protect the local SQLite database")
        self.backup_folder = QLabel(str(BACKUP_DIR))
        self.last_backup = QLabel("")
        backup = PrimaryButton("Create backup")
        backup.clicked.connect(self._backup)
        restore = SecondaryButton("Restore from backup")
        restore.clicked.connect(self._restore)
        self.backup_encryption = QCheckBox("Backup encryption placeholder")
        card.layout.addWidget(QLabel("Backup folder"))
        card.layout.addWidget(self.backup_folder)
        card.layout.addWidget(self.last_backup)
        card.layout.addWidget(self.backup_encryption)
        card.layout.addWidget(backup)
        card.layout.addWidget(restore)
        layout.addWidget(card)
        layout.addStretch(1)
        return page

    def _appearance_section(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        card = SectionCard("Appearance", "Centralized theme preferences")
        form = QFormLayout()
        self.theme = QComboBox()
        self.theme.addItems(["dark", "light placeholder", "system placeholder"])
        self.accent = QComboBox()
        self.accent.addItems(["blue", "green", "purple", "gold"])
        self.compact = QCheckBox("Compact mode")
        self.table_density = QComboBox()
        self.table_density.addItems(["comfortable", "compact"])
        form.addRow("Theme", self.theme)
        form.addRow("Accent color", self.accent)
        form.addRow("", self.compact)
        form.addRow("Table density", self.table_density)
        save = PrimaryButton("Save appearance")
        save.clicked.connect(self._save_appearance)
        card.layout.addLayout(form)
        card.layout.addWidget(save)
        layout.addWidget(card)
        layout.addStretch(1)
        return page

    def _load_settings(self) -> None:
        with session_scope() as session:
            settings = SettingsService(session)
            auth = AuthService(session)
            values = settings.all_settings()
            self.owner_name.setText(values.get("owner_name", ""))
            self.default_currency.setText(values.get("default_currency", "EUR"))
            self._set_combo(self.app_language, values.get("default_language", "English"))
            self._set_combo(self.default_language, values.get("default_language", "English"))
            self._set_combo(self.date_format, values.get("date_format", "YYYY-MM-DD"))
            self._set_combo(self.first_day, values.get("first_day_of_week", "Monday"))
            self._set_combo(self.dashboard_period, values.get("default_dashboard_period", "this month"))
            self.login_enabled.setChecked(settings.get_bool("login_enabled", True))
            self.remember_username.setChecked(settings.get_bool("remember_username", False))
            self.username.setText(auth.primary_user().username)
            self._set_combo(self.auto_lock, values.get("auto_lock", "disabled"))
            self.default_password_warning.setText("Default password is still active. Change it now." if auth.is_default_password() else "")
            self.report_owner.setText(values.get("owner_name", ""))
            self.report_prefix.setText(values.get("report_title_prefix", "Personal Ledger Pro"))
            self.report_footer.setText(values.get("report_footer_text", "Generated by Personal Ledger Pro"))
            self.logo_path.setText(values.get("report_logo_path", str(APP_LOGO_PATH)) or str(APP_LOGO_PATH))
            self._set_combo(self.report_language, values.get("report_language", "English"))
            self.include_charts.setChecked(settings.get_bool("report_include_charts", False))
            self.include_signature.setChecked(settings.get_bool("report_include_signature", True))
            self.last_backup.setText(f"Last backup: {values.get('last_backup_at', 'Never') or 'Never'}")
            self._set_combo(self.theme, values.get("theme", "dark"))
            self._set_combo(self.accent, values.get("accent_color", "blue"))
            self.compact.setChecked(settings.get_bool("compact_mode", False))
            self._set_combo(self.table_density, values.get("table_density", "comfortable"))

    def _save_general(self) -> None:
        try:
            with session_scope() as session:
                SettingsService(session).update_many(
                    {
                        "owner_name": self.owner_name.text().strip(),
                        "default_currency": self.default_currency.text().strip().upper() or "EUR",
                        "default_language": self.default_language.currentText(),
                        "report_language": self.default_language.currentText(),
                        "date_format": self.date_format.currentText(),
                        "first_day_of_week": self.first_day.currentText(),
                        "default_dashboard_period": self.dashboard_period.currentText(),
                    }
                )
            self._toast("General settings saved.")
            events.settings_changed.emit()
            events.people_changed.emit()
        except Exception as exc:
            show_error(self, "Settings not saved", exc)

    def _save_language(self) -> None:
        try:
            language = self.app_language.currentText()
            with session_scope() as session:
                settings = SettingsService(session)
                settings.set("default_language", language, "str")
                settings.set("report_language", language, "str")
            self._set_combo(self.default_language, language)
            self._set_combo(self.report_language, language)
            apply_translations(self.window(), language)
            self._toast("Language saved. Restart the app to apply it everywhere.")
            events.settings_changed.emit()
        except Exception as exc:
            show_error(self, "Language not saved", exc)

    def _save_security(self) -> None:
        try:
            with session_scope() as session:
                settings = SettingsService(session)
                auth = AuthService(session)
                settings.set_bool("login_enabled", self.login_enabled.isChecked())
                settings.set_bool("remember_username", self.remember_username.isChecked())
                if not self.remember_username.isChecked():
                    settings.set("remembered_username", "", "str")
                settings.set("auto_lock", self.auto_lock.currentText())
                auth.update_username(self.username.text())
                if self.current_password.text() or self.new_password.text() or self.confirm_password.text():
                    auth.change_password(self.current_password.text(), self.new_password.text(), self.confirm_password.text())
            self.current_password.clear()
            self.new_password.clear()
            self.confirm_password.clear()
            self.refresh()
            self._toast("Security settings saved.")
            events.settings_changed.emit()
        except Exception as exc:
            show_error(self, "Security settings not saved", exc)

    def _quick_add_person(self, creditor: bool = False, debtor: bool = False, house: bool = False) -> None:
        name, ok = __import__("PySide6.QtWidgets", fromlist=["QInputDialog"]).QInputDialog.getText(self, "Add person", "Name")
        if not ok or not name.strip():
            return
        try:
            with session_scope() as session:
                PersonService(session).add_or_update_person(name=name, is_creditor=creditor, is_debtor=debtor, is_house_member=house)
            self.refresh()
            events.people_changed.emit()
        except Exception as exc:
            show_error(self, "Person not saved", exc)

    def _refresh_people_tables(self) -> None:
        if not hasattr(self, "people_table"):
            return
        with session_scope() as session:
            service = PersonService(session)
            summary = service.role_summary()
            if hasattr(self, "creditor_stat"):
                self.creditor_stat.value_label.setText(str(summary["creditors"]))
                self.debtor_stat.value_label.setText(str(summary["debtors"]))
            people = service.filtered(self.people_search.text() if hasattr(self, "people_search") else "", self.people_filter.currentText() if hasattr(self, "people_filter") else "All")
            self.people_table.set_readonly_rows([[p.id, p.name, self._roles(p), p.phone or "", p.email or "", "Active" if p.is_active else "Inactive"] for p in people])
            cd = service.creditor_debtors()
            self.creditor_table.set_readonly_rows([[p.id, p.name, "Yes" if p.is_creditor else "No", "Yes" if p.is_debtor else "No", p.phone or "", p.email or ""] for p in cd])
            house = service.house_members()
            self.house_count.setText(f"Active house members: {len(house)}")
            self.house_table.set_readonly_rows([[p.id, p.name, p.phone or "", p.email or "", "Active" if p.is_active else "Inactive"] for p in house])

    def _deactivate_selected_person(self) -> None:
        row = self.people_table.currentRow()
        if row < 0:
            return
        person_id = int(self.people_table.item(row, 0).text())
        try:
            with session_scope() as session:
                PersonService(session).update_roles(person_id, is_active=False)
            self.refresh()
            events.people_changed.emit()
        except Exception as exc:
            show_error(self, "Person not updated", exc)

    def _roles(self, person) -> str:  # type: ignore[no-untyped-def]
        roles = []
        if person.is_creditor:
            roles.append("Creditor")
        if person.is_debtor:
            roles.append("Debtor")
        if person.is_house_member:
            roles.append("House")
        return ", ".join(roles) or "Normal"

    def _add_category(self) -> None:
        try:
            with session_scope() as session:
                CategoryService(session).add_category(self.cat_name.text(), CategoryType(self.cat_type.currentText()), self.cat_color.text())
            self.cat_name.clear()
            self._refresh_categories()
            events.categories_changed.emit()
        except Exception as exc:
            show_error(self, "Category not saved", exc)

    def _refresh_categories(self) -> None:
        if not hasattr(self, "category_table"):
            return
        with session_scope() as session:
            rows = CategoryService(session).list_categories()
            self.category_table.set_readonly_rows([[c.id, c.name, c.type.value, c.color or "", "Yes" if c.is_active else "No"] for c in rows])

    def _deactivate_selected_category(self) -> None:
        row = self.category_table.currentRow()
        if row < 0:
            return
        try:
            with session_scope() as session:
                CategoryService(session).set_active(int(self.category_table.item(row, 0).text()), False)
            self._refresh_categories()
            events.categories_changed.emit()
        except Exception as exc:
            show_error(self, "Category not updated", exc)

    def _add_payment_method(self) -> None:
        try:
            with session_scope() as session:
                PaymentMethodService(session).add_method(self.method_name.text(), PaymentMethodType(self.method_type.currentText()))
            self.method_name.clear()
            self._refresh_payment_methods()
            events.payment_methods_changed.emit()
        except Exception as exc:
            show_error(self, "Payment method not saved", exc)

    def _refresh_payment_methods(self) -> None:
        if not hasattr(self, "payment_table"):
            return
        with session_scope() as session:
            rows = PaymentMethodService(session).list_methods()
            self.payment_table.set_readonly_rows([[m.id, m.name, m.type.value if m.type else "", "Yes" if m.is_active else "No"] for m in rows])

    def _deactivate_selected_method(self) -> None:
        row = self.payment_table.currentRow()
        if row < 0:
            return
        try:
            with session_scope() as session:
                PaymentMethodService(session).set_active(int(self.payment_table.item(row, 0).text()), False)
            self._refresh_payment_methods()
            events.payment_methods_changed.emit()
        except Exception as exc:
            show_error(self, "Payment method not updated", exc)

    def _save_reports(self) -> None:
        try:
            with session_scope() as session:
                settings = SettingsService(session)
                settings.set_owner_name(self.report_owner.text().strip())
                settings.update_many(
                    {
                        "report_title_prefix": self.report_prefix.text().strip(),
                        "report_footer_text": self.report_footer.text().strip(),
                        "report_logo_path": self.logo_path.text().strip(),
                        "report_language": self.report_language.currentText(),
                    }
                )
                settings.set_bool("report_include_charts", self.include_charts.isChecked())
                settings.set_bool("report_include_signature", self.include_signature.isChecked())
            self._toast("Report identity saved.")
            events.settings_changed.emit()
            events.people_changed.emit()
        except Exception as exc:
            show_error(self, "Report settings not saved", exc)

    def _backup(self) -> None:
        try:
            with session_scope() as session:
                target = BackupService(session).create_backup()
            self.refresh()
            self._toast(f"Backup created: {target}")
        except Exception as exc:
            show_error(self, "Backup failed", exc)

    def _restore(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Restore database backup", str(BACKUP_DIR), "SQLite files (*.sqlite3 *.db);;All files (*)")
        if not path:
            return
        if QMessageBox.question(self, "Confirm restore", "Restore will replace the current database after creating a safety backup. Continue?") != QMessageBox.Yes:
            return
        try:
            restore_database(Path(path))
            init_db()
            self._toast("Database restored. Restart the app to reload all data.")
        except Exception as exc:
            show_error(self, "Restore failed", exc)

    def _save_appearance(self) -> None:
        try:
            with session_scope() as session:
                settings = SettingsService(session)
                settings.set("theme", self.theme.currentText())
                settings.set("accent_color", self.accent.currentText())
                settings.set_bool("compact_mode", self.compact.isChecked())
                settings.set("table_density", self.table_density.currentText())
            self._toast("Appearance settings saved.")
            events.settings_changed.emit()
        except Exception as exc:
            show_error(self, "Appearance not saved", exc)

    def _set_combo(self, combo: QComboBox, value: str) -> None:
        idx = combo.findText(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _toast(self, message: str) -> None:
        QMessageBox.information(self, "Settings", message)
