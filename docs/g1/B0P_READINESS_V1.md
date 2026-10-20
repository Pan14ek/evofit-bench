# DEV-B0P-V1 readiness and execution status

**Record date:** 2026-10-20
**Primary execution:** `dev-b0p-20261020-execution-a04` — direct,
`EXECUTED_PARTIAL`.
**Transition:** A0→A0.1, `CALIBRATION_EXPOSED`.
**Author scope decision:** `docs/g1/B0P_AUTHOR_DECISIONS_V1.md`
**Protocol:** `docs/g1/B0P_DEVELOPMENT_PROTOCOL_V1.md`
**Frozen Method P source:** `984f75b11b3153c52275e223ce8ec23b8d0dd0e5`

## Execution status

| Stage | B0 | Method P |
|---|---|---|
| Arm execution | Completed once | Completed once |
| Candidate validation | `VALID` | `INVALID` |
| Prediction | Sealed, SHA-256 `124a2495b5217d1686c9ddae631980c1c314654e8b12a9c48d4fc949deef9b34` | No prediction; authentic `NOT_EMITTED_GOVERNANCE_HOLD` marker |
| Governance | Not applicable | `HOLD`, 10 reason codes |
| Execution mode | `DIRECT` | `DIRECT` |
| Method invocation reused | `false` | `false` |

a04 manifest SHA-256 is
`2b4926d12798f5504e13afeca291d3a9ca09053497f1dc475ba4d9b52d8801c1`.
No recovery or finalization was used. P's candidate validation is `INVALID`;
the governance decision is `HOLD`, and no P prediction exists.

The Import Linter process exited 1 because its configured
`app.repositories` target is missing in A0.1; evidence validity is `VALID`,
compliance is `NOT_EVALUABLE`, and semantic adequacy is `UNKNOWN`. This is
not a confirmed architectural violation. The architecture suite exited 0 with
6/6 tests passing; its suite-level process compliance is `COMPLIANT`, while
semantic adequacy stays `UNKNOWN`.

## Research readiness and claim limits

- RQ1: `NOT_EVALUABLE`; no presealed exact-target reference; scorer not run.
- RQ2: `UNKNOWN`; no complete target-bound denominator or independent
  exact-pair proof; no coverage percentage.
- Twelve P pair diagnostics remain `UNKNOWN`; zero independently verified.
- G1: `INCOMPLETE`.
- G4: `NOT AUTHORIZED`.
- `P_ALGORITHM_STATUS`: `NOT_READY`.
- Method P remains frozen; original B0 remains unchanged.
- A0→A0.1 remains `CALIBRATION_EXPOSED`; this is not a holdout or
  independent validation.
- No B1 arm, human operator, significance test, resource-sampling result, or
  generalized effectiveness claim.

## Preserved attempt history

- `preflight-a01`: unchanged verified preparation, still
  `PREPARED_NOT_EXECUTED`.
- `execution-a01`: stopped before either arm during runtime-context assembly.
- `execution-a02`: both arms and initial evaluators completed; manifest
  construction failed with `KeyError: 'candidate_validation'`. Append-only
  finalization reused persisted arm outputs and reran evaluator commands.
  Historical mode remains `POST_EXECUTION_FINALIZATION`.
- `execution-a03`: both arms ran in direct mode, but the evaluator host lacked
  the required development packages. The attempt was preserved without
  recovery and is not the primary result.
- `execution-a04`: new direct run with evaluator dependencies available;
  both arms and fresh evaluator records completed, and the execution verifier
  passed.

The regression test now follows both isolated-arm results through
`_make_execution_manifest()` and checks the B0/P candidate-validation fields.
The original a02 failure and its evidence remain unchanged.

## Evidence identities and reproduction

- Preparation manifest:
  `d6d55437fcc30c4e8bdd5acb37fd9f881be74f646989e701b03092ba8ac82b2f`
- a04 execution manifest:
  `2b4926d12798f5504e13afeca291d3a9ca09053497f1dc475ba4d9b52d8801c1`
- a04 ZIP:
  `experiments/results/dev-b0p-20261020-execution-a04.zip`
- ZIP SHA-256:
  `13f81c4f74e3cbbf857da204ecff3c22c6f86a87f4c0e0ee4c782983d416cc64`
- Clean extraction: all 355 checksum rows passed; independent verifier:
  `verified=true`, `EXECUTED_PARTIAL`, 357 manifest artifacts.
- Downloadable ZIP and plain-text SHA-256 sidecar are linked in the PR #24
  evidence comment; neither archive is committed to Git.

Focused verification:

```bash
UV_PROJECT_ENVIRONMENT=/private/tmp/b0p-venv UV_CACHE_DIR=/private/tmp/b0p-uv-cache \
/private/tmp/b0p-venv/bin/python -m pytest --no-cov -q -p no:cacheprovider \
  tests/unit/test_b0p_development.py \
  tests/unit/test_b0p_git_inventory.py \
  tests/unit/test_b0p_execution.py
# 40 passed
```

The final local `make development-quality` run passed: 414 DEVELOPMENT tests,
49 EXP-01 tests, and 30 EXP-02 tests, plus lint, type, security, architecture,
and migration checks. The aggregate target excludes
`tests/unit/test_da01_execution.py` and
`tests/unit/test_research_schema_foundation.py`; neither is counted as passed.
Hosted CI is checked separately on the final pushed revision and pending
checks are not considered passes.

## Subsequent independent evaluation

Select and custody a new transition and target-bound reference before
inspecting predictions. Establish an authorized complete obligation
denominator, evaluator positive/negative controls, independent exact-pair
semantic proof, and predeclared scoring and resource sampling. Obtain the
required approvals before any canonical DA01 claim. These requirements are
unchanged by the current DEVELOPMENT execution.
