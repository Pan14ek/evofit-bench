# MONO-E1 DEVELOPMENT pilot preparation report

Date: 2026-10-23
Status: DEVELOPMENT evidence only; official MONO-E1 and B0/P arms were not run.

## Scope and source identities

This report covers the A0.3 → A0.4 transition and the two engineering CI controls
`AC_PUBLIC_API` and `AC_MODULE_GRAPH`. It does not establish the full
`Q(A0.4)` denominator or a scientifically validated fitness representation.

| State | Canonical source commit | Repository tree | Application tree | Checkpoint |
| --- | --- | --- | --- | --- |
| A0.3 `A0_3_GOVERNED_MODULE_GRAPH` | `26a9bb667da7d0938e38aca15d2bf29fd1de4829` | `7b951421395f532ca403dab09d76902ff08a807d` | `b147b8961ea9e76c966663d4832e4c303581151a` | `architecture/acceptance/a1/a0_3_canonical_checkpoint.json`, SHA-256 `5da4a7e1ed359ec8ea1e3288ab81edf32f0b71e2fec946b52a8d0d562dcf43c0` |
| A0.4 `A0_4_REPORT_QUERY_PORT` | `d3101c0d3aa9b7b709253b6ec7518416f05f65b9` | `2b436e0aaf09403ea516d73d20a466a122f86592` | `007196f68652bc13f6798805793ffdfae96f95f7` | `architecture/acceptance/a1/a0_4_canonical_checkpoint.json`, SHA-256 `7b0b0c7a0c6ac782540466d283c42d7589b8aaeb4af7df62104faa01fd154e8e` |

Both canonical checkpoints report complete source scope, successful readback,
and `COMPLIANT` for both controls. Each inspected 31 Python files and 185
import nodes. This records engineering evaluator execution and source-level
compliance under the configured checks.

## A0.3 fitness configuration lineage

No versioned A0.3 fitness configuration or representation mapping for these
controls was found in the canonical A0.3 tree. The frozen A0 B0 configuration
remains the original baseline:

- Source tag `arch-a0-monolith-v1`, revision
  `b78b0967be937634b7762baccf5ac6892b279a73`.
- `fitness/configs/a0-monolith.yaml`, SHA-256
  `5ad60e373463ea459e192bf85d82704ca9aa1c217c4abf4d8caeb66924059ecb`.
- Its architectural representation is `REP_A0_ARCH_CI_LAYERING`, linked to
  `AC_LAYERING`; applicability at A0.3 is `UNKNOWN`.

The A0.3 state manifest requires the two CI evaluators for engineering
acceptance. That requirement does not create fitness representation IDs,
obligation-stage mappings, or a reviewed parent configuration. The separate
candidate at
[`mono_e1_a03_fitness_configuration_candidate_v1.json`](mono_e1_a03_fitness_configuration_candidate_v1.json)
is explicitly `DEVELOPMENT_ONLY_CANDIDATE_NOT_HISTORICAL`. A0.3 parent
configuration is `NOT_IDENTIFIED`, the RETAIN reference is
`NOT_EVALUABLE`, both semantic pairs are `UNREVIEWED`, and method-input and
scientific approval are false. The candidate records provenance without
rewriting frozen A0 bytes or claiming that the candidate existed historically.

## Evaluator and configuration bindings

The same evaluator implementation and configuration bytes are pinned by the
A0.3 and A0.4 checkpoints:

| Control | Evaluator source digest | Configuration | A0.3 / A0.4 outcome |
| --- | --- | --- | --- |
| `AC_PUBLIC_API` v1.0.0 | `5c17373ba8896ef0c443d826bd0064168ec7c5759c7973f9602b6c2c715b169c` | `architecture/acceptance/a1/public_api_v1.yaml`, SHA-256 `8853c3a933b23f698c7ba7c5b6e511f292e8d9285dc0de4378741c53e466f7bb` | completed, complete scope, compliant |
| `AC_MODULE_GRAPH` v1.0.0 | `5c17373ba8896ef0c443d826bd0064168ec7c5759c7973f9602b6c2c715b169c` | `architecture/acceptance/a1/module_graph_v1.yaml`, SHA-256 `1abae6871a477ff2a07685ad645a70defa2f1ac6745598ae4cdc35aab4e95bf6` | completed, complete scope, compliant |

The aggregate evaluator digest binds `__init__.py`, `analyzers.py`, `cli.py`,
and `engine.py`; their individual hashes are recorded in the candidate JSON and
canonical checkpoints. The checked-in A0.3 checkpoint readback and the
A0.4 historical checkpoint checks bind those bytes to the respective source
revisions. No A0.3 or A0.4 source was mutated for this task.

## Controlled evaluator evidence

Existing EVAL-01 and EVAL-02 raw archives were revalidated by external SHA-256
sidecar, ZIP CRC, and their internal `SHA256SUMS` inventories. Both bind to
A0.4 source `d3101c0d3aa9b7b709253b6ec7518416f05f65b9`, application tree
`007196f68652bc13f6798805793ffdfae96f95f7`, and the evaluator/configuration
digests above.

| Study | Calls and integrity | `AC_PUBLIC_API` binary cases | `AC_MODULE_GRAPH` binary cases | Result boundary |
| --- | --- | --- | --- | --- |
| EVAL-01 | 7 conditions × 2 controls × 3 repeats = 42 calls; 0 runner failures; archive SHA-256 `f6cd3c7180a0719c0f410f51acc9596b0843950d7650da7f7d2924716188c9bf`; 116 internal checksums verified | TP=1, TN=5, FP=0, FN=0; 6/6 evaluable | TP=3, TN=3, FP=0, FN=0; 6/6 evaluable | Clean and allowed imports were accepted; private cross-module import, undeclared edge, cycle, and unresolved local import were detected. Missing expected module scope stayed `NOT_EVALUABLE`. |
| EVAL-02 | 10 conditions × 2 controls × 3 repeats = 60 completed calls; 0 launch/parse/provenance failures; 3 exact-diagnostic mismatches retained (the preregistered run reported exit 1); archive SHA-256 `9039e17b5b640db5641b808719c6b972a389b8f5e833ac1dc7783e658f4bf18c`; 161 internal checksums verified | TP=4, TN=4, FP=0, FN=0; 8 applicable cases | TP=2, TN=4, FP=0, FN=0; 6 applicable cases | Positive and negative source patterns classified as preregistered on applicable cases. The missing-function case had expected `NON_COMPLIANT` status but emitted one additional finding class on all three repeats; this remains a diagnostic failure. |

These finite, author-selected source-pattern cases demonstrate that the pinned
rules execute non-vacuously and detect their named static violations. They do
not establish population accuracy, independent labels, or full architecture
conformance. EVAL-02 also found a dynamic private import violation outside the
static import inventory; both controls returned compliant for that out-of-
scope case. `AC_PUBLIC_API` does not validate callable signatures or runtime
behavior. See the original [EVAL-01 report](../experiments/pilots/EVAL01_REPORT_V1.md),
[EVAL-02 report](../experiments/pilots/EVAL02_REPORT_V1.md), and
[EVAL-02 erratum](../experiments/pilots/EVAL02_POST_EXPERIMENT_ERRATUM_V1.md)
for per-case evidence and the preserved mismatch. The archived study reports
record each mutation as a clean child of canonical A0.4 and preserve the
mutation patches and Git bundles; this task introduced no canonical-source
mutation.

## Generic Method P DEVELOPMENT checks

No Method P execution was performed on canonical ΔA4. The generic synthetic
unit and integration suites exercised RETAIN/no-change, missing or insufficient
evidence, stale and contradictory evaluator evidence, HOLD, invalid mappings,
and unauthorized adaptation behavior using synthetic fixtures. The focused
suite passed **154 tests with 1 warning**. The broader `make
development-quality` regression target passed **493 tests**, including those
generic tests and input-isolation checks; its dedicated EXP-01 and EXP-02 suites
then passed **49** and **30** tests. No test failures or skipped tests were
reported; one Starlette deprecation warning was reported.

The development target intentionally excludes the protected
`tests/unit/test_da01_execution.py` and
`tests/unit/test_research_schema_foundation.py` suites. No measured DA01 or
MONO-E1 result follows from these synthetic checks.

## Verification record

Commands executed in the task checkout:

| Command / check | Result |
| --- | --- |
| `tests/architecture/a1/test_evaluators.py`, `tests/unit/test_eval01_runner.py`, `tests/unit/test_eval02_runner.py`, `tests/unit/test_eval02_postrun_validation.py`, `tests/unit/test_mono_e1_ci_profile.py`, `tests/unit/test_mono_e1_a03_fitness_candidate.py` | 68 passed, 16.34 s |
| `tests/unit/test_p_applicability_ruleset_v1.py`, `test_p_applicability_policies_v1.py`, `test_p_impact_v1.py`, `test_p_semantic_pairs_v1.py`, `test_p_operations_v1.py`, `test_p_candidate_governance_v1.py`, `test_p_adaptation_evidence_v1.py`, `test_p_interface_readiness.py`, `tests/integration/test_p_applicability_v3.py`, `test_p_governed_adaptation_v1.py` | 154 passed, 1 warning, 121.55 s |
| `make development-quality UV=/private/tmp/evofit-uv-runtime/bin/uv` with `ARCHITECTURE_STAGE=A0_4_REPORT_QUERY_PORT`, disposable PostgreSQL 16, and isolated uv/import-linter caches | PASS: Ruff check and format; Mypy (141 files); Bandit; Import Linter (5 kept, 0 broken); current and historical architecture checks; migration validation; regression suites 493 + 49 + 30 passed, 1 deprecation warning total |

`make development-quality` completed with exit code 0. Its database was a
disposable local container. The full regression command excludes the two
protected suites listed above by the checked-in Makefile target. Hosted CI
results are reported on the accompanying pull request.

## Readiness and next actions

This work does not change any scientific gate: `P_ALGORITHM_STATUS=NOT_READY`,
G1 is `INCOMPLETE`, G4 is `NOT_AUTHORIZED`, MONO-E1 remains `NO_GO`, and the
full `Q(A0.4)` denominator remains `NOT_ESTABLISHED`. No reference freeze or
scorer-only expected operations were created or added to the repository.

Before canonical B0/P execution, the next work is to:

1. Resolve the historically applicable A0.3 parent fitness configuration, or
   explicitly define a separately versioned E1 treatment without relabeling
   frozen A0 B0; keep RETAIN `NOT_EVALUABLE` until then.
2. Have accountable independent reviewers assign real representation IDs,
   approve the applicable obligation and lifecycle scope, and assess each
   source-bound representation/evaluator/stage pair. Resolve the EVAL-02
   diagnostic mismatch as a documented evaluator issue, not by changing its
   archived outcome.
3. Establish the full 18-obligation denominator and policy authority, or
   approve a separately versioned bounded CI study with explicit exclusions
   and narrower claims.
4. Complete the protocol's independent reference review and
   `G-A1-C4-REF-FROZEN` procedure, resolve common B0/P inputs and comparability,
   freeze a digest-pinned Method P implementation, then complete G1 and obtain
   separate G4 authorization before measured execution.
5. Use a separately authorized positive-adaptation case to assess ADD/REPLACE;
   this no-change preparation cannot establish successful adaptation.

**Recommendation:** address the A0.3 parent-configuration and independent
semantic-pair decisions first, then update the MONO-E1 preflight from evidence.
Keep the current outcome `NO_GO` until all required authority, reference,
comparability, and authorization checks pass.

## Requirement-to-test map

| Requirement | Test/evidence | Outcome |
| --- | --- | --- |
| `MONO-DEV-LIN-01`: distinguish frozen A0 B0 from A0.3 engineering controls; bind candidate claims to canonical A0.3 bytes | `tests/unit/test_mono_e1_a03_fitness_candidate.py`; canonical A0.3 checkpoint | 2 candidate tests passed; historical configuration remains not identified |
| `A1-NEG-01`–`A1-NEG-03`: evaluator accepts controls and reports seeded static violations with source-bound evidence | `tests/architecture/a1/test_evaluators.py`; EVAL-01/02 archives and validators | focused regression passed; archive outcomes and EVAL-02 discrepancy retained |
| `P03-02`–`P03-06`: generic operation selection, exact-pair evidence, candidate governance, rollback/replay, and adaptation boundaries | `tests/unit/test_p_operations_v1.py`, `test_p_semantic_pairs_v1.py`, `test_p_candidate_governance_v1.py`, `test_p_adaptation_evidence_v1.py`; `tests/integration/test_p_governed_adaptation_v1.py` | included in 154 focused synthetic passes and 493 development regressions |
| `S01`: method input excludes oracle/history/network/other-arm output | `tests/unit/test_da01_inputs_and_isolation.py::test_container_negative_probes_cannot_reach_oracle_history_network_or_other_output` | included in the 493-test development regression run |
| `E01`: authorized, independently reviewed measured B0/P comparison | MONO-A1 protocol and G1/G4 gates | not run; remains unauthorized / `NO_GO` |
