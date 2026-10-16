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
| [SPEC_03_AGENT_IMPLEMENTATION_PROMPT.md](SPEC_03_AGENT_IMPLEMENTATION_PROMPT.md) | Implementation-agent prompt for a **separate** DEVELOPMENT PR, without measured DA01 or oracle access. |

**Research reading order for AI agents:** read [`RESEARCH_CONTEXT.md`](RESEARCH_CONTEXT.md) before making scientific claims or beginning SPEC 03, then consult [`EXPERIMENT.md`](EXPERIMENT.md) and the exact DA01 protocol for operational definitions. The manuscript's RQ3/RQ4 and the executable protocol's RQ3/RQ4 are **not interchangeable**; the discrepancy is documented, not resolved by this documentation change.

## Local context guide

The root [`../CONTEXT.md`](../CONTEXT.md) and each eligible tracked subdirectory's `CONTEXT.md` describe local responsibilities, conventions and constraints. See [`../AGENTS.md`](../AGENTS.md) for the **explicit root-to-leaf reading order**; these files are not automatically loaded by every AI agent. The `docs/` directory is intentionally exempt because its documents provide the centralized research and engineering narrative. The strict V3 policy source `experiments/execution/policy-pilot/v1/source/` and its descendants are also exempt: their file allowlist rejects any unexpected `CONTEXT.md`. The parent `experiments/execution/policy-pilot/v1/CONTEXT.md` supplies local context without weakening input integrity. See also [GitHub's community discussion of this pattern](https://github.com/orgs/community/discussions/191257).

## State at documentation baseline

Prepared against `main` after merged PR #5, commit `32172d7acd31a7a0210bdb64f8472d722a702d29` (16 Oct 2026). This is a snapshot of documentation review, **not** a frozen scientific protocol or claim that future HEAD will be unchanged.

- Frozen original architecture: `A0_MONOLITH`.
- Current code organization after DA01: `A0_1_CAPABILITY_MODULES`, still one FastAPI/Uvicorn process and one PostgreSQL database.
- Implemented research infrastructure: Phase A preparation, SPEC 01 and SPEC 02 development candidates.
- Not implemented: full P Impact Analysis, governed adaptation and measured B0/B1/P comparisons.
- Experimental Authority Charter/Registry under `policy-pilot/v1`: design-stage, DRAFT/OPEN; production authority and completeness verification remain missing.

Research rationale comes from the author's working monograph, summarized in [RESEARCH_CONTEXT.md](RESEARCH_CONTEXT.md). It is **proposed science**, not the source of authority for frozen protocol details or verified results.

## Sources of truth and precedence

For behavior, use code and tests. For allowed architecture state, see [`../architecture/states/A0_1_CAPABILITY_MODULES.yaml`](../architecture/states/A0_1_CAPABILITY_MODULES.yaml) and [`../ARCHITECTURE.md`](../ARCHITECTURE.md). For obligation IDs, use [`../fitness/catalog/architectural-obligations.yaml`](../fitness/catalog/architectural-obligations.yaml), not copied tables in this handbook.

For scientific procedure, use [`../experiments/design/ARCHITECTURE_EVOLUTION_SCENARIOS_V1.md`](../experiments/design/ARCHITECTURE_EVOLUTION_SCENARIOS_V1.md), [`../experiments/execution/da01/PROTOCOL.md`](../experiments/execution/da01/PROTOCOL.md), [`../experiments/execution/da01/INPUT_ISOLATION.md`](../experiments/execution/da01/INPUT_ISOLATION.md) and [`../experiments/execution/da01/READINESS.md`](../experiments/execution/da01/READINESS.md). For implemented candidate APIs see [`../experiments/execution/P_INPUT_V11.md`](../experiments/execution/P_INPUT_V11.md) and [`../experiments/execution/P_APPLICABILITY_V1.md`](../experiments/execution/P_APPLICABILITY_V1.md).

If a summary conflicts with a source, report the conflict rather than silently choosing whichever makes a test pass. The original root `README.md` was written around A0; follow the architecture state manifest for current package organization.

## Updating documentation

When changing a feature/contract, update only the affected document and the requirement-to-test mapping. Distinguish **implemented**, **synthetic only**, **planned**, **blocked** and **measured/authorized**. Link exact code paths; avoid duplicating private scenario answers or mutable test counts.

