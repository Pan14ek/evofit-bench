# Context — `experiments/pilots`

> **Audience:** human researchers and AI coding agents. **Type:** descriptive navigation for bounded development pilots; not a frozen DA01 input, authority record, or measured DA01 result.
> **Navigation:** follow root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and `experiments/CONTEXT.md` first.

## Responsibility

Store pilot-specific protocols, reports, derived result tables, and narrow tools that consume the repository's existing DEVELOPMENT evidence collectors.

## Local landmarks

- `PILOT_01_EXPECTATION.md` — expected S0/S1 evaluator outcomes recorded before formal repeated measurements.
- `PILOT_01_REPORT.md` — evidence-backed experimental report and reproducibility limits.
- `PILOT_01_MANUSCRIPT_UA.md` — Ukrainian manuscript subsection based only on collected results.
- `PILOT_01_WORKLOAD.yaml` — the fixed A0.1 pilot load profile.
- `PILOT_01_RESULTS.csv` and `PILOT_01_DESCRIPTIVE_STATISTICS.json` — generated from digest-validated run evidence.
- `PILOT_01_S1_FAULT.patch` — exact isolated source-level S1 intervention.
- `PILOT_02_PROTOCOL.md` — frozen, restricted A0-to-A0.1 architecture-compliance protocol.
- `PILOT_02_DEVELOPMENT_ASSUMPTIONS_V1.json` and `PILOT_02_DEVELOPMENT_ADDENDUM_V1.md` — prospective, TEST_ONLY execution assumptions and their relation to the frozen protocol.
- `PILOT_02_A0_1_METHOD_INPUT_PROFILE_V1.json` — exact DEVELOPMENT mapping profile, pinned by the P verifier.
- `run_pilot02_method_p.py` — validates an EXP-02 run, exports the existing V3 input, verifies the profile, and runs the existing P pipeline.
- `PILOT_02_REPORT.md`, `PILOT_02_RESULTS.csv`, `PILOT_02_MANUSCRIPT_UA.md`, and `PILOT_02_RAW_EVIDENCE.zip` — evidence-derived pilot outputs and their checksums.
- `PILOT_02_RAW_EVIDENCE_CONTINUATION.zip` — separate continuation evidence archive; the first run archive remains unchanged.
- `generate_pilot01_results.py` — validates existing EXP-01/02 artifacts, independently derives runtime metrics from raw Locust/process CSV files, cross-checks the manifest values with documented tolerances, and writes the CSV table and descriptive summary.
- `run_pilot01_measurement.py` — invokes the existing Import Linter, module test, Locust task file, runtime sampler, and EXP-01/02 validators for this pilot only.

## Constraints and known limits

PILOT-01 report and manuscript record the A0.1 engineering evaluator response to one controlled source dependency edge. Its repeated runs are technical repetitions of one condition, not independent architecture changes. It does not establish independent semantic coverage or Method P adaptation effectiveness. Keep the S1 source fault on its isolated branch and worktree; preserve the exact source patch and revision. Raw run directories are generated evidence, excluded from Git, and must retain their hashes in the export archive. The result generator must derive request counts, failures, latency percentiles, throughput, CPU delta, peak RSS, and sample count from the raw CSVs and reject manifest-only metric edits even when artifact hashes validate.

## PILOT-02 limits

PILOT-02 is a restricted DEVELOPMENT case with an independently pending
denominator and semantic reference. Its source-bound profile and exact-pair
diagnostics do not authorize P operations, claim P coverage, or turn the
manually established A0.1 reference into a P output. Preserve the raw archive,
profile bundle, actual Method P trace, and unavailable outcomes as-is.

The author-authorized continuation uses an explicit TEST_ONLY assumption set
to exercise operation planning with authentic evaluator output. Preserve its
separate archive and TEST_ONLY label; a candidate may be materialized while
semantic coverage and governance remain unresolved.

## Verification

Use the focused pilot tests and result generator, then the repository's documented `make development-quality` command with a disposable PostgreSQL database. Never interpret `Coverage_P`, `Coverage_ref`, G1/G4, or measured DA01 outcomes from this pilot.
