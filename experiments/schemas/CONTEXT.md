# Context — `experiments/schemas`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `experiments/CONTEXT.md` before this file.

## Responsibility

Experiment scenario and result schema contracts.

## Local landmarks

- `development_evidence_bundle_v1.schema.json`
- `ground_truth.schema.json`
- `result.schema.json`
- `scenario.schema.json`

## Established conventions

Version contract changes and validate all related cases.

## Constraints and known gaps

Structural schema pass does not imply trustworthy evidence. The EXP-01 contract is DEVELOPMENT-only and fixes coverage claims to not assessed/not established.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
