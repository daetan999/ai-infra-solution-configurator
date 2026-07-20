from __future__ import annotations

import pytest

from app.exports import markdown_export, validate_svg_export
from app.repository import ScenarioRepository
from app.schemas import ScenarioCreate
from tests.test_schemas import valid_payload


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

    brief = markdown_export(run)
    assert "- **Risk:**" in brief
    assert "- **Mitigation:**" in brief
    assert "### Objective" in brief
    assert "### Success criteria" in brief
    assert "### Agenda" in brief
    assert "{'risk':" not in brief
    assert "{'objective':" not in brief

    assert validate_svg_export(run["architecture_svg"]) == run["architecture_svg"]


@pytest.mark.parametrize(
    "svg",
    [
        '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><foreignObject>unsafe</foreignObject></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><a href="https://evil.example">x</a></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><rect onload="alert(1)" /></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><style>rect{fill:url(https://evil)}</style></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><style>@import "https://evil";</style></svg>',
        '<svg xmlns="http://www.w3.org/2000/svg"><rect fill="url(https://evil)" /></svg>',
        (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<set attributeName="href" to="https://evil" /></svg>'
        ),
    ],
)
def test_svg_export_blocks_active_or_external_content(svg: str) -> None:
    with pytest.raises(ValueError, match="unsafe"):
        validate_svg_export(svg)
