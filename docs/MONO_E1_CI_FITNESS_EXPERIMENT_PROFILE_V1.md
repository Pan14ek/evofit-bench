# MONO-E1 CI fitness evaluation — candidate experimental protocol v1

> **Status:** DRAFT / SCIENTIFICALLY NON-AUTHORITATIVE. **No measured experiment or official scientific approval is authorized by this document.** It is an *additive proposal* relative to [MONO-A1 protocol v1](../experiments/execution/MONO_A1_PROTOCOL_V1.md), [W0 readiness](MONO_E1_W0_READINESS_RESOLUTION.md), [G1 decision register](G1_METHOD_DECISION_REGISTER.md), and the merged [MONO-E1 comparability preflight](../experiments/execution/MONO_E1_COMPARABILITY_PREPARATION_REPORT_V1.md). Frozen DA01 protocols, scoring, seals, source pins and other research evidence are unchanged.

## 1. Publication target, research claim and scope

The immediate publication target is the **scientific monograph** on the model and method of governed fitness-function configuration adaptation. The method's object is the versioned configuration `Φ` (criteria, stage-specific representations, policy rules, evidence links and invariants), **not** the application's architectural quality score alone. This study concerns the **fitness controls themselves**, not only CI job success.

**MONO-E1 scientific question:** On the independently pinned Reporting-to-Tasks public query-port refactor A0.3→A0.4, can Method P distinguish a changed architecture from a reason to change architectural fitness controls, and avoid unjustified changes while preserving adequate control *within the approved experimental scope*?

The candidate empirical scope is **CI/test only**, not deployment, runtime, or a proof of full lifecycle-wide control. Continuity here means preservation of relevant CI architectural control *across architectural states*. Whether one or several lifecycle stages are mandatory for each obligation is still an OPEN-03 scientific/policy decision. A CI-only result must not be reported as demonstrated deployment/runtime end-to-end coverage.

The transition is an **a priori negative-control scenario** already documented publicly. It is **not a blinded holdout**. The independently formulated reference must be frozen and kept scorer-side, and neither P nor its authoring/runner inputs may receive private expected operation rows.

## 2. Fixed architecture identities (source identity only)

| | Architecture state | Exact commit | Exact Git tree |
|---|---|---|---|
| Before | `A0_3_GOVERNED_MODULE_GRAPH` | `26a9bb667da7d0938e38aca15d2bf29fd1de4829` | `7b951421395f532ca403dab09d76902ff08a807d` |
| After | `A0_4_REPORT_QUERY_PORT` | `d3101c0d3aa9b7b709253b6ec7518416f05f65b9` | `2b436e0aaf09403ea516d73d20a466a122f86592` |

The source-bound engineering acceptance reports establish the pinned refactor and bounded static checks. Their PASS status is **not** an independent fitness representation–obligation coverage proof, an approved policy denominator, or an experimental P result.

## 3. What is the fitness function in this experiment?

Use the conceptual trace: `architectural criterion → normative obligation q → stage-specific representation r → evaluator/metric → evidence → Method P adaptation decision → candidate configuration Φ'`. A runnable evaluator is an *implementation* of a fitness representation, whereas the normative obligation defines the property to control.

**Candidate engineering evaluator inventory (not an approved scientific mapping):**

| Engineering evaluator | Candidate linked obligation | Observed control and limits | Required next action |
|---|---|---|---|
| `AC_PUBLIC_API` | `AC_PUBLIC_API` | Checks cross-module public API use on source-bound A0.4 scope | Assign a real representation ID, reviewer-approved semantic match, required stage, raw execution/inspection proof, positive and negative control |
| `AC_MODULE_GRAPH` | `AC_MODULE_GRAPH` | Checks graph direction/cycles within source scope | Same exact-pair and stage review, including non-vacuous inspection |
 
**Do not assume** that an evaluator ID equals a representation ID, or that a YAML `covers` declaration establishes adequacy. Source observation paths are pinned in `docs/mono_e1_ci_fitness_profile_v1.json`; they are *engineering* evidence only. A checker that detects a violation can still be a technically suitable monitor; distinguish (i) source-bound execution, (ii) semantic fitness of the pair, and (iii) architecture compliance. The existing frozen DA01/MONO v1 counting rules must not be retroactively reinterpreted.

**Catalog boundary:** the obligation catalog contains **18 IDs**, but their A0.4 applicability, mandatory status, stage obligations, closure and complete `Q(A0.4)` remain unresolved. The candidate JSON carries *all 18* as UNKNOWN/UNRESOLVED; this is not a two-obligation scientific denominator. A bounded **CI experimental subset** is permissible *only after* an explicit versioned review explains what was selected, what was excluded, by whose authority, and which claims are no longer made. `AC_DATA_OWNERSHIP` evaluator's engineering NOT_APPLICABLE state cannot deactivate that normative obligation.

## 4. Study treatments and comparability

- **B0:** unchanged source fitness configuration under the *same pinned A0.4 target*. No semantic adaptation is performed.
- **P:** reviewed generic Method P using permitted common facts/policies/capabilities, with any permitted P-specific traceability recorded as a treatment distinction. `P_ALGORITHM_STATUS=NOT_READY` until an independently reviewed, digest-pinned version is frozen. No scenario-specific patch or expected-answer rule.
- **B1:** out of scope for this monograph case study; no synthetic human baseline.

Before any measured comparison, materialize read-only **separate and digest-bound** input bundles and allowlists, common target/source and evaluator capabilities, configuration lineage, matched timing boundaries, and runner/image/source provenance. Keep private oracle/reference/scorer, `.git`, network access and cross-arm outputs out of both method containers. The PR #44 preflight currently returns `INCOMPLETE / NO_GO`; this proposal does not change that result.

**Workload and database fixture decision:** The wide MONO v1 preflight requires a common deterministic workload and disposable PostgreSQL fixture. A proposed *static-CI-only* study might justify a different common-input profile, but those prerequisites are **not waived** by this document. A reviewed, versioned protocol and corresponding verifier are needed before the readiness outcome may change. Do not modify the old preflight to force GO.

## 5. Endpoints, interpretation and failure handling

| Endpoint | Definition for prospective measured study | Guard |
|---|---|---|
| **Operation/impact correctness (RQ1)** | Target-level predictions versus a *pre-declared* independently justified reference; report precision, recall, F1 and operation correctness where defined | No reference or no valid sealed prediction → NOT_EVALUABLE, not 0 or 100% |
| **Verified fitness-obligation coverage (RQ2)** | Number of distinct active, mandatory and independently supported obligations divided by a single approved shared `Q(A0.4)` denominator | Unknown denominator → UNKNOWN/NOT_EVALUABLE; one evaluator may support two obligations **only** through two independently proved pairs |
| **Uncertainty and governance (RQ4 manuscript)** | Record ACCEPT/REJECT/HOLD/INPUT_REJECTED, unresolved requirements, invalid/vacuous execution and missing evidence separately | No false ACCEPT; a candidate with diagnostic partial coverage is not automatically accepted |
| **Measurement cost (RQ3 manuscript)** | Paired adaptation, evaluator, evidence-validation and arm-total timing with comparable boundaries | Times remain null until actually measured; report CPU/RSS only if sampled |

A known-negative-control outcome may yield **equal** B0/P verified coverage and a correct no-change adaptation decision: a superiority claim is neither required nor implied. A Method P HOLD due to genuine missing mandatory proof is not counted as successful retain. Positive adaptation (ADD/REPLACE, recovered control) requires a **separate scenario** (currently MONO-E2 / completion of A1 or separately reviewed controlled case) before general claims of maintained control are made.

The experiment has **one architectural transition** as its unit. Multiple invocations of the same evaluator/method are technical repetitions, *not* independent architecture samples. Report paired descriptive outcomes, exact inputs, repetitions, raw traces, failures and limitations; no unsupported population significance or cloud-runtime generalization. Keep the monograph RQ labels separate from frozen executable RQ labels as documented in `docs/RESEARCH_CONTEXT.md`.

## 6. Pre-run scientific decisions — not delegated to CI or an AI agent

1. **Policy authority and completeness / OPEN-04:** accountable human owner and independent reviewer approve the state-specific normative scope and classification of all applicable catalog/extension obligations. DRAFT/OPEN policy is not a source of approved applicability.
2. **Lifecycle / OPEN-03:** decide and version the mandatory stage set (CI_TEST only where independently justified; deployment/runtime if actually required), or explicitly bound an independent CI-only research subset without claiming full multistage coverage.
3. **Exact-pair evidence / OPEN-05/07:** independent stage- and source-specific suitability assessment; real representation/evaluator binding, raw bytes/digests, non-vacuous inspected scope and positive/negative controls. Separate execution failure, monitoring fitness and architecture violation.
4. **Algorithm/scoring / OPEN-02/06/08/09:** settle the method version, deterministic search/cost budget, operation units (one evaluator may cover multiple obligations), sample unit, reference protocol, thresholds/unknowns and scorer compatibility *before* execution. Preserve frozen V1 target/scoring contracts.
5. **Reference and custody:** independently justify the scorer-side expected operation/reference rows for the exact after-SHA, mark `AUTHOR_DECLARED` if no true independent review, enforce one-time sealing/readback and prevent leakage.
6. **Comparable execution environment:** resolve B0/P identities, allowlists, workload/fixture scope disposition, images, exact source provenance, timings and preflight.
7. **G1 then G4:** complete real independent review and separate measured-run authorization under the study's approved protocol. No AI-generated signoff, pseudo-key or inferred institutional appointment is accepted.

### Minimum review gate

A draft of this document plus a complete catalog inventory can be reviewed now. **Measured B0/P execution remains NO-GO** until the applicable authority, evidence, reference, comparability, and separate authorization prerequisites actually pass. No `freeze_reference`, scorer call or MONO-E1 run is part of this PR.

## 7. Concrete work packages after approving the protocol

- **WP1:** approve the scoped CI study contract and full catalog disposition with versioned, human evidence; register stage decisions and explicit unknown handling.
- **WP2:** register genuine representation IDs; bind `AC_PUBLIC_API` and `AC_MODULE_GRAPH` to approved obligation-stage pairs and independently validate exact source/semantic evidence. Add pairs only after materialization.
- **WP3:** produce an independent scorer-side reference at the exact pinned state, with write-once custody and no public expected operation rows.
- **WP4:** export and verify actual B0/P input bundles, common evaluator capabilities, frozen P identity, environment and provenance; update **additive** static-CI preflight if approved rather than rewriting the wide V1.
- **WP5:** after G1/G4, execute both arms against exactly the same A0.4, capture raw evidence, seal outputs, calculate only supported endpoints and populate the monograph result tables.
- **WP6:** run a separately approved positive adaptation scenario. Do not treat this negative control as evidence for successful ADD/REPLACE or all-stage cloud-native runtime.

## 8. Traceability and preflight invariants

The sibling machine-readable [candidate profile](mono_e1_ci_fitness_profile_v1.json) is public **preparation metadata only**, never a Method P input or scorer oracle. The new test `tests/unit/test_mono_e1_ci_profile.py` checks that the exact architecture pins and ordered 18-catalog inventory are preserved and refuses accidental approved/GO/frozen status or assertion that two engineering gates close the scientific denominator.

This proposal requires **no change** to `P_ALGORITHM_STATUS`, DA01 input/scoring/reference contracts, MONO v1 schemas, sealed evidence, G1/G4 decision registers, or actual experimental data. Any future change needs a separately versioned reviewed PR.
