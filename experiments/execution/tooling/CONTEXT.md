# Context — `experiments/execution/tooling`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `experiments/execution/CONTEXT.md` before this file.

## Responsibility

Python tooling for export, validation, sealing and independent assessment.

## SPEC 03 governed-adaptation implementation

The additive `p_*` modules implement a development pipeline for adapting the
fitness configuration after architecture evolution. They do not change the
application architecture or the frozen V1 contracts. The intended entry flow
is `verify_v3_p_bundle()` followed by `run_adaptation()` in `p_adaptation.py`;
the first binds allowlisted V3 files and SPEC 01 validation, and the second
reuses SPEC 02 applicability before composing impact, pair evidence, coverage,
operations, candidate materialization and governance.

Module responsibilities:

- `p_impact.py` diffs typed fact and policy changes, validates traceability,
  and reports proven, possible and unresolved impacts conservatively.
- `p_semantic.py` evaluates exact `(representation, obligation)` pairs and
  mandatory coverage; compliance observations remain separate from semantic
  validity.
- `p_operations.py` selects deterministic retain, replace, add, deactivate and
  adjust operations. It requires real hash-bound templates and known authorized
  costs; unresolved prerequisites produce HOLD.
- `p_candidate.py` materializes a parent-bound candidate, derives its version,
  and adapts it to the existing V1 candidate schema. A candidate may be
  materialized before governance; the V1 prediction adapter is only returned
  after ACCEPT, and neither adapter publishes a configuration.
- `p_governance.py` applies ACCEPT/REJECT/HOLD precedence, records an
  append-only event chain, and checks conditional publish and rollback.

The pipeline must preserve `UNKNOWN` as unresolved, never infer `INACTIVE` from
missing evidence, and never use scorer/oracle output as P input. The JSON
schemas are additive DEVELOPMENT contracts. Synthetic test builders and
fixtures live under `tests/unit/test_p_*`, `tests/unit/p_spec03_support.py`,
`tests/integration/test_p_governed_adaptation_v1.py` and
`tests/fixtures/p_method/`; requirement-level status and known blockers are
tracked in `docs/SPEC_03_IMPLEMENTATION_TRACEABILITY.md`.

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
