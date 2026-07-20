"""Deterministic, dependency-free SVG renderer for controlled architecture blueprints."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from html import escape
from types import MappingProxyType
from typing import Final

from app.architecture import (
    ArchitectureBlueprint,
    ArchitectureEdge,
    ArchitectureNode,
    EdgeKind,
    NodeKind,
    build_blueprint,
)


@dataclass(frozen=True, slots=True)
class _NodeBox:
    x: int
    y: int
    width: int
    height: int


_CANVAS_WIDTH: Final = 1440
_CANVAS_HEIGHT: Final = 900
_NODE_LAYOUT: Final[Mapping[str, _NodeBox]] = MappingProxyType(
    {
        "applications": _NodeBox(52, 252, 190, 106),
        "api-gateway": _NodeBox(292, 252, 190, 106),
        "model-serving": _NodeBox(532, 252, 200, 112),
        "runtime": _NodeBox(782, 252, 200, 112),
        "gpu-compute": _NodeBox(1032, 252, 220, 112),
        "retrieval": _NodeBox(532, 438, 200, 112),
        "data-platform": _NodeBox(782, 438, 200, 112),
        "object-storage": _NodeBox(1032, 438, 220, 112),
        "network": _NodeBox(112, 650, 300, 102),
        "security": _NodeBox(570, 650, 300, 102),
        "observability": _NodeBox(1028, 650, 300, 102),
    }
)
_NODE_COLORS: Final[Mapping[NodeKind, tuple[str, str, str]]] = MappingProxyType(
    {
        NodeKind.ACTOR: ("#F2F6F5", "#C7D5D1", "#16312E"),
        NodeKind.ENTRY_POINT: ("#E9F5F1", "#73A89C", "#0E4A43"),
        NodeKind.SERVICE: ("#E9F0FF", "#7699D7", "#183B71"),
        NodeKind.ORCHESTRATOR: ("#F1EEFF", "#9180C5", "#3D2D72"),
        NodeKind.COMPUTE: ("#FFF0E6", "#D58B5B", "#713719"),
        NodeKind.DATA_SERVICE: ("#EAF6FB", "#72AABD", "#184E62"),
        NodeKind.STORAGE: ("#EEF3F5", "#7895A0", "#294853"),
        NodeKind.CONTROL: ("#F7F5EF", "#B5A978", "#51471D"),
    }
)
_EDGE_COLORS: Final[Mapping[EdgeKind, str]] = MappingProxyType(
    {
        EdgeKind.DATA_FLOW: "#55706A",
        EdgeKind.CONTROL: "#9B7A35",
        EdgeKind.TELEMETRY: "#6279A9",
    }
)
_VISIBLE_EDGE_LABELS: Final[frozenset[str]] = frozenset({"context", "connectivity"})


def _xml_text(value: str) -> str:
    return escape(value, quote=True)


def _wrap_label(value: str, *, width: int = 24, lines: int = 2) -> tuple[str, ...]:
    words = value.split()
    wrapped: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > width:
            wrapped.append(current)
            current = word
        else:
            current = candidate
    if current:
        wrapped.append(current)
    if len(wrapped) <= lines:
        return tuple(wrapped)
    final_line = " ".join(wrapped[lines - 1 :])
    if len(final_line) > width:
        final_line = f"{final_line[: width - 1].rstrip()}…"
    return (*wrapped[: lines - 1], final_line)


def _edge_path(edge: ArchitectureEdge) -> tuple[str, int, int]:
    source = _NODE_LAYOUT[edge.source]
    target = _NODE_LAYOUT[edge.target]
    if source.y > target.y:
        start_x = source.x + source.width // 2
        start_y = source.y
        end_x = target.x + target.width // 2
        end_y = target.y + target.height
        bend_y = (start_y + end_y) // 2
        path = f"M {start_x} {start_y} C {start_x} {bend_y}, {end_x} {bend_y}, {end_x} {end_y}"
    else:
        start_x = source.x + source.width
        start_y = source.y + source.height // 2
        end_x = target.x
        end_y = target.y + target.height // 2
        bend_x = (start_x + end_x) // 2
        path = f"M {start_x} {start_y} C {bend_x} {start_y}, {bend_x} {end_y}, {end_x} {end_y}"
    return path, (start_x + end_x) // 2, (start_y + end_y) // 2


def _render_edge(edge: ArchitectureEdge) -> str:
    path, label_x, label_y = _edge_path(edge)
    color = _EDGE_COLORS[edge.kind]
    dash = ' stroke-dasharray="7 6"' if edge.kind is not EdgeKind.DATA_FLOW else ""
    label_markup = ""
    if edge.label in _VISIBLE_EDGE_LABELS:
        label_markup = "\n".join(
            (
                (
                    f'      <rect x="{label_x - 44}" y="{label_y - 12}" '
                    'width="88" height="22" rx="11" fill="#FCFDFC" '
                    'stroke="#DCE4E1"/>'
                ),
                (
                    f'      <text x="{label_x}" y="{label_y + 4}" '
                    'text-anchor="middle" font-size="11" font-weight="600" '
                    f'fill="#4B625D">{_xml_text(edge.label.upper())}</text>'
                ),
            )
        )
    pieces = (
        f'    <g data-edge-kind="{edge.kind.value}" aria-label="{_xml_text(edge.label)}">',
        (
            f'      <path d="{path}" fill="none" stroke="{color}" '
            f'stroke-width="2"{dash} marker-end="url(#arrow-{edge.kind.value})"/>'
        ),
        *((label_markup,) if label_markup else ()),
        "    </g>",
    )
    return "\n".join(pieces)


def _render_node(node: ArchitectureNode) -> str:
    box = _NODE_LAYOUT[node.id]
    fill, stroke, text_color = _NODE_COLORS[node.kind]
    label_lines = _wrap_label(node.label)
    label_y = box.y + 42 - ((len(label_lines) - 1) * 10)
    tspans = "".join(
        f'<tspan x="{box.x + 18}" y="{label_y + index * 21}">{_xml_text(line)}</tspan>'
        for index, line in enumerate(label_lines)
    )
    detail_lines = _wrap_label(node.detail, width=34, lines=2)
    detail_y = box.y + box.height - 29 - ((len(detail_lines) - 1) * 6)
    detail_tspans = "".join(
        f'<tspan x="{box.x + 18}" y="{detail_y + index * 15}">{_xml_text(line)}</tspan>'
        for index, line in enumerate(detail_lines)
    )
    return "\n".join(
        (
            (
                f'    <g data-node-id="{node.id}" data-layer="{node.layer.value}" '
                f'data-node-kind="{node.kind.value}">'
            ),
            (
                f'      <rect x="{box.x}" y="{box.y}" width="{box.width}" '
                f'height="{box.height}" rx="14" fill="#0C211F" opacity="0.08" '
                'transform="translate(0 4)"/>'
            ),
            (
                f'      <rect x="{box.x}" y="{box.y}" width="{box.width}" '
                f'height="{box.height}" rx="14" fill="{fill}" stroke="{stroke}" '
                'stroke-width="1.5"/>'
            ),
            (
                f'      <rect x="{box.x}" y="{box.y}" width="6" '
                f'height="{box.height}" rx="3" fill="{stroke}"/>'
            ),
            f'      <text font-size="16" font-weight="700" fill="{text_color}">{tspans}</text>',
            f'      <text font-size="10.5" fill="#5C706C">{detail_tspans}</text>',
            "    </g>",
        )
    )


def _render_layer_heading(x: int, label: str) -> str:
    return (
        f'  <text x="{x}" y="203" font-size="11" font-weight="700" '
        f'letter-spacing="1.2" fill="#85958F">{label}</text>'
    )


def _render_control_heading() -> str:
    return (
        '  <text x="80" y="635" font-size="11" font-weight="700" '
        'letter-spacing="1.2" fill="#8A7B47">CROSS-CUTTING CONTROLS</text>'
    )


def render_architecture_svg(blueprint: ArchitectureBlueprint) -> str:
    """Render an inert, accessible SVG on a fixed presentation canvas."""

    if not isinstance(blueprint, ArchitectureBlueprint):
        raise TypeError("blueprint must be an ArchitectureBlueprint")
    missing_layout = {node.id for node in blueprint.nodes} - _NODE_LAYOUT.keys()
    if missing_layout:
        raise ValueError("blueprint contains nodes without a controlled layout")

    edge_markup = "\n".join(_render_edge(edge) for edge in blueprint.edges)
    node_markup = "\n".join(_render_node(node) for node in blueprint.nodes)
    title = _xml_text(blueprint.title)
    description = _xml_text(blueprint.description)
    markers = "\n".join(
        (
            f'      <marker id="arrow-{kind.value}" markerWidth="9" markerHeight="9" '
            'refX="8" refY="4.5" orient="auto">'
            f'<path d="M 0 0 L 9 4.5 L 0 9 z" fill="{_EDGE_COLORS[kind]}"/></marker>'
        )
        for kind in EdgeKind
    )

    return "\n".join(
        (
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{_CANVAS_WIDTH}" '
                f'height="{_CANVAS_HEIGHT}" viewBox="0 0 {_CANVAS_WIDTH} {_CANVAS_HEIGHT}" '
                'role="img" aria-labelledby="architecture-title architecture-description" '
                'font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif">'
            ),
            f'  <title id="architecture-title">{title}</title>',
            (
                f'  <desc id="architecture-description">{description} '
                "Initial solution hypothesis; requires technical validation.</desc>"
            ),
            "  <defs>",
            markers,
            "  </defs>",
            f'  <rect width="{_CANVAS_WIDTH}" height="{_CANVAS_HEIGHT}" fill="#F7FAF9"/>',
            (
                '  <rect x="28" y="28" width="1384" height="844" rx="24" '
                'fill="#FFFFFF" stroke="#DDE7E4"/>'
            ),
            (
                '  <text x="58" y="76" font-size="12" font-weight="700" '
                'letter-spacing="1.8" fill="#6D817C">'
                "ENTERPRISE AI SOLUTION CONFIGURATOR</text>"
            ),
            (
                f'  <text x="58" y="114" font-size="28" font-weight="750" '
                f'fill="#102E2A">{title}</text>'
            ),
            f'  <text x="58" y="143" font-size="14" fill="#60746F">{description}</text>',
            '  <line x1="58" y1="158" x2="1382" y2="158" stroke="#E4EBE9"/>',
            _render_layer_heading(58, "EXPERIENCE"),
            _render_layer_heading(298, "INGRESS"),
            _render_layer_heading(538, "AI SERVICES"),
            _render_layer_heading(788, "PLATFORM &amp; DATA"),
            _render_layer_heading(1038, "COMPUTE &amp; STORAGE"),
            (
                '  <rect x="58" y="610" width="1324" height="174" rx="18" '
                'fill="#FBFAF6" stroke="#E8E2CF"/>'
            ),
            _render_control_heading(),
            '  <g aria-label="Architecture relationships">',
            edge_markup,
            "  </g>",
            '  <g aria-label="Architecture components">',
            node_markup,
            "  </g>",
            '  <rect x="58" y="816" width="1324" height="34" rx="10" fill="#EAF3F0"/>',
            (
                '  <text x="720" y="838" text-anchor="middle" font-size="12" '
                'font-weight="700" letter-spacing="0.8" fill="#315A53">'
                "INITIAL SOLUTION HYPOTHESIS · REQUIRES TECHNICAL VALIDATION</text>"
            ),
            "</svg>",
        )
    )


def render_assessment_svg(assessment: Mapping[str, object]) -> str:
    """Build and render an engine assessment through the controlled diagram boundary."""

    return render_architecture_svg(build_blueprint(assessment))


__all__ = ["render_architecture_svg", "render_assessment_svg"]
