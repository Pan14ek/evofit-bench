# Context — `app/modules/notifications/event_handlers`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and all parent `CONTEXT.md` files before this package.

## Responsibility

Notification-side handlers for versioned, synchronous Task domain events.

## Local landmarks

- `__init__.py` — event reactions and explicit handler registration. The Python
  import path is `app.modules.notifications.event_handlers`.

## Established conventions

Use shared event contracts and the caller-provided SQLAlchemy session. Persist
through `notifications.public.create_notification`, which does not commit. Keep
registration explicit and deterministic; dispatcher registration is idempotent.
The local import remains lazy so this preparation branch has no partial ΔA2
facade inventory; its mypy attribute ignore is removed when W1's facade lands.

## Constraints and known gaps

Do not import Task internals or register through dynamic discovery. This package
is not wired into Task operations or application bootstrap at the W4 stage.
Full REST/PostgreSQL rollback remains pending final ΔA6 integration.

## Verification and further reading

See `tests/unit/test_domain_events.py`, `docs/a1/DOMAIN_EVENT_CONTRACT_V1.md`,
and `docs/a1/DOMAIN_EVENTS_INTEGRATION_PLAN.md`.
