from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditLogRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_log(self, **values) -> AuditLog:  # type: ignore[no-untyped-def]
        log = AuditLog(**values)
        self.session.add(log)
        return log
