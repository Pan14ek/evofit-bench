# Context — `architecture/acceptance`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `architecture/CONTEXT.md` before this file.

## Responsibility

Import Linter current-source acceptance configuration and additive A1 source-based architecture evaluator proposals.

## Local landmarks

- `importlinter.toml`
- `a1/` — additive source-based evaluator proposals for AC_PUBLIC_API, AC_MODULE_GRAPH, and AC_DATA_OWNERSHIP.

## Established conventions

Run `make architecture-test` for the historical A0.1 checks and `uv run pytest --no-cov -p no:cacheprovider tests/architecture/a1` for proposed source evaluators. W0 must freeze A1 state-specific configuration before use as an approved gate.

## Constraints and known gaps

Not the frozen A0 research fitness evaluator. The A1 evaluator configs are proposals; they do not alter the A0.1 manifest or exact acceptance tests.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
