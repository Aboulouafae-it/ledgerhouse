from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.security import make_password_hash
from app.models.account import Account, AccountType
from app.models.app_setting import AppSetting
from app.models.app_user import AppUser
from app.models.category import Category, CategoryType
from app.models.payment_method import PaymentMethod, PaymentMethodType
from app.models.person import Person
from app.utils.text import normalize_name

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 2


def get_existing_tables(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names())


def get_existing_columns(engine: Engine, table_name: str) -> set[str]:
    if table_name not in get_existing_tables(engine):
        return set()
    return {column["name"] for column in inspect(engine).get_columns(table_name)}


def run_startup_migrations(engine: Engine) -> None:
    ensure_columns(engine)
    ensure_indexes(engine)


def ensure_columns(engine: Engine) -> None:
    with engine.begin() as conn:
        _add_missing_columns(
            conn,
            "people",
            {
                "normalized_name": "VARCHAR(140) NOT NULL DEFAULT ''",
                "is_creditor": "BOOLEAN NOT NULL DEFAULT 0",
                "is_debtor": "BOOLEAN NOT NULL DEFAULT 0",
                "is_employer": "BOOLEAN NOT NULL DEFAULT 0",
                "is_service_provider": "BOOLEAN NOT NULL DEFAULT 0",
                "is_family_friend": "BOOLEAN NOT NULL DEFAULT 0",
                "is_house_member": "BOOLEAN NOT NULL DEFAULT 0",
                "is_active": "BOOLEAN NOT NULL DEFAULT 1",
                "note": "TEXT",
            },
        )
        _add_missing_columns(
            conn,
            "categories",
            {
                "normalized_name": "VARCHAR(140) NOT NULL DEFAULT ''",
                "is_active": "BOOLEAN NOT NULL DEFAULT 1",
                "created_at": "DATETIME",
                "updated_at": "DATETIME",
            },
        )
        _add_missing_columns(conn, "payment_methods", {"normalized_name": "VARCHAR(120) NOT NULL DEFAULT ''"})
        _add_missing_columns(conn, "app_settings", {"value_type": "VARCHAR(40)"})
        if "type" in _columns(conn, "app_settings") and "value_type" in _columns(conn, "app_settings"):
            conn.execute(text("UPDATE app_settings SET value_type = type WHERE value_type IS NULL AND type IS NOT NULL"))
        _add_missing_columns(
            conn,
            "transactions",
            {
                "account_id": "INTEGER REFERENCES accounts(id) ON DELETE SET NULL",
                "payment_method_id": "INTEGER REFERENCES payment_methods(id) ON DELETE SET NULL",
                "reference_type": "VARCHAR(60)",
                "reference_id": "INTEGER",
                "is_active": "BOOLEAN NOT NULL DEFAULT 1",
                "deleted_at": "DATETIME",
            },
        )
        _add_missing_columns(
            conn,
            "debts",
            {
                "currency": "VARCHAR(3) NOT NULL DEFAULT 'EUR'",
                "created_transaction_id": "INTEGER REFERENCES transactions(id) ON DELETE SET NULL",
            },
        )
        _add_missing_columns(
            conn,
            "debt_payments",
            {
                "currency": "VARCHAR(3) NOT NULL DEFAULT 'EUR'",
                "payment_method_id": "INTEGER REFERENCES payment_methods(id) ON DELETE SET NULL",
                "transaction_id": "INTEGER REFERENCES transactions(id) ON DELETE SET NULL",
                "updated_at": "DATETIME",
            },
        )
        _add_missing_columns(
            conn,
            "shared_expenses",
            {
                "payment_method_id": "INTEGER REFERENCES payment_methods(id) ON DELETE SET NULL",
                "transaction_id": "INTEGER REFERENCES transactions(id) ON DELETE SET NULL",
            },
        )
        _add_missing_columns(
            conn,
            "shared_expense_participants",
            {
                "created_at": "DATETIME",
                "updated_at": "DATETIME",
            },
        )
        _backfill_people_roles(conn)


def ensure_indexes(engine: Engine) -> None:
    statements = [
        "CREATE INDEX IF NOT EXISTS ix_people_normalized_name ON people(normalized_name)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_people_normalized_name_active ON people(normalized_name) WHERE is_active = 1 AND normalized_name != ''",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_categories_normalized_name_type ON categories(normalized_name, type)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_payment_methods_normalized_name ON payment_methods(normalized_name)",
        "CREATE INDEX IF NOT EXISTS ix_transactions_date ON transactions(date)",
        "CREATE INDEX IF NOT EXISTS ix_transactions_type ON transactions(type)",
        "CREATE INDEX IF NOT EXISTS ix_transactions_person_id ON transactions(person_id)",
        "CREATE INDEX IF NOT EXISTS ix_transactions_category_id ON transactions(category_id)",
        "CREATE INDEX IF NOT EXISTS ix_debts_person_id ON debts(person_id)",
        "CREATE INDEX IF NOT EXISTS ix_debts_status ON debts(status)",
        "CREATE INDEX IF NOT EXISTS ix_debts_due_date ON debts(due_date)",
        "CREATE INDEX IF NOT EXISTS ix_shared_expenses_date ON shared_expenses(date)",
        "CREATE INDEX IF NOT EXISTS ix_shared_expenses_paid_by_person_id ON shared_expenses(paid_by_person_id)",
        "CREATE INDEX IF NOT EXISTS ix_shared_expense_participants_person_id ON shared_expense_participants(person_id)",
        "CREATE INDEX IF NOT EXISTS ix_settlements_status ON settlements(status)",
        "CREATE INDEX IF NOT EXISTS ix_settlements_from_person_id ON settlements(from_person_id)",
        "CREATE INDEX IF NOT EXISTS ix_settlements_to_person_id ON settlements(to_person_id)",
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs(created_at)",
        "CREATE INDEX IF NOT EXISTS ix_report_exports_created_at ON report_exports(created_at)",
    ]
    with engine.begin() as conn:
        for statement in statements:
            try:
                conn.execute(text(statement))
            except Exception as exc:
                logger.warning("Skipping non-destructive migration statement %s: %s", statement, exc)


def seed_defaults(session: Session) -> None:
    _seed_settings(session)
    _seed_admin(session)
    _seed_categories(session)
    _seed_payment_methods(session)
    _seed_account(session)
    _backfill_existing_people(session)


def _seed_settings(session: Session) -> None:
    defaults = {
        "schema_version": (str(SCHEMA_VERSION), "int"),
        "login_enabled": ("true", "bool"),
        "remember_username": ("false", "bool"),
        "remembered_username": ("", "str"),
        "default_password_warning_dismissed": ("false", "bool"),
        "owner_name": ("", "str"),
        "owner_person_id": ("", "int"),
        "default_currency": ("EUR", "str"),
        "default_language": ("English", "str"),
        "date_format": ("YYYY-MM-DD", "str"),
        "first_day_of_week": ("Monday", "str"),
        "default_dashboard_period": ("this month", "str"),
        "auto_lock": ("disabled", "str"),
        "report_title_prefix": ("Personal Ledger Pro", "str"),
        "report_footer_text": ("Generated by Personal Ledger Pro", "str"),
        "report_logo_path": ("app/assets/icons/personal-ledger-pro.png", "str"),
        "report_language": ("English", "str"),
        "report_include_charts": ("false", "bool"),
        "report_include_signature": ("true", "bool"),
        "theme": ("dark", "str"),
        "accent_color": ("blue", "str"),
        "compact_mode": ("false", "bool"),
        "table_density": ("comfortable", "str"),
        "last_backup_at": ("", "str"),
    }
    existing = {row[0] for row in session.execute(select(AppSetting.key)).all()}
    for key, (value, kind) in defaults.items():
        if key not in existing:
            session.add(AppSetting(key=key, value=value, value_type=kind))


def _seed_admin(session: Session) -> None:
    if session.scalar(select(AppUser).limit(1)) is None:
        session.add(AppUser(username="admin", password_hash=make_password_hash("admin123"), full_name="Administrator"))


def _seed_categories(session: Session) -> None:
    defaults = [
        ("Salary", CategoryType.INCOME, "#22C55E", "wallet"),
        ("Extra Income", CategoryType.INCOME, "#10B981", "plus"),
        ("Food", CategoryType.EXPENSE, "#EF4444", "utensils"),
        ("Rent", CategoryType.EXPENSE, "#F97316", "home"),
        ("Gas", CategoryType.EXPENSE, "#F59E0B", "fuel"),
        ("Internet", CategoryType.EXPENSE, "#3B82F6", "wifi"),
        ("Transport", CategoryType.EXPENSE, "#06B6D4", "bus"),
        ("Health", CategoryType.EXPENSE, "#EC4899", "heart"),
        ("Debt", CategoryType.DEBT, "#A855F7", "receipt"),
        ("Savings", CategoryType.SAVING, "#EAB308", "vault"),
        ("Shared Living", CategoryType.SHARED, "#14B8A6", "users"),
        ("Other", CategoryType.EXPENSE, "#9CA3AF", "circle"),
    ]
    existing = {(normalize_name(row[0]), row[1]) for row in session.execute(select(Category.name, Category.type)).all()}
    for name, kind, color, icon in defaults:
        normalized = normalize_name(name)
        if (normalized, kind) not in existing:
            session.add(Category(name=name, normalized_name=normalized, type=kind, color=color, icon=icon, is_active=True))
    default_types = {normalize_name(name): kind for name, kind, _color, _icon in defaults}
    categories = list(session.scalars(select(Category)).all())
    existing_pairs = {(category.normalized_name or normalize_name(category.name), category.type) for category in categories}
    for category in categories:
        category.normalized_name = category.normalized_name or normalize_name(category.name)
        expected_type = default_types.get(category.normalized_name)
        if expected_type is not None and category.type != expected_type and (category.normalized_name, expected_type) not in existing_pairs:
            existing_pairs.discard((category.normalized_name, category.type))
            category.type = expected_type
            existing_pairs.add((category.normalized_name, category.type))


def _seed_payment_methods(session: Session) -> None:
    defaults = [
        ("Cash", PaymentMethodType.CASH),
        ("Bank Transfer", PaymentMethodType.TRANSFER),
        ("Card", PaymentMethodType.CARD),
        ("PayPal", PaymentMethodType.OTHER),
        ("Other", PaymentMethodType.OTHER),
    ]
    existing = {normalize_name(row[0]) for row in session.execute(select(PaymentMethod.name)).all()}
    for name, kind in defaults:
        if normalize_name(name) not in existing:
            session.add(PaymentMethod(name=name, normalized_name=normalize_name(name), type=kind))
    for method in session.scalars(select(PaymentMethod)).all():
        method.normalized_name = method.normalized_name or normalize_name(method.name)


def _seed_account(session: Session) -> None:
    if session.scalar(select(Account).limit(1)) is None:
        session.add(Account(name="Cash Wallet", type=AccountType.CASH, currency="EUR", opening_balance=Decimal("0.00")))


def _backfill_existing_people(session: Session) -> None:
    for person in session.scalars(select(Person)).all():
        person.normalized_name = person.normalized_name or normalize_name(person.name)


def _add_missing_columns(conn, table_name: str, columns: dict[str, str]) -> None:  # type: ignore[no-untyped-def]
    existing = _columns(conn, table_name)
    if not existing:
        return
    for name, ddl in columns.items():
        if name not in existing:
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {name} {ddl}"))


def _columns(conn, table_name: str) -> set[str]:  # type: ignore[no-untyped-def]
    return {row[1] for row in conn.execute(text(f"PRAGMA table_info({table_name})")).all()}


def _backfill_people_roles(conn) -> None:  # type: ignore[no-untyped-def]
    people_columns = _columns(conn, "people")
    if not {"normalized_name", "is_creditor", "is_debtor", "is_house_member", "is_active"}.issubset(people_columns):
        return
    conn.execute(text("UPDATE people SET normalized_name = lower(trim(name)) WHERE normalized_name = '' OR normalized_name IS NULL"))
    tables = {row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).all()}
    if "debts" in tables:
        conn.execute(
            text(
                """
                UPDATE people
                SET is_creditor = 1
                WHERE id IN (
                    SELECT person_id FROM debts WHERE direction = 'I_OWE_HIM' AND person_id IS NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE people
                SET is_debtor = 1
                WHERE id IN (
                    SELECT person_id FROM debts WHERE direction = 'HE_OWES_ME' AND person_id IS NOT NULL
                )
                """
            )
        )
    conn.execute(text("UPDATE people SET is_creditor = 1, is_debtor = 1 WHERE is_house_member = 1 AND is_creditor = 0 AND is_debtor = 0"))
