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
- `b0p_development.py`
- `b0p_e1_execution.py` — additive E1 isolated B0/P run envelope with run-bound TEST_ONLY sidecar, reference exclusion, exact-pair readback, canonical RQ1 gating and six-row UNKNOWN RQ2
- `mono_a1.py` — separate MONO-E1/E2 reference custody, prediction-scoring gates, exact-pair RQ2, W2 A1 readback, runtime prerequisites, and checksum archives
- `mono_policy_review_inventory.py` — read-only structural validator for the public MONO-E1 proposal inventory; compares copied rows to the pinned catalog and reports unresolved decision dimensions without certifying approval
- `b0p_execution.py` — common immutable container preparation and evaluator helpers; P accepts a read-only evidence sidecar mount only when the caller supplies one

This is a selected list (20 direct tracked files), not a complete source inventory.

## Established conventions

Use deterministic source hashes and method-input isolation; keep scorer oracle-side.

## Constraints and known gaps

SPEC03 is a DEVELOPMENT implementation only. It uses SPEC02 applicability, exact-pair evidence, conservative impact, materialized templates, bounded deterministic operations, governance, provenance and conditional rollback. Do not use oracle/scorer inputs or claim G1/G4 readiness; unresolved authority, mandatory classifications, templates, costs, multi-stage contracts and method review produce HOLD or remain blockers.

`b0p_development.py` prepares a write-once B0/P DEVELOPMENT package and
verifies its manifest, Git source inventories, frozen configuration bytes,
policy bundle and checksums. It is a preflight stage only: it does not execute
either arm, produce predictions, or score a result. Keep `PREPARED_NOT_EXECUTED`
distinct from an experiment outcome. Its B0, P, policy and architecture source
revisions are separate fields; do not infer authority from the policy digest.

`b0p_execution.py` continues a verified preparation in a separate write-once
run. It builds two source-pinned container contexts, executes B0 and frozen P
separately without network access, then records fresh Import Linter and
architecture-test outputs. `b0p_isolated_b0_runner.py` and
`b0p_isolated_p_runner.py` are run wrappers; the frozen algorithm modules stay
unchanged. The direct arm-result mappings must carry B0 validation from the
persisted execution trace and P validation from the persisted execution result
into manifest assembly; `test_candidate_validation_from_both_isolated_arms_reaches_manifest`
regresses the prior aggregation KeyError. The execution schema and archive are
distinct from the preparation schema and package. An unavailable presealed reference keeps RQ1 NOT_EVALUABLE;
an unbound denominator or missing independent exact-pair proof keeps RQ2
UNKNOWN. Do not turn this calibration-exposed execution into holdout evidence,
G1/G4 approval or measured DA01 results.

`b0p_e1_execution.py` leaves the legacy continuation manifest unchanged. It
uses the same generic preparation and B0/P runtime helpers, while binding a
separately prepared P bundle and signed TEST_ONLY sidecar to one E1 run ID.
The presealed reference is never mounted into either method container. The E1
schema permits a bound six-obligation denominator with `UNKNOWN` coverage and
requires the per-obligation table; it does not authorize an RQ2 percentage.
Canonical `score_rq1()` runs only after both sealed predictions exist, then
checks agreement with the pre-execution calibration reference. E0 remains an
immutable historical comparison point and is never rewritten by this path.

`mono_a1.py` is separate preparation infrastructure. Its exact-pair record
binds representation, obligation, architecture state/source, run, configuration,
and evaluator ID/version/digests. `W2A1ExactPairReadbackVerifier` requires the
reference-pinned W2 checkout and report schema, then calls its `verify_evidence()`
to re-read evaluator, configuration, and inspected subject bytes. Synthetic
adapter tests do not establish real evaluator or MONO results.

The narrowly scoped post-execution finalizer is for the historical a02
`candidate_validation` aggregation failure only; a new direct run must not use
it. The corrected direct path is verified separately by a04. The finalizer
verifies the original
inventory, preparation snapshot, runtime contexts, persisted runner output and
prediction seal, reuses both method outputs, reruns only fresh evaluator
commands under recovery-specific names, and adds a final checksum inventory
without replacing the original failed-attempt inventory. Its execution mode
must remain explicit in the manifest.

## PILOT-02 profile boundary

PILOT-02 adds one pinned A0.1 architecture-compliance profile to the verified
V3 capabilities path. The profile verifier checks the exact source
configuration, obligation catalog, evaluator configuration/source bytes, and
versioned profile definition before exposing candidate descriptors. Its
post-run exact-pair diagnostics bind authentic EXP-02 stdout/stderr and retain
unknown inspection scope and missing semantic proof. In the TEST_ONLY
continuation, a separately digest-validated sidecar of EXP-02 execution
records and raw artifacts is supplied to `run_adaptation()` before adaptation;
the records are not admitted as semantic pair proof and do not establish
coverage or authority. Keep the post-run diagnostics distinct from that
sidecar. The existing P algorithm continues to produce its own operations,
candidate, and governance decision.

Profile V2 also supplies digest-pinned A0.1 DEVELOPMENT evaluator bindings for
parent representations. The V3 verifier checks them against the exact parent
catalog digest and parent row identities. `p_candidate.materialize_candidate`
attaches only those verified artifact references to a detached candidate
snapshot and validates their bytes; it does not mutate parent bytes or consume
the run's evaluator outputs as semantic proof. V1 profiles remain supported.

`p_semantic.py` records compliance only when evaluator execution, identity,
target/stage/mapping scope, and evidence artifacts resolve. Adequacy,
evidence-contract satisfaction, semantic compatibility, and pair proof remain
separate: they can leave pair validity unknown without erasing a resolvable
compliance observation. An unresolved evaluator scope remains `UNKNOWN` even
when its process exits nonzero or zero; a resolved nonzero result is an
observation of noncompliance and does not by itself invalidate exact-pair
semantics.

PILOT-02's `run_pilot02_method_p.py` accepts semantic reports only from the
separate `pilot02_semantic_validation.py` readback verifier, and only in its
TEST_ONLY continuation. The verifier reconstructs typed inspection scope,
positive/negative control interpretation, and the pinned source mutation before
the existing `run_adaptation()` call. Candidate proof reuse is recorded only
when the materialized evaluator row and its evaluator artifact exactly match
the prevalidated template. These reports do not authorize DA01 measurement or
independent coverage.

MONO-A1's `mono_a1.py` is a new additive study namespace and does not modify
the existing B0/P, DA01, or DEV-B0P-E1 execution paths. It requires a verified
sealed reference before RQ1/RQ2, validates that both runs start after freeze,
and binds evidence to a common source/state/run/exact-pair identity.
`W2A1ExactPairReadbackVerifier` consumes W2's versioned JSON schema and invokes
`verify_evidence()` from the exact reference-pinned checkout. Missing, changed,
or mismatched reports remain UNKNOWN. TEST_ONLY is diagnostic only, and no
production authority value or trust anchor is implemented. The RQ3 source-image
helper validates shape/source binding for an externally verified attestation;
it does not authenticate signatures. Synthetic unit fixtures prove contract
behavior only and are not MONO-E1/E2 or authentic W2 evaluator evidence.

`mono_policy_review_inventory.py` reads the public proposal inventory, its
versioned JSON Schema, and the pinned catalog. Its PASS is limited to exact
catalog inventory readback. Authority, applicability, mandatory status,
lifecycle requirements, source-fact truth, semantic adequacy, and scientific
approval remain unresolved or unverified; the tool never emits an approval.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. DEVELOPMENT validation uses `make development-quality` with a **disposable** PostgreSQL database; the protected DA01 test modules are excluded. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
