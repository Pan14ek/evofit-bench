# ΔA6 domain-event PostgreSQL integration plan

**Status:** planned; not executed. This document defines the application-level
rollback proof required after the event dispatcher is integrated into the final
ΔA6 source state. It does not claim that the current A0.1 application uses
domain events or that full application rollback has been verified.

## Scope and prerequisites

Run the integration checks only after the approved event contract is frozen and
the dependent ΔA2–ΔA5 changes are present in the integration source. The final test
must call the public REST API through the application's real composition root,
registered Notification handler, and PostgreSQL session factory. Dispatcher
unit tests alone cannot satisfy A1-EVENT-02 or the ΔA6 seeded-failure control.

Use the existing `tests/integration/client` fixture and a dedicated disposable
PostgreSQL database whose name contains `evofit`. That fixture drops and
recreates the database's `public` schema before and after the test. Do not point
it at a shared, production, or otherwise non-disposable database. Run the
integration file in its own process so the process-local fault state and
Prometheus counters are isolated from other tests.

The REST-visible baseline is in
`tests/integration/test_api_flows.py::test_task_lifecycle_notification_audit_and_report`
and `test_enabled_faults_delay_fail_deterministically_and_reset`. Keep those
regressions intact. The new test file should be isolated, for example
`tests/integration/test_a1_domain_events.py`; do not edit the shared task or
notification service files while preparing W4's dispatcher.

## Required cases

### Successful assignment

1. Create a creator and assignee through the API, then create a task.
2. Assign the task through `POST /api/v1/tasks/{task_id}/assign`.
3. Assert the unchanged `200` response and task representation, the persisted
   `assignee_id`, exactly one `TASK_ASSIGNED` notification with the existing
   message text, and one `assigned` audit row with the existing actor/details.
4. Assert the notification and audit rows are readable after the request's
   caller-owned transaction commits.

### Injected assignment-handler failure and recovery

1. Record the task fields, notification rows/count, audit rows, and relevant
   business metrics before the operation.
2. Inject a deterministic exception in the registered Notification handler
   after its notification insert has been flushed into the caller's session.
   The injection must exercise a real handler call from the REST route and must
   not modify production behavior or create a second database transaction.
3. Call the assignment route. Assert the stable `500` envelope
   (`error.code == "internal_error"`), the task remains unassigned, no new
   notification or audit row persists, and the operation-failure metric rises
   once while success counters remain unchanged.
4. Remove the injected failure and retry the same assignment. Assert `200`, the
   assignment, notification, and audit rows are all present exactly once, and
   normal success counters advance once.

### Injected status-handler failure and recovery

1. Prepare an assigned task using a successful assignment, then record the
   current status, notification and audit rows, and relevant metrics.
2. Inject an exception after the status-change Notification handler has flushed
   its notification. Submit a valid transition to `IN_PROGRESS`.
3. Assert the stable `500` envelope, the task remains `TODO`, and neither the
   attempted `status_changed` audit row nor the extra notification persists.
   Existing assignment notification/audit rows remain. Failure metrics advance
   once; status-change and notification success counters do not advance.
4. Remove the failure and repeat the transition. Assert `200`, status
   `IN_PROGRESS`, one new `TASK_STATUS_CHANGED` notification with the existing
   message text, and one new audit row. This checks that rollback leaves the
   session/application able to serve a later healthy request.

## Traceability

| Requirement | Planned test evidence | Level | Current status |
| --- | --- | --- | --- |
| A1-EVENT-01: synchronous in-process dispatch on caller session | Real API flow plus focused dispatcher unit tests for call-stack execution and shared session identity | Unit + PostgreSQL integration | Unit verified; PostgreSQL integration pending event wiring |
| A1-EVENT-02: Task/Notification/Audit atomicity | Assignment and status handler failures after notification flush; assert all attempted state is absent after rollback | PostgreSQL integration | Planned; **not verified by dispatcher unit tests** |
| A1-EVENT-03: permitted event dependency and no direct Task→Notification implementation import | W2 source-derived A1 architecture evaluator on the exact integrated source SHA | Static + controlled negative case | W2-owned; not part of this integration test |
| A1-EVENT-04: idempotent registration per bootstrap | Focused test configures the same dispatcher twice and confirms each handler runs once | Unit or application bootstrap test | Unit verified; application bootstrap test pending ΔA6 integration |
| REST compatibility and failure observability | Assert response body/status and before/after failure and success metrics for both operations | PostgreSQL integration | Planned; current baseline behavior is documented in `test_api_flows.py` |

## Execution and reporting

After ΔA6 integration, run the focused check with a verified disposable DSN:

```bash
TEST_DATABASE_URL=postgresql+psycopg://evofit:evofit@localhost:5432/evofit_test \
  uv run python -m pytest -q --no-cov -p no:cacheprovider \
  tests/integration/test_a1_domain_events.py
```

Record the exact integrated source SHA, database identity, command, result, and
whether all three tables were checked after each injected failure. If no
disposable PostgreSQL service is available, report `BLOCKED` or `SKIP` with the
actual reason. Do not label a dispatcher-only test, the current pre-event
failure test, or a mocked session as the full ΔA6 transaction proof.

At the W4 preparation stage the full application cases above remain
**not executed**. Their result stays pending until the event handler is wired
into Task assignment and status changes after the preceding architecture
stages merge.
