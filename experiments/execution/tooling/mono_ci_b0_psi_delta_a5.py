"""Read-only ΔA5 readiness checks; never executes B0, Ψ, evaluators, or scoring."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess  # nosec B404 - only fixed read-only local Git identity queries
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any

import jsonschema
import yaml

PACKAGE_RELATIVE = Path(
    "experiments/execution/mono-ci-b0-psi-delta-a5-v1/DELTA_A5_READINESS_V1.json"
)
SCHEMA_RELATIVE = Path(
    "experiments/execution/schemas/mono_ci_b0_psi_delta_a5_readiness_v1.schema.json"
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


def verify_package(repository: Path, package_path: Path | None = None) -> dict[str, Any]:
    """Verify package schema and all repository-local byte/source identities."""
    repository = repository.resolve(strict=True)
    package_path = (package_path or repository / PACKAGE_RELATIVE).resolve(strict=True)
    errors: list[str] = []
    try:
        package = json.loads(package_path.read_text(encoding="utf-8"))
        schema = json.loads((repository / SCHEMA_RELATIVE).read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(package)
    except (OSError, json.JSONDecodeError, jsonschema.ValidationError) as error:
        return {
            "verification_status": "FAIL",
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
    if any(row["pair_validity"] != "UNKNOWN" for row in matrix):
        errors.append("UNREVIEWED_PAIR_PROMOTION")
    if (
        package["method_candidate"]["algorithm_status"] != "NOT_READY"
        or package["method_candidate"]["freeze_status"] != "PROPOSED_NOT_INDEPENDENTLY_FROZEN"
    ):
        errors.append("METHOD_FREEZE_PROMOTION_FORBIDDEN")
    if package["cost_profile"]["status"] != "COST_MODEL_UNRESOLVED":
        errors.append("COST_AUTHORITY_PROMOTION_FORBIDDEN")
    if package["historical_development_run"]["not_a_comparison"] is not True:
        errors.append("DEVELOPMENT_RUN_MISREPRESENTED_AS_COMPARISON")
    guard = package["readiness"]
    if (
        guard["overall_outcome"] != "NO_GO_WITH_EXPLICIT_BLOCKERS"
        or guard["p_algorithm_status"] != "NOT_READY"
        or guard["g1_status"] != "INCOMPLETE"
        or guard["g4_status"] != "NOT_AUTHORIZED"
        or guard["scoring_status"] != "NOT_EXECUTED"
    ):
        errors.append("RESEARCH_GATE_PROMOTION_FORBIDDEN")
    return {
        "verification_status": "PASS" if not errors else "FAIL",
        "study_readiness": package["readiness"]["overall_outcome"],
        "catalog_rows": len(catalog_ids),
        "applicability_scoring_authorized": profile_result["scoring_authorized"],
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--package", type=Path)
    args = parser.parse_args()
    result = verify_package(args.repository, args.package)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verification_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
