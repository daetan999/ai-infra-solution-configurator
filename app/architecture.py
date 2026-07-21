"""Controlled architecture blueprints derived from deterministic engine assessments.

This module deliberately depends on mappings rather than the rules engine's internal types. The
boundary keeps diagram generation reusable while the allowlists below prevent assessment content
from inventing node or edge types.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class ArchitectureLayer(StrEnum):
    """Allowlisted visual and semantic layers in a generated architecture."""

    EXPERIENCE = "experience"
    INGRESS = "ingress"
    SERVING = "serving"
    PLATFORM = "platform"
    COMPUTE = "compute"
    RETRIEVAL = "retrieval"
    DATA = "data"
    STORAGE = "storage"
    NETWORK = "network"
    SECURITY = "security"
    OBSERVABILITY = "observability"


class NodeKind(StrEnum):
    """Allowlisted presentation styles for architecture nodes."""

    ACTOR = "actor"
    ENTRY_POINT = "entry-point"
    SERVICE = "service"
    ORCHESTRATOR = "orchestrator"
    COMPUTE = "compute"
    DATA_SERVICE = "data-service"
    STORAGE = "storage"
    CONTROL = "control"


class EdgeKind(StrEnum):
    """Allowlisted relationships between controlled nodes."""

    DATA_FLOW = "data-flow"
    CONTROL = "control"
    TELEMETRY = "telemetry"


_SAFE_ID: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9-]{0,47}$")
_EXTERNAL_REFERENCE: Final[re.Pattern[str]] = re.compile(
    r"(?:https?|ftp)://[^\s<>'\"]+", re.IGNORECASE
)
_CONTROL_CHARACTERS: Final[re.Pattern[str]] = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _validate_text(value: object, field: str, *, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    if not value.strip():
        raise ValueError(f"{field} must not be blank")
    if len(value) > maximum:
        raise ValueError(f"{field} must be at most {maximum} characters")
    if _CONTROL_CHARACTERS.search(value):
        raise ValueError(f"{field} contains control characters")
    return value


@dataclass(frozen=True, slots=True)
class ArchitectureNode:
    """A validated component selected from the architecture allowlist."""

    id: str
    label: str
    detail: str
    layer: ArchitectureLayer
    kind: NodeKind

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not _SAFE_ID.fullmatch(self.id):
            raise ValueError("node id must use safe kebab-case")
        _validate_text(self.label, "node label", maximum=96)
        _validate_text(self.detail, "node detail", maximum=160)
        if not isinstance(self.layer, ArchitectureLayer):
            raise ValueError("node layer must be allowlisted")
        if not isinstance(self.kind, NodeKind):
            raise ValueError("node kind must be allowlisted")


@dataclass(frozen=True, slots=True)
class ArchitectureEdge:
    """A validated relationship whose endpoints are checked by the blueprint."""

    source: str
    target: str
    kind: EdgeKind
    label: str

    def __post_init__(self) -> None:
        if not isinstance(self.source, str) or not _SAFE_ID.fullmatch(self.source):
            raise ValueError("edge source must use safe kebab-case")
        if not isinstance(self.target, str) or not _SAFE_ID.fullmatch(self.target):
            raise ValueError("edge target must use safe kebab-case")
        if self.source == self.target:
            raise ValueError("edge endpoints must differ")
        if not isinstance(self.kind, EdgeKind):
            raise ValueError("edge kind must be allowlisted")
        _validate_text(self.label, "edge label", maximum=48)


@dataclass(frozen=True, slots=True)
class ArchitectureBlueprint:
    """An immutable, internally consistent diagram-ready solution hypothesis."""

    title: str
    description: str
    nodes: tuple[ArchitectureNode, ...]
    edges: tuple[ArchitectureEdge, ...]

    def __post_init__(self) -> None:
        _validate_text(self.title, "blueprint title", maximum=120)
        _validate_text(self.description, "blueprint description", maximum=240)
        if not isinstance(self.nodes, tuple) or not all(
            isinstance(node, ArchitectureNode) for node in self.nodes
        ):
            raise ValueError("blueprint nodes must be a tuple of ArchitectureNode values")
        if not isinstance(self.edges, tuple) or not all(
            isinstance(edge, ArchitectureEdge) for edge in self.edges
        ):
            raise ValueError("blueprint edges must be a tuple of ArchitectureEdge values")
        if not self.nodes:
            raise ValueError("blueprint must include at least one node")

        node_ids = tuple(node.id for node in self.nodes)
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("blueprint node ids must be unique")
        known_ids = frozenset(node_ids)
        for edge in self.edges:
            if edge.source not in known_ids or edge.target not in known_ids:
                raise ValueError("blueprint edge has an unknown endpoint")
        edge_keys = tuple((edge.source, edge.target, edge.kind) for edge in self.edges)
        if len(edge_keys) != len(set(edge_keys)):
            raise ValueError("blueprint edges must be unique")


@dataclass(frozen=True, slots=True)
class _NodeDefinition:
    id: str
    layer: ArchitectureLayer
    kind: NodeKind
    default_label: str
    detail: str
    architecture_keys: tuple[str, ...]
    trace_layers: tuple[str, ...]


_NODE_DEFINITIONS: Final[tuple[_NodeDefinition, ...]] = (
    _NodeDefinition(
        "applications",
        ArchitectureLayer.EXPERIENCE,
        NodeKind.ACTOR,
        "Users & applications",
        "Approved enterprise consumers",
        (),
        ("applications", "users"),
    ),
    _NodeDefinition(
        "api-gateway",
        ArchitectureLayer.INGRESS,
        NodeKind.ENTRY_POINT,
        "API & policy gateway",
        "Authenticated request entry",
        ("api_gateway", "gateway"),
        ("api_gateway", "gateway", "ingress"),
    ),
    _NodeDefinition(
        "model-serving",
        ArchitectureLayer.SERVING,
        NodeKind.SERVICE,
        "Model serving",
        "Versioned inference endpoints",
        ("model_serving",),
        ("model_serving", "serving"),
    ),
    _NodeDefinition(
        "runtime",
        ArchitectureLayer.PLATFORM,
        NodeKind.ORCHESTRATOR,
        "Managed AI runtime",
        "Scheduling and workload lifecycle",
        ("orchestration",),
        ("orchestration", "runtime", "kubernetes"),
    ),
    _NodeDefinition(
        "gpu-compute",
        ArchitectureLayer.COMPUTE,
        NodeKind.COMPUTE,
        "Accelerator compute",
        "Isolated execution capacity",
        ("accelerator_approach", "compute_layer"),
        ("accelerator_approach", "compute_layer", "compute", "accelerator"),
    ),
    _NodeDefinition(
        "retrieval",
        ArchitectureLayer.RETRIEVAL,
        NodeKind.DATA_SERVICE,
        "Retrieval & feature services",
        "Governed context assembly",
        ("feature_or_retrieval_layer",),
        ("feature_or_retrieval_layer", "retrieval", "feature_layer"),
    ),
    _NodeDefinition(
        "data-platform",
        ArchitectureLayer.DATA,
        NodeKind.DATA_SERVICE,
        "Enterprise data platform",
        "Curated and governed data products",
        ("data_layer",),
        ("data_layer", "data", "data_platform"),
    ),
    _NodeDefinition(
        "object-storage",
        ArchitectureLayer.STORAGE,
        NodeKind.STORAGE,
        "Encrypted object storage",
        "Models, artifacts, and source data",
        ("storage",),
        ("storage", "object_storage"),
    ),
    _NodeDefinition(
        "network",
        ArchitectureLayer.NETWORK,
        NodeKind.CONTROL,
        "Private network fabric",
        "Segmentation and controlled connectivity",
        ("networking",),
        ("networking", "network"),
    ),
    _NodeDefinition(
        "security",
        ArchitectureLayer.SECURITY,
        NodeKind.CONTROL,
        "Identity & security controls",
        "Policy, secrets, and workload identity",
        ("security", "identity"),
        ("security", "identity", "iam"),
    ),
    _NodeDefinition(
        "observability",
        ArchitectureLayer.OBSERVABILITY,
        NodeKind.CONTROL,
        "Platform observability",
        "Metrics, logs, traces, and model signals",
        ("observability",),
        ("observability", "monitoring"),
    ),
)

_RETRIEVAL_MARKERS: Final[tuple[str, ...]] = (
    "rag",
    "retrieval",
    "feature",
    "embedding",
    "vector",
)
_ABSENT_COMPONENTS: Final[frozenset[str]] = frozenset(
    {"", "none", "not applicable", "not required", "n/a"}
)


def _normalise_key(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _normalise_label(value: object, fallback: str) -> str:
    if not isinstance(value, str):
        return fallback
    without_controls = _CONTROL_CHARACTERS.sub("", value)
    without_links = _EXTERNAL_REFERENCE.sub("[external reference removed]", without_controls)
    collapsed = " ".join(without_links.split()).strip()
    if not collapsed:
        return fallback
    if len(collapsed) <= 96:
        return collapsed
    return f"{collapsed[:92].rstrip()}…"


def _component_text(value: object) -> str | None:
    if isinstance(value, str):
        candidate = value
    elif isinstance(value, Mapping):
        candidate = next(
            (
                value.get(key)
                for key in (
                    "component_or_pattern",
                    "recommended_component_or_pattern",
                    "recommendation",
                    "component",
                    "pattern",
                )
                if isinstance(value.get(key), str)
            ),
            None,
        )
    else:
        candidate = None
    if not isinstance(candidate, str) or candidate.strip().lower() in _ABSENT_COMPONENTS:
        return None
    return candidate


def _extract_components(
    architecture: Mapping[str, object], recommendations: Sequence[object]
) -> dict[str, str]:
    components: dict[str, str] = {}

    for definition in _NODE_DEFINITIONS:
        for key in definition.architecture_keys:
            component = _component_text(architecture.get(key))
            if component is not None:
                components[definition.id] = component
                break

    trace_entries = sorted(
        (entry for entry in recommendations if isinstance(entry, Mapping)),
        key=lambda entry: (
            _normalise_key(entry.get("layer") or entry.get("area")),
            str(entry.get("rule_id", "")),
            str(_component_text(entry) or ""),
        ),
    )
    for entry in trace_entries:
        layer = _normalise_key(entry.get("layer") or entry.get("area"))
        component = _component_text(entry)
        if component is None:
            continue
        for definition in _NODE_DEFINITIONS:
            if layer in definition.trace_layers:
                components.setdefault(definition.id, component)
                break
    return components


def _display_name(value: object, fallback: str) -> str:
    key = _normalise_key(value)
    return key.replace("_", " ").title() if key else fallback


def _include_retrieval(
    requirements: Mapping[str, object],
    architecture: Mapping[str, object],
    components: Mapping[str, str],
) -> bool:
    if "retrieval" in components:
        return True
    architecture_component = _component_text(architecture.get("feature_or_retrieval_layer"))
    if architecture_component is not None:
        return True
    workload = " ".join(
        str(requirements.get(key, "")).lower() for key in ("workload_type", "workload", "use_case")
    )
    return any(marker in workload for marker in _RETRIEVAL_MARKERS)


def _build_edges(include_retrieval: bool) -> tuple[ArchitectureEdge, ...]:
    data_entry = "retrieval" if include_retrieval else "data-platform"
    retrieval_pair = (
        (("retrieval", "data-platform", "governed query"),) if include_retrieval else ()
    )
    flow_pairs = (
        ("applications", "api-gateway", "requests"),
        ("api-gateway", "model-serving", "inference"),
        ("model-serving", "runtime", "workloads"),
        ("runtime", "gpu-compute", "schedules"),
        ("api-gateway", data_entry, "context"),
        *retrieval_pair,
        ("data-platform", "object-storage", "artifacts"),
    )
    flow_edges = tuple(
        ArchitectureEdge(source, target, EdgeKind.DATA_FLOW, label)
        for source, target, label in flow_pairs
    )
    control_edges = (
        ArchitectureEdge("network", "api-gateway", EdgeKind.CONTROL, "connectivity"),
        ArchitectureEdge("security", "data-platform", EdgeKind.CONTROL, "policy"),
        ArchitectureEdge("observability", "object-storage", EdgeKind.TELEMETRY, "telemetry"),
    )
    return (*flow_edges, *control_edges)


def _blueprint_inputs(
    assessment: Mapping[str, object],
) -> tuple[Mapping[str, object], Mapping[str, object], Sequence[object]]:
    if not isinstance(assessment, Mapping):
        raise ValueError("assessment must be a mapping")
    requirements_value = assessment.get("requirements", {})
    if not isinstance(requirements_value, Mapping):
        raise ValueError("requirements must be a mapping")
    architecture_value = assessment.get("architecture", {})
    if not isinstance(architecture_value, Mapping):
        raise ValueError("architecture must be a mapping")
    recommendations_value = assessment.get("recommendations", ())
    if isinstance(recommendations_value, (str, bytes)) or not isinstance(
        recommendations_value, Sequence
    ):
        raise ValueError("recommendations must be a sequence")
    return requirements_value, architecture_value, recommendations_value


def build_blueprint(assessment: Mapping[str, object]) -> ArchitectureBlueprint:
    """Create a deterministic allowlisted blueprint from an engine assessment mapping.

    Unknown recommendation layers are ignored. Assessment values may customize controlled labels,
    but they cannot add SVG primitives, node kinds, identifiers, relationships, or coordinates.
    """

    requirements_value, architecture_value, recommendations_value = _blueprint_inputs(assessment)
    components = _extract_components(architecture_value, recommendations_value)
    has_retrieval = _include_retrieval(requirements_value, architecture_value, components)
    nodes = tuple(
        ArchitectureNode(
            id=definition.id,
            label=_normalise_label(components.get(definition.id), definition.default_label),
            detail=definition.detail,
            layer=definition.layer,
            kind=definition.kind,
        )
        for definition in _NODE_DEFINITIONS
        if definition.id != "retrieval" or has_retrieval
    )

    raw_title = assessment.get("scenario_name") or assessment.get("name")
    title = _normalise_label(raw_title, "Enterprise AI solution architecture")
    placement = (
        assessment.get("deployment_pattern")
        or assessment.get("placement")
        or requirements_value.get("deployment_pattern")
        or requirements_value.get("cloud_preference")
    )
    workload = requirements_value.get("workload_type") or requirements_value.get("workload")
    description = (
        f"{_display_name(placement, 'Controlled')} solution hypothesis for "
        f"{_display_name(workload, 'Enterprise AI')}."
    )
    return ArchitectureBlueprint(
        title=title,
        description=description,
        nodes=nodes,
        edges=_build_edges(has_retrieval),
    )


__all__ = [
    "ArchitectureBlueprint",
    "ArchitectureEdge",
    "ArchitectureLayer",
    "ArchitectureNode",
    "EdgeKind",
    "NodeKind",
    "build_blueprint",
]
