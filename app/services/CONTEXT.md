# Context — `app/services`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `app/CONTEXT.md` before this file.

## Responsibility

Shared domain error types used by capability services.

## Local landmarks

- `__init__.py`
- `errors.py`

## Established conventions

Re-use NotFoundError, ConflictError and existing error semantics.

## Constraints and known gaps

Do not recreate a horizontal legacy business service layer.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
