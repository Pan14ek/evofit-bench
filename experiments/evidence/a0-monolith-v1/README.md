# A0 Monolith v1 evidence package

This directory preserves curated evidence for the validated `A0_MONOLITH` baseline. A0 is the single-process FastAPI application with PostgreSQL described by the repository’s A0 architecture state; this package makes no claims about later architectures or comparative performance conclusions.

## Revisions and status

The canonical experiments measured source revision `ce16466d3739ea84fada13f90264de9ed4b5ab12`, with clean working-tree metadata. The current frozen `main` revision is `b78b0967be937634b7762baccf5ac6892b279a73`. The validation report records `a7acbc7b0bec705e7b288d70d401e55ca85ee18b` as the report-only follow-up; the diff from the measured revision through the current frozen revision contains only `experiments/A0_FINAL_VALIDATION_REPORT.md`. No application or experimental code changed after measurement.

The report at [`experiments/A0_FINAL_VALIDATION_REPORT.md`](../../A0_FINAL_VALIDATION_REPORT.md) records final validation **PASS** and A0 **READY TO TAG**. It also says that no tag was created as part of that validation update. At package creation, the repository already has `arch-a0-monolith-v1` pointing at the current frozen `main` revision; this task did not create or move it.

## Canonical and supporting runs

- `smoke/` — canonical smoke run `a0-smoke-validation`. Its run ID, architecture, measured revision, clean-tree status, profile and warmup hashes, fitness configuration, seed fingerprint, summary, and required evidence files agree with the validation report. It records 141 requests and 30 runtime samples, with zero failures and business 5xx responses.
- `baseline/` — canonical baseline run `a0-baseline-validation`. Its provenance and evidence match the report, including the profile and fitness hashes, deterministic warmup fingerprints, summary and runtime evidence. It records 2,332 requests, 119 runtime samples, zero failures and business 5xx responses.
- `fault-sanity/` — validation support run `a0-fault-sanity-validation`, with the report-referenced `fault_sanity.json` and application log.
- `seed-reset/` — validation support run `a0-seed-reset-validation`; both reset fingerprints match the report’s SHA-256 and logical counts.

## Inspected result directories

| Directory | Classification | Reason |
|---|---|---|
| `a0-smoke-validation` | `CANONICAL` | Explicitly named in the report; matching run provenance, profile hashes, fitness config, seed fingerprint, summary and evidence. |
| `a0-baseline-validation` | `CANONICAL` | Explicitly named in the report; matching run provenance, profile hashes, fitness config, seed fingerprint, summary and evidence. |
| `a0-fault-sanity-validation` | `VALIDATION_SUPPORT` | Separate fault validation named in the report; result JSON and log are present. |
| `a0-seed-reset-validation` | `VALIDATION_SUPPORT` | Two independent reset fingerprints named in the report; both are present and equal the expected fingerprint. |
| `a0-acceptance-smoke` | `INTERMEDIATE / EXPLORATORY` | Not named as canonical; `git_commit_sha` is null and it lacks the final validation provenance/profile contract. |
| `a0-v1-baseline` | `INTERMEDIATE / EXPLORATORY` | Legacy run on `46d11876ab5e00d25cde5f40244f8d84c0845e80`, not the measured revision; legacy metadata/profile shape. |
| `a0-v1-smoke` | `INTERMEDIATE / EXPLORATORY` | Legacy run on `46d11876ab5e00d25cde5f40244f8d84c0845e80`, not the measured revision; legacy metadata/profile shape. |

`experiments/results/.gitkeep` is a placeholder, not a result directory. Legacy metrics and warmup Locust files from the exploratory directories were intentionally excluded. No exploratory run was copied into this package.

## Included evidence and integrity

The smoke and baseline folders contain metadata, summaries, runtime metrics, Locust statistics/history/failures/exceptions, before/after Prometheus snapshots, seed fingerprints, workload and warmup profiles, and their application logs. The logs are retained because they are reasonably sized and provide run context. The support folders contain the two deterministic reset fingerprints and the fault sanity JSON/log.

`manifest.json` records the package identity, validation and revision details, canonical/support run IDs, profile/configuration/seed hashes, summary values, directory classifications, and SHA-256 plus size for each included evidence file. `checksums.sha256` covers every package file other than itself, including this README and manifest.

## Scope and limitations

This is validation and baseline evidence, **not the final statistical dissertation dataset**. The report’s limitations apply: Locust scheduling is concurrent and does not replay exact request order; request weights describe a distribution rather than a deterministic trace; runtime sampling adds instrumentation cost; the validation establishes no statistical experimental conclusions; and later B0/B1/P comparisons require a controlled common environment or accounting for environmental effects. The run demonstrates that A0 is measurable and reproducible enough to serve as an experimental starting state, not comparative performance, reliability, or adaptation effectiveness.

No expected canonical evidence file was missing in the inspected raw results. Raw files under `experiments/results/` were not modified.
