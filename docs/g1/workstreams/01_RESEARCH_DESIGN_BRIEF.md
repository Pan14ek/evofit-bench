# G1 Workstream 01 — Research Design & Preregistration Brief

**Status:** `PROPOSED` — for independent review; not a G1 decision, protocol freeze, G4 authorization, or experimental result.
**Source baseline:** `main` at `6e5c43f1bc56e7216a3d5cc2c2bb50abe17c0227` (2026-10-17), the assigned worktree base.
**Assigned decisions:** OPEN-01 / M-01 and OPEN-02 / M-02 / M-06.
**Scope:** research-question alignment, human B1 comparator alternatives, candidate hypotheses/endpoints, and a later multi-transition analysis design.
**Boundary:** this proposal does not amend the canonical preregistration, decision register, DA01 protocol, frozen scores, or validity rules. It reports no B1 session, measured B0/B1/P result, effect, or approval.

## 1. Purpose, source baseline, and attribution

The dissertation’s object is the versioned configuration of architectural fitness controls across architecture evolution. The scientific claim concerns whether evidence-governed adaptation can preserve valid, evidence-supported control of applicable architectural obligations. This is broader than checking whether an evaluator exits successfully. The working manuscript hypothesis remains conditional: P may improve predefined impact-identification, coverage, consistency, or detection outcomes against B0 and an independent human B1 without unacceptable cost. It is not an observed result. [SOURCE: `docs/RESEARCH_CONTEXT.md`, §§1–3, 7]

This brief uses the repository’s current frozen DA01 operational descriptions as the boundary for DA01 claims. The Phase A protocol defines one architecture delta as one research unit, limits DA01 to executable RQ1 and RQ2, and says DA01 cannot establish runtime improvement or population significance. The readiness report keeps G1 incomplete, B1/P measured execution not ready, and G4 unauthorized. [SOURCE: `experiments/execution/da01/PROTOCOL.md`, “Research scope” and “Review gates”; `experiments/execution/da01/READINESS.md`, “Gate status”]

Attribution labels used below:

- **SOURCE** — stated by an existing repository contract or recorded status.
- **PROPOSED** — a candidate design choice offered for review; it has no authority until independently decided.
- **PENDING_INDEPENDENT_REVIEW** — a decision already assigned to independent reviewers.
- **UNKNOWN** — the available source does not establish a value or rule. No numerical threshold is supplied here.

The research packet’s historical source-revision headers predate this worktree baseline. This brief records the actual assigned baseline above; it does not alter those documents or treat their proposals as approvals.

## 2. Research-question and claim crosswalk

The dissertation’s scientific questions and the executable experiment’s RQ labels are different numbering systems. Preserve both until independent review records a mapping; do not silently rename RQ3 or RQ4. [SOURCE: `docs/RESEARCH_CONTEXT.md`, “RQ identity crosswalk”; `docs/DA01_PREREGISTRATION_DRAFT.md`, §2]

| Research layer | Question or claim | What DA01 can address | What needs another study |
| --- | --- | --- | --- |
| Dissertation-level working claim | Can governed adaptation preserve meaningful control of applicable architectural obligations across evolution, with better predefined outcomes than unchanged B0 and independent human B1 at acceptable cost? | DA01 can provide one bounded case on impact identification and independently verified post-change obligation coverage. It can show the case’s evidence and failure modes descriptively. | A population claim, broad generalization, lifecycle-wide control, or acceptable-cost conclusion needs independently constructed transitions, a preregistered analysis, and appropriate lifecycle/cost evidence. |
| Manuscript RQ1 | Does governed adaptation improve architectural-control quality over frozen and periodic heuristic baselines? | Executable DA01 RQ1 measures typed affected-target identification and operation selection; RQ2 measures verified post-change coverage. These are supporting outcomes, not a complete test of the broader question. DA01’s B1 checklist is post-change, not periodic. | A periodic comparator requires a cadence-based design. The broad question needs an independently reviewed mapping and a later sample of transitions. |
| Manuscript RQ2 | Does adapting representations, metrics, execution policies, weights, and thresholds improve coverage and consistency? | Executable DA01 RQ2 tests mandatory-obligation coverage and exact-pair semantic/evidence validity under the existing contract. | DA01 does not test weight/soft-threshold adaptation or a general multi-stage lifecycle denominator. Those require separately approved extensions/studies (M-04, M-05). |
| Manuscript RQ3 | What operational cost does governed adaptation add? | DA01 records separated adaptation-time fields, and B0 time is defined as zero, but DA01 is not a general operational-cost or runtime-benefit trial. | The executable design’s RQ4 addresses adaptation/CI/runtime overhead, CPU, memory, telemetry, and active signals. A cost study needs fixed environments, cost units, measurement windows, and an acceptable-overhead rule. |
| Manuscript RQ4 | Does formal impact analysis plus validation outperform periodic heuristic review? | A post-change B1 can be compared with P on DA01 RQ1/RQ2 outcomes only if its intervention and fairness conditions are approved. | The executable design labels RQ3 as controlled-degradation detection and RQ4 as overhead. A formal-impact ablation or cadence comparison needs its own treatment definition and adequate independent transitions. |
| Executable RQ3 | Does control detect controlled degradation (precision, recall, F1, FPR/FNR, detection time)? | Not in DA01. | Construct controlled degradation cases, detection opportunities, reference events, and observation windows; preregister the detection unit and cost/latency measures. |
| Executable RQ4 / end-to-end continuity | What adaptation, CI, runtime, resource, telemetry, and active-check costs result; do controls remain useful across stages over time? | No population-level or runtime claim follows from DA01’s one architecture transition. | Add independently constructed transitions and approved CI/test, deployment, and runtime-stage contracts. A longitudinal study must define when evidence is collected, stage obligations, delays, and rollback/monitoring outcomes. |

**PROPOSED scope rule:** report DA01 only as a single-case RQ1/RQ2 comparison under the frozen operational definitions. Treat detection quality, lifecycle continuity, runtime benefit, and general overhead as future questions unless their own independently reviewed protocol and evidence are created.

## 3. B1 intervention alternatives (OPEN-01 / M-01)

The current `B1_CHECKLIST.md` is a procedure template for review after a particular architecture transition; it requires a real independent operator and records experience, prior exposure, inputs, tools, decisions, evidence, and time. It does not document a periodic-review implementation or an operator result. [SOURCE: `experiments/execution/da01/B1_CHECKLIST.md`, “Operator record” and “Decision procedure”; `docs/RESEARCH_CONTEXT.md`, M-01]

### Alternative A — periodic human review

- **Estimand — PROPOSED:** performance of a scheduled manual maintenance policy at architecture transitions encountered during the study, including the delay between a transition and the next scheduled review. It estimates the whole periodic policy, not only the reviewer’s decision quality once handed a change.
- **Treatment and timing — PROPOSED:** an independent reviewer examines the accumulated, authorized architecture and fitness evidence at a fixed, preregistered cadence. The review may occur after the transition or may be delayed. If the review is always scheduled immediately after a known transition, the treatment is effectively post-change rather than periodic.
- **Expertise and independence — SOURCE requirement:** recruit an actual architecture/fitness reviewer independent of P development and results; record relevant experience and prior exposure. No simulated or agent-generated human response qualifies.
- **Information exposure — PROPOSED control:** at each scheduled review, provide only the versioned common material available by that time. Record whether the reviewer could see the transition, prior reports, or unrelated changes. Keep the oracle, expected decisions, P output, and private reference results sealed.
- **Evaluator capability — SOURCE dependency:** B1 and P require the same demonstrably available, approved evaluator/template inventory unless a different capability is explicitly approved as part of the treatment. TEST_ONLY synthetic evaluators are not real comparator capability. OPEN-05 remains a prerequisite.
- **Time and measurement — PROPOSED:** predeclare review cadence, per-review and cumulative time cap, stopping/overrun rule, and which preparation/review steps count. Record active review time and calendar delay separately. **UNKNOWN:** an acceptable time/cost cap and cost comparison rule are not set.
- **Fairness relative to P — PROPOSED:** control common inputs, architecture/policy revisions, and evaluator availability; disclose that P alone receives the allowed traceability graph. P runs on the declared transition trigger while periodic B1 may be delayed, so latency and review workload belong to the estimand and must not be hidden as a matched “same-time” comparison.
- **Main validity threats:** cadence changes both opportunity and information; reviewers may know changes are imminent; unequally accumulated evidence, operator familiarity, or a delay that exposes later outcomes can bias the comparison. One DA01 transition cannot estimate recurring-review behavior.
- **Compatibility with DA01:** **not compatible with the existing checklist as written** and not identified by a single-transition case unless the cadence happens to be aligned, in which case it no longer tests a distinct periodic policy. Requires a separately reviewed intervention definition and likely a multi-transition study.

### Alternative B — immediate post-change human review

- **Estimand — PROPOSED:** performance of a transition-triggered manual adaptation after a defined architecture change, compared with frozen B0 and P on the same target architecture and post-change evaluation. It does not estimate periodic maintenance.
- **Treatment and timing — PROPOSED:** notify the reviewer at the preregistered point after the transition and give the same frozen before/after observations and common policy/evaluator bundle available to P. Fix the review window, deadline, and stop rule before the session.
- **Expertise and independence — SOURCE requirement:** an actual, competent operator independent of P development and its output; document architecture/fitness experience, prior exposure to this transition, and blind status. Do not let a reviewer learn the answer from a previous arm or reference scorer.
- **Information exposure — PROPOSED control:** the checklist’s allowed architecture observations, A0 representations, general obligation registry, and common evaluator inventory; no P traceability graph, P output, expected answer, private denominator, scorer, or other-method output. Hash the bundle and seal the human prediction before scoring.
- **Evaluator capability — SOURCE dependency:** make the same real, pinned capability inventory available to B1 and P. Verify artifact authority, semantic scope, target resolution, evidence contract, and non-vacuity; stop if capability parity cannot be established (OPEN-05).
- **Time and measurement — PROPOSED:** set a review time allowance and overrun policy before the run; record active wall time and checklist-step times. Record P’s diff, impact, decision, candidate, and validation times separately. Do not assume human minutes and CPU time are interchangeable or invent a zero human cost. B0 adaptation time remains zero by protocol definition.
- **Fairness relative to P — PROPOSED:** use identical architecture source revisions, common facts and policy bytes, parent configuration, approved evaluators, target revision, validity procedure, and scoring. Explicitly disclose P-only traceability as a treatment difference. Use the same deadline/stopping rule where that makes the intended comparison fair; measure modality-specific effort separately.
- **Main validity threats:** human expertise and prior exposure, expectancy, time pressure, evaluator availability, P-specific traceability, differences in permitted policy execution, and leakage across arms. A single reviewer/session does not estimate variability across operators.
- **Compatibility with DA01:** closest to the present `B1_CHECKLIST.md` and the one-transition RQ1/RQ2 case. This is **compatibility with the documented checklist template**, not an approved cadence or permission to execute; G1 and G4 remain separate gates.

### Alternative C — later multi-arm or cadence study

- **Estimand — PROPOSED:** estimate post-change human response, periodic human maintenance, and P separately; optionally estimate the causal effect of cadence (periodic versus transition-triggered) as a distinct contrast. Do not pool both B1 procedures into one “human baseline.”
- **Treatment and timing — PROPOSED:** predefine a post-change B1 arm and periodic B1 arm with distinct triggers, evidence cutoffs, deadlines, and follow-up windows. Pair both with B0 and P on independently constructed transitions; allocate reviewers/transitions with a design that prevents carry-over and answer sharing.
- **Expertise and independence — PROPOSED:** recruit multiple qualified, independent reviewers or assign reviewers to transitions under a preregistered crossed/nested allocation. Record participant and transition clustering; counterbalance only where learning cannot leak answers into later tasks.
- **Information and capabilities — PROPOSED:** version common information at each decision time; record cadence-specific accumulated evidence. Keep P-only traceability visible as a treatment feature, and provide the same approved evaluator capabilities to both human arms and P unless capability differences are themselves the question.
- **Time, cost, and fairness — PROPOSED:** predeclare both per-review and total study effort rules; report human active time, elapsed response delay, and P computation/validation separately. A multi-arm design can distinguish effectiveness from latency/workload trade-offs but cannot erase their different units.
- **Main validity threats:** operator learning/carry-over, contamination among arms, calendar/time trends, transition difficulty imbalance, unequal evidence windows, participant clustering, and insufficient independent transitions.
- **Compatibility with DA01:** not a DA01 execution amendment. It is the stronger future design if the dissertation needs both the periodic manuscript comparator and an immediate-response comparison.

### Conditional recommendation for DA01

**PROPOSED:** if independent reviewers select one human comparator for the next DA01 package, use the **post-change checklist procedure**, because it is the existing documented intervention and DA01 contains one defined transition. Constrain the claim to “transition-triggered manual response versus P,” not “periodic review versus P.” Before any measured comparison, G1 reviewers must approve the trigger/window, time allowance and overrun rule, operator independence and exposure record, input/capability parity, and candidate sealing. If the dissertation claim must remain specifically periodic, defer B1 effectiveness claims to Alternative C rather than relabeling the existing checklist. `OPEN-01` remains `PENDING_INDEPENDENT_REVIEW`; this is not a decision on the reviewer’s behalf.

## 4. Candidate hypotheses and endpoint hierarchy (OPEN-02 / M-02)

All hypotheses and hierarchy below are **PROPOSED**. They preserve the frozen estimands; values not in source contracts remain `UNKNOWN` / `TBD_PRE_REGISTRATION`.

### RQ1 — affected-target identification and operation selection

**SOURCE definitions:** target identity is `(target_type, target_id)`. The scorer reports `TP`, `FP_in`, `FP_extra`, `FN`, and `TN`; `FP_total = FP_in + FP_extra` is used for precision and F1, and `TN` counts only in-universe negatives. Precision, recall, and F1 use the pinned full target universe. When oracle positives exist and no positive is predicted, all three metrics are zero; when both positive sets are empty in a synthetic negative control, all three are `null` and correct-empty-set detection is reported separately. Operation accuracy uses normalized decisions over the complete oracle universe; omitted existing representations become `implicit_retain`, and omitted obligation targets normalize to scorer-only `missing_add`, never an emitted operation. Unknown target IDs remain visible and cause `UNKNOWN_TARGET` / `PROTOCOL_VIOLATION`. These private scoring inputs remain outside all method bundles. [SOURCE: `experiments/execution/da01/PROTOCOL.md`, “RQ1 scoring”; `experiments/execution/da01/SCORE_RULES.md`, “RQ1 impact and operations”]

**PROPOSED primary endpoint:** transition-level affected-target **F1**, with precision and recall reported alongside it as component outcomes. F1 alone does not hide the false-positive and false-negative counts; always report the underlying counts and protocol status.
**PROPOSED secondary endpoint:** normalized operation-selection accuracy over the complete scoring universe.
**Diagnostics:** `TP`, `FP_in`, `FP_extra`, `FN`, `TN`, `FP_total`, predicted-positive count, unknown-target and protocol-violation flags, per-target decisions after independent scoring, and correct-empty-set status. Do not interpret diagnostic rows as independent samples.

### RQ2 — independently verified mandatory coverage

**SOURCE definition:** each obligation in the complete private post-change required set counts once if at least one active representation has both valid evaluator-execution evidence and a versioned, valid semantic/evidence verdict for that exact `(representation_id, obligation_id)` pair at the target architecture SHA. A `covers` field or general verdict is insufficient; duplicate controls do not add weight; a representation covering several obligations needs a valid separate pair for each. Missing exact-pair evidence is not covered. `Coverage_before` evaluates unchanged A0 against the target architecture; `Coverage_after` evaluates each candidate against that same target and the complete private denominator. The denominator and answer pairs are not method inputs. [SOURCE: `experiments/execution/da01/PROTOCOL.md`, “RQ2 scoring”; `experiments/execution/da01/SCORE_RULES.md`, “RQ2 obligation coverage”; `experiments/execution/da01/VALIDITY_RULES.md`, “Obligation-specific validity”]

**PROPOSED primary endpoint:** transition-level valid mandatory coverage, reported as covered obligations divided by the same full denominator. For `P − B0`, compare `Coverage_after(P)` with the unchanged A0/B0 coverage assessed on the target (the protocol’s `Coverage_before`). For `P − B1`, compare `Coverage_after(P)` with `Coverage_after(B1)` under the same target and denominator.
**PROPOSED secondary endpoints:** candidate-minus-baseline coverage change; per-obligation coverage status; number and identity of valid exact pairs; representation execution validity; and the existing representation-level semantic-violation measure, reported only with its unchanged denominator.
**Diagnostics:** exact pair statuses/reasons and evidence references, missing/vacuous/stale scope, evaluator or infrastructure failures, unresolved applicability, candidate governance status, and any protocol violation. Pair failure and representation invalidity remain distinct.

### Candidate H0/H1 formulations for separate contrasts

Let `c ∈ {B0, B1}` and let `j` index independently constructed architecture transitions in a future study. For endpoint `e ∈ {RQ1 F1, RQ2 valid mandatory coverage}`, define the within-transition difference `d[c,e,j] = Y[P,e,j] − Y[c,e,j]`. Let `μ[c,e]` be the prespecified transition-population mean (or other explicitly chosen aggregate estimand) of these paired differences, and let `δ[e]` be the independently chosen minimum important improvement on that endpoint’s scale.

For **each** comparator and each selected primary endpoint, the candidate directional formulation is:

- `H0[c,e]: μ[c,e] ≤ δ[e]` — P does not exceed the preregistered minimum important improvement over comparator `c`.
- `H1[c,e]: μ[c,e] > δ[e]` — P exceeds that minimum important improvement over comparator `c`.

Thus the design contains separate P-versus-B0 and P-versus-B1 hypotheses; it does not pool the baselines. `δ[e]`, whether a zero-margin superiority test is appropriate, the primary aggregate estimand, and the analysis procedure are `UNKNOWN` / `TBD_PRE_REGISTRATION`. Do not choose a numeric value from this brief. A confirmatory claim also requires the prespecified cost rule to pass; absent an acceptable-cost rule, claim only the endpoint contrast, not “improvement without unacceptable overhead.”

For DA01 alone, there is one `j`. Report `d[c,e,1]`, the case values, denominators, and evidence as descriptive results only if a later authorized run occurs. Do not estimate a transition-population mean, test these hypotheses, or report a p-value from that single case.

### Primary, secondary, diagnostic, and exploratory outcomes

| Class | Candidate outcomes | Boundary |
| --- | --- | --- |
| **Primary (PROPOSED)** | RQ1 affected-target F1; RQ2 valid mandatory coverage; each contrasted separately against B0 and B1. | Reviewers must decide whether these are co-primary, a hierarchy, or one primary family. Freeze effect scale, `δ`, multiplicity, and failure rules before outcomes. |
| **Secondary (PROPOSED)** | RQ1 precision, recall, and operation accuracy; RQ2 candidate-minus-baseline coverage, exact-pair completeness/status, and existing semantic-violation reporting. | Report all named outcomes; do not promote a favorable secondary to primary after seeing results. |
| **Diagnostics (SOURCE plus reporting proposal)** | Confusion counts; unknown/protocol violations; pair-level evidence and reason codes; execution, vacuity, missing scope, `HOLD`/`REJECT`, infrastructure, checker, and scoring statuses. | Preserve the frozen result semantics. Missing exact pairs remain uncovered. Do not collapse diagnostic categories or treat rows as independent replicates. |
| **Exploratory / later study (PROPOSED)** | Adaptation/CI/runtime cost; resource and telemetry use; controlled-degradation detection (F1/FPR/FNR/detection time); longitudinal stage continuity; α/θ changes. | DA01 does not establish these broader outcomes. Define separate interventions, stage contracts, measures, and authority before testing. α/θ is outside core P v1 (OPEN-10/M-05). |

## 5. Statistical plan for DA01 and a later transition study

### Independent unit and DA01 limit

**SOURCE:** one independently constructed architecture transition is the unit of analysis. The one DA01 transition supports a case description, not population-level statistical significance. Targets, obligations, representation–obligation pairs, requests, evaluator invocations, log rows, time samples, and repeated runs of the same transition are correlated/nested observations, not independent architecture trials. [SOURCE: `experiments/execution/da01/PROTOCOL.md`, “Research scope”; `docs/EXPERIMENT.md`, “Experimental subject and research questions”]

**PROPOSED DA01 reporting:** for each method, report the frozen metric values, exact scorer denominator/counts, coverage denominator and evidence trace, statuses/failures, and transition identity. Report paired case differences only as descriptive quantities. No target-level tests, confidence claims, p-values, power claims, or generalization statements.

### Later multi-transition design

1. **Construct independent transitions.** Develop and freeze distinct architecture deltas before method outputs are generated. Keep each transition’s answer key/reference evaluation under independent custody. Sample or purposively cover a declared range of architecture styles, obligation families, evaluator kinds, and change types; disclose the sampling frame and limits. A software-system/project reused across multiple transitions creates clustering and must not be called independent without an explicit model.
2. **Pair all arms within transition.** For each transition, apply the same B0 parent, B1 procedure, and frozen P version to identical architecture revisions, common evidence, policy bytes, target, evaluator inventory, and independent scoring. Compute P−B0 and P−B1 differences within each transition. Keep post-change and periodic B1 as separate arms if both are included.
3. **Control human dependence.** Assign independent qualified reviewers to transitions using a preregistered crossed or nested allocation. Avoid exposing one reviewer to reference answers or P output before later assignments; counterbalance only when carry-over is controlled. Model participant effects if multiple reviews per transition are collected. Operator repeats do not increase the number of independent architecture transitions.
4. **Respect within-transition dependence.** First calculate each transition-level endpoint using its frozen target/obligation universe and exact denominators. Do not pool targets or obligation pairs across transitions as if independent. The primary estimand may be an equally weighted mean of paired transition-level differences (macro-average), so large scenarios do not dominate; alternatives such as a median paired difference or probability of a positive transition effect require advance choice. Report each transition’s values and difference alongside any aggregate.
5. **Uncertainty and analysis options.** After the design is fixed, report effect estimates and uncertainty intervals over independent transitions. Candidate methods include paired randomization/permutation or sign-based procedures when assignment/design justifies them; a paired parametric analysis only when its assumptions and sample adequacy are supported; or a hierarchical model when multiple transitions, operators, and repeated measurements create modeled clustering. A cluster bootstrap must resample transitions, not target rows. These are options, not selected tests; the statistician must select and justify one before outcomes.
6. **Repeated execution.** Repeated P execution can verify determinism or estimate run-to-run/measurement variability. Repeated human execution can estimate operator variability only under an allocation that limits learning and is modeled as clustered. Neither kind of repetition creates a new transition-level sample.
7. **Power/sample-size prerequisites.** Before selecting a sample size, reviewers need a minimum important effect for each primary endpoint, an estimate or defensible range for between-transition variance and endpoint covariance, the chosen paired estimand/test, desired error rate and power, multiplicity strategy, expected missingness/attrition, human-operator allocation, and any cost non-inferiority bound. A prospective sensitivity or simulation analysis may then be appropriate. These inputs and the resulting sample size/power are currently `UNKNOWN`; none is inferred from the single DA01 case.

### Missingness, ties, multiplicity, and acceptable cost

- **Missingness/failure — SOURCE plus unresolved aggregation:** frozen scoring does not post-hoc drop or impute; missing pair evidence is not covered, and method, infrastructure, protocol, checker, and scoring failures retain distinct statuses. Exact comparative treatment for some failures remains unresolved. **PROPOSED:** define in advance which events make an endpoint unscorable, retain every assigned transition and failure status in the study flow, never convert a failure/`HOLD`/`UNKNOWN` into a favorable score, and predefine sensitivity/aggregation rules with the independent scorer. Any rule not already fixed by the contract remains `PENDING_INDEPENDENT_REVIEW`.
- **Ties — UNKNOWN pending review:** no rule for inferential ties is frozen here. **PROPOSED:** retain unrounded endpoint values and paired differences; an exact zero difference is reported as a tie, not as a P win; the test’s boundary equality remains in `H0` as written. Operation conflicts/duplicate decisions continue to follow the frozen prediction-validation rules. Reviewers must decide if an alternative tie rule is needed.
- **Multiplicity — UNKNOWN pending review:** two candidate primary endpoints and two separate contrasts yield multiple confirmatory claims. **PROPOSED options:** define a single hierarchical decision sequence or control the family of primary tests using an independently selected procedure (for example, Holm). Label secondary analyses and exploratory outcomes explicitly. Do not select whichever endpoint/comparator is favorable after results.
- **Minimum effects and cost — UNKNOWN:** no minimum important effect, equivalence/non-inferiority margin, acceptable adaptation-cost bound, or common cost unit is supplied. The B0 zero adaptation-time convention does not settle human-vs-compute cost or monitoring cost. Before an “improvement without unacceptable overhead” claim, preregister the cost components, measurement environment, budget/overrun behavior, and acceptance threshold; otherwise report cost measures descriptively and keep the joint claim open (OPEN-06).

## 6. Compatibility with frozen DA01 and limits

| Contract | Compatibility assessment |
| --- | --- |
| RQ identity | Preserve manuscript RQ1–RQ4 separately from executable RQ1–RQ4. This brief records their mismatch; it does not renumber either system. |
| RQ1 | Use the frozen typed identity, confusion counts, `FP_total`, normalized operation universe, empty-positive conventions, unknown-target diagnostic, and protocol-violation behavior exactly. No private answer material is exposed to a method. |
| RQ2 | Use the complete private post-change obligation set with equal weights, one count per obligation, valid execution plus valid exact-pair evidence, and the existing coverage-before/after definitions. Do not change the denominator or infer coverage from a `covers` field. |
| B1 | The present checklist describes a human reviewing a specific before/after transition. A post-change design is nearest to it; periodic review would require a distinct cadence treatment. The checklist has no recorded operator session and is not itself a protocol approval. |
| Unit/statistics | Keep DA01 to descriptive case evidence. Do not use repeated observations as independent units or claim significance. |
| Authorization and method readiness | The readiness report says G1 is incomplete and G4 is not authorized. This proposal changes neither status and authorizes no measurement. |

The research-context manuscript RQ mapping, the protocol’s readiness narrative, and implementation-status narratives can describe different dates and scopes. Where a current normative score or validity rule governs DA01, use that source; document narrative discrepancies for review rather than silently reconciling them. The protocol’s RQ1/RQ2 scoring remains the operational source for this proposal.

## 7. Main validity threats

- **Construct validity:** affected-target F1 is only one part of architectural-control quality; coverage can be inflated by vacuous, stale, or semantically irrelevant evaluators. Preserve exact-pair validity, evidence adequacy, and target resolution.
- **Comparator validity:** periodic and post-change B1 are different treatments. Human expertise, prior exposure, P-only traceability, common-policy execution, time allowance, and evaluator capability can change the contrast.
- **Internal validity:** mismatched architecture/policy revisions, incomplete or untrusted authority, unequal artifact availability, reviewer learning, time pressure, and unbalanced scenario difficulty can confound results.
- **Scoring validity:** the independent scorer and validity evidence are distinct from method predictions. Missing evidence, UNKNOWN applicability, protocol violations, and checker failure must not be silently dropped. OPEN-07/08 remain unresolved against frozen semantics.
- **Statistical conclusion validity:** DA01 has one independent unit. Treating targets, obligations, pairs, repeated runs, or request samples as independent would be pseudoreplication. Multiplicity, ties, missingness, sample size, and cost acceptance are not yet fixed.
- **External/ecological validity:** current DA01 does not span the planned transition set, cloud deployment styles, operational degradation, lifecycle stages, or production-trust conditions. An experimental method result would be bounded by the sampled systems, obligations, evaluator inventory, and authority model.
- **Researcher/holdout independence:** method authors’ access to expected answers or reference outputs risks tuning to the case. Keep generic P frozen before predictions; isolate oracle/scorer and seal prediction bytes before independent evaluation (OPEN-09).

## 8. Dependencies on OPEN-03…OPEN-09

These dependencies are not resolved by this workstream. Statuses match the current decision docket; OPEN-01/02 remain `PENDING_INDEPENDENT_REVIEW`.

| Decision | Dependency for this design | Current disposition |
| --- | --- | --- |
| OPEN-03 / M-04 | Later multi-stage obligation registry may change future coverage constructs. Do not retrofit stage requirements into DA01’s frozen RQ2 denominator. | `PROPOSED` deferred boundary; independent stage design remains open. |
| OPEN-04 | Authentic policy authority, trust anchors, registry/charter scope, and completeness evidence underlie what counts as a required obligation. | `PENDING_EXTERNAL_AUTHORITY`; insufficient proof remains `UNKNOWN`. |
| OPEN-05 / M-03 | Real approved evaluators/templates and fair B1/P capability parity are prerequisites; P-only rule execution versus shared readable policy material affects the treatment. | `PENDING_EXTERNAL_AUTHORITY` / independent fairness decision pending. |
| OPEN-06 | Defines cost units, P search/budget bounds, tie/collision behavior, overruns, and acceptable cost; needed for the joint benefit-without-unacceptable-overhead claim and sample-size plan. | `PENDING_INDEPENDENT_REVIEW`; numerical values are `UNKNOWN`. |
| OPEN-07 | Architecture non-compliance and invalid/unavailable monitoring may map differently under current reference verdict semantics. | `PENDING_INDEPENDENT_REVIEW`; keep compliance and monitor validity separate. |
| OPEN-08 | Multi-obligation ADD may not map directly to the frozen single-target operation identity. | `PENDING_INDEPENDENT_REVIEW`; no reinterpretation of DA01 operation accuracy. |
| OPEN-09 | Independent algorithm freeze, holdout custody, no-leakage review, and external sealing are necessary before predictions and scoring. | `PENDING_INDEPENDENT_REVIEW`; no prediction or seal is created here. |

OPEN-10/M-05 is a related scope limit: α/θ adaptation is deferred and not part of the proposed DA01 endpoints.

## 9. Decisions requested from independent reviewers

1. **OPEN-01 / M-01:** Is the DA01 comparator post-change as in the checklist, or is a future periodic arm required for the dissertation claim? Specify trigger, evidence cutoff, review window, time budget, overrun rule, operator experience/independence, and prior-exposure treatment.
2. **OPEN-02 / M-02:** Approve or revise the manuscript-to-executable RQ crosswalk while preserving both source label systems in the record. Define whether a separate ablation is needed for “formal impact analysis plus validation versus heuristic review.”
3. **OPEN-02 / M-06:** Select primary endpoint hierarchy (including whether RQ1 F1 and RQ2 coverage are co-primary), P-versus-B0 and P-versus-B1 estimands, minimum important effects, multiplicity procedure, tie and missingness rules, acceptable-cost claim, and the future independent-unit design.
4. **Statistical review:** Before a later multi-transition study, select the paired aggregate estimand and analysis/uncertainty method, justify independent transition construction and human allocation, and calculate sample size only after effect, variability, error-rate, power, multiplicity, and missingness assumptions are available.
5. Confirm the study remains within frozen DA01 scoring/isolation contracts and that no decision in this brief advances G1 or G4.

## 10. Source index

- [`docs/RESEARCH_CONTEXT.md`](../../RESEARCH_CONTEXT.md) — scientific problem/model; manuscript-versus-executable RQ crosswalk; M-01…M-06; validity and unit-of-analysis limits.
- [`docs/EXPERIMENT.md`](../../EXPERIMENT.md) — executable experiment RQ1–RQ4 descriptions, DA01’s RQ1/RQ2 limit, comparison methods, and authorization boundary.
- [`docs/G1_METHOD_SPECIFICATION.md`](../../G1_METHOD_SPECIFICATION.md) — proposed method model, contribution boundary, and unresolved decisions; not independent approval.
- [`docs/DA01_PREREGISTRATION_DRAFT.md`](../../DA01_PREREGISTRATION_DRAFT.md) — current candidate RQ/endpoint and failure-handling proposal; not a canonical preregistration.
- [`docs/B1_P_COMPARABILITY_PLAN.md`](../../B1_P_COMPARABILITY_PLAN.md) — common/method-specific inputs, cadence alternatives, evaluator and time comparability.
- [`docs/G1_METHOD_DECISION_REGISTER.md`](../../G1_METHOD_DECISION_REGISTER.md) — OPEN-01…OPEN-10 status and independent decision requirements.
- [`docs/G1_REVIEW_CHECKLIST.md`](../../G1_REVIEW_CHECKLIST.md) — G1/G4 and reviewer-lane status.
- [`docs/SPEC_G1_METHODOLOGICAL_FREEZE_PREPARATION.md`](../../SPEC_G1_METHODOLOGICAL_FREEZE_PREPARATION.md) — preparation scope, read-first precedence, and research-integrity boundaries.
- [`experiments/execution/da01/PROTOCOL.md`](../../../experiments/execution/da01/PROTOCOL.md) — version 1.0.0 DA01 method contracts, RQ1/RQ2 operational rules, units, timing, sealing, and stop boundary.
- [`experiments/execution/da01/SCORE_RULES.md`](../../../experiments/execution/da01/SCORE_RULES.md) — exact target metrics, empty-set conventions, operation accuracy, and RQ2 coverage denominator/pairs.
- [`experiments/execution/da01/VALIDITY_RULES.md`](../../../experiments/execution/da01/VALIDITY_RULES.md) — evaluator validity, exact-pair semantic/evidence contract, and non-vacuity.
- [`experiments/execution/da01/B1_CHECKLIST.md`](../../../experiments/execution/da01/B1_CHECKLIST.md) — post-change human procedure template and operator/exposure/time record.
- [`experiments/execution/da01/INPUT_ISOLATION.md`](../../../experiments/execution/da01/INPUT_ISOLATION.md) — method-input allowlists, execution boundary, and oracle/history/network isolation.
- [`experiments/execution/da01/READINESS.md`](../../../experiments/execution/da01/READINESS.md) — recorded G0–G4 status, measured-readiness limits, and no-human/no-outcome boundary.
