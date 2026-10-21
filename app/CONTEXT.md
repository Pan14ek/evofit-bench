# Context — `app`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `CONTEXT.md` before this file.

## Responsibility

Benchmark FastAPI/Uvicorn application, currently capability-organized A0.1 monolith,
with additive event-contract preparation for the future ΔA6 transition.

## Local landmarks

- `__init__.py`
- `config.py`
- `main.py`
- `events/` — versioned in-process contract and synchronous dispatcher; not yet
  wired into Task service or application bootstrap.

## Established conventions

Business modules own domain logic; app.main composes routes/telemetry. The
shared event dispatcher accepts the caller's session and never owns commits.

## Constraints and known gaps

One process and database, synchronous calls and no broker; P method lives outside app.
ΔA6 event primitives are prepared but application-level rollback remains pending
sequential integration.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
