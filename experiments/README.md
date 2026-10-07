# Controlled experiments

The [architecture-evolution experimental design specification](design/ARCHITECTURE_EVOLUTION_SCENARIOS_V1.md) defines the controlled architecture-evolution trajectory, ground-truth rules, research questions, and experimental data requirements for DA01–DA14.

## Research artifact layout

- `design/` defines the experimental protocol.
- `schemas/` defines machine-readable research contracts.
- `scenarios/` contains pre-registered scenario specifications and frozen ground truth.
- `results/` contains generated raw runs and remains ignored by Git.
- `evidence/` contains curated immutable evidence.

`make load-smoke` and `make load-baseline` reset to the configured deterministic `SEED_ID` (default `a0-v1`), wait for readiness, and run the checked-in YAML profile. Baseline sequence: experiment reset, readiness, read-only warm-up, unchanged seed fingerprint check, `metrics_before.txt`, runtime sampler, measured Locust workload, `metrics_after.txt`, and measured-interval summary/provenance. There is no application restart between warm-up and measurement. Run output is under `experiments/results/<run-id>/` and generated results are ignored by Git.

`runtime_metrics.csv` samples application-process CPU seconds, resident memory, and virtual memory from `/metrics` at the configured interval. A run fails unless the sampler exits successfully, collects at least 90% of expected samples, and has valid timestamps, positive RSS, and a non-decreasing CPU counter. `process_start_time_seconds` must match in `metrics_before.txt` and `metrics_after.txt`. `summary.json` derives CPU delta, memory start/end/max, and business 5xx rate from process samples and start/end counter snapshots. Missing required metrics fail the run; no collector-process resource usage is treated as application evidence.

`metadata.json` records the Git SHA and dirty state, fitness YAML version and exact-byte SHA-256, logical seed fingerprint, workload profile ID and exact-byte SHA-256, application/runtime environment, database version, Docker image ID where available, and fault configuration. Copies of the workload and seed fingerprint accompany the run. Fault controls are process-local, explicit, disabled by default, and should be reset after each fault experiment. These are raw A0 evidence, not scientific conclusions or adaptation decisions.
