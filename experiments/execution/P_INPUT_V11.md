# P Input Contract v1.1 — implementation journal

**Status:** `DEVELOPMENT / SYNTHETIC`; the candidate profile is `VERSIONED / UNFROZEN`. No measured DA01 run was created. This document is an implementation record, not a change to the frozen DA01 protocol.

## Baseline and safeguards

- Feature branch: `codex/p-input-contract-v11`.
- Baseline commit: `4f219e71300b0c544aa73de2c7609f3ba2bb92fe`.
- Protected tag: `arch-a0-monolith-v1` at `aaaca97a3385a92351552cd60d1866873d174a48`.
- Runtime: Python 3.12.14, pytest 8.4.2, jsonschema 4.26.0. `uv` is not installed; checks used the available Python 3.12 runtime and the repository's installed dev packages.
- Baseline unit and architecture suite: 85 passed, 1 existing gevent SSL monkey-patch warning.
- SHA-256 of the 72 protected files was captured before editing in [P_INPUT_V11_SENSITIVE_SHA256.txt](P_INPUT_V11_SENSITIVE_SHA256.txt). Recheck after implementation found zero mismatches.
- `inputs.py`, `method_input.schema.json`, `p_interface.py`, B0/B1/P V1 evaluators, DA01 protocol/readiness/scoring/validity documents, scenario/oracle/scorer data, and experiment outputs remain byte-identical to the captured baseline. The full V1 B0/B1/P output packages were re-exported from the baseline commits and compared file-by-file, including manifests.

## Contract and implemented APIs

The canonical Draft 2020-12 Snapshot schema is stored at `schemas/architecture_policy_snapshot_v1_1.schema.json` and retains `$id` `urn:evofitbench:versioned-architecture-policy-snapshot:v1.1`. Its top-level contract is `schema_version="1.1"`, `contract_id="VERSIONED_ARCH_POLICY_SNAPSHOT_V1_1"`, and `fact_vocabulary_version="FV_CORE_V1"`.

- Snapshot structure and strict RFC3339 format validation: `validate_snapshot_schema`.
- FV registry loading and per-predicate validation: `load_fact_vocabulary`, `validate_facts`; FV_CORE_V1 contains exactly these 12 predicates: `component.python_module_identity`, `component.module_added`, `component.module_removed`, `component.capability_module`, `component.declared_cross_module_dependency`, `component.shared_infrastructure`, `deployment.unit_count_declared`, `deployment.process_count_declared`, `deployment.database_instance_count_declared`, `deployment.database_product_declared`, `communication.internal_mode_declared`, `communication.broker_declared`.
- Exact source bytes, source roles, paths, source state/revision, unique identifiers and references: `validate_source_references`, `load_verified_source_manifest`.
- APA checks: `verify_policy_authority`; external trust is supplied through `AuthorityTrustContext`. Approval records bind the entire policy row by SHA-256 and require an external signature/trust check. An unsigned flag or digest alone cannot establish authority.
- Bounded completeness proof interface: `verify_completeness_claims`; verifier errors/timeouts and unverified claims remain `UNDETERMINED`.
- Combined report: `load_and_validate_snapshot` returns schema, integrity, authority, fact and completeness statuses, stable reason codes, evidence refs and Snapshot digest.
- V2-only strict projection/export/verification: `build_normalized_snapshot`, `export_method_inputs_v2`, `verify_method_bundle_v2`. The profile is `DA01_METHOD_INPUTS_V2_CANDIDATE`, with `profile_status="DEVELOPMENT_UNFROZEN"`; it supports B1 and P only. B1/P share identical Snapshot bytes; P alone receives traceability.

Enums in the Snapshot schema include fact epistemic kinds `DECLARED | EXTRACTED | OBSERVED | UNKNOWN`; policy kinds `UNCONDITIONAL_MANDATE | CONDITIONAL_MANDATE | EXCEPTION | RETIREMENT`; normative statuses `DRAFT | APPROVED | REVOKED | SUPERSEDED`; registry closure `OPEN | CLAIMED_CLOSED`; and completeness kinds `EXACT_ENUMERATION | SOUND_OVERAPPROXIMATION | AUTHORITATIVE_POLICY_REGISTRY`. FV13/FV14 provenance labels and FV15–FV21 reserved predicates are not activation facts.

## V2 isolation and policy behavior

The new exporter reads only pinned Git blobs and `.py` files under `app/`. It never reads `governance` fields as policy evidence and does not contact Google Drive or any network service. The structural YAML is projected through typed allowlists: deployment keys, module `package`, shared infrastructure module names, and dependency `from`/`to` only. Nested rationale, scenario metadata, governance flags and unrecognized fields are omitted. Each architecture inventory records the Git blob SHA-1 for every source file; the verifier checks those object IDs against bundled bytes, re-derives the normalized Snapshot, pins structural observations to the target commit/tree, checks the exact bundle inventory and hashes, rejects symlinks, and fails on any mismatch.

A pinned Charter and Registry are required at `fitness/policy/authority-charter.json` and `fitness/policy/registry.json`, with approval/evidence sidecars under their explicit directories. The current repository has no such authority inputs: a real checkout export was attempted and correctly returned `MISSING_AUTHORITY` without creating an output bundle. Synthetic V2 tests use only a temporary Git repository with explicitly synthetic artifacts.

The successful synthetic V2 bundle was structurally valid and byte/hash valid. Its authority and extracted fact status remain `UNDETERMINED` because no production trust anchors or independent extraction verifier are configured; an open policy registry also does not prove closure. No `ACTIVE`/`INACTIVE` applicability, obligation decisions, candidate operations or P outputs are produced.

## V1 byte compatibility

Pinned baseline commits: before `aaaca97a3385a92351552cd60d1866873d174a48`, after `4f219e71300b0c544aa73de2c7609f3ba2bb92fe`.

| Method | Manifest-listed files | V1 bundle SHA-256 | `method_input.json` SHA-256 | Re-export comparison |
|---|---:|---|---|---|
| B0 | 100 | `62ce5f223715a35a407e58c92c45355ddd31708de192a0479e1afeb2f133b628` | `0f9697276d4f1e86825124bd870473d51c54f5ee587c352b2317186dd632487b` | Byte-identical |
| B1 | 101 | `b2e6eafd84ef4b224bc424421546f8bd0981784b42f05d3bb3ced3cdbccc12a4` | `c541580795be48d372f29109c7feaf80fb8a63bead0c6c9f8c6eb843fc6cc6c3` | Byte-identical |
| P | 102 | `906ad62e1b5306da798878f094712e652beac91009f94a3bb0843a9a95776afb` | `65dcea90e00009078ecd70d43b14b3fd2c1aea4132d32a5f45754d2a5f3e876a` | Byte-identical |

## Verification journal

All Python commands were run with Python 3.12.14 and `PYTHONPATH=.venv/lib/python3.12/site-packages` because `uv` is unavailable.

| Check | Result |
|---|---|
| Baseline `pytest --no-cov tests/unit tests/architecture` | 85 passed, 1 warning |
| `pytest -q --no-cov tests` with temporary PostgreSQL 16 | 146 passed, 6 dependency deprecation/monkey-patch warnings; container removed afterward |
| New contract/APA/FV/V2 tests | 57 passed |
| `ruff check .` and `ruff format --check .` | Passed; 124 Python files formatted |
| `mypy app scripts tests` | Passed; 83 source files |
| `mypy --explicit-package-bases` for the two new validation/export modules | Passed |
| Bandit over `app scripts experiments/execution/tooling` | Passed; existing Bandit comment-parser warnings only |
| Import Linter | Passed; 5 contracts kept, 0 broken |
| `scripts.validate_migrations` with disposable PostgreSQL 16 | Passed at revision `0001_a0_schema`; container removed afterward |
| Sensitive SHA-256 recheck | 72/72 unchanged |
| V1 package re-export comparison | B0/B1/P all byte-identical |
| Real-checkout V2 export | Failed closed with `MISSING_AUTHORITY`; no partial directory created |

## Remaining questions and next boundary

1. Where and how should reviewed Charter, Registry, approval and evidence artifacts be curated and pinned for real runs?
2. Which production trust anchors/signature verifier and independent extracted-fact verifier should be configured? Current signed HMAC trust exists only in explicitly synthetic tests.
3. Which authoritative condition catalog should validate `condition_ref` values? Missing catalog knowledge remains unresolved rather than accepted.
4. What bounded production procedure and independent verifier will establish completeness claims or registry closure?
5. Applicability Ruleset `App_q`, tri-valued activation evaluation, Impact Analysis, candidate generation and scoring remain outside SPEC 01. `P_ALGORITHM_STATUS` remains `NOT_READY`.

No G1/G4 readiness or measured DA01 result is claimed. The next implementation boundary is SPEC 02 (Applicability Ruleset), after review of this contract.
