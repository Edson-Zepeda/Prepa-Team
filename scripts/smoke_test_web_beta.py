from pathlib import Path
import json
import os
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))


def assert_plan_shape(body: dict) -> None:
    assert body["ok"] is True, body
    assert "good_performance_threshold" not in body, body
    assert 0 <= body["estimated_average_10"] <= 10, body
    assert body["good_performance_threshold_10"] == 6.0, body
    assert len(body["priority_factors"]) == 3, body
    assert len(body["top_plans"]) == 3, body
    assert {row["strategy"] for row in body["top_plans"]} == {
        "minimo_esfuerzo",
        "balanceado",
        "mayor_impacto",
    }, body
    assert body["recommended_plan"]["actions"], body
    assert body["recommended_plan"]["target_zone"] in {"medio", "bajo"}, body


def main() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        os.environ["SCHOOL_DB_PATH"] = str(Path(temp_dir) / "school.db")
        os.environ["ADMIN_EMAIL"] = "admin@test.local"
        os.environ["ADMIN_PASSWORD"] = "Admin1234!"

        from fastapi.testclient import TestClient

        from web.backend.app import app

        payload = json.loads((ROOT / "examples" / "student_payload.json").read_text(encoding="utf-8"))
        high_risk_payload = {
            "Age": 17,
            "StudyTimeWeekly": 3,
            "Absences": 18,
            "ParentalEducation": 1,
            "Tutoring": 0,
            "ParentalSupport": 1,
            "Extracurricular": 0,
            "Sports": 0,
            "Music": 0,
            "Volunteering": 0,
        }
        low_risk_payload = {
            "Age": 17,
            "StudyTimeWeekly": 16,
            "Absences": 1,
            "ParentalEducation": 3,
            "Tutoring": 1,
            "ParentalSupport": 4,
            "Extracurricular": 1,
            "Sports": 1,
            "Music": 0,
            "Volunteering": 1,
        }

        with TestClient(app) as client:
            health = client.get("/health")
            assert health.status_code == 200, health.text
            assert health.json()["status"] == "ok"

            schema = client.get("/schema")
            assert schema.status_code == 200, schema.text
            schema_body = schema.json()
            assert schema_body["good_performance_threshold_10"] == 6.0, schema_body
            assert schema_body["acceptable_zone"] == "medio", schema_body
            assert "good_performance_threshold" not in schema_body, schema_body
            assert schema_body["plan_strategies"] == ["minimo_esfuerzo", "balanceado", "mayor_impacto"], schema_body

            public_prediction = client.post("/predict", json=payload)
            assert public_prediction.status_code == 200, public_prediction.text
            public_body = public_prediction.json()
            assert_plan_shape(public_body)

            high_risk_prediction = client.post("/predict", json=high_risk_payload)
            assert high_risk_prediction.status_code == 200, high_risk_prediction.text
            high_risk_body = high_risk_prediction.json()
            assert_plan_shape(high_risk_body)
            assert high_risk_body["risk_level"] in {"muy alto", "alto"}, high_risk_body
            assert high_risk_body["next_level_plan"] is not None, high_risk_body
            assert high_risk_body["recommended_plan"]["target_zone"] in {"medio", "bajo"}, high_risk_body

            low_risk_prediction = client.post("/predict", json=low_risk_payload)
            assert low_risk_prediction.status_code == 200, low_risk_prediction.text
            low_risk_body = low_risk_prediction.json()
            assert_plan_shape(low_risk_body)
            assert low_risk_body["risk_level"] == "bajo", low_risk_body
            assert low_risk_body["next_level_plan"] is None, low_risk_body
            assert low_risk_body["recommended_plan"]["effort_score"] <= 3, low_risk_body

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
                    "subject_name": "Matematicas",
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
            assert_plan_shape(student_body)
            assert student_body["recommended_plan"]["estimated_average_after_10"] >= student_body["estimated_average_10"]

            student_dashboard = client.get("/student/dashboard")
            assert student_dashboard.status_code == 200, student_dashboard.text
            assert "Intervención" in student_dashboard.text, student_dashboard.text

            me = client.get("/api/student/me")
            assert me.status_code == 200, me.text
            me_body = me.json()
            assert me_body["ok"] is True
            assert me_body["school_average"] == 8.7
            assert me_body["profile_complete"] is True

            client.post("/api/auth/logout")
            admin_login_again = client.post(
                "/api/auth/login",
                json={"email": os.environ["ADMIN_EMAIL"], "password": os.environ["ADMIN_PASSWORD"]},
            )
            assert admin_login_again.status_code == 200, admin_login_again.text
            admin_student_view = client.get(f"/admin/students/{student_id}")
            assert admin_student_view.status_code == 200, admin_student_view.text
            assert "Intervención" in admin_student_view.text, admin_student_view.text

        print("School web smoke test passed.")
        print(json.dumps(student_body, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
