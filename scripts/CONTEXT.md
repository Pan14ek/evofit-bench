# Context — `scripts`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `CONTEXT.md` before this file.

## Responsibility

Seed/reset, metrics capture, workload runners, method prep and reproducibility tooling.

## Local landmarks

- `__init__.py`
- `collect_run_metadata.py`
- `da01_contracts.py`
- `da01_execution.py`
- `export_metrics.py`
- `finalize_run.py`
- `prometheus_snapshot.py`

This is a selected list (18 direct tracked files), not a complete source inventory.

## Established conventions

Run on disposable databases; fail clearly if required telemetry/provenance missing.

## Constraints and known gaps

Never fabricate logs, ignore invalid samples or run destructive commands on real data.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
