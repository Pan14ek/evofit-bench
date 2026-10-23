# MONO-A1 reference-freeze checklist v2 — W0 readiness

**Checkpoint:** `G-A1-C4-REF-FROZEN`

**Applies to:** MONO-E1 ΔA4

**Current status:** `NOT_READY`

**As-of main:** `be8ee7d44bdef343c30fd201c411c3cdff748da4`

This version is the current W0 checklist. It preserves the original [V1 checklist](MONO_A1_REFERENCE_FREEZE_CHECKLIST.md) and [V1 protocol](MONO_A1_PROTOCOL_V1.md); read the [source-identity addendum 1.1](MONO_A1_PROTOCOL_V1_W0_ADDENDUM.md) for the corrected source pair. This checklist does not execute or authorize MONO-E1, either arm, scorer access, or reference freeze.

## W0 checklist

- [x] **Source identity only:** A0.3/A0.4 commits, repository/application trees, ancestry, canonical checkpoint, and exact application patch have Git readback. See the versioned addendum. This does not pass the overall checkpoint.
- [ ] **Authority and lifecycle policy:** obtain approved policy source, completeness authority, and independently reviewed lifecycle-stage requirements. DRAFT/OPEN policy inputs do not qualify.
- [ ] **Complete obligation universe:** bind the full catalog/approved-extension universe and prove closure. For each row preserve `ACTIVE`, `INACTIVE`, or `UNKNOWN`, mandatory status, rationale, source-fact IDs, evidence digests, and authority. The two A0.4 engineering gates are not the denominator.
- [ ] **Lifecycle-stage completeness:** predeclare required stages and stage-specific evidence for every obligation under OPEN-03. Do not infer stages from available representations/evaluators. Unknown stage applicability keeps the denominator incomplete.
- [ ] **Reference contract for completeness:** review and approve a versioned binding for catalog/policy/completeness and stage-registry evidence. The V1 reference schema validates supplied-row consistency but does not prove catalog closure or bind a typed lifecycle registry.
- [ ] **Representation/evaluator map:** for every required pair bind representation, obligation, lifecycle stage, A0.4 source, evaluator/version/source/tree/configuration, capability, scope, and raw evidence. Keep unsupported pairs `UNKNOWN`.
- [ ] **Semantic assessment and controls:** obtain pair-specific, non-vacuous positive/negative control evidence and an exact-pair semantic report, independently reviewed by a qualified human. W2 readback and synthetic fixtures alone are insufficient.
- [ ] **B0/P method identities:** pin unchanged B0 bytes and an independently reviewed, separately versioned executable P algorithm/configuration. `P_ALGORITHM_STATUS` is currently `NOT_READY`; do not bypass its guard or modify frozen P artifacts.
- [ ] **Common inputs and fairness:** freeze the same target source, approved policy/catalog/capability inventory, workload, PostgreSQL fixture/seed/migrations, environment, runner identities, image digests, and comparable timer boundaries. Record separate allowlists and digests for B0 and P.
- [ ] **Isolation and provenance:** independently audit that neither arm can access reference/scorer/oracle, `.git`, network, or the other arm's artifacts. Verify source-to-image attestations against the same target source SHA.
- [ ] **Scorer custody:** assign an authorized custodian and scorer-only location with access controls and role separation. Keep target labels, expected operations, ground truth, and private reference bytes out of public PRs and method inputs.
- [ ] **Schema/readback:** validate the complete reference and all versioned sidecars, verify cross-artifact digests, and independently review completeness and source facts. A schema pass alone is not truth or authority.
- [ ] **One-time freeze:** only after every item above is approved, obtain explicit W0 authorization and let the custodian call `freeze_reference(...)` once in a new scorer-only directory. This item is currently **NOT AUTHORIZED** and was not performed.
- [ ] **Verified readback and checkpoint:** call `load_verified_reference(...)`, verify exact payload/seal/source/time/study bytes, then record `G-A1-C4-REF-FROZEN = PASS` only after actual readback. Otherwise retain `NOT_READY`.

## Source pair record

| Role | State | Commit | Repository tree | Application tree |
| --- | --- | --- | --- | --- |
| Before | `A0_3_GOVERNED_MODULE_GRAPH` | `26a9bb667da7d0938e38aca15d2bf29fd1de4829` | `7b951421395f532ca403dab09d76902ff08a807d` | `b147b8961ea9e76c966663d4832e4c303581151a` |
| After | `A0_4_REPORT_QUERY_PORT` | `d3101c0d3aa9b7b709253b6ec7518416f05f65b9` | `2b436e0aaf09403ea516d73d20a466a122f86592` | `007196f68652bc13f6798805793ffdfae96f95f7` |

- Reference ID / digest / freeze timestamp: `UNASSIGNED / UNASSIGNED / NOT_FROZEN`
- W0 scorer custodian / independent reviewer: `UNASSIGNED / UNASSIGNED`
- Checkpoint: `G-A1-C4-REF-FROZEN = NOT_READY`
- Open blockers: complete approved Q and lifecycle policy; exact-pair semantic evidence/authority; executable P identity; common bundles/fixture/runner/provenance; scorer custody; one-time freeze and verified readback.

The public checklist records no target-level labels or expected operations. Any such reference content belongs only in the authorized scorer-only custody location.
