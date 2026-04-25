from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.app_setting import AppSetting


class SettingRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_value(self, key: str) -> str | None:
        setting = self.session.scalar(select(AppSetting).where(AppSetting.key == key))
        return setting.value if setting else None

    def set_value(self, key: str, value: str, value_type: str | None = None) -> None:
        setting = self.session.scalar(select(AppSetting).where(AppSetting.key == key))
        if setting:
            setting.value = value
            setting.value_type = value_type or setting.value_type
            setting.updated_at = datetime.utcnow()
        else:
            self.session.add(AppSetting(key=key, value=value, value_type=value_type))

    def all_settings(self) -> dict[str, str]:
        return {setting.key: setting.value for setting in self.session.scalars(select(AppSetting))}

