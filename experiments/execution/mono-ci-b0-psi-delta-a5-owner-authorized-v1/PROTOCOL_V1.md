# Research-owner-authorized exploratory ΔA5 protocol v1

- Study ID: MONO_CI_B0_PSI_DELTA_A5_OWNER_AUTHORIZED_DEV_V1
- Transition: A0_4_REPORT_QUERY_PORT → A0_5_MODULE_DATA_OWNERSHIP
- Classification: evaluator work is DEVELOPMENT_CALIBRATION; full B0/Ψ runs are EXPLORATORY_DEVELOPMENT.
- Status: owner-authorized for exploratory execution; not independently reviewed, not an official measured comparison.
- Unit: one architecture transition. Repeated executions estimate technical variability only.

## Authorization and gate boundary

On 2026-10-27 the user explicitly authorized real, reproducible experimental execution and a separate RESEARCH_OWNER_AUTHORIZED protocol if the official G1/G4 prerequisites could not be satisfied. The authorization is recorded as a direct conversation instruction. No name, signature, external authorization artifact, or independent identity verification was supplied; this protocol does not fabricate one.

The existing official mono-ci-b0-psi-delta-a5-v1 stop rule requires independently evidenced baseline approval, bounded applicability and stage scope, semantic review, method freeze and READY status, authorized cost/search rules, input parity/isolation, independent reference custody, G1 disposition, and separate G4 authorization. These remain unsatisfied. This protocol does not amend that protocol or call its protected measured-study entrypoint. It uses the existing A0.5 DEVELOPMENT adapter and its isolated Method Ψ process under the owner's separate exploratory authorization. G1 remains INCOMPLETE, G4 remains NOT_AUTHORIZED, and P_ALGORITHM_STATUS remains NOT_READY in every result.

## Question and bounded claim

Observe how the unchanged prospective two-control B0 and the existing Method Ψ implementation behave on the declared A0.4→A0.5 source transition, and calibrate the pinned static evaluators on one clean source and one existing source mutation.

The study can report actual source-bound evaluator outcomes, raw Method Ψ governance/operation/candidate outputs, and technical elapsed-time variability. It cannot establish mandatory-obligation coverage, independent correctness, generalized effectiveness, statistical significance, or an official B0/Ψ comparison.

## Frozen subjects and cases

- A0.4: commit d3101c0d3aa9b7b709253b6ec7518416f05f65b9; repository tree 2b436e0aaf09403ea516d73d20a466a122f86592; application tree 007196f68652bc13f6798805793ffdfae96f95f7; state manifest SHA-256 9c981442a34830bdc44d77ffc17de5b9f832b0b261d0d92f28bd15dc567febd9.
- A0.5: commit a349d19fb89b577e6799e9736ed4ce0acc572166; repository tree 97c060cc26313a879f0940a178d42e422cc4d188; same application tree; state manifest SHA-256 2906216b212b450706368d44233488fd638d2e7af789980ea2abf02740a04ae8.
- B0: exact prospective reconstruction SHA-256 9a8c15fabc41ec6e079b3ec708a60dcc0320fa5e7370e1416123e9ec4f64643d, containing AC_PUBLIC_API and AC_MODULE_GRAPH. It is not a historical baseline and is not approved.
- Clean case: exact A0.5 source above.
- Negative case: byte-preserving replay of the existing PR #56 Tasks-to-Notifications table-access probe, one changed path only. This is historical calibration material, not a newly sealed holdout. It is evaluated after Ψ has produced its result and is not mounted into Ψ input.
- No new holdout case is introduced. No ground-truth, expected-operation, scorer, or other-arm output is supplied to Ψ.

## Conditions and repetitions

Before outcomes, freeze this protocol, the harness, B0 bytes, method/evaluator/config/schema hashes, source identities, runtime class, timing boundaries, analysis rules, and budget in PRE_RUN_FREEZE.json. Its parent commit identifies the checked implementation; the freeze commit must change only that freeze record.

1. Evaluator calibration: AC_PUBLIC_API, AC_MODULE_GRAPH and AC_DATA_OWNERSHIP on clean A0.5 and the existing negative probe. Execute one randomized-order warmup and ten randomized-order measured repetitions per evaluator×case cell (66 planned process calls). A calibration call records both evaluator subprocess time and the surrounding existing scope-verification call. Warmups are retained but excluded from descriptive summaries.
2. Transition execution: run the existing full A0.4→A0.5 DEVELOPMENT adapter once as a warmup, then three measured technical repetitions. Each run executes the original B0 controls on the exact A0.4 and A0.5 source states and invokes the actual isolated Ψ implementation against the clean transition evidence. Existing A0.5 positive and negative diagnostic evaluations are post-method; they are not method input.
3. Order: shuffle the six calibration cells within each round from preregistered seed 20261027; run the full transition warmup first, then measured runs in order 1–3. No replacement run is allowed after observing an unfavorable result; failures and missing calls remain in the dataset.

The four full transition executions are technical repeats of one transition, not four architecture-level experimental units.

## Metrics and boundaries

- Evaluator process elapsed time: existing run_fresh_evaluator.duration_ms, monotonic start immediately before and end immediately after the evaluator subprocess. It includes process launch, CLI work and captured output; it excludes subsequent scope verification.
- Evaluator-plus-verification elapsed time: outer monotonic interval around the existing _run_bound_evaluator call.
- CPU: runner self CPU and reaped-child CPU deltas around each evaluator-plus-verification call and each full transition execution. Child CPU includes the evaluator plus the existing Git/scope-verification subprocesses; it is not evaluator-only CPU.
- Peak RSS: unavailable per process from the existing runner; record NOT_AVAILABLE, never infer it from a cumulative high-water mark.
- Method duration: existing transition record psi.execution_duration_ms around the isolated method process. The current contract does not expose reliable per-stage Ψ durations; they are unavailable and will not be inferred. Full-run elapsed time is the outer monotonic interval around run_a05_transition, including its evaluators and diagnostic work, but excluding dependency setup, archive packing and GitHub artifact upload.
- Outcomes: actual exit code, execution status, compliance, inspected-source counts, finding codes, Method Ψ decision, operation list, prediction flag, candidate state/digest when present, and explicit error/missing status.
- Scoring and coverage: NOT_EXECUTED / UNKNOWN. No coverage percentage, operation correctness score, or independent reference is computed.

## Cost budget set before runs

The hosted A0.5 DEVELOPMENT workflow has a documented 60-minute job timeout. This study sets a 45-minute measured-execution wall-clock ceiling, reserving 15 minutes of that workflow window for setup, archive readback and upload overhead. Within it, the author selected a 15-minute evaluator-calibration cap and a 30-minute transition-run cap. These splits are researcher-selected operational limits, not independent cost authority and not per-candidate Method Ψ costs. The existing planner's cost model, maximum incremental cost, candidate costs and search bound remain unresolved. If a cap is reached, stop, preserve completed observations and report unrun samples as missing.

## Analysis and integrity

Use only machine-readable records from the raw calibration and transition archives. For each evaluator×case cell, report valid count, failures/missing samples, mean, median, sample standard deviation, minimum, maximum and nearest-rank p90. Include warmups in raw tables but exclude them from summary statistics. For the three measured full runs, report exact outcomes and descriptive times; do not run significance tests. Retain the single architecture transition as the experimental unit.

The calibration archive uses a member-digest manifest and SHA-256 sidecar. Each full-run archive uses the existing V4 transition packer/verifier and readback. The final evidence manifest binds archive and sidecar digests, source identities, run IDs, outputs and analysis inputs. Preserve historical PR #56 evidence as a separately labeled reference; do not merge its observations into the new sample counts.

## Activation history

The initial pre-run freeze commit `500bc94d5914ef84c5796d8833e9b233955124d3` produced GitHub Actions run `40491096266`, which ended with zero jobs. The refreshed freeze commit `a2db859248236bcb6acf8860080ce5b5b89d2b41` produced run `40493480973`, also with zero jobs. The third freeze, `7049affc12f9f2d6aca224730af4ff49a252b464`, produced owner-workflow run `40494704760` and caller run `40494706231`; GitHub reported no checks or jobs, and no runner logs were created. The fourth freeze, `d20e0f698bf1b0ccdba949b30d04102673c0a74a`, produced run `40496123688` with zero jobs. Local actionlint identified the cause in the inline workflow: `runner.temp` is not available in a job-level `env` block. None of these attempts started evaluator calibration or a B0/Ψ transition, and none produced study observations. They are retained as activation failures. The corrected job uses fixed temporary paths, is inline in the established `ci.yml`, is gated to its dedicated branch, and follows development-quality; a fresh freeze is required before execution.

## Stop and reporting rules

If a source/config/method pin, clean-checkout check, archived-probe replay, network-isolation requirement, archive verifier, or declared time budget fails, do not bypass it. Record the error and continue only with independent activities still permitted. Preserve actual HOLD, empty operation plans, unmaterialized candidates, and failed/missing measurements. The protocol is not an approval of the proposed B0, applicability, semantic mappings, evaluator validity, or cost model.

## Requirement-to-test matrix

| Protocol requirement | Automated evidence |
|---|---|
| Owner authorization is recorded without identity/signature fabrication; G1/G4/P remain unchanged | `test_protocol_records_owner_authorization_without_promoting_official_gates`; `test_protocol_schema_rejects_gate_promotion_and_unapproved_baseline` |
| Freeze and execution records use versioned schemas; actual outcomes cannot be promoted to an invented state | `test_execution_schema_requires_actual_run_statuses_and_preserves_gate_states`; runner validates freeze/protocol/execution payloads before use/readback |
| Calibration plan and summaries preserve warmups, failures, missing calls, and descriptive-only statistics | `test_calibration_summary_excludes_warmup_and_retains_failed_and_missing_samples`; `test_nearest_rank_quantile_uses_preregistered_rank_without_interpolation`; `test_descriptive_statistics_preserve_empty_and_single_sample_states` |
| Ψ HOLD, empty operation plan, unapplied candidate, and absent prediction remain the actual method outcome | `test_method_outcome_preserves_hold_empty_plan_and_unapplied_candidate` |
| Raw calibration archive has schema, member hashes, safe paths, and detached digest readback | `test_calibration_archive_round_trips_all_members_and_rejects_sidecar_tampering`; `test_calibration_archive_rejects_parent_traversal_even_with_matching_digest` |
| Derived tables and report are checked against their own checksum inventory | `test_analysis_readback_verifies_each_derived_artifact_digest`; `test_analysis_readback_rejects_checksum_path_traversal` |
| Budget sensitivity is derived from observed evaluator timings and remains distinct from Ψ cost authority | `test_budget_sensitivity_keeps_the_psi_cost_model_unresolved` |

These tests exercise schema and failure semantics. They do not establish scientific validity, independent approval, or measured outcomes; those come only from the separately frozen execution and its verified raw archive.
