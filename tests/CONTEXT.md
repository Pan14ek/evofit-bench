# Context — `tests`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `CONTEXT.md` before this file.

## Responsibility

Python unit, architecture and PostgreSQL integration suites, including EXP-01/02 evidence contracts, EXP-03 bridge integration, EXP-04 evidence admission, and independent synthetic SPEC03 impact, exact-pair, operation, materialization, governance, provenance and rollback tests.

## Local landmarks

- `__init__.py`
- `fixtures/p_method/`
- `unit/test_p_impact_v1.py`
- `unit/test_p_semantic_pairs_v1.py`
- `unit/test_p_operations_v1.py`
- `unit/test_p_candidate_governance_v1.py`
- `integration/test_p_governed_adaptation_v1.py`
- `integration/test_exp03_method_bridge.py`
- `integration/test_exp04_evidence_admission.py`
- `unit/test_pilot01_results.py`
- `unit/test_pilot02_method_input_profile.py`
- `unit/test_pilot02_testonly_execution.py`
- `unit/test_b0p_git_inventory.py` — pinned Git inventory and digest-tampering checks
- `unit/test_b0p_development.py` — isolated-copy preparation, source-pin and readback checks
- `unit/test_module_public_apis.py` — ΔA2 exports, cross-module public imports and Reporting exception
- `integration/test_public_module_contracts.py` — public facade session ownership and task rollback

## Established conventions

Synthetic tests and quality gates must be distinguished from scientific measured runs.

## Constraints and known gaps

SPEC03 fixtures are independently authored TEST_ONLY inputs. Never use oracle to manufacture P predictions or call skips passes; the SPEC03 synthetic pipeline is not measured validation.

The EXP-03 bridge integration tests use digest-valid EXP-02 fixture runs and
the repository's DRAFT/OPEN V3 policy pilot. They execute the actual verified
Method P development path and assert HOLD/UNKNOWN; they do not authorize
positive semantic proof or measured DA01 outcomes. Existing V3 TEST_ONLY
positive cases remain separate and run in the hosted development regression.

The EXP-04 integration tests validate digest-bound EXP-02 observations,
adversarial canonical mappings, verifier failures, TEST_ONLY sidecar
consumption without semantic proof, noncompliance versus evaluator adequacy,
and contradictory readback. These fixtures do not claim production authority
or represent measured EXP-02 runs.

The B0/P DEVELOPMENT preparation tests use an isolated Git clone, exercise
write-once input export and strict readback, and reject source, denominator,
path, and evaluator-digest mismatches. They verify preparation only; they do
not run either arm or produce experimental scores.

## PILOT-02 tests

PILOT-02 profile tests bind the A0.1 architecture-compliance mappings to the
pinned profile and exact configuration/catalog/evaluator bytes. Pair tests
preserve unavailable inspection scope as UNKNOWN without substituting a
numeric zero.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
