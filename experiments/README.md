# Controlled experiments

The [architecture-evolution experimental design specification](design/ARCHITECTURE_EVOLUTION_SCENARIOS_V1.md) defines the controlled architecture-evolution trajectory, ground-truth rules, research questions, and experimental data requirements for DA01–DA14.

For each scenario, `required_obligations_after` is the complete active obligation set Q(A_after), including obligations unaffected by the current delta. `new_obligations` contains only obligations introduced by that delta and must be a subset of the required set. An unaffected obligation remains required; it is not a removed obligation. An unaffected representation normally receives `retain` unless its semantic validity has changed.

The canonical machine-readable obligation identities, criteria, intents, and default weights are in [architectural-obligations.yaml](../fitness/catalog/architectural-obligations.yaml). The design document remains the human-readable protocol.

## Research artifact layout

- `design/` defines the experimental protocol.
- `schemas/` defines machine-readable research contracts.
- `scenarios/` contains pre-registered scenario specifications and frozen ground truth.
- `results/` contains generated raw runs and remains ignored by Git.
- `evidence/` contains curated immutable evidence.

`make load-smoke` and `make load-baseline` reset to the configured deterministic `SEED_ID` (default `a0-v1`), wait for readiness, and run the checked-in YAML profile. Baseline sequence: experiment reset, readiness, read-only warm-up, unchanged seed fingerprint check, `metrics_before.txt`, runtime sampler, measured Locust workload, `metrics_after.txt`, and measured-interval summary/provenance. There is no application restart between warm-up and measurement. Run output is under `experiments/results/<run-id>/` and generated results are ignored by Git.

`runtime_metrics.csv` samples application-process CPU seconds, resident memory, and virtual memory from `/metrics` at the configured interval. A run fails unless the sampler exits successfully, collects at least 90% of expected samples, and has valid timestamps, positive RSS, and a non-decreasing CPU counter. `process_start_time_seconds` must match in `metrics_before.txt` and `metrics_after.txt`. `summary.json` derives CPU delta, memory start/end/max, and business 5xx rate from process samples and start/end counter snapshots. Missing required metrics fail the run; no collector-process resource usage is treated as application evidence.

`metadata.json` records the Git SHA and dirty state, fitness YAML version and exact-byte SHA-256, logical seed fingerprint, workload profile ID and exact-byte SHA-256, application/runtime environment, database version, Docker image ID where available, and fault configuration. Copies of the workload and seed fingerprint accompany the run. Fault controls are process-local, explicit, disabled by default, and should be reset after each fault experiment. These are raw A0 evidence, not scientific conclusions or adaptation decisions.

## EXP-01 A0.1 DEVELOPMENT evidence

`make exp01-smoke` starts the worktree's local Docker Compose app and PostgreSQL services without resetting the database, then runs the versioned DEVELOPMENT collector. It writes a unique bundle to `experiments/results/<run-id>/evidence_bundle.json`. The direct command for an already running app is:

```bash
uv run python -m scripts.exp01_evidence \
  --architecture-state A0_1_CAPABILITY_MODULES \
  --base-url http://localhost:8000 \
  --run-id exp01-dev-smoke
```

The collector runs Import Linter with `architecture/acceptance/importlinter.toml`, makes a read-only Docker Compose observation, checks readiness, samples `/metrics` and process resources, and sends a fixed set of read-only loopback requests. It preserves raw outputs and exact input digests. `--base-url` only accepts unauthenticated loopback HTTP endpoints. Existing run directories are never overwritten.

The checked-in fitness YAML is still declared for `A0_MONOLITH`; the bundle records its digest and marks it mismatched for A0.1. Import Linter execution, container counts, and runtime metrics do not establish `Coverage_P`, `Coverage_ref`, architectural compliance, G1/G4, or measured DA01 results. Missing stages remain explicit and make the bundle incomplete. Exit code 0 means collection is complete and the engineering architecture check passed; 1 means the architecture check detected a violation; 2 means one or more stages could not produce available evidence.
