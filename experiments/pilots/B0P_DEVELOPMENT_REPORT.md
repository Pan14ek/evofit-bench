# B0 vs Method P Comparative DEVELOPMENT Report

**Study:** `DEV-B0P-V1`
**Preparation run:** `dev-b0p-20261020-preflight-a01`
**Execution run:** `dev-b0p-20261020-execution-a02`
**Execution status:** `EXECUTED_PARTIAL`
**Exposure:** `CALIBRATION_EXPOSED`
**Record date:** 2026-10-20

## Summary

This is the first actual B0/frozen-Method-P DEVELOPMENT comparison on the
previously exposed A0→A0.1 transition. Both isolated method containers ran
once from the verified preparation inputs. B0 produced a valid candidate and
sealed prediction. Frozen P ran its existing `run_adaptation()` implementation,
produced an invalid candidate, and returned governance `HOLD`; it emitted no
prediction. No method was changed to influence that outcome.

The execution is calibration-exposed evidence. It is not a holdout, independent
validation, authorized measured DA01 result, or evidence of generalized P
superiority. RQ1 is `NOT_EVALUABLE`; RQ2 is `UNKNOWN`. The scorer was not
invoked.

The original runner lost in-memory arm result fields after both arms and the
first evaluators had completed. The run was finalized append-only from its
persisted outputs: both original method outputs and seals were verified and
reused, and only the two post-arm evaluator commands were rerun under
`recovery_a01_` names. The original failure and checksum inventory remain in
the package. No method container was invoked again.

## Design and frozen identities

| Input | Identity |
|---|---|
| Before architecture | `b78b0967be937634b7762baccf5ac6892b279a73` |
| After architecture | `3fdd5c68f8f60fad5757eefa66cc2aa8b24d9306` |
| B0 source and policy-source revision | `165a7d6ef31adbe8ce3abe9f72e59d74692c987e` |
| Frozen Method P source | `984f75b11b3153c52275e223ce8ec23b8d0dd0e5` |
| B0 input bundle SHA-256 | `62ce5f223715a35a407e58c92c45355ddd31708de192a0479e1afeb2f133b628` |
| P input bundle SHA-256 | `b39899ade3ac7330362e0bd4d986b19e8d0112101cdd2dda24dc5355ab2ec11f` |
| Original preparation manifest SHA-256 | `d6d55437fcc30c4e8bdd5acb37fd9f881be74f646989e701b03092ba8ac82b2f` |
| B0 frozen configuration SHA-256 | `5ad60e373463ea459e192bf85d82704ca9aa1c217c4abf4d8caeb66924059ecb` |
| Import Linter configuration SHA-256 | `88ff64a4792c6048a6ab0686ddf9326ebbee49f76996933845a6142cc1a2ba27` |

The preparation package `dev-b0p-20261020-preflight-a01` is unchanged. Its
217-file preparation inventory was verified before execution and its manifest
was independently verified again for the continuation. The A0→A0.1 transition
was explicitly accepted as calibration-exposed. No new architecture scenario
was necessary for this bounded DEVELOPMENT execution.

The B0 and P method images were built from separate, digest-recorded contexts
using the pinned base image
`python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1`
and hash-locked runtime dependencies. Both method containers ran with network
disabled and read-only roots. Their observed image IDs are recorded in the
execution manifest. Method inputs did not contain Git history, scorer material,
ground truth, or expected-operation labels.

## Execution observations

| Stage | B0 | Method P | Interpretation |
|---|---|---|---|
| Input preparation | Verified bundle `62ce…b628` | Verified bundle `b398…c11f` | Both bind the same after-architecture SHA and separate method inputs. |
| Method execution | Completed; `B0_UNCHANGED_V1` | Completed; `P_GOVERNED_ADAPTATION_DEVELOPMENT_V1` | Frozen method sources were used. |
| Candidate validation | `VALID` | `INVALID` | P's candidate is not a validated configuration. |
| Prediction | Sealed; SHA-256 `124a2495…ef9b34` | Not emitted; governance HOLD marker SHA-256 `f612bb1b…c857650` | The P marker is not a prediction. |
| Governance | Not applicable | `HOLD` | DRAFT/OPEN policy and unresolved mandatory inputs remain blockers. |
| Adaptation operations | Empty list by unchanged B0 definition | Empty operation plan | P recorded hold reasons and proposed no operations. |

P's recorded HOLD reasons are `APPLICABILITY_UNKNOWN`,
`CANDIDATE_NOT_POSITIVELY_VALIDATED`, `COST_MODEL_UNRESOLVED`,
`COST_VERDICT_UNRESOLVED`, `INPUT_AUTHORITY_OR_COMPLETENESS_UNRESOLVED`,
`INVARIANT_VERDICTS_NOT_ALL_POSITIVE`,
`MANDATORY_APPLICABILITY_UNKNOWN`,
`MANDATORY_CLASSIFICATION_UNRESOLVED`,
`UNKNOWN_MANDATORY_LINK_PREVENTS_TRANSITION`, and
`VERIFIED_GOVERNANCE_PIPELINE_PROOF_MISSING`. The trace contains 12 current
and candidate pair records; each remains `UNKNOWN` for independent verification.
P's candidate coverage object is not an RQ2 result and is not used as an
independent reference.

## Fresh evaluator observations

Both evaluator commands ran after the method outputs. These are current-run
process observations bound to the target source and recorded configuration.
Their successful execution does not by itself establish semantic adequacy or
independent exact-pair proof.

| Evaluator | Exit | Evidence validity | Recorded compliance | Semantic adequacy | Result |
|---|---:|---|---|---|---|
| Frozen B0 Import Linter | 1 | `VALID` | `NOT_EVALUABLE` | `UNKNOWN` | Its configured `app.repositories` target does not exist in A0.1 (`Module 'app.repositories' does not exist.`); no broken-contract count was emitted. This is a scope mismatch, not a confirmed architectural violation. |
| `tests/architecture` | 0 | `VALID` | `COMPLIANT` at process/suite level | `UNKNOWN` | 6 tests passed. This does not prove all obligations or exact-pair semantics. |

The evaluator output digests, commands, source revision, source-tree identity,
configuration digest, durations, and raw stdout/stderr are included in the run
package. Evaluator execution time was `865,165,750 ns`; the recorded evidence
verification overhead was `1,240,166 ns`. The verification duration does not
include all run setup or Docker build work.

## RQ1 and RQ2

| Endpoint | B0 | Method P | Status and reason |
|---|---|---|---|
| RQ1 TP/FP/FN/TN, precision, recall, F1 | `NOT_EVALUABLE` | `NOT_EVALUABLE` | No exact-after-SHA reference was fixed and sealed before the predictions. The scorer was not invoked. |
| Operation-selection accuracy | Not calculated | Not calculated | There is no admissible expected-operation reference. P emitted no prediction and proposed no operations. |
| RQ2 evidence-supported coverage | `UNKNOWN` | `UNKNOWN` | A complete target-bound obligation set and independent exact-pair semantic evidence were not established. No percentage or shared denominator is claimed. |
| Governance-accepted configuration coverage | Not applicable | `UNKNOWN` | P returned HOLD; no accepted P configuration exists in this run. |
| Independent exact-pair proofs | 0 | 0 | All 12 P-trace pair diagnostics remain `UNKNOWN`; P's own pair verdicts are not the independent reference. |

The preparation protocol records six required obligations, but that historical
count alone does not bind a complete, applicable denominator to this A0.1
target. It is therefore not used to calculate RQ2. Missing reference and pair
proof prevent positive scientific claims without invalidating the actual
method execution evidence.

## Timings and quantitative limits

| Timing | B0 | Method P | Measurement boundary |
|---|---:|---:|---|
| Method execution | `84,999,500 ns` | `457,522,042 ns` | B0 builder/prediction path; P bundle verification plus adaptation path. These timer boundaries differ and are not a controlled performance comparison. |
| Adaptation | `0 ns` | `190,146,001 ns` | B0 is unchanged by definition; P timer surrounds `run_adaptation()`. |
| Evaluator execution | Shared fresh evaluator suite: `865,165,750 ns` | Shared | Two sequential commands; not attributed separately to the arms. |
| Evidence verification overhead | `1,240,166 ns` | Shared | Recorded verifier interval only. |
| CPU time / peak RSS | `UNKNOWN` | `UNKNOWN` | No resource sampler was configured; values remain null. |

These are single-run engineering observations. They do not establish speedup,
latency improvement, statistical significance, or comparative effectiveness.

## Execution and artifact integrity

The first execution attempt `dev-b0p-20261020-execution-a01` stopped while
assembling the P container context, before either method ran. The second
attempt `dev-b0p-20261020-execution-a02` completed both methods and its first
fresh evaluator processes, then recorded a post-arm `KeyError` while assembling
the manifest. The append-only finalization verifies the original inventory,
copied preparation, runtime contexts, run-specific images, both persisted arm
responses, the B0 seal, and the P HOLD marker. It reruns only the evaluator
commands to preserve their result records. The mode is
`POST_EXECUTION_FINALIZATION`; the original failure and `SHA256SUMS` are
preserved, and `FINAL_SHA256SUMS` covers the finalized package.

The finalized run has 363 artifact entries in the manifest. The ZIP contains
366 entries, including the manifest and both checksum inventories. Its SHA-256
sidecar passed `shasum -a 256 -c`. A clean extraction under `/private/tmp` passed
both checksum inventories and the independent execution verifier.

## Implementation and requirement-to-test matrix

These PR-local IDs supplement the versioned DEVELOPMENT protocol; they do not
amend scientific rules.

| Requirement | Implementation and verification | Result |
|---|---|---|
| `DEV-B0P-EXEC-01`: separate versioned execution contract | `b0p_development_execution_v1.schema.json`; strict manifest validation | PASS |
| `DEV-B0P-EXEC-02`: run source-pinned, isolated B0/P arms | separate digest-bound Docker contexts and offline runner containers | Both arms executed once; outputs reused in append-only finalization. |
| `DEV-B0P-EXEC-03`: validate and seal outputs | B0 seal verification; P HOLD marker and candidate checks; tamper/source/bundle tests | PASS for recorded B0 seal; P emitted no prediction. |
| `DEV-B0P-EXEC-04`: fresh evaluator collection/readback | raw output, status, run/source/config identity checks; evaluator scope mismatch tests | PASS as execution evidence; semantic adequacy remains UNKNOWN. |
| `DEV-B0P-EXEC-05`: fail closed on missing references and denominators | no-scorer RQ1, unknown RQ2, unknown exact pairs and resource metrics | PASS; no unsupported score emitted. |
| `DEV-B0P-EXEC-06`: preserve write-once evidence through recovery | original and final checksum inventory checks; tamper and extra-file tests | PASS; clean archive extraction verified. |

Focused commands and outcomes:

```bash
pytest --no-cov -p no:cacheprovider -q \
  tests/unit/test_b0p_development.py \
  tests/unit/test_b0p_git_inventory.py \
  tests/unit/test_b0p_execution.py
# 39 passed

ruff check experiments/execution/tooling/b0p_execution.py \
  experiments/execution/tooling/b0p_isolated_b0_runner.py \
  experiments/execution/tooling/b0p_isolated_p_runner.py \
  scripts/run_b0p_development_execution.py \
  scripts/verify_b0p_development_execution.py \
  scripts/finalize_b0p_development_execution.py \
  tests/unit/test_b0p_execution.py
# All checks passed

ruff format --check experiments/execution/tooling/b0p_execution.py \
  experiments/execution/tooling/b0p_isolated_b0_runner.py \
  experiments/execution/tooling/b0p_isolated_p_runner.py \
  scripts/run_b0p_development_execution.py \
  scripts/verify_b0p_development_execution.py \
  scripts/finalize_b0p_development_execution.py \
  tests/unit/test_b0p_execution.py
# 7 files already formatted

python scripts/verify_b0p_development_execution.py \
  --run-directory experiments/results/dev-b0p-20261020-execution-a02
# exit 0; verified=true; EXECUTED_PARTIAL
```

`make development-quality` passed locally: Ruff check and format, Mypy (119
source files), Bandit, Import Linter (5 kept, 0 broken), architecture tests (6
passed), migration validation, the DEVELOPMENT regression set (414 passed),
EXP-01 (49 passed), and EXP-02 (30 passed). The aggregate target excludes
`tests/unit/test_da01_execution.py` and
`tests/unit/test_research_schema_foundation.py`; neither is counted as passed.
One existing Starlette/httpx deprecation warning was emitted.

The exact local invocation used a disposable PostgreSQL test container and
temporary cache paths to keep tool caches outside the managed worktree:

```bash
PATH=/private/tmp/b0p-uv/bin:$PATH UV_CACHE_DIR=/private/tmp/b0p-uv-cache UV_PROJECT_ENVIRONMENT=/private/tmp/b0p-venv RUFF_CACHE_DIR=/private/tmp/b0p-ruff-cache MYPY_CACHE_DIR=/private/tmp/b0p-mypy-cache PYTEST_ADDOPTS='-p no:cacheprovider' TEST_DATABASE_URL=postgresql+psycopg://evofit:evofit@localhost:5432/evofit_test make UV=/private/tmp/b0p-uv-cache-wrapper development-quality
# PASS
```

Hosted GitHub Actions run [#220](https://github.com/Pan14ek/evofit-bench/actions/runs/39480351406)
completed successfully on implementation commit
`2abf028e758c0736656dbf27afff893e54c3c5e0`. The follow-up commit updates this
report's focused-test count and records those verification results; it does not
change the tested implementation.

## Limits and next experiment

This run is one calibration-exposed architecture transition. P's policy bundle
remains DRAFT/OPEN with no production authority. The P algorithm status remains
`NOT_READY`; G1 remains `INCOMPLETE`; G4 remains `NOT AUTHORIZED`. Exact-pair
semantic proof, a source-grounded reference frozen before predictions, a
complete target-bound obligation denominator, and resource sampling were not
available. No B1 arm or human operator participated.

A subsequent independent evaluation requires a prospectively selected and
custodied architecture transition and reference, an authorized and complete
obligation set, evaluator positive/negative controls and exact-pair evidence,
predeclared scoring rules, and the applicable G1/G4 approvals for canonical
DA01 claims. None of these limitations invalidates the recorded calibration
execution; they constrain which endpoints can be calculated and what can be
claimed from it.

## Evidence record

- Preparation: `experiments/results/dev-b0p-20261020-preflight-a01/`
- Execution: `experiments/results/dev-b0p-20261020-execution-a02/`
- Execution manifest SHA-256: `8aa1de87ed3c1bc55610b7f4722c3ffe3a88ef5b9ed9dc75c79a827513487e3d`
- Final checksum inventory SHA-256: `bd0b770afb494fe9cb324f172eb7a38dea4ffd10ce8ef8f4b93c6b31c5c721f2`
- Semantic-pair diagnostic SHA-256: `f16bc1621a84e30922fe9d651346cefe3b904665493d02901a60548d897f22c7`
- Evidence archive: `experiments/results/dev-b0p-20261020-execution-a02.zip`
- Archive SHA-256: `c36a97c49295b36ba166901a372f8c65e961c2f2eda174643a1f0d7b0bb6f87c`
- Clean extraction: `/private/tmp/dev-b0p-20261020-execution-a02-clean/dev-b0p-20261020-execution-a02/`

The execution results are ignored local DEVELOPMENT artifacts and are supplied
as a separate archive; they do not alter historical PILOT-02 or the original
preparation package.
