# Configurator integration TDD evidence

## Source and journey

The integration journey was derived from the portfolio brief: a validated requirement set must
flow through deterministic rules, a controlled architecture blueprint, a presentation-ready
diagram, immutable persistence, and a downloadable solution brief without external credentials.

## Execution report

| Stage | Command and evidence | Result |
|---|---|---|
| Initial RED | `python3 -m pytest -q -o addopts='' tests/test_integration_workflow.py` before implementation | Intended `ModuleNotFoundError` for the absent workflow modules |
| Structured-export RED | The real engine workflow test required risk/mitigation, PoC, and workshop sections | Failed because nested dictionaries were rendered as Python dictionary text |
| SVG-contract RED | `/tmp/configurator-venv/bin/python -m pytest -q -o addopts='' tests/test_integration_workflow.py` | Real generated SVG failed because a blanket URL check rejected the required W3C namespace |
| GREEN | `/tmp/configurator-venv/bin/python -m pytest -q -o addopts='' tests/test_integration_workflow.py` | `9 passed` after structural Markdown rendering and XML-aware SVG validation |
| SVG hardening RED | `bb9ac76 test: harden normalized inputs and SVG exports` | Reproduced CSS import, external paint URL, and declarative-animation vectors |
| SVG hardening GREEN | `bad56fe fix: enforce normalized bounds and inert SVG exports` | Allowed only inert elements, fragment-local URL references, and passive attributes |
| Integrated GREEN | `PYTHONWARNINGS=default /tmp/configurator-venv/bin/python -m pytest -q --disable-warnings` | `73 passed`, 90.34% branch-aware coverage, no SQLite resource warnings |

## Test specification

| # | Guarantee | Test | Type | Result |
|---|---|---|---|---|
| 1 | Validated inputs reach the real deterministic rules engine | `test_real_rules_to_blueprint_to_export_workflow` | Workflow | PASS |
| 2 | Assessment outputs contain recommendation traces, architecture layers, and confidence | `test_real_rules_to_blueprint_to_export_workflow` | Workflow | PASS |
| 3 | The controlled blueprint contains connected nodes and edges | `test_real_rules_to_blueprint_to_export_workflow` | Integration | PASS |
| 4 | The exact assessment, blueprint, and SVG are persisted and read back, not recalculated | `test_real_rules_to_blueprint_to_export_workflow` | Persistence | PASS |
| 5 | Markdown renders risk/mitigation and PoC/workshop objects as executive-readable sections | `test_real_rules_to_blueprint_to_export_workflow` | Export | PASS |
| 6 | A generated SVG with the standard W3C namespace is downloadable | `test_real_rules_to_blueprint_to_export_workflow` | Export/security | PASS |
| 7 | Script, foreign-object, remote-link, event-handler, and CSS URL payloads are rejected | `test_svg_export_blocks_active_or_external_content` | Security | PASS |

## Safety boundary

SVG validation parses XML and rejects active or externally addressable content while preserving
the renderer's required `http://www.w3.org/2000/svg` namespace. Downloads also set `nosniff` and
a sandboxed content-security policy. The diagram is generated from the stored deterministic
assessment and contains no model-generated markup.
