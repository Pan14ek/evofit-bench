UV ?= uv
BASE_URL ?= http://localhost:8000
RUN_ID ?= $(shell date -u +%Y%m%dT%H%M%SZ)
PROFILE ?= a0-smoke-v1
DURATION ?= 30
RUN_STARTED_AT_UTC ?= $(shell date -u +%Y-%m-%dT%H:%M:%SZ)

.PHONY: install run test test-unit test-integration lint typecheck security architecture-test quality migration-test db-upgrade seed seed-fingerprint reset wait-ready load-smoke load-baseline experiment-reset export-metrics metadata

install:
	$(UV) sync --extra dev

run:
	$(UV) run python -m scripts.run_app --reload

test:
	$(UV) run python -m pytest --cov=app --cov-report=term-missing --cov-report=xml

test-unit:
	$(UV) run python -m pytest --no-cov tests/unit tests/architecture

test-integration:
	$(UV) run python -m pytest --no-cov tests/integration

lint:
	$(UV) run ruff check .
	$(UV) run ruff format --check .

typecheck:
	$(UV) run mypy app scripts tests

security:
	$(UV) run bandit -q -r app scripts

architecture-test:
	$(UV) run lint-imports
	$(UV) run python -m pytest --no-cov tests/architecture

quality: lint typecheck security architecture-test migration-test test

migration-test:
	$(UV) run python -m scripts.validate_migrations

db-upgrade:
	$(UV) run alembic upgrade head

seed:
	$(UV) run python -m scripts.seed_db

seed-fingerprint:
	$(UV) run python -m scripts.seed_fingerprint

wait-ready:
	$(UV) run python -m scripts.wait_ready --url $(BASE_URL)

reset:
	$(UV) run python -m scripts.reset_db

load-smoke:
	mkdir -p experiments/results/$(RUN_ID)/logs
	$(MAKE) experiment-reset
	$(MAKE) wait-ready
	$(UV) run python -m scripts.run_load_experiment --run-id $(RUN_ID) --profile load/profiles/a0-smoke-v1.yaml --url $(BASE_URL)
	@docker compose logs --no-color --since=35s app > experiments/results/$(RUN_ID)/logs/app.log 2>/dev/null || true

load-baseline:
	mkdir -p experiments/results/$(RUN_ID)/logs
	$(MAKE) experiment-reset
	$(MAKE) wait-ready
	$(UV) run python -m scripts.run_load_experiment --run-id $(RUN_ID) --profile load/profiles/a0-baseline-v1.yaml --url $(BASE_URL)
	@docker compose logs --no-color --since=125s app > experiments/results/$(RUN_ID)/logs/app.log 2>/dev/null || true

experiment-reset:
	docker compose up -d postgres
	docker compose build app
	docker compose stop app
	docker compose run --rm --no-deps app python -m scripts.reset_db
	docker compose up -d --wait app

export-metrics:
	$(UV) run python -m scripts.export_metrics --url $(BASE_URL) --run-id $(RUN_ID)

metadata:
	$(UV) run python -m scripts.collect_run_metadata --run-id $(RUN_ID) --workload-profile load/profiles/$(PROFILE).yaml --run-started-at-utc $(RUN_STARTED_AT_UTC) --measurement-duration-seconds $(DURATION) --url $(BASE_URL)
