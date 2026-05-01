from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.person import Person
from app.repositories.person_repository import PersonRepository
from app.repositories.setting_repository import SettingRepository
from app.services.audit_log_service import AuditLogService
from app.services.exceptions import ValidationError
from app.utils.text import normalize_name


class SettingsService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = SettingRepository(session)

    def get(self, key: str, default: str = "") -> str:
        return self.repo.get_value(key) or default

    def get_bool(self, key: str, default: bool = False) -> bool:
        value = self.get(key, "true" if default else "false").strip().lower()
        return value in {"1", "true", "yes", "on"}

    def set(self, key: str, value: str, type_: str | None = None) -> None:
        self.repo.set_value(key, value, type_)

    def set_bool(self, key: str, value: bool) -> None:
        self.set(key, "true" if value else "false", "bool")

    def get_str(self, key: str, default: str = "") -> str:
        return self.get(key, default)

    def get_int(self, key: str, default: int = 0) -> int:
        try:
            return int(self.get(key, str(default)))
        except ValueError:
            return default

    def get_decimal(self, key: str, default: Decimal = Decimal("0.00")) -> Decimal:
        try:
            return Decimal(self.get(key, str(default)))
        except Exception:
            return default

    def set_value(self, key: str, value: str | int | Decimal | bool, type_: str | None = None) -> None:
        if isinstance(value, bool):
            self.set_bool(key, value)
        else:
            self.set(key, str(value), type_)

    def all_settings(self) -> dict[str, str]:
        return self.repo.all_settings()

    def update_many(self, values: dict[str, str]) -> None:
        for key, value in values.items():
            if key == "owner_name":
                self.set_owner_name(value)
            else:
                self.set(key, value)

    def owner_person_id(self) -> int | None:
        raw = self.get("owner_person_id", "").strip()
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    def owner_person(self) -> Person | None:
        owner_id = self.owner_person_id()
        if owner_id is None:
            return None
        person = PersonRepository(self.session).get_by_id(owner_id)
        if person and person.is_active:
            return person
        return None

    def set_owner_name(self, name: str) -> Person | None:
        name = name.strip()
        if not name:
            raise ValidationError("Owner name is required.")

        repo = PersonRepository(self.session)
        owner = self.owner_person()
        matching = repo.find_by_normalized_name(name)
        normalized = normalize_name(name)

        if matching and owner and matching.id != owner.id:
            person = repo.update_person(
                matching,
                is_house_member=True,
                is_active=True,
            )
        elif owner:
            if matching and matching.id == owner.id:
                person = owner
            elif matching is None or normalize_name(owner.name) == normalized:
                person = repo.update_person(
                    owner,
                    name=name,
                    is_house_member=True,
                    is_active=True,
                )
            else:
                raise ValidationError("A different person with this owner name already exists.")
        elif matching:
            person = repo.update_person(
                matching,
                is_house_member=True,
                is_active=True,
            )
        else:
            person = repo.create_person(
                name=name,
                normalized_name=normalized,
                is_house_member=True,
                is_active=True,
            )

        self.set("owner_name", person.name, "str")
        self.set("owner_person_id", str(person.id), "int")
        AuditLogService(self.session).record("set owner person", "Person", person.id, new_value={"name": person.name})
        return person
