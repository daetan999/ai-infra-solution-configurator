# Configurator diagram TDD evidence

## Source and journeys

The journeys were derived from the portfolio build specification and the configurator engine
boundary agreed during implementation.

- As a solution workshop facilitator, I can turn an engine assessment into a stable architecture
  blueprint without a model inventing components.
- As a reviewer, I can trace every diagram node to a controlled component type and safely inspect
  user-controlled labels.
- As a document consumer, I receive an accessible, presentation-ready SVG that is inert and
  reproducible.

## Task report

- **RED:** `python3 -m pytest -o addopts='' tests/test_diagram.py -q` failed during
  collection with `ModuleNotFoundError: No module named 'app.architecture'`. This was the intended
  missing-implementation failure. The contract is preserved in commits `3361b79` and `eb6aae3`.
- **GREEN:** `/tmp/configurator-diagram-venv/bin/python -m pytest -o addopts=''
  tests/test_diagram.py -q` completed with `13 passed`. The first GREEN implementation is preserved
  in commit `df743a2`.
- **Quality:** `/tmp/configurator-diagram-venv/bin/ruff check app/architecture.py app/diagram.py
  tests/test_diagram.py` completed with `All checks passed!`.
- **Visual:** both checked-in SVG examples parsed as XML, were rendered in Chrome at 1440×900, and
  were visually inspected for hierarchy, clipping, connector routing, and text legibility.

## Test specification

| # | What is guaranteed | Test file or command | Test type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Trace and architecture assessments map only to controlled nodes | `tests/test_diagram.py` | Unit | PASS | 13-test GREEN gate |
| 2 | Unsafe IDs, duplicate nodes, and dangling edges are rejected | `tests/test_diagram.py` | Unit | PASS | 13-test GREEN gate |
| 3 | Unknown trace layers cannot invent diagram components | `tests/test_diagram.py` | Security/unit | PASS | 13-test GREEN gate |
| 4 | SVG output is deterministic, accessible, escaped, inert, and valid XML | `tests/test_diagram.py` | Security/unit | PASS | 13-test GREEN gate |
| 5 | The adapter renders a live `evaluate_configuration` engine result | `tests/test_diagram.py` | Integration | PASS | 13-test GREEN gate |

## Coverage and known gaps

`/tmp/configurator-diagram-venv/bin/python -m pytest -o addopts='' --cov=app.architecture
--cov=app.diagram --cov-report=term-missing tests/test_diagram.py -q` reported **88% branch-aware
coverage** across the two owned modules (85% architecture, 95% diagram). Browser-level download
behavior belongs to the interface integration suite; this module verifies the generated SVG payload
itself.

## Merge evidence

RED contract: `3361b79`, `eb6aae3`. First GREEN implementation: `df743a2`. This report preserves
the evidence if the checkpoint commits are later squash-merged.
