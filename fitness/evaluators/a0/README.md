# Frozen A0 architecture evaluator

This configuration is the frozen experimental evaluator for:

```text
representation_id: REP_A0_ARCH_CI_LAYERING
architecture_state: A0_MONOLITH
frozen_source_tag: arch-a0-monolith-v1
frozen_source_revision: b78b0967be937634b7762baccf5ac6892b279a73
```

It preserves the original A0 Import Linter contracts: API modules cannot depend on repositories; repositories cannot depend on API; models cannot depend on API or services; and the global package direction is `app.api -> app.services -> app.repositories -> app.models`.

Run the snapshot from the repository root with a supported Import Linter configuration option:

```bash
uv run lint-imports --config fitness/evaluators/a0/importlinter.toml
```

This file is an experimental artifact. It is intentionally not the current engineering acceptance configuration. After DA01 moves capability code, this frozen A0 evaluator may no longer pass against the current source tree; do not edit it to follow later architecture states.
