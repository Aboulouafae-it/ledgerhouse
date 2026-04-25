from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.settlement import Settlement


class SettlementRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_settlement(self, **values) -> Settlement:  # type: ignore[no-untyped-def]
        settlement = Settlement(**values)
        self.session.add(settlement)
        self.session.flush()
        return settlement
