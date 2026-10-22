# Technology stack and working environment

This document describes the **current repository implementation**, not a mandated technology stack for the scientific method. P's models should remain technology-agnostic; this concrete Python stack is a convenient experimental instrument.

## Runtime and infrastructure

| Area | Technology actually present | Source |
| --- | --- | --- |
| Language | Python `>=3.12,<3.14`; CI uses 3.12 | `pyproject.toml`, `.github/workflows/ci.yml` |
| Dependency/build | `uv`, `uv.lock`, Hatchling | `pyproject.toml`, `Makefile` |
| HTTP | FastAPI, Uvicorn, Pydantic/Pydantic Settings | `app/main.py`, `pyproject.toml` |
| Persistence | PostgreSQL **16**, SQLAlchemy 2, psycopg 3, Alembic | `docker-compose.yml`, `alembic/` |
| Packaging | Dockerfile and Docker Compose | `Dockerfile`, `docker-compose.yml` |
| Metrics | `prometheus-client` exposition at `GET /metrics` | `app/observability/metrics.py`, `app/api/metrics.py` |
| Tracing | OpenTelemetry API/SDK; optional OTLP HTTP exporter | `app/observability/tracing.py`, env config |
| Load | Locust profiles, read-only warm-up, custom run/evidence scripts | `load/`, `scripts/run_load_experiment.py` |
| Contracts | JSON Schema (`jsonschema`), YAML (`PyYAML`), exact-byte SHA-256 | `experiments/execution/schemas/`, `tooling/contracts.py`, `hashing.py` |
| Quality | pytest, pytest-cov, Ruff, mypy, Bandit, Import Linter | `Makefile`, `pyproject.toml` |
| CI | GitHub Actions `A0 quality`, PostgreSQL 16 service | `.github/workflows/ci.yml` |

There is **no implemented** Kubernetes cluster, separate application microservices, Kafka/RabbitMQ broker, mandatory cloud provider, Java/Spring service, LLM multi-agent runtime, distributed tracer backend or external authentication component in this repository. Do not describe these as current architecture; some may be future scenario options.

The dependency constraints in `pyproject.toml` are ranges; `uv.lock` determines resolved dependency versions. Avoid copying resolved version numbers into docs unless they are required and verified.

## Setup

```bash
uv sync --frozen --extra dev
cp .env.example .env
docker compose up -d postgres
make db-upgrade
make seed
make run
```

App: `http://localhost:8000`, OpenAPI UI: `/docs`, health endpoints `/health/`, Prometheus at `/metrics`. Alternatively, `docker compose up --build` brings up PostgreSQL and app. Keep fault injection disabled unless a specifically controlled test requires `EXPERIMENT_MODE=true`.

## Safe test environment

```bash
docker compose up -d postgres
docker compose exec -T postgres createdb -U evofit evofit_test
make test-unit
EVOFIT_TEST_DATABASE_ALLOW_SCHEMA_RESET=I_CONFIRM_DISPOSABLE_DATABASE_SCHEMA_RESET \
TEST_DATABASE_URL=postgresql+psycopg://evofit:evofit@localhost:5432/evofit_test make test-integration
make lint
make typecheck
make security
make architecture-test
EVOFIT_TEST_DATABASE_ALLOW_SCHEMA_RESET=I_CONFIRM_DISPOSABLE_DATABASE_SCHEMA_RESET \
TEST_DATABASE_URL=postgresql+psycopg://evofit:evofit@localhost:5432/evofit_test make quality
```

Integration fixtures **drop and recreate the public schema** of the configured test database before applying Alembic. Before connecting, they require an exact `evofit_test` database, a loopback host, no URL query overrides of the target, and the explicit schema-reset confirmation shown above. They verify `current_database()` before dropping the schema. The migration test uses the same checks and also modifies the database. Never use production or shared database credentials with these commands.

`make quality` runs lint, mypy, Bandit, Import Linter, architecture tests, migration test and coverage tests. The configured **80% minimum is application-code coverage**, because `[tool.coverage.run].source = ["app"]`; it is not 80% coverage of P/SPEC 01/SPEC 02 logic. Track research-module test completeness via `docs/TESTING.md` and explicit focused suites.

## Data and telemetry definitions

- `GET /metrics` exposes HTTP counters/histograms with bounded route-template labels, business-rule rejections and unexpected operation failures, plus task/notification counters. Business validation/conflict rejections should not be counted as unexpected service failures.
- Optional OpenTelemetry tracing is configured at startup; an OTLP endpoint is configurable rather than required.
- Fault injection lives under `app/experiment/`; settings include `task_delay_ms`, `notification_delay_ms`, and `fail_next_n_notifications`. It is process-local, resettable, and **not** a distributed chaos framework.
- Locust outputs, runtime snapshots, sampled process resources, seed fingerprint and checksummed metadata are recorded for experimental provenance. A count, latency or p95 value is not a scientific conclusion without scenario conditions and analysis.

Useful entry points: `README.md`, `load/README.md`, `experiments/README.md`, `scripts/`, and the versioned workflow.

