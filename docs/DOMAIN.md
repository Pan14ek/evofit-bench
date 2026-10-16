# Domain model: benchmark application vs scientific method

EvoFitBench is a **controlled research platform** whose task-management application supplies architectural changes, executable representations, metrics and degradations. The application is not the research contribution itself.

## 1. Benchmark application's domain (implemented)

| Capability package | Main responsibility | Concrete contract |
| --- | --- | --- |
| `app.modules.users` | Create and retrieve users; email uniqueness | `users` table, audit on creation |
| `app.modules.tasks` | Create, retrieve, list, assign and change task status | `tasks` table; status transitions, transactional side effects |
| `app.modules.notifications` | Store in-app notifications synchronously | `notifications` table; **no external delivery service** |
| `app.modules.reporting` | Task status/assignment summary | Reads through Task service; no separate read model |
| `app.modules.audit` | Record business change events | `audit_events` table; writes in caller's transaction |

### Business invariants

- A task starts at `TODO`. Transitions: `TODO -> IN_PROGRESS | CANCELLED`; `IN_PROGRESS -> DONE | CANCELLED`; `DONE` and `CANCELLED` have no outgoing transitions. Verify in `app/modules/tasks/service.py`.
- Creating a user normalizes email and records an audit event in one transaction.
- Assigning a task records an assignment, notification and audit event within **one SQLAlchemy session/commit**; failures roll back the operation. Changing task status records an audit event and optionally a notification to an existing assignee in that transaction.
- Tasks and users are UUID-keyed; notification creation is local persistence and **not** email, a message bus, or a distributed event.
- The default deterministic seed (`SEED_ID=a0-v1`) creates **100 users and 500 tasks** (200 TODO, 150 IN_PROGRESS, 100 DONE, 50 CANCELLED), zero notifications and zero audit events, with reproducible IDs/timestamps. This is a test control, not a representative workload.
- Public routes are under `/api/v1` (users, tasks, notifications, task summary). Additional `/health/`, `/metrics` and opt-in `/internal/experiment/` endpoints are infrastructure, not business capabilities.
- No authentication/authorization exists in this baseline. Never expose a local research deployment or fault-injection endpoints to an untrusted network.

Relevant code: `app/modules/*/`, `app/main.py`, `app/experiment/`, `scripts/seed_db.py`, `tests/integration/test_api_flows.py`.

## 2. Research domain (versioned contracts)

| Term | Meaning | Authoritative artifact |
| --- | --- | --- |
| Architecture state `A` / change `ΔA` | A controlled before/after architectural condition | `architecture/states/`; `experiments/design/` |
| Architectural obligation `q ∈ Q(A)` | A normative characteristic whose applicability may depend on architecture state, policy and evidence | `fitness/catalog/architectural-obligations.yaml` (18 IDs) |
| Fitness representation `r ∈ Φ` | Concrete evaluator/metric/control at a stage (CI/test/runtime), potentially covering one or more obligations | `fitness/catalog/a0-fitness-elements.yaml`; `fitness/configs/a0-monolith.yaml` |
| APA | Architecture Policy Authority: charter, registry, approvals, scope, effective time and externally verified trust | SPEC 01/02 contracts and policy-pilot artifacts |
| FV_CORE_V1 | Exactly **12 activation-grade fact predicates**, typed, scoped and versioned | `experiments/execution/contracts/fact_vocabulary_v1.json` |
| Snapshot | Versioned architecture, factual and normative input with evidence provenance | `experiments/execution/schemas/architecture_policy_snapshot_v1_1.schema.json` |
| AR-DSL / applicability `g(q,K)` | Declaration and evidence-aware assessment returning `ACTIVE`, `INACTIVE` or `UNKNOWN` | SPEC 02 `p_applicability.py`, JSON schemas |
| Traceability | Explicit relationships between current representations and architectural facts/obligations | `fitness/traceability/a0-traceability.yaml` |
| Candidate adaptation | Proposed `retain/replace/add/deactivate/adjust` changes to the representation configuration | Contracts/protocol prepared; **P selection not yet implemented** |
| Independent oracle | Sealed reference answers used *after* method predictions; not method data | Private to controlled scoring; never feed into P policy/rule authoring |

The obligation catalog has **3 performance, 7 reliability and 8 architecture-compliance** entries. Its default weights are 1.0 per entry; do not interpret those weights as experimental validation of a universal weighted fitness objective.

### Critical semantic separations

1. **Applicability** says a requirement is normatively relevant, not whether it passes.
2. **Compliance** requires an independent evaluator/criterion against the actual architecture.
3. **Coverage** requires an active representation plus **valid evaluator evidence and obligation-specific semantic verdict** for the relevant `(representation_id, obligation_id)`; a `covers` field alone is not evidence.
4. **UNKNOWN** means insufficient or conflicting admissible facts/policy proof. A missing fact/policy in an open registry is not FALSE or INACTIVE.
5. Approval, source hashes and completeness are distinct: integrity of bytes is not proof of policy authority or factual completeness.

The dissertation explores end-to-end adaptive architectural fitness functions. An illustrative multi-criteria research formulation is `F(x) = Σ α_i · f_i_norm(x)`; **this expression is research context, not the currently implemented or frozen DA01 scoring algorithm**. The current DA01 protocol explicitly defines RQ1/RQ2 scorers; new fitness/selection formulas require independent formalization, protocol review and tests.

## 3. Research evolution is not deployment status

The controlled design proposes `A0_MONOLITH -> A0_1_CAPABILITY_MODULES -> ... -> A1_MODULAR_MONOLITH -> ... -> A2_DISTRIBUTED_CLOUD_NATIVE` (DA01–DA14). Only the DA01 target package reorganization is reflected in the current application code. Future broker, remote dependencies, independent services, event-driven read models and replicas are **scenario designs**, not present runtime infrastructure.

See `experiments/design/ARCHITECTURE_EVOLUTION_SCENARIOS_V1.md` for the exact scope and intended comparisons.

