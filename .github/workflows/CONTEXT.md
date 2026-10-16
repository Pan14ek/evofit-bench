# Context — `.github/workflows`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `.github/CONTEXT.md` before this file.

## Responsibility

CI workflow YAML: uv, Python and disposable PostgreSQL.

## Local landmarks

- `ci.yml`

## Established conventions

Keep actions aligned with Makefile and pyproject.toml.

## Constraints and known gaps

Do not skip tests to get a green run; skipped Docker isolation probes remain unresolved.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
