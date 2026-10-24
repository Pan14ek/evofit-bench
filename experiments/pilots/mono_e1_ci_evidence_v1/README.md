# MONO-E1 CI evidence package

This package consolidates two distinct empirical tracks for the Ukrainian monograph: source-bound A0.3/A0.4 CI observations and finite EVAL-01/EVAL-02 evaluator controls (Track A), plus eight synthetic Method P DEVELOPMENT scenarios with 24 technical repetitions (Track B). It is not an official MONO-E1/B0/P experiment.

## Contents

- `evidence_tables_v1.json` — complete derived tables, provenance, verification results, claim matrix, and figure metadata.
- `table_01_scope_v1.csv` through `table_06_limitations_v1.csv` — publication tables.
- `claim_to_evidence_v1.csv` — claim IDs, evidence strength, permitted/prohibited interpretations, and verification routes.
- `figure_to_claim_map_v1.json` — figure titles, axes, captions, exact claim mapping, source-data boundary, and SHA-256 for each existing dashboard export.
- `coverage_assessment_transitions.{svg,png}`, `operations_and_governance.{svg,png}`, `execution_duration_by_operation_scenario.{svg,png}` — exports from the existing read-only dashboard figure exporter; no new visualization logic.
- `../../../docs/MONO_E1_CI_EXPERIMENTAL_EVIDENCE_REPORT_UA.md` — Ukrainian monograph-ready report.

## Reproduce and verify

```bash
make test-monograph-evidence
```

The read-only verifier validates the P raw manifest and all 57 run checksums, verifies eight V3 input archives, reruns the pinned scorer on a temporary copy, compares P results/report/score manifest, checks canonical A0.3/A0.4 source and evaluator identities, recalculates EVAL binary metrics from case rows, verifies report/CSV/archive parity, and confirms figure exports against validated source data. It writes no experiment or publication files.

To regenerate only derived tables, report, and dashboard-export figures after source evidence changes:

```bash
uv run --frozen --extra dev --with-requirements research_dashboard/requirements.lock \
  python -m experiments.pilots.verify_monograph_evidence write-derived
```

`write-derived` never executes Method P or evaluator studies and never edits retained raw records, manifests, references, canonical checkpoints, EVAL archives, G1/G4, or readiness flags.

## Scientific boundary

Three technical repetitions per synthetic scenario are not independent scenarios. The reference is AUTHOR_DECLARED / DEVELOPMENT / NON_INDEPENDENT. Candidate coverage is an assessment, not an applied outcome; actual post-adaptation coverage is `NOT_MEASURED`. D2's expected HOLD / observed REJECT and all three EVAL-02 diagnostic mismatches remain explicit. No canonical B0/P execution, human B1 comparison, production approval, deployment/runtime observation, or statistical superiority is claimed.
