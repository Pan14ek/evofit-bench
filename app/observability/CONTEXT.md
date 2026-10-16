# Context — `app/observability`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `app/CONTEXT.md` before this file.

## Responsibility

Prometheus counters/histograms, structured logging and optional OpenTelemetry traces.

## Local landmarks

- `__init__.py`
- `logging.py`
- `metrics.py`
- `tracing.py`

## Established conventions

Separate expected business rejections from unexpected operation failures; keep bounded labels.

## Constraints and known gaps

Raw measurements are not proof of semantic fitness coverage or P efficacy.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
