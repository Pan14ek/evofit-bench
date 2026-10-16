# EvoFitBench — SPEC 03: Impact Analysis & Governed Adaptation

**ID:** EVOFITBENCH_SPEC_03_V1_DRAFT  
**Status:** PROPOSED DEVELOPMENT SPECIFICATION — not a frozen scientific algorithm; not authorization for measured DA01  
**Reviewed main:** da96862518a385a41b2451612a29f9b33bd5dae5 (after merged PR #7), 2026-10-16  
**Deliverables:** technology-agnostic formal method P, implementation contracts, SPEC 01–03 Verification & Validation Test Plan and Test Traceability Matrix.  
**Approval:** review scientific open decisions before G1; ordinary code and synthetic tests may proceed beforehand.

> This is a **design proposal**, based on the working manuscript ``2–5, `docs/RESEARCH_CONTEXT.md` and current EvoFitBench contracts. It does not silently amend an experiment protocol, declare approved policies, or assert empirical scientific results.

## 0. Read-first, precedence and prohibited data

Read `AGENTS.md`, root and ancestor `CONTEXT.md`, `docs/RESEARCH_CONTEXT.md`, `docs/DOMAIN.md`, `docs/ARCHITECTURE.md`, `docs/EXPERIMENT.md`, `docs/TESTING.md` and implementation journals `experiments/execution/P_INPUT_V11.md` and `P_APPLICABILITY_V1.md`. For executable experimental rules, defer to `experiments/execution/da01/PROTOCOL.md`, `INPUT_ISOLATION.md`, `VALIDITY_RULES.md`, `READINESS.md`, `B1_CHECKLIST.md` and exact schemas/source.

The manuscript is authoritative for **scientific intent**; protocol, tested implementations and pinned artifacts for **current execution semantics**. The RQ numbering, human B1 cadence, lifecycle coverage and weights/thresholds discrepancies documented in `docs/RESEARCH_CONTEXT.md` remain OPEN. Do not reconcile them by editing frozen files.

**Strict prohibition:** Never inspect, import, infer from, or incorporate the DA01 private ground truth, scenario-specific expected operations, oracle, independent scorer, another method's outputs or an engineering-acceptance reference checker into P selection logic or fixtures. Do not modify frozen A0/DA01 states, evaluator, evidence, workload/seed, scoring, predictions, V1 method inputs, or historic tags. Method input may not access `.git`, network, scorer, oracle or another method's output. Do not fabricate approved mandates, trust anchors, completeness, human B1 results or scientific outcomes.

G1 = independent review/freeze of general method/protocol; G4 = explicit authorization for **measured** DA01. They do **not** block regular implementation and synthetic tests.

### 0.1 Verified baseline contracts

| Artifact | Current status and required compatibility |
| --- | --- |
| SPEC 01: `p_input_validation.py`, `p_input_export_v2.py`, Snapshot v1.1 | DEVELOPMENT; strict hashes/source/APA/FV/completeness; 12 activation-grade FV_CORE_V1 predicates; V2 candidate B1/P input. |
| SPEC 02: `p_applicability.py`, `p_policy_source_v3.py` | DEVELOPMENT; Strong Kleene `ACTIVE/INACTIVE/UNKNOWN`; 18 obligations; separately pinned policy V3; DRAFT/OPEN pilot **not** approved. |
| `fitness/catalog/architectural-obligations.yaml` | 3 performance, 7 reliability, 8 architecture compliance. Default 1.0 weights are not scientific priority proof. |
| `fitness/traceability/a0-traceability.yaml` | Partial A0 graph; no completeness guarantee for evolved architectures. |
| `fitness/catalog/a0-fitness-elements.yaml` | Five A0 stage-specific representations; field `covers` alone does not prove coverage. |
| `prediction.schema.json` v1 | `target_type=obligation` permits only `add`; `target_type=representation` permits `retain/replace/deactivate/adjust`. Non-retain `predicted_affected` and `proposed_operations` must agree. No HOLD field. |
| `candidate_configuration.schema.json` v1 | Candidate configuration, parent hash, representations and local validation; `candidate_validation=valid` is **not** ACCEPT. |
| `obligation_verdict.schema.json`, `coverage_assessment.schema.json` | Independent pair-specific semantic evidence/coverage for scoring; private reference outputs must never become P inputs. |
| `experiments/execution/tooling/inputs.py` | Shared B1/P capability names exist, but `generic_candidate_templates=[]`: no executable generic replacement/add template currently exists. |
| `p_interface.py`, `P_ALGORITHM_STATUS.md` | P protocol exists, algorithm remains `NOT_READY`. |
| `READINESS.md` | G1 incomplete/G4 not authorized; no measured B0/B1/P study or human B1 session. |

**Compatibility rule:** add separate versioned DEVELOPMENT diagnostics/schemas; never overload frozen v1 prediction/scorer/input schemas with governance states. V1/2/3 existing outputs must remain regression-compatible.

## 1. Scientific problem and formal model

After an architecture change an old fitness evaluator may still execute but measure the wrong subject, scope, stage or obligation. The research object is a **versioned configuration of architectural fitness controls**, NOT the application architecture.

\[
\Phi_t=\langle C_t,R_t,\alpha_t,\theta_t,H_t,v_t\rangle.
\]

`C` = persistent architectural criteria (intent/identity); `R` = CI/test/deployment/runtime representations (evaluator, metric, scope, context, policy and evidence contract); `α` = optional weighting; `θ` = threshold rules; `H` = noncompensatory mandatory/hard constraints; `v` = version/provenance.

An obligation `q` specifies a particular normative requirement, criterion, intent, applicability rule, scope, policy basis, mandatory flag, version and provenance. `K_t=(Z_t,Π_t,Γ_t,ν_t)` is fact/policy/evidence-completeness/version knowledge; `G_T` is a typed traceability graph.

Method P is a function from **verified** states/knowledge/config/trace/capabilities to typed change `Δ`, possibly affected set `I`, justified operations `O`, materialized candidate `Φ'`, decision `D∈{ACCEPT,REJECT,HOLD}` and explanations/provenance. It never optimizes or edits the business architecture itself.

**Separate four questions:** applicability (is q normatively required?), compliance (does actual architecture meet q?), representation coverage (does a semantically valid r with evidence control q?), governance (is adapted Φ safely admissible?). Successful evaluator exit, a metric name, a `covers` declaration, or a high weighted sum proves none of the latter by itself.

### 1.1 Applicability, evidence and mandatory coverage

Reuse SPEC 02 exactly:

\[
g_q(K_t)\in\{ACTIVE,INACTIVE,UNKNOWN\}.
\]

Define method-side pair validity separately from the **independent** reference verdict:

\[
V_P(r,q,A,E)\in\{VALID,INVALID,UNKNOWN\}.
\]

`VALID` needs proven scope/context/stage/semantic match, source-version compatibility, real executable/nonvacuous evaluator, obligation-specific adequate evidence and provenance. `INVALID` needs a proved mismatch or necessary condition failure. Missing/ambiguous proof is `UNKNOWN`. Nonzero evaluator exit signaling *actual compliance violation* must be distinguished from failure of monitoring semantics; this possible mismatch with frozen reference validity is `OPEN-07`.

For an **approved** required lifecycle-stage set `S(q,A)`:

\[
Covered_P(q,s)=1\iff \exists r\in R_{active}:
stage(r)=s\land q\in covers(r)\land V_P(r,q,A,E)=VALID.
\]

If not proven, report NOT_DEMONSTRATED with separate INVALID/UNKNOWN/missing reasons. Do **not** create new multistage obligations: frozen DA01 independent RQ2 follows its current exact-pair and full-denominator rules. Unknown normative status in OPEN registry is not inactive.

### 1.2 Mandatory safety invariants

| ID | Assertion |
| --- | --- |
| INV-01 | Criterion intent and approved hard constraints cannot silently be weakened. |
| INV-02 | INACTIVE/deactivate demands verified normative negative proof of exact scope/completeness; UNKNOWN is never INACTIVE. |
| INV-03 | No deactivation of r if another ACTIVE or UNKNOWN mandatory q may still need it. |
| INV-04 | Mandatory positive coverage requires correct, nonvacuous, current, exact-pair evidence, not just pass/field/aggregate. |
| INV-05 | Wrong authority, time, revision, provenance, digest or reuse of stale validation never yields a positive proof. |
| INV-06 | Add/replace require a real materializable, digest-pinned, authorized evaluator/template; never invented checkers. |
| INV-07 | Retain on impacted r requires positive semantic adequacy; implicit unchanged retain is not verified coverage. |
| INV-08 | Stable identifiers, canonical serialization, unique targets, bound parent hashes and immutable history. |
| INV-09 | Proposed operations and v1 non-retain affected targets must agree; duplicates/conflicts forbidden. |
| INV-10 | No ACCEPT on invalid or unresolved mandatory coverage; HOLD cannot publish; rollback needs fresh current-state validation. |
| INV-11 | Semantic decision/order/hash deterministic for identical inputs and method version; timestamps are external. |
| INV-12 | No oracle/specific scenario expected-answer access or hardcoded DA01/obligation-ID logic. |

### 1.3 Boundaries for α and θ

Keep α and θ in formal Φ, but **do not implement generalized automatic weight or threshold optimization** in core v1. `adjust` is permitted only if an externally legitimate, exact-parameter, versioned bounded soft-adjustment rule exists; never relax H or redefine intent. An approved context-dependent threshold rule evaluated at a new context is not automatically a new configuration version. Record manuscript RQ2's weight/threshold part as untested until separately implemented and validated.

## 2. Method P — procedure and decision semantics

### 2.1 Preflight and typed differences

Consume verified and allowlisted SPEC 01 Snapshot/source manifest, SPEC 02 applicability (before and after if adequately proven), current Φ, complete obligation catalog, traceability, common evaluator capabilities and method-authorized evidence. Bind architecture SHAs, policy revision, ruleset hash, common input digest and evaluation time. Invalid manifest, integrity, schema, allowlist or cross-source binding produces **INPUT_REJECTED**, not a fitness REJECT. Well-formed but unverified policy, absence/completeness or evaluator evidence produces **HOLD**.

Build a typed difference for architectural facts: ADDED, REMOVED, VALUE_CHANGED, SCOPE_CHANGED, VERSION_CHANGED, UNCHANGED or INDETERMINATE, retaining predicate, subject, scope, old/new values or hashes and evidence references. A missing row from an incomplete source is **not** proven removed. Build policy difference separately (mandates, exceptions, retirement, conditional rules, authority, effective scope/time and closure); policy-only changes may occur with identical architecture SHA. Compare applicability for **every** obligation in the catalog; unknown before-state is not fabricated.

Normalize all independent inputs and outputs into stable ID ordering. Reject or preserve ambiguity on contradictory duplicate identities; never last-write-wins.

### 2.2 Typed, criterion-centric impact

Create a graph with typed nodes for architectural fact/element, normative policy, obligation, criterion, representation, evaluator and evidence contract. Type, scope, version and provenance constrain edges. Valid paths may connect changed fact/policy to obligation, then criterion and representation. The A0 graph is partial, and absence of its link is not proof of no impact.

\[
Seed = Map(\Delta Z \cup \Delta \Pi \cup \Delta Q,G_T)
\]
\[
I = Representations(Reach_{typed}(Seed,G_T))
    \cup Uncovered(Q^{ACTIVE}_{after}) \cup UnresolvedLinks .
\]

Produce separate classifications PROVEN_AFFECTED, POSSIBLY_AFFECTED, NOT_AFFECTED_WITH_PROOF and UNRESOLVED, each with causal paths/reasons. Reachability means **requires reassessment**, not automatically invalid or replace. Missing coverage of an ACTIVE q must be found even when q does not occur in trace graph. No architecture change does not excuse a new policy requirement. Reordering graph rows or adding unrelated independent nodes cannot invent impacts.

### 2.3 Exact representation–obligation semantic validity

For every relevant pair (r,q), verify exact criterion intent, normative scope, stage/context, evaluator artifact availability, target resolution, non-vacuous inspected subjects, evidence contract, revision/time, origin and pair-specific semantics. Output method-side VALID / INVALID / UNKNOWN with stable reasons and references. A field named covers, a zero exit code or a metric name is insufficient. Missing proof gives UNKNOWN; known incompatibility gives INVALID. Keep evaluator execution, actual architectural compliance and capability to *monitor* q distinct.

**Do not feed independent scorer-produced verdicts to P.** P may derive its own bounded self-assessment using only admissible method input and independently sourced admissible test evidence. The official reference verifier evaluates only **after** an independently sealed prediction.

### 2.4 Deterministic operations

| Operation | Strict precondition | Effect / if impossible |
| --- | --- | --- |
| RETAIN | No justified change; or positive validity after potential impact | Preserve representation; unresolved mandatory pairs still force HOLD. |
| REPLACE | Old r provably semantically inadequate; a real, digest-pinned executable successor covers *all remaining mandatory links* | Materialize successor, preserve parent/history; otherwise HOLD/NEEDS_IMPLEMENTATION. |
| ADD | q provably ACTIVE, mandatory coverage absent, real evaluator/template available | Legacy prediction targets the **obligation**; candidate adds verifiable new representation. Missing template: HOLD. |
| DEACTIVATE | Verified normative INACTIVE plus no ACTIVE/UNKNOWN mandatory obligation depending on r, including unresolved links | Deactivate r without erasing history; otherwise forbidden. |
| ADJUST | Explicit authorized versioned and bounded soft-parameter rule, no weakening of H or intent | Only supported authorized adjustment; no automatic weight/threshold optimization in v1. |

A shared r linked to two q cannot be deactivated merely because one becomes inactive. A replacement may not discard another still-necessary q. Multiple valid r can cover one q, counted once using pair evidence.

Only **actually materializable** operations may enter feasible-candidate selection. At current baseline the common capability inventory has no generic candidate templates. It is therefore legitimate for a real ADD/REPLACE to remain HOLD/NEEDS_IMPLEMENTATION; inventing checker code, a prepared reference checker, or oracle-inspired templates is forbidden. Synthetic tests may supply isolated independently constructed generic checker artifacts clearly labelled TEST_ONLY.

Proposed deterministic choice among fully evidenced feasible candidates is lexicographic: (non-retain operation count, known additional evaluator cost, canonical operation/artifact IDs). A versioned cost model and resource/search budget must be supplied; unknown cost does **not** mean zero. Budget exhaustion => HOLD/BUDGET_EXHAUSTED, not an optimality claim.

**Open compatibility question:** frozen v1 prediction allows ADD on an obligation ID, although one new evaluator may cover several q. Proposed development owner = lexicographically first positively ACTIVE uncovered q the evaluator actually covers, with separate pair links for others. Before any measured execution, independently review compatibility with the unchanged scorer rather than tailoring to DA01.

### 2.5 Materialization, governance and result precedence

Assemble full candidate Φ with unique stable representation IDs, hashed evaluator artifacts, parent configuration path/digest, changes, stages/scopes/coverage links and source provenance. Run existing validate_candidate and all semantic/hard/missing-coverage checks. candidate_validation.status=valid means a local validation, **not** ACCEPT.

New **additive DEVELOPMENT output** contracts (do not edit legacy v1 schemas): p_impact_assessment_v1, p_pair_assessment_v1, p_adaptation_trace_v1 and p_governance_decision_v1. Their JSON Schemas must be strict, identity/version-bound, hash-bound and reason-coded. Governance decision includes method/algorithm versions, original and target SHAs, policy source/ruleset/digest/as-of, parent/candidate hashes, affected objects, evidence refs, blocking obligations/pairs, invariant and cost verdicts, result and unresolved reasons.

Decision precedence:

1. **INPUT_REJECTED** on invalid/tampered/prohibited method input; no candidate, no counted algorithm result.
2. **REJECT** an individual candidate with a proven hard, provenance, unauthorized parameter or cost violation. Rejection of *one* candidate does not preclude considering another feasible candidate.
3. **HOLD** when essential obligation applicability, semantic coverage, evaluator materialization, trusted policy/completeness or known cost is unresolved, or search budget exhausted. No candidate publication.
4. **ACCEPT** only when a complete candidate is materialized and all required hard, mandatory coverage, semantic, evidence, provenance and cost checks are **positively verified**; no residual mandatory uncertainty. A no-op ACCEPT likewise requires positive target validity, not mere absence of observed changes.

The old prediction-v1 and candidate-v1 outputs must be produced only through explicit compatible adapters and validated with existing validators; a HOLD diagnostic must not masquerade as a successful v1 prediction.

### 2.6 Versioning and safe rollback

Use an append-only version/event log: PROPOSED, VALIDATED, ACCEPTED, REJECTED, HELD, ROLLED_BACK, ROLLBACK_BLOCKED, with parent/child hashes, architecture and policy versions, operations, reasons, evidence and timestamps. Canonical semantic outputs must be deterministic for equal input and algorithm version; timestamps/seals reside outside the deterministic content digest.

Rollback to an earlier Φ is **conditional on revalidating it against the current architecture/policy/obligations/evidence**. If unsafe or unknown, return ROLLBACK_BLOCKED/HOLD, not an asserted successful restoration. Detect source/policy changes between validation and atomic write-once publication; abort publication on stale context.

### 2.7 Orchestration pseudocode

    ctx = SPEC01_VERIFY_BUNDLE_AND_BIND_ALL_REVISIONS(input)
    if ctx.invalid: return INPUT_REJECTED
    before = SPEC02_ASSESS_BEFORE(ctx)
    after  = SPEC02_ASSESS_AFTER(ctx)
    delta = TYPED_DIFF_FACTS_POLICIES_OBLIGATIONS(ctx, before, after)
    graph = VALIDATE_TYPED_TRACEABILITY(ctx.traceability, ctx.catalog)
    impact = CONSERVATIVE_IMPACT(delta, graph, after)
    pairs = ASSESS_METHOD_SIDE_PAIR_SEMANTICS(ctx, after, impact)
    deficits = REQUIRED_MANDATORY_CONTROL_GAPS(after, pairs, authorized_stage_contract)
    options = ENUMERATE_ONLY_JUSTIFIED_MATERIALIZABLE_OPERATIONS(impact, deficits)
    for cand in DETERMINISTIC_BOUNDED_FEASIBLE_CANDIDATES(options, ctx.cost_rules):
        checks = INDEPENDENT_METHOD_SIDE_CANDIDATE_VALIDATION(cand, ctx)
        if checks.all_required_positive:
            return ACCEPT_WITH_PROVENANCE_AND_V1_PROJECTION(cand)
        record_candidate_failure(checks)
    if exhaustively_proven_infeasible: return REJECT_WITH_REASONS
    return HOLD_WITH_UNRESOLVED_REASONS

This is proposed research pseudocode, not an assertion that the remaining tie/cost/decision ambiguities are already independently approved.

## 3. Planned implementation and compatibility

Recommended single-purpose modules under experiments/execution/tooling/: p_impact.py (typed diff/graph), p_semantic.py (method-side exact-pair assessment), p_operations.py (finite operation choice), p_candidate.py (actual candidate/version/compatibility), p_governance.py (invariants/decisions/rollback), p_adaptation.py (orchestration). Integrate p_interface.py only once the DEVELOPMENT method passes documented tests; a readiness flag must **not** suggest G1/G4 cleared.

New output schemas should be additive, strict, and covered by semantic validators (not just JSON Schema). Preserve original V1/V2/V3 input allowlists, scorer, prediction/candidate schemas, archived A0 evaluator, and B1/P common fact/policy bytes. Do not add files to the restricted pilot-policy source path. Keep relevant CONTEXT.md and docs accurate.

## 4. Verification & Validation Test Plan — SPEC 01–03

### 4.1 Three distinct types of evidence

**Code verification** demonstrates implementation correctness against contracts and invariants: unit, schema/contract, negative, boundary, integration, adversarial, property-based/metamorphic, isolation and regression tests.

**Development method validation** uses independently designed synthetic/falsification scenarios to test whether the general P algorithm can detect unsafe false deactivation, stale or vacuous control, unsupported evaluator and incomplete traceability. Synthetic signed/approved test fixtures are explicitly **not** real normative authority.

**Scientific experimental validation** requires a pre-frozen generic algorithm/protocol, independent withheld oracle, authentic human B1, approved trust/evidence, verified isolation and a measured DA01 authorization (G1/G4). DA01 addresses executable RQ1/RQ2 *only* and is **one architecture transition**, not a population. Synthetic PASS must never be called a measured advantage.

### 4.2 Every test must declare

- Stable test ID, requirement ID(s), test category and implementation location.
- Fixture provenance (synthetically authored independently of oracle), source digests, assumed trust status, architecture/config/ruleset revisions.
- Setup, allowed input, mutation/fault stimulus, expected result and stable reason codes; positive, negative, boundary and integration paths.
- Independent test derivation; no copying scenario ground truth or private scorer outputs.
- Actual PASS / FAIL / SKIP / BLOCKED, exact command/CI URL, and whether the check can run without Docker, DB or external policy authority.
- Mapping from test to requirement and to invariants; report **requirement coverage** separately from Python statement/branch coverage and scientific power.

Never mark a skipped Docker negative probe as PASS. The current application-line coverage gate in make quality is **not** a P method coverage measure.

### 4.3 Requirement registry and proof obligations

| ID | Component | Required behavior |
| --- | --- | --- |
| C01 | SPEC 01 | Strict architecture-policy Snapshot/FV/source/hash/schema/version contract; fail closed on tamper. |
| C02 | SPEC 01 | External APA authority/approval and scoped completeness evidence; missing or forged proof remains undetermined. |
| C03 | SPEC 01 | V1 compatibility, strict V2 source projection and method bundle isolation. |
| A01 | SPEC 02 | Closed typed AR-DSL, Strong Kleene truth tables, evidence trace and deterministic evaluation. |
| A02 | SPEC 02 | Exact 18-obligation coverage in results, including UNKNOWN rather than absent row. |
| A03 | SPEC 02 | Mandates, conflict, exception/retirement and registry closure with proof and time/scope. |
| A04 | SPEC 02 | Prevent stale SnapshotValidationResult and evidence-ledger replay/rebinding. |
| A05 | SPEC 02 | Independently pinned V3 policy bundle; identical B1/P normative facts/policies; P-only trace allowed. |
| A06 | SPEC 02 | Synthetic export → SPEC 01 verify → ledger → SPEC 02 end-to-end determinism. |
| S01 | Cross-cutting | Deny oracle, scorer, Git history, forbidden methods' outputs and network access. |
| P03-01 | SPEC 03 | Verified, exact revision/provenance-bound P preflight. |
| P03-02 | SPEC 03 | Typed architecture, policy and obligation state differences. |
| P03-03 | SPEC 03 | Typed criterion-centric trace graph; detect missing, dangling and unproven links. |
| P03-04 | SPEC 03 | Conservative but discriminating impact detection and negative controls. |
| P03-05 | SPEC 03 | Exact-pair stage/context/semantic/nonvacuity and evidence assessment, separate compliance. |
| P03-06 | SPEC 03 | Full mandatory control coverage and UNKNOWN handling without scalar compensation. |
| P03-07 | SPEC 03 | General and deterministic retain/replace/add/deactivate/adjust, including shared representation constraints. |
| P03-08 | SPEC 03 | Materialized, real hashed evaluator artifact or explicit blocked status. |
| P03-09 | SPEC 03 | Parent/hash/ID-bound candidate, v1 prediction/candidate adapters and schema validation. |
| P03-10 | SPEC 03 | Input error vs ACCEPT/REJECT/HOLD precedence and no unsafe publish. |
| P03-11 | SPEC 03 | Immutable provenance, conditional rollback and stale-context concurrency safety. |
| P03-12 | SPEC 03 | Deterministic canonical semantics, bounded search and known cost rules. |
| P03-13 | SPEC 03 | Regression of V1/V2/V3, B1/P parity and exact frozen artifact bytes. |
| P03-14 | SPEC 03 | Full synthetic P path without oracle leakage. |
| E01 | Measured study | Separate G1/G4 approval, actual B0/B1/P evidence, independent scoring and research statistics — NOT part of SPEC 03 engineering PR. |

### 4.4 Test Traceability Matrix — SPEC 01 and SPEC 02 regression

These rows map **required observations** to current test entry points, but they are not claims that every row has already passed. The agent must inspect/update coverage and report exact local results.

| Test ID | Req | Types | Input / expected behavior | Existing test entry point |
| --- | --- | --- | --- | --- |
| TT-C01-01 | C01 | positive, negative, boundary | Correct v1.1 Snapshot passes; malformed version, predicate, fact type/state/scope or required field rejected. | tests/unit/test_p_input_contract_v11.py |
| TT-C01-02 | C01,C03 | negative, boundary | Source/manifest hash or size mismatch, symlink, forbidden file, extra role rejected; legacy export unchanged. | tests/unit/test_p_input_v2_isolation.py |
| TT-C02-01 | C02 | positive, negative | Approved policy verified only via admissible independent trust; unsigned, DRAFT, revoked or forged approval never accepted. | tests/unit/test_p_input_authority_validation.py |
| TT-C02-02 | C02 | boundary, negative | Exact scoped completeness with matching source can support absence; wrong predicate/scope/revision/time, verifier errors stay undetermined. | tests/unit/test_p_input_authority_validation.py |
| TT-A01-01 | A01 | property, table | Strong Kleene NOT/AND/OR across T/F/U, consistent evaluation reasons for reordered independent children. | tests/unit/test_p_applicability_ruleset_v1.py |
| TT-A01-02 | A01 | negative, boundary | Disallowed expression/selector, type confusion, bool-as-int, oversize AST/depth/conditions, duplicate unsorted IDs rejected. | tests/unit/test_p_applicability_ruleset_v1.py |
| TT-A02-01 | A02 | positive, property | Every catalog q has exactly one ACTIVE/INACTIVE/UNKNOWN result, stable order and evidence reasons, no dropped UNKNOWN. | tests/unit/test_p_applicability_policies_v1.py |
| TT-A03-01 | A03 | negative, boundary | OPEN Registry, conflicting mandates/overrides, wrong precedence evidence, expiry half-open boundary cannot infer unsupported ACTIVE/INACTIVE. | tests/unit/test_p_applicability_policies_v1.py |
| TT-A04-01 | A04 | negative, replay | Correct-looking SnapshotValidationResult from another hash/revision/policy is rejected, not rebound. | tests/unit/test_p_applicability_policies_v1.py; tests/integration/test_p_applicability_v3.py |
| TT-A05-01 | A05,C03 | integration, metamorphic | Policy-only V3 revision changes policy digest but not pinned architecture; B1/P common policy bytes equal. | tests/integration/test_p_applicability_v3.py |
| TT-A06-01 | A06 | integration, negative | Export→validate→external test ledger→three-state assessment deterministically, tampered intermediate refuses proof. | tests/integration/test_p_applicability_v3.py |
| TT-S01-01 | S01 | adversarial, integration | Method input cannot access oracle/scorer/.git/network/other output; forbidden fields/paths denied. Docker probe unavailable = SKIP/BLOCKED, not PASS. | tests/unit/test_da01_inputs_and_isolation.py; existing isolation probes |

### 4.5 Test Traceability Matrix — SPEC 03 (new required cases)

**Fixture independence:** use fresh generic predicate/criterion/obligation and representation IDs, synthetic source revisions and synthetic test-only verifiers. Do not derive a test answer from DA01 ground truth or target-specific expected operations.

| Test ID | Req | Category | Test stimulus | Required observable outcome |
| --- | --- | --- | --- | --- |
| TT-P03-01 | P03-01 | positive/integration | Fully well-formed, consistent, synthetic verified Snapshot + applicability and correct hashes. | P preflight records bound source/policy/ruleset/context identity. |
| TT-P03-02 | P03-01 | negative | Swap policy SHA, as-of, architecture SHA or applicability source after verification. | Fail closed (INPUT_REJECTED) or HOLD for genuine undecidable proof; no ACCEPT. |
| TT-P03-03 | P03-01,S01 | adversarial | Extra input role, path traversal, symlink or oracle marker in bundle. | Reject before P method logic; no leaked read. |
| TT-P03-04 | P03-02 | positive | Typed added/removed/changed fact with matched before/after complete sources. | Exact change kind, scope and provenance. |
| TT-P03-05 | P03-02 | boundary | Same architecture SHA, valid change to separate policy authority/condition. | Policy-only difference and relevant obligation reassessment. |
| TT-P03-06 | P03-02 | negative | Missing before-state evidence or contradictory fact identities. | INDETERMINATE; no invented REMOVED/UNCHANGED. |
| TT-P03-07 | P03-02,P03-12 | metamorphic | Permute facts and independently labeled input record order. | Same canonical diff/decision/digest. |
| TT-P03-08 | P03-03 | positive | Typed graph has two paths and one independent unrelated criterion. | Valid typed reach with source paths and excluded unrelated path. |
| TT-P03-09 | P03-03 | negative | Dangling/duplicate/obsolete edge and incomplete link inventory. | Unresolved link diagnostic; never silently NOT_AFFECTED_WITH_PROOF. |
| TT-P03-10 | P03-04 | positive | One changed fact affects one control, another control independent. | Affected only where justified; unrelated check not auto-replaced. |
| TT-P03-11 | P03-04 | boundary | New ACTIVE q absent from original trace graph. | Mandatory missing-coverage discovery despite missing edge. |
| TT-P03-12 | P03-04 | metamorphic | Add unrelated graph nodes and reorder edges. | Pre-existing independent impact classifications unchanged. |
| TT-P03-13 | P03-05 | positive | Exact pair with right scope/stage, actual test-only executable, resolved nonvacuous inspected subjects and proof. | P-side VALID with exact pair refs; synthetic status explicit. |
| TT-P03-14 | P03-05 | negative | Evaluator exit zero but no resolved target or no inspected subjects. | VACUOUS / not valid coverage. |
| TT-P03-15 | P03-05 | negative | Same metric, wrong stage/subject/scope/context or swapped obligation ID. | Pair invalid/unknown as proven; no cross-pair reuse. |
| TT-P03-16 | P03-05 | boundary | Cleanly executed evaluator detects actual architectural violation vs evaluator infrastructure crash. | Separate compliance violation from evaluator monitoring adequacy / crash; no false PASS. |
| TT-P03-17 | P03-05 | metamorphic | Same raw bytes cited for q1 and q2 with different semantics. | Pair judgments independent even with shared source evidence. |
| TT-P03-18 | P03-06 | positive | Two valid pair-backed representations cover same mandatory q. | q counted **once**, not twice. |
| TT-P03-19 | P03-06 | negative | High aggregate score plus covers declaration but mandatory exact-pair evidence absent. | Not demonstrated covered; no ACCEPT. |
| TT-P03-20 | P03-06 | boundary | ACTIVE/INACTIVE/UNKNOWN mix and an unapproved multistage requirement. | UNKNOWN intact; no fabricated stage or altered frozen denominator. |
| TT-P03-21 | P03-07 | positive | An unchanged valid representation survives unrelated change. | RETAIN only; no false non-retain target. |
| TT-P03-22 | P03-07,P03-08 | positive | Proven-invalid old r and a valid, hash-pinned, real replacement for all still-active q. | REPLACE materialized, no lost mandatory links. |
| TT-P03-23 | P03-07,P03-08 | positive | New ACTIVE uncovered q, valid generic template/capability. | ADD on obligation target; real new r in candidate with exact proof. |
| TT-P03-24 | P03-07 | negative | One r serves two q; q1 becomes INACTIVE, q2 remains ACTIVE. | Cannot deactivate whole r. |
| TT-P03-25 | P03-07 | negative | UNKNOWN mandatory q or missing absence/completeness claim. | No deactivate, HOLD/unresolved. |
| TT-P03-26 | P03-07,P03-09 | boundary | Duplicate/contradictory operations on same typed target. | Reject candidate/prediction with stable validation reason. |
| TT-P03-27 | P03-07 | negative | Unauthorized adjustment of weight, soft threshold or hard requirement. | No accepted adjustment; proven hard relaxation REJECT. |
| TT-P03-28 | P03-08 | negative | Only evaluator name, empty generic_candidate_templates, no artifact bytes. | HOLD/NEEDS_IMPLEMENTATION; no fictional ADD. |
| TT-P03-29 | P03-08 | adversarial | Wrong template hash, nonallowlisted checker path, mutable external reference. | Materialization forbidden; fail closed. |
| TT-P03-30 | P03-09 | positive | Unique IDs, complete candidate, parent digest, actual artifact and exact revision. | Pass candidate v1 and extra semantic checks. |
| TT-P03-31 | P03-09 | negative | New representation ID collision, orphaned q, stale parent hash or missing evaluator. | Candidate validation failure with audit. |
| TT-P03-32 | P03-09,P03-13 | regression | Output adapter projects non-retain and proposed operations to old v1 prediction schema. | validate_prediction passes without changing frozen schema. |
