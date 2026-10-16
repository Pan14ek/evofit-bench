# Agent instructions — EvoFitBench

This file governs automated contributors working in this repository. Read it before editing. The repository is a **research instrument**, not a production task-management product. Prefer verifiable, reproducible behavior to feature breadth.

## Read-first map

1. [Research and document index](docs/README.md).
2. [Two domains and terminology](docs/DOMAIN.md).
3. [Implemented architecture and boundaries](docs/ARCHITECTURE.md).
4. [Experiment, protocols, freeze and isolation](docs/EXPERIMENT.md).
5. [Actual technology stack and commands](docs/TECHNOLOGY.md).
6. [Verification and test traceability](docs/TESTING.md).

For normative experimental details, prefer the **versioned source files** over narrative summaries: `experiments/design/ARCHITECTURE_EVOLUTION_SCENARIOS_V1.md`; `experiments/execution/da01/PROTOCOL.md`, `INPUT_ISOLATION.md`, `READINESS.md`, `SCORE_RULES.md`, `VALIDITY_RULES.md`; `fitness/catalog/architectural-obligations.yaml`; and the corresponding JSON Schemas. If narrative documents disagree, identify the discrepancy in the PR; do not silently reconcile or rewrite scientific rules.

## Current state (update only with evidence)

- The **A0_MONOLITH** starting point is a frozen research baseline. The current `main` application code is the **A0_1_CAPABILITY_MODULES** capability-oriented monolith from DA01, still **one deployable application process, one PostgreSQL database, synchronous calls and no broker**. See `ARCHITECTURE.md` and the state manifest.
- SPEC 01 (versioned architecture-policy Snapshot v1.1, APA/FV validation, B1/P V2 candidate exports) and SPEC 02 (AR-DSL, evidence-aware `ACTIVE/INACTIVE/UNKNOWN` assessment, separately pinned V3 candidate policy source) are implemented as **development/synthetic** components.
- Full P impact analysis, operation selection, candidate generation and governed acceptance/rollback are **not implemented**. `experiments/execution/tooling/p_interface.py` reports `P_ALGORITHM_STATUS = NOT_READY`.
- The policy pilot under `experiments/execution/policy-pilot/v1/` contains **DRAFT** policies, **OPEN** registry, and no production trust anchors. It is not a sealed approved authority or independent oracle.
- No measured B0/B1/P DA01 comparison has been authorized or reported by the existing Phase A protocol.

## Change discipline

1. Create a dedicated branch and PR from the current `main`; record the base SHA. Do not push directly to `main` or perform a merge without an explicit request.
2. Read relevant code, tests, manifests and protocol **before** modifying a contract. State which scientific requirement the change satisfies. Keep technology choices experimental, not requirements of the mathematical method.
3. **Do not modify or regenerate** frozen A0 source tags/commits, DA01 scenario/ground truth, private oracle or scoring rules, sealed predictions, reference checkers, curated evidence, frozen A0 evaluator, fixed seed/workload contracts, or V1 method-input artifacts to make a new feature pass. Do not silently change V2/V3 candidate contracts; version breaking changes separately.
4. Never read `experiments/scenarios/DA01/ground_truth.yaml` or scenario-specific expected operations when authoring P rules, candidate logic, policy fixtures or B1 instructions. That data is oracle-side only. The repository may contain it for independent evaluation; **method input bundles must not**.
5. Keep method input allowlists strict. The P runtime must not access `.git`, private scorer, oracle, another method's outputs or network. Never bypass a missing digest-pinned Docker image with an unisolated local subprocess for an official method run.
6. Separate **applicability** (normative obligation is in force), **compliance** (architecture satisfies it), **representation coverage** (valid evidence supports the obligation) and **fitness/adaptation**. `UNKNOWN` is not `FALSE`; insufficient evidence is not approval; `DRAFT` is not `APPROVED`.
7. Code new P logic generically across all catalog obligations and states. Do not special-case `DA01`, an obligation ID, a known oracle target, expected operation or score in the implementation.
8. Preserve the original architectural invariants of DA01 unless a *separately authorized* evolution scenario explicitly changes them. Do not add services, brokers, database instances, event semantics, retry patterns or authentication just to match a desired future architecture.
9. Distinguish synthetic unit/integration checks and existing A0 runtime evidence from scientific measured experimental results. Never invent human B1 participation, policy approvals, review sign-off, statistics or runtime improvements. G1/G4 authorization is mandatory **for measured DA01**, not for ordinary implementation or synthetic tests.
10. An implementation PR must include code-level tests, adversarial/negative tests, regression/integration checks, stable failure semantics, new-contract schema tests and a requirement-to-test matrix (see `docs/TESTING.md`). Report actual commands and PASS/FAIL/SKIP, CI link, artifact SHAs and unresolved issues. Skipped tests are not passes.
11. Prefer concise changes and source links to copying large protocols. Update relevant `docs/` pages when changing source behavior; do not assert “implemented” until code/tests demonstrate it.

## Normal development commands

```bash
uv sync --frozen --extra dev
make test-unit
make lint
make typecheck
make security
make architecture-test
make migration-test
make quality
```

`make quality` requires a disposable PostgreSQL test database; follow `README.md` and `docs/TECHNOLOGY.md`. Its coverage gate is for `app/`, not a percentage claim about research tool coverage. The CI workflow is `.github/workflows/ci.yml`. Do not run destructive database resets against a non-disposable DB.

## Required PR report

Include: purpose/research requirement; base and head SHA; changed files; implementation status; added/modified tests and requirement IDs; exact verification commands with results; contract/backward-compatibility and input-isolation checks; whether any research artifact/gate was touched; unresolved proof/authority limitations; and the next SPEC boundary.

