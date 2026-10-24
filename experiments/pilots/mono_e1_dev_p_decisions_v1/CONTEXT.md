# Context — `experiments/pilots/mono_e1_dev_p_decisions_v1`

> **Audience:** contributors. **Type:** navigation context only; never method input, authority, or reference evidence.

## Responsibility

Contains the TEST_ONLY synthetic architecture-evolution decision experiment, its preregistered scorer-side reference, replayable raw traces, and descriptive report.

## Landmarks

- `scenarios_v1.json` defines eight synthetic before/after transitions, initial fitness inputs, obligation assumptions, evaluator capabilities, and available evidence.
- `reference_v1.json` and its SHA-256 sidecar declare expected operations before execution; scorer-side only.
- `runner.py` builds and verifies V3 bundles, archives each exact input bundle, and calls the existing `run_adaptation()` pipeline.
- The synthetic evaluator is authored by the existing TEST_ONLY integration fixture builder and runs as a subprocess; its artifact and output digests are retained with scenario-prefixed raw files.
- `report_v1.md` and `results_v1.json` separate eight scenario-level outcomes from 24 technical repetitions. Coverage assessments, actual evidence-record inventories, proposed configurations, governance decisions, and actual post-adaptation coverage are distinct fields.
- B0_SYNTH is a derived unchanged-configuration assessment using the same verified input and Method P `current_coverage`; it is not an independently executed baseline arm.
- `raw/` preserves runs and exact input archives; raw execution evidence and preregistered reference bytes are immutable during reporting corrections.

## Boundaries

This experiment is independent of canonical MONO-E1 A0.3→A0.4 and DA01 runs. It does not change Method P, `P_ALGORITHM_STATUS`, G1/G4, MONO-E1 readiness, frozen protocols, or official B0. Synthetic author-declared outcomes are not independent ground truth or scientific validation. Keep the reference out of method bundles, sidecars, environment variables, and execution calls.

## Validation

Use the focused `tests/unit/test_mono_e1_dev_p_decisions.py` cases and reproduce with the documented `execute` then `score` commands in the report. Preserve raw artifacts; never overwrite an existing run directory or edit the frozen reference after execution.
