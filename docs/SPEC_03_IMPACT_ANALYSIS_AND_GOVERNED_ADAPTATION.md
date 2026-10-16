# EvoFitBench — SPEC 03: Impact Analysis & Governed Adaptation

**ID:** EVOFITBENCH_SPEC_03_V1_DRAFT  
**Status:** PROPOSED DEVELOPMENT SPECIFICATION — not a frozen scientific algorithm; not authorization for measured DA01  
**Reviewed main:** da96862518a385a41b2451612a29f9b33bd5dae5 (after merged PR #7), 2026-10-16  
**Deliverables:** technology-agnostic formal method P, implementation contracts, SPEC 01–03 Verification & Validation Test Plan and Test Traceability Matrix.  
**Approval:** review scientific open decisions before G1; ordinary code and synthetic tests may proceed beforehand.

> This is a **design proposal**, based on the working manuscript ``2–5, `docs/RESEARCH_CONTEXT.md` and current EvoFitBench contracts. It does not silently amend an experiment protocol, declare approved policies, or assert empirical scientific results.

## 0. Read-first, precedence and prohibited data

Read `AGENTS.md`, root and ancestor `CONTEXT.md`, `docs/RESEARCH_CONTEXT.md`, `docs/DOMAIN.md`, `docs/ARCHITECTURE.md`, `docs/EXPERIMENT.md`, `docs/TESTING.md` and implementation journals `experiments/execution/P_INPUT_V11.md` and `P_APPLICABILITY_V1.md`. For executable experimental rules, defer to `experiments/execution/da01/PROTOCOL.md`, `INPUT_ISOLATION.md`, `VALIDITY_RULES.md`, `READINESS.md`, `B1_CHECKLIST.md` and exact schemas/source.

The manuscript is authoritative for **scientific intent**; protocol, tested implementations and pinned artifacts for **current execution semantics**. The RQ numbering, human B1 cadence, lifecycle coverage and weights/thresholds discrepancies documented in `docs/RESEARCH_CONTEXT.md` remain OPEN. Do not reconcile them by editing frozen files.

**Strict prohibition:** Never inspect, import, infer from, or incorporate the DA01 private ground truth, scenario-specific expected operations, oracle, independent scorer, another method's outputs or an engineering-acceptance reference checker into P selection logic or fixtures. Do not modify frozen A0/DA01 states, evaluator, evidence, workload/seed, scoring, predictions, V1 method inputs, or historic tags. Method input may not access `.git`, network, scorer, oracle or another method's output. Do not fabricate approved mandates, trust anchors, completeness, human B1 results or scientific outcomes.

G1 = independent review/freeze of general method/protocol; G4 = explicit authorization for **measured** DA01. They do **not** block regular implementation and synthetic tests.

### 0.1 Verified baseline contracts

| Artifact | Current status and required compatibility |
| --- | --- |
| SPEC 01: `p_input_validation.py`, `p_input_export_v2.py`, Snapshot v1.1 | DEVELOPMENT; strict hashes/source/APA/FV/completeness; 12 activation-grade FV_CORE_V1 predicates; V2 candidate B1/P input. |
| SPEC 02: `p_applicability.py`, `p_policy_source_v3.py` | DEVELOPMENT; Strong Kleene `ACTIVE/INACTIVE/UNKNOWN`; 18 obligations; separately pinned policy V3; DRAFT/OPEN pilot **not** approved. |
| `fitness/catalog/architectural-obligations.yaml` | 3 performance, 7 reliability, 8 architecture compliance. Default 1.0 weights are not scientific priority proof. |
| `fitness/traceability/a0-traceability.yaml` | Partial A0 graph; no completeness guarantee for evolved architectures. |
| `fitness/catalog/a0-fitness-elements.yaml` | Five A0 stage-specific representations; field `covers` alone does not prove coverage. |
| `prediction.schema.json` v1 | `target_type=obligation` permits only `add`; `target_type=representation` permits `retain/replace/deactivate/adjust`. Non-retain `predicted_affected` and `proposed_operations` must agree. No HOLD field. |
| `candidate_configuration.schema.json` v1 | Candidate configuration, parent hash, representations and local validation; `candidate_validation=valid` is **not** ACCEPT. |
| `obligation_verdict.schema.json`, `coverage_assessment.schema.json` | Independent pair-specific semantic evidence/coverage for scoring; private reference outputs must never become P inputs. |
| `experiments/execution/tooling/inputs.py` | Shared B1/P capability names exist, but `generic_candidate_templates=[]`: no executable generic replacement/add template currently exists. |
| `p_interface.py`, `P_ALGORITHM_STATUS.md` | P protocol exists, algorithm remains `NOT_READY`. |
| `READINESS.md` | G1 incomplete/G4 not authorized; no measured B0/B1/P study or human B1 session. |

**Compatibility rule:** add separate versioned DEVELOPMENT diagnostics/schemas; never overload frozen v1 prediction/scorer/input schemas with governance states. V1/2/3 existing outputs must remain regression-compatible.

## 1. Scientific problem and formal model

After an architecture change an old fitness evaluator may still execute but measure the wrong subject, scope, stage or obligation. The research object is a **versioned configuration of architectural fitness controls**, NOT the application architecture.

\[
\Phi_t=\langle C_t,R_t,\alpha_t,\theta_t,H_t,v_t\rangle.
\]

`C` = persistent architectural criteria (intent/identity); `R` = CI/test/deployment/runtime representations (evaluator, metric, scope, context, policy and evidence contract); `α` = optional weighting; `θ` = threshold rules; `H` = noncompensatory mandatory/hard constraints; `v` = version/provenance.

An obligation `q` specifies a particular normative requirement, criterion, intent, applicability rule, scope, policy basis, mandatory flag, version and provenance. `K_t=(Z_t,Π_t,Γ_t,ν_t)` is fact/policy/evidence-completeness/version knowledge; `G_T` is a typed traceability graph.

Method P is a function from **verified** states/knowledge/config/trace/capabilities to typed change `Δ`, possibly affected set `I`, justified operations `O`, materialized candidate `Φ'`, decision `D∈{ACCEPT,REJECT,HOLD}` and explanations/provenance. It never optimizes or edits the business architecture itself.

**Separate four questions:** applicability (is q normatively required?), compliance (does actual architecture meet q?), representation coverage (does a semantically valid r with evidence control q?), governance (is adapted Φ safely admissible?). Successful evaluator exit, a metric name, a `covers` declaration, or a high weighted sum proves none of the latter by itself.

### 1.1 Applicability, evidence and mandatory coverage

Reuse SPEC 02 exactly:

\[
g_q(K_t)\in\{ACTIVE,INACTIVE,UNKNOWN\}.
\]

Define method-side pair validity separately from the **independent** reference verdict:

\[
V_P(r,q,A,E)\in\{VALID,INVALID,UNKNOWN\}.
\]

`VALID` needs proven scope/context/stage/semantic match, source-version compatibility, real executable/nonvacuous evaluator, obligation-specific adequate evidence and provenance. `INVALID` needs a proved mismatch or necessary condition failure. Missing/ambiguous proof is `UNKNOWN`. Nonzero evaluator exit signaling *actual compliance violation* must be distinguished from failure of monitoring semantics; this possible mismatch with frozen reference validity is `OPEN-07`.

For an **approved** required lifecycle-stage set `S(q,A)`:

\[
Covered_P(q,s)=1\iff \exists r\in R_{active}:
stage(r)=s\land q\in covers(r)\land V_P(r,q,A,E)=VALID.
\]

If not proven, report NOT_DEMONSTRATED with separate INVALID/UNKNOWN/missing reasons. Do **not** create new multistage obligations: frozen DA01 independent RQ2 follows its current exact-pair and full-denominator rules. Unknown normative status in OPEN registry is not inactive.

### 1.2 Mandatory safety invariants

| ID | Assertion |
| --- | --- |
| INV-01 | Criterion intent and approved hard constraints cannot silently be weakened. |
| INV-02 | INACTIVE/deactivate demands verified normative negative proof of exact scope/completeness; UNKNOWN is never INACTIVE. |
| INV-03 | No deactivation of r if another ACTIVE or UNKNOWN mandatory q may still need it. |
| INV-04 | Mandatory positive coverage requires correct, nonvacuous, current, exact-pair evidence, not just pass/field/aggregate. |
| INV-05 | Wrong authority, time, revision, provenance, digest or reuse of stale validation never yields a positive proof. |
| INV-06 | Add/replace require a real materializable, digest-pinned, authorized evaluator/template; never invented checkers. |
| INV-07 | Retain on impacted r requires positive semantic adequacy; implicit unchanged retain is not verified coverage. |
| INV-08 | Stable identifiers, canonical serialization, unique targets, bound parent hashes and immutable history. |
| INV-09 | Proposed operations and v1 non-retain affected targets must agree; duplicates/conflicts forbidden. |
| INV-10 | No ACCEPT on invalid or unresolved mandatory coverage; HOLD cannot publish; rollback needs fresh current-state validation. |
| INV-11 | Semantic decision/order/hash deterministic for identical inputs and method version; timestamps are external. |
| INV-12 | No oracle/specific scenario expected-answer access or hardcoded DA01/obligation-ID logic. |

### 1.3 Boundaries for α and θ

Keep α and θ in formal Φ, but **do not implement generalized automatic weight or threshold optimization** in core v1. `adjust` is permitted only if an externally legitimate, exact-parameter, versioned bounded soft-adjustment rule exists; never relax H or redefine intent. An approved context-dependent threshold rule evaluated at a new context is not automatically a new configuration version. Record manuscript RQ2's weight/threshold part as untested until separately implemented and validated.
