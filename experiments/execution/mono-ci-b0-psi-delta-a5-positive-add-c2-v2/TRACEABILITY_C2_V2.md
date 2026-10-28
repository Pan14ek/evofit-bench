# C2 V2 traceability

| Requirement | Source | Verification |
|---|---|---|
| Exact three-obligation TEST_ONLY universe; other 15 remain UNKNOWN | `PROTOCOL_C2_V2.json`, `inputs/POSITIVE_ADD_C2_PROFILE_V2.json`, `p_applicability_c2_v2.py`, `p_adaptation_c2_v2.py` | Exact-set positive and adversarial regressions in `tests/unit/test_p_applicability_exact_test_only.py` and `tests/unit/test_mono_ci_psi_a05_positive_add_c2.py` |
| Source-bound retain evidence for public API and module graph | C2 profile and existing source/configuration-bound C1 evidence | Fresh evaluator runs, exact pair validity, frozen evaluator source/configuration digests |
| Existing ownership evaluator/template and 225 ms cost cap | C2 profile, `mono_ci_psi_a05_positive_add.py`, `p_operations.py` | Candidate validation, cost verdict, clean and negative evaluator outputs |
| Freeze protocol, method, profile, schemas, source identities and Docker preflight | `mono_ci_psi_a05_positive_add_c2.py` | `PRE_RUN_FREEZE_C2.json`, archive checksum inventories, post-run `verify_results` |
| Preserve official boundary | Protocol, freeze/results schemas, transition archive schema | G1 INCOMPLETE, G4 NOT_AUTHORIZED, P algorithm NOT_READY, scoring NOT_EXECUTED |

The exact-set route is a new versioned TEST_ONLY closure hook over the unchanged
DEVELOPMENT evaluator. It validates six source-bound claims for the exact
three-obligation, two-state set while preserving the original Snapshot and
registry proof; the other 15 full-catalog results remain UNKNOWN. The pinned
`p_adaptation.py`, `p_applicability.py`, global closure algorithm, and canonical
obligation catalog are unchanged.
