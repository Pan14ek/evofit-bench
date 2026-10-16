# Context — `tests/integration`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `tests/CONTEXT.md` before this file.

## Responsibility

Business API/DB integration and SPEC02 V3 full synthetic pipeline.

## Local landmarks

- `conftest.py`
- `test_api_flows.py`
- `test_p_applicability_v3.py`

## Established conventions

Use disposable DB and genuine interfaces instead of only mocked modules.

## Constraints and known gaps

Do not report integration success as G1/G4 or sample-level significance.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
