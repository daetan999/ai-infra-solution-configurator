from __future__ import annotations

import sqlite3
from pathlib import Path

from app.repository import ScenarioRepository
from app.schemas import ScenarioCreate

from .test_schemas import valid_payload


def fake_evaluator(requirements: dict[str, object]) -> dict[str, object]:
    return {
        "recommendations": [
            {
                "customer_requirement": requirements["workload_type"],
                "rule_triggered": "TEST-001",
                "recommended_component_or_pattern": "Controlled runtime",
                "reason": "Deterministic test fixture",
                "alternative": "Managed runtime",
                "risk": "Requires validation",
                "required_validation": "Benchmark the target workload",
                "layer": "compute",
                "priority": "high",
            }
        ],
        "solution_confidence": {"level": "medium", "score": 0.72},
        "input_digest": "fixture-digest",
    }


def fake_blueprint(assessment: dict[str, object]) -> dict[str, object]:
    return {"title": "Fixture architecture", "assessment": assessment["input_digest"]}


def fake_renderer(blueprint: dict[str, object]) -> str:
    return f'<svg role="img"><title>{blueprint["title"]}</title></svg>'


def repository(connection: sqlite3.Connection | None = None) -> ScenarioRepository:
    return ScenarioRepository(
        connection=connection or sqlite3.connect(":memory:", check_same_thread=False),
        evaluator=fake_evaluator,
        blueprint_builder=fake_blueprint,
        diagram_renderer=fake_renderer,
    )


def test_create_update_and_historical_runs_are_immutable() -> None:
    repo = repository()
    created = repo.create_scenario(ScenarioCreate.model_validate(valid_payload()))

    assert created["version"] == 1
    assert created["latest_run"]["scenario_version"] == 1
    assert created["latest_run"]["assessment"]["input_digest"] == "fixture-digest"

    updated_payload = {**valid_payload(), "throughput_target_rps": 90}
    updated = repo.update_scenario(1, ScenarioCreate.model_validate(updated_payload))
    runs = repo.list_runs(1)

    assert updated is not None
    assert updated["version"] == 2
    assert [run["scenario_version"] for run in runs] == [1, 2]
    assert runs[0]["requirements"]["throughput_target_rps"] == 45
    assert runs[1]["requirements"]["throughput_target_rps"] == 90


def test_sql_is_parameterized_and_soft_delete_preserves_run(tmp_path: Path) -> None:
    database = tmp_path / "configurator.sqlite3"
    repo = ScenarioRepository(
        database_path=database,
        evaluator=fake_evaluator,
        blueprint_builder=fake_blueprint,
        diagram_renderer=fake_renderer,
    )
    payload = {**valid_payload(), "name": "Fictional '; DROP TABLE scenarios; -- case"}
    created = repo.create_scenario(ScenarioCreate.model_validate(payload))
    run_id = created["latest_run"]["id"]

    assert len(repo.list_scenarios()) == 1
    assert repo.delete_scenario(created["id"]) is True
    assert repo.get_scenario(created["id"]) is None
    assert repo.get_run(run_id)["scenario_id"] == created["id"]

    reopened = ScenarioRepository(
        database_path=database,
        evaluator=fake_evaluator,
        blueprint_builder=fake_blueprint,
        diagram_renderer=fake_renderer,
    )
    assert reopened.get_run(run_id)["architecture_svg"].startswith("<svg")


def test_unknown_records_return_none_or_empty_collections() -> None:
    repo = repository()
    payload = ScenarioCreate.model_validate(valid_payload())

    assert repo.get_scenario(404) is None
    assert repo.get_run(404) is None
    assert repo.update_scenario(404, payload) is None
    assert repo.delete_scenario(404) is False
    assert repo.list_runs(404) == []
