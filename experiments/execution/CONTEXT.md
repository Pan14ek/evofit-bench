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
- `schemas/exp03_method_integration_v1.schema.json`
- `schemas/exp03_method_p_execution_trace_v1.schema.json`
- `schemas/exp04_evidence_admission_v1.schema.json`
- `schemas/exp04_method_p_execution_trace_v1.schema.json`
- `schemas/exp04_evidence_verifier_config_v1.schema.json`
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
