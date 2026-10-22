# Context — `app/events`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `app/CONTEXT.md` before this file.

## Responsibility

Versioned in-process event contracts and a synchronous dispatcher shared by
capability modules. This package contains no event persistence or transport.

## Local landmarks

- `contracts.py` — immutable v1 Task event payloads and event-owned status values.
- `dispatcher.py` — explicit ordered registration, synchronous invocation and
  required-handler checks.

## Established conventions

Callers pass the active SQLAlchemy `Session` to `dispatch`; the dispatcher does
not commit or roll back. Register handlers explicitly and keep registration
order deterministic. Handler exceptions propagate unchanged.

## Constraints and known gaps

No dynamic discovery, queue, broker, outbox, worker, retry, event store or
delivery guarantee. The dispatcher is prepared for controlled ΔA6 integration;
the current Task service is not wired to it. Full application rollback remains
unverified until that integration runs against disposable PostgreSQL.

## Verification and further reading

See `tests/unit/test_domain_events.py` and `docs/a1/DOMAIN_EVENT_CONTRACT_V1.md`.
The full REST/rollback acceptance plan is in
`docs/a1/DOMAIN_EVENTS_INTEGRATION_PLAN.md`.
