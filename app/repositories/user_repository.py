from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.app_user import AppUser


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_active_by_username(self, username: str) -> AppUser | None:
        return self.session.scalar(select(AppUser).where(AppUser.username == username, AppUser.is_active.is_(True)))

    def get_by_id(self, user_id: int) -> AppUser | None:
        return self.session.get(AppUser, user_id)

    def get_primary_user(self) -> AppUser | None:
        return self.session.scalar(select(AppUser).order_by(AppUser.id))
