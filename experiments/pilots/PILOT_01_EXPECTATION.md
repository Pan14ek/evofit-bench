# PILOT-01 — expected evaluator outcomes

**Recorded:** 2026-10-19 UTC, before the formal repeated workload and EXP-01/02 runs.
**Base source:** `5d285a04da00863088f8cd88a10afb3faaf02ddb`.
**Scope:** one source dependency edge in S1; the existing evaluator configuration and A0.1 fitness configuration remain byte-identical.

## Predeclared expectations

- **S0:** all five existing Import Linter contracts are kept, with zero broken contracts and exit code 0. The existing architecture tests and the module-structure check pass.
- **S1:** one import from `app.modules.notifications.repository` to `app.modules.notifications.api` violates the existing `Notifications module internal layering` contract. Expect one broken contract and a nonzero Import Linter exit. The existing `test_layer_rules.py` notification case fails; the independent module-structure test passes because the injected edge does not change the manifest or required files.
- The S1 code change is isolated in source commit `ccbfb002e1fc71d9dcaadf11635d449b8a881cac`, parented directly on the stated base. No evaluator, fitness configuration, Import Linter contract, or application API is changed.

## Exploratory probe disclosure

Before this expectation record, an isolated feasibility probe ran the unchanged Import Linter and architecture tests against the S1 commit to confirm the selected injection was detectable. Those outputs are excluded from the formal repeated-run dataset. The expectations above were derived from the unchanged layer order and source diff; all formal S0/S1 workload and evidence runs begin after this record.
