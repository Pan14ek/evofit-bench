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
| Scorer reference and scoring independence | **NOT READY** | The separate EVAL-01 expectation file is author-declared diagnostic metadata only. No approved target-operation/governance reference, complete applicability denominator, scorer-only custodian, freeze, or verified readback exists. | Independent reviewer/custodian must approve or explicitly label the reference `AUTHOR_DECLARED`, seal it once, and prove it is excluded from both arm bundles. |
| Reproducible execution environment | **NOT READY** | Existing evaluator evidence records its environment; this study has no common B0/Ψ runner identity, pinned isolated runtime image, arm timer record or source-to-runner provenance. The bounded CI-only timer change requires protocol review. | Pin dependencies, runner/image, resource limits, source provenance, common timer boundaries and failure/repetition rules. |
| Separate authorization | **NOT AUTHORIZED** | Existing G1 is `INCOMPLETE`, G4 is `NOT AUTHORIZED`, and `G-A1-C4-REF-FROZEN` is `NOT_READY`. None of these records authorizes this separate protocol. | Complete this protocol's independent review/G1 disposition, satisfy the applicable ΔA4 reference gate, then obtain a separate explicit G4 authorization. |

## Metrics status

| Outcome | Status | Reason |
|---|---|---|
| B0-vs-Ψ operation correctness | `NOT_EVALUABLE` | No identified A0.3 parent configuration or approved target-operation reference. |
| Governance decision correctness | `NOT_EVALUABLE` | No reviewed operation/governance reference or Ψ execution. |
| Valid mandatory coverage | `NOT_EVALUABLE` | The applicable mandatory denominator and exact-pair validity are unresolved. No percentage is valid. |
| Detection of controlled violations | `NOT_MEASURED` for this comparison | Existing EVAL-01 evaluator observations are not B0/Ψ outputs. |
| Stale/invalid evaluator representations | `NOT_MEASURED` | No approved representation mappings or independent exact-pair results. |
| B0/Ψ duration or resource cost | `NOT_MEASURED` | Neither arm ran under a common measurement boundary. Historical evaluator-only times are not substitutes. |

The existing EVAL-01/EVAL-02 studies provide finite, author-selected engineering evaluator checks, not an independent B0 baseline, method Ψ execution, full obligation coverage, or this study's measured comparison.

## Stop decision and next action

**NO_GO is required.** A read-only package check or successful synthetic test cannot promote this study to GO, complete G1, grant G4, identify the A0.3 parent configuration, or establish a scientific result.

Smallest next action: W0 plus an independent methods reviewer must issue a recorded decision identifying the B0 starting configuration and approving the bounded obligation/stage scope. That decision would clear only the first design blockers; Ψ readiness, reference custody, arm isolation and separate G1/G4 authorization would still remain.
