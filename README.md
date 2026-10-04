# EvoFitBench

EvoFitBench is a controlled research platform for studying how architectural fitness-function configurations evolve as software architecture changes. This repository implements only **A0_MONOLITH**, the baseline: one deployable Python application process, one PostgreSQL database, synchronous internal calls, and a versioned REST API. It is intentionally a small layered monolith.

## Run locally

Requirements: Python 3.12, `uv`, and Docker Compose for PostgreSQL. Copy `.env.example` to `.env`, then run:

```bash
make install
docker compose up -d postgres
make db-upgrade
make seed
make run
```

The API listens at `http://localhost:8000`; interactive OpenAPI docs are at `/docs`. Alternatively, `docker compose up --build` starts PostgreSQL and the application together. Startup applies Alembic migrations.

## Tests and quality checks

```bash
docker compose up -d postgres
docker compose exec -T postgres createdb -U evofit evofit_test
make test-unit
TEST_DATABASE_URL=postgresql+psycopg://evofit:evofit@localhost:5432/evofit_test make test-integration
make lint
make typecheck
make security
make architecture-test
TEST_DATABASE_URL=postgresql+psycopg://evofit:evofit@localhost:5432/evofit_test make quality
```

Integration tests require a disposable PostgreSQL database: their fixture drops and recreates its `public` schema. `make quality` includes all tests and creates terminal and XML coverage reports. CI provisions PostgreSQL and runs the same checks.

## Reset and seed

`make experiment-reset` stops the app container, resets the local Compose database, applies migrations, loads the deterministic seed, checks 100 users and 500 tasks, and restarts the app. Run it only against the Compose database; the reset script refuses database names without `evofit`. `make seed` reloads the same fixed records after schema setup. Seed IDs use UUIDv5 and fixed `a0-v1` naming; task statuses are exactly 200 TODO, 150 IN_PROGRESS, 100 DONE, and 50 CANCELLED. Every fourth task is unassigned; all other assignment and creator IDs are deterministic. Seed timestamps start at 2026-01-01 UTC and advance by fixed seconds.

## Load and evidence

Start from the same dataset with `make experiment-reset`. Then run `make load-smoke` for 5 users at 1 user/s for 30 seconds or `make load-baseline` for a 30-second warm-up plus 120-second measurement at 20 users and 5 users/s. The fixed request mix and Locust code live in `load/locustfile.py`; these settings are provisional workload profiles, not scientific results.

The load targets write `locust_stats.csv`, a compact `summary.json`, `metrics.json`, and `metadata.json` (including fault settings, duration, CPU time, and peak RSS where available) beneath the run directory. The directory also reserves `logs/` for app logs. For a separately managed run, set one ID and collect evidence:

```bash
RUN_ID=baseline-001 make load-smoke
RUN_ID=baseline-001 make export-metrics
RUN_ID=baseline-001 PROFILE=smoke make metadata
```

Generated files are placed in `experiments/results/<run-id>/` and are ignored by Git. Use `GET /metrics` for Prometheus exposition.

## Experiment faults

Fault controls default to off. Set `EXPERIMENT_MODE=true` for the app process to register `/internal/experiment/faults` and enable the in-process fault hooks. `GET` reads settings, `PUT` replaces them, and `DELETE` resets them. Supported settings are `notification_delay_ms`, `task_delay_ms`, and `fail_next_n_notifications`; delay is bounded at five seconds and notification failures are consumed deterministically. Keep this process-local experiment control out of ordinary business configuration.

No authentication or authorization is implemented, as specified for this local research baseline. Do not expose the app or experiment endpoints to an untrusted network.
