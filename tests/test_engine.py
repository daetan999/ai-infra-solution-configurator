from __future__ import annotations

from copy import deepcopy

import pytest

from app.domain import ARCHITECTURE_LAYERS, TRACE_FIELDS
from app.engine import evaluate_configuration


def complete_requirements() -> dict[str, object]:
    return {
        "workload_type": "rag",
        "execution_mode": "inference",
        "model_size_billion_parameters": 70,
        "latency_requirement_ms": 175,
        "throughput_requirement_requests_per_second": 240,
        "data_volume_tb": 24,
        "data_sensitivity": "restricted",
        "sovereignty_requirement": "in_country",
        "cloud_preference": "private_cloud",
        "on_premises_preference": True,
        "hybrid_requirement": True,
        "availability_target_percent": 99.95,
        "recovery_objective_minutes": 30,
        "existing_kubernetes_environment": True,
        "existing_cloud_environment": True,
        "existing_data_platform": True,
        "security_requirements": ["encryption", "audit logging"],
        "observability_maturity": "developing",
        "team_operating_model": "platform_team",
        "budget_sensitivity": "high",
        "timeline_weeks": 16,
        "annual_growth_rate_percent": 45,
    }


def test_result_has_every_required_solution_layer_and_trace_field() -> None:
    result = evaluate_configuration(complete_requirements())

    assert set(result["architecture"]) == set(ARCHITECTURE_LAYERS)
    assert len(result["recommendations"]) == len(ARCHITECTURE_LAYERS)
    for recommendation in result["recommendations"]:
        assert set(TRACE_FIELDS).issubset(recommendation)
        assert recommendation["recommendation"] == recommendation[
            "recommended_component_or_pattern"
        ]
        assert recommendation["layer"] in ARCHITECTURE_LAYERS
        assert recommendation["priority"] >= 0
    assert result["placement"] == result["deployment_pattern"]
    assert result["placement"] == result["architecture"]["deployment_pattern"][
        "component_or_pattern"
    ]


def test_private_hybrid_rag_uses_explainable_specialized_patterns() -> None:
    result = evaluate_configuration(complete_requirements())

    architecture = result["architecture"]
    assert architecture["deployment_pattern"]["rule_id"] == "DEPLOY-HYBRID"
    assert architecture["feature_or_retrieval_layer"]["rule_id"] == "RETRIEVAL-RAG"
    assert architecture["security"]["rule_id"] == "SECURITY-RESTRICTED"
    assert "private" in architecture["deployment_pattern"]["component_or_pattern"].lower()


def test_result_and_digests_are_canonical_across_mapping_and_set_like_order() -> None:
    requirements = complete_requirements()
    reordered = dict(reversed(tuple(requirements.items())))
    reordered["security_requirements"] = ["audit logging", "encryption", "audit logging"]

    first = evaluate_configuration(requirements)
    second = evaluate_configuration(reordered)

    assert first == second
    assert len(first["input_digest"]) == 64
    assert len(first["ruleset_digest"]) == 64


def test_input_change_updates_digest_and_recommendation() -> None:
    cloud = complete_requirements()
    cloud.update(
        hybrid_requirement=False,
        on_premises_preference=False,
        cloud_preference="public_cloud",
        sovereignty_requirement="none",
        data_sensitivity="internal",
    )

    hybrid_result = evaluate_configuration(complete_requirements())
    cloud_result = evaluate_configuration(cloud)

    assert hybrid_result["input_digest"] != cloud_result["input_digest"]
    assert cloud_result["architecture"]["deployment_pattern"]["rule_id"] == "DEPLOY-CLOUD"


def test_competing_preferences_are_resolved_and_exposed() -> None:
    result = evaluate_configuration(complete_requirements())

    deployment_conflicts = [
        conflict for conflict in result["conflicts"] if conflict["layer"] == "deployment_pattern"
    ]
    assert deployment_conflicts
    assert all(conflict["selected_rule"] == "DEPLOY-HYBRID" for conflict in deployment_conflicts)
    assert all(
        conflict["selected_priority"] >= conflict["superseded_priority"]
        for conflict in deployment_conflicts
    )


def test_sparse_evidence_lowers_confidence_and_creates_questions() -> None:
    result = evaluate_configuration({"workload_type": "inference"})

    assert result["solution_confidence"]["level"] == "low"
    assert result["solution_confidence"]["score"] < 0.6
    assert "latency_requirement_ms" in {
        evidence["field"] for evidence in result["missing_evidence"]
    }
    assert result["open_questions"]


def test_complete_evidence_produces_actionable_workshop_outputs() -> None:
    result = evaluate_configuration(complete_requirements())

    assert result["solution_confidence"]["level"] in {"medium", "high"}
    assert result["primary_risks"]
    assert result["migration_considerations"]
    assert result["recommended_poc"]["objective"]
    assert len(result["recommended_poc"]["success_criteria"]) >= 3
    assert result["recommended_next_workshop"]["title"]
    assert result["recommended_next_workshop"]["agenda"]


def test_engine_does_not_mutate_validated_input() -> None:
    requirements = complete_requirements()
    before = deepcopy(requirements)

    evaluate_configuration(requirements)

    assert requirements == before


def test_non_mapping_input_is_rejected() -> None:
    with pytest.raises(TypeError, match="mapping"):
        evaluate_configuration(["not", "a", "mapping"])  # type: ignore[arg-type]
