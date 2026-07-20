from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from tests.test_repository import repository
from tests.test_schemas import valid_payload


def client() -> TestClient:
    return TestClient(create_app(repository=repository()))


def test_health_and_scenario_crud_use_safe_envelopes() -> None:
    api = client()

    health = api.get("/api/health")
    assert health.status_code == 200
    assert health.json() == {
        "success": True,
        "data": {"status": "ok"},
        "error": None,
        "meta": {},
    }

    created_response = api.post("/api/scenarios", json=valid_payload())
    assert created_response.status_code == 201
    created = created_response.json()["data"]
    assert created["scenario"]["name"] == valid_payload()["name"]
    assert created["latest_run"]["assessment"]["recommendations"][0]["rule_triggered"]

    assert api.get("/api/scenarios").json()["data"]["scenarios"][0]["id"] == 1
    assert api.get("/api/scenarios/1").json()["data"]["scenario"]["id"] == 1

    update = {**valid_payload(), "timeline_weeks": 30}
    updated = api.put("/api/scenarios/1", json=update)
    assert updated.status_code == 200
    assert updated.json()["data"]["scenario"]["version"] == 2
    assert len(api.get("/api/scenarios/1/runs").json()["data"]["runs"]) == 2

    deleted = api.delete("/api/scenarios/1")
    assert deleted.status_code == 200
    assert deleted.json()["data"] == {"deleted": True, "id": 1}
    assert api.get("/api/scenarios/1").status_code == 404


def test_validation_and_missing_records_have_redacted_errors() -> None:
    api = client()
    invalid = api.post("/api/scenarios", json={**valid_payload(), "timeline_weeks": 0})

    assert invalid.status_code == 422
    error = invalid.json()
    assert error["success"] is False
    assert error["data"] is None
    assert error["error"]["code"] == "validation_error"
    assert "input" not in str(error["error"]).lower()

    missing = api.get("/api/runs/999")
    assert missing.status_code == 404
    assert missing.json()["error"] == {
        "code": "not_found",
        "message": "Assessment run was not found.",
    }


def test_historical_and_scenario_alias_exports_are_deterministic_and_safe() -> None:
    api = client()
    created = api.post("/api/scenarios", json=valid_payload()).json()["data"]
    run_id = created["latest_run"]["id"]

    run = api.get(f"/api/runs/{run_id}")
    assert run.status_code == 200
    assert run.json()["data"]["run"]["scenario_version"] == 1

    first_json = api.get(f"/api/runs/{run_id}/export.json")
    second_json = api.get("/api/scenarios/1/export?format=json")
    assert first_json.content == second_json.content
    assert first_json.headers["content-disposition"] == 'attachment; filename="solution-run-1.json"'

    markdown = api.get("/api/scenarios/1/export?format=markdown")
    assert markdown.status_code == 200
    assert markdown.headers["content-type"].startswith("text/markdown")
    assert "# Enterprise AI Solution Brief" in markdown.text
    assert "initial solution hypothesis" in markdown.text.lower()

    svg = api.get("/api/scenarios/1/diagram.svg")
    canonical_svg = api.get(f"/api/runs/{run_id}/architecture.svg")
    assert svg.content == canonical_svg.content
    assert svg.headers["content-type"].startswith("image/svg+xml")
    assert svg.headers["content-disposition"] == 'attachment; filename="architecture-run-1.svg"'
    assert "<script" not in svg.text.lower()
    assert "foreignobject" not in svg.text.lower()


def test_unexpected_errors_do_not_leak_exception_details() -> None:
    class ExplodingRepository:
        def list_scenarios(self) -> list[dict[str, object]]:
            raise RuntimeError("database password=super-secret")

    api = TestClient(create_app(repository=ExplodingRepository()), raise_server_exceptions=False)
    response = api.get("/api/scenarios")

    assert response.status_code == 500
    assert response.json()["error"] == {
        "code": "internal_error",
        "message": "The request could not be completed.",
    }
    assert "super-secret" not in response.text
