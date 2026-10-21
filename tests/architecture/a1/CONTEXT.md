# Context — `tests/architecture/a1`

> **Audience:** human developers and AI coding agents. **Type:** maintained test context; fixtures are synthetic engineering checks, not research predictions or oracle labels.

## Responsibility

Exercise W2's proposed A1 architecture evaluators with fixed, source-level valid and adversarial Python fixtures.

## Local landmarks

- `test_evaluators.py` — public/private imports, the intermediate Reporting exception, source-derived graph edges and cycles, shared infrastructure, module/data ownership, incomplete scope, revision mismatch, digest readback, and schema validation.
- `REQUIREMENT_TEST_MATRIX.md` — requirement-to-test traceability and exact acceptance boundaries.

## Established conventions

Tests create a disposable Git fixture repository, pin its commit SHA, run the same standalone evaluator functions as the CLI, and inspect exact imported paths/lines and structured output. A source fixture pass proves only that the evaluator detects its controlled source elements.

## Constraints and known gaps

These TEST_ONLY fixtures are not A1 application-state implementations, DA01 evidence, P predictions, or measurements. Keep them separate from `tests/architecture/test_module_structure.py` and `tests/architecture/test_layer_rules.py`, which are historical A0.1 architecture checks. Do not use oracle/scorer data or edit frozen expected results.

## Verification

```bash
uv run pytest --no-cov -p no:cacheprovider tests/architecture/a1
```
