# MONO-E1 Comparability Preparation Report V1

## Purpose and boundary

This report accompanies the versioned read-only preflight for the B0/P
MONO-E1 negative-control comparison, A0.3→A0.4. The implementation checks
preparation inputs; it does not execute an arm, produce predictions, score
results, freeze a reference, create a database fixture, or authorize a run.

The canonical source pair is pinned as follows:

| State | Commit | Repository tree | Application tree |
| --- | --- | --- | --- |
| A0.3 `A0_3_GOVERNED_MODULE_GRAPH` | `26a9bb667da7d0938e38aca15d2bf29fd1de4829` | `7b951421395f532ca403dab09d76902ff08a807d` | `b147b8961ea9e76c966663d4832e4c303581151a` |
| A0.4 `A0_4_REPORT_QUERY_PORT` | `d3101c0d3aa9b7b709253b6ec7518416f05f65b9` | `2b436e0aaf09403ea516d73d20a466a122f86592` | `007196f68652bc13f6798805793ffdfae96f95f7` |

The verifier checks the canonical checkpoint and patch digests, W0 addendum,
checkpointed observation set, Git ancestry, source trees, B0 historical source
files, and unchanged P review-candidate identity. It reuses the existing
`mono_a1`, method-bundle, hashing, and isolation utilities.

## Current readback

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m experiments.execution.tooling.mono_e1_preflight
```

The checked-in snapshot reads as **INCOMPLETE**, with no invalid source or
artifact digest reasons. Architecture source identity and pinned input bytes
pass their bounded checks. The experimental gate is **NO_GO**; measured run
status is **NOT_EXECUTED**, and scientific readiness is **NOT_ESTABLISHED**.

| Dimension | Readback | Remaining work |
| --- | --- | --- |
| Architecture identity | PASS, source identity only | Scientific interpretation and policy approval are separate gates |
| Pinned input artifacts | PASS, byte identity only | No evidence authority is inferred from the hashes |
| Workload | PINNED_PROPOSAL_ONLY; repeatability NOT_ESTABLISHED | Approve a common fixed request trace or deterministic open-loop runner and bind its digest |
| PostgreSQL fixture | NOT_CREATED | Choose a seed identity, create per-arm disposable databases from identical bytes, record and verify a fingerprint |
| Evaluator capabilities | Inventory missing/unapproved | Approve the complete capability denominator and bind it to both arms |
| B0/P identities | Historical B0 and P review candidate only | Establish E1-specific frozen method identities and input bundles |
| Arm allowlists | INCOMPLETE | Export and independently read back separate B0/P bundles and allowlist digests |
| Runtime images | UNVERIFIED | Pin image digests and obtain external source-to-image verification for each arm |
| Isolation | Specified | Preserve explicit read-only mounts, no network, no Git metadata, scorer, oracle, labels, or other-arm outputs |
| Measurement | Boundaries specified; values absent | Record timings only during a future authorized run; CPU and RSS stay null until sampled |
| Policy and experiment authority | PENDING | Resolve policy/lifecycle authority, catalog completeness, P review, scorer custody, and reference freeze; satisfy G1 and G4 |

The existing A0 profile supplies candidate parameters (20 users, 5 users/sec,
30-second read-only warmup, 120-second measurement, and the recorded operation
weights), but it is not a reproducible MONO-E1 workload. Locust randomly selects
weighted tasks and `between(0.5, 1.5)` uses randomized waits; equal profile bytes
do not make the per-arm request sequence identical. See the [Locust task and
wait-time documentation](https://github.com/locustio/locust/blob/master/docs/writing-a-locustfile.rst).
The preflight records these randomness sources and blocks readiness until an
approved immutable request trace or deterministic open-loop runner is supplied.

The fixture proposal is explicitly digest-bound as
`MONO_E1_POSTGRES_FIXTURE_SPEC_V1`. It pins migration bytes and seed-tool
identities and proposes 100 users and 500 tasks in separate disposable
databases. Its seed ID, expected fingerprint, and actual fixture identity remain
null. The A0 workload profile remains a proposal because its source architecture
is A0 and it has mutating operations, stochastic task selection, and randomized
wait timing.

## Requirement-to-test traceability

All tests below use checked-in public artifacts or synthetic mutations. None
invokes the measured Method P interface or accesses scorer/reference data.

| Requirement | Test coverage |
| --- | --- |
| Strict contract and clean, incomplete positive readback | `test_current_preflight_is_validly_incomplete_and_non_authoritative` |
| Exact common A0.4 target and arm source parity | `test_different_target_source_shas_fail_closed` |
| Workload digest/repeatability and shared fixture/migration identity | `test_workload_digest_mismatch_is_detected`; `test_unverified_workload_repeatability_is_incomplete`; `test_fixture_and_migration_identity_mismatches_are_detected` |
| Required evaluator capability denominator | `test_missing_required_evaluator_capability_is_incomplete` |
| Separate, digest-bound allowlists | `test_missing_allowlist_remains_incomplete`; `test_malformed_allowlist_digest_is_invalid` |
| No reference/scorer/oracle or cross-arm output paths | `test_reference_or_cross_arm_path_leakage_is_invalid` |
| External verification required for image provenance | `test_structural_image_record_without_external_verifier_stays_unverified` |
| Matched timing boundaries and honest missing resource data | `test_incompatible_timing_boundary_is_invalid`; `test_uncollected_cpu_and_rss_remain_null` |
| Pending authority cannot yield PASS or GO | `test_pending_authority_never_becomes_pass_or_go` |
| B0 source and P configuration digest tampering | `test_tampered_b0_source_and_p_configuration_digests_are_invalid` |

## Future authorized integration handoff

After the separate methodological and governance gates are resolved:

1. Record the approved obligation denominator, policy/lifecycle registries,
   architecture facts, and evaluator capability inventory with their authority
   evidence and digests.
2. Approve a deterministic common workload trace/runner and the fixture
   specification. Assign the seed ID, produce the expected fingerprint, and create separate disposable databases
   only under an explicitly disposable local test environment.
3. Freeze the B0 and P E1 identities. Export two arm-specific method bundles
   using the existing versioned input exporters, then run each existing bundle
   verifier and bind its exact file inventory and digest to this manifest.
4. Pin runner and image digests. Supply externally verified attestations that
   bind both images to the exact A0.4 target source; a manifest status field is
   not authentication.
5. Re-run this read-only verifier with the two bundle directories and the
   external image and authority verifiers. Resolve every structural blocker,
   then follow the separately authorized reference-freeze and isolated-run
   protocol. This preflight itself remains NO_GO and does not replace G1/G4.

## Verification record

| Command | Result |
| --- | --- |
| `make development-regression-test UV=/private/tmp/uv-mono-e1` | PASS: 491 regression tests, then the separately repeated EXP-01/02 suites passed 49 and 30 tests |
| `/private/tmp/b0p-venv/bin/ruff check . --no-cache --extend-exclude=tests/unit/test_da01_execution.py --extend-exclude=tests/unit/test_research_schema_foundation.py` | PASS |
| `/private/tmp/b0p-venv/bin/ruff format --check . --no-cache --extend-exclude=tests/unit/test_da01_execution.py --extend-exclude=tests/unit/test_research_schema_foundation.py` | PASS: 345 files already formatted |
| `/private/tmp/b0p-venv/bin/mypy --explicit-package-bases experiments/execution/tooling/mono_e1_preflight.py tests/unit/test_mono_e1_preflight.py --cache-dir=/private/tmp/mypy-cache-mono-e1-targeted` | PASS: no issues in the two changed Python files |
| `/private/tmp/b0p-venv/bin/bandit -q -r app scripts experiments/execution/tooling` | PASS |
| `PYTHONDONTWRITEBYTECODE=1 /private/tmp/b0p-venv/bin/python -m experiments.execution.tooling.mono_e1_preflight` | PASS readback: INCOMPLETE, no invalid reasons, NO_GO, NOT_EXECUTED |

The repository-wide mypy command still fails with 35 pre-existing errors in 11
untouched files; the targeted mypy command for this change passes. The local
environment does not provide `uv`, so the Makefile regression target used a
temporary dispatcher to the available project virtual environment. Hosted PR
CI remains the final repository-level check.

Do not edit frozen A0 artifacts, the P candidate identity, the policy approval
package, or scorer-side reference data to satisfy this handoff.
