# Context — `experiments`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `CONTEXT.md` before this file.

## Responsibility

Scientific protocol, scenarios, execution, curated evidence and run results.

## Local landmarks

- `A0_FINAL_VALIDATION_REPORT.md`
- `README.md`
- `schemas/development_evidence_bundle_v1.schema.json`
- `schemas/fitness_representation_evidence_v1.schema.json`
- `execution/EXP04_EVIDENCE_ADMISSION.md`
- `execution/schemas/pilot02_inherited_evaluator_results_v1.schema.json`
- `results/` (ignored generated run outputs)
- `pilots/` contains PILOT-01 and PILOT-02 protocols, reports, manuscript subsections, generated tables, evidence archives, and narrow tools

## Established conventions

Read experiments/design/ and execution/da01/ canonical research rules.

## Constraints and known gaps

EXP-01/02 output is DEVELOPMENT execution and representation evidence, not Coverage_P, Coverage_ref, or measured DA01 evidence. Bundle v1.2 links the manually established A0.1 configuration to exact evaluator records and raw artifacts; v1.0/v1.1 remain readable. Runtime bundles distinguish collector revision from observed Docker target identity; without authoritative source-to-image provenance, source binding remains unverified. Never treat a code merge as G4 authorization or a single scenario as many independent samples.

EXP-04 preserves validated evaluator observations separately from exact P
mapping, verifier authority, and semantic validity. Its current A0.1-to-V3
mapping remains unresolved; outputs are DEVELOPMENT diagnostics and cannot
establish coverage or authorize a measured run. See the execution guide for
commands and output interpretation.

## PILOT-02

PILOT-02 exercises one versioned A0.1-to-P candidate profile for
`AC_LAYERING` and `AC_MODULE_STRUCTURE`. Its original HOLD run is preserved.
The prospective development continuation may pass authentic evaluator
observations and explicitly TEST_ONLY assumptions through existing Method P
contracts to observe operations and candidate materialization. Those inputs
are not independent semantic proof or production authority. Keep independent
coverage pending and never label it DA01 `Coverage_ref`.

Profile V2 additionally binds four unchanged A0 representation rows to exact
A0.1 DEVELOPMENT evaluator source bytes. Fresh Locust, EXP-01 runtime, and
PostgreSQL integration outputs remain in the separate ignored run directory;
they are not passed to P as semantic proof. The inherited-evaluator protocol
defines these runs before measurement.

The semantic-validation continuation runs the pinned Import Linter and module
structure evaluators with clean and source-mutated controls, independently
reconstructs inspection scope and mutation inventories, and rechecks report
bytes before admitting exact-pair proofs through the existing TEST_ONLY
sidecar. Its pair statuses remain DEVELOPMENT diagnostics; they do not
establish DA01 authorization, independent coverage, G1/G4, or production
readiness.

V5's canonical run `pilot02-inherited-20261020-v5d` executed the four inherited
evaluator rows and its full candidate validator returned `valid` after the
versioned V2 DEVELOPMENT bindings were admitted. The V5 archive preserves the
canonical run, linked EXP-01 bundle and earlier attempts. Runtime failure samples
remain unavailable; exact pairs are UNKNOWN, the internal diagnostic is 0/2,
governance remains HOLD, and no coverage or DA01 result is established.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
