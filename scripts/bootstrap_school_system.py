from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from web.backend.db import SchoolRepository
from web.backend.settings import get_settings


if __name__ == "__main__":
    settings = get_settings()
    repository = SchoolRepository(settings)
    repository.initialize()
    print("School system database initialized.")
    print("Database:", settings.database_path)
    print("Admin email:", settings.admin_email)
    print("Admin password:", settings.admin_password)
    print("Student email: edson@prepateam.mx | Password: prepateam")
    print("Student email: francisco@prepateam.mx | Password: prepateam")
    print("Student email: alan@prepateam.mx | Password: prepateam")
