from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    root_dir: Path = ROOT_DIR
    database_path: Path = Path(os.getenv("SCHOOL_DB_PATH", ROOT_DIR / "data" / "app" / "school.db"))
    templates_dir: Path = ROOT_DIR / "web" / "frontend" / "templates"
    static_dir: Path = ROOT_DIR / "web" / "frontend" / "static"
    session_cookie_name: str = os.getenv("SESSION_COOKIE_NAME", "prepa_team_session")
    session_days: int = int(os.getenv("SESSION_DAYS", "7"))
    app_secret: str = os.getenv("APP_SECRET", "prepa-team-demo-secret")
    admin_email: str = os.getenv("ADMIN_EMAIL", "admin@prepateam.local")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "Admin1234!")
    admin_name: str = os.getenv("ADMIN_NAME", "Director Demo")
    school_name: str = os.getenv("SCHOOL_NAME", "Sistema de control escolar")


def get_settings() -> Settings:
    return Settings()
