# A0 fitness configuration

`configs/a0-monolith.yaml` defines the initial research configuration Φ₀ for performance, reliability, and architecture compliance. Reliability evidence is the integration-test result, business HTTP 5xx rate, and `business_operation_failures_total`. Expected business-rule rejections are separately recorded and are not service reliability failures by default. `notifications_created_total` counts committed notification rows only. Runtime metrics and test outputs are evidence, not automatic judgments. This baseline contains no mechanism that adapts or optimizes the configuration.

The A0 Import Linter snapshot at `evaluators/a0/importlinter.toml` is the frozen experimental evaluator for `REP_A0_ARCH_CI_LAYERING`. Current implementation guardrails live separately in `architecture/acceptance/importlinter.toml`; those engineering checks are not method results and must not be copied into future B0/B1/P result records.
