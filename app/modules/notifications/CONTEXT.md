# Context — `app/modules/notifications`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `app/modules/CONTEXT.md` before this file.

## Responsibility

Synchronous in-app notification persistence.

## Local landmarks

- `__init__.py`
- `api.py`
- `model.py`
- `repository.py`
- `schemas.py`
- `service.py`
- `event_handlers/` — explicit reactions to versioned Task events, prepared
  for later ΔA6 composition-root registration.

## Established conventions

Notification faults exercise rollback in caller's transaction.
Event handlers call local notification persistence and preserve that
caller-owned transaction through the approved `public.create_notification`
facade; registration is explicit and idempotent through the shared dispatcher.

## Constraints and known gaps

No external delivery, broker, durable consumer, outbox or remote notification
service. The prepared in-process handlers are not wired into Task operations at
the W4 stage.
The facade is supplied by W1's ΔA2 work; PostgreSQL preparation tests skip
until that module is present on the integrated source.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
