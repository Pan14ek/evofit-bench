# Context — controlled positive ADD study V1

> **Audience:** repository contributors. **Type:** versioned DEVELOPMENT study; this context is descriptive and does not grant scientific authority.

## Responsibility

Define one TEST_ONLY positive-input experiment for unchanged Method Ψ on the exact A0.4→A0.5 transition, reusing the archived V2 controls and timing evidence.

## Local landmarks

- `PROTOCOL_V1.md` and `PROTOCOL_V1.json` — frozen scope, conditions, cost rule, repetitions and stop semantics.
- `inputs/POSITIVE_ADD_PROFILE_V1.json` — author-declared scoped obligation, evaluator mapping and candidate-template fields.
- `analysis/` — Ukrainian manuscript result, insertion map, and post-run recovery note, populated only from the verified archive.
- Hosted run `40612830900` — one warmup and all three C1 transition archives completed. The original receipt assembly failed strict schema validation; the archived transitions were read back and packed with the `recover` command. The recovered bundle SHA-256 is `3c3aaaa0ab675ec33158cebba9eae565bacab973a09e98ba5e48273952c760a2`.

## Boundaries

The study uses the unchanged P algorithm in the existing digest-pinned Docker isolation. Its scoped policy, exact-pair semantics, template, cost model and invariants are TEST_ONLY author declarations. In C1, Ψ recorded HOLD while its operation plan contained ADD for AC_DATA_OWNERSHIP; the materialized candidate passed both evaluator conditions, but the HOLD was not accepted or applied. The recovery reads existing raw archives only and must not repeat C1. The study does not approve policy, establish independent validity, alter the 18-row canonical catalog, or authorize DA01/G1/G4.

## Validation

Use `make test-mono-ci-psi-a05-positive-add` and `make development-quality`. The actual three measured C1 repetitions run only in the frozen hosted workflow after the same-runner Docker preflight succeeds. For a post-run packaging failure, use the readback-only `recover` command on the uploaded evidence artifact; it does not execute Ψ or evaluators.
