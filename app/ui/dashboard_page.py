from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QGridLayout, QHBoxLayout, QLabel, QTableWidgetItem, QVBoxLayout, QWidget

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
except Exception:  # pragma: no cover
    FigureCanvas = None
    Figure = None

from app.core.database import session_scope
from app.services.dashboard_service import DashboardService
from app.services.transaction_service import TransactionService
from app.ui.events import events
from app.ui.theme import Theme
from app.ui.widgets import ModernTable, SecondaryButton, SectionCard, StatCard
from app.utils.money import money


class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(28, 26, 28, 26)
        self.layout.setSpacing(20)
        title = QLabel("Dashboard")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Your month at a glance: cash flow, obligations, and shared living balances.")
        subtitle.setObjectName("pageSubtitle")
        self.layout.addWidget(title)
        self.layout.addWidget(subtitle)
        controls = QHBoxLayout()
        self.period = QComboBox()
        self.period.addItems(["This month", "Last month", "This year", "All time"])
        self.period.currentTextChanged.connect(self.refresh)
        self.period_label = QLabel("")
        refresh = SecondaryButton("Refresh")
        refresh.clicked.connect(self.refresh)
        controls.addWidget(QLabel("Period"))
        controls.addWidget(self.period)
        controls.addWidget(self.period_label, 1)
        controls.addWidget(refresh)
        self.layout.addLayout(controls)
        self.cards = QGridLayout()
        self.cards.setSpacing(16)
        self.layout.addLayout(self.cards)
        self.chart_card = SectionCard("Income vs Expenses", "Last six months")
        self.chart_body = QWidget()
        self.chart_layout = QVBoxLayout(self.chart_body)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        self.chart_card.layout.addWidget(self.chart_body)
        self.layout.addWidget(self.chart_card, 1)
        self.table_card = SectionCard("Recent Transactions", "Latest activity from the local ledger")
        self.table = ModernTable(["Date", "Type", "Amount", "Category", "Note"])
        self.table_card.layout.addWidget(self.table)
        self.layout.addWidget(self.table_card)
        events.transactions_changed.connect(self.refresh)
        events.debts_changed.connect(self.refresh)
        events.shared_living_changed.connect(self.refresh)
        events.settings_changed.connect(self._load_default_period)
        self._load_default_period()

    def _load_default_period(self) -> None:
        with session_scope() as session:
            summary = DashboardService(session).summary()
        label = str(summary["period_label"])
        index = self.period.findText(label)
        if index >= 0:
            self.period.setCurrentIndex(index)
        self.refresh()

    def refresh(self) -> None:
        while self.cards.count():
            item = self.cards.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        with session_scope() as session:
            summary = DashboardService(session).summary(period=self.period.currentText())
            currency = str(summary["currency"])
            self.period_label.setText(str(summary["period_label"]))
            metrics = [
                ("Income", money(summary["income"], currency), Theme.INCOME),
                ("Expenses", money(summary["expenses"], currency), Theme.EXPENSE),
                ("Net Balance", money(summary["net_balance"], currency), Theme.INFO),
                ("Savings", money(summary["savings"], currency), Theme.SAVINGS),
                ("Owed To Me", money(summary["owed_to_me"], currency), Theme.SHARED),
                ("I Owe", money(summary["i_owe"], currency), Theme.WARNING),
                ("Shared To Collect", money(summary["shared_receivable"], currency), Theme.SHARED),
                ("Shared To Pay", money(summary["shared_payable"], currency), Theme.WARNING),
            ]
            for idx, metric in enumerate(metrics):
                self.cards.addWidget(StatCard(*metric), idx // 4, idx % 4)
            self._render_chart(DashboardService(session).monthly_income_expenses())
            transactions = TransactionService(session).list_transactions(limit=8)
            self.table.setRowCount(len(transactions))
            for row, tx in enumerate(transactions):
                values = [str(tx.date), tx.type.value.replace("_", " "), money(tx.amount, tx.currency), tx.category.name if tx.category else "", tx.note or ""]
                for col, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                    self.table.setItem(row, col, item)

    def _render_chart(self, rows) -> None:  # type: ignore[no-untyped-def]
        while self.chart_layout.count():
            item = self.chart_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if FigureCanvas is None:
            self.chart_layout.addWidget(QLabel("Install matplotlib to enable charts."))
            return
        fig = Figure(figsize=(6, 2.7), facecolor=Theme.SURFACE)
        ax = fig.add_subplot(111)
        ax.set_facecolor(Theme.SURFACE)
        labels = [r[0] for r in rows]
        income = [r[1] for r in rows]
        expenses = [r[2] for r in rows]
        x = range(len(labels))
        ax.bar([i - 0.18 for i in x], income, width=0.36, color=Theme.INCOME, label="Income")
        ax.bar([i + 0.18 for i in x], expenses, width=0.36, color=Theme.EXPENSE, label="Expenses")
        ax.set_xticks(list(x), labels)
        ax.tick_params(colors=Theme.MUTED)
        ax.spines[:].set_color(Theme.BORDER)
        ax.legend(facecolor=Theme.SURFACE, labelcolor=Theme.TEXT)
        fig.tight_layout()
        self.chart_layout.addWidget(FigureCanvas(fig))
