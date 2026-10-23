# EVAL-02 post-experiment editorial erratum

Date: 2026-10-23

This erratum clarifies execution status and diagnostic correspondence after the preregistered EVAL-02 study completed. It does not amend the preregistration, mutation catalog, runner, original observations, confusion matrices, or raw evidence archive.

## Preservation and version difference

The original generated report and Ukrainian manuscript remain unchanged inside `EVAL02_RAW_EVIDENCE_V1.zip`. Their archived member digests are:

- `EVAL02_REPORT_V1.md`: `e4c37809e8c1ed86845d82f81529a1c9b739b386ea7a3c7ccdb2de3d8c38c033`
- `EVAL02_MANUSCRIPT_UA.md`: `375d287581fa0f30ca463e0be5b0769702d256c5f66b487b606419d7bd20db5c`
- Raw ZIP sidecar: `9039e17b5b640db5641b808719c6b972a389b8f5e833ac1dc7783e658f4bf18c`

The tracked report corrects a stray hyphen in the raw-inventory `PASS` line and appends an execution-status clarification. The tracked Ukrainian manuscript appends the section titled “Редакційне уточнення після завершення експерименту.” These additions are editorial amendments; the archived generated report/manuscript bytes and their checksums are preserved as originally generated.

## Execution status

The original execution stage returned exit code 1 under its preregistered rule because it recorded three `FINDING_CLASS_MISMATCH` rows for `missing_required_public_function` / `AC_PUBLIC_API`, repeats 1, 2, and 3. Each evaluator call completed, returned the expected binary `NON_COMPLIANT` classification, and emitted both `PUBLIC_INTERFACE_MISSING` and `UNDECLARED_PUBLIC_INTERFACE`; the preregistered exact finding set contained only the former.

These are diagnostic-expectation mismatches, not evaluator launch/parse failures or source/evaluator/configuration/checkout provenance failures. All 60 calls completed; launch and parse failures were zero; source/provenance failures were zero. The analysis completed, reported raw inventory `PASS`, and retained all observations. The read-only post-run validator verifies the raw ZIP sidecar, ZIP CRC, and 161 internal checksums without invoking evaluators.

## Interpretation

The published confusion matrices and F1 values remain unchanged:

- `AC_PUBLIC_API`: TP=4, FP=0, TN=4, FN=0 across 8 applicable binary cases.
- `AC_MODULE_GRAPH`: TP=2, FP=0, TN=4, FN=0 across 6 applicable binary cases.

Technical repeats are not independent cases. F1 = 1.0 describes only binary classification over the preregistered applicable finite cases; it does not imply perfect diagnostic correspondence or full architectural correctness. The dynamic private-import blind spot, indeterminate signature-contract boundary, finite author-selected catalog, and lack of population-level inference remain unchanged. EVAL-02 neither validates Method P nor authorizes MONO-E1 execution.
