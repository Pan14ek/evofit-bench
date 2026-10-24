# Context — `experiments/pilots/mono_e1_ci_evidence_v1`

> **Audience:** researchers and contributors. **Type:** derived publication package; not an experiment run, protocol, authority, or method input.

## Responsibility

Provide reproducible tables, claim traceability, figure mapping, and a Ukrainian report for the bounded CI-only empirical scope. The verifier reads preserved evidence and writes only temporary replay/figure files during verification.

## Landmarks

- `evidence_tables_v1.json` and `table_*.csv` — deterministic publication tables derived from canonical source observations, EVAL-01/EVAL-02 artifacts, and the retained synthetic Method P raw records.
- `claim_to_evidence_v1.csv` — permitted and prohibited interpretations with evidence strength and validation route.
- `figure_to_claim_map_v1.json` — figure labels derived from validated source data, claim links, limits, and SHA-256 digests for the checked-in SVG/PNG assets.
- `../verify_monograph_evidence.py` — read-only integrity, replay, aggregate, and cross-artifact verifier; `write-derived` writes only these derived products and the Ukrainian report.
- `../../../docs/MONO_E1_CI_EXPERIMENTAL_EVIDENCE_REPORT_UA.md` — monograph-ready synthesis; no Google Docs edit or experiment execution.

## Boundaries

Track A contains source-bound A0.3/A0.4 CI observations and finite evaluator-control studies. Track B contains eight synthetic TEST_ONLY Method P scenarios and 24 technical repetitions. Keep the tracks separate. Candidate coverage is an assessment; actual post-adaptation coverage is `NOT_MEASURED`. Preserve the D2 expected HOLD / observed REJECT mismatch and all three EVAL-02 diagnostic mismatches. This package does not authorize or report official MONO-E1, canonical B0/P, B1, deployment, or runtime experiments.

## Validation

Run `make test-monograph-evidence` to verify source integrity, byte-stable derived tables/reports, figure metadata and checked-in asset digests. Matplotlib SVG/PNG render bytes can vary across platforms, so verification does not require temporary re-renders to match stored image bytes. The verifier uses existing dashboard publication preflight, the retained Method P scorer on a temporary copy, the canonical A0.3/A0.4 evidence validator, and the EVAL-02 post-run validator. It must never rewrite raw experiment artifacts.
