# Context — `experiments/execution`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `experiments/CONTEXT.md` before this file.

## Responsibility

Phase A input isolation, contracts, preparation, SPEC01 validation, SPEC02 applicability, and the generic SPEC03 governed-adaptation development pipeline.

## Local landmarks

- `P_APPLICABILITY_V1.md`
- `P_INPUT_V11.md`
- `P_INPUT_V11_SENSITIVE_SHA256.txt`
- `da01/P_ALGORITHM_STATUS.md`
- `tooling/p_adaptation.py`
- `tooling/p_impact.py`
- `P_GOVERNED_ADAPTATION_V1.md`
- `README.md`

## Established conventions

Research implementation under tooling/; DA01 protocol under da01/.

## Constraints and known gaps

SPEC03 pipeline code and additive DEVELOPMENT schemas are implemented and synthetically tested. This does not make P ready for measured trials: current inputs do not provide complete mandatory classifications, approved generic evaluator templates, or an authorized cost model, and G1/G4 remain separate. Keep `p_interface.py` readiness blocked until the documented gates are met.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
