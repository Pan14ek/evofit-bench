# Context — `experiments`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `CONTEXT.md` before this file.

## Responsibility

Scientific protocol, scenarios, execution, curated evidence and run results.

## Local landmarks

- `A0_FINAL_VALIDATION_REPORT.md`
- `README.md`
- `schemas/development_evidence_bundle_v1.schema.json`
- `results/` (ignored generated run outputs)

## Established conventions

Read experiments/design/ and execution/da01/ canonical research rules.

## Constraints and known gaps

EXP-01 output is DEVELOPMENT execution evidence, not Coverage_P, Coverage_ref, or measured DA01 evidence. Runtime bundles distinguish collector revision from observed Docker target identity; without authoritative source-to-image provenance, source binding remains unverified. Never treat a code merge as G4 authorization or a single scenario as many independent samples.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
