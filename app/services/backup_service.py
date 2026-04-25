from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.core.backup import backup_database, restore_database
from app.services.audit_log_service import AuditLogService
from app.services.settings_service import SettingsService


class BackupService:
    def __init__(self, session: Session):
        self.session = session

    def create_backup(self) -> Path:
        target = backup_database()
        SettingsService(self.session).set("last_backup_at", target.name, "str")
        AuditLogService(self.session).record("create backup", "Backup", None, new_value={"path": str(target)})
        return target

    def restore_backup(self, source: Path) -> None:
        restore_database(source)
