# ARCHITECTURE_EVOLUTION_SCENARIOS_V1

## 1. Purpose of the Document

This document defines the first version of the controlled architecture-evolution trajectory for the **EvoFitBench** experimental system, from the frozen `A0_MONOLITH` state to a modular monolith and then to a distributed/cloud-native architecture.

The document is an **experimental protocol**, not a conventional refactoring roadmap. For every architecture change `ΔA_i`, the following are defined in advance:

- architecture state before and after the change;
- scope of the controlled architecture delta;
- architectural obligations `Q(A)`;
- ground truth for the fitness-configuration elements that should be considered affected;
- expected operations `retain / replace / add / deactivate / adjust`;
- controlled degradation scenarios;
- data that must be collected for `RQ1–RQ4`.

Main experimental idea:

\[
ArchitectureChange \rightarrow ImpactAnalysis \rightarrow FitnessAdaptation \rightarrow Coverage \rightarrow Detection \rightarrow Overhead
\]

Main research question:

> **After a controlled architecture change, can the proposed method correctly identify the affected fitness configuration, adapt it in a governed way, restore the required coverage of architectural obligations, and preserve the ability to detect controlled degradations with acceptable overhead?**

---

## 2. Frozen Starting Point: A0

### 2.1. Baseline State

`A0_MONOLITH` is the frozen initial architecture state:

- one FastAPI/Uvicorn application process;
- one PostgreSQL database;
- internal communication through synchronous Python calls;
- external API via REST;
- no message broker;
- task assignment/status change, notification creation, and audit recording execute within one SQLAlchemy transaction;
- horizontal layering: `API -> Services -> Repositories -> Models`.

### 2.2. Frozen Revisions

- canonical experiments measured source revision: `ce16466d3739ea84fada13f90264de9ed4b5ab12`;
- frozen A0 source tag: `arch-a0-monolith-v1`;
- frozen A0 source revision under that tag: `b78b0967be937634b7762baccf5ac6892b279a73`;
- curated evidence package: `experiments/evidence/a0-monolith-v1/`.

### 2.3. A0 Fitness Configuration

A0 criteria:

1. `performance`;
2. `reliability`;
3. `architecture_compliance`.

Baseline representations:

- Performance / test / Locust / `http_p95_ms`;
- Performance / runtime / Prometheus / `http_request_duration_seconds`;
- Reliability / test / pytest / `integration_test_result`;
- Reliability / runtime / Prometheus / `business_http_5xx_rate`, `business_operation_failures_total`;
- Architecture compliance / CI / import-linter / `dependency_rule_violations`.

---

## 3. Research Questions

### RQ1 — Impact Identification

**How accurately does the method identify the fitness-configuration elements that must change after an architecture delta `ΔA_i`?**

Primary metrics:

\[
Precision_{impact},\ Recall_{impact},\ F1_{impact}
\]

Experimental unit: one controlled architecture-change scenario.

### RQ2 — Coverage and Semantic Consistency

**Does the adaptation restore sufficient coverage of architectural obligations and semantic consistency of fitness representations?**

Primary metric:

\[
Coverage(\Phi,A)
\]

Additional metrics:

- semantic-consistency violation rate;
- invalid/stale representation count;
- operation accuracy for `retain / replace / add / deactivate / adjust`.

### RQ3 — Detection Quality

**Does the adapted configuration detect controlled degradations introduced after architecture changes?**

Primary metrics:

\[
Precision_{detect},\ Recall_{detect},\ F1_{detect},\ FPR,\ FNR,\ T_{detect}
\]

### RQ4 — Overhead

**What overhead is introduced by the proposed method and the adapted fitness configuration?**

Primary metrics:

- `T_adapt` — time required to construct and validate the adaptation;
- `T_CI` — additional CI time;
- runtime CPU overhead;
- runtime memory overhead;
- telemetry volume;
- number of active signals/evaluators.

---

## 4. Ground-Truth Construction Rules

Ground truth must be created **before execution of the proposed method `P`** and must not be modified after observing its output.

Ground truth for `ΔA_i` is derived from:

1. architecture decision / scenario specification;
2. declared architecture invariants;
3. public API and communication contracts;
4. deployment topology;
5. data-ownership rules;
6. consistency and failure semantics;
7. observability/evidence requirements.

For every representation `R_i^s`, evaluate:

\[
SemanticCompatible(R_i^s,C_i,A_{t+1})
\]

and:

\[
Valid(R_i^s,A_{t+1},c)
\]

Ground truth must explicitly contain:

- `affected=true/false`;
- impact rationale;
- expected operation;
- expected replacement/addition/deactivation;
- required evidence;
- fault scenario, where applicable.

Negative-control changes are required as well. Their correct ground truth may be:

\[
Affected_t=\varnothing
\]

or may contain only `retain`, allowing the experiment to test whether the method introduces unnecessary adaptations.

---

## 5. Architectural Obligation Catalog `Q(A)`

### Performance Obligations

| ID | Obligation |
|---|---|
| `P_EXT_LATENCY` | User-facing API operations must satisfy the declared end-to-end latency policy. |
| `P_REMOTE_LATENCY` | Synchronous inter-service calls must satisfy the declared dependency latency budget. |
| `P_ASYNC_LAG` | Asynchronous delivery/processing must satisfy the declared lag budget. |

### Reliability Obligations

| ID | Obligation |
|---|---|
| `R_BUSINESS_FAILURE` | Unexpected business-operation failures must be observable separately from expected rejections. |
| `R_HTTP_5XX` | External/business HTTP 5xx responses must be monitored. |
| `R_LOCAL_ATOMICITY` | The local transactional Task/Notification/Audit model must preserve atomic consistency. |
| `R_REMOTE_DEPENDENCY` | Remote timeout/retry/circuit failures must be observable. |
| `R_EVENT_DELIVERY` | Event publication/consumption failures, backlog, and DLQ state must be controlled. |
| `R_IDEMPOTENCY` | Repeated event delivery must not create duplicate side effects. |
| `R_READMODEL_CONVERGENCE` | Event-driven reporting read model must converge to source state within the declared bound. |

### Architecture-Compliance Obligations

| ID | Obligation |
|---|---|
| `AC_LAYERING` | Internal dependencies must conform to the allowed layering model. |
| `AC_MODULE_STRUCTURE` | Capability modules must have declared structure and identity. |
| `AC_PUBLIC_API` | Cross-module access is allowed only through public module APIs. |
| `AC_MODULE_GRAPH` | The module-dependency graph must be acyclic and conform to allowed dependency directions. |
| `AC_DATA_OWNERSHIP` | A module/service must not bypass ownership through foreign repositories/tables. |
| `AC_SERVICE_BOUNDARY` | In-process/code-level dependencies between deployment units are forbidden. |
| `AC_COMMUNICATION_POLICY` | Communication channels must conform to the corresponding architecture decision. |
| `AC_DEPLOYMENT_TOPOLOGY` | Actual deployment units/replicas must conform to the expected architecture state. |

---

## 6. Overall Architecture-Evolution Trajectory

```text
A0_MONOLITH
   |
   | ΔA1..ΔA6
   v
A1_MODULAR_MONOLITH
   |
   | ΔA7..ΔA14
   v
A2_DISTRIBUTED_CLOUD_NATIVE
```

Business capabilities and the external REST API should remain functionally equivalent wherever possible. This is required to ensure that observed effects are associated primarily with architecture evolution rather than with new domain functionality.

---

# 7. Architecture Evolution Scenario Matrix

| Δ | State after | Controlled change | Primary change type | Ground-truth affected criteria | Expected operations | RQ |
|---|---|---|---|---|---|---|
| `ΔA1` | `A0_1_CAPABILITY_MODULES` | Horizontal packages -> capability-oriented modules | structure | architecture_compliance | replace + add + retain | RQ1,RQ2 |
| `ΔA2` | `A0_2_PUBLIC_MODULE_APIS` | Introduce explicit public module APIs | boundary | architecture_compliance | add + retain | RQ1,RQ2 |
| `ΔA3` | `A0_3_GOVERNED_MODULE_GRAPH` | Allowed module graph + cycle prohibition | dependency | architecture_compliance | add + retain | RQ1,RQ2 |
| `ΔA4` | `A0_4_REPORT_QUERY_PORT` | Reporting accesses Task only through the already-defined public API | negative control | none / architecture_compliance retained | retain only | RQ1,RQ2 |
| `ΔA5` | `A0_5_MODULE_DATA_OWNERSHIP` | Module-owned repositories/tables; cross-module persistence access forbidden | data boundary | architecture_compliance | add + retain | RQ1,RQ2 |
| `ΔA6` | `A1_MODULAR_MONOLITH` | Direct Task->Notification call -> synchronous in-process domain event, transaction preserved | communication abstraction | reliability + architecture_compliance | replace + add + retain | RQ1,RQ2,RQ3 |
| `ΔA7` | `A1_1_NOTIFICATION_HTTP` | Notification extracted to a separate deployment unit using synchronous HTTP | deployment/communication | performance + reliability + architecture_compliance | add + replace + deactivate + retain | RQ1-RQ4 |
| `ΔA8` | `A1_2_NOTIFICATION_PRIVATE_DB` | Notification gets a private database; direct DB sharing prohibited | data ownership | reliability + architecture_compliance | add + replace + retain | RQ1-RQ4 |
| `ΔA9` | `A1_3_RESILIENT_NOTIFICATION_HTTP` | Bounded timeout/retry/circuit-breaker policy | resilience policy | performance + reliability | adjust + add + retain | RQ1-RQ4 |
| `ΔA10` | `A1_4_NOTIFICATION_ASYNC` | Sync HTTP -> broker + transactional outbox | communication semantics | performance + reliability + architecture_compliance | deactivate + replace + add + retain | RQ1-RQ4 |
| `ΔA11` | `A1_5_IDEMPOTENT_NOTIFICATION_CONSUMER` | Idempotent consumer + retry/DLQ policy | delivery semantics | reliability | add + retain | RQ1-RQ4 |
| `ΔA12` | `A1_6_REPORTING_HTTP` | Reporting extracted as a separate deployment unit using Task query API over HTTP | deployment/communication | performance + reliability + architecture_compliance | add + replace + retain | RQ1-RQ4 |
| `ΔA13` | `A1_7_REPORTING_READ_MODEL` | Reporting HTTP query -> event-fed read model with bounded eventual consistency | consistency semantics | performance + reliability + architecture_compliance | deactivate + replace + add + retain | RQ1-RQ4 |
| `ΔA14` | `A2_DISTRIBUTED_CLOUD_NATIVE` | Scale Notification to >1 replicas; telemetry must aggregate across instances | deployment/runtime scope | performance + reliability + architecture_compliance | replace/retain contextual + add | RQ1-RQ4 |

---

# 8. Detailed Ground Truth per Scenario

## ΔA1 — Horizontal Layers -> Capability-Oriented Modules

### Architecture Change

Move code from global horizontal packages into capability-oriented modules, for example:

```text
app/modules/users/
app/modules/tasks/
app/modules/notifications/
app/modules/reporting/
app/modules/audit/
```

Inside each module, `api/service/repository/model` or equivalent internal layers may remain.

### What Must Not Change

- one process;
- one PostgreSQL database;
- local Python calls;
- transaction semantics;
- external REST API;
- workload.

### Ground Truth

Affected criterion:

- `architecture_compliance`.

Expected operations:

- `replace`: global `AC_LAYERING` evaluator -> module-aware internal layering evaluator;
- `add`: `AC_MODULE_STRUCTURE`;
- `retain`: performance and reliability representations.

### RQ Contribution

- RQ1: test whether the method correctly avoids marking performance/reliability as affected;
- RQ2: test whether architecture coverage is restored after code-structure change.

### Seeded Violation

No runtime degradation is required. Use a structural seeded violation, for example an intentional import from one module's API directly into a foreign repository in a controlled test fixture/branch.

---

## ΔA2 — Explicit Public Module APIs

### Architecture Change

Every capability module receives a declared public surface. Internal implementation packages must not be used directly by other modules.

### Ground Truth

Affected:

- `architecture_compliance`.

Expected operations:

- `add`: `AC_PUBLIC_API` evaluator;
- `retain`: `AC_LAYERING`, `AC_MODULE_STRUCTURE`, performance, reliability.

### Seeded Violation

`reporting` or `tasks` imports internal `notification_repository` instead of the Notification public API.

---

## ΔA3 — Governed Module Dependency Graph

### Architecture Change

Define the allowed module dependency graph and prohibit cycles. Dependencies must pass through explicitly declared contracts rather than arbitrary cross-module access.

### Ground Truth

Affected:

- `architecture_compliance`.

Expected operations:

- `add`: `AC_MODULE_GRAPH`;
- `retain`: existing module/public-API checks.

### Seeded Violation

Create a controlled dependency cycle such as `tasks -> reporting -> tasks`.

---

## ΔA4 — Reporting Refactor Through Existing Task Public Query API

### Role in Experiment

**Negative-control architecture change.**

Reporting stops accessing Task internals and instead uses an already-defined Task public query API. No new architectural obligation is introduced; the implementation is only brought into compliance with already-existing rules.

### Ground Truth

Expected affected set:

\[
Affected_{\Delta A4}=\varnothing
\]

or, at representation level, every existing element receives operation `retain`.

### Scientific Value

Tests the false-positive tendency of the proposed method. The method must not generate a new fitness configuration merely because source code changed.

---

## ΔA5 — Module Data Ownership

### Architecture Change

Every module receives ownership of its repositories/models/tables. Foreign modules must not directly use another module's repositories/models.

### Ground Truth

Affected:

- `architecture_compliance`.

Expected operations:

- `add`: `AC_DATA_OWNERSHIP`;
- `retain`: module structure/API/graph checks;
- performance/reliability remain valid.

### Seeded Violation

`tasks` directly reads the `notifications` table/repository.

---

## ΔA6 — Synchronous In-Process Domain Event

### Architecture Change

Replace direct Task->Notification service invocation with an in-process domain event/dispatcher while preserving:

- one process;
- one database;
- synchronous handler execution;
- transaction semantics.

### Ground Truth

Affected:

- `architecture_compliance`;
- `reliability` partially.

Expected operations:

- `replace`: direct module dependency rule -> allowed event-contract rule;
- `add`: event handler registration/allowed-event dependency representation;
- `retain`: `R_LOCAL_ATOMICITY`, external HTTP/Locust performance representations;
- `retain`: external failure counters.

### Seeded Degradation

Notification event handler throws an exception. Expected ground truth: Task/Notification/Audit transaction remains rolled back.

### Milestone

After this scenario passes:

`A1_MODULAR_MONOLITH`.

---

## ΔA7 — Extract Notification as Synchronous HTTP Service

### Architecture Change

Notification becomes a separate deployment unit. Task-related side effects invoke Notification through HTTP.

### Semantic Consequence

A local SQLAlchemy transaction can no longer atomically span Task state and the remote Notification service.

### Ground Truth

Affected criteria:

- performance;
- reliability;
- architecture_compliance.

Expected operations:

- `add`: `P_REMOTE_LATENCY`;
- `add`: `R_REMOTE_DEPENDENCY`;
- `deactivate`: representation claiming local Task+Notification atomicity within one database transaction;
- `replace`: in-process dependency evaluator -> service-boundary/contract evaluator;
- `add`: `AC_SERVICE_BOUNDARY`;
- `add`: `AC_COMMUNICATION_POLICY` for Task->Notification HTTP;
- `retain`: external API p95, HTTP 5xx, business-operation failures.

### Seeded Degradations

1. Notification response delay;
2. Notification HTTP 500;
3. Notification unavailable/connection failure.

### Required Data

- remote-call duration;
- remote status/error type;
- external request latency;
- operation failure;
- detection latency;
- CPU/RAM for both services.

---

## ΔA8 — Notification Private Database

### Architecture Change

Notification receives its own persistent store. Task service must not have direct SQL access to notification data.

### Ground Truth

Affected:

- architecture_compliance;
- reliability.

Expected operations:

- `add`: service-level `AC_DATA_OWNERSHIP` / no cross-database access;
- `replace`: integration tests that inspect one shared DB -> cross-service consistency/contract evidence;
- `retain`: remote latency and dependency metrics;
- `retain`: external API fitness.

### Seeded Violation

Task deployment receives credentials or a code path to the Notification database. The architecture evaluator must detect it.

### Reliability Degradation

Notification database unavailable while Task database remains healthy.

---

## ΔA9 — Bounded Timeout/Retry/Circuit-Breaker Policy

### Architecture Change

Introduce a declared resilience policy for Task->Notification HTTP:

- bounded timeout;
- bounded retry count/backoff;
- circuit breaker.

Exact values must be defined as scenario parameters before execution.

### Ground Truth

Affected:

- performance;
- reliability.

Expected operations:

- `adjust`: dependency timeout/latency budget within predeclared bounds;
- `add`: retry-exhausted / circuit-open evidence;
- `retain`: service-boundary/data-ownership rules.

### Seeded Degradations

- response delay slightly below timeout;
- response delay above timeout;
- repeated remote failures sufficient to open the circuit.

### Scientific Importance

This scenario specifically tests `adjust` without changing criterion intent.

---

## ΔA10 — Synchronous Notification HTTP -> Broker + Transactional Outbox

### Architecture Change

Task service no longer invokes Notification synchronously. After the business transaction, an event is reliably published through a transactional outbox to a broker; Notification consumer processes it asynchronously.

### Ground Truth

Affected:

- performance;
- reliability;
- architecture_compliance.

Expected operations:

- `deactivate`: `P_REMOTE_LATENCY` for Task->Notification HTTP;
- `deactivate`: HTTP dependency evaluator for this edge;
- `add`: `P_ASYNC_LAG`;
- `add`: `R_EVENT_DELIVERY`;
- `replace`: HTTP communication-policy representation -> broker/event-channel representation;
- `add`: outbox backlog/age evidence;
- `retain`: external user-facing p95;
- `retain`: business failures/5xx.

### Seeded Degradations

1. broker unavailable;
2. publisher paused -> outbox backlog;
3. consumer paused -> queue lag;
4. event-processing failure.

---

## ΔA11 — Idempotent Consumer + Retry/DLQ

### Architecture Change

Notification consumer receives:

- event identity;
- duplicate suppression/idempotent handling;
- bounded retry;
- dead-letter path.

### Ground Truth

Affected:

- reliability.

Expected operations:

- `add`: `R_IDEMPOTENCY` evaluator;
- `add`: DLQ/retry-exhausted evidence;
- `retain`: `R_EVENT_DELIVERY`, `P_ASYNC_LAG`, architecture communication rules.

### Seeded Degradations

- duplicate delivery of one notification event;
- poison event that deterministically fails processing.

### Expected Observation

Duplicate events must not create duplicate Notifications. Poison events must become observable through retry/DLQ evidence.

---

## ΔA12 — Extract Reporting as Synchronous HTTP Service

### Architecture Change

Reporting becomes a separate deployment unit and obtains data through the Task public query API over HTTP.

### Ground Truth

Affected:

- performance;
- reliability;
- architecture_compliance.

Expected operations:

- `add`: remote query latency representation;
- `add`: reporting->task remote dependency failure representation;
- `replace`: in-process module dependency check -> service contract/communication check;
- `add`: Reporting deployment-topology requirement;
- `retain`: external reporting endpoint performance criterion.

### Seeded Degradations

- Task query endpoint delay;
- Task service unavailable during report request.

---

## ΔA13 — Reporting HTTP Query -> Event-Fed Read Model

### Architecture Change

Reporting stops synchronously reading Task service for every report request. Reporting maintains its own read model from Task events.

### Ground Truth

Affected:

- performance;
- reliability;
- architecture_compliance.

Expected operations:

- `deactivate`: Reporting->Task synchronous remote-latency/dependency representations;
- `add`: `P_ASYNC_LAG` for report projection;
- `add`: `R_READMODEL_CONVERGENCE`;
- `replace`: HTTP communication edge -> event-subscription rule;
- `retain`: external report endpoint latency;
- `retain`: service/data-ownership rules.

### Seeded Degradations

- report consumer paused;
- delayed task events;
- stale read model.

### Ground-Truth Detection Condition

If source Task state changes at `t0`, the read model must reach the corresponding state no later than the declared convergence bound.

---

## ΔA14 — Multi-Replica Notification Deployment

### Architecture Change

Notification deployment scales from one instance to two or more replicas.

### Ground Truth

Affected:

- performance representations if they are instance-scoped;
- reliability representations if counters are instance-scoped;
- architecture compliance for deployment topology.

Expected operations:

- `replace`: single-instance evaluator scope -> aggregated multi-instance scope, where the previous evaluator does not aggregate correctly;
- `retain`: criterion intent;
- `add`: replica/topology conformance evidence;
- context-driven replica count may change without a configuration version if the rule `g(c_t)` was declared in advance.

### Seeded Degradations

- failure of one replica;
- latency injection into only one replica;
- uneven load distribution.

### Scientific Value

Tests end-to-end telemetry semantics after runtime-scope change: a representation may use the correct metric name yet still be semantically invalid if it aggregates only one instance.

### Milestone

After PASS:

`A2_DISTRIBUTED_CLOUD_NATIVE`.

---

# 9. Ground-Truth Matrix

The following is the initial expected matrix. Before implementation of each scenario, it must be refined down to concrete representation IDs.

| Scenario | Performance | Reliability | Architecture Compliance | New/changed obligations |
|---|---:|---:|---:|---|
| ΔA1 | retain | retain | affected | AC_LAYERING replacement, AC_MODULE_STRUCTURE add |
| ΔA2 | retain | retain | affected | AC_PUBLIC_API add |
| ΔA3 | retain | retain | affected | AC_MODULE_GRAPH add |
| ΔA4 | retain | retain | retain | none — negative control |
| ΔA5 | retain | retain | affected | AC_DATA_OWNERSHIP add |
| ΔA6 | retain | partially affected | affected | event dependency rule, atomicity test retained |
| ΔA7 | affected | affected | affected | remote latency/dependency, service boundary; local atomicity deactivated |
| ΔA8 | retain/indirect | affected | affected | private DB/data ownership, consistency evidence |
| ΔA9 | affected | affected | retain | timeout/retry/circuit policy |
| ΔA10 | affected | affected | affected | async lag, event delivery; sync HTTP deactivated |
| ΔA11 | retain | affected | retain | idempotency, retry/DLQ |
| ΔA12 | affected | affected | affected | reporting remote dependency/service boundary |
| ΔA13 | affected | affected | affected | read-model convergence, async lag; reporting HTTP dependency deactivated |
| ΔA14 | affected | affected | affected | multi-instance aggregation + topology |

---

# 10. Seeded Degradation Catalog

| Fault ID | Description | Applicable scenarios | Ground truth |
|---|---|---|---|
| `F_STRUCT_IMPORT` | Forbidden import/dependency | ΔA1–ΔA5 | architecture degradation exists |
| `F_MODULE_CYCLE` | Module cycle | ΔA3 | architecture degradation exists |
| `F_HANDLER_EXCEPTION` | In-process event-handler failure | ΔA6 | transaction must roll back |
| `F_REMOTE_DELAY` | Remote Notification/Task delay | ΔA7,ΔA9,ΔA12 | performance/reliability degradation |
| `F_REMOTE_500` | Remote dependency HTTP 500 | ΔA7,ΔA12 | reliability degradation |
| `F_REMOTE_DOWN` | Remote service unavailable | ΔA7–ΔA9,ΔA12 | reliability degradation |
| `F_DB_DOWN` | Notification private DB unavailable | ΔA8 | reliability degradation |
| `F_CIRCUIT_OPEN` | Repeated dependency failures open the circuit | ΔA9 | declared resilience event |
| `F_BROKER_DOWN` | Broker unavailable | ΔA10 | event-delivery degradation |
| `F_OUTBOX_BACKLOG` | Publisher paused / outbox grows | ΔA10 | delivery degradation |
| `F_CONSUMER_LAG` | Consumer paused | ΔA10,ΔA13 | async-lag degradation |
| `F_DUPLICATE_EVENT` | Duplicate event delivery | ΔA11 | duplicate side effect is forbidden |
| `F_POISON_EVENT` | Deterministically failing event | ΔA11 | DLQ/retry evidence expected |
| `F_STALE_REPORT` | Read model exceeds convergence bound | ΔA13 | reliability degradation |
| `F_ONE_REPLICA_SLOW` | One replica receives latency injection | ΔA14 | aggregated fitness must detect it if the threshold is exceeded |
| `F_ONE_REPLICA_DOWN` | One replica unavailable | ΔA14 | degraded availability/topology evidence |

---

# 11. Comparison Methods: B0 / B1 / P

For every architecture delta, all methods must start from the same controlled conditions.

## B0 — Unchanged Configuration

After `ΔA_i`, use the previous fitness configuration without adaptation.

This baseline shows what happens when architecture governance does not react to architecture evolution.

## B1 — Manual Heuristic Adaptation

A human adapts the fitness configuration using a reproducible checklist but without the proposed formal impact-analysis/traceability/acceptance mechanism.

B1 may manually:

- add;
- adjust;
- deactivate;
- replace;

but does not use the complete proposed governed-adaptation process.

## P — Proposed Governed Adaptation

Uses:

\[
\Delta A_t + G_T + \Phi_t
\rightarrow Impact
\rightarrow Affected
\rightarrow Operations
\rightarrow \Phi_{t+1}^{cand}
\rightarrow Validation
\rightarrow Accept/Reject
\]

---

# 12. Data to Collect for Every Scenario

For every `scenario × method`, create a machine-readable result record.

Minimum schema:

```json
{
  "scenario_id": "DA07",
  "architecture_before": "A1_MODULAR_MONOLITH",
  "architecture_after": "A1_1_NOTIFICATION_HTTP",
  "method": "B0|B1|P",
  "ground_truth_affected": [],
  "predicted_affected": [],
  "ground_truth_operations": {},
  "applied_operations": {},
  "coverage_before": 0.0,
  "coverage_after": 0.0,
  "semantic_violations_before": 0,
  "semantic_violations_after": 0,
  "adaptation_time_ms": 0,
  "ci_time_ms": 0,
  "active_signal_count": 0,
  "runtime_overhead": {},
  "fault_runs": []
}
```

### RQ1 Fields

- `ground_truth_affected`;
- `predicted_affected`;
- TP / FP / FN / TN, where TN is computed over a fixed universe of configuration elements;
- Precision / Recall / F1.

### RQ2 Fields

- required obligations `Q(A)`;
- valid covered obligations;
- `Coverage`;
- semantic violations;
- operation confusion matrix.

### RQ3 Fields

For every fault run:

- `fault_id`;
- `fault_started_at`;
- `detected`;
- `detected_at`;
- `T_detect`;
- expected affected criterion;
- actual triggered evaluator;
- false-positive / false-negative classification.

### RQ4 Fields

- adaptation-computation time;
- fitness-validation time;
- added CI duration;
- application CPU/RAM delta;
- telemetry-collection CPU/RAM;
- telemetry bytes/events produced;
- active evaluator/signal count.

---

# 13. Run Organization

Recommended structure:

```text
experiments/
  scenarios/
    DA01/
      scenario.yaml
      ground_truth.yaml
    DA02/
      ...

  results/
    DA07/
      B0/
        run-001/
        run-002/
      B1/
        ...
      P/
        ...

  evidence/
    architecture-evolution-v1/
      ... curated final results ...
```

Canonical scenario IDs should use `DA01 ... DA14` in filesystem paths rather than the `Δ` symbol.

---

# 14. Machine-Readable Scenario Specification

Before implementation of each delta, create `scenario.yaml`.

Example for `DA07`:

```yaml
id: DA07
architecture_before: A1_MODULAR_MONOLITH
architecture_after: A1_1_NOTIFICATION_HTTP

change:
  type: deployment_communication
  description: Extract Notification into a separate deployment unit and use synchronous HTTP.

invariants:
  external_api_equivalent: true
  workload_profile_equivalent: true

required_obligations:
  - P_EXT_LATENCY
  - P_REMOTE_LATENCY
  - R_BUSINESS_FAILURE
  - R_HTTP_5XX
  - R_REMOTE_DEPENDENCY
  - AC_SERVICE_BOUNDARY
  - AC_COMMUNICATION_POLICY

expected_fitness_operations:
  - operation: add
    obligation: P_REMOTE_LATENCY
  - operation: add
    obligation: R_REMOTE_DEPENDENCY
  - operation: deactivate
    obligation: R_LOCAL_ATOMICITY
  - operation: replace
    obligation: AC_SERVICE_BOUNDARY

faults:
  - F_REMOTE_DELAY
  - F_REMOTE_500
  - F_REMOTE_DOWN
```

`ground_truth.yaml` must be reviewed/frozen before running `P`.

---

# 15. Statistical Design

## RQ1 / RQ2

Experimental unit: architecture-change scenario.

For `B0`, `B1`, and `P`, compare paired outcomes on the same `ΔA_i`.

For three methods:

- Friedman test for paired multi-method comparison;
- after a significant omnibus result — pairwise Wilcoxon signed-rank;
- effect size: rank-biserial correlation or Cliff's delta;
- 95% confidence intervals.

For paired binary correctness of individual decisions, McNemar may be used.

## RQ3 / RQ4

Runtime fault experiments require multiple independent runs. The number of repetitions must be determined separately using pilot stability/power analysis. One canonical run must not be treated as an inferential sample.

Avoid pseudoreplication: thousands of HTTP requests inside one run are not thousands of independent experimental units.

---

# 16. Implementation Order

Recommended sequence:

1. Freeze this document as design `v1`.
2. Implement schemas for `scenario.yaml` and `ground_truth.yaml`.
3. Create DA01 ground truth before changing source code.
4. Implement `ΔA1` as one isolated architecture commit/PR.
5. Record architecture-state ID in experiment metadata.
6. Run a pilot of B0/B1/P for RQ1/RQ2.
7. Check whether the ground-truth construction process is sufficiently unambiguous.
8. Continue DA02–DA06 until `A1_MODULAR_MONOLITH`.
9. Perform an interim review before the distributed phase.
10. Implement DA07–DA14 one controlled delta at a time.
11. Add repeated runtime-fault experiments for scenarios marked for RQ3/RQ4.
12. After completion, build the curated dissertation dataset.

---

# 17. Exit Criteria for Every Architecture Scenario

A scenario is complete only if:

- the architecture change is implemented separately and is traceable;
- business API/functionality is preserved, or a documented exception exists;
- scenario ground truth was frozen before execution of the proposed method;
- B0/B1/P were executed or explicitly marked not applicable;
- the required evidence package is preserved;
- quality/CI is green;
- architecture state has a reproducible identifier/commit;
- all seeded faults are reset after execution;
- no unaccounted workload/seed/environment changes exist;
- results are not interpreted beyond the corresponding RQ.

---

# 18. What This Plan Does Not Claim

This document does **not** assume that:

- a modular monolith is automatically better than a monolith;
- a distributed architecture is automatically better than a modular monolith;
- more fitness functions automatically imply better governance;
- a lower p95 automatically implies a better architecture;
- one successful detection run proves effectiveness of the proposed method.

The experiment evaluates the **correctness and usefulness of governed fitness-configuration adaptation**, not the superiority of a specific architecture style.

---

# 19. Main Dissertation Evidence Chain

After implementing this plan, the expected evidence chain is:

\[
\boxed{
Architecture\ Change
\rightarrow
Impact\ Identification
\rightarrow
Governed\ Fitness\ Adaptation
\rightarrow
Coverage/Consistency
\rightarrow
Degradation\ Detection
\rightarrow
Measured\ Overhead
}
\]

This directly supports the dissertation thesis concerning the **end-to-end use and governed adaptation of fitness functions during the evolution of cloud software architecture**.
