"""Read-only ΔA5 readiness checks; never executes B0, Ψ, evaluators, or scoring."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess  # nosec B404 - only fixed read-only local Git identity queries
import tempfile
import zipfile
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any

import jsonschema
import yaml

PACKAGE_RELATIVE = Path(
    "experiments/execution/mono-ci-b0-psi-delta-a5-v1/DELTA_A5_READINESS_V2.json"
)
SCHEMA_RELATIVE = Path(
    "experiments/execution/schemas/mono_ci_b0_psi_delta_a5_readiness_v2.schema.json"
)
EXPECTED_SOURCE_IDENTITIES = (
    (
        "A0_4_REPORT_QUERY_PORT",
        "d3101c0d3aa9b7b709253b6ec7518416f05f65b9",
        "2b436e0aaf09403ea516d73d20a466a122f86592",
        "007196f68652bc13f6798805793ffdfae96f95f7",
        "architecture/states/A0_4_REPORT_QUERY_PORT.yaml",
        "9c981442a34830bdc44d77ffc17de5b9f832b0b261d0d92f28bd15dc567febd9",
    ),
    (
        "A0_5_MODULE_DATA_OWNERSHIP",
        "a349d19fb89b577e6799e9736ed4ce0acc572166",
        "97c060cc26313a879f0940a178d42e422cc4d188",
        "007196f68652bc13f6798805793ffdfae96f95f7",
        "architecture/states/A0_5_MODULE_DATA_OWNERSHIP.yaml",
        "2906216b212b450706368d44233488fd638d2e7af789980ea2abf02740a04ae8",
    ),
)
METHOD_CANDIDATE_BASE_SHA = "08e0a7269311ba6ec33882365deb97d4c3f38573"
HISTORICAL_RUN_SOURCE_SHA = "a349d19fb89b577e6799e9736ed4ce0acc572166"
SEMANTIC_INVENTORY_CLAIM_IDS = {
    "ARCHIVE_IDENTITY_AND_MEMBER_INTEGRITY",
    "METHOD_OUTCOME_AND_OUTPUT_DIGESTS",
    "EVALUATOR_RESULTS_AND_SOURCE_BINDINGS",
    "PROBE_SOURCE_AND_REPRODUCTION",
    "HISTORICAL_TIMING_SAMPLES",
}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_repo_path(value: str) -> Path:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("unsafe repository-relative path")
    return Path(*path.parts)


def _run_git(repository: Path, *args: str) -> bytes:
    git_binary = shutil.which("git")
    if git_binary is None:
        raise ValueError("git executable unavailable")
    result = subprocess.run(  # nosec B603 - fixed read-only local Git queries  # noqa: S603
        [git_binary, "-C", str(repository), *args],
        check=False,
        capture_output=True,
        env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "C.UTF-8"},
    )
    if result.returncode:
        raise ValueError("git object read failed")
    return result.stdout


def _git_text(repository: Path, *args: str) -> str:
    return _run_git(repository, *args).decode("utf-8").strip()


def _git_bytes(repository: Path, *args: str) -> bytes:
    return _run_git(repository, *args)


def evaluate_applicability_profile(
    profile: dict[str, Any],
    *,
    catalog_ids: list[str],
    catalog_sha256: str,
    state_manifest_sha256: str,
    authority_verified: bool = False,
    independent_review_verified: bool = False,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Apply fail-closed applicability semantics to a proposed profile.

    The two verification arguments must come from an external signature/authority
    verifier. A status string in the profile is not itself authorization.
    """
    current_date = as_of or date.today()
    issues: list[str] = []
    rows = profile.get("rows")
    if not isinstance(rows, list):
        rows = []
        issues.append("ROWS_MISSING")
    by_id: dict[str, dict[str, Any]] = {}
    duplicate_ids: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("obligation_id"), str):
            issues.append("ROW_INVALID")
            continue
        obligation_id = row["obligation_id"]
        if obligation_id in by_id:
            duplicate_ids.add(obligation_id)
        by_id[obligation_id] = row
    if duplicate_ids:
        issues.append("DUPLICATE_OBLIGATION_ROWS")
    if profile.get("catalog_sha256") != catalog_sha256:
        issues.append("CATALOG_DIGEST_STALE")
    if profile.get("state_manifest_sha256") != state_manifest_sha256:
        issues.append("STATE_SOURCE_STALE")
    if profile.get("catalog_closure_status") != "COMPLETE":
        issues.append("CATALOG_CLOSURE_UNRESOLVED")
    if set(by_id) != set(catalog_ids):
        issues.append("CATALOG_INVENTORY_INCOMPLETE")
    valid_until = profile.get("valid_until")
    stale = False
    if valid_until is not None:
        try:
            stale = date.fromisoformat(valid_until) < current_date
        except (TypeError, ValueError):
            stale = True
            issues.append("VALIDITY_DATE_INVALID")
    if stale:
        issues.append("PROFILE_OUTDATED")
    if not authority_verified:
        issues.append("AUTHORITY_UNVERIFIED")
    if not independent_review_verified:
        issues.append("INDEPENDENT_REVIEW_UNVERIFIED")
    trusted = authority_verified and independent_review_verified
    source_current = (
        profile.get("catalog_sha256") == catalog_sha256
        and profile.get("state_manifest_sha256") == state_manifest_sha256
    )
    complete = (
        profile.get("catalog_closure_status") == "COMPLETE"
        and set(by_id) == set(catalog_ids)
        and not duplicate_ids
    )
    classifications: dict[str, dict[str, Any]] = {}
    for obligation_id in catalog_ids:
        row = by_id.get(obligation_id)
        if row is None:
            classifications[obligation_id] = {
                "applicability": "UNKNOWN",
                "mandatory_status": "UNKNOWN",
                "lifecycle_stages": [],
                "reason": "MISSING_ROW",
            }
            continue
        conflict = bool(row.get("conflict"))
        row_applicability = row.get("applicability")
        row_mandatory = row.get("mandatory_status")
        stages = row.get("lifecycle_stages")
        row_stage_status = row.get("lifecycle_status")
        row_resolvable = (
            trusted
            and source_current
            and complete
            and not stale
            and not conflict
            and row_applicability in {"ACTIVE", "INACTIVE"}
            and row_mandatory in {"MANDATORY", "OPTIONAL"}
            and row_stage_status in {"RESOLVED", "NOT_REQUIRED"}
            and isinstance(stages, list)
        )
        if conflict:
            issues.append("CONFLICT_UNRESOLVED")
        if not row_resolvable:
            classifications[obligation_id] = {
                "applicability": "UNKNOWN",
                "mandatory_status": "UNKNOWN",
                "lifecycle_stages": [],
                "reason": "REQUIRED_EVIDENCE_UNRESOLVED",
            }
        else:
            classifications[obligation_id] = {
                "applicability": row_applicability,
                "mandatory_status": row_mandatory,
                "lifecycle_stages": stages,
                "reason": "VERIFIED_PROFILE_INPUTS",
            }
    scoring_authorized = bool(
        trusted
        and source_current
        and complete
        and not stale
        and not duplicate_ids
        and len(classifications) == len(catalog_ids)
        and all(
            item["applicability"] != "UNKNOWN" and item["mandatory_status"] != "UNKNOWN"
            for item in classifications.values()
        )
    )
    return {
        "profile_status": "RESOLVED_FOR_REVIEW" if scoring_authorized else "UNKNOWN",
        "scoring_authorized": scoring_authorized,
        "classifications": classifications,
        "issues": sorted(set(issues)),
    }


def classify_semantic_inventory_row(row: dict[str, Any]) -> tuple[str, str]:
    """Classify a review-inventory cell without treating capability as coverage."""
    representation_id = row.get("representation_id")
    mapping_status = row.get("declared_mapping_status")
    if representation_id is None:
        return (
            "EVALUATOR_CAPABILITY_CANDIDATE",
            "NOT_COUNTED_NO_MATERIALIZED_REPRESENTATION",
        )
    if not isinstance(representation_id, str) or not representation_id.strip():
        raise ValueError("representation identifier must be non-empty or null")
    if mapping_status == "NO_DECLARED_PAIR_MAPPING":
        return (
            "UNDECLARED_REPRESENTATION_OBLIGATION_MAPPING",
            "NOT_COUNTED_UNDECLARED_MAPPING",
        )
    if mapping_status == "ENGINEERING_DECLARATION_ONLY":
        return (
            "PROPOSED_REPRESENTATION_OBLIGATION_PAIR",
            "NOT_COUNTED_PAIR_VALIDITY_UNKNOWN",
        )
    raise ValueError("representation-obligation mapping status is unresolved or unsupported")


def is_verified_semantic_coverage(row: dict[str, Any]) -> bool:
    """Return true only for an authorized, independently reviewed exact pair."""
    representation_id = row.get("representation_id")
    return bool(
        isinstance(representation_id, str)
        and representation_id.strip()
        and row.get("declared_mapping_status") == "NORMATIVELY_AUTHORIZED"
        and row.get("pair_validity") == "VALID"
        and row.get("independent_review_status") == "INDEPENDENTLY_REVIEWED"
        and isinstance(row.get("evidence_reference"), str)
        and row["evidence_reference"].strip()
    )


def validate_semantic_inventory(matrix: list[dict[str, Any]]) -> tuple[list[str], dict[str, int]]:
    """Check inventory identities and classes without creating a scoring denominator."""
    errors: list[str] = []
    identities: dict[tuple[Any, ...], dict[str, Any]] = {}
    evaluator_obligation_pairs: set[tuple[str, str]] = set()
    counts = {
        "proposed_representation_obligation_pairs": 0,
        "undeclared_representation_obligation_mappings": 0,
        "evaluator_capability_candidates": 0,
        "verified_coverage_pairs": 0,
    }
    for row in matrix:
        if not isinstance(row, dict):
            errors.append("SEMANTIC_INVENTORY_ROW_INVALID")
            continue
        try:
            inventory_class, coverage_status = classify_semantic_inventory_row(row)
        except ValueError:
            errors.append("SEMANTIC_INVENTORY_CLASSIFICATION_INVALID")
            continue
        if row.get("inventory_class") != inventory_class:
            errors.append("SEMANTIC_INVENTORY_CLASS_MISMATCH")
        if row.get("coverage_status") != coverage_status:
            errors.append("SEMANTIC_INVENTORY_COVERAGE_STATUS_MISMATCH")
        if row.get("pair_validity") != "UNKNOWN":
            errors.append("UNREVIEWED_PAIR_PROMOTION")
        if is_verified_semantic_coverage(row):
            counts["verified_coverage_pairs"] += 1
        else:
            counts_key = {
                "PROPOSED_REPRESENTATION_OBLIGATION_PAIR": (
                    "proposed_representation_obligation_pairs"
                ),
                "UNDECLARED_REPRESENTATION_OBLIGATION_MAPPING": (
                    "undeclared_representation_obligation_mappings"
                ),
                "EVALUATOR_CAPABILITY_CANDIDATE": "evaluator_capability_candidates",
            }[inventory_class]
            counts[counts_key] += 1
        pair = (str(row.get("evaluator_id")), str(row.get("obligation_id")))
        if pair in evaluator_obligation_pairs:
            errors.append("SEMANTIC_MATRIX_DUPLICATE_EVALUATOR_OBLIGATION_CELL")
        evaluator_obligation_pairs.add(pair)
        states = tuple(row.get("architecture_states", []))
        representation_id = row.get("representation_id")
        if representation_id is None:
            identity = (
                states,
                row.get("criterion_id"),
                None,
                row.get("evaluator_id"),
                row.get("obligation_id"),
            )
        else:
            identity = (
                states,
                row.get("criterion_id"),
                representation_id,
                row.get("obligation_id"),
            )
        previous = identities.get(identity)
        if previous is not None:
            issue = (
                "SEMANTIC_INVENTORY_IDENTITY_CONFLICT"
                if previous != row
                else "SEMANTIC_INVENTORY_DUPLICATE_IDENTITY"
            )
            errors.append(issue)
        else:
            identities[identity] = row
    return sorted(set(errors)), counts


def verify_historical_archive(
    repository: Path, package: dict[str, Any], archive_path: Path | None
) -> dict[str, Any]:
    """Optionally replay a supplied pinned archive; never fetches historical artifacts."""
    historical = package["historical_development_run"]
    expected_digest = historical["inner_archive_sha256"]
    expected_source = historical["source_revision_sha"]
    if archive_path is None:
        return {
            "status": "NOT_EXECUTED",
            "expected_archive_sha256": expected_digest,
            "observed_archive_sha256": None,
            "expected_source_revision_sha": expected_source,
            "observed_source_revision_sha": None,
            "verified_claim_ids": [],
            "errors": [],
        }
    original_archive = archive_path.expanduser().absolute()
    try:
        if original_archive.is_symlink() or not original_archive.is_file():
            return {
                "status": "NOT_VERIFIED",
                "expected_archive_sha256": expected_digest,
                "observed_archive_sha256": None,
                "expected_source_revision_sha": expected_source,
                "observed_source_revision_sha": None,
                "verified_claim_ids": [],
                "errors": ["HISTORICAL_ARCHIVE_UNAVAILABLE_OR_UNSAFE"],
            }
        observed_digest = _sha256_bytes(original_archive.read_bytes())
    except OSError:
        return {
            "status": "NOT_VERIFIED",
            "expected_archive_sha256": expected_digest,
            "observed_archive_sha256": None,
            "expected_source_revision_sha": expected_source,
            "observed_source_revision_sha": None,
            "verified_claim_ids": [],
            "errors": ["HISTORICAL_ARCHIVE_READ_FAILED"],
        }
    if observed_digest != expected_digest:
        return {
            "status": "VERIFICATION_FAILED",
            "expected_archive_sha256": expected_digest,
            "observed_archive_sha256": observed_digest,
            "expected_source_revision_sha": expected_source,
            "observed_source_revision_sha": None,
            "verified_claim_ids": [],
            "errors": ["HISTORICAL_ARCHIVE_DIGEST_MISMATCH"],
        }

    from experiments.execution.tooling.mono_ci_b0_psi_archive import (
        ARCHIVE_MANIFEST_NAME,
        verify_psi_transition_archive,
    )

    try:
        with tempfile.TemporaryDirectory(prefix="delta-a5-historical-replay-") as temporary:
            extracted = Path(temporary) / "verified-archive"
            replay = verify_psi_transition_archive(
                original_archive,
                extract_to=extracted,
                repository=repository,
            )
            with zipfile.ZipFile(original_archive, "r") as archive:
                manifest = json.loads(archive.read(ARCHIVE_MANIFEST_NAME))
            run_path = extracted / "development_run.json"
            run = json.loads(run_path.read_text(encoding="utf-8"))
            source_identities = package["subject"]["source_identities"]
            transition = run["transition"]
            transition_matches = (
                transition["before_commit_sha"] == source_identities[0]["commit_sha"]
                and transition["after_commit_sha"] == source_identities[1]["commit_sha"]
                and transition["before_repository_tree_sha"]
                == source_identities[0]["repository_tree_sha"]
                and transition["after_repository_tree_sha"]
                == source_identities[1]["repository_tree_sha"]
                and transition["before_application_tree_sha"]
                == source_identities[0]["application_tree_sha"]
                and transition["after_application_tree_sha"]
                == source_identities[1]["application_tree_sha"]
            )
            metadata_matches = (
                replay["archive_sha256"] == expected_digest
                and replay["workflow_run_url"] == historical["workflow_run_url"]
                and replay["artifact_name"] == historical["artifact_name"]
                and replay["execution_id"] == historical["execution_id"]
                and replay["member_count"] == historical["archive_members"]
                and manifest["source_revision_sha"] == expected_source
                and run["source_revision_sha"] == expected_source
                and transition_matches
            )
            member_digests_match = True
            for row in historical["archive_evidence"]:
                member_path = extracted / _safe_repo_path(row["path"])
                if (
                    not member_path.is_file()
                    or _sha256_bytes(member_path.read_bytes()) != row["sha256"]
                ):
                    member_digests_match = False
                    break
            if not metadata_matches or not member_digests_match:
                errors = []
                if not metadata_matches:
                    errors.append("HISTORICAL_ARCHIVE_IDENTITY_MISMATCH")
                if not member_digests_match:
                    errors.append("HISTORICAL_REPORTED_MEMBER_DIGEST_MISMATCH")
                return {
                    "status": "VERIFICATION_FAILED",
                    "expected_archive_sha256": expected_digest,
                    "observed_archive_sha256": observed_digest,
                    "expected_source_revision_sha": expected_source,
                    "observed_source_revision_sha": manifest.get("source_revision_sha"),
                    "verified_claim_ids": [],
                    "errors": errors,
                }
    except (OSError, ValueError, KeyError, json.JSONDecodeError, zipfile.BadZipFile):
        return {
            "status": "VERIFICATION_FAILED",
            "expected_archive_sha256": expected_digest,
            "observed_archive_sha256": observed_digest,
            "expected_source_revision_sha": expected_source,
            "observed_source_revision_sha": None,
            "verified_claim_ids": [],
            "errors": ["HISTORICAL_ARCHIVE_REPLAY_FAILED"],
        }
    return {
        "status": "INDEPENDENT_ARCHIVE_REPLAY_VERIFIED",
        "expected_archive_sha256": expected_digest,
        "observed_archive_sha256": observed_digest,
        "expected_source_revision_sha": expected_source,
        "observed_source_revision_sha": expected_source,
        "verified_claim_ids": [
            "INNER_ARCHIVE_DIGEST",
            "ARCHIVE_MEMBER_INTEGRITY_AND_READBACK",
            "A0_4_A0_5_SOURCE_IDENTITY_BINDING",
        ],
        "historical_reported_claims_status": "HISTORICAL_VERIFICATION_REFERENCED",
        "errors": [],
    }


def _verify_git_identity(repository: Path, identity: dict[str, Any], errors: list[str]) -> None:
    commit = identity["commit_sha"]
    if re.fullmatch(r"[a-f0-9]{40}", commit) is None:
        errors.append("GIT_COMMIT_ID_INVALID")
        return
    try:
        manifest_path = _safe_repo_path(identity["state_manifest_path"]).as_posix()
        tree = _git_text(repository, "rev-parse", f"{commit}^{{tree}}")
        app_tree = _git_text(repository, "rev-parse", f"{commit}:app")
        manifest = _git_bytes(repository, "show", f"{commit}:{manifest_path}")
    except ValueError:
        errors.append(f"GIT_OBJECT_UNAVAILABLE:{commit}")
        return
    if tree != identity["repository_tree_sha"]:
        errors.append(f"REPOSITORY_TREE_MISMATCH:{commit}")
    if app_tree != identity["application_tree_sha"]:
        errors.append(f"APPLICATION_TREE_MISMATCH:{commit}")
    if _sha256_bytes(manifest) != identity["state_manifest_sha256"]:
        errors.append(f"STATE_MANIFEST_MISMATCH:{commit}")


def verify_package(
    repository: Path,
    package_path: Path | None = None,
    historical_archive_path: Path | None = None,
) -> dict[str, Any]:
    """Verify local package evidence and optionally replay an explicitly supplied archive."""
    repository = repository.resolve(strict=True)
    package_path = (package_path or repository / PACKAGE_RELATIVE).resolve(strict=True)
    errors: list[str] = []
    try:
        package = json.loads(package_path.read_text(encoding="utf-8"))
        schema = json.loads((repository / SCHEMA_RELATIVE).read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(package)
    except (OSError, json.JSONDecodeError, jsonschema.ValidationError) as error:
        return {
            "verification_status": "VERIFICATION_FAILED",
            "local_repository_evidence_status": "VERIFICATION_FAILED",
            "historical_evidence_status": "HISTORICAL_VERIFICATION_REFERENCED",
            "independent_archive_replay": {
                "status": "NOT_EXECUTED",
                "verified_claim_ids": [],
            },
            "study_readiness": "NO_GO_WITH_EXPLICIT_BLOCKERS",
            "errors": [f"PACKAGE_SCHEMA_OR_READ_ERROR:{type(error).__name__}"],
        }
    identities = package["subject"]["source_identities"]
    actual_identity_rows = [
        (
            row["state"],
            row["commit_sha"],
            row["repository_tree_sha"],
            row["application_tree_sha"],
            row["state_manifest_path"],
            row["state_manifest_sha256"],
        )
        for row in identities
    ]
    if tuple(actual_identity_rows) != EXPECTED_SOURCE_IDENTITIES:
        errors.append("CANONICAL_TRANSITION_IDENTITY_MISMATCH")
    if (
        package["subject"]["before_state"] != EXPECTED_SOURCE_IDENTITIES[0][0]
        or package["subject"]["after_state"] != EXPECTED_SOURCE_IDENTITIES[1][0]
        or identities[0]["application_tree_sha"] != identities[1]["application_tree_sha"]
        or package["subject"]["application_code_change"]["same_tree"] is not True
    ):
        errors.append("TRANSITION_SUBJECT_BINDING_MISMATCH")
    for identity in identities:
        _verify_git_identity(repository, identity, errors)
    if package["method_candidate"]["source_revision_sha"] != METHOD_CANDIDATE_BASE_SHA:
        errors.append("METHOD_CANDIDATE_BASE_REVISION_MISMATCH")
    artifact_digests: dict[str, str] = {}
    for artifact in package["source_artifacts"]:
        artifact_path = artifact["path"]
        if artifact_path in artifact_digests:
            errors.append(f"DUPLICATE_SOURCE_ARTIFACT:{artifact_path}")
        try:
            relative = _safe_repo_path(artifact_path)
            actual = _sha256_bytes((repository / relative).read_bytes())
        except (OSError, ValueError):
            errors.append(f"SOURCE_ARTIFACT_UNAVAILABLE:{artifact_path}")
            continue
        artifact_digests[artifact_path] = actual
        if actual != artifact["sha256"]:
            errors.append(f"SOURCE_ARTIFACT_DIGEST_MISMATCH:{artifact_path}")
    baseline = package["baseline"]
    if artifact_digests.get(baseline["path"]) != baseline["sha256"]:
        errors.append("BASELINE_DIGEST_BINDING_MISMATCH")
    method = package["method_candidate"]
    method_artifacts = (
        method["source_digests"] + method["schema_digests"] + method["configuration_digests"]
    )
    for artifact in method_artifacts:
        if artifact_digests.get(artifact["path"]) != artifact["sha256"]:
            errors.append(f"METHOD_ARTIFACT_BINDING_MISMATCH:{artifact['path']}")
    for key, artifact in (
        ("input_schema", method["input_schema"]),
        ("output_schema", method["output_schema"]),
    ):
        if artifact not in {row["path"] for row in method["schema_digests"]}:
            errors.append(f"METHOD_{key.upper()}_NOT_PINNED")
    catalog_path = repository / "fitness/catalog/architectural-obligations.yaml"
    catalog = yaml.safe_load(catalog_path.read_text())
    catalog_ids = [str(row["id"]) for row in catalog["obligations"]]
    actual_catalog_sha256 = _sha256_bytes(catalog_path.read_bytes())
    evaluator_root = repository / "architecture/acceptance/a1"
    evaluator_artifacts = [
        {"path": path.name, "sha256": _sha256_bytes(path.read_bytes())}
        for path in sorted(evaluator_root.glob("*.py"))
    ]
    encoded_inventory = json.dumps(
        evaluator_artifacts, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    evaluator_digest = _sha256_bytes(encoded_inventory)
    if evaluator_digest != package["semantic_adequacy"]["evaluator_source_inventory_sha256"]:
        errors.append("EVALUATOR_SOURCE_INVENTORY_DIGEST_MISMATCH")
    for evaluator in package["semantic_adequacy"]["evaluators"]:
        if evaluator["source_sha256"] != evaluator_digest:
            errors.append(f"EVALUATOR_SOURCE_BINDING_MISMATCH:{evaluator['evaluator_id']}")
        if (
            artifact_digests.get(evaluator["configuration_path"])
            != evaluator["configuration_sha256"]
        ):
            errors.append(f"EVALUATOR_CONFIG_BINDING_MISMATCH:{evaluator['evaluator_id']}")
    for pair in package["semantic_adequacy"]["matrix"]:
        if pair["evaluator_source_sha256"] != evaluator_digest:
            errors.append("PAIR_EVALUATOR_SOURCE_BINDING_MISMATCH")
        if (
            artifact_digests.get(pair["evaluator_configuration_path"])
            != pair["evaluator_configuration_sha256"]
        ):
            errors.append("PAIR_EVALUATOR_CONFIG_BINDING_MISMATCH")
    profile_result = evaluate_applicability_profile(
        package["applicability_profile"],
        catalog_ids=catalog_ids,
        catalog_sha256=actual_catalog_sha256,
        state_manifest_sha256=package["subject"]["source_identities"][1]["state_manifest_sha256"],
        authority_verified=False,
        independent_review_verified=False,
        as_of=date.fromisoformat(package["assessment_date"]),
    )
    if profile_result["scoring_authorized"]:
        errors.append("UNAUTHORIZED_APPLICABILITY_SCORING")
    profile = package["applicability_profile"]
    if (
        profile["authority_status"] != "ENGINEERING_POLICY_DECLARED"
        or profile["independent_review_status"] != "PENDING"
        or profile["catalog_closure_status"] != "OPEN"
        or any(
            row["applicability"] != "UNKNOWN"
            or row["mandatory_status"] != "UNKNOWN"
            or row["lifecycle_status"] != "UNKNOWN"
            for row in profile["rows"]
        )
    ):
        errors.append("PACKAGE_APPLICABILITY_NOT_FAIL_CLOSED")
    matrix = package["semantic_adequacy"]["matrix"]
    pair_keys = {(row["evaluator_id"], row["obligation_id"]) for row in matrix}
    evaluator_ids = {row["evaluator_id"] for row in matrix}
    if len(pair_keys) != 9 or evaluator_ids != {
        "AC_PUBLIC_API",
        "AC_MODULE_GRAPH",
        "AC_DATA_OWNERSHIP",
    }:
        errors.append("SEMANTIC_MATRIX_INCOMPLETE")
    inventory_errors, inventory_counts = validate_semantic_inventory(matrix)
    errors.extend(inventory_errors)
    if inventory_counts != package["semantic_adequacy"]["inventory_counts"]:
        errors.append("SEMANTIC_INVENTORY_COUNTS_MISMATCH")
    if (
        package["semantic_adequacy"]["inventory_purpose"]
        != "REVIEW_INVENTORY_NOT_SCORING_DENOMINATOR"
    ):
        errors.append("SEMANTIC_INVENTORY_PURPOSE_INVALID")
    if (
        package["method_candidate"]["algorithm_status"] != "NOT_READY"
        or package["method_candidate"]["freeze_status"] != "PROPOSED_NOT_INDEPENDENTLY_FROZEN"
    ):
        errors.append("METHOD_FREEZE_PROMOTION_FORBIDDEN")
    if package["cost_profile"]["status"] != "COST_MODEL_UNRESOLVED":
        errors.append("COST_AUTHORITY_PROMOTION_FORBIDDEN")
    if package["historical_development_run"]["not_a_comparison"] is not True:
        errors.append("DEVELOPMENT_RUN_MISREPRESENTED_AS_COMPARISON")
    scope = package["verification_scope"]
    historical_scope = scope["historical_evidence"]
    claim_ids = {row["claim_id"] for row in historical_scope["claims"]}
    if (
        scope["local_repository_evidence"]["status"] != "LOCALLY_VERIFIED"
        or historical_scope["status"] != "HISTORICAL_VERIFICATION_REFERENCED"
        or historical_scope["workflow_run_url"]
        != package["historical_development_run"]["workflow_run_url"]
        or historical_scope["workflow_head_sha"]
        != package["historical_development_run"]["source_revision_sha"]
        or claim_ids != SEMANTIC_INVENTORY_CLAIM_IDS
        or any(
            row["status"] != "HISTORICAL_VERIFICATION_REFERENCED"
            for row in historical_scope["claims"]
        )
    ):
        errors.append("EVIDENCE_CLASSIFICATION_INVALID")
    independent_replay = scope["independent_archive_replay"]
    if (
        independent_replay["status"] != "NOT_EXECUTED"
        or independent_replay["expected_inner_archive_sha256"]
        != package["historical_development_run"]["inner_archive_sha256"]
        or independent_replay["expected_source_revision_sha"] != HISTORICAL_RUN_SOURCE_SHA
        or independent_replay["verified_archive_sha256"] is not None
        or independent_replay["verified_source_revision_sha"] is not None
        or independent_replay["verified_claim_ids"]
    ):
        errors.append("ARCHIVE_REPLAY_STATUS_OVERCLAIMED")
    if (
        package["historical_development_run"]["verification_status"]
        != "HISTORICAL_VERIFICATION_REFERENCED"
        or package["historical_development_run"]["source_revision_sha"] != HISTORICAL_RUN_SOURCE_SHA
    ):
        errors.append("HISTORICAL_RUN_CLASSIFICATION_INVALID")
    guard = package["readiness"]
    if (
        guard["overall_outcome"] != "NO_GO_WITH_EXPLICIT_BLOCKERS"
        or guard["p_algorithm_status"] != "NOT_READY"
        or guard["g1_status"] != "INCOMPLETE"
        or guard["g4_status"] != "NOT_AUTHORIZED"
        or guard["scoring_status"] != "NOT_EXECUTED"
    ):
        errors.append("RESEARCH_GATE_PROMOTION_FORBIDDEN")
    local_status = "LOCALLY_VERIFIED" if not errors else "VERIFICATION_FAILED"
    if errors:
        replay_result = {
            "status": "NOT_EXECUTED",
            "expected_archive_sha256": package["historical_development_run"][
                "inner_archive_sha256"
            ],
            "observed_archive_sha256": None,
            "expected_source_revision_sha": HISTORICAL_RUN_SOURCE_SHA,
            "observed_source_revision_sha": None,
            "verified_claim_ids": [],
            "errors": ["ARCHIVE_REPLAY_SKIPPED_LOCAL_VERIFICATION_FAILED"],
        }
    else:
        replay_result = verify_historical_archive(
            repository,
            package,
            historical_archive_path,
        )
    return {
        "verification_status": local_status,
        "local_repository_evidence_status": local_status,
        "historical_evidence_status": "HISTORICAL_VERIFICATION_REFERENCED",
        "historical_timing_status": "HISTORICAL_TIMING_OBSERVATION_REFERENCED",
        "independent_archive_replay": replay_result,
        "study_readiness": package["readiness"]["overall_outcome"],
        "catalog_rows": len(catalog_ids),
        "applicability_scoring_authorized": profile_result["scoring_authorized"],
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--package", type=Path)
    parser.add_argument(
        "--historical-archive",
        type=Path,
        help="Optional exact local archive file; never downloads a GitHub artifact.",
    )
    args = parser.parse_args()
    result = verify_package(args.repository, args.package, args.historical_archive)
    print(json.dumps(result, indent=2, sort_keys=True))
    replay_status = result["independent_archive_replay"]["status"]
    return int(
        result["verification_status"] != "LOCALLY_VERIFIED"
        or replay_status not in {"NOT_EXECUTED", "INDEPENDENT_ARCHIVE_REPLAY_VERIFIED"}
    )


if __name__ == "__main__":
    raise SystemExit(main())
