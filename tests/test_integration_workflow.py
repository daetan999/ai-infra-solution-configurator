from __future__ import annotations

from app.repository import ScenarioRepository
from app.schemas import ScenarioCreate

from .test_schemas import valid_payload


def test_real_rules_to_blueprint_to_export_workflow(tmp_path) -> None:
    repo = ScenarioRepository(database_path=tmp_path / "workflow.sqlite3")
    created = repo.create_scenario(ScenarioCreate.model_validate(valid_payload()))
    run = created["latest_run"]

    assert run["assessment"]["recommendations"]
    assert run["assessment"]["architecture"]
    assert run["assessment"]["solution_confidence"]["level"] in {"low", "medium", "high"}
    assert run["blueprint"]["nodes"]
    assert run["blueprint"]["edges"]
    assert run["architecture_svg"].startswith("<svg")
    assert "<script" not in run["architecture_svg"].lower()

    persisted = repo.get_run(run["id"])
    assert persisted == run
