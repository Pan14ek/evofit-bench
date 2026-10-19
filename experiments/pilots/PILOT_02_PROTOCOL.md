# PILOT-02 protocol — A0 to A0.1 architecture compliance

**Status:** frozen DEVELOPMENT pilot protocol 1.0.0
**Freeze date:** 2026-10-19, before PILOT-02 Method P execution
**Purpose:** evaluate one bounded A0 to A0.1 fitness-configuration adaptation case. This is not the full DA01 B0/B1/P study and does not authorize measured DA01 claims.

## Research requirement and scope

The case follows `ΔA1: A0_MONOLITH → A0_1_CAPABILITY_MODULES` and evaluates only `architecture_compliance`. The pilot-scoped denominator is the two obligation IDs declared by the exact A0.1 DEVELOPMENT reference configuration:

| Obligation | Criterion intent | A0.1 observation |
|---|---|---|
| `AC_LAYERING` | Internal dependencies conform to the allowed layering model. | `REP_A01_ARCH_INTERNAL_LAYERING_CI` |
| `AC_MODULE_STRUCTURE` | Capability modules have declared structure and identity. | `REP_A01_ARCH_MODULE_STRUCTURE_CI` |

The obligation IDs and criterion intent are read from the versioned catalog. The declared A0.1 scope is taken from `fitness/configs/a0_1-capability-modules.dev.yaml`. Its provenance explicitly says it is manually established, not a Method P or B1 result. Formal applicability, mandatory status, pair semantics, and independent coverage remain pending independent review. This restricted denominator must not be used to calculate frozen DA01 `Coverage_ref`.

## Pinned inputs and comparison

- Frozen A0 source: tag `arch-a0-monolith-v1`, commit `b78b0967be937634b7762baccf5ac6892b279a73`.
- A0.1 source basis: `main` commit `3fdd5c68f8f60fad5757eefa66cc2aa8b24d9306`, app tree `cdff9a6c3cee870e1eca2a5f5f3eb3202b0b1f08`.
- The evidence run must use a clean commit whose `app/` tree and listed evaluator artifacts match that A0.1 source basis. The exact run commit and tree are recorded in the evidence manifest.
- B0 is the unchanged `fitness/configs/a0-monolith.yaml` (SHA-256 `5ad60e373463ea459e192bf85d82704ca9aa1c217c4abf4d8caeb66924059ecb`). Its bytes and the frozen A0 representation catalog are not rewritten.
- The A0.1 manual reference has SHA-256 `3f8c952afd00f97f00b84955cc85fdf8dc5cbe32b52e65771773b8aa5a12fbad`. It is used only to identify the real A0.1 evaluators and candidate template descriptors; it is never reported as a P-generated configuration.
- Both comparison arms use the same A0.1 source commit, Python environment, evaluator package versions, and raw-output collection procedure. B0 retains its original evaluator definition. P uses the existing verified V3 bundle path and `run_adaptation()`; the additive Pilot-02 profile exposes only the two exact A0.1 architecture-compliance candidate descriptors and evaluator artifact bytes.
- The Method P bundle excludes the protocol, B0/P outputs, scorer, oracle, Git metadata, and network access. The adaptation runner receives the verified input bundle and its declared evidence only.

The versioned scenario design independently specifies the reference operation set for `ΔA1`: replace the global layering evaluator with the module-aware layering evaluator, add the module-structure evaluator, and retain the unaffected performance and reliability representations. This reference is evaluation-only and is not copied into the P profile or method input. Independent scoring remains pending.

## Evidence and decision rules

1. An EXP-02 observation is usable for the restricted comparison only after `validate_representation_evidence()` rebuilds it from the exact selected configuration, evaluator records, source revision, configuration artifacts, and raw stdout/stderr digests.
2. A Pilot-02 mapping is exact only when criterion ID and intent, obligation ID, source representation ID, translated lifecycle stage, evaluator ID/name, scope ID, metric name and unit, source revision, evaluator configuration/source artifact bytes, and their SHA-256 values all match the profile and validated EXP-02 bundle. The documented stage translation is `ci_test → ci`; it does not assert equal stage identifiers.
3. Exact structural mapping establishes eligibility for a pair assessment only. It does not prove evaluator adequacy, semantic compatibility, applicability, mandatory status, or coverage.
4. Method P valid coverage requires active independently established applicability, mandatory classification, required-stage authority, an exact current evaluator artifact and evidence, and an independent exact-pair semantic proof. Missing proof or authority stays `UNKNOWN`/`HOLD`; no numeric zero substitutes for unavailable coverage.
5. The primary outcome is the number and set of the two pilot-scoped obligations with independently validated exact-pair coverage, divided by the declared pilot denominator only if the denominator itself is approved. Until that approval exists, report `not established` and list pair-level states. Never label this value DA01 `Coverage_ref`.
6. Independent expected operation judgments, if available, remain in the evaluation record and are inaccessible to the P input. Method P output is not its own reference. No B1 or simulated-human arm is run.
7. The existing PILOT-01 S1 fault may be reused only as the same previously defined evaluator-control condition. It is a secondary evaluator observation, not a new architecture intervention, independent sample, semantic proof, or holdout.

## Measurements

- Record exact architecture before/after commit SHAs and app tree SHAs.
- Preserve actual P before/after applicability results, impact and pair assessments, operation plan, candidate materialization and validation, governance result/reason codes, and input/output digests.
- Measure Method P computation using `time.perf_counter_ns()` immediately around `run_adaptation()`; exclude evidence collection, input export, verification, and report generation. Record these other durations separately where available.
- Record B0 and P evaluator execution time from each evaluator record on the same source revision. Preserve command, version, exit status, stdout/stderr bytes and digests.
- Record actual compliance observations separately from mapping eligibility, pair validity, Method P coverage, and independent assessment.
- Unavailable values are `not measured`, `not established`, or `pending`; they are not encoded as zero.

## Gate and interpretation

The repository still reports `P_ALGORITHM_STATUS=NOT_READY`, G1 `INCOMPLETE`, G4 `NOT AUTHORIZED`, and no authority-backed approval for measured DA01. PILOT-02 therefore records reproducible DEVELOPMENT execution and any resulting `HOLD`/`UNKNOWN` state. A TEST_ONLY path, if used for contract diagnostics, is reported in a separate subsection and cannot count as independent evidence or positive research effectiveness. No policy, verifier, G1/G4, publication, or candidate-acceptance restriction may be weakened.

## Requirement-to-evidence map

| Requirement | Evidence |
|---|---|
| PILOT02-R1 — frozen transition, criterion, denominator, and comparison | This protocol; run manifest pins before/after source and tree SHAs. |
| PILOT02-R2 — exact A0.1-to-P mapping | Versioned Pilot-02 profile, verified V3 input, EXP-02 representation evidence, exact pair assessment records. |
| PILOT02-R3 — existing Method P execution and fail-closed governance | `run_adaptation()` trace, candidate validation, operation plan, governance result and reason codes. |
| PILOT02-R4 — same-source evaluator comparison | B0/P evaluator records and digest-verified raw artifacts for the same A0.1 source revision. |
| PILOT02-R5 — independent assessment boundary | Separate pending/verified reference status; no reference data in P input. |
| PILOT02-R6 — reproducibility | Raw evidence archive, source manifest, input bundle manifest, trace, archive inventory and SHA-256 file. |
