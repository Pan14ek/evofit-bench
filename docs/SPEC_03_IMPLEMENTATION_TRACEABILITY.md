# SPEC 03 implementation traceability and validation report

**Specification status:** PR #8 is merged, but
[`SPEC_03_IMPACT_ANALYSIS_AND_GOVERNED_ADAPTATION.md`](SPEC_03_IMPACT_ANALYSIS_AND_GOVERNED_ADAPTATION.md)
still identifies itself as a draft/proposed development specification.
**Implementation:** branch `codex/spec03-governed-adaptation`, based on main
`248e09621b2c8efd7c1db8f24cb1b79cedced69c` (2026-10-16). **This report does
not claim measured readiness or scientific validation.**

## Initial implementation plan and module mapping

| SPEC 03 area | Existing contract/module reused | New implementation |
| --- | --- | --- |
| Versioned SPEC 01/02 preflight | V3 `verify_method_bundle_v3`, SPEC 01 Snapshot validation, SPEC 02 `evaluate_obligations()` | `experiments/execution/tooling/p_adaptation.py` |
| Fact/policy/obligation deltas, typed trace graph and conservative impact | V1.1 Snapshot and A0 traceability projections | `p_impact.py` |
| Exact pair semantics and mandatory coverage | Existing evidence proof and applicability contracts | `p_semantic.py` |
| `retain / replace / add / deactivate / adjust` | SPEC 02 applicability results; no second activation engine | `p_operations.py` |
| Candidate materialization, version identity and legacy adapters | Frozen V1 candidate/prediction validators | `p_candidate.py` |
| Governance, append-only provenance, conditional publish and rollback | Existing hash and strict-schema utilities | `p_governance.py` |
| Development contracts | Frozen schemas remain unchanged | Nine additive `p_*_v1` JSON Schemas |

## Fixture provenance and hashes

SPEC 03 scenarios use independently authored generic identifiers and
`TEST_ONLY` trust labels. The tests do not derive expected operations from a
DA01 scenario, ground truth, scorer or sealed output. Fixture hashes are
SHA-256. Where test inputs are built inline, the hash identifies the test source
that defines the builder and assertions.

| Fixture/source ID | Path | SHA-256 |
| --- | --- | --- |
| P03-GENERIC | `tests/fixtures/p_method/generic_architecture_evolution_v1.json` | `4a1b63cc08c219d40d6298d8ecd5f6d64208952afd87f5bede39f99002ffe194` |
| P03-BUILDER | `tests/unit/p_spec03_support.py` | `fabedf83695ddaff92af17c23ded9ab872fc8de30d6a376d78af271c6cad7554` |
| P03-IMPACT | `tests/unit/test_p_impact_v1.py` | `87db3af4d76bec0936655550f400635c59612194c9de9f77a32e4a0c4990fea6` |
| P03-PAIR | `tests/unit/test_p_semantic_pairs_v1.py` | `c060e9cc71b1a12d11e93f79a987d14fe0a4b510b8b879945aed62748f36ac5a` |
| P03-OPS | `tests/unit/test_p_operations_v1.py` | `284a9ec32ed121eb77069648dfa1b1d0f9f2e6c39b72bd3f358996bbd20ed0bc` |
| P03-CANDIDATE | `tests/unit/test_p_candidate_governance_v1.py` | `0ccc8f1d13ad0c924d26a0cc2013a9d171deb806a799487f9f80a681ac818b87` |
| P03-E2E | `tests/integration/test_p_governed_adaptation_v1.py` | `c10ae1b68d9f87efe0696b86c608b0650f6cd87e03a58bc01c5b435ccd481b8c` |
| P03-V3-VERIFY | `tests/integration/test_p_applicability_v3.py` | `8f81731a6190913199a5f46b21b5eb4f35cc63829832d3e06456672970b3ef34` |
| SPEC01-SNAPSHOT | `tests/fixtures/p_input_contract_v11_snapshot.json` | `c32ca2e72a451820d72193f18d1ca0ef2c546e739e8004ddf290e41f97fd677f` |
| SPEC01-TESTS | `tests/unit/test_p_input_contract_v11.py` | `b4d8f0f6aa3d7b4b07870f7bc623709d89c5afd4452a6246ded2f121d047cc33` |
| AUTHORITY-TESTS | `tests/unit/test_p_input_authority_validation.py` | `8eb732b91632cb69aba85f9335b2fbc12cc7e53680a3d5091a49dd504e2e9dde` |
| V2-TESTS | `tests/unit/test_p_input_v2_isolation.py` | `d71334c9f29a8e66bec042db080543a7ae7d16836bc91ab7954ff4ec75b32fd1` |
| DSL-TESTS | `tests/unit/test_p_applicability_ruleset_v1.py` | `9d7348e2763d530c7e90040ed9111078937874da85722eeb28543e44e3b5c920` |
| POLICY-TESTS | `tests/unit/test_p_applicability_policies_v1.py` | `dbd48f413f996b32995737aed9b8a2b156ca942772def02c43e9f24a59a3118d` |
| V3-TESTS | `tests/integration/test_p_applicability_v3.py` | `4193677efe854a452cf41b0674ab2f2773b31ba56b274ef23e13fd00564b249e` |
| ISOLATION-TESTS | `tests/unit/test_da01_inputs_and_isolation.py` | `1c25eed5c958d6e579d6f940edef22e690b86172f07572f381de0fa0f6c2a449` |

## Requirement registry status

`PASS` means the listed contract/tests passed in the local run below. `BLOCKED`
means the implementation path remains conservative but a required independent
positive-path prerequisite or a prohibited frozen-artifact check was not
exercised. `E01` is not authorized by SPEC 03.

| Requirement | Outcome | Evidence / limitation |
| --- | --- | --- |
| C01–C03 | PASS | SPEC 01 schema, trust, V2 isolation and legacy adapter tests; see TT-C rows. |
| A01–A06 | PASS | SPEC 02 DSL, authority, three-state, stale-validation and V3 parity/pipeline tests; see TT-A rows. |
| S01 | PASS | Synthetic method-input isolation suite, including the digest-pinned Docker negative probe. |
| P03-01 | BLOCKED | Caller-constructed V3 claims are rejected, verifier-returned object identities bind all bundle content, and TEST_ONLY remains HOLD. The positive production verifier path is still not exercised with approved V3 authority. |
| P03-02–P03-12 | PASS | Typed diffs, graph, exact-pair semantics, coverage, operations, materialization, governance, provenance and rollback tests. |
| P03-13 | BLOCKED | V1/V2/V3 compatibility and B1/P parity tests pass; no frozen experimental output was re-exported or byte-compared. The branch changes no protected artifact paths. |
| P03-14 | BLOCKED | Synthetic end-to-end OPEN-authority path correctly returns HOLD. A fully approved positive V3 P run is unavailable and was not fabricated. |
| E01 | BLOCKED / NOT AUTHORIZED | No G1/G4 approval, measured B0/B1/P run, human B1 result or independent study evidence. |

The 60 TTM rows resolve to **56 PASS and 4 BLOCKED**. The 25-item requirement
registry has 21 engineering requirements PASS, P03-01/P03-13/P03-14 BLOCKED,
and E01 BLOCKED/NOT AUTHORIZED.

## Test Traceability Matrix — SPEC 01/02 regression rows

| Test ID | Requirement | Test entry point | Outcome |
| --- | --- | --- | --- |
| TT-C01-01 | C01 | `test_p_input_contract_v11.py::test_canonical_synthetic_snapshot_passes_schema_with_format_checker`; malformed schema/type/hash cases in the same file | PASS |
| TT-C01-02 | C01,C03 | `test_p_input_v2_isolation.py::test_v2_verifier_rejects_symlink_source_even_with_matching_hash`, `test_v2_verifier_rejects_fact_tampering_after_rehash`; V1 exporter checks in `test_da01_inputs_and_isolation.py` | PASS |
| TT-C02-01 | C02 | `test_p_input_authority_validation.py::test_open_registry_and_untrusted_approval_remain_undetermined`, `test_draft_policy_is_not_treated_as_normatively_valid` | PASS |
| TT-C02-02 | C02 | `test_p_input_authority_validation.py::test_completeness_claim_revision_or_registry_version_mismatch_is_invalid`, `test_completeness_verifier_has_separate_bounded_verdict` | PASS |
| TT-A01-01 | A01 | `test_p_applicability_ruleset_v1.py::test_strong_kleene_tables_are_complete_and_commutative`, `test_assessment_digest_ignores_fact_order_and_paths_are_not_emitted` | PASS |
| TT-A01-02 | A01 | `test_p_applicability_ruleset_v1.py::test_ruleset_rejects_unknown_fields_operator_reserved_predicates_and_bad_types`, `test_ruleset_rejects_bool_numeric_literal_and_ast_resource_overflow` | PASS |
| TT-A02-01 | A02 | `test_p_applicability_policies_v1.py::test_verified_unconditional_mandate_is_active_and_report_has_all_18_rows`, `test_open_registry_and_missing_policy_proof_remain_unknown` | PASS |
| TT-A03-01 | A03 | `test_p_applicability_policies_v1.py::test_opposite_polarity_policies_conflict_without_precedence_and_resolve_with_proof`, `test_unknown_condition_and_expired_or_revoked_policy_do_not_create_active` | PASS |
| TT-A04-01 | A04 | `test_p_applicability_policies_v1.py::test_successful_validation_cannot_be_reused_for_another_snapshot`, `test_p_applicability_v3.py::test_v3_spec01_evidence_ledger_and_applicability_pipeline` | PASS |
| TT-A05-01 | A05,C03 | `test_p_applicability_v3.py::test_policy_revision_changes_without_changing_pinned_architecture`, `test_b1_and_p_receive_identical_policy_and_common_snapshot` | PASS |
| TT-A06-01 | A06 | `test_p_applicability_v3.py::test_v3_spec01_evidence_ledger_and_applicability_pipeline` | PASS |
| TT-S01-01 | S01 | `test_da01_inputs_and_isolation.py::test_container_negative_probes_cannot_reach_oracle_history_network_or_other_output`; synthetic exporter allowlist and bundle tests | PASS |

## Test Traceability Matrix — SPEC 03 rows

| Test ID | Requirement | Test entry point | Outcome |
| --- | --- | --- | --- |
| TT-P03-01 | P03-01 | `test_p_governed_adaptation_v1.py::test_synthetic_pipeline_runs_spec02_and_holds_open_authority_unknown` | BLOCKED — direct test bundle, not a fully verified V3 P export |
| TT-P03-02 | P03-01 | `test_preflight_rejects_snapshot_validation_from_another_exact_revision`, `test_preflight_rejects_policy_and_ruleset_digest_substitution`, `test_caller_cannot_claim_verified_v3_without_verifier_identity`, `test_p_applicability_v3.py::test_v3_verifier_binds_nested_bundle_content_before_adaptation` | PASS — direct claims rejected and nested mutation detected after strict verification; no positive authorized V3 path |
| TT-P03-03 | P03-01,S01 | `test_p_applicability_v3.py::test_policy_source_rejects_answer_markers_and_unallowlisted_files`; V2 path/symlink and method isolation tests | PASS |
| TT-P03-04 | P03-02 | `test_p_impact_v1.py::test_typed_fact_diff_preserves_values_scope_and_source_versions`, `test_fact_scope_shift_is_not_reported_as_removal_plus_addition` | PASS |
| TT-P03-05 | P03-02 | `test_policy_only_change_is_detected_with_identical_architecture_revision` | PASS |
| TT-P03-06 | P03-02 | `test_missing_fact_is_indeterminate_until_exact_scoped_completeness`, `test_policy_addition_requires_proven_prior_inventory_completeness`, `test_policy_duplicate_identity_is_indeterminate_not_last_write_wins` | PASS |
| TT-P03-07 | P03-02,P03-12 | `test_input_permutations_preserve_graph_and_impact_digests` | PASS |
| TT-P03-08 | P03-03 | `test_trace_graph_keeps_typed_reachability_and_source_path` | PASS |
| TT-P03-09 | P03-03 | `test_dangling_duplicate_and_mistyped_edges_remain_unresolved`, `test_incomplete_graph_cannot_prove_no_impact_and_active_q_is_still_found` | PASS |
| TT-P03-10 | P03-04 | `test_unknown_fact_change_yields_possible_not_proven_impact`, `test_irrelevant_isolated_component_does_not_change_existing_impact` | PASS |
| TT-P03-11 | P03-04 | `test_incomplete_graph_cannot_prove_no_impact_and_active_q_is_still_found` | PASS |
| TT-P03-12 | P03-04,P03-12 | `test_irrelevant_isolated_component_does_not_change_existing_impact`, `test_input_permutations_preserve_graph_and_impact_digests` | PASS |
| TT-P03-13 | P03-05 | `test_positive_exact_pair_requires_artifact_and_external_semantic_proof` | PASS — synthetic proof only |
| TT-P03-14 | P03-05 | `test_zero_exit_without_resolved_inspected_subjects_is_vacuous` | PASS |
| TT-P03-15 | P03-05 | `test_wrong_stage_architecture_or_mapping_never_reuses_pair_proof`, `test_wrong_obligation_identity_cannot_borrow_same_metric_evidence` | PASS |
| TT-P03-16 | P03-05 | `test_clean_nonzero_exit_records_noncompliance_without_invalidating_monitor_semantics`, `test_evaluator_infrastructure_failure_is_unknown_and_not_a_compliance_verdict` | PASS |
| TT-P03-17 | P03-05 | `test_wrong_obligation_identity_cannot_borrow_same_metric_evidence`, exact-pair proof subject/hash assertions | PASS |
| TT-P03-18 | P03-06 | `test_same_valid_pair_counts_once_and_unknown_mandate_blocks_coverage`, `test_stale_pair_architecture_revision_cannot_satisfy_coverage`, `test_conflicting_assessments_for_same_pair_cannot_count_as_valid`, `test_same_status_pair_records_with_different_stages_are_conflicting`, `test_mutated_pair_status_with_stale_digest_cannot_count_as_valid` | PASS — stale, conflicting and digest-tampered records stay unresolved |
| TT-P03-19 | P03-06 | `test_high_score_or_covers_declaration_cannot_replace_exact_pair_evidence` | PASS |
| TT-P03-20 | P03-06 | `test_same_valid_pair_counts_once_and_unknown_mandate_blocks_coverage`, `test_required_stage_set_needs_independent_stage_contract` | PASS |
| TT-P03-21 | P03-07 | `test_valid_unaffected_configuration_is_retained` | PASS |
| TT-P03-22 | P03-07,P03-08 | `test_invalid_representation_replacement_covers_all_its_live_mandatory_links` | PASS — hashed TEST_ONLY template, not an authorized production evaluator |
| TT-P03-23 | P03-07,P03-08 | `test_active_uncovered_obligation_adds_only_a_real_hash_bound_test_template` | PASS — hashed TEST_ONLY template |
| TT-P03-24 | P03-07 | `test_shared_representation_stays_active_when_one_q_is_inactive_but_another_is_active` | PASS |
| TT-P03-25 | P03-07 | `test_unknown_mandatory_applicability_never_authorizes_deactivation`, `test_deactivation_requires_all_linked_controls_verified_inactive` | PASS |
| TT-P03-26 | P03-07,P03-09 | `test_candidate_rejects_duplicate_operation_targets_and_tampered_plan_digest`, `test_candidate_rejects_stale_parent_collision_and_orphaned_obligation_link` | PASS |
| TT-P03-27 | P03-07 | `test_adjustment_requires_authorized_bounded_soft_rule` | PASS |
| TT-P03-28 | P03-08 | `test_missing_or_untrusted_template_is_hold_not_a_fictional_add` | PASS — explicit HOLD |
| TT-P03-29 | P03-08 | `test_template_wrong_digest_or_path_traversal_is_never_materialized` | PASS |
| TT-P03-30 | P03-09 | `test_candidate_materialization_binds_parent_artifacts_and_all_source_versions`, `test_candidate_rejects_parent_mapping_unbound_from_hashed_bytes`, `test_child_configuration_version_is_deterministic_and_parent_bound` | PASS |
| TT-P03-31 | P03-09 | `test_candidate_rejects_stale_parent_collision_and_orphaned_obligation_link` | PASS |
| TT-P03-32 | P03-09,P03-13 | `test_v1_candidate_adapter_validates_without_changing_legacy_schema`, `test_v1_prediction_adapter_projects_exact_nonretain_targets_and_blocks_hold` | PASS |
| TT-P03-33 | P03-10 | `test_governance_accepts_only_when_every_required_gate_is_positive` | PASS — unit-level synthetic decision |
| TT-P03-34 | P03-10 | `test_unresolved_coverage_is_hold_and_proven_incomplete_candidate_is_reject` | PASS |
| TT-P03-35 | P03-10 | `test_proven_cost_limit_violation_rejects_only_the_candidate` | PASS |
| TT-P03-36 | P03-10 | `test_preflight_rejects_snapshot_validation_from_another_exact_revision`, `test_synthetic_pipeline_runs_spec02_and_holds_open_authority_unknown` | PASS — input rejection versus HOLD |
| TT-P03-37 | P03-11 | `test_append_only_event_chain_is_deterministic_and_identical_replay_is_idempotent` | PASS |
| TT-P03-38 | P03-11 | `test_rollback_requires_positive_fresh_current_context_validation` | PASS — mismatched configuration hash is blocked |
| TT-P03-39 | P03-11 | `test_publish_requires_accept_and_current_context_parent_compare_and_swap`, `test_publish_rejects_mutated_or_unsealed_governance_decisions`, `test_event_chain_tampering_is_detected_before_append` | PASS — mutation and re-digested HOLD-to-ACCEPT attempts are blocked |
| TT-P03-40 | P03-12 | `test_input_permutations_preserve_graph_and_impact_digests`, deterministic operation/template ordering tests | PASS — deterministic metamorphic cases |
| TT-P03-41 | P03-12 | `test_bounded_set_cover_prefers_fewer_operations_then_cost_then_ids`, `test_search_budget_exhaustion_and_missing_cost_return_hold`, `test_cost_model_rejects_duplicate_or_over_budget_candidate_and_ties_are_stable` | PASS |
| TT-P03-42 | P03-12 | `test_irrelevant_isolated_component_does_not_change_existing_impact` | PASS |
| TT-P03-43 | P03-13 | V1/V2 synthetic adapter tests and `test_b1_and_p_receive_identical_policy_and_common_snapshot` | BLOCKED — no pinned frozen method output re-export or byte comparison |
| TT-P03-44 | P03-13,S01 | `test_container_negative_probes_cannot_reach_oracle_history_network_or_other_output` | PASS — synthetic repository and local digest-pinned image |
| TT-P03-45 | P03-14 | `test_synthetic_pipeline_runs_spec02_and_holds_open_authority_unknown` | BLOCKED — positive authorized V3 authority/evaluator/cost path unavailable |
| TT-P03-46 | P03-14 | `test_synthetic_pipeline_runs_spec02_and_holds_open_authority_unknown`, `test_missing_or_untrusted_template_is_hold_not_a_fictional_add` | PASS — OPEN authority/missing template stays HOLD |
| TT-P03-47 | P03-14 | `test_high_score_or_covers_declaration_cannot_replace_exact_pair_evidence`, end-to-end OPEN-authority HOLD test | BLOCKED — negative half passes; no-op ACCEPT positive path is unavailable |
| TT-P03-48 | P03-14 | Link, exact-pair, stage/context, digest, fact-scope and absence-proof mutation tests listed above | PASS |

## Initial implementation commands and local results

The results in this section apply to the initial implementation before the
review remediations below.

The two existing test modules below were intentionally excluded because they
read the actual DA01 ground truth or execute the private scorer, which SPEC 03
forbids using while implementing P. No expected output from those modules was
read or used. No other tests were excluded by pytest.

```bash
uv sync --frozen --extra dev
make test-unit
make lint
make typecheck
make security
make architecture-test
make migration-test
make quality
```

For the verification run, `PYTEST_ADDOPTS` was
`-p no:cacheprovider --ignore=tests/unit/test_da01_execution.py --ignore=tests/unit/test_research_schema_foundation.py`.
`TEST_DATABASE_URL` pointed at a temporary PostgreSQL 16 container named
`evofit-spec03-postgres`, database `evofit_spec03_test`; the container was
stopped and removed after validation. Worktree cache/report paths were directed
under `/private/tmp` because the managed worktree is read-only to shell cache
writers. The `make quality` target used these same two exclusions.

| Check | Result |
| --- | --- |
| `uv sync --frozen --extra dev` | PASS — frozen environment synchronized |
| `make test-unit` | PASS — 183 passed, 1 existing Locust monkey-patch warning |
| `make lint` | PASS — Ruff check and format check |
| `make typecheck` | PASS — mypy checked 94 source files |
| `make security` | PASS — Bandit; existing comment parsing warnings only |
| `make architecture-test` | PASS — 5 import contracts kept; 6 architecture tests passed |
| `make migration-test` | PASS — disposable PostgreSQL 16; migration to `0001_a0_schema` |
| `make quality` | PASS — 195 passed, 91.24% application coverage, 6 existing warnings |
| Docker method isolation probe | PASS in the full quality run; no pytest skips were reported |
| Tests excluded by prohibition | BLOCKED — `test_da01_execution.py` and `test_research_schema_foundation.py` |
| Main baseline CI | [A0 quality run 38865248861](https://github.com/Pan14ek/evofit-bench/actions/runs/38865248861) — main only, not this implementation branch |
| Implementation branch CI (push) | [A0 quality run 38871687813](https://github.com/Pan14ek/evofit-bench/actions/runs/38871687813) — PASS for `e9c08fb` |
| Implementation branch CI (pull request) | [A0 quality run 38871742376](https://github.com/Pan14ek/evofit-bench/actions/runs/38871742376) — PASS for `e9c08fb` |

`make quality` initially reached 192 passing tests but pytest-cov failed to
write `coverage.xml` in the managed worktree. The successful run redirected the
coverage data and XML report to `/private/tmp`; it completed with 91.24%
application coverage. This is application coverage, not P requirement or method
coverage.

## Review remediation revalidation

The following focused checks ran after the review fixes. The two protected DA01
test modules listed above were not run; no DA01 ground truth, scorer, expected
operations or sealed output was read or used.

```bash
/private/tmp/evofit-spec03-venv/bin/python -m pytest -p no:cacheprovider tests/unit/test_p_candidate_governance_v1.py tests/unit/test_p_semantic_pairs_v1.py tests/integration/test_p_governed_adaptation_v1.py tests/integration/test_p_applicability_v3.py
RUFF_CACHE_DIR=/private/tmp/evofit-spec03-ruff-cache /private/tmp/evofit-spec03-venv/bin/ruff check experiments/execution/tooling/p_adaptation.py experiments/execution/tooling/p_candidate.py experiments/execution/tooling/p_governance.py experiments/execution/tooling/p_semantic.py tests/unit/test_p_candidate_governance_v1.py tests/unit/test_p_semantic_pairs_v1.py tests/integration/test_p_governed_adaptation_v1.py tests/integration/test_p_applicability_v3.py
RUFF_CACHE_DIR=/private/tmp/evofit-spec03-ruff-cache /private/tmp/evofit-spec03-venv/bin/ruff format --check experiments/execution/tooling/p_adaptation.py experiments/execution/tooling/p_candidate.py experiments/execution/tooling/p_governance.py experiments/execution/tooling/p_semantic.py tests/unit/test_p_candidate_governance_v1.py tests/unit/test_p_semantic_pairs_v1.py tests/integration/test_p_governed_adaptation_v1.py tests/integration/test_p_applicability_v3.py
MYPY_CACHE_DIR=/private/tmp/evofit-spec03-mypy-cache /private/tmp/evofit-spec03-venv/bin/mypy app scripts tests
/private/tmp/evofit-spec03-venv/bin/bandit -q -r experiments/execution/tooling/p_adaptation.py experiments/execution/tooling/p_candidate.py experiments/execution/tooling/p_governance.py experiments/execution/tooling/p_semantic.py
git diff --check
```

| Check | Result |
| --- | --- |
| Focused SPEC 03 regression tests plus strict V3 verifier regression suite | PASS — 42 passed, 1 existing Starlette/httpx deprecation warning, 0 skipped |
| Ruff check on changed Python files | PASS |
| Ruff format check on changed Python files | PASS |
| Mypy `app scripts tests` | PASS — 94 source files |
| Bandit on changed implementation modules | PASS |
| `git diff --check` | PASS |
| Local full `make quality` after these remediations | BLOCKED — not run locally because it includes the two protected test modules listed above |
| Hosted GitHub Actions `A0 quality` | PASS — [run 38889778200](https://github.com/Pan14ek/evofit-bench/actions/runs/38889778200), commit `b62d7d1837b09e3f7a453af8b7da65da592f8b43` |

## Unresolved method decisions and research boundary

All OPEN-01 through OPEN-10 items in SPEC 03 remain unresolved. In particular,
the repository V3 catalog lacks approved mandatory classifications, the
generic evaluator template list is empty, and no authorized cost model or
multi-stage contract is available. The supported result is therefore `HOLD`
until those inputs exist. The implementation does not create evaluator code,
modify the application architecture, resolve the manuscript/protocol RQ
numbering, or rewrite scorer semantics.

The code keeps `p_interface.py` at `NOT_READY`. No measured DA01 trial was run,
no human B1 result was created, and G1/G4 remain independent approval gates.
Synthetic success establishes only finite contract behavior, not scientific
novelty, population-level effect, or method superiority.

Frozen-artifact preservation was checked by changed-path review only: `git
status --short` and `git diff --name-only origin/main` show this change is
limited to additive code, schemas, tests and descriptive documentation. No
ground-truth/scorer/result blob contents or hashes were read to perform that
check.
