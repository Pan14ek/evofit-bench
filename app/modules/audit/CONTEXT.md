# Context — `app/modules/audit`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `app/modules/CONTEXT.md` before this file.

## Responsibility

AuditEvent persistence and synchronous business-event recording.

## Local landmarks

- `__init__.py`
- `model.py`
- `public.py` — `record_event` writes through the caller's session and returns no persistence object.
- `repository.py`
- `service.py`

## Established conventions

Audit rows are written within caller transaction by `record_event`; the public facade never commits
or rolls back that transaction.

## Constraints and known gaps

Not an asynchronous event bus or external audit service.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
