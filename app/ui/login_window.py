from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QCheckBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from app.core.config import APP_LOGO_PATH
from app.core.database import session_scope
from app.core.i18n import apply_translations
from app.services.auth_service import AuthService
from app.ui.widgets import PrimaryButton


class LoginWindow(QWidget):
    login_succeeded = Signal(bool)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Personal Ledger Pro - Login")
        if APP_LOGO_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_LOGO_PATH)))
        self.setObjectName("loginWindow")
        self.resize(1120, 760)
        root = QVBoxLayout(self)
        root.setContentsMargins(34, 34, 34, 26)
        root.setSpacing(18)
        root.setAlignment(Qt.AlignCenter)

        shell = QFrame()
        shell.setObjectName("loginShell")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(20)
        shell_layout.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setObjectName("loginCard")
        card.setFixedWidth(460)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(38, 36, 38, 34)
        layout.setSpacing(14)

        logo_wrap = QFrame()
        logo_wrap.setObjectName("loginLogoRing")
        logo_layout = QVBoxLayout(logo_wrap)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo = QLabel()
        logo.setObjectName("loginLogo")
        logo.setAlignment(Qt.AlignCenter)
        if APP_LOGO_PATH.exists():
            logo.setPixmap(QPixmap(str(APP_LOGO_PATH)).scaled(66, 66, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            logo.setText("PL")
        logo_layout.addWidget(logo)
        title = QLabel("Personal Ledger Pro")
        title.setObjectName("loginTitle")
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("Secure personal finance management")
        subtitle.setObjectName("loginSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        username_field = self._field("◎", self.username)
        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.Password)
        self.toggle_password = QPushButton("Show")
        self.toggle_password.setObjectName("passwordToggle")
        self.toggle_password.clicked.connect(self._toggle_password)
        password_field = self._field("◆", self.password, self.toggle_password)

        self.remember = QCheckBox("Remember me")
        self.error = QLabel("")
        self.error.setObjectName("loginError")
        self.error.setWordWrap(True)
        self.error.setVisible(False)
        login = PrimaryButton("Login")
        login.setObjectName("loginButton")
        login.clicked.connect(self._login)
        self.password.returnPressed.connect(self._login)
        note = QLabel("Your data stays local on this device.")
        note.setObjectName("securityNote")
        note.setAlignment(Qt.AlignCenter)
        footer = QLabel("Local-first finance manager for Debian")
        footer.setObjectName("loginFooter")
        footer.setAlignment(Qt.AlignCenter)

        layout.addWidget(logo_wrap, 0, Qt.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(12)
        layout.addWidget(username_field)
        layout.addWidget(password_field)
        layout.addWidget(self.remember)
        layout.addWidget(self.error)
        layout.addSpacing(4)
        layout.addWidget(login)
        layout.addWidget(note)
        shell_layout.addWidget(card, 0, Qt.AlignCenter)
        shell_layout.addWidget(footer, 0, Qt.AlignCenter)
        root.addWidget(shell, 1)
        self._load_remembered_username()
        apply_translations(self)

    def _field(self, icon: str, input_widget: QLineEdit, action: QPushButton | None = None) -> QFrame:
        frame = QFrame()
        frame.setObjectName("loginField")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(8)
        icon_label = QLabel(icon)
        icon_label.setObjectName("loginFieldIcon")
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        input_widget.setObjectName("loginInput")
        layout.addWidget(input_widget, 1)
        if action:
            layout.addWidget(action)
        return frame

    def _load_remembered_username(self) -> None:
        with session_scope() as session:
            auth = AuthService(session)
            remembered = auth.remembered_username()
            self.username.setText(remembered)
            self.remember.setChecked(bool(remembered))
        if self.username.text():
            self.password.setFocus()
        else:
            self.username.setFocus()

    def _toggle_password(self) -> None:
        visible = self.password.echoMode() == QLineEdit.Normal
        self.password.setEchoMode(QLineEdit.Password if visible else QLineEdit.Normal)
        self.toggle_password.setText("Show" if visible else "Hide")

    def _login(self) -> None:
        self.error.setText("")
        self.error.setVisible(False)
        try:
            with session_scope() as session:
                auth = AuthService(session)
                user = auth.authenticate(self.username.text(), self.password.text(), self.remember.isChecked())
                default_password = auth.is_default_password(user)
            self.login_succeeded.emit(default_password)
            self.close()
        except Exception as exc:
            self.error.setText(str(exc))
            self.error.setVisible(True)
