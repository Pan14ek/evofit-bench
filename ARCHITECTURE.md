# A0.1 capability-module architecture

| Property | Current value |
| --- | --- |
| Architecture State | `A0_1_CAPABILITY_MODULES` |
| Deployment Units | 1 |
| Application Processes | 1 FastAPI/Uvicorn process |
| Database | 1 PostgreSQL database |
| Internal Communication | synchronous Python calls |
| External API | the A0 REST contract |
| Message Broker | none |

The code is organized into five capability packages: `app.modules.users`, `app.modules.tasks`, `app.modules.notifications`, `app.modules.reporting`, and `app.modules.audit`. `app.main` composes their routers into one FastAPI application. The packages are not separately deployed services.

Each capability keeps its own internal dependency direction. Direct calls between capabilities remain allowed and are listed in `architecture/states/A0_1_CAPABILITY_MODULES.yaml`: Tasks calls Users, Notifications, and Audit; Users calls Audit; Reporting calls Tasks. DA01 does not add public module APIs or enforce a dependency graph.

Shared infrastructure remains in `app.config`, `app.db`, `app.experiment`, `app.observability`, `app.api`, `app.models.base`, and `app.services.errors`. `app.db.model_registry` imports the capability models so Alembic and the application use the same declarative `Base` and metadata.

The public business routes remain `/api/v1/users`, `/api/v1/users/{user_id}`, `/api/v1/tasks`, `/api/v1/tasks/{task_id}`, `/api/v1/tasks/{task_id}/assign`, `/api/v1/tasks/{task_id}/status`, `/api/v1/notifications`, and `/api/v1/reports/task-summary`. Health, metrics, and experiment-control routes remain in the shared API package.

Task assignment and status changes still mutate the task, create notification and audit rows, and commit once through the same SQLAlchemy session. A notification failure rolls the operation back as a unit. Database tables, columns, constraints, foreign keys, indexes, enum values, and Alembic revision are unchanged.

The `architecture/acceptance/importlinter.toml` configuration checks internal layering within each capability. `tests/architecture/test_module_structure.py` checks the exact DA01 manifest, shared infrastructure, and removal of horizontal business files. The frozen A0 evaluator remains at `fitness/evaluators/a0/importlinter.toml`; it is an experimental artifact and is not the current engineering acceptance configuration.

DA01 changes package organization only. It adds no deployment unit, process, database, broker, internal HTTP call, event mechanism, distributed transaction, retry policy, or independent module deployment. Experiment controls and metric names and semantics remain unchanged.
