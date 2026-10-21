# SPEC-A1-03 v1 — Monograph B0/P experiment, reference custody and evidence

**Status:** PROPOSED experimental protocol for DEVELOPMENT monograph; **not** a G4/DA01 authorization.
**Deadline target:** complete source freeze by 2026-10-27, execute by 2026-10-29, update monograph on 2026-10-30/31.
**Source baseline:** `main` at `83aec475dcc00875faa2e4e0851064b23455f2cf`, pending review and separate integration of PR #25.
**Links:** [architecture](SPEC_A1_ARCHITECTURE_AND_CONTRACTS_V1.md), [agents](SPEC_A1_PARALLEL_AGENTS_V1.md), [critical path](SPEC_A1_CRITICAL_PATH_V1.md).

## 1. Avoid naming collisions and equivocation

**Historical DEVELOPMENT measurements:** `DEV-B0P-V1 execution-a04` (evidence-poor A0→A0.1, P HOLD) and **PR #25 `DEV-B0P-E1`** (evidence-sufficient but calibration-exposed A0→A0.1, candidate VALID, governance HOLD, no P prediction, RQ1 NOT_EVALUABLE, RQ2 UNKNOWN as reported). These are NOT independent confirmatory samples.

**Monograph treatment names (separate namespace):**
- `MONO-E0` = already exposed A0→A0.1 context, references historical runs, no compulsory repeat.
- `MONO-E1` = **ΔA4** negative-control transition A0.3→A0.4; no newly mandatory fitness obligation merely because Reporting uses an established public query port.
- `MONO-E2` = **A0→A1 compound transition** on final `A1_MODULAR_MONOLITH` source SHA, unchanged frozen A0 configuration B0 versus proposed candidate from frozen Method P.

The scenario family is known in advance. Pre-registering a particular observed revision later does not retroactively create a blind holdout. Report exposure and author involvement explicitly.

**RQ numbering is overloaded:** manuscript RQ1 impact/operations, RQ2 valid coverage, RQ3 overhead, RQ4 controls/governance. The older `experiments/design/ARCHITECTURE_EVOLUTION_SCENARIOS_V1.md` uses RQ3 detection and RQ4 overhead. Store both labels and a versioned `rq_mapping`; never silently relabel or change frozen DA01 protocols.

## 2. Study objective and hypotheses

H1: On source-grounded controlled architecture evolution, P may select more appropriate `retain/add/replace/deactivate/adjust` operations than unchanged B0. H2: P's **candidate** may support more independently evidenced required obligations than B0, separately from **governance-accepted** coverage. H3: added adaptation and validation overhead can be measured without hidden timing asymmetry. H4: P respects a retain-only negative control and produces conservative HOLD/UNKNOWN where evidence/authority is unresolved.

These are falsifiable propositions, not established results. A P candidate, a passing evaluator and an ACCEPT decision are distinct objects.

## 3. Freeze-before-run checklist: scorer-only custody

**Owner:** W3 prepares; W0 checks the frozen decision record before any MONO-E1 or MONO-E2 P run. If a genuinely independent reviewer is unavailable, label reference `AUTHOR_DECLARED`, not independently reviewed. At a minimum save:

- Exact `before_sha`, `after_sha`, source tree IDs, date, commit lineage, allowed changes and stable workload/DB fixture.
- Versioned architecture state and architecture facts independently recomputed from exact Git trees (not trusting a manifest as observation).
- Complete typed target universe for impact/operations, including unaffected representations and newly applicable obligations.
- Full **applicable, mandatory, source-grounded** `Q(A_after)` of performance, reliability and architecture obligations; record `ACTIVE/INACTIVE/UNKNOWN` decisions and reasons. Do not blindly reuse DA01's six IDs or PILOT-02's internal two-pair denominator.
- Expected affected/unaffected decisions and `retain/add/replace/deactivate/adjust` operations, with source facts and rationale. No obligation or operation labels derived from Method P's outputs.
- Evaluator capability/inspection scope, source/config digests, necessary stage(s) and adequacy criteria for each required exact `(representation_id,obligation_id,after_sha)`.
- Negative-control semantic expectation and mutation/fault fixtures separately from method input.
- Reference schema/digest/seal, prepared/frozen timestamp, witness identity (author if only author is available) and allowed later readback rules.
- Frozen B0 source/config and Method P source identities, executor image provenance, input allowlists, isolation and runtime resource profile.

Use Git commit plus SHA-256 seal for the reference; avoid a circular manifest-to-itself checksum. **W3 cannot pass oracle paths, scorer outputs, expected operations or the complete private reference into Method P.** Only preapproved architecture facts, public policies and evidence in verified sidecar/trust context can reach P.

W0 must ensure an evaluator demonstrating the required property exists for each positive coverage claim; absence becomes `UNKNOWN`, not automatic `COMPLIANT`. Proven performance/reliability claims require adequate telemetry, valid source-to-image mapping, scopes/thresholds and stage-specific evidence.

## 4. Two-arm comparison and isolation

Run B0 (frozen unchanged A0 configuration and no adaptation) and frozen P (as built at independently pinned revision) on the **same exact target source SHA and workload conditions**. A P run with TEST_ONLY authority is diagnostic DEVELOPMENT, not G4 acceptance. Record both actual configurations and `candidate_validation`, method trace and all reason codes.

Sequence:
1. Freeze architecture source and experimental reference; verify write-once checksum/inventory.
2. Generate separately scoped method bundles; verify algorithm version, executable provenance and isolation; no Git history/oracle/scorer/network from the P container.
3. Provide P **source-bound genuine evaluator observations**, eligible TEST_ONLY policy/authority and signed sidecar where appropriate. Missing evidence stays unknown; never inject expected answers.
4. Execute B0/P and capture raw outputs. Seal emitted predictions before opening scorer reference. If P returns HOLD and the contract does not emit a prediction, save the authentic `NOT_EMITTED_GOVERNANCE_HOLD` marker; do not fabricate a sealed prediction.
5. Separately execute independent readback and semantic-evidence verifier using real clean/mutated scenarios. The verifier must not trust P's own coverage claims.
6. Only after sealed runs read the scorer-only reference and attempt RQ1/RQ2; preserve endpoint-specific `NOT_EVALUABLE/UNKNOWN` when prerequisites fail.
7. Archive raw stdout/stderr, trace, results, evaluator code/config versions, source SHA bindings, failure attempts and SHA256SUMS. Verify ZIP after **clean extraction**.

For `MONO-E1` inspect whether P proposes any unnecessary change, false positives, or inappropriate HOLD. A correct no-op is informative, but do not force positive metric when the scorer has no verified prediction.

For `MONO-E2` the **compound** A0→A1 change must be processed by the unchanged P algorithm and source-bound adapters, not scenario-specific rules. The earlier A0.1 candidate had governance HOLD and is **not** an accepted predecessor configuration. Do not seed the method with it as a legitimate accepted A0 baseline.

## 5. Operational endpoints / exact results

| Monograph endpoint | Required primary data | Failure/uncertainty semantics |
| --- | --- | --- |
| RQ1 affected targets and operation correctness | Presealed typed target universe and expected operations; valid sealed predictions; TP, FP_in, FP_extra, FN, TN, precision/recall/F1, operation confusion and accuracy | No P prediction → canonical scorer NOT_EVALUABLE; separately label unscored operation-plan diagnostic |
| RQ2 valid coverage | Same full `Q(A_after)` for B0 and P; executable evaluator, source-bound exact-pair semantic proof and compliance; separately candidate vs accepted configuration | Partial/missing proof → UNKNOWN (or explicitly bounded per-obligation findings). Do not convert two pair proofs into full-percent coverage |
| RQ3 costs | Same timer boundaries; method compute, candidate evaluation, evidence verification, CI, CPU/RSS/telemetry where actually measured | Distinguish UNKNOWN, not collected and not comparable. One run → descriptive timing, not significance |
| RQ4 control/governance | ΔA4 no-op decisions, clean/controlled forbidden import and module cycle, ΔA5 foreign data access, ΔA6 handler failure/rollback, exact governance statuses | Test PASS does not independently prove all semantic adequacy; HOLD != accepted candidate |

Every comparison table distinguishes (1) candidate structurally VALID, (2) evaluator execution VALID, (3) exact pair VERIFIED, (4) architecture COMPLIANT, (5) P governance ACCEPT/HOLD/REJECT, (6) accepted published fitness configuration. Explicitly report per-stage numerator/denominator; avoid misleading `0/0` and scalar aggregation of unknown mandatory obligations.

No significance or effect generalization from one compound transition plus one known negative control. Technical repeated runs test reproducibility/variance, not independent architectural unit count.

## 6. Required E1/E2 controls

- **Source truth:** Git tree/revision readback recomputes modules, public APIs and import graph; fail on stale/inaccurate source assertions.
- **Architectural controls:** in A1 run clean actual evaluator, prohibited foreign implementation import, dependency cycle, cross-module repository access, and event handler exception controls; archive different SHA/context identities for mutants.
- **Transaction:** disposable real PostgreSQL test asserts task state + notification + audit rollback as a unit under injected synchronous handler failure; verify normal event and notification count/API behavior.
- **Functional equivalence:** exercise API lifecycle, pagination, forbidden transitions, error statuses, logging and business metrics on before/after state with matched fixtures.
- **Isolation:** wrong source digest, wrong policy/authority, stale sidecar, cross-run reuse, oracle leak, tampered seal and missing outputs fail closed.
- **Data completeness:** measure numerator, matching runtime failure denominator and telemetry scope explicitly; no fabricated zero failure rate or p95 threshold.
- **Audit:** no changes to historical `execution-a04`, PILOT-02 V6, PR #25 archive, DA01 oracle, scorer, input lists, protected artifacts or gate statuses.

## 7. Minimal machine-readable study record (new additive schema only)

```yaml
schema_version: "mono-a1-study-v1"
study_id: "MONO-E2"
exposure: "KNOWN_SCENARIO_AUTHOR_DECLARED"
architecture_before_sha: "<full pinned A0 SHA>"
architecture_after_sha: "<full pinned A1 SHA>"
method_p_source_sha: "<verified frozen SHA>"
b0_source_sha: "<verified frozen SHA>"
reference_sha256: "<sealed separately, scorer-only>"
required_obligations_reference_sha256: "<scorer-only digest>"
input_packages: []            # content digests, no oracle file paths in P input
arms:
  B0: {run_id: null, execution: NOT_RUN, prediction: NOT_EMITTED}
  P:  {run_id: null, execution: NOT_RUN, prediction: NOT_EMITTED}
governance_p: NOT_RUN
exact_pair_evidence: []
research_endpoints:
  RQ1: NOT_EVALUABLE
  RQ2: UNKNOWN
  RQ3: UNKNOWN
  RQ4: UNKNOWN
artifact_sha256_inventory: null
```

The above is a **proposed contract example**, not observed measurements; validate/implement the schema before producing a run. Avoid committing private reference content to a publicly exposed P worktree. Even with one human author, separate directories, roles and sealed timing remain necessary to make scoring auditable.

## 8. Reporting contract

Write a Ukrainian results subsection only after authentic E1/E2 runs. Include preregistration/freeze and exact revisions, code changes, source-truth controls, paired outcomes by method, timing/resource boundaries, missing evidence, internal/external validity threats and measured/non-measured claims. Do **not** retitle the scientific contribution as superiority of A1 over A0 or claim a cloud-native distributed system was exercised. A1 is one-process/one-database, so end-to-end runtime/cloud generalization remains bounded.

The monograph itself should not be rewritten while SPEC-A1 and application stages are being implemented. After verified results, change only results, tables, discussion, conclusion and abstract as required.
