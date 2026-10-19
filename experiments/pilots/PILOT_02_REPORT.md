# PILOT-02 — A0 to A0.1 Method P DEVELOPMENT results

**Latest corrected execution:** V4, `pilot02-a01-ci-20261020-v4`.
**Result class:** materialized but not fully validated; governance `HOLD`.
**Scope:** TEST_ONLY DEVELOPMENT for the single transition `A0_MONOLITH → A0_1_CAPABILITY_MODULES`; this is not a measured DA01 result.

## Objective and protocol boundary

PILOT-02 compares the unchanged frozen B0 fitness configuration with the existing Method P adaptation path for the architecture-compliance obligations `AC_LAYERING` and `AC_MODULE_STRUCTURE`. B0 and P used the same clean A0.1 application tree and source revision. The baseline configuration and its evaluator were not changed.

The V2 assumption file, pinned before V2 and reused unchanged in V3/V4, classifies `AC_LAYERING` as active in A0 and A0.1, and `AC_MODULE_STRUCTURE` as inactive in A0 and active in A0.1. These are researcher-declared TEST_ONLY states informed by the checked-in A0 traceability, frozen A0 configuration/evaluator, and A0.1 state manifest. They are not independent policy authority or an approved coverage denominator. The target stage is `ci`.

The assumption file explicitly records `expected_operations_in_method_input=false`. The method inputs contain the declared applicability and candidate-template bindings; they do not contain expected output operations or oracle/scorer labels.

The A0.1 candidate templates came from the manually established DEVELOPMENT profile. Method P selected operations over those known templates; this run does not demonstrate automatic discovery of new evaluator representations.

## V4 source and evidence bindings

| Item | Value |
|---|---|
| Fetched `origin/main` basis | `3fdd5c68f8f60fad5757eefa66cc2aa8b24d9306` |
| Frozen A0 source | `b78b0967be937634b7762baccf5ac6892b279a73` |
| Clean V4 experiment source revision | `d793c92b881f0b69321188f888fa7346c468fc3c` |
| A0.1 application-tree SHA-1 | `cdff9a6c3cee870e1eca2a5f5f3eb3202b0b1f08` |
| B0 fitness configuration SHA-256 | `5ad60e373463ea459e192bf85d82704ca9aa1c217c4abf4d8caeb66924059ecb` |
| B0 Import Linter configuration SHA-256 | `88ff64a4792c6048a6ab0686ddf9326ebbee49f76996933845a6142cc1a2ba27` |
| EXP-01 bundle SHA-256 | `f1258256840c2ce1b6345b24e97c9aa8598726101768cd199aa4485c35ae7b36` |
| EXP-02 representation evidence SHA-256 | `f0596adeb83bacbfa93ee8aa680687dbd05da630ddfe2d0fbf9d152b171dac06` |
| V2 TEST_ONLY assumptions SHA-256 | `900129e68cd0571771cbea1f2b70fc11723a1bf7a64fcc9ecc605c0bcc5ff1a2` |
| P input bundle SHA-256 | `8886a7b61d395f4e12a9330ccab44ba4a3c79cc1532768a6e33ca21b835011ac` |
| Policy bundle SHA-256 | `62ec546ef488895ae40ae30b11de4caadb1425a463116d54d3cc9b26175dc1a1` |
| TEST_ONLY evidence-sidecar SHA-256 | `60526e9ded1860577c6135016d6490e4cb67ee86e71bdccebaba4d096cfa948a` |
| Candidate configuration SHA-256 | `9f319ad6795f69321bd9e06d88c0aac2efabde90508cfd1678a39f5df6c2fc2d` |
| Method P trace SHA-256 | `c855bb532c8e1d749d87688d74f2958908af62f92ed72122a7fc5e3814709b3a` |
| Run-manifest SHA-256 | `095d7e22feed5557f6f5c09427d6221f55bdbf746ef7bc4326b41311597761a3` |
| Raw V4 archive SHA-256 | `4ff90f865ad48dae7e89e18f43b281467f35858fe92970858b2375342016b1a0` |

The run manifest records `git_dirty=false`; B0 and candidate evaluators ran against the same application-tree SHA above. The raw archive contains the EXP-01/02 run, the 130 inventoried Method P artifacts, source-bound inputs, candidate, trace, evaluator stdout/stderr, and checksums.

## Experimental results

| Measure | Unchanged B0 | Method P candidate / bounded profile | Evidence limit |
|---|---|---|---|
| `AC_LAYERING` | Frozen evaluator ran; its configured `app.repositories` target is absent from A0.1. Exit 1; broken-contract count not reported. | Import Linter 2.15 exited 0: 5 contracts kept, 0 broken. Candidate profile binding matched. | B0 is inconclusive because its target scope does not resolve. The P execution is not an exact-pair semantic proof. |
| `AC_MODULE_STRUCTURE` | No representation in the unchanged B0 architecture-compliance configuration. | Pytest 8.4.2 exited 0; 1 module-structure test passed. Candidate profile binding matched. | A successful test does not independently establish obligation adequacy. |
| TEST_ONLY applicability | Not independently established. | `AC_LAYERING`: active before and after. `AC_MODULE_STRUCTURE`: inactive before, active after. | States are explicit assumptions, not policy authority. |
| Adaptation operations | Not applicable. | `REPLACE REP_A0_ARCH_CI_LAYERING`; `ADD AC_MODULE_STRUCTURE`. Each has a TEST_ONLY planning cost of 1.0 unit. | The cost units are not elapsed time or measured human effort. |
| Candidate | Not applicable. | Materialized; SHA-256 above. | Full validation failed; candidate is not accepted. |
| Exact target-pair status | `AC_LAYERING`: `INVALID` pair due unresolved/mismatched evaluator scope; compliance `UNKNOWN`. B0 has no `AC_MODULE_STRUCTURE` pair. | Both pairs `UNKNOWN`; compliance `UNKNOWN`. | Candidate reasons include `EVALUATOR_INSPECTION_SCOPE_UNKNOWN` and `PAIR_SEMANTIC_PROOF_MISSING`. |
| Internal coverage diagnostic | Parent configuration: `INCOMPLETE`, 0/2 in this TEST_ONLY diagnostic. | Candidate: `UNKNOWN`, 0/2 in this TEST_ONLY diagnostic. | These are internal diagnostics only. No numeric `Coverage_P` or independent coverage is claimed. |
| Full candidate validation | Not applicable. | `failed`: `ACTIVE_EVALUATOR_ARTIFACT_UNAVAILABLE`. | Four active inherited non-target A0 representations lack exact pinned evaluator artifacts. |
| Governance | Not applicable. | `HOLD`. | Reasons are listed below. |

EXP-01 captured both CI evaluator records with exit status 0. Deployment observation was deliberately skipped, and runtime evidence is missing; the EXP-01 bundle is therefore `incomplete` (command exit 2). EXP-02 validated five representation rows and recorded three unresolved mappings. Its claims remain `Coverage_P=not_assessed` and `Coverage_ref=not_established`.

The unchanged B0 run used Import Linter 2.15 and took `85,392,875 ns`. It resolved 3 of 4 configured targets and reported `app.repositories` missing, exiting 1 without a broken-contract count. The B0 exact pair is `INVALID` because the evaluator artifact and target scope do not establish the exact pair; its compliance status is `UNKNOWN`, not `NON_COMPLIANT`.

Method P emitted two operations and materialized a candidate. Its scoped candidate evaluations both matched the complete pinned representation template, evaluator/configuration digests, architecture revision/tree, scope, stage, covered obligation, and evidence contract before execution. Their raw results are in the V4 archive. The entire candidate still failed validation because these two scoped runs do not supply artifacts for the four inherited active representations:

- `REP_A0_PERF_RUNTIME_HTTP_DURATION`
- `REP_A0_PERF_TEST_HTTP_P95`
- `REP_A0_REL_RUNTIME_FAILURES`
- `REP_A0_REL_TEST_INTEGRATION`

The candidate evaluator passes do not clear that full-configuration failure.

## Evidence consumption, pair validity, and governance

V4 records `exp02_evidence_admission_status=admitted_execution_evidence`, `exp02_evidence_admitted_to_p_calculations=true`, and `adaptation_evidence_trust_scope=TEST_ONLY`. The digest-validated execution records and raw artifacts were supplied to `run_adaptation()` before adaptation and were available to P's pair assessment and operation planning. The separate field `exp02_observations_used_as_semantic_pair_evidence=false` remains false; no positive semantic pair proof was supplied. Execution evidence therefore entered the intended DEVELOPMENT calculation but did not become valid pair coverage or authority.

Both candidate exact pairs remain `UNKNOWN` because evaluator inspection scope is not established and pair semantic proof is missing. Their compliance fields are also `UNKNOWN`. The corrected assessor leaves compliance unknown when evaluator identity, execution, target/stage/mapping scope, or artifact integrity is unresolved; a clean exit code cannot override those blockers. A resolved nonzero result remains a separate noncompliance observation even when adequacy is unproven.

Governance returned `HOLD` with these reason codes:

- `CANDIDATE_NOT_POSITIVELY_VALIDATED`
- `IMPACTED_RETAIN_REASSESSMENT_MISSING`
- `INPUT_AUTHORITY_OR_COMPLETENESS_UNRESOLVED`
- `INVARIANT_VERDICTS_NOT_ALL_POSITIVE`
- `REQUIRED_STAGE_EVIDENCE_UNKNOWN`
- `VERIFIED_GOVERNANCE_PIPELINE_PROOF_MISSING`

The current result is therefore a materialized but unvalidated adaptation. It shows that the existing Method P DEVELOPMENT pipeline can produce operations and a candidate from the real A0 → A0.1 source transition under declared TEST_ONLY applicability assumptions and digest-validated evaluator observations. It does not demonstrate accepted adaptation, verified coverage improvement, B0/P detection superiority, or full candidate validity. B0 could not produce a usable comparison because its frozen evaluator scope mismatched A0.1; no controlled degradation was introduced in this execution. The independent coverage denominator and semantic adequacy remain unresolved.

## Time measurements

| Timed component | Duration | Measurement boundary |
|---|---:|---|
| Method P adaptation | `225,158,417 ns` (`0.225158417 s`) | Timer around `run_adaptation()` only. |
| B0 evaluator | `85,392,875 ns` (`0.085392875 s`) | One frozen Import Linter invocation; inconclusive result. |
| Candidate Import Linter | `99,483,667 ns` (`0.099483667 s`) | One scoped evaluator subprocess. |
| Candidate module-structure pytest | `296,822,875 ns` (`0.296822875 s`) | One scoped evaluator subprocess. |
| Candidate evaluator total | `396,306,542 ns` (`0.396306542 s`) | Sum of the two subprocess durations, including startup. |

The candidate evaluator set has two runs while B0 has one, and the configurations differ. These durations are descriptive measurements, not a controlled speedup comparison. Preparation of the P input, the whole candidate validator, and runtime/deployment overhead are not included in the Method P timer.

## Preserved continuation history

All versions concern the same transition and are not independent samples. Earlier records remain preserved without rewriting their raw trace bytes. V2's exit-only compliance labels are superseded by the generic classification correction in V3. V3's inherited `not_admitted` trace label is superseded by the V4 wrapper correction; V4 distinguishes admitted execution observations from absent semantic proof.

| Record | Source / purpose | Preserved archive and SHA-256 |
|---|---|---|
| Original HOLD | Initial PILOT-02 run | `PILOT_02_RAW_EVIDENCE.zip`; `07d678b6f67018c9f59b4b9f27406dceebdf8d38ecd975b3b64cd40342f3b917` |
| V1 continuation | Historical TEST_ONLY continuation | `PILOT_02_RAW_EVIDENCE_CONTINUATION.zip`; `243111746f805f39f256622bed3e2fdf74b25a001f6f7dd1015ec4acbf8339d4` |
| V2 continuation | Corrected applicability and candidate-evaluator binding | `PILOT_02_RAW_EVIDENCE_CONTINUATION_V2.zip`; `fd2dd3b4070729d3b1c802817400f560c77e4d8c50a8b1404090192b44768285` |
| V3 continuation | Corrected unresolved-scope compliance classification | `PILOT_02_RAW_EVIDENCE_CONTINUATION_V3.zip`; `9c0c3f08de9d580b6f233dbeef20a9291206cfe455ec56bd5e84bbb347b02c92` |
| V4 continuation | Corrected execution-evidence admission trace label; current result | `PILOT_02_RAW_EVIDENCE_CONTINUATION_V4.zip`; `4ff90f865ad48dae7e89e18f43b281467f35858fe92970858b2375342016b1a0` |

## Reproduction and verification

The V4 experiment used the bundled Python 3.12 runtime because `uv` is not installed in this environment. From the clean V4 source commit, these were the experiment commands and outcomes:

```bash
export PYTHONDONTWRITEBYTECODE=1
export PYTHONHOME=/Users/oleksii_makieiev/.cache/codex-runtimes/codex-primary-runtime/dependencies/python
export PYTHONPATH=/Users/oleksii_makieiev/Documents/startups/evofit-bench/.venv/lib/python3.12/site-packages
PYTHON=/Users/oleksii_makieiev/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3

"$PYTHON" -m scripts.exp01_evidence --architecture-state A0_1_CAPABILITY_MODULES --run-id pilot02-a01-ci-20261020-v4 --skip-deployment-observation
# Exit 2: bundle incomplete because deployment was skipped and runtime evidence was missing.
"$PYTHON" -m scripts.exp02_fitness_evidence --run-dir experiments/results/pilot02-a01-ci-20261020-v4
# Exit 0: valid; five representations; three unresolved mappings.
"$PYTHON" -m experiments.pilots.run_pilot02_method_p --exp02-run-dir experiments/results/pilot02-a01-ci-20261020-v4 --output-dir /private/tmp/pilot02-corrected-v4-20261020 --test-only-continuation --test-only-assumptions experiments/pilots/PILOT_02_DEVELOPMENT_ASSUMPTIONS_V2.json
# Exit 0: TEST_ONLY continuation completed; governance HOLD.
```

Focused and adjacent verification on the corrected code:

- The exact-pair, governance, adaptation-evidence, EXP-04, PILOT-02 candidate/runner, context-document, EXP-03 bridge, and governed-adaptation suites: **122 passed, 1 existing deprecation warning**. The command was `python -m pytest -q --no-cov -p no:cacheprovider tests/unit/test_p_semantic_pairs_v1.py tests/unit/test_p_candidate_governance_v1.py tests/unit/test_p_adaptation_evidence_v1.py tests/integration/test_exp04_evidence_admission.py tests/unit/test_pilot02_testonly_execution.py tests/unit/test_pilot02_candidate_evaluators.py tests/unit/test_context_documents.py tests/integration/test_exp03_method_bridge.py tests/integration/test_p_governed_adaptation_v1.py`.
- PILOT-02 TEST_ONLY runner, candidate-evaluator, context-document, and EXP-03 bridge suites: **51 passed, 1 existing deprecation warning**. The command was `python -m pytest -q --no-cov -p no:cacheprovider tests/unit/test_pilot02_testonly_execution.py tests/unit/test_pilot02_candidate_evaluators.py tests/unit/test_context_documents.py tests/integration/test_exp03_method_bridge.py`.
- Repository Ruff check: **PASS**; repository Ruff format check: **PASS, 259 files already formatted**.
- Targeted Mypy for the changed semantic assessor/tests and PILOT-02 runner/test: **PASS**.
- Architecture tests: **PASS, 6 passed**; Import Linter: **PASS, 5 contracts kept, 0 broken**; Bandit: **exit 0** with existing comment-parser warnings.
- `git diff --check`: **PASS**.
- Full local Mypy attempt: **FAIL**, with four existing errors in unchanged PILOT-01 files (`generate_pilot01_results.py` and `run_pilot01_measurement.py`, including missing `psutil` stubs); changed files pass targeted Mypy.
- Migration validation: **BLOCKED** because `TEST_DATABASE_URL` is unset and no disposable database was configured. `make development-quality` was not run because `uv` is unavailable and the local migration prerequisite is absent.

The V4 archive's run-manifest digest and all 130 inventoried artifact sizes and SHA-256 values were verified during archive construction. EXP-02 independently validated the V4 bundle. Hosted CI for the final PR head is tracked in PR #22.

## Research status and limits

G1 remains `INCOMPLETE`; G4 remains `NOT AUTHORIZED`; `P_ALGORITHM_STATUS` remains `NOT_READY`. The pilot does not alter frozen A0/DA01 files, the DA01 authorization boundary, the oracle/scorer, or research gates. No statistical significance is claimed from this single architecture transition or its technical continuations. External review is not a prerequisite for this DEVELOPMENT experiment and did not gate its execution.
