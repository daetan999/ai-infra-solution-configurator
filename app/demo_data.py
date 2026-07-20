"""Fictional, idempotent portfolio demonstration scenarios."""

from __future__ import annotations

from app.repository import ScenarioRepository
from app.schemas import ScenarioCreate


def demo_scenarios() -> tuple[ScenarioCreate, ...]:
    return (
        ScenarioCreate(
            name="Fictional Northstar Private RAG",
            description=(
                "A fictional regulated knowledge assistant spanning controlled cloud "
                "and private data."
            ),
            workload_type="enterprise_rag",
            lifecycle_mode="inference",
            model_size_billion=70,
            latency_target_ms=900,
            throughput_target_rps=45,
            data_volume_tb=18,
            data_sensitivity="restricted",
            sovereignty_requirement="in_country",
            cloud_preference="private_cloud",
            on_premises_preference="prefer",
            hybrid_requirement=True,
            availability_target_pct=99.95,
            recovery_objective_hours=4,
            existing_kubernetes="production",
            existing_cloud="single_cloud",
            existing_data_platform="lakehouse",
            security_requirements=(
                "customer_managed_keys",
                "private_networking",
                "audit_logging",
                "data_loss_prevention",
            ),
            observability_maturity="established",
            team_operating_model="platform_team",
            budget_sensitivity="moderate",
            timeline_weeks=24,
            annual_growth_pct=35,
        ),
        ScenarioCreate(
            name="Fictional Meridian Real-Time Inference",
            description=(
                "A fictional digital service requiring low-latency, high-availability "
                "model inference."
            ),
            workload_type="real_time_inference",
            lifecycle_mode="inference",
            model_size_billion=13,
            latency_target_ms=120,
            throughput_target_rps=850,
            data_volume_tb=4,
            data_sensitivity="confidential",
            sovereignty_requirement="in_region",
            cloud_preference="gcp",
            on_premises_preference="avoid",
            hybrid_requirement=False,
            availability_target_pct=99.99,
            recovery_objective_hours=1,
            existing_kubernetes="pilot",
            existing_cloud="single_cloud",
            existing_data_platform="warehouse",
            security_requirements=(
                "encryption_at_rest",
                "encryption_in_transit",
                "workload_identity",
                "audit_logging",
            ),
            observability_maturity="developing",
            team_operating_model="centralized",
            budget_sensitivity="high",
            timeline_weeks=16,
            annual_growth_pct=60,
        ),
        ScenarioCreate(
            name="Fictional Aster Hybrid AI Platform",
            description=(
                "A fictional hybrid AI platform keeping sensitive records on premises "
                "while bursting safely."
            ),
            workload_type="hybrid_ai_platform",
            lifecycle_mode="both",
            model_size_billion=120,
            latency_target_ms=650,
            throughput_target_rps=180,
            data_volume_tb=240,
            data_sensitivity="restricted",
            sovereignty_requirement="specific_jurisdiction",
            cloud_preference="azure",
            on_premises_preference="required",
            hybrid_requirement=True,
            availability_target_pct=99.95,
            recovery_objective_hours=2,
            existing_kubernetes="production",
            existing_cloud="multi_cloud",
            existing_data_platform="streaming",
            security_requirements=(
                "customer_managed_keys",
                "private_networking",
                "confidential_computing",
                "zero_trust",
                "regulatory_controls",
            ),
            observability_maturity="advanced",
            team_operating_model="federated",
            budget_sensitivity="moderate",
            timeline_weeks=40,
            annual_growth_pct=45,
        ),
    )


def seed_demo_scenarios(repository: ScenarioRepository) -> int:
    created = 0
    for demo in demo_scenarios():
        if repository.has_active_name(demo.name):
            continue
        repository.create_scenario(demo)
        created += 1
    return created
