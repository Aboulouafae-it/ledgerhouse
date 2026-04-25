from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.payment_method import PaymentMethod, PaymentMethodType
from app.utils.text import normalize_name


class PaymentMethodRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_active_methods(self) -> list[PaymentMethod]:
        return list(self.session.scalars(select(PaymentMethod).where(PaymentMethod.is_active.is_(True)).order_by(PaymentMethod.name)))

    def get_by_id(self, method_id: int) -> PaymentMethod | None:
        return self.session.get(PaymentMethod, method_id)

    def list_methods(self, active_only: bool = False) -> list[PaymentMethod]:
        stmt = select(PaymentMethod).order_by(PaymentMethod.name)
        if active_only:
            stmt = stmt.where(PaymentMethod.is_active.is_(True))
        return list(self.session.scalars(stmt))

    def create_payment_method(self, name: str, type_: PaymentMethodType | None = None) -> PaymentMethod:
        method = PaymentMethod(name=name.strip(), normalized_name=normalize_name(name), type=type_ or PaymentMethodType.OTHER, is_active=True)
        self.session.add(method)
        self.session.flush()
        return method

    def deactivate_payment_method(self, method_id: int) -> None:
        method = self.get_by_id(method_id)
        if method:
            method.is_active = False
