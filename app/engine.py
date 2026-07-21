"""Pure, deterministic solution assessment engine."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from app.domain import ARCHITECTURE_LAYERS, EVIDENCE_FIELDS, Rule
from app.rules import (
    RULESET_VERSION,
    matching_rules,
    normalize_requirements,
    resolve_rule_conflicts,
    ruleset_digest,
)

EVIDENCE_GUIDANCE = {
    "workload_type": (
        "architecture scope",
        "Confirm the primary user journey and workload boundary.",
    ),
    "lifecycle_mode": (
        "compute and serving topology",
        "Confirm whether the platform supports training, inference, or both.",
    ),
    "model_size_billion": (
        "accelerator memory and runtime choice",
        "Provide the target model parameter count and expected precision.",
    ),
    "latency_target_ms": (
        "serving headroom and placement",
        "Define the latency percentile, measurement boundary, and target in milliseconds.",
    ),
    "throughput_target_rps": (
        "capacity and network sizing",
        "Provide average and peak requests per second with concurrency.",
    ),
    "data_volume_tb": (
        "storage, indexing, and migration",
        "Estimate source, active, index, and growth volumes in terabytes.",
    ),
    "data_sensitivity": (
        "security controls and placement",
        "Classify the highest-sensitivity data used by the workload.",
    ),
    "sovereignty_requirement": (
        "jurisdiction and support model",
        "Confirm data, metadata, operator, and support-location constraints.",
    ),
    "cloud_preference": (
        "service availability and placement",
        "Confirm acceptable cloud providers or the need for cloud neutrality.",
    ),
    "on_premises_preference": (
        "private infrastructure scope",
        "Confirm whether on-premises placement is avoided, neutral, preferred, or required.",
    ),
    "hybrid_requirement": (
        "cross-environment boundaries",
        "Confirm whether components must span cloud and private environments.",
    ),
    "availability_target_pct": (
        "redundancy and operating cost",
        "Define the service availability target and excluded maintenance windows.",
    ),
    "recovery_objective_hours": (
        "recovery topology",
        "Confirm recovery time and recovery point objectives.",
    ),
    "existing_kubernetes": (
        "orchestration reuse",
        "Assess whether an existing Kubernetes platform is absent, pilot, or production-ready.",
    ),
    "existing_cloud": (
        "landing-zone integration",
        "Document existing cloud accounts, landing zones, contracts, and operational ownership.",
    ),
    "existing_data_platform": (
        "data integration and lineage",
        "Identify the system of record and available governed data interfaces.",
    ),
    "security_requirements": (
        "control design and approval",
        "List mandatory control frameworks, audit evidence, and security integrations.",
    ),
    "observability_maturity": (
        "telemetry integration and runbooks",
        "Assess current infrastructure, service, model, cost, and data-quality monitoring.",
    ),
    "team_operating_model": (
        "platform ownership",
        "Identify who builds, operates, supports, and governs the solution.",
    ),
    "budget_sensitivity": (
        "service tier and headroom",
        "Define budget constraints and the preferred cost-versus-risk tradeoff.",
    ),
    "timeline_weeks": (
        "phasing and procurement",
        "Confirm target dates, dependencies, procurement lead time, and approval gates.",
    ),
    "annual_growth_pct": (
        "capacity runway",
        "Estimate annual demand and data growth with an upside case.",
    ),
}


def _input_digest(requirements: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        requirements,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _display(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) or "not provided"
    if value in (None, ""):
        return "not provided"
    return str(value).replace("_", " ")


def _requirement_summary(rule: Rule, requirements: Mapping[str, Any]) -> str:
    return "; ".join(
        f"{field.replace('_', ' ')}: {_display(requirements.get(field))}"
        for field in rule.requirement_fields
    )


def _recommendation(rule: Rule, requirements: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "area": rule.layer,
        "layer": rule.layer,
        "rule_id": rule.rule_id,
        "priority": rule.priority,
        "customer_requirement": _requirement_summary(rule, requirements),
        "rule_triggered": f"{rule.rule_id}: {rule.condition.replace('_', ' ')}",
        "recommended_component_or_pattern": rule.component,
        "recommendation": rule.component,
        "reason": rule.reason,
        "alternative": rule.alternative,
        "risk": rule.risk,
        "required_validation": rule.required_validation,
    }


def _architecture(recommendations: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_layer = {item["layer"]: item for item in recommendations}
    return {
        layer: {
            "component_or_pattern": by_layer[layer]["recommendation"],
            "recommendation": by_layer[layer]["recommendation"],
            "rule_id": by_layer[layer]["rule_id"],
            "priority": by_layer[layer]["priority"],
        }
        for layer in ARCHITECTURE_LAYERS
    }


def _is_missing(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == ()


def _missing_evidence(requirements: Mapping[str, Any]) -> list[dict[str, str]]:
    evidence: list[dict[str, str]] = []
    for field in EVIDENCE_FIELDS:
        if field in requirements and not _is_missing(requirements[field]):
            continue
        impact, validation = EVIDENCE_GUIDANCE[field]
        evidence.append(
            {
                "field": field,
                "impact": impact,
                "required_validation": validation,
            }
        )
    return evidence


def _confidence(
    missing: list[dict[str, str]], conflicts: tuple[dict[str, Any], ...]
) -> dict[str, Any]:
    completeness = (len(EVIDENCE_FIELDS) - len(missing)) / len(EVIDENCE_FIELDS)
    conflict_penalty = min(len(conflicts) * 0.03, 0.15)
    score = round(max(0.2, min(0.98, 0.25 + (0.7 * completeness) - conflict_penalty)), 2)
    level = "high" if score >= 0.8 else "medium" if score >= 0.6 else "low"
    return {
        "level": level,
        "score": score,
        "evidence_complete": len(EVIDENCE_FIELDS) - len(missing),
        "evidence_total": len(EVIDENCE_FIELDS),
        "rationale": (
            f"{len(EVIDENCE_FIELDS) - len(missing)} of {len(EVIDENCE_FIELDS)} evidence "
            f"fields are present; {len(conflicts)} competing rule decisions were resolved."
        ),
    }


def _primary_risks(selected: tuple[Rule, ...]) -> list[dict[str, str]]:
    ordered = sorted(selected, key=lambda rule: (-rule.priority, rule.rule_id))
    risks: list[dict[str, str]] = []
    seen: set[str] = set()
    for rule in ordered:
        if rule.risk in seen:
            continue
        risks.append(
            {
                "layer": rule.layer,
                "rule_id": rule.rule_id,
                "risk": rule.risk,
                "mitigation": rule.required_validation,
            }
        )
        seen.add(rule.risk)
        if len(risks) == 6:
            break
    return risks


def _open_questions(
    missing: list[dict[str, str]], conflicts: tuple[dict[str, Any], ...], selected: tuple[Rule, ...]
) -> list[str]:
    questions = [item["required_validation"] for item in missing[:6]]
    for conflict in conflicts[:3]:
        questions.append(
            "Confirm whether "
            f"{conflict['selected_rule']} should supersede {conflict['superseded_rule']} "
            f"for {str(conflict['layer']).replace('_', ' ')}."
        )
    if not questions:
        questions = [rule.required_validation for rule in selected[:3]]
    return questions


def _platform_migration_considerations(
    requirements: Mapping[str, Any],
) -> list[dict[str, str]]:
    considerations: list[dict[str, str]] = []
    if requirements.get("existing_kubernetes") not in {None, "", "none"}:
        considerations.append(
            {
                "area": "orchestration",
                "consideration": "Assess and extend the existing Kubernetes platform in phases.",
                "validation": (
                    "Verify version, accelerator operators, tenancy, policy, and ownership."
                ),
            }
        )
    if requirements.get("existing_cloud") not in {None, "", "none"}:
        considerations.append(
            {
                "area": "cloud foundation",
                "consideration": "Integrate with existing landing zones and identity boundaries.",
                "validation": (
                    "Confirm accounts, quotas, connectivity, logging, and support ownership."
                ),
            }
        )
    if requirements.get("existing_data_platform") not in {None, "", "none"}:
        considerations.append(
            {
                "area": "data",
                "consideration": "Introduce versioned AI data products over the current platform.",
                "validation": (
                    "Test lineage, freshness, access filtering, and throughput before cutover."
                ),
            }
        )
    return considerations


def _migration_considerations(requirements: Mapping[str, Any]) -> list[dict[str, str]]:
    considerations = _platform_migration_considerations(requirements)
    if requirements.get("hybrid_requirement") is True:
        considerations.append(
            {
                "area": "hybrid boundary",
                "consideration": "Migrate one governed flow before expanding cross-domain traffic.",
                "validation": (
                    "Exercise identity, policy, latency, retry, and outage behavior end to end."
                ),
            }
        )
    annual_growth = float(requirements.get("annual_growth_pct") or 0)
    if annual_growth >= 25:
        considerations.append(
            {
                "area": "capacity runway",
                "consideration": (
                    "Phase capacity in measured increments with explicit growth headroom."
                ),
                "validation": (
                    f"Model the {annual_growth:g}% annual growth case by quarter and define "
                    "utilization triggers for the next capacity increment."
                ),
            }
        )
    if not considerations:
        considerations.append(
            {
                "area": "foundation",
                "consideration": (
                    "Establish a minimal governed landing zone before workload migration."
                ),
                "validation": (
                    "Approve ownership, network, identity, security, telemetry, and rollback."
                ),
            }
        )
    return considerations


def _assumptions(requirements: Mapping[str, Any]) -> list[str]:
    assumptions = [
        (
            "Latency and throughput targets are planning objectives until measured at an agreed "
            "percentile, concurrency, and service boundary."
        ),
        (
            "Existing platform and operating-maturity inputs are assumed accurate enough for "
            "discovery and require validation by their owners."
        ),
        (
            f"Annual growth of {_display(requirements.get('annual_growth_pct'))}% is treated as a "
            "compound planning signal, not reserved capacity."
        ),
        (
            f"The {_display(requirements.get('availability_target_pct'))}% availability target "
            f"and {_display(requirements.get('recovery_objective_hours'))}-hour recovery objective "
            "are assumed to share one service boundary."
        ),
    ]
    if requirements.get("hybrid_requirement") is True:
        assumptions.append(
            "Required cross-environment identity, network, and policy controls can be approved."
        )
    return assumptions


def _poc(requirements: Mapping[str, Any]) -> dict[str, Any]:
    workload = _display(requirements.get("workload_type"))
    objective = "Validate the end-to-end solution hypothesis with one fictional workload slice."
    criteria = [
        "Demonstrate repeatable deployment and rollback from version-controlled configuration.",
        "Meet agreed performance targets under representative average and peak load.",
        "Produce auditable security, identity, data-lineage, and observability evidence.",
    ]
    if "rag" in workload:
        objective = "Validate governed retrieval quality and model-serving performance end to end."
        criteria.append(
            "Meet agreed retrieval relevance, citation, freshness, and access-filter tests."
        )
    elif "real time" in workload:
        objective = "Validate tail latency, throughput, and recovery for real-time inference."
        criteria.append(
            "Meet p95 and p99 latency objectives at peak concurrency with failure injection."
        )
    elif "training" in workload:
        objective = "Validate distributed training efficiency, checkpoint recovery, and operations."
        criteria.append(
            "Measure scaling efficiency and successful recovery from a worker interruption."
        )
    elif "hybrid" in workload:
        objective = "Validate one governed hybrid data and inference path across trust boundaries."
        criteria.append(
            "Prove identity, policy, latency, and outage behavior across both environments."
        )
    return {
        "objective": objective,
        "scope": (
            "One model, one governed dataset, one environment path, and one operating runbook."
        ),
        "duration_weeks": min(max(int(requirements.get("timeline_weeks") or 8) // 3, 3), 6),
        "success_criteria": criteria,
        "exit_decision": "Proceed, revise the hypothesis, or stop based on measured evidence.",
    }


def _next_workshop(requirements: Mapping[str, Any], missing_count: int) -> dict[str, Any]:
    deployment = (
        "hybrid boundary and operating model"
        if requirements.get("hybrid_requirement") is True
        else "solution validation and delivery sequencing"
    )
    return {
        "title": f"Architecture workshop: {deployment}",
        "duration_minutes": 120,
        "participants": [
            "application owner",
            "platform engineering",
            "data owner",
            "security and identity",
            "operations and finance",
        ],
        "agenda": [
            f"Close the highest-impact evidence gaps ({missing_count} currently open).",
            "Review rule decisions, alternatives, risks, and required validation.",
            "Agree PoC scope, success criteria, owners, dates, and exit decision.",
            "Confirm migration phases, dependencies, and formal review gates.",
        ],
    }


def evaluate_configuration(inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate validated inputs without mutation, I/O, randomness, or external calls."""

    requirements = normalize_requirements(inputs)
    resolution = resolve_rule_conflicts(matching_rules(requirements))
    recommendations = [_recommendation(rule, requirements) for rule in resolution.selected]
    architecture = _architecture(recommendations)
    missing = _missing_evidence(requirements)
    placement = architecture["deployment_pattern"]["component_or_pattern"]
    return {
        "recommendations": recommendations,
        "architecture": architecture,
        "placement": placement,
        "deployment_pattern": placement,
        "migration_considerations": _migration_considerations(requirements),
        "assumptions": _assumptions(requirements),
        "primary_risks": _primary_risks(resolution.selected),
        "open_questions": _open_questions(missing, resolution.conflicts, resolution.selected),
        "recommended_poc": _poc(requirements),
        "recommended_next_workshop": _next_workshop(requirements, len(missing)),
        "solution_confidence": _confidence(missing, resolution.conflicts),
        "missing_evidence": missing,
        "conflicts": list(resolution.conflicts),
        "ruleset_version": RULESET_VERSION,
        "ruleset_digest": ruleset_digest(),
        "input_digest": _input_digest(requirements),
    }
