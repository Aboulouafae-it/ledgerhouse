from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.core.session import current_session
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.user_repository import UserRepository


class AuditLogService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = AuditLogRepository(session)

    def record(self, action: str, entity_type: str, entity_id: int | None = None, old_value: object | None = None, new_value: object | None = None) -> None:
        try:
            actor_user_id = current_session.user_id
            if actor_user_id is not None and UserRepository(self.session).get_by_id(actor_user_id) is None:
                actor_user_id = None
            self.repo.create_log(
                actor_user_id=actor_user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                old_value=json.dumps(old_value, default=str) if old_value is not None else None,
                new_value=json.dumps(new_value, default=str) if new_value is not None else None,
            )
        except Exception:
            # Audit logging must never break the user operation.
            return
