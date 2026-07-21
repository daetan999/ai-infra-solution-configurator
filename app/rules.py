"""Deterministic rule catalog, matching, and conflict resolution."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from app.domain import ARCHITECTURE_LAYERS, ConflictRecord, Rule, RuleResolution

RULESET_VERSION = "2026.07.1"


def _rule(
    rule_id: str,
    layer: str,
    priority: int,
    condition: str,
    fields: tuple[str, ...],
    component: str,
    reason: str,
    alternative: str,
    risk: str,
    validation: str,
    *,
    fallback: bool = False,
) -> Rule:
    return Rule(
        rule_id=rule_id,
        layer=layer,
        priority=priority,
        condition=condition,
        requirement_fields=fields,
        component=component,
        reason=reason,
        alternative=alternative,
        risk=risk,
        required_validation=validation,
        is_fallback=fallback,
    )


RULES = (
    _rule(
        "COMPUTE-BASE",
        "compute_layer",
        10,
        "always",
        ("workload_type",),
        "CPU control nodes with benchmark-sized accelerator worker pools",
        "Separating control and accelerated workloads preserves operational flexibility.",
        "A fully managed compute service can reduce platform ownership.",
        "Generic sizing may miss workload-specific memory or throughput constraints.",
        "Benchmark the representative model and concurrency profile.",
        fallback=True,
    ),
    _rule(
        "COMPUTE-TRAINING",
        "compute_layer",
        70,
        "training",
        ("lifecycle_mode",),
        "Scale-out training cluster with isolated control and accelerator node pools",
        "Distributed training needs schedulable accelerator capacity and failure isolation.",
        "Burst training jobs into managed cloud accelerator capacity.",
        "Collective communication or checkpoint I/O can limit scaling efficiency.",
        "Run a multi-node scaling and checkpoint recovery benchmark.",
    ),
    _rule(
        "COMPUTE-LARGE-MODEL",
        "compute_layer",
        80,
        "large_model",
        ("model_size_billion",),
        "High-memory accelerator nodes sized for model and runtime memory headroom",
        "Large models require explicit memory placement before throughput optimization.",
        "Use model compression or a smaller task-specialized model.",
        "Memory estimates can change materially with precision, cache, and parallelism.",
        "Measure loaded-model, KV-cache, and framework overhead on candidate hardware.",
    ),
    _rule(
        "ACCELERATOR-BASE",
        "accelerator_approach",
        10,
        "always",
        ("model_size_billion", "throughput_target_rps"),
        "Benchmark-selected accelerator pool with explicit utilization targets",
        "Accelerator choice should follow measured workload fit rather than brand assumptions.",
        "CPU or inference-optimized silicon may be viable for smaller models.",
        "Illustrative profiles are not capacity commitments or vendor quotes.",
        "Compare latency, throughput, memory headroom, availability, and cost in a PoC.",
        fallback=True,
    ),
    _rule(
        "ACCELERATOR-TRAINING",
        "accelerator_approach",
        75,
        "training",
        ("lifecycle_mode", "model_size_billion"),
        "High-memory accelerators with high-bandwidth peer interconnect",
        "Training performance depends on memory capacity and collective efficiency.",
        "A managed training service can supply elastic accelerator clusters.",
        "Low utilization can make dedicated high-end accelerators uneconomic.",
        "Validate achieved scaling efficiency and productive accelerator hours.",
    ),
    _rule(
        "ACCELERATOR-LOW-LATENCY",
        "accelerator_approach",
        85,
        "low_latency",
        ("latency_target_ms", "throughput_target_rps"),
        "Latency-optimized inference accelerators with reserved serving headroom",
        "A tight latency objective requires predictable queueing and model execution.",
        "Use a smaller or quantized model on lower-cost accelerators.",
        "Reserved headroom can reduce average utilization and increase unit cost.",
        "Load test p50, p95, and p99 latency at the expected peak concurrency.",
    ),
    _rule(
        "ACCELERATOR-BUDGET",
        "accelerator_approach",
        65,
        "budget_sensitive",
        ("budget_sensitivity",),
        "Mixed accelerator pool with autoscaling and quantization evaluation",
        "High budget sensitivity favors measured right-sizing and workload tiering.",
        "Reserve a uniform premium accelerator fleet for operational simplicity.",
        "A heterogeneous fleet adds scheduling and image-compatibility complexity.",
        "Benchmark candidate precisions and validate scheduler placement behavior.",
    ),
    _rule(
        "ORCHESTRATION-BASE",
        "orchestration",
        10,
        "always",
        ("team_operating_model",),
        "Managed container runtime with declarative deployment and policy controls",
        "A managed runtime provides repeatable operations with lower control-plane burden.",
        "Operate a dedicated Kubernetes platform for maximum control.",
        "Managed services can constrain portability or specialized scheduling.",
        "Validate supported accelerators, networking, policy, and upgrade paths.",
        fallback=True,
    ),
    _rule(
        "ORCHESTRATION-K8S",
        "orchestration",
        80,
        "existing_kubernetes",
        ("existing_kubernetes", "team_operating_model"),
        "Existing Kubernetes platform extended with accelerator operators and policy",
        "Reusing a capable platform reduces migration while preserving operating practices.",
        "Create a separate managed AI runtime to isolate platform risk.",
        "The current cluster may lack GPU scheduling, isolation, or upgrade readiness.",
        "Assess cluster version, operators, quotas, tenancy, and support ownership.",
    ),
    _rule(
        "MODEL-SERVING-BASE",
        "model_serving",
        10,
        "always",
        ("lifecycle_mode", "model_size_billion"),
        "Versioned model-serving runtime with health checks and controlled rollout",
        "A standardized serving boundary supports repeatability and rollback.",
        "Use a managed model endpoint for reduced platform operations.",
        "Runtime defaults may not meet workload latency or memory needs.",
        "Benchmark the selected runtime with representative payloads and model versions.",
        fallback=True,
    ),
    _rule(
        "MODEL-SERVING-LOW-LATENCY",
        "model_serving",
        85,
        "low_latency",
        ("latency_target_ms", "throughput_target_rps"),
        "Optimized serving runtime with continuous batching, warm replicas, and autoscaling",
        "Queue control and warm capacity are required to protect tail latency.",
        "Deploy fixed replicas without batching for simpler request isolation.",
        "Batching and autoscaling thresholds can increase tail latency during bursts.",
        "Replay peak traffic and validate p95/p99 latency plus scale-out time.",
    ),
    _rule(
        "MODEL-SERVING-RAG",
        "model_serving",
        75,
        "rag",
        ("workload_type",),
        "Model gateway with retrieval-aware request orchestration and versioned prompts",
        "RAG serving must coordinate retrieval context, model calls, and policy consistently.",
        "Embed retrieval logic inside each application service.",
        "Coupled retrieval and serving changes can complicate rollback.",
        "Test context construction, prompt versioning, fallback, and citation behavior.",
    ),
    _rule(
        "NETWORK-BASE",
        "networking",
        10,
        "always",
        ("throughput_target_rps",),
        "Segmented application, data, management, and accelerator network paths",
        "Segmentation provides a governable baseline for performance and security.",
        "Use a simplified shared network for a constrained pilot.",
        "Shared paths can create contention and broaden the blast radius.",
        "Validate bandwidth, latency, firewall paths, DNS, and egress controls.",
        fallback=True,
    ),
    _rule(
        "NETWORK-HIGH-THROUGHPUT",
        "networking",
        75,
        "high_throughput",
        ("throughput_target_rps", "data_volume_tb"),
        "High-bandwidth data paths with explicit ingress, east-west, and egress budgets",
        "Sustained request and data movement require capacity beyond interface line rates.",
        "Use workload sharding across independent network domains.",
        "Oversubscription or shared services can become the system bottleneck.",
        "Measure end-to-end throughput under concurrent model and data traffic.",
    ),
    _rule(
        "NETWORK-SOVEREIGN",
        "networking",
        90,
        "sovereignty",
        ("sovereignty_requirement", "data_sensitivity"),
        "Private connectivity with controlled egress and jurisdiction-aware routing",
        "Sovereignty constraints require enforceable data and administration boundaries.",
        "Use public endpoints protected by identity-aware access controls.",
        "Misconfigured routes or support access can violate location constraints.",
        "Review traffic flows, administrative access, DNS, egress, and audit evidence.",
    ),
    _rule(
        "STORAGE-BASE",
        "storage",
        10,
        "always",
        ("data_volume_tb",),
        "Durable object storage with lifecycle policy and a workload-local cache",
        "Object durability plus local caching balances governance and runtime performance.",
        "Use a shared parallel file system for all workload data.",
        "Cache behavior and small-file patterns may create unpredictable performance.",
        "Profile object size, read/write mix, retention, and required throughput.",
        fallback=True,
    ),
    _rule(
        "STORAGE-LARGE-DATA",
        "storage",
        75,
        "large_data",
        ("data_volume_tb", "lifecycle_mode"),
        "Tiered object storage with high-throughput staging and checkpoint tiers",
        "Large datasets need separate durability, active-data, and checkpoint paths.",
        "Use a single high-performance storage tier for operational simplicity.",
        "Data staging or checkpoint contention can idle expensive compute.",
        "Benchmark sustained read/write throughput and recovery from checkpoints.",
    ),
    _rule(
        "DATA-BASE",
        "data_layer",
        10,
        "always",
        ("existing_data_platform", "data_volume_tb"),
        "Governed data platform interface with lineage, quality, and access controls",
        "Explicit governance keeps model inputs reproducible and reviewable.",
        "Use a pilot-only curated dataset with manual approvals.",
        "Weak lineage can undermine evaluation, audit, and incident response.",
        "Validate ownership, quality gates, lineage, retention, and access workflows.",
        fallback=True,
    ),
    _rule(
        "DATA-EXISTING",
        "data_layer",
        75,
        "existing_data_platform",
        ("existing_data_platform",),
        "Existing data platform exposed through governed, versioned AI data products",
        "Integration preserves established ownership while creating stable AI contracts.",
        "Replicate approved data into a separate AI-focused platform.",
        "Existing data interfaces may not support model-scale throughput or freshness.",
        "Test access latency, change capture, lineage, and dataset versioning.",
    ),
    _rule(
        "RETRIEVAL-BASE",
        "feature_or_retrieval_layer",
        10,
        "always",
        ("workload_type",),
        "Optional feature and retrieval services behind versioned interfaces",
        "A replaceable interface avoids coupling applications to one retrieval technology.",
        "Keep task-specific features inside the application for a narrow pilot.",
        "Premature shared services can add complexity without measurable value.",
        "Confirm reuse needs, freshness targets, and retrieval evaluation metrics.",
        fallback=True,
    ),
    _rule(
        "RETRIEVAL-RAG",
        "feature_or_retrieval_layer",
        90,
        "rag",
        ("workload_type", "data_volume_tb", "data_sensitivity"),
        "Hybrid retrieval service with metadata filters, reranking, and citation lineage",
        "Enterprise RAG needs relevance controls plus traceable source authorization.",
        "Use keyword retrieval only where corpus size and terminology are stable.",
        "Stale indexes or authorization drift can return incomplete or unsafe context.",
        "Evaluate retrieval quality, freshness, access filtering, and citation accuracy.",
    ),
    _rule(
        "SECURITY-BASE",
        "security",
        10,
        "always",
        ("security_requirements", "data_sensitivity"),
        "Zero-trust service boundaries with encryption, policy, secrets, and audit controls",
        "A defense-in-depth baseline is required for production AI workloads.",
        "Use an isolated pilot environment with tightly limited data and users.",
        "Unmapped controls can delay approval or leave material gaps.",
        "Complete threat modeling and map controls to required evidence.",
        fallback=True,
    ),
    _rule(
        "SECURITY-RESTRICTED",
        "security",
        95,
        "restricted_data",
        ("data_sensitivity", "sovereignty_requirement", "security_requirements"),
        "Private endpoints, customer-controlled encryption, policy enforcement, and audit trail",
        "Restricted data requires verifiable isolation and accountable access paths.",
        "Use de-identified data in a managed environment for the initial PoC.",
        "Model, prompt, log, or vector stores can create unreviewed sensitive-data copies.",
        "Perform data-flow review, threat modeling, key-control review, and access tests.",
    ),
    _rule(
        "IDENTITY-BASE",
        "identity",
        10,
        "always",
        ("security_requirements",),
        "Enterprise identity federation with workload identity and least-privilege roles",
        "Human and service identities need distinct, auditable authorization boundaries.",
        "Use environment-local identities for an isolated short-lived pilot.",
        "Role sprawl or long-lived credentials can create hidden privilege paths.",
        "Validate role design, token lifetime, break-glass access, and access reviews.",
        fallback=True,
    ),
    _rule(
        "IDENTITY-CLOUD",
        "identity",
        70,
        "existing_cloud",
        ("existing_cloud", "security_requirements"),
        "Federated enterprise identity mapped to cloud and workload-native identities",
        "Existing cloud identity controls can anchor consistent human and service access.",
        "Operate a dedicated identity boundary for the AI platform.",
        "Cross-account and workload mappings may create privilege escalation paths.",
        "Review trust policies, workload federation, role boundaries, and audit events.",
    ),
    _rule(
        "OBSERVABILITY-BASE",
        "observability",
        10,
        "always",
        ("observability_maturity",),
        "Unified infrastructure, model, retrieval, cost, and service telemetry",
        "AI operations need correlated service health and model-quality signals.",
        "Start with managed infrastructure monitoring for a constrained pilot.",
        "Unbounded high-cardinality telemetry can increase cost and obscure signals.",
        "Define service levels, model metrics, retention, ownership, and alert actions.",
        fallback=True,
    ),
    _rule(
        "OBSERVABILITY-DEVELOPING",
        "observability",
        70,
        "low_observability",
        ("observability_maturity", "team_operating_model"),
        "Managed telemetry baseline with curated dashboards, alerts, and runbooks",
        "A developing practice benefits from opinionated signals and operating procedures.",
        "Extend an existing enterprise observability platform with AI-specific telemetry.",
        "Managed defaults can leave model quality or retrieval health unobserved.",
        "Exercise alert routing, incident runbooks, quality drift, and cost thresholds.",
    ),
    _rule(
        "RESILIENCE-BASE",
        "resilience",
        10,
        "always",
        ("availability_target_pct", "recovery_objective_hours"),
        "Health-checked services with backups, controlled rollback, and tested recovery",
        "A recoverable baseline protects the solution from routine component failure.",
        "Use a single-zone pilot with documented rebuild procedures.",
        "Untested recovery assumptions can materially overstate availability.",
        "Run restore, rollback, node-loss, and dependency-failure exercises.",
        fallback=True,
    ),
    _rule(
        "RESILIENCE-HA",
        "resilience",
        80,
        "high_availability",
        ("availability_target_pct",),
        "Multi-zone serving with redundant ingress and disruption-controlled replicas",
        "A high availability target requires removal of single-zone service dependencies.",
        "Use active-passive recovery when service demand permits longer failover.",
        "Dependent data and identity services may still be single points of failure.",
        "Test zone failure, capacity during failover, and dependency service levels.",
    ),
    _rule(
        "RESILIENCE-TIGHT-RTO",
        "resilience",
        85,
        "tight_recovery",
        ("recovery_objective_hours", "availability_target_pct"),
        "Warm recovery capacity with automated state restoration and failover runbooks",
        "A short recovery objective requires pre-provisioned capacity and rehearsed automation.",
        "Use backup-and-rebuild recovery for lower cost and a longer objective.",
        "Replication lag or configuration drift can prevent recovery within target.",
        "Measure recovery time and recovery point during a representative failover drill.",
    ),
    _rule(
        "DEPLOY-BASE",
        "deployment_pattern",
        10,
        "always",
        ("cloud_preference", "on_premises_preference", "hybrid_requirement"),
        "Portable single-environment deployment with documented placement assumptions",
        "A neutral baseline keeps placement open until constraints are validated.",
        "Select a managed cloud or private platform immediately.",
        "Delayed placement decisions can block network and security design.",
        "Confirm data location, service availability, ownership, timeline, and economics.",
        fallback=True,
    ),
    _rule(
        "DEPLOY-CLOUD",
        "deployment_pattern",
        70,
        "cloud_preferred",
        ("cloud_preference", "existing_cloud"),
        "Cloud deployment using managed control-plane services and isolated data paths",
        "Cloud preference supports faster access to elastic capacity and managed services.",
        "Use a portable private-cloud deployment for greater placement control.",
        "Service availability, quotas, egress, or lock-in may constrain the design.",
        "Validate regional services, quotas, pricing, egress, support, and portability.",
    ),
    _rule(
        "DEPLOY-ONPREM",
        "deployment_pattern",
        85,
        "on_premises_preferred",
        ("on_premises_preference", "data_sensitivity"),
        "Private on-premises AI platform with locally governed data and operations",
        "An on-premises preference prioritizes placement and operational control.",
        "Use dedicated private-cloud capacity with controlled connectivity.",
        "Procurement lead time and fixed capacity can limit delivery or elasticity.",
        "Validate facility capacity, supply lead time, skills, support, and lifecycle ownership.",
    ),
    _rule(
        "DEPLOY-SOVEREIGN",
        "deployment_pattern",
        92,
        "sovereignty",
        ("sovereignty_requirement", "data_sensitivity"),
        "Sovereignty-aligned private placement with jurisdiction-controlled operations",
        "Location and administration constraints take precedence over general cloud preference.",
        "Use an approved sovereign cloud region if controls and services are sufficient.",
        "Operational support or replicated metadata may cross the intended boundary.",
        "Confirm legal interpretation, operator location, support access, and data flows.",
    ),
    _rule(
        "DEPLOY-HYBRID",
        "deployment_pattern",
        100,
        "hybrid_required",
        ("hybrid_requirement", "cloud_preference", "on_premises_preference"),
        "Hybrid private-data plane with policy-controlled cloud or shared AI services",
        "An explicit hybrid requirement needs controlled boundaries across placement domains.",
        "Consolidate into one private environment to reduce cross-domain operations.",
        "Latency, identity, policy, and failure handling become cross-environment concerns.",
        "Validate end-to-end data flows, identity, latency, outage modes, and ownership.",
    ),
)


def _canonicalize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _canonicalize(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_canonicalize(item) for item in value]
    return value


def normalize_requirements(requirements: Mapping[str, Any]) -> dict[str, Any]:
    """Return a canonical copy without changing the validated input mapping."""

    if not isinstance(requirements, Mapping):
        raise TypeError("configuration inputs must be a mapping")
    normalized = {str(key): _canonicalize(value) for key, value in requirements.items()}
    security = normalized.get("security_requirements")
    if isinstance(security, list):
        normalized["security_requirements"] = sorted({str(item) for item in security})
    return dict(sorted(normalized.items()))


def _number(requirements: Mapping[str, Any], field: str) -> float | None:
    value = requirements.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _truthy(requirements: Mapping[str, Any], field: str) -> bool:
    value = requirements.get(field)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value not in {"", "false", "no", "none", "not_required", "no_preference"}
    return bool(value)


def _text(requirements: Mapping[str, Any], field: str) -> str:
    value = requirements.get(field, "")
    return value if isinstance(value, str) else ""


def _always(_: Mapping[str, Any]) -> bool:
    return True


def _training(requirements: Mapping[str, Any]) -> bool:
    return _text(requirements, "lifecycle_mode") in {"both", "training"}


def _rag(requirements: Mapping[str, Any]) -> bool:
    workload = _text(requirements, "workload_type")
    return "rag" in workload or "retrieval" in workload


def _large_model(requirements: Mapping[str, Any]) -> bool:
    value = _number(requirements, "model_size_billion")
    return value is not None and value >= 30


def _low_latency(requirements: Mapping[str, Any]) -> bool:
    value = _number(requirements, "latency_target_ms")
    return value is not None and value <= 250


def _high_throughput(requirements: Mapping[str, Any]) -> bool:
    value = _number(requirements, "throughput_target_rps")
    return value is not None and value >= 200


def _large_data(requirements: Mapping[str, Any]) -> bool:
    value = _number(requirements, "data_volume_tb")
    return value is not None and value >= 10


def _restricted_data(requirements: Mapping[str, Any]) -> bool:
    return _text(requirements, "data_sensitivity") in {
        "confidential",
        "high",
        "regulated",
        "restricted",
        "sensitive",
    }


def _sovereignty(requirements: Mapping[str, Any]) -> bool:
    return _text(requirements, "sovereignty_requirement") not in {"", "none"}


def _cloud_preferred(requirements: Mapping[str, Any]) -> bool:
    return _text(requirements, "cloud_preference") in {
        "aws",
        "azure",
        "gcp",
        "private_cloud",
    }


def _on_premises_preferred(requirements: Mapping[str, Any]) -> bool:
    return _text(requirements, "on_premises_preference") in {"prefer", "required"}


def _high_availability(requirements: Mapping[str, Any]) -> bool:
    value = _number(requirements, "availability_target_pct")
    return value is not None and value >= 99.9


def _tight_recovery(requirements: Mapping[str, Any]) -> bool:
    value = _number(requirements, "recovery_objective_hours")
    return value is not None and value <= 1


def _low_observability(requirements: Mapping[str, Any]) -> bool:
    return _text(requirements, "observability_maturity") in {
        "ad_hoc",
        "basic",
        "developing",
        "emerging",
        "low",
        "none",
    }


def _budget_sensitive(requirements: Mapping[str, Any]) -> bool:
    return _text(requirements, "budget_sensitivity") in {"high", "very_high", "strict"}


def _configured_enum(requirements: Mapping[str, Any], field: str) -> bool:
    return _text(requirements, field) not in {"", "none"}


CONDITION_MATCHERS: dict[str, Callable[[Mapping[str, Any]], bool]] = {
    "always": _always,
    "budget_sensitive": _budget_sensitive,
    "cloud_preferred": _cloud_preferred,
    "existing_cloud": lambda values: _configured_enum(values, "existing_cloud"),
    "existing_data_platform": lambda values: _configured_enum(values, "existing_data_platform"),
    "existing_kubernetes": lambda values: _configured_enum(values, "existing_kubernetes"),
    "high_availability": _high_availability,
    "high_throughput": _high_throughput,
    "hybrid_required": lambda values: _truthy(values, "hybrid_requirement"),
    "large_data": _large_data,
    "large_model": _large_model,
    "low_latency": _low_latency,
    "low_observability": _low_observability,
    "on_premises_preferred": _on_premises_preferred,
    "rag": _rag,
    "restricted_data": _restricted_data,
    "sovereignty": _sovereignty,
    "tight_recovery": _tight_recovery,
    "training": _training,
}


def matching_rules(requirements: Mapping[str, Any]) -> tuple[Rule, ...]:
    """Return all triggered rules in stable catalog order."""

    normalized = normalize_requirements(requirements)
    return tuple(rule for rule in RULES if CONDITION_MATCHERS[rule.condition](normalized))


def resolve_rule_conflicts(rules: Iterable[Rule]) -> RuleResolution:
    """Select one rule per layer using descending priority and lexical rule ID."""

    grouped: dict[str, list[Rule]] = {}
    for rule in rules:
        grouped.setdefault(rule.layer, []).append(rule)

    layer_order = {layer: position for position, layer in enumerate(ARCHITECTURE_LAYERS)}
    selected: list[Rule] = []
    conflicts: list[ConflictRecord] = []
    for layer in sorted(grouped, key=lambda item: (layer_order.get(item, 999), item)):
        candidates = sorted(grouped[layer], key=lambda rule: (-rule.priority, rule.rule_id))
        winner = candidates[0]
        selected.append(winner)
        for candidate in candidates[1:]:
            if candidate.is_fallback:
                continue
            conflicts.append(
                {
                    "layer": layer,
                    "selected_rule": winner.rule_id,
                    "selected_priority": winner.priority,
                    "superseded_rule": candidate.rule_id,
                    "superseded_priority": candidate.priority,
                    "reason": (
                        "Higher priority rule selected."
                        if winner.priority != candidate.priority
                        else "Equal priority resolved by lexical rule ID."
                    ),
                }
            )
    return RuleResolution(selected=tuple(selected), conflicts=tuple(conflicts))


def ruleset_digest(rules: Iterable[Rule] = RULES) -> str:
    """Hash the semantic ruleset independently of declaration order."""

    payload = [
        {
            "rule_id": rule.rule_id,
            "layer": rule.layer,
            "priority": rule.priority,
            "condition": rule.condition,
            "requirement_fields": list(rule.requirement_fields),
            "component": rule.component,
            "reason": rule.reason,
            "alternative": rule.alternative,
            "risk": rule.risk,
            "required_validation": rule.required_validation,
            "is_fallback": rule.is_fallback,
        }
        for rule in sorted(rules, key=lambda item: item.rule_id)
    ]
    encoded = json.dumps(
        {"version": RULESET_VERSION, "rules": payload},
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()
