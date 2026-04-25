from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from app.core.config import STYLES_DIR, config
from app.ui.dashboard_page import DashboardPage
from app.ui.debts_page import DebtsPage
from app.ui.people_page import PeoplePage
from app.ui.reports_page import ReportsPage
from app.ui.settings_page import SettingsPage
from app.ui.shared_living_page import SharedLivingPage
from app.ui.transactions_page import TransactionsPage


class MainWindow(QMainWindow):
    def __init__(self, default_password_warning: bool = False):
        super().__init__()
        self.setWindowTitle(config.app_name)
        self.resize(QSize(1280, 820))
        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(230)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(16, 20, 16, 18)
        side_layout.setSpacing(8)
        brand = QLabel("Personal\nLedger Pro")
        brand.setObjectName("brandTitle")
        brand_subtitle = QLabel("Local finance suite")
        brand_subtitle.setObjectName("brandSubtitle")
        side_layout.addWidget(brand)
        side_layout.addWidget(brand_subtitle)
        side_layout.addSpacing(16)
        self.stack = QStackedWidget()
        pages = [
            ("Dashboard", DashboardPage()),
            ("Transactions", TransactionsPage()),
            ("Debts", DebtsPage()),
            ("Shared Living", SharedLivingPage()),
            ("People", PeoplePage()),
            ("Reports", ReportsPage()),
            ("Settings", SettingsPage()),
        ]
        group = QButtonGroup(self)
        group.setExclusive(True)
        for index, (name, page) in enumerate(pages):
            btn = QPushButton(name)
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked=False, i=index: self.stack.setCurrentIndex(i))
            group.addButton(btn)
            side_layout.addWidget(btn)
            self.stack.addWidget(page)
            if index == 0:
                btn.setChecked(True)
        side_layout.addStretch(1)
        footer = QLabel("SQLite local storage")
        footer.setObjectName("brandSubtitle")
        side_layout.addWidget(footer)
        layout.addWidget(sidebar)
        layout.addWidget(self.stack, 1)
        self.stack.currentChanged.connect(self._refresh_current_page)
        self._load_stylesheet()
        if default_password_warning:
            QMessageBox.information(self, "Security reminder", "You are using the default password. Please change it in Settings.")

    def _refresh_current_page(self, index: int) -> None:
        page = self.stack.widget(index)
        refresh = getattr(page, "refresh", None)
        if callable(refresh):
            refresh()

    def _load_stylesheet(self) -> None:
        qss = STYLES_DIR / "dark.qss"
        if qss.exists():
            self.setStyleSheet(qss.read_text(encoding="utf-8"))
