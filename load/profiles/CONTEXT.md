# Context — `load/profiles`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `load/CONTEXT.md` before this file.

## Responsibility

Versioned baseline/smoke/warm-up YAML load profiles.

## Local landmarks

- `a0-baseline-v1.yaml`
- `a0-smoke-v1.yaml`
- `a0-warmup-v1.yaml`

## Established conventions

Read-only warm-up and timed load are different phases.

## Constraints and known gaps

Profiles are experimental controls, not measured method results.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
