# Context — `tests/unit`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `tests/CONTEXT.md` before this file.

## Responsibility

Contract, schema, validity, applicability, safety and deterministic tests.

## Local landmarks

- `p_applicability_support.py`
- `test_da01_execution.py`
- `test_da01_inputs_and_isolation.py`
- `test_experiment_evidence.py`
- `test_exp01_evidence.py`
- `test_exp02_fitness_evidence.py`
- `test_pilot01_results.py`
- `test_pilot02_method_input_profile.py` (also checks evaluator-run records bind source,
  configuration, command, metrics and raw streams to exact digests)
- `test_p_candidate_governance_v1.py` (including verified inherited-row bindings)
- `test_pilot02_candidate_evaluators.py`
- `test_pilot02_testonly_execution.py`
- `test_p_adaptation_evidence_v1.py` (signed/unsigned verifier-sidecar admission)
- `test_fault_state.py`
- `test_p_applicability_policies_v1.py`
- `test_p_applicability_ruleset_v1.py`
- `p_spec03_support.py`
- `test_p_impact_v1.py`
- `test_p_semantic_pairs_v1.py`
- `test_p_operations_v1.py`
- `test_p_candidate_governance_v1.py`
- `test_p_adaptation_evidence_v1.py`
- `test_g1_method_decision_register.py`

This is a selected list (14 direct tracked files), not a complete source inventory.

## Established conventions

Test negative/unverified/expired/contradictory inputs plus backward compatibility.
PILOT-02 candidate-evaluator cases verify the materialized row, source revision,
profile artifacts, scope, stage, coverage links, and evidence contract before a
scoped evaluator can run; mismatches must remain unmeasured.
PILOT-02 semantic-proof preflight accepts a new row only when its full template
is present in the verified candidate-template catalog; a conflicting row with
the same ID in the parent representation catalog fails closed, and materialized
candidate equality is checked again before proof reuse.
The post-materialization comparison indexes the actual `representations` list
returned by scoped candidate evaluators; it must not look for a nonexistent
`records` field or treat measured bindings as unavailable.
Profile V2 tests also reject parent-catalog digest mismatches, unknown inherited
rows, and evaluator bytes that do not match the verified profile binding.
SPEC03 regression cases also check stale pair revisions, conflicting and
digest-tampered pair assessments, parent-byte/mapping consistency, publish
decision integrity, exact-hash rollback authorization, and full-template
descriptor authorization. Verifier-sidecar tests bind signed evidence to source
digests and immutable snapshots, including V1 compatibility and V2 replay
rejection. The G1 register test audits required decision IDs and pending gate
status; it cannot approve a decision.

## Constraints and known gaps

Current coverage gate reports app-only coverage, not research-tool or requirement completeness. EXP-01 source-binding cases use synthetic Docker identity observations; a passing fixture does not supply authoritative source-to-image provenance. SPEC03 fixtures are synthetic and explicitly TEST_ONLY.

`tests/unit/test_exp01_evidence.py` and `tests/unit/test_exp02_fitness_evidence.py` are included in `DEVELOPMENT_REGRESSION_TESTS` and run again individually by `make development-regression-test` to expose their test counts in hosted logs. EXP-02 fixtures use digest-bound evaluator records, check that digest-valid derived-evidence tampering is rejected, and never provide independent coverage.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. SPEC 01/02/03 DEVELOPMENT checks use `make development-quality` with a **disposable** PostgreSQL database; its lint, format, type-check, and test discovery exclude the two protected DA01 modules. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.

- test_pilot02_v6_archive.py verifies the PILOT-02 V6 packaging-copy helper preserves payload bytes, emits sha256sum-compatible relative rows, and rejects traversal paths; it does not alter or authorize the historical experiment.
