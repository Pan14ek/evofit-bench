UV ?= uv
BASE_URL ?= http://localhost:8000
RUN_ID ?= $(shell date -u +%Y%m%dT%H%M%SZ)
PROFILE ?= a0-smoke-v1
DURATION ?= 30
RUN_STARTED_AT_UTC ?= $(shell date -u +%Y-%m-%dT%H:%M:%SZ)
EXP01_RUN_ID ?= exp01-dev-$(shell date -u +%Y%m%dT%H%M%SZ)
ARCHITECTURE_STAGE ?= auto
IMPORT_LINTER_CACHE_DIR ?= .import_linter_cache
DEVELOPMENT_REGRESSION_TESTS = \
	tests/unit/test_p_input_contract_v11.py \
	tests/unit/test_p_input_authority_validation.py \
	tests/unit/test_p_input_v2_isolation.py \
	tests/unit/test_p_applicability_ruleset_v1.py \
	tests/unit/test_p_applicability_policies_v1.py \
	tests/unit/test_p_impact_v1.py \
	tests/unit/test_p_semantic_pairs_v1.py \
	tests/unit/test_p_operations_v1.py \
	tests/unit/test_p_candidate_governance_v1.py \
	tests/unit/test_p_adaptation_evidence_v1.py \
	tests/unit/test_p_executable_candidate_identity.py \
	tests/unit/test_p_interface_readiness.py \
	tests/unit/test_g1_method_decision_register.py \
	tests/unit/test_context_documents.py \
	tests/unit/test_mono_policy_review_inventory.py \
	tests/unit/test_mono_e1_preflight.py \
	tests/unit/test_mono_e1_a03_fitness_candidate.py \
	tests/unit/test_mono_e1_a03_dev_fitness_config.py \
	tests/unit/test_architecture_stage_checks.py \
	tests/unit/test_exp01_evidence.py \
	tests/unit/test_exp02_fitness_evidence.py \
	tests/unit/test_pilot01_results.py \
	tests/unit/test_eval02_runner.py \
	tests/unit/test_eval02_postrun_validation.py \
	tests/unit/test_pilot02_method_input_profile.py \
	tests/unit/test_pilot02_candidate_evaluators.py \
	tests/unit/test_pilot02_testonly_execution.py \
	tests/unit/test_b0p_development.py \
	tests/unit/test_b0p_git_inventory.py \
	tests/unit/test_b0p_e1_execution.py \
	tests/integration/test_exp03_method_bridge.py \
	tests/integration/test_exp04_evidence_admission.py \
	tests/unit/test_da01_inputs_and_isolation.py::test_container_negative_probes_cannot_reach_oracle_history_network_or_other_output \
	tests/integration/test_p_applicability_v3.py \
	tests/integration/test_p_governed_adaptation_v1.py

DEVELOPMENT_PROTECTED_TESTS = \
	tests/unit/test_da01_execution.py \
	tests/unit/test_research_schema_foundation.py

.PHONY: install run test test-unit test-integration development-regression-test development-lint development-typecheck development-quality lint typecheck security architecture-test quality migration-test db-upgrade seed seed-fingerprint reset wait-ready load-smoke load-baseline exp01-smoke experiment-reset export-metrics metadata research-dashboard research-figures test-research-dashboard

install:
	$(UV) sync --extra dev

run:
	$(UV) run python -m scripts.run_app --reload

research-dashboard:
	$(UV) run --frozen --with-requirements research_dashboard/requirements.lock streamlit run research_dashboard/app.py

research-figures:
	$(UV) run --frozen --with-requirements research_dashboard/requirements.lock python -m research_dashboard.figures

test-research-dashboard:
	$(UV) run --frozen --extra dev --with-requirements research_dashboard/requirements.lock \
		python -m pytest -q --no-cov -p no:cacheprovider tests/unit/test_research_dashboard.py

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
	$(UV) run bandit -q -r app scripts experiments/execution/tooling research_dashboard

architecture-test:
	$(UV) run lint-imports --config architecture/acceptance/importlinter.toml --cache-dir $(IMPORT_LINTER_CACHE_DIR)
	$(UV) run python -m scripts.check_architecture_stages --stage $(ARCHITECTURE_STAGE)

quality: lint typecheck security architecture-test migration-test test

development-regression-test:
	$(UV) run --frozen --extra dev --with-requirements research_dashboard/requirements.lock \
		python -m pytest -q --no-cov -p no:cacheprovider tests/unit/test_research_dashboard.py
	$(UV) run --frozen --extra dev \
		python -m pytest -q --no-cov -p no:cacheprovider \
		$(foreach test,$(DEVELOPMENT_PROTECTED_TESTS),--ignore=$(test)) \
		$(DEVELOPMENT_REGRESSION_TESTS)
	$(UV) run python -m pytest -q --no-cov -p no:cacheprovider tests/unit/test_exp01_evidence.py
	$(UV) run python -m pytest -q --no-cov -p no:cacheprovider tests/unit/test_exp02_fitness_evidence.py

development-lint:
	$(UV) run ruff check . \
		--extend-exclude=tests/unit/test_da01_execution.py \
		--extend-exclude=tests/unit/test_research_schema_foundation.py
	$(UV) run ruff format --check . \
		--extend-exclude=tests/unit/test_da01_execution.py \
		--extend-exclude=tests/unit/test_research_schema_foundation.py

development-typecheck:
	$(UV) run mypy app scripts tests research_dashboard \
		--exclude '(^|/)test_da01_execution\.py$$' \
		--exclude '(^|/)test_research_schema_foundation\.py$$'

development-quality: development-lint development-typecheck security architecture-test migration-test development-regression-test

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

exp01-smoke:
	docker compose up -d --build --wait
	$(UV) run python -m scripts.exp01_evidence --architecture-state A0_1_CAPABILITY_MODULES --fitness-config fitness/configs/a0_1-capability-modules.dev.yaml --base-url $(BASE_URL) --run-id $(EXP01_RUN_ID)

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
