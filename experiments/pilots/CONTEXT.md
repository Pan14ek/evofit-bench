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
- `generate_pilot01_results.py` — validates existing EXP-01/02 artifacts and derives the CSV table.
- `run_pilot01_measurement.py` — invokes the existing Import Linter, module test, Locust task file, runtime sampler, and EXP-01/02 validators for this pilot only.

## Constraints and known limits

PILOT-01 measures the A0.1 engineering evaluator response to one controlled source dependency edge. Its repeated runs are technical repetitions of one condition, not independent architecture changes. It does not establish independent semantic coverage or Method P adaptation effectiveness. Keep the S1 source fault on its isolated branch and worktree; preserve the exact source patch and revision. Raw run directories are generated evidence, excluded from Git, and must retain their hashes in the export archive.

## Verification

Use the focused pilot tests and result generator, then the repository's documented `make development-quality` command with a disposable PostgreSQL database. Never interpret `Coverage_P`, `Coverage_ref`, G1/G4, or measured DA01 outcomes from this pilot.
