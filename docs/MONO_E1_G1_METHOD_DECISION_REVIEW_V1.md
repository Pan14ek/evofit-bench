# MONO-E1 Method P decision package: OPEN-06…09, v1

**Status: PROPOSAL FOR INDEPENDENT REVIEW ONLY.** This document records no approved method decision, reviewer appointment, signature, G1 completion, or G4 authorization. OPEN-06…09 remain pending independent review.

**Base:** latest main at a1e2f79d4bc3c10431cac3e2d8be54105061a98b, including merged PR #42.

**Scope:** decision-ready analysis of cost/search, evaluator validity versus compliance, multi-obligation ADD, and independent review/custody. It reuses the OPEN-03/04 preparation from [PR #41](https://github.com/Pan14ek/evofit-bench/pull/41) and the exact candidate identity from [PR #42](https://github.com/Pan14ek/evofit-bench/pull/42). It does not duplicate either package.

## Candidate and authority anchors

PR #42 added [the DEVELOPMENT candidate review](P_EXECUTABLE_CANDIDATE_REVIEW_V1.md) and [the executable identity manifest](../experiments/execution/P_EXECUTABLE_CANDIDATE_V1.json). The candidate remains review-only:

- Method version: P_GOVERNED_ADAPTATION_DEVELOPMENT_V1.
- Algorithm version: P_GOVERNED_ADAPTATION_V1.
- Pinned source: commit 6ca20ea1b86c3570510c4c3f206ae3c418d13781, tree a195778a5137674bfc1c3d46069f752336438549.
- Manifest identity SHA-256: 45c75b7d211705ab001f080a193aa64641e01d5222e25603cd0ef241fecefde4.
- Source identity SHA-256: c477bd4258734a615fcdaf8491988a36bba90004eb4af083c76e0e814ff0ccbf.
- Configuration identity SHA-256: cdd4df7342e821927c3a565f6bcec02d51a6c65bbca2fd131cfaae099ecb9fca.

Keep this identity unchanged. PR #42 records that the existing runner output does not echo the manifest identity digest. Before any measured integration, a separately versioned run envelope must bind the manifest digest and the digest-pinned image to each execution record.

For OPEN-03/04, use [MONO-E1 policy approval preparation v1](MONO_E1_POLICY_APPROVAL_PREPARATION_V1.md) as the existing review package. Its catalog inventory is not an approved obligation universe, policy decision, denominator, lifecycle rule, or trust anchor. Its decision and sign-off fields remain unfilled. The more recent [W0 readiness resolution](MONO_E1_W0_READINESS_RESOLUTION.md) remains authoritative for the current no-go boundary.

## A. Decision matrix

| Decision | PROPOSAL for reviewers | Material consequence | Required review |
| --- | --- | --- | --- |
| OPEN-06 Cost and bounded search | Preserve the DEVELOPMENT lexicographic order: fewest non-retain operations, then an independently authorized scalar cost, then canonical operation identifiers. Report elapsed/resource dimensions separately; unknown cost or incomplete search cannot be called feasible, infeasible, or optimal. | Changes which plan is selected, the feasible set, and MONO overhead interpretation. | Operations-cost and experimental-methods/statistics reviewers. |
| OPEN-07 Compliance versus evaluator validity | Preserve frozen DA01 validity and current MONO-A1 v1 positive-coverage predicates. Record execution, monitor/pair suitability, and compliance separately. A noncompliant observation is not DA01-valid execution or MONO-A1 v1 positive coverage. If the intended estimand counts a valid monitor that detects noncompliance as coverage, require a separately versioned contract and independent approval. | Changes the RQ2 numerator and the meaning of coverage; may also change failure and detection outcomes. | Evaluator-validity, formal-methods, and DA01/MONO scoring-contract reviewers. |
| OPEN-08 Multi-obligation ADD | Do not canonize the current lexical owner as a scientific rule. PROPOSE defining one scored ADD target per obligation and grouping those targets to one materialized representation in an additive candidate-configuration v2. Keep prediction-v1 and the scorer unchanged. If reviewers do not approve the grouping contract before method freeze, defer such ADD cases by HOLD; never tailor targets to reference answers. | Changes RQ1 target counts, duplicates, F1 and operation accuracy; grouped materialization must also preserve one candidate representation and its exact-pair links. | Operation-scoring and formal-methods reviewers. |
| OPEN-09 Independent review and custody | Require an independent algorithm review against the PR #42 manifest, an independent holdout/reference custodian, strict input separation, and write-once predictions sealed before scoring. No role or signature is presumed. | Without independent review and custody evidence, the prediction cannot support an unbiased comparison and G1 cannot close. | Independent method reviewer, research-integrity/holdout custodian, evaluator/semantic reviewer, and authorized G1 decision authority. |

These are proposed dispositions, not scientific approvals. The detailed status docket remains in the [G1 decision register](G1_METHOD_DECISION_REGISTER.md).

## B. OPEN-06 — cost model and bounded search

### Scientific question and current behavior

What is the least-change feasible candidate under a reproducible cost and search budget, and what overhead is attributable to adaptation versus evaluator execution and validation?

The current [cost schema](../experiments/execution/schemas/p_cost_model_v1.schema.json) provides an authority flag, one scalar maximum, a search-node limit, and numeric costs indexed by artifact SHA-256. It does not define a cost unit, a calibration method, human effort, evaluator invocations, runtime/resource sampling, or whether a repeated artifact is charged once or per use. In the current planner, template selection sums selected candidate costs, while the final cost verdict deduplicates artifact digests. That usage difference needs an explicit rule.

The DEVELOPMENT implementation in [p_operations.py](../experiments/execution/tooling/p_operations.py) searches a finite set of allowlisted materializable templates and ranks a set cover by operation count, cost, then stable identifiers. It returns HOLD for missing/unauthorized costs or search exhaustion. The exhaustive-search claim is limited to the enumerated bundle and the reviewed node limit; it is not a global optimum over unavailable templates or all possible evaluator designs. MONO’s [protocol](../experiments/execution/MONO_A1_PROTOCOL_V1.md) measures adaptation, evaluator, verification, and total time separately and leaves unsampled CPU/RSS unknown. The frozen DA01 protocol defines B0 adaptation time as zero; that does not make B0 evaluator execution cost zero.

### Proposed definitions

Let F be the finite set of authorized, digest-pinned materializable templates in one input bundle. A plan S selects templates from F and produces a normalized operation list O(S) and a materialized candidate Φ′(S).

- Target-operation count: Nop(S) is the number of distinct non-RETAIN target operations after duplicate/conflict normalization. Under the proposed OPEN-08 grouped rule, also report Nmat(S), the number of distinct materialized representation rows. Do not silently substitute one count for the other.
- Evaluator work: record Nexec by distinct evaluator invocations, each bound to artifact/configuration digest, target source, scope, and stage. Exact-pair assessments remain per (representation, obligation) even if one evaluator invocation supplies evidence to multiple pairs.
- Time and resource: report adaptation decision, materialization, evaluator execution, and candidate validation wall times separately in their source units; report CPU time, peak memory, and other resources only when actually sampled. Keep unavailable measurements UNKNOWN or NOT_COLLECTED.
- Declared planner cost: use Cplan only if an independent authority defines its unit, per-use versus per-artifact charging, provenance, calibration, and applicability. Do not infer zero from a missing cost or add unlike units with arbitrary weights.
- Overall measured cost: preserve the vector (human active time, P compute/adaptation time, evaluator time, validation time, CPU, peak memory, and declared operational/resource measures). Human minutes and machine CPU time remain separate unless an independently justified conversion is approved.

For an authorized scalar Cplan and approved bounds B and N, retain this lexicographic DEVELOPMENT preference:

    rank(S) = (Nop(S), Cplan(S), canonical(O(S)))

where canonical(O(S)) sorts and serializes each target type, target ID, operation, and bound artifact identity. A candidate is within bounds only if it is materializable, passes the stated hard constraints, has complete known cost, satisfies Cplan(S) ≤ B, and is found before the approved search-node limit N. The planner may call a plan optimal only within the frozen finite F and only after completing the bounded enumeration.

### Generic bounded example

Suppose synthetic obligations q-alpha and q-beta lack demonstrated coverage. One authorized template r-shared covers both; two other templates r-alpha and r-beta cover one each. Write their independently established costs as c-shared, c-alpha, and c-beta, and the authorized ceiling as B. No numeric value is assumed.

- The one-template plan has Nop = 1 and cost c-shared.
- The two-template plan has Nop = 2 and cost c-alpha + c-beta, subject to the approved charging rule.
- If both are within B and enumeration is complete, the lexicographic proposal prefers the one-operation plan even if its scalar cost is higher. If it exceeds B, it is not feasible under that declared bound; the two-operation plan may still be feasible.
- If any required cost is unknown or costs use incomparable units, the planner cannot rank the affected alternatives and must HOLD.
- If the search-node budget ends before enumeration completes, report BUDGET_EXHAUSTED/HOLD. Do not report infeasibility or optimality.
- If complete enumeration finds no candidate within B, report no feasible plan within this particular authorized bound. Do not generalize this to “no possible adaptation.”

The current schema and code use search limits in DEVELOPMENT; their exact semantics must be pinned before approval. Reviewers should reconcile the recursive visited-node bound in template set-cover search with any candidate-count bound in other planner helpers.

### Reproducibility, fairness, and sensitivity criteria

A PASS requires a versioned cost model with units and provenance for each value; a declared per-artifact/per-invocation rule; frozen timer boundaries and environment; B1/P capability parity where applicable; separate human and compute ledgers; a finite candidate inventory; and a documented search-completion indicator. A sensitivity report must rerun the same candidate set over prospectively selected bounds and show feasibility, selected plan, and exhaustion status at each bound. Select the primary bound before outcomes are seen. The reviewer sets the admissible bounds and any cost ceiling; this package supplies no calibrated values.

RQ effects: target-operation count and selection affect RQ1; candidate feasibility and valid pair coverage can affect RQ2; cost is direct for MONO manuscript RQ3 (legacy executable RQ4); governance/control outcomes may appear in MONO manuscript RQ4 (legacy executable RQ3). One transition supports descriptive observations only.

## C. OPEN-07 — compliance violation versus evaluator validity

### Proposed separation

Keep three questions separate:

1. Did the evaluator process complete with verifiable source, configuration, scope, and raw output?
2. Is the representation an adequate, semantically matched monitor for the exact obligation?
3. Does the architecture comply with that obligation?

A successful process alone proves neither monitor adequacy nor compliance. A noncompliant architecture does not, by itself, prove the monitor is invalid. Yet the current frozen contracts determine which outcomes count for their own measurements, so the three fields cannot be recombined ad hoc.

The code in [p_semantic.py](../experiments/execution/tooling/p_semantic.py) can currently return pair status VALID with compliance_status NON_COMPLIANT when a completed, adequately evidenced evaluator has only the compliance-violation reason. In contrast, frozen [DA01 validity rules](../experiments/execution/da01/VALIDITY_RULES.md) classify a nonzero evaluator exit as EXECUTION_FAILURE. The current MONO-A1 v1 verifier requires execution VERIFIED, a non-vacuous inspected scope, suitable exact-pair assessment, verified raw evidence, and compliance COMPLIANT before it returns positive evidence; a NONCOMPLIANT row is UNKNOWN for positive RQ2 coverage. These predicates are not interchangeable.

There is a second DEVELOPMENT limitation: p_semantic.py derives COMPLIANT from a completed zero exit unless one of its listed execution/identity/scope blockers applies. Semantic incompatibility or an inadequate evidence contract can make the pair INVALID while leaving compliance_status COMPLIANT. Reviewers must treat that field as a code-derived observation, not an independently adjudicated compliance conclusion. Any future outcome contract must bind compliance to a valid observation with adequate target scope.

### Decision table for independent review

| Event | Evaluator execution | Compliance | Exact-pair validity | Coverage and governance | Existing contract crosswalk |
| --- | --- | --- | --- | --- | --- |
| Completed, source-bound run; correct scope; compliant architecture | VERIFIED only after raw execution/scope readback | COMPLIANT if the observation supports that conclusion | VALID only with an independent exact-pair semantic/evidence proof | Counts for coverage only under the complete approved denominator and current pair rule; ACCEPT still requires every other invariant | Compatible in principle; successful exit alone is insufficient. |
| Completed run returns structured evidence of a violation, with process exit 0 | Process may be VERIFIED; current P parser does not define a distinct structured-finding outcome | NONCOMPLIANT only if the finding is independently interpretable | A valid monitor may be VALID as a monitoring claim, but this does not imply a valid-coverage mapping in current DA01/MONO-A1 v1 | Do not count as positive MONO-A1 v1 coverage; hold the RQ2 interpretation pending a reviewed outcome contract | DA01 v1 has no approved mapping for this distinct structured outcome. Preserve UNKNOWN until reviewed. |
| Nonzero exit attributed to an architectural violation | DEVELOPMENT pair code may be VALID with NON_COMPLIANT when no other unresolved reason remains | NONCOMPLIANT only if raw evidence proves the violation | Preserve the P-side diagnostic separately; do not override the reference rule | No DA01 RQ2 credit: frozen status is EXECUTION_FAILURE. MONO-A1 v1 returns UNKNOWN for positive coverage because compliance is not COMPLIANT. No ACCEPT based on this row alone. | Direct compatibility boundary. Do not edit DA01 or MONO-A1 v1 predicates. |
| Nonzero exit caused by infrastructure failure | FAILED or UNKNOWN; it is not a valid compliance observation | UNKNOWN | UNKNOWN | Not covered; governance HOLD unless a separate proven hard failure applies | Keep INFRASTRUCTURE_FAILURE distinct from compliance failure. |
| Vacuous success: zero exit but no applicable/resolved/inspected subjects | Process completed, but scope is invalid or unresolved | UNKNOWN; exit zero is insufficient | INVALID when vacuity is proved; UNKNOWN when scope evidence is missing | Not covered; HOLD for unresolved scope, or REJECT a candidate when a hard invalidity/incomplete-coverage condition is proved | DA01 labels VACUOUS_SUCCESS; preserve it. |
| Missing raw output, pair proof, or required evidence | UNKNOWN | UNKNOWN | UNKNOWN | Not covered; HOLD; never infer absence as compliance or inactivity | DA01 missing evidence stays visible and is not imputed. |
| Stale source, configuration, architecture revision, or evaluator identity | Process may have completed, but its evidence is not bound to the target | UNKNOWN unless separately established from valid target evidence | INVALID on a verified mismatch; UNKNOWN if the binding cannot be checked | Not covered; INPUT_REJECTED for invalid bundle identity, otherwise HOLD or candidate REJECT according to proven scope | DA01 has stale-scope/source statuses; do not relabel stale bytes as current. |
| Insufficient inspection scope or unresolved targets | Process may complete, but required scope is not established | UNKNOWN | UNKNOWN for incomplete/unverified scope; INVALID for an explicit scope mismatch | Not covered; HOLD | DA01 distinguishes missing target/scope from a valid applicable verdict. |
| Explicit semantic or evidence-contract mismatch | Execution can be valid as a process event | Compliance status is independent and cannot be inferred from this mismatch | INVALID when mismatch is proved; UNKNOWN when suitability is undetermined | Not covered; REJECT only when a hard candidate failure is proved, otherwise HOLD | Pair validity remains distinct from representation-wide execution status. |
| Conflicting, tampered, or unverifiable evidence; checker/protocol error | UNKNOWN or invalid input, depending on the failed binding | UNKNOWN | UNKNOWN absent a proved mismatch; INVALID for a verified contradiction/tamper | No coverage and no method success; HOLD or INPUT_REJECTED; reference-checker errors/protocol violations are reported separately | Preserve the failure category and evidence. Never score a checker error as method success. |

### Proposed compatibility disposition

For any DA01 claim, preserve the frozen V1 rule: nonzero exit is EXECUTION_FAILURE and cannot satisfy its RQ2 execution predicate, regardless of a P-side VALID diagnostic. For MONO-A1 v1, preserve its current positive-evidence predicate, including compliance COMPLIANT. This is conservative for monitor-validity research: a noncompliant observation remains visible, but it does not become a coverage numerator under these existing contracts.

If reviewers decide that coverage means “a valid control can detect a violation,” rather than “a compliant architecture is positively controlled,” the smallest safe route is an additive, versioned pair/outcome and coverage contract for a future study. It must distinguish execution integrity, monitor suitability, and compliance outcome; define the RQ2 numerator; preserve a DA01 v1 crosswalk; and add independent review plus synthetic positive/negative/infrastructure controls. Existing DA01 schemas, scorer, validity rules, MONO-A1 v1, and the PR #42 candidate identity remain unchanged.

RQ effects: RQ2 numerator and validity interpretation are direct; RQ1 can be affected by whether a candidate operation is treated as an adequately evidenced control; evaluator and validation timings affect RQ3 (legacy executable RQ4); detection and governance interpretation affect RQ4 (legacy executable RQ3).

## D. OPEN-08 — multi-obligation ADD under V1 scoring

### Contract and alternatives

The frozen prediction identity is one pair (target_type, target_id). An ADD target is an obligation ID. The scorer computes target-level TP, FP, FN, precision, recall, F1, and operation accuracy; omitted obligation targets normalize to scorer-only missing_add. RQ2 is separate: one representation may cover multiple obligations, but every (representation, obligation) pair needs its own valid execution and semantic/evidence proof, and each obligation counts once.

Current DEVELOPMENT behavior in [p_operations.py](../experiments/execution/tooling/p_operations.py) selects the lexically smallest uncovered obligation that a selected template covers as the ADD owner, then marks the template’s covered obligations assigned. Candidate materialization stores the representation once with its covers links. V1 prediction projection emits the owner obligation as one ADD target. Candidate materialization rejects a second ADD that reuses the same representation ID. The lexical owner is deterministic software behavior, not a scientifically justified target rule.

Let q-alpha and q-beta be generic mandatory obligations and r-shared one generic evaluator representation with suitable evidence for each pair:

| Encoding | Prediction target identities | Candidate identity and duplicate behavior | RQ1 / operation effects | RQ2 and cost effects |
| --- | --- | --- | --- | --- |
| One canonical owner plus coverage links | One ADD, for the fixed owner obligation; candidate row covers both q-alpha and q-beta | One materialized row and one candidate digest. Current owner rule is lexical; duplicate/conflicting owner targets must fail closed. | If a reference expects both obligation targets, one target is a false negative; if it expects only the owner, adding the other is a false positive. Thus either target set can change precision, recall, F1, and operation accuracy. The owner must not be selected by inspecting answers. | Pair evidence still required separately for both. One representation is materialized; evaluator invocations and cost must follow the approved usage rule. |
| Separate ADD targets, shared materialization | Two ADD targets, one for each obligation, both mapped to the same materialization identity | One representation row but two operation records. Current candidate V1 materializer cannot do this: repeated payload ID collides. Requires additive candidate materialization v2 with stable grouping; prediction-v1 already permits distinct obligation targets. | Score consequences are symmetric: target-level identities match the operation definition, but extra targets become false positives if not expected. Operation count and materialization count must be reported separately. | One representation may support two independently verified pairs. Charge one materialization and the actual evaluator invocations, not two copies merely because there are two target records. |
| Separate representations for separate targets | Two ADD targets with distinct representation IDs | Two candidate rows; no collision, but duplicates logic/artifact and a different candidate digest | Can increase false positives or match two expected targets; cannot be selected after seeing the reference | May duplicate execution and resource cost; only count each valid pair and each obligation once. |
| Defer multi-obligation ADD from measured behavior | No approved grouped ADD emitted; unresolved case remains blocked | No synthetic candidate grouping; existing candidate identity is untouched | A HOLD has no sealed V1 prediction and makes canonical RQ1 NOT_EVALUABLE. A valid empty prediction would instead be scored normally, including missing_add/FN consequences. Do not drop the target. | Candidate coverage remains absent/UNKNOWN for the affected obligations; full denominator is retained. |

### Recommended proposal and normalization

PROPOSAL: define the scored operation unit as an obligation-target ADD and the materialized artifact as a separate unit. Emit one unique V1 ADD target per uncovered mandatory obligation that the selected materialization is intended to serve; bind each target to one stable materialization ID in an additive candidate-configuration v2. Materialize a shared representation once, with its complete sorted covers list and a separate exact-pair evidence record for every claimed obligation.

This proposal follows the frozen V1 target identity and avoids an arbitrary lexical owner while keeping the V1 prediction schema/scorer unchanged. It changes DEVELOPMENT candidate materialization and therefore requires a new additive candidate schema, adapter, method version/identity, and independent approval before any measured use. PR #42’s pinned candidate remains unchanged and unapproved for this grouping behavior. If that versioned change cannot be approved and verified before the measured method is frozen, use the explicit defer/HOLD alternative; do not alter the target universe, denominator, or scorer.

The current PR #42 executable has no configuration switch that defers multi-obligation ADD. Implementing that fallback also needs a new method version and configuration identity, or else any case requiring grouped ADD remains outside the executable candidate's approved scope.

For the additive grouped contract, require these deterministic rules:

1. Normalize obligation IDs and target operation tuples by stable lexical order before digesting or emitting.
2. Emit each (obligation ID, ADD) target at most once. An exact duplicate is rejected or collapsed only if the reviewed contract explicitly selects deduplication; a conflicting duplicate is a hard contract error.
3. A materialization ID maps to exactly one representation ID, descriptor digest, and artifact digest. Reuse with different bytes or descriptors is a collision and must reject the candidate.
4. Repeated target records referencing the same valid materialization resolve to one candidate row; they do not silently create duplicate representations.
5. Candidate identity includes the grouped target map, full covers links, artifact/configuration digests, and parent identity. RQ2 still evaluates every pair separately.
6. Cost reporting distinguishes target-operation count, materialized representation count, evaluator invocation count, and artifact/resource use.

A symbolic example shows why the rule must be fixed before scoring. Let G be the reference-positive target set and let P be the emitted ADD target set. Then TP = |P ∩ G|, FP = |P \ G|, FN = |G \ P|, and F1 = 2TP/(2TP + FP + FN). With P = {q-alpha}, a reference G = {q-alpha, q-beta} yields one FN; a reference G = {q-alpha} yields no FN. With P = {q-alpha, q-beta}, the latter reference yields one FP. These are generic conditional examples, not claims about DA01 or MONO reference labels. No option may be selected after inspecting scorer-only answers.

## E. OPEN-09 — independent review, holdout custody, and change control

### Review roles and separation

No names, appointments, or approvals are supplied here. Before any method freeze, assign and record:

- A method reviewer who did not author or materially tune the P algorithm and has architecture-method/software-method expertise.
- An evaluator and semantic-pair reviewer independent of the representation-obligation mapping author.
- A holdout/reference custodian independent of method authors and P execution, with access control over expected labels, scorer, reference, and holdout inputs.
- A research-integrity reviewer to audit conflicts, exposure, isolation, sealing, and change history.
- An authorized G1 decision authority who records each actual decision. Policy authority and completeness signers for OPEN-04 are handled through PR #41’s existing preparation and external authority process.

Roles may be combined only after an independent separation-of-duties assessment documents why the combination cannot expose answers or bias decisions. The method reviewer must not receive holdout labels or scorer output before sealing. The custodian must not author the P algorithm or feed hidden answers into method inputs.

### Reviewer procedure and evidence record

1. Verify the manifest against its schema and independently recompute identity, source, and configuration SHA-256 values. Read every listed implementation, configuration, and review-basis file from the exact pinned Git commit/tree and compare bytes with the reviewed checkout.
2. Confirm the candidate is the PR #42 identity listed above. The source tree, method version, and manifest digest are immutable for this review. A source or configuration mismatch is UNRESOLVED or FAIL, not a waiver.
3. Inspect the complete decision path: strict V3 input allowlist; source/policy/evidence binding; applicability and impact; exact-pair assessment; bounded operation planning; candidate materialization; governance result precedence; V1 adapters; sealing and output gating.
4. Inspect adverse and boundary cases, including missing/unknown applicability, stale or conflicting source, invalid pair evidence, vacuity, nonzero/infrastructure exits, cost and node exhaustion, duplicate target IDs, materialization collisions, HOLD without a prediction, and forbidden oracle/scorer/network/cross-arm inputs. Synthetic tests demonstrate code paths only; they do not prove scientific effectiveness.
5. Verify method inputs are named allowlisted bytes only. The measured method must not read .git, private reference/scorer/ground truth, another method’s outputs, or network. Keep method authoring fixtures separate from independently held-out transitions and expected answers.
6. Record the custodian, access-control evidence, allowed method inputs, held-out inventory digest, reviewer conflict/exposure declarations, and the separation between method authors, policy/pair assessors, reference custodian, prediction runner, and scorer.
7. Freeze the exact method/configuration and preregistered decisions before any held-out prediction. Record the run-level manifest identity digest and image digest in a versioned execution envelope. Require the reference to be frozen and read back through the approved W0 route before the first method execution; predictions are write-once exact bytes with SHA-256 and UTC seal time before scorer access.
8. Keep scoring outputs and oracle-side artifacts outside authoring/execution inputs. The independent scorer receives sealed predictions only after reference/prediction readback and never returns labels to an active method run.
9. If review discovers a defect, do not sign this candidate as approved. An algorithm or behavior change requires a new method version, source revision, manifest, digest, synthetic regression evidence, and independent re-review. A material input/configuration/schema/normalization/cost/tie-rule change requires a new configuration identity and review; if it changes decision behavior, use a new method version. Never overwrite a sealed prediction or backdate a change.
10. Record exact reviewed commit/tree, manifest identity, files and schemas inspected, commands/results, issues and dispositions, independence/conflict declaration, decision rationale, date, and signature or institutionally approved review artifact digest. Leave fields blank until real reviewers complete them.

### Conditions that require a new version or renewed review

A change to impact, operation choice, cost/search bound semantics, compliance/pair mapping, multi-ADD normalization, allowed inputs, template authority, candidate construction, governance, or output projection changes the algorithm or its scientific behavior and requires a new method version and identity. A change to a manifest-listed configuration or schema requires a new manifest/configuration digest and review even if claimed behavior-neutral. A documentation-only correction outside the pinned candidate files does not authorize a method change; if it changes a decision rule, it is not documentation-only.

## F. Executable behavior-to-methodology traceability

| Decision | Current DEVELOPMENT behavior and source | Existing synthetic evidence | Limit of that evidence |
| --- | --- | --- | --- |
| OPEN-06 | p_cost_model_v1 has no unit/calibration field. p_operations.py ranks bounded template sets by count, cost, IDs; p_adaptation.py verifies cost authority and final cost. | test_bounded_set_cover_prefers_fewer_operations_then_cost_then_ids; test_search_budget_exhaustion_and_missing_cost_return_hold; test_cost_model_rejects_duplicate_or_over_budget_candidate_and_ties_are_stable; test_proven_cost_limit_violation_rejects_only_the_candidate | Confirms mechanics on synthetic costs. Does not calibrate a scientific unit, establish fair B1/P limits, or prove optimality outside the bounded candidate set. |
| OPEN-07 | p_semantic.py separates PairStatus and ComplianceStatus; MONO-A1 v1 verifier counts positive exact-pair evidence only when compliance is COMPLIANT; DA01 frozen rules map nonzero exit to EXECUTION_FAILURE. | test_clean_nonzero_exit_records_noncompliance_without_invalidating_monitor_semantics; test_evaluator_infrastructure_failure_is_unknown_and_not_a_compliance_verdict; test_zero_exit_without_resolved_inspected_subjects_is_vacuous; test_exact_pair_requires_exact_mapping_raw_bytes_and_non_vacuous_proof | Demonstrates typed software outcomes only. The difference between P diagnostics, MONO-A1 v1, and frozen DA01 is unresolved method/scoring policy. |
| OPEN-08 | p_operations.py assigns one lexical owner to a multi-obligation ADD; p_candidate.py applies one payload and rejects duplicate representation IDs; prediction-v1 allows obligation-target ADD rows. | test_bounded_set_cover_prefers_fewer_operations_then_cost_then_ids; test_candidate_rejects_duplicate_operation_targets_and_tampered_plan_digest; test_candidate_rejects_stale_parent_collision_and_orphaned_obligation_link; test_v1_candidate_adapter_validates_without_changing_legacy_schema; test_rq1_scores_only_sealed_predictions_and_reports_operation_confusion | Does not authorize lexical ownership or grouped materialization. No hidden expected operations are examined here. A grouped rule needs an additive candidate contract and new method identity. |
| OPEN-09 | PR #42 pins implementation/configuration/review-basis bytes and source commit/tree. p_interface.py remains NOT_READY; method-input isolation and prediction seals are separate controls. | test_identity_manifest_matches_schema_and_pinned_git_bytes; test_identity_manifest_digest_detects_tampering; test_reference_labels_cannot_enter_method_input; test_reference_is_write_once_and_post_seal_mutation_is_detected; test_p_interface_readiness | Source hashes and synthetic isolation tests do not prove reviewer independence, real access control, custody, holdout non-exposure, or run-level image provenance. |

Every test named above is existing engineering evidence, not a result produced by this review package and not proof of scientific effectiveness.

## G. MONO-E1 dependencies and smallest human decision set

| Dependency | Why it is required | Current source and boundary |
| --- | --- | --- |
| OPEN-02 RQ mapping/endpoints | Fixes the estimand, denominator, missing/HOLD handling, endpoint hierarchy, and the manuscript-to-executable RQ crosswalk before predictions or analysis. | [Decision register](G1_METHOD_DECISION_REGISTER.md); preserve MONO manuscript RQ3/RQ4 ↔ legacy executable RQ4/RQ3 mapping in the [MONO protocol](../experiments/execution/MONO_A1_PROTOCOL_V1.md). One transition is descriptive only. |
| OPEN-03 Lifecycle stages | Defines which stages each obligation must cover, the required exact pairs, and how missing stages affect completeness. | Reuse [PR #41 preparation](MONO_E1_POLICY_APPROVAL_PREPARATION_V1.md); its proposal inventory does not classify obligations or approve a stage. Do not retrofit a new denominator into frozen DA01. |
| OPEN-04 Policy authority and completeness | Establishes who may approve the obligation universe, ACTIVE/INACTIVE/UNKNOWN, mandatory state, closure proof, trust, effective scope/time, and revocation. | Reuse [PR #41 preparation](MONO_E1_POLICY_APPROVAL_PREPARATION_V1.md) and [W0 resolution](MONO_E1_W0_READINESS_RESOLUTION.md). A DRAFT/OPEN pilot, catalog digest, or synthetic signature is not authority. |
| OPEN-05 Evaluator/template authority and parity | Supplies real materializable capabilities, exact pair evidence, and a reviewed B1/P capability rule. Without it, ADD/REPLACE and RQ2 semantic coverage remain blocked. | [Comparability plan](B1_P_COMPARABILITY_PLAN.md) and W0 resolution; TEST_ONLY fixtures are not production evaluators. |
| OPEN-06…09 | Freeze cost/search; validity semantics; operation mapping; and independent review/custody. | This package proposes choices and evidence criteria only. |
| OPEN-01 if B1 is included | A B1 cadence and time budget are needed only if MONO-E1 is expanded to include the human comparator. | Current MONO-A1 protocol declares B0/P. OPEN-01 remains necessary for any full B0/B1/P comparison, not an assumed extra MONO-E1 arm. |
| W0/G2/G4 execution gates | The reference, inputs, exact source pair, evaluator evidence, isolation, selected execution environment, and run authorization must independently pass. | [W0 readiness resolution](MONO_E1_W0_READINESS_RESOLUTION.md) is NO-GO for freeze/run; G4 remains a separate authorization. |

The smallest human decision sequence for any future MONO-E1 execution is:

1. Independent methods/statistics reviewers resolve OPEN-02 endpoints and missing-data rules, informed by OPEN-06…08, without changing frozen DA01 scoring.
2. An accountable policy authority and independent methods reviewer complete the existing OPEN-03/04 process; a qualified independent reviewer establishes evaluator/pair semantics and capability parity for OPEN-05.
3. Independent method and scoring reviewers decide OPEN-06…08 against the exact PR #42 candidate identity. If an additive candidate-v2 change is selected, review a new version; otherwise use only the approved behavior or HOLD.
4. Independent reviewers and authorized custodians complete OPEN-09: source identity, conflicts, access control, holdout separation, exact input allowlists, environment audit, and write-once sealing.
5. W0 completes the source-grounded reference and readback gates. Only after G1 is genuinely recorded may the authorized process consider a separate, run-specific G4 request.

These are prerequisites, not approvals granted here. OPEN-03/04's existing preparation can be consumed by the responsible authority; it cannot be replaced by this package.

## H. Experiment Infrastructure handoff

Keep these assumptions explicit in preparation manifests and execution envelopes until the corresponding independent decision is recorded. Infrastructure records choices and observations; it does not select or silently default a scientific rule.

| Still open | Keep configurable or visible | Stop condition |
| --- | --- | --- |
| OPEN-02 endpoints and missing-data rules | Bind the selected RQ crosswalk, endpoint hierarchy, denominator, abstention/HOLD rule, and analysis role to a versioned study record. Preserve the MONO manuscript/executable crosswalk. | No prediction scoring or summary metrics while endpoint/denominator rules are unresolved. |
| OPEN-03/04 stages and authority | Keep obligation universe, applicability/mandatory status, required stages, policy revision, completeness evidence, authority, and trust scope as explicit versioned inputs. Reuse the PR #41 review package; do not derive approval from its catalog hash. | UNKNOWN/UNRESOLVED rows remain in the record; no denominator closure or reference freeze without the approved authority path. |
| OPEN-05 evaluator/template parity | Bind evaluator and template inventories by source/config/artifact digests, capability scope, allowed use, stage, and B1/P availability. Keep TEST_ONLY separate from measured trust. | No ADD/REPLACE or positive RQ2 claim using unapproved or non-parity capabilities. |
| OPEN-06 cost/search | Carry the cost-model version and authority, declared unit, per-use/per-artifact rule, search universe, node limit, cost ceiling, search-completion/exhaustion, and raw timing/resource fields. Do not convert missing measurements to zero or combine unlike units. | Unknown cost is UNKNOWN/HOLD; exhaustion is not optimality or infeasibility. |
| OPEN-07 validity mapping | Preserve raw exit code, infrastructure status, exact source/config/scope, output digest, semantic-pair result, and compliance observation as separate fields. Keep the frozen DA01 and MONO-A1 v1 interpretations visible. | Do not derive coverage from a P-side pair status or change a frozen checker mapping. |
| OPEN-08 ADD normalization | Record selected owner, grouped target-to-materialization mapping, deduplication/collision rules, Nop, Nmat, evaluator invocation count, and candidate digest. This is a new method/config identity if grouped behavior is selected. | Do not use the PR #42 lexical owner as an approved rule; do not run a case whose ADD mapping remains unresolved. |
| OPEN-09 identity, custody, and sealing | Bind the PR #42 manifest identity SHA-256 and image digest to each future run record. Keep method allowlists, holdout inventory, custodian permissions, prediction bytes/seal, and scorer outputs in separately inventoried stores. | Never mount reference/scorer/oracle data, .git, network, or other-arm outputs into a method run; do not start before reference readback and authorized run gates. |

The PR #42 source identity stays pinned. If a selected decision requires code or behavior changes, stop infrastructure integration until a new method version, manifest, tests, and independent review exist. No MONO run, scorer invocation, reference freeze, or G4 action is part of this handoff.

## I. Independent reviewer checklist and sign-off record

### Objective review outcomes

Mark each criterion PASS, FAIL, or UNRESOLVED. PASS requires source-backed evidence and an explicit rationale; FAIL identifies a contradicted requirement; UNRESOLVED means evidence, authority, reviewer independence, or contract compatibility is absent. UNRESOLVED never counts as PASS.

| Criterion | PASS only when | FAIL when | Current expected state before review |
| --- | --- | --- | --- |
| Identity | Manifest schema, canonical digest, all listed source/config bytes, pinned commit/tree, and checkout match independently. | Any hash, source, configuration, or method-version mismatch. | UNRESOLVED until independent readback record exists. |
| OPEN-06 cost/search | Unit, calibration, usage-count rule, finite search universe, bounds, exhaustion behavior, tie order, sensitivity plan, and comparator cost boundaries are fixed before outcomes. | Missing cost is treated as zero; search exhaustion is called optimal/infeasible; incomparable costs are silently combined. | UNRESOLVED. |
| OPEN-07 validity | Every case has distinct execution, compliance, exact-pair, coverage, and governance mapping; frozen DA01 and MONO-A1 v1 semantics are preserved or a new approved version is specified. | A P-side diagnostic is substituted for frozen reference validity or scorer semantics are changed in place. | UNRESOLVED. |
| OPEN-08 operation mapping | Owner/grouping/defer rule is selected before predictions; target IDs, duplicate/collision behavior, candidate identity, pair evidence, and cost counts are deterministic; no answer access. | Owner is selected from expected labels, duplicate target rows are silently accepted, or multi-use materialization collides. | UNRESOLVED. |
| OPEN-09 independence | Actual independent reviewers/custodian, conflict/exposure records, permissions, separation of duties, and holdout inventory custody are documented. | Method author controls reference/holdout or an invented reviewer/signature is presented. | UNRESOLVED. |
| Inputs and isolation | Method input inventory is digest-bound and excludes reference/scorer/oracle, .git, network, and other-arm output; selected-environment G2 evidence passes. | Forbidden inputs or unverified environment are present. | UNRESOLVED. |
| Seal and change control | Candidate/method is frozen before output; exact prediction bytes are write-once sealed before scoring; any behavior change gets a new version and review. | Post-seal edits or a changed algorithm retain the old identity. | UNRESOLVED. |
| G1/G4 boundary | G1 is recorded only after applicable decisions/reviews pass; G4 has a separate explicit authorization. | This package or synthetic test results are treated as approval/run permission. | G1 INCOMPLETE; G4 NOT AUTHORIZED. |

### Unfilled decision/sign-off record

No reviewer, decision, or signature is prefilled.

| OPEN item | Decision selected or amendment | Rationale and rejected alternatives | Contract/version impact | Reviewer role/name | Independence/conflict record | Date | Outcome PASS/FAIL/UNRESOLVED | Reviewer signature or approved sign-off record digest |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OPEN-06 |  |  |  |  |  |  |  |  |
| OPEN-07 |  |  |  |  |  |  |  |  |
| OPEN-08 |  |  |  |  |  |  |  |  |
| OPEN-09 |  |  |  |  |  |  |  |  |

Record the approved method/configuration identity, reviewed commit/tree, exact decision-register revision, required follow-up artifact, and separate G1/G4 status with the completed forms. Until then, all rows above remain proposals and G1/G4 remain unchanged.

## Sources

- [G1 method decision register](G1_METHOD_DECISION_REGISTER.md), OPEN-02…09.
- [G1 method specification](G1_METHOD_SPECIFICATION.md) and [SPEC 03](SPEC_03_IMPACT_ANALYSIS_AND_GOVERNED_ADAPTATION.md).
- [B0/B1/P comparability plan](B1_P_COMPARABILITY_PLAN.md).
- [MONO-A1 protocol](../experiments/execution/MONO_A1_PROTOCOL_V1.md), [DA01 scoring](../experiments/execution/da01/SCORE_RULES.md), and [DA01 validity](../experiments/execution/da01/VALIDITY_RULES.md).
- [W0 readiness resolution](MONO_E1_W0_READINESS_RESOLUTION.md) and reused [policy approval preparation](MONO_E1_POLICY_APPROVAL_PREPARATION_V1.md).
- [PR #42 executable candidate review](P_EXECUTABLE_CANDIDATE_REVIEW_V1.md), identity manifest, code, schemas, and tests listed above.
