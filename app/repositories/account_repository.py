from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.account import Account


class AccountRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_active_accounts(self) -> list[Account]:
        return list(self.session.scalars(select(Account).where(Account.is_active.is_(True)).order_by(Account.name)))

