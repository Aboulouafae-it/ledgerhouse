from __future__ import annotations

from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import make_password_hash, verify_password_hash
from app.core.session import current_session
from app.models.app_user import AppUser
from app.repositories.user_repository import UserRepository
from app.services.audit_log_service import AuditLogService
from app.services.exceptions import NotFoundError, ValidationError
from app.services.settings_service import SettingsService


DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"


class AuthService:
    def __init__(self, session: Session):
        self.session = session
        self.settings = SettingsService(session)
        self.users = UserRepository(session)

    def login_enabled(self) -> bool:
        return self.settings.get_bool("login_enabled", True)

    def authenticate(self, username: str, password: str, remember_username: bool = False) -> AppUser:
        username = username.strip()
        user = self.users.get_active_by_username(username)
        if not user or not verify_password_hash(password, user.password_hash):
            raise ValidationError("Invalid username or password.")
        user.last_login_at = datetime.utcnow()
        current_session.set_user(user.id, user.username, user.full_name or "")
        self.settings.set_bool("remember_username", remember_username)
        self.settings.set("remembered_username", username if remember_username else "", "str")
        return user

    def remembered_username(self) -> str:
        return self.settings.get("remembered_username", "")

    def is_default_password(self, user: AppUser | None = None) -> bool:
        user = user or self.primary_user()
        return bool(user and verify_password_hash(DEFAULT_PASSWORD, user.password_hash))

    def primary_user(self) -> AppUser:
        user = self.users.get_primary_user()
        if not user:
            raise NotFoundError("No application user exists.")
        return user

    def update_username(self, new_username: str) -> AppUser:
        new_username = new_username.strip()
        if not new_username:
            raise ValidationError("Username is required.")
        user = self.primary_user()
        user.username = new_username
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise ValidationError("This username is already in use.") from exc
        AuditLogService(self.session).record("change username", "AppUser", user.id, new_value={"username": user.username})
        return user

    def change_password(self, current_password: str, new_password: str, confirm_password: str) -> None:
        user = self.primary_user()
        if not verify_password_hash(current_password, user.password_hash):
            raise ValidationError("Current password is incorrect.")
        if len(new_password) < 8:
            raise ValidationError("New password must be at least 8 characters.")
        if new_password != confirm_password:
            raise ValidationError("New password and confirmation do not match.")
        user.password_hash = make_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        self.settings.set_bool("default_password_warning_dismissed", False)
        AuditLogService(self.session).record("change password", "AppUser", user.id)
