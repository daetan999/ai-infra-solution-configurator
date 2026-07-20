"""Deterministic, presentation-ready assessment exports."""

from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as element_tree
from collections.abc import Mapping, Sequence


def _safe_text(value: object) -> str:
    return html.escape(str(value), quote=False).replace("\r", " ").replace("\n", " ")


def json_export(run: Mapping[str, object]) -> str:
    """Build a stable JSON solution brief without embedding duplicate SVG markup."""

    payload = {
        "export_schema_version": "1.0",
        "solution_brief": {
            "scenario_id": run["scenario_id"],
            "scenario_version": run["scenario_version"],
            "scenario_name": run["scenario_name"],
            "scenario_description": run["scenario_description"],
            "requirements": run["requirements"],
            "assessment": run["assessment"],
            "blueprint": run["blueprint"],
            "created_at": run["created_at"],
        },
        "disclaimer": (
            "This export is an initial solution hypothesis for discovery and workshops. "
            "It requires technical validation and does not replace a formal architecture review."
        ),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _bullet_lines(values: object, fallback: str) -> list[str]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)) or not values:
        return [f"- {fallback}"]
    return [f"- {_safe_text(value)}" for value in values]


def _risk_lines(values: object) -> list[str]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)) or not values:
        return ["- Validate solution risks during formal architecture review."]
    lines: list[str] = []
    for value in values:
        if isinstance(value, Mapping):
            lines.extend(
                [
                    f"### {_safe_text(value.get('layer', 'Solution')).replace('_', ' ').title()}",
                    "",
                    f"- **Risk:** {_safe_text(value.get('risk', 'Requires validation'))}",
                    "- **Mitigation:** "
                    + _safe_text(value.get("mitigation", "Validate during architecture review")),
                    "",
                ]
            )
        else:
            lines.append(f"- {_safe_text(value)}")
    return lines


def _poc_lines(value: object) -> list[str]:
    if not isinstance(value, Mapping):
        return [_safe_text(value or "Run a bounded workload validation."), ""]
    duration = value.get("duration_weeks")
    lines = [
        "### Objective",
        "",
        _safe_text(value.get("objective", "Validate the proposed solution.")),
        "",
        "### Scope",
        "",
        _safe_text(value.get("scope", "One representative workload and environment.")),
        "",
    ]
    if duration is not None:
        lines.extend(["### Duration", "", f"{_safe_text(duration)} weeks", ""])
    lines.extend(["### Success criteria", ""])
    lines.extend(_bullet_lines(value.get("success_criteria"), "Agree measurable exit criteria."))
    lines.extend(
        [
            "",
            "### Exit decision",
            "",
            _safe_text(value.get("exit_decision", "Proceed, revise, or stop based on evidence.")),
            "",
        ]
    )
    return lines


def _workshop_lines(value: object) -> list[str]:
    if not isinstance(value, Mapping):
        return [_safe_text(value or "Architecture validation and operating-model workshop."), ""]
    lines = [
        f"### {_safe_text(value.get('title', 'Architecture validation workshop'))}",
        "",
    ]
    duration = value.get("duration_minutes")
    if duration is not None:
        lines.extend([f"**Duration:** {_safe_text(duration)} minutes", ""])
    lines.extend(["### Participants", ""])
    lines.extend(_bullet_lines(value.get("participants"), "Solution stakeholders"))
    lines.extend(["", "### Agenda", ""])
    lines.extend(_bullet_lines(value.get("agenda"), "Resolve evidence gaps and agree validation."))
    lines.append("")
    return lines


def markdown_export(run: Mapping[str, object]) -> str:
    """Build an executive-readable brief from the stored assessment snapshot."""

    assessment = run.get("assessment", {})
    assessment = assessment if isinstance(assessment, Mapping) else {}
    recommendations = assessment.get("recommendations", [])
    lines = [
        "# Enterprise AI Solution Brief",
        "",
        f"**Scenario:** {_safe_text(run['scenario_name'])}",
        f"**Version:** {_safe_text(run['scenario_version'])}",
        f"**Generated:** {_safe_text(run['created_at'])}",
        "",
        _safe_text(run["scenario_description"]),
        "",
        "## Recommended architecture",
        "",
    ]
    if isinstance(recommendations, Sequence) and not isinstance(recommendations, (str, bytes)):
        for recommendation in recommendations:
            if not isinstance(recommendation, Mapping):
                continue
            component = recommendation.get(
                "recommended_component_or_pattern", recommendation.get("recommendation", "Review")
            )
            lines.extend(
                [
                    f"### {_safe_text(recommendation.get('layer', 'Solution pattern')).title()}",
                    "",
                    "- **Requirement:** "
                    + _safe_text(recommendation.get("customer_requirement", "Not stated")),
                    f"- **Rule:** {_safe_text(recommendation.get('rule_triggered', 'Not stated'))}",
                    f"- **Recommendation:** {_safe_text(component)}",
                    f"- **Reason:** {_safe_text(recommendation.get('reason', 'Not stated'))}",
                    "- **Alternative:** "
                    + _safe_text(recommendation.get("alternative", "Validate during discovery")),
                    "- **Risk:** "
                    + _safe_text(recommendation.get("risk", "Requires technical validation")),
                    "- **Required validation:** "
                    + _safe_text(
                        recommendation.get("required_validation", "Architecture workshop")
                    ),
                    "",
                ]
            )
    lines.extend(["## Primary risks", ""])
    lines.extend(_risk_lines(assessment.get("primary_risks")))
    lines.extend(["", "## Open questions", ""])
    lines.extend(
        _bullet_lines(assessment.get("open_questions"), "Confirm requirements with stakeholders.")
    )
    lines.extend(
        [
            "",
            "## Recommended proof of concept",
            "",
        ]
    )
    lines.extend(_poc_lines(assessment.get("recommended_poc")))
    lines.extend(["## Recommended next workshop", ""])
    lines.extend(_workshop_lines(assessment.get("recommended_next_workshop")))
    lines.extend(
        [
            "---",
            "",
            (
                "This is an initial solution hypothesis for discovery and workshops. It requires "
                "technical validation and does not replace a formal architecture review."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def validate_svg_export(svg: object) -> str:
    """Reject active or externally addressable SVG content before download."""

    if not isinstance(svg, str) or not svg.lstrip().startswith("<svg"):
        raise ValueError("stored architecture is not SVG")
    if len(svg.encode("utf-8")) > 2_000_000:
        raise ValueError("stored architecture SVG is too large")
    lowered = svg.lower()
    if any(token in lowered for token in ("<!doctype", "<!entity", "<?xml-stylesheet")):
        raise ValueError("stored architecture SVG contains unsafe content")
    try:
        root = element_tree.fromstring(svg)
    except element_tree.ParseError as error:
        raise ValueError("stored architecture SVG is malformed") from error

    def local_name(qualified_name: str) -> str:
        return qualified_name.rsplit("}", 1)[-1].lower()

    if local_name(root.tag) != "svg":
        raise ValueError("stored architecture is not SVG")
    blocked_elements = {
        "script",
        "style",
        "foreignobject",
        "iframe",
        "object",
        "embed",
        "image",
        "set",
        "animate",
        "animatemotion",
        "animatetransform",
        "discard",
    }
    for element in root.iter():
        if local_name(element.tag) in blocked_elements:
            raise ValueError("stored architecture SVG contains unsafe content")
        for attribute, value in element.attrib.items():
            attribute_name = local_name(attribute)
            normalized_value = value.strip().lower()
            has_external_url = (
                "url(" in normalized_value
                and re.fullmatch(r"url\(#[a-z0-9_.:-]+\)", normalized_value) is None
            )
            if (
                attribute_name.startswith("on")
                or "javascript:" in normalized_value
                or has_external_url
            ):
                raise ValueError("stored architecture SVG contains unsafe content")
            if attribute_name in {"href", "src"} and not normalized_value.startswith("#"):
                raise ValueError("stored architecture SVG contains unsafe content")
    return svg
