---
name: implement-or-update-core-feature-with-tests
description: Workflow command scaffold for implement-or-update-core-feature-with-tests in ai-infra-solution-configurator.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /implement-or-update-core-feature-with-tests

Use this workflow when working on **implement-or-update-core-feature-with-tests** in `ai-infra-solution-configurator`.

## Goal

Implements or updates a core feature in the application, accompanied by relevant test coverage.

## Common Files

- `app/engine.py`
- `app/rules.py`
- `app/architecture.py`
- `app/diagram.py`
- `app/domain.py`
- `app/demo_data.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Edit or create files in app/ (such as engine.py, rules.py, architecture.py, diagram.py, etc.)
- Edit or create corresponding test files in tests/ (such as test_engine.py, test_rules.py, test_diagram.py, test_api.py, etc.)

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.