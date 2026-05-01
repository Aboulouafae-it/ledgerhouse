from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import sqlite3
from pathlib import Path
from typing import Iterator

from sqlalchemy import Numeric, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.core.config import BACKUP_DIR, config, ensure_app_dirs


class Base(DeclarativeBase):
    pass


Money = Numeric(12, 2, asdecimal=True)


class TimestampMixin:
    created_at: Mapped[object]
    updated_at: Mapped[object]


engine = create_engine(config.database_url, future=True, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    ensure_app_dirs()
    # Import models before metadata creation.
    from app.models import account, app_setting, app_user, audit_log, category, debt, debt_payment, payment_method, person, report_export, settlement, shared_expense, shared_expense_participant, transaction  # noqa: F401
    from app.core.migrations import run_startup_migrations, seed_defaults

    backup_path = _backup_existing_database_before_schema_update()
    try:
        Base.metadata.create_all(bind=engine)
        run_startup_migrations(engine)
        with session_scope() as session:
            seed_defaults(session)
        run_startup_migrations(engine)
    except Exception as exc:
        if backup_path is not None:
            _restore_database_from_backup(backup_path)
        raise RuntimeError(f"Database upgrade failed. Existing data was preserved from backup: {backup_path}") from exc


def _backup_existing_database_before_schema_update() -> Path | None:
    database_path = config.database_path
    if not database_path.exists() or database_path.stat().st_size == 0:
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = BACKUP_DIR / f"personal_ledger_pre_migration_{stamp}.sqlite3"
    try:
        with sqlite3.connect(database_path) as source, sqlite3.connect(target) as destination:
            source.backup(destination)
    except Exception as exc:
        raise RuntimeError(f"Could not create safety backup before database upgrade: {target}") from exc
    return target


def _restore_database_from_backup(backup_path: Path) -> None:
    engine.dispose()
    with sqlite3.connect(backup_path) as source, sqlite3.connect(config.database_path) as destination:
        source.backup(destination)
