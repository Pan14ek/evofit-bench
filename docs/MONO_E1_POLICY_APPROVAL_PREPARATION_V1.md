# MONO-E1 policy approval preparation v1

**Status:** public, non-authoritative review package. No policy decision, human appointment, scientific denominator, G1/G4 gate, reference freeze, or experiment is approved by this document.

**Prepared from `main`:** `6ca20ea1b86c3570510c4c3f206ae3c418d13781` (PR #40 merge), repository tree `a195778a5137674bfc1c3d46069f752336438549`.

**Target source identity:** `A0_4_REPORT_QUERY_PORT`, commit `d3101c0d3aa9b7b709253b6ec7518416f05f65b9`, tree `2b436e0aaf09403ea516d73d20a466a122f86592`. This is the canonical A0.4 source pair already recorded in W2; no application source or canonical checkpoint is changed here.

## Purpose and limits

This package advances the first MONO-E1 blocker identified by W2: a complete, authority-backed, state-specific obligation universe and its required lifecycle stages. It gives the accountable policy authority and independent methods reviewer concrete questions, options, evidence requirements, acceptance criteria, and an unfilled sign-off form.

The [machine-readable inventory](mono_e1_policy_review_inventory_v1.json) copies every row in the current catalog in source order and pins catalog schema version `1` and SHA-256 `8c5bd8fffe3bdb2af8fb85f8d0012bc34673f72866e52daed99fab96f9763011`. Each row retains the catalog ID, criterion, intent, and default weight. The [schema](mono_e1_policy_review_inventory_v1.schema.json) forbids target-level applicability or mandatory decisions in this public proposal.

**Catalog inventory completeness is not policy completeness.** The inventory accounts for all rows in one pinned source file. It does not establish that this file is the complete normative universe, that any obligation applies or is mandatory at A0.4, or that an evaluator covers any obligation. Policy closure, all decisions, source facts, lifecycle stages, and representation evidence remain pending. No percentage denominator is available.

## Existing policy source readback

No approved source governing an A0.4 obligation was identified in the reviewed record. For each catalog ID, the inventory points to the corresponding row in `policy-pilot/v1/policy-design.yaml` without copying its candidate classifications. That file is `DEVELOPMENT_CANDIDATES_ONLY`, revision `controlled-policy-pilot-candidates-v1`, SHA-256 `4d9cd50a849cd510c1f63cd2dd3c28f0751fc5962253fb16bf914e9957860ced`.

The inventory also records the existing pilot authority materials by path and digest: the applicability ruleset is a development candidate; the charter is DRAFT; the registry is OPEN; and the completeness-claims file contains no claim. These digests identify candidate bytes; the structural validator checks the catalog pin, not these policy-source files. No hash establishes authority, truth, or completeness. The repo's DRAFT/OPEN pilot has no appointed production authority or production trust anchor. The two A0.4 evaluator gates remain engineering acceptance rules and do not define `Q(A_after)`.

## Proposed policy decision contract

This section is a proposal for review, not an approved policy. The authorized decision should be an immutable, versioned record bound to the exact architecture source, policy sources, fact evidence, reviewer decisions, and schema/verifier versions.

### Obligation applicability and mandatory status

For every pinned catalog or approved extension ID, record separately:

- **Applicability:** `ACTIVE`, `INACTIVE`, or `UNKNOWN` for the exact architecture state, source commit, and tree. `UNKNOWN` remains a live unresolved state and must never be converted to `INACTIVE` because a fact, policy, or evaluator is absent.
- **Mandatory status:** `MANDATORY`, `OPTIONAL`, or `UNRESOLVED`, with an authorized rule and rationale. `UNRESOLVED` or any possibly-mandatory row blocks a complete denominator. A default catalog weight is not mandatory status.
- **Source facts:** stable fact IDs, claim and fact type, exact architecture state/commit/tree, source path or record locator, raw evidence artifact path and SHA-256, observation method, evidence completeness scope, freshness/effective interval, verifier, and any conflicting evidence. A hash establishes byte identity only.
- **Policy provenance:** approved charter/registry revision, applicable rule IDs and version, decision authority, approval artifact and digest, signer identity/role, trust-anchor revision, effective time, expiry/revocation state, and superseded decision IDs.

Declared manifest facts, static evaluator observations, and runtime observations must retain their evidence type. A manifest declaration does not become an observed deployment fact. Absence can refute a condition only when a reviewer-approved completeness claim covers the exact fact type, state, source revision, and scope.

### Lifecycle-stage requirements (OPEN-03)

For every obligation, record either a nonempty set of required stages from `CI_TEST`, `DEPLOYMENT`, and `RUNTIME`, or an explicit `NOT_REQUIRED` decision with rationale and source-fact references. The decision must state which evidence is needed at every required stage, how missing or stale stage evidence is handled, and whether the stage rule is compatible with the existing frozen DA01 RQ2 procedure.

A missing lifecycle-stage decision remains unresolved. Missing evidence at a required stage is not evidence of compliance. Do not infer required stages from the available evaluators or representations. Preserve the DA01 denominator and V1 schemas unchanged; any MONO lifecycle registry or reference binding must be a separately reviewed, versioned sidecar.

### Authority, closure, versioning, and review (OPEN-04)

An accountable external policy authority must approve the charter, registry, applicability rules, mandatory semantics, catalog-closure process, completeness signers, permitted scope, effective-date rules, approval keys, key custody, expiry, revocation, and supersession. The authority must say whether the 18-row catalog is exhaustive for this study and how additional obligations are discovered. A repository digest, local TEST_ONLY key, AI assessment, or successful schema validation cannot appoint or authenticate this authority.

Each version is immutable and has a unique ID, policy and catalog pins, effective-from/effective-until times, scope, approving roles, signed decision artifact digest, trust-anchor reference, and predecessor/supersession links. Corrections create a new version; they do not silently rewrite past decisions. Revocation records the revoked version and effective time while retaining its bytes and review history.

`ACTIVE`, `INACTIVE`, or `MANDATORY` may be used only when an authorized rule and verified source facts support the decision. Conflicting or stale facts, absent authority, missing completeness evidence, out-of-scope rules, or mismatched revisions yield `UNKNOWN`/HOLD. The future trusted verifier must authenticate the approval against an independently governed trust anchor and enforce signer scope and revocation; a structural checker cannot do that.

### Extension handling

An added obligation requires a new catalog or authority-approved extension-ledger version. Preserve a stable ID, criterion, intent, origin, source digest, effective date, rationale, and supersession/retirement links. The authorized closure statement must account for the union of the pinned catalog and approved extensions. Never make an omitted or new row disappear by editing this inventory alone.

## OPEN-03 and OPEN-04 decision docket

The repository names the required human review roles, but no accountable policy authority or independent methods reviewer is appointed in the current record. Names, credentials, approvals, and signatures are intentionally left blank. An AI-generated assessment cannot serve as the independent human scientific review.

### OPEN-03 — mandatory lifecycle stages

| Review item | Proposal for decision |
| --- | --- |
| Decision question | For each of the 18 catalog rows and any approved extension, which of CI/test, deployment, and runtime require evidence? Where is an explicitly justified subset sufficient, and where is no lifecycle-stage requirement justified? |
| Repository evidence | G1 OPEN-03 is `PENDING_INDEPENDENT_REVIEW`; M-04 identifies the missing multi-stage contract. MONO V1 and the current exact-pair schema do not bind a lifecycle stage. W2 found that neither the two evaluator gates nor current exact-pair observations supply a stage registry. |
| Permissible options | (1) Retain the existing single-pair DA01 rule for DA01 and define a separate MONO registry; (2) require a specified subset of stages per obligation with fact-based rationale; (3) require all three stages for selected obligations, with rationale; (4) explicitly state `NOT_REQUIRED` for a row with evidence and rationale. No option changes the frozen DA01 denominator. |
| Scientific consequence | Adding stages can increase evidence requirements and change coverage; omitting a required stage can overstate control. Missing stage evidence must remain unknown and cannot be counted as compliance. |
| Required reviewer roles | Architecture-quality researcher and independent protocol reviewer, as specified in G1 OPEN-03. A separate accountable policy authority must authorize normative rules. All appointments are currently **UNASSIGNED**. |
| Decision artifact | Signed, versioned lifecycle-stage registry and OPEN-03 review record; if used by MONO reference material, add a versioned completeness sidecar/schema rather than editing frozen V1 contracts. |
| Objective acceptance criteria | One decision per catalog/extension ID; required stages are explicit or `NOT_REQUIRED` is justified; every required stage has an evidence contract and missing/stale/conflict rule; the exact policy, state, source, and reviewer artifacts have digests; an independent reviewer confirms DA01 compatibility; no unresolved possibly-mandatory row is treated as covered. |

### OPEN-04 — policy authority and completeness trust

| Review item | Proposal for decision |
| --- | --- |
| Decision question | Who is authorized to approve the obligation rules, classify applicability and mandatory status, declare catalog closure, sign completeness, and manage trust anchors and revocation for this study? |
| Repository evidence | G1 OPEN-04 is `PENDING_EXTERNAL_AUTHORITY`. The policy pilot is DRAFT/OPEN; its completeness-claims file is empty, and no production trust anchor or named accountable authority is recorded. The current files and hashes are inventoried above. |
| Permissible options | An institutionally managed signing authority with documented role and key custody, or another externally governed and independently auditable authority system. The selected system must define signer scope, trust-root distribution, expiry/revocation, and completeness authority. Repository-local TEST_ONLY keys do not qualify. |
| Scientific consequence | Without accountable authority and trustworthy closure, `ACTIVE`, `INACTIVE`, mandatory, and complete-universe claims cannot support the study denominator. Unsupported or conflicting cases remain `UNKNOWN`/HOLD. |
| Required reviewer roles | Accountable policy authority owner; security/key-custody reviewer; independent methods reviewer. An independent completeness reviewer must be independent of the policy author and obligation mapper. All appointments are currently **UNASSIGNED**. |
| Decision artifact | Approved versioned authority charter and registry, trust-anchor/key-custody and revocation record, approval-scope record, catalog/extension closure attestation, and independently reviewed completeness decision, each with exact digests. |
| Objective acceptance criteria | Named accountable institution/role and independent reviewers are appointed through the external process; trust anchor and signer authorization validate independently; scope, version, time, expiry, revocation, and supersession rules are executable; every pinned ID and approved extension is accounted for; omitted/unknown IDs and invalid, expired, revoked, or out-of-scope signers fail closed; a reviewer independent of the author signs the closure readback. |

### Unfilled sign-off form

Complete this form only after the people and authority have been appointed. The current proposal intentionally supplies no names or signatures.

| Field | OPEN-03 | OPEN-04 |
| --- | --- | --- |
| Decision ID and selected option(s) | `UNRESOLVED` | `UNRESOLVED` |
| Accountable authority role / appointment record | `UNASSIGNED` | `UNASSIGNED` |
| Independent reviewer role / appointment record | `UNASSIGNED` | `UNASSIGNED` |
| Decision artifact path, version, SHA-256 | `PENDING` | `PENDING` |
| Catalog and architecture state/source pins | `PENDING` | `PENDING` |
| Evidence and trust-anchor digests | `PENDING` | `PENDING` |
| Effective date, expiry/revocation route | `PENDING` | `PENDING` |
| Unresolved items and dissent | `PENDING` | `PENDING` |
| Approval signature and timestamp | `NOT PROVIDED` | `NOT PROVIDED` |

## Deterministic Q-completeness verification design

The future authority-backed verifier should produce separate results for each layer below. It must never collapse a catalog-complete skeleton into an approved denominator.

1. **Catalog inventory:** verify the source file digest and version; reject missing, duplicate, or unknown IDs; compare each copied definition to the pinned source; preserve declared order; record extension-ledger identity separately.
2. **Authority-backed applicability:** require an authenticated, in-scope decision and decision digest for every catalog/extension row. Accept only `ACTIVE`, `INACTIVE`, or `UNKNOWN`; an `UNKNOWN` or unauthenticated result keeps Q incomplete.
3. **Mandatory status:** require an authority-backed `MANDATORY`, `OPTIONAL`, or explicitly unresolved decision for every row. A possibly mandatory unresolved row prevents denominator closure.
4. **Lifecycle stages:** require either explicit required stages with rationale or an explicit, justified `NOT_REQUIRED` decision for every row. For each required stage, require an exact stage evidence contract; missing evidence is not compliance.
5. **Source-fact bindings:** bind each decision to fact IDs, exact architecture state/commit/tree, observation type, source locator, evidence artifact digest, scope and freshness. Missing facts are incomplete; conflicting facts are conflicting; stale facts are rejected or unknown under the approved rule.
6. **Representation/evidence requirements:** for each required obligation-stage pair, bind representation ID and obligation ID, architecture state/source commit/tree, required lifecycle stage, evaluator ID/version/source SHA/configuration digest, evidence scope, raw artifact digests, positive and negative controls, pair-specific semantic assessment, and independent review artifact.

Only an authority-authenticated and independently read-back package could support a later scientific decision. Even then, a completeness validator reports evidence for review; an authorized human must record approval separately. This package does not implement a production trust-anchor or approval verifier.

### Required negative cases

| Adversarial input | Required outcome |
| --- | --- |
| Missing obligation | Catalog inventory incomplete; list missing ID. |
| Duplicate obligation | Reject duplicate even if row bytes match. |
| Unknown obligation ID | Reject ID outside pinned catalog and approved extension set. |
| Catalog version or digest mismatch | Fail closed before completeness claims. |
| Missing authority | Applicability and mandatory decisions are not authority-backed; denominator not established. |
| Unresolved possibly-mandatory row | Keep Q incomplete; do not coerce to optional or inactive. |
| Missing required lifecycle stage or stage evidence | Lifecycle completeness incomplete; never infer compliance from absence. |
| Missing or conflicting source facts | Mark incomplete or conflicting; never pick the favorable fact silently. |
| Missing exact-pair mapping or control/review artifacts | Representation/evidence requirements incomplete. |
| Well-formed JSON/YAML with unsigned or invalid approval | Never certify scientific approval from syntax or hashes alone. |

The implemented read-only validator covers the non-sensitive proposal inventory and these structural failure classes. It reports decision dimensions separately, does not write files, does not run evaluators, and always emits `scientific_approval=NOT_CERTIFIED`.

## W2/W3 handoff after policy approval

After the accountable authority and independent reviewer approve the Q and lifecycle contract, W2 and W3 can populate a new, versioned matrix with one row per required `(representation, obligation, stage)` pair. Each pair must bind:

- representation ID and obligation ID;
- architecture state and exact source commit/tree SHA;
- approved applicability and mandatory decision artifact IDs/digests;
- required lifecycle stage and stage-policy revision;
- evaluator ID/version, source commit/tree SHA, artifact digest, and configuration digest;
- evidence scope, inspected-item count/scope digest, and raw artifact paths/digests;
- pair-specific semantic assessment with rationale and limitations;
- positive and negative control identities, inputs, outputs, scope, and raw digests;
- independent semantic reviewer role, review artifact and digest, separate from the mapping author.

W2 is responsible for exact source-bound evaluator execution and raw evidence readback. W3 is responsible for the exact-pair semantic assessment. A successful byte readback or engineering evaluator gate does not establish semantic adequacy or scientific coverage. Missing, stale, conflicting, out-of-scope, or insufficient evidence remains `UNKNOWN`. No pair-level evidence is fabricated here.

## Additive contract boundary

Do not change `mono_a1_reference_v1.schema.json`, `mono_a1_exact_pair_evidence_v1.schema.json`, DA01 scoring, or existing frozen evidence. Before any future MONO reference freeze, propose an additive `mono_a1_q_completeness_v1` sidecar/schema that binds:

- catalog and extension pins plus a closure statement;
- authority charter, registry, trust-anchor, signer-scope and decision-artifact digests;
- every obligation's applicability, mandatory, stage and source-fact decision bindings;
- every required representation/obligation/stage evidence contract;
- reviewer role separation, signature/readback evidence, effective dates and revocation/supersession links.

This sidecar remains a proposal until OPEN-03/04 receive real human decisions and an independent reviewer approves its contract. The current validator checks the preparation inventory only.

## Requirement-to-test mapping

| Requirement | Validation evidence |
| --- | --- |
| PA-01: Exact, ordered catalog inventory and pinned version/digest | `test_current_inventory_is_catalog_complete_but_not_an_approved_denominator`; missing/duplicate/unknown/version/digest adversarial cases in `test_catalog_inventory_rejects_incomplete_or_mismatched_inputs` |
| PA-02: No public target-level policy classifications | `test_inventory_rejects_target_level_decisions_in_public_skeleton` |
| PA-03: Separate authority-backed applicability and mandatory status | `test_missing_authority_does_not_back_structurally_supplied_decisions`; `test_unresolved_possibly_mandatory_obligation_stays_incomplete` |
| PA-04: Required lifecycle stages cannot be omitted | `test_missing_required_lifecycle_stage_stays_incomplete` |
| PA-05: Missing/conflicting source facts remain unresolved | `test_missing_source_fact_binding_stays_incomplete`; `test_conflicting_source_fact_bindings_remain_conflicting` |
| PA-06: Exact-pair evidence needs evaluator, scope, raw bytes, controls and independent review bindings | `test_missing_representation_evidence_binding_stays_incomplete` |
| PA-07: Structural validity never certifies authority or scientific approval | `test_structural_fields_never_certify_authority_or_scientific_approval` |

Run the focused checks with:

```bash
uv run python -m experiments.execution.tooling.mono_policy_review_inventory
uv run python -m pytest -q --no-cov -p no:cacheprovider tests/unit/test_mono_policy_review_inventory.py
```
