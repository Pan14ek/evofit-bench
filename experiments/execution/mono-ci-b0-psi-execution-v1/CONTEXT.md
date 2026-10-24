# Context — `experiments/execution/mono-ci-b0-psi-execution-v1`

> **Audience:** human developers and AI coding agents. **Type:** proposed execution supplement; not protocol approval, method input, or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `experiments/execution/CONTEXT.md` first.

## Responsibility

Holds a separately versioned reconstruction proposal and DEVELOPMENT-only technical validation contract for the MONO CI B0/Ψ study. It does not revise the frozen-for-review PR #51 package or change its NO_GO status.

## Local landmarks

- `BASELINE_RECONSTRUCTION_V1.json` — provenance, derivation, and remaining review decisions.
- `RECONSTRUCTED_B0_A03_V1.json` — prospective CI-only baseline configuration; explicitly not historical.
- `TRANSITION_ASSESSMENT_V1.json` — source-bounded analysis of unchanged controls, the A0.3 exception, and adaptation uncertainty.
- `REQUIREMENT_TEST_MATRIX.md` — implementation-to-test traceability.
- `DEVELOPMENT_VALIDATION.md` — exact local technical validation evidence, when run.
- `SHA256SUMS` — digest inventory for this proposal package.

The runner is `experiments/execution/tooling/mono_ci_b0_psi_execution.py`; execution and result schemas are under `experiments/execution/schemas/`.

## Constraints

Never present this reconstructed proposal as the historical A0.3 configuration or as an approved B0 baseline. Keep the case archive, expected evaluator labels, scorer, and `.git` outside method input bundles. Do not execute the official comparison while the study or measured Ψ interface is NO_GO/NOT_READY. Development evaluator probes are technical validation only and cannot support strategy scores or superiority claims.

## Verification

Use `make test-mono-ci-b0-psi` and `uv run python -m experiments.execution.tooling.mono_ci_b0_psi_execution --development-validation --output <path>` with a new output path outside the repository. A successful development probe does not advance G1, G4, or the ΔA4 reference gate.
