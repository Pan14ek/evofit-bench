# G1 Workstream 03 — Policy Authority, Evaluator Capability, and Adaptation Cost

**Status:** Proposed review brief; not independently approved. This document does not grant policy authority, promote evaluator artifacts, freeze a cost model, amend DA01 contracts, complete G1, or authorize G4.

**Reviewed source baseline:** 6e5c43f1bc56e7216a3d5cc2c2bb50abe17c0227 (the assigned base commit). Statements below describe repository evidence at this baseline. OPEN-04 and OPEN-05 remain PENDING_EXTERNAL_AUTHORITY; OPEN-06 remains PENDING_INDEPENDENT_REVIEW.

## 1. Objective and scope

This workstream prepares the authority, evaluator-capability, and cost decisions needed before a defensible B0/B1/P comparison. The research object remains the versioned fitness-control configuration. A passing process, matching digest, or populated covers field does not by itself establish that a policy is authorized or an evaluator meaningfully controls an obligation.

The brief answers OPEN-04, OPEN-05/M-03, and OPEN-06 as a source-based review proposal. “Implemented” below refers only to DEVELOPMENT software behavior. “Available” identifies a repository artifact, not approval for experimental use. PENDING_EXTERNAL_AUTHORITY, UNKNOWN, and HOLD remain the outcomes when required independent evidence is absent. No production signer, evaluator, cost, or approval is supplied here.

**Implementation-status discrepancy:** [Root AGENTS.md](../../../AGENTS.md) and the state section of [docs/README.md](../../README.md) still say full P impact analysis and governed adaptation are not implemented. The [G1 method specification](../../G1_METHOD_SPECIFICATION.md) and [SPEC 03 traceability report](../../SPEC_03_IMPLEMENTATION_TRACEABILITY.md) at this baseline document an implemented synthetic DEVELOPMENT pipeline while the measured interface remains NOT_READY. This brief follows the detailed implementation traceability and preserves the measured-readiness boundary; it does not reconcile the broader handbook status text.

Normative boundaries remain the [DA01 protocol](../../../experiments/execution/da01/PROTOCOL.md), [input isolation contract](../../../experiments/execution/da01/INPUT_ISOLATION.md), [validity rules](../../../experiments/execution/da01/VALIDITY_RULES.md), and [readiness record](../../../experiments/execution/da01/READINESS.md). This brief does not modify them or select a B1/P fairness model.

## 2. Authority and trust-chain status

### 2.1 Five different claims

| Claim | What it establishes | Current DEVELOPMENT support | What it does not establish |
| --- | --- | --- | --- |
| **Hash integrity** | The bytes read match a declared digest and allowlisted bundle inventory. | V3 manifests and Snapshot validation bind file paths, roles, sizes, revisions, and digests; tampering and inventory mismatches are rejected. | Who created or approved the bytes, whether facts are true, whether the inventory is complete, or whether a rule is correct. |
| **Provenance** | An artifact or observation is attributable to identified sources, revisions, scope, and time. | Source IDs, digests, revision/scope bindings, and verifier results are represented in DEVELOPMENT contracts. | Independent trust in the source, collector, signer, or verifier. A self-asserted provenance field is not external validation. |
| **Authorization** | An accountable authority empowered the signer to approve this policy, artifact, scope, and version during the relevant period. | Interfaces accept configured authority/trust verifiers; synthetic integration uses TEST_ONLY trust. | Real institutional authority, managed signing keys, custody, revocation, or approved roles. These are absent. |
| **Completeness** | A bounded inventory is closed for specified predicates, scope, target revision, source set, and time, so absence can support a negative conclusion. | SPEC 01/02 can validate a completeness proof against exact bindings and return unresolved status when proof is missing or mismatched. | That the verifier is independently trusted or that a pilot’s OPEN registry is complete. A digest of an incomplete list remains incomplete. |
| **Semantic correctness** | The policy and evaluator actually express and measure the intended normative obligation. | A bounded AR-DSL is parsed; exact representation–obligation checks and evidence contracts are evaluated in DEVELOPMENT. | That the policy interpretation is normatively sound, the evaluator is non-vacuous for the real system, or the semantic mapping is independently accepted. |

The [V3 policy-source schema](../../../experiments/execution/schemas/policy_source_v3.schema.json) defines a pinned bundle profile and file roles; a schema-valid bundle is not an approval. The [Snapshot v1.2 DEVELOPMENT note](../../../experiments/execution/P_INPUT_V12_DEVELOPMENT.md) binds distinct before/after registry-closure claims, but explicitly does not create production authority. The [G1 decision register](../../G1_METHOD_DECISION_REGISTER.md) records the external evidence still required.

### 2.2 Trust chain and minimum admissible evidence

| Link | Minimum evidence needed before it can support a decision | Baseline status |
| --- | --- | --- |
| **Normative policy → authority charter** | Identified external authority and governance process; charter bytes/version and effective interval; approved scope and source allowlist; authorized roles; trusted signer identities; independently verifiable signatures and key status. | Pilot charter is marked draft and grants only DRAFT_POLICY; no production trust anchor or approval signature is present. |
| **Charter → policy Registry and ruleset** | Registry and ruleset revisions/digests; explicit approval record for each policy; signer authority and scope; effective-from/until; precedence/conflict rule; revocation status; audit trail. | Pilot Registry is OPEN; its policy rows are DRAFT and have no approval source. Hash binding exists in the development packaging path, but approval is absent. |
| **Registry → architecture facts** | Each fact bound to a target source revision, predicate, subject/scope, collection method, source digest, time, and independently checked provenance. | Validation interfaces accept typed verifier results; the repository does not provide an external production fact-verification authority. Declared observations alone do not prove runtime truth. |
| **Facts → bounded completeness proof** | A signed claim naming the exact predicate/fact type, state, source revisions, scope, registry/ruleset version, evaluation time, inventory boundary, source set, verifier identity, method, and supporting evidence. The verifier must demonstrate that omitted items could have been observed. | SPEC 01/02 has exact-binding checks. The pilot completeness-claims file is empty; no production completeness signer/verifier is established. |
| **Policy + facts → applicability** | Approved rules, authorized and conflict-resolved interpretations, trusted fact/completeness proofs, and deterministic evaluation over the complete obligation catalog. | Three-state applicability is implemented in DEVELOPMENT. The pilot is not authority; unresolved or conflicting evidence remains UNKNOWN. |
| **Applicability + evaluator evidence → adaptation** | Exact-pair semantic evidence, complete mandatory denominator and stages, authorized materializable artifacts, authorized cost evidence, and a governed decision bound to all source versions. | SPEC 03 has synthetic DEVELOPMENT flows. Production inputs and measured-method readiness remain blocked; p_interface.py remains NOT_READY. |

**Authority and evidence requirements:** A future authority package should bind (1) the charter and registry bytes, (2) policy approvals and signer role grants, (3) signer key custody, rotation, compromise response, and revocation history, (4) scope, version, and validity intervals, (5) policy precedence and conflict handling, and (6) immutable decision and audit records. Evaluation must check whether a signature was valid at the approval time and whether the signer was authorized for that policy and scope—not merely whether a signature string or digest is present.

**Completeness requirements:** Negative applicability requires a predicate-specific, bounded closure proof. It must identify the exact architecture state/revision and source universe, not just a general “complete” flag. A missing fact, open Registry, absent claim, expired claim, mismatched scope/revision, or conflicting interpretation cannot establish INACTIVE; unresolved cases stay UNKNOWN/HOLD.

**Conflict and revalidation:** Conflicts require an approved precedence rule or remain unresolved. Revalidate affected policy, approval, key, fact, and completeness claims when their bytes, source revisions, scope, effective period, trust status, or governing rules change. Re-run applicability and candidate checks for the new context. Preserve the old decision and evidence in an auditable history; a fresh digest does not retroactively repair a stale approval.

## 3. Evaluator capability inventory

The inventory separates catalog declarations, runnable artifacts, evidence contracts, and experimentally admissible capabilities. A schema declaration or evaluator name is not proof that a usable artifact exists.

| Category | Repository evidence | Classification and limit |
| --- | --- | --- |
| **A0 architecture dependency check** | Frozen [Import Linter configuration](../../../fitness/evaluators/a0/importlinter.toml) for REP_A0_ARCH_CI_LAYERING, with frozen source tag/revision documented in its [README](../../../fitness/evaluators/a0/README.md). | **Available real, frozen A0 artifact.** It is a historical B0 control. It is not a generic post-change template and has not thereby been approved for B1/P or shown adequate for every target architecture. The README warns that it may no longer pass after DA01. |
| **Latency test (locust)** | Named in [A0 configuration/catalog](../../../fitness/configs/a0-monolith.yaml) as a test-stage metric. | **Cataloged representation only in the reviewed evaluator inventory.** No byte-pinned generic evaluator/template plus independent semantic and corrupted-control evidence is established here. |
| **Runtime metrics (prometheus)** | Named in the A0 configuration/catalog for request duration and failure-rate metrics. | **Cataloged representation only in the reviewed evaluator inventory.** A metric name does not establish a scoped, independently verified evaluator artifact or admissible B1/P capability. |
| **Reliability tests (pytest)** | Named in the A0 configuration/catalog for a test-stage integration result. | **Cataloged representation only in the reviewed evaluator inventory.** The repository’s ordinary test suite is not, by itself, a pinned obligation-specific evaluator contract. |
| **Evaluator evidence and pair assessment** | [Evaluator evidence schema](../../../experiments/execution/schemas/evaluator_evidence.schema.json), p_semantic.py, and DA01 [validity rules](../../../experiments/execution/da01/VALIDITY_RULES.md). | **DEVELOPMENT contract and assessment machinery, not an evaluator.** It records target resolution, inspected subjects, stage, mapping, evidence adequacy, probes, output hashes, and execution status; method-side assessment is not the independent reference verdict. |
| **Synthetic evaluator used by SPEC 03 integration** | The [implementation traceability report](../../SPEC_03_IMPLEMENTATION_TRACEABILITY.md) records a digest-pinned evaluator in synthetic no-op/ADD cases under TEST_ONLY trust. | **TEST_ONLY fixture.** It verifies software paths, not a production capability, real authority, or measured effectiveness. |
| **Generic evaluator templates and authorized cost inputs** | SPEC 03 traceability and [governed-adaptation note](../../../experiments/execution/P_GOVERNED_ADAPTATION_V1.md) report no production-approved generic templates or cost authority. | **Missing/unverified for a measured comparison.** A development schema and a template-validation function do not supply admissible artifacts. |

At this baseline, the only concrete frozen evaluator artifact identified in the A0 evaluator directory is the Import Linter configuration. Other A0 entries are declarations of representations and metrics. SPEC 03 consumes supplied, pinned evaluator evidence and artifact bytes; it does not generate a new evaluator. The policy pilot’s generic_candidate_templates inventory is empty. No candidate is promoted by this brief.

### 3.1 Promotion checklist for an evaluator capability

A candidate is **not admissible** until an independent reviewer has recorded evidence for every applicable item below:

- [ ] Stable artifact identity, canonical bytes and digest; reproducible build/source provenance where applicable; immutable version and change history.
- [ ] Authorized purpose, obligation family, scope, stage, operating conditions, licensing, and availability to the required study arms.
- [ ] Pinned execution environment: runtime/dependencies, image or environment digest, configuration, resource boundary, input/output allowlist, and failure semantics.
- [ ] Explicit supported quality attributes and obligation IDs, with independently reviewed semantic mapping; covers declarations alone are insufficient.
- [ ] Non-vacuous target selection: configured and resolved targets, inspected subjects, missing-target behavior, and evidence that the target population is complete for the claim.
- [ ] Versioned evidence contract with source/target revisions, stage, scope, timestamps, provenance, raw output hashes, uncertainty/status, and required supporting evidence.
- [ ] Independently reproduced clean-control behavior under the intended environment, including the expected output and evidence shape.
- [ ] Independently injected corrupted-control cases relevant to the obligation, with observed detection behavior and false-positive/false-negative handling documented.
- [ ] Pair-specific semantic-validity review, distinct from compliance outcome and process exit status.
- [ ] Repeatability across declared reruns/environments and explicit treatment of nondeterminism, flaky execution, and infrastructure failure.
- [ ] Measured evaluator, construction, and validation resource/time costs with units, method, environment, and raw evidence.
- [ ] B1/P access and capability-parity record, including templates, configuration options, supporting evidence, and any deliberate method-specific difference.
- [ ] Independent approval record, reviewer role, date, evidence digests, limitations, and a bounded scope of admission.

An absent item remains UNKNOWN/not admitted. Promotion requires a separate reviewer decision; completing this checklist in documentation cannot self-approve an artifact.

## 4. B1/P information and capability parity

The current DA01 design gives B1 the common architecture observations, obligation registry, A0 fitness representations, and shared evaluator inventory; B1 does not receive P’s traceability graph or impact engine. P may receive the A0 traceability artifact and programmatically execute applicability over the common normative/condition catalog. These are declared method-specific differences. They may be part of the treatment if preregistered as such; an unequal evaluator, evidence, candidate-template, or time/resource opportunity is a potential confound unless explicitly justified and reflected in the estimand. OPEN-05/M-03 remains unresolved. No B1/P contract is changed here.

### 4.1 Current parity evidence

| Dimension | Existing repository record | Assessment at this baseline |
| --- | --- | --- |
| Normative source information | B1/P share the normative and condition catalog bytes in the comparability draft; P alone executes the applicability procedure. | Source information is intended to match; whether executable interpretation is treatment or unfair assistance remains M-03. |
| Evaluator artifacts | B1/P are intended to use one shared authorized capability inventory. | No approved real shared inventory is evidenced; parity is a prerequisite, not an established fact. |
| Candidate templates | P requires authorized, digest-pinned templates for ADD/REPLACE; generic production templates are not supplied. | No equivalent template menu is established for B1 and P. |
| Evidence | The protocol requires independent exact-pair evidence for coverage, and the comparability draft calls for common verification rules. | A common, byte-pinned evidence bundle and equal access to candidate-specific evaluator outputs are not established. |
| Architecture observations | Same pinned before/after revisions and common allowed structural observations are specified. | Intended parity; record exact source and observation hashes for every arm. |
| Time and resources | The drafts require recording B1 human time and P adaptation/validation time, while B1 cadence and allowance and OPEN-06 limits remain pending. | No comparable or approved per-arm time/resource allowance is fixed. Report human and compute costs separately. |

These are source-contract intentions and unresolved gaps, not evidence that a measured comparison or B1 session exists. See the [DA01 protocol](../../../experiments/execution/da01/PROTOCOL.md), [comparability plan](../../B1_P_COMPARABILITY_PLAN.md), and [decision register](../../G1_METHOD_DECISION_REGISTER.md).

| Fairness model | Estimand | Feasibility | Limitations | Required pre-run record |
| --- | --- | --- | --- | --- |
| **1. Common readable normative information and shared evaluator artifacts; algorithms differ** | Difference between the frozen P workflow (including its declared traceability and programmatic applicability procedure) and an independent human B1 procedure, conditional on the same source facts, policy/obligation content, parent configuration, and approved evaluator/template menu. This estimates the effect of the overall adaptation procedure under common information and capabilities. | Feasible once genuine authority and a shared, byte-pinned evaluator inventory exist. The current protocol and comparability draft already describe much of this common-input structure. | Equal access to information does not make human interpretation and programmatic execution equivalent. P’s graph and automated procedure are intended treatment features but may advantage P; operator experience, exposure, B1 cadence, and incomparable resource limits can still affect results. | Hash every common input; disclose P-only inputs/tools and rationale; predeclare B1 trigger, independence/exposure, time and stop rules, candidate options, evidence access, and separate cost measures; record capability use per arm. |
| **2. Stricter capability and execution parity, with justified method differences** | Difference in adaptation decisions when both arms receive the same verified observations/evaluator outputs and can use the same pinned evaluator artifacts, templates, candidate validation rules, and evidence contracts; P’s graph and automated decision procedure remain explicit treatment features. Report human and compute costs separately. | Feasible if a neutral harness can execute shared evaluators once or provide identical pinned outputs, and if the same authorized templates are usable by both arms. It requires more governance and artifact preparation. | Shared outputs isolate adaptation decisions but do not compare evaluator selection/execution performance. Human and compute resources cannot be made physically identical; P’s structured traceability remains a method difference. Pre-executing evaluators can move evaluator cost outside both arms and changes the estimand. | Freeze the shared evidence bundle, execution harness and environment, template/menu bytes, allowed tools and permissions; specify which costs are inside/outside the intervention; justify any different human/compute ceilings; disclose the traceability/applicability treatment and preregister its interpretation. |

For either model, a parity audit should compare architecture revisions and observations, policy and obligation bytes, parent configuration, evaluator/template digests, evidence scope/stage, candidate validation, and access restrictions. An undocumented mismatch is not “part of the treatment.” Decide and document the treatment boundary before outcomes are seen. DA01’s frozen input and scoring contracts remain authoritative; any change requires its own review.

## 5. Candidate multidimensional cost model

The following is a **candidate measurement model**, not an approved cost definition or budget:

\[
\mathbf{c}_{m}(a) = \langle
 t_{\mathrm{human,active}},\ t_{\mathrm{method,wall}},\ t_{\mathrm{construction}},\ t_{\mathrm{evaluator}},\ t_{\mathrm{validation}},\ r_{\mathrm{CPU}},\ r_{\mathrm{memory}},\ r_{\mathrm{I/O}},\ n_{\mathrm{generated}},\ n_{\mathrm{considered}},\ n_{\mathrm{feasible}},\ n_{\mathrm{evaluated}},\ k_{\mathrm{operations}},\ k_{\mathrm{operational}}\rangle.
\]

Here m identifies B1 or P, and a is the complete adaptation attempt, including a HOLD or exhausted search. Record only dimensions that have a defined instrument and unit. B1 human-active time and P method wall/CPU time stay separate; evaluator execution, validation/reference checking, candidate construction, and setup are separate intervals. Do not convert one human minute into one compute second or combine incomparable dimensions with an unreviewed weight. Report missing values as missing with a reason, not as zero.

| Dimension | Candidate evidence | Comparison caution |
| --- | --- | --- |
| Human adaptation effort | B1 active time by step, elapsed session time, operator count/experience and deviations. | Human time is not interchangeable with processor time; breaks, prior knowledge, and cadence matter. |
| P computational adaptation | Wall and CPU time for diff, impact, applicability, decision, and plan search; environment and concurrency. | Startup, queueing, I/O and parallel execution can distort wall-time comparisons. Keep interval boundaries fixed. |
| Candidate construction | Time/resources to materialize candidate bytes and bind provenance. | Report failed or abandoned construction too. |
| Evaluator execution | Per-artifact elapsed/CPU/resource values and run count. | Separate common precomputed evidence from arm-specific execution. Do not count independent reference scoring as adaptation cost. |
| Validation | Time/resources for contract, semantic, coverage, governance, and candidate checks. | State whether shared validation is inside the treatment or a common study service. |
| Resource consumption | CPU-seconds, peak or integrated memory, I/O, and other instrumented units. | Pin hardware/runtime and measurement method; do not invent prices or energy conversions. |
| Search and output size | Generated, considered, feasible, rejected, and evaluated candidate counts; search nodes and operations. | A candidate cap changes the method’s opportunity set and must be fixed prospectively. |
| Operational complexity | Measurable setup steps, tool/dependency count, maintenance effort, and separately sourced licensing/service charges. | Avoid subjective “complexity scores” unless a validated rubric and independent raters are specified. |

### 5.1 Comparison approaches

1. **Wall-time accounting.** Measure active human time and P wall/CPU time separately, with evaluator and validation intervals broken out. This is operationally legible but does not make human and compute seconds commensurate; platform speed, concurrency, waiting, and operator experience differ.
2. **Resource-based accounting.** Report fixed machine resources (for example CPU time, memory, and I/O) under a pinned environment; report human effort as its own dimension. This supports reproducible compute comparisons but cannot by itself summarize opportunity cost or operational burden. Monetary conversion would require external price data and an approved model.
3. **Bounded candidate search.** Predeclare a candidate/node bound and any authorized per-artifact or total cost rule. Count the complete searched space and its completion status. This limits work but can truncate a better candidate; exhaustion is incomplete evidence, not proof that no feasible candidate exists or that a selected candidate is optimal.
4. **Explicit multidimensional reporting.** Publish the cost vector and raw measurement provenance, then compare dimensions separately or use a prospectively approved partial order. This avoids hidden exchange rates between human, compute, and operational costs, but may yield incomparable arms rather than one scalar winner.

The current DEVELOPMENT cost contract is narrower: [p_cost_model_v1.schema.json](../../../experiments/execution/schemas/p_cost_model_v1.schema.json) has a scalar max_incremental_cost, max_search_nodes, and per-artifact costs with status VERIFIED, UNVERIFIED, or TEST_ONLY. The current planner ranks feasible selections by fewer non-retain operations, then authorized scalar cost, then stable canonical IDs; it returns unresolved on unknown cost authority or exhausted search. Units, real cost provenance, bounds, and cross-family tie semantics remain OPEN-06. This code behavior is not an approved study cost model.

### 5.2 Search, ties, infeasibility, and sensitivity

- Fix candidate universe, candidate-generation rules, maximum search effort, evaluator-run allowance, and stopping rule before outcome access. Record generated/considered/feasible/evaluated counts and whether enumeration completed.
- Within a reviewed scalar model, deterministic order may use a declared lexicographic key such as operation count, authorized incremental cost, then canonical stable IDs. Resolve duplicate IDs/digests and exact ties deterministically. If vector dimensions are incomparable, retain the nondominated alternatives or apply a separately justified, preregistered preference; do not invent a post-hoc weight.
- If complete enumeration plus trusted costs proves every candidate exceeds an authorized bound, report the candidate set as infeasible under that bound. If cost authority or a cost is missing, report HOLD/unknown. If the node/time bound is exhausted before complete enumeration, report search-incomplete and do not claim infeasibility, a global minimum, or an optimum.
- Run sensitivity analyses on a prospectively defined set of bounds and report changes in feasibility, chosen candidate, and completion. Do not select the bound that produces the preferred DA01 outcome.

### 5.3 Prospective calibration protocol

1. Define each measure, clock boundary, resource unit, aggregation rule, and inclusion/exclusion rule. Pin the hardware, runtime/container, evaluator versions, concurrency, warm/cold-start procedure, and measurement instrumentation.
2. Select a calibration workload independent of DA01 outcomes and holdout answers. Use representative non-oracle development tasks or neutral benchmark cases; do not tune the bound against expected DA01 operations or scores.
3. Measure repeated candidate construction, evaluator execution, validation, and search runs under the pinned environment. Record raw measurements, failures, candidate-space size, and provenance. Calibrate B1 timing separately with a real independent pilot only under an approved procedure; do not create a synthetic human result.
4. Choose candidate and resource limits from a documented external operational envelope and the blinded calibration distribution, using a predeclared decision rule. Record who authorized the rule and units. No numerical limit is set by this brief.
5. Freeze the cost model, candidate universe, search-completion semantics, tie policy, and sensitivity grid before the DA01 method version or reference outcomes are exposed. Preserve calibration artifacts and hashes.
6. Report the primary declared cost dimensions plus the full vector, uncertainty/repeatability, incomplete runs, and sensitivity results. Do not collapse them to a composite without a separate independent review.

## 6. Review status and next boundary

This brief is evidence preparation, not a decision record. OPEN-04 still needs an authentic external authority, trust/key-custody process, and bounded-completeness verifier. OPEN-05 still needs independently accepted real evaluator artifacts and an explicit B1/P capability-parity decision. OPEN-06 still needs a reviewed cost basis, search bounds, calibration evidence, tie/infeasibility semantics, and sensitivity plan. G1 remains incomplete and G4 remains not authorized; no measured B0/B1/P result is reported.

The next boundary is independent review and evidence acquisition for these three decisions. Any new authority, evaluator, evidence, or cost contract should be versioned only after that review. Do not change frozen DA01 inputs, validity/scoring rules, B1 input contract, policy-pilot source allowlist, or the private oracle/scorer to complete this workstream. The G1 review and separate G4 authorization procedures remain in the [review checklist](../../G1_REVIEW_CHECKLIST.md) and [DA01 protocol](../../../experiments/execution/da01/PROTOCOL.md).

## 7. Source index

- [Research rationale and M-03 crosswalk](../../RESEARCH_CONTEXT.md)
- [G1 method specification](../../G1_METHOD_SPECIFICATION.md)
- [OPEN-04/05/06 decision records](../../G1_METHOD_DECISION_REGISTER.md)
- [B0/B1/P comparability draft](../../B1_P_COMPARABILITY_PLAN.md)
- [G1 review checklist](../../G1_REVIEW_CHECKLIST.md)
- [SPEC 03 implementation traceability](../../SPEC_03_IMPLEMENTATION_TRACEABILITY.md)
- [SPEC 03 DEVELOPMENT behavior](../../../experiments/execution/P_GOVERNED_ADAPTATION_V1.md)
- [Snapshot v1.2 DEVELOPMENT boundary](../../../experiments/execution/P_INPUT_V12_DEVELOPMENT.md)
- [Policy source and cost schemas](../../../experiments/execution/schemas/policy_source_v3.schema.json), [evaluator evidence schema](../../../experiments/execution/schemas/evaluator_evidence.schema.json), [cost model schema](../../../experiments/execution/schemas/p_cost_model_v1.schema.json)
- [SPEC 03 policy-source, input-validation, applicability, semantic, operation, candidate, and governance modules](../../../experiments/execution/tooling/p_policy_source_v3.py), [p_input_validation.py](../../../experiments/execution/tooling/p_input_validation.py), [p_applicability.py](../../../experiments/execution/tooling/p_applicability.py), [p_semantic.py](../../../experiments/execution/tooling/p_semantic.py), [p_operations.py](../../../experiments/execution/tooling/p_operations.py), [p_candidate.py](../../../experiments/execution/tooling/p_candidate.py), [p_governance.py](../../../experiments/execution/tooling/p_governance.py)
- [DA01 protocol](../../../experiments/execution/da01/PROTOCOL.md), [input isolation](../../../experiments/execution/da01/INPUT_ISOLATION.md), [validity rules](../../../experiments/execution/da01/VALIDITY_RULES.md), and [readiness](../../../experiments/execution/da01/READINESS.md)
- [Frozen A0 evaluator](../../../fitness/evaluators/a0/README.md), [A0 evaluator configuration](../../../fitness/evaluators/a0/importlinter.toml), and [A0 configuration](../../../fitness/configs/a0-monolith.yaml)
- [Policy pilot status document](../../../experiments/execution/policy-pilot/v1/CONTEXT.md), [draft policy design](../../../experiments/execution/policy-pilot/v1/policy-design.yaml), and pilot Charter, Registry, and completeness claims under experiments/execution/policy-pilot/v1/source/fitness/policy/
