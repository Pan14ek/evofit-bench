# Context — MONO CI ΔA5 B0 versus Ψ readiness

> Audience: human developers and AI contributors. Type: separate, draft A0.4→A0.5 comparison proposal and readiness evidence; not a measured experiment, policy approval, G1 freeze, or G4 authorization.
> Navigation: read root AGENTS.md, docs/RESEARCH_CONTEXT.md, and experiments/execution/CONTEXT.md first.

## Responsibility

Pins the prospective A0.4→A0.5 study subject, proposes a bounded CI review scope, records exact development evidence, and keeps scientific gates fail-closed. It does not run either comparison arm or score outcomes.

## Landmarks

- DELTA_A5_READINESS_V2.json — source identities, baseline, 18-row unknown applicability inventory, classified 9-cell semantic review inventory, evidence verification scopes, proposed method identity, and human decision matrix.
- PROTOCOL_V1.md — separately versioned proposed comparison protocol. The A0.3→A0.4 protocol remains unchanged.
- HANDOFF_UK_V1.md — Ukrainian provenance, evidence boundary, proposed manuscript text, and figure specification.
- tests/unit/test_mono_ci_b0_psi_delta_a5.py — package readback and adversarial applicability-profile contracts.
- experiments/execution/tooling/mono_ci_b0_psi_delta_a5.py — read-only schema, digest, Git identity, and fail-closed applicability verifier.

## Constraints

Keep the baseline named PROSPECTIVE_RECONSTRUCTED_BASELINE. Keep every catalog row UNKNOWN until separately verified authority, complete scope, review, and current source evidence exist. The three proposed CI review targets are not a mandatory denominator. The nine-cell review inventory contains two proposed representation-obligation pairs, four undeclared mappings, and three evaluator capability candidates; none is verified coverage and all pair validity remains UNKNOWN. PR #56 archive/result/timing values are historical references. The current verifier checks repository-local source/artifact bytes only; independent archive replay is NOT_EXECUTED unless an exact local archive is explicitly supplied and verified. Preserve P NOT_READY, G1 INCOMPLETE, G4 NOT_AUTHORIZED, no scoring, and historical Ψ HOLD. Never add scorer/reference labels to Ψ inputs.

## Verification

Run make test-mono-ci-psi-delta-a5. The tool verifies repository bytes and contracts only; it does not execute evaluators, B0, Ψ, or a scorer. Readiness outcome remains NO_GO_WITH_EXPLICIT_BLOCKERS.
