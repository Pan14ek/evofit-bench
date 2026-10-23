# EVAL-01 results — controlled evaluator validation

- **Protocol/catalog:** version 1.0.0; preregistration commit `7186dfe6359cba5ac8e0a8fc616bdb5118e59415`; catalog SHA-256 `0d4aeb1b49aa800a4618dbce79966de40dcd070f78dfd515eb100086acab04a8`.
- **Main base:** `6a7d44595ac5155c443ee3aad84d6792d587f666`.
- **Canonical A0.4:** `d3101c0d3aa9b7b709253b6ec7518416f05f65b9`; app tree `007196f68652bc13f6798805793ffdfae96f95f7`.
- **Run window:** 2026-10-23T06:00:35.357359+00:00 — 2026-10-23T06:00:44.239355+00:00.
- **Execution environment:** Python 3.12.14, PyYAML 6.0.3, macOS-26.6.2-arm64-arm-64bit.

## Research question and preregistered hypotheses

**RQ:** On clean, source-pinned A0.4 checkouts, do `AC_PUBLIC_API` and `AC_MODULE_GRAPH` produce the outcomes catalogued for the controlled mutations, and what subprocess wall time is observed?

- **H1:** allowed public module imports remain compliant; the private Reporting → Tasks service import is rejected by `AC_PUBLIC_API`.
- **H2:** `AC_MODULE_GRAPH` rejects the injected undeclared edge, cycle, and unresolved local import while accepting the five declared edges.
- **H3:** deleting the expected Audit package yields explicit `NOT_EVALUABLE` scope results, not a detection true positive.

## Intervention and execution

The experiment materialized 7 source conditions from canonical commit `d3101c0d3aa9b7b709253b6ec7518416f05f65b9`. Every mutation has a distinct Git commit with canonical A0.4 as its sole parent; the archive retains the exact mutation patch and Git bundle. Before each of 42 evaluator calls the runner required clean checkout state and passed the case HEAD as `--expected-source-sha`. Both evaluators ran 3 times on every condition in seed-randomized order. The untouched baseline checks all five expected edges, zero cycles, and zero unresolved imports. The public-import pair contrasts the same Reporting/Tasks boundary. Type-checking-only cases test static source rules without claiming runtime execution.

These are controlled W2 engineering evaluator observations, not MONO-E1/E2, B0, Method P, scorer, production, or fitness-representation coverage evidence.

## Results

### Case-level detection metrics

| Evaluator | TP | FP | TN | FN | Labeled/evaluable | Unknown or invalid | Precision | Recall | Specificity | Accuracy | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| AC_PUBLIC_API | 1 | 0 | 5 | 0 | 6/6 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| AC_MODULE_GRAPH | 3 | 0 | 3 | 0 | 6/6 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

The unit is one labeled evaluator-by-source-case condition. The 42 evaluator calls are **not** 42 independent cases; the three calls for each condition are collapsed before confusion metrics. Counts include only preregistered binary labels with stable, source/configuration-bound `COMPLIANT` or `NON_COMPLIANT` outcomes. The missing-package condition is `NOT_EVALUABLE` and is excluded by the catalog. Undefined metric denominators are shown as `NOT_DEFINED`. No confidence intervals or population inference are computed.

### Per-case observations

| Case | Evaluator | Expected | Observed by repeat | Finding classes | Metric status |
| --- | --- | --- | --- | --- | --- |
| `clean_unchanged_dependencies` | `AC_PUBLIC_API` | `COMPLIANT` | COMPLIANT, COMPLIANT, COMPLIANT | none; none; none | included |
| `clean_unchanged_dependencies` | `AC_MODULE_GRAPH` | `COMPLIANT` | COMPLIANT, COMPLIANT, COMPLIANT | none; none; none | included |
| `allowed_public_api_import` | `AC_PUBLIC_API` | `COMPLIANT` | COMPLIANT, COMPLIANT, COMPLIANT | none; none; none | included |
| `allowed_public_api_import` | `AC_MODULE_GRAPH` | `COMPLIANT` | COMPLIANT, COMPLIANT, COMPLIANT | none; none; none | included |
| `forbidden_private_cross_module_import` | `AC_PUBLIC_API` | `NON_COMPLIANT` | NON_COMPLIANT, NON_COMPLIANT, NON_COMPLIANT | CROSS_MODULE_IMPORT_NOT_PUBLIC; CROSS_MODULE_IMPORT_NOT_PUBLIC; CROSS_MODULE_IMPORT_NOT_PUBLIC | included |
| `forbidden_private_cross_module_import` | `AC_MODULE_GRAPH` | `COMPLIANT` | COMPLIANT, COMPLIANT, COMPLIANT | none; none; none | included |
| `undeclared_capability_dependency` | `AC_PUBLIC_API` | `COMPLIANT` | COMPLIANT, COMPLIANT, COMPLIANT | none; none; none | included |
| `undeclared_capability_dependency` | `AC_MODULE_GRAPH` | `NON_COMPLIANT` | NON_COMPLIANT, NON_COMPLIANT, NON_COMPLIANT | UNDECLARED_DEPENDENCY; UNDECLARED_DEPENDENCY; UNDECLARED_DEPENDENCY | included |
| `dependency_cycle` | `AC_PUBLIC_API` | `COMPLIANT` | COMPLIANT, COMPLIANT, COMPLIANT | none; none; none | included |
| `dependency_cycle` | `AC_MODULE_GRAPH` | `NON_COMPLIANT` | NON_COMPLIANT, NON_COMPLIANT, NON_COMPLIANT | DEPENDENCY_CYCLE, UNDECLARED_DEPENDENCY; DEPENDENCY_CYCLE, UNDECLARED_DEPENDENCY; DEPENDENCY_CYCLE, UNDECLARED_DEPENDENCY | included |
| `unresolved_local_import` | `AC_PUBLIC_API` | `COMPLIANT` | COMPLIANT, COMPLIANT, COMPLIANT | none; none; none | included |
| `unresolved_local_import` | `AC_MODULE_GRAPH` | `NON_COMPLIANT` | NON_COMPLIANT, NON_COMPLIANT, NON_COMPLIANT | UNRESOLVED_LOCAL_IMPORT; UNRESOLVED_LOCAL_IMPORT; UNRESOLVED_LOCAL_IMPORT | included |
| `missing_expected_capability` | `AC_PUBLIC_API` | `NOT_EVALUABLE` | NOT_EVALUABLE, NOT_EVALUABLE, NOT_EVALUABLE | UNDECLARED_PUBLIC_INTERFACE; UNDECLARED_PUBLIC_INTERFACE; UNDECLARED_PUBLIC_INTERFACE | excluded: Incomplete expected-module scope has no binary compliance label and is reported as NOT_EVALUABLE, not as a detection true positive. |
| `missing_expected_capability` | `AC_MODULE_GRAPH` | `NOT_EVALUABLE` | NOT_EVALUABLE, NOT_EVALUABLE, NOT_EVALUABLE | UNRESOLVED_LOCAL_IMPORT; UNRESOLVED_LOCAL_IMPORT; UNRESOLVED_LOCAL_IMPORT | excluded: Incomplete expected-module scope has no binary compliance label and is reported as NOT_EVALUABLE, not as a detection true positive. |

### Subprocess wall time

| Evaluator | Valid completed calls | Median ms | Minimum ms | Maximum ms |
| --- | ---: | ---: | ---: | ---: |
| `AC_PUBLIC_API` | 21 | 205.865 | 196.621 | 232.06 |
| `AC_MODULE_GRAPH` | 21 | 209.188 | 198.191 | 246.596 |

Wall duration includes interpreter startup, source inventory, AST analysis, and JSON output. It is a descriptive evaluator-call measurement, not application runtime, full CI latency, adaptation overhead, CPU, or memory cost. Repeated calls are timing repeats of the same source revisions.

### Failures and unavailable outcomes

Runner-recorded failures: 0.

- None.

Analysis/artifact-integrity issues:

- No provenance, execution, outcome, or artifact-integrity failures were recorded.

Unexpected nonzero evaluator exits are retained. Expected CLI exit 1 for `NON_COMPLIANT` and exit 2 for `NOT_EVALUABLE` are outcomes, not execution failures. A source SHA mismatch, dirty source, evaluator/configuration drift, launch/parse error, or absent observation is never counted as a true positive.

## Limitations and threats to validity

The finite cases were selected by the experiment author from the versioned A0.4 policy, and their labels follow the explicit interventions. Results therefore test these exact conditions and evaluator versions; they do not establish broad external validity or independent semantic review. Mutations are static Python source changes and do not verify runtime behavior.

`AC_PUBLIC_API` checks configured top-level API names and `TaskSummary` fields, not call signatures, runtime re-exports, or behavior. `AC_MODULE_GRAPH` derives dependency edges from direct Python imports and configured shared roots; it does not inspect dynamic imports, reflection, runtime dependency injection, raw SQL contents, database permissions, or deployable topology. Conditional imports count as dependencies regardless of reachability. Missing expected module scope is deliberately unresolved and has no binary label.

The measured duration covers only a fresh evaluator subprocess. This study has one canonical architecture baseline, no runtime workload, no independently designed architecture transitions, no inferential statistics, and no B0/Method P or scorer comparison.

## Supported conclusions

The conclusions are limited to whether each preregistered case produced its expected source-bound evaluator outcome and to the observed subprocess durations. Any confirmed detection supports only the named rule, source pattern, evaluator/configuration version, and A0.4 baseline in this catalog. `NOT_EVALUABLE`, execution failures, and unknown observations remain separate. No conclusion about MONO-E1/E2, Method P effectiveness, production authorization, G1/G4, or population-level evaluator accuracy follows from EVAL-01.

## Reproduction and evidence

Follow [`EVAL01_PROTOCOL_V1.md`](EVAL01_PROTOCOL_V1.md). The archive contains raw stdout JSON and stderr for every scheduled call, exact commands and timings, source and application tree SHAs, evaluator/configuration digests, mutation patches, mutation Git bundles, generated analysis, and `SHA256SUMS`. Verify the external archive sidecar before extraction. See the case-level CSV for machine-readable rows.
