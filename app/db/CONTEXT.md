# Context — `app/db`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `app/CONTEXT.md` before this file.

## Responsibility

Database engine, session ownership, and registration of shared SQLAlchemy metadata.

## Local landmarks

- `__init__.py`
- `engine.py`
- `model_registry.py`
- `session.py`

## Established conventions

Use one caller-owned session for atomic Task/Notification/Audit effects.

## Constraints and known gaps

No service-owned databases or distributed transactions exist.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
