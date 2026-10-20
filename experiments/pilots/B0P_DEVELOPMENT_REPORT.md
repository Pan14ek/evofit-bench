# B0 vs Method P Comparative DEVELOPMENT Report

**Study:** `DEV-B0P-V1`
**Primary direct execution:** `dev-b0p-20261020-execution-a04`
**Preparation:** `dev-b0p-20261020-preflight-a01`
**Classification:** `CALIBRATION_EXPOSED`
**Record date:** 2026-10-20

## Purpose and scope

This report records a fresh direct execution of unchanged B0 and frozen Method P
on the previously exposed A0→A0.1 transition. The run is DEVELOPMENT evidence
only. It is not a holdout, independent validation, authorized measured DA01
result, or evidence of generalized P superiority. The scorer was not invoked.

The preparation package was verified before execution: all 217 entries in its
SHA-256 inventory passed, and the preparation verifier returned
`PREPARED_NOT_EXECUTED`. The preparation manifest SHA-256 is
`d6d55437fcc30c4e8bdd5acb37fd9f881be74f646989e701b03092ba8ac82b2f`.

## Aggregation defect and regression

The earlier `a02` run executed both method containers and initial evaluators,
then failed while building the in-memory manifest with
`KeyError: 'candidate_validation'`. The persisted B0 execution trace and P
execution result contained the field, but the direct arm-result mappings did
not preserve it for manifest construction. The append-only `a02` finalizer
reconstructed those values from persisted outputs, reused both method
invocations, reran the evaluator commands, and retained the original failure.

The current `_run_isolated_arm()` implementation carries B0 validation from
its persisted execution trace and P validation from its persisted execution
result into the mappings consumed by `_make_execution_manifest()`. The new
regression test exercises both isolated-arm readbacks and calls the manifest
builder, asserting B0 `VALID` and P `INVALID`; dropping either field again
reproduces the original failure. No method, scorer, governance, or scientific
decision logic was changed.

## Frozen identities and isolation

| Input | Identity |
|---|---|
| Before architecture | `b78b0967be937634b7762baccf5ac6892b279a73` |
| After architecture | `3fdd5c68f8f60fad5757eefa66cc2aa8b24d9306` |
| B0 source and policy-source revision | `165a7d6ef31adbe8ce3abe9f72e59d74692c987e` |
| Frozen Method P source | `984f75b11b3153c52275e223ce8ec23b8d0dd0e5` |
| B0 input bundle SHA-256 | `62ce5f223715a35a407e58c92c45355ddd31708de192a0479e1afeb2f133b628` |
| P input bundle SHA-256 | `b39899ade3ac7330362e0bd4d986b19e8d0112101cdd2dda24dc5355ab2ec11f` |
| B0 frozen configuration SHA-256 | `5ad60e373463ea459e192bf85d82704ca9aa1c217c4abf4d8caeb66924059ecb` |
| Import Linter configuration SHA-256 | `88ff64a4792c6048a6ab0686ddf9326ebbee49f76996933845a6142cc1a2ba27` |

B0 and P ran once in separate offline containers with read-only roots. Method
inputs excluded Git history, scorer material, ground truth, and
expected-operation labels. Runtime image IDs and input digests are recorded in
the execution manifest.

## Direct execution

Exact command (with the verified development environment and cache wrapper):

```bash
UV_PROJECT_ENVIRONMENT=/private/tmp/b0p-venv UV_CACHE_DIR=/private/tmp/b0p-uv-cache \
/private/tmp/b0p-venv/bin/python -m scripts.run_b0p_development_execution \
  --preparation-directory experiments/results/dev-b0p-20261020-preflight-a01 \
  --run-id dev-b0p-20261020-execution-a04 \
  --uv /private/tmp/b0p-uv-cache-wrapper
```

The manifest records `execution_mode.kind=DIRECT`,
`source_attempt_run_id=null`, and
`method_invocations_reused=false`. No recovery/finalization procedure was
used. The run is `EXECUTED_PARTIAL`: both methods ran and the evaluators
completed, while one evaluator could not assess its configured target.

| Observation | B0 | Frozen Method P |
|---|---|---|
| Arm status | Completed | Completed |
| Candidate validation | `VALID` | `INVALID` |
| Method version | `B0_UNCHANGED_V1` | `P_GOVERNED_ADAPTATION_DEVELOPMENT_V1` |
| Prediction | Sealed, SHA-256 `124a2495b5217d1686c9ddae631980c1c314654e8b12a9c48d4fc949deef9b34` | Not emitted; authentic `NOT_EMITTED_GOVERNANCE_HOLD` marker, SHA-256 `2a823976c09789216244f2592f8f58e1109a2ae47646d0428627dc7fbb28e7ce` |
| Governance | Not applicable | `HOLD` |
| Method time | `70,372,750 ns` | `410,543,750 ns` |
| Adaptation time | `0 ns` | `179,001,708 ns` |
| Runtime image | `sha256:540f18d1c50961fc7e19b819fd1d2b6e0c9b75bcc2cbf59845641df87d79442f` | `sha256:03fd10c8f4e0eabe51a4089458af66751156125671b717c5dccf60c2022bc5d1` |

P's recorded HOLD reasons are `APPLICABILITY_UNKNOWN`,
`CANDIDATE_NOT_POSITIVELY_VALIDATED`, `COST_MODEL_UNRESOLVED`,
`COST_VERDICT_UNRESOLVED`, `INPUT_AUTHORITY_OR_COMPLETENESS_UNRESOLVED`,
`INVARIANT_VERDICTS_NOT_ALL_POSITIVE`,
`MANDATORY_APPLICABILITY_UNKNOWN`,
`MANDATORY_CLASSIFICATION_UNRESOLVED`,
`UNKNOWN_MANDATORY_LINK_PREVENTS_TRANSITION`, and
`VERIFIED_GOVERNANCE_PIPELINE_PROOF_MISSING`. P's operation plan was empty.
The policy material remains DRAFT/OPEN without production authority.

## Fresh evaluators

| Evaluator | Exit | Evidence validity | Compliance | Semantic adequacy | Interpretation |
|---|---:|---|---|---|---|
| Frozen B0 Import Linter | 1 | `VALID` | `NOT_EVALUABLE` | `UNKNOWN` | Configured `app.repositories` target is absent from A0.1; this is not a confirmed violation. |
| `tests/architecture` | 0 | `VALID` | `COMPLIANT` at suite/process level | `UNKNOWN` | 6/6 tests passed; this does not establish exact-pair semantics. |

Evaluator duration was `521,890,584 ns`; recorded evidence-verification
overhead was `1,858,458 ns`. Timer boundaries differ and no controlled
performance comparison is supported. CPU and peak RSS remain `UNKNOWN`.

## Research endpoints and limitations

- RQ1 is `NOT_EVALUABLE`: no exact-target reference was sealed before
  predictions; the scorer was not run. TP/FP/FN/TN, precision, recall, F1, and
  operation-selection accuracy were not calculated.
- RQ2 is `UNKNOWN`: no complete target-bound denominator or independent
  exact-pair semantic evidence was established. No coverage percentage is
  reported. Twelve pair diagnostics remain `UNKNOWN`; zero were independently
  verified.
- G1 remains `INCOMPLETE`; G4 remains `NOT AUTHORIZED`; measured-DA01
  `P_ALGORITHM_STATUS` remains `NOT_READY`.
- The A0→A0.1 transition remains `CALIBRATION_EXPOSED`. No B1 arm, human
  operator, significance test, or generalized claim is reported.

## Preserved attempt history

- `preflight-a01`: original verified preparation; unchanged and still
  `PREPARED_NOT_EXECUTED`.
- `execution-a01`: stopped during runtime-context assembly before either arm
  ran; preserved.
- `execution-a02`: both arms and initial evaluators ran, then manifest
  aggregation raised the missing-field `KeyError`. Append-only finalization
  reused arm outputs and reran evaluator commands. It remains
  `POST_EXECUTION_FINALIZATION`; its artifacts are unchanged.
- `execution-a03`: a separate direct attempt ran both arms, but its host
  evaluator subprocesses lacked the required development packages (Import
  Linter executable unavailable; architecture pytest import failed). It was
  not recovered or overwritten and is not the primary verified execution.
- `execution-a04`: primary corrected direct run documented above. Host
  evaluator dependencies were explicitly supplied before execution; no
  recovery was used.

## Archive and verification

- Run directory: `experiments/results/dev-b0p-20261020-execution-a04/`
- Manifest SHA-256:
  `2b4926d12798f5504e13afeca291d3a9ca09053497f1dc475ba4d9b52d8801c1`
- Run `SHA256SUMS` SHA-256:
  `3943bea82bc5184607bc9ce9709bfc610aa619ebe5b2c4e38bb2b07570bc5b82`
- ZIP: `experiments/results/dev-b0p-20261020-execution-a04.zip`
- ZIP SHA-256:
  `13f81c4f74e3cbbf857da204ecff3c22c6f86a87f4c0e0ee4c782983d416cc64`
- ZIP sidecar verification and `unzip -tq`: passed.
- Clean extraction: 355 `SHA256SUMS` rows passed; independent verifier returned
  `verified=true`, `EXECUTED_PARTIAL`, 357 manifest artifacts, B0 sealed,
  P governance HOLD.
- Download: PR #24 evidence comment will link the ZIP and its plain-text
  SHA-256 sidecar; the archive is not committed to Git.

Preparation and historical a02 evidence remain unchanged. The a04 ZIP has 359
entries; its run inventory contains 355 rows and the manifest records 357
artifacts.

## Implementation verification

The regression matrix covers `DEV-B0P-EXEC-02` (arm-result propagation into
manifest aggregation). The existing focused B0/P suites also cover source and
bundle bindings, seals/HOLD markers, evaluator identity, write-once evidence,
unknown denominators, no-scorer rules, and archive integrity.

```bash
UV_PROJECT_ENVIRONMENT=/private/tmp/b0p-venv UV_CACHE_DIR=/private/tmp/b0p-uv-cache \
/private/tmp/b0p-venv/bin/python -m pytest --no-cov -q -p no:cacheprovider \
  tests/unit/test_b0p_development.py \
  tests/unit/test_b0p_git_inventory.py \
  tests/unit/test_b0p_execution.py
# 40 passed
```

The final local DEVELOPMENT quality run passed with a disposable PostgreSQL
test database. It ran Ruff check/format (287 files), Mypy (119 source files),
Bandit, Import Linter (5 kept, 0 broken), architecture tests (6 passed),
migration validation, the DEVELOPMENT regression set (414 passed), EXP-01
(49 passed), and EXP-02 (30 passed). One existing Starlette/httpx deprecation
warning was emitted. The target excludes
`tests/unit/test_da01_execution.py` and
`tests/unit/test_research_schema_foundation.py`; neither is counted as passed.

Exact invocation:

```bash
PATH=/private/tmp/b0p-uv/bin:$PATH \
UV_PROJECT_ENVIRONMENT=/private/tmp/b0p-venv \
UV_CACHE_DIR=/private/tmp/b0p-uv-cache \
RUFF_CACHE_DIR=/private/tmp/b0p-ruff-cache \
MYPY_CACHE_DIR=/private/tmp/b0p-mypy-cache \
PYTEST_ADDOPTS='-p no:cacheprovider' \
TEST_DATABASE_URL=postgresql+psycopg://evofit:evofit@127.0.0.1:55432/evofit_test \
make UV=/private/tmp/b0p-uv-cache-wrapper development-quality
# PASS
```

Hosted CI is tracked separately on the final pushed revision; no PASS is
inferred from a pending check.

## Next research boundary

Independent evaluation requires a prospectively selected and custodied
transition and reference, authorized complete obligation set, evaluator
positive/negative controls, independent exact-pair evidence, predeclared
scoring, and applicable G1/G4 approvals for canonical DA01 claims. This
engineering fix and DEVELOPMENT execution change none of those boundaries.
