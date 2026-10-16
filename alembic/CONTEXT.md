# Context — `alembic`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `CONTEXT.md` before this file.

## Responsibility

Database migration environment and model metadata registration.

## Local landmarks

- `env.py`
- `script.py.mako`

## Established conventions

app.db.model_registry registers capability ORM classes on shared SQLAlchemy Base.

## Constraints and known gaps

DA01 preserved revision 0001_a0_schema; no database refactoring without a separate scenario.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
