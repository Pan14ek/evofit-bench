# Context — `experiments/execution/tooling`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `experiments/execution/CONTEXT.md` before this file.

## Responsibility

Python tooling for export, validation, sealing and independent assessment.

## Local landmarks

- `__init__.py`
- `b0.py`
- `b1.py`
- `contracts.py`
- `errors.py`
- `hashing.py`
- `inputs.py`
- `p_adaptation.py`
- `p_impact.py`
- `p_semantic.py`
- `p_operations.py`
- `p_candidate.py`
- `p_governance.py`

This is a selected list (17 direct tracked files), not a complete source inventory.

## Established conventions

Use deterministic source hashes and method-input isolation; keep scorer oracle-side.

## Constraints and known gaps

SPEC03 is a DEVELOPMENT implementation only. It uses SPEC02 applicability, exact-pair evidence, conservative impact, materialized templates, bounded deterministic operations, governance, provenance and conditional rollback. Do not use oracle/scorer inputs or claim G1/G4 readiness; unresolved authority, mandatory classifications, templates, costs, multi-stage contracts and method review produce HOLD or remain blockers.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
