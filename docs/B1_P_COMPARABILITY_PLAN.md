# B0/B1/P comparability plan — review draft

**DRAFT — NOT INDEPENDENTLY APPROVED**

**Review source revision:** prepared branch commit 02c1654f457fd1cf685fd449b552d6e35701ea54, based on main at 740c60aeece6e424c56ba081eacc079dc0f16d74 (PR #10 merged).
**Status:** fairness plan for independent review. No B1 participant, comparator session, or measured comparison is reported.
**Proposed reviewers:** independent experimental-methods reviewer; human-comparator/fairness reviewer; policy/evaluator authority reviewer.

## 1. Comparison objective and hard boundary

Compare three responses to the same before/after architecture and post-change assessment:

- **B0:** unchanged frozen A0 fitness configuration.
- **B1:** a genuinely independent human following the reviewed manual procedure.
- **P:** a frozen general governed adaptation method with its explicitly declared traceability input.

The [DA01 protocol](../experiments/execution/da01/PROTOCOL.md) and [input isolation contract](../experiments/execution/da01/INPUT_ISOLATION.md) control the current scope. This draft does not authorize execution. No human session is simulated. TEST_ONLY evaluators, policies, signatures, and synthetic ACCEPT cases are engineering test fixtures, not production authority or a fair production capability inventory.

## 2. Comparison matrix

| Dimension | B0 | B1 | P | Parity or review requirement |
| --- | --- | --- | --- | --- |
| Architecture pair | Same pinned before and target source revisions | Same pair | Same pair | Record exact source SHAs and sanitized observation hashes; any mismatch stops comparison |
| Common architecture facts | Assessment uses the same allowed pinned architecture and structural observations | Receives the common allowed observations | Receives the common allowed observations | Same verified facts and revision scope |
| Policy and obligation source | Frozen A0 configuration is assessed under the authorized protocol | Common readable normative catalog and policy information | Same normative and condition catalog bytes | SPEC 02 V3 shares policy/condition catalog bytes for B1/P; P alone executes the applicability procedure. Fairness of that execution difference is M-03 and needs review |
| A0 fitness configuration | Preserved unchanged | Available to inspect and adapt under checklist | Parent configuration bound by digest | Same parent identity and bytes |
| Evaluator capability inventory | No new adapted capability is added | Shared authorized capability inventory | Same inventory | Verify byte-pinned availability before either B1 or P; no unavailable capability is assumed |
| Traceability | No adaptation trace model | No P traceability graph or impact engine | A0 traceability graph allowed as method-specific input | Disclose and review P-only traceability as a treatment advantage; do not hide it |
| Method-specific tools | None beyond frozen assessment | Manual checklist and approved common tools | Frozen P implementation and approved common tools | Record exact tool versions, permitted files, and environment |
| Candidate | Frozen A0 configuration | Human-authored candidate with reasons and evidence | Materialized candidate with operation/evidence/version record | Same target architecture, candidate validation rules, evidence requirements, and independent verifier |
| Policy/evaluator authority | Existing frozen A0 evaluator remains the B0 artifact | Real approved shared evaluator inventory required | Same real approved inventory and authorized templates required | TEST_ONLY status does not satisfy authority or availability |
| Time | Adaptation time is zero by frozen protocol definition | Actual human wall time and per-step times | Record diff, impact, decision, candidate, and validation time | Fix comparable budget and stop rule before run; reference-scoring time is excluded |
| B1 cadence | Not applicable | Periodic or post-change remains undecided | P is triggered by the declared transition | OPEN-01/M-01: do not silently pick a cadence |
| Operator independence | Not applicable | Independent of P development/results; exposure and experience recorded | Code/version frozen before output | Independent operator and prior-exposure record required |
| Holdout/blinding | No method prediction | Blind to reference answers until prediction is sealed | No oracle/scorer/other-method access | Independent custodian controls holdout and post-seal scoring |
| Output and identity | Empty explicit operation/prediction list; implicit-retain handling follows protocol | Sealed human prediction and candidate | Version-bound sealed output only after governed ACCEPT | Hash, timestamp, source revision, and input bundle identity for every output |

## 3. Common and method-specific inputs

### Common controlled information

For each arm, freeze the same before/after architecture source SHAs, allowed structural observations, parent A0 fitness configuration identity, general obligation catalog revision, normative policy revision/bytes, permitted evaluator capability inventory, target architecture identity, evaluation environment, and scoring/validity contracts. Record each input bundle hash and the source revision that produced it.

Do not supply any method with the scenario answer, expected affected targets or operations, private required-obligation answer set, independent scorer/reference rules, another method’s output, engineering acceptance configuration, Git metadata/history/remotes, or network access.

### Method-specific information

- B0 keeps the original A0 configuration unchanged; its operation list is empty. Its old evaluator may be stale, vacuous, or unsuitable for the target and must be independently assessed.
- B1 may use the common architecture observations, complete general obligation registry, A0 representations, and shared evaluator capability inventory through the manual checklist. It must not receive the P traceability graph or P output.
- P may receive the same common bundle plus the explicitly permitted A0 traceability graph and its pinned general algorithm. This P-only input must be disclosed, hashed, and reviewed as part of the causal contrast.

The B1/P normative-source issue remains open. The source implementation provides identical normative/condition catalog bytes to B1 and P while P alone executes the rulebook. Reviewers must decide whether readable rule parity, execution parity, or another predeclared treatment defines fairness. No resolution is made here.

## 4. Architecture, policy, and evaluator identity

The target pair and all policy/registry/ruleset sources must be immutable for one comparison. Bind each bundle to:

- before and after architecture revisions and structural-evidence digests;
- Snapshot and schema version, fact-vocabulary version, policy bundle revision, ruleset digest, registry/charter identity, and scoped completeness proof;
- parent fitness configuration digest, obligation catalog digest, evaluator artifact and template descriptor digests, and traceability digest where permitted;
- candidate digest, method/checklist version, environment/runtime identity, and source allowlist.

An OPEN registry, DRAFT policy, unverified authority, or missing completeness claim remains UNKNOWN/HOLD. Snapshot v1.2 is an additive unfrozen DEVELOPMENT extension. It is not a production authority grant or frozen DA01 input contract.

Before comparison, the independent reviewer must inventory real evaluator artifacts available to B1 and P, verify their hashes, clean-pass and corrupted-control behavior, target resolution, non-vacuity, stage/scope, evidence contracts, and operational availability. A TEST_ONLY integration evaluator is not a substitute. If B1 and P do not have comparable real capabilities, stop and resolve OPEN-05 instead of improvising a parity adjustment.

## 5. Human B1 procedure and cadence decision

The current [B1 checklist](../experiments/execution/da01/B1_CHECKLIST.md) specifies review after a particular architecture transition. The manuscript describes periodic heuristic review and explicitly warns that these interventions differ. This is OPEN-01/M-01; the independent reviewer must record one predeclared choice and its estimand before a measured comparison.

| Cadence alternative | Intervention | Consequence for comparison |
| --- | --- | --- |
| Periodic review | Human reviews at a fixed predeclared cadence, which may not coincide with the change | Estimates a periodic maintenance intervention; the response delay and review workload are part of the treatment |
| Post-change review | Human is prompted after the defined architecture transition | Estimates a transition-triggered manual response; differs from periodic review in timing and information |
| Other reviewed cadence | Must be operationally defined before data collection | Requires a separate rationale and matched time/input rule |

No alternative is selected in this draft. The decision record must set trigger, review window, maximum time allowance, permitted evidence, treatment of overruns, prior exposure, and whether the P trigger is temporally comparable.

For an actual B1 session, record pseudonym/ID through the approved custody process, architecture-quality experience, prior exposure, independence from P development, blind status, bundle hash, start/end UTC times, active adaptation time, tools, evaluator capabilities used, each decision and rationale, uncertainty, evidence references, deviations, complete candidate hash, and sealing time. Keep the participant fields blank until a real independent operator is recruited; no fictional or prefilled session is acceptable.

## 6. Time and cost measurements

The DA01 protocol defines B0 adaptation time as zero. For B1 record actual human wall time, including the agreed checklist steps. For P record the separately instrumented diff, impact, decision, candidate-construction, and method-validation times. Record resource usage only if the measurement and environment are fixed before collection. Reference validation/scoring time is separate from adaptation time.

OPEN-06 remains pending: cost units, candidate-search bound, acceptable cost, treatment of incomparable costs, and the handling of budget exhaustion require independent review. Apply identical externally measured limits where the estimand requires comparable effort, and report method computation and human time separately rather than pretending their units are interchangeable. Do not set a numerical budget or infer a zero cost from a synthetic fixture.

## 7. Candidate verification, sealing, and holdout protection

Each candidate must be evaluated against the same target architecture revision and independent exact-pair evidence procedure. Keep applicability, architecture compliance, representation execution validity, pair-specific semantic validity, evidence adequacy, and governance status as separate fields.

B1 and P must preserve their complete proposed candidate, operation list, rationale/reason codes, evidence references, evaluator/template digests, and unresolved items. B0 remains byte-identical to its frozen parent configuration. Candidate review does not reveal the reference answer.

An independent custodian must hold the answer key, reference scorer, holdout scenarios, and sealed method outputs. Freeze the generic P version and preregistration before a prediction is generated. Seal exact prediction bytes once; after sealing, an independent scorer may evaluate them. The scorer and its private inputs are not available to B0, B1, P, or method authors before seal. Keep scoring output separate from method inputs.

The production publication writer is currently disabled. Synthetic TEST_ONLY ACCEPT demonstrates a code path only; it does not authorize a production candidate or count as a scored outcome.

## 8. Stop conditions

Stop and mark the comparison NEEDS_APPROVAL if any of these holds:

- architecture, policy, registry, catalog, or method source revisions differ across arms or cannot be verified;
- policy authority, exact-scope completeness, fact provenance, or required evaluator authority is missing or untrusted;
- B1 operator independence, prior exposure, or required time/cadence record is unavailable;
- B1/P evaluator artifacts or capability inventories differ without an independently approved treatment definition;
- a candidate relies on an unpinned, stale, vacuous, semantically unsupported, or unmaterializable evaluator;
- an exact-pair verdict or evidence reference is missing, conflicting, stale, or scoped to another architecture;
- method isolation, holdout custody, prediction sealing, or independent scoring cannot be demonstrated;
- the preregistered budget, candidate limit, or input contract is exceeded or no longer comparable;
- the independent checker or scoring process fails.

Do not repair a stopped comparison by changing frozen scoring, inventing policy authority, simulating B1, giving a method hidden information, or treating missing proof as approval.

## 9. Review record and source index

- Independent cadence decision: **PENDING_INDEPENDENT_REVIEW**
- Selected B1 trigger/cadence: ____________________
- Time budget and overrun rule: ____________________
- Common input/source identity approved by: ____________________
- Evaluator/capability parity evidence: ____________________
- Holdout custodian and sealing procedure: ____________________
- Reviewer role/name/date/outcome: ____________________

Sources: [DA01 protocol](../experiments/execution/da01/PROTOCOL.md), [input isolation](../experiments/execution/da01/INPUT_ISOLATION.md), [B1 checklist](../experiments/execution/da01/B1_CHECKLIST.md), [readiness](../experiments/execution/da01/READINESS.md), [research context and M-01/M-03](RESEARCH_CONTEXT.md#10-open-methodological-discrepancies--do-not-silently-choose), [P adaptation development note](../experiments/execution/P_GOVERNED_ADAPTATION_V1.md), and [PR #10 engineering traceability](SPEC_03_IMPLEMENTATION_TRACEABILITY.md).
