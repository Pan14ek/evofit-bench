# EvoFitBench — SPEC G1: Methodological Freeze Preparation

**Specification ID:** SPEC_G1_METHODOLOGICAL_FREEZE_PREPARATION  
**Status:** PROPOSED / DOCUMENTATION-ONLY / AWAITING INDEPENDENT REVIEW  
**Date:** 2026-10-16  
**Verified baseline:** Pan14ek/evofit-bench, main at 740c60aeece6e424c56ba081eacc079dc0f16d74 (merged PR #10). Verify latest main before implementation.  
**Target:** docs/SPEC_G1_METHODOLOGICAL_FREEZE_PREPARATION.md

> **Authority boundary:** The deliverable is a **G1 review package**, not a G1 sign-off, frozen scientific method, authorization of a measured experiment, or a scientific result. G1 remains **INCOMPLETE**, G4 **NOT AUTHORIZED**, and the P measured interface **NOT_READY**. Successful TEST_ONLY synthetic ACCEPT does not establish production authority.

## 0. Read-first sources and precedence

Read these **actual repository documents** before drafting any review text:

1. [Agent instructions](../AGENTS.md) and applicable local CONTEXT.md files.
2. [DA01 protocol](../experiments/execution/da01/PROTOCOL.md), [scoring rules](../experiments/execution/da01/SCORE_RULES.md), [independent validity rules](../experiments/execution/da01/VALIDITY_RULES.md), [input isolation](../experiments/execution/da01/INPUT_ISOLATION.md), [B1 checklist](../experiments/execution/da01/B1_CHECKLIST.md) and [DA01 readiness](../experiments/execution/da01/READINESS.md). These control current executable experiment meaning and are not silently editable.
3. [Research context](RESEARCH_CONTEXT.md) (especially manuscript-versus-executable RQ numbering and M-01…M-06), [experiment context](EXPERIMENT.md), [parent SPEC 03](SPEC_03_IMPACT_ANALYSIS_AND_GOVERNED_ADAPTATION.md), [SPEC 03 completion](SPEC_03_COMPLETION_AND_READINESS.md) and [testing plan](TESTING.md).
4. [Existing G1 decision register](G1_METHOD_DECISION_REGISTER.md) (OPEN-01…OPEN-10), [SPEC 03 evidence/traceability](SPEC_03_IMPLEMENTATION_TRACEABILITY.md) (final PR #10 section supersedes historical pre-fix statuses), [P development status](../experiments/execution/da01/P_ALGORITHM_STATUS.md), [implementation description](../experiments/execution/P_GOVERNED_ADAPTATION_V1.md) and [Snapshot v1.2 DEVELOPMENT note](../experiments/execution/P_INPUT_V12_DEVELOPMENT.md).
5. Relevant current implementation in experiments/execution/tooling/, JSON schemas, and **permitted** synthetic unit/integration tests, only to validate source-to-model mapping.

**Forbidden input:** DA01 private ground truth, scenario-specific expected operations, private oracle/reference scorer implementation or output, engineering acceptance implementation as a method answer source, other methods' results, sealed predictions and protected test-module internals. Do **not** read scenario-specific ground-truth sections of ARCHITECTURE_EVOLUTION_SCENARIOS_V1.md while creating the preregistration or Method P review. Do not run tests/unit/test_da01_execution.py or tests/unit/test_research_schema_foundation.py, or any quality command that inadvertently runs them. No viewing protected material to “verify” the correct answer.

**Verified engineering starting point:** merged PR #10 introduced a versioned Snapshot v1.2 DEVELOPMENT extension with independent before/after policy closure claims. The current SPEC 03 evidence report describes TEST_ONLY V3 no-op and descriptor-authorized ADD reaching governance ACCEPT, 12/12 S03R rows PASS, and a 60-row historic matrix with 59 PASS and TT-P03-43 BLOCKED. These are **engineering test reports**, not measured B0/B1/P outcomes, signed authority, or independent algorithm approval.

**Known stale narrative:** docs/G1_METHOD_DECISION_REGISTER.md still says positive V3 ACCEPT is unavailable in its G3 summary. Correct this *historical descriptive statement* using merged PR #10 evidence. Do not alter the normative DA01 scoring or declare G1 passed.

## 1. Research problem and model alignment

**Research problem:** As software architecture evolves, fitness-control configurations may remain syntactically runnable while their evaluator semantics, architecture scope, stage or required-obligation coverage become stale. The proposed method must make evidence-based, version-bound changes to the **fitness configuration**, not modify application architecture.

The parent SPEC 03 proposes:

- Configuration: Φ_t = <C_t, R_t, α_t, θ_t, H_t, v_t>.
- Knowledge: K_t = (Z_t, Π_t, Γ_t, ν_t).
- Obligation applicability: g_q(K_t) ∈ {ACTIVE, INACTIVE, UNKNOWN}.
- Method-side pair validity: V_P(r, q, A, E) ∈ {VALID, INVALID, UNKNOWN}.
- Typed impact via changed facts/policies/obligations, conservative typed-graph reachability, uncovered mandatory obligations and unresolved trace links.
- Justified operation O ∈ {RETAIN, ADD, REPLACE, DEACTIVATE, ADJUST}; governance D ∈ {ACCEPT, REJECT, HOLD}; invalid or tampered method input yields INPUT_REJECTED.

Definitions: C = persistent criterion intent; q = concrete normative architectural obligation; R = stage-specific evaluator/metric/target/evidence representation; α = optional weights; θ = soft threshold rules; H = hard mandatory constraints; v = configuration version/provenance; Z = architectural facts; Π = versioned policies; Γ = bounded evidence/completeness; ν = source versions. A valid evaluator exit does not prove normative applicability, architectural compliance, semantic validity, mandatory coverage or governance acceptance.

**Scientific claim remains a hypothesis:** Under a fair comparison with frozen B0 and independently performed human/heuristic B1, a governed and evidence-aware P may improve impact identification and demonstrable obligation coverage while managing adaptation cost. No measured superiority, runtime benefit, cross-stack generalizability or scientific novelty is established by successful synthetic tests. Dynamic α/θ optimization is outside core P v1 and requires a later separate study.

## 2. Deliverables

Create exactly four major review drafts under docs/ and update the existing register. Each new document must begin **DRAFT — NOT INDEPENDENTLY APPROVED**, identify the repository source revision, list source references, distinguish observed contracts from proposals, show unresolved decisions and name **reviewer roles**, not fictional people.

| Deliverable | File | Substantive result | Never claim |
| --- | --- | --- | --- |
| G1P-D01 | docs/G1_METHOD_SPECIFICATION.md | Formal and implementation-grounded independent Method P review | Novelty proved / method frozen |
| G1P-D02 | docs/DA01_PREREGISTRATION_DRAFT.md | Pre-outcome RQ1/RQ2 experiment plan, hypotheses, outcomes, failure treatment | Data collected / H1 accepted |
| G1P-D03 | docs/B1_P_COMPARABILITY_PLAN.md | Comparator fairness, information/time/evaluator parity, blinding and human independence | Real B1 session took place |
| G1P-D04 | docs/G1_REVIEW_CHECKLIST.md | Independent reviewer work package and gate audit/evidence index | G1 approved / G4 authorized |
| G1P-D05 | Existing docs/G1_METHOD_DECISION_REGISTER.md | Accurate navigation, full OPEN/M coverage and updated PR #10 engineering evidence | Any independent OPEN decision resolved by the agent |

Follow repository convention: do not add docs/CONTEXT.md absent an existing requirement. Changes should be documents and, if useful, a narrow document-contract test; not P algorithm, prediction, scorer or experimental-protocol edits.

### 2.1 G1P-D01 — Method specification

Provide the following **reviewable** sections with definitions, tables, algorithms and exact source/module references:

1. The software-engineering problem, investigation object, proposed falsifiable methodological contribution and boundary between **engineering implementation**, **method**, and **scientific evidence**.
2. Typed mathematical vocabulary A, ΔA, C, q, R, E, Φ, K, G_T and version/scope/authority dependencies. Separate architecture fact, policy, criterion, obligation, representation and evaluator.
3. Strict preflight: V3 method-input manifest, SPEC 01 authority/integrity/completeness, Snapshot v1.1 vs additive unfrozen v1.2; V1/V2 legacy compatibility; invalid integrity → INPUT_REJECTED, missing trustworthy proof → UNKNOWN/HOLD. Hash consistency does not imply policy approval.
4. SPEC 02 before/after Strong Kleene applicability and policy-only changes; negative evidence requires exact type/state/revision/scope/time completeness. No inference of INACTIVE from absence in an open registry.
5. Typed fact/policy/obligation differences, typed traceability, PROVEN_AFFECTED/POSSIBLY_AFFECTED/NOT_AFFECTED_WITH_PROOF/UNRESOLVED and how missing graph edges behave.
6. Exact (representation, obligation) validity; evaluator artifact, target resolution, stage/context, nonvacuity, evidence adequacy and independent reference verdict distinct from method-side assessment; compliance-violation vs monitor-validity remains OPEN-07.
7. Mandatory obligations and full coverage rule; unknown applicability or stage contract is not silently dropped. A later lifecycle-stage registry is unapproved and must **not change frozen DA01 RQ2**.
8. RETAIN/ADD/REPLACE/DEACTIVATE/authorized bounded ADJUST preconditions; retained controls need valid proof when impacted; no invented executable template. Cost hierarchy and bounded deterministic search, multi-obligation ADD ambiguity OPEN-08.
9. Candidate construction and parent/config/artifact hashes; 12 mandatory invariants INV-01…INV-12 with their exact meaning; ACCEPT/REJECT/HOLD decision precedence, traceability, conditional rollback and production publishing disabled without atomic CAS.
10. Algorithm pseudocode consistent with current p_adaptation.py, p_impact.py, p_semantic.py, p_operations.py, p_candidate.py, p_governance.py; assumptions, failure scenarios, test mappings, scientific falsifiability, research limitations.
11. An explicit **IMPLEMENTED_DEVELOPMENT vs PROPOSED vs NEEDS_INDEPENDENT_AUTHORITY vs DEFERRED** status for each mechanism. Do not upgrade an algorithm to approved status because it compiles.

### 2.2 G1P-D02 — DA01 preregistration draft

Keep executable DA01 RQ1/RQ2 distinct from broader **manuscript RQ1–RQ4**. The manuscript and executable design use different meanings for RQ3/RQ4 (M-02). Display the two schemes in separate columns; never silently rename either scheme.

**Current executable DA01 scope:**

- **RQ1:** precision, recall, F1 for affected typed targets (target_type,target_id), plus operation-selection accuracy; frozen score conventions TP, FP_in, FP_extra, FN, TN and FP_total=FP_in+FP_extra. For positive oracle set with no positive predictions use zero; if both positive sets are empty use null for precision/recall/F1 and report correct-empty-set separately. An unknown target can yield FP_extra and PROTOCOL_VIOLATION. Do **not** reveal private target universe or answers to any method.
- **RQ2:** Coverage_before of frozen A0 and Coverage_after of candidate, both against the **same post-change architecture** and full **private required-obligation denominator**. Coverage needs a valid representation execution verdict AND a versioned independently evaluated, adequate exact-pair (representation_id,obligation_id) evidence verdict; duplicate controls never multiply coverage. Unknown/missing pair is not covered. Do **not** copy private denominator or expected pairs into method inputs.
- **B0:** frozen A0 unchanged, empty explicit operation list; original evaluator can be stale or vacuous and must be independently evaluated.
- **B1:** actual independent human with predeclared procedure, time budget, permitted inputs, experience/exposure and a sealed candidate, not an agent-generated imitation.
- **P:** independently frozen general governed method with declared P-only traceability advantage, separate from oracle/scorer and other methods' outputs.

**Hypothesis/estimand work (all UNAPPROVED):** define H0/H1 separately for each proposed primary endpoint and B0–P/B1–P contrast, beneficial direction, estimand, numerator/denominator, handling of missing/abstentions/protocol failures, primary-versus-secondary outcomes, effect-size scale, inference procedure, planned uncertainty intervals, multiple-comparison strategy and allowable overhead. Where the protocol does not determine a numeric threshold, sample size, statistical test, equivalence margin, overhead ceiling or effect benchmark, explicitly write **TBD_PRE_REGISTRATION / PENDING_INDEPENDENT_REVIEW**, not an invented value.

**No pseudoreplication:** one independently designed architecture transition is an experimental unit. DA01 is only **one transition**, so report it descriptively. Individual obligations, evaluator invocations, requests, repetitions and time samples are **not independent architecture trials**. Design future statistical comparison across separately constructed architecture transitions under a separately approved plan; do not produce a p-value or declare significance for DA01 alone.

**Failure/abstention outcomes:** make one explicit classification table: INPUT_REJECTED, HOLD, candidate REJECT, UNKNOWN applicability, missing pair, vacuous success, monitoring/architecture violation, evaluator execution failure, infrastructure failure, protocol violation, reference-checker error and scoring failure. Preserve frozen score semantics and separate run invalidity from missing architectural coverage. Unknown treatment not documented by normative sources must remain a reviewer decision.

**Data custodianship:** describe clean pre-outcome preregistration, independent reviewer/holdout custody, sealed predictions before oracle scoring, permitted method input allowlists, logging/provenance, no author access to expected answers. Do not execute DA01, generate seal or inspect scorer/ground-truth source.

### 2.3 G1P-D03 — B1/P comparability plan

Provide an explicit B0/B1/P matrix for source revisions, common snapshot bytes, policies/conditions, obligation catalog, evaluator capabilities, traceability graph, budget, evidence, timing, allowed tools, permitted knowledge, target SHA, input hashes and sealing.

**Fairness constraints:** B1/P get the same verified common normative and architecture information and the capabilities needed to propose real checks, unless a documented and independently approved experimental difference exists. P-only traceability is a separately reviewable methodological treatment, not a hidden policy advantage. Equal evaluator artifact availability must be demonstrable; TEST_ONLY code does not count as an approved real evaluator.

**OPEN-01:** manuscript calls B1 periodic while the current human checklist is post-change. Present both alternatives, the different causal estimands, and a decision template for cadence, time budget and prior exposure; do **not** choose without review.

**Real human B1:** independence and prior-exposure questionnaire/record template with placeholders only; B1_CHECKLIST inputs, environment, start/end timestamps, operation/evidence decisions, adaptation time, competence and protocol deviations. No fake participant or prefilled session output.

**Trust/blockers:** record OPEN-04 real policy/closure trust anchors, OPEN-05 permitted verified evaluator inventory, OPEN-06 measured/prespecified search budget and cost; if absent real P remains HOLD/NOT_READY. No use of reference checker, private oracle, .git, network or another method output in measured method execution.

**Stop/review:** mismatched inputs, unsourced semantic proof, B1 operator unavailable, stale revision, unequal capabilities, unapproved temporal budget, missing evaluator/checker or untrusted closure mean STOP/NEEDS_APPROVAL, never an improvised compliant comparator.

### 2.4 G1P-D04 — independent reviewer checklist

Build an auditable gate matrix and evidence index with fields: requirement, source document/commit, evidence kind, limitations, reviewer role, pending action, decision/status and independent approval reference (blank until authentic).

Review lanes:

- Scientific construct and executable algorithm model, INV-01…INV-12, uncertain proof, OPEN-07/08.
- RQ crosswalk, hypotheses, B1 design, denominators, missing data and statistical units, OPEN-01/02/M-01/02/06.
- Normative policy, independent authority, evaluator templates and cost evidence, OPEN-04/05/06.
- Actual method-input isolation, protected oracle, independent B1/operator, held-out data custody, algorithm freeze, OPEN-09.
- Lifecycle-stage scope, optional future α/θ, OPEN-03/10; note DA01 cannot prove end-to-end cloud runtime control or weight adaptation.
- TT-P03-43 independent frozen-output byte-parity **BLOCKED** until separately authorized; historical G0/G2/G3 evidence and selected measured environment re-verification.
- G1 requires genuinely **independent approval/freeze**. G4 requires **separate explicit human authorization** after appropriate prerequisites. Neither CI nor filled forms automatically advance a gate.

Use status values NOT_REVIEWED, EVIDENCE_INCOMPLETE, PENDING_INDEPENDENT_REVIEW, PENDING_EXTERNAL_AUTHORITY, PROPOSED, DEFERRED_WITH_LIMITATION as appropriate. If describing a possible APPROVED status, make it a **future template state only**; do not populate it with fake reviewers, signatures, dates, keys or approvals.

**Required explicit output:** PACKET_READY_FOR_REVIEW (if documentary requirements pass), never G1_PASS or P_READY.

### 2.5 G1P-D05 — existing decision register maintenance

Preserve OPEN-01…OPEN-10 and M-01…M-06 with their original meaning. Add links to the four documents, a clear source/proposal/independent-approval status legend and current baseline commit.

Correct stale **descriptive** references saying no synthetic V3 ACCEPT path: merged PR #10 tests for no-op and ADD demonstrated TEST_ONLY ACCEPT with separate before/after closure claims. Distinguish this from DA01 Phase A gate statuses, which remain unchanged unless independently approved. Do not rewrite historical assertions into false claims of experimental readiness. Keep OPEN-10 explicitly deferred from core α/θ study.

## 3. Decision docket: every open issue must be carried through

| Decision | Research consequence | Document that must explicitly address it | Review disposition |
| --- | --- | --- | --- |
| OPEN-01 / M-01 | Periodic vs post-change B1 is a different intervention | B1 comparability, preregistration | PENDING_INDEPENDENT_REVIEW |
| OPEN-02 / M-02/M-06 | RQ identity, primary endpoints, hypotheses and inference | Preregistration | PENDING_INDEPENDENT_REVIEW |
| OPEN-03 / M-04 | Multi-stage mandatory stage claims differ from frozen DA01 denominator | Method, reviewer checklist | PROPOSED/DEFERRED, not retrofitted |
| OPEN-04 | Real authority Charter/Registry/completeness keys and custody absent | Comparability, checklist | PENDING_EXTERNAL_AUTHORITY |
| OPEN-05 / M-03 | Verified real evaluator artifacts, fair B1/P capability access | Comparability, checklist | PENDING_EXTERNAL_AUTHORITY |
| OPEN-06 | Legitimate cost units and bounded search limit | Method, preregistration | PENDING_INDEPENDENT_REVIEW |
| OPEN-07 | Noncompliance versus monitor invalidity / frozen verdict mismatch | Method, preregistration | PENDING_INDEPENDENT_REVIEW |
| OPEN-08 | One multi-obligation ADD versus frozen single-target operation identity | Method, preregistration | PENDING_INDEPENDENT_REVIEW |
| OPEN-09 | Independent algorithm review, holdout, version/seal custody | Checklist, preregistration | PENDING_INDEPENDENT_REVIEW |
| OPEN-10 / M-05 | α/θ adaptation separately tested, not a core result | Method, checklist | DEFERRED_FUTURE_RESEARCH |

Decision preparation order: (01/02) RQ/comparator → (03/07/08) method and frozen-score boundary → (04/05/06) real trust/artifact/cost availability → (09) independent review and freeze → **separately** G4. This is a review agenda, not a set of approvals.

## 4. Documentation verification matrix

All rows are PLANNED until backed by actual PR tests/review artifacts. A document passing a linter proves only that a document is structurally present.

| ID | Requirement and evidence |
| --- | --- |
| G1P-01 | All four new documents exist, identify their status, baseline and approval boundary, and link relevant canonical sources |
| G1P-02 | Method formal entities, Φ and K, implemented-versus-proposed crosswalk are accurate, technology-agnostic and do not claim α/θ optimization |
| G1P-03 | All twelve INV-01…INV-12 and governance INPUT_REJECTED/REJECT/HOLD/ACCEPT are accurately and separately specified |
| G1P-04 | Manuscript/executable RQ crosswalk preserves RQ3/RQ4 mismatches, and DA01 scope remains only RQ1/RQ2 |
| G1P-05 | Frozen RQ1 typed F1/operation conventions and RQ2 exact-pair coverage correctly reproduced from safe protocol descriptions |
| G1P-06 | B0/B1/P input, capability, time, prior-exposure, independence and oracle blinding comparisons explicit |
| G1P-07 | UNKNOWN/HOLD/invalid/vacuous/missing/ref-checker error handling separated without invented denominator treatment |
| G1P-08 | DA01 has one independent architecture transition, no invalid target-level statistics and no invented effect thresholds |
| G1P-09 | OPEN-01…OPEN-10 and M-01…M-06 all represented, linked and remain pending/deferred |
| G1P-10 | Authentic policy, evaluator, cost and TT-P03-43 blockers distinguished from TEST_ONLY code regressions |
| G1P-11 | G0…G4 review conditions, P NOT_READY and separate G4 human approval documented; no fake sign-off |
| G1P-12 | Evidence source/version index contains no secret key, protected oracle data, raw scorer output or answer-specific reference |
| G1P-13 | Historical stale G1 register reference to no positive V3 ACCEPT corrected with PR #10 engineering evidence |
| G1P-14 | All new local Markdown links and named implementation paths checked against tracked files |
| G1P-15 | Changed-file audit confirms no frozen A0/DA01 contracts, protected modules, private oracle/scorer, source tags or actual measured results modified |
| G1P-16 | Final PR report includes requirement-to-test map, exact commands/results, base/head SHAs and SOURCE / PROPOSED / UNKNOWN attribution for claims |

**Testing discipline:** minimal read-only document-contract tests are permissible (for example tests/unit/test_g1_review_package.py, plus nearest CONTEXT.md when required). Use make development-quality when feasible; do not run broad make quality if it executes protected modules. Record all tests as PASS/FAIL/SKIP/BLOCKED from actual output. Do not equate documentary completeness with G1 protocol approval.

## 5. Hard research-integrity boundaries

DO NOT:

- Read DA01 ground truth, oracle, scorer code/output, scenario-specific expected targets/operations, another method's outputs or protected test modules.
- Edit frozen A0/DA01 source, seeds, workloads, score and validity contracts, experiment PROTOCOL/READINESS to force permission, sealed outputs, historic tags or V1/V2 legacy meaning.
- Run measured DA01 B0/B1/P, generate method predictions for scoring, fake a B1 participant, forge provenance/authority/reviewer approvals or claim empirical superiority.
- Use developmental signed TEST_ONLY evidence as real production policy/evaluator/cost approval.
- Modify Method P algorithm, runtime adapters, the frozen scorer or construct a new α/θ optimization method in this documentary PR.
- Change P interface readiness or automatically advance G1/G4 gates.
- Create a p-value, confidence bound, sample size or statistical significance result from one architecture transition.

For every unavailable normative choice write PENDING_INDEPENDENT_REVIEW, PENDING_EXTERNAL_AUTHORITY, TBD_PRE_REGISTRATION or DEFERRED_WITH_LIMITATION, with its consequence. Never silently fill gaps using arbitrary engineering assumptions.

## 6. Execution phases

**G1P-A — Baseline/source audit.** Verify HEAD and PR #10 merged, inspect safe sources, prepare discrepancy inventory and source→claim table. Flag misleading historical summaries without changing normative frozen sources.

**G1P-B — Formal method.** Write G1_METHOD_SPECIFICATION.md with model/algorithm/invariants/versions, crosswalk to real code and exact unresolved scientific decisions.

**G1P-C — Experimental design.** Write DA01_PREREGISTRATION_DRAFT.md and B1_P_COMPARABILITY_PLAN.md: fixed existing scoring semantics, candidate endpoints/estimands, independent-unit limitations and fairness constraints.

**G1P-D — Independent review package.** Write G1_REVIEW_CHECKLIST.md and update existing G1_METHOD_DECISION_REGISTER.md descriptively, not normatively.

**G1P-E — Validation and review.** Verify all four documents, links, OPEN/M references and protected-path diff. Run only safe checks. Report G1P-01…16 statuses and blockers. Open a **draft pull request** to main after the user-provided specification branch is ready; do not merge automatically.

Suggested changes: documents in docs/, optionally narrow non-oracle documentation tests under tests/unit/ and corresponding local CONTEXT.md update. Do not implement new experiment infrastructure or algorithmic behavior.

## 7. Final agent report requirements

Include base/head SHAs; changed files; four output documents; G1P-01…16 statuses, evidence and commands; OPEN-01…OPEN-10 plus M-01…M-06 crosswalk; source-derived facts versus proposed decisions versus unavailable external proof; B0/B1/P fairness and RQ1/RQ2 estimands; independent reviewer requests; limitations and gate status; protected-path and private-data boundary audit; exact CI URL/results.

**Success means the methodological packet is independently reviewable**, not frozen, signed, approved or measured.

## 8. Exit criteria and human handoff

**Ready for document review:** all deliverables exist and consistently cite actual current sources, the G1 decision register is up to date, all decisions/assumptions and external dependencies are explicit, and reported safe validation passes or honest blockers are documented.

**Still NOT done:** independent algorithm/method freeze, human B1, actual approved policy and evaluator authority, TT-P03-43 authorized independent byte parity, selected measured environment audit, G1 sign-off, G4 authorization and experimental DA01 outcomes.

**Next human step:** review OPEN-01…OPEN-09 with responsible independent reviewers; defer OPEN-10 with a scope limitation; obtain authentic policy/evaluator/cost proof, independent B1 and holdout custody; authorize measured DA01 only through a separate G4 decision after G1 and other gates.
