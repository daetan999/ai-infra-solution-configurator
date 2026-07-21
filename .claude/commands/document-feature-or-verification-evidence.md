---
name: document-feature-or-verification-evidence
description: Workflow command scaffold for document-feature-or-verification-evidence in ai-infra-solution-configurator.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /document-feature-or-verification-evidence

Use this workflow when working on **document-feature-or-verification-evidence** in `ai-infra-solution-configurator`.

## Goal

Adds or updates documentation to capture feature contracts, TDD evidence, architecture diagrams, or verification walkthroughs.

## Common Files

- `docs/testing/configurator-engine.tdd.md`
- `docs/testing/configurator-diagram.tdd.md`
- `docs/testing/configurator-api.tdd.md`
- `docs/testing/configurator-integration.tdd.md`
- `docs/testing/browser-qa.md`
- `docs/architecture.md`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Edit or create markdown documentation in docs/ (such as docs/testing/*.md, docs/architecture.md, docs/rules-and-guardrails.md)
- Optionally add or update assets in docs/assets/
- Optionally update README.md

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.