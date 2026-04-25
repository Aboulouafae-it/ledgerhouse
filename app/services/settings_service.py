from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.setting_repository import SettingRepository


class SettingsService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = SettingRepository(session)

    def get(self, key: str, default: str = "") -> str:
        return self.repo.get_value(key) or default

    def get_bool(self, key: str, default: bool = False) -> bool:
        value = self.get(key, "true" if default else "false").strip().lower()
        return value in {"1", "true", "yes", "on"}

    def set(self, key: str, value: str, type_: str | None = None) -> None:
        self.repo.set_value(key, value, type_)

    def set_bool(self, key: str, value: bool) -> None:
        self.set(key, "true" if value else "false", "bool")

    def get_str(self, key: str, default: str = "") -> str:
        return self.get(key, default)

    def get_int(self, key: str, default: int = 0) -> int:
        try:
            return int(self.get(key, str(default)))
        except ValueError:
            return default

    def get_decimal(self, key: str, default: Decimal = Decimal("0.00")) -> Decimal:
        try:
            return Decimal(self.get(key, str(default)))
        except Exception:
            return default

    def set_value(self, key: str, value: str | int | Decimal | bool, type_: str | None = None) -> None:
        if isinstance(value, bool):
            self.set_bool(key, value)
        else:
            self.set(key, str(value), type_)

    def all_settings(self) -> dict[str, str]:
        return self.repo.all_settings()

    def update_many(self, values: dict[str, str]) -> None:
        for key, value in values.items():
            self.set(key, value)
