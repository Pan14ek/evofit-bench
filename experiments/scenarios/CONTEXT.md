# Context — `experiments/scenarios`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `experiments/CONTEXT.md` before this file.

## Responsibility

Registered scenario descriptions and oracle-side reference data.

## Local landmarks

- No direct tracked files; inspect the child directories.

## Established conventions

Method inputs must originate only from allowlisted versions, not private scenarios.

## Constraints and known gaps

Never inspect scenario ground truth when authoring P logic, policy rules or B1 responses.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
