# Context — `architecture/states`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `architecture/CONTEXT.md` before this file.

## Responsibility

Versioned architecture-state records for the preserved capability application and additive governance states.

## Local landmarks

- `A0_1_CAPABILITY_MODULES.yaml`
- `A0_3_GOVERNED_MODULE_GRAPH.yaml` and its JSON Schema — ΔA3 predecessor, invariants, approved graph, temporary exception, mandatory evaluator set, and source provenance.

## Established conventions

The frozen A0.1 manifest remains historical input. A0.3 is an engineering state record; its source SHA is recorded in evaluator evidence rather than embedded in the manifest.

## Constraints and known gaps

The A0.3 record preserves one application process, one PostgreSQL database, synchronous Python communication, REST behavior, and caller-managed session/transaction ownership. It does not assert that static AST evidence observes dynamic imports, runtime behavior, or external deployment identity.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
