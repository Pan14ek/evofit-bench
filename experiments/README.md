# Controlled experiments

## PILOT-01 DEVELOPMENT measurement

The completed [PILOT-01 report](pilots/PILOT_01_REPORT.md), [Ukrainian
manuscript subsection](pilots/PILOT_01_MANUSCRIPT_UA.md), and validated
[result table](pilots/PILOT_01_RESULTS.csv) describe a single source-level
dependency intervention with three technical repetitions per condition. This
is evaluator-behavior evidence; it is not measured DA01 evidence, independent
semantic coverage, or a B0/B1/Method P comparison. The raw outputs are ignored
under `experiments/results/`; the report documents their local archive and
verification procedure.

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

The collector runs Import Linter with `architecture/acceptance/importlinter.toml`, makes read-only Docker Compose and container/image observations, checks readiness, samples `/metrics` and process resources, and sends a fixed set of read-only loopback requests. It preserves sanitized target identity observations and exact input digests. `--base-url` only accepts unauthenticated loopback HTTP endpoints. Existing run directories are never overwritten.

Evidence bundle schema 1.1 distinguishes the collector's Git revision from the observed application identity. Schema 1.0 bundles remain readable for compatibility, but their source binding is unknown and must not be inferred from the collector revision. When Docker is available, the runtime record captures container and image IDs before and after sampling and checks whether the requested host port maps to one stable Compose `app` container. A different observed revision label or changed target identity is `mismatch`; missing target identity remains `unverified`. A matching `org.opencontainers.image.revision` label remains an unauthenticated claim, so source binding is still `unverified`. Schema 1.1 validation rejects `verified` source binding because this DEVELOPMENT pipeline has no authoritative source-to-image provenance verifier. Docker identity, runtime metrics, and collector Git HEAD do not by themselves prove which source revision produced the serving application.

The checked-in fitness YAML is still declared for `A0_MONOLITH`; the bundle records its digest and marks it mismatched for A0.1. Import Linter execution, container counts, and runtime metrics do not establish `Coverage_P`, `Coverage_ref`, architectural compliance, G1/G4, or measured DA01 results. Missing stages remain explicit and make the bundle incomplete. Exit code 0 means collection is complete and the engineering architecture check passed; 1 means the architecture check detected a violation; 2 means one or more stages could not produce available evidence.
