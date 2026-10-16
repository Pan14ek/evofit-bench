# P algorithm status — DEVELOPMENT IMPLEMENTED, NOT READY FOR MEASURED STUDY

The merged SPEC 03 document from PR #8 is still labeled a draft/proposed
development specification. This branch implements its generic DEVELOPMENT
pipeline and additive `p_*_v1` contracts. The implementation adapts a versioned
fitness configuration; it does not edit application architecture.

## Implemented path

`tooling/p_adaptation.py` verifies a pinned V3 P bundle, calls the existing
SPEC 02 applicability evaluator for before/after states, computes typed fact,
policy and obligation deltas, assesses criterion-centric impact, exact
`(representation, obligation)` validity, mandatory coverage, and a deterministic
operation plan. It then materializes a digest-bound child configuration,
returns a governed `ACCEPT`, `REJECT`, or `HOLD`, and exposes V1 adapters. The
supporting modules are `p_impact.py`, `p_semantic.py`, `p_operations.py`,
`p_candidate.py`, and `p_governance.py`.

Synthetic tests use independent generic identifiers and explicit `TEST_ONLY`
provenance. They are code-verification evidence, not authority, measured
outcomes, a B1 result, or evidence of scientific advantage. `p_interface.py`
continues to report `NOT_READY`; the measured-method gate has not been opened.

## Current operational limits

The current V3 input/catalog path has no approved mandatory classifications,
generic evaluator templates, or authorized cost model. Missing or unresolved
proof remains `UNKNOWN` and produces `HOLD`; the pipeline must not infer
`INACTIVE`. The code does not create or execute evaluator programs. The
candidate path can only bind actual pinned artifact bytes and caller-supplied
method-side evidence.

The following independent questions in SPEC 03 remain open: B1 timing and RQ
crosswalk (OPEN-01/02), multi-stage controls (OPEN-03), real policy authority
(OPEN-04), shared evaluator templates and cost rules (OPEN-05/06), compliance
versus monitor-validity reporting (OPEN-07), multi-obligation V1 ADD encoding
(OPEN-08), independent method/holdout review (OPEN-09), and adaptive weight or
threshold research (OPEN-10). The DEVELOPMENT implementation does not resolve
them.

G1 and G4 remain separate approval requirements. No measured DA01 run was
conducted, and no human B1 result or oracle-derived expectation was created.
See [`docs/SPEC_03_IMPLEMENTATION_TRACEABILITY.md`](../../../docs/SPEC_03_IMPLEMENTATION_TRACEABILITY.md)
for requirement-level coverage, blocked rows and actual verification results.
