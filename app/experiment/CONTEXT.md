# Context — `app/experiment`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `app/CONTEXT.md` before this file.

## Responsibility

Deterministic process-local fault hooks for research tests.

## Local landmarks

- `__init__.py`
- `fault_injector.py`
- `fault_state.py`

## Established conventions

Fault controls require EXPERIMENT_MODE; reset on completion.

## Constraints and known gaps

Not a distributed chaos engineering system; do not leave active in normal operations.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
