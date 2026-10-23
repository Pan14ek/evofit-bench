# W0 — MONO-E1 readiness resolution after W3

**Record date:** 2026-10-23

**Repository:** `Pan14ek/evofit-bench`

**Reviewed main HEAD:** `be8ee7d44bdef343c30fd201c411c3cdff748da4` (PR #36 merge)

**Checkpoint:** `G-A1-C4-REF-FROZEN = NOT_READY`

**Disposition:** NO-GO for reference freeze and for either MONO-E1 arm. GO only for the ordered, pre-freeze preparation below.

This record resolves documentation conflicts and classifies W3 findings against repository evidence. It does not execute MONO-E1/E2, B0, Method P, or the scorer; call `freeze_reference`; publish target labels; change frozen DA01 evidence; initiate ΔA5/ΔA6; authorize G1/G4 or production policy authority; or claim independent scientific review. W3's assessment and this record are technical/evidence reviews, not independent human scientific approval.

## Evidence baseline

PR #36 merged as `be8ee7d44bdef343c30fd201c411c3cdff748da4`. The verified `main` branch and the dedicated worktree both resolve to that commit. Its `app/` tree is `007196f68652bc13f6798805793ffdfae96f95f7`, identical to canonical A0.4; the A0.3→A0.4 source pair therefore remains the exact ΔA4 pair despite later documentation commits.

The Git objects for both canonical state commits are present. Their repository trees are `7b951421395f532ca403dab09d76902ff08a807d` (A0.3) and `2b436e0aaf09403ea516d73d20a466a122f86592` (A0.4); A0.3 is an ancestor of A0.4. The canonical A0.4 checkpoint is byte-identified by SHA-256 `7b0b0c7a0c6ac782540466d283c42d7589b8aaeb4af7df62104faa01fd154e8e`; its exact application patch is `6538147b9aa4fa5075314aaa54a0e24ea51f33cf0d314342e926d41dabec17ac`.

The current-main post-merge workflow is GitHub Actions run [39904998039](https://github.com/Pan14ek/evofit-bench/actions/runs/39904998039), triggered by `push` on the exact reviewed HEAD; `development-quality` completed **PASS**, including `uv sync --frozen --extra dev` and `make development-quality`. The prior W3-cited run 39862039360 is evidence for its own commit `ce0ae8164d35bbf321ba65af0a21a48077ef8c48`; it is not a substitute for run 39904998039. W3's six focused local test passes are accepted as reported, not rerun here and not promoted to scientific evidence.

## W3 finding dispositions

| W3 finding | W0 disposition | Repository evidence and limit |
| --- | --- | --- |
| F-01: exact A0.3/A0.4 commits, trees, and ancestry | **Accept, source identity only.** | Canonical checkpoints, `W3_HANDOFF.md`, and Git object readback agree. The new [V1 source-identity addendum](../experiments/execution/MONO_A1_PROTOCOL_V1_W0_ADDENDUM.md) supersedes only the stale `UNASSIGNED` fields. |
| F-02/F-03: ΔA4 source change and query delegation | **Accept with wording correction.** | The canonical patch changes `app/modules/reporting/service.py` and `app/modules/reporting/public.py`; `Tasks.public.get_task_summary` existed before ΔA4. ΔA4 changes Reporting to use it. This is not proof of target labels or a new mandatory obligation. |
| F-04/F-05: graph and declared architecture invariants | **Accept, within static source scope.** | A0.3/A0.4 manifests preserve the five capability edges and declare one process, one PostgreSQL database, synchronous calls, no broker, unchanged REST behavior, and caller-managed sessions. These are versioned source contracts, not deployment/runtime attestation. |
| F-06: A0.4 engineering evaluator gates | **Accept narrowly.** | `A0_4_REPORT_QUERY_PORT.yaml` requires `AC_PUBLIC_API` and `AC_MODULE_GRAPH`; `AC_DATA_OWNERSHIP` is `NOT_APPLICABLE`. This is an engineering acceptance policy for that state, not complete scientific `Q(A_after)`. |
| F-07: canonical W2 evidence byte readback | **Accept, engineering evidence only.** | Canonical A0.3/A0.4 indices and the historical readback tests bind manifests, source, evaluator/configuration bytes, observations, and diagnostics. Readback does not establish representation semantic adequacy or authority. |
| F-08: query shape and transactional regression | **Accept within the named tests.** | The unit/integration tests and PR #34 hosted run cover the reported delegation, four summary fields, and rollback case. They do not prove every REST/data path or production runtime behavior. |
| C-01: stale protocol/checklist source identities | **Accept and correct additively.** | V1 files still contain `UNASSIGNED`, while canonical readback supplies the exact A0.3/A0.4 identities. V1 bytes are preserved; the addendum and Checklist V2 are now the current W0 references. |
| C-02: evaluator approval wording conflict | **Resolve by scope.** | `W3_HANDOFF.md` records W0's 2026-10-21 approval of state-specific engineering policies; parent `architecture/acceptance/CONTEXT.md` called all A1 evaluators proposals. The context descriptions are corrected to distinguish those engineering gates from scientific applicability, semantic adequacy, production authority, G1, and G4, which remain unapproved. |
| U-01: complete denominator and exact-pair mappings | **Accept; blocker remains.** | The public catalog contains 18 obligation IDs and the frozen A0 catalog contains five candidate representations, but neither provides an approved A0.4 fitness mapping or complete applicability/mandatory policy. The policy-pilot registry is DRAFT/OPEN. The two engineering gates are not a denominator. |
| W3 exact-pair assessment | **Accept; pair validity remains UNKNOWN.** | W2 evidence has no `representation_id`; the W3 verifier checks source/evaluator bytes and bindings, not substantive semantic suitability or evidence authority. Synthetic controls only exercise mechanics. |
| W3 P readiness assessment | **Accept; separate blocker.** | `p_interface.py` declares `P_ALGORITHM_STATUS = NOT_READY`, and `require_p_algorithm()` raises `MethodNotReadyError` because impact, activation, candidate, and governance rules are not frozen. No E1 executable algorithm/configuration digest exists. |
| W3 shared inputs, measurement, and custody gaps | **Accept; blockers remain.** | No E1 arm bundles/allowlist digests, common workload/database fixture, runner identity, source-to-image attestation, or W0-authorized scorer-only location is recorded. `freeze_reference` only validates structure/source identities and writes an author-declared seal; it does not authorize W0 or enforce independent review/access control. |

No W3 finding is treated as an independent scientific review. The positive source/readback findings are bounded engineering evidence; all unsupported scientific pairs and policy claims remain `UNKNOWN` or `NOT_AUTHORIZED`.

## Approved engineering gates versus open scientific authority

The following distinction is the W0 clarification:

- **Approved engineering acceptance scope:** the A1 evaluator implementations/configurations and state-specific rules recorded in `architecture/acceptance/a1/W3_HANDOFF.md` and the versioned state configs. At A0.4, `AC_PUBLIC_API` and `AC_MODULE_GRAPH` are required; `AC_DATA_OWNERSHIP` is `NOT_APPLICABLE`. Their exact-source checks fail closed on incomplete scope, identity/configuration mismatch, unresolved imports, undeclared edges, cycles, or noncompliance.
- **What that approval does not decide:** which of the 18 catalog obligations are mandatory/applicable at A0.4; whether the catalog is complete; which lifecycle stages each obligation requires; whether a representation measures an obligation adequately; whether W2 evidence is authoritative for that pair; or whether a policy source has production trust.
- **Still open:** G1 is `INCOMPLETE`; G4 is `NOT AUTHORIZED`. `docs/G1_METHOD_DECISION_REGISTER.md` keeps OPEN-03 lifecycle requirements at `PENDING_INDEPENDENT_REVIEW`, OPEN-04 production policy authority at `PENDING_EXTERNAL_AUTHORITY`, OPEN-05 evaluator/template parity at `PENDING_EXTERNAL_AUTHORITY`, and OPEN-09 independent algorithm/holdout review at `PENDING_INDEPENDENT_REVIEW`. The DRAFT/OPEN pilot registry and synthetic tests cannot close these decisions.

`NOT_APPLICABLE` for the ownership evaluator is an evaluator-policy state; it does not imply that `AC_DATA_OWNERSHIP` is absent, non-mandatory, or outside `Q(A_after)`.

## Source-grounded process for complete `Q(A_after)`

Do not use the two A0.4 engineering gates as the denominator. The public source catalog currently lists 18 obligation IDs in `fitness/catalog/architectural-obligations.yaml` (SHA-256 `8c5bd8fffe3bdb2af8fb85f8d0012bc34673f72866e52daed99fab96f9763011`). The five A0 representation rows in `fitness/catalog/a0-fitness-elements.yaml` (SHA-256 `d1a019bb5389e64351751fe10dabd685b29a0fac383ab4ea5fd21906c807cfef`) are candidate inputs, not the approved A0.4 target universe. An approved authority must state whether the 18-row catalog is exhaustive and how any additional obligation family is handled.

The dependency order for `Q(A_after)` is:

1. **Pin the source universe.** Bind the exact catalog and any approved extension registry by version and SHA-256. Require a completeness/closure statement that accounts for every row and declares how unlisted obligations would be found. An omitted row is not evidence of `INACTIVE`.
2. **Approve the policy source.** An accountable policy authority must approve the charter, registry, applicability rules, mandatory classifications, version/as-of semantics, completeness signer, and trust/revocation process. The current DRAFT/OPEN pilot has no such authority.
3. **Classify every obligation at the exact A0.4 state.** For each catalog/extension ID, record `ACTIVE`, `INACTIVE`, or `UNKNOWN`, mandatory status, rationale, source fact IDs, and byte-bound evidence. A known `ACTIVE` or `INACTIVE` decision needs verified source facts and an approved rule. Missing or conflicting evidence stays `UNKNOWN`; it cannot be converted to `INACTIVE` or `mandatory=false` to make the set close. Any unresolved possibly-mandatory item blocks a complete denominator.
4. **Resolve lifecycle requirements under OPEN-03.** For each obligation, explicitly decide which stages (CI/test, deployment, runtime, or a justified subset) require proof and why. Record stage-specific representation, scope, evaluator capability, observation contract, and treatment of missing stages. Do not infer stages from an available evaluator or an A0 representation. Preserve DA01's frozen denominator; any lifecycle contract for MONO must be separately versioned and reviewed.
5. **Construct the denominator and completeness evidence.** The candidate active mandatory set is the unique set of approved obligations classified `ACTIVE` and mandatory; keep mandatory `UNKNOWN` entries in an unresolved set. Prove that the row set equals the pinned complete universe, every row has a disposition, every disposition is authorized, and lifecycle coverage is closed. No percentage or `complete=true` is valid while any mandatory/applicability/stage item is unresolved.
6. **Bind the proof to the reference.** The current `mono_a1_reference_v1.schema.json` checks consistency of supplied rows and derived active/unresolved ID sets, but does not prove that all catalog rows were supplied, bind a completeness authority, or provide a typed lifecycle-stage registry. Its `additionalProperties: false` also prevents adding this provenance ad hoc. Before a freeze, an independently reviewed, versioned Q-completeness addendum/schema or an equivalently digest-bound scorer custody sidecar must bind the complete-universe proof and stage policy to the reference. Do not change the V1 schema or frozen DA01 contracts in place.

Until that process is authority-approved and complete, every unsupported status stays `UNKNOWN`, the denominator stays `INCOMPLETE`, and no coverage percentage may be computed.

## W2/W3 representation-to-evaluator evidence contract

W2 supplies exact source-bound evaluator results; W3 must separately establish whether a specific representation measures a specific obligation at the required state, source, and lifecycle stage. For every required pair, the scorer-side matrix must bind:

- representation ID and source/configuration digest;
- obligation ID, approved applicability/mandatory status, and stage;
- exact architecture state and source commit/tree;
- evaluator ID/version, exact source/tree, configuration digest, capabilities, inspection scope, non-vacuous count, and raw evidence digests;
- a pair-specific semantic assessment with rationale, limitations, reviewer role, and evidence digest;
- positive and negative controls on that pair, with control inputs, observed results, scope, and readback.

The controls must show that the evaluator can observe the intended in-scope condition and reject a relevant corrupted/out-of-scope condition without relying on vacuous success. W2/W3 engineering fixtures may demonstrate mechanics, but synthetic fixtures are not evidence authority or pair-level scientific proof. A successful `verify_evidence()` only establishes byte readback. An unsupported representation/obligation/evaluator/stage mapping remains `UNKNOWN` until a qualified independent human reviewer has reviewed the exact pair and controls. Keep any target-level answer or operation labels in scorer-only custody; publish neither labels nor scorer content in the PR.

## Method P readiness, separately

The current DEVELOPMENT pipeline and TEST_ONLY positive cases are not a frozen MONO-E1 arm. A genuine P arm requires a separately versioned, general algorithm and exact configuration with immutable source/tree and artifact digests; a deterministic input/output contract; generic handling of all approved obligation states; fail-closed behavior for unknown evidence; no oracle/scorer/network/other-arm access; a digest-bound runner/image; and an independent algorithm/holdout review under OPEN-09. Existing frozen method bytes must remain unchanged; any new executable must be a new reviewed version, not a readiness-flag edit. G1 methodological approval and separate G4 run authorization remain required. Until `require_p_algorithm()` is backed by that reviewed executable and the required authorities approve it, the MONO-E1 P identity is absent and the reference cannot pass its method-identity gate.

## Fair B0/P inputs and measurement to freeze

Before either arm can start, W0 and the runner/evaluator owners must record one immutable study manifest that binds:

- the exact common after-source commit/tree (`d3101c0d3aa9b7b709253b6ec7518416f05f65b9` / `2b436e0aaf09403ea516d73d20a466a122f86592`), architecture facts, approved obligation catalog/policy/stage registry, and common evaluator/capability inventory;
- separate B0 and P allowlists and byte digests, with shared permitted facts/config inputs explicitly enumerated; neither arm receives the reference, scorer, oracle, `.git`, network, or the other arm's input/output;
- unchanged B0 code/config identities and the separately reviewed P version/config identities;
- the same frozen workload definition, database fixture/seed/migrations, environment, application target, runner identity, and image digests, with independently verified source-to-image attestations binding each arm to the same target source SHA;
- comparable exposure and explicit start/stop boundaries. Follow MONO protocol v1's timing separation for adaptation, evaluator, verification, and total time; capture CPU/RSS only when actually sampled and preserve `UNKNOWN`/`NOT_COLLECTED` otherwise.

No E1 bundle, allowlist digest, fixture, runner, image, or source-to-image attestation currently exists in the reviewed record. The known B0 baseline bytes do not establish an E1 bundle; the current P interface remains `NOT_READY`.

## Scorer custody and freeze evidence

Before creating a reference, W0 must name an authorized scorer custodian and a scorer-only location with access controls that exclude method authors/runners and the public repository. The custodian records the reference inventory and exact bytes privately, with role separation for policy approval, pair review, freeze, and readback. A qualified independent human reviewer must review the completeness proof and pair evidence; an AI assessment alone is not independent scientific review. If no such reviewer is available, record that explicitly and do not describe the reference as independently reviewed or blinded.

The public PR may contain only non-sensitive decisions, process, evidence digests, and readiness status. It must not contain expected operations, ground truth, target-level answer keys, private reference rows, or scorer-only artifacts. `freeze_reference(...)` writes an `AUTHOR_DECLARED` seal and does not enforce custody permissions or reviewer independence. Only after all upstream gates pass may the authorized custodian make the one-time write in a new scorer-only directory, then call `load_verified_reference(...)` and verify exact payload bytes, seal metadata, source identities, timestamp, and study ID. The freeze digest may be reported publicly only if the custodian confirms it does not disclose scorer content.

## Dependency-ordered readiness plan

| Order / blocker | Responsible role | Required artifact | Acceptance criteria | Prerequisites and independent review |
| --- | --- | --- | --- | --- |
| 0. Source identity record — **resolved** | W0 evidence recorder | V1 source-identity addendum; Checklist V2 | Git commit/tree objects and ancestry read back; exact ΔA4 patch and state checkpoint agree; later `main` application tree matches A0.4 | Complete. This proves source identity only. |
| 1. Policy authority and lifecycle rules — **open** | Accountable policy authority; methods reviewer | Approved, versioned charter/registry and lifecycle-stage rules with completeness authority | Scope, mandatory/applicability semantics, stage requirements, signer/custody, version/time rules, and closure process are independently reviewable | OPEN-03/04/05; requires external authority plus independent methods/protocol review. |
| 2. Complete `Q(A_after)` — **open** | W0 evidence owner; architecture-quality researcher | Catalog-complete scorer-side Q manifest and digest-bound completeness proof | Every approved universe row is accounted for; statuses and mandatory state are evidence-backed; no unknown possibly-mandatory item; all required stages declared; no percentage with unresolved entries | Requires step 1; independent policy/completeness review. |
| 3. Representation/evaluator pairs — **open** | W2 evaluator owner and W3 semantic assessor | Scorer-side mapping matrix, pair reports, raw evidence, positive/negative controls | Every required pair binds exact representation, obligation, stage, state/source, evaluator/config, complete non-vacuous scope, and reviewed semantic claim; unsupported pairs remain UNKNOWN | Requires steps 1–2; independent evaluator-domain and methods reviewers; W2 byte readback alone is insufficient. |
| 4. Frozen executable P identity — **open** | Method author; independent algorithm reviewer | New versioned executable/configuration, immutable digests, algorithm/holdout review record | `NOT_READY` guard is not bypassed; general deterministic behavior, isolation, and output contract reviewed; existing frozen P bytes unchanged | Requires G1 decisions including OPEN-09 and external authority where relevant; independent reviewer is required. G4 remains separate. |
| 5. Comparable B0/P study inputs — **open** | W0 study owner; runner and database-fixture owners | Study manifest, per-arm allowlists, common fixture/workload, runner/image and provenance records | Exact bytes/digests; same target source/fixture/environment and timer boundaries; separate inputs; independently verified source-to-image evidence; isolation audit passes | Requires steps 1–4 and approved capability parity; independent fairness/security review. |
| 6. Reference assembly and schema path — **open** | W0 reference author; schema owner | Complete private reference plus Q-completeness/stage binding under an approved versioned contract | Schema and cross-artifact readback pass; complete universe and pair matrix match authority; no public scorer content | Requires steps 1–5; independent reference review and scorer-custody review. V1 structural validation alone is insufficient. |
| 7. One-time freeze and verified readback — **not authorized** | Authorized scorer custodian; separate W0 reviewer | Write-once sealed reference and verified readback record | Actual one-time write in scorer-only storage; `load_verified_reference(...)` verifies exact bytes, seal, source IDs, timestamp, study ID; W0 records PASS only afterward | Requires every previous item and explicit W0 authorization; independent human review and custody audit. Do not run arms as part of this preparation. |

## Current gate and next step

`G-A1-C4-REF-FROZEN = NOT_READY`. The source-pair identity sub-item is resolved, but Q completeness, lifecycle policy, exact-pair semantics/authority, executable P identity, shared inputs, custody, and actual freeze/readback are not.

**GO:** proceed with a non-authoritative, catalog-complete `Q(A_after)` proposal skeleton and completeness-evidence plan. Keep unsupported classifications `UNKNOWN`; do not record private target labels publicly. Any classified scorer-side matrix requires an appointed custodian and the approved authority/review path. This is preparation for review, not policy approval.

**NO-GO:** do not call `freeze_reference`, run B0/P or scorer, declare the reference frozen, close G1/G4, or claim MONO-E1 is executable. Reconsider freeze only after the dependency table passes and actual write-once freeze plus verified readback have occurred.
