# Context — `load`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `CONTEXT.md` before this file.

## Responsibility

Locust load workload and read-only warmup orchestration.

## Local landmarks

- `README.md`
- `locustfile.py`
- `warmup_locustfile.py`
- `workload_profile.py`

## Established conventions

Use checked-in profiles; reset deterministic seed before measured workloads.

## Constraints and known gaps

Do not change canonical inputs without creating a new controlled profile version.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
