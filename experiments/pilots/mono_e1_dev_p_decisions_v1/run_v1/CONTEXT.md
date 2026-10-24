# Context — `run_v1`

Generated outputs for MONO_E1_DEV_P_DECISIONS_V1. `execution_manifest.json` binds
the pre-registration commit, Method P source identity, environment, and scenario
bundle digests. `raw_records_manifest.json` binds every retained raw file. The
scorer writes `results_v1.json`, `report_v1.md`, and `score_manifest.json` only
after all raw execution records exist. `results_v1.json` schema version 2 and
`report_v1.md` separate eight scenario-level outcomes from 24 technical
repetitions. They preserve pre-adaptation and candidate-configuration coverage
separately from evidence-record inventories; no aggregate evidence-completeness
verdict is inferred from coverage. Actual post-adaptation coverage is not measured.

The `raw/` directory stores scenario-prefixed records and deterministic ZIP
archives of the exact V3 method input bundles. Extract a bundle archive to a new
directory and run `verify_method_bundle_v3()` before reuse. Do not overwrite this
run; use a new versioned output directory for a reproduction. B0_SYNTH is a
derived unchanged-configuration assessment based on the same verified input and
Method P's `current_coverage`; it is not an independently executed baseline arm.
