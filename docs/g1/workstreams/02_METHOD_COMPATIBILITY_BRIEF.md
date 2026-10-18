# EvoFitBench G1 Workstream 02 — Formal Method & Scoring Compatibility Brief

**Status:** independent review proposal; no method, scoring, validity, or decision-register contract is changed here.
**Source baseline:** commit 6e5c43f1bc56e7216a3d5cc2c2bb50abe17c0227, branch research/g1-method.
**Scope:** OPEN-03/M-04 lifecycle-stage proof, OPEN-07 compliance versus monitor validity, and OPEN-08 multi-obligation ADD under the frozen V1 target identity.

The analysis uses the public research/specification documents, permitted DEVELOPMENT modules, and public schemas. It does not inspect private oracle/scorer material, scenario-specific expected operations, sealed predictions, or protected test internals. Source precedence remains the current DA01 protocol and schemas for DA01, with SPEC 03 and the G1 documents treated as proposed method material ([research context](../../RESEARCH_CONTEXT.md#L1), [DA01 protocol](../../../experiments/execution/da01/PROTOCOL.md#L9)).

## 1. Source baseline and implementation-status boundary

The worktree is pinned to 6e5c43f1bc56e7216a3d5cc2c2bb50abe17c0227. At this revision, Method P has a substantive synthetic DEVELOPMENT implementation across impact, semantic assessment, operations, candidate materialization, and governance. That is engineering evidence for the code paths, not a frozen algorithm or measured method.

The repository records G1 as incomplete, G4 as not authorized, and the measured interface as P_ALGORITHM_STATUS = NOT_READY. The traceability report records TEST_ONLY no-op and ADD paths reaching ACCEPT, while TT-P03-43 remains blocked because frozen-output byte parity was not independently checked. No measured DA01 prediction or result is reported ([P status](../../../experiments/execution/da01/P_ALGORITHM_STATUS.md#L1), [readiness](../../../experiments/execution/da01/READINESS.md#L6), [traceability outcome](../../SPEC_03_IMPLEMENTATION_TRACEABILITY.md#L413)).

This brief offers formal alternatives for independent review. It does not approve an option, prove the algorithm sound, alter a denominator, or advance a gate.

## 2. Formal entities and consistent mathematical notation

The model separates a versioned control configuration from the knowledge used to assess it:

\[
\Phi_t=\langle C_t,\mathcal{R}_t,\alpha_t,\theta_t,H_t,v_t\rangle
\qquad
K_t=\langle Z_t,\Pi_t,\Gamma_t,\nu_t\rangle
\]

| Symbol | Meaning | DEVELOPMENT correspondence and limit |
| --- | --- | --- |
| \(C_t\) | Stable criterion intents and approved hard constraints | Representations carry a criterion ID and obligation links; criteria and constraints are not a fully separate materialized object in the candidate path. |
| \(\mathcal{R}_t\) | The complete representation set in the configuration | Versioned representation rows contain stage, evaluator, artifact, scope, evidence contract, active state, and covered obligations. |
| \(\alpha_t,\theta_t\) | Optional weights and soft-threshold rules | There is no optimization or general adaptation of weights or thresholds in core P. An authorized bounded adjustment hook is narrower than an α/θ adaptation method. |
| \(H_t\) | Approved hard invariants | SPEC 03 carries INV-01…INV-12 as code-level governance checks; production approval of the invariant set remains a review matter. |
| \(v_t\) | Configuration and provenance identity | Parent hash, source/policy identities, operation digest, and deterministic child version are bound in DEVELOPMENT. |
| \(Z_t\) | Typed architecture facts | Snapshot fact records and source-bound observations. |
| \(\Pi_t\) | Versioned normative policy source | Snapshot policy rows plus the separately pinned V3 policy/ruleset source. |
| \(\Gamma_t\) | Evidence, evaluator records, and completeness claims | Evidence ledger and signed DEVELOPMENT sidecars. A hash proves byte identity, not authority or truth. |
| \(\nu_t\) | Revision, scope, time, version, and provenance bindings | Source digests and scoped proof bindings in the verified bundle. |

Use \(F_{\mathrm{fit}}\) only for an optional aggregate fitness function, for example \(F_{\mathrm{fit}}(\Phi_t)=\sum_i \alpha_i f_{i,\mathrm{norm}}\). Use \(Z_t\) for architecture facts. The current G1 draft uses \(F_t\) for a fact inventory in its impact equation, while the research context also uses \(F\) for the aggregate fitness function. This brief writes fact change as \(\Delta_Z\); the notation collision should be resolved in a reviewed revision of the draft, not silently rewritten here ([G1 model](../../G1_METHOD_SPECIFICATION.md#L23), [impact equation](../../G1_METHOD_SPECIFICATION.md#L94), [fitness-function note](../../RESEARCH_CONTEXT.md#L248)).

Keep these judgments distinct:

\[
g_q(K_t)\in\{\mathrm{ACTIVE},\mathrm{INACTIVE},\mathrm{UNKNOWN}\}
\]
\[
c_q(A_t)\in\{\mathrm{COMPLIANT},\mathrm{NON\_COMPLIANT},\mathrm{UNKNOWN}\}
\]
\[
V(r,q,A_t,E)\in\{\mathrm{VALID},\mathrm{INVALID},\mathrm{UNKNOWN}\}
\]

Applicability asks whether an authorized rule requires control of \(q\). Compliance asks whether the architecture satisfies that requirement. Pair validity asks whether representation \(r\) validly measures \(q\) for this architecture, scope, and stage. Coverage aggregates only valid pairs over a declared obligation set. Governance decides whether a materialized configuration candidate satisfies its proof and safety gates. A valid monitor can observe noncompliance; a compliant architecture does not, by itself, prove that a monitor is valid. The DEVELOPMENT pair result stores monitor/pair status separately from observed compliance ([pair model](../../../experiments/execution/tooling/p_semantic.py#L25), [pair assessment](../../../experiments/execution/tooling/p_semantic.py#L175), [research distinction](../../RESEARCH_CONTEXT.md#L62)).

## 3. Typed impact/coverage interpretation

For consistent notation, let \(\mathcal{R}_t\) be the full configuration representation set. Let \(\mathcal{R}^{+}_t\subseteq\mathcal{R}_t\) be representations reached by verified impact paths and \(\mathcal{R}^{?}_t\subseteq\mathcal{R}_t\) be representations reached only by possible paths. These are subsets, never alternate names for the whole \(\mathcal{R}_t\).

A coherent typed abstraction is:

\[
\Delta_Z=\mathrm{Diff}(Z_t,Z_{t+1}),\quad
\Delta_\Pi=\mathrm{Diff}(\Pi_t,\Pi_{t+1}),\quad
\Delta_g=\mathrm{Diff}(g(K_t),g(K_{t+1}))
\]
\[
S^+,S^?=\mathrm{Map}(\Delta_Z\uplus\Delta_\Pi\uplus\Delta_g,G_T)
\]
\[
P^+=\mathrm{Reach}_{G_T^+}(S^+),\quad
P^?=\mathrm{Reach}_{G_T}(S^+\cup S^?)\setminus P^+
\]
\[
\mathcal{R}^{+}_t=\pi_{\mathcal{R}}(P^+),\quad
\mathcal{R}^{?}_t=\pi_{\mathcal{R}}(P^?)
\]
\[
U_{t+1}=\{q\in Q:m(q)=\mathrm{true}\land g_q(K_{t+1})=\mathrm{ACTIVE}\land q\notin\mathrm{Covered}_{t+1}\}
\]

Here \(P^+\) and \(P^?\) are path/node domains; the projections are representation-ID subsets. \(U_{t+1}\) and the unresolved-link diagnostics \(L^?_t\) remain separate from affected representations:

\[
I_t=\langle \mathrm{Impact}_{\mathcal{R}}(\mathcal{R}^{+}_t,\mathcal{R}^{?}_t), U_{t+1},L^?_t\rangle
\]

This notation also avoids overloading \(F\) for facts. An impact path establishes a reason to reassess a control; it does not establish that the control is semantically invalid.

**What the DEVELOPMENT code does:** diff_snapshot emits typed fact and policy ChangeRecords; fact removal/addition requires scoped completeness evidence. run_adaptation also appends obligation applicability-state ChangeRecords before calling analyze_impact. Thus applicability deltas are present in the orchestration output, although there is no separate ChangeObligation algebraic type, and p_impact.diff_snapshot itself does not produce them. The G1 draft says Δ_Q is not emitted by p_impact.py; the broader orchestration and P_ALGORITHM_STATUS describe typed obligation deltas. This is a scope/documentation discrepancy to keep visible for review ([fact/policy diff](../../../experiments/execution/tooling/p_impact.py#L190), [orchestration](../../../experiments/execution/tooling/p_adaptation.py#L340), [applicability diff](../../../experiments/execution/tooling/p_adaptation.py#L1092), [draft boundary](../../G1_METHOD_SPECIFICATION.md#L109), [status crosswalk](../../G1_METHOD_SPECIFICATION.md#L213)).

The graph analyzer creates verified adjacency only for edges with matching scopes, endpoint versions, and source digests. It keeps a broader declared adjacency for possible paths. It emits PROVEN_AFFECTED, POSSIBLY_AFFECTED, NOT_AFFECTED_WITH_PROOF, or UNRESOLVED per declared representation. NOT_AFFECTED_WITH_PROOF requires verified complete graph and change inventories and no unresolved context or seed. Missing or unverified links cannot silently establish no impact. Active uncovered obligations are derived separately, so an unrepresented active obligation can still enter \(U_{t+1}\) even if the trace graph has no edge ([impact traversal](../../../experiments/execution/tooling/p_impact.py#L469), [impact classification and uncovered set](../../../experiments/execution/tooling/p_impact.py#L641)).

Coverage in the DEVELOPMENT module is deduplicated per mandatory, active obligation. It can report COMPLETE, INCOMPLETE, or UNKNOWN. Applicability UNKNOWN remains unresolved; a missing/invalid pair is not positive coverage. Operation planning separately consumes impact, pair evidence, and coverage. Candidate construction binds a child to parent bytes; candidate_validation=valid is not governance ACCEPT. Governance requires positive invariant, coverage, cost, candidate, and pipeline proof before ACCEPT; the V1 adapters check the exact sealed ACCEPT ([coverage](../../../experiments/execution/tooling/p_semantic.py#L417), [operations](../../../experiments/execution/tooling/p_operations.py#L142), [candidate](../../../experiments/execution/tooling/p_candidate.py#L35), [governance](../../../experiments/execution/tooling/p_governance.py#L203)).

## 4. OPEN-03 stage-model alternatives

Lifecycle stage is part of representation context: the exact-pair proof binds the representation stage. DA01 RQ2 nevertheless defines coverage by exact \((representation\_id, obligation\_id)\) evidence and one fixed obligation denominator; it does not require a general registry of CI/test, deployment, or runtime stages.

| Semantics | Definition | Denominator and assumption |
| --- | --- | --- |
| Existing DA01 / at-least-one pair | \(covered(q)=1\) when at least one active representation has independently valid execution and exact-pair evidence for \(q\). Stage is checked as context for that pair. | Fixed required-obligation set \(Q_D\); each obligation counts once. No stage expansion. |
| All required stages, obligation-level | Given an approved, verified, nonempty registry \(\Sigma_v(q)\), \(\operatorname{CoveredAllStages}(q,A)=1\) iff \(\bigwedge_{s\in\Sigma_v(q)}\operatorname{CoveredStage}(q,s,A)\). The predicates are defined below and require independent execution and exact-pair validity. | Denominator stays \(|Q_M|\), where \(Q_M\) is the mandatory applicable obligation set. Every required stage must pass before that obligation contributes one. This is strict and preserves equal obligation weight. |
| Stage-pair, micro-coverage | \(C_{stage}=\frac{\sum_{q\in Q_M}\sum_{s\in\Sigma_v(q)}w_{q,s}\,1[\operatorname{CoveredStage}(q,s,A)]}{\sum_{q\in Q_M}\sum_{s\in\Sigma_v(q)}w_{q,s}}\). | Denominator is the number or total weight of required obligation-stage pairs. With unit weights, obligations requiring more stages receive more total weight unless normalized. |
| Explicit stage alternatives | For reviewed stage groups \(G_v(q)\), \(\operatorname{CoveredAllStages}(q,A)=1\) iff \(\forall G\in G_v(q)\ \exists s\in G:\ \operatorname{CoveredStage}(q,s,A)\). | Appropriate only when stages within a group are approved substitutes. The alternative groups and their weights must be frozen. |

The frozen DA01 rule remains \(\operatorname{Covered}_{DA01}(q,A)=1\) iff there exists an active \(r\) with both an independently valid execution verdict \(\operatorname{ExecutionValid}_{DA01}(r,A)\) and an independently valid exact-pair verdict \(\operatorname{PairVerdictValid}_{DA01}(r,q,A,E_{r,q})\). The fixed complete required-obligation denominator, equal obligation weighting, and one-count-per-obligation rule remain in force; stage is checked as pair context, with no universal quantification over lifecycle stages.

For this proposed future all-stage model, let \(A\) be the exact target architecture revision, \(\mathcal{R}_{\mathrm{active}}(A)\) the complete active representation set for the candidate evaluated at \(A\), \(\operatorname{scope}(r)\) the representation scope, and \(E_{r,q}\) the evidence for the exact representation-obligation pair. A stage is covered only when both independent validity conditions hold:

\[
\begin{aligned}
\operatorname{CoveredStage}(q,s,A)
={}&\exists r\in\mathcal{R}_{\mathrm{active}}(A):\operatorname{stage}(r)=s\\
&\land\operatorname{ExecutionValid}(r,A,s,\operatorname{scope}(r))\\
&\land\operatorname{PairVerdictValid}(r,q,A,s,\operatorname{scope}(r),E_{r,q})
\end{aligned}
\]

\[
\operatorname{CoveredAllStages}(q,A)=
\begin{cases}
\displaystyle\bigwedge_{s\in\Sigma_v(q)}\operatorname{CoveredStage}(q,s,A),
&\operatorname{RegistryOK}(q,\Sigma_v(q))=\mathrm{TRUE}\\
\mathrm{UNKNOWN},&\text{otherwise.}
\end{cases}
\]

Evaluate the existential and conjunction with three-valued semantics. Any active representation with both verdicts valid makes its stage TRUE. If no valid witness exists, a proven absence or failure makes that stage FALSE; unresolved representation inventory or evidence leaves it UNKNOWN. The all-stage result is TRUE only when every required stage is TRUE, FALSE when any required stage is FALSE, and UNKNOWN otherwise. Only TRUE contributes one covered obligation.

Here \(\operatorname{ExecutionValid}\) is the independently verified evaluator/representation execution verdict for that representation, target revision, stage, and scope. \(\operatorname{PairVerdictValid}\) is the independently verified semantic/evidence verdict for the exact \((r,q)\) pair at those same bindings. The evidence and verdicts must identify the target architecture revision, stage, scope, representation, and obligation. Both conditions must be valid; the \texttt{covers} field alone does not establish coverage. One representation can satisfy a required stage only with sufficient execution and exact-pair evidence for that stage.

\(\operatorname{RegistryOK}\) means the versioned required-stage registry for \(q\) is approved, independently verified, resolved, and nonempty. An absent, unverified, unresolved, or empty registry therefore yields UNKNOWN, never vacuous success. A missing or unresolved execution/pair verdict likewise cannot satisfy a stage. Requiring multiple stages changes what “covered” means even when the obligation-level denominator remains fixed: an obligation that previously had one valid pair may become uncovered if another required stage lacks evidence. A stage-pair denominator changes both its numeric size and the implicit weighting.

The DEVELOPMENT \(p_{\mathrm{semantic}}\) \(\texttt{PairStatus}\) is a method-side assessment. Its \(\texttt{VALID}\) value does not itself establish the independent DA01 reference verdict ([method pair status](../../../experiments/execution/tooling/p_semantic.py#L25)).

**Implementation boundary:** assess_mandatory_coverage already accepts required_stages and stage_contract_verified. When a verified nonempty stage set is supplied, it requires all listed stages for that obligation and still counts the obligation once in mandatory_total. run_adaptation verifies the stage claim against the V3 bundle and pinned capability source. A synthetic test verifies that a required-stage set needs an independent stage-contract proof. This is a narrower DEVELOPMENT mechanism, not an approved lifecycle registry or DA01 amendment ([coverage stage logic](../../../experiments/execution/tooling/p_semantic.py#L417), [scoped stage proof](../../../experiments/execution/tooling/p_adaptation.py#L741), [stage test](../../../tests/unit/test_p_semantic_pairs_v1.py)).

**DA01 boundary:** keep its current exact-pair rule, full required-obligation denominator, equal obligation weights, and existing validity schemas unchanged. A later end-to-end study needs a separate reviewed stage registry, stage-specific evidence contracts, stage availability and missingness rules, pair-validation procedure, denominator/crosswalk, and preregistered aggregation. Do not add lifecycle stages to the frozen DA01 denominator ([OPEN-03](../../G1_METHOD_DECISION_REGISTER.md#L118), [DA01 RQ2](../../../experiments/execution/da01/SCORE_RULES.md#L31), [M-04](../../RESEARCH_CONTEXT.md#L259)).

## 5. OPEN-07 compliance/monitoring decision matrix

The P-side pair result and the independent DA01 reference verdict answer different questions. In the table, V is the DEVELOPMENT PairStatus; “coverage” refers to DA01 RQ2 unless marked method-side.

| Condition | Applicability | Observed compliance | P-side pair validity | Independent DA01 validity / coverage implication | Governance implication | Unresolved |
| --- | --- | --- | --- | --- | --- | --- |
| Completed, adequate evaluator detects a real architecture violation | ACTIVE if policy proof is positive; otherwise UNKNOWN | NON_COMPLIANT only when the evaluator’s contracted result is evidence of a rule violation | VALID is possible if artifacts, scope, nonvacuity, exact-pair proof, and all bindings pass; code records a completed nonzero exit as NON_COMPLIANT without making that reason alone INVALID | Written VALIDITY_RULES classify a nonzero evaluator exit as EXECUTION_FAILURE, so the current DA01 reference path would not grant valid execution or coverage from that exit | Current governance is about configuration proof and does not take a separate compliance verdict as an input; a configuration ACCEPT would not mean the architecture complies. A separate hard compliance disposition needs review | Reconcile the frozen reference rule with the DEVELOPMENT behavior before measurement; define evaluator-specific exit semantics and whether a real violation is a candidate hard failure |
| Completed, adequate evaluator returns compliant result | ACTIVE or independently determined state | COMPLIANT is recorded for completed exit 0 | VALID only with exact semantic proof, current revision, scope, real artifact and nonvacuous evidence | Exit 0 alone is insufficient. Reference validity and exact-pair evidence must both pass; then q can count once | ACCEPT remains conditional on all candidate gates; it says the control configuration is admissible, not that every system property has been independently proved by this one result | Establish that the evaluator can detect a corrupted control case; a clean result alone is not an adequacy proof |
| Proven semantic mismatch | Applicability is independent | Any exit-derived value is not trustworthy for the intended q | INVALID for an explicit mismatch; UNKNOWN if compatibility/proof is unresolved | SEMANTIC_MISMATCH or equivalent invalid pair; no RQ2 coverage | Proven invalid control/coverage failure can REJECT a valid candidate; unresolved evidence should HOLD | Freeze rules separating “monitor cannot assess q” from a true q violation |
| Vacuous evaluator success | Applicability is independent | A zero exit is not evidence of compliance when no applicable targets or subjects were inspected; current code nevertheless records COMPLIANT from exit 0 | INVALID because VACUOUS_SUCCESS is a hard mismatch | VACUOUS_SUCCESS; no valid execution and no coverage | A demonstrated incomplete candidate can REJECT; unresolved coverage can HOLD | Current compliance field overstates what an exit 0 means for a vacuous run; define compliance as UNKNOWN in that condition in a reviewed contract |
| Stale or mismatched architecture revision | Applicability may be known for the current revision | UNKNOWN for the current target; a raw observation from another revision cannot be attributed | INVALID for a bound revision mismatch; a stale PairAssessment passed to coverage is excluded and makes the affected obligation unresolved | STALE_ARCHITECTURE_SCOPE or revision mismatch; no coverage | Invalid current proof blocks ACCEPT; depending on whether the failure is proven or merely unavailable, REJECT versus HOLD follows governance precedence | Specify stale evidence expiration and distinguish a proved wrong revision from a missing revision binding |
| Missing evaluator artifact or artifact bytes | Applicability may be known | UNKNOWN | Usually UNKNOWN for unavailable bytes; an invalid path or digest mismatch is INVALID | MISSING_EVIDENCE / invalid evaluator evidence; no coverage | HOLD when required artifact/proof is unavailable; proven tampering can REJECT | Set stable reference status for missing artifact versus digest tampering |
| Missing exact-pair evidence | Applicability may be known | UNKNOWN unless another independent source establishes it | UNKNOWN when an expected pair has no evidence; an absent pair record is simply not demonstrated | Missing obligation verdict is MISSING_EVIDENCE; q is uncovered | HOLD for unresolved exact-pair status; a positively established incomplete candidate can REJECT | Define the method-outcome aggregation for abstention without shrinking Q_D |
| UNKNOWN obligation applicability | UNKNOWN | A raw evaluator may have a result, but it does not resolve whether q is mandatory | Pair may be assessed independently; coverage for q remains UNKNOWN | The private complete DA01 denominator remains fixed; a P-side UNKNOWN cannot remove q from it | HOLD; UNKNOWN cannot become INACTIVE or authorize deactivation | Specify the comparison treatment while retaining raw status and the complete denominator |
| Evaluator infrastructure failure | Applicability may remain ACTIVE | UNKNOWN; do not infer architecture failure | UNKNOWN, not a compliance failure | INFRASTRUCTURE_FAILURE; no semantic pass or valid coverage | HOLD or an explicit operational abstention; do not REJECT the architecture from the runner outage | Predeclare how infrastructure failures enter any comparative estimand |
| Independent reference-checker failure | Method applicability may be known | UNKNOWN from the failed independent assessment | P-side V may have been computed, but it is not a substitute for the reference result | Record checker error; no method success/failure inference, no valid RQ2 metric, and no imputation | P governance does not consume this post-seal result; it cannot authorize a measured effectiveness claim | Define run-level validity/aggregation handling before G4; keep this distinct from P failure |

The most important contract discrepancy is concrete: p_semantic permits a completed nonzero result to coexist with PairStatus=VALID and compliance_status=NON_COMPLIANT when the exact proof is valid and no other failure remains. The frozen DA01 VALIDITY_RULES currently say a nonzero evaluator exit is an execution failure. The synthetic test named test_clean_nonzero_exit_records_noncompliance_without_invalidating_monitor_semantics verifies the DEVELOPMENT behavior; it cannot revise the DA01 reference verdict rule. The G1 review must reconcile these statements without changing the existing scorer or validity contracts in this brief ([P classification](../../../experiments/execution/tooling/p_semantic.py#L297), [pair status resolution](../../../experiments/execution/tooling/p_semantic.py#L328), [frozen validity rule](../../../experiments/execution/da01/VALIDITY_RULES.md#L46), [test entry point](../../../tests/unit/test_p_semantic_pairs_v1.py)).

## 6. OPEN-08 multi-obligation ADD alternatives

The frozen prediction identity is one typed pair \((target\_type,target\_id)\). For ADD, the DEVELOPMENT planner uses target_type=obligation and one obligation ID. A representation’s covers list can still name several obligations, each requiring its own exact pair for coverage. The candidate representation ID and its obligation target are distinct identities ([score identity](../../../experiments/execution/da01/SCORE_RULES.md#L3), [planner owner mapping](../../../experiments/execution/tooling/p_operations.py#L394)).

| Option | Semantic interpretation and identity | Candidate mapping and duplicates | Metric consequences and conditions |
| --- | --- | --- | --- |
| Canonical owner obligation | One materialized representation corresponds to one ADD decision. Choose one owner q and emit (obligation,q,ADD); candidate carries the representation once and keeps all its covers links. Current code picks the lexicographically first uncovered obligation the template covers. | Candidate is materialized once under its representation ID. Repeated operations on the same typed target are rejected; the current planner tracks obligations already covered by a selected template. The owner tie-break is deterministic, but lexical order has no inherent scientific meaning. | If the independent target contract treats every newly controlled q as a positive ADD target, one owner omits positives and creates FNs. If the contract treats one evaluator artifact as one action, separate q-targets would overcount. A reviewed, normative owner rule and candidate-to-prediction crosswalk are prerequisites. |
| Separate obligation-level ADD predictions | Emit one typed ADD for each q supported by the new representation; each operation names its own obligation target, while the representation identity and artifact are shared. | Different q targets are distinct V1 target pairs, so they are not duplicate target identities. However, the current candidate materializer applies each ADD payload separately and rejects the repeated representation ID on the second application. A grouped candidate/operation mapping or output-only projection would need a new reviewed rule. Duplicate entries for the same q remain contradictory. | Recall can rise or precision fall depending on how the reference labels a multi-q artifact; repeated operations can also distort operation accuracy and cost. The protocol must say whether one artifact is charged once and how shared candidate identity is normalized. |
| Prospectively restrict multi-obligation ADD in a separate future protocol | A future protocol may declare an eligibility rule for a single designated uncovered obligation, subject to independent review. This option cannot filter an already frozen DA01 case. Synthetic DEVELOPMENT support may remain as engineering behavior. | Existing one-target candidate and prediction adapters remain usable; there is no implicit transformation of a multi-cover candidate into scenario-specific answers. | Any future restriction narrows the empirical claim and requires prospective declaration plus justification of scientific scope and selection bias. |

For every option, the candidate’s additional covered obligations need independent exact-pair evidence. An operation prediction does not establish coverage. Public scoring rules are enough to establish the typed target identity, precision/recall consequences, complete-universe operation accuracy, duplicate rejection, and separate exact-pair coverage. They do not disclose how the private reference labels a single multi-obligation artifact; no conclusion about that label is justified without an independently approved public mapping rule ([RQ1/RQ2 rules](../../../experiments/execution/da01/SCORE_RULES.md#L5), [candidate materialization](../../../experiments/execution/tooling/p_candidate.py#L371), [V1 adapter](../../../experiments/execution/tooling/p_candidate.py#L296)).

**Frozen DA01 compatibility boundary:** the existing DA01 target universe, expected-operation semantics, complete mandatory-obligation denominator, validity rules, and scorer remain authoritative and unchanged. Neither this workstream nor Method P may exclude a mandatory DA01 case because its ADD mapping is inconvenient or unresolved. If a frozen case cannot be represented unambiguously under the current method-output contract, record a compatibility blocker and resolve OPEN-08 before G1/G4; retain the case, oracle, and scoring rules unchanged. A method-side HOLD or inability to express a prediction remains visible under the existing protocol: it must not be relabeled as an accepted RETAIN, used to remove a mandatory obligation, or presented as supported coverage.

Deferring multi-obligation ADD or restricting eligibility may be considered only as a prospectively declared rule in a separately designed future protocol, subject to independent review and a justification of the resulting scientific scope and selection bias. The current DEVELOPMENT lexical owner rule is an implementation fact, not an approved scientific operation-target rule.

## 7. Frozen DA01 compatibility assessment

The following boundary preserves the current Phase A contract:

1. RQ1 target identity stays \((target\_type,target\_id)\). Precision, recall, F1, operation accuracy, empty-set handling, unknown-target handling, and duplicate validation stay unchanged.
2. RQ2 uses the complete private required-obligation set and equal obligation weights; the public score rules state six obligations for the frozen DA01 oracle. Each q counts once when an active representation has valid evaluator execution plus a valid exact \((representation\_id,q)\) verdict at the target architecture SHA. A shared representation needs a separate valid pair for each q.
3. No lifecycle-stage registry or stage-expanded denominator is added to DA01. Stage remains part of pair context and the validity evidence.
4. Coverage_before remains the unchanged A0 configuration assessed against the target architecture; Coverage_after remains the candidate assessed against that same architecture and denominator.
5. The private denominator, oracle, expected operations, reference rules, scorer, and other methods’ outputs remain outside P inputs. Method-side coverage cannot redefine the scorer’s denominator.
6. A valid P-side result, a TEST_ONLY governance ACCEPT, and a valid candidate schema do not establish independent DA01 coverage or measured success.

These are compatibility constraints, not new scoring decisions. The public V1/V2/V3 compatibility byte check recorded as TT-P03-43 remains blocked pending permitted independent byte-parity verification; this work does not perform that check ([DA01 scoring](../../../experiments/execution/da01/SCORE_RULES.md#L31), [input allowlist](../../../experiments/execution/da01/INPUT_ISOLATION.md#L8), [traceability status](../../SPEC_03_IMPLEMENTATION_TRACEABILITY.md#L430)).

## 8. Invariant-to-evidence mapping

The table maps SPEC 03 invariants to existing synthetic test entry points recorded in the repository. A listed PASS is the traceability report’s engineering result, not an independent proof of a mathematical property.

| Invariant | Existing synthetic evidence | Evidence limit |
| --- | --- | --- |
| INV-01 — Preserve criterion intent and hard constraints | test_adjustment_requires_authorized_bounded_soft_rule in [operation tests](../../../tests/unit/test_p_operations_v1.py) | Checks the bounded adjustment hook; it does not validate all possible criterion-intent weakening. |
| INV-02 — UNKNOWN never authorizes INACTIVE/deactivate | test_unknown_mandatory_applicability_never_authorizes_deactivation and test_deactivation_requires_all_linked_controls_verified_inactive in [operation tests](../../../tests/unit/test_p_operations_v1.py) | Synthetic policy/completeness evidence only. |
| INV-03 — Do not deactivate a shared control still needed by ACTIVE/UNKNOWN q | test_shared_representation_stays_active_when_one_q_is_inactive_but_another_is_active in [operation tests](../../../tests/unit/test_p_operations_v1.py) | Does not establish completeness of a production obligation catalog. |
| INV-04 — Coverage needs current, nonvacuous, exact-pair evidence | test_zero_exit_without_resolved_inspected_subjects_is_vacuous, test_wrong_obligation_identity_cannot_borrow_same_metric_evidence, and test_same_valid_pair_counts_once_and_unknown_mandate_blocks_coverage in [pair tests](../../../tests/unit/test_p_semantic_pairs_v1.py) | Test verifier and evidence are synthetic. |
| INV-05 — Wrong revision, provenance, authority, or digest cannot prove validity | test_stale_pair_architecture_revision_cannot_satisfy_coverage and test_mutated_pair_status_with_stale_digest_cannot_count_as_valid in [pair tests](../../../tests/unit/test_p_semantic_pairs_v1.py); stale-seed and unversioned-edge cases in [impact tests](../../../tests/unit/test_p_impact_v1.py) | Does not certify production trust anchors or live evidence truth. |
| INV-06 — ADD/REPLACE uses a real authorized hash-bound artifact | test_same_artifact_bytes_do_not_authorize_a_different_template_descriptor and test_missing_or_untrusted_template_is_hold_not_a_fictional_add in [operation tests](../../../tests/unit/test_p_operations_v1.py) | TEST_ONLY evaluator and template, not production-authorized capability. |
| INV-07 — Impacted retain requires positive reassessment | test_proven_impact_requires_reassessment_but_does_not_override_valid_semantics in [operation tests](../../../tests/unit/test_p_operations_v1.py) | Synthetic trace and pair evidence; not a soundness theorem. |
| INV-08 — Stable identity, parent binding, and immutable history | test_candidate_materialization_binds_parent_artifacts_and_all_source_versions, test_child_configuration_version_is_deterministic_and_parent_bound, and test_append_only_event_chain_is_deterministic_and_identical_replay_is_idempotent in [candidate/governance tests](../../../tests/unit/test_p_candidate_governance_v1.py) | Repository-level software properties only. |
| INV-09 — V1 target and operation mapping is unique and consistent | test_candidate_rejects_duplicate_operation_targets_and_tampered_plan_digest and test_v1_prediction_adapter_projects_exact_nonretain_targets_and_blocks_hold in [candidate/governance tests](../../../tests/unit/test_p_candidate_governance_v1.py) | Does not resolve the semantic granularity of multi-obligation ADD. |
| INV-10 — No ACCEPT with unresolved coverage; safe publish and rollback | test_unresolved_coverage_is_hold_and_proven_incomplete_candidate_is_reject, test_publication_stays_disabled_without_an_atomic_compare_and_swap_writer, and test_rollback_requires_positive_fresh_current_context_validation in [candidate/governance tests](../../../tests/unit/test_p_candidate_governance_v1.py) | No production publisher or measured rollback exists. |
| INV-11 — Identical inputs yield deterministic semantics | test_input_permutations_preserve_graph_and_impact_digests in [impact tests](../../../tests/unit/test_p_impact_v1.py), plus bounded set-cover ordering in [operation tests](../../../tests/unit/test_p_operations_v1.py) | Bounded-search behavior is synthetic; no operational cost validity follows. |
| INV-12 — No oracle-specific rules or forbidden input access | The reported synthetic Docker probe, test_container_negative_probes_cannot_reach_oracle_history_network_or_other_output, and generic-ID integration tests ([traceability](../../SPEC_03_IMPLEMENTATION_TRACEABILITY.md#L413)) | This review did not read the protected test module; local probe evidence does not certify arbitrary host/runtime compromise. |

The traceability report states that its current run had 59 PASS and one BLOCKED row, including the frozen-byte check; that result is reported here as historical evidence and was not rerun for this document ([traceability](../../SPEC_03_IMPLEMENTATION_TRACEABILITY.md#L430)).

## 9. Falsifiable properties and counterexample classes

The method’s central safety claims need counterexamples that would fail an implementation or falsify the method specification:

- **Conservative impact:** remove a relevant trace edge while declaring the graph incomplete. If the corresponding representation is labeled NOT_AFFECTED_WITH_PROOF, the claim fails. Also permute edges and add an isolated component; unrelated classifications should remain stable.
- **Positive proof for retention:** mark a representation impacted, then omit its current exact-pair proof or substitute proof for a different q, stage, scope, or architecture revision. RETAIN must not be justified by an old pass flag or another pair.
- **No unsupported deactivation:** let one linked obligation become INACTIVE while another remains ACTIVE or UNKNOWN. A representation serving either live or unresolved mandatory obligation must not be deactivated.
- **No fabricated evaluator:** provide an evaluator label or template descriptor without authorized descriptor proof and artifact bytes. ADD/REPLACE must stay blocked; changing the bytes without changing the authorized digest must fail closed.
- **Nonvacuous exact-pair coverage:** use exit 0 with no resolved targets or inspected subjects, or reuse one pair verdict across another obligation. The q must remain uncovered.
- **Validity/compliance separation:** use a correctly scoped and semantically adequate evaluator that signals a real violation, then contrast it with an infrastructure crash, semantic mismatch, and stale revision. The monitor verdict must not be collapsed into the compliance observation.
- **Deterministic operation choice:** reorder inputs, present equal-cost plans, repeat a shared artifact, and exceed the search budget. Stable inputs should yield the same canonical plan; exhaustion or unknown costs must not be presented as an optimum.
- **Governance and rollback:** mutate the candidate after ACCEPT, attempt publication with a changed context/parent, or revalidate an old configuration only under an obsolete context. No stale or altered configuration may be accepted or rolled back.
- **Stage denominator:** omit one required stage, then remove or leave unsigned the stage registry. Under all-stage semantics the former cannot count fully covered; the latter must be UNKNOWN, not an empty requirement set.

Several of these counterexample classes have synthetic regression coverage. Independent proof obligations remain: prove that the impact relation is conservative for the declared graph model, characterize false positives and false negatives under incomplete traceability, justify evaluator semantics and authority, and show that acceptance rules preserve the intended scientific construct across independently designed cases.

## 10. Implementation versus proposal versus missing proof

| Status | Finding |
| --- | --- |
| Implemented in DEVELOPMENT | Typed fact/policy changes, source/version-bound graph traversal, separate PROVEN/POSSIBLE/UNRESOLVED impact states, per-obligation coverage, deterministic operation ordering, digest-bound candidate construction, sealed governance decisions, and synthetic V1 adapters. “Implemented” describes code behavior; it does not prove the algorithm correct. |
| Implemented with narrower scope | Applicability changes enter through orchestration-generated obligation ChangeRecords rather than a distinct typed Δ_Q algebra; optional all-required-stage coverage exists behind proof-bound DEVELOPMENT inputs, with obligation-level counting; pair assessment records monitor/pair status and compliance separately, while the frozen DA01 reference contract uses separate execution and exact-pair verdicts. |
| Proposed but not implemented as a scientific contract | Independently approved lifecycle-stage registry; frozen stage aggregation; reviewed multi-obligation ADD normalization; formally justified error model for incomplete graphs; accepted production publication/atomic rollback protocol; general α/θ adaptation. |
| Ambiguous and requiring independent review | Nonzero-exit semantics across P and frozen DA01 validity; whether an observed architecture violation is a hard candidate rejection or a valid monitored state; denominator/weight policy for a future multi-stage study; target granularity and artifact cost for multi-obligation ADD. |

Production policy authority, evaluator templates, and cost authority are also absent from the current catalog path. The no-op and ADD integration passes use TEST_ONLY trust. The independent measured reference-evaluator path and G1/G4 authorizations remain separate ([development limits](../../../experiments/execution/P_GOVERNED_ADAPTATION_V1.md#L57), [G1 status](../../G1_REVIEW_CHECKLIST.md#L15)).

## 11. Recommended options for independent review

These are review recommendations, not approved decisions.

- **OPEN-03:** preserve the DA01 rule without stage requirements. For a later end-to-end study, review an explicit versioned stage registry. Consider all-required-stage coverage with one equal-weight contribution per obligation as the primary candidate; report stage-pair completeness as a diagnostic. This keeps the current obligation weighting while making every required lifecycle stage a hard condition. If partial-stage credit is scientifically desired, predeclare its stage-pair denominator and weights as a separate estimand.
- **OPEN-07:** specify monitor validity and architecture compliance as orthogonal outputs. Interpret a nonzero exit as NON_COMPLIANT only when the evaluator contract establishes that the process completed, assessed the intended scope, and uses nonzero to signal the tested architectural violation. Preserve infrastructure failure, vacuity, stale scope, semantic mismatch, and missing evidence as distinct. For DA01, follow the current written reference-validity contract until an independently reviewed versioned change reconciles the nonzero-exit conflict; this brief makes no such change.
- **OPEN-08:** for frozen DA01, keep every target, expected-operation rule, mandatory obligation, and scorer rule in force; an ambiguous ADD mapping is a compatibility blocker to resolve before G1/G4, not a basis to exclude the case. Only a separate future protocol may prospectively restrict multi-obligation ADD eligibility, with independent review and an explicit scope and selection-bias justification. The DEVELOPMENT lexical owner is not approved scientific mapping; independent G1 review is still required. If a later study adopts one artifact/one ADD, consider an explicit canonical owner field tied to template semantics while retaining other links in the candidate and requiring separate exact-pair evidence. Separate ADD targets need a grouped candidate representation and a once-only artifact-cost rule.

Before G1, the independent review should settle these choices, test their counterexamples with synthetic generic IDs, crosswalk them to frozen schemas without changing them, and record the decision outside this proposal.

## 12. Remaining scientific limitations

Synthetic tests demonstrate selected software behavior. They do not prove impact soundness, evaluator truth, policy authority, stage completeness, fairness against a real human B1, or improved outcomes. DA01 has one architecture transition and supports descriptive case reporting only. There is no basis here for population significance, cross-stack generalization, runtime benefit, or α/θ effect claims.

The tested evaluator and trust inputs are TEST_ONLY. Production policy/completeness authorities, generic evaluator templates, and authorized cost limits remain unavailable. Independent review of the general algorithm and the OPEN decisions remains pending; G4 measured-run authorization remains absent. A future result must retain UNKNOWN and failure statuses, preserve the fixed DA01 denominator, and distinguish code-level regressions from independent reference validity and scientific validation.
