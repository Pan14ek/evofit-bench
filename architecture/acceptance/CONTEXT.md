# Context — `architecture/acceptance`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `architecture/CONTEXT.md` before this file.

## Responsibility

Import Linter current-source acceptance configuration and additive A1 source-based architecture evaluators with state-specific engineering acceptance policies.

## Local landmarks

- `importlinter.toml`
- `a1/` — source-based evaluators for AC_PUBLIC_API, AC_MODULE_GRAPH, and AC_DATA_OWNERSHIP, with state-specific engineering acceptance policies.

## Established conventions

Run `make architecture-test` for the historical A0.1 checks and `uv run pytest --no-cov -p no:cacheprovider tests/architecture/a1` for the source evaluators. The W0 state-specific engineering policies recorded in `a1/W3_HANDOFF.md` and versioned state configs govern the named architecture acceptance gates.

## Constraints and known gaps

These are not the frozen A0 research fitness evaluator. W0 approval covers the named state-specific engineering acceptance policies only; it does not establish a complete scientific applicability/mandatory universe, representation-to-obligation semantic adequacy, production policy authority, G1 completion, or G4 authorization. The evaluators do not alter the A0.1 manifest or historical acceptance tests.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
