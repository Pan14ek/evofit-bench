# PILOT-02 — A0 to A0.1 Method P DEVELOPMENT results

**Latest completed execution:** V5d, `pilot02-inherited-20261020-v5d`.
**Result class:** candidate configuration valid; governance `HOLD`; one inherited runtime-failure measurement remains unavailable.
**Scope:** TEST_ONLY DEVELOPMENT for the single transition `A0_MONOLITH → A0_1_CAPABILITY_MODULES`; this is not a measured DA01 result.

## Objective and protocol boundary

PILOT-02 compares the unchanged frozen B0 fitness configuration with the existing Method P adaptation path for the architecture-compliance obligations `AC_LAYERING` and `AC_MODULE_STRUCTURE`. B0 and P used the same clean A0.1 application tree and source revision. The baseline configuration and its evaluator were not changed.

The V2 assumption file, pinned before V2 and reused unchanged through V5d, classifies `AC_LAYERING` as active in A0 and A0.1, and `AC_MODULE_STRUCTURE` as inactive in A0 and active in A0.1. These are researcher-declared TEST_ONLY states informed by the checked-in A0 traceability, frozen A0 configuration/evaluator, and A0.1 state manifest. They are not independent policy authority or an approved coverage denominator. The target stage is `ci`.

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
| Historical V4 continuation | Corrected execution-evidence admission trace label before inherited-evaluator execution | `PILOT_02_RAW_EVIDENCE_CONTINUATION_V4.zip`; `4ff90f865ad48dae7e89e18f43b281467f35858fe92970858b2375342016b1a0` |
| V5 canonical continuation | Four inherited evaluator observations; full candidate artifact validation | `PILOT_02_RAW_EVIDENCE_CONTINUATION_V5.zip`; `358c6758c5acf7efde694357471a17f12546d8f3076a85fc1263634688240d9b` |

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


## V5 inherited-evaluator execution and Method P continuation

### Run identity and evidence status

The canonical continuation is `pilot02-inherited-20261020-v5d`, captured from clean source revision `3758e2cd60810b8d4263f8d91443ec829efc8bb5`. The A0.1 application tree is SHA-1 `cdff9a6c3cee870e1eca2a5f5f3eb3202b0b1f08`; the versioned inherited-evaluator profile V2 is SHA-256 `c480b1907d9f69cb7c5d1c4f45cb221551aeb857881ba859529e8c1f1fd5e8c9`. All four inherited rows are explicitly bound as `A0_1_DEVELOPMENT_ADAPTER` records. This is a prospective A0.1 binding and does not assert that these executable artifact paths were packaged with frozen A0. This DEVELOPMENT run used the pinned TEST_ONLY applicability assumptions and did not provide expected operations, oracle labels, or scorer outputs to Method P. The exact command argument vectors and stdout/stderr hashes are preserved in the run evidence.

The run completed as `completed_development_evidence`. Post-write readback validated all 193 inventoried artifacts. The run manifest SHA-256 is `5805be2dea554e7b314de1c7224054ddb769aeabd219423e0faf244cbf9b14d8`; `inventory.json` SHA-256 is `325b59609f1017ed87d4c4be14bab1a460abb13f29dfe6cf454e8cf5f37155b1`; `evaluator_inventory.json` SHA-256 is `2c5b916173b7a4a2c68eb3dff2e0dc8b73b529215c83c422eaf2fdcee77adbb2`; `evaluator_results.json` SHA-256 is `69ab9f0d7d6895b2fe7997ed4b88f256ee4bd05a927f4c6254d61b27162f4f93`.

### Inherited evaluator observations

Each unchanged inherited row was executed once against the same fresh A0.1 source. These are shared observations for the unchanged B0 and P-retained rows, not separate arm executions or independent replicates.

| Representation | Reused A0.1 DEVELOPMENT evaluator and pinned artifacts | V5d observation | Candidate-validation impact and limit |
|---|---|---|---|
| `REP_A0_PERF_TEST_HTTP_P95` | Existing Locust workload source `load/locustfile.py`; source SHA-256 `c8c7922998c8ca2e9479c5c720f547a805418248afc2f078c79493080ac41574`; configuration SHA-256 `966bc5e5762324e4b8b9af6d998a29f6a0d919a1321b955922dec6d3bd41f4b1`. | Measured; exit 0; `http_p95_ms=23`; 133 requests, 0 failures, p50 14 ms, p99 42 ms; 30.280 s. `evaluation_status=NOT_EVALUATED` because no threshold is configured. | Exact source/config binding satisfies the candidate artifact check. This is an observed latency, not an SLO pass. App source-to-image identity remains unverified. |
| `REP_A0_PERF_RUNTIME_HTTP_DURATION` | Existing EXP-01 runtime collector `scripts/exp01_evidence_runtime.py`; source SHA-256 `467302575f6eff47e0b1139337b9f6087473c07fd530a520afb4776c9216d4f8`; configuration SHA-256 `1b323b9fe5a65995138c821a4d0f174e3158588de7e79df5d42cc4b9005b71b1`. | Measured; exit 0; 153 raw histogram series (135 bucket, 9 count, 9 sum); across count series, interval delta 95; summed sum-series delta 0.674420002 seconds over 15 s. No p50/p95/p99 was inferred. `evaluation_status=NOT_EVALUATED`. | Exact source/config binding satisfies the candidate artifact check. Collector is an A0.1 adapter absent from frozen A0; runtime image provenance is unverified. |
| `REP_A0_REL_TEST_INTEGRATION` | Existing targeted pytest node in `tests/integration/test_api_flows.py`; source SHA-256 `dbd306696ecd625f54476a9d918c586c4ca67d532c623ffd04c32c72117e5eb3`; configuration SHA-256 `a465ad4f6096867793bb60081d289295fe9af8a6e21a132738fbed348c8bc8cb`. | `tests/integration/test_api_flows.py::test_enabled_faults_delay_fail_deterministically_and_reset`; measured `PASS`; 1 passed, 0 failed, 0 errors, 0 skipped; 1.605 s. Used isolated disposable `evofit_pilot02_test` PostgreSQL. | Exact source/config binding satisfies the candidate artifact check. The pre-run inventory maps this targeted fault-and-consistency check to `R_LOCAL_ATOMICITY`; its run does not supply independent Method P semantic-pair proof. |
| `REP_A0_REL_RUNTIME_FAILURES` | Existing EXP-01 runtime collector `scripts/exp01_evidence_runtime.py`; source SHA-256 `467302575f6eff47e0b1139337b9f6087473c07fd530a520afb4776c9216d4f8`; configuration SHA-256 `ecf4c7726418fe53c1fc9e91dc4e5eaca061ad4be0556a473c14f822128dda75`. | Partial execution; exit 0; `evaluation_status=UNKNOWN`. The business-request counter recorded 75, but no matching 5xx numerator or business-operation-failure samples were available. No zero failure rate is claimed. | Exact source/config binding satisfies the candidate artifact check. The required failure observations remain unavailable, so this row does not establish a runtime-failure result. |

The two runtime rows share one 16.762 s EXP-01 collection interval. Its endpoint stayed bound to one Docker application container, but no application revision label or authoritative source-to-image proof was available. The dedicated PostgreSQL container ID and database name are recorded in the run evidence; credentials were not recorded. The disposable database was stopped after evidence capture.

### B0 comparison and Method P result

The unchanged B0 Import Linter invocation took `105,177,542 ns` and exited 1 because its configured `app.repositories` target is absent from A0.1; no broken-contract count was emitted. This result is inconclusive, not an architecture-violation finding. B0 has no `AC_MODULE_STRUCTURE` representation.

With the four V2 artifact bindings present, the full candidate validator changed from V4's `failed: ACTIVE_EVALUATOR_ARTIFACT_UNAVAILABLE` to V5d `candidate_status=valid`. Method P formed two TEST_ONLY operations:

- `ADD AC_MODULE_STRUCTURE`
- `REPLACE REP_A0_ARCH_CI_LAYERING`

The materialized candidate SHA-256 is `1396dc3735e15088920ee423701021505ca1c1d37712d3b7e68a98ca5a879534`. The two planning costs are 1.0 TEST_ONLY units each; these are not elapsed time. Candidate Import Linter execution exited 0 with 5 contracts kept and 0 broken in `95,593,375 ns`; the module-structure test exited 0 with 1 test passed in `264,222,708 ns`. Their combined subprocess time was `359,816,083 ns`.

Method P's `run_adaptation()` computation took `211,492,500 ns`. The candidate exact pairs for `AC_LAYERING` and `AC_MODULE_STRUCTURE` remain `UNKNOWN`, with unresolved inspection scope and missing semantic pair proof. Compliance remains `UNKNOWN`. The candidate's internal mandatory diagnostic is 0/2; it is not `Coverage_P` or independent coverage. Governance remains `HOLD` because retained-representation reassessment, authority/completeness, positive invariant verdicts, required-stage evidence, and verified governance-pipeline proof are unresolved. `P_ALGORITHM_STATUS=NOT_READY`, G1=`INCOMPLETE`, and G4=`NOT AUTHORIZED` remain unchanged.

### Timing and detection limits

| Timed activity | Duration | Boundary |
|---|---:|---|
| Locust | 30,280,221,834 ns | Fresh 30 s workload process; includes process execution. |
| Shared EXP-01 runtime collection | 16,762,113,542 ns | One collector for both runtime representations; overlaps the Locust workload. |
| Targeted integration test | 1,605,201,042 ns | One exact pytest node against the disposable database. |
| Unchanged B0 evaluator | 105,177,542 ns | One frozen Import Linter invocation; inconclusive. |
| Method P adaptation computation | 211,492,500 ns | Timer around `run_adaptation()` only. |
| P candidate evaluators | 359,816,083 ns | Sum of two candidate subprocess durations, including startup. |
| Method P CLI continuation | 6,905,094,125 ns | Full command recorded in the run manifest, including work outside the adaptation timer. |

These durations have different boundaries. The runtime collector overlaps Locust, and preparation, Compose setup, full candidate validation and teardown are not all represented by the adaptation timer. They are not a controlled speedup comparison. B0 was inconclusive, P exact pairs are UNKNOWN, and no controlled degradation was introduced. Comparative detection behavior is therefore not established.

### Blocker status and preserved attempts

The original `ACTIVE_EVALUATOR_ARTIFACT_UNAVAILABLE` blocker is **fully resolved as a candidate-validator artifact-binding error**: all four rows now have exact source/configuration bindings in the prospective V2 profile, and the full candidate validator reports `valid`. This does not establish complete or semantically adequate evidence for every row. In particular, `REP_A0_REL_RUNTIME_FAILURES` remains `UNKNOWN`, exact-pair validity and coverage remain unresolved, and governance remains `HOLD`.

The V5 archive `PILOT_02_RAW_EVIDENCE_CONTINUATION_V5.zip` has SHA-256 `358c6758c5acf7efde694357471a17f12546d8f3076a85fc1263634688240d9b`. It contains the canonical V5d run and linked EXP-01 bundle, the V2 protocol/profile/assumptions/schemas and runner sources, plus raw records of earlier V5 technical attempts. The initial setup failure ran no evaluator; V5b recorded authentic outputs but failed finalization on a runner `KeyError`; V5c completed but omitted the database container ID. Those attempts are preserved and excluded from primary analysis. V1–V4 archives remain unchanged.
