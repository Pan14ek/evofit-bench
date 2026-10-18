# Context — `experiments/schemas`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `experiments/CONTEXT.md` before this file.

## Responsibility

Experiment scenario and result schema contracts.

## Local landmarks

- `development_evidence_bundle_v1.schema.json`
- `fitness_representation_evidence_v1.schema.json`
- `ground_truth.schema.json`
- `result.schema.json`
- `scenario.schema.json`

## Established conventions

Version contract changes and validate all related cases.

## Constraints and known gaps

Structural schema pass does not imply trustworthy evidence. EXP-01 bundle schema 1.2 adds the selected manual A0.1 configuration, multiple evaluator records, and a digest-linked representation-evidence artifact; 1.0/1.1 remain readable. Source-binding status stays separate from collector revision, and verified runtime binding is rejected without authoritative provenance. Contracts are DEVELOPMENT-only and fix coverage claims to not assessed/not established.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
