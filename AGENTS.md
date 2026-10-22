# Agent instructions — EvoFitBench

This file governs automated contributors working in this repository. Read it before editing. The repository is a **research instrument**, not a production task-management product. Read [`docs/RESEARCH_CONTEXT.md`](docs/RESEARCH_CONTEXT.md) for the scientific purpose, model, manuscript-to-protocol RQ crosswalk, falsifiable hypotheses, validity threats, and implementation boundaries of the proposed method. Prefer verifiable, reproducible behavior to feature breadth.

## Read-first map

1. [Research rationale, model and scientific purpose](docs/RESEARCH_CONTEXT.md).
2. [Research and document index](docs/README.md).
3. [Two domains and terminology](docs/DOMAIN.md).
4. [Implemented architecture and boundaries](docs/ARCHITECTURE.md).
5. [Experiment, protocols, freeze and isolation](docs/EXPERIMENT.md).
6. [Actual technology stack and commands](docs/TECHNOLOGY.md).
7. [Verification and test traceability](docs/TESTING.md).

For manuscript scientific RQ1–RQ4 versus executable experiment RQ1–RQ4, start with the explicit crosswalk and open methodological discrepancies in [`docs/RESEARCH_CONTEXT.md`](docs/RESEARCH_CONTEXT.md). These are not equivalent numbering schemes; do not rename or resolve either one by editing frozen research artifacts.

For normative experimental details, prefer the **versioned source files** over narrative summaries: `experiments/design/ARCHITECTURE_EVOLUTION_SCENARIOS_V1.md`; `experiments/execution/da01/PROTOCOL.md`, `INPUT_ISOLATION.md`, `READINESS.md`, `SCORE_RULES.md`, `VALIDITY_RULES.md`; `fitness/catalog/architectural-obligations.yaml`; and the corresponding JSON Schemas. If narrative documents disagree, identify the discrepancy in the PR; do not silently reconcile or rewrite scientific rules.

## Hierarchical CONTEXT.md convention (mandatory for repository work)

The repository uses **local, descriptive** `CONTEXT.md` files in the root and every tracked directory outside `docs/`, **except the five subdirectories rooted at `experiments/execution/policy-pilot/v1/source/`**. This versioned policy-source tree has a strict, test-enforced file allowlist that must not be relaxed for documentation; its nearest safe parent `experiments/execution/policy-pilot/v1/CONTEXT.md` covers the excluded source tree. The approach is inspired by [GitHub Community Discussion #191257](https://github.com/orgs/community/discussions/191257); it is a project convention, **not automatic context loading by every AI tool**. Explicitly read these files. `docs/RESEARCH_CONTEXT.md` remains the canonical research-rationale document; `docs/` deliberately has no local `CONTEXT.md` files.

Before working on any path:
1. Read root `AGENTS.md`, root `CONTEXT.md` and `docs/RESEARCH_CONTEXT.md`.
2. Read the `CONTEXT.md` files for **all ancestors** of the target file, in order from root to leaf. For example, editing `app/modules/tasks/service.py` requires `app/CONTEXT.md`, `app/modules/CONTEXT.md`, `app/modules/tasks/CONTEXT.md`.
3. Read and follow the actual module code, tests, manifests and frozen research protocols. `CONTEXT.md` is descriptive context, **not permission** to override these sources.
4. When adding a tracked directory outside `docs/` and outside the strictly allowlisted policy source tree, create its `CONTEXT.md` in the same PR. Update existing local context **in the same PR** when boundaries, artifacts, APIs, commands or known limitations materially change.
5. Keep each local file focused: responsibility, meaningful file landmarks, architectural patterns, validation commands and concrete anti-patterns. Do not copy whole source files, embed secrets or oracle labels, fabricate experiment outcomes or treat local context as an approved policy.
6. Archived/scientific directories also contain navigation files solely to satisfy repository coverage; these additions **do not enter the curated evidence inventories, ground truth or method input allowlists**. Never alter existing frozen bytes or rebase a protocol on supplemental context.

CI tests `tests/unit/test_context_documents.py` check complete tracked-directory coverage (except `docs/` and the explicitly exempt policy-source tree). If such a test cannot inspect Git metadata, report a clear skip rather than pretending to have verified coverage.

## Current state (update only with evidence)

- The **A0_MONOLITH** starting point is a frozen research baseline. At the ΔA3 integration base (`b003144ae78238707af555aee68a16ffa14e800b`), the application already has the **A0_2_PUBLIC_MODULE_APIS** surfaces; ΔA3 adds the explicit **A0_3_GOVERNED_MODULE_GRAPH** state record and mandatory source-based acceptance. The application remains **one deployable process, one PostgreSQL database, synchronous calls and no broker**. See `ARCHITECTURE.md` and `architecture/states/`.
- SPEC 01 (versioned architecture-policy Snapshot v1.1, APA/FV validation, B1/P V2 candidate exports) and SPEC 02 (AR-DSL, evidence-aware `ACTIVE/INACTIVE/UNKNOWN` assessment, separately pinned V3 candidate policy source) are implemented as **development/synthetic** components.
- SPEC 03 DEVELOPMENT implementation exists for typed impact analysis, exact-pair semantic assessment, operation planning, candidate construction, governance, and synthetic tests. Measured Method P remains **NOT READY**: `experiments/execution/tooling/p_interface.py` reports `P_ALGORITHM_STATUS = NOT_READY`; G1 remains INCOMPLETE and G4 NOT AUTHORIZED.
- The next priority is implementation and experimental validation according to §5 of the monograph. EXP-01 is the A0.1 DEVELOPMENT evidence pipeline; its execution records do not establish `Coverage_P`, `Coverage_ref`, G1/G4, or measured DA01 results.
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

