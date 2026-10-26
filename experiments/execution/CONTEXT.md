# Context — `experiments/execution`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `experiments/CONTEXT.md` before this file.

## Responsibility

Phase A input isolation, contracts, preparation, SPEC01 validation, SPEC02 applicability, and the generic SPEC03 governed-adaptation development pipeline.

## Local landmarks

- tooling/mono_e1_a03_fitness_config.py — read-only schema, digest, canonical-source, and evaluator-archive validation for proposed B0_DEV_A03; it does not invoke Method P or alter readiness

- `P_APPLICABILITY_V1.md`
- `P_INPUT_V11.md`
- `P_INPUT_V12_DEVELOPMENT.md`
- `P_INPUT_V11_SENSITIVE_SHA256.txt`
- `da01/P_ALGORITHM_STATUS.md`
- `tooling/p_adaptation.py`
- `tooling/p_impact.py`
- `EXP03_METHOD_INTEGRATION.md`
- `EXP04_EVIDENCE_ADMISSION.md`
- `MONO_A1_PROTOCOL_V1.md` — historical MONO-E0/E1/E2 preparation protocol; source-identity fields for E1 are superseded by the additive W0 addendum; no observed MONO results
- `MONO_A1_PROTOCOL_V1_W0_ADDENDUM.md` — versioned A0.3/A0.4 source-identity correction; does not authorize a run or freeze
- `MONO_E1_COMPARABILITY_PREFLIGHT_V1.json` and `schemas/mono_e1_comparability_preflight_v1.schema.json` — strict read-only B0/P comparability preparation snapshot; current status remains INCOMPLETE/NO_GO
- `MONO_E1_COMPARABILITY_PREPARATION_REPORT_V1.md` — requirement-to-test traceability and authorized-run integration handoff
- `tooling/mono_e1_preflight.py` — exact source/artifact readback, proposed workload/fixture specification, arm allowlist checks, isolation and measurement-boundary checks; no arm execution or scorer access
- `mono-ci-b0-psi-v1/` and `tooling/mono_ci_b0_psi_preflight.py` — separate, read-only preparation for a bounded monograph CI comparison; current NO_GO, historical observations excluded from methods/current case status, metric statuses defined by arm, and no method bundles or measured execution.
- `mono-ci-b0-psi-execution-v1/` and `tooling/mono_ci_b0_psi_execution.py` — separately versioned baseline-reconstruction proposal and DEVELOPMENT-only input/evaluator runner; preserves NO_GO and does not score.
- `mono-ci-b0-psi-execution-a05-v1/` and `tooling/mono_ci_psi_a05.py` — separate prospective A0.4 two-control baseline and bounded A0.4→A0.5 adapter; fresh ownership probes, raw evidence, and Method Ψ DEVELOPMENT result preserve NO_GO and do not score.
- `tooling/mono_ci_psi_transition.py` — additive one-transition A0.3→A0.4 Method P DEVELOPMENT execution and verified archive; keeps method runtime isolated from repository/Git/network access and leaves official NO_GO/NOT_READY gates intact.
- `tooling/mono_ci_psi_a05.py` — transition-specific adapter over the existing isolated runner; it leaves A0.3→A0.4 defaults unchanged and records an independently source-bound ownership positive/negative probe.
- `tooling/mono_ci_psi_evidence.py` — fresh A1 evaluator observations, V1-compatible / V2 source-scope evidence projection, source-inventory fact readback, and a run-local TEST_ONLY evidence trust context; it does not supply normative authority or semantic adequacy.
- `tooling/mono_ci_psi_coverage.py` — independent Git-tree/config/manifest inspection coverage and source-derived static module-import/cycle comparison; typed adaptation comparison keeps exact dynamic dependency completeness UNKNOWN.
- `schemas/mono_ci_psi_inspection_coverage_v1.schema.json` and `schemas/mono_ci_psi_adaptation_necessity_v1.schema.json`/`v2` — additive DEVELOPMENT diagnostic contracts, separate from Method P operation selection; V2 records independent requirement provenance/completeness and separately verified evaluator capabilities, while V1 remains readable without reinterpretation.
- `MONO_CI_PSI_EVIDENCE_REQUIREMENT_TEST_MATRIX.md` and `MONO_CI_PSI_EVIDENCE_BACKED_DEVELOPMENT_REPORT_UK.md` — implementation-to-test traceability and the source-revision-specific DEVELOPMENT run readback; neither is a scientific approval or result claim.
- `MONO_CI_PSI_COVERAGE_ADAPTATION_REPORT_UK.md` — readback of the verified A0.3→A0.4 source coverage, the separate adaptation-necessity diagnosis, actual Ψ HOLD, and unchanged scientific gates.
- `MONO_CI_PSI_TRANSITION_DEVELOPMENT_REPORT_UK.md` — concise Ukrainian record of the raw DEVELOPMENT result, hashes, uncertainties, verification and unchanged research gates.
- `MONO_CI_PSI_A05_DEVELOPMENT_REPORT_UK.md` — source-bound A0.4→A0.5 ownership probes and actual Ψ HOLD/candidate readback; reports the PARTIAL engineering finding, private archive verification, and billing-blocked hosted run without advancing research gates.
- `MONO_A1_REFERENCE_FREEZE_CHECKLIST.md` — preserved V1 checklist; see V2 for current W0 readiness
- `MONO_A1_REFERENCE_FREEZE_CHECKLIST_V2.md` — current W0 checklist for `G-A1-C4-REF-FROZEN`; the source-pair identity sub-item is verified, while all scientific, method, fixture, custody, freeze, and readback blockers remain
- `../../docs/MONO_E1_W0_READINESS_RESOLUTION.md` — W3 finding dispositions, authority boundary, complete-Q process, pair/P/input/custody blockers, and dependency-ordered plan; contains no scorer labels
- `MONO_A1_RESULTS_TEMPLATE_UK.md` — Ukrainian report template with explicit UNKNOWN/NOT_RUN states and evidence placeholders
- `schemas/mono_a1_study_v1.schema.json`
- `schemas/mono_a1_reference_v1.schema.json`
- `schemas/mono_a1_exact_pair_evidence_v1.schema.json`
- `tooling/mono_a1.py` — additive MONO reference seal/readback, input isolation, W2 A1 exact-pair adapter, endpoint helpers, and archive readback; no actual trial runner
- `schemas/exp03_method_integration_v1.schema.json`
- `schemas/exp03_method_p_execution_trace_v1.schema.json`
- `schemas/exp04_evidence_admission_v1.schema.json`
- `schemas/exp04_method_p_execution_trace_v1.schema.json`
- `schemas/exp04_evidence_verifier_config_v1.schema.json`
- `tooling/b0p_development.py`
- `tooling/b0p_e1_execution.py` — versioned E1 envelope that composes the unchanged isolated B0/P runners with exact-run TEST_ONLY evidence, a presealed exposed-calibration reference, independent pair readback, canonical RQ1 only after both sealed predictions, and a complete UNKNOWN RQ2 table
- `schemas/b0p_development_study_v1.schema.json`
- `schemas/b0p_evidence_sufficient_execution_v1.schema.json`
- `schemas/b0p_e1_rq2_obligation_evidence_v1.schema.json`
- `../../scripts/prepare_b0p_development_comparison.py`
- `../../scripts/verify_b0p_development_comparison.py`
- `P_GOVERNED_ADAPTATION_V1.md`
- `P_EXECUTABLE_CANDIDATE_V1.json` — source/configuration byte identity for the DEVELOPMENT review candidate; does not freeze or authorize Method P
- `README.md`

## Established conventions

Research implementation under tooling/; DA01 protocol under da01/.

The MONO-E1 A0.3 fitness configuration is a new bounded DEVELOPMENT proposal,
not a historical parent config or approved method input. Its source-bound
engineering observations and EVAL-01/02 controls remain separate from
applicability, semantic validity, reference custody, and scientific approval.

## Constraints and known gaps

SPEC03 pipeline code and additive DEVELOPMENT schemas are implemented and
synthetically tested. V2 adaptation evidence binds full template descriptors;
V1 artifact hashes remain non-authorizing. V3 Snapshot v1.2 can bind separate
before/after registry closure claims; its positive no-op and ADD regressions
use TEST_ONLY evidence, while the v1.1 single-claim negative case remains
UNKNOWN/HOLD. This does not make P ready for measured trials: production inputs
still lack approved policy authority, mandatory classifications, evaluator
templates, and cost authority, and G1/G4 remain separate. Keep
`p_interface.py` readiness blocked until the documented gates are met.

The B0/P preparation runner produces source-pinned, read-only method bundles,
checks frozen B0 bytes and independently recomputes the four Git module
inventory fields. Its status remains `PREPARED_NOT_EXECUTED`; it does not
create predictions, open the scorer, assert pair coverage, or change G1/G4.
The selected A0-to-A0.1 transition is `CALIBRATION_EXPOSED`. Readiness and
exact blockers are recorded in `docs/g1/B0P_READINESS_V1.md`.

The additive A0.3→A0.4 Ψ execution path binds fresh A1 evaluator processes to
both exact source revisions, while only fresh A0.4 observations enter the
adaptation sidecar. Independent coverage derives expected files from pinned Git
trees, state manifests, and evaluator configuration, then compares output paths
and source digests. The graph check compares static imports and cycles while
leaving dynamic dependency completeness UNKNOWN. A separate adaptation
diagnostic runs after Method P and is not supplied as a method input. Its V2
contract separates requirements extracted from pinned architecture manifests
and catalog/authority uncertainty from typed capabilities extracted from
evaluator configuration and raw observations. It compares them only through
documented structured mappings; historical V1 reports retain schema and
checksum readback without reinterpretation. Sidecar
verification is explicitly `TEST_ONLY`; pair adequacy and normative mapping
remain `UNDETERMINED`, and source-inventory readback recomputes only four module
facts from digest-pinned inventory paths.
The runtime remains network-isolated and cannot read the source repositories
or A0.3 evaluator observations. The run/archive schemas retain NO_GO,
NOT_READY, G1/G4 and reference-gate boundaries; no scoring or cross-arm
comparison is performed.

The A0.4→A0.5 adapter is a separate V3 run identity. Its prospective baseline
contains only the two A0.4 active controls. A0.5's static persistence ownership
requirement is independently extracted from the versioned state manifest and
compared after Method Ψ; AC_DATA_OWNERSHIP is a separately executed, available
evaluator rather than a preloaded baseline representation. A clean A0.5 source
and an isolated Tasks→Notifications foreign-table probe bind to exact commits,
configuration digests, raw outputs, and independent inspection coverage. The
probe demonstrates only the recorded static detector scope. Method input remains
governed by the existing V3 projection and DRAFT/OPEN policy source; the run's
actual decision and any candidate status are preserved without inserting
preregistered expected operations. All official readiness and authorization
gates remain unchanged.

The additive E1 execution contract is separate from the generic continuation
schema. It may consume an exact-run PILOT-02 TEST_ONLY sidecar, copies the
semantic-verification input into the immutable run, and reads back two semantic
control pairs from that run-contained directory; that scope does not grant
production authority or establish full six-obligation RQ2 coverage. Its
reference is copied outside the P method mounts, RQ1 is scored only after both
outputs are sealed, and an abstaining P remains NOT_EVALUABLE without a
manufactured prediction. Resource CPU/RSS remain UNKNOWN unless a sampler
supplies real measurements.

MONO-E1/E2 preparation uses its own `mono_a1` namespace: source-pinned,
author-declared reference seals; exact-run predictions; complete mandatory
denominators; pair sidecars; timing and RQ4 evidence; and checksum archives.
`W2A1ExactPairReadbackVerifier` consumes the W2 versioned JSON report and
invokes the exact pinned W2 checkout's `verify_evidence()` for byte readback.
Its synthetic test fixture proves only the adapter contract, not evaluator or
experiment outcomes. No MONO run is authorized until W0 freezes the required
reference inputs, policy and lifecycle authority, exact-pair semantic evidence,
method identities, shared inputs, and scorer custody. The E1 source pair is
now Git-read-back and recorded in the additive W0 addendum; that does not close
`G-A1-C4-REF-FROZEN`. These contracts do not change DA01, B0, Method P, or
historical results.

The MONO-E1 comparability preflight is a separate read-only preparation layer.
It rechecks the exact W0 A0.3/A0.4 pair, canonical checkpoints and observations,
method candidate bytes, shared-input parity, explicit arm allowlists, runtime
limits, isolation and timing boundaries. Its current workload profile is a
proposal, its fixture is specified but not created, and its method bundles,
images, external attestations, policy/lifecycle authority, complete evaluator
capability inventory, reference custody, G1 and G4 remain blocked. Never use
this preflight as permission to run or freeze MONO-E1.

The EXP-03 bridge in `scripts/exp03_method_bridge.py` reads validated EXP-02
artifacts and optionally executes the verified V3 pipeline. EXP-02 execution
and compliance observations remain separate from semantic pair proof. The
bridge supplies no trust context or evidence sidecar, so the DRAFT/OPEN pilot
path remains UNKNOWN/HOLD, and the machine-readable output states that EXP-02
evidence is not admitted to P calculations. Its v1.1.0 readback revalidates
referenced source inputs and cross-checks manifest fields against the P trace.
See `EXP03_METHOD_INTEGRATION.md` for preparation, commands, output fields,
and constraints.

EXP-04 records each EXP-02 observation and checks all P identity dimensions
before it can reach the V3 evaluator-evidence path. It reuses the V3 verifier
registry and `run_adaptation()`; it adds no semantic verifier. Manifest/trace
schema 1.1.0 separates mapping eligibility, execution authorization scope, and
actual exact-pair consumption. TEST_ONLY evidence can exercise DEVELOPMENT
execution but cannot establish research authority. The current A0.1-to-V3
mapping and runtime source identity stay unresolved, so ordinary runs execute
P without EXP-02 evidence. See `EXP04_EVIDENCE_ADMISSION.md` for the readback
contract and unresolved requirements.

The MONO CI B0/Ψ supplement is a separate proposal to PR #51. It records the
absence of a historical A0.3 fitness configuration, freezes a two-control
prospective reconstruction for review, and includes a local technical runner.
Its B0 evaluator probe is DEVELOPMENT-only; the measured P guard, study NO_GO,
G1/G4, and the ΔA4 reference gate remain intact. No scorer reference or
positive adaptation case is created.

## Verification and further reading

For the evidence-backed A0.3→A0.4 path, `make test-mono-ci-psi-transition`
runs the real isolated transition integration test and its adapter/verifier
unit tests. The hosted workflow also runs `make test-mono-ci-b0-psi-execution`,
`make development-quality` with a **disposable** PostgreSQL database, then
packs and verifies the fresh transition archive. Development quality excludes
the two protected DA01 test modules from discovery. When a context summary
conflicts with source code, a reviewed manifest or a frozen scientific
protocol, **report the conflict**; do not silently reinterpret research rules.
