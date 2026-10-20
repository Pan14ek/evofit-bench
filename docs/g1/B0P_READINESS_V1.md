# DEV-B0P-V1 readiness and execution checklist

**Record date:** 2026-10-20.
**Study status:** PREPARATION — source-pinned inputs and readback are implemented; no B0/P arm has run and no independent measured DA01 result exists.
**Author scope decision:** docs/g1/B0P_AUTHOR_DECISIONS_V1.md.
**Protocol:** docs/g1/B0P_DEVELOPMENT_PROTOCOL_V1.md.
**Algorithm source to pin:** 984f75b11b3153c52275e223ce8ec23b8d0dd0e5.

## Prepared in this PR

- [x] Isolated DEVELOPMENT author decision register, without altering canonical G1 independent review requirements.
- [x] Prospective B0/P comparison plan with RQ1/RQ2 endpoints, abstention rules and full-denominator discipline.
- [x] Explicit B1 omission: no human B1 was conducted.
- [x] Disclosure that PILOT-02 / DA01 A0->A0.1 is calibration-exposed, not a blind holdout.
- [x] Independent-from-P structural Git module-inventory verifier and synthetic/adversarial tests (implementation checked in; do not call tests passing before CI reports).
- [x] Write-once B0/P DEVELOPMENT preparation CLI, strict manifest schema, pinned-source checks, input-bundle verification, and independent Git inventory readback.
- [x] Record the full six-obligation RQ2 denominator from this protocol without opening the oracle or copying obligation identifiers into method inputs.
- [x] Historical PILOT-02 artifacts untouched; new work lives on a separate branch.

## Still required before a genuine new B0/P DEVELOPMENT observation

- [ ] Select a new experimental architecture delta and fix both source commit IDs and admissible observation scope. A0->A0.1 reuse must be labeled CALIBRATION_EXPOSED.
- [ ] Establish a complete applicable-obligation reference with explicit author/independent evidence type and separate custody from P inputs; do not silently collapse to two TEST_ONLY pairs.
- [ ] Pin the actual execution image, Python dependencies, validator/evaluator artifacts, source-to-image provenance, scoring scripts and configuration hashes.
- [x] Compare exported fact rows against directly recomputed Git inventories and reject mismatches for the prepared A0-to-A0.1 package.
- [ ] Verify actual evaluator execution and exact-pair semantic/evidence adequacy, separately from compliance and governance.
- [x] Prepare read-only B0/P input bundles and verify exact source, policy, configuration, and bundle digests.
- [ ] Prepare isolated method execution, write-once predictions, and scorer-only reference access. Confirm isolation negative probes in the selected environment.
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

## B0/P preparation and readback

The current prospective package pins the A0-to-A0.1 transition as
`CALIBRATION_EXPOSED`, B0/policy source at the requested study base, and frozen
Method P at `984f75b11b3153c52275e223ce8ec23b8d0dd0e5`. Generate a new package
with `scripts.prepare_b0p_development_comparison` using full commit SHAs, then
verify it with `scripts.verify_b0p_development_comparison`. Preparation does
not execute an arm or open the scorer. The run-specific report records the
exact run ID, manifest hash, and blockers.

The selected transition is repeatedly exposed through PILOT-02 and therefore
supports calibration characterization only. A future unexposed transition
needs independently prepared custody. Method execution also remains blocked
until a pinned runtime and evaluator provenance are available; RQ2 additionally
requires fresh, independent exact-pair evidence for this run.

The design lists `ΔA2` (explicit public module APIs), but no executable
`scenario.yaml` exists for it. The design requires that scenario specification
before implementation and requires its ground truth to be frozen before P is
run. This task does not have independent reference custody, so it does not
create that transition or label it held out. The prepared A0-to-A0.1 package
remains calibration-only.

The generated preparation-only package is `dev-b0p-20261020-preflight-a01`.
Its `study_manifest.json` SHA-256 is
`d6d55437fcc30c4e8bdd5acb37fd9f881be74f646989e701b03092ba8ac82b2f`; its
`SHA256SUMS` SHA-256 is
`29852caf847e50133977c4624a84df9a335f022dd61becbd0d75f2b54e3d37f7`. The
readback verifier returned exit 0 and all 217 listed files passed checksum
verification. The package is ignored local DEVELOPMENT output at
`experiments/results/dev-b0p-20261020-preflight-a01/`; no B0/P arm, evaluator,
scorer, or governance process ran. The English report and Ukrainian manuscript
subsection record the run state and blockers in
`experiments/pilots/B0P_DEVELOPMENT_REPORT.md` and
`experiments/pilots/B0P_DEVELOPMENT_MANUSCRIPT_UA.md`.

Reproduce the package readback with:

```bash
python -m scripts.verify_b0p_development_comparison \
  --run-directory experiments/results/dev-b0p-20261020-preflight-a01
```

## Completion criterion for this preparation PR

The preparation implementation, tests, source-pinned package, readback verification, and outstanding empirical prerequisites are recorded. Local checks for this change include the focused B0/P tests, development lint, security scan, architecture check, disposable-database migration check, and development regression suite. The full `make development-quality` target stops at type checking on 10 diagnostics in four untouched pilot files; therefore this document does not claim that target passed. Hosted GitHub Actions status is reported on the Draft PR. Completing preparation does **not** authorize changing canonical G1/G4 statuses or claiming a new measured outcome.
