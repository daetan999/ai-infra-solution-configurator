# Configurator API TDD evidence

## Source and journeys

The journeys were derived from the Enterprise AI Solution Configurator portfolio brief.

- As a discovery lead, I can save a complete fictional customer scenario and receive an
  explainable solution hypothesis.
- As a solution architect, I can revise requirements without losing the prior assessment.
- As a reviewer, I can retrieve a historical assessment and deterministic solution exports.
- As a workshop facilitator, I can start from three clearly fictional, repeatable scenarios.
- As an operator, I receive bounded validation errors and redacted server failures.

## RED and GREEN checkpoints

| Stage | Evidence | Result |
|---|---|---|
| RED | `python3 -m pytest -q -o addopts='' tests/test_schemas.py tests/test_repository.py tests/test_api.py tests/test_demo_data.py tests/test_integration_workflow.py` | Five intended collection failures because the contracted modules did not exist |
| RED commit | `d2d8986 test: define configurator API workflow contracts` | Failing schema, repository, API, demo, and integrated-workflow contracts preserved before implementation |
| GREEN | `/tmp/configurator-venv/bin/python -m pytest -q -o addopts='' tests/test_schemas.py tests/test_repository.py tests/test_api.py tests/test_demo_data.py tests/test_integration_workflow.py` | `37 passed` |
| GREEN commit | `8cb3ba5 feat: deliver validated configurator workflow API` | Validated workflow, immutable snapshots, exports, aliases, and safety controls implemented |
| Hardening RED | `bb9ac76 test: harden normalized inputs and SVG exports` | Reproduced post-normalization bound bypasses and additional active SVG vectors |
| Hardening GREEN | `bad56fe fix: enforce normalized bounds and inert SVG exports` | Visible-text bounds and structural SVG controls implemented |
| Quality | `/tmp/configurator-venv/bin/ruff check app tests` | `All checks passed!` |

## Test specification

| # | Guarantee | Test | Type | Result |
|---|---|---|---|---|
| 1 | Every brief input is represented by a bounded, extra-forbid Pydantic contract | `tests/test_schemas.py` | Unit | PASS |
| 2 | Contradictory lifecycle and placement combinations are rejected | `tests/test_schemas.py` | Unit | PASS |
| 3 | Scenarios are forced to be fictional and security controls are allowlisted and unique | `tests/test_schemas.py` | Security/unit | PASS |
| 4 | SQLite statements safely preserve SQL-like input without executing it | `tests/test_repository.py` | Integration/security | PASS |
| 5 | Updates append immutable versioned assessment runs | `tests/test_repository.py` | Integration | PASS |
| 6 | Soft deletion removes an active scenario while preserving its historical run | `tests/test_repository.py` | Integration | PASS |
| 7 | CRUD, run-history, health, and export endpoints use consistent envelopes | `tests/test_api.py` | API | PASS |
| 8 | Validation, missing-record, and unexpected-server errors do not leak input or exception details | `tests/test_api.py` | API/security | PASS |
| 9 | JSON, Markdown, and SVG aliases resolve to the persisted latest assessment | `tests/test_api.py` | API | PASS |
| 10 | Repeated demo seeding produces exactly three fictional scenarios and no duplicate runs | `tests/test_demo_data.py` | Integration | PASS |

## Coverage and known gaps

The integrated command `PYTHONWARNINGS=default /tmp/configurator-venv/bin/python -m pytest -q
--disable-warnings` completed with `73 passed` and **90.34% branch-aware coverage**. SQLite
connections were finalized cleanly; no resource warnings remained. Authentication and multi-user
authorization are intentionally outside this local public-prototype API. The stored outputs are
initial solution hypotheses, not approved production architectures.
