from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.person import Person
from app.repositories.person_repository import PersonRepository
from app.services.audit_log_service import AuditLogService
from app.services.exceptions import ValidationError
from app.utils.text import normalize_name


class PersonService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = PersonRepository(session)

    def list_people(self) -> list[Person]:
        return self.repo.search_people()

    def active_people(self) -> list[Person]:
        return self.repo.get_active_people()

    def creditors(self) -> list[Person]:
        return self.repo.get_creditors()

    def debtors(self) -> list[Person]:
        return self.repo.get_debtors()

    def creditor_debtors(self) -> list[Person]:
        return [p for p in self.active_people() if p.is_creditor or p.is_debtor]

    def house_members(self) -> list[Person]:
        return self.repo.get_house_members()

    def filtered(self, search: str = "", role_filter: str = "All") -> list[Person]:
        return self.repo.search_people(search, role_filter)

    def add_person(
        self,
        *,
        name: str,
        phone: str | None = None,
        email: str | None = None,
        is_house_member: bool = False,
        is_creditor: bool = False,
        is_debtor: bool = False,
        note: str | None = None,
    ) -> Person:
        name = name.strip()
        if not name:
            raise ValidationError("Name is required.")
        existing = self.repo.find_by_normalized_name(name)
        if existing and existing.is_active:
            raise ValidationError("A person with this name already exists.")
        if existing and not existing.is_active:
            updated = self.repo.update_person(
                existing,
                name=name,
                phone=(phone or "").strip() or None,
                email=(email or "").strip() or None,
                note=(note or "").strip() or None,
                is_house_member=existing.is_house_member or is_house_member,
                is_creditor=existing.is_creditor or is_creditor,
                is_debtor=existing.is_debtor or is_debtor,
                is_active=True,
            )
            AuditLogService(self.session).record("reactivate person", "Person", updated.id, new_value={"name": updated.name})
            return updated
        person = self.repo.create_person(
            name=name,
            normalized_name=normalize_name(name),
            phone=(phone or "").strip() or None,
            email=(email or "").strip() or None,
            note=(note or "").strip() or None,
            is_house_member=is_house_member,
            is_creditor=is_creditor,
            is_debtor=is_debtor,
            is_active=True,
        )
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise ValidationError("A person with this name already exists.") from exc
        AuditLogService(self.session).record("create person", "Person", person.id, new_value={"name": person.name})
        return person

    def find_by_name(self, name: str) -> Person | None:
        return self.repo.find_by_normalized_name(name)

    def add_or_update_person(
        self,
        *,
        name: str,
        phone: str | None = None,
        email: str | None = None,
        is_house_member: bool = False,
        is_creditor: bool = False,
        is_debtor: bool = False,
        note: str | None = None,
    ) -> Person:
        existing = self.find_by_name(name)
        if existing:
            existing.phone = (phone or existing.phone or "").strip() or None
            existing.email = (email or existing.email or "").strip() or None
            existing.note = (note or existing.note or "").strip() or None
            existing.is_house_member = existing.is_house_member or is_house_member
            existing.is_creditor = existing.is_creditor or is_creditor
            existing.is_debtor = existing.is_debtor or is_debtor
            existing.is_active = True
            AuditLogService(self.session).record("update person", "Person", existing.id, new_value={"roles": self.role_summary()})
            return existing
        return self.add_person(
            name=name,
            phone=phone,
            email=email,
            is_house_member=is_house_member,
            is_creditor=is_creditor,
            is_debtor=is_debtor,
            note=note,
        )

    def update_roles(self, person_id: int, *, is_creditor: bool | None = None, is_debtor: bool | None = None, is_house_member: bool | None = None, is_active: bool | None = None) -> None:
        person = self.repo.get_by_id(person_id)
        if not person:
            raise ValidationError("Person not found.")
        if is_creditor is not None:
            person.is_creditor = is_creditor
        if is_debtor is not None:
            person.is_debtor = is_debtor
        if is_house_member is not None:
            person.is_house_member = is_house_member
        if is_active is not None:
            person.is_active = is_active
        AuditLogService(self.session).record("update person", "Person", person.id, new_value={"active": person.is_active})

    def role_summary(self) -> dict[str, int]:
        people = self.list_people()
        return {
            "creditors": sum(1 for p in people if p.is_active and p.is_creditor),
            "debtors": sum(1 for p in people if p.is_active and p.is_debtor),
            "house_members": sum(1 for p in people if p.is_active and p.is_house_member),
            "active": sum(1 for p in people if p.is_active),
        }
