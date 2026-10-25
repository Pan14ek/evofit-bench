# A0.3→A0.4 Ψ evidence implementation: requirement-to-test matrix

This matrix traces the bounded DEVELOPMENT implementation. Passing checks establish software behavior and artifact readback only. They do not approve the reconstructed B0, establish independent semantic adequacy, freeze a reference, authorize measurement, or advance G1/G4.

| ID | Implementation requirement | Primary evidence | Regression coverage |
|---|---|---|---|
| PSI-E01 | Pin the A0.3/A0.4 commits, trees, and state manifests. | `mono_ci_psi_transition.py::_verify_transition_sources`, `_source_binding`, `_verify_transition_state_sidecar` | `test_mono_ci_psi_transition.py::test_real_transition_executes_psi_and_archive_round_trips` |
| PSI-E02 | Execute both configured evaluators as fresh processes against clean exact-revision source worktrees; record exit, stdout, stderr, timing, source and config digests. | `mono_ci_psi_evidence.py::run_fresh_evaluator`; `mono_ci_psi_transition.py::_collect_evaluator_matrix` | `test_mono_ci_psi_transition.py::test_real_transition_executes_psi_and_archive_round_trips` |
| PSI-E03 | Bind evaluator implementation and configuration bytes to the recorded observations. | `evaluator_source_artifacts`, `_evaluator_artifact_references`, `_verify_evaluator_observation` | `test_mono_ci_psi_evidence.py::test_evaluator_source_manifest_is_canonical_and_digest_bound`; transition round-trip test |
| PSI-E04 | Supply only A0.4 observations to adaptation; preserve A0.3 runs as source-bound context. | `run_transition` selection of `after_runs`; `_verify_evidence_backed_run` | Transition round-trip test checks the four-row matrix and test-only sidecar |
| PSI-E05 | Bind the evidence sidecar to the exact V3 bundle and source digests under an explicitly TEST_ONLY verifier. | `create_test_only_sidecar`; `TestOnlyHmacVerifier`; `_verify_evidence_backed_run` | `test_mono_ci_psi_evidence.py::test_test_only_verifier_checks_hmac_and_rejects_unregistered_authority`; `test_test_only_verifier_rejects_short_keys`; transition tamper test |
| PSI-E06 | Keep semantic compatibility unknown and adequacy unproven; do not infer normative mapping from evaluator compliance. | `adapt_evaluator_evidence`; undetermined exact-pair proofs in `run_transition` | `test_mono_ci_psi_evidence.py::test_adapter_preserves_semantic_and_adequacy_unknowns`; transition sidecar readback |
| PSI-E07 | Recompute only the four module inventory facts from digest-pinned, sorted unique source path records; leave policy and completeness proofs unverified. | `build_source_inventory_fact_ledger` | `test_source_inventory_paths_are_sorted_unique_app_modules`; transition round-trip test verifies the exact four fact IDs and unverified-proof flags |
| PSI-E08 | Isolate P execution from network, source repositories, and other evaluator observations; fail closed when OS isolation is unavailable. | `mono_ci_psi_transition.py::_execute_isolated_method` | `test_mono_ci_psi_transition.py::test_real_transition_executes_psi_and_archive_round_trips`; hosted workflow installs bubblewrap and runs the full integration path |
| PSI-E09 | Validate result decision shape without assuming a specific outcome: ACCEPT requires prediction and candidate; HOLD/REJECT require neither. | `_validate_method_result_v2`; V2 run schema | `test_v2_method_result_allows_each_decision_with_bounded_prediction_shape`; transition round-trip test checks the returned decision and associated output shape |
| PSI-E10 | Preserve NO_GO, NOT_EXECUTED, P NOT_READY, G1 incomplete, G4 unauthorized, reference gate NOT_READY, and no scoring or other-arm outputs. | V2 run/archive schemas; `verify_transition_run` | Transition round-trip and contract promotion rejection tests |
| PSI-E11 | Package, extract and independently read back the run archive while preserving V1 archive readback. | `mono_ci_b0_psi_archive.py::pack_psi_transition_archive`, `verify_psi_transition_archive` | Transition round-trip test; hosted archive verify step |

## Verification entry points

- `make test-mono-ci-b0-psi-execution`
- `make test-mono-ci-psi-transition`
- `make development-quality`
- `.github/workflows/mono-ci-psi-transition-development.yml` runs the fresh isolated execution, archive packaging, and archive readback on hosted Linux.
