# Context — positive ADD results and monograph insertion

> **Audience:** repository contributors. **Type:** post-run TEST_ONLY analysis; this file describes evidence scope and does not grant scientific authority.

## Responsibility

Keep the Ukrainian results, exact monograph insertion map, and recovery note derived from the verified C1 archive. The note explains why recovery was needed and which values could not be recovered.

## Landmarks

- RESULTS_POSITIVE_ADD_UK.md — per-run C0/C1 interpretation and technical limits.
- MONOGRAPH_INSERTION_MAP_UK.md — proposed exact results/discussion additions; it does not edit the monograph.
- POST_RUN_READBACK_RECOVERY_UK.md — provenance of the recovered outer archive and the post-run aggregation correction.
- Each generated Markdown file has a neighboring .sha256 sidecar.

## Evidence and limits

These files derive from hosted run 40612830900, whose frozen implementation commit is 37176a42cc099f1f159dc137b85fe3e32b8290d5. The verified recovered archive has SHA-256 3c3aaaa0ab675ec33158cebba9eae565bacab973a09e98ba5e48273952c760a2. It contains one completed warmup and three completed measured runs. Each C1 decision is HOLD; the operation plan contains an obligation-level ADD, the candidate evaluator is validated and executed, and the candidate is not accepted or applied.

The workflow's first outer-receipt assembly failed strict schema validation after all four transition archives were written. The recovery command reads those existing archives and does not execute Method Ψ, evaluators, or transitions. Full transition wall-clock timings were lost before receipt persistence and remain unknown. Do not infer them.

The selected policy scope and exact-pair declarations remain author-declared TEST_ONLY inputs. The result does not establish a global denominator, independent validity, DA01 measurement, or readiness-gate promotion.

## Validation

Run make test-mono-ci-psi-a05-positive-add for scoped unit, negative, and recovery-summary regressions. Validate a recovered bundle with python -m experiments.execution.tooling.mono_ci_psi_a05_positive_add_study verify-bundle against the frozen implementation checkout recorded in its pre-run freeze.
