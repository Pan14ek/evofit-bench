# MONO CI-only B0 versus governed adaptation Ψ — ΔA5 protocol v1

- Study ID: MONO_CI_B0_PSI_DELTA_A5_COMPARISON_V1
- Transition: A0_4_REPORT_QUERY_PORT → A0_5_MODULE_DATA_OWNERSHIP
- Status: DRAFT_NOT_APPROVED; no measured arm, scoring, or comparison is authorized
- Readiness: NO_GO_WITH_EXPLICIT_BLOCKERS
- Base source identity: main after PR #56, 08e0a7269311ba6ec33882365deb97d4c3f38573
- Architecture-level experimental unit: one architecture transition

This is a separate protocol for ΔA5. It does not amend the A0.3→A0.4 protocol in mono-ci-b0-psi-v1, frozen DA01 materials, or historical A0.5 evidence.

## 1. Objective and claim boundary

Compare an unchanged fitness configuration B0 with governed configuration adaptation method Ψ after the declared A0.4→A0.5 ownership-policy transition. The scientific question is whether valid, independently authorized controls preserve or restore applicable obligation coverage under the selected transition. This protocol does not predict that adaptation is necessary or that Ψ will add a representation.

A0.4 and A0.5 have the same application tree, 007196f68652bc13f6798805793ffdfae96f95f7. A0.5 activates an engineering policy for persistence ownership and adds an evaluator requirement; the pair is not an application-code refactor. This limits conclusions to the policy and static source-control condition.

## 2. Exact subject and source cases

The A0.4 source is commit d3101c0d3aa9b7b709253b6ec7518416f05f65b9, repository tree 2b436e0aaf09403ea516d73d20a466a122f86592, application tree 007196f68652bc13f6798805793ffdfae96f95f7. Its state manifest SHA-256 is 9c981442a34830bdc44d77ffc17de5b9f832b0b261d0d92f28bd15dc567febd9.

The prospective A0.5 source is commit a349d19fb89b577e6799e9736ed4ce0acc572166, repository tree 97c060cc26313a879f0940a178d42e422cc4d188, the same application tree, and state-manifest SHA-256 2906216b212b450706368d44233488fd638d2e7af789980ea2abf02740a04ae8. The manifests preserve one deployable process, one PostgreSQL database, synchronous in-process calls, and no broker.

The transition adds the declared table/model/repository ownership map and prohibits foreign repository imports, foreign ORM model import/use, and foreign table construction/metadata lookup. The exact shared model registry exception is app/db/model_registry.py. A0.4 marked AC_DATA_OWNERSHIP NOT_APPLICABLE; A0.5 marks it as an engineering requirement that is not independently approved.

The baseline remains PROSPECTIVE_RECONSTRUCTED_BASELINE. Its exact bytes are RECONSTRUCTED_B0_A04_V1.json, SHA-256 9a8c15fabc41ec6e079b3ec708a60dcc0320fa5e7370e1416123e9ec4f64643d. It retains only AC_PUBLIC_API and AC_MODULE_GRAPH. No historical A0.4 fitness-configuration identity was found. The proposal is neither historical nor approved and does not define a complete mandatory denominator.

The current source cases are the clean A0.5 source and one isolated source patch adding Tasks-to-Notifications table access. The patch changes only app/modules/tasks/repository.py. It is a controlled static evaluator case, not an independent architecture transition or a runtime/database-permission test. Future official arms must each receive fresh evidence on the exact same case source; archived outcomes are provenance only.

## 3. Applicability and stages

The catalog contains 18 obligations. The package records every row as applicability UNKNOWN, mandatory status UNKNOWN, and lifecycle status UNKNOWN. AC_PUBLIC_API, AC_MODULE_GRAPH, and AC_DATA_OWNERSHIP are proposed CI review targets because their state declarations and static evaluator configurations make a bounded review possible. These three rows are not yet a scoring denominator. The other 15 entries remain unresolved and are not designated inactive, optional, or excluded.

CI_TEST is a proposed study stage, not an authorized stage decision. Deployment and runtime requirements remain unknown. The study cannot make a percentage or mandatory-coverage claim until an accountable policy authority and independent methods reviewer approve the bounded scope, closure claim, mandatory semantics, stage requirements, effective dates, and conflict rules. A missing, stale, conflicting, incomplete, empty, or unauthorized input yields UNKNOWN. UNKNOWN never becomes INACTIVE.

The facts to review are the exact before/after manifests, the unchanged application-tree identity, static ownership map and exception, and the scoped source-inspection records. Manifest statements are declared requirements, not independently observed truth. The evaluator configuration is not evidence of policy authority. The predefined operation is not evidence of applicability.

## 4. Semantic adequacy evidence

The shared A1 evaluator source inventory SHA-256 is 5c17373ba8896ef0c443d826bd0064168ec7c5759c7973f9602b6c2c715b169c. Exact per-evaluator configuration digests and a nine-cell semantic review inventory appear in DELTA_A5_READINESS_V2.json. The inventory contains two proposed representation–obligation pairs with representation IDs and engineering-only mappings, four representation cells with no declared mapping, and three evaluator capability candidates with no representation ID. It is not a set of nine existing exact pairs or a scoring denominator. All nine cell validity values remain UNKNOWN.

PR #56's hosted DEVELOPMENT archive reported the clean A0.5 source COMPLIANT for all three evaluators. It reported that the ownership evaluator inspected 32 of 32 declared files with no missing, unexpected, or altered subjects. On the isolated negative probe it reported NON_COMPLIANT / FOREIGN_TABLE_ACCESS; the older public API and module-graph evaluators reported COMPLIANT without an attributable finding. These outcomes and source-bound probe records are historical evidence references in this package, not fresh observations made by its verifier. This is one finite pattern-specific observation only.

The ownership analyzer supports selected static Python/SQLAlchemy patterns. It does not inspect raw SQL, text() contents, dynamic table selection, reflection, runtime access, or database permissions. The exact model-registry exception and shared database remain allowed. A clean result, detected finding, matching hash, or declared mapping does not independently establish the semantics of a representation-obligation pair. All nine matrix pairs remain UNKNOWN pending independent review.

### Verification scope and historical archive status

The V2 verifier's `LOCALLY_VERIFIED` status covers only repository-local evidence: schema validity, pinned Git objects/manifests, local file bytes and SHA-256 values, and the corresponding baseline, Method Ψ, evaluator, schema and configuration bindings. It separately returns `HISTORICAL_VERIFICATION_REFERENCED` for claims copied from PR #56. The old `PASS_ARCHIVE_READBACK` value is retained only as `reported_verification_status`; it does not describe the current verifier's work.

Independent archive replay is `NOT_EXECUTED` in this readiness package. The verifier does not download workflow artifacts. An operator may explicitly provide a local archive with `--historical-archive`; replay is reported only after the existing archive verifier checks the exact pinned archive digest, its members, the A0.4→A0.5 source identities and the reported member digests. Even a successful archive replay verifies that archive scope; evaluator observations, method outcomes and timings remain historical references unless separately compared to their raw archive bytes. Historical timing rows are never measurements from the current verifier.

## 5. Comparator identities and input parity

### B0

B0 is the unchanged prospective two-control A0.4 configuration. It executes only its actual controls, emits no synthetic RETAIN, operation, or governance decision, and preserves UNKNOWN / NOT_EVALUABLE. Its source and configuration digests are recorded in the subject manifest. A study owner and independent reviewer must approve this reconstruction or supply a verified historical baseline before a scored comparison.

### Ψ

The proposed method identity pins the seven existing implementation modules, current input/output and candidate schemas, operation and cost contracts, catalog, traceability file, and evaluator configurations. The implementation version is P_GOVERNED_ADAPTATION_DEVELOPMENT_V1; the measured interface still reports P_ALGORITHM_STATUS=NOT_READY. The snapshot is PROPOSED_NOT_INDEPENDENTLY_FROZEN, not a G1 freeze. The operation planner minimizes operation count, then authorized incremental cost, then stable identifiers. Unknown evidence remains unknown and can cause HOLD. It supports RETAIN, ADD, REPLACE, DEACTIVATE, and ADJUST, but does not author evaluator programs. Candidate proposal is not candidate application.

Both future arms must receive the exact source states, approved facts and applicability profile, same source conditions, evaluator versions, runner identity, and comparable measurement boundaries. Ψ may additionally receive only approved method-specific traceability and templates. Historical evaluator observations, source-control history, scorer references, expected operations/classifications, and other-arm outputs are not common method inputs.

## 6. Metrics, scorer, and statistical interpretation

Primary outcomes are: (1) verified mandatory-obligation coverage after an approved denominator and independent exact-pair evidence; (2) raw detection outcome on the reviewed controlled negative case; and (3) actual post-adaptation coverage only if a candidate is materialized and independently re-evaluated. Report current configuration coverage, assessed candidate coverage, and actual post-adaptation coverage separately.

Secondary outcomes are Ψ operation and governance correctness against a separate reviewed reference, adaptation time, candidate construction/validation time, incremental evaluator time, total CI-control time, measurable resources, UNKNOWN/HOLD frequency, and missing-data frequency. B0 has no operation correctness outcome. No missing metric is zero by default. UNKNOWN, NOT_EVALUABLE, NOT_MEASURED, and N/A remain distinct.

The scorer/reference contract is proposed only. An independent custodian and reviewer must establish reference creation, review, sealing, access and readback. The scorer and expected labels must remain outside Ψ's mounts. The A0.5 DEVELOPMENT operation/result is not an independent reference and is not reused for scoring.

The architecture transition is the single architecture-level unit. Three technical executions per arm/case are a proposal for repeatability only; the exact count, order and failure/missing-data rules require G1 review. Repeated evaluator or CI runs do not create new architecture transitions. With one transition, report exact counts, raw outcomes, descriptive time samples and limitations; do not use inferential significance tests or claim generalization.

## 7. Cost contract proposal

The existing planner requires cost authority, max_incremental_cost, max_search_nodes and per-artifact candidate costs; the current schema has no unit or timer-boundary fields. Missing or unapproved data yields COST_MODEL_UNRESOLVED. Do not tune a threshold using the expected operation.

The proposal uses monotonic elapsed wall-clock milliseconds and records separately: method adaptation call through sealed raw output; candidate construction through validation output; per-candidate evaluator subprocesses; and full CI workflow through archive readback. CPU milliseconds and peak RSS bytes should be recorded if the runner exposes them. The historic archive has single-run evaluator samples and one 779.222 ms Ψ process sample, but no CPU/RSS or variance data; these are feasibility observations, not calibration.

A 3,600,000 ms total workflow ceiling is proposed from the current 60-minute hosted workflow timeout. It is not an approved Method Ψ per-artifact cost threshold. CPU/RSS caps, candidate costs, search bound and admissibility remain unresolved. The cost verdict remains COST_MODEL_UNRESOLVED.

## 8. Isolation and execution procedure

Before any measured run, review and pin the method, both arms, cases, common input, evaluator identities, runner, resource rules, timer boundaries, repeats and scoring reference. Produce separate write-once input/output directories. Verify allowlists and digests before execution. Run both arms on the same source cases. Seal predictions before independent scorer access. Read back all outputs and prove that no scorer, expected label, Git history, network, or other arm output entered Ψ. Re-evaluate an accepted candidate separately before claiming actual post-adaptation coverage.

The hosted DEVELOPMENT archive records a Python-isolated method process with network, source repositories and other source observations denied. That verifies only the historical run's declared isolation and archive structure. Future arm bundles do not exist and require their own isolation checks.

## 9. Gate and stop rule

Stop before any B0/Ψ study arm and before scoring unless all of the following are independently evidenced: B0 identity approval; applicability and lifecycle-stage scope; complete or explicitly bounded obligation closure; exact-pair semantic review; method/source freeze and READY status; authorized cost model; future arm parity and isolation; independent scorer custody and frozen references; G1 disposition; and separate G4 authorization. Existing preparation, CI passes, or the A0.5 archive cannot grant these gates.

Current decision: NO_GO_WITH_EXPLICIT_BLOCKERS. Permitted work is local source/package verification and contract tests. Historical archive replay was NOT_EXECUTED in this verification; the archive readback status in PR #56 is referenced as a prior report only. The last hosted Ψ outcome remains a historically reported HOLD with an empty operation plan and no prediction; the run is not a comparison. No study-arm rehearsal was run; execution stopped before either arm and scoring because the common scope/reference and method readiness conditions are unresolved.
