# DA01 Phase A readiness report

**Report status:** methodological corrections implemented and ready for
post-push review; measured DA01 execution remains **NOT READY**.

## Gate status

| Gate | Status | Evidence / blocker |
| --- | --- | --- |
| G0 — architecture freeze | PASS for recorded inputs | `arch-a0-monolith-v1^{commit}` resolves to `b78b0967be937634b7762baccf5ac6892b279a73`; target candidate remains `5231a637d1489f83d4c17649c235a6ce2a2f40ac`. Frozen application, A0 evaluator/configuration, DA01 scenario/ground truth, workload, seed, and acceptance inputs are unchanged. No architecture tag was created or moved. |
| G1 — protocol freeze | INCOMPLETE | The general P algorithm and independent methodological review remain open. No P algorithm or DA01 outcome is claimed. |
| G2 — isolation audit | PASS for validated local evidence | Existing isolation evidence is preserved. The Docker negative probes passed locally with image `sha256:5a2dc0c42e8ef06560a3d61c077b66c8ee66f0f3fba7252fec1a5af34e234f27`; the correction quality run also passed those probes. A CI environment without the required runtime image may report Docker-specific probes as `SKIPPED`; such a skip is not a probe pass. |
| G3 — synthetic rehearsal | PASS | Targeted DA01 execution tests: 49 passed. `make migration-test`: passed. `make quality`: passed, 88 tests, 91.24% application coverage, including lint, formatting, type checking, security, architecture checks, migration validation, and full tests. |
| G4 — measured-run authorization | NOT AUTHORIZED | This task authorizes no measured B0, B1, or P trial. |

## Corrections delivered

- Architecture observations derive sorted, distinct `app.*` module inventories
  relative to each committed export root. Synthetic Git tests verify exact
  before/after inventories, added/removed sets, B0/B1/P bundles, manifest hashes,
  export-root naming independence, and fail-closed malformed sources.
- RQ2 now requires both representation/evaluator execution validity and a
  version 1 obligation verdict for each exact representation-obligation pair.
  Version 2 coverage assessments identify pair statuses and supporting evidence
  while preserving the complete private obligation denominator. Pair failures
  do not inflate the existing representation-level semantic-violation rate.
- RQ1 loads known target IDs from the representation catalog and general
  obligation registry at the pinned architecture SHA. Known out-of-universe
  targets remain ordinary `FP_extra`; unknown IDs add `UNKNOWN_TARGET` and
  deterministically propagate `PROTOCOL_VIOLATION` into sealed scored results.
- `experiments/schemas/result.schema.json` remains unchanged. The scorer
  envelope remains version 1.

## Scope and evidence limits

No measured DA01 prediction, candidate adaptation, reference score, or outcome
was created. No canonical A0 load experiment was run. Existing architecture
validation and isolation evidence are not method outcomes. No B1 operator is
recorded, so B1 remains NOT READY. P remains NOT READY because its general
algorithm is unfrozen.

Before any measured run, G1 still requires the deferred general P algorithm,
independent methodological review, trusted reference-evaluator/evidence
execution, externally anchored prediction seals, reproducible Docker negative
probes in the selected CI environment, and an independent B1 operator. Any
measured run requires separate explicit authorization after G0–G3 review.
