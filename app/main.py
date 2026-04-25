from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.core.database import init_db
from app.core.session import current_session
from app.services.auth_service import AuthService
from app.core.database import session_scope
from app.ui.login_window import LoginWindow
from app.ui.main_window import MainWindow


def main() -> int:
    init_db()
    app = QApplication(sys.argv)
    qss_path = __import__("app.core.config", fromlist=["STYLES_DIR"]).STYLES_DIR / "dark.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
    windows: dict[str, object] = {}

    def open_main(default_password_warning: bool = False) -> None:
        window = MainWindow(default_password_warning=default_password_warning)
        windows["main"] = window
        window.show()

    with session_scope() as session:
        login_enabled = AuthService(session).login_enabled()
    if login_enabled:
        login = LoginWindow()
        windows["login"] = login
        login.login_succeeded.connect(open_main)
        login.show()
    else:
        current_session.clear()
        open_main(False)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
