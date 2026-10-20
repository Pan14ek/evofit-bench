# B0/P Comparative DEVELOPMENT Study Report

**Study:** DEV-B0P-V1
**Run ID:** `dev-b0p-20261020-preflight-a01`
**Record date:** 2026-10-20
**Status:** `PREPARED_NOT_EXECUTED`
**Exposure:** `CALIBRATION_EXPOSED`

## Research question

This study is intended to compare the unchanged B0 fitness configuration with frozen Method P after an architectural transition. RQ1 asks whether P identifies affected fitness representations and obligations. RQ2 asks whether P's candidate and governance-accepted configurations provide more valid, evidence-supported coverage of the required obligations than B0.

This run produced a verified preparation package only. Neither arm was executed. It has no predictions, evaluator results, sealed outputs, governance decision, RQ1 measurements, or RQ2 measurements. It therefore supplies no comparative effectiveness result.

## Experimental design

The package records the available A0-to-A0.1 source transition:

| Input | Identity |
|---|---|
| Before architecture | `b78b0967be937634b7762baccf5ac6892b279a73` |
| After architecture | `3fdd5c68f8f60fad5757eefa66cc2aa8b24d9306` |
| B0 source and study base | `165a7d6ef31adbe8ce3abe9f72e59d74692c987e` |
| Frozen Method P source | `984f75b11b3153c52275e223ce8ec23b8d0dd0e5` |
| Policy source | `165a7d6ef31adbe8ce3abe9f72e59d74692c987e` |
| Exposure class | `CALIBRATION_EXPOSED` |

The A0-to-A0.1 transition was repeatedly exposed during PILOT-02 and is unsuitable as a prospective holdout. The design document describes `ΔA2` (public module APIs), but the repository has no executable `scenario.yaml` for it. The protocol requires a scenario definition and frozen reference before P execution. This task has no independent reference custody, so it did not implement a new transition or label one held out.

The package records the full RQ2 denominator as six required obligations, read from the DEVELOPMENT protocol. The scorer-side oracle and scenario-specific expected identifiers were not opened, and no obligation identifiers were added to method inputs. G1 remains `INCOMPLETE`; G4 remains `NOT AUTHORIZED`.

## Baselines

| Arm | Frozen identity | Preparation finding |
|---|---|---|
| B0 | `B0_UNCHANGED_V1`, source `165a7d6ef31adbe8ce3abe9f72e59d74692c987e` | Original A0 configuration and evaluator-configuration bytes were verified at both architecture revisions. |
| P | `P_GOVERNED_ADAPTATION_DEVELOPMENT_V1`, algorithm source `984f75b11b3153c52275e223ce8ec23b8d0dd0e5` | Source-pinned input bundle prepared; `P_ALGORITHM_STATUS=NOT_READY`; governance status `NOT_RUN`. The included policy source is DRAFT/OPEN and has no production authority. |

No B1 arm was included, and no human operator participated.

## Measurement procedure

The preparation command exported read-only method-input bundles, recorded source and configuration identities, independently recomputed Git module inventories for both architecture revisions, captured the protocol denominator, and wrote checksums. The independent inventory readback returned `VERIFIED_GIT_INVENTORY` for the four module-name facts. It does not verify completeness outside that module inventory, establish policy authority, prove compliance, or establish semantic evaluator adequacy.

The resulting manifest records B0 bundle SHA-256 `62ce5f223715a35a407e58c92c45355ddd31708de192a0479e1afeb2f133b628`, P bundle SHA-256 `b39899ade3ac7330362e0bd4d986b19e8d0112101cdd2dda24dc5355ab2ec11f`, and policy bundle SHA-256 `3fff9d4d0f2aeb584868c295f5da482b0d5541235e643c4c307a51856b4c68a8`. The Import Linter configuration SHA-256 is `88ff64a4792c6048a6ab0686ddf9326ebbee49f76996933845a6142cc1a2ba27`. The runtime image digest is absent; evaluator runtime and source-to-image provenance are not pinned.

No evaluator was run, no current-run exact-pair evidence was generated, and no output was sealed or scored. The preparation/readback commands were:

```bash
python -m scripts.prepare_b0p_development_comparison \
  --run-id dev-b0p-20261020-preflight-a01 \
  --before-sha b78b0967be937634b7762baccf5ac6892b279a73 \
  --after-sha 3fdd5c68f8f60fad5757eefa66cc2aa8b24d9306 \
  --b0-source-sha 165a7d6ef31adbe8ce3abe9f72e59d74692c987e \
  --p-source-sha 984f75b11b3153c52275e223ce8ec23b8d0dd0e5 \
  --policy-source-sha 165a7d6ef31adbe8ce3abe9f72e59d74692c987e

python -m scripts.verify_b0p_development_comparison \
  --run-directory experiments/results/dev-b0p-20261020-preflight-a01
```

## Results

| Endpoint | B0 | Method P | Difference | Evidence and interpretation |
|---|---|---|---|---|
| RQ1 TP/FP/FN/TN, precision, recall, F1 | Not measured | Not measured | Not estimable | No predictions or reference labels were scored. |
| RQ1 operation-selection accuracy and protocol violations | Not measured | Not measured | Not estimable | P was not executed; no arm outputs exist. |
| RQ2 required-obligation denominator | 6, from frozen protocol | 6, from frozen protocol | Not applicable | This is denominator provenance only; no obligation identifiers were read during preparation. |
| RQ2 independently valid coverage | Not measured | Candidate: not measured; accepted: not measured | Not estimable | No evaluator evidence, exact-pair evidence, predictions, or governance result exists. |
| Governance | Not run | `NOT_RUN`; policy remains DRAFT/OPEN | Not estimable | Candidate quality and accepted configuration quality cannot be assessed. |
| Method/adaptation, evaluator, and verification overhead | Not measured | Not measured | Not estimable | No method or evaluator execution occurred. |

### Engineering findings

The prospective input package was produced and read back successfully. Its architecture module inventory was independently verified within the verifier's stated scope. All 217 entries in `SHA256SUMS` passed `shasum -a 256 -c`; no PILOT-02 artifact was imported. The package does not contain arm predictions, seals, evaluator evidence, semantic verdicts, governance output, score files, or a completed comparative archive.

### Methodological findings

No finding about P's operation selection, proposed candidate quality, governance acceptance, or comparative coverage follows from this preparation. The package correctly preserves the absence of those observations rather than deriving them from source structure or prior PILOT-02 diagnostics.

## Comparison

The evidence supports only a comparison of preparation identities and readiness. B0 and P were exported as separate bundles from recorded source revisions, and the pinned source inventories and configuration bytes were checked. Their behavioral outcomes and coverage difference remain unknown. A successful source-inventory check does not establish that B0's evaluator is stale, that the architecture is compliant or noncompliant, or that P is superior.

## Validity threats and remaining blockers

The run manifest records these blockers:

1. `CURRENT_A0_TO_A0_1_TRANSITION_IS_CALIBRATION_EXPOSED`
2. `DELTA_A2_SCENARIO_AND_REFERENCE_NOT_FROZEN_OR_INDEPENDENTLY_CUSTODIED`
3. `METHOD_RUNTIME_IMAGE_NOT_BUILT_OR_PINNED`
4. `EVALUATOR_RUNTIME_AND_SOURCE_TO_IMAGE_PROVENANCE_NOT_PINNED`
5. `P_POLICY_SOURCE_IS_DRAFT_OPEN_WITHOUT_AUTHORITY`
6. `INDEPENDENT_EXACT_PAIR_EVIDENCE_NOT_GENERATED_FOR_THIS_RUN`
7. `RQ1_RESULTS_NOT_AVAILABLE_UNTIL_BOTH_ARM_PREDICTIONS_ARE_SEALED`
8. `RQ2_RESULTS_NOT_AVAILABLE_UNTIL_SEALED_PREDICTIONS_AND_CURRENT_RUN_PAIR_EVIDENCE_EXIST`

The source-fact verifier covers module-name inventories, not every possible architectural fact. One transition cannot establish generalization or statistical significance. G1 is incomplete and G4 is not authorized; this report is DEVELOPMENT-only and does not change canonical readiness records.

## Conclusion

This run advances reproducible preparation, not the comparative experiment. Its manifest, source-pinned B0/P bundles, structural inventory readback, and checksums are verified. RQ1 and RQ2 remain unmeasured. A future execution needs an independently specified and custodied transition/reference, a pinned method and evaluator environment with source-to-image provenance, valid policy authority for the intended claim, fresh exact-pair evidence, and sealed predictions before scoring.

## Evidence record

- Run directory: `experiments/results/dev-b0p-20261020-preflight-a01/` (ignored local DEVELOPMENT output; preparation package only).
- `study_manifest.json` SHA-256: `d6d55437fcc30c4e8bdd5acb37fd9f881be74f646989e701b03092ba8ac82b2f`.
- `SHA256SUMS` SHA-256: `29852caf847e50133977c4624a84df9a335f022dd61becbd0d75f2b54e3d37f7`.
- Verification: readback CLI exit 0; 217/217 listed files verified; architecture status `VERIFIED_GIT_INVENTORY`.
- The directory is not represented as a completed study archive because comparative execution did not occur.
