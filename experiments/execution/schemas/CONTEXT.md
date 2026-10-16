# Context — `experiments/execution/schemas`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `experiments/execution/CONTEXT.md` before this file.

## Responsibility

Versioned schemas for Snapshots, applicability, method packages, evidence and results.

## Local landmarks

- `applicability_assessment_v1.schema.json`
- `applicability_ruleset_v1.schema.json`
- `architecture_policy_snapshot_v1_1.schema.json`
- `candidate_configuration.schema.json`
- `coverage_assessment.schema.json`
- `evaluator_evidence.schema.json`
- `ground_truth_hash.schema.json`

This is a selected list (17 direct tracked files), not a complete source inventory.

## Established conventions

Validate exact contract version; maintain separate intermediate V3 profile.

## Constraints and known gaps

Do not weaken frozen DA01 prediction or scorer schemas to force a fit.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
