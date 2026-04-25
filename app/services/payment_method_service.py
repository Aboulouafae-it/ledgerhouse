from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.payment_method import PaymentMethod, PaymentMethodType
from app.repositories.payment_method_repository import PaymentMethodRepository
from app.services.audit_log_service import AuditLogService
from app.services.exceptions import ValidationError


class PaymentMethodService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = PaymentMethodRepository(session)

    def list_methods(self, active_only: bool = False) -> list[PaymentMethod]:
        return self.repo.list_methods(active_only)

    def add_method(self, name: str, type_: PaymentMethodType | None = None) -> PaymentMethod:
        name = name.strip()
        if not name:
            raise ValidationError("Payment method name is required.")
        method = self.repo.create_payment_method(name, type_ or PaymentMethodType.OTHER)
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise ValidationError("A payment method with this name already exists.") from exc
        AuditLogService(self.session).record("create payment method", "PaymentMethod", method.id, new_value={"name": method.name})
        return method

    def set_active(self, method_id: int, active: bool) -> None:
        if active:
            method = self.repo.get_by_id(method_id)
            if method:
                method.is_active = True
        else:
            self.repo.deactivate_payment_method(method_id)
        AuditLogService(self.session).record("deactivate payment method" if not active else "activate payment method", "PaymentMethod", method_id)
