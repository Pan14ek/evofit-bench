# Context — `app/modules/reporting`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `app/modules/CONTEXT.md` before this file.

## Responsibility

Task status and assignment aggregate reporting.

## Local landmarks

- `__init__.py`
- `api.py`
- `public.py` — exports the existing task-summary query with the canonical `tasks.public.TaskSummary` return type.
- `schemas.py`
- `service.py`

## Established conventions

Delegates to Tasks service and shared database. `public.py` returns the canonical `tasks.public.TaskSummary`
shape. `service.py` intentionally keeps the direct `Tasks.service.task_summary` call as the
source-visible ΔA4 migration exception.

## Constraints and known gaps

No independent read model; a future architecture delta adds different communication.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
