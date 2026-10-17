# DA01 preregistration — review draft

**DRAFT — NOT INDEPENDENTLY APPROVED**

**Review source revision:** prepared branch commit 02c1654f457fd1cf685fd449b552d6e35701ea54, based on main at 740c60aeece6e424c56ba081eacc079dc0f16d74 (PR #10 merged).
**Status:** proposed pre-outcome design for independent review. No DA01 prediction, B1 session, score, outcome, or authorization is recorded here.
**Proposed reviewers:** independent experimental-methods reviewer; statistician; holdout/data custodian.

## 1. Scope and authority

This draft prepares the existing DA01 executable RQ1/RQ2 procedure for review. The frozen [DA01 protocol](../experiments/execution/da01/PROTOCOL.md), [score rules](../experiments/execution/da01/SCORE_RULES.md), and [validity rules](../experiments/execution/da01/VALIDITY_RULES.md) control current operational definitions. This draft does not amend them, set G1, authorize a run, or claim an effect.

DA01 is one independently designed architecture transition. It supports descriptive case reporting only. Requests, evaluator invocations, obligations, pair rows, and repeated measurements of this same transition are not independent architecture trials. DA01 cannot by itself establish population significance, cloud/runtime benefit, or generalization.

## 2. Manuscript and executable RQ crosswalk

Keep the two numbering systems distinct pending OPEN-02/M-02. The manuscript asks broader scientific questions; the executable DA01 protocol has narrower observables.

| Label | Manuscript scientific question | Executable experiment question | Status |
| --- | --- | --- | --- |
| RQ1 | Does governed adaptation improve architectural-control quality over a frozen and periodic heuristic baseline? | Accuracy of affected-target identification and operation selection | Not equivalent; target accuracy is one outcome, not the whole manuscript claim |
| RQ2 | Does adapting representations, metrics, execution policies, weights, and thresholds improve coverage and consistency? | Independently evidenced post-change obligation coverage and exact-pair semantic validity | Weights, thresholds, and lifecycle-wide stages are not evaluated by DA01 |
| RQ3 | What operational cost does governed adaptation add? | Detection quality under controlled degradation, including F1/FPR/FNR and detection time | Different constructs |
| RQ4 | Does formal impact analysis plus validation outperform periodic heuristic review? | Runtime/CI/adaptation overhead | Different constructs; manuscript RQ4 needs an explicit comparator/possibly ablation |

The manuscript/executable RQ3 and RQ4 mapping remains unresolved. No numbering is renamed or reconciled here. See [RESEARCH_CONTEXT M-02](RESEARCH_CONTEXT.md#10-open-methodological-discrepancies--do-not-silently-choose).

## 3. DA01 operational estimands and endpoint candidates

All endpoint hierarchy and hypotheses below are proposals. A reviewer must choose and freeze primary versus secondary endpoints, multiplicity handling, estimands, and missing-data rules before any outcome is available.

### Executable RQ1 — affected targets and operations

The target identity is the typed pair **(target_type, target_id)**. The independent scorer reconstructs the target universe from protected oracle material; that universe and answer key are not method inputs. Positive means the oracle operation is not retain.

For each method, report TP, FP_in, FP_extra, FN, TN and FP_total = FP_in + FP_extra. TN covers only in-universe negatives. Candidate metrics are:

    precision = TP / (TP + FP_total)
    recall    = TP / (TP + FN)
    F1        = 2 TP / (2 TP + FP_total + FN)

The frozen empty-set convention applies: if the oracle has positive targets but the method predicts none, precision, recall, and F1 are zero. If both positive sets are empty in a synthetic negative control, all three are null and correct-empty-set detection is reported separately. A known out-of-universe target is FP_extra; an unknown target is also flagged UNKNOWN_TARGET and propagates PROTOCOL_VIOLATION. Operation accuracy compares scorer-normalized decisions over the complete oracle universe. Omitted existing representations normalize to implicit_retain; scorer-only missing_add for omitted obligation targets is never a valid emitted operation.

Candidate primary endpoint family: typed affected-target precision/recall/F1. Candidate secondary endpoint: operation-selection accuracy. Whether F1 or another member is the single primary endpoint is TBD_PRE_REGISTRATION.

### Executable RQ2 — valid mandatory coverage

Coverage_before evaluates the unchanged A0 configuration against the target architecture. Coverage_after evaluates the candidate against that same target architecture. Both use the same complete, private post-change required-obligation denominator and equal obligation weights. The denominator is not exported to B1 or P.

An obligation counts once only if an active representation has both a valid evaluator-execution verdict and a valid versioned semantic/evidence verdict for that exact **(representation_id, obligation_id)** pair. The pair must match the target architecture SHA, establish semantic match, adequate evidence-contract coverage, and cite evidence. A covers field or general representation verdict is insufficient. Missing pairs remain uncovered; duplicate valid controls do not multiply coverage; one representation can support several obligations only with separate valid pair verdicts.

Candidate primary endpoint: valid post-change mandatory coverage, with Coverage_before as the frozen comparator baseline and Coverage_after as candidate outcome. Candidate secondary descriptions: per-obligation pair status, execution invalidity, and separately reported semantic-violation measures under the unchanged protocol. Pair failures do not silently change the protocol’s existing representation-level semantic-violation denominator.

## 4. Candidate hypotheses and contrasts

The alternatives below are candidate one-sided hypotheses about beneficial direction, not accepted hypotheses. The contrasts are separate; B0 and B1 are not pooled.

| Outcome family | Contrast | Candidate H0 | Candidate H1 / beneficial direction | Scale and denominator |
| --- | --- | --- | --- | --- |
| RQ1 target identification | P minus B0 | P does not improve the selected target metric | P improves the preregistered target metric | Precision/recall/F1 on the scorer’s complete typed target universe |
| RQ1 target identification | P minus B1 | P does not improve the selected target metric | P improves the preregistered target metric | Same target universe and scoring rules |
| RQ1 operation selection | P minus B0 | P does not improve operation accuracy | P improves operation accuracy | Correct normalized operations divided by the complete oracle target universe |
| RQ1 operation selection | P minus B1 | P does not improve operation accuracy | P improves operation accuracy | Same operation universe and normalization |
| RQ2 coverage | P candidate minus unchanged B0 | P does not improve valid mandatory coverage | P improves valid mandatory coverage | Covered obligations divided by the same complete private required set |
| RQ2 coverage | P candidate minus B1 candidate | P does not improve valid mandatory coverage | P improves valid mandatory coverage | Same denominator and independently checked exact-pair rule |

The numerical superiority margin, choice of primary member within each family, treatment of ties, multiplicity correction, equivalence/noninferiority alternative, and acceptable overhead are TBD_PRE_REGISTRATION and PENDING_INDEPENDENT_REVIEW. No threshold, sample size, p-value, confidence interval, power estimate, or effect is supplied by this draft.

## 5. Abstention, evidence, and failure treatment

Do not collapse method decision status, evaluator execution, infrastructure, protocol validity, or independent scoring into one success/failure field. The frozen scorer performs no post-hoc dropping or imputation. The mapping of some method failures to a comparative estimand remains an independent-review decision; retain raw status and reason codes.

| Event/status | Required record and RQ2 consequence | Comparative handling |
| --- | --- | --- |
| INPUT_REJECTED | Record invalid method input and reason; no positive coverage claim | Retain as a protocol/method outcome; exact aggregation rule PENDING_INDEPENDENT_REVIEW |
| HOLD | Record abstention, blockers, and unresolved obligations | Do not call it ACCEPT or infer coverage; denominator remains fixed |
| Candidate REJECT | Preserve the proven hard failure and candidate status | Do not relabel as infrastructure failure or remove post hoc |
| UNKNOWN applicability | Record policy/fact/completeness references and scope; do not convert to INACTIVE | An unresolved mandatory obligation cannot be silently dropped; reviewer must approve exact scoring treatment |
| Missing exact pair | Record MISSING_EVIDENCE and pair identity | Pair is not covered under frozen RQ2 |
| Vacuous success | Record target-resolution/inspection evidence and VACUOUS_SUCCESS | Does not establish valid execution or coverage |
| Architecture/compliance violation | Preserve the observed violation separately from monitor validity | OPEN-07 requires review against frozen reference verdict semantics |
| Evaluator execution failure | Preserve exit/error and artifact/evidence identity | No valid coverage; distinguish from infrastructure failure |
| Infrastructure failure | Preserve environment, stage, and failure evidence | Do not score as a semantic pass; treatment in the estimand remains PENDING_INDEPENDENT_REVIEW |
| Protocol violation / unknown target | Preserve diagnostic and derived protocol status | Do not suppress or normalize away the violation |
| Reference-checker error | Preserve independent checker error and affected evidence | Not a method success or method failure; run validity/aggregation rule PENDING_INDEPENDENT_REVIEW |
| Scoring failure | Preserve the failure and prohibit derived metric claims | No imputation or reconstructed score |

The frozen RQ2 rule that missing pair evidence is not covered remains in force. When this draft identifies a treatment not fixed by the existing protocol, it explicitly leaves that choice pending review rather than inventing a denominator or penalty.

## 6. Independent units and statistical plan

The architecture transition is the independent unit. DA01 has one such unit, so all DA01 outcomes must be presented descriptively with the exact case, denominator, evidence coverage, and limitations. Do not run target-level significance tests or treat requests, obligations, representation pairs, log rows, or reruns as independent transitions.

For a later study with separately designed transitions, a candidate analysis is to compute paired method contrasts within each transition, report per-transition values and a predeclared aggregate estimand, and use uncertainty intervals only after the number and design of independent transitions, dependence structure, missingness, and multiplicity procedure are fixed. Choose a statistical test only after the independent-unit design and hypotheses are approved. Repeated runs can characterize measurement variability but do not create new architecture units. Sample size, power, confidence level, test, interval method, effect benchmark, and overhead ceiling are all TBD_PRE_REGISTRATION.

## 7. Comparator and data-custody conditions

The [comparability plan](B1_P_COMPARABILITY_PLAN.md) is part of this preregistration package. Before a measured run, freeze architecture source revisions, common inputs, evaluator capability inventory, policy/ruleset versions, allowed P-only traceability, timing/cadence, human independence, and candidate-verification procedures.

Preregister and preserve the method version, input hashes, source revisions, allowed file roles, environment, adaptation-time fields, decision reasons, candidate/evaluator hashes, deviations, and failure statuses. Independent custody must keep ground truth, expected operations, reference scoring, sealed outputs, and holdout material outside the method-authoring and method-execution inputs. Freeze generic P and decision rules before predictions. Seal each prediction once with exact bytes before independent scoring. The scorer consumes sealed predictions only after method output is fixed.

The permitted [input-isolation contract](../experiments/execution/da01/INPUT_ISOLATION.md) excludes scenario answers, private reference rules, engineering acceptance, Git metadata/history/remotes, network access, and other methods’ outputs. No actual prediction or seal is created by this draft.

## 8. Validity threats and limitations

- **Construct validity:** a wrong or vacuous evaluator, stale scope, missing pair evidence, or incomplete authority can inflate claimed control.
- **Internal validity:** policy changes, unequal evaluator artifacts, different time budgets, or inconsistent target revisions can confound the method contrast.
- **Comparator validity:** periodic and post-change B1 are different interventions; OPEN-01/M-01 remains unresolved. No human B1 participant is represented.
- **Scoring validity:** OPEN-07 and OPEN-08 affect compliance/monitor interpretation and multi-obligation ADD identity. Frozen score and validity semantics are not changed here.
- **Statistical conclusion validity:** one transition cannot support population inference; no target-level pseudoreplication.
- **External validity:** the controlled benchmark, current obligation/fact vocabulary, and synthetic evaluator artifacts do not establish cross-stack or production behavior.
- **Holdout independence:** method-author access to expected answers risks overfitting; OPEN-09 requires independent custody and review.

## 9. Decisions required before G1/G4

OPEN-01/M-01: B1 periodic versus post-change cadence, intervention, time budget, and exposure.

OPEN-02/M-02/M-06: manuscript/executable RQ mapping, primary endpoints, estimands, hypotheses, multiplicity, and future multi-transition analysis.

OPEN-03/M-04: later lifecycle-stage obligations without changing DA01’s frozen denominator.

OPEN-04/05: production policy/evaluator authority, completeness proof, and B1/P capability parity.

OPEN-06: cost units, search bound, budget handling, and tie rules.

OPEN-07/08: compliance versus monitor-invalidity mapping and multi-obligation ADD compatibility with frozen scoring.

OPEN-09: independent algorithm freeze, holdout custody, and sealing separation.

OPEN-10/M-05: α/θ adaptation is deferred to a separate study and is not a DA01 claim.

Approval and authorization remain separate: independent G1 review/freeze first, then a distinct human G4 authorization after all required readiness evidence. Current [READINESS](../experiments/execution/da01/READINESS.md) remains authoritative for gate status.
