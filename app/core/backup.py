from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from app.core.config import BACKUP_DIR, config


def backup_database() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = BACKUP_DIR / f"personal_ledger_{stamp}.sqlite3"
    with sqlite3.connect(config.database_path) as source, sqlite3.connect(target) as destination:
        source.backup(destination)
    return target


def restore_database(source: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(source)
    from app.core.database import engine

    engine.dispose()
    emergency = backup_database()
    with sqlite3.connect(source) as restored, sqlite3.connect(config.database_path) as current:
        restored.backup(current)
