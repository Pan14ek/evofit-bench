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
- `mono_e1_preflight.py` — read-only MONO-E1 comparability verifier; reuses source revision, method-bundle, image-provenance, and timing validators without executing either method
- `mono_ci_b0_psi_delta_a5.py` — read-only ΔA5 V2 local package verifier; optional historical replay accepts only an explicit local archive and uses `mono_ci_b0_psi_archive.verify_psi_transition_archive` after checking the pinned archive digest. The default performs no artifact download and reports replay as `NOT_EXECUTED`.
- `mono_ci_b0_psi_preflight.py` — read-only source/archive/package verifier for a separate monograph-specific CI comparison; hard-fails on provenance drift, rejects historical observations as current-case evidence, validates arm-specific metric statuses, and preserves NO_GO without invoking evaluators, methods or scorer.
- `mono_ci_b0_psi_execution.py` — exact-source materialization, separate DEVELOPMENT common-input bundles, B0 evaluator-only technical validation, checksummed result readback, and preserved NO_GO/Ψ guards.
- `mono_ci_b0_psi_archive.py` — deterministic archive pack/readback for verified DEVELOPMENT raw outputs; embeds the run/bundle provenance, exact execution boundary, dependency/environment identities, reproduction commands, and member hashes, then writes a detached SHA-256 sidecar.
- `mono_ci_psi_transition.py` — one exact A0.3→A0.4 Method P DEVELOPMENT execution using the public V3 verifier/adaptation API and a source-denying network-isolated runtime. It independently verifies evaluator coverage, writes a post-method adaptation-necessity diagnostic outside the P input, and checksums/recomputes both outputs during archive readback.
- `mono_ci_psi_a05.py` — bounded A0.4→A0.5 transition adapter over the existing isolated Method Ψ runner; V4 persists a binary probe patch, exact changed source bytes, evaluator configs and raw streams, and can replay a deterministic local-only probe commit without a remote probe object. Detection attribution binds evaluator-specific findings to added probe lines and structured import, dependency-edge, or table-owner evidence; code matches alone are insufficient.
- `mono_ci_psi_evidence.py` — runs pinned A1 evaluators against clean A0.3/A0.4 worktrees, records backward-compatible V1 or coverage-bound V2 source-scope evidence, adapts only active baseline controls into existing V3 evidence, and provides run-local TEST_ONLY sidecar signatures. It asserts no semantic adequacy or policy authority.
- `mono_ci_psi_coverage.py` — independently derives expected evaluator files from pinned Git trees, state manifests and evaluator configuration; checks source digests, reported scope and counts; reconstructs static imports/cycles; and compares typed source-independent requirements with separately verified evaluator capabilities through a bounded mapping registry. Exact dynamic dependency completeness remains UNKNOWN.
- `mono_ci_b0_psi_archive.py transition-pack/transition-verify` — additive transition-level archive contract using the existing deterministic ZIP, SHA-256 sidecar, member checks, extraction and readback helpers; V1/V2/V3 readback remains unchanged and V4 requires the source checkout to replay and verify the ΔA5 probe and recompute its evaluator-specific detection diagnostic.
- `mono_ci_b0_psi_scoring.py` — separate post-run scorer gate; verifies sealed DEVELOPMENT results and emits categorical NOT_EVALUABLE statuses until a separate approved reference exists. The execution runner does not import it.
- `mono_e1_a03_fitness_config.py` — read-only schema, digest, canonical-source, frozen-A0, and evaluator-archive verifier for proposed B0_DEV_A03; it neither runs Method P nor changes readiness
- `mono_policy_review_inventory.py` — read-only structural validator for the public MONO-E1 proposal inventory; compares copied rows to the pinned catalog and reports unresolved decision dimensions without certifying approval
- `b0p_execution.py` — common immutable container preparation and evaluator helpers; P accepts a read-only evidence sidecar mount only when the caller supplies one

This is a selected list (21 direct tracked files), not a complete source inventory.


- mono_ci_psi_owner_authorized.py — preregistration freeze verifier, randomized repeated A1 evaluator calibration, existing A0.5 isolated DEVELOPMENT runner, calibration archive readback, and V4 per-run archive packing; owner-authorized exploratory lane only.
- mono_ci_psi_owner_authorized_analysis.py — deterministic descriptive analysis from verified raw archives, CSV tables, SVG timing figure, and Ukrainian monograph handoff; no score, coverage percentage, or inferential test.
- mono_ci_psi_owner_authorized_v2.py — additive V2 hosted Docker isolation preflight, write-once freeze verification, exact-source V1 evaluator raw-output replay, same-runner preflight binding, V2 DEVELOPMENT execution, partial-evidence archive/readback, and release-bundle verification; it does not call the official entrypoint or advance G1/G4.
- `mono_ci_psi_owner_authorized_v2.py` validates the reconstructed A0.4 baseline through `mono_ci_psi_a05._validate_a04_proposal`; the legacy transition proposal validator is not interchangeable. Technical-preflight failures preserve their actual pre-measurement diagnostics and input identities without creating calibration or transition records.
- mono_ci_psi_owner_authorized_v2_analysis.py — deterministic descriptive V1/V2 comparison tables, SVG, and Ukrainian monograph insertion map from verified archives; no scoring, compliance inference from process exit codes, or inferential statistics.

## Established conventions

Use deterministic source hashes and method-input isolation; keep scorer oracle-side.

## Constraints and known gaps

SPEC03 is a DEVELOPMENT implementation only. It uses SPEC02 applicability, exact-pair evidence, conservative impact, materialized templates, bounded deterministic operations, governance, provenance and conditional rollback. Do not use oracle/scorer inputs or claim G1/G4 readiness; unresolved authority, mandatory classifications, templates, costs, multi-stage contracts and method review produce HOLD or remain blockers.

The additive single-transition path records a fresh two-evaluator-by-two-state
matrix. Evaluator source/configuration and raw process outputs are digest-bound;
only the after-state rows enter P evidence, with semantic compatibility left
null and adequacy false. The embedded HMAC verifier/key is run-local and
TEST_ONLY, so signed bytes are reproducible integrity evidence rather than an
independent authority anchor. The isolated runtime consumes the sidecar and
source inventory facts while source repositories, network access and other
evaluator observations stay denied. This does not change measured-method
readiness or the authority required by G1/G4.

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

`mono_e1_preflight.py` binds the W0 A0.3/A0.4 identity, checkpointed
engineering observations, B0/P candidate identities, proposed common workload
and fixture specification, arm-specific allowlists, image attestations,
isolation, and timing boundaries. It returns INCOMPLETE/NO_GO while inputs or
authority are absent. Only external callbacks can authenticate image and
authority evidence; a manifest claim alone is insufficient. The module does
not create fixtures or bundles, invoke P, access the scorer, freeze a reference,
or run an arm.

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

`mono_e1_a03_fitness_config.py` validates the new two-control A0.3 DEVELOPMENT
proposal against its schema, pinned source/evaluator artifacts, preserved A0
baseline bytes, and archived EVAL-01/EVAL-02 evidence. It fails closed on
missing or contradictory evidence, reports semantic validity as UNKNOWN, and
does not produce a Method P input bundle or invoke Method P.

`mono_ci_b0_psi_execution.py` keeps PR #51's package unchanged and uses a
separate review proposal. It verifies A0.3/A0.4 source and evaluator identities,
materializes app-only case trees from pinned Git objects/bundles, and writes
separate B0/Ψ common-input bundles with no `.git`, EVAL archive, expectations,
scorer, or arm outputs. The B0 DEVELOPMENT evaluator reads configuration and
state manifests directly from its verified arm bundle. Because the evaluator
uses Git metadata, its checkout's complete `app/` byte map is compared with
both the bundle and the pinned Git tree before and after each evaluator; the
evaluator-reported source/config/state digests are checked against those same
bundle files before raw evidence is sealed. Run records persist this binding.
The probe records only raw evaluator outputs; applicability and semantic
validity stay UNKNOWN, no metrics/operations/governance are emitted, and Ψ is
BLOCKED_NOT_EXECUTED through the measured-method guard.

`mono_ci_b0_psi_archive.py` accepts only a fully verified run directory with
the four B0 raw-output pairs and the separate common-input bundles. It rejects
unexpected paths, validates bundle parity and run provenance, emits a
fixed-metadata ZIP and SHA-256 sidecar, and can safely extract and re-verify
that archive without a source checkout. The workflow publishes these files as
a DEVELOPMENT-only GitHub Actions artifact with 90-day retention.

`mono_ci_psi_transition.py` is a separate DEVELOPMENT supplement. It binds the
canonical A0.3/A0.4 commits, repository/application trees and original state
manifest bytes, carries the explicitly unapproved reconstructed B0 proposal as
the parent representation source, and invokes `verify_v3_p_bundle()` followed
by `run_adaptation()` once in an isolated runtime. Its result archive preserves
the raw HOLD/REJECT decision and UNKNOWN values without scoring. The archive
contains no B0 evaluator outputs, case outputs, scorer, oracle, Git metadata or
repository checkout. Packing and readback extend the existing B0/Ψ archive
module without changing its original contract. This does not change
`P_ALGORITHM_STATUS`, study readiness, G1/G4, or the reference-freeze gate.

Independent evaluator coverage and the adaptation-necessity assessment are
DEVELOPMENT diagnostics stored outside method input. File scope is rebuilt
from the source Git tree, state manifest and evaluator configuration;
explicit additional source paths outside the module root are resolved as
literal Git paths and included in the same digest-bound inventory. Static
module edges and cycles are checked against source. The graph evaluator's
dynamic dependency completeness remains UNKNOWN. V2 evidence binds expected
and inspected file scope, while archive verification can reconstruct the
historical V1 projection. The diagnostic label does not replace exact-pair,
normative, historical-baseline, independent-review or authorization evidence.
Evaluator execution records expose the configuration identity as
`configuration_sha256`; capability verification must consume that exact
digest, validate its SHA-256 shape, and retain the other source, scope,
execution, diagnostics and representation checks. Archive readback binds the
same field to the copied evaluator configuration artifact.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. DEVELOPMENT validation uses `make development-quality` with a **disposable** PostgreSQL database; the protected DA01 test modules are excluded. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
