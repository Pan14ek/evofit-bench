# Method P executable candidate review package v1

**Status:** DEVELOPMENT review candidate only. This package does not freeze the
algorithm, close G1, authorize G4, or report a measured experiment.

## Candidate identity

The machine-readable identity is
[`P_EXECUTABLE_CANDIDATE_V1.json`](../experiments/execution/P_EXECUTABLE_CANDIDATE_V1.json),
validated by
[`p_executable_candidate_identity_v1.schema.json`](../experiments/execution/schemas/p_executable_candidate_identity_v1.schema.json).
It records method version `P_GOVERNED_ADAPTATION_DEVELOPMENT_V1`, algorithm
version `P_GOVERNED_ADAPTATION_V1`, the exact source revision and tree, and
SHA-256 values for implementation, input/configuration contracts, and review
basis files. `source_identity_sha256` covers the source revision and implementation list;
`configuration_sha256` covers the configuration list. `identity_sha256` is SHA-256
over canonical JSON of the whole manifest with that one field omitted. The identity
test reads each named file
from both the recorded Git tree and the checkout and requires byte equality.

The pinned implementation source is latest `main` at commit
`6ca20ea1b86c3570510c4c3f206ae3c418d13781`, tree
`a195778a5137674bfc1c3d46069f752336438549`. The manifest identity digest is
`45c75b7d211705ab001f080a193aa64641e01d5222e25603cd0ef241fecefde4`; source identity
is `c477bd4258734a615fcdaf8491988a36bba90004eb4af083c76e0e814ff0ccbf`, and
configuration identity is `cdd4df7342e821927c3a565f6bcec02d51a6c65bbca2fd131cfaae099ecb9fca`.
The implementation files are unchanged from that base; this branch adds
reproducibility and regression checks plus this review package. The identity
manifest is a package-level pin. Current runner output does not repeat its
identity digest, so a later measured execution envelope must bind this manifest
digest explicitly before it can claim run-level source provenance.

## Executable path and contracts

The candidate reuses `verify_v3_p_bundle()` and `run_adaptation()` in
`experiments/execution/tooling/p_adaptation.py`. V3 verification composes the
existing SPEC 01 snapshot validator, SPEC 02 ruleset and applicability engine,
exact-pair semantics, typed impact analysis, operation planner, candidate
materializer, and governance path. It does not introduce a second adaptation
algorithm. `b0p_isolated_p_runner.py` serializes this existing result in the
restricted development execution path; it adds no decision rule.

The input is the strict, allowlisted V3 method bundle and optional separately
verified evidence. The output is the existing typed assessment set, operation
plan, candidate if materialized, governance decision, and deterministic trace.
Invalid schema, digest, role, or identity bindings are rejected. Missing
authority, applicability, evidence, evaluator capability, or cost remains
unknown/held. Governance outcomes are `INPUT_REJECTED`, `REJECT`, `HOLD`, and
`ACCEPT`; a compatibility prediction is projected only from the sealed
`ACCEPT` decision. Publication remains disabled. TEST_ONLY trust is explicit
and cannot authorize production output.

## Formal procedure crosswalk

| Stage | Implementation and contract | Existing automated evidence | Gap and approval boundary |
| --- | --- | --- | --- |
| 1. Strict input and provenance | `verify_v3_p_bundle()`, `verify_method_bundle_v3()`, `load_verified_source_manifest()`; V3 manifest and evidence schemas | `test_p_input_contract_v11.py`, `test_p_input_v2_isolation.py`, `test_p_input_authority_validation.py`, `test_p_applicability_v3.py` | Source and configuration bytes are pinned in this package. The current runtime trace does not yet echo this package identity; run-level binding is required before measured integration. |
| 2. Architecture and policy snapshot validation | `load_and_validate_snapshot()`, `load_and_validate_ruleset()`; Snapshot v1.2 and pinned V3 policy bundle | `test_p_applicability_policies_v1.py`, `test_p_input_authority_validation.py`, V3 verifier and substitution regressions | Production policy authority and approved completeness claims are absent. They remain outside this implementation task. |
| 3. Evidence-aware applicability | `evaluate_obligations()` uses three-valued `ACTIVE/INACTIVE/UNKNOWN` rules and scoped evidence | `test_p_applicability_ruleset_v1.py`, `test_p_applicability_policies_v1.py`, V3 no-op, missing-proof, and closure-binding cases | TEST_ONLY positive fixtures demonstrate mechanics only. Approved production policy authority remains a G1/G4 prerequisite. |
| 4. Typed impact | `diff_snapshot()`, applicability diff in `run_adaptation()`, then `analyze_impact()` over typed trace edges | `test_p_impact_v1.py`, including indeterminate changes and order-invariant impact digests | Applicability changes are represented as obligation `ChangeRecord` values rather than a separate runtime algebraic type, as documented in SPEC 03. The formal abstraction is not silently expanded here. |
| 5. Exact representation-obligation semantics | `assess_pair()` checks one pair, scope, stage, revision, evaluator, evidence, and semantic proof | `test_p_semantic_pairs_v1.py`, V3 exact-pair and tamper controls | This is method-side assessment, not the independent reference verdict. Independent evidence authority remains separate. |
| 6. Mandatory coverage | `assess_mandatory_coverage()` requires the complete applicable denominator and valid pair/execution evidence | `test_p_semantic_pairs_v1.py`, coverage controls in `test_p_applicability_v3.py` | Production mandatory classifications and independent pair proofs are not yet available; unknown rows cannot be removed. |
| 7. Deterministic operation choice | `build_operation_plan()` selects a bounded plan by operation count, authorized cost, then stable identifiers; missing cost or exhausted search holds | `test_p_operations_v1.py`, especially missing template/cost, unknown applicability, budget exhaustion, and tie controls | Cost units, admissible bounds, and search-exhaustion interpretation remain OPEN-06 pending independent review. Existing draft behavior is preserved. |
| 8. Candidate construction | `materialize_candidate()` binds a child to parent bytes, operation plan, source and artifact digests; V1 adapters project the existing contract | `test_p_candidate_governance_v1.py`, including parent mapping, candidate digest, V1 adapter and deterministic child-version checks | The runtime uses verified templates; it does not synthesize evaluator code. OPEN-08 still governs interpretation of multi-obligation ADD in frozen V1 scoring. |
| 9. Governance | `run_adaptation()` reaches sealed governance with twelve invariant verdicts; `p_governance.py` blocks unsealed publication and unsafe rollback | `test_p_candidate_governance_v1.py`, V3 TEST_ONLY ACCEPT/HOLD/reject controls | Synthetic ACCEPT is test evidence only. `PUBLISHING_ENABLED` remains false, and the measured interface remains NOT_READY. |
| 10. Deterministic output and trace | Canonical assessment/plan/candidate/governance digests; `b0p_isolated_p_runner.py` writes trace and outputs without adding method rules | Exact replay in `test_v3_synthetic_noop_accepts_with_independent_before_after_closure_claims`; sidecar-order permutation regression; `test_p_candidate_governance_v1.py` event replay; identity tests in this package | A live digest-pinned container run was not performed for this review. The candidate does not claim measured runtime or per-run image provenance. |

## Requirements-to-tests matrix

| Requirement | Evidence |
| --- | --- |
| Unaffected control returns justified RETAIN/no-op | `test_v3_synthetic_noop_accepts_with_independent_before_after_closure_claims` asserts unchanged representation and RETAIN-only operations under TEST_ONLY evidence. |
| Authorized, fully evidenced change can materialize a candidate | `test_v3_synthetic_add_uses_authorized_descriptor_and_accepts_with_scoped_closure_claims` uses a hash-pinned evaluator and full-descriptor TEST_ONLY authorization. |
| Unknown applicability or missing proof leads to HOLD | `test_synthetic_pipeline_runs_spec02_and_holds_open_authority_unknown`, `test_missing_scoped_adaptation_proof_holds_without_legacy_outputs`, and unit unknown-applicability cases. |
| Invalid input or tampered identity is rejected/detected | V3 digest/revision substitution and source-manifest tests; `test_identity_manifest_digest_detects_tampering`; source identity test checks pinned Git blobs and checkout bytes. |
| Missing evaluator capability or authority cannot ACCEPT | `test_missing_or_untrusted_template_is_hold_not_a_fictional_add`, `test_v1_artifact_hash_sidecar_does_not_authorize_template_descriptor`, and missing-proof V3 case. |
| Hard invariant failure cannot be ignored | `test_proven_hard_invariant_failure_rejects_valid_candidate` asserts a valid-input `FAIL` returns REJECT with `INVARIANT_VIOLATION_PROVEN`; `test_unresolved_coverage_is_hold_and_proven_incomplete_candidate_is_reject` checks separate HOLD/REJECT cases. |
| Input ordering preserves canonical decisions and hashes | `test_input_permutations_preserve_graph_and_impact_digests` and new `test_v3_equivalent_sidecar_orderings_preserve_semantic_hashes`. |
| Repeated frozen inputs replay equivalently | V3 no-op integration replay checks plan, candidate, governance, V1 candidate, and prediction identities; append-only event-chain identical replay test. |
| Forbidden inputs stay outside the method bundle | `test_v3_export_rejects_answer_markers_and_unallowlisted_files`, `test_oracle_git_and_scorer_paths_are_forbidden_method_inputs`, `test_oracle_contamination_and_historical_overwrite_are_rejected`; `tooling/isolation.py` configures `--network=none` and bounded mounts. |
| Readiness guard remains intact | New `test_p_interface_readiness.py` asserts `P_ALGORITHM_STATUS == NOT_READY` and `require_p_algorithm()` raises `MethodNotReadyError`. |

## Synthetic verification and isolation boundary

The suite contains a TEST_ONLY no-op ACCEPT and an authorized descriptor ADD
ACCEPT, both with scoped before/after closure evidence and a real hash-pinned
synthetic evaluator. The same path returns HOLD for missing authority or proof,
and rejects malformed or mismatched source, policy, and evaluator bindings.
These cases are generic fixtures and do not supply DA01 expected operations,
private targets, or a research result.

Input manifests reject oracle, scorer, Git, and other-arm paths; V3 bundle
verification reads named allowlisted files. The isolated runner uses the
existing no-network container command and bounded input/output mounts. The
review verification below exercises structural and synthetic checks; it does
not claim a fresh Docker execution or an adversarial live container probe.

## Verification record

Commands ran from the repository root with the task venv on `PATH` and the
checkout on `PYTHONPATH`:

```bash
PATH=/private/tmp/b0p-venv/bin:$PATH PYTHONPATH="$PWD" pytest --no-cov -p no:cacheprovider -q tests/unit/test_p_impact_v1.py tests/unit/test_p_semantic_pairs_v1.py tests/unit/test_p_operations_v1.py tests/unit/test_p_candidate_governance_v1.py tests/unit/test_p_adaptation_evidence_v1.py tests/unit/test_p_input_authority_validation.py tests/unit/test_p_applicability_ruleset_v1.py tests/unit/test_p_applicability_policies_v1.py tests/unit/test_p_interface_readiness.py tests/unit/test_p_executable_candidate_identity.py tests/integration/test_p_applicability_v3.py tests/integration/test_p_governed_adaptation_v1.py
```

Result: **175 passed**, one Starlette/httpx deprecation warning. The separate
identity/readiness rerun after lint formatting passed **3 tests**.

```bash
PATH=/private/tmp/b0p-venv/bin:$PATH PYTHONPATH="$PWD" pytest --no-cov -p no:cacheprovider -q tests/unit/test_context_documents.py tests/unit/test_p_input_contract_v11.py tests/unit/test_p_input_v2_isolation.py tests/unit/test_b0p_execution.py
```

Result: **57 passed**. The checks cover hierarchical context documents,
strict input contracts, bundle isolation, forbidden oracle/scorer paths, and
the existing runner behavior.

Ruff check and format check passed for the changed Python files. Mypy passed for the two new readiness/identity unit modules with
`PATH=/private/tmp/b0p-venv/bin:$PATH PYTHONPATH="$PWD" MYPY_CACHE_DIR=/private/tmp/method-p-candidate-mypy-cache mypy --follow-imports=skip tests/unit/test_p_interface_readiness.py tests/unit/test_p_executable_candidate_identity.py`.
`git diff --check` passed. A full `make quality` run and a fresh Docker
execution were not performed: this environment has no `uv` command and no
disposable PostgreSQL test database, and this review was not authorized to run
MONO-E1/E2.

## OPEN-06 through OPEN-09: alternatives retained for review

- **OPEN-06 — bounded cost and search.** Keep the current deterministic
  lexicographic planner with operation count, then authorized incremental cost,
  then stable identifiers; alternatively define a different admissible cost
  model or a broader optimization objective. The current rule is implemented
  as DEVELOPMENT behavior, while cost units, bounds, collision policy, and
  exhausted-search interpretation remain unapproved. Choosing among them
  changes the feasible operation set and adaptation-cost endpoint.
- **OPEN-07 — compliance violation versus invalid evidence.** Preserve the
  code's separate compliance and pair-validity fields; alternatively revise
  the validity mapping for completed nonzero evaluator exits after reconciling
  it with frozen DA01 rules. The current development pair assessment may report
  VALID with NON_COMPLIANT when evidence is adequate, while the frozen DA01
  validity contract treats nonzero exit as execution failure. Changing this
  affects coverage and would require a separately reviewed/versioned contract.
- **OPEN-08 — multi-obligation ADD and V1 target identity.** Retain the
  DEVELOPMENT canonical owner obligation with coverage links; alternatively
  emit separate obligation ADDs for one representation or defer such changes
  from measured scope. These choices change target counts, duplicates, and
  precision/recall compatibility. No frozen scorer or V1 schema is changed.
- **OPEN-09 — independent review and holdout custody.** Require an external
  reviewer before any measured prediction, or establish a separately governed
  review team with sealed holdout custody and auditable prediction sealing.
  A signed freeze record, separation of duties, and evidence that authors did
  not see holdout labels remain necessary. The synthetic suite is not a
  substitute for that process.

All four items remain `PENDING_INDEPENDENT_REVIEW` in the G1 decision
register. This package documents options and consequences without selecting a
scientific policy.

## DEVELOPMENT-to-measured boundary and next step

This candidate reuses existing rules and remains `P_GOVERNED_ADAPTATION_V1` in
DEVELOPMENT. Before measured integration, the independent process must resolve
OPEN-06..09 and the other applicable G1 decisions, supply production-approved
policy and evaluator/template/cost authority, establish independent exact-pair
evidence and holdout custody, and bind the manifest identity plus digest-pinned
container image into each execution record. Then an authorized reviewer must
freeze a versioned method and W0 must separately grant G4 authorization. The
measured interface guard remains in force until those gates are met. No
MONO-E1/E2 run, readiness update, reference freeze, or scorer access is part of
this candidate.
