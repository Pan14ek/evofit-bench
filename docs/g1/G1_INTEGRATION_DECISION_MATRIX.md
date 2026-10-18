# G1 integration decision matrix — Method P and DA01

**DRAFT — FOR INDEPENDENT REVIEW; NOT A G1 DECISION**

**Integration source baseline:** main commit **ca8d9781401f74297d7d47f68aa978557ca58e98**, containing the merged workstreams in PRs #12–#15. The four briefs retain their own historical review baselines and are unchanged by this integration.

**Current gate status:** G1 **INCOMPLETE**; G4 **NOT AUTHORIZED**; measured interface **P_ALGORITHM_STATUS = NOT_READY**; TT-P03-43 **BLOCKED**. This document proposes dispositions and organizes evidence. It does not approve a method, protocol, authority, evaluator, reviewer, or experiment.

## 1. Scientific objective and integration scope

The dissertation asks how meaningful, evidence-supported architectural control can be preserved as software evolves. The research object is the versioned fitness-control configuration and its normative applicability, architectural representations, semantic adequacy, evidence, and governed adaptation—not simply a set of tests or an automated evaluator.

Method P proposes one linked procedure:

    architecture and policy evolution
      → obligation applicability
      → conservative impact analysis
      → exact representation–obligation validation
      → evidence-supported operation selection
      → candidate construction and governance
      → versioned decision and monitored continuity

The contribution remains a falsifiable proposal: under independently reviewed definitions and a fair preregistered comparison, frozen P may improve specified architectural-control outcomes against unchanged B0 and a genuinely independent human B1 while meeting separately approved cost constraints. No improvement, novelty, generality, or operational benefit is established by implementation or synthetic tests.

DA01 is one architecture transition. It supports a descriptive case demonstration under its frozen executable RQ1/RQ2 contracts; it does not support population-level inference, a periodic-human-review claim, or a measured B0/B1/P result. The manuscript and executable experiment use different RQ label mappings; both are preserved in [RESEARCH_CONTEXT.md](../RESEARCH_CONTEXT.md).

The experimental architecture baseline remains frozen **A0_MONOLITH**. The current post-DA01 application code is organized as **A0_1_CAPABILITY_MODULES**, still one deployable process and one PostgreSQL database with synchronous calls and no broker. These architecture facts delimit the benchmark; they are not claims that P has evolved the application architecture.

This package consolidates the four merged reviews into one decision record. It does not treat the briefs as independent scientific findings, rewrite their recommendations into approvals, change frozen DA01 contracts, inspect answer-specific material, perform TT-P03-43, or authorize measurement.

## 2. Source and evidence map

### Workstream crosswalk

| Workstream / source | Merged PR and commit at baseline | Assigned decisions | Integrated finding |
| --- | --- | --- | --- |
| WT-01 [Research Design brief](workstreams/01_RESEARCH_DESIGN_BRIEF.md) | [PR #12](https://github.com/Pan14ek/evofit-bench/pull/12), a8b922549a187f809e8ec849ff7cdd28e970458c | OPEN-01, OPEN-02; M-01, M-02, M-06 | Makes post-change B1 a candidate aligned to the existing transition-triggered checklist, while preserving periodic review as a different future treatment. Keeps RQ1 impact/operation identification and RQ2 valid coverage as candidate endpoints; DA01 remains descriptive. |
| WT-02 [Formal Method & Scoring Compatibility brief](workstreams/02_METHOD_COMPATIBILITY_BRIEF.md) | [PR #14](https://github.com/Pan14ek/evofit-bench/pull/14), ca8d9781401f74297d7d47f68aa978557ca58e98 | OPEN-03, OPEN-07, OPEN-08; M-04 | Recommends a future all-required-stage formulation without changing DA01's at-least-one exact-pair rule. Surfaces the nonzero-exit validity mismatch and single-target ADD representation issue as compatibility decisions. |
| WT-03 [Authority, Evaluator Capability & Cost brief](workstreams/03_AUTHORITY_CAPABILITY_COST_BRIEF.md) | [PR #15](https://github.com/Pan14ek/evofit-bench/pull/15), 92be354420e0f8ee9f6fc51275a000e59cbe9413 | OPEN-04, OPEN-05, OPEN-06; M-03 | Separates five trust claims, identifies the absence of production authority and approved generic evaluators, compares fairness models, and proposes multidimensional cost reporting without numeric thresholds. |
| WT-04 [Holdout and Isolation Review brief](workstreams/04_HOLDOUT_ISOLATION_REVIEW_BRIEF.md) | [PR #13](https://github.com/Pan14ek/evofit-bench/pull/13), b1fdd2c0797ac7013d2329639294962c9c938dc7 | OPEN-09, G2, TT-P03-43 | Proposes independent freeze, custody, sealing, and role separation. Reports no actual custodian/reviewer, selected measured-environment audit, prediction seal, or independent frozen-output byte-parity record. |

### Normative and implementation sources

| Evidence class | Sources | What they establish and do not establish |
| --- | --- | --- |
| Frozen DA01 protocol | [PROTOCOL.md](../../experiments/execution/da01/PROTOCOL.md), [SCORE_RULES.md](../../experiments/execution/da01/SCORE_RULES.md), [VALIDITY_RULES.md](../../experiments/execution/da01/VALIDITY_RULES.md), [INPUT_ISOLATION.md](../../experiments/execution/da01/INPUT_ISOLATION.md), [B1_CHECKLIST.md](../../experiments/execution/da01/B1_CHECKLIST.md) | Governs the existing DA01 operation identity, full denominator, exact-pair coverage, evaluator validity, allowed inputs, and transition-triggered checklist. This documentation package does not amend them. |
| Readiness and status | [READINESS.md](../../experiments/execution/da01/READINESS.md), [P_ALGORITHM_STATUS.md](../../experiments/execution/da01/P_ALGORITHM_STATUS.md), **p_interface.py** | Recorded G1/G2/G3/G4 limits and measured interface NOT_READY. Synthetic engineering evidence does not advance a scientific gate. |
| DEVELOPMENT implementation | [p_adaptation.py](../../experiments/execution/tooling/p_adaptation.py), [p_impact.py](../../experiments/execution/tooling/p_impact.py), [p_semantic.py](../../experiments/execution/tooling/p_semantic.py), [p_operations.py](../../experiments/execution/tooling/p_operations.py), [p_candidate.py](../../experiments/execution/tooling/p_candidate.py), [p_governance.py](../../experiments/execution/tooling/p_governance.py) | A synthetic DEVELOPMENT pipeline implements typed changes, applicability, exact-pair assessment, planning, candidates, governance, and rollback safeguards. Code behavior is not independent proof, production authorization, or measured evidence. |
| Engineering traceability | [SPEC_03_IMPLEMENTATION_TRACEABILITY.md](../SPEC_03_IMPLEMENTATION_TRACEABILITY.md), [SPEC_03_IMPACT_ANALYSIS_AND_GOVERNED_ADAPTATION.md](../SPEC_03_IMPACT_ANALYSIS_AND_GOVERNED_ADAPTATION.md) | Historical safe synthetic regression and invariant mapping. The latest recorded summary is 59 traceability rows PASS and TT-P03-43 BLOCKED; this integration does not rerun tests or verify the protected byte comparison. |
| Research framing and docket | [RESEARCH_CONTEXT.md](../RESEARCH_CONTEXT.md), [G1_METHOD_SPECIFICATION.md](../G1_METHOD_SPECIFICATION.md), [G1_METHOD_DECISION_REGISTER.md](../G1_METHOD_DECISION_REGISTER.md), [G1_REVIEW_CHECKLIST.md](../G1_REVIEW_CHECKLIST.md), [DA01_PREREGISTRATION_DRAFT.md](../DA01_PREREGISTRATION_DRAFT.md), [B1_P_COMPARABILITY_PLAN.md](../B1_P_COMPARABILITY_PLAN.md) | Proposals and current open statuses; none is an independent approval or authorization. |

The policy pilot is DRAFT/OPEN and TEST_ONLY; it supplies no production trust anchor or approved authority. The frozen A0 Import Linter is a historical B0 artifact, not an approved generic evaluator. Locust, Prometheus, and pytest entries are catalog declarations, not authority-approved capabilities. The test traceability report does not independently verify frozen-output parity; TT-P03-43 remains BLOCKED.

### Claim labels used below

- **SOURCE**: versioned contract, implementation behavior, or recorded engineering evidence within its stated scope.
- **PROPOSED**: candidate method or study decision for independent review; not binding.
- **UNKNOWN**: evidence is absent, unresolved, or insufficient.
- **EXTERNAL AUTHORITY**: a real independent authority, trust anchor, approval, custody action, or artifact is required.
- **INDEPENDENT REVIEW**: a methodological or formal decision has not been made by this document.

## 3. Integrated Method P model

### 3.1 Typed objects and notation

Use distinct symbols for the fitness aggregate and architecture facts:

    A_t       architecture state at revision t
    Z_t       typed architecture facts and observations
    Π_t       versioned normative policy source
    Q         architectural-obligation catalog
    C_t       stable fitness criterion intents and hard constraints
    ℛ_t       the complete set of fitness representations in configuration Φ_t
    F_fit     optional aggregate fitness function/value; not an architecture-fact inventory
    E         evaluator and telemetry evidence, with provenance and scope
    Γ_t       evidence and completeness claims
    ν_t       source, revision, scope, version, and provenance bindings

    Φ_t = ⟨C_t, ℛ_t, α_t, θ_t, H_t, v_t⟩
    K_t = ⟨Z_t, Π_t, Γ_t, ν_t⟩

Here α denotes optional weights, θ optional soft thresholds, H approved hard invariants, and v configuration/provenance identity. Dynamic α/θ adaptation is outside core P v1 and remains OPEN-10 / M-05 deferred. An aggregate fitness value cannot substitute for an obligation-specific proof.

For each obligation q:

    g_q(K_t) ∈ {ACTIVE, INACTIVE, UNKNOWN}             applicability
    c_q(A_t) ∈ {COMPLIANT, NON_COMPLIANT, UNKNOWN}      architecture compliance
    X(r, A_t, E) ∈ {VALID, INVALID, UNKNOWN}           evaluator execution validity
    V_P(r, q, A_t, E_q) ∈ {VALID, INVALID, UNKNOWN}     method-side exact-pair validity
    D ∈ {ACCEPT, REJECT, HOLD}                         candidate governance

Applicability asks whether authorized normative policy requires q. Compliance asks whether the architecture meets q. Execution validity asks whether the evaluator ran in the right non-vacuous scope. Pair validity asks whether a representation provides adequate semantic and evidence support for one exact (r,q) pair. Coverage asks whether the frozen or reviewed coverage predicate is met. Governance asks whether a candidate may be accepted. These are separate judgments; UNKNOWN is not FALSE or approval.

### 3.2 Typed change and conservative impact

The conceptual change domain is a typed product/sum over separate sources:

    Δ_Z = Diff(Z_t, Z_(t+1))                 architecture-fact changes
    Δ_Π = Diff(Π_t, Π_(t+1))                 policy changes
    Δ_g = Diff(g(K_t), g(K_(t+1)))           applicability-state changes
    Δ   = Δ_Z ⊎ Δ_Π ⊎ Δ_g

The notation Δ_g is a model-level label, not a claim that the implementation defines a standalone ChangeObligation algebra or a separate serialized change type. In source, **diff_snapshot()** emits fact and policy **ChangeRecord** values; **run_adaptation()** appends applicability changes returned by **_diff_applicability()**, also as ordinary **ChangeRecord** values (entity kind obligation, before/after status in version fields), before calling **analyze_impact()**. The orchestration boundary therefore includes all three change sources.

Let **G_T** be the typed trace graph, **S⁺/S?** verified/uncertain seeds, and **P⁺/P?** verified/possible graph paths. Let **π_ℛ** project graph nodes to the declared representation universe. Define:

    𝓡⁺ₜ = π_𝓡(P⁺)       proven affected representation subset
    𝓡?ₜ = π_𝓡(P?)       possibly affected representation subset
    Uₜ₊₁ = currently mandatory, ACTIVE obligations not demonstrated covered
    L?ₜ = unresolved links, mappings, provenance/context, or inventory diagnostics

Then impact is a product of distinct result domains:

    Iₜ = ⟨Impact_𝓡(𝓡⁺ₜ, 𝓡?ₜ), Uₜ₊₁, L?ₜ⟩

Here **Impact_𝓡** is the pair of affected representation subsets (proven and possible); **Uₜ₊₁** is the set of uncovered mandatory, ACTIVE obligations; and **L?ₜ** is the set of unresolved trace-link, mapping, provenance/context, or inventory diagnostics. The full configuration representation set **𝓡ₜ** is not the same as either impacted subset. Incomplete or unresolved traceability cannot prove no impact; missing edges remain uncertain. Uncovered obligations are derived separately from exact-pair coverage and applicability, not inferred solely from graph reachability. This definition matches [G1_METHOD_SPECIFICATION.md §5](../G1_METHOD_SPECIFICATION.md#5-typed-differences-and-conservative-impact).

### 3.3 Coverage predicates and implementation boundary

Distinguish **Coverage_P**, P's own reported coverage assessment based on its internal pair/execution judgments and declared inputs, from **Coverage_ref**, the result determined by an independent experimental reference/evidence path. Coverage_P is a method output/diagnostic: a P-side `VALID` judgment cannot independently verify itself or be presented as reference evidence. The frozen DA01 score predicate uses valid evaluator-execution evidence and a valid, cited exact-pair record for (r,q) at the target architecture revision, once per obligation over the complete private required-obligation denominator. The pair record is a Phase A contract, not a trusted reference-run attestation; independent evaluator/evidence verification remains a deferred G4 requirement. Therefore Coverage_ref requires independent verification of execution and pair evidence under the frozen DA01 validity/scoring rules; P's verdict or scorer output alone is not independent proof. P does not receive the private denominator or reference verdicts, and multiple obligations require separate pair proofs. No authorized Coverage_ref result currently exists.

For a later lifecycle-wide protocol only, a candidate generalization is an approved, verified, nonempty required-stage registry S(q,A) and:

    Covered_all(q) = 1 iff for every s in S(q,A),
      there exists active r with stage(r)=s, q in covers(r),
      valid execution X(r,A,E), and exact-pair V_P(r,q,A,E_q)=VALID.

Unknown or unverified stage membership, or an absent/empty registry, yields UNKNOWN rather than vacuous success. Obligation-level coverage counts q once when every required stage is covered. Stage-pair coverage reports each (q,s) cell and therefore has a different denominator/weighting. Neither form retrofits a multi-stage requirement into DA01.

### 3.4 Method sequence and source status

1. Verify the allowlisted, revision-bound inputs; malformed integrity/schema/binding is INPUT_REJECTED, while missing authority/completeness remains UNKNOWN/HOLD.
2. Evaluate policy-backed applicability before and after for the catalog obligations.
3. Build typed fact, policy, and applicability changes; retain uncertainty and provenance.
4. Traverse the typed trace graph conservatively and retain proven impact, possible impact, uncovered obligations, and unresolved diagnostics separately.
5. Assess exact representation–obligation pairs and mandatory coverage against adequate evidence.
6. Select only justified retain/replace/add/deactivate/adjust operations using materializable authorized artifacts and a bounded cost model.
7. Materialize and validate a parent-bound candidate; govern as ACCEPT, REJECT, or HOLD; expose the exact compatibility projection only under its defined accepted state. Publication is disabled; rollback requires fresh current-context validation.

The merged implementation provides these mechanisms in DEVELOPMENT and synthetic TEST_ONLY flows. Production authority/evaluator evidence, independent method freeze, selected-environment isolation audit, measured comparisons, and scientific validation remain absent or blocked. See the source/status crosswalk in [G1_METHOD_SPECIFICATION.md](../G1_METHOD_SPECIFICATION.md); this sequence is a synthesis, not a claim that each link is scientifically validated.

## 4. OPEN-01…OPEN-09 decision matrix

The readiness labels in this section are analytical labels for this integration only. They do not replace the canonical status register.

### OPEN-01 — B1 cadence, time, and exposure

- **Problem / source:** WT-01; M-01. The manuscript describes periodic heuristic review; DA01's [B1 checklist](../../experiments/execution/da01/B1_CHECKLIST.md) is transition-triggered. These are different interventions.
- **Contract and alternatives:** Current DA01-compatible candidate: independent human B1 after the declared change. Alternative: periodic review, which requires a separately designed cadence, observation window, and comparator protocol. They cannot be treated as the same arm.
- **PROPOSED disposition:** For a DA01-only comparison, ask the independent reviewer whether to define B1 as post-change, explicitly limiting the claim to that intervention. Preserve periodic review for a future multi-arm study if the dissertation claim requires it. Do not call either choice approved here.
- **Scientific consequence / DA01 compatibility:** Post-change is aligned to the current checklist but does not test periodic review. Cadence, time budget, prior exposure, and evidence cutoff change the estimand. DA01 contract compatibility is plausible only after a reviewed protocol fixes these details; no human session exists.
- **Required evidence / dependencies:** Preregistered B1 procedure, common-input and capability inventory, operator independence/exposure record, fixed time budget and stop/deviation rules; depends on OPEN-05 fairness and OPEN-02 estimand.
- **Reviewer / status / readiness:** Independent experimental-methods and human-comparator reviewers. Canonical status **PENDING_INDEPENDENT_REVIEW**. **READY_FOR_INDEPENDENT_DECISION** on the cadence choice, conditional on OPEN-05 and OPEN-02 boundaries.

### OPEN-02 — RQ crosswalk, endpoints, estimands, and statistical claims

- **Problem / source:** WT-01; M-02 and M-06. Manuscript RQ1–RQ4 and executable RQ1–RQ4 differ; executable DA01 evaluates RQ1 affected-target/operation identification and RQ2 exact-pair mandatory coverage.
- **Contract and alternatives:** Preserve both label systems and their crosswalk. Candidate endpoint families are affected-target F1, normalized operation accuracy, verified coverage, plus diagnostics/failure states. Alternatives: F1 and coverage co-primary candidates, or an independently selected hierarchical endpoint with multiplicity rules; operation accuracy may be secondary/exploratory.
- **PROPOSED disposition:** Retain F1 and coverage as co-primary *candidates* for independent review because they represent different constructs; require a statistician/research-methods reviewer to select a hierarchy or co-primary plan before any measurement. Keep operation accuracy and validity/failure diagnostics visible, with final inferential role undecided.
- **Scientific consequence / DA01 compatibility:** The executable outcomes support only parts of the broader manuscript claims. DA01 has one transition and is descriptive; it cannot establish significance or generalizable superiority. No margin, sample size, power, p-value plan, interval, or multiplicity rule is invented.
- **Required evidence / dependencies:** Approved operational definitions, comparator estimands, missingness/abstention handling, denominators, independent unit and future multi-transition plan. Depends on OPEN-01, OPEN-05, OPEN-06, OPEN-07, OPEN-08.
- **Reviewer / status / readiness:** Independent statistician and experimental-methods reviewer. **PENDING_INDEPENDENT_REVIEW**. **NEEDS_ADDITIONAL_METHOD_ANALYSIS**.

### OPEN-03 — lifecycle-stage coverage

- **Problem / source:** WT-02; M-04. Future fitness controls may span CI/test, deployment, and runtime; DA01 has no frozen general required-stage registry.
- **Contract and alternatives:** Preserve DA01's current at-least-one valid exact-pair rule. For a later protocol, compare an all-required-stage obligation predicate to stage-pair reporting; the former counts each obligation once only after every registered stage is covered, while the latter reports individual (q,s) pairs.
- **PROPOSED disposition:** Consider all-required-stage coverage only in a separately versioned future study with an independently authorized, verified, nonempty stage registry and per-stage execution plus exact-pair proof. Missing/unknown stage membership returns UNKNOWN; no vacuous coverage.
- **Scientific consequence / DA01 compatibility:** Changes the construct and denominator interpretation in future studies; incompatible with silently modifying DA01. No current DA01 requirement is changed.
- **Required evidence / dependencies:** Formal stage-registry contract, stage-specific evaluator capability and proof rules, synthetic negative cases for missing/unknown stages, prospective protocol review. Depends on OPEN-04/05 authority and OPEN-02 endpoint plan.
- **Reviewer / status / readiness:** Formal-methods, lifecycle-architecture, and experimental-methods reviewers. **PENDING_INDEPENDENT_REVIEW**. **DEFERRED_FUTURE_RESEARCH**.

### OPEN-04 — production policy authority and completeness

- **Problem / source:** WT-03. A policy result requires more than matching bytes.
- **Contract and alternatives:** Preserve distinct claims: (1) byte integrity, (2) provenance, (3) authorization, (4) completeness, and (5) semantic correctness. The pilot Registry is OPEN and policy material DRAFT/TEST_ONLY; hash or synthetic verification does not confer production trust. Alternatives are to obtain an actual governed authority/trust chain, or keep measured applicability UNKNOWN/HOLD.
- **PROPOSED disposition:** Do not promote the pilot. For any measured scope, require a real authorized policy/registry source, trusted keys/custody, scope and effective-time authority, independent completeness evidence, and a reviewed semantic interpretation.
- **Scientific consequence / DA01 compatibility:** Without this chain, required-obligation membership/applicability is not established, so a coverage claim cannot be justified. Development synthetic flows remain useful engineering evidence only.
- **Required evidence / dependencies:** Authentic charter/registry and approval records, trust-anchor custody, bounded completeness proof, independent source and semantics review. This is an external prerequisite to OPEN-05 and any positive coverage or ADD authority.
- **Reviewer / status / readiness:** Policy authority, key-custody, completeness, and semantic-policy reviewers. **PENDING_EXTERNAL_AUTHORITY**. **PENDING_EXTERNAL_AUTHORITY**.

### OPEN-05 — real evaluator capabilities and B1/P fairness

- **Problem / source:** WT-03; M-03. Source information parity, executable interpretation parity, and evaluator capability parity are distinct.
- **Contract and alternatives:** Model A shares readable common evidence and evaluator capabilities while allowing treatment-specific processing; P's programmatic applicability and traceability remain disclosed treatment features. Model B requires strict common evaluator execution/output parity. Precomputed evaluation evidence may equalize access but moves evaluation outside the treatment and changes the estimand.
- **PROPOSED disposition:** Have reviewers select a fairness model and estimand explicitly. Inventory real evaluator artifacts, versions, scope, sensitivity/negative fixtures, evidence contract, materialization, and authority. Keep common admissible method evidence separate from independent oracle/reference scoring. Never place oracle labels, expected operations, private checker verdicts, post-seal scores, or another method's confidential output in shared inputs. Do not silently change input contracts.
- **Scientific consequence / DA01 compatibility:** Same catalog bytes do not prove the same executable interpretation. Identical evaluation results can alter whether the experiment measures adaptation with evaluator execution or adaptation given precomputed evidence. Frozen B1/P input allowlists remain controlling.
- **Required evidence / dependencies:** External approval and byte-pinned capability inventory, equal availability/access, explicit treatment statement, environment and cost accounting. Depends on OPEN-04, OPEN-01, OPEN-02, OPEN-06.
- **Reviewer / status / readiness:** Evaluator-domain/authority reviewer plus independent experimental-fairness reviewer. Canonical **PENDING_EXTERNAL_AUTHORITY**; M-03 fairness choice also **PENDING_INDEPENDENT_REVIEW**. **PENDING_EXTERNAL_AUTHORITY**.

### OPEN-06 — cost dimensions and bounded search

- **Problem / source:** WT-03. The DEVELOPMENT planner uses a scalar authorized incremental cost, max search nodes, and per-artifact costs; this is not an approved experimental cost model.
- **Contract and alternatives:** Candidate dimensions include human B1 active time, P compute/adaptation, construction, evaluator execution, candidate validation, resource use, candidate count, and operational burden. Keep unlike units separate; do not convert human minutes to CPU seconds with arbitrary weights. A single preregistered composite is an alternative only with an independently justified conversion.
- **PROPOSED disposition:** Report a vector first and retain source-native units. Separately define a comparable time/resource allowance if the research claim needs one. Report search completion and budget exhaustion separately: exhaustion or unknown cost is not proof of infeasibility, and incomplete bounded search cannot claim global optimality.
- **Scientific consequence / DA01 compatibility:** Budget and stop rules affect fairness and the “benefit subject to cost” claim. The current scalar planner is DEVELOPMENT behavior; no numerical cost threshold or overhead ceiling is approved.
- **Required evidence / dependencies:** Cost provenance, unit definitions, measurement boundaries, search-completion semantics, candidate/tie rules, and independently reviewed acceptance thresholds. Depends on OPEN-01/02/05.
- **Reviewer / status / readiness:** Independent operations-cost and experimental-methods/statistics reviewers. **PENDING_INDEPENDENT_REVIEW**. **NEEDS_ADDITIONAL_METHOD_ANALYSIS**.

### OPEN-07 — nonzero evaluator exit and frozen validity semantics

- **Problem / source:** WT-02; frozen [VALIDITY_RULES.md](../../experiments/execution/da01/VALIDITY_RULES.md) and DEVELOPMENT **p_semantic.py**. P can yield PairStatus VALID with compliance NON_COMPLIANT when a completed, adequate evaluator's only reason is a violation; DA01 validity labels any nonzero evaluator exit EXECUTION_FAILURE.
- **Contract and alternatives:** Scientific distinction: a monitor can execute adequately and detect noncompliance, while the architecture remains noncompliant. Frozen DA01 instead treats nonzero as execution failure for its RQ2 reference validity. Options: (a) obey the frozen rule for DA01 and leave such a case uncovered under its semantics; (b) propose a separate future versioned contract with orthogonal execution/monitor validity and compliance dimensions; (c) revise a future evaluator contract so violation is data rather than process failure, subject to review. Do not combine incompatible interpretations as if both governed the current DA01 score.
- **PROPOSED disposition:** Keep DA01 checker and RQ2 rule unchanged. Mark P-to-DA01 coverage interpretation **blocked** for the nonzero-exit case until an independent method/scoring decision specifies the future contract boundary and any versioned migration. For DA01, the frozen validity rule controls, regardless of P's internal diagnostic.
- **Scientific consequence / DA01 compatibility:** Counting the same event as valid coverage in one layer and execution failure in the frozen reference layer changes the coverage numerator and interpretation of degradation; this is a direct contract compatibility issue, not wording alone.
- **Required evidence / dependencies:** Independent operational definition, versioned schema/checker proposal for any later study, synthetic clean/noncompliant/monitor-failure examples, explicit mapping to RQ2. No scorer or frozen file is changed here.
- **Reviewer / status / readiness:** Independent formal-methods, evaluator-validity, and DA01 scoring-contract reviewers. Canonical **PENDING_INDEPENDENT_REVIEW**. **BLOCKED_BY_CONTRACT_COMPATIBILITY**.

### OPEN-08 — multi-obligation ADD and target identity

- **Problem / source:** WT-02; frozen [PROTOCOL.md](../../experiments/execution/da01/PROTOCOL.md). DA01 operation identity is (target_type,target_id); a new representation can cover multiple obligations, while the development planner assigns one ADD owner target.
- **Contract and alternatives:** (a) Canonical owner obligation plus coverage links needs a stable, scientifically justified owner rule; lexical first-q is only a development tie choice. (b) Emit one obligation-target prediction per obligation but group on a representation identity for artifact/cost/operation counting; this may create duplicate identity or alter accuracy. (c) Limit future eligible templates prospectively under a separately reviewed protocol; this risks selection bias and cannot exclude a difficult case in frozen DA01.
- **PROPOSED disposition:** Do not inspect private answers or select an option for score advantage. Require a prospective, unambiguous mapping that preserves one representation's identity, cost, and all independently valid coverage pairs while remaining representable by the frozen operation schema. If no such mapping exists for a case in DA01, record a compatibility blocker; do not drop it or rewrite the denominator/scorer.
- **Scientific consequence / DA01 compatibility:** The alternatives can change operation universe, duplicate counting, FP/FN behavior, and representation identity. DA01 universe and expected-operation semantics remain unchanged.
- **Required evidence / dependencies:** Public contract-level examples independent of DA01 answers, schema/scoring compatibility analysis, adversarial duplicate/conflict cases, independent review of owner/grouping semantics. Depends on OPEN-02 and exact V1 adapter behavior.
- **Reviewer / status / readiness:** Independent formal-methods and operation-scoring reviewers. Canonical **PENDING_INDEPENDENT_REVIEW**. **BLOCKED_BY_CONTRACT_COMPATIBILITY**.

### OPEN-09 — independent freeze, custody, sealing, and isolation

- **Problem / source:** WT-04, [INPUT_ISOLATION.md](../../experiments/execution/da01/INPUT_ISOLATION.md), READINESS, and traceability row TT-P03-43.
- **Contract and alternatives:** Required roles include independent algorithm/version freezer, B1 operator, holdout custodian, independent scorer/evaluator, and conflict reviewer. Roles may be combined only where an approved separation-of-duties review justifies it. Freeze generic P/protocol before predictions; seal exact bytes before scoring; keep oracle/scorer/holdout and other-method outputs outside authoring and execution inputs. Preserve conflict/exposure declarations and a post-result deviation/version log; never rewrite or replace sealed outputs. Selected-environment G2 is separate from historical synthetic probe records.
- **PROPOSED disposition:** Establish actual authorized people, conflict/exposure declarations, exact input/output inventories, custody and sealing procedure, independent scoring path, and selected-environment audit. TT-P03-43 requires an authorized inventory, exact frozen-output byte comparison, and independent signed record; this integration does not perform it.
- **Scientific consequence / DA01 compatibility:** Without independence and isolation evidence, answer leakage and post-result tuning cannot be excluded. Historical local probes and aggregate CI with a skip do not prove G2 for a measured environment.
- **Required evidence / dependencies:** Real custodian/reviewer appointments and records, exact method freeze/source pin, sealed-output protocol, environment-specific G2 report, TT-P03-43 authorization and independent byte-parity evidence. Depends on finalized OPEN-01/02/05/07/08 decisions; precedes G1 completion record and any separate G4 request.
- **Reviewer / status / readiness:** Research-integrity lead, holdout custodian, independent frozen-artifact verifier, and G1 decision authority. **PENDING_INDEPENDENT_REVIEW**; selected-environment G2 outstanding; TT-P03-43 **BLOCKED**. **PENDING_EXTERNAL_AUTHORITY**.

### Deferred item

**OPEN-10 / M-05 — adaptive α/θ:** keep deferred to a separate study. Core P v1 does not claim generalized weight or threshold optimization. Any future extension needs a distinct method/version, scientific question, authority and protocol; no current decision is requested here.

## 5. Methodological inconsistencies and evidence gaps

The labels below classify the issue; “contradiction” means two applicable semantics cannot both govern the same claim. A documentary drift or open choice is not silently converted to a contradiction.

| ID | Class | Evidence on each side | Consequence and safe disposition |
| --- | --- | --- | --- |
| C1 / OPEN-01 / M-01 | Unresolved treatment choice | Manuscript describes periodic B1; DA01 checklist is post-transition. | Different intervention and estimand. Ask reviewer to bound DA01 to one; future periodic comparison needs its own arm/protocol. |
| C2 / OPEN-02 / M-02/M-06 | Crosswalk and analysis choice | Manuscript RQ1–RQ4 differ from executable RQ1–RQ4; DA01 is one transition. | Preserve both maps; choose endpoints/hierarchy and statistical plan independently. DA01 descriptive only. |
| C3 / OPEN-03 / M-04 | Future construct extension | Future lifecycle-wide all-stage proposal vs frozen DA01 at-least-one exact pair. | Keep all-stage as separately versioned future method; do not alter denominator or scoring. |
| C4 / OPEN-04 | External evidence gap | Five distinct trust properties; pilot is DRAFT/OPEN and TEST_ONLY. | No production policy authority/completeness can be inferred from hashes or synthetic proofs. Required authority is absent. |
| C5 / OPEN-05 / M-03 | Unresolved fairness/estimand choice | Common policy/catalog bytes, P-only executable applicability and traceability; strict parity and shared precomputation are alternatives. | Declare method-specific information and evaluator-execution treatment. Shared evidence is not reference/oracle scoring. Do not change allowlists silently. |
| C6 / OPEN-06 | Unresolved cost model | Development scalar budget/search vs experimental human, compute, evaluation, validation, and resource costs. | Report dimensions separately; exhaustion is not infeasibility; no numeric boundary or global optimality claim. |
| C7 / OPEN-07 | **Contract compatibility contradiction** | P internal pair model can treat an adequate completed nonzero monitor as VALID pair + NON_COMPLIANT architecture; frozen DA01 says nonzero evaluator exit is EXECUTION_FAILURE. | Same event can change RQ2 coverage. Frozen rule governs DA01; no compatibility claim for this case until independent future versioned decision. Do not edit checker. |
| C8 / OPEN-08 | **Contract compatibility blocker** | V1 target identity is single typed target; one ADD payload may cover multiple q; planner selects lexical owner. | Owner, grouped predictions, and prospective eligibility each affect operation/scoring semantics. No answer-specific exclusion or scorer rewrite. Block if unambiguous mapping cannot be demonstrated. |
| C9 / OPEN-09 / G2 / TT-P03-43 | External/independence evidence gap | No real freeze/custody/seal roles or selected-environment audit; exact-byte parity not independently verified. | G1 cannot close on proposed procedure alone; G4 remains separately unauthorized. |
| D1 | Documentary drift | [docs/README.md](../README.md) has been updated in this PR to distinguish the synthetic DEVELOPMENT implementation from measured readiness. Only root [AGENTS.md](../../AGENTS.md) retains the stale statement that full P impact/governed adaptation are not implemented. | The README correction is included here. Root AGENTS.md remains unchanged as required and can be corrected in the next implementation-focused PR. |

### M-discrepancy crosswalk

| Research-context item | Integrated decision | Current treatment |
| --- | --- | --- |
| M-01 | OPEN-01 | Post-change may be considered for current DA01; cadence not approved. |
| M-02 | OPEN-02 | Preserve both RQ numbering systems; reconciliation and endpoint roles pending. |
| M-03 | OPEN-05 | Shared information vs P-specific executable interpretation is a fairness/estimand decision. |
| M-04 | OPEN-03 | Future stage registry only; no DA01 denominator change. |
| M-05 | OPEN-10 | Dynamic α/θ adaptation deferred. |
| M-06 | OPEN-02 | DA01 one independent transition permits descriptive reporting only. |

## 6. Integrated B0/B1/P comparison design

The following is a candidate protocol skeleton for review; it does not amend the frozen protocol or establish that the arms are ready.

| Arm | Candidate treatment | Evidence and fairness boundary |
| --- | --- | --- |
| B0 | Unchanged frozen A0 fitness configuration assessed after the same declared transition. Frozen protocol defines adaptation cost as zero. | Preserve exact parent bytes and evaluator identity. Report stale/vacuous/invalid evidence under frozen validity; zero adaptation effort does not mean zero evaluation cost. |
| B1 | Independent human applies the reviewed manual procedure to the same transition and common admissible information. Post-change is the closest current DA01 option but awaits OPEN-01. | No simulated human. Record operator experience/prior exposure, inputs, tool versions, active/wall time, deviations, reasons, candidate and exact seal before scoring. |
| P | Frozen generic method version runs on the same architecture revisions, common policy/obligation/capability inputs, and its declared method-specific traceability input. | No oracle, scorer, expected operation, sealed result, network, Git history, or other method output. Disclose programmatic applicability/traceability as part of the treatment. Publish/accept is not enabled by this document. |

### Candidate hypotheses and outcomes

- **Affected-target and operation identification:** P may improve the frozen executable RQ1 target metrics relative to B0 and B1. Candidate reports include affected-target precision/recall/F1 and normalized operation accuracy. Report target-level counts and metrics exactly as the frozen scorer defines them; preserve out-of-universe decisions and protocol violations.
- **Mandatory coverage:** P may improve independently verified **Coverage_ref** under the frozen exact-pair rule relative to B0 and B1. Report P's **Coverage_P** separately as a method diagnostic; never substitute it for Coverage_ref. Report the complete reference denominator, covered count, UNKNOWN/invalid/missing pair reasons, and evidence limits; no inferred denominator reduction.
- **Cost:** any benefit claim is conditional on a separately approved cost boundary. Report human active time, P computation/adaptation, candidate construction, evaluator execution, validation, resources and search completion as distinct fields; do not invent a weighted sum.
- **Diagnostics:** operation accuracy, validity failures, abstention/HOLD, protocol violations, evidence completeness, and reviewer-visible reasons remain available. Their role in the confirmatory endpoint family is OPEN-02.

F1 and verified coverage remain co-primary candidates pending independent endpoint selection. No minimum important effect, sample size, power, p-value, confidence level, multiplicity correction, acceptable overhead, or statistical test is approved by these documents. The independent unit is the architecture transition; DA01 has one and therefore supports a descriptive case report, not inferential claims. A future multi-transition study must independently define the transitions, units, dependence, missingness, multiplicity, effect benchmarks, uncertainty method, and external-validity coverage.

Common evaluator evidence may be supplied to each method only if a reviewed protocol explicitly makes it admissible and records its provenance. That design estimates adaptation conditional on a shared precomputed evaluation. If each arm executes evaluators, it estimates a different total treatment and incurs different execution cost. Neither precomputed method evidence nor the shared input set may include private oracle/reference verdicts or post-seal scoring.

## 7. Invariant and proof-obligation mapping

The SPEC 03 specification defines INV-01…INV-12. The implementation traceability report records synthetic engineering tests for P03-01…P03-14 and 59 PASS rows, with TT-P03-43 BLOCKED. This table connects the invariant claims to evidence categories; it is not a new test run or a formal proof.

| Invariant | Method property | Recorded synthetic evidence examples | Remaining proof/evidence limit |
| --- | --- | --- | --- |
| INV-01 | Criterion intent and hard constraints are not silently weakened. | Authorized bounded soft-adjustment validation; operation/candidate validation in [test_p_operations_v1.py](../../tests/unit/test_p_operations_v1.py) and [test_p_candidate_governance_v1.py](../../tests/unit/test_p_candidate_governance_v1.py). | Synthetic rule behavior; independent normative authority and formal soundness absent. |
| INV-02 | UNKNOWN applicability never authorizes deactivation. | **test_unknown_mandatory_applicability_never_authorizes_deactivation**; applicability Strong Kleene and open-registry tests. | TEST_ONLY policy evidence; external authority/completeness absent. |
| INV-03 | Shared representation stays active if another ACTIVE/UNKNOWN obligation may need it. | **test_shared_representation_stays_active_when_one_q_is_inactive_but_another_is_active** and related operation tests. | Synthetic obligation catalog, not measured architecture. |
| INV-04 | Coverage requires non-vacuous execution and valid exact-pair evidence. | [test_p_semantic_pairs_v1.py](../../tests/unit/test_p_semantic_pairs_v1.py): zero-exit vacuity, exact-pair mapping, same-pair counting, and stale/conflicting pair regressions. | Independent evaluator adequacy and frozen reference interpretation remain outstanding; OPEN-07. |
| INV-05 | Stale revision, bad digest, authority, or provenance cannot create positive proof. | Exact-revision preflight, digest tamper, stale-pair and cross-revision/scope replay regressions. | Synthetic trust and no selected measured-environment G2 audit. |
| INV-06 | ADD/REPLACE require a real pinned, authorized materializable artifact. | Missing/untrusted-template HOLD; full template descriptor binding and TEST_ONLY authorized descriptor tests. | No production-approved generic evaluator/template; OPEN-04/05. |
| INV-07 | Retain on proven impact requires positive semantic adequacy; unchanged is not coverage. | Impact retain tests in [test_p_impact_v1.py](../../tests/unit/test_p_impact_v1.py) plus exact-pair evidence in [test_p_semantic_pairs_v1.py](../../tests/unit/test_p_semantic_pairs_v1.py). | Scientific adequacy of trace/evaluator semantics unvalidated. |
| INV-08 | IDs, parent hashes, target uniqueness, serialization, and event history remain bound. | Parent-bytes/candidate binding, duplicate target and event-chain tampering tests. | Engineering hash integrity does not confer authority or custody. |
| INV-09 | Operations agree with the V1 non-retain projection; duplicates/conflicts are rejected. | V1 adapter tests, **test_v1_prediction_adapter_projects_exact_nonretain_targets_and_blocks_hold**, duplicate target rejection. | OPEN-08 remains a schema/scorer compatibility blocker. |
| INV-10 | Invalid/unresolved mandatory coverage cannot ACCEPT; HOLD cannot publish; rollback needs fresh validation. | **test_unresolved_coverage_is_hold_and_proven_incomplete_candidate_is_reject**, publication disabled tests, fresh-context rollback check. | Synthetic governance only; no production authority or G1/G4. |
| INV-11 | Deterministic outputs and bounded search are stable for fixed inputs. | **test_input_permutations_preserve_graph_and_impact_digests**, bounded-set-cover deterministic tie and search-exhaustion tests. | Bounded search does not imply global optimum when incomplete; cost semantics OPEN-06. |
| INV-12 | Generic method has no scenario/oracle-specific answer logic. | Generic fixture provenance, isolation negative probes and input allowlist checks documented in traceability. | No protected TT-P03-43 byte-parity comparison; no claim of independent G2 approval. |

Evidence levels must remain separate:

1. **Unit/integration regression:** records software behavior on generic synthetic fixtures.
2. **Mathematical/formal justification:** no complete independent proof of soundness/completeness is supplied here.
3. **Independent evaluator evidence:** approved real capabilities and sensitivity/adequacy review are missing.
4. **Controlled experiment:** no measured B0/B1/P result is authorized or reported.
5. **Statistical inference:** not supported by one DA01 transition.
6. **External validity:** no multi-system/multi-transition evidence is supplied.

No matter how many unit cases pass, they do not establish the later evidence levels. In particular, implementation tests are not mathematical proof, evaluator certification, G1 approval, measured effects, statistical inference, or external validity.


## 8. G1 dependency graph

| Dependency class | Prerequisite → dependent decision | Why / state |
| --- | --- | --- |
| Methodological | OPEN-01 + OPEN-05 + OPEN-06 → OPEN-02 | Cadence, information/capability parity, and cost/stop rules define the comparator and estimand; all remain open. |
| Contract compatibility | OPEN-07 and OPEN-08 → OPEN-02 | RQ2 coverage and RQ1 operation scoring cannot be interpreted until their mappings are independently dispositioned. DA01 contracts remain frozen. |
| External authority | OPEN-04 → OPEN-05 and positive applicability/coverage evidence | Policy scope/completeness and evaluator capabilities require real authority, not synthetic TEST_ONLY trust. |
| Technical/implementation | Exact source/input inventories + selected runtime → G2 and TT-P03-43 | Existing synthetic probes do not audit the selected measured environment; independent byte parity remains blocked. |
| Independent review | OPEN-01…OPEN-08 decisions + OPEN-09 custody/freeze evidence → G1 record | Workstream agreement is not independent approval; preserve reviewer identity, conflicts, findings, dates, and exact versions. |
| Measured authorization | G1 + applicable G0–G3 + authority/evaluator/B1/custody evidence → G4 | G4 is a separate run-specific authorization and remains NOT AUTHORIZED. |
| Future-only | OPEN-03 stage registry; OPEN-10 α/θ study → later method/protocol version | Neither changes current core P v1 or frozen DA01. |

OPEN-04 authority/evaluator evidence and OPEN-03 future-stage analysis can be prepared in parallel with independent resolution of the OPEN-07/08 contract questions. OPEN-01, OPEN-05, OPEN-06, and the OPEN-07/08 dispositions feed endpoint and estimand selection in OPEN-02. The dependency order is: resolve construct/scoring boundaries; establish real authority and evaluator/fairness evidence; freeze comparator, endpoints, cost and missingness rules; assign independent roles and audit the selected environment; obtain a genuine G1 decision record; request G4 separately for an exact run. No dependency is marked complete merely because a proposal exists.

## 9. Research validity and falsification plan

The proposal is falsifiable at several levels. Negative findings must be retained rather than repaired after seeing sealed outcomes.

| Claim or validity threat | Falsifying observation or review test | Evidence level and limit |
| --- | --- | --- |
| Applicability is evidence-aware and conservative. | An unknown, stale, conflicting, or incomplete rule is silently treated as INACTIVE/ACTIVE without proof; an independent policy reviewer finds unbound scope or closure. | Synthetic tests cover selected software cases; actual policy authority/completeness review is absent. |
| Impact does not miss potentially affected controls by treating unknown links as no impact. | A verified or possible path is omitted, or an incomplete graph is used to assert NOT_AFFECTED_WITH_PROOF. | Generic tests demonstrate selected path cases; no theorem or measured sensitivity estimate is supplied. |
| Pair evidence establishes representation-specific control. | Wrong revision, wrong obligation, vacuity, inadequate evidence, or semantic mismatch is accepted as valid; independent evaluator fails a clean/corrupted sensitivity test. | Regression evidence only; production evaluator authority is missing. OPEN-07 also affects compatibility with frozen RQ2. |
| Operations preserve mandatory controls and map to scorer targets. | A necessary operation is omitted, unsupported operation emitted, shared representation deactivated unsafely, or ADD target cannot be represented unambiguously. | Synthetic tests cover generic cases; OPEN-08 blocks a general DA01 compatibility conclusion. |
| Governance prevents unsafe candidate acceptance/publication. | Candidate ACCEPTs on unknown mandatory coverage, altered bound bytes, missing authority, or stale validation; HOLD is published. | TEST_ONLY development tests; no production authority or enabled atomic publisher. |
| P is more effective than B0/B1 on approved outcomes. | On preregistered independent transitions, P fails the approved comparison, violates coverage/safety, or exceeds approved cost. | Not tested; DA01 alone is descriptive and no G4 authorization exists. |
| B1 comparison is fair and independent. | Human sees P output/oracle, has unequal evaluator access/time, or cadence does not match the stated estimand. | No actual B1 session or operator record. |
| Isolation and custody prevent leakage. | The selected runtime reads protected/private inputs, network, Git history, or other method output; freeze/seal chain is incomplete. | Historical/synthetic probe evidence is not selected-environment G2; TT-P03-43 remains BLOCKED. |
| Findings generalize beyond DA01. | Independent transitions/systems/evaluator families contradict the claimed boundary or expose uncovered classes. | No cross-transition evidence; external validity UNKNOWN. |

No matter how many unit cases pass, they do not establish the later evidence levels. In particular, implementation tests are not mathematical proof, evaluator certification, G1 approval, measured effects, statistical inference, or external validity.

## 10. G1 readiness assessment

| Area | Evidence-based status | What remains |
| --- | --- | --- |
| Source integration | Four merged workstreams and frozen public contracts are available at the pinned baseline. | Independent reviewers must assess the unified package and unresolved alternatives. |
| Formal model | A coherent notation and implementation boundary can be stated; development source implements the orchestration described. | OPEN-07/08 compatibility decisions and independent formal/method review. |
| OPEN-01/02/06 | Reviewable candidate choices exist, but no independent decision. | Cadence, endpoints/hypotheses, cost units and search semantics. |
| OPEN-03/10 | Properly separated as future stage and α/θ research. | New study/version only if later authorized; no DA01 retrofit. |
| OPEN-04/05 | Development/synthetic evidence only; authority and approved evaluator capabilities absent. | External policy/evaluator authority, completeness, fairness choice. |
| OPEN-07/08 | Material compatibility blockers. | Versioned, independently reviewed disposition; DA01 remains frozen. |
| OPEN-09 / G2 | Proposed custody/freeze procedure; actual roles and selected-environment audit absent. | Real role appointments, conflict records, sealed-prediction and independent scoring process, environment audit. |
| TT-P03-43 | **BLOCKED**. No authorized exact-byte independent parity verification. | Authorized inventory, direct byte comparison, signed independent review record. |
| G1 | **INCOMPLETE**. | Independent decisions on OPEN-01…09, authentic method/protocol freeze and records. |
| G4 | **NOT AUTHORIZED**. | Separate explicit run-specific decision after prerequisites. |
| Measured P | **P_ALGORITHM_STATUS = NOT_READY**. | Readiness and authorization process; no measured result implied by this document. |

**Open for independent review:** the package structure, source crosswalk, notation correction, candidate treatments, and explicit blocker analyses.

**Blocked from closure:** any claim that the above choices are approved; a DA01 score interpretation for the OPEN-07 nonzero-exit case; an unambiguous ADD mapping for all DA01 cases; production authority/capability; G2/TT-P03-43; G1/G4 or measured readiness.

## 11. Prioritized next actions

The established monograph is the scientific basis; its model, method, research objectives, and B0/B1/P direction are defined. The next primary objective is to implement and experimentally evaluate the method according to §5. Reuse the versioned [architecture-evolution scenarios](../../experiments/design/ARCHITECTURE_EVOLUTION_SCENARIOS_V1.md), integrate executable fitness functions across CI/CD, deployment, and runtime, implement controlled degradations with reproducible evidence, and complete P with real evaluator artifacts. DA01 remains a frozen experimental case, not the scientific boundary of the dissertation. Resolve further theoretical questions only when a concrete implementation or authorized-experiment blocker requires it.

This closes the current methodological documentation-consolidation phase; it does not close G1 or authorize a measured run. G1 remains **INCOMPLETE**, G4 remains **NOT AUTHORIZED**, and P remains **NOT_READY**.

| Order | Next execution priority | Required evidence and preconditions | Boundary |
| --- | --- | --- | --- |
| 1 | Implement the planned evolution scenarios and end-to-end fitness controls across CI/CD, deployment, and runtime; add controlled degradations, reproducible evidence collection, and real-evaluator integration for P. | Reuse the V1 scenario contract; preserve DA01 and its protected artifacts; validate the implementation with synthetic engineering evidence and report remaining evaluator/authority gaps. | Implementation-focused work; no DA01 contract or gate changes. Clarify theory only for concrete blockers. |
| 2 | Prepare and execute independent B0/B1/P comparisons, then analyze detection quality, mandatory **Coverage_ref**, semantic consistency, and operational overhead. | Complete applicable G1/G4 and run-specific authorization, independent B1/fairness and evaluator evidence, preregistered outcomes, custody/sealing, and selected-environment isolation prerequisites. Keep **Coverage_P** separate from independently scored **Coverage_ref**. | No measurement before authorization; DA01 remains frozen and supports only its defined case scope. |

## 12. Open questions for the human researcher

These items remain in the existing decision docket; they do not initiate another broad review cycle. Resolve an item when it blocks concrete implementation or is required for an appropriately authorized experiment. Codex cannot approve independent decisions or experimental gates:

1. Should the dissertation's current DA01 comparator be explicitly limited to post-change B1, or must the planned scientific claim await a separate periodic-review arm?
2. Should DA01 present affected-target F1 and verified mandatory coverage as co-primary candidates or select a hierarchy, and how should manuscript and executable RQ labels be reconciled without replacing either source?
3. What real policy authority and completeness process can govern the measured obligation set, and who has custody of its trust anchors?
4. Which real evaluator artifacts are admissible and independently adequate? Does the experiment compare adaptation with evaluator execution or adaptation conditional on shared precomputed evidence?
5. What independently justified cost dimensions/limits and search stop rules define acceptable overhead without combining unlike units?
6. Should future method versions treat an adequately completed nonzero monitor as valid evidence of noncompliance, and what separately versioned contract would be required? The frozen DA01 rule remains controlling until a valid external decision.
7. Can a multi-obligation ADD be represented without changing DA01 target identity, duplicate semantics, or expected-operation meaning? If not, how should the compatibility blocker be recorded for the frozen case?
8. Who will independently freeze P and the protocol, operate B1, hold the holdout, seal predictions, score outputs, review conflicts, and audit the selected measured environment?
9. Which evidence and independent decision record would authorize G1, and what separate run-specific facts would later be required for G4?
10. Should lifecycle-stage all-required coverage or adaptive α/θ be pursued in a separate study? They remain outside DA01 and core P v1.

## 13. Source references and limitations

Primary sources are linked in §2 and in each decision record. The four review briefs are source-based proposals, not approvals. The formal source is a DEVELOPMENT implementation, not a scientific proof. The frozen protocol, scoring, validity, and isolation documents remain normative for DA01.

The following remain **UNKNOWN** or unverified in the inspected repository evidence: actual independent reviewer identities/dispositions; real production policy authority and trust-anchor custody; approved generic evaluator capabilities; actual human B1 participation; selected measured environment and its G2 audit; authorized frozen-output inventory and independent TT-P03-43 byte-parity result; sealed predictions; measured B0/B1/P outcomes; inferential statistics; and generalization beyond DA01.

This document creates no external literature or novelty claim. It makes no source-level change to application/method code, DA01 protocol/scorer/checker/input contracts, protected data, policy pilot, or workstream briefs. G1 remains **INCOMPLETE**, G4 **NOT AUTHORIZED**, measured P **NOT_READY**, and TT-P03-43 **BLOCKED**.
