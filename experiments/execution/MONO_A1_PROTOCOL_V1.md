# MONO-E1 / MONO-E2 experimental protocol v1

**Status:** preparation infrastructure; no MONO-E1 or MONO-E2 run has been executed by this change.
**Scope:** DEVELOPMENT monograph experiment only. This protocol does not authorize measured DA01, G1, or G4 claims.
**Exposure:** the scenario family and author involvement are known; neither treatment is a blinded holdout.

## 1. Scientific objective and treatment names

The experiment evaluates whether frozen Method P adapts a fitness configuration more appropriately than unchanged frozen B0 under controlled architecture evolution. It does not test whether A1 is architecturally superior to A0/A0.1. Candidate validity, evaluator execution, exact-pair proof, compliance, governance, and publication of an accepted configuration remain separate observations.

| Study ID | Treatment | Required interpretation |
| --- | --- | --- |
| `MONO-E0` | Historical A0→A0.1 calibration | Reference historical evidence only. Do not rerun absent a documented reason or rewrite its outputs. |
| `MONO-E1` | ΔA4 Reporting query-port refactor, A0.3→A0.4 | Negative control. The source changes while no new fitness obligation arises solely from using the established public query API. Score whether P proposes an unjustified change instead of RETAIN/no-op. W0 owns the source change. |
| `MONO-E2` | Compound transition to final `A1_MODULAR_MONOLITH` | Main B0/P comparison on the exact same final A1 source SHA and full, source-grounded `Q(A_after)`. Do not seed P with the prior A0.1 HOLD candidate as an accepted configuration. |

### W0-approved MONO-E2 comparison

| Role | Architecture state | Source commit SHA |
| --- | --- | --- |
| Before | `A0_MONOLITH` | `b78b0967be937634b7762baccf5ac6892b279a73` |
| After | `A1_MODULAR_MONOLITH` | `UNASSIGNED` until final A1 verification |

MONO-E2's experimental comparison is `A0_MONOLITH → A1_MODULAR_MONOLITH`. The `A0.1→A1` sequence remains the engineering implementation trajectory. The reference schema binds E2's before state and commit to the approved A0 baseline and requires the after state to be final A1 with a full commit and tree SHA. The after SHA remains unset until final A1 verification; do not seal an E2 reference before then.

### MONO-E1 source-freeze gate

`G-A1-C4-REF-FROZEN` is a required W0 checkpoint before any Method P execution on ΔA4. The transition labels remain A0.3→A0.4; its exact before/after commit and tree SHAs are `UNASSIGNED` until W0 verifies them. Complete [the reference-freeze procedure and checklist](MONO_A1_REFERENCE_FREEZE_CHECKLIST.md), then freeze and read back the scorer-only reference before starting either study arm. A planned reference or a filled-in SHA string without Git object readback does not pass the checkpoint.

**Current checkpoint state:** `NOT_READY`. ΔA4 source SHAs and the complete source-derived reference inputs have not been supplied or verified in this update; no reference is frozen and no MONO-E1/E2 run is authorized by this protocol change.

## 2. RQ crosswalk

The manuscript numbering is stored separately from the older executable scenario protocol. Do not rename or edit the frozen legacy protocol to make numbering appear consistent.

| MONO manuscript endpoint | Meaning | Legacy executable RQ |
| --- | --- | --- |
| RQ1 | Impact identification and adaptation-operation correctness | No direct numeric equivalence |
| RQ2 | Valid coverage over the full applicable mandatory obligation set | No direct numeric equivalence |
| RQ3 | Adaptation, evaluator, and verification overhead | Legacy executable RQ4: runtime and CI overhead |
| RQ4 | Architecture controls, ΔA4 negative control, and governance | Legacy executable RQ3: controlled-degradation detection |

The crosswalk is serialized as `MONO_A1_RQ_CROSSWALK_V1` in every study record.

## 3. Freeze-before-run reference custody

The scorer-only reference is the answer key for RQ1 and the denominator/expected obligation state for RQ2. It is never mounted in a B0 or P input bundle. If no genuinely independent reviewer has checked it, set `custody_status=AUTHOR_DECLARED`; do not call it independent, blinded, or holdout evidence.

Before either new study's first method run:

1. For E1, W0 confirms the A0.3/A0.4 source pair and passes `G-A1-C4-REF-FROZEN`. For E2, use the canonical A0 commit above and final `A1_MODULAR_MONOLITH`; record the final A1 commit only after verification. For both studies, record exact full commit and Git tree SHAs, commit lineage, permitted changes, and stable workload/DB fixture, then verify revisions against Git object readback.
2. Recompute architecture facts from the pinned trees. Bind each fact to a source SHA and evidence artifact digest. A target label may only cite verified source facts; unresolved target truth blocks a complete reference.
3. Construct the typed target universe, including affected and unaffected representations and obligation targets. Independently justify `retain/add/replace/deactivate/adjust`; do not derive the expected labels from B0 or P output.
4. Derive the entire mandatory, applicable `Q(A_after)` from the architecture and obligation sources. Record `ACTIVE`, `INACTIVE`, or `UNKNOWN` with rationale and source fact IDs. Do not reuse DA01's six obligations, PILOT-02's two diagnostic pairs, or any earlier partial denominator by default.
5. For each mandatory active obligation, define all required exact pairs, inspection scope, evaluator ID, and evidence requirement. Pin evaluator source commit/tree, artifact digest, configuration digest, capabilities, and scope. A missing or inadequate evaluator means the pair stays UNKNOWN.
6. Record frozen B0 and P algorithm versions/source SHAs/configuration digests, method bundle allowlist digests, runner identity, and any source-to-image provenance. B0 remains unchanged. P remains the frozen Method P implementation.
7. Complete the linked W0 checklist for E1 or verify final A1 and the canonical A0 predecessor for E2. Validate against `mono_a1_reference_v1.schema.json`; call `freeze_reference(...)` in a scorer-only custody directory before either arm starts. The function checks source commit/tree identities, writes canonical reference bytes and a separate SHA-256 seal exactly once, and marks custody `AUTHOR_DECLARED`.
8. Read back the exact bytes with `load_verified_reference(...)`. Verify the seal, source revisions, timestamp ordering, and expected study ID. Record the returned reference digest in the study record.
9. Create separately allowlisted B0 and P bundles. `verify_method_input_isolation(...)` rejects root/nested symlinks, reference-tree overlap, reference digest/payload, and suspicious oracle/scorer/cross-arm paths or JSON keys. This scanner is supplemental: independently review the allowlist and bundle inventory; a clean scan is not semantic proof that arbitrary prose contains no labels.

Never seal a complete E2 reference until final A1 exists and its exact commit/tree are verified. E2's predecessor is fixed to `A0_MONOLITH` at `b78b0967be937634b7762baccf5ac6892b279a73`; do not substitute the engineering A0.1 predecessor. Never invent A1 or ΔA4 SHAs or expected labels. Do not place the private reference or expected operations in a public PR artifact, method input, or committed result template.

## 4. Run order and sealed output

Run B0 and P against the same exact `architecture.after.commit_sha`, same declared obligation universe, same workload/fixture, and comparable environment. Record distinct arm run IDs and start times. E2 B0 uses the unchanged frozen A0 configuration with no adaptation; P uses the frozen Method P version/configuration. A0.1's previous HOLD candidate is not an accepted parent.

Keep method inputs disjoint from the reference, scorer, ground truth, other arm outputs, `.git`, network, and unapproved scenario material. The scorer is an oracle-side operation. Record each bundle's byte digest and allowlist digest.

Seal only authentic emitted predictions with the repository's existing write-once prediction format. Preserve stdout, stderr, traces, runner logs, failures, evaluator outputs, configuration bytes, and reason codes. If P returns HOLD without an emitted prediction, record `NOT_EMITTED_GOVERNANCE_HOLD`; do not manufacture a prediction. Only open the scorer after both required outputs and the reference pass readback. RQ1 remains `NOT_EVALUABLE` if either prediction is not genuinely sealed.

## 5. Endpoint definitions

### RQ1 — impacts and operations

`score_mono_rq1(...)` requires a verified scorer-only reference, B0 and P `SEALED` status, source and input-bundle SHA matches, both run-start timestamps after reference freeze, and verified sealed prediction bytes. It reports target-level TP, FP-in, FP-extra, FN, TN, precision, recall, F1, operation accuracy, and the expected-operation × predicted-operation confusion matrix. Missing predictions produce `NOT_EVALUABLE` and `scorer_invoked=false`; do not replace that with an operation-plan diagnostic. If a metric denominator is zero, preserve `null`.

An exploratory operation-plan comparison may be included in a separate diagnostic table, clearly marked unscored. It cannot replace canonical sealed-prediction RQ1.

### RQ2 — valid obligation coverage

Use the sealed reference's complete active mandatory denominator, identical for B0 and P. `score_mono_rq2(...)` accepts the scorer-only reference directory, not an in-memory caller-authored reference; it verifies the seal, Git revisions, and that both executions began after freeze. It returns three distinct views: B0 evidence-backed coverage, P proposed-candidate potential, and P governance-accepted configuration.

Each positive proof binds `(representation_id, obligation_id, architecture_state, architecture_source_sha)` plus the run, arm, configuration role/digest, evaluator identity/version, non-vacuous inspected count, semantic report, compliance observation, and raw artifact digests. Each declared execution, inspection-scope, and semantic-assessment SHA must resolve to an included raw file. `W2A1ExactPairReadbackVerifier` reads the `W2_A1_EVALUATOR_EVIDENCE` JSON artifact, checks its W2 schema and exact state/source/scope/result bindings, requires the W2 evaluator checkout at the reference-pinned commit/tree, and invokes that checkout's `verify_evidence()` to re-read evaluator, configuration, and inspected subject bytes. Without a matching pinned checkout or successful readback, the result is UNKNOWN. Tests exercise only a synthetic stand-in; no real W2 or MONO execution was run.

`TEST_ONLY` evidence remains `DIAGNOSTIC_ONLY` and cannot produce an accepted-coverage percentage. MONO-A1 v1 has no production trust-anchor adapter and its schema does not accept a self-declared `PRODUCTION_AUTHORITY` value. A development governance ACCEPT may be shown as a development accepted-configuration view; it does not mean production authorization, G1 completion, or G4 approval. Missing evidence stays UNKNOWN. No coverage percentage is emitted for an incomplete denominator or unresolved per-obligation evidence.

### RQ3 — cost and runtime

Use the same declared timer boundary for B0 and P and record adaptation, evaluator, verification, and total nanoseconds separately. Capture CPU/RSS only when a sampler actually collected them; otherwise use `UNKNOWN` or `NOT_COLLECTED`. Source-to-image attestation must be independently verified and bind each arm to the same target source SHA before reporting descriptive timing. The current helper checks the structure and SHA binding of an externally verified attestation record; it does not authenticate the attestation signature itself.

One transition supports descriptive timing only. Do not infer significance, variance, or population effects. Mark unlike boundaries `NOT_COMPARABLE`/UNKNOWN rather than normalizing after the fact.

### RQ4 — architecture controls and governance

Collect independently source-pinned, non-vacuous raw evidence for each applicable control:

| Control | Evidence required |
| --- | --- |
| ΔA4 negative control | Distinct before/after source SHAs; actual Reporting query-port refactor; expected RETAIN/no-op reference; record every proposed change and HOLD reason. |
| Forbidden cross-module import | Clean evaluator run plus controlled import mutation, exact source SHA, inspected-file count, raw stdout/stderr, and finding. |
| Dependency cycle | Clean graph evaluation and injected cycle; inspected edge/node scope and raw graph result. |
| Data ownership violation | Clean source-derived ownership evaluation and a foreign repository/table access mutation; inspected scope and raw finding. |
| Synchronous handler failure / transaction rollback | Disposable real PostgreSQL fixture; inject handler failure and assert Task, Notification, and Audit effects roll back in one transaction; retain migration/fixture identities and query evidence. |
| Governance | Exact candidate/config digest and authentic ACCEPT/REJECT/HOLD/UNKNOWN trace. HOLD/UNKNOWN remain distinct from ACCEPT. |

An evaluator process exit code alone is not semantic adequacy or compliance. A test PASS is bounded by the inspected scope and source SHA.

## 6. Evidence archive and readback

Before archiving, write the deterministic evidence inventory with `write_evidence_inventory(...)`. Include the study record, sealed reference digest metadata (not public expected labels), method bundle inventories, prediction seals, evaluator identities and raw records, control outputs, timer/resource data, environment/source-image attestations, failed attempts, and report tables. `create_mono_archive(...)` writes a digest sidecar and verifies a clean extraction against the inventory; preserve the archive and sidecar byte-for-byte. Do not overwrite a prior run.

The archive's checksum proves byte integrity after capture; it does not independently establish the truth of the reference, evaluator claims, authority, or scientific conclusion.

## 7. Requirements-to-test matrix

| Requirement | Implementation | Synthetic test |
| --- | --- | --- |
| Exact source commit/tree and reference sealing | `freeze_reference`, `load_verified_reference`, `verify_source_revision` | `test_reference_freeze_is_source_pinned_and_precedes_method_execution`; `test_freeze_rejects_incorrect_source_tree_sha`; seal/mutation tests |
| Full applicable denominator and correct RQ2 denominator | `validate_mono_reference`, `score_mono_rq2` | `test_rq2_rejects_a_wrong_denominator_and_keeps_unknown_applicability`; `test_rq2_uses_one_full_denominator_and_separates_three_coverage_views` |
| Reference/oracle isolation | `verify_method_input_isolation` | `test_reference_labels_cannot_enter_method_input` |
| Seal tampering / write-once | reference/prediction seal loaders | `test_reference_readback_rejects_missing_or_forged_seal`; `test_reference_is_write_once_and_post_seal_mutation_is_detected` |
| Exact source/run/pair mapping and raw bytes | `verify_exact_pair_evidence` | `test_exact_pair_requires_exact_mapping_raw_bytes_and_non_vacuous_proof`; `test_exact_pair_rejects_cross_run_evidence_reuse`; duplicate-pair regression |
| Independent W2 evaluator readback and TEST_ONLY separation | `W2A1ExactPairReadbackVerifier` | W2 adapter readback and mismatch tests; `test_exact_pair_requires_exact_mapping_raw_bytes_and_non_vacuous_proof`; `test_rq2_keeps_governance_acceptance_separate_from_test_only_proof` (synthetic evaluator only) |
| P HOLD without prediction | `score_mono_rq1`, `validate_mono_study` | `test_p_hold_without_prediction_preserves_rq1_not_evaluable`; `test_study_gate_rejects_scoring_when_p_hold_has_no_prediction` |
| Runtime/timer and source-image prerequisites | `assess_mono_rq3`, `validate_source_image_provenance` | `test_incomplete_runtime_metrics_and_invalid_image_binding_remain_unknown` |
| Archive integrity and clean extraction | inventory/archive helpers | `test_evidence_archive_integrity_and_clean_extraction_readback` |

Run the focused tests with:

```bash
PATH=/private/tmp/b0p-venv/bin:$PATH PYTHONPATH="$PWD" pytest -q tests/unit/test_mono_a1.py
```

This is a synthetic infrastructure suite, not an actual MONO run. Run repository lint/type checks as part of PR validation; the full quality target additionally needs a verified disposable PostgreSQL database.

## 8. Readiness and stop rules

This preparation is consumable only after W0 applies the approved E2 source-state sequence, verifies the final A1 source, freezes exact E1/E2 revisions, and passes the E1 reference gate, and W2 supplies the final evaluator IDs, pinned sources/configs, artifact readback interface, and non-vacuous control evidence. RQ2 must remain UNKNOWN until the independent W2 adapter exists and verifies the real source-bound raw artifacts. RQ3 remains UNKNOWN until timer and source-image attestations have real provenance. RQ4 remains UNKNOWN for every unexecuted control. No measured values, significance, ACCEPT, G1/G4 status, or architecture-superiority claim may be inferred from these synthetic checks.

If A1 is not frozen by the planned deadline, preserve the last verified intermediate state and report the missing dependency. Do not relabel an intermediate state as A1, substitute the already exposed A0.1 calibration, or fabricate MONO-E1/E2 outputs.
