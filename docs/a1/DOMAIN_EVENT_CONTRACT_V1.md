# ΔA6 in-process domain-event contract v1

**Status:** frozen for W4 preparation on 2026-10-21 after approval of the W4
proposal. **Implementation status:** dispatcher and Notification-side handlers
are prepared; Task service and application composition are not yet wired to
them. Full REST/PostgreSQL transaction acceptance remains pending final ΔA6
integration.

## Purpose and boundary

This contract replaces the direct Task→Notification implementation dependency
at the later ΔA6 integration stage. It describes synchronous facts within the
existing one-process, one-database application. It is not a messaging system,
event store, durable event log, or delivery guarantee.

The contract is owned by `app/events/contracts.py`; synchronous dispatch is
owned by `app/events/dispatcher.py`; Notification-side reaction is owned by
`app/modules/notifications/event_handlers/__init__.py`. The application composition
root must register handlers explicitly. No dynamic module scan is permitted.

## Event schema

The Python contract version is `1.0.0`. Each immutable, validated event also
has a versioned `event_type` literal. Additional fields are rejected.

| Event type | Required payload | Optional payload | Notification behavior |
| --- | --- | --- | --- |
| `task.assigned.v1` | `task_id: UUID`, `assignee_id: UUID`, `actor_id: UUID` | None | `TASK_ASSIGNED`, message `Task {task_id} was assigned to you` |
| `task.status_changed.v1` | `task_id: UUID`, `actor_id: UUID`, `previous_status: TaskStatusValue`, `new_status: TaskStatusValue` | `assignee_id: UUID \| None` (defaults to `None`) | If assigned, `TASK_STATUS_CHANGED`, message `Task {task_id} changed to {new_status}`; otherwise no notification |

`TaskStatusValue` is owned by the event contract so Notifications does not
import Task internals. Its values are `TODO`, `IN_PROGRESS`, `DONE`, and
`CANCELLED`. Contract v1 has no event ID or timestamp because events are neither
queued nor persisted; this makes no claim about replay or duplicate delivery.

### Accepted Python representation deviation

The W0 freeze fixes the event names, payload fields and types, immutability,
unknown-field rejection, status vocabulary, and dispatch/transaction semantics.
The implementation encodes those frozen semantics with Pydantic `BaseModel`
payloads, `Literal` event tags, and a `StrEnum` status mirror. These concrete
Python representation choices are the accepted deviation from the freeze's
technology-neutral typed-contract description; they do not change the event
interface or promise a wire format. `TaskStatusValue` stays owned by the event
contract to avoid a production dependency on Task internals;
`test_event_task_status_values_match_canonical_task_status_enum` checks that its
member names and values exactly match the canonical `TaskStatus` enum.

## Registration and dispatch

- `EventDispatcher.register(event_type, handler)` explicitly appends a
  synchronous handler and returns `True`. Registering the same event type and
  same handler identity again returns `False` without adding another call.
- A different callable claiming the same module-qualified handler identity is
  rejected with `DuplicateHandlerRegistrationError`. Distinct handler
  identities are allowed and execute in registration order.
- Coroutine handlers are rejected. There is no await, executor, thread,
  background task, broker, outbox, queue, retry, or event-store dependency.
- `dispatch(session, event)` requires a registered handler for the concrete
  event type; otherwise it raises `MissingEventHandlerError`.
- The dispatcher passes the exact caller-provided SQLAlchemy `Session` to each
  handler on the caller's stack. It never commits or rolls back.
- Handler exceptions propagate unchanged. The Task service remains responsible
  for catching the error and rolling back the operation's existing transaction.
- Dispatch logs event type and handler identity/count at debug level. It never
  logs event payload values.

## Integration boundary and acceptance

When ΔA2–ΔA5 are integrated and W0 schedules the dependent ΔA6 source change:

1. Task assignment emits `task.assigned.v1` after recording the audit row and
   before its existing commit.
2. A Task status change emits `task.status_changed.v1` after its audit row and
   before its existing commit, with the status snapshot and optional assignee.
3. Notification handlers write using the same session and do not commit. An
   unassigned status change produces no notification, as today.
4. Any handler failure reaches the existing Task error path, which rolls back
   Task, Notification, and Audit changes and preserves REST failure metrics.
5. The final architecture evaluator proves the event-contract dependency,
   registration, and absence of a direct Task→Notifications service import.

Only application-level PostgreSQL tests after integration can establish the
full rollback requirement. The exact future cases, response/metric assertions,
database precautions, and commands are recorded in
[`DOMAIN_EVENTS_INTEGRATION_PLAN.md`](DOMAIN_EVENTS_INTEGRATION_PLAN.md).

## Requirement-to-test matrix

| Requirement | Test evidence | Current status |
| --- | --- | --- |
| A1-EVENT-01: typed v1 contract and synchronous dispatch | `tests/unit/test_domain_events.py` payload validation, status-enum compatibility, inline invocation, order, and caller-session cases; `tests/integration/test_a1_domain_events.py` PostgreSQL delivery checks | Unit verified; dispatcher/Notification PostgreSQL preparation tests added; Task operation integration pending |
| A1-EVENT-02: handler failures propagate without autonomous transaction decisions | Unit exception and no-commit/no-rollback tests; PostgreSQL injected-handler rollback/recovery preparation test; future Task/Notification/Audit REST rollback cases in integration plan | Unit verified; Notification transaction preparation covered by PostgreSQL test; full application proof pending integration |
| A1-EVENT-03: allowed event dependency and forbidden direct service dependency | W2-owned A1 source evaluator on the integrated source SHA | Not implemented by W4 |
| A1-EVENT-04: idempotent registration | Duplicate-registration and Notification registration bootstrap tests | Unit verified; application bootstrap wiring pending |
| External-infrastructure boundary | Dispatcher construction and synchronous dispatch unit test with an in-memory Session mock | Unit verified; no new infrastructure required by this code path |
