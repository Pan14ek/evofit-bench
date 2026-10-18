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

