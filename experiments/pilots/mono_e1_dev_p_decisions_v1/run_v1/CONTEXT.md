# Context — `run_v1`

Generated outputs for MONO_E1_DEV_P_DECISIONS_V1. `execution_manifest.json` binds
the pre-registration commit, Method P source identity, environment, and scenario
bundle digests. `raw_records_manifest.json` binds every retained raw file. The
scorer writes `results_v1.json`, `report_v1.md`, and `score_manifest.json` only
after all raw execution records exist.

The `raw/` directory stores scenario-prefixed records and deterministic ZIP
archives of the exact V3 method input bundles. Extract a bundle archive to a new
directory and run `verify_method_bundle_v3()` before reuse. Do not overwrite this
run; use a new versioned output directory for a reproduction.
