# MONO_CI_B0_PSI_COMPARISON_V1 — readiness and authorization matrix

- **Assessment date:** 2026-10-25
- **Decision:** **NO_GO** for either measured arm, scoring, or a scientific B0-vs-Ψ comparison.
**Permitted now:** read-only source/artifact verification, contract tests, protocol review and non-method engineering checks. No arm or evaluator run is performed by this readiness package.

## Readiness matrix

| Required condition | Status | Evidence and limit | Needed before measured execution |
|---|---|---|---|
| Canonical A0.3→A0.4 source identity | **PASS — source identity only** | Exact source/repository/application trees and canonical checkpoint digests are recorded in `CASE_MANIFEST_V1.json`; A0.3 is an ancestor of A0.4. This proves identity, not treatment validity. | Revalidate pinned objects and checkpoints at the run freeze. |
| Frozen source and application integrity | **PASS — historical readback only** | Canonical checkpoint records bind both evaluator outputs to the source; A0.4 application tree remains `007196f…`. EVAL-01 mutation cases are archived with commit/tree/patch/bundle hashes. No new source mutations are made. | Export method inputs from exact source objects and verify at execution. |
| Unchanged B0 fitness configuration at A0.3 | **BLOCKED** | `mono_e1_a03_fitness_configuration_candidate_v1.json` says the historical A0.3 config is `NOT_IDENTIFIED`; the frozen A0 config is a different state, and `B0_DEV_A03` is a later DEVELOPMENT-only proposal. Its RETAIN reference is not evaluable. | Accountable owner and independent reviewer must approve the exact baseline lineage and operation semantics, or identify and verify an actual pre-transition configuration. |
| Selected controls and policy authority | **UNKNOWN / BLOCKED** | The two A0.4 engineering gates are `AC_PUBLIC_API` and `AC_MODULE_GRAPH`. The 18-entry catalog does not supply complete state-specific applicability or mandatory status; the pilot registry is DRAFT/OPEN. | Approve a bounded CI-only obligation/stage subset and exclusion rationale, or establish a complete authorized denominator. |
| Evaluator representation and exact-pair validity | **UNKNOWN** | Canonical outputs are source-bound and complete-scope, but do not bind an approved representation ID or independent representation–obligation–stage semantic assessment. EVAL-02's three diagnostic mismatches remain recorded. | Independent exact-pair review and suitable positive/negative evidence for every measured pair; preserve known evaluator limits. |
| Method Ψ readiness | **BLOCKED** | `P_ALGORITHM_STATUS=NOT_READY`; `require_p_algorithm()` raises `MethodNotReadyError`. No approved E1 executable/configuration identity, digest-bound method bundle or proof of generic support exists for this study. | Freeze a general algorithm/version and contract with independent method/isolation review; do not bypass the interface guard. |
| Same common inputs and arm isolation | **NOT READY** | `INPUTS_V1.json` defines a common-input plan, but B0/Ψ bundles and allowlist digests are `NOT_CREATED`. No approved applicable policy input or accepted B0/Ψ parity evidence exists. | Assemble separate digest-bound allowlisted bundles from the same common sources, with only approved method-specific additions, then run negative isolation probes. |
| Case set and case-source provenance | **PASS — source identities only** | Four EVAL-01 source conditions are identified by exact source/tree/patch/bundle hashes. These are evaluator-control cases, not measured B0/Ψ inputs or independent architecture transitions. | Materialize case sources in isolated temporary input trees and confirm exact byte identity before each arm. |
| Historical versus case-specific evaluator evidence | **PASS — stale reuse blocked** | Canonical A0.3/A0.4 observations are source-bound historical context, excluded from both method bundles. A0.4 observations bind only to clean `CASE_01`; case-specific evidence arrays remain empty. The preflight rejects a current-case observation unless commit, repository tree, application tree, and independent execution all match. | In a future authorized run, independently execute evaluators on each exact case source and record case-matching output digests. |
| Scorer reference and scoring independence | **NOT READY** | The separate EVAL-01 expectation file is author-declared diagnostic metadata only. No approved target-operation/governance reference, complete applicability denominator, scorer-only custodian, freeze, or verified readback exists. | Independent reviewer/custodian must approve or explicitly label the reference `AUTHOR_DECLARED`, seal it once, and prove it is excluded from both arm bundles. |
| Reproducible execution environment | **NOT READY** | Existing evaluator evidence records its environment; this study has no common B0/Ψ runner identity, pinned isolated runtime image, arm timer record or source-to-runner provenance. The bounded CI-only timer change requires protocol review. | Pin dependencies, runner/image, resource limits, source provenance, common timer boundaries and failure/repetition rules. |
| Separate authorization | **NOT AUTHORIZED** | Existing G1 is `INCOMPLETE`, G4 is `NOT AUTHORIZED`, and `G-A1-C4-REF-FROZEN` is `NOT_READY`. None of these records authorizes this separate protocol. | Complete this protocol's independent review/G1 disposition, satisfy the applicable ΔA4 reference gate, then obtain a separate explicit G4 authorization. |

## Metrics status

See `METRIC_CONTRACT_V1.json` for each numerator, denominator, measurement boundary, and evidence source.

| Metric | B0 | Ψ | Reason |
|---|---|---|---|
| Operation-selection correctness | `N/A` | `NOT_EVALUABLE` | B0 emits no operation; Ψ has no separate scorer reference. B0 is not implicitly scored as `RETAIN`. |
| Governance-decision correctness | `N/A` | `NOT_EVALUABLE` | B0 emits no governance decision; Ψ has no separate scorer reference. |
| Current-configuration verified coverage | `NOT_EVALUABLE` | `NOT_EVALUABLE` | A0.3 baseline, complete approved denominator, and independent pair validity remain unresolved. |
| Controlled-violation detection | `NOT_MEASURED` | `NOT_MEASURED` | No evaluator was executed for either strategy on the selected case inputs. |
| Stale/semantically invalid representations | `NOT_EVALUABLE` | `NOT_EVALUABLE` | No approved representation mappings or independent pair reference exist. |
| Assessed candidate coverage | `N/A` | `NOT_MEASURED` | B0 creates no candidate; Ψ created and assessed none. |
| Actual post-adaptation coverage | `N/A` | `NOT_MEASURED` | B0 does not adapt; no Ψ candidate was materialized and evaluated. |
| End-to-end case execution duration | `NOT_MEASURED` | `NOT_MEASURED` | Neither arm ran under a common pinned timer boundary. |

`N/A`, `NOT_EVALUABLE`, and `NOT_MEASURED` are distinct categorical statuses. None is converted to zero, failure, or success.

## Scientific case limit

The selected cases are a clean control, controlled evaluator violations, and incomplete-scope uncertainty from EVAL-01. None is a predeclared positive adaptation case. This study's narrow aim is strategy behavior on these CI controls; these cases cannot establish that the fitness-function configuration needed to change or that adaptation provided a positive benefit. Such a claim needs a separately approved case and independent reference in a future protocol.

The existing EVAL-01/EVAL-02 studies provide finite, author-selected engineering evaluator checks, not an independent B0 baseline, method Ψ execution, full obligation coverage, or this study's measured comparison.

## Stop decision and next action

**NO_GO is required.** A read-only package check or successful synthetic test cannot promote this study to GO, complete G1, grant G4, identify the A0.3 parent configuration, or establish a scientific result.

Smallest next action: W0 plus an independent methods reviewer must issue a recorded decision identifying the B0 starting configuration and approving the bounded obligation/stage scope. That decision would clear only the first design blockers; Ψ readiness, reference custody, arm isolation and separate G1/G4 authorization would still remain.
