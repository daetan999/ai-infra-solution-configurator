# Rules and guardrails

## Recommendation contract

Every selected recommendation retains:

- the customer requirement considered;
- the stable rule identifier and triggered condition;
- the recommended component or pattern;
- the reason for the recommendation;
- a viable alternative;
- the principal risk; and
- required technical validation.

Exclusive candidates are resolved by declared priority and stable rule ID. The engine does not use
file order, random selection, external inference, or a hidden architecture prompt.

## Evidence and confidence

Confidence is a completeness signal. Missing governance, recovery, operational, or workload evidence
creates an explicit deduction and an open question. A high score does not certify the architecture,
hardware performance, security posture, or commercial fit.

## Diagram controls

The architecture diagram is rendered from typed nodes and edges drawn from an allowlist. The SVG uses
a fixed view box, local shapes, system fonts, escaped bounded text, and accessibility metadata. Scripts,
external images, remote fonts, `foreignObject`, event handlers, and arbitrary user markup are excluded.

## Public-data boundary

Bundled scenarios are fictional. Do not enter customer names, confidential requirements, proprietary
configurations, production telemetry, credentials, internal project identifiers, contract prices, or
supplier quotes into a public demonstration.

## Decision boundary

Recommendations are initial solution hypotheses for discovery and workshops. They require workload
benchmarks, security and identity review, recovery testing, network and storage validation, operational
readiness review, and formal architecture approval before any commitment.

