# Context — `experiments/execution/da01`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `experiments/execution/CONTEXT.md` before this file.

## Responsibility

Canonical Phase A protocol, safety gates, scoring rules and method isolation.

## Local landmarks

- `B1_CHECKLIST.md`
- `INPUT_ISOLATION.md`
- `PROTOCOL.md`
- `P_ALGORITHM_STATUS.md`
- `READINESS.md`
- `SCORE_RULES.md`
- `VALIDITY_RULES.md`

This is a selected list (8 direct tracked files), not a complete source inventory.

## Established conventions

Read PROTOCOL.md, INPUT_ISOLATION.md, READINESS.md and P_ALGORITHM_STATUS.md.

## Constraints and known gaps

Method must never ingest scenario oracle or private scoring information; G1/G4 open.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
