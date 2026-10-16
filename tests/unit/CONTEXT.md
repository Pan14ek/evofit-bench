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
- `test_fault_state.py`
- `test_p_applicability_policies_v1.py`
- `test_p_applicability_ruleset_v1.py`
- `p_spec03_support.py`
- `test_p_impact_v1.py`
- `test_p_semantic_pairs_v1.py`
- `test_p_operations_v1.py`
- `test_p_candidate_governance_v1.py`

This is a selected list (13 direct tracked files), not a complete source inventory.

## Established conventions

Test negative/unverified/expired/contradictory inputs plus backward compatibility.
SPEC03 regression cases also check stale pair revisions, conflicting and
digest-tampered pair assessments, parent-byte/mapping consistency, publish
decision integrity, and exact-hash rollback authorization.

## Constraints and known gaps

Current coverage gate reports app-only coverage, not research-tool or requirement completeness. SPEC03 fixtures are synthetic and explicitly TEST_ONLY.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
