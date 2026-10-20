# DEV-B0P-V1 readiness and execution status

**Record date:** 2026-10-20
**Study status:** `EXECUTED_PARTIAL` — both calibration-exposed DEVELOPMENT
arms ran; B0 prediction was sealed; P returned `HOLD` and emitted no prediction.
**Author scope decision:** `docs/g1/B0P_AUTHOR_DECISIONS_V1.md`
**Protocol:** `docs/g1/B0P_DEVELOPMENT_PROTOCOL_V1.md`
**Frozen Method P source:** `984f75b11b3153c52275e223ce8ec23b8d0dd0e5`

## Completed in this PR

- [x] Preserve the independently verified preparation package
  `dev-b0p-20261020-preflight-a01` and its original manifest/checksums.
- [x] Execute unchanged B0 and frozen P once each on A0→A0.1, labeled
  `CALIBRATION_EXPOSED`.
- [x] Pin separate offline method images, input bundles, source identities and
  hash-locked runtime dependencies.
- [x] Verify and seal the B0 prediction; preserve the P candidate, full trace,
  `HOLD` decision and no-prediction marker.
- [x] Run fresh Import Linter and architecture-test evaluators after both
  methods; preserve raw output, source/configuration bindings and current-run
  identities.
- [x] Record RQ1 as `NOT_EVALUABLE` and RQ2 as `UNKNOWN`; do not invoke the
  scorer or claim a coverage percentage.
- [x] Preserve the original post-arm failure and checksum list; finalize
  append-only by reusing both method outputs and rerunning only evaluator
  commands for result persistence.
- [x] Create a SHA-256 sidecar for the evidence ZIP; verify sidecar,
  `SHA256SUMS`, `FINAL_SHA256SUMS`, and execution manifest after clean
  extraction.
- [x] Update the English report and Ukrainian manuscript with observed results
  and limits.

## Execution result

| Stage | B0 | Method P |
|---|---|---|
| Candidate validation | `VALID` | `INVALID` |
| Prediction | `SEALED`, SHA-256 `124a2495b5217d1686c9ddae631980c1c314654e8b12a9c48d4fc949deef9b34` | `NOT_EMITTED_GOVERNANCE_HOLD` |
| Governance | Not applicable | `HOLD`; 10 recorded reason codes |
| Method time | `84,999,500 ns` | `457,522,042 ns` |
| Adaptation time | `0 ns` by unchanged-B0 definition | `190,146,001 ns` |
| Evaluator evidence | Shared fresh commands | Shared fresh commands |
| RQ1 | `NOT_EVALUABLE` | `NOT_EVALUABLE` |
| RQ2 | `UNKNOWN` | `UNKNOWN` |

Import Linter exited 1 with `Module 'app.repositories' does not exist`; its
evidence is valid as a process observation but compliance is `NOT_EVALUABLE`
because its configured target is absent. This is not a confirmed architectural
violation. The architecture suite exited 0 (6 passed); process-level compliance
is recorded as `COMPLIANT`, while semantic adequacy remains `UNKNOWN`.

Method execution, adaptation, evaluator and evidence-verification timers have
different boundaries. CPU and RSS remain `UNKNOWN`. No runtime performance
comparison is inferred.

## Research readiness and claim limits

- Transition: A0→A0.1, `CALIBRATION_EXPOSED`; this is not a holdout or
  independent validation.
- P policy source: DRAFT/OPEN, without production authority; P's observed HOLD
  is a valid outcome of this DEVELOPMENT run.
- Candidate: P candidate validation is `INVALID`; proposed operation list is
  empty. No governance-accepted P configuration exists.
- Pair evidence: 0 independently verified exact pairs; 12 trace diagnostics
  remain `UNKNOWN`.
- RQ1: no exact-after-SHA reference was sealed before predictions; scorer not
  invoked; precision, recall, F1 and operation accuracy are not calculated.
- RQ2: no complete target-bound shared denominator and independent semantic
  pair evidence; no coverage percentage is reported. The protocol's six-item
  count alone is insufficient to establish this run's denominator.
- G1 remains `INCOMPLETE`; G4 remains `NOT AUTHORIZED`; measured-DA01
  `P_ALGORITHM_STATUS` remains `NOT_READY`.
- No B1 arm, human operator, significance test or generalization claim.

The unavailable references and authority constrain score calculation and
research claims. They do not invalidate the isolated method execution or the
observed evaluator outputs.

## Preserved attempt history

- `dev-b0p-20261020-preflight-a01`: the original verified preparation package;
  unchanged and still `PREPARED_NOT_EXECUTED`.
- `dev-b0p-20261020-execution-a01`: failed during runtime-context assembly
  before either method ran; original failure artifacts retained.
- `dev-b0p-20261020-execution-a02`: both method containers and initial
  evaluators completed. The first manifest aggregation failed on a missing
  in-memory `candidate_validation` field. Finalization read back the persisted
  runner outputs and seals, reran only the post-arm evaluators, and preserved
  the original failure/checksum inventory.

The finalized execution is `POST_EXECUTION_FINALIZATION`,
`EXECUTED_PARTIAL`; method outputs were reused and neither method invocation
was repeated.

## Evidence identities

- Execution manifest SHA-256:
  `8aa1de87ed3c1bc55610b7f4722c3ffe3a88ef5b9ed9dc75c79a827513487e3d`
- Preparation manifest SHA-256:
  `d6d55437fcc30c4e8bdd5acb37fd9f881be74f646989e701b03092ba8ac82b2f`
- Evidence ZIP:
  `experiments/results/dev-b0p-20261020-execution-a02.zip`
- ZIP SHA-256:
  `c36a97c49295b36ba166901a372f8c65e961c2f2eda174643a1f0d7b0bb6f87c`
- Clean extraction verifier: exit 0; 363 manifest artifacts; both original and
  final checksum inventories passed.

## Reproduction and verification

The following commands are read-only verification of the preserved run:

```bash
python scripts/verify_b0p_development_comparison.py \
  --run-directory experiments/results/dev-b0p-20261020-preflight-a01

python scripts/verify_b0p_development_execution.py \
  --run-directory experiments/results/dev-b0p-20261020-execution-a02

(cd experiments/results && \
  shasum -a 256 -c dev-b0p-20261020-execution-a02.zip.sha256)
```

Focused implementation checks passed locally. The latest result of
`make development-quality` and the latest hosted GitHub Actions runs must be
recorded with their actual statuses before release review; neither status
changes G1/G4 or turns this into independent evidence.

## Subsequent independent evaluation

Plan a new architecture transition and target-bound reference before any
prediction is inspected. Freeze separate custody, applicability and complete
obligation denominator; run evaluator positive/negative controls and obtain
independent exact-pair semantic proof. Predeclare scoring and resource
sampling. Obtain the approvals required for any canonical DA01 claim. Retain
this run as calibration evidence; do not retrospectively relabel it as
holdout, G4-authorized, or generalized validation.
