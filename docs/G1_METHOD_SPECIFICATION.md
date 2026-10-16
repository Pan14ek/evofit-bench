# G1 Method P specification — review draft

**DRAFT — NOT INDEPENDENTLY APPROVED**

**Review source revision:** prepared branch commit 02c1654f457fd1cf685fd449b552d6e35701ea54, based on main at 740c60aeece6e424c56ba081eacc079dc0f16d74 (PR #10 merged).
**Status:** documentation for independent methodological review. This is not a frozen method, G1 approval, G4 authorization, or a measured result.
**Proposed reviewers:** independent architecture-method researcher; formal-methods reviewer; evaluator-validity specialist; research-integrity reviewer.

## 1. Problem, object, and contribution claim

Architecture evolution can leave a fitness-configuration syntactically runnable while its evaluators no longer match the architecture, their scopes, or the obligations they claim to control. Method P concerns changes to that fitness configuration. It does not change the application architecture.

The proposed method is an evidence-gated procedure for identifying potentially affected controls, checking exact representation–obligation pairs, selecting the smallest justified configuration change, materializing a versioned candidate from available artifacts, and returning a governed decision. Its scientific claim is conditional and falsifiable: under a preregistered, fair comparison, a frozen P version may improve affected-target/operation identification and independently demonstrated mandatory coverage over frozen B0 and a genuinely independent human B1, subject to declared adaptation cost. No superiority, novelty, generalizability, or operational benefit is established by implementation or synthetic tests.

Engineering implementation, methodological specification, and scientific evidence are different:

| Layer | Current evidence | What it does not establish |
| --- | --- | --- |
| Engineering | SPEC 01/02/03 DEVELOPMENT code, schemas, regression tests, and TEST_ONLY end-to-end no-op/ADD cases | Production authority, a frozen method, or measured effectiveness |
| Method | This proposed formal description, the parent SPEC 03, and unresolved OPEN decisions | Independent correctness or G1 freeze |
| Science | No measured DA01 B0/B1/P outcomes are authorized or reported | Any effect, significance, or cross-transition generalization |

## 2. Formal vocabulary and configuration model

Let **Aₜ** be an architecture state identified by its source revision and verified structural observations. **ΔAₜ** is the typed difference between the before and after states. **Πₜ** is the versioned normative policy source; policy changes are represented separately as **ΔΠₜ**. Architecture facts, policy rules, observations, and evaluator outputs are not interchangeable.

Let **Q** be the catalog of architectural obligations. For **q ∈ Q**, applicability asks whether an authorized normative rule requires control of q in a given state. It does not say whether the architecture complies.

Let **Cₜ** be stable criterion intents and hard constraints. A criterion records its intended property, scope, applicable obligation links, policy basis, version, provenance, and trace links. Let **Rₜ** be concrete fitness representations, indexed by lifecycle stage where specified. A representation identifies an evaluator or metric, target scope, execution policy, evidence contract, artifact identity, and the obligations it purports to cover.

The versioned configuration model is:

    Φₜ = ⟨Cₜ, Rₜ, αₜ, θₜ, Hₜ, vₜ⟩

Here **αₜ** denotes optional weights, **θₜ** optional soft-threshold rules, **Hₜ** approved hard invariants, and **vₜ** configuration and provenance identity. The core adaptation described here does not optimize or adapt α or θ. Any later change to them is outside core P v1 and is deferred under OPEN-10.

The evidence-bearing knowledge state is:

    Kₜ = ⟨Zₜ, Πₜ, Γₜ, νₜ⟩

**Zₜ** is the typed architecture-fact set; **Γₜ** is the bounded evidence and completeness information; **νₜ** binds source revisions, scopes, policy/ruleset versions, timestamps, and provenance. Hashes establish byte identity, not authority, completeness, or factual truth.

**G_T** is a typed traceability graph connecting facts and policy decisions to obligations, criteria, representations, evaluators, and evidence contracts. Missing edges in an incomplete graph do not prove non-impact.

For a representation **r**, obligation **q**, target architecture **A**, and evidence **E**, pair validity is:

    V(r,q,A,E) ∈ {VALID, INVALID, UNKNOWN}

VALID requires current revision and scope, applicable stage/context, resolved nonvacuous evaluator artifact, pair-specific semantic match, adequate evidence, and admissible provenance. INVALID requires a demonstrated contradiction or failed necessary condition. Missing, stale, conflicting, or unverified proof is UNKNOWN.

## 3. Decisions that must remain separate

| Judgment | Question | Not established by |
| --- | --- | --- |
| Applicability | Does approved policy require q to be controlled in A? | A passing evaluator, a trace edge, or an observed fact alone |
| Compliance | Does architecture A satisfy the applicable requirement? | Applicability or an evaluator’s successful execution |
| Representation validity | Does r measure the intended q in the current scope, stage, and context? | A covers field, metric name, exit code zero, or another pair’s verdict |
| Mandatory coverage | Is every required obligation supported by at least one valid exact pair and execution verdict? | Aggregate fitness score, duplicate controls, or an incomplete denominator |
| Governance | Is the materialized, versioned candidate admissible under all required proof and safety conditions? | A positive policy decision, synthetic ACCEPT, or green CI |

SPEC 02 applicability is three-valued:

    g_q(Kₜ) ∈ {ACTIVE, INACTIVE, UNKNOWN}

The implementation uses evidence-aware Strong Kleene evaluation. Negative applicability needs verified completeness for the exact predicate/type, scope, source revision, registry version, and evaluation time. Absence in an open registry, missing facts, conflicting rules, or missing authority yields UNKNOWN rather than INACTIVE. Applicability is not architecture compliance.

## 4. Versioned inputs, preconditions, and provenance

The development input path is a strict, version-pinned V3 P bundle. Its manifest binds allowlisted file roles and digests, source revisions, architecture-policy Snapshot, the separately pinned policy source/ruleset, parent configuration, traceability, evidence, and available evaluator/template artifacts. P reads only the manifest’s named inputs; it must not discover data by walking a checkout.

SPEC 01 Snapshot v1.1 remains the existing contract. Snapshot v1.2 is an additive, unfrozen DEVELOPMENT extension used by the V3 pipeline to bind before/after registry-closure claims independently. The V2 exporter continues to emit v1.1. The v1.2 extension does not amend a frozen DA01 or V1/V2 contract. See the [v1.1 schema](../experiments/execution/schemas/architecture_policy_snapshot_v1_1.schema.json), [v1.2 development schema](../experiments/execution/schemas/architecture_policy_snapshot_v1_2.schema.json), and [v1.2 note](../experiments/execution/P_INPUT_V12_DEVELOPMENT.md).

### Formal development input and output contract

Let **Xₜ** be the manifest-allowlisted bundle: before/after architecture revisions and structural evidence; Snapshot and source bindings; policy/ruleset and obligation catalog; representation catalog and parent configuration; permitted trace graph; evidence ledger/sidecars; and only those evaluator/template bytes and authorization descriptors named by the bundle. Each object is versioned, scoped, hashed, and provenance-bound. No oracle, scorer, answer list, other-method output, repository history, or network input is admissible.

The development output is:

    Yₜ = ⟨g_before, g_after, Iₜ, V_current, V_candidate,
          Coverage_current, Coverage_candidate, Oₜ, Φ′ₜ, Dₜ, Auditₜ⟩

Here **g_before/g_after** are applicability assessments; **Iₜ** is typed impact; **V** and **Coverage** contain exact-pair and mandatory-coverage assessments; **Oₜ** is the deterministic operation plan; **Φ′ₜ** is either a fully materialized child candidate or absent; **Dₜ** is the governance decision; and **Auditₜ** carries bound versions, digests, reasons, blockers, and evidence references. A missing or invalid prerequisite must not be replaced with an invented field value. The compatibility prediction and candidate projections are emitted only for the exact sealed ACCEPT decision. These are DEVELOPMENT schemas and behaviors, not a promise of measured-interface readiness.

Before assessment, the pipeline verifies bundle role/path allowlists, schema versions, source pins and hashes, architecture revisions, policy-source identity, fact and completeness evidence, and parent configuration identity. An invalid schema, digest, or binding is INPUT_REJECTED. Missing trust, authority, or completeness is unresolved evidence: it must remain UNKNOWN and can lead to HOLD. Never convert absent proof to a successful negative fact. Hash consistency alone is not policy approval.

For a policy-only revision with the same architecture SHA, the policy delta is still assessed. The policy source revision and ruleset digest remain bound in the impact and governance records.

## 5. Typed differences and conservative impact

The proposed typed difference is:

    Δₜ = Diff(Zₜ,Zₜ₊₁) ∪ Diff(Πₜ,Πₜ₊₁) ∪ Diff(Qₜ,Qₜ₊₁)
    Seedₜ = Map(Δₜ, G_T)
    Iₜ = Reach_G_T(Seedₜ) ∪ Uₜ₊₁ ∪ Lₜ

The difference records entity kind and identity, change kind, predicate, subject, old/new scopes, value digests, versions, evidence references, and reason codes. Typed graph traversal may identify causal paths; it does not itself prove invalidity.

Let **Uₜ₊₁** be the set of currently mandatory obligations not demonstrated by a valid pair, and **Lₜ** the set of unresolved trace links or inventory omissions. The graph-reachable representation set is conservative; its members are not automatically invalid.

Each representation receives one conservative impact state:

| State | Meaning |
| --- | --- |
| PROVEN_AFFECTED | A supported typed path or direct bound change establishes an effect |
| POSSIBLY_AFFECTED | A relevant path exists but does not prove semantic invalidity |
| NOT_AFFECTED_WITH_PROOF | Complete, verified inputs and graph establish no relevant change |
| UNRESOLVED | Missing edges, incomplete inventory, or uncertain evidence prevent classification |

An uncovered newly/currently mandatory obligation is considered even if the previous graph lacks a link. An absent edge in an incomplete graph yields possible impact or unresolved status, never proof of no impact. The implementation reports paths and evidence references and binds the result digest to architecture, policy, ruleset, Snapshot, and graph versions.

## 6. Exact-pair semantics and mandatory coverage

For every relevant pair **(r,q)**, the method assesses target revision, scope, stage/context, evaluator availability and artifact digest, resolved targets and inspected subjects, semantic mapping, evidence-contract adequacy, evidence references, and provenance. A pair cannot inherit validity from another obligation or from a representation-wide verdict.

The independent DA01 validity procedure separately checks evaluator execution and exact-pair semantic/evidence validity. The method’s development assessment is not the independent reference verdict. A valid method-side prediction does not certify compliance; the independent checker is not a P input.

For later approved method contracts, mandatory coverage is complete only when each mandatory obligation in the authorized applicable set has at least one valid execution verdict and one valid, version-compatible exact-pair verdict. Count each obligation once. A representation covering multiple obligations needs a separate valid pair for each. Unknown mandatory applicability or an unknown stage contract cannot be dropped to make the denominator smaller.

OPEN-03/M-04 remain unresolved: a general lifecycle-stage registry is not approved. Do not add multi-stage obligations to the frozen DA01 denominator. DA01 RQ2 uses its existing private complete required-obligation denominator and exact-pair rule; Method P inputs do not receive the private denominator or expected pairs.

OPEN-07 remains unresolved: a true architecture noncompliance and invalid/unavailable monitoring can lead to different interpretations under the frozen reference verdict rules. This draft preserves their separate reporting and does not change scorer semantics.

## 7. Operation choice and candidate construction

The DEVELOPMENT planner considers **retain**, **add**, **replace**, **deactivate**, and **adjust**. It does not author evaluator code.

| Operation | Necessary justification |
| --- | --- |
| retain | Existing control is still demonstrated semantically adequate for the target pair; an impacted retain requires positive current proof |
| add | A mandatory obligation lacks verified coverage and an authorized, materializable evaluator artifact is available |
| replace | Existing representation is proved unsuitable and a compatible authorized replacement artifact is materializable |
| deactivate | Exact policy-backed INACTIVE proof exists and no other ACTIVE or unresolved mandatory obligation still depends on the representation |
| adjust | Only a pre-authorized bounded soft parameter may change; stable intent, hard constraints, and mandatory coverage remain fixed |

Template labels or evaluator bytes alone do not authorize an operation. A materializable template requires a validated full descriptor digest, a signed/verified authorization binding, a pinned artifact digest, and matching artifact bytes. If a required evaluator cannot be materialized, report a blocker/NEEDS_IMPLEMENTATION and do not fabricate a candidate.

Among feasible plans the DEVELOPMENT planner uses a deterministic bounded choice: minimize operation count, then authorized incremental cost, then stable identifiers. Cost units, admissible bounds, tie/collision policy across real evaluator families, and the meaning of an exhausted search remain OPEN-06. The multi-obligation ADD to single-target V1 mapping remains OPEN-08; DEVELOPMENT normalization is not approved DA01 scoring semantics.

Candidate Φ′ is built as a child of the exact parent configuration. It binds the parent digest, before/after architecture, policy and ruleset versions, operation plan, evaluator/template digests, semantic and coverage assessments, and deterministic child version. Prior configurations and decision history remain immutable. V1 candidate/prediction adapters expose output only after a sealed governance ACCEPT.

## 8. Governance, rollback, and twelve invariants

The decision set is **INPUT_REJECTED**, **REJECT**, **HOLD**, or **ACCEPT**:

| Result | Meaning |
| --- | --- |
| INPUT_REJECTED | Input integrity/contract is invalid or tampered; this is distinct from a fitness rejection |
| REJECT | Trustworthy evidence proves a hard invariant, candidate, cost, or mandatory-coverage failure |
| HOLD | No hard failure is established, but required authority, evidence, candidate validation, cost, applicability, or pipeline proof is missing or conflicting |
| ACCEPT | Every required invariant, mandatory coverage, semantic/evidence, provenance, candidate, cost, and authorized pipeline condition is positively verified |

The order matters: invalid input is rejected first; proven hard failure is REJECT; unresolved prerequisites are HOLD; ACCEPT is possible only with positive proof. Decision records bind versions, digests, operations, pairs, evidence references, blockers, reason codes, and invariant verdicts. Publication is disabled in the current module; a TEST_ONLY ACCEPT does not publish production state.

Rollback is conditional. Revalidate the proposed previous configuration against the current architecture and policy context. If neither the candidate nor rollback target is positively valid, leave the transition unresolved. The code includes development rollback checks; continuous monitoring, production publication, and an atomic compare-and-swap writer are not established.

All twelve invariants carried forward from SPEC 03 are mandatory method requirements:

| ID | Invariant |
| --- | --- |
| INV-01 | Criterion intent and approved hard constraints cannot silently be weakened. |
| INV-02 | INACTIVE/deactivate requires verified normative negative proof for exact scope and completeness; UNKNOWN is never INACTIVE. |
| INV-03 | Do not deactivate r while another ACTIVE or UNKNOWN mandatory q may still need it. |
| INV-04 | Mandatory positive coverage requires correct, nonvacuous, current, exact-pair evidence, not a pass flag, field, or aggregate. |
| INV-05 | Wrong authority, time, revision, provenance, digest, or stale validation never yields positive proof. |
| INV-06 | ADD/REPLACE requires a real materializable, digest-pinned, authorized evaluator/template; never invent a checker. |
| INV-07 | Retain on impacted r requires positive semantic adequacy; implicit unchanged retain is not verified coverage. |
| INV-08 | Use stable identifiers, canonical serialization, unique targets, parent-hash binding, and immutable history. |
| INV-09 | Proposed operations and V1 non-retain affected targets must agree; duplicates and conflicts are forbidden. |
| INV-10 | Never ACCEPT with invalid/unresolved mandatory coverage; HOLD cannot publish; rollback requires fresh current-state validation. |
| INV-11 | Semantic decision, order, and hash are deterministic for identical inputs and method version; timestamps are external. |
| INV-12 | No oracle or scenario-specific expected-answer access and no hardcoded DA01/obligation-ID logic. |

## 9. General algorithm

The following is the intended DEVELOPMENT sequence, not a claim that P is frozen or ready for a measured DA01 run:

    verify V3 manifest and allowlisted bytes
    validate versioned Snapshot, authority, facts, completeness, and source bindings
    if integrity/schema/binding is invalid: return INPUT_REJECTED
    assess before and after obligation applicability with SPEC 02
    if essential authority/completeness is unknown: preserve UNKNOWN and blockers
    compute typed architecture/policy/obligation differences
    traverse the versioned typed graph conservatively; retain unresolved links
    assess current and candidate exact representation–obligation pairs
    compute mandatory coverage without shrinking an unresolved denominator
    build a deterministic bounded operation plan from verified artifacts only
    materialize a child candidate and validate its schema and semantic invariants
    decide REJECT for proved hard failure; HOLD for missing/conflicting proof
    ACCEPT only when all twelve invariants and all positive proof conditions pass
    emit V1-compatible outputs only for the exact sealed ACCEPT
    publish only through an independently authorized atomic writer (currently disabled)
    rollback only after fresh validation in the current context

## 10. Implementation/status crosswalk

| Mechanism | Current status | Source-to-model mapping |
| --- | --- | --- |
| V3 manifest, Snapshot, authority/fact/completeness preflight | IMPLEMENTED_DEVELOPMENT; production trust is PENDING_EXTERNAL_AUTHORITY | [p_policy_source_v3.py](../experiments/execution/tooling/p_policy_source_v3.py), [p_input_validation.py](../experiments/execution/tooling/p_input_validation.py), [Snapshot v1.1 schema](../experiments/execution/schemas/architecture_policy_snapshot_v1_1.schema.json), [Snapshot v1.2 schema](../experiments/execution/schemas/architecture_policy_snapshot_v1_2.schema.json) |
| Three-valued applicability and V3 policy source | IMPLEMENTED_DEVELOPMENT; pilot authority remains DRAFT/OPEN | [p_applicability.py](../experiments/execution/tooling/p_applicability.py), [policy-source schema](../experiments/execution/schemas/policy_source_v3.schema.json) |
| Typed impact and conservative graph classification | IMPLEMENTED_DEVELOPMENT | [p_impact.py](../experiments/execution/tooling/p_impact.py), [impact schema](../experiments/execution/schemas/p_impact_assessment_v1.schema.json) |
| Exact-pair assessment and mandatory coverage | IMPLEMENTED_DEVELOPMENT; independent measured evidence remains pending | [p_semantic.py](../experiments/execution/tooling/p_semantic.py), [validity rules](../experiments/execution/da01/VALIDITY_RULES.md) |
| Deterministic operations and authorized materialization | IMPLEMENTED_DEVELOPMENT; real artifacts/cost authority remain pending | [p_operations.py](../experiments/execution/tooling/p_operations.py), [p_candidate.py](../experiments/execution/tooling/p_candidate.py) |
| Candidate versioning, V1 adapters, governance, event history, rollback checks | IMPLEMENTED_DEVELOPMENT; production publishing disabled | [p_candidate.py](../experiments/execution/tooling/p_candidate.py), [p_governance.py](../experiments/execution/tooling/p_governance.py) |
| End-to-end V3 no-op and ADD TEST_ONLY acceptance | IMPLEMENTED_DEVELOPMENT synthetic evidence in merged PR #10 | [SPEC 03 implementation traceability](SPEC_03_IMPLEMENTATION_TRACEABILITY.md) |
| Measured-method interface and independent algorithm freeze | NOT_READY / PENDING_INDEPENDENT_REVIEW | [P algorithm status](../experiments/execution/da01/P_ALGORITHM_STATUS.md), [DA01 readiness](../experiments/execution/da01/READINESS.md) |
| Authentic policy/evaluator authority and trusted completeness | PENDING_EXTERNAL_AUTHORITY | OPEN-04 and OPEN-05 in [decision register](G1_METHOD_DECISION_REGISTER.md) |
| B1 cadence, cost/search rules, verdict reconciliation, multi-obligation ADD | PENDING_INDEPENDENT_REVIEW | OPEN-01, OPEN-06, OPEN-07, and OPEN-08 in the [decision register](G1_METHOD_DECISION_REGISTER.md) |
| α/θ adaptation and lifecycle-stage extension | DEFERRED | OPEN-03 and OPEN-10; no such benefit is claimed |

The merged code is more complete than earlier descriptive paragraphs in the research and architecture handbooks, which still describe some SPEC 03 mechanisms as planned/not implemented. This table and the final PR #10 section of the implementation traceability report describe the current DEVELOPMENT code; neither changes the DA01 protocol nor raises P readiness.

## 11. Falsifiable claims, limitations, and review decisions

Candidate claims for later preregistration are that P can improve (a) typed affected-target and operation identification and (b) valid mandatory coverage, compared separately with frozen B0 and human B1, while adaptation cost is measured. These claims can be falsified by lower target accuracy, lower independently evidenced coverage, unjustified changes, unsafe ACCEPT, or unacceptable cost under a predeclared protocol. No numerical margin or endpoint hierarchy is approved here.

DA01 contains one architecture transition. It can support a descriptive case demonstration only, not population-level significance, cross-stack generalizability, runtime improvement, or a causal claim about α/θ. Additional independently designed transitions and external validation would be required for broader inference.

Unresolved assumptions and decisions include B1 cadence (OPEN-01/M-01), RQ crosswalk and endpoint hierarchy (OPEN-02/M-02/M-06), lifecycle stages (OPEN-03/M-04), policy and evaluator authority (OPEN-04/05), cost/bounded search (OPEN-06), compliance versus monitor invalidity (OPEN-07), multi-obligation ADD scoring (OPEN-08), holdout/freeze custody (OPEN-09), and α/θ (OPEN-10/M-05, deferred). The complete docket is in the [decision register](G1_METHOD_DECISION_REGISTER.md).

## 12. Source index and verification boundary

Normative DA01 sources are [PROTOCOL](../experiments/execution/da01/PROTOCOL.md), [SCORE_RULES](../experiments/execution/da01/SCORE_RULES.md), [VALIDITY_RULES](../experiments/execution/da01/VALIDITY_RULES.md), [INPUT_ISOLATION](../experiments/execution/da01/INPUT_ISOLATION.md), [B1_CHECKLIST](../experiments/execution/da01/B1_CHECKLIST.md), and [READINESS](../experiments/execution/da01/READINESS.md). The proposed model is in [SPEC 03](SPEC_03_IMPACT_ANALYSIS_AND_GOVERNED_ADAPTATION.md); synthetic implementation evidence and limitations are in [SPEC 03 traceability](SPEC_03_IMPLEMENTATION_TRACEABILITY.md) and [P governed adaptation development](../experiments/execution/P_GOVERNED_ADAPTATION_V1.md).

Permitted synthetic verification sources include the SPEC 03 implementation traceability report and DEVELOPMENT test names listed there, including [impact tests](../tests/unit/test_p_impact_v1.py), [semantic-pair tests](../tests/unit/test_p_semantic_pairs_v1.py), [operation tests](../tests/unit/test_p_operations_v1.py), [register tests](../tests/unit/test_g1_method_decision_register.py), and [synthetic V3 integration tests](../tests/integration/test_p_applicability_v3.py). These are engineering evidence only.

This review package does not inspect DA01 private ground truth, scenario-specific expected operations, protected test-module internals, private scorer/oracle code or output, sealed predictions, or another method’s outputs. It creates no measured prediction and changes no frozen score, validity, workload, seed, or method-input contract.
