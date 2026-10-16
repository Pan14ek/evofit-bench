# Verification and validation strategy (SPEC 01–03)

**Purpose:** give coding agents an explicit, auditable test plan. The SPEC 01/02 table below remains the regression map. The complete SPEC 03 requirement and test status, exact test names, fixture provenance, hashes, commands and blockers are recorded in [`SPEC_03_IMPLEMENTATION_TRACEABILITY.md`](SPEC_03_IMPLEMENTATION_TRACEABILITY.md).

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
| P03-01 | Generic architecture/policy/obligation diff and conservative impact graph | `p_impact.py`, `test_p_impact_v1.py` | See complete status matrix |
| P03-02 | `retain/add/replace/deactivate/adjust` selection is generic and evidence-gated | `p_operations.py`, `test_p_operations_v1.py` | See complete status matrix |
| P03-03 | Exact-pair validity, mandatory coverage and ACCEPT/REJECT/HOLD | `p_semantic.py`, `p_governance.py` and their unit tests | See complete status matrix |
| P03-04 | Candidate materialization, deterministic versioning and V1 adapters | `p_candidate.py`, `test_p_candidate_governance_v1.py` | See complete status matrix |
| P03-05 | Deterministic replay, version binding, event log and conditional rollback | `p_governance.py`, impact and governance tests | See complete status matrix |
| P03-06 | SPEC 02 reuse, V3 preflight and end-to-end method isolation | `p_adaptation.py`, `test_p_governed_adaptation_v1.py` | See complete status matrix |
| E01 | Sealed measured B0/B1/P comparison meets G1/G4 and independent oracle boundary | Later authorized protocol-run record | **Not authorized** |

The exact assertions and PASS/SKIP counts come from running the suites, never this table. The SPEC 03 report expands its 14 requirements into all 48 required rows and records which rows are blocked by absent approved positive-path inputs.

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

