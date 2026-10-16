# Context — `tests/integration`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `tests/CONTEXT.md` before this file.

## Responsibility

Business API/DB integration, SPEC02 V3 synthetic pipeline, and SPEC03 synthetic orchestration through impact, candidate and governance.

## Local landmarks

- `conftest.py`
- `test_api_flows.py`
- `test_p_applicability_v3.py`
- `test_p_governed_adaptation_v1.py`

## Established conventions

Use disposable DB and genuine interfaces instead of only mocked modules.

## Constraints and known gaps

Do not report integration success as G1/G4 or sample-level significance. The SPEC03 orchestration fixture is TEST_ONLY and intentionally HOLDs under OPEN authority.
The integration tests also reject caller-claimed VERIFIED_V3 provenance and
detect nested input mutation after the strict V3 verifier returns a bundle;
these checks do not replace a positive approved V3 production-input path.
Coverage regressions also ensure stale or colliding pair evidence cannot
satisfy mandatory obligations. Governance regressions bind publication to an
unchanged decision digest and rollback to the exact revalidated configuration.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
