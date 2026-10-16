# G1 methodological decision register

**DRAFT — AWAITING INDEPENDENT METHODOLOGICAL REVIEW**

This register prepares review of the proposed method and the DA01 Phase A
protocol. It records unresolved choices; it does not approve them, amend a
frozen contract, authorize a measured run, or supply a policy authority.
Every decision below is pending. No reviewer names or signatures are recorded.

## Decision status

| Decision | Review state |
| --- | --- |
| OPEN-01 | PENDING_INDEPENDENT_REVIEW |
| OPEN-02 | PENDING_INDEPENDENT_REVIEW |
| OPEN-03 | PENDING_INDEPENDENT_REVIEW |
| OPEN-04 | PENDING_EXTERNAL_AUTHORITY |
| OPEN-05 | PENDING_EXTERNAL_AUTHORITY |
| OPEN-06 | PENDING_INDEPENDENT_REVIEW |
| OPEN-07 | PENDING_INDEPENDENT_REVIEW |
| OPEN-08 | PENDING_INDEPENDENT_REVIEW |
| OPEN-09 | PENDING_INDEPENDENT_REVIEW |
| OPEN-10 | DEFERRED_FUTURE_RESEARCH |

## Decision records

### OPEN-01 — B1 intervention, time budget, and exposure

**Related discrepancy:** [M-01](RESEARCH_CONTEXT.md#10-open-methodological-discrepancies--do-not-silently-choose).

**Choice and alternatives:** decide whether B1 reviews periodically, after
each architectural transition as the current [B1 checklist](../experiments/execution/da01/B1_CHECKLIST.md)
describes, or under another predeclared cadence. Fix a time allowance and the
allowed input/evaluator inventory before any B1 session.

**Scientific consequence:** cadence, time pressure, and prior exposure change
the B1 intervention. A periodic review is not interchangeable with a
post-change review; unequal time or information can bias the P comparison.

**Evidence required:** a preregistered B1 protocol, operator-independent pilot
of the timing procedure, common-input hash, complete time log, prior-exposure
record, and deviations. Do not simulate an operator or derive a B1 answer from
P or an oracle.

**Proposed reviewers:** independent experimental-methods reviewer and the
owner of the human-comparison procedure. **Approval:** PENDING_INDEPENDENT_REVIEW.

### OPEN-02 — RQ mapping, endpoints, and hypothesis family

**Related discrepancies:** [M-02](RESEARCH_CONTEXT.md#10-open-methodological-discrepancies--do-not-silently-choose)
and [M-06](RESEARCH_CONTEXT.md#10-open-methodological-discrepancies--do-not-silently-choose).

**Choice and alternatives:** freeze one crosswalk between manuscript and
executable RQ labels; select a primary endpoint family and state whether other
outcomes are secondary, exploratory, or multiplicity-adjusted. The manuscript
describes RQ3 as overhead and RQ4 as formal impact versus heuristic; the
executable design labels RQ3 detection and RQ4 overhead. These numberings must
remain distinct until an independent decision reconciles them.

**Candidate primary endpoints, unapproved:**

- Executable DA01 RQ1: affected-target/operation precision, recall, and F1
  under the exact frozen [scoring rules](../experiments/execution/da01/SCORE_RULES.md).
- Executable DA01 RQ2: coverage of the complete frozen required-obligation
  denominator using exact-pair evidence and the execution verdict under the
  same [scoring rules](../experiments/execution/da01/SCORE_RULES.md).

**Denominators and missing evidence:** use the pinned scenario universe and
the frozen complete obligation denominator. Keep `UNKNOWN`, `HOLD`, invalid,
vacuous, infrastructure failure, protocol violation, and reference-checker
error distinct. Do not drop, impute, or relabel them to improve a metric; apply
the existing protocol's result rules.

**Proposed analysis choices, all unapproved:** consider reporting effect sizes
with confidence intervals, defining an overhead limit before data collection,
using an architectural transition as the independent unit, selecting sample
size from a prospective power/sensitivity analysis, and predeclaring a
multiple-comparison and missing-data procedure. The reviewer must select the
estimand, interval method, bounds, repetitions, and analysis; this register does
not assign numerical thresholds.

**Scientific consequence:** a post-hoc crosswalk or endpoint family permits
selective reporting. One DA01 transition cannot establish population-level
significance or runtime/cloud performance improvement.

**Evidence required:** dated preregistration, executable-to-manuscript RQ
crosswalk, endpoint definitions, denominators, effect-size and interval plan,
sample-size rationale, and analysis script reviewed before outcomes are seen.

**Proposed reviewers:** independent statistician and dissertation-methods
reviewer. **Approval:** PENDING_INDEPENDENT_REVIEW.

### OPEN-03 — Lifecycle stages requiring mandatory proof

**Related discrepancy:** [M-04](RESEARCH_CONTEXT.md#10-open-methodological-discrepancies--do-not-silently-choose).

**Choice and alternatives:** decide which obligations require CI/test,
deployment, runtime, or multiple lifecycle stages. Options include retaining
the single exact-pair criterion for DA01, or defining a versioned obligation
stage registry for later scenarios. Do not infer required stages from an
available evaluator or from a synthetic fixture.

**Scientific consequence:** adding stages can increase the denominator and
change coverage; omitting a required stage can overstate control. Changing the
frozen DA01 denominator would invalidate comparisons.

**Evidence required:** obligation-by-stage rationale, independent stage
contracts, versioning and missing-stage rules, and a crosswalk proving whether
the proposed rule is compatible with frozen DA01 RQ2. Any later lifecycle
registry needs a separate reviewed contract.

**Proposed reviewers:** architecture-quality researcher and independent
protocol reviewer. **Approval:** PENDING_INDEPENDENT_REVIEW.

### OPEN-04 — Production policy authority and completeness trust

**Choice and alternatives:** identify an external authority for the real
Authority Charter, policy Registry, trust anchors, approval keys, and
completeness signers. Options include institutionally managed signing keys or
another independently auditable authority system; repository-local TEST_ONLY
keys are not candidates for production trust.

**Scientific consequence:** without an independently accountable authority,
`ACTIVE`, `INACTIVE`, and closed-policy claims cannot support production
decisions. Missing proof remains `UNKNOWN`/`HOLD`.

**Evidence required:** named institutional roles through an approved external
process, key custody and revocation, signer authorization, scope/time/version
rules, completeness-verifier validation, and independent audit evidence. Do
not add real names or approvals to this draft.

**Proposed reviewers:** policy authority owner, security/key-custody reviewer,
and independent methods reviewer. **Approval:** PENDING_EXTERNAL_AUTHORITY.

### OPEN-05 — Executable evaluators, templates, and B1/P parity

**Related discrepancy:** [M-03](RESEARCH_CONTEXT.md#10-open-methodological-discrepancies--do-not-silently-choose).

**Choice and alternatives:** select versioned real evaluator artifacts and
generic templates and decide how their capabilities are made equally available
to B1 and P. Options include one common capability inventory or separately
documented inventories with a justified parity rule. P-only traceability may
remain an analysis input, but it must not conceal an evaluator/capability
advantage.

**Scientific consequence:** unequal capability or unavailable artifacts can
confound method comparisons. TEST_ONLY artifacts verify code paths only; they
are not production evaluators or evidence of effectiveness.

**Evidence required:** byte-pinned artifacts, independent clean-pass and
corrupted-control results, target/scope/non-vacuity checks, stage and evidence
contracts, provenance, licensing/operational availability, and a B1/P
capability-parity audit.

**Proposed reviewers:** evaluator-domain specialist, independent B1/P fairness
reviewer, and security reviewer. **Approval:** PENDING_EXTERNAL_AUTHORITY.

### OPEN-06 — Cost model and bounded search

**Choice and alternatives:** predeclare the candidate-search bound, per-artifact
cost basis, total acceptable cost, and handling of incomparable costs. Options
include a measured operational budget, a resource-based proxy, or a small
predeclared candidate count; no TEST_ONLY zero-cost fixture sets a real limit.

**Scientific consequence:** an arbitrary bound can make a method appear cheap
or incomplete by construction. Budget exhaustion or unknown costs must remain
visible and cannot imply a feasible optimum.

**Evidence required:** provenance for each cost, calibration procedure,
resource units, sensitivity analysis over bounds, deterministic tie behavior,
and an independent audit that B1/P cost comparisons measure comparable work.

**Proposed reviewers:** performance/cost-methods reviewer and independent
statistician. **Approval:** PENDING_INDEPENDENT_REVIEW.

### OPEN-07 — Compliance violation versus invalid monitoring

**Choice and alternatives:** determine how an evaluator's cleanly executed
nonzero result, a semantic mismatch, a stale target, vacuous success, and an
infrastructure failure map to candidate governance and frozen reference
verdicts. Preserve the current separation between compliance and evaluator
adequacy while reconciling any mismatch through review.

**Scientific consequence:** treating a detected violation as invalid monitoring
can hide a true architecture defect; treating an unavailable evaluator as a
compliance failure can penalize a method for infrastructure. The [frozen
validity rules](../experiments/execution/da01/VALIDITY_RULES.md) and scoring
semantics remain authoritative for DA01.

**Evidence required:** decision table covering clean violations, vacuous
success, stale scope, missing evidence, infrastructure failure, and independent
reference-checker error; paired synthetic controls; and a reviewed crosswalk to
the frozen verdict schemas. Do not rewrite scorer/reference semantics here.

**Proposed reviewers:** independent evaluator-validity specialist and DA01
protocol reviewer. **Approval:** PENDING_INDEPENDENT_REVIEW.

### OPEN-08 — Multi-obligation ADD and single-target V1 scoring

**Choice and alternatives:** decide how a single representation that covers
multiple obligations is represented in an ADD prediction while the frozen V1
scoring identity is one `(target_type, target_id)`. Options include a canonical
owner obligation with coverage links in the candidate, separate obligation
ADDs with one representation identity, or deferring multi-obligation ADD from
the measured scope.

**Scientific consequence:** alternative encodings change target counts,
precision/recall, duplicate handling, and whether one artifact is charged once
or repeatedly. The DEVELOPMENT owner rule is not approved scoring semantics.

**Evidence required:** examples with one and multiple obligations, deterministic
normalization, duplicate/collision behavior, candidate-to-prediction mapping,
and a scorer-independent compatibility review. Do not modify the frozen V1
schema or scorer to make an option pass.

**Proposed reviewers:** independent scoring-contract reviewer and methods
reviewer. **Approval:** PENDING_INDEPENDENT_REVIEW.

### OPEN-09 — Independent algorithm review and holdout discipline

**Choice and alternatives:** define who independently reviews and freezes the
versioned P algorithm and how holdout scenarios, expected answers, and method
developers' access are controlled. Options include an external reviewer before
any measured prediction, or a separately governed review team and sealed
holdout process.

**Scientific consequence:** method authors' access to target-specific expected
answers risks overfitting and invalidates an independent comparison. A synthetic
suite does not substitute for blinded review.

**Evidence required:** reviewed algorithm version, signed freeze record under
the later approved process, documented separation of duties, input/output
allowlists, holdout custody, and auditable prediction sealing before scoring.

**Proposed reviewers:** independent architecture-method researcher and
research-integrity/holdout custodian. **Approval:** PENDING_INDEPENDENT_REVIEW.

### OPEN-10 — Adaptive α/θ and a separate causal study

**Related discrepancy:** [M-05](RESEARCH_CONTEXT.md#10-open-methodological-discrepancies--do-not-silently-choose)
and [M-06](RESEARCH_CONTEXT.md#10-open-methodological-discrepancies--do-not-silently-choose).

**Choice and alternatives:** decide whether adaptive weights (`α`) or soft
thresholds (`θ`) should be studied later, and whether they require a separate
specification and causal design. The current core does not adapt them. Options
include deferring them entirely, a later isolated extension, or a separately
randomized factorial study after the core is frozen.

**Scientific consequence:** introducing α/θ changes adds confounding and a
second treatment. No current test or DA01 evidence establishes a benefit from
weight or threshold adaptation.

**Evidence required:** a separate preregistered estimand, treatment isolation,
independent units, objective endpoint and cost plan, and sensitivity analysis.
Do not include these effects in the core SPEC 03 claim.

**Proposed reviewers:** independent methods/statistics reviewers. **Approval:**
DEFERRED_FUTURE_RESEARCH.

## Comparator and outcome preparation — proposals only

The following conditions are candidates for preregistration, not approved
protocol changes:

- **B0:** preserve the frozen A0 fitness configuration and its declared scoring
  procedure.
- **B1:** use an independent human operator and the reviewed checklist; record
  experience, prior exposure, authorized input hash, start/end time, total
  adaptation time, tools, capability inventory, rationale, uncertainty, and
  deviations. Do not simulate B1.
- **P:** use the same allowed architecture facts, policy bytes, obligation
  catalog, and capability inventory as the comparator where the protocol
  requires parity; record P-only traceability and execution costs explicitly.
- **Endpoints:** consider the executable DA01 RQ1 precision/recall/F1 and RQ2
  exact-pair mandatory coverage listed above as primary candidates. Freeze exact
  denominators, invalid/HOLD/vacuous handling, and any secondary endpoint family
  before seeing outcomes.
- **Inference:** an architectural transition, not a request, event, obligation
  row, or evaluator invocation, is the relevant independent research unit.
  Select the number of transitions, repetitions, effect-size threshold,
  confidence-interval method, multiple-comparison procedure, missing-data rule,
  and overhead ceiling prospectively. No numerical values are approved here.

The frozen [DA01 protocol](../experiments/execution/da01/PROTOCOL.md),
[scoring rules](../experiments/execution/da01/SCORE_RULES.md),
[validity rules](../experiments/execution/da01/VALIDITY_RULES.md), and
[method-input isolation rules](../experiments/execution/da01/INPUT_ISOLATION.md)
take precedence. DA01 alone cannot establish population significance or
runtime/cloud performance improvements.

## Gate checklist

| Gate | Current status | Review evidence / boundary |
| --- | --- | --- |
| G0 — architecture and inputs frozen | PASS as recorded for the existing Phase A inputs | The current change-path audit is limited to DEVELOPMENT code, tests, schemas, and descriptive docs; it is not an independent byte-parity audit of frozen artifacts. |
| G1 — methodological/protocol freeze | **INCOMPLETE** | OPEN-01…OPEN-09 require independent decisions; OPEN-10 is deferred. This draft records no approvals. |
| G2 — isolation audit | Existing Phase A evidence recorded; current branch probe pending | Prior local digest-pinned probe evidence is in [READINESS](../experiments/execution/da01/READINESS.md). This branch's Docker probe status is reported separately in the implementation traceability report. |
| G3 — synthetic rehearsal | Engineering-only, partial for SPEC 03 positive acceptance | S03R tests exercise strict TEST_ONLY paths. No accepted V3 no-op or ADD output is claimed because exact before-state applicability remains unresolved. |
| G4 — measured-run authorization | **NOT AUTHORIZED** | No B0/B1/P DA01 run is authorized by this register or its tests. |

`experiments/execution/tooling/p_interface.py` remains `NOT_READY`. Independent
review and separate explicit authorization are required before any measured
DA01 experiment.
