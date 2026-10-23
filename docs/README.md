# EvoFitBench — research and engineering documentation

These are **maintained navigation documents**, not replacements for the versioned scientific protocol, schemas, source manifests or actual code. Read [`../AGENTS.md`](../AGENTS.md) first when using an automated coding agent.

| Document | What it answers |
| --- | --- |
| [RESEARCH_CONTEXT.md](RESEARCH_CONTEXT.md) | **Why** the dissertation study exists; mathematical model, scientific hypotheses, method P, manuscript–protocol RQ crosswalk, validity threats, contribution limits and open decisions. |
| [DOMAIN.md](DOMAIN.md) | What are the application's business domain and the separate research domain? |
| [ARCHITECTURE.md](ARCHITECTURE.md) | What architecture is actually implemented, and what is still only planned? |
| [EXPERIMENT.md](EXPERIMENT.md) | What is being compared, how are observations and oracle isolated, and which approval gates apply? |
| [TECHNOLOGY.md](TECHNOLOGY.md) | Which tools are *actually used*, how is the environment run, and which tools are merely future options? |
| [TESTING.md](TESTING.md) | What test categories, requirement-to-test traceability and pre-merge checks are expected? |
| [SPEC_03_IMPACT_ANALYSIS_AND_GOVERNED_ADAPTATION.md](SPEC_03_IMPACT_ANALYSIS_AND_GOVERNED_ADAPTATION.md) | **DRAFT** scientific/engineering SPEC 03: Impact, semantic validity, governed operations, rollback and complete SPEC 01–03 test traceability. Not frozen G1. |
| [EXP-04 verified evaluator evidence admission](../experiments/execution/EXP04_EVIDENCE_ADMISSION.md) | Development-only contract, invocation, readback, and limitations for verified EXP-02 evidence at the existing Method P boundary. |
| [MONO-E1/E2 experimental preparation](../experiments/execution/MONO_A1_PROTOCOL_V1.md) and [W0 reference-freeze checklist](../experiments/execution/MONO_A1_REFERENCE_FREEZE_CHECKLIST.md) | Approved A0→A1 MONO-E2 source binding, E1 `G-A1-C4-REF-FROZEN` procedure, reference custody, RQ crosswalk, and current blockers; no actual MONO runs are reported. |
| [MONO-E1 policy approval preparation](MONO_E1_POLICY_APPROVAL_PREPARATION_V1.md) | Non-authoritative, catalog-complete proposal inventory and OPEN-03/OPEN-04 review form; does not establish policy authority or an approved denominator. |
| [MONO-E1 CI fitness experimental profile](MONO_E1_CI_FITNESS_EXPERIMENT_PROFILE_V1.md) | Draft CI-only negative-control methodology and 18-obligation unresolved inventory; not authorized, not a replacement for MONO v1 / DA01. |
| [MONO-E1 A0.3 fitness configuration candidate](mono_e1_a03_fitness_configuration_candidate_v1.json) | Development-only lineage record for the missing A0.3 parent configuration; separates frozen A0 B0 from later engineering CI checks. |
| [MONO-E1 Method P decision package](MONO_E1_G1_METHOD_DECISION_REVIEW_V1.md) | Decision-ready OPEN-06…09 proposals, executable traceability, independent-review criteria, and MONO-E1 dependencies; not an approval or run authorization. |
| [SPEC_03_AGENT_IMPLEMENTATION_PROMPT.md](SPEC_03_AGENT_IMPLEMENTATION_PROMPT.md) | Implementation-agent prompt for a **separate** DEVELOPMENT PR, without measured DA01 or oracle access. |
| [G1_METHOD_SPECIFICATION.md](G1_METHOD_SPECIFICATION.md) | Review draft for the current SPEC 03 DEVELOPMENT method; not an independent freeze or measured-method approval. |
| [DA01_PREREGISTRATION_DRAFT.md](DA01_PREREGISTRATION_DRAFT.md) | Proposed DA01 RQ1/RQ2 preregistration; does not amend the frozen protocol or authorize a run. |
| [B1_P_COMPARABILITY_PLAN.md](B1_P_COMPARABILITY_PLAN.md) | B0/B1/P fairness plan with the B1 cadence decision left open. |
| [G1 integration decision matrix](g1/G1_INTEGRATION_DECISION_MATRIX.md) | Consolidated OPEN-01…OPEN-09 analysis, formal model, DA01 compatibility findings, dependencies and readiness limits; proposal only. |
| [G1 Workstream 01 brief](g1/workstreams/01_RESEARCH_DESIGN_BRIEF.md) | Research design, RQ/endpoints and B1 cadence analysis for OPEN-01/02. |
| [G1 Workstream 02 brief](g1/workstreams/02_METHOD_COMPATIBILITY_BRIEF.md) | Formal method and frozen-scoring compatibility analysis for OPEN-03/07/08. |
| [G1 Workstream 03 brief](g1/workstreams/03_AUTHORITY_CAPABILITY_COST_BRIEF.md) | Proposed policy-authority, evaluator-capability/parity, and adaptation-cost analysis for OPEN-04/05/06. |
| [G1 Workstream 04 brief](g1/workstreams/04_HOLDOUT_ISOLATION_REVIEW_BRIEF.md) | Research independence, custody, G2, and TT-P03-43 evidence boundaries for OPEN-09. |
| [G1_REVIEW_CHECKLIST.md](G1_REVIEW_CHECKLIST.md) | Independent G1 review evidence index and separate G4 authorization checklist. |
| [G1_METHOD_DECISION_REGISTER.md](G1_METHOD_DECISION_REGISTER.md) | OPEN-01…OPEN-10 and M-01…M-06 decision docket and current gate status. |

**Research reading order for AI agents:** read [`RESEARCH_CONTEXT.md`](RESEARCH_CONTEXT.md) before making scientific claims or beginning SPEC 03, then consult [`EXPERIMENT.md`](EXPERIMENT.md) and the exact DA01 protocol for operational definitions. The manuscript's RQ3/RQ4 and the executable protocol's RQ3/RQ4 are **not interchangeable**; the discrepancy is documented, not resolved by this documentation change.

## Local context guide

The root [`../CONTEXT.md`](../CONTEXT.md) and each eligible tracked subdirectory's `CONTEXT.md` describe local responsibilities, conventions and constraints. See [`../AGENTS.md`](../AGENTS.md) for the **explicit root-to-leaf reading order**; these files are not automatically loaded by every AI agent. The `docs/` directory is intentionally exempt because its documents provide the centralized research and engineering narrative. The strict V3 policy source `experiments/execution/policy-pilot/v1/source/` and its descendants are also exempt: their file allowlist rejects any unexpected `CONTEXT.md`. The parent `experiments/execution/policy-pilot/v1/CONTEXT.md` supplies local context without weakening input integrity. See also [GitHub's community discussion of this pattern](https://github.com/orgs/community/discussions/191257).

## State at documentation baseline

Prepared against `main` at `ca8d9781401f74297d7d47f68aa978557ca58e98` (18 Oct 2026), containing merged G1 workstreams PR #12–#15. This is a documentation snapshot, **not** a frozen scientific protocol or claim that future HEAD will be unchanged.

- Frozen original architecture: `A0_MONOLITH`.
- Current code organization after DA01: `A0_1_CAPABILITY_MODULES`, still one FastAPI/Uvicorn process and one PostgreSQL database.
- Implemented research infrastructure: Phase A preparation and SPEC 01/02/03 DEVELOPMENT pipelines, including typed impact, exact-pair assessment, operation planning, candidate validation, synthetic TEST_ONLY governance flows, and the separate EXP-01 A0.1 execution-evidence collector.
- No production policy or evaluator authority is available; measured B0/B1/P comparisons are neither authorized nor reported. The measured P interface remains `P_ALGORITHM_STATUS = NOT_READY`; G1 remains INCOMPLETE and G4 NOT AUTHORIZED.
- Experimental Authority Charter/Registry under `policy-pilot/v1`: design-stage, DRAFT/OPEN; production authority and completeness verification remain missing.

### Next research priority

The established monograph is EvoFitBench's scientific basis; its model, method, objectives, and B0/B1/P direction are already defined. EXP-01 provides the first A0.1 DEVELOPMENT evidence collector. The next primary objective remains implementation and experimental evaluation according to §5: reuse [`ARCHITECTURE_EVOLUTION_SCENARIOS_V1.md`](../experiments/design/ARCHITECTURE_EVOLUTION_SCENARIOS_V1.md), extend executable fitness evidence across controlled evolution scenarios, add controlled degradations and reproducible evidence, and complete P with real evaluator artifacts. Conduct independent B0/B1/P comparisons and analyze detection quality, mandatory coverage, semantic consistency, and operational overhead only under the applicable authorization. DA01 remains a frozen case within the dissertation's wider scope; further theory clarification should follow concrete implementation or experimental blockers. See the [prioritized next actions](g1/G1_INTEGRATION_DECISION_MATRIX.md#11-prioritized-next-actions).

Root [AGENTS.md](../AGENTS.md) now records the existing SPEC 03 DEVELOPMENT implementation and keeps measured P, G1, and G4 readiness separate. EXP-01 evidence is also labeled as engineering execution evidence, not positive fitness coverage or a measured DA01 result.

Research rationale comes from the author's working monograph, summarized in [RESEARCH_CONTEXT.md](RESEARCH_CONTEXT.md). It is **proposed science**, not the source of authority for frozen protocol details or verified results.

## Sources of truth and precedence

For behavior, use code and tests. For allowed architecture state, see [`../architecture/states/A0_1_CAPABILITY_MODULES.yaml`](../architecture/states/A0_1_CAPABILITY_MODULES.yaml) and [`../ARCHITECTURE.md`](../ARCHITECTURE.md). For obligation IDs, use [`../fitness/catalog/architectural-obligations.yaml`](../fitness/catalog/architectural-obligations.yaml), not copied tables in this handbook.

For scientific procedure, use [`../experiments/design/ARCHITECTURE_EVOLUTION_SCENARIOS_V1.md`](../experiments/design/ARCHITECTURE_EVOLUTION_SCENARIOS_V1.md), [`../experiments/execution/da01/PROTOCOL.md`](../experiments/execution/da01/PROTOCOL.md), [`../experiments/execution/da01/INPUT_ISOLATION.md`](../experiments/execution/da01/INPUT_ISOLATION.md) and [`../experiments/execution/da01/READINESS.md`](../experiments/execution/da01/READINESS.md). For implemented candidate APIs see [`../experiments/execution/P_INPUT_V11.md`](../experiments/execution/P_INPUT_V11.md) and [`../experiments/execution/P_APPLICABILITY_V1.md`](../experiments/execution/P_APPLICABILITY_V1.md).

If a summary conflicts with a source, report the conflict rather than silently choosing whichever makes a test pass. The original root `README.md` was written around A0; follow the architecture state manifest for current package organization.

## Updating documentation

When changing a feature/contract, update only the affected document and the requirement-to-test mapping. Distinguish **implemented**, **synthetic only**, **planned**, **blocked** and **measured/authorized**. Link exact code paths; avoid duplicating private scenario answers or mutable test counts.

