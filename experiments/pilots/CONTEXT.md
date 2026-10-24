# Context — `experiments/pilots`

> **Audience:** human researchers and AI coding agents. **Type:** descriptive navigation for bounded development pilots; not a frozen DA01 input, authority record, or measured DA01 result.
> **Navigation:** follow root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and `experiments/CONTEXT.md` first.

## Responsibility

Store pilot-specific protocols, reports, derived result tables, and narrow tools that consume the repository's existing DEVELOPMENT evidence collectors.

## Local landmarks

- `mono_e1_dev_p_decisions_v1/` — separately versioned eight-case TEST_ONLY Method P DEVELOPMENT decision rehearsal, scorer-only frozen author-declared reference, three technical repetitions per case, B0_SYNTH output, raw V3 inputs/traces, result table, and checksums; not official MONO-E1 or DA01 execution.
- `mono_e1_ci_evidence_v1/` and `verify_monograph_evidence.py` — derived tables, claim matrix, figure exports, Ukrainian report, and read-only replay/integrity verifier for separate canonical-CI and synthetic tracks; never a method input or official MONO-E1 result.
- `mono_e1_dev_p_decisions_v1/runner.py` — reference-blind `execute` phase followed by digest-checked `score`; uses the existing verified V3 and `run_adaptation()` path.
- `EVAL01_PROTOCOL_V1.md`, `EVAL01_MUTATION_CATALOG_V1.json`, and `run_eval01.py` — preregistered A0.4 W2 evaluator-validation protocol, mutation cases, clean Git provenance, repeated source-bound evaluator calls, analysis, and raw evidence packaging; independent of MONO-E1/E2 and Method P.
- `EVAL01_REPORT_V1.md`, `EVAL01_CASE_RESULTS_V1.csv`, `EVAL01_ANALYSIS_V1.json`, and `EVAL01_RAW_EVIDENCE_V1.zip` — evidence-derived EVAL-01 report, finite case-level confusion metrics, machine-readable analysis, and checksummed raw runs; the ZIP sidecar holds its external SHA-256.
- `EVAL02_PROTOCOL_V1.md`, `EVAL02_MUTATION_CATALOG_V1.json`, and `run_eval02.py` — preregistered W2 continuation on canonical A0.4, with case-specific architecture labels, evaluator applicability, clean source revisions, repeated calls, and evidence analysis.
- `EVAL02_REPORT_V1.md`, `EVAL02_MANUSCRIPT_UA.md`, `EVAL02_POST_EXPERIMENT_ERRATUM_V1.md`, `EVAL02_CASE_RESULTS_V1.csv`, and `EVAL02_ANALYSIS_V1.json` — evidence-derived case table, metrics, descriptive timing, limitations, Ukrainian manuscript subsection, and traceable editorial clarifications.
- `EVAL02_RAW_EVIDENCE_V1.zip` and its `.sha256` sidecar — raw evaluator streams, source provenance, mutation patches and Git bundles, preregistration snapshot, frozen evaluator inputs, and internal checksum inventory.
- `validate_eval02_postrun.py` — read-only post-experiment status and archive-integrity check; it validates preserved records and never invokes evaluators or edits the archive.
- `PILOT_01_EXPECTATION.md` — expected S0/S1 evaluator outcomes recorded before formal repeated measurements.
- `PILOT_01_REPORT.md` — evidence-backed experimental report and reproducibility limits.
- `PILOT_01_MANUSCRIPT_UA.md` — Ukrainian manuscript subsection based only on collected results.
- `PILOT_01_WORKLOAD.yaml` — the fixed A0.1 pilot load profile.
- `PILOT_01_RESULTS.csv` and `PILOT_01_DESCRIPTIVE_STATISTICS.json` — generated from digest-validated run evidence.
- `PILOT_01_S1_FAULT.patch` — exact isolated source-level S1 intervention.
- `PILOT_02_PROTOCOL.md` — frozen, restricted A0-to-A0.1 architecture-compliance protocol.
- `PILOT_02_DEVELOPMENT_ASSUMPTIONS_V1.json` and `PILOT_02_DEVELOPMENT_ADDENDUM_V1.md` — prospective, TEST_ONLY execution assumptions and their relation to the frozen protocol.
- `PILOT_02_DEVELOPMENT_ASSUMPTIONS_V2.json` and `PILOT_02_DEVELOPMENT_ADDENDUM_V2.md` — prospective correction of A0 applicability assumptions, evaluator-row binding rules, and V2 execution boundary; not DA01 authority.
- `PILOT_02_DEVELOPMENT_ADDENDUM_V3.md` — prospective correction of compliance classification when evaluator scope is unresolved; V2 assumptions remain unchanged.
- `PILOT_02_DEVELOPMENT_ADDENDUM_V4.md` — prospective correction of the TEST_ONLY execution-evidence admission label in the PILOT-02 trace; it does not claim semantic pair proof.
- `PILOT_02_A0_1_METHOD_INPUT_PROFILE_V1.json` — exact DEVELOPMENT mapping profile, pinned by the P verifier.
- `PILOT_02_A0_1_METHOD_INPUT_PROFILE_V2.json` — additive profile binding four inherited A0 rows to A0.1 DEVELOPMENT evaluator source bytes; V1 remains unchanged.
- `PILOT_02_INHERITED_EVALUATOR_PROTOCOL_V1.md` — pre-execution protocol for the four inherited evaluator observations.
- `run_pilot02_inherited_evaluators.py` — fresh Locust, EXP-01 runtime and isolated PostgreSQL integration evidence collector; emits per-evaluator source/configuration hashes, raw-stream digests, `evaluator_inventory.json`, results, and a run manifest.
- `run_pilot02_method_p.py` — validates an EXP-02 run, exports the existing V3 input, verifies the profile, and runs the existing P pipeline.
- `pilot02_testonly_execution.py` — builds only the prospective continuation's isolated TEST_ONLY policy source, evidence ledger and adaptation sidecar; never used as a production trust anchor.
- `PILOT_02_REPORT.md`, `PILOT_02_RESULTS.csv`, `PILOT_02_MANUSCRIPT_UA.md`, and `PILOT_02_RAW_EVIDENCE.zip` — evidence-derived pilot outputs and their checksums.
- `PILOT_02_RAW_EVIDENCE_CONTINUATION.zip` — separate continuation evidence archive; the first run archive remains unchanged.
- `PILOT_02_RAW_EVIDENCE_CONTINUATION_V2.zip` — corrected prospective continuation archive; V1 assumptions and outputs remain unchanged.
- `PILOT_02_RAW_EVIDENCE_CONTINUATION_V3.zip` and `PILOT_02_RAW_EVIDENCE_CONTINUATION_V4.zip` — preserved prospective continuations; each archive has a separate SHA-256 sidecar.
- `PILOT_02_RAW_EVIDENCE_CONTINUATION_V5.zip` — inherited-evaluator execution and V2-profile continuation evidence, with a separate SHA-256 sidecar.
- `PILOT_02_RAW_EVIDENCE_CONTINUATION_V6.zip` — final source-bound semantic controls, validated exact-pair reports, four inherited evaluator observations, and the Method P continuation; its SHA-256 sidecar is separate, and v6g/v6h/v6j attempts are retained as excluded diagnostics.
- `pilot02_semantic_validation.py` — pinned clean/fault evaluator controls, typed scope inventories, source-mutation readback, and TEST_ONLY pair reports for the existing Method P path.
- `generate_pilot01_results.py` — validates existing EXP-01/02 artifacts, independently derives runtime metrics from raw Locust/process CSV files, cross-checks the manifest values with documented tolerances, and writes the CSV table and descriptive summary.
- `run_pilot01_measurement.py` — invokes the existing Import Linter, module test, Locust task file, runtime sampler, and EXP-01/02 validators for this pilot only.
- `B0P_DEVELOPMENT_REPORT.md` and `B0P_DEVELOPMENT_MANUSCRIPT_UA.md` — preparation and comparative DEVELOPMENT report; a04 is the primary direct execution, while a02 recovery and a03 evaluator-environment failure remain separately preserved; preserve UNKNOWN/HOLD and do not infer RQ1/RQ2 scores
- `DEV_B0P_E1_REPORT_UK.md` and `DEV_B0P_E1_CALIBRATION_20261021.zip` — evidence-sufficient but calibration-exposed E1 result, Ukrainian report, complete raw package, and SHA-256 sidecar

## Constraints and known limits

PILOT-01 report and manuscript record the A0.1 engineering evaluator response to one controlled source dependency edge. Its repeated runs are technical repetitions of one condition, not independent architecture changes. It does not establish independent semantic coverage or Method P adaptation effectiveness. Keep the S1 source fault on its isolated branch and worktree; preserve the exact source patch and revision. Raw run directories are generated evidence, excluded from Git, and must retain their hashes in the export archive. The result generator must derive request counts, failures, latency percentiles, throughput, CPU delta, peak RSS, and sample count from the raw CSVs and reject manifest-only metric edits even when artifact hashes validate.

## PILOT-02 limits

PILOT-02 is a restricted DEVELOPMENT case with an independently pending
denominator and semantic reference. Its source-bound profile and exact-pair
diagnostics do not authorize P operations, claim P coverage, or turn the
manually established A0.1 reference into a P output. Preserve the raw archive,
profile bundle, actual Method P trace, and unavailable outcomes as-is.

The author-authorized continuation uses an explicit TEST_ONLY assumption set
to exercise operation planning with authentic evaluator output. Preserve its
separate archive and TEST_ONLY label; a candidate may be materialized while
semantic coverage and governance remain unresolved.

V5's canonical run `pilot02-inherited-20261020-v5d` validates the full candidate
configuration after all four inherited evaluator bindings are supplied. The
runtime-failure metric remains UNKNOWN, exact pairs remain UNKNOWN, and
governance remains HOLD. Earlier V5 attempts are retained in the V5 archive and
excluded from primary analysis.

V1 classified `AC_LAYERING` as inactive in A0; the versioned A0 traceability,
fitness configuration, and frozen A0 evaluator support applicability in A0.
Keep V1 as historical evidence, and use the separate V2 assumption set for a
prospective correction. The V2 runner checks each candidate row against the
source-bound profile and records a scoped architecture measurement without
changing full candidate validation.

V2's raw compliance fields are retained; V3 corrects the generic evaluator
scope/compliance distinction. V3's raw trace is also retained; V4 aligns the
execution-evidence admission label with the verified TEST_ONLY sidecar and
keeps `exp02_observations_used_as_semantic_pair_evidence` false. These are
successive corrections on one transition, not independent samples.

The V6 semantic-validation continuation reports `VALID` for the two exact A0.1
pairs only after recomputing pinned source/configuration bindings, typed inspection
inventories, mutation effects, and raw evaluator outcomes. The reports record no
independent human assessment. Pair validity remains TEST_ONLY and cannot establish
a DA01 prediction or coverage denominator; Method P governance remains HOLD.

The B0/P preparation package identifies the A0-to-A0.1 transition as
`CALIBRATION_EXPOSED`. It pins B0, Method P, policy, architecture, exporter,
scorer, sealer, and verifier sources and records the full six-item RQ2
denominator from the DEVELOPMENT protocol. `PREPARED_NOT_EXECUTED` is not a
B0/P result; do not score prior PILOT-02 evidence into the new run.

The separate execution continuation preserves the preflight package, runs the
two pinned methods in separate offline containers, and collects fresh
evaluators after both arms. A missing presealed target-operation reference
keeps RQ1 unscored; absence of current independent exact-pair proofs and an
exact-target denominator keeps RQ2 UNKNOWN. This calibration execution is not
a holdout, an independent validation, or a G1/G4-authorized DA01 measurement.

The E1 calibration run `b0p-e1-cal-20261021-a4` completed on source revision
`14fc8b1bbec2aad2f2968e96e04a02b81a9ed720`. It used a pre-execution,
author-declared exposed reference, fresh digest-bound evaluator observations
(runtime source-to-image provenance remains unverified), and two exact-pair
proofs with `TEST_ONLY` trust. P's candidate was structurally
VALID and its plan contained ADD/REPLACE operations, but governance stayed HOLD;
RQ1 remains NOT_EVALUABLE and RQ2 UNKNOWN over all six obligations. The raw
package preserves the E1 archive, fresh raw evaluator runs, exact P inputs,
semantic controls, and excluded failed readback attempts. It includes a pointer
to the immutable E0 archive rather than rewriting or duplicating E0 bytes.
See `DEV_B0P_E1_REPORT_UK.md` for measured details and limitations.

## Verification

Use the focused pilot tests and result generator, then the repository's documented `make development-quality` command with a disposable PostgreSQL database. Never interpret `Coverage_P`, `Coverage_ref`, G1/G4, or measured DA01 outcomes from this pilot.

- PILOT-02 final V6 audit: PILOT_02_GOVERNANCE_AUDIT_V1.json records INV-05/INV-10 and four inherited-row reassessments; correct_pilot02_v6_archive.py creates a path-normalized copy while preserving V6 payload bytes; the corrected ZIP and sidecar are separate from the immutable original.
- tests/unit/test_pilot02_v6_archive.py checks inventory normalization, byte preservation, and traversal rejection. Clean extraction verification uses shasum -a 256 -c SHA256SUMS from the extracted V6 archive root.


EVAL-01 is a separate controlled validation of the named static A0.4 evaluators. Its known mutation labels come from the preregistered source interventions; they are not scorer-only reference labels. Keep its single A0.4 base and mutation revisions separate from PILOT-01/02 and MONO-E1/E2. The missing-package case is NOT_EVALUABLE and is excluded from binary metrics. Timing repeats are descriptive only.

EVAL-02 extends the source-pattern catalog on the same canonical A0.4 base.
Its dynamic-import and call-signature cases are explicit applicability
boundaries; static evaluator output is not complete architecture truth, and
repeated calls are not independent cases.
The post-run validator distinguishes evaluator invocation, source/evaluator
binding, preregistered diagnostic mismatch, analysis, and archive-integrity
status without changing the frozen run or its derived metrics.

`MONO_E1_DEV_P_DECISIONS_V1` is a distinct TEST_ONLY synthetic decision
experiment on eight authored architecture transitions. It invokes the current
verified V3 P path, records three technical repetitions per case, and compares
only after raw traces exist with the frozen non-independent author reference.
It does not execute the canonical A0.3→A0.4 pair or establish G1/G4, `Coverage_P`,
`Coverage_ref`, scientific improvement, or P readiness.
