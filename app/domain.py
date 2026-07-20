"""Typed, immutable domain contracts for the configurator rules engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

ARCHITECTURE_LAYERS = (
    "compute_layer",
    "accelerator_approach",
    "orchestration",
    "model_serving",
    "networking",
    "storage",
    "data_layer",
    "feature_or_retrieval_layer",
    "security",
    "identity",
    "observability",
    "resilience",
    "deployment_pattern",
)

TRACE_FIELDS = (
    "customer_requirement",
    "rule_triggered",
    "recommended_component_or_pattern",
    "reason",
    "alternative",
    "risk",
    "required_validation",
)

EVIDENCE_FIELDS = (
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
)


@dataclass(frozen=True, slots=True)
class Rule:
    """A declarative recommendation rule with stable conflict priority."""

    rule_id: str
    layer: str
    priority: int
    condition: str
    requirement_fields: tuple[str, ...]
    component: str
    reason: str
    alternative: str
    risk: str
    required_validation: str
    is_fallback: bool = False


class ConflictRecord(TypedDict):
    """Machine-readable evidence of a deterministic rule decision."""

    layer: str
    selected_rule: str
    selected_priority: int
    superseded_rule: str
    superseded_priority: int
    reason: str


@dataclass(frozen=True, slots=True)
class RuleResolution:
    """Selected rules and the alternatives they superseded."""

    selected: tuple[Rule, ...]
    conflicts: tuple[ConflictRecord, ...]
