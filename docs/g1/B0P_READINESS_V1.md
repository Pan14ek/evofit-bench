# DEV-B0P-V1 readiness and execution checklist

**Record date:** 2026-10-20.
**Study status:** PREPARATION — no new comparative run or independent measured DA01 result.
**Author scope decision:** docs/g1/B0P_AUTHOR_DECISIONS_V1.md.
**Protocol:** docs/g1/B0P_DEVELOPMENT_PROTOCOL_V1.md.
**Algorithm source to pin:** 984f75b11b3153c52275e223ce8ec23b8d0dd0e5.

## Prepared in this PR

- [x] Isolated DEVELOPMENT author decision register, without altering canonical G1 independent review requirements.
- [x] Prospective B0/P comparison plan with RQ1/RQ2 endpoints, abstention rules and full-denominator discipline.
- [x] Explicit B1 omission: no human B1 was conducted.
- [x] Disclosure that PILOT-02 / DA01 A0->A0.1 is calibration-exposed, not a blind holdout.
- [x] Independent-from-P structural Git module-inventory verifier and synthetic/adversarial tests (implementation checked in; do not call tests passing before CI reports).
- [x] Historical PILOT-02 artifacts untouched; new work lives on a separate branch.

## Still required before a genuine new B0/P DEVELOPMENT observation

- [ ] Select a new experimental architecture delta and fix both source commit IDs and admissible observation scope. A0->A0.1 reuse must be labeled CALIBRATION_EXPOSED.
- [ ] Establish a complete applicable-obligation reference with explicit author/independent evidence type and separate custody from P inputs; do not silently collapse to two TEST_ONLY pairs.
- [ ] Pin the actual execution image, Python dependencies, validator/evaluator artifacts, source-to-image provenance, scoring scripts and configuration hashes.
- [ ] Compare exported fact rows against directly recomputed Git inventories and reject mismatches.
- [ ] Verify actual evaluator execution and exact-pair semantic/evidence adequacy, separately from compliance and governance.
- [ ] Prepare read-only B0/P inputs, write-once predictions, and a scorer-only reference directory. Confirm isolation negative probes in the selected environment.
- [ ] Execute a prospective B0/P DEVELOPMENT run with immutable inputs, outcomes and evidence, and publish a raw checksum inventory.
- [ ] Produce full RQ1 confusion matrix and RQ2 full-denominator results, preserving HOLD, UNKNOWN, NOT_EVALUABLE and infrastructure errors.
- [ ] Keep claims descriptive and development-scoped. No population-significance or B1 comparison claim.

## Scientific readiness boundaries

- **G1** remains **INCOMPLETE** under the existing independent-review contract.
- **G4** remains **NOT AUTHORIZED** for measured DA01.
- **P_ALGORITHM_STATUS** for measured DA01 remains **NOT_READY**; the working DEVELOPMENT algorithm exists but is not independently frozen/approved.
- The author-scoped DEVELOPMENT direction does not itself grant production policy authority, comprehensive lifecycle coverage or a blind generalization claim.
- B0/P comparison does not replicate the complete frozen DA01 B0/B1/P design.

## Independent Git source-fact checker

Command template (use exact real commit SHAs and an actual observation JSON; do not supply a scenario oracle):

```bash
uv run python -m scripts.verify_b0p_git_inventory \
  --repository . \
  --before-sha <full-40-hex-commit> \
  --after-sha <full-40-hex-commit> \
  --observations <exported-architecture-observations.json> \
  --output <new-run-dir>/git_inventory_verification.json
```

Expected output: source-fact VERIFIED_GIT_INVENTORY or MISMATCH, hashes, all four observed versus recomputed inventories and explicit limits. It is not a policy or exact-pair semantic proof. Run targeted tests with:

```bash
uv run pytest --no-cov -q tests/unit/test_b0p_git_inventory.py
```

## Completion criterion for this preparation PR

Author decisions, protocol and checker are present, CI is green, and outstanding empirical prerequisites are clearly recorded. Completing preparation does **not** authorize changing canonical G1/G4 statuses or claiming a new measured outcome.
