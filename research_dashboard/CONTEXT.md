# Context — `research_dashboard`

> Research visualization code for the synthetic MONO_E1_DEV_P_DECISIONS_V1 results. This directory is not a Method P input, scorer, protocol, or scientific authority.

## Responsibility

Load and validate the merged PR #48 results without writing to experiment artifacts; derive descriptive views; present a local Streamlit dashboard; and export publication figures.

## Landmarks

- `data.py` — read-only exploratory loading, schema/digest checks, and strict publication-export readiness validation.
- `metrics.py` — scenario/repetition summaries, categorical transitions, correctness, duration, report comparison, and evidence inventory.
- `charts.py` — interactive Plotly chart preparation.
- `figures.py` — deterministic Matplotlib SVG/PNG exports and CLI.
- `app.py` — six Streamlit pages; presentation only.
- `schemas/results_v2.schema.json` — dashboard reader schema for the corrected result format.
- `screenshots/` — UI samples for code review, not experiment evidence.

## Constraints

Keep the eight scenario records distinct from the 24 technical repetitions. Preserve UNKNOWN and missing measurements. Candidate-configuration coverage is not actual post-adaptation coverage. Never infer evidence completeness from a coverage status. B0_SYNTH is a derived unchanged-configuration assessment, not an executed baseline. Preserve the D2 expected HOLD / observed REJECT mismatch. Do not modify the experiment, scorer, reference, inputs, or raw evidence. Exploratory loading may warn and continue when optional artifacts are unavailable; publication export must call `validate_publication_export_readiness()` and fail before output creation when required source provenance is incomplete.

## Validation

Run `make test-research-dashboard`, `make research-figures`, and the documented development checks. Publication export reloads source artifacts, verifies the complete non-empty checksum inventory and report summaries before writing; `--force` only applies after that preflight passes.
