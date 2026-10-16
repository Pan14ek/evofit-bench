# EvoFitBench — research and engineering documentation

These are **maintained navigation documents**, not replacements for the versioned scientific protocol, schemas, source manifests or actual code. Read [`../AGENTS.md`](../AGENTS.md) first when using an automated coding agent.

| Document | What it answers |
| --- | --- |
| [DOMAIN.md](DOMAIN.md) | What are the application's business domain and the separate research domain? |
| [ARCHITECTURE.md](ARCHITECTURE.md) | What architecture is actually implemented, and what is still only planned? |
| [EXPERIMENT.md](EXPERIMENT.md) | What is being compared, how are observations and oracle isolated, and which approval gates apply? |
| [TECHNOLOGY.md](TECHNOLOGY.md) | Which tools are *actually used*, how is the environment run, and which tools are merely future options? |
| [TESTING.md](TESTING.md) | What test categories, requirement-to-test traceability and pre-merge checks are expected? |

## State at documentation baseline

Prepared against `main` after merged PR #5, commit `32172d7acd31a7a0210bdb64f8472d722a702d29` (16 Oct 2026). This is a snapshot of documentation review, **not** a frozen scientific protocol or claim that future HEAD will be unchanged.

- Frozen original architecture: `A0_MONOLITH`.
- Current code organization after DA01: `A0_1_CAPABILITY_MODULES`, still one FastAPI/Uvicorn process and one PostgreSQL database.
- Implemented research infrastructure: Phase A preparation, SPEC 01 and SPEC 02 development candidates.
- Not implemented: full P Impact Analysis, governed adaptation and measured B0/B1/P comparisons.
- Experimental Authority Charter/Registry under `policy-pilot/v1`: design-stage, DRAFT/OPEN; production authority and completeness verification remain missing.

## Sources of truth and precedence

For behavior, use code and tests. For allowed architecture state, see [`../architecture/states/A0_1_CAPABILITY_MODULES.yaml`](../architecture/states/A0_1_CAPABILITY_MODULES.yaml) and [`../ARCHITECTURE.md`](../ARCHITECTURE.md). For obligation IDs, use [`../fitness/catalog/architectural-obligations.yaml`](../fitness/catalog/architectural-obligations.yaml), not copied tables in this handbook.

For scientific procedure, use [`../experiments/design/ARCHITECTURE_EVOLUTION_SCENARIOS_V1.md`](../experiments/design/ARCHITECTURE_EVOLUTION_SCENARIOS_V1.md), [`../experiments/execution/da01/PROTOCOL.md`](../experiments/execution/da01/PROTOCOL.md), [`../experiments/execution/da01/INPUT_ISOLATION.md`](../experiments/execution/da01/INPUT_ISOLATION.md) and [`../experiments/execution/da01/READINESS.md`](../experiments/execution/da01/READINESS.md). For implemented candidate APIs see [`../experiments/execution/P_INPUT_V11.md`](../experiments/execution/P_INPUT_V11.md) and [`../experiments/execution/P_APPLICABILITY_V1.md`](../experiments/execution/P_APPLICABILITY_V1.md).

If a summary conflicts with a source, report the conflict rather than silently choosing whichever makes a test pass. The original root `README.md` was written around A0; follow the architecture state manifest for current package organization.

## Updating documentation

When changing a feature/contract, update only the affected document and the requirement-to-test mapping. Distinguish **implemented**, **synthetic only**, **planned**, **blocked** and **measured/authorized**. Link exact code paths; avoid duplicating private scenario answers or mutable test counts.

