from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class CurrentSession:
    user_id: int | None = None
    username: str = ""
    full_name: str = ""
    logged_in_at: datetime | None = None

    def set_user(self, user_id: int, username: str, full_name: str = "") -> None:
        self.user_id = user_id
        self.username = username
        self.full_name = full_name
        self.logged_in_at = datetime.utcnow()

    def clear(self) -> None:
        self.user_id = None
        self.username = ""
        self.full_name = ""
        self.logged_in_at = None


current_session = CurrentSession()

