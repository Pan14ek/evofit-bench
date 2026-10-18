# Context — `tests`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `CONTEXT.md` before this file.

## Responsibility

Python unit, architecture and PostgreSQL integration suites, including EXP-01/02 evidence contracts, EXP-03 bridge integration, and independent synthetic SPEC03 impact, exact-pair, operation, materialization, governance, provenance and rollback tests.

## Local landmarks

- `__init__.py`
- `fixtures/p_method/`
- `unit/test_p_impact_v1.py`
- `unit/test_p_semantic_pairs_v1.py`
- `unit/test_p_operations_v1.py`
- `unit/test_p_candidate_governance_v1.py`
- `integration/test_p_governed_adaptation_v1.py`
- `integration/test_exp03_method_bridge.py`

## Established conventions

Synthetic tests and quality gates must be distinguished from scientific measured runs.

## Constraints and known gaps

SPEC03 fixtures are independently authored TEST_ONLY inputs. Never use oracle to manufacture P predictions or call skips passes; the SPEC03 synthetic pipeline is not measured validation.

The EXP-03 bridge integration tests use digest-valid EXP-02 fixture runs and
the repository's DRAFT/OPEN V3 policy pilot. They execute the actual verified
Method P development path and assert HOLD/UNKNOWN; they do not authorize
positive semantic proof or measured DA01 outcomes. Existing V3 TEST_ONLY
positive cases remain separate and run in the hosted development regression.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
