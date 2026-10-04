UV ?= uv
BASE_URL ?= http://localhost:8000
RUN_ID ?= $(shell date -u +%Y%m%dT%H%M%SZ)

.PHONY: install run test test-unit test-integration lint typecheck security architecture-test quality db-upgrade seed seed-fingerprint reset load-smoke load-baseline experiment-reset export-metrics metadata

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

quality: lint typecheck security architecture-test test

db-upgrade:
	$(UV) run alembic upgrade head

seed:
	$(UV) run python -m scripts.seed_db

seed-fingerprint:
	$(UV) run python -m scripts.seed_fingerprint

reset:
	$(UV) run python -m scripts.reset_db

load-smoke:
	mkdir -p experiments/results/$(RUN_ID)/logs
	$(UV) run locust -f load/locustfile.py --headless -u 5 -r 1 --run-time 30s --host $(BASE_URL) --csv experiments/results/$(RUN_ID)/locust
	$(UV) run python -m scripts.summarize_load --csv experiments/results/$(RUN_ID)/locust_stats.csv --run-id $(RUN_ID) --profile smoke
	$(UV) run python -m scripts.export_metrics --url $(BASE_URL) --run-id $(RUN_ID)
	$(UV) run python -m scripts.collect_run_metadata --run-id $(RUN_ID) --load-profile smoke --run-duration-seconds 30 --url $(BASE_URL)
	@docker compose logs --no-color --since=35s app > experiments/results/$(RUN_ID)/logs/app.log 2>/dev/null || true

load-baseline:
	mkdir -p experiments/results/$(RUN_ID)/logs
	$(UV) run locust -f load/locustfile.py --headless -u 20 -r 5 --run-time 30s --host $(BASE_URL) --csv experiments/results/$(RUN_ID)/warmup
	$(MAKE) experiment-reset
	$(UV) run locust -f load/locustfile.py --headless -u 20 -r 5 --run-time 120s --host $(BASE_URL) --csv experiments/results/$(RUN_ID)/locust
	$(UV) run python -m scripts.summarize_load --csv experiments/results/$(RUN_ID)/locust_stats.csv --run-id $(RUN_ID) --profile experiment-baseline
	$(UV) run python -m scripts.export_metrics --url $(BASE_URL) --run-id $(RUN_ID)
	$(UV) run python -m scripts.collect_run_metadata --run-id $(RUN_ID) --load-profile experiment-baseline --run-duration-seconds 120 --url $(BASE_URL)
	@docker compose logs --no-color --since=125s app > experiments/results/$(RUN_ID)/logs/app.log 2>/dev/null || true

experiment-reset:
	docker compose up -d postgres
	docker compose stop app
	docker compose run --rm --no-deps app python -m scripts.reset_db
	docker compose up -d app

export-metrics:
	$(UV) run python -m scripts.export_metrics --url $(BASE_URL) --run-id $(RUN_ID)

metadata:
	$(UV) run python -m scripts.collect_run_metadata --run-id $(RUN_ID) --load-profile $(or $(PROFILE),smoke) --url $(BASE_URL)
