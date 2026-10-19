# PILOT-01 — real measurements of evaluator behavior

- **Status:** completed DEVELOPMENT pilot; not a measured DA01 comparison.
- **Measurement date:** 2026-10-19.
- **Base revision:** `5d285a04da00863088f8cd88a10afb3faaf02ddb` (the fetched `origin/main`, including PR #20).
- **S0 revision:** `5d285a04da00863088f8cd88a10afb3faaf02ddb`.
- **S1 revision:** `ccbfb002e1fc71d9dcaadf11635d449b8a881cac`, parented directly on the base.

## A. Experimental objective

The research question was: **Can the existing A0.1 architecture fitness representations reliably detect a genuine source-level architectural dependency violation while preserving evidence provenance and reproducibility?**

PILOT-01 tests the behavior of the existing Import Linter and module checks when one source dependency violates an existing layer rule. It does not evaluate or compare B0, B1, or Method P adaptation.

## B. Experimental design

Two committed source conditions were run:

- **S0 — conforming:** clean A0.1 source at the base revision.
- **S1 — controlled violation:** one delayed import was added inside `app.modules.notifications.repository.add_notification`: it imports `notifications.api.router`. The existing `Notifications module internal layering` Import Linter contract prohibits this repository-to-API edge. The change is recorded in [the exact patch](PILOT_01_S1_FAULT.patch), and the source commit is isolated on branch `research/pilot01-s1-fault`; it is not part of this PR branch's application source.

The API response contract, Import Linter rules, fitness configuration, evaluator thresholds, and workload were held fixed. The delay avoids a module-initialization cycle, and the source variant completed startup and the measured workload. The predeclared expectations are in [PILOT_01_EXPECTATION.md](PILOT_01_EXPECTATION.md). One exploratory feasibility probe of S1 preceded that record; its outputs were excluded from the six formal repetitions.

Each condition had three technical repetitions. Repetitions are repeat measurements of the same source condition; there is one independent architecture intervention. Each repetition used a fresh, condition-specific Compose project/database and re-created the application container. S0 was measured three times, then S1 three times. There was no randomized or interleaved run order.

The fixed 30-second workload used five Locust users at 1 user/second, no warm-up, one-second runtime sampling, and the request mix in [PILOT_01_WORKLOAD.yaml](PILOT_01_WORKLOAD.yaml). It is an A0.1-labelled copy of the existing smoke mix. Import Linter, the notification layer pytest case, the module-structure test, EXP-01, EXP-02, Locust and process telemetry were collected using the existing repository evaluators/collectors through the pilot-specific runner.

## C. Environment

| Item | Observed value |
| --- | --- |
| Host | macOS 26.6.2, ARM64, 10 logical/physical CPUs, 16 GiB RAM |
| Python / pytest | 3.12.14 / 8.4.2 |
| Import Linter / Locust | 2.15 / 2.46.6 |
| Docker Engine / Compose | 29.8.2 / 5.5.1 |
| PostgreSQL | 16.15 (Debian 16.15-1.pgdg13+2) |
| Container limits | No Compose resource limits configured |
| S0 app image ID | `sha256:8607ff76b0bb22760b96dd07d049f104bbe3498120d39954e59e2b2a2e04dc94` |
| S1 app image ID | `sha256:d42c0e69fffb16f2444200ffa5cb3f8fe9e2dad7c35914cfeeadcc516b029c50` |
| PostgreSQL image ID | `sha256:c319f2a8182bcdcbb3297d568e2a9cc9e7da3a624438e14b63921c719817e1b6` |

The fitness configuration digest was `3f8c952afd00f97f00b84955cc85fdf8dc5cbe32b52e6577173b8aa5a12fbad`; the Import Linter configuration digest was `5e938273faa86b4584886e2ede5700b35b064d5e54fe04b0c3d1e50278c64eb0`. Both digests were identical for all six runs. The exact workload digest was `bca4dac8994cdf8021670beb4d19075ef45dc93df5fb464e98fef6188ab6c168`.

EXP-01 runtime application source identity was **unverified in all six runs**. The recorded container/image identity and the collector's Git revision do not prove which source revision produced the serving image. The distinct image IDs are recorded as observations, not source provenance.

## D. Actual results

### D.1 Evaluator and evidence outcomes

| Condition | Runs | Import Linter | Module-structure check | EXP-01 / EXP-02 |
| --- | ---: | --- | --- | --- |
| S0 | 3 | 0 broken contracts; exit 0; all five contracts kept | Passed in all 3 runs | Valid and complete / valid in all 3 |
| S1 | 3 | 1 broken contract; exit 1; four kept, one broken: `Notifications module internal layering` | Passed in all 3 runs | Valid and complete / valid in all 3 |

The separate full architecture verification passed for S0: `make architecture-test` exited 0; Import Linter kept five contracts and broke none; architecture pytest reported 6 passed. On S1, the same `make architecture-test` command exited 2 because the Import Linter prerequisite returned 1 (four contracts kept, one broken). Running `uv run pytest --no-cov -q tests/architecture` separately returned 1: `test_module_dependencies_follow_local_layer_order[notifications]` failed as expected and five other tests passed. The independent module-structure check passed on S1.

### D.2 Measurements by formal repetition

Durations are seconds; RSS is bytes; latency is milliseconds. The authoritative row-level values, environment JSON, and artifact references are in [PILOT_01_RESULTS.csv](PILOT_01_RESULTS.csv).

| Run | Lint exit / broken | Lint s | Structure s | Requests / failures | p50 / p95 / p99 ms | Requests/s | App CPU Δ s | App RSS max B | Samples |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| S0-r01 | 0 / 0 | 0.162 | 0.362 | 115 / 0 | 14 / 33 / 76 | 4.589 | 1.29 | 99,033,088 | 32 |
| S0-r02 | 0 / 0 | 0.198 | 0.399 | 138 / 0 | 12 / 21 / 43 | 4.741 | 1.46 | 98,885,632 | 32 |
| S0-r03 | 0 / 0 | 0.315 | 0.417 | 134 / 0 | 12 / 45 / 58 | 4.607 | 1.53 | 98,893,824 | 32 |
| S1-r01 | 1 / 1 | 0.296 | 0.463 | 136 / 0 | 11 / 28 / 130 | 4.675 | 1.59 | 99,475,456 | 32 |
| S1-r02 | 1 / 1 | 0.186 | 0.412 | 134 / 0 | 10 / 28 / 46 | 4.609 | 1.41 | 98,795,520 | 32 |
| S1-r03 | 1 / 1 | 0.212 | 0.490 | 140 / 0 | 11 / 21 / 35 | 4.824 | 1.39 | 100,229,120 | 32 |

All six Locust runs recorded zero request failures. All six runtime samplers recorded 32 samples. The S1 notification API remained usable during the workload; this observation does not establish other runtime or semantic properties.

### D.3 Descriptive summaries

The generated [statistics JSON](PILOT_01_DESCRIPTIVE_STATISTICS.json) reports min/mean/max for the three technical repetitions per condition. For example, mean Import Linter duration was 0.225 s (S0) and 0.231 s (S1); mean p95 latency was 33.0 ms (S0) and 25.7 ms (S1). The repetitions are not independent architecture changes and these differences are not inferential results.

## E. Reproducibility and evidence preservation

The run directories are ignored by Git and retained locally under `experiments/results/`:

- `pilot01-s0-r01` through `pilot01-s0-r03`, with matching `-exp01` directories.
- `pilot01-s1-r01` through `pilot01-s1-r03`, with matching `-exp01` directories.

Every run manifest inventories the original stdout/stderr, Locust output, runtime metrics, EXP-01 bundle, EXP-02 representation evidence, selected inputs, and environment records by size and SHA-256. The result generator rechecks those inventories and reruns the EXP-01/02 validators before emitting the CSV and statistics.

The six runs used the following command shape from the PR worktree; each repetition value 1, 2, and 3 was run once per condition:

```bash
PYTHONDONTWRITEBYTECODE=1 /private/tmp/evofit-pilot01-main-env/bin/python \
  experiments/pilots/run_pilot01_measurement.py \
  --checkout /Users/oleksii_makieiev/Documents/startups/evofit-pilot01-s0 \
  --condition S0 --repetition 1
```

For S1, the checkout was `/Users/oleksii_makieiev/Documents/startups/evofit-pilot01-s1` and condition was `S1`. The same runner and fixed profile were used for each repetition. The exported results can be regenerated and revalidated with:

```bash
PYTHONDONTWRITEBYTECODE=1 /private/tmp/evofit-pilot01-main-env/bin/python \
  -m experiments.pilots.generate_pilot01_results
```

Source revisions: S0 `5d285a04da00863088f8cd88a10afb3faaf02ddb`; S1 `ccbfb002e1fc71d9dcaadf11635d449b8a881cac`. S1's exact patch SHA-256 is `7f52e0239d27d089aa9e456821f341259982eeaecdaca44a85404eef8a1f56d8`. Config and workload digests are listed in §C and embedded per row in the CSV. Each run's full artifact digests are embedded in that CSV and the corresponding `run_manifest.json`.

A local export archive is stored at `experiments/results/pilot01-evidence-2026-10-19.tar.gz` (SHA-256 `bb38e48ed6161d2c44b2817d3a08349aca085efc9108cedf221879ef89bdc522`). It contains all twelve raw/evidence directories, supporting architecture logs, the result CSV/statistics, expectation, workload, runner/generator, and source patch. The archive and raw run directories are marked read-only after validation. This archive is local workspace storage, not durable external artifact storage. Verify its digest and list/extract it with:

```bash
shasum -a 256 experiments/results/pilot01-evidence-2026-10-19.tar.gz
tar -tzf experiments/results/pilot01-evidence-2026-10-19.tar.gz
mkdir -p /tmp/pilot01-export
tar -xzf experiments/results/pilot01-evidence-2026-10-19.tar.gz -C /tmp/pilot01-export
```

The committed S1 fault branch preserves the exact source revision independently of the PR branch. To recover the source patch from the PR worktree, use `git apply experiments/pilots/PILOT_01_S1_FAULT.patch` only in a disposable checkout at the stated base SHA.

### Verification status

- Focused PILOT-01 tests: **PASS** — `PYTHONDONTWRITEBYTECODE=1 /private/tmp/evofit-pilot01-main-env/bin/python -m pytest -q --no-cov -p no:cacheprovider tests/unit/test_pilot01_results.py`; 3 passed.
- Pilot Ruff check/format: **PASS** — all checks passed; the three pilot Python files were already formatted.
- `make development-quality`: **PASS**, exit 0. Ruff check passed; Ruff format checked 248 files; Mypy passed for 105 source files; Bandit passed with existing comment-parser/`nosec` warnings; Import Linter kept five contracts and broke none; architecture tests reported 6 passed; disposable PostgreSQL 16 migration validation passed at `0001_a0_schema`; DEVELOPMENT regression selection reported 331 passed in 280.68 s; the separate EXP-01 and EXP-02 suites reported 49 and 30 passed. One existing Starlette/httpx deprecation warning was reported.
- The target excluded `tests/unit/test_da01_execution.py` and `tests/unit/test_research_schema_foundation.py` from pytest, Ruff check/format, and Mypy, as specified by the Makefile. They were not treated as passes.
- `git diff --check`: **PASS** before final commit.
- S0 architecture check: **PASS**; S1 expected evaluator failure and separate architecture pytest outcomes are detailed in §D.1.
- Frozen scientific files, private oracle/scorer, and measured DA01 inputs: **not accessed or changed**.

The quality command used a new disposable PostgreSQL database named `evofit` in its own Compose project. The exact local invocation was:

```bash
UV_PYTHON=/Users/oleksii_makieiev/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
UV_PROJECT_ENVIRONMENT=/private/tmp/evofit-pilot01-main-env \
UV_CACHE_DIR=/private/tmp/evofit-pilot01-cache \
PYTHONPATH=/private/tmp/evofit-pilot01-uv \
PYTHONDONTWRITEBYTECODE=1 \
TEST_DATABASE_URL=postgresql+psycopg://evofit:evofit@localhost:5432/evofit \
make UV='python3 -m uv' development-quality
```

This engineering validation does not advance G1/G4 or Method P readiness. The raw table SHA-256 is `d1a5c2b627b1293e0f82d7fb1d324e75b97e296345ec3696deed0128c471eb0b`; the descriptive-statistics JSON SHA-256 is `644f958bf1699215b4e7093b4da6fe49d9ce021e640c7dec60d1f0659cf5a4d3`.

## F. Limitations

1. EXP-01's application source binding is unverified in every run; the evidence validates collector outputs and observed runtime records, not source-to-image provenance.
2. EXP-02 validation establishes representation-evidence structure and its recorded evaluator observations. It does not establish independent semantic adequacy, `Coverage_P`, or `Coverage_ref`; these remain `not_assessed` and `not_established`.
3. The fitness configuration is a DEVELOPMENT input. No approved policy authority or human B1 review was used. The pilot does not execute Method P or compare B0/B1/P.
4. Three repetitions per condition are technical repeats of one source intervention. The single controlled edge is not a population of independent architecture changes; no significance testing or generalization is justified.
5. The 30-second, five-user smoke workload has no configured container resource limits and no warm-up. Latency/throughput/resource differences are descriptive observations only, not a performance claim.
6. A pre-expectation S1 feasibility probe is disclosed in the predeclaration and excluded from formal data.
7. The experiment concerns one existing Python layer contract in a single-process A0.1 application. It does not establish fitness behavior for distributed or cloud-native systems.

## G. Results interpretation

The predeclared evaluator expectation was met: S0 had no broken Import Linter contracts, while every S1 repetition recorded exactly one broken contract for the injected repository-to-API dependency. The targeted notification layer-order test failed on S1; the module-structure check passed under both conditions. S1 also started and served the fixed workload without a Locust request failure.

Thus, PILOT-01 provides reproducible DEVELOPMENT evidence that the existing evaluator detects this one known source-level violation while preserving its raw outputs and validator results. It verifies fitness-evaluator behavior for this intervention, not the effectiveness of Method P adaptation or independent semantic fitness coverage.

### Minimum blockers before PILOT-02

- Method P must be ready to execute an authorized, governed adaptation; the current repository state reports `P_ALGORITHM_STATUS=NOT_READY`.
- The A0 → A0.1 experiment needs a frozen, exact B0 parent configuration and an independently justified, materializable candidate/adaptation path with evidence bound to exact bytes and exact representation–obligation pairs.
- The required G1 design/validity conditions must be complete and G4 must authorize the measured comparison; evaluator admission and independent reference evidence must support any claimed `Coverage_ref`.
- The protocol must prospectively define the independent unit, outcomes, runtime source-binding evidence, and comparable cost accounting for B0 and P. PILOT-01 supplies none of those approvals or comparative outcomes.
