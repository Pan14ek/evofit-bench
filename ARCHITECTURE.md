# A0 architecture

| Property | A0 value |
| --- | --- |
| Architecture State | A0_MONOLITH |
| Deployment Units | 1 |
| Application Processes | 1 |
| Database | 1 PostgreSQL |
| Internal Communication | synchronous Python calls |
| External API | REST |
| Message Broker | none |

```text
HTTP / API
    |
    v
Services
    |
    v
Repositories
    |
    v
SQLAlchemy Models / PostgreSQL
```

The application is organized by horizontal technical layers. All capabilities run in one FastAPI/Uvicorn process, backed by one PostgreSQL database. Notifications and audit records are created with ordinary synchronous Python calls; there are no internal HTTP clients, separate services, broker, module databases, or distributed transactions.

For task assignment and status changes, the service loads and updates the task, creates any notification, and records the audit event in one SQLAlchemy session transaction. The service commits only after all synchronous side effects succeed. If a side effect fails, it rolls the transaction back so task state, notification, and audit remain consistent. User and task creation likewise commit the entity and its audit event together. This local transaction boundary is specific to A0.

The API layer depends on services and request/response schemas. Services call repositories and persistence models. Repositories do not depend on the API; models do not depend on API or service code. `tests/architecture` checks these prohibitions and CI runs the check.
