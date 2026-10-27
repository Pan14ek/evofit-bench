# Context — `tests/unit`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `tests/CONTEXT.md` before this file.

## Responsibility

Contract, schema, validity, applicability, safety and deterministic tests.

## Local landmarks

- test_research_dashboard.py — validated read-only result loading, descriptive scenario/repetition summaries, explicit D2 mismatch, and deterministic figure export; no Method P execution.
- `test_monograph_evidence_package.py` — validates source replay, EVAL aggregate/archive/report consistency, exact text outputs, platform-independent figure metadata, checked-in figure digests, and read-only behavior; it does not execute the canonical Method P experiment.

- `p_applicability_support.py`
- `test_module_public_apis.py` — ΔA2 facade exports, shared `TaskSummary` type, delegated semantics and import-boundary regression
- `test_architecture_stage_checks.py` — rejects missing/partial interfaces, stale historical pins, A0.2/A0.3/A0.4/A0.5 ambiguity, committed state-manifest deletion, invalid state/policy evidence, stage downgrade, failed evaluators, dirty source and vacuous test selection; preserves historical A0.2/A0.3/A0.4 detection and pins CI to A0.5.
- `test_a05_data_ownership.py` — validates the prospective A0.5 ownership manifest and shows a controlled foreign-table access remains invisible to the old public API/module graph analyzers while the existing ownership analyzer reports it.
- `test_mono_ci_psi_a05.py` — also checks evaluator-specific finding attribution against patch-added source lines, three-state UNKNOWN/incomplete handling, archived diagnostic recomputation, and deterministic source-patch replay without a remote probe commit.
- `test_mono_ci_b0_psi_delta_a5.py` — validates ΔA5 local source pins and evidence-status separation; rejects source/method digest tampering, archive digest mismatch, historical value/timing overclaims, duplicate semantic identities, and uncountable evaluator/mapping cells, alongside fail-closed applicability cases. No test authorizes or executes a study.
- `test_da01_execution.py`
- `test_da01_inputs_and_isolation.py`
- `test_experiment_evidence.py`
- `test_exp01_evidence.py`
- `test_exp02_fitness_evidence.py`
- `test_pilot01_results.py`
- `test_eval01_runner.py` — EVAL-01 case-level metric aggregation and fail-closed provenance/unknown handling.
- `test_eval02_runner.py` — EVAL-02 separates architecture labels from expected evaluator output and excludes inapplicable boundary cases from binary metrics.
- `test_eval02_postrun_validation.py` — EVAL-02 post-run checks preserve binary metrics while distinguishing completed calls, provenance, diagnostic mismatches, analysis and archive integrity.
- `test_pilot02_method_input_profile.py` (also checks evaluator-run records bind source,
  configuration, command, metrics and raw streams to exact digests)
- `test_p_candidate_governance_v1.py` (including verified inherited-row bindings)
- `test_pilot02_candidate_evaluators.py`
- `test_pilot02_testonly_execution.py`
- `test_p_adaptation_evidence_v1.py` (signed/unsigned verifier-sidecar admission)
- `test_fault_state.py`
- `test_p_applicability_policies_v1.py`
- `test_p_applicability_ruleset_v1.py`
- `p_spec03_support.py`
- `test_p_impact_v1.py`
- `test_p_semantic_pairs_v1.py`
- `test_p_operations_v1.py`
- `test_p_candidate_governance_v1.py`
- `test_p_executable_candidate_identity.py` — verifies the candidate source/configuration manifest, Git tree, and tamper detection
- `test_p_interface_readiness.py` — preserves the NOT_READY measured-method guard
- `test_p_adaptation_evidence_v1.py`
- `test_g1_method_decision_register.py`
- `test_b0p_git_inventory.py`
- `test_b0p_development.py`
- `test_b0p_execution.py` — prediction/source/bundle bindings, tamper rejection, P HOLD markers, no-scorer reference rules, unknown denominator/resource metrics, evaluator identity, write-once checks, append-only checksum inventories, and B0/P candidate-validation propagation into direct manifest assembly
- `test_b0p_e1_execution.py` — exact-run sidecar/signature/source bindings, independent Git fact readback, run-contained semantic-directory readback, complete six-row UNKNOWN RQ2, candidate diagnostics under HOLD, oracle contamination, write-once behavior, and RQ1 abstention gating
- `test_mono_a1.py` — synthetic MONO reference seals, denominator/scoring gates, exact-pair mapping, W2 JSON readback adapter, input isolation, timing, and archive integrity; no MONO runs or authentic evaluator outputs
- `test_mono_a1.py` — synthetic MONO reference seals/source pins, E2 predecessor/A0 SHA/final-state negative schema cases and Git-object seal rejection, RQ1 prediction seals/abstention, RQ2 denominator/exact-pair/verifier boundary and TEST_ONLY separation, timer/source-image gaps, isolation, and clean archive readback
- `test_mono_policy_review_inventory.py` — catalog pin/order/ID and digest checks; missing authority, unresolved mandatory status, missing stages/facts, conflicting or stale facts, exact-pair gaps, and non-certification assertions
- `test_mono_e1_ci_profile.py` — draft CI-only fitness-profile contract checks: exact A0.3/A0.4 source pins, complete 18-ID catalog with unresolved classifications, engineering-only evaluator claims and adversarial NO_GO safeguards; no scientific execution or approval.
- `test_mono_e1_preflight.py` — exact W0 source identity, workload repeatability/digest and fixture/migration parity, capability inventory, arm allowlists and path isolation, external image verification, timing boundaries, null CPU/RSS, and pending-authority rejection; synthetic preparation only
- `test_mono_ci_b0_psi_preflight.py` — pinned source/archive and package digests, historical-observation/case-source mismatch rejection, B0/Ψ metric applicability and status semantics, common-input parity, no scorer/method-input leakage, unknown applicability, baseline/method blockers and immutability; preparation only, never a measured comparison.
- `test_mono_ci_b0_psi_execution.py` — prospective baseline provenance, exact case/tree materialization, bundle-to-checkout source/config/state equivalence, tamper rejection before evaluator execution, common-input parity, arm/output isolation, forbidden-input rejection, source-bound evaluator records, separate unscored scorer output, result readback, nonnumeric statuses, and preserved NO_GO/P guards; DEVELOPMENT only.
- `test_mono_ci_b0_psi_execution.py` archive cases — deterministic ZIP and sidecar verification, exact raw-output/provenance inventory, safe extraction, missing/modified member rejection, forbidden-file rejection, and unchanged scientific nonmeasurement statuses.
- `test_mono_ci_psi_transition.py` — checks architecture-manifest requirement extraction, historical V1 diagnostic readback, scientific status guards, and A05 archive-name/baseline compatibility, then executes the actual DEVELOPMENT P path once on the source-pinned A0.3→A0.4 transition; it reads back evaluator coverage and TEST_ONLY evidence, verifies post-method diagnostic isolation, round-trips the archive, and rejects tampering/status promotion without hardcoding the method decision.
- `test_mono_ci_psi_a05.py` — verifies the separate A0.4 prospective two-control baseline, independent ownership obligation mapping, materialized-candidate coverage projection, adapter version/pins, and non-oracle/non-expected-operation boundary.
- `test_mono_ci_psi_coverage.py` — independently derives file scope and source digests, rejects omitted/unexpected/altered/stale evaluator inputs, compares static imports and cycles, preserves dynamic-edge uncertainty, and proves the typed assessment detects a missing manifest requirement, rejects evaluator-sourced requirements and unverified mappings, and keeps incomplete inventories unresolved.
- `test_mono_ci_psi_evidence.py` — checks canonical evaluator-source manifest digests, V1-compatible and V2 independently scoped projections, TEST_ONLY verifier scope/signatures, and preservation of unknown semantic adequacy in the evidence adapter.
- `test_mono_e1_a03_fitness_candidate.py` — verifies the A0.3 DEVELOPMENT lineage candidate stays separate from frozen A0 B0 and binds candidate engineering controls to canonical source/configuration readback without assigning representation IDs.
- `test_mono_e1_a03_dev_fitness_config.py` — validates the separate B0_DEV_A03 proposal, exact provenance and archived evaluator controls, and rejection of missing evidence or unauthorized scientific promotion.
- `test_mono_e1_dev_p_decisions.py` — scenario/reference schema and digest, method-input reference exclusion, verified TEST_ONLY replay, missing/stale evidence HOLD behavior, raw digest tamper rejection, and no scientific-status promotion for the separate synthetic experiment.

This is a selected list of direct tracked files, not a complete source inventory.

## Established conventions

Test negative/unverified/expired/contradictory inputs plus backward compatibility.
PILOT-02 candidate-evaluator cases verify the materialized row, source revision,
profile artifacts, scope, stage, coverage links, and evidence contract before a
scoped evaluator can run; mismatches must remain unmeasured.
PILOT-02 semantic-proof preflight accepts a new row only when its full template
is present in the verified candidate-template catalog; a conflicting row with
the same ID in the parent representation catalog fails closed, and materialized
candidate equality is checked again before proof reuse.
The post-materialization comparison indexes the actual `representations` list
returned by scoped candidate evaluators; it must not look for a nonexistent
`records` field or treat measured bindings as unavailable.
Profile V2 tests also reject parent-catalog digest mismatches, unknown inherited
rows, and evaluator bytes that do not match the verified profile binding.
SPEC03 regression cases also check stale pair revisions, conflicting and
digest-tampered pair assessments, parent-byte/mapping consistency, publish
decision integrity, exact-hash rollback authorization, and full-template
descriptor authorization. Verifier-sidecar tests bind signed evidence to source
digests and immutable snapshots, including V1 compatibility and V2 replay
rejection. The G1 register test audits required decision IDs and pending gate
status; it cannot approve a decision.

`test_mono_a1.py` exercises preparation contracts only. Its synthetic Git
SHAs, raw records, and verifier adapter are not MONO-E1/E2 observations or W2
evaluator evidence. Requirement traceability is in
`experiments/execution/MONO_A1_PROTOCOL_V1.md`.

`test_mono_e1_preflight.py` validates only the comparability preparation
contract. Its clean positive case is structurally consistent but intentionally
INCOMPLETE/NO_GO; adversarial cases do not construct a frozen bundle, execute
an arm, or provide scientific authority.

## Constraints and known gaps

The B0/P preparation tests independently clone the Git source and verify exact
input bundles, six-obligation protocol denominator, pinned source bytes,
write-once behavior, and package readback. `test_b0p_execution.py` checks the
separate continuation's fail-closed seals, evaluator bindings, P governance
markers, abstention rules and unknown measurements; synthetic cases do not
substitute for the isolated real execution or produce RQ scores.

E1-specific unit checks keep calibration labels out of method inputs, reject
sidecar replay across run IDs or policy revisions, verify run-contained semantic
evidence directory readback, and preserve candidate potential as a diagnostic
while governance is HOLD. They do not substitute for a fresh B0/P container
execution or make TEST_ONLY authority independent.

Current coverage gate reports app-only coverage, not research-tool or requirement completeness. EXP-01 source-binding cases use synthetic Docker identity observations; a passing fixture does not supply authoritative source-to-image provenance. SPEC03 fixtures are synthetic and explicitly TEST_ONLY.

`tests/unit/test_exp01_evidence.py` and `tests/unit/test_exp02_fitness_evidence.py` are included in `DEVELOPMENT_REGRESSION_TESTS` and run again individually by `make development-regression-test` to expose their test counts in hosted logs. EXP-02 fixtures use digest-bound evaluator records, check that digest-valid derived-evidence tampering is rejected, and never provide independent coverage.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. SPEC 01/02/03 DEVELOPMENT checks use `make development-quality` with a **disposable** PostgreSQL database; its lint, format, type-check, and test discovery exclude the two protected DA01 modules. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.

- test_pilot02_v6_archive.py verifies the PILOT-02 V6 packaging-copy helper preserves payload bytes, emits sha256sum-compatible relative rows, and rejects traversal paths; it does not alter or authorize the historical experiment.
