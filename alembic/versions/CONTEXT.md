# Context — `alembic/versions`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `alembic/CONTEXT.md` before this file.

## Responsibility

Alembic versioned migration source files.

## Local landmarks

- `0001_a0_schema.py`

## Established conventions

Validate new revisions through make migration-test against a disposable database.

## Constraints and known gaps

Do not rewrite the frozen base migration.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
