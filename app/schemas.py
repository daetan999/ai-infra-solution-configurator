"""Validated public contracts for configurator scenarios."""

from __future__ import annotations

from typing import ClassVar, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

WorkloadType = Literal[
    "enterprise_rag",
    "real_time_inference",
    "hybrid_ai_platform",
    "model_training",
    "batch_inference",
    "feature_platform",
]
LifecycleMode = Literal["training", "inference", "both"]
DataSensitivity = Literal["public", "internal", "confidential", "restricted"]
SovereigntyRequirement = Literal["none", "in_region", "in_country", "specific_jurisdiction"]
CloudPreference = Literal["cloud_agnostic", "aws", "azure", "gcp", "private_cloud", "no_cloud"]
OnPremisesPreference = Literal["avoid", "neutral", "prefer", "required"]
ExistingKubernetes = Literal["none", "pilot", "production"]
ExistingCloud = Literal["none", "single_cloud", "multi_cloud"]
ExistingDataPlatform = Literal["none", "warehouse", "data_lake", "lakehouse", "streaming"]
ObservabilityMaturity = Literal["emerging", "developing", "established", "advanced"]
TeamOperatingModel = Literal["centralized", "platform_team", "federated", "outsourced"]
BudgetSensitivity = Literal["low", "moderate", "high"]
SecurityControl = Literal[
    "encryption_at_rest",
    "encryption_in_transit",
    "customer_managed_keys",
    "private_networking",
    "workload_identity",
    "audit_logging",
    "data_loss_prevention",
    "confidential_computing",
    "zero_trust",
    "regulatory_controls",
]


class ScenarioCreate(BaseModel):
    """Complete, bounded scenario input used by create and update operations."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    REQUIREMENT_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
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
    )

    name: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=10, max_length=1_000)
    fictional: Literal[True] = True
    workload_type: WorkloadType
    lifecycle_mode: LifecycleMode
    model_size_billion: float = Field(gt=0, le=10_000)
    latency_target_ms: float = Field(gt=0, le=3_600_000)
    throughput_target_rps: float = Field(gt=0, le=10_000_000)
    data_volume_tb: float = Field(gt=0, le=1_000_000)
    data_sensitivity: DataSensitivity
    sovereignty_requirement: SovereigntyRequirement
    cloud_preference: CloudPreference
    on_premises_preference: OnPremisesPreference
    hybrid_requirement: bool
    availability_target_pct: float = Field(ge=90, lt=100)
    recovery_objective_hours: float = Field(ge=0, le=720)
    existing_kubernetes: ExistingKubernetes
    existing_cloud: ExistingCloud
    existing_data_platform: ExistingDataPlatform
    security_requirements: tuple[SecurityControl, ...] = Field(min_length=1, max_length=10)
    observability_maturity: ObservabilityMaturity
    team_operating_model: TeamOperatingModel
    budget_sensitivity: BudgetSensitivity
    timeline_weeks: int = Field(ge=1, le=520)
    annual_growth_pct: float = Field(ge=0, le=1_000)

    @field_validator("name", "description")
    @classmethod
    def strip_bounded_text(cls, value: str, info: ValidationInfo) -> str:
        normalized = " ".join(value.split())
        minimum_length = 3 if info.field_name == "name" else 10
        if len(normalized) < minimum_length:
            raise ValueError(f"text must contain at least {minimum_length} visible characters")
        return normalized

    @field_validator("security_requirements")
    @classmethod
    def security_controls_are_unique(
        cls, controls: tuple[SecurityControl, ...]
    ) -> tuple[SecurityControl, ...]:
        if len(set(controls)) != len(controls):
            raise ValueError("security requirements must not contain duplicates")
        return controls

    @model_validator(mode="after")
    def requirements_are_consistent(self) -> Self:
        if self.workload_type == "model_training" and self.lifecycle_mode == "inference":
            raise ValueError("contradictory workload and lifecycle requirements")
        if self.workload_type in {"enterprise_rag", "real_time_inference"} and (
            self.lifecycle_mode == "training"
        ):
            raise ValueError("contradictory workload and lifecycle requirements")
        if self.hybrid_requirement and (
            self.cloud_preference == "no_cloud" or self.on_premises_preference == "avoid"
        ):
            raise ValueError("contradictory hybrid placement requirements")
        if not self.hybrid_requirement and (
            self.on_premises_preference == "required"
            and self.cloud_preference in {"aws", "azure", "gcp"}
        ):
            raise ValueError("contradictory single-placement requirements")
        if not self.hybrid_requirement and (
            self.cloud_preference == "no_cloud" and self.on_premises_preference == "avoid"
        ):
            raise ValueError("contradictory placement requirements")
        return self

    def requirements_dict(self) -> dict[str, object]:
        """Return a detached, JSON-safe requirements snapshot."""

        return self.model_dump(mode="json", include=self.REQUIREMENT_FIELDS)


ScenarioUpdate = ScenarioCreate
