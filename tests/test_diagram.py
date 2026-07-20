"""Contract tests for deterministic, controlled architecture diagrams."""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.architecture import (
    ArchitectureBlueprint,
    ArchitectureEdge,
    ArchitectureLayer,
    ArchitectureNode,
    EdgeKind,
    NodeKind,
    build_blueprint,
)
from app.diagram import render_architecture_svg, render_assessment_svg


PRIVATE_RAG_ASSESSMENT = {
    "scenario_name": "Northstar Private Enterprise RAG",
    "requirements": {
        "workload_type": "retrieval_augmented_generation",
        "deployment_pattern": "private_cloud",
        "data_sensitivity": "restricted",
        "existing_kubernetes": True,
    },
    "recommendations": [
        {
            "layer": "model_serving",
            "recommended_component_or_pattern": "Private inference endpoints",
        },
        {
            "layer": "orchestration",
            "recommended_component_or_pattern": "Existing Kubernetes platform",
        },
        {
            "layer": "retrieval",
            "recommended_component_or_pattern": "Governed vector retrieval",
        },
        {
            "layer": "security",
            "recommended_component_or_pattern": "Workload identity and policy",
        },
    ],
}


def test_builder_maps_engine_assessment_to_allowlisted_blueprint() -> None:
    blueprint = build_blueprint(PRIVATE_RAG_ASSESSMENT)

    assert blueprint.title == "Northstar Private Enterprise RAG"
    assert tuple(node.id for node in blueprint.nodes) == (
        "applications",
        "api-gateway",
        "model-serving",
        "runtime",
        "gpu-compute",
        "retrieval",
        "data-platform",
        "object-storage",
        "network",
        "security",
        "observability",
    )
    assert all(isinstance(node.kind, NodeKind) for node in blueprint.nodes)
    assert all(isinstance(node.layer, ArchitectureLayer) for node in blueprint.nodes)
    assert {edge.source for edge in blueprint.edges} <= {node.id for node in blueprint.nodes}
    assert {edge.target for edge in blueprint.edges} <= {node.id for node in blueprint.nodes}
    assert next(node for node in blueprint.nodes if node.id == "model-serving").label == (
        "Private inference endpoints"
    )


def test_builder_is_deterministic_when_trace_order_changes() -> None:
    reversed_trace = {
        **PRIVATE_RAG_ASSESSMENT,
        "recommendations": list(reversed(PRIVATE_RAG_ASSESSMENT["recommendations"])),
    }

    assert build_blueprint(PRIVATE_RAG_ASSESSMENT) == build_blueprint(reversed_trace)
    assert render_assessment_svg(PRIVATE_RAG_ASSESSMENT) == render_assessment_svg(
        reversed_trace
    )


def test_builder_adapts_hybrid_sensitive_assessment_without_engine_imports() -> None:
    assessment = {
        "scenario_name": "Fictional Hybrid Sensitive AI",
        "requirements": {
            "workload_type": "real_time_inference",
            "deployment_pattern": "hybrid",
            "data_sensitivity": "highly_sensitive",
        },
        "recommendations": [
            {
                "layer": "networking",
                "recommended_component_or_pattern": "Private interconnect",
            },
            {
                "layer": "compute",
                "recommended_component_or_pattern": "Dedicated accelerator pool",
            },
        ],
    }

    blueprint = build_blueprint(assessment)

    assert "Hybrid" in blueprint.description
    assert next(node for node in blueprint.nodes if node.id == "network").label == (
        "Private interconnect"
    )
    assert next(node for node in blueprint.nodes if node.id == "gpu-compute").label == (
        "Dedicated accelerator pool"
    )
    assert "retrieval" not in {node.id for node in blueprint.nodes}


def test_builder_prefers_engine_architecture_components_when_available() -> None:
    assessment = {
        "scenario_name": "Fictional Governed Platform",
        "requirements": {"workload_type": "rag", "deployment_pattern": "hybrid"},
        "deployment_pattern": "hybrid",
        "architecture": {
            "accelerator_approach": {
                "component_or_pattern": "Partitioned accelerator pools",
                "rule_id": "ACC-004",
                "priority": "high",
            },
            "feature_or_retrieval_layer": {
                "component_or_pattern": "Policy-filtered retrieval service",
                "rule_id": "RET-002",
                "priority": "high",
            },
            "identity": {
                "component_or_pattern": "Federated workload identity",
                "rule_id": "IAM-001",
                "priority": "high",
            },
        },
        "recommendations": [
            {
                "layer": "compute_layer",
                "recommended_component_or_pattern": "Lower-priority trace fallback",
            }
        ],
    }

    blueprint = build_blueprint(assessment)

    labels = {node.id: node.label for node in blueprint.nodes}
    assert labels["gpu-compute"] == "Partitioned accelerator pools"
    assert labels["retrieval"] == "Policy-filtered retrieval service"
    assert labels["security"] == "Federated workload identity"


def test_unknown_trace_layers_cannot_add_arbitrary_nodes() -> None:
    assessment = {
        **PRIVATE_RAG_ASSESSMENT,
        "recommendations": [
            *PRIVATE_RAG_ASSESSMENT["recommendations"],
            {
                "layer": "<script>arbitrary</script>",
                "recommended_component_or_pattern": "Injected component",
            },
        ],
    }

    blueprint = build_blueprint(assessment)

    assert "Injected component" not in {node.label for node in blueprint.nodes}
    assert {node.id for node in blueprint.nodes} <= {
        "applications",
        "api-gateway",
        "model-serving",
        "runtime",
        "gpu-compute",
        "retrieval",
        "data-platform",
        "object-storage",
        "network",
        "security",
        "observability",
    }


@pytest.mark.parametrize(
    ("assessment", "message"),
    [
        ([], "assessment must be a mapping"),
        ({"requirements": []}, "requirements must be a mapping"),
        ({"requirements": {}, "recommendations": {}}, "recommendations must be a sequence"),
    ],
)
def test_builder_rejects_malformed_assessment_boundaries(
    assessment: object, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        build_blueprint(assessment)  # type: ignore[arg-type]


def test_blueprint_validates_ids_uniqueness_and_edge_endpoints() -> None:
    node = ArchitectureNode(
        id="applications",
        label="Applications",
        detail="Fictional workload entry points",
        layer=ArchitectureLayer.EXPERIENCE,
        kind=NodeKind.ACTOR,
    )

    with pytest.raises(ValueError, match="safe kebab-case"):
        replace(node, id="unsafe id")
    with pytest.raises(ValueError, match="unique"):
        ArchitectureBlueprint(
            title="Duplicate",
            description="Invalid duplicate node demonstration",
            nodes=(node, node),
            edges=(),
        )
    with pytest.raises(ValueError, match="unknown endpoint"):
        ArchitectureBlueprint(
            title="Dangling",
            description="Invalid dangling edge demonstration",
            nodes=(node,),
            edges=(
                ArchitectureEdge(
                    source="applications",
                    target="missing-node",
                    kind=EdgeKind.DATA_FLOW,
                    label="request",
                ),
            ),
        )


def test_renderer_produces_accessible_fixed_canvas_with_system_fonts() -> None:
    svg = render_architecture_svg(build_blueprint(PRIVATE_RAG_ASSESSMENT))

    assert svg.startswith("<svg ")
    assert 'viewBox="0 0 1440 900"' in svg
    assert 'width="1440" height="900"' in svg
    assert 'role="img" aria-labelledby="architecture-title architecture-description"' in svg
    assert '<title id="architecture-title">Northstar Private Enterprise RAG</title>' in svg
    assert '<desc id="architecture-description">' in svg
    assert "-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" in svg
    assert 'data-node-id="applications"' in svg
    assert 'data-node-id="retrieval"' in svg
    assert 'data-layer="security"' in svg


def test_renderer_escapes_untrusted_text_and_remains_inert() -> None:
    assessment = {
        **PRIVATE_RAG_ASSESSMENT,
        "scenario_name": '<script>alert("title")</script>',
        "recommendations": [
            {
                "layer": "model_serving",
                "recommended_component_or_pattern": '<image href="https://bad.invalid/x"/>',
            }
        ],
    }

    svg = render_assessment_svg(assessment)
    lower_svg = svg.lower()

    assert "&lt;script&gt;alert(&quot;" in svg
    assert "&lt;image href=&quot;" in svg
    assert "<script" not in lower_svg
    assert "<foreignobject" not in lower_svg
    assert "javascript:" not in lower_svg
    assert "https://bad.invalid" not in svg
    assert ' href="' not in lower_svg


def test_renderer_is_stable_and_allows_only_known_svg_elements() -> None:
    svg = render_architecture_svg(build_blueprint(PRIVATE_RAG_ASSESSMENT))

    assert svg == render_architecture_svg(build_blueprint(PRIVATE_RAG_ASSESSMENT))
    for forbidden in ("<iframe", "<object", "<embed", "<audio", "<video", "<canvas"):
        assert forbidden not in svg.lower()
