# C2 V1 requirement traceability

This map links the bounded TEST_ONLY condition to its contract checks and retained run evidence. It is not an approval record or a scientific gate.

| Requirement | Contract or implementation | Verification |
|---|---|---|
| C2 scope selects only ownership ADD plus the two evidence-backed retain controls; all other applicability stays UNKNOWN. | `inputs/POSITIVE_ADD_C2_PROFILE_V1.json`; `mono_ci_psi_positive_add_c2_profile_v1.schema.json`; `create_policy_source`. | `test_c2_profile_and_protocol_are_versioned_and_fail_closed`; `test_c2_policy_input_has_only_three_scoped_active_obligations`; each V6 archive's scoped-policy readback. |
| Retain source, evaluator, and configuration identities match the recovered C1 observations and current pinned evaluator sources. | Profile's exact-pair bindings; `_validate_static_profile`; `prepare_method_inputs`; pre-run freeze. | `test_c2_retain_profile_rejects_changed_configuration_binding`; C1 archive readback; C2 freeze and per-run evidence verification. |
| C1 method-input and run-record contracts remain readable. | Additive C2 capability key and V6 transition schema; C1 remains on V1/V5 profile and run schemas. | `test_c2_method_runtime_keeps_c1_profile_capability_backward_compatible`; readback of all four original C1 transition archives. |
| One warmup and three measured transitions use the pinned network-isolated Method Ψ runtime without changing its algorithm. | `PROTOCOL_C2_V1.json`; C2 freeze; digest-pinned Docker adapter; result schema. | C2 workflow preflight and result readback; `C2_RESULTS.json` archive list and SHA-256 inventory. |
| Record the actual ADD/RETAIN plan, governance reasons, candidate validation, acceptance, application status, B0/candidate clean and negative outcomes, incremental evaluator cost, Ψ time, and transition time. | C2 runner summary; `mono_ci_psi_positive_add_c2_results_v1.schema.json`. | Per-run summaries are reconstructed from raw V6 archives and compared during `verify_results`. |
| Preserve official readiness and authorization boundaries. | Protocol, profile, freeze, V6 transition, and results contracts all pin `NO_GO`, `NOT_READY`, G1 `INCOMPLETE`, and G4 `NOT_AUTHORIZED`. | Focused C2 tests; hosted `make development-quality`; verified raw archive manifests. |

Focused unit checks are run with `make test-mono-ci-psi-a05-positive-add-c2`. The hosted C2 workflow additionally runs `make test-mono-ci-psi-a05` and `make development-quality` before the Docker-isolated experiment.
