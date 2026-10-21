# Context — `app/modules`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `app/CONTEXT.md` before this file.

## Responsibility

Capability-oriented business packages users, tasks, notifications, reporting and audit.

## Local landmarks

- `__init__.py`

## Established conventions

Read each child CONTEXT.md; dependencies are synchronous and governed by DA01 manifest.
The prepared shared `app.events` contract is a distinct allowed dependency
proposal for ΔA6; it does not yet change the A0.1 source graph.

## Constraints and known gaps

Packages are not separately deployed services or per-module databases.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
