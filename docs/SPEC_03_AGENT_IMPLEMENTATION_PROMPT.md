# Agent implementation prompt — SPEC 03 (copy into your coding agent)

You are the implementation agent for the EvoFitBench scientific research platform (https://github.com/Pan14ek/evofit-bench).

**Objective:** implement the DEVELOPMENT version of SPEC 03 — Architecture Change Impact Analysis & Governed Fitness Configuration Adaptation — as a technology-agnostic, generalizable method P for adapting the *configuration of architectural fitness functions* after an architecture change. You are **not** optimizing the software architecture or running an official scientific DA01 experiment.

**Required primary specification:** `docs/SPEC_03_IMPACT_ANALYSIS_AND_GOVERNED_ADAPTATION.md` (version EVOFITBENCH_SPEC_03_V1_DRAFT). If the documentation PR is not merged, read the exact version from branch `docs/spec03-governed-adaptation-v1-draft` and state that it is a reviewed/unreviewed DRAFT; do not silently treat it as a frozen G1 scientific algorithm. Start your implementation on a **new branch** from the latest user-approved `main` (or ask before basing it on an unmerged specification). Never push directly to main or merge without permission.

## Before coding

1. Read the current `AGENTS.md`, root + ancestor `CONTEXT.md`, `docs/RESEARCH_CONTEXT.md`, `docs/TESTING.md`, `docs/EXPERIMENT.md`, `docs/DOMAIN.md`, `docs/ARCHITECTURE.md`, SPEC 01/02 journals, DA01 `PROTOCOL.md`/`INPUT_ISOLATION.md`/`READINESS.md`/`VALIDITY_RULES.md` and existing method schemas/interfaces/tests.
2. Verify actual main HEAD, merge status, GitHub Actions and implementation baseline. Record SHA and applicable frozen artifacts without opening ground-truth/oracle/scorer content.
3. Produce a concise implementation plan and requirement-to-test matrix before implementing any algorithm. Distinguish confirmed existing behavior from SPEC 03 proposed decisions and OPEN-01…OPEN-10.
4. Do **not** read `experiments/scenarios/DA01/ground_truth.yaml` or use DA01-specific expected operations, the private scorer, sealed results, reference checker or other methods' outputs while developing P. Do not tailor code, tests, fixtures, rules, graph edges or evaluator templates to oracle answers.
5. Do not alter frozen A0/DA01 artifacts, V1 method inputs, prediction/candidate/scorer rules, fixed seed/workload or existing versioned V2/V3 contracts. Prefer additive versioned DEVELOPMENT interfaces.

## Required implementation

Build generic P modules for: strict SPEC 01/02 verified input bindings; typed architectural/policy/obligation diff; criterion-centric typed traceability and conservative Impact; semantic validity and evidence adequacy of exact (representation, obligation) pairs; missing mandatory coverage; deterministic, evidence-backed RETAIN/REPLACE/ADD/DEACTIVATE and explicitly authorized limited ADJUST; actual candidate materialization; validation of invariants/provenance/cost; ACCEPT/REJECT/HOLD; append-only versions and conditional rollback.

Preserve the distinctions among **applicability**, **compliance**, **representation coverage** and **governance**. UNKNOWN never means INACTIVE. A passing/vacuous evaluator or declared covers link never grants coverage. A candidate that cannot materialize a real verified evaluator returns HOLD/NEEDS_IMPLEMENTATION, not an invented checker. At baseline generic_candidate_templates is empty. OPEN/DRAFT policy pilot is not approved. No inferred hard thresholds or optimization of alpha/theta.

Reuse SPEC 02 `ApplicabilityAssessment` and its proof validation — no second hardcoded engine. P's self-evidence must not import the independent post-hoc oracle. Report missing real trust anchors, complete architecture facts, capability templates or policy closure as evidence limitations, not as silent defaults.

Define new **additive** strict JSON Schemas for impact, pair-validity, adaptation trace and governance decision. Keep legacy `prediction.schema.json` v1 and `candidate_configuration.schema.json` v1 unchanged; provide tested projections/adapters where safe, and distinguish INPUT_REJECTED from REJECT/HOLD/ACCEPT. Version all algorithm contracts and stable reason codes. Protect content hashing, source pins and input allowlists.

## Verification & Validation (mandatory)

Implement the entire Test Traceability Matrix in `SPEC_03_IMPACT_ANALYSIS_AND_GOVERNED_ADAPTATION.md`: SPEC 01/02 regression rows TT-C01/TT-C02/TT-A/TT-S01 plus SPEC 03 rows TT-P03-01…TT-P03-48. Maintain 25 requirement IDs and evidence of coverage, with **positive, negative, boundary, integration, adversarial and property-based/metamorphic** tests.

Every critical condition needs both success and failure tests. Test no-change and policy-only change; partial graph; multi-obligation shared representation; missing/forged/stale authority and evidence; semantic scope mismatch; vacuous evaluator; missing evaluator template; conflicting operations; candidate acceptance gates; rollback invalid in current state; publish race; deterministic canonical replay; and strict V1/V2/V3 compatibility. Tests must use generic independently created synthetic fixtures, never oracle-derived answers.

Run targeted suites, existing regression, `make test-unit`, `make lint`, `make typecheck`, `make security`, `make architecture-test`, `make migration-test`, `make quality` with disposable PostgreSQL, and Docker negative isolation probes when a digest-pinned image exists. Report PASS/FAIL/SKIP/BLOCKED exactly; unavailable Docker probe is SKIP/BLOCKED, not PASS.

## Research safeguards

Do not run measured DA01 B0/B1/P trials or simulate a human B1. G1 and G4 are not satisfied by implementation. Do not claim improvement in RQ1–RQ4, significance, research novelty or a validated scientific experiment from synthetic checks. Preserve the explicit manuscript-to-protocol RQ mismatch (manuscript RQ3 overhead/RQ4 formal-vs-heuristic versus executable RQ3 detection/RQ4 overhead). Do not silently change baselines, accepted scientific endpoints, cost model, stage requirements, or official scoring. Treat unapproved OPEN decisions conservatively (typically HOLD) and list them for independent review.

## Delivery

Make reviewable commits and open a **separate SPEC 03 implementation PR**, without merging. Update relevant local CONTEXT.md and docs, and provide: base/head SHAs, code/config diff, proposed contract versions, exact tests/TTM mapping and fixture independence, command outputs + CI links, PASS/FAIL/SKIP/BLOCKED, V1/V2/V3 byte/regression and method-input isolation evidence, whether any protected file changed (expected: none), unresolved proof/authority/OPEN decisions, and honest DEVELOPMENT vs G1/G4 readiness.

If a conflict requires changing frozen experimental procedure or accessing private ground truth, **do not do it**. Document the conflict and ask for methodological review. Continue independent synthetic engineering work that does not depend on that decision.
