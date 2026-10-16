# EvoFitBench

EvoFitBench is a controlled research platform for studying the evolution of architectural fitness-function configurations. Its frozen starting point is **A0_MONOLITH**; the current application code after DA01 is **A0_1_CAPABILITY_MODULES**, a capability-oriented monolith that still uses one FastAPI/Uvicorn application process, one PostgreSQL database, synchronous internal calls, and a versioned REST API. Planned distributed/cloud-native states are research scenarios, not currently deployed services.

For project context, architecture, experiment safeguards, technology stack and test strategy, start with **[docs/README.md](docs/README.md)**. Automated coding agents should also read **[AGENTS.md](AGENTS.md)**. The authoritative scientific protocol and frozen artifacts remain under `experiments/` and `fitness/`.

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

Integration tests require a disposable PostgreSQL database: their fixture drops and recreates its `public` schema, then upgrades it through Alembic before tests. `make migration-test` independently validates a clean migration, required tables, the recorded revision, and basic insert/read behavior. `make quality` includes migration validation and all tests, and creates terminal and XML coverage reports. CI provisions PostgreSQL and runs the same checks.

## Reset and seed

`SEED_ID` is the canonical seed identity used by application settings, the seeder, Locust ID generation, and provenance (default `a0-v1`). Seed IDs use UUIDv5; task statuses are exactly 200 TODO, 150 IN_PROGRESS, 100 DONE, and 50 CANCELLED. Every fourth task is unassigned; all other assignment and creator IDs are deterministic. Seed timestamps start at 2026-01-01 UTC and advance by fixed seconds.

## Load and evidence

`make load-smoke` and `make load-baseline` reset the dataset and wait for readiness. Baseline then runs a 30-second read-only warm-up and a 120-second measurement on the same application process. Warm-up reads only tasks, task lists, and the task summary, and its before/after seed fingerprints must match. The measured profile is 20 users at 5 users/s; smoke is 5 users at 1 user/s for 30 seconds. Versioned profiles and request mixes live in `load/profiles/`; they are provisional controls, not scientific findings.

Each successful run writes `metadata.json`, `seed_fingerprint.json`, `summary.json`, `workload_profile.yaml`, `metrics_before.txt`, `metrics_after.txt`, `runtime_metrics.csv`, `locust_stats.csv`, warm-up fingerprint records, and `logs/app.log`. Summary counters use before/after Prometheus deltas. CPU and memory come from the running application process via `/metrics`; the metadata collector process is not used as runtime evidence. Metadata binds the commit and dirty state, fitness configuration, seed fingerprint, workload profile, and environment.

```bash
RUN_ID=baseline-001 make load-smoke
```

Generated files are placed in `experiments/results/<run-id>/` and are ignored by Git. Use `GET /metrics` for Prometheus exposition.

## Experiment faults

Fault controls default to off. Set `EXPERIMENT_MODE=true` for the app process to register `/internal/experiment/faults` and enable the in-process fault hooks. `GET` reads settings, `PUT` replaces them, and `DELETE` resets them. Supported settings are `notification_delay_ms`, `task_delay_ms`, and `fail_next_n_notifications`; delay is bounded at five seconds and notification failures are consumed deterministically. Keep this process-local experiment control out of ordinary business configuration.

## Telemetry semantics

Expected business rejections are recorded by `business_rule_rejections_total` with bounded reason labels and do not count as service failures. `business_operation_failures_total` counts unhandled operation failures that return 5xx. Reliability evidence consists of integration-test results, business HTTP 5xx rate, and operation-failure counts. `notifications_created_total` advances only after the transaction that stores the notification commits. HTTP metrics use route templates and classify business, operational, experiment, and unmatched traffic.

No authentication or authorization is implemented, as specified for this local research baseline. Do not expose the app or experiment endpoints to an untrusted network.
