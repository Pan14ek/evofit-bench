# PILOT-02 results — A0 to A0.1 architecture compliance

**Status:** the original HOLD run is preserved, and a prospective TEST_ONLY DEVELOPMENT continuation on the same transition completed. Method P materialized a candidate and proposed one ADD plus one REPLACE, while returning HOLD and failing candidate validation. These are bounded development observations, not approved or measured DA01 results.

## Purpose and claim boundary

PILOT-02 exercises the existing governed Method P V3 adaptation path on the A0 to A0.1 capability-module transition. Its focused development profile maps the two executable A0.1 architecture-compliance observations to exact representation–obligation pairs:

- AC_LAYERING
- AC_MODULE_STRUCTURE

The run establishes that digest-bound A0.1 evaluator observations can be translated into the pinned profile and passed through the existing pair-assessment path. It does not establish semantic adequacy, valid obligation coverage, adaptation effectiveness, or independent validation. The pair diagnostics were produced after adaptation and are explicitly marked as not supplied to P.

## Source revisions and input integrity

| Item | Value |
|---|---|
| A0 architecture source | b78b0967be937634b7762baccf5ac6892b279a73 |
| A0.1 source used for the run | 38242a7f920c8a7232d01826c3025788e09ac79c |
| A0.1 application tree SHA | cdff9a6c3cee870e1eca2a5f5f3eb3202b0b1f08 |
| Latest-main profile basis | 3fdd5c68f8f60fad5757eefa66cc2aa8b24d9306 |
| P harness source revision | 38242a7f920c8a7232d01826c3025788e09ac79c |
| EXP-02 bundle SHA-256 | 8a8cdff3640b4ab5edd4c9c1d958aaa70fba2017530f3f8837e8877a49f1b057 |
| EXP-02 representation evidence SHA-256 | a9103c40c188056da38433b02ed5bd2bcb6e19fde0ec611718f97f0202988f3f |
| P input bundle SHA-256 | b55383a8a50481eba5e0d383b18206bc3ba9771e618e1450885b4a08a3896573 |
| P input manifest SHA-256 | cbed17959566695cf7d6dcc605062b8c88fc84a234e9eaa7ee75c56a0ab0c53d |
| Policy bundle SHA-256 | 3fff9d4d0f2aeb584868c295f5da482b0d5541235e643c4c307a51856b4c68a8 |
| Profile definition SHA-256 | b9f9ceb7f5947b4de36544dcaccaafeafe5e0c22bf2742d96af3f56226858712 |
| Frozen B0 fitness configuration SHA-256 | 5ad60e373463ea459e192bf85d82704ca9aa1c217c4abf4d8caeb66924059ecb |
| B0 evaluator configuration SHA-256 | 88ff64a4792c6048a6ab0686ddf9326ebbee49f76996933845a6142cc1a2ba27 |

EXP-01 returned an incomplete bundle: both CI records were captured, deployment observation was skipped, and runtime evidence was unavailable. EXP-02 validated five representation rows, including the two architecture CI rows; three runtime rows remained unresolved. Its metadata reports Coverage_P as not assessed and Coverage_ref as not established. These outputs are DEVELOPMENT evidence only.

The policy source supplied to P is DRAFT and its registry closure is OPEN. The Method P algorithm remains NOT_READY. The experiment did not admit EXP-02 observations into P's calculations, did not supply an evidence sidecar to adaptation, and did not access private oracle/scorer data.

## Results

| Measure | B0 | Method P | Independent assessment |
|---|---|---|---|
| Applicability for the two target obligations | Not independently established | UNKNOWN under the open DRAFT policy registry | Pending |
| Representations | Pinned B0 configuration has 5 existing representations; architecture representation is REP_A0_ARCH_CI_LAYERING | Failed materialized candidate retained: REP_A0_ARCH_CI_LAYERING, REP_A0_PERF_RUNTIME_HTTP_DURATION, REP_A0_PERF_TEST_HTTP_P95, REP_A0_REL_RUNTIME_FAILURES, REP_A0_REL_TEST_INTEGRATION; no edits | Pending |
| Added/replaced representations | Not applicable | None | Pending |
| Valid obligation coverage | Not established | Not established; denominator approval is pending and target pair statuses are UNKNOWN | Pending |
| Controlled S1 violation | Frozen B0 evaluator is inconclusive | P candidate evaluation was not measured; separate A0.1 evaluator control found one notification-layering violation | Pending |
| Adaptation computation time | Not applicable | 174096417 ns (0.174096417 s) | Not applicable |
| Evaluator time | 124764583 ns (0.124764583 s), inconclusive | Not measured; candidate validation failed | Not applicable |
| Governance | Not applicable | HOLD | Pending |

### Exact pair diagnostics

Both records below are post-run diagnostics produced from the actual EXP-02 raw outputs by the existing exact-pair assessment routine. They are expressly not inputs to P adaptation. Execution success and a zero-valued metric do not establish semantic adequacy or coverage.

| Representation | Obligation | Lifecycle stage mapping | Observed result | Compliance / pair status | Pair reason |
|---|---|---|---|---|---|
| REP_A01_ARCH_INTERNAL_LAYERING_CI | AC_LAYERING | ci_test to ci | dependency_rule_violations = 0 contracts; evaluator exit 0 | COMPLIANT / UNKNOWN | EVALUATOR_INSPECTION_SCOPE_UNKNOWN, PAIR_SEMANTIC_PROOF_MISSING |
| REP_A01_ARCH_MODULE_STRUCTURE_CI | AC_MODULE_STRUCTURE | ci_test to ci | module_structure_test_failures = 0 tests; evaluator exit 0 | COMPLIANT / UNKNOWN | EVALUATOR_INSPECTION_SCOPE_UNKNOWN, PAIR_SEMANTIC_PROOF_MISSING |

Both assessments retain the reason codes EVALUATOR_INSPECTION_SCOPE_UNKNOWN and PAIR_SEMANTIC_PROOF_MISSING. Independent semantic adequacy remains pending.

## B0 evaluator and controlled S1 evidence

The unchanged B0 fitness configuration was evaluated against the A0.1 source using the pinned Import Linter 2.15 evaluator. It exited 1 with the message: Module app.repositories does not exist. The evaluator reports no broken-contract count, so this result is inconclusive, not evidence of a violation or pass. Elapsed evaluator time was 124764583 ns.

The separate pre-existing PILOT-01 S1 control was run on commit ccbfb002e1fc71d9dcaadf11635d449b8a881cac, whose parent is 5d285a04da00863088f8cd88a10afb3faaf02ddb. The A0.1 profile Import Linter reported 4 kept contracts and 1 broken Notifications module layering contract; the targeted notification layering test failed, while module structure passed. The frozen B0 evaluator remained inconclusive on S1 with the same missing-module message. This control validates evaluator behavior on a known synthetic source change. It is not a P candidate result and does not establish P effectiveness.

## Method P and governance outcome

Method P completed the existing development adaptation path in 174096417 ns. The operation plan was empty, with HOLD reasons: COST_MODEL_UNRESOLVED, MANDATORY_APPLICABILITY_UNKNOWN, UNKNOWN_MANDATORY_LINK_PREVENTS_TRANSITION. The materialized candidate has SHA-256 287a8aa33fb8f5ed98dda59ae16ba9dac881e558a21c3d9d62ad30cbe872e1cf, contains no configuration changes, and failed candidate validation with ACTIVE_EVALUATOR_ARTIFACT_UNAVAILABLE. Candidate evaluator time is therefore not measured.

Governance returned HOLD. Recorded reasons: APPLICABILITY_UNKNOWN, CANDIDATE_NOT_POSITIVELY_VALIDATED, COST_MODEL_UNRESOLVED, COST_VERDICT_UNRESOLVED, INPUT_AUTHORITY_OR_COMPLETENESS_UNRESOLVED, INVARIANT_VERDICTS_NOT_ALL_POSITIVE, MANDATORY_APPLICABILITY_UNKNOWN, MANDATORY_CLASSIFICATION_UNRESOLVED, UNKNOWN_MANDATORY_LINK_PREVENTS_TRANSITION, VERIFIED_GOVERNANCE_PIPELINE_PROOF_MISSING. No candidate was authorized or positively validated. These outcomes are preserved as HOLD; they are not recast as zero coverage, a rejected architecture, or successful adaptation.

## TEST_ONLY continuation on the same PILOT-02 transition

This is the author-authorized DEVELOPMENT continuation recorded prospectively in `PILOT_02_DEVELOPMENT_ADDENDUM_V1.md`; it does not restart PILOT-02 or replace the first HOLD run. Two harness preflights were rejected before `run_adaptation()` and are listed in the continuation archive. Only continuation-v3 is the reported Method P result.

| Binding | Value |
|---|---|
| Fetched `origin/main` base | `3fdd5c68f8f60fad5757eefa66cc2aa8b24d9306` |
| Clean experiment source commit | `a6b18480aa60eee2e0274a8da3f5a4f62e35193b` |
| A0.1 app tree | `cdff9a6c3cee870e1eca2a5f5f3eb3202b0b1f08` |
| EXP-01/02 run ID | `pilot02-a01-ci-20261019-continuation-v3` |
| EXP-02 bundle SHA-256 | `521a320a03c1aa4566156c474bcdcdb1f1a122b6c3dece73b0e1c3f2da58beec` |
| EXP-02 representation-evidence SHA-256 | `c112505bd7fc5d319366ae9efb38a45e90b1ad9e4beb570bad95ae1381846ca4` |
| P input bundle SHA-256 | `26c5fa7daedf955d486354557fce5e1bebec268e9fa7e38fe50f3934f001d76e` |
| TEST_ONLY assumptions SHA-256 | `5a652999080a2a31b519dc07cdf24ef1c1f04fbdc231e7d127a0d1bc0f7de6ae` |
| Candidate SHA-256 | `971c2074f00de4fb1fe290d6786e58217047dcabd1db70284669555d75707954` |
| P run manifest SHA-256 | `a311288a8e3c0135f15beeaf48299cc1fbefddc3b0f8d6adadf9538be307265a` |

EXP-01 ran the two in-scope CI evaluators on this clean revision: Import Linter passed with 0 broken contracts, and the module-structure test passed (1 test). Deployment was explicitly skipped and runtime evidence was missing. EXP-02 validated five representation records, with three unresolved mappings; the bundle is `incomplete`, `Coverage_P` is `not_assessed`, and `Coverage_ref` is `not_established`.

The continuation admitted the actual, digest-validated EXP-02 evaluator execution records under a local TEST_ONLY sidecar. The P input did not contain expected operations, oracle labels, or scorer data. The assumptions marked only `AC_LAYERING` and `AC_MODULE_STRUCTURE` as inactive before and active/mandatory after, specified `ci` as the required stage, and assigned a two-unit TEST_ONLY planning ceiling. These assumptions create a bounded engine exercise; they are not independent applicability, denominator, policy-authority, or semantic findings.

| Outcome | B0 unchanged | Existing Method P, TEST_ONLY continuation |
|---|---|---|
| Applicability for the two target obligations | Not independently established | Before `INACTIVE`, after `ACTIVE` under the declared TEST_ONLY assumptions only |
| Evaluator observation | Frozen Import Linter 2.15 exited 1; `app.repositories` was absent from A0.1; no broken-contract count was reported, so B0 is inconclusive | P's two materialized-profile evaluators both exited 0: 5 layering contracts kept, 0 broken; module-structure test 1 passed |
| Method P operations | Not applicable | `REPLACE REP_A0_ARCH_CI_LAYERING` and `ADD AC_MODULE_STRUCTURE`; each planned cost 1 TEST_ONLY unit |
| Materialized candidate | Not applicable | Yes; candidate SHA-256 above; includes both profile representations |
| Candidate validation | Not applicable | Failed with `ACTIVE_EVALUATOR_ARTIFACT_UNAVAILABLE`: four active inherited non-target A0 performance/reliability representations have no evaluator artifact |
| Exact target-pair validity | B0 layering pair classified TEST_ONLY `INVALID` only for evaluator-scope mismatch; this is not an architecture violation | Both candidate pairs are `UNKNOWN` with `EVALUATOR_INSPECTION_SCOPE_UNKNOWN` and `PAIR_SEMANTIC_PROOF_MISSING`; exit-0 execution is not a semantic proof |
| Coverage diagnostic | Not established | Candidate coverage `UNKNOWN`; no numeric P coverage or `Coverage_P` claim is made |
| Adaptation computation | Not applicable | `201084750` ns (`0.201084750` s), measured around `run_adaptation()` only |
| Evaluator execution time | `83797667` ns (`0.083797667` s), one frozen evaluator | `289808166` ns (`0.289808166` s) total for two profile evaluators; subprocess startup included |
| Governance | Not applicable | `HOLD`; includes `CANDIDATE_NOT_POSITIVELY_VALIDATED`, `IMPACTED_RETAIN_REASSESSMENT_MISSING`, `REQUIRED_STAGE_EVIDENCE_UNKNOWN`, and `VERIFIED_GOVERNANCE_PIPELINE_PROOF_MISSING` |

The B0 and P evaluator durations are reported separately because they use different configurations and run counts; their difference is not treated as a controlled speedup estimate. P's planned replacement is supported only by the TEST_ONLY scope-mismatch rule: the unchanged B0 configuration names `app.repositories`, the A0.1 source inventory lacks it, and the actual evaluator output reports that missing module. The candidate is a materialized development configuration, not a validated or accepted configuration. The four inherited non-target artifact gaps and the unresolved impact-retain check are retained rather than silently repaired.

The pre-existing PILOT-01 S1 observation remains secondary context only: its A0.1 evaluator reported one controlled Notifications layering violation. It was not rerun as part of this continuation and is not a new sample or a P candidate result.

Artifact-level integrity checks passed for all 130 files in the P run inventory, the run-manifest checksum, and the EXP-01/02 and EXP-02 validators. The separate continuation archive preserves the final raw bundle, P input and trace, candidate, raw evaluator outputs, assumptions, and both rejected harness preflights. The original `PILOT_02_RAW_EVIDENCE.zip` and its checksum are unchanged.

## Verification

### Initial PILOT-02 branch checks

- Focused pilot and exact-pair tests: 19 passed.
- EXP-03 bridge integration tests: 25 passed, 1 warning.
- Governed adaptation integration tests: 5 passed, 1 warning.
- make development-quality: passed using a fresh disposable PostgreSQL 16 database. Included lint (251 files formatted), mypy (106 source files), Bandit, architecture checks (6 passed), migration validation, the development regression suite (342 passed), EXP-01 unit tests (49 passed), and EXP-02 unit tests (30 passed). The Makefile's protected DA01 execution and research schema foundation tests were intentionally excluded.

### TEST_ONLY continuation verification

The following continuation checks apply to source commit `a6b18480aa60eee2e0274a8da3f5a4f62e35193b`. Commands ran from the repository worktree. Python commands used the bundled Python 3.12 runtime with repository site-packages; the shell variable below records the executable path.

```bash
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/Users/oleksii_makieiev/Documents/startups/evofit-bench/.venv/lib/python3.12/site-packages
PYTHON=/Users/oleksii_makieiev/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
"$PYTHON" -m scripts.exp01_evidence --architecture-state A0_1_CAPABILITY_MODULES --run-id pilot02-a01-ci-20261019-continuation-v3 --skip-deployment-observation
"$PYTHON" -m scripts.exp02_fitness_evidence --run-dir experiments/results/pilot02-a01-ci-20261019-continuation-v3
"$PYTHON" -m experiments.pilots.run_pilot02_method_p --exp02-run-dir experiments/results/pilot02-a01-ci-20261019-continuation-v3 --output-dir /private/tmp/pilot02-continuation-20261019-v3 --test-only-continuation
```

EXP-01 collected both target CI evaluators successfully; the bundle remained incomplete because deployment was skipped and runtime evidence was missing. EXP-02 returned `valid` for five representation rows, with three unresolved mappings. Method P completed under `TEST_ONLY`, emitted one ADD and one REPLACE, materialized a candidate, and returned HOLD.

```bash
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/Users/oleksii_makieiev/Documents/startups/evofit-bench/.venv/lib/python3.12/site-packages
PYTHON=/Users/oleksii_makieiev/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
"$PYTHON" -m pytest -q -p no:cacheprovider tests/unit/test_pilot02_testonly_execution.py tests/unit/test_pilot02_method_input_profile.py tests/unit/test_context_documents.py
"$PYTHON" -m pytest -q -p no:cacheprovider tests/unit/test_p_adaptation_evidence_v1.py
"$PYTHON" -m pytest -q -p no:cacheprovider tests/integration/test_exp03_method_bridge.py
ruff check --no-cache experiments/pilots/run_pilot02_method_p.py experiments/pilots/pilot02_testonly_execution.py tests/unit/test_pilot02_testonly_execution.py
ruff format --check experiments/pilots/run_pilot02_method_p.py experiments/pilots/pilot02_testonly_execution.py tests/unit/test_pilot02_testonly_execution.py
mypy --no-incremental --explicit-package-bases --follow-imports=silent --ignore-missing-imports experiments/pilots/run_pilot02_method_p.py
mypy --no-incremental --explicit-package-bases --follow-imports=silent --ignore-missing-imports --module experiments.pilots.pilot02_testonly_execution
```

Results: the focused PILOT-02/context suite passed (6); the adaptation-evidence suite passed (6); the EXP-03 bridge integration passed (25, 1 Starlette/httpx deprecation warning); Ruff checks passed and all three files were formatted; both targeted mypy commands reported no issues. The P run manifest checksum and all 130 inventoried artifact hashes matched. The continuation ZIP passed `unzip -t` and all 223 internal SHA-256 entries verified. The original archive checksum remained `07d678b6f67018c9f59b4b9f27406dceebdf8d38ecd975b3b64cd40342f3b917`.

Repository-wide `make development-quality` was not rerun for this continuation patch; the earlier development-quality result above belongs to the initial branch verification. Hosted CI for the new commits remains separate from these local checks.

## Hosted CI

Two GitHub Actions development-quality runs passed for code revision 8bda339894c1adddce9c77e011e3b00c33e9b360: [run 39316552803](https://github.com/Pan14ek/evofit-bench/actions/runs/39316552803) and [run 39316624260](https://github.com/Pan14ek/evofit-bench/actions/runs/39316624260). This follow-up records the results; it changes report text only.

## Research gates and limits

G1 remains INCOMPLETE; G4 remains NOT AUTHORIZED. The independent assessment is pending. The source policy registry is OPEN and DRAFT; the profile denominator and semantic adequacy are not independently approved. No measured B0/B1/P DA01 comparison, Coverage_P, Coverage_ref, or general effectiveness claim is established. No frozen research artifact or gate was changed by this pilot.

Further DEVELOPMENT runs can proceed under separately predeclared assumptions and must keep their evidence and limits explicit. External review can follow completion of the research, as directed. Any measured DA01 study remains subject to its existing authorization restrictions; this continuation does not change them. Do not infer DA01 readiness from this development run.

## Requirement-to-evidence map

| Requirement | Evidence |
|---|---|
| Pin architecture source and evaluator/configuration inputs | Profile JSON, EXP-02 bundle, P input manifest, and run manifest in the raw archive |
| Exercise the existing P V3 path | method-p/final/method_p_trace.json and candidate configuration |
| Exercise operations with actual evaluator runs under TEST_ONLY scope | continuation-v3 trace, operation plan, candidate evaluators, assumptions file, and separate continuation archive |
| Preserve exact two-obligation mappings and stages | pilot02_profile_pair_assessments in the trace and the exact-pair table above |
| Compare B0 evaluator behavior and S1 control | B0 raw output plus controlled-s1/control_manifest.json and digest-bound raw files |
| Preserve uncertainty and governance hold | Candidate validation, governance result, applicability, and pair reason codes in the trace |
| Preserve reproducible raw evidence | PILOT_02_RAW_EVIDENCE.zip; SHA-256 07d678b6f67018c9f59b4b9f27406dceebdf8d38ecd975b3b64cd40342f3b917 in the companion sidecar |
