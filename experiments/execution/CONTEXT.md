# Context — `experiments/execution`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `experiments/CONTEXT.md` before this file.

## Responsibility

Phase A input isolation, contracts, preparation, SPEC01 validation, SPEC02 applicability, and the generic SPEC03 governed-adaptation development pipeline.

## Local landmarks

- `P_APPLICABILITY_V1.md`
- `P_INPUT_V11.md`
- `P_INPUT_V12_DEVELOPMENT.md`
- `P_INPUT_V11_SENSITIVE_SHA256.txt`
- `da01/P_ALGORITHM_STATUS.md`
- `tooling/p_adaptation.py`
- `tooling/p_impact.py`
- `EXP03_METHOD_INTEGRATION.md`
- `EXP04_EVIDENCE_ADMISSION.md`
- `MONO_A1_PROTOCOL_V1.md` — separate MONO-E0/E1/E2 preparation protocol; W0-approved A0→A1 E2 source binding; E1 freeze-before-run custody, RQ mapping, denominator rules, and W0/W2 stop conditions; no observed MONO results
- `MONO_A1_REFERENCE_FREEZE_CHECKLIST.md` — W0 evidence checklist for `G-A1-C4-REF-FROZEN`; exact ΔA4 SHAs remain unassigned until Git readback
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
- `README.md`

## Established conventions

Research implementation under tooling/; DA01 protocol under da01/.

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
source revisions and resolves the A0/A0.1 versus A0.1/A1 transition conflict.
These contracts do not change DA01, B0, Method P, or PR #25 results.

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

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. The DEVELOPMENT validation workflow uses `make development-quality` with a **disposable** PostgreSQL database and excludes the two protected DA01 test modules from discovery. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
