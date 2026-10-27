# Context — `experiments/execution/schemas`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `experiments/execution/CONTEXT.md` before this file.

## Responsibility

Versioned schemas for Snapshots, applicability, method packages, evidence and results.

## Local landmarks

- `applicability_assessment_v1.schema.json`
- `applicability_ruleset_v1.schema.json`
- `architecture_policy_snapshot_v1_1.schema.json`
- `architecture_policy_snapshot_v1_2.schema.json` (additive, unfrozen DEVELOPMENT extension)
- `candidate_configuration.schema.json`
- `coverage_assessment.schema.json`
- `evaluator_evidence.schema.json` — includes backward-compatible typed inspection scope (`dependency_edge`, `module`, or `file`) with digest-bound inventory evidence; version 2 may also record independently verified expected and inspected file counts.
- `mono_ci_psi_inspection_coverage_v1.schema.json` — strict report of independently derived file scope and source-bound static module graph/cycle comparison for A0.3–A0.5; dynamic edge completeness is explicit.
- `mono_ci_psi_adaptation_necessity_v1.schema.json` — strict post-method DEVELOPMENT diagnostic with bounded conclusion states, evidence references, and unresolved-proof fields; it is not method input or scientific approval.
- `mono_ci_psi_adaptation_necessity_v2.schema.json` — additive strict diagnostic with independent requirement provenance/completeness, verified evaluator capabilities, and explicit typed comparisons; old V1 archive records keep their original schema/checksum readback and are not reinterpreted.
- `ground_truth_hash.schema.json`
- `p_traceability_graph_v1.schema.json`
- `p_impact_assessment_v1.schema.json`
- `p_pair_assessment_v1.schema.json`
- `p_coverage_assessment_v1.schema.json`
- `p_operation_plan_v1.schema.json`
- `p_candidate_configuration_v1.schema.json`
- `p_governance_decision_v1.schema.json`
- `p_adaptation_trace_v1.schema.json`
- `p_cost_model_v1.schema.json`
- `p_adaptation_evidence_v1.schema.json`
- `p_adaptation_evidence_v2.schema.json`
- `p_executable_candidate_identity_v1.schema.json` — strict schema for the source/configuration identity manifest; review-only, not method input
- `exp03_method_integration_v1.schema.json`
- `exp03_method_p_execution_trace_v1.schema.json`
- `exp04_evidence_admission_v1.schema.json`
- `exp04_method_p_execution_trace_v1.schema.json`
- `exp04_evidence_verifier_config_v1.schema.json`
- `pilot02_method_input_profile_v1.schema.json`
- `pilot02_method_input_profile_v2.schema.json` (additive inherited evaluator bindings)
- `pilot02_inherited_evaluator_results_v1.schema.json`
- `pilot02_inherited_evaluator_inventory_v1.schema.json`
- `b0p_development_study_v1.schema.json` — strict source-pinned preparation record; `PREPARED_NOT_EXECUTED` is not a comparative outcome
- `b0p_development_execution_v1.schema.json` — separate source-bound execution continuation; preserves partial execution, P governance, unavailable scoring, runtime images and unknown metrics
- `b0p_evidence_sufficient_execution_v1.schema.json` — additive, calibration-exposed E1 execution envelope with separate TEST_ONLY input binding and explicit RQ1/RQ2 states
- `b0p_e1_rq2_obligation_evidence_v1.schema.json` — complete six-row denominator with per-obligation unknowns and no percentage when independent coverage is incomplete
- `mono_a1_study_v1.schema.json` — additive MONO-E0/E1/E2 study record with explicit manuscript/legacy RQ mapping and separate endpoint states
- `mono_a1_reference_v1.schema.json` — scorer-only, source-pinned MONO reference and complete target/obligation denominator; E2 is bound to the approved A0 commit and final A1 state
- `mono_a1_exact_pair_evidence_v1.schema.json` — raw-artifact-bound exact-pair record; excludes self-declared production-authority scope
- `mono_ci_b0_psi_delta_a5_readiness_v2.schema.json` — ΔA5 readiness package with separate local, historical-reference and optional archive-replay statuses; distinguishes proposed exact-pair review rows, undeclared mappings, and evaluator capability candidates, all excluded from verified coverage in this draft.
- `mono_e1_comparability_preflight_v1.schema.json` — strict additive preparation manifest for exact source pair, shared/arm identities, workload and fixture specification, isolation, runtime, authority gaps, and measurement boundaries; never authorizes execution
- `mono_ci_b0_psi_case_manifest_v1.schema.json`, `mono_ci_b0_psi_inputs_v1.schema.json`, `mono_ci_b0_psi_evaluator_expectations_v1.schema.json`, and `mono_ci_b0_psi_metric_contract_v1.schema.json` — separate strict draft-study contracts; canonical observations are provenance-only and case-bound evidence is absent in preparation; evaluator expectations remain review-only metadata and none of these schemas authorizes execution.
- `mono_ci_b0_psi_reconstructed_baseline_v1.schema.json` and `mono_ci_b0_psi_baseline_reconstruction_v1.schema.json` — explicitly prospective baseline review proposal.
- `mono_ci_b0_psi_arm_input_v1.schema.json` — strict DEVELOPMENT common-input manifest; the paired verifier rejects scorer/expected-output paths.
- `mono_ci_b0_psi_dev_run_v1.schema.json` — DEVELOPMENT evaluator-probe record with NO_GO, nonmeasurement, nonnumeric-status, and per-case source/configuration/state input bindings.
- `mono_ci_b0_psi_development_archive_v1.schema.json` — persistent archive provenance, environment, reproduction commands, authorization boundary, and per-member integrity contract.
- `mono_ci_b0_psi_score_v1.schema.json` — scorer-side categorical status record that forbids numeric outputs while the separate reference is unresolved.
- `mono_ci_psi_transition_run_v2.schema.json` and `mono_ci_psi_transition_archive_v2.schema.json` — additive evidence-backed transition records with raw-output-bound inspection coverage, checksummed post-method necessity diagnostics and TEST_ONLY evidence bindings; allow decision values HOLD/REJECT/ACCEPT, require predictions only for ACCEPT, and preserve all scientific NO_GO/NOT_READY gates. V1 schemas remain supported for readback.
- `mono_ci_psi_transition_archive_v3.schema.json` — A0.5 archive contract pinned to the prospective A0.4 baseline, while V1/V2 archive readback remains unchanged.
- `mono_ci_psi_a05_experiment_evidence_v1.schema.json` — binds the A0.5 ownership positive/negative probes and, when Method Ψ materializes a candidate, its exact serialized candidate, independent evaluator runs, baseline comparison, obligation coverage, and measured incremental control cost.
- `mono_ci_psi_transition_run_v4.schema.json` and `mono_ci_psi_transition_archive_v4.schema.json` — additive outcome-neutral ΔA5 DEVELOPMENT contracts; V4 archive verification requires replay against the pinned source checkout, while V1/V2/V3 semantics remain unchanged.
- `mono_ci_psi_transition_run_v5.schema.json` and `mono_ci_psi_transition_archive_v5.schema.json` — V5 identifies the bounded A0.4→A0.5 TEST_ONLY profile and its extra source-bound evaluator evidence without changing earlier archive semantics.
- `mono_ci_psi_positive_add_profile_v1.schema.json`, `mono_ci_psi_positive_add_study_freeze_v1.schema.json`, `mono_ci_psi_positive_add_study_execution_v1.schema.json`, and `mono_ci_psi_positive_add_study_archive_v1.schema.json` — narrowly scoped profile, preregistered source/cost/host freeze, hosted repetitions, and complete member-integrity contract; all preserve NO_GO and official research gates.
- `mono_ci_psi_a05_experiment_evidence_v2.schema.json` and `mono_ci_psi_a05_probe_manifest_v1.schema.json` — bind exact negative-probe patch and source bytes, local-only deterministic source identity, evaluator/process/raw-stream identities, and DETECTED/NOT_DETECTED/NOT_EVALUABLE diagnostics without fixing evaluator outcomes.
- `mono_ci_psi_owner_authorized_protocol_v1.schema.json`, `mono_ci_psi_owner_authorized_pre_run_freeze_v1.schema.json`, `mono_ci_psi_owner_authorized_execution_v1.schema.json`, and `mono_ci_psi_owner_authorized_calibration_archive_v1.schema.json` — owner-authorized DEVELOPMENT protocol, preregistration freeze, raw execution index, and calibration member manifest. They preserve exploratory classification, UNKNOWN coverage, and unchanged official gates.
- `mono_ci_psi_owner_authorized_protocol_v2.schema.json`, `mono_ci_psi_owner_authorized_pre_run_freeze_v2.schema.json`, `mono_ci_psi_owner_authorized_execution_v2.schema.json`, `mono_ci_psi_docker_isolation_preflight_v1.schema.json`, and `mono_ci_psi_partial_execution_archive_v1.schema.json` — additive V2 DEVELOPMENT contracts for frozen hosted-runner/image identity, timestamped V1 runtime comparison, sandbox capability evidence, full study execution and checksummed partial runs; they preserve the V1 archive contract and scientific gates.
- `mono_ci_psi_v2_postexecution_readback_failure_v1.schema.json` — pins the preserved first V2 post-method readback failure and the actual observations recoverable from its separately verified raw release, without rewriting that run.

This is a selected list, not a complete source inventory.

The separate MONO CI execution schemas do not alter PR #51's source-case,
metric, or readiness contracts. They mark the baseline as a nonhistorical
reconstruction proposal, and DEVELOPMENT run records require
`measurement_status=NOT_EXECUTED` with Ψ predictions absent.
The archive manifest is additive and cannot promote the run: it pins the raw
run record, bundle/source identities, dependency lock hashes, workflow run,
and archive members while retaining `NO_GO`, `NOT_EXECUTED`, and
`BLOCKED_NOT_EXECUTED` as required values.

The transition V1 schemas preserve the original readback contract. V2 adds
fresh evaluator observations, independently verified file/graph coverage,
checksummed post-method diagnostics, run-local TEST_ONLY evidence and an
evidence digest summary to the archive. The run binds exact A0.3/A0.4 commits and trees,
marks reconstructed B0 unapproved, and preserves `NO_GO`, `NOT_EXECUTED`,
`P_ALGORITHM_STATUS=NOT_READY`, G1/G4 and reference-gate values. ACCEPT is a
method DEVELOPMENT decision contract only and does not advance scientific
authorization or permit scoring.

## Established conventions

Validate exact contract version; maintain separate intermediate V3 profile.

## Constraints and known gaps

The `p_*_v1` contracts remain additive DEVELOPMENT contracts. Snapshot v1.2
adds a V3-only registry closure-claim list so exact before and after claims can
be verified independently; Snapshot v1.1 and the V2 exporter retain their
single-claim contract. Adaptation evidence V2 is an additive sidecar schema for full-template descriptor
authorization; it does not reinterpret V1 signed evidence. Do not weaken frozen
DA01 prediction or scorer schemas to force a fit.

The EXP-03 manifest and execution-trace schemas are DEVELOPMENT-only. Version
1.1.0 distinguishes source-contract validation from independent semantic
validation and records that EXP-02 evidence is not admitted to P calculations.
Readback cross-checks manifest fields against the serialized existing V3
verifier/adaptation trace; these schemas grant no semantic proof, coverage,
policy authority, or measured prediction.

The EXP-04 manifest and trace schemas retain EXP-02 execution/compliance
observations separately from exact V3 bindings, sidecar authority, semantic
pair proof, and actual P evidence consumption. Their additive DEVELOPMENT
1.1.0 extension separates eligibility, authorization scope, and exact-pair
consumption, and includes an authorized-but-unconsumed state. Readback enforces
construction-time governance and publication restrictions after digest
resealing. The CLI verifier-config schema is TEST_ONLY and cannot assert
research authority. These contracts do not establish canonical A0.1-to-V3
mappings, positive coverage, or research readiness.

The E1 schemas are versioned DEVELOPMENT evidence. The RQ2 table requires all
six public DA01 obligations and an explicit null coverage percentage when
proof is incomplete. TEST_ONLY pair evidence can support only exact pairs
whose source, evaluator, controls and artifact digests read back successfully;
it does not establish production authority or full-method coverage.

MONO-A1 schemas are a separate namespace and do not relax frozen DA01 or
DEV-B0P-E1 contracts. The E2 reference requires `A0_MONOLITH` at the approved
`b78b0967be937634b7762baccf5ac6892b279a73` predecessor and final
`A1_MODULAR_MONOLITH`; its source commit/tree must be full Git SHAs. The E2
study record can keep its after commit/tree null while final A1 is unverified.
E1 remains structurally compatible with the existing generic source-pinned
reference shape; the W0 `G-A1-C4-REF-FROZEN` procedure is documented separately.
No E1/E2 reference was frozen by this update. Their study record is validated
with the additional cross-field checks in `tooling/mono_a1.py`. The exact-pair
schema has no production-authority enum; the independent W2 readback adapter is
not yet integrated, so absent verifier evidence must remain UNKNOWN.

## PILOT-02 profile schema

PILOT-02's profile schema pins exact A0.1 representation identities,
translated stages, evaluator artifacts, and embedded byte digests. Evaluator
evidence permits `inspected_edge_count: null` when a collector does not report
an inspection count; this remains unresolved input and must not be serialized
as a fabricated zero.
Profile V2 preserves V1 and adds digest-bound parent-row evaluator artifacts
against the exact A0 representation-catalog bytes. PILOT-02 inherited
evaluator results require per-representation source/configuration identities,
commands, timings, raw-stream hashes, and an evaluator inventory. They describe DEVELOPMENT execution only; they do not change
DA01 prediction, scorer, or evidence contracts.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. DEVELOPMENT validation uses `make development-quality` with a **disposable** PostgreSQL database; it excludes the two protected DA01 test modules. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
