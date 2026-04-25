from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category, CategoryType
from app.utils.text import normalize_name


class CategoryRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_active_by_type(self, types: CategoryType | list[CategoryType]) -> list[Category]:
        type_list = types if isinstance(types, list) else [types]
        return list(self.session.scalars(select(Category).where(Category.is_active.is_(True), Category.type.in_(type_list)).order_by(Category.name)))

    def get_by_id(self, category_id: int) -> Category | None:
        return self.session.get(Category, category_id)

    def list_categories(self, type_: CategoryType | None = None, active_only: bool = False) -> list[Category]:
        stmt = select(Category).order_by(Category.type, Category.name)
        if type_:
            stmt = stmt.where(Category.type == type_)
        if active_only:
            stmt = stmt.where(Category.is_active.is_(True))
        return list(self.session.scalars(stmt))

    def create_category(self, name: str, type_: CategoryType, color: str = "#3B82F6", icon: str | None = None) -> Category:
        category = Category(name=name.strip(), normalized_name=normalize_name(name), type=type_, color=color, icon=icon, is_active=True)
        self.session.add(category)
        self.session.flush()
        return category

    def deactivate_category(self, category_id: int) -> None:
        category = self.get_by_id(category_id)
        if category:
            category.is_active = False
