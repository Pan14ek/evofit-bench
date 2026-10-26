# Context — `experiments/execution/mono-ci-b0-psi-execution-a05-v1`

> **Audience:** human developers and AI coding agents. **Type:** prospective DEVELOPMENT baseline package; not historical evidence, approved method input, or scientific authorization.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `experiments/execution/CONTEXT.md` first.

## Responsibility

Holds a bounded reconstruction of the two-control A0.4 active fitness configuration for the A0.4→A0.5 Method Ψ DEVELOPMENT transition. The canonical A0.4 source is pinned, but no historical A0.4 configuration was found; this proposal is prospective and unapproved.

## Local landmarks

- `RECONSTRUCTED_B0_A04_V1.json` — two active controls, source/configuration identities, nonhistorical status, and unchanged NO_GO gates.
- `RECONSTRUCTED_B0_A04_V1.json.sha256` — detached digest for the proposal bytes.
- `SHA256SUMS` — package inventory.

The versioned proposal schema and transition runner are under `experiments/execution/schemas/` and `experiments/execution/tooling/mono_ci_psi_a05.py`.

## Constraints

Do not add AC_DATA_OWNERSHIP to this baseline before the method run. The evaluator's availability and A0.5 support do not make it an active baseline representation. Do not present this reconstruction as historical or approved, and do not change the proposal using preregistered expected operation labels.

## Verification

Run `make test-mono-ci-psi-a05`. A fresh A0.4→A0.5 DEVELOPMENT run uses `uv run --frozen --extra dev python -m experiments.execution.tooling.mono_ci_psi_a05 --repository <checkout> --output <new-path> --execution-id <unique-id>`. This does not advance study readiness, P readiness, G1, G4, or the reference gate.
