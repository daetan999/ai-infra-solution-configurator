from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import ScenarioCreate


def valid_payload() -> dict[str, object]:
    return {
        "name": "Fictional private enterprise RAG",
        "description": "A fictional regulated knowledge assistant used for solution discovery.",
        "fictional": True,
        "workload_type": "enterprise_rag",
        "lifecycle_mode": "inference",
        "model_size_billion": 70,
        "latency_target_ms": 900,
        "throughput_target_rps": 45,
        "data_volume_tb": 18,
        "data_sensitivity": "restricted",
        "sovereignty_requirement": "in_country",
        "cloud_preference": "private_cloud",
        "on_premises_preference": "prefer",
        "hybrid_requirement": True,
        "availability_target_pct": 99.95,
        "recovery_objective_hours": 4,
        "existing_kubernetes": "production",
        "existing_cloud": "single_cloud",
        "existing_data_platform": "lakehouse",
        "security_requirements": [
            "customer_managed_keys",
            "private_networking",
            "audit_logging",
        ],
        "observability_maturity": "established",
        "team_operating_model": "platform_team",
        "budget_sensitivity": "moderate",
        "timeline_weeks": 24,
        "annual_growth_pct": 35,
    }


def test_accepts_every_brief_requirement_and_normalizes_text() -> None:
    payload = valid_payload()
    payload["name"] = "  Fictional private enterprise RAG  "

    scenario = ScenarioCreate.model_validate(payload)

    assert scenario.name == "Fictional private enterprise RAG"
    assert scenario.fictional is True
    assert scenario.security_requirements == (
        "customer_managed_keys",
        "private_networking",
        "audit_logging",
    )
    assert set(scenario.requirements_dict()) == {
        "workload_type",
        "lifecycle_mode",
        "model_size_billion",
        "latency_target_ms",
        "throughput_target_rps",
        "data_volume_tb",
        "data_sensitivity",
        "sovereignty_requirement",
        "cloud_preference",
        "on_premises_preference",
        "hybrid_requirement",
        "availability_target_pct",
        "recovery_objective_hours",
        "existing_kubernetes",
        "existing_cloud",
        "existing_data_platform",
        "security_requirements",
        "observability_maturity",
        "team_operating_model",
        "budget_sensitivity",
        "timeline_weeks",
        "annual_growth_pct",
    }


def test_rejects_unknown_fields_and_non_fictional_scenarios() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ScenarioCreate.model_validate({**valid_payload(), "hidden_override": True})

    with pytest.raises(ValidationError, match="literal_error"):
        ScenarioCreate.model_validate({**valid_payload(), "fictional": False})


@pytest.mark.parametrize(
    ("field", "value"),
    [("name", " a "), ("description", "          brief          ")],
)
def test_rejects_text_that_falls_below_bounds_after_normalization(
    field: str, value: str
) -> None:
    with pytest.raises(ValidationError):
        ScenarioCreate.model_validate({**valid_payload(), field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("model_size_billion", 0),
        ("latency_target_ms", 0),
        ("throughput_target_rps", -1),
        ("data_volume_tb", -0.1),
        ("availability_target_pct", 89),
        ("availability_target_pct", 100),
        ("recovery_objective_hours", 721),
        ("timeline_weeks", 0),
        ("annual_growth_pct", 1001),
    ],
)
def test_rejects_values_outside_documented_bounds(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        ScenarioCreate.model_validate({**valid_payload(), field: value})


@pytest.mark.parametrize(
    "changes",
    [
        {"workload_type": "model_training", "lifecycle_mode": "inference"},
        {"workload_type": "real_time_inference", "lifecycle_mode": "training"},
        {
            "hybrid_requirement": True,
            "cloud_preference": "no_cloud",
            "on_premises_preference": "required",
        },
        {
            "hybrid_requirement": False,
            "cloud_preference": "aws",
            "on_premises_preference": "required",
        },
        {
            "hybrid_requirement": False,
            "cloud_preference": "no_cloud",
            "on_premises_preference": "avoid",
        },
    ],
)
def test_rejects_contradictory_requirements(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError, match="contradict"):
        ScenarioCreate.model_validate({**valid_payload(), **changes})


def test_rejects_duplicate_or_unknown_security_controls() -> None:
    with pytest.raises(ValidationError):
        ScenarioCreate.model_validate(
            {**valid_payload(), "security_requirements": ["audit_logging", "audit_logging"]}
        )

    with pytest.raises(ValidationError):
        ScenarioCreate.model_validate(
            {**valid_payload(), "security_requirements": ["disable_all_controls"]}
        )
