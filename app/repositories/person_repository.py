from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.person import Person
from app.utils.text import normalize_name


class PersonRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_person(self, **values) -> Person:  # type: ignore[no-untyped-def]
        values["normalized_name"] = normalize_name(values["name"])
        person = Person(**values)
        self.session.add(person)
        self.session.flush()
        return person

    def update_person(self, person: Person, **values) -> Person:  # type: ignore[no-untyped-def]
        if "name" in values:
            values["normalized_name"] = normalize_name(values["name"])
        for key, value in values.items():
            setattr(person, key, value)
        self.session.flush()
        return person

    def deactivate_person(self, person_id: int) -> None:
        person = self.get_by_id(person_id)
        if person:
            person.is_active = False

    def get_by_id(self, person_id: int) -> Person | None:
        return self.session.get(Person, person_id)

    def find_by_normalized_name(self, name: str) -> Person | None:
        return self.session.scalar(select(Person).where(Person.normalized_name == normalize_name(name)))

    def get_active_people(self) -> list[Person]:
        return list(self.session.scalars(select(Person).where(Person.is_active.is_(True)).order_by(Person.name)))

    def get_creditors(self) -> list[Person]:
        return list(self.session.scalars(select(Person).where(Person.is_active.is_(True), Person.is_creditor.is_(True)).order_by(Person.name)))

    def get_debtors(self) -> list[Person]:
        return list(self.session.scalars(select(Person).where(Person.is_active.is_(True), Person.is_debtor.is_(True)).order_by(Person.name)))

    def get_house_members(self) -> list[Person]:
        return list(self.session.scalars(select(Person).where(Person.is_active.is_(True), Person.is_house_member.is_(True)).order_by(Person.name)))

    def existing_active_ids(self, person_ids: list[int]) -> set[int]:
        return set(self.session.scalars(select(Person.id).where(Person.id.in_(person_ids), Person.is_active.is_(True))).all())

    def search_people(self, search: str = "", role_filter: str = "All") -> list[Person]:
        stmt = select(Person).order_by(Person.name)
        if search.strip():
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(or_(Person.name.ilike(pattern), Person.email.ilike(pattern), Person.phone.ilike(pattern)))
        if role_filter == "Creditors":
            stmt = stmt.where(Person.is_creditor.is_(True))
        elif role_filter == "Debtors":
            stmt = stmt.where(Person.is_debtor.is_(True))
        elif role_filter == "House members":
            stmt = stmt.where(Person.is_house_member.is_(True))
        elif role_filter == "Active":
            stmt = stmt.where(Person.is_active.is_(True))
        elif role_filter == "Inactive":
            stmt = stmt.where(Person.is_active.is_(False))
        return list(self.session.scalars(stmt))
