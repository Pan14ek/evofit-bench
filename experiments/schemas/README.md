# Research schemas

These JSON Schemas define the machine-readable contracts for pre-registered scenarios, frozen ground truth, and future method results. YAML artifacts use the same data model and are validated after YAML parsing.

## Primary RQ1 classification universe

For scenario `i`, the classification universe is:

```text
U_i = existing fitness representations in Φ_t
      ∪ newly required architectural obligations in A_(t+1)
```

Existing representation targets may receive `retain`, `replace`, `deactivate`, or `adjust`. A newly required obligation may receive `add`. Criteria-level affected flags are descriptive/contextual and are not primary units for Precision, Recall, or F1. `ground_truth.schema.json` encodes targets by `target_type` and constrains operations accordingly; `result.schema.json` records predictions and applied operations against stable target IDs.

Scenario and ground-truth artifacts are frozen before a method is run. Result files are reserved for later B0/B1/P runs and are not created as part of this schema foundation.
