# MONO CI-only B0 vs. governed adaptation Ψ — protocol v1

- **Study ID:** `MONO_CI_B0_PSI_COMPARISON_V1`
- **Status:** `DRAFT_NOT_APPROVED`; preparation and review only
- **Readiness:** `NO_GO` for either measured arm, scoring, or a scientific comparison
- **Base:** `main` at `606e1ebb635bb52f6bbbb14eb052e7005da445a8` (merged PR #50)
**Study unit:** one architecture transition; technical case repeats are not independent transitions.

This protocol is separately versioned from the frozen DA01 protocol and from `MONO_A1_PROTOCOL_V1`. It does not amend either artifact, inherit their approvals, or authorize a measured run. Because it uses the same A0.3→A0.4 transition, the existing `G-A1-C4-REF-FROZEN` stop rule for Method P on ΔA4 remains applicable unless an accountable reviewer explicitly approves a different route. Any B0/Ψ comparison also requires separate review of this protocol, a completed applicable G1 decision, and explicit G4 authorization for this study.

## 1. Scientific objective and boundary

Compare two procedures on the same predeclared source cases:

- **B0 — unchanged fitness configuration:** independently execute the exact A0.3 fitness configuration without adaptation against the A0.4 target cases.
- **Ψ — governed fitness configuration adaptation:** run a frozen, reviewed, digest-bound implementation that assesses applicability, architectural compliance, representation coverage and validity, candidate changes, and governance separately.

The internal repository interface may continue to use the identifier `P`; publication-facing text in this study uses **governed adaptation method Ψ**.

The selected transition is:

> Transition from explicitly governed inter-module dependencies to interaction through a public module query interface.

The source pair is `A0_3_GOVERNED_MODULE_GRAPH` → `A0_4_REPORT_QUERY_PORT`. The bounded control inventory is `AC_PUBLIC_API` and `AC_MODULE_GRAPH`. Those are source-required engineering CI checks; their presence does **not** establish that they are the complete applicable or mandatory fitness-obligation universe, nor that an engineering evaluator is a valid fitness representation.

This study excludes the other 16 catalog entries from measurement only if a future independent reviewer approves the bounded scope and its claim limits. Until then, all applicability, mandatory status, lifecycle-stage membership and the full denominator remain unresolved. `UNKNOWN` stays unknown; no absence-based `INACTIVE` decision is allowed.

### Questions this version can answer

The preparation package can verify the canonical source pair, the four archived source-case identities, the planned common-input/case parity, and the current execution blockers. It cannot answer whether B0 retains valid fitness behavior, whether Ψ chooses correct operations or governance decisions, whether either strategy covers the active mandatory denominator, or which strategy has lower cost. Those comparative questions remain `NOT_EVALUABLE` or `NOT_MEASURED` until both strategies execute under an approved protocol with an independent reference. These labels are study questions, not manuscript or DA01 RQ numbers.

The bounded transition is selected because its A0.3 and A0.4 canonical source revisions and source-bound CI observations are available, and the A0.4 state requires the two specified engineering controls. That makes provenance and a small set of controlled evaluator conditions inspectable. It does not establish independent fitness-representation validity or justify generalization to other transitions.

This study does not cover B1 human review, deployment, runtime telemetry, distributed architecture, the complete A1 architecture, weight/threshold optimization, the complete DA01–DA14 program, or population-level inference. A positive adaptation claim would require a separate approved case; the selected controls are primarily a negative-control/detection set.

### Relation to the dissertation research program

This is a bounded engineering and methods case intended to support a monograph comparison, not the full dissertation experiment. The repository's research crosswalk describes **five** manuscript tasks, while the supplied request calls this the “sixth research task.” That numbering discrepancy is left open for author/reviewer reconciliation before publication.

## 2. Frozen source pair and case set

The canonical source identities and checkpoint bytes are pinned in `CASE_MANIFEST_V1.json` and `INPUTS_V1.json`:

| State | Commit | Repository tree | Application tree | Checkpoint SHA-256 |
|---|---|---|---|---|
| A0.3 `A0_3_GOVERNED_MODULE_GRAPH` | `26a9bb667da7d0938e38aca15d2bf29fd1de4829` | `7b951421395f532ca403dab09d76902ff08a807d` | `b147b8961ea9e76c966663d4832e4c303581151a` | `5da4a7e1ed359ec8ea1e3288ab81edf32f0b71e2fec946b52a8d0d562dcf43c0` |
| A0.4 `A0_4_REPORT_QUERY_PORT` | `d3101c0d3aa9b7b709253b6ec7518416f05f65b9` | `2b436e0aaf09403ea516d73d20a466a122f86592` | `007196f68652bc13f6798805793ffdfae96f95f7` | `7b0b0c7a0c6ac782540466d283c42d7589b8aaeb4af7df62104faa01fd154e8e` |

Four A0.4 source conditions are reused from the archived, preregistered EVAL-01 evaluator study, rather than creating new architecture changes:

1. Untouched compliant source.
2. Controlled Reporting-to-Tasks private-service import.
3. Controlled undeclared capability dependency.
4. Incomplete expected-module scope, which must remain `NOT_EVALUABLE`/uncertain.

Each archived condition is pinned by source commit, repository/application tree, mutation patch and Git-bundle digest. The EVAL-01 archive is provenance-only. A future exporter may materialize only the case source files into isolated temporary input trees; it must not copy the EVAL archive, reports, expected outputs or `.git` into either method bundle, and must not mutate the canonical source revisions.

The case manifest identifies source inputs only. `EVALUATOR_CONTROL_EXPECTATIONS_V1.json` separately records the existing EVAL-01 author-declared expected evaluator statuses for those four controls. Those labels are not a new reference, not independent review, and not expected B0/Ψ operations or governance decisions. `INPUTS_V1.json` contains no expected outcomes.

## 3. Treatment procedures and fair inputs

Both arms must receive the same exact case source, architecture facts/checkpoint evidence, evaluator source/configuration identities, and any approved common applicability/policy information. Method-specific traceability may be provided to Ψ only if it is explicitly permitted and its digest is recorded. Each arm needs a separate, allowlisted bundle and separate output location. Do not expose the scorer reference, expected outputs, `.git`, network, or the other arm's outputs.

### B0 procedure

1. Pin the fitness configuration that existed at A0.3 before the transition.
2. Verify its exact bytes and representation IDs; preserve the configuration unchanged.
3. Execute its applicable evaluators independently on every predeclared case and save raw output/provenance.
4. Emit no adaptation operation. Record each unresolved applicability or validity result as `UNKNOWN`.

The required A0.3 parent configuration is currently `NOT_IDENTIFIED`. The frozen A0 configuration and the later `B0_DEV_A03` proposal are not interchangeable substitutes. No independent B0 procedure can run until an accountable reviewer resolves this identity and the baseline is actually materialized.

### Ψ procedure

1. Freeze a general Ψ algorithm/version and exact executable/configuration digests after independent review.
2. Feed the same case source and common evidence as B0, plus only reviewed Ψ-specific inputs.
3. Preserve `ACTIVE` / `INACTIVE` / `UNKNOWN` applicability semantics; missing evidence cannot prove non-applicability.
4. Separate compliance observations, exact-pair validity, current coverage, candidate coverage and actually evaluated post-adaptation coverage.
5. Materialize any candidate before claiming it was applied; independently execute its evaluators before reporting post-adaptation coverage.
6. Record `ACCEPT`, `REJECT`, `HOLD`, input rejection and infrastructure failure separately.

The measured interface currently sets `P_ALGORITHM_STATUS=NOT_READY` and `require_p_algorithm()` raises `MethodNotReadyError`. Synthetic DEVELOPMENT components do not satisfy this procedure's freeze or readiness requirements. This PR does not bypass that guard.

## 4. Inputs, provenance and run environment

`INPUTS_V1.json` records checksummed source artifacts and a proposed common-input inventory. Its arm bundle fields deliberately remain `NOT_CREATED`; list equality is a plan-level parity check, not evidence that comparable bundles exist. The approved policy input is unavailable: the registry is `DRAFT` and `OPEN`, so applicability cannot be resolved from it. The A0.3 baseline and Ψ-specific traceability identity are also missing.

Before measured execution, create isolated immutable input bundles from the allowlist, verify every included file SHA-256, bind each bundle and allowlist digest to the arm record, and run negative isolation probes in the actual digest-pinned environment. Do not downgrade isolation if the required runtime is unavailable. Pin Python/dependency, runner and timer boundaries. Since this protocol measures CI-only controls, it does not use an application database/workload or report application runtime; reviewer approval is required for this narrower boundary relative to MONO-A1's broader protocol.

The source-pinned EVAL-01 archive and current checkpoints are retained unchanged. The read-only verifier validates archive-internal checksums and compares the selected source identities, patch hashes and bundle hashes with the archived manifest. It does not execute an evaluator or method.

## 5. Independent reference and scoring separation

The EVAL-01 expected evaluator statuses are an author-declared diagnostic reference only. They do not define the fitness operation, applicability, mandatory status, semantic validity, or governance reference for this study. No target-operation reference or complete obligation denominator is created in this PR.

Before a future comparison, an authorized custodian must freeze a separate scorer-only reference after independent review (or explicitly label it `AUTHOR_DECLARED` if no independent reviewer is available), write it once, verify its digest/readback, and record the review route. The reference must not be mounted in either method bundle. Scoring occurs only after both authentic method outputs and all source/input seals pass readback.

Never infer a missing prediction, operation, evidence record or applicability verdict. Use `NOT_MEASURED` where an execution did not occur and `NOT_EVALUABLE` where the frozen reference/input contract cannot assess a case. Do not change scoring rules after seeing outputs.

## 6. Metrics and measurement boundary

Report raw counts before percentages. For each metric retain its full case/pair status table and source record:

| Metric | Numerator / denominator | Boundary | Current status |
|---|---|---|---|
| Operation selection correctness | Correct operation per predeclared `(target_type, target_id)` / all reference-scored targets | Separate B0 and Ψ prediction outputs; operation universe and reference must be frozen first | `NOT_EVALUABLE` |
| Governance decision correctness | Correct `ACCEPT`/`REJECT`/`HOLD` outcome / all reference-adjudicated cases | Authentic Ψ governance record vs. independent scorer reference | `NOT_EVALUABLE` |
| Valid coverage of applicable mandatory obligations | Distinct obligations with at least one independently valid exact pair / complete approved active-mandatory denominator | Exact representation–obligation–stage evidence; incomplete denominator emits no percentage | `NOT_EVALUABLE` |
| Controlled-violation detection | TP/FP/FN/TN per evaluator-by-case over only predeclared binary-evaluable rows | Case-level evaluator observations; keep unknown/invalid rows separate | `NOT_MEASURED` for B0 vs. Ψ |
| Stale/semantically invalid representations | Count and rate by exact pair, with unresolved rows reported separately | Source/config/evaluator and independent semantic assessment | `NOT_MEASURED` |
| Execution duration | Nanoseconds from arm start to sealed arm completion; separately adaptation, evaluator and verification boundaries | Same pinned runner, limits, software and timer for both arms | `NOT_MEASURED` |

An incomplete-scope case is not a negative detection and is not scored as `FALSE`; preserve `NOT_EVALUABLE`/`UNKNOWN`. Current coverage, candidate-assessed coverage and actual post-adaptation coverage are distinct. Actual post-adaptation coverage is `NOT_MEASURED` unless a materialized candidate is executed and verified. B0 adaptation time may be recorded as zero only after confirming that no adaptation process ran; its evaluator time is not zero by definition.

Three technical process repeats per case/arm are proposed for repeatability only, with a fixed case order and alternating arm order. They do not create additional architecture transitions and support no significance claim. Reviewers must approve this repeat/failure rule before G1.

## 7. Stop conditions, approvals and validity limits

Stop before either arm, reference scoring or any measured comparison if any of these conditions remains:

- A0.3 baseline configuration/representation lineage is unidentified.
- Policy authority, bounded applicability, mandatory status, lifecycle-stage scope, or denominator is incomplete.
- Representation/evaluator exact-pair semantic adequacy is not independently reviewed.
- Ψ is not ready under a reviewed algorithm identity or still reports `NOT_READY`.
- Common inputs, arm allowlists, source/environment provenance, or isolation are missing.
- The independent scorer reference and custody/readback route are not frozen.
- This study's protocol review/G1 disposition or separate G4 authorization is absent.

Existing G1/G4 status for other work does not authorize this study. The existing ΔA4 reference-freeze gate is not waived. This draft does not record any human approval, research authorization or institutional decision.

Even after those gates, the result covers one architecture transition and a narrow static CI subset. It cannot establish superiority, full `Q(A0.4)` coverage, runtime/cloud behavior, generalization, or statistical significance.

## 8. Reproduction and requirement traceability

Read-only package/provenance check (does not run B0, Ψ, evaluator or scorer):

```bash
uv run python -m experiments.execution.tooling.mono_ci_b0_psi_preflight
```

Focused contract suite:

```bash
uv run pytest --no-cov -p no:cacheprovider tests/unit/test_mono_ci_b0_psi_preflight.py
```

Requirement IDs and checks are listed in `docs/TESTING.md`. Any future executable comparison requires a new reviewed change with independent arm entry points, strict bundle schemas, scorer separation, negative isolation tests, real run archives, and a fresh authorization audit. No measured result is produced by this protocol.
