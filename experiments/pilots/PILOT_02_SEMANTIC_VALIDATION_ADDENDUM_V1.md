# PILOT-02 Semantic Validation Addendum V1

**Status:** prospective DEVELOPMENT / TEST_ONLY protocol
**Frozen before controls:** commit containing this file
**Parent experiment:** PILOT-02, A0_MONOLITH → A0_1_CAPABILITY_MODULES
**Pinned A0.1 source revision:** `3758e2cd60810b8d4263f8d91443ec829efc8bb5`
**Pinned A0.1 application-tree SHA-1:** `cdff9a6c3cee870e1eca2a5f5f3eb3202b0b1f08`
**Existing continuation:** V5d, preserved unchanged
**Pair targets:** `REP_A01_ARCH_INTERNAL_LAYERING_CI → AC_LAYERING`; `REP_A01_ARCH_MODULE_STRUCTURE_CI → AC_MODULE_STRUCTURE`

This addendum defines a prospective, mechanically reproducible semantic-validation procedure for the two PILOT-02 A0.1 architecture-compliance pairs. It does not alter frozen B0, DA01 research gates, governance acceptance, or production authority. Results are TEST_ONLY and do not constitute an independent human or external research assessment.

## Pinned intent and evaluator inputs

The pair intent is read from the exact obligation catalog:

- `fitness/catalog/architectural-obligations.yaml`, SHA-256 `8c5bd8fffe3bdb2af8fb85f8d0012bc34673f72866e52daed99fab96f9763011`.
- `AC_LAYERING`: internal dependencies conform to the allowed layering model.
- `AC_MODULE_STRUCTURE`: capability modules have declared structure and identity.

The source-bound PILOT-02 V2 profile is SHA-256 `c480b1907d9f69cb7c5d1c4f45cb221551aeb857881ba859529e8c1f1fd5e8c9`. The pinned DEVELOPMENT fitness configuration is SHA-256 `3f8c952afd00f97f00b84955cc85fdf8dc5cbe32b52e65771773b8aa5a12fbad`.

### Layering pair

The evaluator configuration is `architecture/acceptance/importlinter.toml`, SHA-256 `5e938273faa86b4584886e2ede5700b35b064d5e54fe04b0c3d1e50278c64eb0`. Its five named contracts cover Users, Tasks, Notifications, Reporting, and Audit internal layers. The configuration contains 17 layer targets. Before any positive conclusion, the verifier must parse the exact pinned TOML, confirm all five contract definitions and all 17 target entries, resolve each target to the pinned source/import graph, and report missing targets.

The actual evaluator is `lint-imports --config architecture/acceptance/importlinter.toml --no-cache`. The source dependency graph is independently extracted with the lockfile-pinned Grimp version. The recorded graph must identify all configured target modules and enumerate only direct dependency edges whose endpoints fall within the configured module-layer scope. The full project graph count must not be substituted for the in-scope edge count. Each contract's actual kept/broken result and any reported violating edge must be preserved from evaluator output. If exact in-scope edges, graph provenance, target resolution, or contract results cannot be verified, scope and semantic adequacy remain unresolved.

Positive control: execute the exact evaluator against the clean pinned source. Expected observation: all five contracts pass with zero violations and no unresolved target.

Negative control: apply the already documented `experiments/pilots/PILOT_01_S1_FAULT.patch` in a disposable source copy at `app/modules/notifications/repository.py`. The patch SHA-256 is `7f52e0239d27d089aa9e456821f341259982eeaecdaca44a85404eef8a1f56d8`; the clean target-file SHA-256 is `bc154b83d2dd508294293bec02ad33088ea26b4b866794e7f10f0af6e448ec90`. It adds a repository-to-API import inside the existing Notifications module. Expected observation: the Notifications internal-layering contract reports the forbidden dependency. This is a secondary evaluator-sensitivity control reusing PILOT-01 S1, not an additional independent architecture transition. A failure caused by import collection, a missing target, or another error does not count as detection.

### Module-structure pair

The declared state manifest is `architecture/states/A0_1_CAPABILITY_MODULES.yaml`, SHA-256 `e062c8cd0689116240bddcb4feacd5975dcf28c86a88cc11e29ebf03968d0aeb`. The actual evaluator is `tests/architecture/test_module_structure.py`, SHA-256 `d1f7ae29a1c8ed5fb5a4e1c37df8c8c22bfe98a31e0fa85c8c32012c0d083f7c`, run as `python -m pytest -q --no-header tests/architecture/test_module_structure.py`.

The verifier must record the test's concrete checks: manifest state/scenario/deployment and declared dependency/governance fields; exact five capability package names; the root module-file inventory; the required `.py` filename set for each module; presence of shared-infrastructure paths; and absence of listed legacy capability paths. For each module it must include expected and discovered file paths and mismatches. It must state that the evaluator checks file/package shape and manifest declarations; it does not prove module API behavior, implementation semantics, or the dependency graph.

Positive control: execute the exact test against the clean pinned source. Expected observation: the single declared structural test passes.

Negative control: in a separate disposable copy, remove exactly `app/modules/audit/model.py`. Before mutation, verify its SHA-256 is `7017f08f13274d7d600aaa3a9c54d8eb99d441fa7addbeb2326553f5cea599b5`; after mutation, record the source-tree inventory and mutation-manifest digests before executing the test. Expected observation: the exact module-structure test fails because the discovered Audit `.py` file set no longer equals the required file set. A collection error or unrelated assertion failure does not count as detection.

## Typed inspection evidence and admission criteria

Typed evaluator evidence may add an optional `inspection_scope` object containing:

- `unit`: `dependency_edge`, `module`, or `file`;
- `expected_subjects`: the finite, non-empty expected subject inventory;
- `measured_count`: the observed count using the declared unit;
- `evidence_artifact`: an exact path and SHA-256 reference to the graph or inventory evidence.

The existing top-level `inspected_subjects` remains the actual inspected inventory. The old `inspected_edge_count` remains nullable and backward compatible. For legacy records without typed scope, null edge count remains unresolved. A module/file record may leave edge count null only when its typed scope is internally consistent: all expected subjects were inspected, the measured count matches that unit, and the supporting artifact bytes are digest-verified. An edge count of zero must never be inserted to bypass the unresolved-scope reason.

For either pair, the independent TEST_ONLY semantic verifier must bind the frozen obligation ID/criterion/intent, exact representation ID and template, A0.1 revision and application-tree identity, evaluator artifact and evidence-contract digests, inspection record, complete raw positive/negative control outputs, control-specific expected behavior, and evidence-contract compatibility. `semantic_compatible=true` and `adequacy_proven=true` are admitted only when all relevant conditions pass. Incomplete scope, unresolved behavior, mismatched identity, or an unexplained control outcome yields `UNKNOWN`/undetermined.

A positive proof is formed using the existing `pair_proof_subject()` and the verified adaptation-evidence sidecar. The proof must bind the exact representation/obligation pair, architecture revision, evaluator artifact, evidence-contract digest, and exact evaluator-evidence digest; it must reference digest-checked artifacts and use the existing explicitly configured TEST_ONLY adaptation verifier. The report must identify its verification component and inputs so another researcher can reproduce the checks. The verifier must derive conclusions from those artifacts; it must not echo caller-supplied VALID claims.

## Execution order and controls

1. Freeze this addendum before executing semantic controls.
2. Export the clean pinned A0.1 source to a disposable checkout. Do not mutate the main or PR source tree.
3. Verify all pinned evaluator/obligation/profile bytes and derive inspection inventories.
4. Execute both positive and negative controls using the actual evaluators; capture complete stdout/stderr and exact exit codes. Hash the negative mutation before evaluator execution.
5. Independently validate scope records, control behavior, and report-to-input digests. Only then create a TEST_ONLY pair proof.
6. Supply verified evidence and proof to the existing `run_adaptation()` sidecar path before Method P runs. Do not include expected operations, oracle outputs, or comparison scores in method inputs.
7. Compare the exact candidate representation/template and evaluator bytes with the prevalidated template. If any differ, do not reuse proof for that candidate. Run the materialized candidate's evaluator afterward only as a consistency check.
8. Preserve each continuation in a new versioned immutable archive. Never modify V1–V5 archives or their checksums.

## Decision and limits

The pair is `VALID` only if the existing Method P exact-pair contract accepts the independently generated proof and all execution, identity, evidence, scope, mapping, and criterion checks resolve. A successful positive control alone is insufficient. A detected negative control supports evaluator sensitivity for this bounded mutation; it does not prove completeness against all defects.

If a prerequisite cannot be verified, preserve its exact unresolved reason and leave the pair `UNKNOWN`. Any valid result remains TEST_ONLY evidence for this one transition. It does not establish DA01 authorization, production readiness, G1/G4 approval, `Coverage_P`, or independent `Coverage_ref`.
