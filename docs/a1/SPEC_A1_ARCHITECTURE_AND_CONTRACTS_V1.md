# SPEC-A1-01 v1 — A0.1 → A1 architecture and integration contracts

**Status:** PROPOSED / DEVELOPMENT; review before implementation.
**Source baseline:** `main` at `83aec475dcc00875faa2e4e0851064b23455f2cf` (PR #24 merged). PR #25 is a separate open Draft evidence-sufficient A0→A0.1 calibration; do not assume it is merged.
**Scientific target:** provide a controlled architecture-evolution treatment for evaluating fitness-configuration adaptation, **not** evidence that modular monoliths are superior.
**Deadline target:** A1 code/state frozen by 2026-10-27, with research evidence by 2026-10-29; targets are conditional on correct implementation and evidence.
**Related:** [SPEC-A1-02](SPEC_A1_PARALLEL_AGENTS_V1.md), [SPEC-A1-03](SPEC_A1_EXPERIMENT_CONTRACT_V1.md), [SPEC-A1-04](SPEC_A1_CRITICAL_PATH_V1.md); `experiments/design/ARCHITECTURE_EVOLUTION_SCENARIOS_V1.md` (§ΔA2–ΔA6); `AGENTS.md`.

## 1. Non-negotiable scope

Starting state is **A0_1_CAPABILITY_MODULES** with one FastAPI/Uvicorn process, one PostgreSQL database, one SQLAlchemy unit of work, synchronous in-process calls, and no broker. Preserve REST API paths, request/response meaning and status codes; task lifecycle invariants; side effects (notifications, audit); business and failure observability; existing fixture/workload contract. No Kafka, outbox, Kubernetes, distributed service, new database, independent B1, weight/threshold optimization, or DA07–DA14.

Deliver one **A1_MODULAR_MONOLITH** through separately identifiable/source-pinned intermediate states. ΔA2–ΔA5 may be developed in overlapping worktrees, **not** collapsed into an untraceable single Git change. ΔA6 is a dependent integration stage. A1 is not reached by flipping manifest flags or satisfying vacuous tests.

Freeze and do not edit historical A0, A0.1 DA01 manifest or its exact acceptance tests, the original A0 Import Linter, frozen DA01 input/oracle/scorer, previous pilots and sealed archives. Create additive new state manifests, contracts and tests. Keep `P_ALGORITHM_STATUS=NOT_READY`, G1=`INCOMPLETE`, G4=`NOT AUTHORIZED` unless separately, legitimately authorized.

## 2. Source-backed baseline / impact inventory

| Current source | Existing behavior | Implication |
| --- | --- | --- |
| `app/modules/tasks/service.py` | Imports `app.modules.users.repository.get_user`, `app.modules.notifications.service.create_notification` and `app.modules.audit.service.record_event` | ΔA2 public ports; ΔA5 no foreign repository; ΔA6 event-driven notification |
| `app/modules/reporting/service.py` | Imports `app.modules.tasks.service.task_summary` | Design a new Task query public API; retain a documented pre-ΔA4 direct call until actual negative-control delta |
| `app/modules/users/service.py` | Calls Audit service | Migrate to explicit Audit public API |
| `app/db/model_registry.py` | Registers ORM models centrally on one shared Base | Explicit infrastructure-only exception; **not** general permission for cross-module persistence |
| `tests/architecture/test_module_structure.py` | Exact immutable DA01 five-module inventory and historical dependency graph | Do not edit to add A1 files; write separate A1 tests and manifests |
| `tests/integration/test_api_flows.py` | REST lifecycle, notification, audit and fault tests | Stable observable business regression baseline |

These facts were inspected against the source baseline. The exact proposed API names below are **design decisions**, not claims that implementations already exist.

## 3. Module boundaries and contract decisions

Each module owns its implementation files and exposes a consciously narrow `public.py` (or a documented public package with equivalent explicit exports). **Choose and freeze one convention** in the contract milestone; do not allow individual agents to invent different conventions. Use typed functions/DTOs where helpful. Foreign modules import public contracts only; internal `repository.py`, `model.py`, `service.py`, `schemas.py` remain private except explicitly documented composition-root/ORM registration exceptions. FastAPI routing and central application composition are infrastructure entry points, not backdoors for business cross-module imports.

Publish a **versioned allowed dependency graph** and source/module inventory. At minimum account for the existing legitimate interactions Tasks→Users, Tasks→Audit, Users→Audit, Reporting→Tasks, and an initial Tasks→Notifications dependency. These edges are provisional; the final ΔA6 state should communicate task notification events through a documented in-process event contract rather than retain a forbidden direct Tasks→Notifications service call. Absence of an unwanted direct edge must be tested, not presumed.

Ownership: each capability owns its tables/models/repositories and query logic; `Tasks` must not directly import `Users.repository`. `Reporting` obtains task summaries through a Task public query contract, not direct `Tasks.repository`. Shared `Session`, `Base`, `model_registry`, relational foreign keys and migration metadata may exist across modules, but are not by themselves permission for arbitrary cross-module reads/writes. Verify SQLAlchemy usage and explicitly document any justified exceptions.

### ΔA2 — Explicit Public Module APIs (target `A0_2_PUBLIC_MODULE_APIS`)

**Req A1-API-01:** introduce explicit public entry contracts for all five modules without altering external REST behavior.

**Req A1-API-02:** migrate direct foreign implementation imports to public contracts, except a **short-lived, explicitly recorded Reporting→Task internal query legacy edge** retained solely to make ΔA4 a genuine later source-level negative-control change. This exception must be concrete, scoped, limited to the intermediate state, and **must fail the final A1 architecture gate**. A0.2 may not claim full zero-exception enforcement.

**Req A1-API-03:** preserve return shapes, typed not-found behavior, session ownership and transaction decisions. A public facade must not issue hidden `session.commit()` for an operation whose caller owns the transaction.

**Req A1-API-04:** implement new-source AST/import controls with positive and controlled forbidden-internal-import cases; verify real subject scope and counts. Do not alter the frozen DA01 architecture tests.

### ΔA3 — Governed dependency graph (target `A0_3_GOVERNED_MODULE_GRAPH`)

**Req A1-GRAPH-01:** specify allowed directed capability dependencies, graph scope and treatment of imports from the composition root and shared infrastructure. Reject undeclared edges, cycles and unresolved imports in strict mode.

**Req A1-GRAPH-02:** use source-derived dependency edges rather than manifest-only self-attestation; the target graph must inspect all declared capability modules and relevant Python source files. Handle relative and absolute imports or explicitly document/evidence coverage limitations.

**Req A1-GRAPH-03:** controlled forbidden-edge and cycle cases must fail a non-vacuous evaluator. The temporary Reporting→Task legacy exception is tracked explicitly and not mistaken for compliance with the final rule.

### ΔA4 — Reporting query-port negative control (target `A0_4_REPORT_QUERY_PORT`)

**Req A1-NEG-01:** perform a real source change after A0.3: replace the outstanding Reporting→Tasks internal query import/call with the already-defined Task public query port. Remove its temporary exception in the same isolated commit.

**Req A1-NEG-02:** do not activate a *new* architectural obligation merely because the internal caller refactors. For the configured tested universe the predeclared expected adaptation is `retain`/no new fitness operation, subject to the independently frozen reference. If changed facts or constraints contradict this assumption, report it and amend prospective design **before** P is run; do not rewrite reference after seeing P.

**Req A1-NEG-03:** run the MONO-E1 negative control on exact before/after SHAs. A code refactor alone is not a pass: demonstrate same REST/data behavior and non-vacuous module checks.

### ΔA5 — Module data ownership (target `A0_5_MODULE_DATA_OWNERSHIP`)

**Req A1-DATA-01:** codify ownership of Users, Tasks, Notifications, Reporting (no new table implied), and Audit persistence paths. A foreign module cannot import another capability's repository/model for runtime data access.

**Req A1-DATA-02:** migrate remaining cross-module access through public ports; distinguish module-owned persistence from permitted infrastructure model registration and migrations. Preserve one DB and one transaction boundary.

**Req A1-DATA-03:** evaluator exercises a clean case and a controlled illegal `Tasks`→`Notifications.repository` or foreign table query with explicit non-vacuous inspection, not filename-only declaration.

### ΔA6 — Synchronous in-process domain events (target **`A1_MODULAR_MONOLITH`**)

**Req A1-EVENT-01:** convert direct Tasks→Notifications service invocation to an explicit in-process domain event contract with deterministic, synchronous handler invocation **inside the caller's SQLAlchemy transaction**, without queue/broker/outbox/background worker. Define dispatch ownership, handler order, error propagation and registration duplication protection before coding.

**Req A1-EVENT-02:** preserve Task/Notification/Audit atomicity on assignments and status transitions. A Notification handler exception must cause rollback of all transaction changes; failures must not be swallowed, scheduled asynchronously or committed independently. Existing business-facing failure metrics semantics must not silently change.

**Req A1-EVENT-03:** source-scoped architectural evaluator must assert allowed event-contract dependency, registration and forbidden direct implementation dependency; preserve R_LOCAL_ATOMICITY evidence with a real disposable-PostgreSQL failure test.

**Req A1-EVENT-04:** prove idempotent **registration** per application bootstrap where required; this is not a claim of event-delivery exactly-once semantics or a new idempotent-consumer protocol.

## 4. Common acceptance and provenance

Each stage creates a new versioned source state under `architecture/states/` (actual schema approved with validator) or an equally auditable Git-bound manifest; state metadata must include predecessor/target/source SHA, changed source paths, allowed dependencies, intended invariants, status, and exact version. Recorded SHAs are generated after code is finalized; self-referential manifest SHA fields must not be fabricated.

For each stage preserve: source diff, regression commands/outcomes, state file/readback, compliance evaluator raw stdout/stderr, negative-control result, and SHA-256 inventory. Document exemptions and unresolved facts as `UNKNOWN`, not automatic passes. Keep scenario reference/expected operations in scorer-only custody, never in P bundles or adaptation rules.

A1 acceptance requires all five capability boundaries, graph compliance, data ownership, synchronous event/rollback safety, unchanged REST and one-process/one-DB topology. A1 governance/engineering `PASS` does **not** mean Method P research governance `ACCEPT`.

## 5. Change freeze and open design choices

Contract integrator must freeze before agents edit shared app code: (a) public API shape and DTO imports; (b) event schema and sync dispatch error semantics; (c) allowed dependency graph/legacy exception; (d) module ownership matrix; (e) test fixture expectations; (f) planned snapshots and source evidence extraction coverage.

Do not infer that any undocumented API, evaluator or proof already exists. If a feasibility check reveals that ΔA2–ΔA6 cannot all be completed before the monograph deadline, report earliest blocking dependency, preserve honest intermediate state, and request a bounded scope decision. Never label partial A1 as complete.
