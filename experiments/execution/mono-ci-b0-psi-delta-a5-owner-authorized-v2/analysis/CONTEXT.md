# Context — supplemental ΔA5 V2 post-run analysis

> **Audience:** human developers and AI coding agents. **Type:** descriptive context for derived reports; it is not protocol authority or scientific approval.
> **Navigation:** read repository `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, `experiments/execution/CONTEXT.md`, and the parent V2 `CONTEXT.md` before editing.

## Responsibility

Preserve the corrected, post-run descriptive analysis and Ukrainian monograph insertion map for hosted V2 run `40579333932`. These files derive from the byte-verified release and do not modify its raw evidence, its original analysis, or the pre-run freeze.

## Local landmarks

- `OWNER_AUTHORIZED_RESULTS_UK_V2.md` — corrected Ukrainian handoff, including explicit run limits and post-run analysis correction note.
- `analysis-summary.json` — V3 summary separates calibration B0 timing from transition-level B0 timing and keeps warmup counts separate from measured sample counts.
- `POST_RUN_ANALYSIS_CORRECTION.md` — states the difference between the frozen V2 analyzer and this derived correction.
- `MONOGRAPH_INSERTION_MAP_UK.md` — manual insertion guidance; the Google Doc was not edited.
- `transition-run-table.csv`, `evaluator-samples.csv`, `transition-samples.csv`, `technical-failures.csv`, and `evaluator-time-distributions.svg` — supporting derived tables and figure.
- `ANALYSIS_SHA256SUMS.json` — checksums for the corrected analysis files.
- `EVIDENCE_RECEIPT.json` — links the corrected analysis to the immutable GitHub release, its downloaded outer-archive digest, and successful bundle verification.

## Evidence handling

The frozen run remains tied to commit `b34165dc2e8a857be84a12d42d1545453e626fd7` and its pre-run analyzer digest. The supplemental V3 report was derived after the release was independently downloaded and verified. It reuses the same archived calibration and transition evidence; it does not rerun evaluators or Method Ψ. Keep the original release unchanged and do not describe this post-run correction as part of the frozen measurement implementation.

The analyzer records its own source digest and the frozen analyzer digest in `analysis-summary.json`. Verify corrected output files against `ANALYSIS_SHA256SUMS.json` and use `EVIDENCE_RECEIPT.json` to identify the source release. If the analyzer changes again, regenerate the derived outputs and their checksums from the same immutable release.

## Validation and limits

Focused coverage is `make test-mono-ci-psi-owner-authorized-v2`; repository style and type checks are `make development-lint` and `make development-typecheck`. The figures and tables are descriptive only. The run remains one architecture-level unit with three technical transition repetitions; G1 stays INCOMPLETE, G4 NOT AUTHORIZED, P NOT_READY, scoring NOT_EXECUTED, and coverage UNKNOWN.
