"""Read-only, fail-closed preparation checks for the MONO CI B0/Ψ study.

This module checks package contracts, artifact hashes, source identity and
readiness blockers. It never executes an evaluator, B0, Ψ, or a scorer.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess  # nosec B404
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, cast

from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.hashing import sha256_bytes, sha256_file

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_RELATIVE = Path("experiments/execution/mono-ci-b0-psi-v1")
INPUTS_NAME = "INPUTS_V1.json"
CASE_MANIFEST_NAME = "CASE_MANIFEST_V1.json"
EXPECTATIONS_NAME = "EVALUATOR_CONTROL_EXPECTATIONS_V1.json"
CHECKSUMS_NAME = "SHA256SUMS"
CASE_SCHEMA = "mono_ci_b0_psi_case_manifest_v1.schema.json"
INPUTS_SCHEMA = "mono_ci_b0_psi_inputs_v1.schema.json"
EXPECTATIONS_SCHEMA = "mono_ci_b0_psi_evaluator_expectations_v1.schema.json"

ARTIFACT_SCHEMA_BY_NAME = {
    CASE_MANIFEST_NAME: CASE_SCHEMA,
    INPUTS_NAME: INPUTS_SCHEMA,
    EXPECTATIONS_NAME: EXPECTATIONS_SCHEMA,
}


def verify_preflight(repository: Path = REPOSITORY_ROOT) -> dict[str, Any]:
    """Verify the source-bound preparation package without running a study arm."""
    root = repository.resolve(strict=True)
    package = root / PACKAGE_RELATIVE
    inputs = _read_json(package / INPUTS_NAME)
    cases = _read_json(package / CASE_MANIFEST_NAME)
    expectations = _read_json(package / EXPECTATIONS_NAME)

    validate_payload(INPUTS_SCHEMA, inputs)
    validate_payload(CASE_SCHEMA, cases)
    validate_payload(EXPECTATIONS_SCHEMA, expectations)
    _verify_package_checksums(package)
    _verify_source_artifacts(root, inputs)
    _verify_case_bindings(root, inputs, cases, expectations)
    _verify_eval01_archive(root, cases)
    _verify_canonical_source_pair(root, cases)
    _verify_readiness_blockers(root, inputs, expectations)

    return {
        "study_id": inputs["study_id"],
        "integrity_status": "PASS",
        "readiness": "NO_GO",
        "measurement_status": "NOT_EXECUTED",
        "arms": {"B0": "NOT_EXECUTED", "PSI": "NOT_EXECUTED"},
        "evaluator_execution": "NOT_EXECUTED",
        "scoring": "NOT_EXECUTED",
        "source_pair_readback": "PASS",
        "case_archive_readback": "PASS",
        "remaining_gates": [
            "A0.3 parent fitness configuration is NOT_IDENTIFIED",
            "complete approved applicability/mandatory denominator and stage scope are unresolved",
            "exact-pair semantic validity is not independently reviewed",
            "method Ψ remains NOT_READY and has no frozen study-specific identity",
            "method bundles, allowlists, isolation probes and common runner are NOT_CREATED",
            "independent scorer reference and custody/readback are not established",
            "G1 is INCOMPLETE, G4 is NOT AUTHORIZED, and the ΔA4 reference gate is NOT_READY",
        ],
    }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractValidationError(f"MONO_CI_B0_PSI_JSON_READ_FAILED:{path.name}") from error
    if not isinstance(payload, dict):
        raise ContractValidationError(f"MONO_CI_B0_PSI_JSON_OBJECT_REQUIRED:{path.name}")
    return cast(dict[str, Any], payload)


def _repository_file(root: Path, relative: str) -> Path:
    candidate = PurePosixPath(relative)
    if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts:
        raise ContractValidationError(f"MONO_CI_B0_PSI_UNSAFE_PATH:{relative}")
    path = root.joinpath(*candidate.parts)
    current = root
    for part in candidate.parts:
        current = current / part
        if current.is_symlink():
            raise ContractValidationError(f"MONO_CI_B0_PSI_SYMLINK_PATH:{relative}")
    try:
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise ContractValidationError(f"MONO_CI_B0_PSI_ARTIFACT_MISSING:{relative}") from error
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ContractValidationError(f"MONO_CI_B0_PSI_ARTIFACT_PATH_INVALID:{relative}")
    return resolved


def _verify_package_checksums(package: Path) -> None:
    checksum_path = package / CHECKSUMS_NAME
    if not checksum_path.is_file() or checksum_path.is_symlink():
        raise ContractValidationError("MONO_CI_B0_PSI_PACKAGE_CHECKSUMS_MISSING")
    declared: dict[str, str] = {}
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)", line)
        if not match:
            raise ContractValidationError("MONO_CI_B0_PSI_PACKAGE_CHECKSUMS_INVALID")
        digest, name = match.groups()
        if name in declared or name == CHECKSUMS_NAME:
            raise ContractValidationError("MONO_CI_B0_PSI_PACKAGE_CHECKSUMS_DUPLICATE")
        declared[name] = digest
    actual_names = {
        path.name for path in package.iterdir() if path.is_file() and path.name != CHECKSUMS_NAME
    }
    if set(declared) != actual_names:
        raise ContractValidationError("MONO_CI_B0_PSI_PACKAGE_CHECKSUMS_INVENTORY_MISMATCH")
    for name, digest in declared.items():
        path = package / name
        if path.is_symlink() or sha256_file(path) != digest:
            raise ContractValidationError(f"MONO_CI_B0_PSI_PACKAGE_DIGEST_MISMATCH:{name}")


def _verify_source_artifacts(root: Path, inputs: dict[str, Any]) -> None:
    artifacts = inputs["source_artifacts"]
    seen_ids: set[str] = set()
    for artifact in artifacts:
        artifact_id = str(artifact["id"])
        if artifact_id in seen_ids:
            raise ContractValidationError(f"MONO_CI_B0_PSI_DUPLICATE_ARTIFACT_ID:{artifact_id}")
        seen_ids.add(artifact_id)
        path = _repository_file(root, str(artifact["path"]))
        if sha256_file(path) != artifact["sha256"]:
            raise ContractValidationError(f"MONO_CI_B0_PSI_SOURCE_DIGEST_MISMATCH:{artifact_id}")
        if artifact["method_input_eligible"] and _contains_forbidden_method_input_token(artifact):
            raise ContractValidationError(f"MONO_CI_B0_PSI_FORBIDDEN_METHOD_INPUT:{artifact_id}")
    required = {
        "EVAL01_RAW_ARCHIVE",
        "EVAL01_ARCHIVE_SHA256_SIDECAR",
        "A03_LINEAGE_CANDIDATE_RECORD",
        "P_MEASURED_INTERFACE",
        "G1_G4_REGISTER",
    }
    if not required.issubset(seen_ids):
        raise ContractValidationError("MONO_CI_B0_PSI_REQUIRED_PROVENANCE_ARTIFACT_MISSING")


def _contains_forbidden_method_input_token(artifact: dict[str, Any]) -> bool:
    text = " ".join(str(artifact.get(key, "")) for key in ("id", "path", "role")).upper()
    return any(
        token in text
        for token in (
            "EVAL01",
            "EXPECTATION",
            "SCORER",
            "ORACLE",
            "DRAFT_POLICY",
            "P_STATUS",
            "G1_G4",
        )
    )


def _verify_case_bindings(
    root: Path, inputs: dict[str, Any], cases: dict[str, Any], expectations: dict[str, Any]
) -> None:
    if inputs["case_manifest_path"] != (PACKAGE_RELATIVE / CASE_MANIFEST_NAME).as_posix():
        raise ContractValidationError("MONO_CI_B0_PSI_CASE_MANIFEST_PATH_MISMATCH")
    case_manifest_bytes = (root / PACKAGE_RELATIVE / CASE_MANIFEST_NAME).read_bytes()
    if sha256_bytes(case_manifest_bytes) != inputs["case_manifest_sha256"]:
        raise ContractValidationError("MONO_CI_B0_PSI_CASE_MANIFEST_DIGEST_MISMATCH")
    artifacts_by_id = {item["id"]: item for item in inputs["source_artifacts"]}
    archive_record = cases["source_case_archive"]
    artifact_bindings = (
        ("EVAL01_RAW_ARCHIVE", archive_record["path"], archive_record["sha256"]),
        (
            "EVAL01_MUTATION_CATALOG",
            archive_record["case_catalog_path"],
            archive_record["case_catalog_sha256"],
        ),
    )
    for artifact_id, expected_path, expected_digest in artifact_bindings:
        artifact = artifacts_by_id.get(artifact_id)
        if (
            artifact is None
            or artifact["path"] != expected_path
            or artifact["sha256"] != expected_digest
        ):
            raise ContractValidationError(
                f"MONO_CI_B0_PSI_CASE_ARCHIVE_BINDING_MISMATCH:{artifact_id}"
            )
    if inputs["shared_policy_context"]["applicability"] != "UNKNOWN":
        raise ContractValidationError("MONO_CI_B0_PSI_UNKNOWN_APPLICABILITY_MUST_REMAIN_UNKNOWN")

    arm_b0 = inputs["arms"]["B0"]
    arm_psi = inputs["arms"]["PSI"]
    if arm_b0["common_input_ids"] != arm_psi["common_input_ids"]:
        raise ContractValidationError("MONO_CI_B0_PSI_COMMON_INPUT_PARITY_MISMATCH")
    if arm_b0["common_input_ids"] != inputs["common_input_ids_plan"]:
        raise ContractValidationError("MONO_CI_B0_PSI_COMMON_INPUT_PLAN_MISMATCH")
    if arm_b0["planned_case_ids"] != arm_psi["planned_case_ids"]:
        raise ContractValidationError("MONO_CI_B0_PSI_CASE_PARITY_MISMATCH")
    if arm_b0["bundle_status"] != "NOT_CREATED" or arm_psi["bundle_status"] != "NOT_CREATED":
        raise ContractValidationError("MONO_CI_B0_PSI_BUNDLES_MUST_REMAIN_UNCREATED")
    if arm_b0["baseline_configuration_status"] != "NOT_IDENTIFIED":
        raise ContractValidationError("MONO_CI_B0_PSI_BASELINE_CANNOT_BE_PROMOTED_BY_PREFLIGHT")
    if arm_psi["algorithm_status"] != "NOT_READY":
        raise ContractValidationError("MONO_CI_B0_PSI_METHOD_CANNOT_BE_PROMOTED_BY_PREFLIGHT")

    cases_by_id = {item["case_id"]: item for item in cases["cases"]}
    source_rows = {item["case_id"]: item for item in inputs["case_sources"]}
    if set(cases_by_id) != set(source_rows) or set(cases_by_id) != set(arm_b0["planned_case_ids"]):
        raise ContractValidationError("MONO_CI_B0_PSI_CASE_INVENTORY_MISMATCH")
    for case_id, case in cases_by_id.items():
        source = source_rows[case_id]
        for field in ("source_commit_sha", "repository_tree_sha", "application_tree_sha"):
            if source[field] != case[field]:
                raise ContractValidationError(
                    f"MONO_CI_B0_PSI_CASE_SOURCE_MISMATCH:{case_id}:{field}"
                )
        if source["source_snapshot_status"] != "NOT_EXPORTED_TO_METHOD_BUNDLE":
            raise ContractValidationError("MONO_CI_B0_PSI_CASE_SNAPSHOT_ALREADY_EXPORTED")
    if expectations["included_in_method_inputs"] is not False:
        raise ContractValidationError("MONO_CI_B0_PSI_EXPECTATIONS_MUST_STAY_OUTSIDE_METHOD_INPUTS")
    if (
        expectations["fitness_operation_reference"] != "NOT_ESTABLISHED"
        or expectations["governance_reference"] != "NOT_ESTABLISHED"
    ):
        raise ContractValidationError("MONO_CI_B0_PSI_EXPECTATIONS_CANNOT_BECOME_METHOD_REFERENCE")
    if (
        expectations["source"]["preregistered_catalog_path"] != archive_record["case_catalog_path"]
        or expectations["source"]["preregistered_catalog_sha256"]
        != archive_record["case_catalog_sha256"]
        or expectations["source"]["raw_archive_sha256"] != archive_record["sha256"]
    ):
        raise ContractValidationError("MONO_CI_B0_PSI_EXPECTATION_SOURCE_BINDING_MISMATCH")
    expected_case_ids = [item["case_id"] for item in expectations["expectations"]]
    if set(expected_case_ids) != set(cases_by_id) or len(expected_case_ids) != len(
        set(expected_case_ids)
    ):
        raise ContractValidationError("MONO_CI_B0_PSI_EXPECTATION_CASE_INVENTORY_MISMATCH")


def _parse_archive_checksums(raw: bytes, member_names: set[str]) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for line in raw.decode("utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_CHECKSUMS_INVALID")
        digest, name = match.groups()
        if (
            name in checksums
            or PurePosixPath(name).is_absolute()
            or ".." in PurePosixPath(name).parts
        ):
            raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_CHECKSUM_PATH_INVALID")
        checksums[name] = digest
    if set(checksums) != member_names - {"SHA256SUMS"}:
        raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_CHECKSUMS_INVENTORY_MISMATCH")
    return checksums


def _compare_case_archive_manifest(cases: dict[str, Any], run_manifest: dict[str, Any]) -> None:
    archived_cases = run_manifest.get("cases")
    if not isinstance(archived_cases, dict):
        raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_CASES_MISSING")
    for case in cases["cases"]:
        archived = archived_cases.get(case["source_case_id"])
        if not isinstance(archived, dict):
            raise ContractValidationError(f"MONO_CI_B0_PSI_ARCHIVE_CASE_MISSING:{case['case_id']}")
        pairs = {
            "source_commit_sha": "source_commit_sha",
            "repository_tree_sha": "repository_tree_sha",
            "application_tree_sha": "application_tree_sha",
            "mutation_patch_sha256": "mutation_patch_sha256",
            "mutation_bundle_sha256": "mutation_bundle_sha256",
        }
        for case_field, archive_field in pairs.items():
            if case[case_field] != archived.get(archive_field):
                raise ContractValidationError(
                    f"MONO_CI_B0_PSI_ARCHIVE_PROVENANCE_MISMATCH:{case['case_id']}:{case_field}"
                )
        parent = case["source_parent_sha"]
        parents = archived.get("source_parent_shas", [])
        is_mutation = archived.get("is_mutation_revision") is True
        if is_mutation and (parent is None or parent not in parents):
            raise ContractValidationError(
                f"MONO_CI_B0_PSI_ARCHIVE_PARENT_MISMATCH:{case['case_id']}"
            )
        if not is_mutation and parent is not None:
            raise ContractValidationError(
                f"MONO_CI_B0_PSI_ARCHIVE_PARENT_MISMATCH:{case['case_id']}"
            )


def _verify_eval01_archive(root: Path, cases: dict[str, Any]) -> None:
    archive = _repository_file(root, cases["source_case_archive"]["path"])
    sidecar = _repository_file(root, cases["source_case_archive"]["path"] + ".sha256")
    archive_digest = sha256_file(archive)
    expected_digest = cases["source_case_archive"]["sha256"]
    if archive_digest != expected_digest:
        raise ContractValidationError("MONO_CI_B0_PSI_EVAL01_ARCHIVE_DIGEST_MISMATCH")
    sidecar_line = sidecar.read_text(encoding="utf-8").strip()
    if sidecar_line != f"{archive_digest}  {archive.name}":
        raise ContractValidationError("MONO_CI_B0_PSI_EVAL01_ARCHIVE_SIDECAR_MISMATCH")
    with zipfile.ZipFile(archive) as archive_file:
        bad_member = archive_file.testzip()
        if bad_member is not None:
            raise ContractValidationError(f"MONO_CI_B0_PSI_EVAL01_ARCHIVE_CRC_FAILURE:{bad_member}")
        member_names = {name for name in archive_file.namelist() if not name.endswith("/")}
        checksum_data = archive_file.read("SHA256SUMS")
        declared = _parse_archive_checksums(checksum_data, member_names)
        for name, digest in declared.items():
            if sha256_bytes(archive_file.read(name)) != digest:
                raise ContractValidationError(
                    f"MONO_CI_B0_PSI_EVAL01_MEMBER_DIGEST_MISMATCH:{name}"
                )
        run_manifest = _read_json_from_bytes(archive_file.read("run-manifest.json"))
    _compare_case_archive_manifest(cases, run_manifest)


def _read_json_from_bytes(raw: bytes) -> dict[str, Any]:
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_JSON_OBJECT_REQUIRED")
    return cast(dict[str, Any], payload)


def _git(root: Path, *arguments: str) -> str:
    result = _run_git(root, arguments)
    return result.stdout.strip()


def _run_git(
    root: Path, arguments: tuple[str, ...], *, check: bool = True
) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("git")
    if executable is None or not Path(executable).is_absolute():
        raise ContractValidationError("MONO_CI_B0_PSI_GIT_EXECUTABLE_UNAVAILABLE")
    try:
        result = subprocess.run(  # noqa: S603  # nosec B603
            [str(Path(executable).resolve(strict=True)), "-C", str(root), *arguments],
            check=check,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise ContractValidationError("MONO_CI_B0_PSI_GIT_READBACK_FAILED") from error
    return result


def _verify_canonical_source_pair(root: Path, cases: dict[str, Any]) -> None:
    transition = cases["architecture_transition"]
    for prefix in ("before", "after"):
        commit = transition[f"{prefix}_commit_sha"]
        repo_tree = _git(root, "rev-parse", f"{commit}^{{tree}}")
        app_tree = _git(root, "rev-parse", f"{commit}:app")
        if repo_tree != transition[f"{prefix}_repository_tree_sha"]:
            raise ContractValidationError(
                f"MONO_CI_B0_PSI_{prefix.upper()}_REPOSITORY_TREE_MISMATCH"
            )
        if app_tree != transition[f"{prefix}_application_tree_sha"]:
            raise ContractValidationError(
                f"MONO_CI_B0_PSI_{prefix.upper()}_APPLICATION_TREE_MISMATCH"
            )
        _git(root, "cat-file", "-e", f"{commit}^{{commit}}")
    ancestry = _run_git(
        root,
        (
            "merge-base",
            "--is-ancestor",
            transition["before_commit_sha"],
            transition["after_commit_sha"],
        ),
        check=False,
    )
    if ancestry.returncode != 0:
        raise ContractValidationError("MONO_CI_B0_PSI_SOURCE_ANCESTRY_MISMATCH")


def _verify_readiness_blockers(
    root: Path, inputs: dict[str, Any], expectations: dict[str, Any]
) -> None:
    lineage = _read_json(root / "docs/mono_e1_a03_fitness_configuration_candidate_v1.json")
    registry = _read_json(
        root / "experiments/execution/policy-pilot/v1/source/fitness/policy/registry.json"
    )
    p_interface = (root / "experiments/execution/tooling/p_interface.py").read_text(
        encoding="utf-8"
    )
    p_status = (root / "experiments/execution/da01/P_ALGORITHM_STATUS.md").read_text(
        encoding="utf-8"
    )
    authorization = (root / "docs/G1_METHOD_DECISION_REGISTER.md").read_text(encoding="utf-8")
    ref_gate = (root / "experiments/execution/MONO_A1_REFERENCE_FREEZE_CHECKLIST_V2.md").read_text(
        encoding="utf-8"
    )

    if lineage["historical_fitness_configuration"]["a03_configuration_status"] != "NOT_IDENTIFIED":
        raise ContractValidationError("MONO_CI_B0_PSI_BASELINE_READINESS_CHANGED_REQUIRES_REVIEW")
    if registry.get("closure") != "OPEN" or any(
        item.get("normative_status") != "DRAFT" for item in registry.get("policies", [])
    ):
        raise ContractValidationError(
            "MONO_CI_B0_PSI_POLICY_AUTHORITY_STATUS_CHANGED_REQUIRES_REVIEW"
        )
    if 'P_ALGORITHM_STATUS = "NOT_READY"' not in p_interface or "NOT_READY" not in p_status:
        raise ContractValidationError("MONO_CI_B0_PSI_METHOD_STATUS_CHANGED_REQUIRES_REVIEW")
    if "| G1 — methodological/protocol freeze | **INCOMPLETE** |" not in authorization:
        raise ContractValidationError("MONO_CI_B0_PSI_G1_STATUS_CHANGED_REQUIRES_REVIEW")
    if "| G4 — measured-run authorization | **NOT AUTHORIZED** |" not in authorization:
        raise ContractValidationError("MONO_CI_B0_PSI_G4_STATUS_CHANGED_REQUIRES_REVIEW")
    if "**Current status:** `NOT_READY`" not in ref_gate:
        raise ContractValidationError(
            "MONO_CI_B0_PSI_REFERENCE_GATE_STATUS_CHANGED_REQUIRES_REVIEW"
        )
    if expectations["reference_status"] != "AUTHOR_DECLARED_UNREVIEWED_DIAGNOSTIC_ONLY":
        raise ContractValidationError("MONO_CI_B0_PSI_REFERENCE_CANNOT_BE_PROMOTED_BY_PREFLIGHT")
    if inputs["reference_separation"]["included_in_either_method_bundle"] is not False:
        raise ContractValidationError("MONO_CI_B0_PSI_REFERENCE_SEPARATION_FAILED")


def main() -> int:
    """Run and print the read-only package verification result."""
    try:
        print(json.dumps(verify_preflight(), indent=2, sort_keys=True))
    except ContractValidationError as error:
        print(json.dumps({"integrity_status": "FAIL", "error": str(error)}, indent=2))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = ["verify_preflight"]
