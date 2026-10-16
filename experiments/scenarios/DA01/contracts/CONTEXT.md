# Context — `experiments/scenarios/DA01/contracts`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `experiments/scenarios/DA01/CONTEXT.md` before this file.

## Responsibility

Archived OpenAPI, DB, Alembic, metrics, seed and workload parity contracts.

## Local landmarks

- `a0-alembic-state.json`
- `a0-metrics-contract.json`
- `a0-openapi.normalized.json`
- `a0-seed-fingerprint.json`
- `a0-sqlalchemy-schema.json`
- `a0-workload-hashes.json`
- `da01-alembic-state.json`

This is a selected list (12 direct tracked files), not a complete source inventory.

## Established conventions

Treat as frozen invariants for scenario verification.

## Constraints and known gaps

Never edit to accommodate a new method implementation.

**Frozen provenance boundary:** this new context file is supplemental navigation metadata, not part of the archived evidence/checksum inventory. Preserve existing artifact bytes and never export CONTEXT.md in an isolated method bundle.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
