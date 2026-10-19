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

Review safeguards recognize only bundle objects returned by the V3 verifier,
bind their identity to every input digest, and recheck their content before
adaptation. Candidate materialization verifies that the
configuration mapping is the projection of the exact parent bytes whose hash
is recorded. Coverage excludes stale pair revisions and holds on conflicting
or digest-invalid assessments. Governance decisions expose isolated payload
copies; conditional publication rechecks the signed decision payload, and
rollback requires the exact configuration hash that was revalidated.

Method-side sidecars are schema-checked, content-hashed, bound to exact source
digests and verified through an explicitly configured verifier registry in
`p_adaptation_evidence.py`. V1 retains its artifact-hash meaning and cannot
authorize ADD/REPLACE; additive V2 authorizes a canonical full-template
descriptor digest tied to pinned capabilities and exact context. A missing
trust anchor leaves evidence unresolved. The additive Snapshot v1.2 DEVELOPMENT
projection supports independently verified closure claims for before and after
states. Synthetic V3 no-op and full-descriptor ADD cases reach ACCEPT and V1
adapters only under TEST_ONLY trust; legacy v1.1 single-claim, incomplete, or
mismatched evidence remains UNKNOWN/HOLD.

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
- `p_adaptation_evidence.py`
- `p_adaptation_evidence.py`
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

## PILOT-02 profile boundary

PILOT-02 adds one pinned A0.1 architecture-compliance profile to the verified
V3 capabilities path. The profile verifier checks the exact source
configuration, obligation catalog, evaluator configuration/source bytes, and
versioned profile definition before exposing candidate descriptors. Its
post-run exact-pair diagnostics bind authentic EXP-02 stdout/stderr and retain
unknown inspection scope and missing semantic proof. Those diagnostics are
not passed into `run_adaptation()` and do not establish coverage or authority.
The existing P algorithm continues to produce its own operations, candidate,
and governance decision.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. DEVELOPMENT validation uses `make development-quality` with a **disposable** PostgreSQL database; the protected DA01 test modules are excluded. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
