# Context — `experiments/execution/mono-ci-b0-psi-v1`

> **Audience:** human developers and AI coding agents. **Type:** descriptive navigation context, not an approved protocol, method input, policy or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `experiments/execution/CONTEXT.md` first.

## Responsibility

Separate, bounded, CI-only monograph study preparation for one A0.3→A0.4 architecture transition and the `AC_PUBLIC_API` / `AC_MODULE_GRAPH` engineering controls. This namespace is distinct from DA01 and MONO-A1; it does not supersede either protocol.

## Local landmarks

- `PROTOCOL.md` — review draft `MONO_CI_B0_PSI_COMPARISON_V1`; no arm execution authorization.
- `READINESS.md` — source-backed NO_GO matrix and exact remaining prerequisites.
- `CASE_MANIFEST_V1.json` — four source-case identities reused from EVAL-01 without outcome labels.
- `INPUTS_V1.json` — digest inventory and planned common-input parity; method bundles are not assembled.
- `EVALUATOR_CONTROL_EXPECTATIONS_V1.json` — separate author-declared EVAL-01 evaluator expectations; not a method input or complete B0/Ψ reference.
- `SHA256SUMS` — package-file integrity inventory.

The validating read-only preflight is `experiments/execution/tooling/mono_ci_b0_psi_preflight.py`; contract tests are in `tests/unit/test_mono_ci_b0_psi_preflight.py`.

## Established conventions

Preserve the exact source/checkpoint identities, keep evaluator compliance separate from fitness representation validity and obligation applicability, and keep the scorer-side expectations outside method input bundles. Technical case rows are not independent architecture transitions.

## Constraints and known gaps

This preparation is not a B0/Ψ execution path. The A0.3 parent fitness configuration is `NOT_IDENTIFIED`, the A0.3 two-control configuration is DEVELOPMENT-only, the measured P interface is `NOT_READY`, the complete applicable obligation denominator and exact-pair semantics are unresolved, no method bundles or scorer custody exist, G1 is `INCOMPLETE`, and G4 is `NOT AUTHORIZED`. The preflight may verify package integrity and report NO_GO; it must never execute an evaluator, method, or scorer.

## Verification

Run `uv run python -m experiments.execution.tooling.mono_ci_b0_psi_preflight` and `uv run pytest --no-cov -p no:cacheprovider tests/unit/test_mono_ci_b0_psi_preflight.py`. A passing preflight is package/provenance evidence only and cannot advance readiness.
