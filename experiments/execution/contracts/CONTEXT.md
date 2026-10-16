# Context — `experiments/execution/contracts`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `experiments/execution/CONTEXT.md` before this file.

## Responsibility

Versioned FV and applicability rule data.

## Local landmarks

- `applicability_ruleset_v1.json`
- `fact_vocabulary_v1.json`

## Established conventions

FV_CORE_V1 contains exactly 12 allowed activation-grade predicates.

## Constraints and known gaps

Reserved predicates cannot be silently interpreted as false or present.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
