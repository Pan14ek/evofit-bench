# EVAL-02 results — expanded controlled evaluator validation

- **Protocol/catalog:** 1.0.0; preregistration commit `b9952abd42d507febeafe3217cc7b3f4f0e370dd`; catalog SHA-256 `09b3ceda59cf92683abe0e5bad7fd40f4fec18b9e04752292a586d22e6ded637`.
- **Verified main base:** `cd134063e8c1eae37eb3bafe01ce228f02f49493`; PR #38 merge commit.
- **Canonical A0.4 source:** `d3101c0d3aa9b7b709253b6ec7518416f05f65b9`; application tree `007196f68652bc13f6798805793ffdfae96f95f7`.
- **Run window:** 2026-10-23T08:09:19.222401+00:00 — 2026-10-23T08:09:43.216962+00:00.
- **Environment:** Python 3.12.14, PyYAML 6.0.3, macOS-26.6.2-arm64-arm-64bit.

## Design and interpretation

Ten source conditions were registered before evaluator execution. Each mutation was independently created as a clean Git child of canonical A0.4. Both evaluators were called three times per condition; the repeats are collapsed to one case result and are not independent samples. Architectural labels, per-evaluator applicability and expected evaluator outputs were preregistered separately. Out-of-scope and indeterminate cases remain visible but are not included in binary metrics.

## Case-level metrics

| Evaluator | TP | FP | TN | FN | Labeled/evaluable | Unknown/invalid | Excluded | Precision | Recall | Specificity | Accuracy | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `AC_PUBLIC_API` | 4 | 0 | 4 | 0 | 8/8 | 0 | 2 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `AC_MODULE_GRAPH` | 2 | 0 | 4 | 0 | 6/6 | 0 | 4 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |

The unit is one evaluator-by-source-condition case. These finite counts do not estimate population-level accuracy, and no confidence intervals or significance tests are reported.

Applicability and architecture-label counts are shown separately:

| Evaluator | Architectural status counts | Applicability counts |
| --- | --- | --- |
| `AC_PUBLIC_API` | COMPLIANT: 4, INDETERMINATE: 1, NON_COMPLIANT: 5 | APPLICABLE: 8, OUT_OF_SCOPE_CALL_SIGNATURE: 1, OUT_OF_SCOPE_DYNAMIC_IMPORT: 1 |
| `AC_MODULE_GRAPH` | COMPLIANT: 7, NON_COMPLIANT: 3 | APPLICABLE: 6, NOT_APPLICABLE_PUBLIC_CONTRACT_CONSTRUCT: 3, OUT_OF_SCOPE_DYNAMIC_IMPORT: 1 |

## Case results

| Case | Evaluator | Architecture | Applicability | Expected output | Observed repeats | Expected findings | Observed findings | Matrix |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `clean_scope_control` | `AC_PUBLIC_API` | `COMPLIANT` | `APPLICABLE` | `COMPLIANT` | COMPLIANT, COMPLIANT, COMPLIANT | none | none; none; none | included |
| `clean_scope_control` | `AC_MODULE_GRAPH` | `COMPLIANT` | `APPLICABLE` | `COMPLIANT` | COMPLIANT, COMPLIANT, COMPLIANT | none | none; none; none | included |
| `relative_public_import_control` | `AC_PUBLIC_API` | `COMPLIANT` | `APPLICABLE` | `COMPLIANT` | COMPLIANT, COMPLIANT, COMPLIANT | none | none; none; none | included |
| `relative_public_import_control` | `AC_MODULE_GRAPH` | `COMPLIANT` | `APPLICABLE` | `COMPLIANT` | COMPLIANT, COMPLIANT, COMPLIANT | none | none; none; none | included |
| `function_local_public_import_control` | `AC_PUBLIC_API` | `COMPLIANT` | `APPLICABLE` | `COMPLIANT` | COMPLIANT, COMPLIANT, COMPLIANT | none | none; none; none | included |
| `function_local_public_import_control` | `AC_MODULE_GRAPH` | `COMPLIANT` | `APPLICABLE` | `COMPLIANT` | COMPLIANT, COMPLIANT, COMPLIANT | none | none; none; none | included |
| `missing_required_public_function` | `AC_PUBLIC_API` | `NON_COMPLIANT` | `APPLICABLE` | `NON_COMPLIANT` | NON_COMPLIANT, NON_COMPLIANT, NON_COMPLIANT | PUBLIC_INTERFACE_MISSING | PUBLIC_INTERFACE_MISSING, UNDECLARED_PUBLIC_INTERFACE; PUBLIC_INTERFACE_MISSING, UNDECLARED_PUBLIC_INTERFACE; PUBLIC_INTERFACE_MISSING, UNDECLARED_PUBLIC_INTERFACE | included |
| `missing_required_public_function` | `AC_MODULE_GRAPH` | `COMPLIANT` | `NOT_APPLICABLE_PUBLIC_CONTRACT_CONSTRUCT` | `COMPLIANT` | COMPLIANT, COMPLIANT, COMPLIANT | none | none; none; none | excluded: NOT_APPLICABLE_PUBLIC_CONTRACT_CONSTRUCT |
| `missing_typed_dict_field` | `AC_PUBLIC_API` | `NON_COMPLIANT` | `APPLICABLE` | `NON_COMPLIANT` | NON_COMPLIANT, NON_COMPLIANT, NON_COMPLIANT | PUBLIC_TYPED_DICT_FIELDS_MISMATCH | PUBLIC_TYPED_DICT_FIELDS_MISMATCH; PUBLIC_TYPED_DICT_FIELDS_MISMATCH; PUBLIC_TYPED_DICT_FIELDS_MISMATCH | included |
| `missing_typed_dict_field` | `AC_MODULE_GRAPH` | `COMPLIANT` | `NOT_APPLICABLE_PUBLIC_CONTRACT_CONSTRUCT` | `COMPLIANT` | COMPLIANT, COMPLIANT, COMPLIANT | none | none; none; none | excluded: NOT_APPLICABLE_PUBLIC_CONTRACT_CONSTRUCT |
| `undeclared_public_export` | `AC_PUBLIC_API` | `NON_COMPLIANT` | `APPLICABLE` | `NON_COMPLIANT` | NON_COMPLIANT, NON_COMPLIANT, NON_COMPLIANT | UNDECLARED_PUBLIC_EXPORT | UNDECLARED_PUBLIC_EXPORT; UNDECLARED_PUBLIC_EXPORT; UNDECLARED_PUBLIC_EXPORT | included |
| `undeclared_public_export` | `AC_MODULE_GRAPH` | `COMPLIANT` | `NOT_APPLICABLE_PUBLIC_CONTRACT_CONSTRUCT` | `COMPLIANT` | COMPLIANT, COMPLIANT, COMPLIANT | none | none; none; none | excluded: NOT_APPLICABLE_PUBLIC_CONTRACT_CONSTRUCT |
| `aliased_private_service_module_import` | `AC_PUBLIC_API` | `NON_COMPLIANT` | `APPLICABLE` | `NON_COMPLIANT` | NON_COMPLIANT, NON_COMPLIANT, NON_COMPLIANT | CROSS_MODULE_IMPORT_NOT_PUBLIC | CROSS_MODULE_IMPORT_NOT_PUBLIC; CROSS_MODULE_IMPORT_NOT_PUBLIC; CROSS_MODULE_IMPORT_NOT_PUBLIC | included |
| `aliased_private_service_module_import` | `AC_MODULE_GRAPH` | `NON_COMPLIANT` | `APPLICABLE` | `NON_COMPLIANT` | NON_COMPLIANT, NON_COMPLIANT, NON_COMPLIANT | UNDECLARED_DEPENDENCY | UNDECLARED_DEPENDENCY; UNDECLARED_DEPENDENCY; UNDECLARED_DEPENDENCY | included |
| `function_local_relative_undeclared_edge` | `AC_PUBLIC_API` | `COMPLIANT` | `APPLICABLE` | `COMPLIANT` | COMPLIANT, COMPLIANT, COMPLIANT | none | none; none; none | included |
| `function_local_relative_undeclared_edge` | `AC_MODULE_GRAPH` | `NON_COMPLIANT` | `APPLICABLE` | `NON_COMPLIANT` | NON_COMPLIANT, NON_COMPLIANT, NON_COMPLIANT | UNDECLARED_DEPENDENCY | UNDECLARED_DEPENDENCY; UNDECLARED_DEPENDENCY; UNDECLARED_DEPENDENCY | included |
| `dynamic_private_module_import_boundary` | `AC_PUBLIC_API` | `NON_COMPLIANT` | `OUT_OF_SCOPE_DYNAMIC_IMPORT` | `COMPLIANT` | COMPLIANT, COMPLIANT, COMPLIANT | none | none; none; none | excluded: The architecture is NON_COMPLIANT on both obligations, but dynamic imports are outside the pinned evaluators' source-import inventory; outputs are retained as boundary observations and excluded from binary metrics. |
| `dynamic_private_module_import_boundary` | `AC_MODULE_GRAPH` | `NON_COMPLIANT` | `OUT_OF_SCOPE_DYNAMIC_IMPORT` | `COMPLIANT` | COMPLIANT, COMPLIANT, COMPLIANT | none | none; none; none | excluded: The architecture is NON_COMPLIANT on both obligations, but dynamic imports are outside the pinned evaluators' source-import inventory; outputs are retained as boundary observations and excluded from binary metrics. |
| `keyword_only_signature_break_boundary` | `AC_PUBLIC_API` | `INDETERMINATE` | `OUT_OF_SCOPE_CALL_SIGNATURE` | `COMPLIANT` | COMPLIANT, COMPLIANT, COMPLIANT | none | none; none; none | excluded: The public API configuration specifies names, interface kinds and TypedDict field names but not callable signatures; API architectural status is therefore INDETERMINATE for this sub-question. |
| `keyword_only_signature_break_boundary` | `AC_MODULE_GRAPH` | `COMPLIANT` | `APPLICABLE` | `COMPLIANT` | COMPLIANT, COMPLIANT, COMPLIANT | none | none; none; none | included |

## Descriptive evaluator time

| Evaluator | Valid completed calls | Median ms | Minimum ms | Maximum ms |
| --- | ---: | ---: | ---: | ---: |
| `AC_PUBLIC_API` | 30 | 212.824 | 206.403 | 443.724 |
| `AC_MODULE_GRAPH` | 30 | 216.526 | 209.111 | 230.298 |

Times are fresh subprocess wall durations, not application runtime, CI latency, adaptation cost, CPU or memory use. Timing repetitions are technical repeats on the same source revisions.

## Execution failures, unavailable outcomes and integrity

Runner-recorded failures: 3.

- `missing_required_public_function` / `AC_PUBLIC_API` / repeat 3: observation_validation: FINDING_CLASS_MISMATCH
- `missing_required_public_function` / `AC_PUBLIC_API` / repeat 1: observation_validation: FINDING_CLASS_MISMATCH
- `missing_required_public_function` / `AC_PUBLIC_API` / repeat 2: observation_validation: FINDING_CLASS_MISMATCH

Case-level `NOT_EVALUABLE` outcomes:

- `AC_PUBLIC_API`: none
- `AC_MODULE_GRAPH`: none

Raw archive/inventory integrity: PASS; no inventory or raw stream digest errors.

Expected CLI exit codes for `NON_COMPLIANT` and `NOT_EVALUABLE` are outcomes, not launch failures. `NOT_EVALUABLE`, unknown, unstable, missing or provenance-invalid rows are reported separately and never converted into detections.

## Post-experiment execution-status clarification

This editorial clarification was added after the experiment; the original generated report and manuscript remain unchanged inside the raw evidence ZIP. The execution command returned exit code 1 because its preregistered observation validation recorded three `FINDING_CLASS_MISMATCH` failures for `missing_required_public_function` / `AC_PUBLIC_API`, repeats 1–3. This exit status indicates an exact diagnostic-set mismatch, not an evaluator launch or execution failure: all 60 calls completed, with zero launch errors and zero parse errors. The observed `NON_COMPLIANT` classification matched the preregistered binary outcome in all three repeats.

The post-run check found zero source, evaluator, configuration, or checkout provenance failures. Analysis and evidence packaging completed; the archived analysis reports a passing raw-inventory check. A separate read-only post-experiment validation verified the archive sidecar, ZIP CRC, and all 161 internal checksums. The three mismatches remain failures against the preregistered diagnostic expectations and are not relabeled as successes.

The perfect binary classification and `F1 = 1.0` describe only the preregistered applicable finite cases. They do not imply perfect diagnostic correspondence or full architectural correctness. The dynamic-import blind spot and signature-contract boundary remain as described below.

## Threats to validity

**Internal:** all cases use one frozen A0.4 baseline; the local OS, Python runtime, filesystem and cache state may affect timing. Repeats measure invocation stability only.

**Construct:** cases are finite and author-selected. Labels follow the frozen API/edge inventory and language/source semantics; there was no external reviewer or independent human oracle. The signature case is indeterminate under the frozen contract. The dynamic-import boundary is an architecture violation outside both evaluators' direct-import scope. A static source result does not establish runtime behavior or full architecture conformance.

**External:** results apply only to the named evaluator/configuration versions, patterns and A0.4 baseline. They do not support population-level accuracy or generalization to other architectures, repositories, languages or runtime mechanisms.

## Recommendation before MONO-E1

The evaluators can be used as narrowly scoped source evidence when their exact source/configuration bindings and applicability are recorded. EVAL-02 does not justify treating them as complete architecture oracles: the dynamic-import boundary demonstrates a concrete blind spot. Further validation is necessary before using these evaluators as the sole basis for an architecture-validity claim in MONO-E1. MONO-E1 may use them as one bounded input only if the report preserves this limitation and the run has separate checks for unsupported mechanisms; this result does not change any MONO-E1 gate or authorize Method P.

## Reproduction and evidence

See [`EVAL02_PROTOCOL_V1.md`](EVAL02_PROTOCOL_V1.md). The raw archive contains exact commands and streams, case SHAs/trees, mutation patches and Git bundles, preregistration snapshots, frozen evaluator inputs, derived tables, and internal checksums. Verify the external ZIP sidecar before extraction, then run `sha256sum -c SHA256SUMS` from the extraction root.
