# G1 independent review checklist — review draft

**DRAFT — NOT INDEPENDENTLY APPROVED**

**Review source revision:** prepared branch commit 02c1654f457fd1cf685fd449b552d6e35701ea54, based on main at 740c60aeece6e424c56ba081eacc079dc0f16d74 (PR #10 merged).
**Packet status:** PACKET_READY_FOR_REVIEW after local documentation verification; this status is not G1_PASS, P_READY, or G4 authorization.
**Approval fields:** intentionally blank pending authentic independent review.

## 1. How to use this checklist

Reviewers should record evidence and limitations, decide the open questions assigned to their role, and state whether a claim is supported, unsupported, or needs revision. A document link or passing test is not independent scientific approval. Do not fill an approval field for another reviewer or infer institutional authority.

Use the [G1 integration decision matrix](g1/G1_INTEGRATION_DECISION_MATRIX.md) as the consolidated source crosswalk and proposal index. It does not replace this checklist or the frozen DA01 contracts, and it does not close any OPEN item.

Permitted review outcomes include **NOT_REVIEWED**, **EVIDENCE_INCOMPLETE**, **PENDING_INDEPENDENT_REVIEW**, **PENDING_EXTERNAL_AUTHORITY**, **PROPOSED**, and **DEFERRED_WITH_LIMITATION**. **APPROVED** is a future template state only and is not used in this package.

## 2. Gate summary

| Gate | Current repository record | What remains |
| --- | --- | --- |
| G0 — architecture/input freeze | PASS for recorded Phase A inputs in [READINESS](../experiments/execution/da01/READINESS.md) | A changed-path review for this documentation package is not an independent byte-parity re-export |
| G1 — method/protocol freeze | INCOMPLETE | Independent review of the method, RQ/endpoints, B1 cadence, unresolved decisions, and an authentic freeze record |
| G2 — isolation audit | Phase A and PR #11 current-branch DEVELOPMENT synthetic probes PASS locally; measured-environment audit remains pending. | [READINESS](../experiments/execution/da01/READINESS.md) records the historical CI probe SKIPPED. At PR #11 head `b2a6a8d`, direct execution of the selected synthetic test passed (`1 passed in 4.53s`, digest-pinned image); push and PR `make development-quality` also passed, but their `200 passed, 1 skipped` aggregate does not identify the selected test's individual CI result. Independently validate the selected measured environment and exact deployed runtime before a later run. |
| G3 — synthetic rehearsal | Engineering-only PASS for recorded tests; PR #10 has TEST_ONLY no-op and ADD ACCEPT cases | This is synthetic DEVELOPMENT evidence, not production authority, independent review, or an outcome |
| G4 — measured-run authorization | NOT AUTHORIZED | Separate explicit human authorization after G1 and required prerequisites |

The measured interface remains **P_ALGORITHM_STATUS = NOT_READY**. A documentation packet may be ready for reviewers while all measurement gates remain unchanged.

## 3. Independent review lanes

For each line, fill the blank status, evidence note, and independent approval reference only after review.

| Review lane | Questions the reviewer must answer | Evidence and known limitation | Reviewer role | Status / action | Approval reference |
| --- | --- | --- | --- | --- | --- |
| Scientific construct validity | Does the method measure semantic architectural control and distinguish applicability, compliance, pair validity, coverage, and governance? Are claims falsifiable and bounded? | [RESEARCH_CONTEXT](RESEARCH_CONTEXT.md), [Method P specification](G1_METHOD_SPECIFICATION.md); formal adequacy and novelty are unapproved | Architecture-method researcher | PENDING_INDEPENDENT_REVIEW | |
| Method P correctness/completeness | Are definitions, preconditions, impact rules, operations, deterministic choice, governance, rollback, and INV-01…INV-12 complete and consistent with the actual DEVELOPMENT code? | [SPEC 03](SPEC_03_IMPACT_ANALYSIS_AND_GOVERNED_ADAPTATION.md), [implementation map](../experiments/execution/P_GOVERNED_ADAPTATION_V1.md), [traceability](SPEC_03_IMPLEMENTATION_TRACEABILITY.md); source tests do not prove scientific soundness | Formal-methods reviewer | PENDING_INDEPENDENT_REVIEW | |
| B0/B1/P fairness | Are common facts, policy bytes, target revisions, evaluator capabilities, time, human exposure, and P-only traceability treatment fair? | [Comparability plan](B1_P_COMPARABILITY_PLAN.md), [input isolation](../experiments/execution/da01/INPUT_ISOLATION.md); M-01 and M-03 remain open | Experimental-methods reviewer | PENDING_INDEPENDENT_REVIEW | |
| Outcomes/statistics | Are endpoints, estimands, denominators, hypotheses, missing-data treatment, independent units, multiplicity, and uncertainty procedures preregistered? | [Preregistration draft](DA01_PREREGISTRATION_DRAFT.md), [score rules](../experiments/execution/da01/SCORE_RULES.md); DA01 has one transition and no inferential result | Independent statistician | PENDING_INDEPENDENT_REVIEW | |
| Policy authority/completeness | Are Charter, Registry, trust anchors, approval keys, scope, time, and completeness evidence authentic and independently governed? | [policy status](../experiments/execution/P_GOVERNED_ADAPTATION_V1.md), [Snapshot v1.2 note](../experiments/execution/P_INPUT_V12_DEVELOPMENT.md); pilot remains DRAFT/OPEN | Policy authority and key-custody reviewer | PENDING_EXTERNAL_AUTHORITY | |
| Evaluator artifacts/semantics | Are real generic evaluators available, pinned, nonvacuous, semantically adequate, independently checked, and equally available to B1/P? | [validity rules](../experiments/execution/da01/VALIDITY_RULES.md), [comparator plan](B1_P_COMPARABILITY_PLAN.md); TEST_ONLY evaluator is not production authority | Evaluator-domain reviewer | PENDING_EXTERNAL_AUTHORITY | |
| Frozen scoring compatibility | Are RQ1 target identity, empty-positive behavior, RQ2 exact pairs, full denominator, and B0 before-coverage rules unchanged? | [protocol](../experiments/execution/da01/PROTOCOL.md), [score rules](../experiments/execution/da01/SCORE_RULES.md), [validity rules](../experiments/execution/da01/VALIDITY_RULES.md); OPEN-07/08 require review without scorer changes | DA01 scoring-contract reviewer | PENDING_INDEPENDENT_REVIEW | |
| Isolation and holdout independence | Are method allowlists enforced, and are oracle, scorer, sealed predictions, holdout, Git/history, network, and other-method outputs isolated? | [input isolation](../experiments/execution/da01/INPUT_ISOLATION.md), [traceability test report](SPEC_03_IMPLEMENTATION_TRACEABILITY.md); TT-P03-43 remains BLOCKED for independent frozen-output byte parity | Research-integrity/holdout custodian | EVIDENCE_INCOMPLETE | |
| Limitations and scope | Are open issues visible, including stage scope and α/θ; are cloud/runtime and generalization claims excluded? | [decision register](G1_METHOD_DECISION_REGISTER.md), [M-01…M-06](RESEARCH_CONTEXT.md#10-open-methodological-discrepancies--do-not-silently-choose); α/θ deferred | Independent methods reviewer | PENDING_INDEPENDENT_REVIEW | |
| Evidence required before G1 | Are independent reviews, approved algorithm version, custody/freeze process, and all necessary protocol choices complete? | This checklist and [READINESS](../experiments/execution/da01/READINESS.md); none of these fields self-approve | Independent G1 chair/approver under an authentic process | NOT_REVIEWED | |
| Separate G4 authorization | Has an authorized human explicitly approved the specific measured run after G1 and prerequisite gates? | [READINESS](../experiments/execution/da01/READINESS.md); G4 is currently NOT AUTHORIZED | Authorized human decision-maker | NOT_AUTHORIZED | |

## 4. Decision docket carried into review

| Decision | Required independent disposition | Documents that must address it | Current state |
| --- | --- | --- | --- |
| OPEN-01 / M-01 | Choose periodic vs post-change B1, trigger, time, exposure, and evidence | [Preregistration](DA01_PREREGISTRATION_DRAFT.md), [comparability](B1_P_COMPARABILITY_PLAN.md) | PENDING_INDEPENDENT_REVIEW |
| OPEN-02 / M-02 / M-06 | Reconcile RQ labels; choose endpoints, hypotheses, units, and analysis | [Preregistration](DA01_PREREGISTRATION_DRAFT.md) | PENDING_INDEPENDENT_REVIEW |
| OPEN-03 / M-04 | Define later stage registry without retrofitting DA01 | [Method](G1_METHOD_SPECIFICATION.md), this checklist | PROPOSED / DEFERRED_WITH_LIMITATION |
| OPEN-04 | Provide authentic authority, trust anchors, and completeness proof | [Comparability](B1_P_COMPARABILITY_PLAN.md), this checklist | PENDING_EXTERNAL_AUTHORITY |
| OPEN-05 / M-03 | Approve real evaluator artifacts and B1/P capability parity | [Comparability](B1_P_COMPARABILITY_PLAN.md), this checklist | PENDING_EXTERNAL_AUTHORITY |
| OPEN-06 | Set cost units, bounded search, budget and ties | [Method](G1_METHOD_SPECIFICATION.md), [preregistration](DA01_PREREGISTRATION_DRAFT.md) | PENDING_INDEPENDENT_REVIEW |
| OPEN-07 | Decide future monitor/compliance semantics while frozen DA01 treats nonzero exit as EXECUTION_FAILURE | [Method](G1_METHOD_SPECIFICATION.md), [preregistration](DA01_PREREGISTRATION_DRAFT.md), [integration analysis](g1/G1_INTEGRATION_DECISION_MATRIX.md) | PENDING_INDEPENDENT_REVIEW |
| OPEN-08 | Resolve multi-obligation ADD under single-target frozen operation identity | [Method](G1_METHOD_SPECIFICATION.md), [preregistration](DA01_PREREGISTRATION_DRAFT.md) | PENDING_INDEPENDENT_REVIEW |
| OPEN-09 | Establish independent algorithm freeze, holdout custody and sealing | [Preregistration](DA01_PREREGISTRATION_DRAFT.md), this checklist | PENDING_INDEPENDENT_REVIEW |
| OPEN-10 / M-05 | Keep α/θ adaptation separate from core P v1 | [Method](G1_METHOD_SPECIFICATION.md), this checklist | DEFERRED_WITH_LIMITATION |

## 5. Evidence index

| Review claim | Primary repository evidence | Evidence class | Limitation |
| --- | --- | --- | --- |
| Manuscript and executable research questions differ | [RESEARCH_CONTEXT](RESEARCH_CONTEXT.md), [DA01 protocol](../experiments/execution/da01/PROTOCOL.md) | Source contract/document | Does not reconcile the difference |
| RQ1/RQ2 scoring and validity | [SCORE_RULES](../experiments/execution/da01/SCORE_RULES.md), [VALIDITY_RULES](../experiments/execution/da01/VALIDITY_RULES.md) | Frozen executable contract | Private denominator and oracle stay outside this packet |
| Input allowlist and isolation | [INPUT_ISOLATION](../experiments/execution/da01/INPUT_ISOLATION.md) | Versioned method-input contract | Historical probe evidence is environment-specific |
| Current P DEVELOPMENT implementation | [P module map](../experiments/execution/P_GOVERNED_ADAPTATION_V1.md), [SPEC 03 source map](SPEC_03_IMPLEMENTATION_TRACEABILITY.md) | Engineering source/report | Synthetic TEST_ONLY proof only |
| Synthetic governance accept behavior | [PR #10 traceability](SPEC_03_IMPLEMENTATION_TRACEABILITY.md), including S03R-04/05 and no-op/ADD cases | Historical DEVELOPMENT regression report | Not measured, not production-authorized, not independently approved |
| G0–G4 and measured status | [READINESS](../experiments/execution/da01/READINESS.md), [P status](../experiments/execution/da01/P_ALGORITHM_STATUS.md) | Current repository readiness report | Does not advance itself by checklist completion |
| Integrated workstream analysis | [G1 integration decision matrix](g1/G1_INTEGRATION_DECISION_MATRIX.md) | Source-based review synthesis | Recommendations are proposals; no decision is approved |
| Open decisions and scientific discrepancies | [Decision register](G1_METHOD_DECISION_REGISTER.md), [RESEARCH_CONTEXT M-01…M-06](RESEARCH_CONTEXT.md#10-open-methodological-discrepancies--do-not-silently-choose), [integration matrix](g1/G1_INTEGRATION_DECISION_MATRIX.md) | Pending docket | Independent outcomes are absent |
| Safe synthetic code evidence | [SPEC 03 traceability](SPEC_03_IMPLEMENTATION_TRACEABILITY.md); safe unit/integration paths listed there | Test report | Tests establish code properties only |
| Protected/frozen scope | Changed-path diff and status audit recorded in the delivery report | Local audit | Not independent byte-parity verification; TT-P03-43 remains blocked |

## 6. Conditions for a genuine G1 completion record

Before recording G1 complete, reviewers must resolve or explicitly disposition OPEN-01…OPEN-09, approve the algorithm and protocol versions under an independent process, set the preregistered endpoints and failure rules, establish policy/evaluator authority where required, specify B1 and holdout custody, verify method isolation for the selected environment, and preserve authentic reviewer identities, decisions, dates, and artifacts. OPEN-10 remains deferred to a separate α/θ study.

The repository’s successful TEST_ONLY code paths, CI, this packet, and completed checklist fields do not automatically constitute a G1 freeze. Report G1 only when authentic independent approval evidence exists.

## 7. Separate G4 requirements

G4 is a distinct explicit human authorization for a specific measured DA01 run. It requires the approved G1 method/protocol, G0–G3 evidence appropriate to the selected environment, authorized policy/evaluator and reference-checking arrangements, authentic B1 if that comparison is included, prediction-seal and holdout custody, and a recorded run scope. No reviewer may infer G4 from G1 or engineering CI. G4 remains **NOT AUTHORIZED** in this package.

## 8. Reviewer record

| Field | Entry |
| --- | --- |
| Reviewer role | |
| Reviewer identity under approved process | |
| Evidence/version reviewed | |
| Findings and required revisions | |
| Disposition | NOT_REVIEWED |
| Date/time and review record reference | |
| Separate G1 approval reference, if later authentic | |
| Separate G4 authorization reference, if later applicable | |

No person, signature, institution, date, or approval has been supplied or inferred by this draft.
