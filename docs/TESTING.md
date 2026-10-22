# Verification and validation strategy (SPEC 01–04)

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

## ΔA4 Reporting query port acceptance

The stage-aware architecture check keeps historical A0.1 acceptance pinned to
its original Git commit, A0.2 at the exact predecessor in the preserved A0.3
manifest, and canonical A0.3 at its pinned merge commit and trees. Development
CI explicitly requires A0.4. Stage detection recognizes A0.4 before retained
A0.3 history, validates the A0.4 manifest and its preserved A0.3 predecessor,
and fails closed if the A0.4 manifest is removed on a descendant commit or if
the requested stage is downgraded. Historical A0.2 and A0.3 commits still
resolve from their own ancestry and run their corresponding checks.

A0.4 acceptance runs source-based `AC_PUBLIC_API` and `AC_MODULE_GRAPH` against
the exact clean candidate HEAD. Both must report complete source scope,
matching source identity, no unresolved imports, `COMPLIANT`, and successful
digest readback. AC_PUBLIC_API accepts Reporting → Tasks.public and rejects
Reporting → Tasks.service; AC_MODULE_GRAPH preserves the approved five-edge
capability graph. AC_DATA_OWNERSHIP remains NOT_APPLICABLE.

Focused checks:

```bash
uv run pytest --no-cov -p no:cacheprovider tests/unit/test_architecture_stage_checks.py
uv run pytest --no-cov -p no:cacheprovider tests/architecture/a1/test_evaluators.py
make architecture-test ARCHITECTURE_STAGE=A0_4_REPORT_QUERY_PORT
TEST_DATABASE_URL=postgresql+psycopg://evofit:evofit@localhost:5432/evofit_test uv run pytest --no-cov -p no:cacheprovider tests/integration/test_api_flows.py tests/integration/test_public_module_contracts.py
```

The focused checks cover A1-NEG-01 through A1-NEG-03 and preserve the ΔA3
acceptance matrix in `tests/architecture/a1/REQUIREMENT_TEST_MATRIX.md`. The
stage command runs pinned historical A0.1, A0.2, and A0.3 checks, then the
current A0.4 evaluators and architecture test selection. Full development
verification uses `make development-quality` with a disposable PostgreSQL
database. These checks establish engineering acceptance only; they do not
establish semantic fitness coverage, G1/G4, or measured DA01 results.

The checked-in A0.3 evaluator observations and readback sidecar remain
historical candidate evidence bound to source commit
`1b7a0c94dfd7c4bbca03def62b870da3e3cce580`. They are not the final canonical
post-merge A0.3 checkpoint. The separate canonical post-merge checkpoint is
recorded in `architecture/acceptance/a1/a0_3_canonical_checkpoint.json` and
binds fresh AC_PUBLIC_API and AC_MODULE_GRAPH outputs to PR #32 merge commit
`26a9bb667da7d0938e38aca15d2bf29fd1de4829`. Its source tree is not the later
commit that stores the evidence files. The canonical checkpoint test validates
the manifest, exact source/config/evaluator digests, raw diagnostic bytes, and
independent evidence readback while preserving the candidate observations.

`architecture-test` stores Import Linter's cache under `.import_linter_cache`
by default. Set `IMPORT_LINTER_CACHE_DIR` to a writable external path when
running from a restricted worktree.

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
| P03-03 | Exact-pair validity, mandatory coverage and ACCEPT/REJECT/HOLD; compliance stays UNKNOWN when evaluator identity, execution scope, mapping, or artifact integrity is unresolved, while adequacy remains separate | `p_semantic.py`, `p_governance.py`, `test_p_semantic_pairs_v1.py` (`test_unresolved_targets_do_not_become_an_architecture_violation`, `test_success_with_unknown_inspection_scope_is_not_compliant`), `test_noncompliance_and_evaluator_inadequacy_are_independent` | See complete status matrix |
| P03-04 | Candidate materialization, deterministic versioning and V1 adapters | `p_candidate.py`, `test_p_candidate_governance_v1.py` | See complete status matrix |
| P03-05 | Deterministic replay, version binding, event log and conditional rollback | `p_governance.py`, impact and governance tests | See complete status matrix |
| P03-06 | SPEC 02 reuse, V3 preflight and end-to-end method isolation | `p_adaptation.py`, `test_p_governed_adaptation_v1.py` | See complete status matrix |
| E01 | Sealed measured B0/B1/P comparison meets G1/G4 and independent oracle boundary | Later authorized protocol-run record | **Not authorized** |

The exact assertions and PASS/SKIP counts come from running the suites, never this table. The SPEC 03 report expands its 14 requirements into all 48 required rows and records which rows are blocked by absent approved positive-path inputs.

## EXP-01 DEVELOPMENT evidence pipeline

The new evidence collector is an engineering data path. Its bundle cannot establish semantic fitness coverage or measured research outcomes.

| Requirement | Expected behavior | Unit tests / fixture provenance | Status |
| --- | --- | --- | --- |
| EXP01-01 | Run IDs and target URLs are bounded to safe path components and loopback HTTP. | `test_run_id_*`, `test_runtime_url_*`; literal input cases. | Implemented; synthetic unit tests |
| EXP01-02 | Bundle schema, run identity, source revision, and artifact digests validate; corruption and cross-revision references fail. | `test_bundle_round_trips_schema_and_all_artifact_digests`, `test_bundle_detects_corrupted_artifact_digest`, `test_bundle_rejects_wrong_architecture_and_cross_revision_evidence`; local temporary artifacts. | Implemented; synthetic unit tests |
| EXP01-03 | Import Linter records actual executable/version, config digest, duration, exit status, and raw outputs; violations remain distinct from execution errors. | `test_import_linter_*`; controlled `CompletedProcess` output fixtures. | Implemented; adapter behavior mocked |
| EXP01-04 | Prometheus samples preserve business/operational labels, reject non-finite or incompatible samples, and never turn a reset into a valid rate. | `test_realistic_prometheus_samples_*`, `test_nonfinite_values_*`, `test_counter_decrease_*`; in-memory exposition fixtures. | Implemented; synthetic unit tests |
| EXP01-05 | Runtime collection records readiness, bounded read-only traffic, process sampling, histogram buckets, and explicit missing/stale evidence. | `test_runtime_source_binding_controls_bundle_and_cli_outcome`, `test_stale_snapshot_interval_*`; mocked local client and sampler plus CSV fixtures. | Implemented; adapter behavior mocked |
| EXP01-06 | Compose observations preserve actual service container counts while process and communication semantics remain NOT_OBSERVED. | `test_compose_observation_*`; controlled Docker command responses. | Implemented; adapter behavior mocked |
| EXP01-07 | Missing evaluator/runtime evidence, wrong architecture, and existing run directories cannot produce positive coverage or overwrite results. | `test_import_linter_missing_*`, `test_runtime_readiness_failure_*`, `test_missing_evaluator_*`, `test_existing_run_directory_*`. | Implemented; synthetic unit tests |
| EXP01-08 | Runtime inputs do not require private ground truth, scorer, or another method's output. | `test_runtime_inputs_do_not_include_private_or_scorer_sources`; checked-in source/config allowlist. | Implemented; source-contract test |
| EXP01-09 | Collector Git identity is separate from observed application identity; read-only Docker metadata binds the loopback endpoint to a stable container/image when available. Missing identity stays unverified, observed revision disagreement is mismatch, and no unauthenticated label can establish verified source binding. A mismatch invalidates runtime evidence, prevents a complete bundle, and gives the CLI a nonzero exit; unverified binding remains acceptable when metrics are valid. Schema 1.0 remains readable as legacy evidence without a source-binding claim. | `test_docker_target_observation_binds_published_loopback_port`, `test_runtime_missing_target_identity_stays_unverified`, `test_runtime_mismatched_target_revision_is_not_bound_to_collector`, `test_runtime_changed_target_container_is_a_mismatch`, `test_matching_oci_revision_label_does_not_verify_source_binding`, `test_missing_application_revision_label_stays_unverified_with_bound_endpoint`, `test_runtime_source_binding_controls_bundle_and_cli_outcome`, `test_bundle_rejects_available_runtime_with_mismatched_source_binding`, `test_bundle_rejects_promotion_of_unverified_runtime_binding`, `test_bundle_v1_0_remains_readable_without_source_binding`; in-memory Docker metadata fixtures. | Implemented for DEVELOPMENT; revision-bound verification unavailable without authoritative source-to-image provenance |

Run the focused suite with `uv run python -m pytest -q --no-cov -p no:cacheprovider tests/unit/test_exp01_evidence.py`. `make development-regression-test` also runs this module separately after the allowlisted regression command so hosted logs show its exact test count. The optional live path is `make exp01-smoke`; it is separate from unit tests and must be reported as blocked if Compose, the database, or a ready app is unavailable.

## EXP-02 A0.1 fitness representation evidence

The A0.1 DEVELOPMENT configuration is a manually established reference, validated by `fitness/configs/a0_1-capability-modules.dev.schema.json`. The EXP-01 runner emits bundle schema 1.2.0, adds the existing module-structure test as an evaluator record, and packages the EXP-02 adapter output. The adapter verifies exact configuration and evaluator artifact digests and keeps evaluator execution, compliance observations, scope, applicability, semantic validity, and independent coverage separate.

| Requirement | Expected behavior | Test owner | Status |
| --- | --- | --- | --- |
| EXP02-01 | A0.1 configuration validates, links catalog obligation IDs, records manual DEVELOPMENT provenance, and cannot claim P/B1 authorship. | `test_a01_fitness_configuration_validates_as_manual_development_reference`, `test_configuration_rejects_a0_identity_mismatch` | Synthetic contract tests |
| EXP02-02 | Evaluator outputs bind by run, revision, evaluator, stage, scope, configuration and raw artifact identity; all derived evidence is recomputed from the selected configuration and evaluator records, so inconsistent values fail closed even with valid updated digests. | `test_configuration_and_evaluator_artifact_digests_are_verified`, `test_conflicting_evaluator_stage_scope_or_identity_is_rejected`, `test_conflicting_source_revision_is_rejected`, `test_digest_valid_derived_evidence_tampering_is_rejected` | Synthetic contract tests |
| EXP02-03 | Existing module-structure, Import Linter, and runtime outputs map to configured representations; a functioning architecture evaluator can report noncompliance. | `test_real_evaluator_records_map_to_representation_evidence`, `test_noncompliant_architecture_result_is_not_hidden_by_execution_success` | Synthetic adapter tests; optional live smoke |
| EXP02-04 | Missing evaluator/metric, invalid evidence, scope mismatch, and unverified application identity remain explicit and cannot become positive semantic coverage. | `test_missing_evaluator_or_metric_remains_explicit`, `test_invalid_or_stale_runtime_record_never_yields_available_metrics`, `test_unverified_application_identity_is_preserved_as_unknown` | Synthetic adapter tests |
| EXP02-05 | EXP-01 bundle schema 1.0/1.1 remains readable; v1.2 links its versioned representation-evidence artifact. | `test_legacy_exp01_schema_versions_1_0_and_1_1_remain_readable`, `test_real_evaluator_records_map_to_representation_evidence` | Schema/contract tests |
| EXP02-06 | Method inputs remain isolated from oracle/scorer sources; `Coverage_P` and `Coverage_ref` remain unclaimed. | `test_exp02_inputs_remain_isolated_from_oracle_and_scorer_sources`, `test_representation_schema_rejects_unearned_coverage_claim` | Source/negative tests |

Run the focused suite with `uv run python -m pytest -q --no-cov -p no:cacheprovider tests/unit/test_exp02_fitness_evidence.py`. `make development-quality` runs it in the hosted `development-quality` job through `development-regression-test`. The optional isolated DEVELOPMENT smoke is `COMPOSE_PROJECT_NAME=evofit-exp02-smoke make exp01-smoke`; it uses the explicit `fitness/configs/a0_1-capability-modules.dev.yaml` selection. Runtime application source binding remains unverified without authoritative source-to-image provenance.

## EXP-03 EXP-02 to existing Method P integration

EXP-03 validates an existing EXP-01 v1.2 bundle and its recomputed EXP-02
representation evidence, then preserves the original evaluator and input
artifact references in a versioned integration manifest. When an explicit V3
bundle is supplied, the bridge uses `verify_v3_p_bundle()` followed by
`run_adaptation()` with an empty evidence ledger and no adaptation evidence
sidecar. EXP-02 evidence is validated and mapped for diagnostics but is not
admitted to P calculations; the output names this boundary explicitly. The
checked-in DRAFT/OPEN policy-pilot source is sufficient to
exercise that path, but it correctly leaves policy authority and applicability
unresolved and cannot produce an ACCEPT.

| Requirement | Expected behavior | Test owner | Status |
| --- | --- | --- | --- |
| EXP03-01 | Validate EXP-01/02 artifacts, revalidate referenced source artifacts on readback, and preserve run, configuration, source revision, evaluator IDs and original digests without claiming semantic validation. | `test_original_evaluator_artifact_references_survive_unchanged`, `test_digest_valid_source_reference_mismatch_fails_contract_revalidation`; digest-valid EXP-02 fixtures. | Implemented; integration contract tests |
| EXP03-02 | Translate only explicit `ci_test → ci` and `runtime → runtime` stages; unsupported stages and unrepresented scopes stay ineligible. | `test_unsupported_stage_and_unrepresented_scope_fail_closed`; actual V3 representation catalog. | Implemented; integration negative test |
| EXP03-03 | Keep missing evaluator/metric, invalid evidence, and unverified runtime identity unresolved. | `test_missing_evaluator_or_metric_remains_unresolved`, `test_modified_representation_evidence_is_rejected`, `test_unverified_runtime_identity_never_becomes_semantic_pair_proof`. | Implemented; integration negative tests |
| EXP03-04 | Keep evaluator execution and observed compliance separate, including actual noncompliance. | `test_actual_evaluator_noncompliance_is_separate_from_pair_validity`. | Implemented; integration test |
| EXP03-05 | Block incompatible V3 after revisions and reject contradictory source/evaluator/canonical-pair bindings. | `test_incompatible_architecture_revision_blocks_method_p_execution`, `test_conflicting_source_revision_is_rejected_before_packaging`, `test_contradictory_evaluator_binding_is_rejected`, `test_duplicate_canonical_pair_binding_is_rejected`. | Implemented; integration negative tests |
| EXP03-06 | Execute the existing verified V3 Method P pipeline for the supported A0→A0.1 delta; no EXP-02 observation becomes pair proof or enters P calculations. | `test_real_exp02_run_executes_existing_p_pipeline_and_preserves_hold`, `test_missing_policy_authority_and_exact_pair_proof_produce_unknown_hold`, `test_exp02_observation_changes_do_not_change_method_p_governance`. | Implemented; actual verifier/adaptation path, DRAFT/OPEN policy source; evidence-consumption limitation explicit |
| EXP03-07 | Keep `Coverage_P`, `Coverage_ref`, and measured DA01 prediction unclaimed; require no oracle/scorer artifact. | `test_integration_does_not_emit_measured_da01_prediction`, `test_no_private_oracle_or_scorer_artifacts_are_required`. | Implemented; integration boundary tests |
| EXP03-08 | Read back generated artifacts, revalidate referenced inputs, cross-check manifest-derived fields against the exact P trace, and report absent V3 input explicitly. Digest-valid inconsistencies fail closed. | `test_complete_integration_artifact_round_trips_and_checks_digests`, `test_digest_valid_cross_artifact_mismatches_fail_closed`, `test_no_v3_input_is_reported_as_an_explicit_blocker`. | Implemented; integration artifact tests |
| EXP03-09 | Keep existing TEST_ONLY positive V3 scenarios unchanged and covered by hosted DEVELOPMENT regression. | Existing `test_v3_synthetic_noop_accepts_with_independent_before_after_closure_claims` and `test_v3_synthetic_add_uses_authorized_descriptor_and_accepts_with_scoped_closure_claims` in `test_p_applicability_v3.py`. | Existing TEST_ONLY tests; run separately from real-evidence HOLD path |
| EXP03-10 | Report EXP-02 contract validation, mapping, V3 verification, P execution, and P evidence admission as separate states; `completed_with_hold` does not imply evidence-driven adaptation. | `test_real_exp02_run_executes_existing_p_pipeline_and_preserves_hold`, `test_exp02_observation_changes_do_not_change_method_p_governance`. | Implemented; admission remains `not_admitted` by design |

Prepare any V3 input through the existing `package_policy_source_v3()` and
`export_method_inputs_v3()` APIs. Pass the policy source, before/after source
revisions, and registry `as_of` explicitly. The method input directory must
be outside the repository and must not be discovered from protected materials.
Then run the bridge into a unique output directory:

```bash
uv run python -m scripts.exp03_method_bridge \
  --exp02-run-dir experiments/results/<exp02-run-id> \
  --p-input-dir /private/tmp/<prepared-v3-method-input> \
  --output-dir experiments/results/<unique-exp03-run-id>
```

If no P input is supplied, EXP-03 writes the validated EXP-02 linkage and a
machine-readable `P_V3_INPUT_REQUIRED` blocker. The manifest also reports
`EXP02_EVIDENCE_NOT_ADMITTED_TO_METHOD_P` because EXP-02 observations are not
supplied to `run_adaptation()`. A verified V3 input produces a trace with
before/after revisions, impact, pair and coverage assessments, operation
plan, governance decision, and unresolved prerequisites. A
`completed_with_hold` status reports the existing P decision only; it does
not mean that EXP-02 evidence drove adaptation. Readback reruns source
validators and the V3 verifier, so those referenced input directories must
remain available.
See [`experiments/execution/EXP03_METHOD_INTEGRATION.md`](../experiments/execution/EXP03_METHOD_INTEGRATION.md)
for the command contract and interpretation.

Run the focused suite with `uv run python -m pytest -q --no-cov -p no:cacheprovider tests/integration/test_exp03_method_bridge.py`. `make development-quality` includes it in the hosted `development-quality` job and also runs existing TEST_ONLY V3 positive scenarios. EXP-03 does not alter `P_ALGORITHM_STATUS=NOT_READY`, G1/G4, frozen A0/DA01 files, or measured-run authorization.

## EXP-04 verified EXP-02 evidence admission

EXP-04 adds a versioned admission manifest and trace around the existing
EXP-03/V3 boundary. It validates original EXP-02 artifacts, then requires
exact representation, obligation, intent, evaluator, metric/unit, lifecycle,
revision, scope, source-artifact, and metric-observation-contract bindings.
The current A0 V3 representation catalog does not provide those A0.1
bindings, so the checked-in path reports `mapping_unresolved`. A verifier
signature and a digest-valid artifact are distinct: only the existing V3
adaptation-evidence registry can verify a sidecar, and this EXP-04 CLI's
external key-file adapter is restricted to `TEST_ONLY`. No local config can
declare production authority.

The manifest preserves the verified EXP-02 execution verdict and compliance
observation separately from P's pair validity. A signed observation may enter
P only when exact bindings and existing V3 verifier checks succeed. It never
acts as pair semantic proof; positive pair proof remains subject to separate
G1/G4 authorization. Readback revalidates EXP-01/02 and V3 input references,
verifier scope, the signed sidecar, generated trace, per-pair consumption,
and output digests. The run never asserts `Coverage_P` or `Coverage_ref`,
emits a prediction, or changes `P_ALGORITHM_STATUS=NOT_READY`.

| Requirement | Expected behavior | Test owner | Status |
| --- | --- | --- | --- |
| EXP04-01 | Preserve source run, evaluator/config/raw-output digests, metric values, execution verdict, and the EXP-02 compliance observation. | `test_validated_observation_keeps_provenance_and_separates_compliance` | Implemented; digest-valid EXP-02 fixtures |
| EXP04-02 | Keep conforming and nonconforming observations distinct while exact P mappings remain unresolved and P evidence consumption stays false. | `test_validated_observation_keeps_provenance_and_separates_compliance` | Implemented; fixture observations |
| EXP04-03 | Reject revision, evaluator, scope, stage, criterion intent, metric/unit, source artifact, and observation-contract mismatches. | `test_architecture_revision_mismatch_stays_unresolved`, `test_strict_mapping_rejects_individual_identity_mismatches` | Implemented; adversarial mappings |
| EXP04-04 | Preserve unverified runtime application identity as an admission blocker. | `test_runtime_source_identity_must_be_verified` | Implemented; changed binding fixture |
| EXP04-05 | Missing verifier authority stays unavailable; an invalid signature is rejected through the existing V3 verifier; the file adapter is digest-pinned and TEST_ONLY. | `test_missing_or_invalid_external_verifier_never_consumes_sidecar`, `test_cli_verifier_configuration_is_pinned_and_test_only` | Implemented; TEST_ONLY V3 verifier fixture |
| EXP04-06 | Verified evaluator execution without exact-pair semantic proof remains UNKNOWN/HOLD. | `test_test_only_verified_evaluator_execution_without_pair_proof_is_not_valid` | Implemented; separately authored TEST_ONLY evidence |
| EXP04-07 | An externally supplied TEST_ONLY observation enters the existing V3 calculation only after V3 verification; compliance and adequacy remain separate, and TEST_ONLY is never research authority. | `test_test_only_verified_evaluator_execution_without_pair_proof_is_not_valid`, `test_noncompliance_and_evaluator_inadequacy_are_independent` | Implemented; synthetic verification and pair fixtures |
| EXP04-08 | Digest-valid but contradictory admission statuses fail readback. | `test_digest_valid_contradictory_admission_manifest_fails_readback` | Implemented; resealed negative artifact |
| EXP04-09 | Never assert positive `Coverage_ref`, measured DA01 prediction, or unauthorized ACCEPT from EXP-04. | `test_validated_observation_keeps_provenance_and_separates_compliance` | Implemented; DEVELOPMENT boundary |
| EXP04-10 | Preserve the existing TEST_ONLY positive V3 path without turning it into production authority. | `test_existing_test_only_positive_p_path_remains_available` and existing V3 suite | Implemented; TEST_ONLY only |
| EXP04-11 | Separate mapping eligibility, sidecar execution authorization and actual P consumption; an authorized row is admitted only after its exact current pair consumes the verified sidecar evidence digest. | `test_test_only_sidecar_admission_tracks_actual_pair_consumption[authorized-but-unconsumed]`, `test_test_only_sidecar_admission_tracks_actual_pair_consumption[exact-pair-consumed]` | Implemented; isolated TEST_ONLY DEVELOPMENT fixtures, no pair proof |
| EXP04-12 | Trace aggregate, per-representation consumption and overall completion states agree with exact verified sidecar pairs, P execution and required blockers. | `test_test_only_sidecar_admission_tracks_actual_pair_consumption`, `test_digest_valid_contradictory_admission_manifest_fails_readback`, `test_resealed_completed_status_with_blockers_is_rejected` | Implemented; readback re-derivation |
| EXP04-13 | Readback applies construction-time bans on ACCEPT, measured prediction and candidate publication even after manifest and trace digests are recomputed. | `test_resealed_accept_in_manifest_and_trace_is_rejected`, `test_resealed_prediction_and_candidate_publication_are_rejected` | Implemented; cross-file resealed rejection |
| EXP04-14 | Evidence-consumption claims require a verified authorized sidecar and a matching exact P pair; digest resealing cannot create either. | `test_resealed_evidence_consumption_claim_without_sidecar_is_rejected` | Implemented; cross-file resealed rejection |

Run the focused suite with:

```bash
uv run python -m pytest -q --no-cov -p no:cacheprovider tests/integration/test_exp04_evidence_admission.py
```

`make development-quality` includes this suite in hosted DEVELOPMENT CI.
The local result artifacts described in the EXP-04 operational guide are
separate DEVELOPMENT observations and do not establish scientific readiness.
See
[`experiments/execution/EXP04_EVIDENCE_ADMISSION.md`](../experiments/execution/EXP04_EVIDENCE_ADMISSION.md)
for explicit invocation, output validation, and the present A0-to-V3 binding
blockers.

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

## SPEC 03 completion/readiness follow-up

The current S03R-01…12 test mapping, exact synthetic fixture hashes, per-row
PASS/BLOCKED outcomes, Docker image ID, and the explanation for the unchanged
G1/G4 gates are recorded in
[`SPEC_03_IMPLEMENTATION_TRACEABILITY.md`](SPEC_03_IMPLEMENTATION_TRACEABILITY.md).
The exact descriptor-authority, sidecar-replay, four missing-proof HOLD,
synthetic V3 no-op/ADD, and G1-register test cases are in that matrix.

Use these safe local commands for the DEVELOPMENT regressions. The interpreter
and `PYTHONPATH` below are specific to the managed macOS workspace; adapt them
to the installed project environment when reproducing elsewhere.

```bash
PYTHONPATH='.venv/lib/python3.12/site-packages' /Users/oleksii_makieiev/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest -q --no-cov -p no:cacheprovider tests/unit/test_p_operations_v1.py tests/unit/test_p_adaptation_evidence_v1.py tests/unit/test_g1_method_decision_register.py tests/integration/test_p_applicability_v3.py tests/integration/test_p_governed_adaptation_v1.py
PYTHONPATH='.venv/lib/python3.12/site-packages' /Users/oleksii_makieiev/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest -q --no-cov -p no:cacheprovider --ignore=tests/unit/test_da01_execution.py --ignore=tests/unit/test_research_schema_foundation.py tests/unit tests/architecture
.venv/bin/ruff check .
.venv/bin/ruff format --check .
PYTHONPATH='.venv/lib/python3.12/site-packages' MYPY_CACHE_DIR=/private/tmp/evofit-spec03-mypy-cache /Users/oleksii_makieiev/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m mypy app scripts tests
PYTHONPATH='.venv/lib/python3.12/site-packages' /Users/oleksii_makieiev/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m bandit -q -r app scripts experiments/execution/tooling
# Set TEST_DATABASE_URL to a disposable PostgreSQL database whose name contains "evofit".
PYTHONPATH='.venv/lib/python3.12/site-packages' /Users/oleksii_makieiev/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m scripts.validate_migrations
git diff --check
```

The following earlier results describe the pre-review-fix PR #10 implementation.
The current review-fix outcome is recorded below. Earlier outcomes remain in
place as historical evidence.

Pre-review-fix local results: focused SPEC 03 regressions **42
passed** (one existing Starlette/httpx deprecation warning); unit and
architecture suites **213 passed** (one existing Locust monkey-patch warning,
zero skips); Ruff check and format **PASS** (220 files formatted); Mypy **PASS**
(96 files); Bandit **PASS** (existing comment-parser and `nosec` warnings); and
`git diff --check` **PASS**. The Docker probe ran against local image ID
`sha256:5a2dc0c42e8ef06560a3d61c077b66c8ee66f0f3fba7252fec1a5af34e234f27` and
passed without a skip. Migration validation passed on a temporary PostgreSQL
16 database named `evofit_spec03_test`; the container was stopped and removed
afterward.

For SPEC 03 DEVELOPMENT changes, use `make development-quality` with a
**disposable** PostgreSQL database. The target runs explicit SPEC 01/02/03 and
S03R regressions, the synthetic Docker isolation probe, static/security/
architecture checks, and migrations. It excludes
`tests/unit/test_da01_execution.py` and
`tests/unit/test_research_schema_foundation.py` from Ruff check/format, Mypy,
and pytest discovery. The default `make quality` still includes the broader
test suite and must not be used for this protected work. These engineering
checks do not change G1/G4 readiness, and no measured DA01 run is part of this
DEVELOPMENT scope.

The reproducible safe command is:

```bash
TEST_DATABASE_URL=postgresql+psycopg://evofit:evofit@localhost:5432/evofit_test make development-quality
```

The database must be disposable and its database name must contain `evofit`.
GitHub Actions supplies a temporary PostgreSQL 16 service and runs this same
Make target on push and pull request events.

### PR #10 review-fix verification

On 2026-10-16, the full safe target passed locally with a temporary PostgreSQL
16 container and the synthetic Docker isolation probe enabled. The host had no
`uv` executable, so a temporary wrapper delegated the Make target's `uv run`
commands to the project's installed Python 3.12 tool environment. The wrapper
and database container were removed/stopped after the run.

| Check | Result |
| --- | --- |
| Ruff check | PASS — all checks passed; protected test modules excluded |
| Ruff format | PASS — 219 Python files checked; protected modules excluded |
| Mypy | PASS — 94 source files; protected modules excluded |
| Bandit | PASS — existing comment-parser and `nosec` warnings only |
| Architecture import rules | PASS — 5 contracts kept, 0 broken |
| Architecture tests | PASS — 6 passed |
| Disposable PostgreSQL migration validation | PASS — PostgreSQL 16, `0001_a0_schema` |
| Safe SPEC 01/02/03 and S03R regressions, including Docker isolation probe | PASS — 201 passed, one existing Starlette/httpx deprecation warning, 0 skipped |
| `git diff --check` | PASS |

The target explicitly excludes `tests/unit/test_da01_execution.py` and
`tests/unit/test_research_schema_foundation.py` from test, lint, formatting,
and type-check discovery. Neither protected module was opened, executed,
modified, linted, formatted, or type-checked in this run.
The exact current-head GitHub Actions URLs and conclusions are recorded in the
existing [PR #10 description](https://github.com/Pan14ek/evofit-bench/pull/10).

### PILOT-01 evidence and result export

PILOT-01 is a DEVELOPMENT pilot of existing architecture-evaluator behavior. It
uses isolated S0/S1 source revisions and preserves raw run outputs under the
ignored `experiments/results/` tree. Rebuild the CSV only after the generator
validates each manifest inventory and the EXP-01/EXP-02 evidence:

```bash
uv run python -m experiments.pilots.generate_pilot01_results
uv run python -m pytest -q --no-cov -p no:cacheprovider tests/unit/test_pilot01_results.py
```

| Requirement | Evidence / test |
| --- | --- |
| PILOT01-R1: use Locust's recorded aggregate values without recalculating percentiles | `test_locust_aggregate_reads_saved_statistics` |
| PILOT01-R2: detect post-collection raw-artifact mutation by size or digest | `test_artifact_inventory_rejects_changed_bytes`; result generator revalidates all six run inventories and EXP-01/02 bundles |
| PILOT01-R3: label three technical repeats descriptively, without inferential statistics | `test_statistics_label_repetitions_as_non_inferential` |

The pilot records one independent source intervention. Its results do not establish
`Coverage_P`, `Coverage_ref`, G1/G4, Method P readiness, or measured DA01
outcomes. The isolated S1 source fault is not part of the normal implementation
branch.

### PILOT-02 TEST_ONLY runner

The bounded runner uses the existing V3 P input verifier and `run_adaptation()` path. A TEST_ONLY sidecar can supply execution observations to adaptation calculations, while exact-pair semantic proof and research authority remain separate.

| Requirement | Expected behavior | Test owner | Status |
| --- | --- | --- | --- |
| PILOT02-DEV-01 | Report admitted execution evidence only when a sidecar is supplied and Method P verifies TEST_ONLY trust scope; do not label execution observations as semantic pair proof. | `test_execution_evidence_admission_trace_matches_verified_sidecar_scope`, `test_real_exp02_run_executes_existing_p_pipeline_and_preserves_hold` | Implemented; TEST_ONLY runner and bridge fixtures |
| PILOT02-DEV-02 | Execute candidate-profile evaluators only when the materialized row and all pinned identity, artifact, revision, scope, stage, coverage, and evidence-contract bindings match; mismatches stay not measured. | `tests/unit/test_pilot02_candidate_evaluators.py` | Implemented; positive scoped execution and adversarial mismatches |
| PILOT02-DEV-03 | Verify inherited parent evaluator artifact bytes against the exact parent catalog and attach them only to a detached materialized candidate; preserve the parent bytes. | `tests/unit/test_pilot02_method_input_profile.py`, `tests/unit/test_p_candidate_governance_v1.py` | Implemented; positive and negative binding checks |
| PILOT02-DEV-04 | Record each fresh inherited evaluator execution with exact source and configuration hashes, command, timestamps, metric units/status, raw stream digests, database-container identity, and per-run evaluator inventory; reject source path or digest mismatches and tampered raw output. | `test_inherited_evaluator_result_binds_source_config_and_raw_streams`, `test_inherited_evaluator_source_reference_rejects_digest_and_path_mismatch`, `test_inherited_evaluator_readback_rejects_tampered_raw_output`, `test_inherited_evaluator_database_container_uses_published_host_port` | Implemented; focused runner-record checks; real execution recorded separately |
| PILOT02-SEM-01 | Establish exact-pair semantic evidence only after actual pinned clean/negative evaluator controls, non-vacuous typed scope, source mutation reconstruction, and exact representation/obligation/source/evaluator binding. | `tests/integration/test_pilot02_semantic_validation.py::test_real_controls_establish_two_testonly_semantic_pairs` | Live TEST_ONLY evaluator control integration; no DA01 authority or coverage claim |
| PILOT02-SEM-02 | Reject digest-resealed scope, identity, source-revision, raw-stream, or negative-control tampering; do not reuse proof after a candidate-row change or admit unsigned evidence. | `tests/integration/test_pilot02_semantic_validation.py::test_readback_rejects_digest_resealed_adversarial_evidence`, `test_pilot02_testonly_execution.py::test_semantic_proof_is_not_reusable_after_candidate_row_changes`, `test_p_adaptation_evidence_v1.py::test_v2_sidecar_rejects_unsigned_proof_payload`, `test_p_semantic_pairs_v1.py::test_representation_proof_cannot_be_reused_for_a_different_representation` | Positive and adversarial controls; noncompliance remains separate from pair validity |
| PILOT02-SEM-03 | Admit a semantic proof only when the exact pinned candidate template is present in the verified template catalog; a new ADD/REPLACE row need not already exist in the parent representation catalog, while conflicting parent rows remain unresolved and candidate-row equality is rechecked from the measured candidate evaluator records after materialization. | `tests/unit/test_pilot02_testonly_execution.py::test_prevalidated_new_candidate_template_does_not_need_parent_catalog_row`, `test_prevalidated_template_binding_rejects_missing_or_conflicting_template`, `test_candidate_evaluator_representation_records_are_used_for_proof_readback`, `test_semantic_proof_is_not_reusable_after_candidate_row_changes` | TEST_ONLY proof handoff and post-materialization exact-row check |

Run the real semantic controls and adversarial readback checks with:

```bash
uv run python -m pytest -q --no-cov -p no:cacheprovider tests/integration/test_pilot02_semantic_validation.py
```

The test invokes pinned Grimp/Import Linter and pytest evaluators in disposable
source copies. The preserved experiment archive is generated separately by
`python -m experiments.pilots.pilot02_semantic_validation`; test executions are
engineering verification, not independent architecture-transition samples.

### B0/P E1 evidence-sufficient calibration

The E1 envelope is separate from the legacy B0/P continuation and uses the
same frozen B0 and P runtimes. The following traceability rows map its core
requirements to focused adversarial checks:

| Requirement | Expected behavior | Test owner | Status |
| --- | --- | --- | --- |
| B0P-E1-01 | Bind the P input, extracted architecture facts, and TEST_ONLY sidecar to exact source SHAs and one run-specific policy revision. | `test_git_fact_verifier_recomputes_each_reported_inventory_field`, `test_e1_sidecar_requires_signature_digest_source_and_exact_run_binding`, `test_pinned_git_inventory_recomputes_all_four_fields`, `test_a_tampered_observation_is_not_admitted` | Unit and Git-object adversarial checks |
| B0P-E1-02 | Reject missing/invalid signatures, another run's sidecar, wrong policy/source/bundle binding, and oracle, scorer, Git-history, or other-arm files in P input. | `test_e1_sidecar_requires_signature_digest_source_and_exact_run_binding`, `test_oracle_contamination_and_historical_overwrite_are_rejected`, `test_oracle_git_and_scorer_paths_are_forbidden_method_inputs` | Unit and isolation contract checks |
| B0P-E1-03 | Reject missing/vacuous evaluator scope and source/configuration/run mismatches; do not infer compliance from exit zero alone. | `test_import_linter_scope_mismatch_is_not_evaluable_even_on_exit_zero`, `test_reused_evaluator_record_from_another_run_is_rejected`, `test_evaluator_rejects_wrong_source_revision_and_configuration`, `test_readback_rejects_digest_resealed_adversarial_evidence` | Unit and TEST_ONLY readback checks |
| B0P-E1-04 | Keep the author-declared calibration reference outside method mounts; do not call the canonical RQ1 scorer or manufacture a prediction after P abstains. | `test_hold_cannot_invoke_canonical_rq1_or_emit_score`, `test_rq1_scorer_requires_a_reference_established_before_predictions`, `test_prediction_must_bind_method_architecture_and_bundle` | Unit contract checks; real mount command is recorded per run |
| B0P-E1-05 | Bind the full six-obligation denominator; preserve per-obligation UNKNOWN and no percentage when evidence is incomplete. | `test_rq2_requires_exact_complete_denominator_and_never_fabricates_percent`, `test_unknown_rq2_cannot_claim_shared_or_bound_denominator`, `test_rq2_cannot_score_method_pair_diagnostics_as_independent_proof` | Unit/schema checks; complete measurement requires a real E1 run |
| B0P-E1-06 | Keep a structurally valid candidate separate from governance ACCEPT; HOLD has no accepted coverage. | `test_candidate_potential_is_diagnostic_when_governance_holds`, `test_p_hold_requires_matching_no_prediction_marker`, `test_prevalidated_template_binding_rejects_missing_or_conflicting_template` | Unit and TEST_ONLY checks |
| B0P-E1-07 | Preserve write-once history, reject post-seal mutation, and verify ZIP/checksum readback after clean extraction. | `test_oracle_contamination_and_historical_overwrite_are_rejected`, `test_sealed_prediction_tampering_is_rejected`, `test_run_inventory_leaves_nested_checksum_manifests_to_their_scope` | Unit checks plus per-run archive readback |
| B0P-E1-08 | Revalidate copied semantic evidence from a regular run-contained directory; reject path traversal and non-directory substitutions. | `test_e1_semantic_pair_readback_requires_run_contained_directory` | Focused unit and E1 clean-extraction readback |

Run the E1-focused suite with:

```bash
uv run python -m pytest -q --no-cov -p no:cacheprovider \
  tests/unit/test_b0p_e1_execution.py \
  tests/unit/test_b0p_execution.py \
  tests/unit/test_b0p_git_inventory.py \
  tests/unit/test_pilot02_testonly_execution.py
```

These tests verify contracts and known adversarial inputs. They do not
substitute for running both isolated arms, fresh evaluators, current-run
semantic readback, or the post-run archive verification.

### MONO-E1/E2 custody and scoring preparation

MONO-A1 is a separate monograph-study namespace. The focused tests use synthetic
Git-bound fixtures and a synthetic exact-pair verifier adapter; they do not
represent MONO-E1/E2 measurements or W2 evaluator evidence.

| Requirement | Expected behavior | Test owner | Status |
| --- | --- | --- | --- |
| MONO-A1-01 | Reference source commit/tree SHAs verify against Git; canonical reference and seal are write-once; missing, forged, or changed seal bytes fail closed. | `test_reference_freeze_is_source_pinned_and_precedes_method_execution`, `test_freeze_rejects_incorrect_source_tree_sha`, `test_reference_readback_rejects_missing_or_forged_seal`, `test_reference_is_write_once_and_post_seal_mutation_is_detected` | Synthetic contract checks |
| MONO-A1-02 | The RQ2 denominator matches all active mandatory obligations; unknown mandatory applicability remains unresolved and suppresses percentages. | `test_rq2_rejects_a_wrong_denominator_and_keeps_unknown_applicability`, `test_rq2_uses_one_full_denominator_and_separates_three_coverage_views` | Synthetic scorer checks |
| MONO-A1-03 | Reference labels, oracle/scorer paths, symlinks, cross-arm material, and cross-run or duplicate exact-pair evidence are rejected. | `test_reference_labels_cannot_enter_method_input`, `test_exact_pair_rejects_cross_run_evidence_reuse`, `test_rq2_rejects_duplicate_exact_pair_rows` | Adversarial synthetic checks |
| MONO-A1-04 | RQ1 uses only both authentic sealed predictions after reference freeze; P HOLD without a prediction is NOT_EVALUABLE and cannot invoke the scorer. | `test_rq1_scores_only_sealed_predictions_and_reports_operation_confusion`, `test_p_hold_without_prediction_preserves_rq1_not_evaluable`, `test_study_gate_rejects_scoring_when_p_hold_has_no_prediction` | Synthetic seal/scorer checks |
| MONO-A1-05 | TEST_ONLY proofs stay diagnostic and do not become governance-accepted coverage; accepted coverage remains separate from candidate potential. | `test_rq2_keeps_governance_acceptance_separate_from_test_only_proof` | Synthetic verifier adapter only; no production trust anchor |
| MONO-A1-06 | Missing timers, invalid source-to-image bindings, and uncollected resources remain UNKNOWN rather than fabricated values. | `test_incomplete_runtime_metrics_and_invalid_image_binding_remain_unknown` | Synthetic precondition checks; attestation authentication remains external |
| MONO-A1-07 | Evidence inventory/archive checksums survive clean extraction and detect archive mutation. | `test_evidence_archive_integrity_and_clean_extraction_readback` | Synthetic archive readback |
| MONO-A1-08 | W2 evidence binds evaluator version, architecture state/source, complete inspected paths, and exact raw bytes; a pinned W2 checkout's `verify_evidence()` must pass. | `test_w2_readback_binds_the_pinned_evaluator_state_and_source` | Synthetic W2-shaped fixture only; no actual W2 report admitted |
| MONO-A1-09 | E2 references reject an A0.1 predecessor, incorrect A0 commit, or non-A1 final state; missing or unavailable final A1 commit/tree identities cannot be sealed. | `test_mono_e2_schema_rejects_a0_1_predecessor`, `test_mono_e2_schema_rejects_incorrect_a0_commit_sha`, `test_mono_e2_schema_rejects_incorrect_final_architecture_state`, `test_mono_e2_reference_cannot_be_sealed_without_real_final_a1_identities` | Synthetic schema and Git-object custody checks; no final A1 source or MONO run is represented |

Run the focused suite with:

```bash
PATH=/private/tmp/b0p-venv/bin:$PATH PYTHONPATH="$PWD" \
  pytest -q tests/unit/test_mono_a1.py
```

`W2A1ExactPairReadbackVerifier` consumes the report contract from Draft PR #28
and invokes `verify_evidence()` from the exact pinned W2 checkout. This suite
uses a synthetic W2-shaped source tree and report only; it does not validate
authentic W2 output or establish MONO-E1/E2 results.
