from __future__ import annotations

from copy import deepcopy

from app.domain import ARCHITECTURE_LAYERS, Rule
from app.rules import RULES, matching_rules, normalize_requirements, resolve_rule_conflicts


def complete_requirements() -> dict[str, object]:
    return {
        "workload_type": "enterprise_rag",
        "lifecycle_mode": "inference",
        "model_size_billion": 70,
        "latency_target_ms": 175,
        "throughput_target_rps": 240,
        "data_volume_tb": 24,
        "data_sensitivity": "restricted",
        "sovereignty_requirement": "in_country",
        "cloud_preference": "private_cloud",
        "on_premises_preference": "required",
        "hybrid_requirement": True,
        "availability_target_pct": 99.95,
        "recovery_objective_hours": 0.5,
        "existing_kubernetes": "production",
        "existing_cloud": "single_cloud",
        "existing_data_platform": "lakehouse",
        "security_requirements": ["Audit Logging", "encryption", "audit logging"],
        "observability_maturity": "developing",
        "team_operating_model": "platform_team",
        "budget_sensitivity": "high",
        "timeline_weeks": 16,
        "annual_growth_pct": 45,
    }


def test_normalization_is_immutable_and_canonical() -> None:
    requirements = complete_requirements()
    requirements["workload_type"] = "  RAG  "
    before = deepcopy(requirements)

    normalized = normalize_requirements(requirements)

    assert requirements == before
    assert normalized["workload_type"] == "rag"
    assert normalized["security_requirements"] == ["audit logging", "encryption"]


def test_matching_rules_cover_every_architecture_layer() -> None:
    matches = matching_rules(complete_requirements())

    assert set(ARCHITECTURE_LAYERS) == {rule.layer for rule in matches}
    assert "RETRIEVAL-RAG" in {rule.rule_id for rule in matches}
    assert "SECURITY-RESTRICTED" in {rule.rule_id for rule in matches}
    assert "DEPLOY-HYBRID" in {rule.rule_id for rule in matches}


def test_conflict_resolution_uses_priority_then_rule_id() -> None:
    rules = (
        Rule(
            rule_id="COMPUTE-ZULU",
            layer="compute_layer",
            priority=80,
            condition="always",
            requirement_fields=("workload_type",),
            component="Z component",
            reason="Z reason",
            alternative="Z alternative",
            risk="Z risk",
            required_validation="Z validation",
        ),
        Rule(
            rule_id="COMPUTE-ALPHA",
            layer="compute_layer",
            priority=80,
            condition="always",
            requirement_fields=("workload_type",),
            component="A component",
            reason="A reason",
            alternative="A alternative",
            risk="A risk",
            required_validation="A validation",
        ),
        Rule(
            rule_id="COMPUTE-LOW",
            layer="compute_layer",
            priority=40,
            condition="always",
            requirement_fields=("workload_type",),
            component="Low component",
            reason="Low reason",
            alternative="Low alternative",
            risk="Low risk",
            required_validation="Low validation",
        ),
    )

    resolution = resolve_rule_conflicts(tuple(reversed(rules)))

    assert resolution.selected[0].rule_id == "COMPUTE-ALPHA"
    assert [conflict["superseded_rule"] for conflict in resolution.conflicts] == [
        "COMPUTE-ZULU",
        "COMPUTE-LOW",
    ]


def test_ruleset_identifiers_are_unique() -> None:
    identifiers = [rule.rule_id for rule in RULES]

    assert len(identifiers) == len(set(identifiers))
