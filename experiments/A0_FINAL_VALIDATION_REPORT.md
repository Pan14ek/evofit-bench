# A0 Final Validation Report

## Decision

**Final decision: FAIL**

**A0 status: NOT READY TO TAG**

Every completed local validation criterion passed. The hosted CI criterion is not met: no workflow ran for the validation commit because the attempted push was rejected by the automatic approval review. The specification requires CI success for PASS, so the final decision is FAIL pending that gate. No Git tag was created.

## Validation record

- Validation date/time: 2026-10-05 23:50 Europe/Kyiv (EEST)
- Validated source revision: `ce16466d3739ea84fada13f90264de9ed4b5ab12`
- Working tree during canonical runs: clean; `metadata.git_dirty=false`
- CI workflow: **BLOCKED / NOT RUN**. The push to `origin` for `codex/a0-final-validation` was rejected by automatic approval review because it would export repository source/history to a GitHub destination that was not verified as trusted or user-owned. No alternate publishing route was used.
- Migration validation: **PASS**, Alembic revision `0001_a0_schema`
- Quality checks: **PASS** — Ruff, Ruff format, mypy, Bandit, import-linter (4 contracts kept), architecture tests (3 passed), migration test, unit tests, and integration tests
- Test count: **29 passed**
- Coverage: **91.17%** (required: at least 80%)

## Deterministic reset

Two independent successful `make experiment-reset` runs produced these fingerprints:

| Reset | Seed ID | Users | Tasks | Notifications | Audit events | SHA-256 |
|---|---:|---:|---:|---:|---:|---|
| #1 | `a0-v1` | 100 | 500 | 0 | 0 | `074aba9f614f5cc348729261dbc4ce2588ae5d270a2f8adb54cc01df0dfe89d9` |
| #2 | `a0-v1` | 100 | 500 | 0 | 0 | `074aba9f614f5cc348729261dbc4ce2588ae5d270a2f8adb54cc01df0dfe89d9` |

**Seed reset reproducibility: PASS.** Both complete logical fingerprints match.

## Canonical runs

### Smoke

- Run ID: `a0-smoke-validation`
- Profile: `a0-smoke-v1`
- Result: **PASS** — 30-second run, no warm-up, 0 Locust failures, 0 business 5xx, valid sampler and evidence package
- Generated summary: 141 requests; 30 runtime samples
- Source revision: `ce16466d3739ea84fada13f90264de9ed4b5ab12`; `git_dirty=false`

### Baseline

- Run ID: `a0-baseline-validation`
- Result: **PASS** — canonical no-fault workload completed without request failures or business 5xx
- Workload: `a0-baseline-v1`; profile SHA-256 `98517928987a9cdede42b9c10ef6546ad97cb09f9142984fa5ce29efe8ed013c`
- Warm-up: `a0-warmup-v1`; profile SHA-256 `54bae6cffd29a35b3d5b4bcefe29a32c60bc667342706fab39598782fb42f643`
- Fitness configuration: version `1`; SHA-256 `5ad60e373463ea459e192bf85d82704ca9aa1c217c4abf4d8caeb66924059ecb`
- Warm-up fingerprint before: `074aba9f614f5cc348729261dbc4ce2588ae5d270a2f8adb54cc01df0dfe89d9`
- Warm-up fingerprint after: `074aba9f614f5cc348729261dbc4ce2588ae5d270a2f8adb54cc01df0dfe89d9`
- Warm-up read-only invariant: **PASS**, full logical fingerprints equal
- Request count: `2332`
- Failure count: `0`
- Business 5xx count: `0`
- p50: `11.0 ms`; p95: `22.0 ms`; p99: `47.0 ms`
- Throughput: `19.511867599000553 requests/s`
- Application CPU delta: `15.55 seconds`
- Application RSS maximum: `100995072 bytes`
- Runtime samples: `119` of approximately `120`; minimum accepted was `108`
- Sampler exit: `0`; required fields, timestamps, RSS positivity, CPU monotonicity, process-start continuity, and RSS maximum consistency: **PASS**
- Application process start time at both measurement boundaries: `1791232818.39`
- Metadata source revision matches the validated Git `HEAD`; `git_dirty=false`

The checked-in and copied workload profile bytes match, and the metadata SHA-256 matches those bytes. Effective Locust weights were regression-tested as derived from the selected profile. Fitness configuration values and reliability evidence identifiers match the A0 configuration.

### Baseline evidence package

`experiments/results/a0-baseline-validation/` contains:

```text
metadata.json
seed_fingerprint.json
seed_fingerprint_before_warmup.json
seed_fingerprint_after_warmup.json
workload_profile.yaml
warmup_profile.yaml
metrics_before.txt
metrics_after.txt
runtime_metrics.csv
locust_stats.csv
locust_stats_history.csv
locust_failures.csv
locust_exceptions.csv
summary.json
logs/app.log
```

Mandatory evidence-file integrity checks passed.

## Fault sanity validation

- Run ID: `a0-fault-sanity-validation` (separate from canonical runs)
- Mode: `EXPERIMENT_MODE=true`; `fail_next_n_notifications=1`
- HTTP result: expected `500`
- Task, notification, and audit database state: unchanged
- Full logical seed fingerprint: unchanged
- `notifications_created_total`: `0 -> 0`
- `business_operation_failures_total`: `0 -> 1`
- `business_rule_rejections_total`: `0 -> 0`
- Fault controls reset to all zero; app restored with `EXPERIMENT_MODE=false`
- Result: **PASS**

Evidence is saved in `experiments/results/a0-fault-sanity-validation/fault_sanity.json` and `logs/app.log`.

## Known limitations

1. Locust scheduling is concurrent; exact request order is not replayed.
2. Request weights define a workload distribution, not an exact deterministic request trace.
3. Runtime metric sampling adds a small instrumentation cost.
4. This A0 validation does not establish statistical experimental conclusions.
5. The canonical run is environment-specific; later B0/B1/P comparisons must use the same controlled environment or account for environmental effects.

The run demonstrates only that A0 is measurable and reproducible enough to serve as an experimental starting state. It does not support conclusions about performance, reliability comparisons, or adaptation effectiveness.

## PASS criteria status

| Criterion | Result |
|---|---|
| CI success | **NOT MET** — hosted workflow not run because branch push was rejected |
| Migration, quality, tests, coverage | PASS |
| Seed reset and warm-up reproducibility | PASS |
| Application process continuity | PASS |
| Runtime sampler exit and completeness | PASS |
| Canonical smoke and baseline runs | PASS |
| Clean source revision and required provenance | PASS |
| Workload and fitness profile hashes | PASS |
| No unexpected load failures; business 5xx zero | PASS |
| Required runtime resources valid | PASS |
| Fault sanity validation | PASS |

Because CI success is a mandatory PASS criterion and remains unavailable, **A0 final validation = FAIL**. Re-run/confirm hosted CI after the validation branch is safely published, then reassess the final decision. Do not tag before all PASS criteria are satisfied.
