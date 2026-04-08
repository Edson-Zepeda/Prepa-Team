from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from fastapi.testclient import TestClient

from web.backend.app import app


def main() -> None:
    payload = json.loads((ROOT / "examples" / "student_payload.json").read_text(encoding="utf-8"))
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200, health.text
    assert health.json()["status"] == "ok"

    response = client.post("/predict", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True, body
    assert 0 <= body["estimated_gpa"] <= 4, body
    assert 0 <= body["good_performance_probability"] <= 1, body
    assert body["messages"], body
    assert body["recommended_plan"]["plan"], body

    invalid = client.post("/predict", json={**payload, "Absences": 99})
    assert invalid.status_code == 200, invalid.text
    invalid_body = invalid.json()
    assert invalid_body["ok"] is False, invalid_body
    assert invalid_body["errors"], invalid_body

    print("Web beta smoke test passed.")
    print(json.dumps(body, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
