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
- `evaluator_evidence.schema.json` — includes backward-compatible typed inspection scope (`dependency_edge`, `module`, or `file`) with digest-bound inventory evidence.
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

This is a selected list, not a complete source inventory.

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
