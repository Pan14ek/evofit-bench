# Context — `tests`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `CONTEXT.md` before this file.

## Responsibility

Python unit, architecture and PostgreSQL integration suites, including EXP-01/02 evidence contracts, EXP-03 bridge integration, EXP-04 evidence admission, and independent synthetic SPEC03 impact, exact-pair, operation, materialization, governance, provenance and rollback tests.

## Local landmarks

- `__init__.py`
- `architecture/a1/test_evaluators.py` — W2 evaluator fixtures plus exact-byte A0.3/A0.4 canonical checkpoint readback, later-revision reproduction, and fail-closed tamper controls.
- `architecture/a1/REQUIREMENT_TEST_MATRIX.md`
- `fixtures/p_method/`
- `unit/test_p_impact_v1.py`
- `unit/test_p_executable_candidate_identity.py` — verifies the review identity manifest against its pinned Git blobs and checkout bytes
- `unit/test_p_semantic_pairs_v1.py`
- `unit/test_p_operations_v1.py`
- `unit/test_p_candidate_governance_v1.py`
- `integration/test_p_governed_adaptation_v1.py`
- `integration/test_exp03_method_bridge.py`
- `integration/test_exp04_evidence_admission.py`
- `unit/test_pilot01_results.py`
- `unit/test_eval01_runner.py` — repeated evaluator observations collapse to one source-case result; source-identity mismatches, unstable repeats and `NOT_EVALUABLE` scope are excluded from binary metrics.
- `unit/test_eval02_runner.py` — EVAL-02 confusion metrics use independent architecture labels and exclude non-applicable or out-of-scope evaluator observations.
- `unit/test_eval02_postrun_validation.py` — verifies the preserved EVAL-02 archive and keeps diagnostic mismatches separate from invocation and provenance failures.
- `unit/test_pilot02_method_input_profile.py`
- `unit/test_pilot02_testonly_execution.py`
- `unit/test_b0p_git_inventory.py` — pinned Git inventory and digest-tampering checks
- `unit/test_b0p_development.py` — isolated-copy preparation, source-pin and readback checks
- `unit/test_mono_a1.py` — synthetic MONO reference custody, E2 source-binding negative checks, sealed scoring prerequisites, denominator/exact-pair boundaries, and archive readback
- `unit/test_mono_e1_preflight.py` — source-pair and B0/P comparability readback, allowlist/leakage, image attestation, timing, missing resource values, and authority fail-closed checks; no method execution
- `unit/test_mono_e1_dev_p_decisions.py` — author-reference freeze, eight-scenario catalog, TEST_ONLY V3 P replay, evidence fail-closed cases, and raw-output checksum integrity; separate from official MONO-E1
- `unit/test_mono_policy_review_inventory.py` — exact catalog copy, OPEN-03/OPEN-04 completeness dimensions, and structural-only approval boundary
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

The MONO-A1 tests validate only additive preparation contracts. Their
synthetic reference and verifier fixtures are not MONO-E1/E2 measurements or
independent W2 evaluator evidence. See
`experiments/execution/MONO_A1_PROTOCOL_V1.md` for readiness gates.

The `MONO_E1_DEV_P_DECISIONS_V1` runner reuses the synthetic SPEC 03 integration
fixture builder, then performs fresh `verify_v3_p_bundle()` calls and invokes
`run_adaptation()` for every repetition. Its scorer reference is never copied
to method inputs; all labels remain non-independent DEVELOPMENT assumptions.

## PILOT-02 tests

PILOT-02 profile tests bind the A0.1 architecture-compliance mappings to the
pinned profile and exact configuration/catalog/evaluator bytes. Pair tests
preserve unavailable inspection scope as UNKNOWN without substituting a
numeric zero.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
