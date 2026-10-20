# PILOT-02 inherited evaluator execution protocol v1

**Status:** DEVELOPMENT execution protocol; approved before these evaluator runs.
**Scope:** fresh A0.1 execution of the four evaluator representations inherited from frozen A0.
**Does not authorize:** measured DA01, positive semantic pair proof, `Coverage_P`, `Coverage_ref`, G1 or G4.

## Source and configuration

The frozen A0 representation catalog identifies four inherited rows and metrics but carries no executable artifact paths. The separately pinned PILOT-02 profile V2 therefore binds each unchanged A0 row to an executable A0.1 source artifact. Every such binding is labeled `A0_1_DEVELOPMENT_ADAPTER`; it does not claim the artifact path was present in frozen A0. The A0 source catalog bytes remain the candidate's parent configuration bytes.

The exact evaluators, raw measurements and validity treatment are:

| A0 representation | Executable evidence | Prespecified observation |
|---|---|---|
| `REP_A0_PERF_TEST_HTTP_P95` | Existing `load/locustfile.py`, Locust headless, using the versioned `PILOT_01_WORKLOAD.yaml` profile as a fresh PILOT-02 workload parameter. | Locust aggregated request count, failed request count, p50/p95/p99 milliseconds and requests/second from `locust_stats.csv`. `95%` is the reported Locust statistic; no histogram-derived percentile. |
| `REP_A0_PERF_RUNTIME_HTTP_DURATION` | Existing A0.1 EXP-01 runtime collector and unchanged Prometheus instrumentation. | Preserve before/after exposition, interval deltas for histogram buckets/count/sum, labels and timestamps. Do not calculate p50/p95/p99 from buckets. Preserve runtime sampling count and source identity observation. |
| `REP_A0_REL_TEST_INTEGRATION` | Exact node `tests/integration/test_api_flows.py::test_enabled_faults_delay_fail_deterministically_and_reset`. | Pytest status, passed/failed/skipped counts, elapsed time, JUnit, stdout/stderr. Use a disposable PostgreSQL database whose name contains `evofit`; the fixture drops and recreates `public`. |
| `REP_A0_REL_RUNTIME_FAILURES` | Same EXP-01 runtime interval as the HTTP-duration row. | Preserve business 5xx numerator, business-request denominator, rate when defined, operation-failure counters and separate business-rule rejection counters. Zero remains an observed zero; missing series or denominator remains unavailable. |

## Execution controls

- Use the pinned A0.1 application tree `cdff9a6c3cee870e1eca2a5f5f3eb3202b0b1f08` from a clean committed source revision.
- Use a unique `evofit-pilot02-...` Compose project. The runner builds and starts its app/database, resets the A0 seed with `scripts.reset_db`, recreates the app to reset process counters, then records the exact setup and cleanup commands.
- Preserve the exact workload profile bytes. It specifies five users, spawn rate one per second, 30 seconds, no warm-up, and the stated six-operation request mix. No prior PILOT-01 measurements are admitted.
- Run Locust while the EXP-01 runtime collector collects a 15-second interval with a one-second sample interval. The runtime collector's read-only activity and the Locust requests are both in the observed interval.
- Run the integration node separately against a dedicated disposable PostgreSQL test database. The runner records the database container ID and database name, not credentials.
- Save all raw bytes and outputs under a new `experiments/results/<run-id>/`. Do not overwrite an existing run ID.
- After the four observations, run the existing Method P runner against the newly generated, validated EXP-01 bundle with profile version 2 and the existing TEST_ONLY assumption set V2. Preserve the complete Method P run under the same result directory. The existing runner supplies only its explicitly TEST_ONLY execution sidecar to `run_adaptation()`; the four inherited metric outputs are not semantic pair proof.
- A run can be reported as measured only if the source revision is clean, Locust emitted a parseable aggregate row, EXP-01 bundle and representation evidence validate, and pytest emitted its actual process result. Individual failures remain measured failures rather than being converted to passes.

## Interpretation and comparison

The four observations evaluate controls that B0 leaves unchanged and Method P retains. One exact execution is linked to both arms because the evaluator source, configuration, workload, A0.1 source revision and selected node are byte-identical; it is a shared observation, not two independent executions. Method P's two architecture-compliance candidate evaluators remain separately executed by the existing PILOT-02 runner. Report process durations for Locust, EXP-01, pytest, B0 and P candidate evaluators, plus the existing `run_adaptation()` timer. Do not call these wall-clock totals a speedup or infer semantic coverage from evaluator output.

Runtime source-to-container identity, evaluator adequacy, applicability authority and independent semantic pair validity remain separate fields. Any unresolved identity or scope stays explicitly unverified/unknown.
