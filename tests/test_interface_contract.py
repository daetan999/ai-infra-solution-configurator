"""Contract tests for the guided configurator interface."""

from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "index.html"
SCRIPT = ROOT / "static" / "app.js"
STYLES = ROOT / "static" / "styles.css"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_interface_has_five_labelled_wizard_stages_and_every_requirement() -> None:
    html = unescape(_read(TEMPLATE))

    assert html.count('class="stage-tab"') == 5
    for stage in ("Intent", "Service targets", "Placement & data", "Operations", "Constraints"):
        assert stage in html

    for field in (
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
    ):
        assert f'name="{field}"' in html


def test_interface_exposes_explainability_and_solution_workshop_outputs() -> None:
    html = _read(TEMPLATE)

    for identifier in (
        "scenario-rail",
        "requirement-summary",
        "recommendation-traces",
        "solution-risks",
        "solution-assumptions",
        "solution-alternatives",
        "solution-confidence",
        "poc-recommendation",
        "next-workshop",
        "architecture-diagram",
    ):
        assert f'id="{identifier}"' in html

    for export_format in ("json", "markdown", "svg"):
        assert f'data-export-format="{export_format}"' in html


def test_client_uses_scenario_endpoints_without_mock_recommendations_or_unsafe_html() -> None:
    script = _read(SCRIPT)

    assert '"/api/scenarios"' in script
    assert "/diagram.svg" in script
    assert "/export?format=" in script
    assert "AbortController" in script
    assert "textContent" in script
    assert "innerHTML" not in script
    assert "mock" not in script.lower()


def test_accessibility_and_responsive_behaviour_are_explicit() -> None:
    html = _read(TEMPLATE)
    css = _read(STYLES)

    assert 'href="#workspace"' in html
    assert 'aria-live="polite"' in html
    assert 'aria-describedby="recommendation-disclaimer"' in html
    assert 'id="engine-status-label"' in html
    assert 'aria-controls="solution-assumptions"' in html
    assert 'aria-labelledby="assumptions-tab"' in html
    assert "@media (max-width: 760px)" in css
    assert "prefers-reduced-motion: reduce" in css
    assert ":focus-visible" in css


def test_wizard_validation_health_and_tab_keyboard_behaviour_are_bound() -> None:
    script = _read(SCRIPT)

    assert "findFirstInvalidStage" in script
    assert "navigateToStage" in script
    assert "checkHealth" in script
    assert 'case "ArrowRight"' in script
    assert 'case "ArrowLeft"' in script


def test_scenario_switching_preserves_update_target_and_unsaved_drafts() -> None:
    script = _read(SCRIPT)
    selection = script[
        script.index("async function selectScenario") : script.index("function setStage")
    ]

    assert selection.index("await apiFetch") < selection.index(
        "state.activeScenarioId = bundle.scenario.id"
    )
    assert "state.dirty" in script
    assert "window.confirm" in script
    assert "Discard unsaved changes" in script


def test_compact_stage_navigation_retains_accessible_names() -> None:
    html = _read(TEMPLATE)

    for stage, label in enumerate(
        ("Intent", "Service targets", "Placement and data", "Operations", "Constraints"),
        start=1,
    ):
        assert f'aria-label="Stage {stage}: {label}"' in html


def test_documentation_assets_are_original_accessible_svg() -> None:
    for name in ("configurator-hero.svg", "configuration-workflow.svg", "rules-engine.svg"):
        svg = _read(ROOT / "docs" / "assets" / name)
        assert svg.startswith("<svg")
        assert "<title" in svg
        assert "<desc" in svg
        assert 'role="img"' in svg
