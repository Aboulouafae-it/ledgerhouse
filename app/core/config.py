from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = BASE_DIR / "backups"
ASSETS_DIR = BASE_DIR / "app" / "assets"
STYLES_DIR = ASSETS_DIR / "styles"
ICONS_DIR = ASSETS_DIR / "icons"
APP_LOGO_PATH = ICONS_DIR / "personal-ledger-pro.png"


@dataclass(frozen=True)
class AppConfig:
    app_name: str = "Personal Ledger Pro"
    default_currency: str = "EUR"
    database_path: Path = DATA_DIR / "personal_ledger.sqlite3"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path}"


config = AppConfig()


def ensure_app_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
