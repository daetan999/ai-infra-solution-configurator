# Configurator engine TDD evidence

## Source and journeys

The journeys were derived from the portfolio build brief for the Enterprise AI Solution
Configurator; no separate implementation plan was used.

- As a solution consultant, I can turn validated discovery inputs into one recommendation for
  every required architecture layer, so an initial solution hypothesis is complete.
- As a technical reviewer, I can trace every selected component to the customer requirement,
  triggered rule, rationale, alternative, risk, and required validation.
- As a workshop facilitator, I can see deterministically resolved conflicts, missing evidence,
  confidence, open questions, migration considerations, a PoC, and the next workshop.
- As an auditor, I can reproduce a result from its normalized input and ruleset digests without
  network calls, randomness, or input mutation.

## RED and GREEN checkpoints

| Stage | Commit | Command | Observed result |
|---|---|---|---|
| RED: public contract | `d3bcee2` | `python -m pytest tests/test_rules.py tests/test_engine.py -q --no-cov` | Collection failed on the intentionally absent `app.domain` and `app.engine` modules. |
| GREEN: rules engine | `6616374` | `python -m pytest tests/test_rules.py tests/test_engine.py -q --no-cov` | `13 passed`; all initial contracts were satisfied. |
| RED: enum edges | `b9a9875` | `python -m pytest tests/test_rules.py -q --no-cov` | Two intended failures reproduced absent platform evidence incorrectly triggering reuse rules and lifecycle `both` failing to trigger training rules. |
| GREEN: enum edges | `30cc995` | `python -m pytest tests/test_rules.py tests/test_engine.py --cov=app.domain --cov=app.rules --cov=app.engine --cov-branch -q -o addopts=''` | `16 passed`; enum behavior fixed and branch-aware coverage remained above the gate. |

Commands above used the isolated verification interpreter at
`/tmp/capacity-planner-venv-2/bin/python`; the repository command is otherwise identical after
installing the `dev` dependency group.

## Test specification

| # | Guarantee | Evidence | Type | Result |
|---|---|---|---|---|
| 1 | Normalization is canonical, de-duplicates set-like security controls, and does not mutate inputs. | `tests/test_rules.py::test_normalization_is_immutable_and_canonical` | Unit | PASS |
| 2 | Triggered rules always cover all 13 architecture output layers. | `tests/test_rules.py::test_matching_rules_cover_every_architecture_layer` | Unit | PASS |
| 3 | Conflicts resolve by descending priority, then lexical rule ID for stable ties. | `tests/test_rules.py::test_conflict_resolution_uses_priority_then_rule_id` | Unit | PASS |
| 4 | Rule IDs are unique and the ruleset digest is independent of declaration order. | `tests/test_rules.py::test_ruleset_identifiers_are_unique`, `test_ruleset_digest_is_independent_of_declaration_order` | Unit | PASS |
| 5 | Missing existing-platform evidence does not silently trigger reuse recommendations. | `tests/test_rules.py::test_absent_existing_platform_evidence_does_not_trigger_reuse_rules` | Unit | PASS |
| 6 | Validated lifecycle and neutral placement enum values match their intended rules. | `tests/test_rules.py::test_combined_lifecycle_triggers_training_rules`, `test_neutral_placement_values_do_not_trigger_cloud_or_on_premises_rules` | Unit | PASS |
| 7 | Every assessment exposes all required trace fields and compatibility aliases. | `tests/test_engine.py::test_result_has_every_required_solution_layer_and_trace_field` | Unit | PASS |
| 8 | A fictional private hybrid RAG input selects specialized deployment, retrieval, and security patterns. | `tests/test_engine.py::test_private_hybrid_rag_uses_explainable_specialized_patterns` | Scenario | PASS |
| 9 | Semantically equivalent mapping and security-control order produces an identical assessment and digests. | `tests/test_engine.py::test_result_and_digests_are_canonical_across_mapping_and_set_like_order` | Determinism | PASS |
| 10 | Changing placement evidence changes the input digest and deployment recommendation. | `tests/test_engine.py::test_input_change_updates_digest_and_recommendation` | Unit | PASS |
| 11 | Competing rules remain visible with selected and superseded IDs and priorities. | `tests/test_engine.py::test_competing_preferences_are_resolved_and_exposed` | Unit | PASS |
| 12 | Sparse evidence reduces confidence and creates explicit validation questions. | `tests/test_engine.py::test_sparse_evidence_lowers_confidence_and_creates_questions` | Boundary | PASS |
| 13 | Complete evidence produces risks, migration steps, PoC criteria, and a next-workshop agenda. | `tests/test_engine.py::test_complete_evidence_produces_actionable_workshop_outputs` | Scenario | PASS |
| 14 | The engine rejects non-mappings and never mutates a validated mapping. | `tests/test_engine.py::test_non_mapping_input_is_rejected`, `test_engine_does_not_mutate_validated_input` | Boundary | PASS |

## Final verification

Executed:

```text
ruff check app/domain.py app/rules.py app/engine.py tests/test_rules.py tests/test_engine.py
python -m pytest tests/test_rules.py tests/test_engine.py \
  --cov=app.domain --cov=app.rules --cov=app.engine \
  --cov-report=term-missing --cov-branch --cov-fail-under=80 -q -o addopts=''
```

Observed:

```text
All checks passed!
17 passed
app/domain.py 100%
app/engine.py 90%
app/rules.py 97%
TOTAL 94.02% branch-aware coverage
```

## Known gaps and boundaries

- This report covers the pure rules engine. API, persistence, diagram, export, and browser tests
  are separate integration surfaces in this repository.
- Recommendations are initial solution hypotheses; technical validation and a formal architecture
  review remain required.
- The engine performs no external calls. Any optional wording enhancement must occur after the
  deterministic assessment and must not change rule decisions, calculations, or digests.

