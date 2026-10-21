# SPEC-A1-04 v1 — Critical path, readiness gates and acceptance matrix

**Status:** proposed implementation schedule for the 2026-10-31 monograph deadline.
**Starting state:** source-backed A0.1; `main` integration base `83aec475dcc00875faa2e4e0851064b23455f2cf`.
**Change policy:** minimal scientifically justified A0.1→A1 evolution only. No all-14-scenario program.
**Links:** [architecture requirements](SPEC_A1_ARCHITECTURE_AND_CONTRACTS_V1.md), [parallel worktrees](SPEC_A1_PARALLEL_AGENTS_V1.md), [experiment contract](SPEC_A1_EXPERIMENT_CONTRACT_V1.md).

## 1. Feasibility observations and critical blockers

The initial source inspection establishes:
1. Public module surfaces do not yet exist and current business code has direct cross-module service/repository imports.
2. `Reporting` currently imports `Tasks.service.task_summary`; ΔA4 cannot be a meaningful separate source-level negative control if ΔA2 rewrites this edge too early. The SPEC-A1-01 scoped temporary exception resolves scheduling but must be removed before A1 final compliance.
3. `Tasks.service` calls `Notifications.service.create_notification` synchronously, with `Audit.service.record_event` and one `Session`; converting to events safely requires signed-off transaction and handler failure contracts and real PostgreSQL rollback tests.
4. Existing `tests/architecture/test_module_structure.py` and `architecture/states/A0_1_CAPABILITY_MODULES.yaml` describe **exact DA01 historical state**. They cannot be edited to accept new `public.py` without corrupting the baseline; introduce stage-specific acceptance.
5. PR #25 is still an **open Draft** at SPEC creation, describing E1 calibration on A0.1 with P candidate VALID and governance HOLD; its experimental execution code is not part of `main`. The A1 experiment must not silently depend on it until merged.
6. A1 evaluator and evidence completeness for all applicable obligations are **not yet established**. A structurally passing A1 cannot by itself yield RQ2 full valid coverage or governance ACCEPT.

No blanket "A1 is feasible" verdict is asserted before unit/integration tests and stage checks run.

## 2. Time-boxed milestones and stop rules

| Deadline | Deliverable and testable exit criterion | Owners | Principal risk |
| --- | --- | --- | --- |
| **Oct 21–22** | Review SPEC-A1 docs; freeze public API, dependency graph, data ownership and sync event contracts; record integrator/base SHA; launch worktrees with nonoverlapping ownership | W0 + all | Ambiguous API contracts lead to conflicting implementations |
| **By Oct 24** | Source-grounded feasibility audit, implemented ΔA2 public ports and non-vacuous controls at least in dedicated PR; W2 static evaluator, W3 reference custody and W4 dispatcher tests in parallel | W1/W2/W3/W4 | ΔA2/ΔA4 boundary contradiction; failing API semantics |
| **Oct 25** | Integrate source-pinned ΔA2 and ΔA3; keep temporary exception honest; produce an identifiable ΔA4 source delta and reference freeze **before** its P run | W0 + W1/W2/W3 | Negative control lost if Reporting already migrated |
| **Oct 26** | Preserve MONO-E1 control; integrate ΔA5 data ownership and graph/foreign import regression | W0 + W2 | Database/model migration scope creep |
| **By Oct 27** | Integrate ΔA6 one-process event dispatcher, handler exception rollback, full REST tests, fresh A1 state manifest and source SHA; CI pass | W0 + W4 | Shared transaction semantics or evaluator adequacy |
| **Oct 28–29** | Freeze MONO-E2 source+reference; execute B0/P with admissible DEVELOPMENT evidence; seals/readback, exact-pair assessment, RQ1/RQ2 where supported, costs and raw archive | W3 + W0 | P returns HOLD; incomplete reference/coverage; source-to-image gap |
| **Oct 30–31** | Verify evidence and update monograph results, tables, limitations, abstract and conclusions only for observed values | Research author | Unsupported efficacy claims and deadline |

Schedule is a target, not a claim that implementation or reviewer approval has occurred. Escalate a critical blocker the same day it is observed. Do not invent passing controls, a complete A1 state, research percentages, or independent external validation to satisfy a date.

## 3. Stage-entry and exit requirements

### Gate G-A1-C0: architecture contract frozen
- Five public API surfaces and ownership rules approved for coding.
- Allowed dependency graph and temporary Reporting exception versioned.
- Event schema/registration/handler exception and session ownership frozen.
- W1/W2/W3/W4 independent editable path sets; integration DAG agreed.
- No modifications to protected DA01, frozen Method P or public oracle.

### Gate G-A1-C2: ΔA2 source state
- All capability public interfaces present with stable typed signatures.
- Call sites migrated except **documented Reporting exception**.
- Same REST operation/response/error/transaction behavior.
- Validated current-source manifest and negative internal-import check.
- Historical DA01 acceptance still tested on its **original source revision**; no rewriting the old expectation to make the new tree appear to be DA01.

### Gate G-A1-C3: ΔA3 dependency policy
- Valid non-vacuous complete-enough imported edge scope.
- Allowed graph and no prohibited cycles; controlled violation fails.
- Existing Reporting exception explicitly reported, not concealed as global API compliance.
- Source/checker commit SHAs pinned.

### Gate G-A1-C4: ΔA4 / MONO-E1 negative control
- New, separately recorded Reporting code refactor and removal of exception.
- Before/after Git SHA pair preserved; no newly activated obligation introduced merely by cleanup.
- Full reference sealed before any new P prediction is observed.
- Method predicted operations, candidate and governance recorded without forced success.
- REST reporting outputs and appropriate architecture tests PASS.

### Gate G-A1-C5: ΔA5 ownership
- Foreign module repository access eliminated or source-grounded and rejected as noncompliant.
- Same ORM tables/one DB; no unneeded migration.
- Positive evaluator and illegal foreign repository/table access control executed.
- User/Task/Report transactional and REST regressions PASS.

### Gate G-A1-C6: ΔA6 / A1
- One synchronous, in-process event flow; no external broker or outbox.
- Notification/audit behavior preserved on normal paths.
- Handler failure rolls back Task/Notification/Audit, checked on a disposable real DB.
- No direct forbidden Task→Notifications service dependency.
- A1 architecture source manifest verified against real Git state.
- Full quality + controlled architecture checks green, unresolved status clearly shown.
- **Only after this gate call the result `A1_MODULAR_MONOLITH`.**

### Gate G-A1-R: monograph experiment
- Both arms same target SHA; frozen algorithm/config identities.
- Reference and full mandatory obligation set sealed before P execution and kept out of inputs.
- Real source-bound/contract-verifiable evidence; non-vacuous controls.
- Prediction or authentic HOLD marker, exact reason codes, independent semantic verifier output.
- RQ1/RQ2 computed only when full scorer prerequisites hold; `UNKNOWN` and `NOT_EVALUABLE` preserved.
- Timings, CPU/RSS (if collected), source-to-image provenance or explicit gaps.
- Immutable raw archive, reproducible checksum check and Ukrainian scientific report.

**G-A1-R does not modify G1/G4/DA01 authorization.** The author may conduct honest DEVELOPMENT experiments, but cannot misstate them as authorized measured DA01 outcomes.

## 4. Acceptance and requirement-to-test matrix

| Requirement | Test/proof target | Type | Pass condition |
| --- | --- | --- | --- |
| A1-API-01/03 | Existing REST `tests/integration/test_api_flows.py` + new contract tests | Real PostgreSQL integration | Same externally observable behavior and caller session ownership |
| A1-API-02/04 | New public-boundary AST/import evaluator, clean and forbidden import | Static + negative control | Inspects all expected modules, reports violation, no silent allowlist hole |
| A1-GRAPH-01/03 | Source-based graph analyzer, injected cycle | Static + mutation | Expected edges inspected and cycle rejected |
| A1-NEG-01/03 | Reporting public query port and no-new-obligation reference | Code diff + experimental seal | Distinct revisions, no post-P oracle modification |
| A1-DATA-01/03 | Real cross-module repo import query and illicit import fixture | Static + mutation | Source evidence identifies ownership bypass |
| A1-EVENT-01/02 | Synchronous dispatcher, failure injection, DB rollback | Unit + disposable Postgres integration | Task+Notification+Audit effects all rollback under error |
| A1-EVENT-03 | Registration/forbidden direct dependency verifier | Static + integration | Non-vacuous event contract check and valid handler registration |
| A1-EXP-REF | Correct full obligation denominator, target universe and sealed reference | Schema/readback/adversarial | Stable hashes; no oracle in method inputs; source-bound reference |
| A1-EXP-P | Same-source B0/P executed and outputs sealed | Isolated execution/integrity | Authentic emissions and reason codes, missing scores not fabricated |
| A1-EXP-EVID | Exact pair and raw evidence replay | Independent verifier | Each positive assertion grounded in a raw evaluator/control |
| A1-EXP-RQ | RQ mapping, descriptive timing and analysis | Scorer and manuscript audit | No swapped manuscript RQ3/RQ4, no pseudoreplication |

**Status at document creation:** these are defined requirements, not PASS results. Each implementing PR adds actual test names, fixture provenance and commands.

## 5. Integration/test workflow

At every stage the integrator runs the repository-supported `make development-quality` and relevant new acceptance tests, plus `git diff --check`. For application integration, run the required DB tests on an explicitly disposable PostgreSQL environment; document SKIP/BLOCKED if none is available. Re-run protected artifact hashes to ensure no historical alteration. Hosted green CI checks engineering quality, not semantic-independent proof or research-gate authorization.

Change windows must not collide: agent W1 may be adding public facades while W2 builds evaluators and W3 freezes new study contracts; W4 builds a generic dispatcher independently. But W1 and W4 cannot simultaneously modify `Tasks.service`, and MONO-E1 must occur before W3's final MONO-E2 run and before ΔA5 integration rewrites further source history.

If an agent needs to edit another owner's file, submit a handoff note (file, reason, proposed diff, dependency) and let W0 schedule ownership transfer after previous PR merges. No simultaneous push to a shared branch.

## 6. Scientific and delivery stop conditions

Stop and report a concrete blocker if:
- needed architecture truth cannot be independently inspected and pinned;
- public-API or graph evaluator passes without inspecting targets;
- no real rollback negative control can execute;
- reference cannot be sealed before P use;
- P input bundle contains reference/scorer data or method self-validates its own evidence;
- source-to-image identity invalidates an asserted runtime claim;
- frozen Method P would need outcome-specific behavior changes;
- a stage would require amending frozen DA01 or overwriting raw evidence;
- cross-worktree changes make ΔA4 no longer a distinct source-level intervention.

**Fallback if A1 deadline is missed:** preserve latest genuinely completed intermediate architecture state and its raw evidence; report a partial engineering result and remaining research gaps. Do not call it A1, do not fake MONO-E2 and do not substitute the already exposed A0.1 calibration for an independent A1 comparison. Agree any smaller scientifically meaningful monograph scope explicitly before changing the research narrative.

## 7. PR order proposal

1. **SPEC-A1 documentation PR** (this branch) → merge after review.
2. **W1 ΔA2 public contracts PR** and **W2 non-vacuous evaluator PR** can develop concurrently; integrate contracts before final evaluator policy activation.
3. **ΔA3 graph stage** → **ΔA4 Reporting negative control + MONO-E1 evidence** (distinct commits/source identities).
4. **ΔA5 ownership stage** → **ΔA6 event integration/A1 state**.
5. **W3 experiment adapter/reference PR** may be developed in parallel, but execute **MONO-E2** only after final A1 source and contract freeze, with PR #25 integration status explicitly resolved.
6. **Monograph results update**, using independently checked observed artifacts rather than engineering-green assumptions.

Review all PRs before merge. No automatic merging, no mandatory expansion beyond A1.

## 8. Immediate CI compatibility issue (must be addressed before ΔA2 merge)

The existing `Makefile` runs `architecture-test` as part of `development-quality`; that target executes **all** `tests/architecture`, including `test_module_structure.py`. This historical test asserts the DA01 exact Python file inventory. Adding `public.py` to the live A1 source will therefore **correctly make the legacy test fail** if the test continues to treat today's HEAD as A0.1. This is a known stage-transition mismatch, not justification for editing the frozen historical manifest or deleting assertions.

**W0 owns a mandatory CI/profile migration before activating ΔA2 on main:**
1. Preserve and continue to execute the historical A0.1 acceptance on the exact **pinned A0.1 Git revision** (detached clean worktree or a versioned fixture with independently verified source provenance). Record its source SHA and test result.
2. Execute **new A1/current-stage** module/public-API/graph/ownership tests against the live stage SHA and declare that stage in a verified manifest. Never implicitly infer stage from unrelated file names or skip a failure as a pass.
3. Implement an explicit state-aware `architecture-test` / `development-quality` CI profile or an equivalent clearly reported two-check matrix. Existing code must not silently stop running baseline fidelity checks. Each profile reports PASS/FAIL/SKIP separately, including the original frozen Import Linter B0 (whose inability to inspect A1 is an expected research observation, not a live engineering CI gate).
4. Do not weaken `test_module_structure.py` to accept arbitrary files in all architectures, nor alter its historical expected module inventory and dependencies. If source-level code changes to test orchestration are unavoidable, use a new wrapper/selection mechanism, with direct source-revision proof, and preserve historical assertions byte-for-byte.
5. Gate ΔA2 integration on demonstrably green **both** historical A0.1 and stage-specific A1 tests plus the rest of the development-quality requirements.

If this migration cannot be achieved safely in the available time, stop and report the blocker; do not declare ΔA2's new files compatible with the current default CI by assertion.
