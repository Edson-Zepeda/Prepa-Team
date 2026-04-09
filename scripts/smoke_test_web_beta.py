from pathlib import Path
import json
import os
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))


def main() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        os.environ["SCHOOL_DB_PATH"] = str(Path(temp_dir) / "school.db")
        os.environ["ADMIN_EMAIL"] = "admin@test.local"
        os.environ["ADMIN_PASSWORD"] = "Admin1234!"

        from fastapi.testclient import TestClient

        from web.backend.app import app

        payload = json.loads((ROOT / "examples" / "student_payload.json").read_text(encoding="utf-8"))

        with TestClient(app) as client:
            health = client.get("/health")
            assert health.status_code == 200, health.text
            assert health.json()["status"] == "ok"

            public_prediction = client.post("/predict", json=payload)
            assert public_prediction.status_code == 200, public_prediction.text
            public_body = public_prediction.json()
            assert public_body["ok"] is True, public_body
            assert 0 <= public_body["estimated_average_10"] <= 10, public_body
            assert public_body["good_performance_threshold_10"] == 6.0, public_body

            admin_login = client.post(
                "/api/auth/login",
                json={"email": os.environ["ADMIN_EMAIL"], "password": os.environ["ADMIN_PASSWORD"]},
            )
            assert admin_login.status_code == 200, admin_login.text
            assert admin_login.json()["ok"] is True, admin_login.text

            new_student = client.post(
                "/api/admin/students",
                json={
                    "student_code": "A001",
                    "full_name": "Alumno Demo",
                    "group_name": "6A",
                    "current_period": "2026-1",
                    "account_email": "alumno@test.local",
                    "account_password": "Alumno1234!",
                },
            )
            assert new_student.status_code == 200, new_student.text
            student_id = new_student.json()["student_id"]

            manual_grade = client.post(
                "/api/admin/grades/manual",
                json={
                    "student_id": student_id,
                    "subject_name": "Matemáticas",
                    "period": "2026-1",
                    "grade": 8.7,
                },
            )
            assert manual_grade.status_code == 200, manual_grade.text
            assert manual_grade.json()["ok"] is True

            admin_prediction_before = client.get(f"/api/admin/students/{student_id}/predict")
            assert admin_prediction_before.status_code == 422, admin_prediction_before.text

            client.post("/api/auth/logout")
            student_login = client.post(
                "/api/auth/login",
                json={"email": "alumno@test.local", "password": "Alumno1234!"},
            )
            assert student_login.status_code == 200, student_login.text
            assert student_login.json()["ok"] is True

            save_profile = client.put("/api/student/profile", json=payload)
            assert save_profile.status_code == 200, save_profile.text
            assert save_profile.json()["ok"] is True

            student_prediction = client.post("/api/student/predict")
            assert student_prediction.status_code == 200, student_prediction.text
            student_body = student_prediction.json()
            assert student_body["ok"] is True, student_body
            assert 0 <= student_body["estimated_average_10"] <= 10, student_body
            assert student_body["recommended_plan"]["estimated_average_after_10"] >= student_body["estimated_average_10"]

            me = client.get("/api/student/me")
            assert me.status_code == 200, me.text
            me_body = me.json()
            assert me_body["ok"] is True
            assert me_body["school_average"] == 8.7
            assert me_body["profile_complete"] is True

        print("School web smoke test passed.")
        print(json.dumps(student_body, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
