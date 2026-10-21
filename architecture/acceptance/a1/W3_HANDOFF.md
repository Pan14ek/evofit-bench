# W3 handoff — A1 source evaluator evidence contract

This W2 proposal assigns stable evaluator identities and provides an evidence format that W3 can bind to an exact representation/obligation pair after W0 freezes the A1 contracts.

| Obligation | Evaluator ID | Version | Configuration proposal |
| --- | --- | --- | --- |
| AC_PUBLIC_API | `AC_PUBLIC_API` | `1.0.0` | `public_api_v1.yaml` |
| AC_MODULE_GRAPH | `AC_MODULE_GRAPH` | `1.0.0` | `module_graph_v1.yaml` |
| AC_DATA_OWNERSHIP | `AC_DATA_OWNERSHIP` | `1.0.0` | `data_ownership_v1.yaml` |

## Readback fields

Each CLI result conforms to `evidence.schema.json` and records:

- `evaluator.id`, `evaluator.obligation_id`, `evaluator.version`, a digest over exact evaluator source files, and the exact configuration digest.
- `architecture.state`, target Git source SHA, state-manifest path/digest, expected source SHA comparison, and whether inspected subject files are dirty.
- Every discovered module identity, inspected Python path and path digest, exact AST import records (file, line, source/target module, imported symbol), and explicit scope uncertainties.
- Evaluator-specific graph/ownership observations, violations, execution status, compliance result, raw diagnostic digest, and known static-analysis limits.

`verify_evidence()` re-reads evaluator, config, and subject bytes. W3 can use those exact values in its separate sidecar/readback contract; the evaluator result itself does not establish evidence authority.

## Exact-pair boundary

This output identifies an evaluator and architecture obligation. It does **not** assert which fitness representation was used, whether that representation semantically measures the obligation, whether evidence is independently adequate, or whether an obligation is active/mandatory. W3 must bind a result to the exact `(representation_id, obligation_id, architecture_state, target_source_sha)` and independently assess evaluator-to-representation semantic adequacy. A green evaluator exit and `COMPLIANT` result are not pair-level semantic proof.

## W0 freeze needed

Before these proposals can be treated as approved architecture policy, W0 must freeze:

1. The module public entrypoint/export convention (`app.modules.<capability>.public`) and whether public symbol signatures need their own schema.
2. The allowed capability graph per intermediate/final state, including whether the event contract is a shared infrastructure node and which edges are forbidden at A1.
3. State applicability and exact source revision/manifest pins for each evaluator.
4. The table ownership matrix, accepted persistence dependency symbols, and the path-scoped `app.db.model_registry.py` exception.
5. The precise period for the Reporting → Tasks legacy query exception (proposed only for A0.2/A0.3, removed by ΔA4).

The checked-in A0.1 observation is `NOT_APPLICABLE` for these future obligations and is only source-derived diagnostic evidence.
