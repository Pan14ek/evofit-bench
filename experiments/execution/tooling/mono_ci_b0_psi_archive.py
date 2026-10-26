"""Pack and verify persistent DEVELOPMENT-only MONO CI B0/Ψ evidence archives."""

from __future__ import annotations

import argparse
import json
import platform
import re
import stat
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, cast

from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError, ProtocolError
from experiments.execution.tooling.hashing import pretty_json_bytes, sha256_bytes, sha256_file
from experiments.execution.tooling.mono_ci_b0_psi_execution import (
    BASELINE_NAME,
    PROPOSAL_RELATIVE,
    _git_text,
    _write_new_bytes,
    verify_arm_input_bundle,
    verify_development_result,
    verify_execution_proposal,
)
from experiments.execution.tooling.mono_ci_b0_psi_preflight import verify_preflight

ARCHIVE_SCHEMA = "mono_ci_b0_psi_development_archive_v1.schema.json"
TRANSITION_ARCHIVE_SCHEMA_V1 = "mono_ci_psi_transition_archive_v1.schema.json"
TRANSITION_ARCHIVE_SCHEMA_V2 = "mono_ci_psi_transition_archive_v2.schema.json"
TRANSITION_ARCHIVE_SCHEMA_V3 = "mono_ci_psi_transition_archive_v3.schema.json"
ARCHIVE_MANIFEST_NAME = "ARCHIVE_MANIFEST.json"
WORKFLOW_URL_PATTERN = re.compile(
    r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/actions/runs/[0-9]+$"
)
ARTIFACT_NAME_PATTERN = re.compile(
    r"^mono-ci-(?:b0-psi-development|psi-transition|psi-a05)-[A-Za-z0-9_-]+$"
)
SOURCE_SHA_PATTERN = re.compile(r"^[a-f0-9]{40}$")
MAX_ARCHIVE_SIZE_BYTES = 100 * 1024 * 1024
MAX_ARCHIVE_MEMBER_SIZE_BYTES = 20 * 1024 * 1024
MAX_ARCHIVE_MEMBER_COUNT = 10_000
FORBIDDEN_ARCHIVE_PARTS = {
    ".git",
    "scorer",
    "scoring",
    "oracle",
    "reference",
    "expected_outputs",
    "ground_truth",
    "groundtruth",
    "eval01",
    "eval02",
    "evaluator_control_expectations",
    ".env",
    "credentials",
    "secrets",
}


def pack_development_archive(
    run_root: Path,
    archive_path: Path,
    repository: Path,
    workflow_run_url: str,
    artifact_name: str,
    uv_version: str,
) -> dict[str, Any]:
    """Pack a verified DEVELOPMENT run into a deterministic ZIP plus SHA-256 sidecar."""
    run_directory = run_root.resolve(strict=True)
    repo_root = repository.resolve(strict=True)
    run = verify_development_result(run_directory)
    _validate_archive_metadata(workflow_run_url, artifact_name, uv_version)
    proposal = verify_execution_proposal(repo_root)
    preflight = verify_preflight(repo_root)
    baseline_config = _decode_manifest((repo_root / PROPOSAL_RELATIVE / BASELINE_NAME).read_bytes())
    authorization = baseline_config["authorization"]
    if (
        preflight["integrity_status"] != "PASS"
        or preflight["readiness"] != "NO_GO"
        or proposal["baseline_configuration_sha256"] != run["baseline"]["configuration_sha256"]
        or authorization
        != {
            "baseline_approval": False,
            "method_input_authorized": False,
            "scientific_measurement_authorized": False,
            "study_readiness": "NO_GO",
            "P_ALGORITHM_STATUS": "NOT_READY",
            "G1": "INCOMPLETE",
            "G4": "NOT_AUTHORIZED",
            "G_A1_C4_REF_FROZEN": "NOT_READY",
        }
    ):
        raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_AUTHORIZATION_STATUS_MISMATCH")
    source_revision = _git_text(repo_root, "rev-parse", "HEAD")
    if SOURCE_SHA_PATTERN.fullmatch(source_revision) is None:
        raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_SOURCE_REVISION_INVALID")

    member_paths = _run_member_paths(run_directory)
    members = [
        {
            "path": relative,
            "size_bytes": (run_directory / relative).stat().st_size,
            "sha256": sha256_file(run_directory / relative),
        }
        for relative in member_paths
    ]
    manifest = {
        "schema_version": "MONO_CI_B0_PSI_DEVELOPMENT_ARCHIVE_V1",
        "archive_purpose": "DEVELOPMENT_RAW_EVALUATOR_EVIDENCE_ONLY",
        "execution_id": run["execution_id"],
        "workflow": {
            "run_url": workflow_run_url,
            "artifact_name": artifact_name,
            "retention_days": 90,
        },
        "source_revision_sha": source_revision,
        "execution_record_sha256": sha256_file(run_directory / "development_run.json"),
        "run_inventory_sha256": sha256_file(run_directory / "SHA256SUMS"),
        "baseline": run["baseline"],
        "authorization_boundary": {
            "study_readiness": run["study_readiness"],
            "measurement_status": run["measurement_status"],
            "p_algorithm_status": authorization["P_ALGORITHM_STATUS"],
            "g1": authorization["G1"],
            "g4": authorization["G4"],
            "reference_gate": authorization["G_A1_C4_REF_FROZEN"],
            "psi_status": run["arms"]["PSI"]["status"],
            "scoring": run["scoring"],
        },
        "cases": _case_provenance(run_directory, run),
        "environment": {
            "python_version": sys.version.split()[0],
            "operating_system": platform.platform(),
            "architecture": platform.machine(),
            "uv_version": uv_version,
            "pyproject_sha256": sha256_file(repo_root / "pyproject.toml"),
            "uv_lock_sha256": sha256_file(repo_root / "uv.lock"),
        },
        "reproduction_commands": _reproduction_commands(),
        "members": members,
    }
    validate_payload(ARCHIVE_SCHEMA, manifest)

    destination = archive_path.expanduser().absolute()
    parent = destination.parent.resolve(strict=True)
    destination = parent / destination.name
    sidecar_path = Path(f"{destination}.sha256")
    if (
        destination.exists()
        or destination.is_symlink()
        or sidecar_path.exists()
        or sidecar_path.is_symlink()
    ):
        raise ProtocolError("MONO_CI_B0_PSI_ARCHIVE_OUTPUT_MUST_BE_NEW")

    archive_bytes = _build_zip(run_directory, members, manifest)
    try:
        with destination.open("xb") as handle:
            handle.write(archive_bytes)
        digest = sha256_bytes(archive_bytes)
        with sidecar_path.open("xb") as handle:
            handle.write(f"{digest}  {destination.name}\n".encode())
    except OSError as error:
        raise ProtocolError("MONO_CI_B0_PSI_ARCHIVE_WRITE_FAILED") from error

    result = verify_development_archive(destination)
    return {
        "archive_path": str(destination),
        "archive_sha256": digest,
        "execution_id": run["execution_id"],
        "member_count": result["member_count"],
        "verification_status": "PASS",
    }


def pack_psi_transition_archive(
    run_root: Path,
    archive_path: Path,
    repository: Path,
    workflow_run_url: str,
    artifact_name: str,
    uv_version: str,
) -> dict[str, Any]:
    """Pack a verified transition-level P run with the shared DEVELOPMENT archive helpers."""
    from experiments.execution.tooling.mono_ci_psi_transition import verify_transition_run

    run_directory = run_root.resolve(strict=True)
    repo_root = repository.resolve(strict=True)
    run = verify_transition_run(run_directory)
    source_revision = _git_text(repo_root, "rev-parse", "HEAD")
    if source_revision != run["source_revision_sha"]:
        raise ProtocolError("MONO_CI_PSI_TRANSITION_ARCHIVE_SOURCE_REVISION_MISMATCH")
    _validate_archive_metadata(workflow_run_url, artifact_name, uv_version)
    members = [
        {
            "path": relative,
            "size_bytes": (run_directory / relative).stat().st_size,
            "sha256": sha256_file(run_directory / relative),
        }
        for relative in _run_member_paths(run_directory)
    ]
    is_a05 = run.get("schema_version") == "MONO_CI_PSI_TRANSITION_RUN_V3"
    manifest = {
        "schema_version": (
            "MONO_CI_PSI_TRANSITION_ARCHIVE_V3" if is_a05 else "MONO_CI_PSI_TRANSITION_ARCHIVE_V2"
        ),
        "archive_purpose": "DEVELOPMENT_METHOD_RAW_EXECUTION_ONLY",
        "execution_id": run["execution_id"],
        "workflow": {
            "run_url": workflow_run_url,
            "artifact_name": artifact_name,
            "retention_days": 90,
        },
        "source_revision_sha": source_revision,
        "execution_record_sha256": sha256_file(run_directory / "development_run.json"),
        "run_inventory_sha256": sha256_file(run_directory / "SHA256SUMS"),
        "structural_manifest_path": run["method_input"]["structural_manifest_path"],
        "baseline": run["baseline"],
        "authorization_boundary": _transition_authorization_boundary(run),
        "transition": run["transition"],
        "evidence": {
            "input_bundle_sha256": run["method_input"]["bundle_sha256"],
            "method_implementation_sha256": run["method_implementation"]["sha256"],
            "evaluator_source_sha256": sorted(
                {row["evaluator_source_sha256"] for row in run["evaluator_observations"]}
            ),
            "adaptation_sidecar_sha256": run["adaptation_evidence"]["sha256"],
            "adaptation_trust_scope": run["adaptation_evidence"]["trust_scope"],
        },
        "environment": {
            "python_version": sys.version.split()[0],
            "operating_system": platform.platform(),
            "architecture": platform.machine(),
            "uv_version": uv_version,
        },
        "reproduction_commands": [
            "uv sync --frozen --extra dev",
            "make test-mono-ci-psi-transition" if not is_a05 else "make test-mono-ci-psi-a05",
            (
                "uv run --frozen --extra dev python -m "
                + (
                    "experiments.execution.tooling.mono_ci_psi_transition run "
                    "--repository <checkout> --output <new-path> "
                    "--execution-id DEV_PSI_TRANSITION_<unique>"
                    if not is_a05
                    else "experiments.execution.tooling.mono_ci_psi_a05 --repository <checkout> "
                    "--output <new-path> --execution-id DEV_PSI_TRANSITION_A05_<unique>"
                )
            ),
        ],
        "members": members,
    }
    validate_payload(
        TRANSITION_ARCHIVE_SCHEMA_V3 if is_a05 else TRANSITION_ARCHIVE_SCHEMA_V2,
        manifest,
    )

    destination = archive_path.expanduser().absolute()
    parent = destination.parent.resolve(strict=True)
    destination = parent / destination.name
    sidecar_path = Path(f"{destination}.sha256")
    if (
        destination.exists()
        or destination.is_symlink()
        or sidecar_path.exists()
        or sidecar_path.is_symlink()
    ):
        raise ProtocolError("MONO_CI_PSI_TRANSITION_ARCHIVE_OUTPUT_MUST_BE_NEW")
    archive_bytes = _build_zip(run_directory, members, manifest)
    try:
        with destination.open("xb") as handle:
            handle.write(archive_bytes)
        digest = sha256_bytes(archive_bytes)
        with sidecar_path.open("xb") as handle:
            handle.write(f"{digest}  {destination.name}\n".encode())
    except OSError as error:
        raise ProtocolError("MONO_CI_PSI_TRANSITION_ARCHIVE_WRITE_FAILED") from error
    result = verify_psi_transition_archive(destination)
    return {
        "archive_path": str(destination),
        "archive_sha256": digest,
        "execution_id": run["execution_id"],
        "member_count": result["member_count"],
        "verification_status": "PASS",
    }


def verify_psi_transition_archive(
    archive_path: Path, *, extract_to: Path | None = None
) -> dict[str, Any]:
    """Verify a transition archive with the shared ZIP, sidecar, extraction and readback checks."""
    from experiments.execution.tooling.mono_ci_psi_transition import verify_transition_run

    original_archive = archive_path.expanduser().absolute()
    if original_archive.is_symlink():
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_ARCHIVE_INVALID")
    archive = original_archive.resolve(strict=True)
    if not archive.is_file() or archive.stat().st_size > MAX_ARCHIVE_SIZE_BYTES:
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_ARCHIVE_INVALID")
    sidecar = Path(f"{archive}.sha256")
    if sidecar.is_symlink() or not sidecar.is_file():
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_ARCHIVE_SIDECAR_MISSING")
    if sidecar.read_text(encoding="utf-8").strip() != f"{sha256_file(archive)}  {archive.name}":
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_ARCHIVE_SIDECAR_MISMATCH")

    try:
        with zipfile.ZipFile(archive, "r") as zipped:
            infos = zipped.infolist()
            names = [info.filename for info in infos]
            _validate_zip_members(infos)
            if len(names) != len(set(names)) or ARCHIVE_MANIFEST_NAME not in names:
                raise ContractValidationError(
                    "MONO_CI_PSI_TRANSITION_ARCHIVE_MEMBER_INVENTORY_INVALID"
                )
            manifest = _decode_manifest(zipped.read(ARCHIVE_MANIFEST_NAME))
            validate_payload(_transition_archive_schema(manifest), manifest)
            payload = {name: zipped.read(name) for name in names if name != ARCHIVE_MANIFEST_NAME}
    except (OSError, zipfile.BadZipFile, KeyError, UnicodeDecodeError) as error:
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_ARCHIVE_READ_FAILED") from error

    declared = {item["path"]: item for item in manifest["members"]}
    if set(payload) != set(declared):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_ARCHIVE_MEMBER_SET_MISMATCH")
    for relative, content in payload.items():
        _validate_archive_member_path(relative)
        expected = declared[relative]
        if len(content) != expected["size_bytes"] or sha256_bytes(content) != expected["sha256"]:
            raise ContractValidationError("MONO_CI_PSI_TRANSITION_ARCHIVE_MEMBER_DIGEST_MISMATCH")

    with tempfile.TemporaryDirectory(prefix="mono-ci-psi-transition-archive-") as temporary:
        extracted_root = Path(temporary).resolve(strict=True)
        for relative, content in payload.items():
            _write_new_bytes(extracted_root, relative, content)
        run = verify_transition_run(extracted_root)
        _verify_transition_archive_manifest_binding(manifest, extracted_root, run)
        if extract_to is not None:
            _extract_to_new_directory(payload, extract_to)
    return {
        "archive_path": str(archive),
        "archive_sha256": sha256_file(archive),
        "execution_id": manifest["execution_id"],
        "member_count": len(payload),
        "verification_status": "PASS",
        "workflow_run_url": manifest["workflow"]["run_url"],
        "artifact_name": manifest["workflow"]["artifact_name"],
        "retention_days": manifest["workflow"]["retention_days"],
    }


def _transition_authorization_boundary(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "study_readiness": run["study_readiness"],
        "measurement_status": run["measurement_status"],
        "p_algorithm_status": run["p_algorithm_status"],
        "g1": run["g1"],
        "g4": run["g4"],
        "reference_gate": run["reference_gate"],
        "psi_status": run["psi"]["status"],
        "psi_decision": run["psi"]["decision"],
        "scoring": run["psi"]["scoring"],
    }


def _transition_archive_schema(manifest: dict[str, Any]) -> str:
    version = manifest.get("schema_version")
    if version == "MONO_CI_PSI_TRANSITION_ARCHIVE_V1":
        return TRANSITION_ARCHIVE_SCHEMA_V1
    if version == "MONO_CI_PSI_TRANSITION_ARCHIVE_V2":
        return TRANSITION_ARCHIVE_SCHEMA_V2
    if version == "MONO_CI_PSI_TRANSITION_ARCHIVE_V3":
        return TRANSITION_ARCHIVE_SCHEMA_V3
    raise ContractValidationError("MONO_CI_PSI_TRANSITION_ARCHIVE_SCHEMA_UNSUPPORTED")


def _verify_transition_archive_manifest_binding(
    manifest: dict[str, Any], run_root: Path, run: dict[str, Any]
) -> None:
    if (
        manifest["execution_id"] != run["execution_id"]
        or manifest["source_revision_sha"] != run["source_revision_sha"]
        or manifest["execution_record_sha256"] != sha256_file(run_root / "development_run.json")
        or manifest["run_inventory_sha256"] != sha256_file(run_root / "SHA256SUMS")
        or manifest["structural_manifest_path"] != run["method_input"]["structural_manifest_path"]
        or manifest["baseline"] != run["baseline"]
        or manifest["transition"] != run["transition"]
        or manifest["authorization_boundary"] != _transition_authorization_boundary(run)
        or (
            manifest.get("schema_version")
            in {"MONO_CI_PSI_TRANSITION_ARCHIVE_V2", "MONO_CI_PSI_TRANSITION_ARCHIVE_V3"}
            and manifest.get("evidence")
            != {
                "input_bundle_sha256": run["method_input"]["bundle_sha256"],
                "method_implementation_sha256": run["method_implementation"]["sha256"],
                "evaluator_source_sha256": sorted(
                    {row["evaluator_source_sha256"] for row in run["evaluator_observations"]}
                ),
                "adaptation_sidecar_sha256": run["adaptation_evidence"]["sha256"],
                "adaptation_trust_scope": run["adaptation_evidence"]["trust_scope"],
            }
        )
    ):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_ARCHIVE_RUN_BINDING_MISMATCH")


def verify_development_archive(
    archive_path: Path, *, extract_to: Path | None = None
) -> dict[str, Any]:
    """Verify the archive sidecar, ZIP inventory, payload checksums, and raw run readback."""
    original_archive = archive_path.expanduser().absolute()
    if original_archive.is_symlink():
        raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_FILE_INVALID")
    archive = original_archive.resolve(strict=True)
    if not archive.is_file() or archive.stat().st_size > MAX_ARCHIVE_SIZE_BYTES:
        raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_FILE_INVALID")
    sidecar = Path(f"{archive}.sha256")
    if sidecar.is_symlink() or not sidecar.is_file():
        raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_SIDECAR_MISSING")
    sidecar_text = sidecar.read_text(encoding="utf-8").strip()
    expected_sidecar = f"{sha256_file(archive)}  {archive.name}"
    if sidecar_text != expected_sidecar:
        raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_SIDECAR_MISMATCH")

    try:
        with zipfile.ZipFile(archive, "r") as zipped:
            infos = zipped.infolist()
            names = [info.filename for info in infos]
            _validate_zip_members(infos)
            if len(names) != len(set(names)) or ARCHIVE_MANIFEST_NAME not in names:
                raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_MEMBER_INVENTORY_INVALID")
            manifest = _decode_manifest(zipped.read(ARCHIVE_MANIFEST_NAME))
            validate_payload(ARCHIVE_SCHEMA, manifest)
            file_members = {
                name: zipped.read(name) for name in names if name != ARCHIVE_MANIFEST_NAME
            }
    except (OSError, zipfile.BadZipFile, KeyError, UnicodeDecodeError) as error:
        raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_READ_FAILED") from error

    declared = {item["path"]: item for item in manifest["members"]}
    if set(file_members) != set(declared):
        raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_MEMBER_SET_MISMATCH")
    for relative, content in file_members.items():
        _validate_archive_member_path(relative)
        expected = declared[relative]
        if len(content) != expected["size_bytes"] or sha256_bytes(content) != expected["sha256"]:
            raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_MEMBER_DIGEST_MISMATCH")

    with tempfile.TemporaryDirectory(prefix="mono-ci-b0-psi-archive-verify-") as temporary:
        extracted_root = Path(temporary).resolve(strict=True)
        for relative, content in file_members.items():
            _write_new_bytes(extracted_root, relative, content)
        run = verify_development_result(extracted_root)
        _verify_manifest_run_binding(manifest, extracted_root, run)
        if extract_to is not None:
            _extract_to_new_directory(file_members, extract_to)

    return {
        "archive_path": str(archive),
        "archive_sha256": sha256_file(archive),
        "execution_id": manifest["execution_id"],
        "member_count": len(file_members),
        "verification_status": "PASS",
        "workflow_run_url": manifest["workflow"]["run_url"],
        "artifact_name": manifest["workflow"]["artifact_name"],
        "retention_days": manifest["workflow"]["retention_days"],
    }


def _case_provenance(run_root: Path, run: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for case in run["arms"]["B0"]["case_results"]:
        case_id = case["case_id"]
        b0 = verify_arm_input_bundle(run_root / "B0/input_bundle" / case_id, expected_arm="B0")
        psi = verify_arm_input_bundle(run_root / "PSI/input_bundle" / case_id, expected_arm="PSI")
        if b0["common_input_sha256"] != psi["common_input_sha256"]:
            raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_COMMON_INPUT_PARITY_MISMATCH")
        cases.append(
            {
                "case_id": case_id,
                "source_commit_sha": case["source_commit_sha"],
                "repository_tree_sha": case["repository_tree_sha"],
                "application_tree_sha": case["application_tree_sha"],
                "input_bundle_sha256": b0["bundle_sha256"],
                "common_input_sha256": b0["common_input_sha256"],
                "execution_binding": case["execution_binding"],
                "evaluators": case["evaluators"],
            }
        )
    return cases


def _verify_manifest_run_binding(
    manifest: dict[str, Any], run_root: Path, run: dict[str, Any]
) -> None:
    if (
        manifest["execution_id"] != run["execution_id"]
        or manifest["execution_record_sha256"] != sha256_file(run_root / "development_run.json")
        or manifest["run_inventory_sha256"] != sha256_file(run_root / "SHA256SUMS")
        or manifest["baseline"] != run["baseline"]
        or manifest["authorization_boundary"]
        != {
            "study_readiness": run["study_readiness"],
            "measurement_status": run["measurement_status"],
            "p_algorithm_status": "NOT_READY",
            "g1": "INCOMPLETE",
            "g4": "NOT_AUTHORIZED",
            "reference_gate": "NOT_READY",
            "psi_status": run["arms"]["PSI"]["status"],
            "scoring": run["scoring"],
        }
        or manifest["cases"] != _case_provenance(run_root, run)
    ):
        raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_RUN_PROVENANCE_MISMATCH")


def _run_member_paths(run_root: Path) -> list[str]:
    expected = set()
    for path in run_root.rglob("*"):
        if path.is_symlink():
            raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_SYMLINK_FORBIDDEN")
        if path.is_file():
            relative = path.relative_to(run_root).as_posix()
            _validate_archive_member_path(relative)
            expected.add(relative)
    if "SHA256SUMS" not in expected:
        raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_RUN_INVENTORY_MISSING")
    return sorted(expected)


def _build_zip(run_root: Path, members: list[dict[str, Any]], manifest: dict[str, Any]) -> bytes:
    from io import BytesIO

    output = BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as zipped:
        for member in members:
            relative = member["path"]
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            zipped.writestr(info, (run_root / relative).read_bytes())
        info = zipfile.ZipInfo(ARCHIVE_MANIFEST_NAME, date_time=(1980, 1, 1, 0, 0, 0))
        info.create_system = 3
        info.external_attr = 0o100644 << 16
        info.compress_type = zipfile.ZIP_STORED
        zipped.writestr(info, pretty_json_bytes(manifest))
    return output.getvalue()


def _validate_zip_members(infos: list[zipfile.ZipInfo]) -> None:
    if len(infos) > MAX_ARCHIVE_MEMBER_COUNT:
        raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_MEMBER_COUNT_EXCEEDED")
    total_size = 0
    for info in infos:
        _validate_archive_member_path(info.filename)
        mode = info.external_attr >> 16
        file_type = stat.S_IFMT(mode)
        if (
            info.is_dir()
            or (file_type not in (0, stat.S_IFREG))
            or info.compress_type != zipfile.ZIP_STORED
            or info.file_size > MAX_ARCHIVE_MEMBER_SIZE_BYTES
        ):
            raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_NONREGULAR_MEMBER_FORBIDDEN")
        total_size += info.file_size
        if total_size > MAX_ARCHIVE_SIZE_BYTES:
            raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_UNCOMPRESSED_SIZE_EXCEEDED")


def _validate_archive_member_path(relative: str) -> None:
    path = PurePosixPath(relative)
    if (
        path.is_absolute()
        or not path.parts
        or ".." in path.parts
        or "\\" in relative
        or ":" in path.parts[0]
    ):
        raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_PATH_INVALID")
    if {part.lower() for part in path.parts}.intersection(FORBIDDEN_ARCHIVE_PARTS):
        raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_FORBIDDEN_CONTENT_PATH")


def _validate_archive_metadata(workflow_url: str, artifact_name: str, uv_version: str) -> None:
    if WORKFLOW_URL_PATTERN.fullmatch(workflow_url) is None:
        raise ProtocolError("MONO_CI_B0_PSI_ARCHIVE_WORKFLOW_URL_INVALID")
    if ARTIFACT_NAME_PATTERN.fullmatch(artifact_name) is None:
        raise ProtocolError("MONO_CI_B0_PSI_ARCHIVE_ARTIFACT_NAME_INVALID")
    if not uv_version or len(uv_version) > 200 or "\n" in uv_version:
        raise ProtocolError("MONO_CI_B0_PSI_ARCHIVE_UV_VERSION_INVALID")


def _decode_manifest(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_MANIFEST_INVALID") from error
    if not isinstance(value, dict):
        raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_MANIFEST_OBJECT_REQUIRED")
    return cast(dict[str, Any], value)


def _extract_to_new_directory(members: dict[str, bytes], destination: Path) -> None:
    target = destination.expanduser().absolute()
    if target.exists() or target.is_symlink():
        raise ProtocolError("MONO_CI_B0_PSI_ARCHIVE_EXTRACT_PATH_MUST_BE_NEW")
    parent = target.parent.resolve(strict=True)
    target = parent / target.name
    target.mkdir(mode=0o700)
    target = target.resolve(strict=True)
    for relative, content in members.items():
        _write_new_bytes(target, relative, content)


def _reproduction_commands() -> list[str]:
    return [
        "uv sync --frozen --extra dev",
        "make test-mono-ci-b0-psi-execution",
        "make development-quality",
        (
            'echo "EXECUTION_ID='
            'DEV_MONO_CI_GHA_${GITHUB_RUN_ID}_${GITHUB_RUN_ATTEMPT}" >> "$GITHUB_ENV"'
        ),
        (
            'echo "ARTIFACT_NAME=mono-ci-b0-psi-development-'
            '${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}" >> "$GITHUB_ENV"'
        ),
        (
            'echo "RUN_OUTPUT=${RUNNER_TEMP}/mono-ci-b0-psi-development-'
            '${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}" >> "$GITHUB_ENV"'
        ),
        (
            'echo "ARCHIVE_PATH=${RUNNER_TEMP}/mono-ci-b0-psi-development-'
            '${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}.zip" >> "$GITHUB_ENV"'
        ),
        (
            'echo "VERIFY_OUTPUT=${RUNNER_TEMP}/mono-ci-b0-psi-development-'
            '${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-verified" >> "$GITHUB_ENV"'
        ),
        (
            'echo "WORKFLOW_RUN_URL=${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}'
            '/actions/runs/${GITHUB_RUN_ID}" >> "$GITHUB_ENV"'
        ),
        (
            "uv run --frozen --extra dev python -m "
            "experiments.execution.tooling.mono_ci_b0_psi_execution "
            '--development-validation --repository "$GITHUB_WORKSPACE" '
            '--output "$RUN_OUTPUT" --execution-id "$EXECUTION_ID"'
        ),
        (
            "uv run --frozen --extra dev python -m "
            "experiments.execution.tooling.mono_ci_b0_psi_archive pack "
            '--run "$RUN_OUTPUT" --archive "$ARCHIVE_PATH" '
            '--repository "$GITHUB_WORKSPACE" '
            '--workflow-run-url "$WORKFLOW_RUN_URL" '
            '--artifact-name "$ARTIFACT_NAME" --uv-version "$(uv --version)"'
        ),
        (
            "uv run --frozen --extra dev python -m "
            "experiments.execution.tooling.mono_ci_b0_psi_archive verify "
            '--archive "$ARCHIVE_PATH" --extract-to "$VERIFY_OUTPUT"'
        ),
    ]


def _cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command_name in ("pack", "transition-pack"):
        pack = commands.add_parser(command_name)
        pack.add_argument("--run", type=Path, required=True)
        pack.add_argument("--archive", type=Path, required=True)
        pack.add_argument("--repository", type=Path, required=True)
        pack.add_argument("--workflow-run-url", required=True)
        pack.add_argument("--artifact-name", required=True)
        pack.add_argument("--uv-version", required=True)
    for command_name in ("verify", "transition-verify"):
        verify = commands.add_parser(command_name)
        verify.add_argument("--archive", type=Path, required=True)
        verify.add_argument("--extract-to", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _cli().parse_args(argv)
    try:
        if args.command == "pack":
            result = pack_development_archive(
                args.run,
                args.archive,
                args.repository,
                args.workflow_run_url,
                args.artifact_name,
                args.uv_version,
            )
        elif args.command == "transition-pack":
            result = pack_psi_transition_archive(
                args.run,
                args.archive,
                args.repository,
                args.workflow_run_url,
                args.artifact_name,
                args.uv_version,
            )
        elif args.command == "transition-verify":
            result = verify_psi_transition_archive(args.archive, extract_to=args.extract_to)
        else:
            result = verify_development_archive(args.archive, extract_to=args.extract_to)
    except (ContractValidationError, ProtocolError) as error:
        print(json.dumps({"verification_status": "FAIL", "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "main",
    "pack_development_archive",
    "pack_psi_transition_archive",
    "verify_development_archive",
    "verify_psi_transition_archive",
]
