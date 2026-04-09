from __future__ import annotations

import csv
import io
import sqlite3
from pathlib import Path
from typing import Any

from student_success.config import ADVICE_FEATURES

from .security import hash_password, iso_in_days, iso_now, new_session_token, verify_password
from .settings import Settings


PROFILE_FIELDS = {
    "Age": "age",
    "StudyTimeWeekly": "study_time_weekly",
    "Absences": "absences",
    "ParentalEducation": "parental_education",
    "Tutoring": "tutoring",
    "ParentalSupport": "parental_support",
    "Extracurricular": "extracurricular",
    "Sports": "sports",
    "Music": "music",
    "Volunteering": "volunteering",
}


DEMO_STUDENTS = [
    {
        "student_code": "PT001",
        "full_name": "Edson Manuel Zepeda Chavez",
        "group_name": "6A",
        "current_period": "2026-A",
        "email": "edson@prepateam.mx",
        "password": "prepateam",
        "profile": {
            "Age": 17,
            "StudyTimeWeekly": 4,
            "Absences": 15,
            "ParentalEducation": 1,
            "Tutoring": 0,
            "ParentalSupport": 1,
            "Extracurricular": 0,
            "Sports": 0,
            "Music": 0,
            "Volunteering": 0,
        },
        "grades": {
            "Matematicas": 5.8,
            "Fisica": 5.3,
            "Programacion": 6.1,
            "Ingles": 6.4,
            "Comunicacion": 5.9,
        },
    },
    {
        "student_code": "PT002",
        "full_name": "Francisco Ricardo Moreno Sanchez",
        "group_name": "6B",
        "current_period": "2026-A",
        "email": "francisco@prepateam.mx",
        "password": "prepateam",
        "profile": {
            "Age": 17,
            "StudyTimeWeekly": 14,
            "Absences": 2,
            "ParentalEducation": 3,
            "Tutoring": 1,
            "ParentalSupport": 4,
            "Extracurricular": 1,
            "Sports": 1,
            "Music": 1,
            "Volunteering": 1,
        },
        "grades": {
            "Matematicas": 9.6,
            "Fisica": 9.3,
            "Programacion": 9.8,
            "Ingles": 9.4,
            "Comunicacion": 9.5,
        },
    },
    {
        "student_code": "PT003",
        "full_name": "Alan Emir Martinez Espinosa",
        "group_name": "6B",
        "current_period": "2026-A",
        "email": "alan@prepateam.mx",
        "password": "prepateam",
        "profile": {
            "Age": 17,
            "StudyTimeWeekly": 6,
            "Absences": 10,
            "ParentalEducation": 2,
            "Tutoring": 0,
            "ParentalSupport": 2,
            "Extracurricular": 0,
            "Sports": 1,
            "Music": 0,
            "Volunteering": 0,
        },
        "grades": {
            "Matematicas": 7.1,
            "Fisica": 6.8,
            "Programacion": 7.4,
            "Ingles": 7.2,
            "Comunicacion": 7.0,
        },
    },
]


class SchoolRepository:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _connect(self) -> sqlite3.Connection:
        self.settings.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.settings.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_code TEXT NOT NULL UNIQUE,
                    full_name TEXT NOT NULL,
                    group_name TEXT,
                    current_period TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('admin', 'student')),
                    student_id INTEGER,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS student_profiles (
                    student_id INTEGER PRIMARY KEY,
                    age INTEGER,
                    study_time_weekly REAL,
                    absences INTEGER,
                    parental_education INTEGER,
                    tutoring INTEGER,
                    parental_support INTEGER,
                    extracurricular INTEGER,
                    sports INTEGER,
                    music INTEGER,
                    volunteering INTEGER,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS subjects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    is_active INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS grade_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    subject_id INTEGER NOT NULL,
                    period TEXT NOT NULL,
                    grade REAL NOT NULL,
                    status TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    UNIQUE(student_id, subject_id, period),
                    FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
                    FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS audit_imports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uploaded_by INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    total_rows INTEGER NOT NULL,
                    inserted_rows INTEGER NOT NULL,
                    updated_rows INTEGER NOT NULL,
                    error_rows INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(uploaded_by) REFERENCES users(id) ON DELETE CASCADE
                );
                """
            )
            connection.commit()
        self.bootstrap_admin()
        self.bootstrap_demo_students()

    def bootstrap_admin(self) -> None:
        if self.get_user_by_email(self.settings.admin_email):
            return
        self.create_user(
            email=self.settings.admin_email,
            password=self.settings.admin_password,
            role="admin",
        )

    def bootstrap_demo_students(self) -> None:
        for item in DEMO_STUDENTS:
            student = self.get_student_by_code(item["student_code"])
            if student:
                student_id = int(student["id"])
                self.update_student(
                    student_id=student_id,
                    student_code=item["student_code"],
                    full_name=item["full_name"],
                    group_name=item["group_name"],
                    current_period=item["current_period"],
                    is_active=True,
                )
            else:
                student_id = self.create_student(
                    student_code=item["student_code"],
                    full_name=item["full_name"],
                    group_name=item["group_name"],
                    current_period=item["current_period"],
                )

            self.create_or_update_student_user(student_id, item["email"], item["password"])
            self.upsert_profile(student_id, item["profile"])

            for subject_name, grade in item["grades"].items():
                subject_id = self.get_or_create_subject(subject_name)
                self.upsert_grade_record(
                    student_id=student_id,
                    subject_id=subject_id,
                    period=item["current_period"],
                    grade=grade,
                    source="seed",
                )

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT users.*, students.full_name AS student_name
                FROM users
                LEFT JOIN students ON students.id = users.student_id
                WHERE lower(users.email) = lower(?)
                """,
                (email,),
            ).fetchone()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT users.*, students.full_name AS student_name
                FROM users
                LEFT JOIN students ON students.id = users.student_id
                WHERE users.id = ?
                """,
                (user_id,),
            ).fetchone()
        return dict(row) if row else None

    def create_user(self, email: str, password: str, role: str, student_id: int | None = None) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO users (email, password_hash, role, student_id, is_active, created_at)
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (email.strip().lower(), hash_password(password), role, student_id, iso_now()),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def create_or_update_student_user(self, student_id: int, email: str, password: str) -> int:
        existing = self.get_student_user(student_id)
        existing_by_email = self.get_user_by_email(email)
        with self._connect() as connection:
            if existing:
                connection.execute(
                    """
                    UPDATE users
                    SET email = ?, password_hash = ?, is_active = 1
                    WHERE id = ?
                    """,
                    (email.strip().lower(), hash_password(password), existing["id"]),
                )
                connection.commit()
                return int(existing["id"])
            if existing_by_email:
                connection.execute(
                    """
                    UPDATE users
                    SET email = ?, password_hash = ?, role = 'student', student_id = ?, is_active = 1
                    WHERE id = ?
                    """,
                    (email.strip().lower(), hash_password(password), student_id, existing_by_email["id"]),
                )
                connection.commit()
                return int(existing_by_email["id"])
        return self.create_user(email=email, password=password, role="student", student_id=student_id)

    def authenticate_user(self, email: str, password: str) -> dict[str, Any] | None:
        user = self.get_user_by_email(email)
        if not user or not user["is_active"]:
            return None
        if not verify_password(password, user["password_hash"]):
            return None
        return user

    def create_session(self, user_id: int) -> str:
        token = new_session_token()
        with self._connect() as connection:
            connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (iso_now(),))
            connection.execute(
                """
                INSERT INTO sessions (token, user_id, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (token, user_id, iso_now(), iso_in_days(self.settings.session_days)),
            )
            connection.commit()
        return token

    def get_session_user(self, token: str | None) -> dict[str, Any] | None:
        if not token:
            return None
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT users.*, students.full_name AS student_name
                FROM sessions
                JOIN users ON users.id = sessions.user_id
                LEFT JOIN students ON students.id = users.student_id
                WHERE sessions.token = ? AND sessions.expires_at > ?
                """,
                (token, iso_now()),
            ).fetchone()
        return dict(row) if row else None

    def delete_session(self, token: str | None) -> None:
        if not token:
            return
        with self._connect() as connection:
            connection.execute("DELETE FROM sessions WHERE token = ?", (token,))
            connection.commit()

    def list_students(self, search: str = "") -> list[dict[str, Any]]:
        search = f"%{search.strip().lower()}%"
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    students.*,
                    users.email AS account_email,
                    ROUND(AVG(grade_records.grade), 2) AS school_average,
                    COUNT(grade_records.id) AS grade_count,
                    SUM(CASE WHEN grade_records.status = 'failed' THEN 1 ELSE 0 END) AS failed_count
                FROM students
                LEFT JOIN users ON users.student_id = students.id AND users.role = 'student'
                LEFT JOIN grade_records ON grade_records.student_id = students.id
                WHERE (? = '%%' OR lower(students.full_name) LIKE ? OR lower(students.student_code) LIKE ?)
                GROUP BY students.id, users.email
                ORDER BY students.full_name COLLATE NOCASE
                """,
                (search, search, search),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_student(self, student_code: str, full_name: str, group_name: str, current_period: str) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO students (student_code, full_name, group_name, current_period, is_active, created_at)
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (student_code.strip(), full_name.strip(), group_name.strip(), current_period.strip(), iso_now()),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def update_student(self, student_id: int, student_code: str, full_name: str, group_name: str, current_period: str, is_active: bool) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE students
                SET student_code = ?, full_name = ?, group_name = ?, current_period = ?, is_active = ?
                WHERE id = ?
                """,
                (student_code.strip(), full_name.strip(), group_name.strip(), current_period.strip(), int(is_active), student_id),
            )
            connection.commit()

    def get_student(self, student_id: int) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT students.*, users.email AS account_email
                FROM students
                LEFT JOIN users ON users.student_id = students.id AND users.role = 'student'
                WHERE students.id = ?
                """,
                (student_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_student_by_code(self, student_code: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM students WHERE student_code = ?",
                (student_code.strip(),),
            ).fetchone()
        return dict(row) if row else None

    def get_student_by_user_id(self, user_id: int) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT students.*
                FROM students
                JOIN users ON users.student_id = students.id
                WHERE users.id = ?
                """,
                (user_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_student_user(self, student_id: int) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE student_id = ? AND role = 'student'",
                (student_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_profile(self, student_id: int) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM student_profiles WHERE student_id = ?",
                (student_id,),
            ).fetchone()
        if not row:
            return {
                "student_id": student_id,
                "age": None,
                "study_time_weekly": None,
                "absences": None,
                "parental_education": None,
                "tutoring": None,
                "parental_support": None,
                "extracurricular": None,
                "sports": None,
                "music": None,
                "volunteering": None,
            }
        return dict(row)

    def upsert_profile(self, student_id: int, payload: dict[str, Any]) -> None:
        mapped = {column: payload.get(field) for field, column in PROFILE_FIELDS.items()}
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO student_profiles (
                    student_id, age, study_time_weekly, absences, parental_education, tutoring,
                    parental_support, extracurricular, sports, music, volunteering, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(student_id) DO UPDATE SET
                    age = excluded.age,
                    study_time_weekly = excluded.study_time_weekly,
                    absences = excluded.absences,
                    parental_education = excluded.parental_education,
                    tutoring = excluded.tutoring,
                    parental_support = excluded.parental_support,
                    extracurricular = excluded.extracurricular,
                    sports = excluded.sports,
                    music = excluded.music,
                    volunteering = excluded.volunteering,
                    updated_at = excluded.updated_at
                """,
                (
                    student_id,
                    mapped["age"],
                    mapped["study_time_weekly"],
                    mapped["absences"],
                    mapped["parental_education"],
                    mapped["tutoring"],
                    mapped["parental_support"],
                    mapped["extracurricular"],
                    mapped["sports"],
                    mapped["music"],
                    mapped["volunteering"],
                    iso_now(),
                ),
            )
            connection.commit()

    def profile_payload(self, student_id: int) -> dict[str, Any] | None:
        profile = self.get_profile(student_id)
        payload = {}
        for api_name, column_name in PROFILE_FIELDS.items():
            value = profile.get(column_name)
            if value is None:
                return None
            payload[api_name] = value
        return payload

    def profile_is_complete(self, student_id: int) -> bool:
        return self.profile_payload(student_id) is not None

    def list_subjects(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM subjects ORDER BY name COLLATE NOCASE"
            ).fetchall()
        return [dict(row) for row in rows]

    def create_subject(self, name: str) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO subjects (name, is_active) VALUES (?, 1)",
                (name.strip(),),
            )
            connection.commit()
            if cursor.lastrowid:
                return int(cursor.lastrowid)
        with self._connect() as connection:
            row = connection.execute("SELECT id FROM subjects WHERE name = ?", (name.strip(),)).fetchone()
        return int(row["id"])

    def get_or_create_subject(self, name: str) -> int:
        return self.create_subject(name)

    def upsert_grade_record(self, student_id: int, subject_id: int, period: str, grade: float, source: str) -> str:
        status = "approved" if grade >= 6.0 else "failed"
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT id FROM grade_records
                WHERE student_id = ? AND subject_id = ? AND period = ?
                """,
                (student_id, subject_id, period.strip()),
            ).fetchone()
            if existing:
                connection.execute(
                    """
                    UPDATE grade_records
                    SET grade = ?, status = ?, recorded_at = ?, source = ?
                    WHERE id = ?
                    """,
                    (grade, status, iso_now(), source, existing["id"]),
                )
                action = "updated"
            else:
                connection.execute(
                    """
                    INSERT INTO grade_records (student_id, subject_id, period, grade, status, recorded_at, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (student_id, subject_id, period.strip(), grade, status, iso_now(), source),
                )
                action = "inserted"
            connection.commit()
        return action

    def list_student_grades(self, student_id: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT grade_records.*, subjects.name AS subject_name
                FROM grade_records
                JOIN subjects ON subjects.id = grade_records.subject_id
                WHERE grade_records.student_id = ?
                ORDER BY grade_records.period DESC, subjects.name COLLATE NOCASE
                """,
                (student_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def average_for_student(self, student_id: int) -> float | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT ROUND(AVG(grade), 2) AS average_grade FROM grade_records WHERE student_id = ?",
                (student_id,),
            ).fetchone()
        if not row or row["average_grade"] is None:
            return None
        return float(row["average_grade"])

    def school_average(self) -> float | None:
        with self._connect() as connection:
            row = connection.execute("SELECT ROUND(AVG(grade), 2) AS average_grade FROM grade_records").fetchone()
        if not row or row["average_grade"] is None:
            return None
        return float(row["average_grade"])

    def student_counts(self) -> dict[str, int]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS total_students,
                    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS active_students
                FROM students
                """
            ).fetchone()
        return {"total_students": int(row["total_students"] or 0), "active_students": int(row["active_students"] or 0)}

    def import_grades_csv(self, csv_bytes: bytes, filename: str, uploaded_by: int) -> dict[str, Any]:
        content = csv_bytes.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(content))
        required = {"student_code", "full_name", "subject_name", "period", "grade"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError("El CSV debe incluir: student_code, full_name, subject_name, period, grade")

        inserted_rows = 0
        updated_rows = 0
        error_rows = 0
        total_rows = 0
        errors: list[str] = []

        for index, row in enumerate(reader, start=2):
            if not any((value or "").strip() for value in row.values()):
                continue
            total_rows += 1
            try:
                student_code = (row.get("student_code") or "").strip()
                full_name = (row.get("full_name") or "").strip()
                subject_name = (row.get("subject_name") or "").strip()
                period = (row.get("period") or "").strip()
                grade = float((row.get("grade") or "").strip())
                if not student_code or not full_name or not subject_name or not period:
                    raise ValueError("Campos obligatorios vacíos.")
                if grade < 0 or grade > 10:
                    raise ValueError("La calificación debe estar entre 0 y 10.")

                student = self.get_student_by_code(student_code)
                if not student:
                    student_id = self.create_student(
                        student_code=student_code,
                        full_name=full_name,
                        group_name="Sin grupo",
                        current_period=period,
                    )
                else:
                    student_id = int(student["id"])
                    self.update_student(
                        student_id=student_id,
                        student_code=student_code,
                        full_name=full_name,
                        group_name=student.get("group_name") or "Sin grupo",
                        current_period=period,
                        is_active=bool(student["is_active"]),
                    )

                subject_id = self.get_or_create_subject(subject_name)
                action = self.upsert_grade_record(
                    student_id=student_id,
                    subject_id=subject_id,
                    period=period,
                    grade=grade,
                    source="csv",
                )
                if action == "inserted":
                    inserted_rows += 1
                else:
                    updated_rows += 1
            except Exception as exc:  # pragma: no cover - aggregated for UI feedback
                error_rows += 1
                errors.append(f"Fila {index}: {exc}")

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO audit_imports (uploaded_by, filename, total_rows, inserted_rows, updated_rows, error_rows, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (uploaded_by, filename, total_rows, inserted_rows, updated_rows, error_rows, iso_now()),
            )
            connection.commit()

        return {
            "filename": filename,
            "total_rows": total_rows,
            "inserted_rows": inserted_rows,
            "updated_rows": updated_rows,
            "error_rows": error_rows,
            "errors": errors[:20],
        }
