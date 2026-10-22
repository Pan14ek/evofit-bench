# Context — `tests/architecture/a1`

> **Audience:** human developers and AI coding agents. **Type:** maintained test context; fixtures are synthetic engineering checks for W0-approved policy, not research predictions or oracle labels.

## Responsibility

Exercise W2's A1 architecture evaluators and W0-approved policy configurations with fixed, source-level valid and adversarial Python fixtures.

## Local landmarks

- `test_evaluators.py` — public/private imports, the A0.2/A0.3 Reporting exception, A0.4 public query acceptance/private query rejection, final Tasks → Notifications prohibition, `app.events` shared infrastructure, exact model-registry exception, source-derived graph edges and cycles, module/data ownership, incomplete scope, revision mismatch, portable manifest readback after subject/evidence relocation, evaluator/config/source/raw-output digest readback, and exact-byte ΔA3/ΔA4 candidate and canonical checkpoint validation.
- `REQUIREMENT_TEST_MATRIX.md` — W2 evaluator requirements plus ΔA3 and canonical ΔA4 checkpoint stage/governance requirement-to-test traceability.

## Established conventions

Tests create a disposable Git fixture repository, pin its commit SHA, run the same standalone evaluator functions as the CLI, and inspect exact imported paths/lines and structured output. A source fixture pass proves only that the evaluator detects its controlled source elements.

## Constraints and known gaps

These TEST_ONLY fixtures are not A1 application-state implementations, DA01 evidence, P predictions, or measurements. Keep them separate from `tests/architecture/test_module_structure.py` and `tests/architecture/test_layer_rules.py`, which are historical A0.1 architecture checks. Do not use oracle/scorer data or edit frozen expected results. The ΔA3 and ΔA4 stage gates separately run both source evaluators against their clean candidate checkouts; canonical evidence readback uses each checkpoint's pinned historical source and evaluator/configuration bytes.

## Verification

```bash
uv run pytest --no-cov -p no:cacheprovider tests/architecture/a1
```
