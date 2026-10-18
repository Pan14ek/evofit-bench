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
- `evaluator_evidence.schema.json`
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
- `exp03_method_integration_v1.schema.json`
- `exp03_method_p_execution_trace_v1.schema.json`

This is a selected list (19 direct tracked files), not a complete source inventory.

## Established conventions

Validate exact contract version; maintain separate intermediate V3 profile.

## Constraints and known gaps

The `p_*_v1` contracts remain additive DEVELOPMENT contracts. Snapshot v1.2
adds a V3-only registry closure-claim list so exact before and after claims can
be verified independently; Snapshot v1.1 and the V2 exporter retain their
single-claim contract. Adaptation evidence V2 is an additive sidecar schema for full-template descriptor
authorization; it does not reinterpret V1 signed evidence. Do not weaken frozen
DA01 prediction or scorer schemas to force a fit.

The EXP-03 manifest and execution-trace schemas are DEVELOPMENT-only. They
bind validated EXP-02 references and serialized results from the existing V3
verifier/adaptation path; neither schema grants semantic proof, coverage,
policy authority, or a measured prediction.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. DEVELOPMENT validation uses `make development-quality` with a **disposable** PostgreSQL database; it excludes the two protected DA01 test modules. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
