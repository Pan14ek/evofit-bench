# Context — `architecture/states`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `architecture/CONTEXT.md` before this file.

## Responsibility

Versioned architecture-state records for the preserved capability application and additive governance states.

## Local landmarks

- `A0_1_CAPABILITY_MODULES.yaml`
- `A0_3_GOVERNED_MODULE_GRAPH.yaml` and its JSON Schema — ΔA3 predecessor, invariants, approved graph, temporary exception, mandatory evaluator set, and source provenance.
- `A0_4_REPORT_QUERY_PORT.yaml` and its JSON Schema — ΔA4 current state, existing public query port, preserved graph, expired exception, evaluator applicability, and pinned A0.3 provenance.
- `A0_5_MODULE_DATA_OWNERSHIP.yaml` and its JSON Schema — prospective ΔA5 ownership-policy activation, source-owned table/model/repository mappings, narrow model-registry exception, three required evaluators, and canonical A0.4 predecessor provenance.

## Established conventions

The frozen A0.1 manifest remains historical input. A0.3 remains the historical predecessor record and canonical evaluator evidence is pinned to its exact source. A0.4 records the current reporting query transition and its source SHA, repository tree, and application tree predecessors.

## Constraints and known gaps

The A0.4 and prospective A0.5 records preserve one application process, one PostgreSQL database, synchronous Python communication, REST behavior, and caller-managed session/transaction ownership. A0.5 is a declared engineering requirement, not independent approval; its static AST evaluator does not observe raw SQL text, dynamic table selection, reflection/runtime behavior, or database permissions.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
