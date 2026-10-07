# Research schemas

These JSON Schemas define the machine-readable contracts for pre-registered scenarios, frozen ground truth, and future method results. YAML artifacts use the same data model and are validated after YAML parsing.

## Primary RQ1 classification universe

For scenario `i`, the classification universe is:

```text
U_i = existing fitness representations in Φ_t
      ∪ newly required architectural obligations in A_(t+1)
```

Existing representation targets may receive `retain`, `replace`, `deactivate`, or `adjust`. A newly required obligation may receive `add`. Criteria-level affected flags are descriptive/contextual and are not primary units for Precision, Recall, or F1. `ground_truth.schema.json` encodes targets by `target_type` and constrains operations accordingly; `result.schema.json` records predictions and applied operations against stable target IDs.

`expected_operations` is a total mapping over this complete classification universe. `affected_targets` lists the targets whose expected operation is not `retain`; `retained_representations` lists the existing representation targets whose operation is `retain`.

## Obligation and representation semantics

`required_obligations_after` means the complete active set Q(A_after), not only obligations affected by the current delta. `new_obligations` means obligations introduced by that delta and must be a subset of `required_obligations_after`. An unaffected obligation is still required and is not a removed obligation. An unaffected representation normally receives `retain`, unless its semantic validity has changed.

Obligation IDs, criteria, semantic intent, and equal default weights are defined in the canonical machine-readable [obligation registry](../../fitness/catalog/architectural-obligations.yaml). Cross-artifact references and consistency relationships are checked by the research-schema tests.

The initial Coverage calculation uses `default_weight: 1.0` for every obligation, so Coverage is the number of covered and valid required obligations divided by the complete required-obligation count.

Scenario and ground-truth artifacts are frozen before a method is run. Result files are reserved for later B0/B1/P runs and are not created as part of this schema foundation.
