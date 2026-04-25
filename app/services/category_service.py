from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.category import Category, CategoryType
from app.repositories.category_repository import CategoryRepository
from app.services.audit_log_service import AuditLogService
from app.services.exceptions import ValidationError


class CategoryService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = CategoryRepository(session)

    def list_categories(self, type_: CategoryType | None = None, active_only: bool = False) -> list[Category]:
        return self.repo.list_categories(type_, active_only)

    def add_category(self, name: str, type_: CategoryType, color: str = "#3B82F6", icon: str = "") -> Category:
        name = name.strip()
        if not name:
            raise ValidationError("Category name is required.")
        category = self.repo.create_category(name=name, type_=type_, color=color.strip() or "#3B82F6", icon=icon.strip() or None)
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise ValidationError("A category with this name already exists.") from exc
        AuditLogService(self.session).record("create category", "Category", category.id, new_value={"name": category.name, "type": category.type.value})
        return category

    def set_active(self, category_id: int, active: bool) -> None:
        if active:
            category = self.repo.get_by_id(category_id)
            if category:
                category.is_active = True
        else:
            self.repo.deactivate_category(category_id)
        AuditLogService(self.session).record("deactivate category" if not active else "activate category", "Category", category_id)
