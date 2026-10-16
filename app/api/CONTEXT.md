# Context — `app/api`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `app/CONTEXT.md` before this file.

## Responsibility

Shared operational HTTP endpoints and dependencies.

## Local landmarks

- `__init__.py`
- `dependencies.py`
- `experiment.py`
- `health.py`
- `metrics.py`

## Established conventions

Business route modules reside in app/modules/*/api.py; shared routes cover health, metrics and experiment control.

## Constraints and known gaps

Experiment endpoints require opt-in and must not be exposed publicly.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
