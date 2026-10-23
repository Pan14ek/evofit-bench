"""Read-only, fail-closed MONO-E1 comparability preparation checks.

The preflight binds known engineering artifacts and reports missing scientific
inputs. It never creates method bundles, executes an arm, freezes a reference,
or authorizes a measured study.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed Git executable, validated refs, no shell
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any, cast

from experiments.execution.tooling.b0p_development import (
    B0_SOURCE_FILES,
    FROZEN_B0_CONFIG_PATH,
    FROZEN_B0_EVALUATOR_PATH,
    PINNED_B0_SOURCE_SHA,
)
from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError, ProtocolError
from experiments.execution.tooling.hashing import (
    bundle_sha256,
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)
from experiments.execution.tooling.inputs import (
    FORBIDDEN_PATH_PARTS,
    MethodId,
    verify_method_bundle,
)
from experiments.execution.tooling.isolation import MAX_CPUS, MAX_MEMORY, MAX_PIDS
from experiments.execution.tooling.mono_a1 import (
    assess_mono_rq3,
    validate_source_image_provenance,
    verify_source_revision,
)
from experiments.execution.tooling.p_policy_source_v3 import verify_method_bundle_v3

SCHEMA_NAME = "mono_e1_comparability_preflight_v1.schema.json"
MANIFEST_PATH = Path("experiments/execution/MONO_E1_COMPARABILITY_PREFLIGHT_V1.json")
WORKLOAD_SCHEMA_VERSION = "MONO_E1_WORKLOAD_FIXTURE_SPEC_V1"
STUDY_ID = "MONO-E1"

BEFORE_SOURCE = {
    "state_id": "A0_3_GOVERNED_MODULE_GRAPH",
    "commit_sha": "26a9bb667da7d0938e38aca15d2bf29fd1de4829",
    "repository_tree_sha": "7b951421395f532ca403dab09d76902ff08a807d",
    "application_tree_sha": "b147b8961ea9e76c966663d4832e4c303581151a",
}
AFTER_SOURCE = {
    "state_id": "A0_4_REPORT_QUERY_PORT",
    "commit_sha": "d3101c0d3aa9b7b709253b6ec7518416f05f65b9",
    "repository_tree_sha": "2b436e0aaf09403ea516d73d20a466a122f86592",
    "application_tree_sha": "007196f68652bc13f6798805793ffdfae96f95f7",
}
CANONICAL_A03_CHECKPOINT_SHA256 = "5da4a7e1ed359ec8ea1e3288ab81edf32f0b71e2fec946b52a8d0d562dcf43c0"
CANONICAL_A04_CHECKPOINT_SHA256 = "7b0b0c7a0c6ac782540466d283c42d7589b8aaeb4af7df62104faa01fd154e8e"
CANONICAL_A04_PATCH_SHA256 = "6538147b9aa4fa5075314aaa54a0e24ea51f33cf0d314342e926d41dabec17ac"
W0_ADDENDUM_SHA256 = "5adda1c5169acf089d48304ca584483b30cdfe886ee9e2853d0c8a9154745cc4"
CATALOG_SHA256 = "8c5bd8fffe3bdb2af8fb85f8d0012bc34673f72866e52daed99fab96f9763011"
P_CANDIDATE_PATH = "experiments/execution/P_EXECUTABLE_CANDIDATE_V1.json"
P_CANDIDATE_IDENTITY_SHA256 = "45c75b7d211705ab001f080a193aa64641e01d5222e25603cd0ef241fecefde4"
P_CANDIDATE_SOURCE_SHA256 = "c477bd4258734a615fcdaf8491988a36bba90004eb4af083c76e0e814ff0ccbf"
P_CANDIDATE_CONFIG_SHA256 = "cdd4df7342e821927c3a565f6bcec02d51a6c65bbca2fd131cfaae099ecb9fca"
PINNED_RUNNER_SOURCE_SHA = "a1e2f79d4bc3c10431cac3e2d8be54105061a98b"
PINNED_RUNNER_TREE_SHA = "8288d8dc666a28f557c652d47c81f2d0f6b301d4"

REQUIRED_TIMINGS = (
    "adaptation_ns",
    "evaluator_execution_ns",
    "verification_ns",
    "total_execution_ns",
)
EXPECTED_TIMING_BOUNDARIES = [
    {
        "field": "adaptation_ns",
        "start_event": "arm_method_entry",
        "stop_event": "adaptation_decision_complete",
    },
    {
        "field": "evaluator_execution_ns",
        "start_event": "evaluator_invocation_start",
        "stop_event": "evaluator_invocation_complete",
    },
    {
        "field": "verification_ns",
        "start_event": "verification_start",
        "stop_event": "verification_complete",
    },
    {
        "field": "total_execution_ns",
        "start_event": "arm_start",
        "stop_event": "arm_complete",
    },
]
REQUIRED_PROHIBITIONS = (
    "SCORER",
    "ORACLE",
    "REFERENCE_ANSWERS",
    "HIDDEN_TARGET_LABELS",
    "OTHER_ARM_OUTPUTS",
    "GIT_METADATA",
    "UNAPPROVED_NETWORK",
)
RUNNER_SOURCE_PATHS = (
    "experiments/execution/tooling/b0p_isolated_b0_runner.py",
    "experiments/execution/tooling/b0p_isolated_p_runner.py",
    "experiments/execution/tooling/isolation.py",
    "experiments/execution/tooling/inputs.py",
)

SourceImageVerifier = Callable[[Mapping[str, Any]], bool]
AuthorityVerifier = Callable[[Mapping[str, Any]], bool]


def build_current_preflight_manifest(repository: Path) -> dict[str, Any]:
    """Build a non-authoritative snapshot from pinned repository artifacts.

    This is an in-memory builder. It does not create directories, bundles,
    database fixtures, attestations, or experiment outputs.
    """
    root = repository.resolve(strict=True)
    workload_source = _artifact_record(root, "load/profiles/a0-baseline-v1.yaml")
    workload_payload = _read_yaml_profile(root / workload_source["path"])
    workload_definition = {
        "schema_version": WORKLOAD_SCHEMA_VERSION,
        "target_architecture_state": AFTER_SOURCE["state_id"],
        "source_profile_id": workload_payload["id"],
        "source_architecture_state": workload_payload["architecture_state"],
        "users": workload_payload["users"],
        "spawn_rate_per_second": workload_payload["spawn_rate_per_second"],
        "warmup": workload_payload["warmup"],
        "measurement": workload_payload["measurement"],
        "request_mix": workload_payload["request_mix"],
        "wait_time_seconds": [0.5, 1.5],
        "arrival_order": "STOCHASTIC",
        "database_side_effects": "MUTATING",
        "selection_status": "PROPOSED_REVIEW_REQUIRED",
    }
    workload_digest = sha256_bytes(canonical_json_bytes(workload_definition))

    before_checkpoint = _artifact_record(
        root, "architecture/acceptance/a1/a0_3_canonical_checkpoint.json"
    )
    after_checkpoint = _artifact_record(
        root, "architecture/acceptance/a1/a0_4_canonical_checkpoint.json"
    )
    observations = _checkpoint_observations(root, before_checkpoint["path"], BEFORE_SOURCE)
    observations.extend(_checkpoint_observations(root, after_checkpoint["path"], AFTER_SOURCE))

    catalog = _artifact_record(root, "fitness/catalog/architectural-obligations.yaml")
    policy_records = [
        _artifact_record(
            root,
            "experiments/execution/policy-pilot/v1/source/fitness/policy/authority-charter.json",
        ),
        _artifact_record(
            root,
            "experiments/execution/policy-pilot/v1/source/fitness/policy/registry.json",
        ),
        _artifact_record(
            root,
            "experiments/execution/policy-pilot/v1/source/fitness/policy/completeness-claims.json",
        ),
        _artifact_record(
            root,
            "experiments/execution/policy-pilot/v1/source/policy/applicability_ruleset_v1.json",
        ),
    ]
    parent_configuration = _artifact_record(root, FROZEN_B0_CONFIG_PATH)
    parent_evaluator = _artifact_record(root, FROZEN_B0_EVALUATOR_PATH)
    capability_source = _artifact_record(root, "fitness/catalog/a0-fitness-elements.yaml")

    b0_tree = _git_text(root, "rev-parse", f"{PINNED_B0_SOURCE_SHA}^{{tree}}").strip()
    b0_inventory = [_git_blob_record(root, PINNED_B0_SOURCE_SHA, path) for path in B0_SOURCE_FILES]
    b0_configuration_at_source = _git_blob_record(root, PINNED_B0_SOURCE_SHA, FROZEN_B0_CONFIG_PATH)
    b0_evaluator_at_source = _git_blob_record(root, PINNED_B0_SOURCE_SHA, FROZEN_B0_EVALUATOR_PATH)
    p_candidate = _read_json(root / P_CANDIDATE_PATH)

    migration = _artifact_record(root, "alembic/versions/0001_a0_schema.py")
    seed_script = _artifact_record(root, "scripts/seed_db.py")
    seed_identity = _artifact_record(root, "scripts/seed_identity.py")
    seed_fingerprint = _artifact_record(root, "scripts/seed_fingerprint.py")
    python_version = _artifact_record(root, ".python-version")
    uv_lock = _artifact_record(root, "uv.lock")
    workload_runner = _artifact_record(root, "load/locustfile.py")
    workload_builder = _artifact_record(root, "load/workload_profile.py")
    fixture_definition = {
        "schema_version": "MONO_E1_POSTGRES_FIXTURE_SPEC_V1",
        "target_architecture_state": AFTER_SOURCE["state_id"],
        "migration_revision": "0001_a0_schema",
        "migration_sha256": migration["sha256"],
        "seed_id": None,
        "seed_artifacts": [seed_script, seed_identity, seed_fingerprint],
        "user_count": 100,
        "task_count": 500,
        "expected_fingerprint_sha256": None,
        "per_arm_policy": "SEPARATE_DISPOSABLE_DATABASES_FROM_IDENTICAL_FINGERPRINT",
        "specification_status": "PROPOSED_UNVERIFIED",
    }
    fixture_specification = {
        "definition": fixture_definition,
        "definition_sha256": sha256_bytes(canonical_json_bytes(fixture_definition)),
    }

    verify_source_revision(root, PINNED_RUNNER_SOURCE_SHA, PINNED_RUNNER_TREE_SHA)
    runner_files = [
        {
            "path": path,
            "sha256": _git_blob_sha256(root, PINNED_RUNNER_SOURCE_SHA, path),
        }
        for path in RUNNER_SOURCE_PATHS
    ]
    runner_commit = PINNED_RUNNER_SOURCE_SHA
    runner_tree = PINNED_RUNNER_TREE_SHA

    common_env = {"HOME": "/tmp", "PYTHONDONTWRITEBYTECODE": "1"}  # noqa: S108  # nosec B108 - container-scoped HOME
    shared_input_plan = [
        "architecture.after",
        "architecture.observations",
        "obligation.catalog",
        "policy.authority",
        "policy.lifecycle_stages",
        "fitness.parent_configuration",
        "evaluator.capabilities",
        "workload.specification",
        "postgres.fixture",
        "runtime.environment",
    ]
    arm_records: dict[str, dict[str, Any]] = {}
    for arm_id in ("B0", "P"):
        arm_records[arm_id] = {
            "target_source_sha": AFTER_SOURCE["commit_sha"],
            "target_repository_tree_sha": AFTER_SOURCE["repository_tree_sha"],
            "workload_spec_sha256": workload_digest,
            "database_fixture_id": None,
            "database_fixture_sha256": None,
            "migration_revision": "0001_a0_schema",
            "migration_sha256": migration["sha256"],
            "catalog_sha256": catalog["sha256"],
            "policy_registry_sha256": policy_records[1]["sha256"],
            "lifecycle_registry_sha256": None,
            "evaluator_capability_ids": [],
            "shared_environment": dict(common_env),
            "method_specific_environment": {},
            "resource_limits": {
                "cpus": MAX_CPUS,
                "memory": MAX_MEMORY,
                "pids": MAX_PIDS,
            },
            "input_inventory": {
                "status": "MISSING",
                "shared_input_ids": [],
                "method_specific_input_ids": [],
                "shared_inputs": [],
                "method_specific_inputs": [],
                "allowlist_sha256": None,
            },
            "image_provenance": {
                "status": "MISSING",
                "image_digest": None,
                "source_sha": None,
                "attestation_sha256": None,
                "external_verifier_id": None,
                "verification_evidence_sha256": None,
            },
        }

    measurements = {
        arm_id: {
            "timing_boundary_id": "MONO_E1_TIMING_BOUNDARIES_V1",
            "timings_ns": {field: None for field in REQUIRED_TIMINGS},
            "resource_metrics": {
                "cpu_time_ns": {"status": "NOT_COLLECTED", "value": None},
                "peak_rss_bytes": {"status": "NOT_COLLECTED", "value": None},
            },
        }
        for arm_id in ("B0", "P")
    }

    manifest: dict[str, Any] = {
        "schema_version": "mono-e1-comparability-preflight-v1",
        "study_id": STUDY_ID,
        "preparation_status": "INCOMPLETE",
        "experimental_go": "NO_GO",
        "non_authoritative": True,
        "source_pair": {
            "before": {**BEFORE_SOURCE},
            "after": {**AFTER_SOURCE},
            "lineage": {
                "status": "SOURCE_IDENTITY_ONLY",
                "evidence_path": "experiments/execution/MONO_A1_PROTOCOL_V1_W0_ADDENDUM.md",
                "evidence_sha256": _artifact_record(
                    root, "experiments/execution/MONO_A1_PROTOCOL_V1_W0_ADDENDUM.md"
                )["sha256"],
            },
            "canonical_checkpoints": [before_checkpoint, after_checkpoint],
            "application_patch": {
                "path": "architecture/acceptance/a1/a0_4_canonical_application_source.diff",
                "sha256": CANONICAL_A04_PATCH_SHA256,
            },
            "observations": observations,
        },
        "common_inputs": {
            "obligation_catalog": {
                "artifact": catalog,
                "revision": "architectural-obligations-v1",
                "status": "PINNED_BYTES_ONLY",
            },
            "policy": {
                "candidate_sources": policy_records,
                "authority_status": "PENDING",
                "lifecycle_stage_registry": {
                    "status": "MISSING",
                    "path": None,
                    "sha256": None,
                },
                "completeness_status": "UNKNOWN",
            },
            "architecture_facts": {
                "status": "ENGINEERING_SOURCE_EVIDENCE_ONLY",
                "source_sha": AFTER_SOURCE["commit_sha"],
                "artifact_paths": [
                    item["path"]
                    for item in observations
                    if item["architecture_source_sha"] == AFTER_SOURCE["commit_sha"]
                ],
            },
            "parent_fitness_configuration": {
                "configuration": parent_configuration,
                "evaluator_configuration": parent_evaluator,
                "status": "PINNED_BYTES_ONLY",
            },
            "evaluator_capabilities": {
                "status": "UNAPPROVED_INVENTORY_MISSING",
                "candidate_source": capability_source,
                "required_ids": [],
            },
            "workload": {
                "status": "PROPOSED_NOT_APPROVED",
                "definition": workload_definition,
                "definition_sha256": workload_digest,
                "reproducibility": {
                    "status": "NOT_ESTABLISHED",
                    "randomness_sources": [
                        "Locust weighted task selection uses random choice",
                        "Locust between wait time samples a random interval",
                        "Closed-loop completion rate can vary with arm response time",
                    ],
                    "request_trace_sha256": None,
                    "required_control": (
                        "APPROVED_IMMUTABLE_REQUEST_TRACE_OR_DETERMINISTIC_OPEN_LOOP_RUNNER"
                    ),
                },
                "source_profile": workload_source,
                "runner_source": workload_runner,
                "profile_validator_source": workload_builder,
            },
            "database_fixture": {
                "status": "NOT_CREATED",
                "specification": fixture_specification,
                "fixture_id": None,
                "fixture_sha256": None,
                "migration": {
                    "revision": "0001_a0_schema",
                    "artifact": migration,
                },
                "seed": {
                    "seed_id": None,
                    "user_count": 100,
                    "task_count": 500,
                    "seed_script": seed_script,
                    "identity_script": seed_identity,
                    "fingerprint_script": seed_fingerprint,
                    "expected_fingerprint_sha256": None,
                    "source_artifacts": [seed_script, seed_identity, seed_fingerprint],
                },
                "per_arm_policy": "SEPARATE_DISPOSABLE_DATABASES_FROM_IDENTICAL_FINGERPRINT",
                "destructive_reset_performed": False,
            },
            "environment": {
                "python_version": (root / python_version["path"])
                .read_text(encoding="utf-8")
                .strip(),
                "python_version_file": python_version,
                "dependency_lock": uv_lock,
                "runtime_image_status": "MISSING",
                "environment_variables": common_env,
            },
        },
        "arms": {
            "B0": {
                **arm_records["B0"],
                "method_identity": {
                    "status": "DEVELOPMENT_BASELINE_BYTES_ONLY",
                    "method_version": "B0_A0_BASELINE",
                    "source_commit_sha": PINNED_B0_SOURCE_SHA,
                    "source_tree_sha": b0_tree,
                    "source_inventory": b0_inventory,
                    "configuration": b0_configuration_at_source,
                    "evaluator_configuration": b0_evaluator_at_source,
                    "input_bundle_sha256": None,
                },
                "shared_input_plan": list(shared_input_plan),
                "method_specific_input_ids": [
                    "method.b0.source",
                    "method.b0.fitness_configuration",
                    "method.b0.legacy_evaluator",
                ],
            },
            "P": {
                **arm_records["P"],
                "method_identity": {
                    "status": "DEVELOPMENT_REVIEW_CANDIDATE_NOT_FROZEN",
                    "candidate_manifest": {
                        "path": P_CANDIDATE_PATH,
                        "sha256": sha256_file(root / P_CANDIDATE_PATH),
                        "identity_sha256": p_candidate["identity_sha256"],
                        "source_identity_sha256": p_candidate["source_identity_sha256"],
                        "configuration_sha256": p_candidate["configuration_sha256"],
                        "source_revision": p_candidate["source_revision"],
                    },
                    "input_bundle_sha256": None,
                },
                "shared_input_plan": list(shared_input_plan),
                "method_specific_input_ids": [
                    "method.p.review_candidate",
                    "method.p.traceability",
                    "method.p.algorithm_configuration",
                ],
            },
        },
        "runner": {
            "status": "DEVELOPMENT_RUNNER_CANDIDATE_NOT_APPROVED_FOR_MONO_E1",
            "version": "B0P_ISOLATED_RUNNER_V1",
            "source_commit_sha": runner_commit,
            "source_tree_sha": runner_tree,
            "source_files": runner_files,
            "container_image_digests": {"B0": None, "P": None},
            "resource_limits": {"cpus": MAX_CPUS, "memory": MAX_MEMORY, "pids": MAX_PIDS},
            "common_environment": common_env,
            "isolation": {
                "network": "DISABLED",
                "input_mounts": "EXPLICIT_ALLOWLIST_FILES_ONLY",
                "input_read_only": True,
                "root_filesystem_read_only": True,
                "git_metadata": "PROHIBITED",
                "scorer_or_oracle": "PROHIBITED",
                "reference_answers": "PROHIBITED",
                "hidden_target_labels": "PROHIBITED",
                "other_arm_outputs": "PROHIBITED",
                "broad_repository_mount": "PROHIBITED",
            },
        },
        "measurement_contract": {
            "status": "BOUNDARIES_SPECIFIED_VALUES_NOT_COLLECTED",
            "timing_boundary_id": "MONO_E1_TIMING_BOUNDARIES_V1",
            "boundaries": list(EXPECTED_TIMING_BOUNDARIES),
            "expected_fields": list(REQUIRED_TIMINGS),
            "arm_measurements": measurements,
        },
        "authority": {
            "policy_authority": "PENDING",
            "catalog_completeness": "UNKNOWN",
            "lifecycle_stage_authority": "PENDING",
            "method_p_independent_review": "PENDING",
            "scorer_custody": "NOT_ESTABLISHED",
            "reference_freeze": "NOT_READY",
            "G1": "INCOMPLETE",
            "G4": "NOT_AUTHORIZED",
        },
        "missing_prerequisites": [],
    }
    report = _assess_manifest(manifest, root, None, None, bundle_directories=None)
    manifest["preparation_status"] = report["preparation_status"]
    manifest["missing_prerequisites"] = report["blocked_prerequisites"]
    return manifest


def verify_mono_e1_preflight(
    manifest_path: Path | None = None,
    *,
    repository: Path | None = None,
    bundle_directories: Mapping[str, Path] | None = None,
    source_image_verifier: SourceImageVerifier | None = None,
    authority_verifier: AuthorityVerifier | None = None,
) -> dict[str, Any]:
    """Read and verify a versioned MONO-E1 preflight without mutating artifacts.

    Image and authority verifier callbacks are external trust boundaries. A
    manifest's own status string or digest cannot authenticate either claim.
    """
    root = (repository or Path(__file__).resolve().parents[3]).resolve(strict=True)
    path = manifest_path or root / MANIFEST_PATH
    if not path.is_absolute():
        path = root / path
    if path.is_symlink() or not path.is_file():
        return _invalid_report(["PREFLIGHT_MANIFEST_MISSING_OR_UNSAFE"])
    try:
        manifest = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
        validate_payload(SCHEMA_NAME, manifest)
    except (OSError, json.JSONDecodeError, ContractValidationError) as error:
        return _invalid_report([f"MANIFEST_CONTRACT_INVALID:{type(error).__name__}"])

    report = _assess_manifest(
        manifest,
        root,
        source_image_verifier,
        authority_verifier,
        bundle_directories=bundle_directories,
    )
    declared_status = manifest["preparation_status"]
    declared_blockers = manifest["missing_prerequisites"]
    if declared_status != report["preparation_status"]:
        report["contract_consistency_errors"].append("DECLARED_STATUS_DOES_NOT_MATCH_READBACK")
    if not set(report["blocked_prerequisites"]).issubset(set(declared_blockers)):
        report["contract_consistency_errors"].append("MANIFEST_OMITS_READBACK_BLOCKERS")
    if report["contract_consistency_errors"]:
        report["preparation_status"] = "INVALID"
        report["invalid_reasons"].extend(report["contract_consistency_errors"])
    report["experimental_go"] = "NO_GO"
    report["measured_run_status"] = "NOT_EXECUTED"
    report["scientific_readiness"] = "NOT_ESTABLISHED"
    report["non_authoritative"] = True
    return report


def _assess_manifest(
    manifest: Mapping[str, Any],
    repository: Path,
    source_image_verifier: SourceImageVerifier | None,
    authority_verifier: AuthorityVerifier | None,
    *,
    bundle_directories: Mapping[str, Path] | None,
) -> dict[str, Any]:
    invalid: list[str] = []
    incomplete: list[str] = []
    authority_pending: list[str] = []
    checks: dict[str, str] = {}

    try:
        _verify_architecture_pins(manifest, repository)
        checks["architecture_identity"] = "PASS_SOURCE_IDENTITY_ONLY"
    except (OSError, ProtocolError, subprocess.SubprocessError, ValueError):
        invalid.append("ARCHITECTURE_SOURCE_IDENTITY_MISMATCH")
        checks["architecture_identity"] = "FAIL"

    _verify_artifact_records(repository, manifest, invalid, checks)
    _verify_shared_input_identity(manifest, invalid, incomplete)
    _verify_method_identities(manifest, repository, invalid, incomplete)
    _verify_workload_and_fixture(manifest, repository, invalid, incomplete, checks)
    _verify_capabilities(manifest, incomplete, invalid)
    _verify_arm_inputs(manifest, invalid, incomplete, checks, bundle_directories)
    _verify_environment_and_limits(manifest, invalid, incomplete)
    _verify_isolation_contract(manifest, invalid)
    _verify_measurement_contract(manifest, invalid, incomplete, checks)
    _verify_image_bindings(manifest, source_image_verifier, invalid, incomplete, checks)

    authority = manifest["authority"]
    pending_fields = [
        ("policy_authority", {"APPROVED"}),
        ("catalog_completeness", {"APPROVED"}),
        ("lifecycle_stage_authority", {"APPROVED"}),
        ("method_p_independent_review", {"APPROVED"}),
        ("scorer_custody", {"ESTABLISHED"}),
        ("reference_freeze", {"VERIFIED"}),
        ("G1", {"COMPLETE"}),
        ("G4", {"AUTHORIZED"}),
    ]
    claimed_authority_ready = all(authority[key] in accepted for key, accepted in pending_fields)
    if claimed_authority_ready:
        if authority_verifier is None:
            authority_pending.append("EXTERNAL_AUTHORITY_VERIFICATION_REQUIRED")
        else:
            try:
                if not authority_verifier(authority):
                    invalid.append("EXTERNAL_AUTHORITY_VERIFICATION_FAILED")
                else:
                    checks["external_authority"] = "VERIFIED_BY_EXTERNAL_CALLBACK"
            except Exception:
                invalid.append("EXTERNAL_AUTHORITY_VERIFIER_ERROR")
    else:
        authority_pending.extend(
            f"{key.upper()}_{authority[key]}"
            for key, accepted in pending_fields
            if authority[key] not in accepted
        )
    checks.setdefault(
        "external_authority",
        "PENDING" if authority_pending else "NOT_REQUIRED_FOR_STRUCTURAL_CHECK",
    )

    blocked = sorted(set(incomplete + authority_pending))
    invalid_reasons = sorted(set(invalid))
    if invalid_reasons:
        status = "INVALID"
    elif incomplete:
        status = "INCOMPLETE"
    elif authority_pending:
        status = "AUTHORITY_PENDING"
    else:
        status = "STRUCTURALLY_VALID"

    return {
        "schema_version": "mono-e1-comparability-preflight-report-v1",
        "study_id": STUDY_ID,
        "preparation_status": status,
        "structural_checks": checks,
        "blocked_prerequisites": blocked,
        "invalid_reasons": invalid_reasons,
        "incomplete_reasons": sorted(set(incomplete)),
        "authority_pending_reasons": sorted(set(authority_pending)),
        "contract_consistency_errors": [],
        "experimental_go": "NO_GO",
        "measured_run_status": "NOT_EXECUTED",
        "scientific_readiness": "NOT_ESTABLISHED",
        "non_authoritative": True,
    }


def _verify_architecture_pins(manifest: Mapping[str, Any], root: Path) -> None:
    pair = manifest["source_pair"]
    if pair["before"] != BEFORE_SOURCE or pair["after"] != AFTER_SOURCE:
        raise ProtocolError("Architecture pair differs from the pinned MONO-E1 source pair")
    verify_source_revision(root, BEFORE_SOURCE["commit_sha"], BEFORE_SOURCE["repository_tree_sha"])
    verify_source_revision(root, AFTER_SOURCE["commit_sha"], AFTER_SOURCE["repository_tree_sha"])
    before_app = _git_text(root, "rev-parse", f"{BEFORE_SOURCE['commit_sha']}:app").strip()
    after_app = _git_text(root, "rev-parse", f"{AFTER_SOURCE['commit_sha']}:app").strip()
    if (before_app, after_app) != (
        BEFORE_SOURCE["application_tree_sha"],
        AFTER_SOURCE["application_tree_sha"],
    ):
        raise ProtocolError("Pinned application tree identities do not match Git")
    ancestor = subprocess.run(  # noqa: S603  # nosec B603 - fixed Git operation and full pinned SHAs
        [
            _git_executable(),
            "-C",
            str(root),
            "merge-base",
            "--is-ancestor",
            BEFORE_SOURCE["commit_sha"],
            AFTER_SOURCE["commit_sha"],
        ],
        capture_output=True,
        check=False,
    )
    if ancestor.returncode != 0:
        raise ProtocolError("A0.3 is not an ancestor of the pinned A0.4 source")

    expected_checkpoints = {
        "architecture/acceptance/a1/a0_3_canonical_checkpoint.json": (
            CANONICAL_A03_CHECKPOINT_SHA256
        ),
        "architecture/acceptance/a1/a0_4_canonical_checkpoint.json": (
            CANONICAL_A04_CHECKPOINT_SHA256
        ),
    }
    checkpoints = {record["path"]: record["sha256"] for record in pair["canonical_checkpoints"]}
    if checkpoints != expected_checkpoints:
        raise ProtocolError("Canonical checkpoint pins differ from the W0 source record")
    for relative, expected_sha in expected_checkpoints.items():
        actual = _safe_repo_file(root, relative)
        if sha256_file(actual) != expected_sha:
            raise ProtocolError(f"Canonical checkpoint digest mismatch: {relative}")
        payload = _read_json(actual)
        expected_source = BEFORE_SOURCE if "a0_3_" in relative else AFTER_SOURCE
        source_record = payload.get("source", payload)
        if (
            source_record.get("source_sha") != expected_source["commit_sha"]
            or source_record.get("repository_tree_sha") != expected_source["repository_tree_sha"]
            or source_record.get("application_tree_sha") != expected_source["application_tree_sha"]
            or payload.get("readback_status") != "PASS"
        ):
            raise ProtocolError(f"Canonical checkpoint source binding mismatch: {relative}")

    patch = pair["application_patch"]
    patch_file = _safe_repo_file(root, patch["path"])
    if patch["sha256"] != CANONICAL_A04_PATCH_SHA256 or sha256_file(patch_file) != patch["sha256"]:
        raise ProtocolError("Canonical A0.4 application patch digest mismatch")
    lineage = pair["lineage"]
    lineage_file = _safe_repo_file(root, lineage["evidence_path"])
    if (
        lineage["evidence_path"] != "experiments/execution/MONO_A1_PROTOCOL_V1_W0_ADDENDUM.md"
        or lineage["evidence_sha256"] != W0_ADDENDUM_SHA256
        or sha256_file(lineage_file) != W0_ADDENDUM_SHA256
    ):
        raise ProtocolError("W0 source-pair addendum digest mismatch")

    for observation in pair["observations"]:
        artifact = _safe_repo_file(root, observation["path"])
        if sha256_file(artifact) != observation["sha256"]:
            raise ProtocolError(f"Architecture observation digest mismatch: {observation['path']}")
        payload = _read_json(artifact)
        architecture = payload.get("architecture", {})
        if (
            architecture.get("expected_source_sha") != observation["architecture_source_sha"]
            or architecture.get("target_source_sha") != observation["architecture_source_sha"]
        ):
            observation_path = observation["path"]
            raise ProtocolError(f"Observation source mismatch: {observation_path}")
        checkpoint_relative = (
            "architecture/acceptance/a1/a0_3_canonical_checkpoint.json"
            if observation["architecture_source_sha"] == BEFORE_SOURCE["commit_sha"]
            else "architecture/acceptance/a1/a0_4_canonical_checkpoint.json"
        )
        checkpoint = _read_json(_safe_repo_file(root, checkpoint_relative))
        evaluator_records = dict(checkpoint.get("evaluators", {}))
        evaluator_records.update(checkpoint.get("non_applicable_evaluators", {}))
        expected = evaluator_records.get(observation["evaluator_id"])
        if (
            expected is None
            or expected.get("evidence_path") != Path(observation["path"]).name
            or expected.get("evidence_file_sha256") != observation["sha256"]
        ):
            raise ProtocolError(
                f"Observation is not pinned by its canonical checkpoint: {observation['path']}"
            )
    expected_observations = _checkpoint_observations(
        root,
        "architecture/acceptance/a1/a0_3_canonical_checkpoint.json",
        BEFORE_SOURCE,
    ) + _checkpoint_observations(
        root,
        "architecture/acceptance/a1/a0_4_canonical_checkpoint.json",
        AFTER_SOURCE,
    )
    if pair["observations"] != expected_observations:
        raise ProtocolError(
            "Architecture observations are missing or differ from canonical checkpoints"
        )


def _verify_artifact_records(
    root: Path,
    manifest: Mapping[str, Any],
    invalid: list[str],
    checks: dict[str, str],
) -> None:
    common = manifest["common_inputs"]
    records: list[Mapping[str, Any]] = []
    catalog = common["obligation_catalog"]
    records.append(catalog["artifact"])
    records.extend(common["policy"]["candidate_sources"])
    records.extend(item for item in common["architecture_facts"]["artifact_paths"])
    records.extend(
        [
            common["parent_fitness_configuration"]["configuration"],
            common["parent_fitness_configuration"]["evaluator_configuration"],
        ]
    )
    records.append(common["evaluator_capabilities"]["candidate_source"])
    records.extend(
        [
            common["workload"]["source_profile"],
            common["workload"]["runner_source"],
            common["workload"]["profile_validator_source"],
        ]
    )
    database = common["database_fixture"]
    records.append(database["migration"]["artifact"])
    records.extend(database["seed"]["source_artifacts"])
    records.extend(
        [
            common["environment"]["python_version_file"],
            common["environment"]["dependency_lock"],
        ]
    )
    records.extend(manifest["runner"]["source_files"])
    for record in records:
        if not isinstance(record, Mapping):
            # Architecture fact entries are paths; their digests are pinned in
            # the source-pair observations and canonical checkpoint records.
            continue
        try:
            actual = _safe_repo_file(root, str(record["path"]))
            if sha256_file(actual) != record["sha256"]:
                invalid.append(f"ARTIFACT_DIGEST_MISMATCH:{record['path']}")
        except (OSError, KeyError, ProtocolError):
            invalid.append(f"ARTIFACT_MISSING_OR_UNSAFE:{record.get('path', 'UNKNOWN')}")
    checks["pinned_input_artifacts"] = (
        "PASS_BYTES_ONLY" if not any(item.startswith("ARTIFACT_") for item in invalid) else "FAIL"
    )
    try:
        verify_source_revision(
            root,
            manifest["runner"]["source_commit_sha"],
            manifest["runner"]["source_tree_sha"],
        )
        for record in manifest["runner"]["source_files"]:
            if (
                _git_blob_sha256(root, manifest["runner"]["source_commit_sha"], record["path"])
                != record["sha256"]
            ):
                invalid.append(f"RUNNER_SOURCE_GIT_DIGEST_MISMATCH:{record['path']}")
    except (ProtocolError, OSError, subprocess.SubprocessError):
        invalid.append("RUNNER_SOURCE_IDENTITY_UNVERIFIED")
    if catalog["artifact"]["sha256"] != CATALOG_SHA256:
        invalid.append("OBLIGATION_CATALOG_PIN_MISMATCH")


def _verify_shared_input_identity(
    manifest: Mapping[str, Any], invalid: list[str], incomplete: list[str]
) -> None:
    arms = manifest["arms"]
    shared_fields = (
        "target_source_sha",
        "target_repository_tree_sha",
        "workload_spec_sha256",
        "database_fixture_id",
        "database_fixture_sha256",
        "migration_revision",
        "migration_sha256",
        "catalog_sha256",
        "policy_registry_sha256",
        "lifecycle_registry_sha256",
    )
    for field in shared_fields:
        left = arms["B0"][field]
        right = arms["P"][field]
        if left != right:
            invalid.append(f"B0_P_SHARED_INPUT_MISMATCH:{field}")
    if arms["B0"]["target_source_sha"] != AFTER_SOURCE["commit_sha"]:
        invalid.append("B0_TARGET_SOURCE_NOT_CANONICAL_A04")
    if arms["P"]["target_source_sha"] != AFTER_SOURCE["commit_sha"]:
        invalid.append("P_TARGET_SOURCE_NOT_CANONICAL_A04")
    if not arms["B0"]["workload_spec_sha256"] or not arms["P"]["workload_spec_sha256"]:
        incomplete.append("COMMON_WORKLOAD_IDENTITY_MISSING")
    if not arms["B0"]["database_fixture_sha256"] or not arms["P"]["database_fixture_sha256"]:
        incomplete.append("COMMON_DATABASE_FIXTURE_IDENTITY_MISSING")
    common = manifest["common_inputs"]
    if arms["B0"]["catalog_sha256"] != common["obligation_catalog"]["artifact"]["sha256"]:
        invalid.append("B0_CATALOG_IDENTITY_MISMATCH")
    if arms["P"]["catalog_sha256"] != common["obligation_catalog"]["artifact"]["sha256"]:
        invalid.append("P_CATALOG_IDENTITY_MISMATCH")
    parent_config_sha = common["parent_fitness_configuration"]["configuration"]["sha256"]
    parent_evaluator_sha = common["parent_fitness_configuration"]["evaluator_configuration"][
        "sha256"
    ]
    if arms["B0"]["method_identity"]["configuration"]["sha256"] != parent_config_sha:
        invalid.append("B0_PARENT_CONFIGURATION_IDENTITY_MISMATCH")
    if arms["B0"]["method_identity"]["evaluator_configuration"]["sha256"] != parent_evaluator_sha:
        invalid.append("B0_PARENT_EVALUATOR_IDENTITY_MISMATCH")
    if arms["B0"]["policy_registry_sha256"] != common["policy"]["candidate_sources"][1]["sha256"]:
        invalid.append("B0_POLICY_REGISTRY_IDENTITY_MISMATCH")
    if arms["P"]["policy_registry_sha256"] != common["policy"]["candidate_sources"][1]["sha256"]:
        invalid.append("P_POLICY_REGISTRY_IDENTITY_MISMATCH")
    if arms["B0"]["lifecycle_registry_sha256"] is None:
        incomplete.append("COMMON_LIFECYCLE_STAGE_REGISTRY_MISSING")


def _verify_method_identities(
    manifest: Mapping[str, Any], root: Path, invalid: list[str], incomplete: list[str]
) -> None:
    b0 = manifest["arms"]["B0"]["method_identity"]
    if b0["source_commit_sha"] != PINNED_B0_SOURCE_SHA:
        invalid.append("B0_SOURCE_COMMIT_MISMATCH")
    if [item["path"] for item in b0["source_inventory"]] != list(B0_SOURCE_FILES):
        invalid.append("B0_SOURCE_INVENTORY_PATHS_MISMATCH")
    if b0["configuration"]["path"] != FROZEN_B0_CONFIG_PATH:
        invalid.append("B0_CONFIGURATION_PATH_MISMATCH")
    if b0["evaluator_configuration"]["path"] != FROZEN_B0_EVALUATOR_PATH:
        invalid.append("B0_EVALUATOR_CONFIGURATION_PATH_MISMATCH")
    try:
        verify_source_revision(
            root,
            b0["source_commit_sha"],
            b0["source_tree_sha"],
        )
        for record in b0["source_inventory"]:
            if (
                _git_blob_sha256(root, record["source_commit_sha"], record["path"])
                != record["sha256"]
            ):
                invalid.append(f"B0_SOURCE_DIGEST_MISMATCH:{record['path']}")
        for field in ("configuration", "evaluator_configuration"):
            record = b0[field]
            if _git_blob_sha256(root, b0["source_commit_sha"], record["path"]) != record["sha256"]:
                invalid.append(f"B0_CONFIGURATION_DIGEST_MISMATCH:{field}")
    except (ProtocolError, OSError, subprocess.SubprocessError):
        invalid.append("B0_SOURCE_IDENTITY_UNVERIFIED")
    if b0["input_bundle_sha256"] is None:
        incomplete.append("B0_E1_INPUT_BUNDLE_AND_ALLOWLIST_MISSING")
    if b0["status"] != "FROZEN_E1_IDENTITY":
        incomplete.append("B0_IDENTITY_NOT_BOUND_TO_MONO_E1")

    p = manifest["arms"]["P"]["method_identity"]
    candidate = p["candidate_manifest"]
    try:
        candidate_path = _safe_repo_file(root, candidate["path"])
        candidate_bytes = candidate_path.read_bytes()
        candidate_payload = cast(dict[str, Any], json.loads(candidate_bytes))
        validate_payload("p_executable_candidate_identity_v1.schema.json", candidate_payload)
        digest_payload = {
            key: value for key, value in candidate_payload.items() if key != "identity_sha256"
        }
        if (
            sha256_bytes(canonical_json_bytes(digest_payload)) != candidate["identity_sha256"]
            or candidate_payload["identity_sha256"] != candidate["identity_sha256"]
            or candidate_payload["source_identity_sha256"] != candidate["source_identity_sha256"]
            or candidate_payload["configuration_sha256"] != candidate["configuration_sha256"]
            or sha256_bytes(candidate_bytes) != candidate["sha256"]
        ):
            invalid.append("P_CANDIDATE_SOURCE_OR_CONFIGURATION_DIGEST_MISMATCH")
        if candidate_payload["source_identity_sha256"] != P_CANDIDATE_SOURCE_SHA256:
            invalid.append("P_CANDIDATE_SOURCE_IDENTITY_PIN_MISMATCH")
        if candidate_payload["configuration_sha256"] != P_CANDIDATE_CONFIG_SHA256:
            invalid.append("P_CANDIDATE_CONFIGURATION_IDENTITY_PIN_MISMATCH")
        verify_source_revision(
            root,
            candidate_payload["source_revision"]["commit"],
            candidate_payload["source_revision"]["tree"],
        )
        _verify_candidate_files(root, candidate_payload)
    except (OSError, KeyError, json.JSONDecodeError, ContractValidationError, ProtocolError):
        invalid.append("P_CANDIDATE_IDENTITY_READBACK_FAILED")
    if candidate["identity_sha256"] != P_CANDIDATE_IDENTITY_SHA256:
        invalid.append("P_CANDIDATE_MANIFEST_IDENTITY_PIN_MISMATCH")
    if p["input_bundle_sha256"] is None:
        incomplete.append("P_E1_INPUT_BUNDLE_AND_ALLOWLIST_MISSING")
    if p["status"] != "FROZEN_E1_IDENTITY":
        incomplete.append("P_ALGORITHM_NOT_FROZEN_FOR_MONO_E1")


def _verify_candidate_files(root: Path, candidate: Mapping[str, Any]) -> None:
    revision = candidate["source_revision"]["commit"]
    groups = (
        candidate["implementation_files"],
        candidate["configuration_files"],
        candidate["review_basis_files"],
    )
    for entries in groups:
        for entry in entries:
            if (
                _git_blob_sha256(root, revision, entry["path"]) != entry["sha256"]
                or sha256_file(_safe_repo_file(root, entry["path"])) != entry["sha256"]
            ):
                raise ProtocolError(f"Method P pinned file differs: {entry['path']}")


def _verify_workload_and_fixture(
    manifest: Mapping[str, Any],
    root: Path,
    invalid: list[str],
    incomplete: list[str],
    checks: dict[str, str],
) -> None:
    common = manifest["common_inputs"]
    workload = common["workload"]
    actual_workload_sha = sha256_bytes(canonical_json_bytes(workload["definition"]))
    if actual_workload_sha != workload["definition_sha256"]:
        invalid.append("WORKLOAD_DEFINITION_DIGEST_MISMATCH")
    try:
        if workload["source_profile"]["sha256"] != sha256_file(
            _safe_repo_file(root, workload["source_profile"]["path"])
        ):
            invalid.append("WORKLOAD_SOURCE_PROFILE_DIGEST_MISMATCH")
    except (OSError, KeyError, ProtocolError):
        invalid.append("WORKLOAD_SOURCE_PROFILE_MISSING_OR_UNSAFE")
    if workload["definition"]["source_architecture_state"] != "A0_MONOLITH":
        incomplete.append("WORKLOAD_PROFILE_REQUIRES_A04_COMPATIBILITY_REVIEW")
    if workload["status"] != "APPROVED":
        incomplete.append("COMMON_WORKLOAD_NOT_APPROVED")
    reproducibility = workload["reproducibility"]
    if reproducibility["status"] != "VERIFIED" or reproducibility["request_trace_sha256"] is None:
        incomplete.append("COMMON_WORKLOAD_REPEATABILITY_NOT_ESTABLISHED")
    fixture = common["database_fixture"]
    fixture_definition = fixture["specification"]["definition"]
    if (
        sha256_bytes(canonical_json_bytes(fixture_definition))
        != fixture["specification"]["definition_sha256"]
    ):
        invalid.append("POSTGRES_FIXTURE_SPECIFICATION_DIGEST_MISMATCH")
    if fixture_definition["migration_revision"] != fixture["migration"]["revision"]:
        invalid.append("POSTGRES_FIXTURE_SPECIFICATION_MIGRATION_REVISION_MISMATCH")
    if fixture_definition["migration_sha256"] != fixture["migration"]["artifact"]["sha256"]:
        invalid.append("POSTGRES_FIXTURE_SPECIFICATION_MIGRATION_DIGEST_MISMATCH")
    if fixture["status"] != "VERIFIED":
        incomplete.append("POSTGRES_FIXTURE_NOT_CREATED_AND_VERIFIED")
    if fixture["fixture_id"] is None or fixture["fixture_sha256"] is None:
        incomplete.append("POSTGRES_FIXTURE_IDENTITY_MISSING")
    if fixture["seed"]["seed_id"] is None or fixture["seed"]["expected_fingerprint_sha256"] is None:
        incomplete.append("POSTGRES_SEED_IDENTITY_OR_FINGERPRINT_MISSING")
    if fixture["destructive_reset_performed"]:
        invalid.append("PREFLIGHT_MUST_NOT_RESET_A_DATABASE")
    arms = manifest["arms"]
    for arm in ("B0", "P"):
        if arms[arm]["workload_spec_sha256"] != workload["definition_sha256"]:
            invalid.append(f"{arm}_WORKLOAD_DIGEST_MISMATCH")
        if arms[arm]["database_fixture_id"] != fixture["fixture_id"]:
            invalid.append(f"{arm}_FIXTURE_ID_MISMATCH")
        if arms[arm]["database_fixture_sha256"] != fixture["fixture_sha256"]:
            invalid.append(f"{arm}_FIXTURE_DIGEST_MISMATCH")
        if arms[arm]["migration_sha256"] != fixture["migration"]["artifact"]["sha256"]:
            invalid.append(f"{arm}_MIGRATION_IDENTITY_MISMATCH")
        if arms[arm]["migration_revision"] != fixture["migration"]["revision"]:
            invalid.append(f"{arm}_MIGRATION_REVISION_MISMATCH")
    checks["workload"] = "PINNED_PROPOSAL_ONLY" if workload["status"] != "APPROVED" else "PASS"
    checks["postgres_fixture"] = "NOT_CREATED" if fixture["status"] != "VERIFIED" else "PASS"


def _verify_capabilities(
    manifest: Mapping[str, Any], incomplete: list[str], invalid: list[str]
) -> None:
    capability_input = manifest["common_inputs"]["evaluator_capabilities"]
    required = set(capability_input["required_ids"])
    b0 = set(manifest["arms"]["B0"]["evaluator_capability_ids"])
    p = set(manifest["arms"]["P"]["evaluator_capability_ids"])
    if b0 != p:
        invalid.append("B0_P_EVALUATOR_CAPABILITIES_INCOMPATIBLE")
    missing = (required - b0) | (required - p)
    if not required:
        incomplete.append("REQUIRED_EVALUATOR_CAPABILITY_DENOMINATOR_MISSING")
    if missing:
        incomplete.append("MISSING_EVALUATOR_CAPABILITIES:" + ",".join(sorted(missing)))
    if capability_input["status"] != "APPROVED":
        incomplete.append("COMMON_EVALUATOR_CAPABILITY_INVENTORY_NOT_APPROVED")


def _verify_arm_inputs(
    manifest: Mapping[str, Any],
    invalid: list[str],
    incomplete: list[str],
    checks: dict[str, str],
    bundle_directories: Mapping[str, Path] | None,
) -> None:
    arms = manifest["arms"]
    inventories: dict[str, list[dict[str, Any]]] = {}
    for arm in ("B0", "P"):
        inventory = arms[arm]["input_inventory"]
        shared = inventory["shared_inputs"]
        specific = inventory["method_specific_inputs"]
        entries = list(shared) + list(specific)
        if inventory["shared_input_ids"] != arms[arm]["shared_input_plan"]:
            incomplete.append(f"{arm}_SHARED_INPUT_INVENTORY_INCOMPLETE")
        if inventory["method_specific_input_ids"] != arms[arm]["method_specific_input_ids"]:
            incomplete.append(f"{arm}_METHOD_SPECIFIC_INPUT_INVENTORY_INCOMPLETE")
        paths = [entry["path"] for entry in entries]
        if len(paths) != len(set(paths)):
            invalid.append(f"{arm}_ALLOWLIST_DUPLICATE_PATH")
        for entry in entries:
            if _input_path_is_forbidden(entry["path"], arm):
                invalid.append(f"{arm}_FORBIDDEN_INPUT_PATH:{entry['path']}")
        inventories[arm] = entries
        if not entries or inventory["allowlist_sha256"] is None:
            incomplete.append(f"{arm}_ALLOWLIST_MISSING")
        else:
            actual_allowlist = bundle_sha256(entries)
            if actual_allowlist != inventory["allowlist_sha256"]:
                invalid.append(f"{arm}_ALLOWLIST_DIGEST_MISMATCH")
        if inventory["status"] != "VERIFIED":
            incomplete.append(f"{arm}_INPUT_INVENTORY_NOT_VERIFIED")
        if bundle_directories and arm in bundle_directories:
            try:
                if arm == "B0":
                    actual_manifest = verify_method_bundle(
                        bundle_directories[arm], expected_method_id=cast(MethodId, arm)
                    )
                else:
                    actual_manifest = verify_method_bundle_v3(
                        bundle_directories[arm], expected_method_id="P"
                    )
                actual_files = actual_manifest["files"]
                if actual_files != entries:
                    invalid.append(f"{arm}_BUNDLE_DOES_NOT_MATCH_DECLARED_ALLOWLIST")
                if arms[arm]["method_identity"]["input_bundle_sha256"] != actual_manifest.get(
                    "bundle_sha256"
                ):
                    invalid.append(f"{arm}_BUNDLE_DIGEST_MISMATCH")
            except (OSError, ProtocolError, ContractValidationError, ValueError):
                invalid.append(f"{arm}_BUNDLE_VALIDATION_FAILED")
        elif inventory["status"] == "VERIFIED":
            incomplete.append(f"{arm}_BUNDLE_READBACK_NOT_SUPPLIED")
    if inventories["B0"] and inventories["P"]:
        b0_shared = arms["B0"]["input_inventory"]["shared_inputs"]
        p_shared = arms["P"]["input_inventory"]["shared_inputs"]
        if b0_shared != p_shared:
            invalid.append("B0_P_SHARED_ALLOWLIST_INPUTS_DIFFER")
    if arms["B0"]["shared_input_plan"] != arms["P"]["shared_input_plan"]:
        invalid.append("B0_P_SHARED_INPUT_PLAN_DIFFERS")
    if any(item.endswith("_ALLOWLIST_DIGEST_MISMATCH") for item in invalid):
        checks["arm_allowlists"] = "FAIL"
    elif any(
        "ALLOWLIST_MISSING" in item or "INVENTORY_NOT_VERIFIED" in item for item in incomplete
    ):
        checks["arm_allowlists"] = "INCOMPLETE"
    else:
        checks["arm_allowlists"] = "PASS"


def _verify_environment_and_limits(
    manifest: Mapping[str, Any], invalid: list[str], incomplete: list[str]
) -> None:
    runner = manifest["runner"]
    arms = manifest["arms"]
    if arms["B0"]["shared_environment"] != arms["P"]["shared_environment"]:
        invalid.append("B0_P_SHARED_ENVIRONMENT_MISMATCH")
    if arms["B0"]["shared_environment"] != runner["common_environment"]:
        invalid.append("ARM_ENVIRONMENT_DIFFERS_FROM_RUNNER")
    if arms["B0"]["resource_limits"] != arms["P"]["resource_limits"]:
        invalid.append("B0_P_RESOURCE_LIMITS_MISMATCH")
    if arms["B0"]["resource_limits"] != runner["resource_limits"]:
        invalid.append("ARM_RESOURCE_LIMITS_DIFFER_FROM_RUNNER")
    common = manifest["common_inputs"]["environment"]
    if common["runtime_image_status"] != "PINNED":
        incomplete.append("RUNTIME_DEPENDENCY_IMAGE_NOT_PINNED")
    if not common["dependency_lock"]["sha256"] or not common["python_version"]:
        incomplete.append("RUNTIME_DEPENDENCY_VERSIONS_INCOMPLETE")
    for arm in ("B0", "P"):
        if set(arms[arm]["method_specific_environment"]).intersection(
            arms[arm]["shared_environment"]
        ):
            invalid.append(f"{arm}_METHOD_SPECIFIC_ENV_OVERRIDES_SHARED_VALUE")
        image = arms[arm]["image_provenance"]["image_digest"]
        recorded_image = runner["container_image_digests"][arm]
        if image != recorded_image:
            invalid.append(f"{arm}_RUNNER_AND_ATTESTED_IMAGE_DIGEST_MISMATCH")


def _verify_isolation_contract(manifest: Mapping[str, Any], invalid: list[str]) -> None:
    isolation = manifest["runner"]["isolation"]
    required_values = {
        "network": "DISABLED",
        "input_mounts": "EXPLICIT_ALLOWLIST_FILES_ONLY",
        "input_read_only": True,
        "root_filesystem_read_only": True,
        "git_metadata": "PROHIBITED",
        "scorer_or_oracle": "PROHIBITED",
        "reference_answers": "PROHIBITED",
        "hidden_target_labels": "PROHIBITED",
        "other_arm_outputs": "PROHIBITED",
        "broad_repository_mount": "PROHIBITED",
    }
    if isolation != required_values:
        invalid.append("ISOLATION_CONTRACT_MISMATCH")


def _verify_measurement_contract(
    manifest: Mapping[str, Any],
    invalid: list[str],
    incomplete: list[str],
    checks: dict[str, str],
) -> None:
    contract = manifest["measurement_contract"]
    fields = [item["field"] for item in contract["boundaries"]]
    if (
        fields != list(REQUIRED_TIMINGS)
        or contract["expected_fields"] != list(REQUIRED_TIMINGS)
        or contract["boundaries"] != EXPECTED_TIMING_BOUNDARIES
    ):
        invalid.append("MEASUREMENT_FIELDS_MISMATCH")
    if contract["timing_boundary_id"] != "MONO_E1_TIMING_BOUNDARIES_V1":
        invalid.append("MEASUREMENT_BOUNDARY_ID_MISMATCH")
    for arm in ("B0", "P"):
        record = contract["arm_measurements"][arm]
        if record["timing_boundary_id"] != contract["timing_boundary_id"]:
            invalid.append(f"{arm}_TIMING_BOUNDARY_INCOMPATIBLE")
        for metric in REQUIRED_TIMINGS:
            value = record["timings_ns"][metric]
            if value is not None and (type(value) is not int or value < 0):
                invalid.append(f"{arm}_TIMING_VALUE_INVALID:{metric}")
        for metric in ("cpu_time_ns", "peak_rss_bytes"):
            sample = record["resource_metrics"][metric]
            if sample["status"] == "NOT_COLLECTED" and sample["value"] is not None:
                invalid.append(f"{arm}_{metric.upper()}_MISSING_DATA_MUST_REMAIN_NULL")
            if sample["status"] == "COLLECTED" and (
                type(sample["value"]) is not int or sample["value"] < 0
            ):
                invalid.append(f"{arm}_{metric.upper()}_COLLECTION_VALUE_INVALID")
    timing_result = assess_mono_rq3(
        timing_boundary_ids={
            arm: contract["arm_measurements"][arm]["timing_boundary_id"] for arm in ("B0", "P")
        },
        timings_ns={
            arm: {
                "adaptation_ns": contract["arm_measurements"][arm]["timings_ns"]["adaptation_ns"],
                "evaluator_ns": contract["arm_measurements"][arm]["timings_ns"][
                    "evaluator_execution_ns"
                ],
                "verification_ns": contract["arm_measurements"][arm]["timings_ns"][
                    "verification_ns"
                ],
                "total_ns": contract["arm_measurements"][arm]["timings_ns"]["total_execution_ns"],
            }
            for arm in ("B0", "P")
        },
        source_image_provenance={arm: {"status": "NOT_VERIFIED"} for arm in ("B0", "P")},
        architecture_source_sha=AFTER_SOURCE["commit_sha"],
        resources=None,
    )
    if timing_result["status"] == "UNKNOWN" and any(
        "TIMING_BOUNDARY" in reason for reason in timing_result["reason_codes"]
    ):
        incomplete.append("TIMING_BOUNDARIES_INCOMPATIBLE")
    checks["measurement_boundaries"] = (
        "PASS_BOUNDARIES_ONLY" if not any("TIMING_BOUNDARY" in item for item in invalid) else "FAIL"
    )


def _verify_image_bindings(
    manifest: Mapping[str, Any],
    verifier: SourceImageVerifier | None,
    invalid: list[str],
    incomplete: list[str],
    checks: dict[str, str],
) -> None:
    all_verified = True
    for arm in ("B0", "P"):
        record = manifest["arms"][arm]["image_provenance"]
        if record["status"] == "MISSING" or record["image_digest"] is None:
            incomplete.append(f"{arm}_CONTAINER_IMAGE_DIGEST_MISSING")
            all_verified = False
            continue
        if record["source_sha"] != AFTER_SOURCE["commit_sha"]:
            invalid.append(f"{arm}_SOURCE_TO_IMAGE_BINDING_MISMATCH")
            all_verified = False
            continue
        if (
            record["status"] != "VERIFIED"
            or not record["external_verifier_id"]
            or not record["verification_evidence_sha256"]
        ):
            incomplete.append(f"{arm}_SOURCE_TO_IMAGE_VERIFIER_EVIDENCE_MISSING")
            all_verified = False
            continue
        if not validate_source_image_provenance(
            {
                "status": "VERIFIED",
                "source_sha": record["source_sha"],
                "image_digest": record["image_digest"],
                "attestation_sha256": record["attestation_sha256"] or "",
            },
            AFTER_SOURCE["commit_sha"],
        ):
            incomplete.append(f"{arm}_SOURCE_TO_IMAGE_ATTESTATION_INCOMPLETE")
            all_verified = False
            continue
        if verifier is None:
            incomplete.append(f"{arm}_SOURCE_TO_IMAGE_ATTESTATION_NOT_EXTERNALLY_VERIFIED")
            all_verified = False
            continue
        try:
            verified = verifier(record)
        except Exception:
            verified = False
        if not verified:
            invalid.append(f"{arm}_EXTERNAL_IMAGE_VERIFICATION_FAILED")
            all_verified = False
    checks["source_to_image"] = "EXTERNALLY_VERIFIED" if all_verified else "UNVERIFIED"


def _input_path_is_forbidden(value: str, arm: str) -> bool:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or ".." in path.parts or "\\" in value:
        return True
    parts = {part.lower() for part in path.parts}
    if parts.intersection(FORBIDDEN_PATH_PARTS):
        return True
    normalized = [
        "".join(character for character in part.lower() if character.isalnum())
        for part in path.parts
    ]
    other_arm = "p" if arm == "B0" else "b0"
    output_markers = {"output", "outputs", "result", "results", "runoutput", "runoutputs"}
    if "crossarm" in normalized:
        return True
    if any(
        token in {other_arm, f"method{other_arm}"}
        or token.startswith(f"{other_arm}output")
        or token.startswith(f"method{other_arm}output")
        for token in normalized
    ):
        return True
    return any(
        left in {other_arm, f"method{other_arm}"}
        and right in output_markers
        or left in output_markers
        and right in {other_arm, f"method{other_arm}"}
        for left, right in zip(normalized, normalized[1:], strict=False)
    )


def _checkpoint_observations(
    root: Path, checkpoint_relative: str, source: Mapping[str, str]
) -> list[dict[str, Any]]:
    checkpoint_path = _safe_repo_file(root, checkpoint_relative)
    checkpoint = _read_json(checkpoint_path)
    records: list[dict[str, Any]] = []
    evaluator_maps = [checkpoint.get("evaluators", {})]
    if checkpoint.get("non_applicable_evaluators"):
        evaluator_maps.append(checkpoint["non_applicable_evaluators"])
    for evaluator_map in evaluator_maps:
        for evaluator_id, record in evaluator_map.items():
            evidence_path = record.get("evidence_path")
            if not isinstance(evidence_path, str):
                continue
            relative = f"architecture/acceptance/a1/{evidence_path}"
            artifact = _safe_repo_file(root, relative)
            records.append(
                {
                    "architecture_source_sha": source["commit_sha"],
                    "evaluator_id": evaluator_id,
                    "path": relative,
                    "sha256": sha256_file(artifact),
                    "scope": "ENGINEERING_OBSERVATION_ONLY",
                }
            )
    return records


def _artifact_record(root: Path, relative: str) -> dict[str, Any]:
    path = _safe_repo_file(root, relative)
    return {
        "path": PurePosixPath(relative).as_posix(),
        "sha256": sha256_file(path),
    }


def _git_blob_record(root: Path, revision: str, relative: str) -> dict[str, Any]:
    content = _git_blob(root, revision, relative)
    return {
        "source_commit_sha": revision,
        "path": relative,
        "sha256": sha256_bytes(content),
        "size_bytes": len(content),
    }


def _git_blob_sha256(root: Path, revision: str, relative: str) -> str:
    return sha256_bytes(_git_blob(root, revision, relative))


def _git_blob(root: Path, revision: str, relative: str) -> bytes:
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts or "\\" in relative:
        raise ProtocolError("Git blob path is unsafe")
    if len(revision) != 40 or any(char not in "0123456789abcdef" for char in revision):
        raise ProtocolError("Git blob revision must be a full lowercase commit SHA")
    try:
        result = subprocess.run(  # noqa: S603  # nosec B603 - validated full SHA and safe relative Git path
            [_git_executable(), "-C", str(root), "show", f"{revision}:{path.as_posix()}"],
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ProtocolError("Pinned Git blob is unavailable") from error
    return result.stdout


def _git_text(root: Path, *arguments: str) -> str:
    try:
        return subprocess.run(  # noqa: S603  # nosec B603 - fixed internal Git arguments, no shell
            [_git_executable(), "-C", str(root), *arguments],
            capture_output=True,
            check=True,
            text=True,
        ).stdout
    except (OSError, subprocess.SubprocessError) as error:
        raise ProtocolError("Required Git readback failed") from error


def _git_executable() -> str:
    from shutil import which

    executable = which("git")
    if executable is None:
        raise ProtocolError("Git executable is unavailable")
    return executable


def _safe_repo_file(root: Path, relative: str) -> Path:
    path = PurePosixPath(relative)
    if path.is_absolute() or not path.parts or ".." in path.parts or "\\" in relative:
        raise ProtocolError("Repository artifact path is unsafe")
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise ProtocolError("Repository artifact paths cannot traverse symlinks")
    resolved = current.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise ProtocolError("Repository artifact path escapes its root")
    if not resolved.is_file():
        raise ProtocolError("Repository artifact must be a regular file")
    return resolved


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ProtocolError(f"Expected a JSON object in {path.name}")
    return cast(dict[str, Any], payload)


def _read_yaml_profile(path: Path) -> dict[str, Any]:
    import yaml

    profile = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(profile, dict):
        raise ProtocolError("Pinned workload profile must contain a YAML mapping")
    return cast(dict[str, Any], profile)


def _invalid_report(reasons: Sequence[str]) -> dict[str, Any]:
    return {
        "schema_version": "mono-e1-comparability-preflight-report-v1",
        "study_id": STUDY_ID,
        "preparation_status": "INVALID",
        "structural_checks": {},
        "blocked_prerequisites": [],
        "invalid_reasons": sorted(set(reasons)),
        "incomplete_reasons": [],
        "authority_pending_reasons": [],
        "contract_consistency_errors": [],
        "experimental_go": "NO_GO",
        "measured_run_status": "NOT_EXECUTED",
        "scientific_readiness": "NOT_ESTABLISHED",
        "non_authoritative": True,
    }


def main() -> int:
    """Run the read-only preflight and print one deterministic JSON report."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--repository", type=Path, default=None)
    args = parser.parse_args()
    report = verify_mono_e1_preflight(args.manifest, repository=args.repository)
    sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return 1 if report["preparation_status"] == "INVALID" else 0


if __name__ == "__main__":
    raise SystemExit(main())
