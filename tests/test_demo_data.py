from __future__ import annotations

from app.demo_data import demo_scenarios, seed_demo_scenarios
from tests.test_repository import repository


def test_three_fictional_demo_scenarios_cover_required_workloads() -> None:
    demos = demo_scenarios()

    assert len(demos) == 3
    assert all(demo.fictional is True for demo in demos)
    assert {demo.workload_type for demo in demos} == {
        "enterprise_rag",
        "real_time_inference",
        "hybrid_ai_platform",
    }
    assert {demo.name for demo in demos} == {
        "Fictional Northstar Private RAG",
        "Fictional Meridian Real-Time Inference",
        "Fictional Aster Hybrid AI Platform",
    }


def test_demo_seed_is_idempotent() -> None:
    repo = repository()

    assert seed_demo_scenarios(repo) == 3
    assert seed_demo_scenarios(repo) == 0
    assert len(repo.list_scenarios()) == 3
    assert len(repo.list_runs(repo.list_scenarios()[0]["id"])) == 1


def test_northstar_demo_matches_the_portfolio_case_contract() -> None:
    northstar = next(demo for demo in demo_scenarios() if "Northstar" in demo.name)

    assert northstar.name == "Fictional Northstar Private RAG"
    assert northstar.model_size_billion == 70
    assert northstar.latency_target_ms == 900
    assert northstar.throughput_target_rps == 45
    assert northstar.data_volume_tb == 18
    assert northstar.annual_growth_pct == 35
