# Context — `app/modules/tasks`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `app/modules/CONTEXT.md` before this file.

## Responsibility

Task workflows and atomic assignment/status notifications and audit.

## Local landmarks

- `__init__.py`
- `api.py`
- `model.py`
- `repository.py`
- `schemas.py`
- `service.py`

## Established conventions

Task status: TODO→IN_PROGRESS/CANCELLED; IN_PROGRESS→DONE/CANCELLED; terminal DONE/CANCELLED. Service coordinates SQLAlchemy commit.

## Constraints and known gaps

Preserve rollback, API status behavior and deterministic seed.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
