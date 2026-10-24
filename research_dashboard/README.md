# Method P Research Dashboard

This optional, read-only research visualization presents the retained
MONO_E1_DEV_P_DECISIONS_V1 development pilot. It is not an official MONO-E1
completion report, a Method P runtime, or evidence of an approved experiment.
It reads local JSON and manifest files and runs without PostgreSQL or external
API calls.

## Install and launch

Install the repository's development dependencies, then launch the dashboard.
Its UI and figure packages are pinned separately in `requirements.lock`, so
they do not change the repository's experiment dependency lock:

    uv sync --frozen --extra dev
    make research-dashboard

The default source is
experiments/pilots/mono_e1_dev_p_decisions_v1/run_v1/results_v1.json.
Use the Results JSON path field in the sidebar to inspect another corrected v2
result file. Loading validates its schema and nearby manifests before rendering.

## Pages

1. **Experiment overview** — source identity, calculated counts and agreement,
   governance distribution, checksum inventory, B0_SYNTH provenance, and
   interpretation limits.
2. **Architectural coverage transitions** — categorical current assessment →
   observed operation → candidate assessment → governance, with scenario,
   operation, status, and governance filters.
3. **Method P decision explorer** — one scenario and technical repetition at a
   time, showing recorded architecture metadata, obligation applicability,
   pair evidence, operation, candidate assessment, governance, declared
   reference, and hashes.
4. **Decision correctness and governance** — expected/observed matrices,
   scenario and repetition classification, and all mismatches, including D2.
5. **Execution performance** — individual repetition durations, filtered dot
   plot and distribution, plus descriptive summaries in milliseconds.
6. **Evidence and reproducibility** — manifest/source hashes, per-repetition
   evidence availability, pair statuses, evaluator records, and artifact paths.

All summaries are derived from the selected structured records. The dashboard
shows 8 scenarios separately from 24 technical repetitions; repetitions are
not treated as independent cases.

## Candidate coverage and measured coverage

pre_adaptation_coverage is the assessed current configuration.
candidate_configuration_coverage is the assessment recorded for the proposed
candidate configuration. The candidate was not applied and re-evaluated, so
actual_post_adaptation_coverage remains NOT_MEASURED. The transition matrix
and figures use “candidate configuration coverage assessment” explicitly and
do not present it as measured improvement.

B0_SYNTH is a DERIVED_UNCHANGED_CONFIGURATION_ASSESSMENT based on Method P's
current assessment on the same verified input. It is not an independently
executed baseline arm; no runtime comparison or statistical superiority claim
is available.

Reference labels are AUTHOR_DECLARED / DEVELOPMENT / NON_INDEPENDENT.
D2's expected HOLD governance versus observed REJECT is preserved as a
mismatch in all three technical repetitions. A safety-oriented REJECT may be
defensible, but it still differs from the declared reference.

The dashboard does not change these research gates:
P_ALGORITHM_STATUS=NOT_READY, G1=INCOMPLETE, G4=NOT_AUTHORIZED, and
MONO-E1=NO-GO.

## Publication figures

Generate three deterministic figures without starting Streamlit:

    make research-figures

The default output directory is
experiments/results/research_figures/mono_e1_dev_p_decisions_v1/ (ignored by
Git). It contains SVG and 300 dpi PNG versions of coverage assessment
transitions, operations/governance outcomes, and execution duration by
operation/scenario. Existing files are preserved unless the CLI is explicitly
called with --force:

    uv run --frozen --with-requirements research_dashboard/requirements.lock \
      python -m research_dashboard.figures --force

Figure generation cross-checks calculated summaries against report_v1.md
before writing output. It does not edit the source artifacts.

## Validation

    make test-research-dashboard
    make development-quality

These checks validate the reader and presentation implementation. They do not
establish independent reference validity, G1/G4 approval, or measured DA01
results.
