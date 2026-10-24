# MONO-E1 A0.3 DEVELOPMENT fitness configuration v1

**Status:** DEVELOPMENT proposal only. This configuration is new, is not a historical A0.3 artifact, has no independent semantic approval, and is not an authorized MONO-E1 baseline or Method P input bundle.

## Purpose and artifacts

This proposal versions a bounded two-control fitness configuration for the A0.3 A0_3_GOVERNED_MODULE_GRAPH state:

- Configuration: [fitness/configs/mono-e1-b0-dev-a03-v1.yaml](../fitness/configs/mono-e1-b0-dev-a03-v1.yaml), schema [fitness/configs/mono-e1-b0-dev-a03-v1.schema.json](../fitness/configs/mono-e1-b0-dev-a03-v1.schema.json).
- Configuration SHA-256: 8f74330e03b6b96d4213037e0b76dcb29ef72017876411625e5b96edf1400cdf; its sidecar is stored alongside the YAML file.
- Read-only verifier: [experiments/execution/tooling/mono_e1_a03_fitness_config.py](../experiments/execution/tooling/mono_e1_a03_fitness_config.py).
- Focused contract tests: [tests/unit/test_mono_e1_a03_dev_fitness_config.py](../tests/unit/test_mono_e1_a03_dev_fitness_config.py).

The configuration assigns distinct representation IDs:

| Representation | Evaluator and version | Proposed obligation | Proposed stage |
| --- | --- | --- | --- |
| REP_MONO_E1_DEV_A03_PUBLIC_API_CI_V1 | AC_PUBLIC_API v1.0.0 | AC_PUBLIC_API | ci_test |
| REP_MONO_E1_DEV_A03_MODULE_GRAPH_CI_V1 | AC_MODULE_GRAPH v1.0.0 | AC_MODULE_GRAPH | ci_test |

The evaluator identifiers are kept separate from representation identities. Each representation explicitly records its evaluator configuration digest, shared evaluator-source digest, exact source-bound observation and diagnostic digests at canonical A0.3 and A0.4, categorical metric, stage-binding status, applicability, validity, and limitations. ci_test is a proposed scientific crosswalk from engineering acceptance; it is not an approved lifecycle-stage decision. Applicability and exact representation–obligation–stage validity remain UNKNOWN.

## Source and evaluator evidence

The provenance binds canonical A0.3 commit 26a9bb667da7d0938e38aca15d2bf29fd1de4829, repository tree 7b951421395f532ca403dab09d76902ff08a807d, application tree b147b8961ea9e76c966663d4832e4c303581151a, and checkpoint SHA-256 5da4a7e1ed359ec8ea1e3288ab81edf32f0b71e2fec946b52a8d0d562dcf43c0. It also records canonical A0.4 commit d3101c0d3aa9b7b709253b6ec7518416f05f65b9, repository tree 2b436e0aaf09403ea516d73d20a466a122f86592, application tree 007196f68652bc13f6798805793ffdfae96f95f7, and checkpoint SHA-256 7b0b0c7a0c6ac782540466d283c42d7589b8aaeb4af7df62104faa01fd154e8e.

Both canonical checkpoints bind the same evaluator implementation digest 5c17373ba8896ef0c443d826bd0064168ec7c5759c7973f9602b6c2c715b169c, complete source scope (31 Python files and 185 import nodes), completed execution, and compliant observations. The two evaluator configuration digests are 8853c3a933b23f698c7ba7c5b6e511f292e8d9285dc0de4378741c53e466f7bb for AC_PUBLIC_API and 1abae6871a477ff2a07685ad645a70defa2f1ac6745598ae4cdc35aab4e95bf6 for AC_MODULE_GRAPH.

The real EVAL-01 and EVAL-02 archives are pinned and checked by external sidecar, ZIP CRC, and each archive's complete internal SHA-256 inventory. They provide finite source-pattern controls for evaluator behavior:

| Study | Archive SHA-256 | Calls | AC_PUBLIC_API TP/TN/FP/FN | AC_MODULE_GRAPH TP/TN/FP/FN | Preserved issue |
| --- | --- | ---: | --- | --- | --- |
| EVAL-01 | f6cd3c7180a0719c0f410f51acc9596b0843950d7650da7f7d2924716188c9bf | 42 | 1/5/0/0 | 3/3/0/0 | None in the recorded diagnostic inventory |
| EVAL-02 | 9039e17b5b640db5641b808719c6b972a389b8f5e833ac1dc7783e658f4bf18c | 60 | 4/4/0/0 | 2/4/0/0 | Three exact-diagnostic mismatches remain; binary outcomes do not erase them |

These finite, author-selected controls support only bounded evaluator behavior claims. They do not establish independent labels, population accuracy, semantic suitability, applicability, or full architecture conformance. Dynamic imports remain outside the static inspection; AC_PUBLIC_API also does not verify callable signatures or runtime behavior. The archives are referenced as provenance-only and are excluded from any future Method P input export.

The evaluators are runnable through python -m architecture.acceptance.a1.cli with an exact source checkout, state manifest, architecture state, and expected source SHA. The existing make architecture-test ARCHITECTURE_STAGE=... target invokes the stage gate; the checked-in GitHub workflow currently selects A0.4. This DEVELOPMENT configuration supplies command templates and evidence bindings but is not consumed as a separate CI job and does not change the existing CI workflow.

## Baseline proposal and RETAIN

B0_DEV_A03 v1.0.0 means: leave this exact proposed two-representation A0.3 configuration unchanged when evaluating the A0.3→A0.4 negative-control transition. It is an E1-local treatment proposal, not the historically frozen A0 B0 and not a reconstruction of historical A0.3 fitness intent.

The frozen A0 configuration remains byte-pinned at SHA-256 5ad60e373463ea459e192bf85d82704ca9aa1c217c4abf4d8caeb66924059ecb from tag arch-a0-monolith-v1 / revision b78b0967be937634b7762baccf5ac6892b279a73. The later A0.3 readback separately pins its supporting A0 representation catalog, traceability, and frozen evaluator. Their bytes are unchanged. A0.3 applicability of the frozen REP_A0_ARCH_CI_LAYERING remains UNKNOWN.

Selecting B0_DEV_A03 changes the meaning of RETAIN: it would mean preserve these two proposed CI representations from the new E1-local starting configuration. It would not mean preserve the original A0 REP_A0_ARCH_CI_LAYERING configuration. The proposed baseline contains only two controls; it is not the full 18-obligation Q(A0.4) denominator and does not carry a reviewed applicability decision. Consequently, RETAIN correctness remains NOT_EVALUABLE while the exact-pair semantic validity and applicability are unknown. This proposal does not authorize this treatment as official MONO-E1 B0.

## Readiness assessment

| Readiness level | Result | Basis |
| --- | --- | --- |
| Structurally valid configuration | PASS | Strict JSON Schema and cross-row checks pass; representation IDs are unique and distinct from evaluator IDs. |
| Executable CI evaluator configuration | Engineering path exists | Both existing evaluator configurations and the source-bound CI stage gate are runnable. The proposal provides exact invocation templates; default CI currently selects A0.4. |
| Semantically justified fitness representation | UNKNOWN | Applicability, stage policy, mapping adequacy, and independent review are unresolved. Passing evaluator checks and declared mappings do not prove this level. |
| Approved scientific experimental input | NO | Not an official baseline, not a complete method input bundle, no frozen reference, P_ALGORITHM_STATUS=NOT_READY, G1 INCOMPLETE, G4 NOT_AUTHORIZED, MONO-E1 NO_GO. |

Therefore, the artifact is structurally usable as a proposed configuration component. It is not a complete current Method P input bundle and cannot be run through the Method P interface. The existing method-input contracts require a separately allowlisted bundle with architecture, policy, obligation, and other common evidence; this proposal does not produce that bundle. More directly, [MONO_A1_PROTOCOL_V1.md](../experiments/execution/MONO_A1_PROTOCOL_V1.md) requires G-A1-C4-REF-FROZEN before any Method P execution on canonical ΔA4. No Method P run on A0.3→A0.4 was made here.

## Minimum work before a valid B0/P comparison

1. An accountable owner and independent reviewer must approve the bounded CI scope, lifecycle-stage treatment, and disposition of excluded obligations—or approve a complete denominator. Record the rationale, authority, and evidence in a new versioned review artifact.
2. Independently assess each exact representation–obligation–stage pair, including scope and applicability. Resolve or explicitly bound EVAL-02's diagnostic mismatch and the dynamic-import limitation; do not silently amend archived EVAL outcomes.
3. Approve whether the treatment is B0_DEV_A03 or historical A0 B0, bind the exact unchanged configuration digest and operation semantics, and reconcile that choice with the frozen scoring contract. Keep RETAIN unevaluable until its parent configuration and mappings are reviewable.
4. Complete W0's exact source-pair readback and scorer-only G-A1-C4-REF-FROZEN procedure before any P execution on ΔA4. Keep the private reference and expected operations outside all method inputs.
5. Freeze and independently review the Method P algorithm and digest, assemble separate digest-bound B0/P bundles and allowlists, resolve common-input and workload/fixture comparability under a reviewed additive protocol, complete G1, and obtain separate G4 authorization.
6. Keep a separately authorized positive-adaptation case for claims about ADD/REPLACE; this negative-control proposal cannot support those claims.

## Validation and traceability

The read-only validator checks the schema, configuration sidecar, exact A0.3/A0.4 Git trees and manifests, canonical checkpoint/evaluator/observation/diagnostic digests, frozen A0 bytes, EVAL archive inventories, positive/negative control matrices, and current gate states. It reports semantic validity as UNKNOWN and method execution as unauthorized.

| Requirement | Verification |
| --- | --- |
| Schema, unique identities, distinct evaluator/representation IDs, and exact pair mapping | test_configuration_schema_source_provenance_and_frozen_a0_bytes_validate; test_representation_ids_are_unique_and_separate_from_evaluator_ids |
| Exact source, evaluator config, checkpoint, observation, diagnostic, and archive provenance; frozen A0 bytes | validate_project; test_configuration_schema_source_provenance_and_frozen_a0_bytes_validate |
| Existing positive and negative evaluator controls with real artifacts | test_existing_evaluator_archives_contain_positive_and_negative_controls; tests/architecture/a1/test_evaluators.py |
| Missing, contradictory, or wrong-evaluator evidence fails closed | test_missing_or_contradictory_source_evidence_is_rejected; test_incorrect_evaluator_binding_is_rejected |
| Unknown semantic validity cannot become approval, official B0, or run authorization | test_unknown_semantic_validity_and_open_scientific_gates_cannot_be_promoted |

Run the read-only contract check with **uv run python -m experiments.execution.tooling.mono_e1_a03_fitness_config**. It validates provenance and archived evaluator evidence; it neither executes evaluators nor invokes Method P.
