# Verification and validation strategy (SPEC 01–03)

**Purpose:** give coding agents an explicit, auditable test plan. The table is a documentation-level **traceability seed**: it is not a claim that every row has a passing test. Tests for future SPEC 03 remain planned until the associated functionality is implemented.

## Local context integrity

The tracked-directory coverage check lives in `tests/unit/test_context_documents.py`. It requires a `CONTEXT.md` at the repository root and in every Git-tracked directory outside `docs/`, except under `experiments/execution/policy-pilot/v1/source/`, including nested directories. That V3 policy-source root is protected by an exact file allowlist: do not relax the exporter to permit documentation. Keep its context in the parent `policy-pilot/v1/CONTEXT.md`. Do not conflate this documentation check with the input-isolation or scientific readiness gates. Run:

```bash
uv run pytest --no-cov tests/unit/test_context_documents.py
```

## Required distinction

- **Unit/contract/integration tests:** validate implementation behavior or local synthetic input.
- **Adversarial/metamorphic/isolation tests:** probe failure modes, evidence integrity, nondeterminism and data leakage.
- **Engineering quality:** format, type checks, security scanner, import constraints, migration tests and app coverage.
- **Research validation:** independent sealed oracle, proper unit of analysis, G1/G4 approvals and later measured B0/B1/P data. Test passes **cannot substitute** for measured evidence.

A test described in a specification must have a stable requirement ID, fixture provenance, preconditions, input, expected behavior, test level, location, and PASS/FAIL/SKIP/BLOCKED outcome. Never mark unimplemented requirements as passed.

## Source-backed traceability seed

| Requirement | Expected behavior | Existing suite / planned owner | Status |
| --- | --- | --- | --- |
| C01 | Invalid Snapshot schema/hash/version is rejected | `tests/unit/test_p_input_contract_v11.py`, `test_p_input_authority_validation.py` | Existing synthetic tests |
| C02 | Missing policy approval and absence proof remain UNDETERMINED | `tests/unit/test_p_input_authority_validation.py` | Existing synthetic tests |
| C03 | V1 exports and protected artifacts remain unchanged; V2 strict isolation | `tests/unit/test_p_input_v2_isolation.py`, `test_da01_inputs_and_isolation.py` | Existing regression tests |
| A01 | Complete Strong Kleene T/F/U tables, typed selectors and closed DSL | `tests/unit/test_p_applicability_ruleset_v1.py` | Existing synthetic tests |
| A02 | Exactly 18 obligations each return one valid applicability status/trace | `tests/unit/test_p_applicability_policies_v1.py` | Existing synthetic tests |
| A03 | Unverified opposite-polarity policy blocks unjustified ACTIVE; independent support remains valid | `tests/unit/test_p_applicability_policies_v1.py` | Added in PR #5 follow-up |
| A04 | A SnapshotValidationResult cannot be reused with another Snapshot | `tests/unit/test_p_applicability_policies_v1.py`, `tests/integration/test_p_applicability_v3.py` | Added in PR #5 follow-up |
| A05 | V3 source is separately pinned; B1/P common policy and Snapshot are identical | `tests/integration/test_p_applicability_v3.py` | Existing synthetic tests |
| A06 | Export → SPEC01 verification → proof ledger → SPEC02 assessment runs deterministically | `tests/integration/test_p_applicability_v3.py` | Added in PR #5 follow-up |
| S01 | Oracle/scorer/source-history/network and other-method output cannot enter method input | `tests/unit/test_da01_inputs_and_isolation.py`, `tests/integration/test_p_applicability_v3.py` | Existing; inspect Docker SKIP separately |
| P03-01 | Generic architecture diff / impact graph, including negative/unaffected delta | SPEC 03 test matrix and implementation | **Planned** |
| P03-02 | `retain/add/replace/deactivate/adjust` selection is generic, minimal and correct under evidence | SPEC 03 test matrix and implementation | **Planned** |
| P03-03 | UNKNOWN, stale, conflicting/invalid evidence leads to documented HOLD/blocked decision | SPEC 03 test matrix and implementation | **Planned** |
| P03-04 | Candidate materialization and evaluator-to-obligation coverage are independently validated | SPEC 03 integration / contract tests | **Planned** |
| P03-05 | Determinism under input reorder/replay, version mismatch, tamper and changed policy revision | SPEC 03 metamorphic/adversarial tests | **Planned** |
| P03-06 | V1/V2/V3 compatibility, B1/P fairness and frozen DA01 invariants | SPEC 03 regression/integration tests | **Planned** |
| E01 | Sealed measured B0/B1/P comparison meets G1/G4 and independent oracle boundary | Later authorized protocol-run record | **Not authorized** |

The exact assertions and PASS/SKIP counts must come from running the suites, never this table. SPEC 03 must **expand** P03-01…P03-06 into a complete finite matrix of positive, negative, boundary, property and end-to-end cases, with file/test names and results.

## Pre-merge Definition of Done for implementation SPECs

1. Formalize the feature's observable contract (inputs, outputs, invalid/unknown/halt semantics, provenance fields and version).
2. Write a **requirement-to-test table** and implement all mandatory cases, including relevant adverse evidence, wrong source/version, incomplete closure, conflict and unauthorized state transitions.
3. Test unit math, schema/type constraints and deterministic serialization. Add integration across actual interfaces instead of relying only on mocked per-module tests.
4. Check strict B1/P information parity where inputs change. Assert no oracle/expected-operation tokens reach the method's bundle. Keep legacy V1 and candidate V2/V3 exact-byte/semantic compatibility as relevant.
5. Run targeted tests plus `make test-unit`, `make architecture-test`, `make migration-test`, `make quality` with a **disposable** PostgreSQL DB. Run Docker isolation negative probes when a digest-pinned image is available; report unavailable probes as **SKIP/BLOCKED**, not PASS.
6. Keep coverage notions separate: line/branch coverage, *requirement coverage*, and scientific power/sample size are different. A 100% finite requirement matrix can still miss unexpected faults.
7. Provide CI URLs, commands, actual PASS/FAIL/SKIP summaries and failed-case investigation in the PR. Never edit existing expected outputs/oracle to make new code look correct.
8. An implementation is DEVELOPMENT-ready only after mandatory checks pass or explicit unresolved blockers are accepted for that scope. This does not change G1/G4 for measured runs.

## High-value falsification tests for SPEC 03

- Architecture has no change; method should not invent new operations.
- An obligation remains active while its old evaluator becomes stale/vacuous; mere code-test pass does not certify coverage.
- Two valid requirements collide on one representation; candidate operation ordering must remain deterministic and evidence-justified.
- Changed policy bundle with same architecture SHA affects only relevant normative decisions.
- Missing, mismatched or unverified telemetry/evaluator evidence **never** produces claimed positive coverage.
- Unknown applicability blocks inappropriate deactivation, rather than silently replacing it with `retain` or deleting it from the denominator.
- Multiple representations cover one obligation: count coverage once only when an independently validated pair exists.
- No single DA01 outcome is used as proof of population-level significance.

See `../experiments/execution/da01/PROTOCOL.md`, `SCORE_RULES.md`, `VALIDITY_RULES.md`, `READINESS.md` for the measured-run rules. Do not run the private scorer inside method test suites.

