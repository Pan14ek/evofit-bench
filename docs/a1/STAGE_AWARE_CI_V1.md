# W0 — Stage-aware architecture CI v1 (DEVELOPMENT)

**Status:** implemented CI orchestration, not a scientific authorization.
**Historical source:** `A0_1_CAPABILITY_MODULES` at Git SHA `3fdd5c68f8f60fad5757eefa66cc2aa8b24d9306`, app tree `cdff9a6c3cee870e1eca2a5f5f3eb3202b0b1f08`.
**Current integration base:** `b003144ae78238707af555aee68a16ffa14e800b` (W1 ΔA2 and W2 source evaluators are integrated on `main`).

## Why we need this

The *unchanged* `tests/architecture/test_module_structure.py` is the frozen exact DA01 **A0.1** acceptance, not an evolving A1 module inventory. It must fail if run on W1's ΔA2 checkout containing additional `public.py` files. Running it on current ΔA2 source is a protocol mismatch. Removing assertions or adapting A0.1 manifest/source to make it pass would falsify the historical architecture description.

The new `scripts/check_architecture_stages.py` keeps two independent checks and their results visible:

1. **HISTORICAL_A01:** verifies exact commit/tree, uses `git archive` to materialize the pinned app, original A0.1 architecture manifest, original exact structure and layer tests, and the historical pyproject configuration into an isolated temporary checkout. Runs the original six pytest cases there. No current app/tests, oracle or scorer files are included. The historical acceptance cannot be made to pass by weakening current tests.
2. **CURRENT:** checks the actual clean Git worktree with stage-appropriate tests. Auto-detection recognizes exact `A0_1_CAPABILITY_MODULES` or `A0_2_PUBLIC_MODULE_APIS` (all five capability public modules plus the W1 public-contract tests). A partial module tree, partial public API set, missing W1 contract tests, missing W2 evaluator tests, unexpected pre-A0.2 app changes or dirty source fails closed. A0.1 mode demands the original app tree digest. The W4 event-preparation code is additive to the actual A0.2 base and runs under the A0.2 profile; it does not define an architecture state. Current A0.2 checks execute current layer tests, W1 public API tests and the integrated W2 evaluator fixture suite. Development regression separately runs W4 event unit and PostgreSQL preparation tests.

```bash
uv sync --frozen --extra dev
make architecture-test
make development-quality

# Explicitly assert the expected development source stage:
make architecture-test ARCHITECTURE_STAGE=A0_2_PUBLIC_MODULE_APIS
```

The existing `lint-imports --config architecture/acceptance/importlinter.toml` still runs in `architecture-test` against current source. That configuration only covers current module-local layering; it is **not** an AC_PUBLIC_API governance proof. The frozen B0 research Import Linter is not changed or silently substituted.

## What PASS means — and does not mean

| Check | Meaning | Not established |
| --- | --- | --- |
| Historical A0.1 six cases PASS | Original exact DA01 acceptance still passes on exact pinned history | Today's new architecture also matches A0.1 |
| Current A0.1 PASS | Current app tree matches original A0.1 and its tests pass | Independent P adaptation result |
| Current A0.2 PASS | W1's five facades, public-contract tests, current layer tests and W2 evaluator fixture suite pass | Final A1 Task→Notifications removal, ΔA3–ΔA6 integration, live source-bound architecture evidence or human semantic proof |

**Do not interpret a green developmental PR CI as final `G-A1-C2`, `G-A1-C6` or `G-A1-R` approval.** Full stage gates additionally require independently inspected source-bound W2 evaluator execution, integration tests and appropriate post-merge SHA/reference freezes.

The system intentionally **does not auto-claim A0.3/A0.4/A0.5/A1** merely because public interfaces exist. W0 must extend the profile and bind each future stage to a verified state manifest and exact source SHA before those stages are promoted. This is an explicit next integration boundary, not a claim that this v1 already implements all future state profiles.

## Verification and negative cases

New unit cases in `tests/unit/test_architecture_stage_checks.py` cover:

- exact initial-stage detection;
- missing and partial source inventories;
- missing contract tests;
- invalid historical pin or altered historical app tree;
- stage assertion mismatch;
- claimed A0.1 against nonhistorical current app tree;
- dirty source refusing SHA-bound PASS;
- A0.2 correct focused test selection;
- pre-A0.2 app changes are rejected rather than assigned a temporary W4 architecture state;
- W2 evaluator tests are required for the current A0.2 profile and included in its focused test selection.

Historical `tests/architecture/test_module_structure.py`, `tests/architecture/test_layer_rules.py`, `architecture/states/A0_1_CAPABILITY_MODULES.yaml`, frozen evaluators, historical raw evidence and Method P source stay unchanged. The workflow retains lint/type/security/migration/development regression separately; missing runtime authority, source-to-image identity and G1/G4 are unaffected.

## Integration order

1. `main` now contains W1 ΔA2 and W2's source evaluators at the integration SHA above; current A0.2 checks include the W2 fixture suite.
2. Keep W4 event preparation on that A0.2 profile. Do not add a temporary architecture state for a feature-preparation branch.
3. W0 coordinates ΔA3–ΔA5 and separately authorizes the later ΔA6 Task-service/composition-root integration; preserve the existing historical tests.
4. Later controlled architecture states require their own explicit profiles/state manifests and independent experiment freeze checkpoints.

The stages are research treatments for fitness-adaptation evaluation; no superiority of modular monoliths is implied.
