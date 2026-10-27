"""Run and verify the separately versioned owner-authorized ΔA5 DEVELOPMENT study."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import resource
import shutil
import subprocess  # nosec B404 - fixed local Git argv; no shell execution
import sys
import time
import zipfile
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError, ProtocolError
from experiments.execution.tooling.hashing import pretty_json_bytes
from experiments.execution.tooling.mono_ci_b0_psi_archive import (
    pack_psi_transition_archive,
    verify_psi_transition_archive,
)
from experiments.execution.tooling.mono_ci_psi_a05 import (
    AFTER_STATE,
    _run_bound_evaluator,
    replay_negative_probe,
    run_a05_transition,
)
from experiments.execution.tooling.mono_ci_psi_evidence import EVALUATOR_CONFIGS

PROTOCOL_ROOT = Path("experiments/execution/mono-ci-b0-psi-delta-a5-owner-authorized-v1")
PROTOCOL_JSON = PROTOCOL_ROOT / "PROTOCOL_V1.json"
FREEZE_PATH = PROTOCOL_ROOT / "PRE_RUN_FREEZE.json"
HISTORICAL_PROBE_ROOT = PROTOCOL_ROOT / "inputs/historical-probe"
A04_COMMIT = "d3101c0d3aa9b7b709253b6ec7518416f05f65b9"
A04_TREE = "2b436e0aaf09403ea516d73d20a466a122f86592"
A04_APP_TREE = "007196f68652bc13f6798805793ffdfae96f95f7"
A05_COMMIT = "a349d19fb89b577e6799e9736ed4ce0acc572166"
A05_TREE = "97c060cc26313a879f0940a178d42e422cc4d188"
A05_APP_TREE = "007196f68652bc13f6798805793ffdfae96f95f7"
B0_RELATIVE = Path(
    "experiments/execution/mono-ci-b0-psi-execution-a05-v1/RECONSTRUCTED_B0_A04_V1.json"
)
READINESS_RELATIVE = Path(
    "experiments/execution/mono-ci-b0-psi-delta-a5-v1/DELTA_A5_READINESS_V2.json"
)
CALIBRATION_SCHEMA = "MONO_CI_PSI_OWNER_AUTHORIZED_CALIBRATION_ARCHIVE_V1"
EVALUATORS = ("AC_PUBLIC_API", "AC_MODULE_GRAPH", "AC_DATA_OWNERSHIP")
SOURCE_CONDITIONS = ("A0_5_CLEAN", "EXISTING_NEGATIVE_PROBE")
CALIBRATION_WARMUPS = 1
CALIBRATION_REPETITIONS = 10
TRANSITION_WARMUPS = 1
TRANSITION_REPETITIONS = 3
CALIBRATION_BUDGET_SECONDS = 900
TRANSITION_BUDGET_SECONDS = 1800
MAX_TOTAL_EXECUTION_SECONDS = 2700


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_new_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(pretty_json_bytes(value))


def _git(root: Path, *args: str) -> str:
    git_binary = shutil.which("git")
    if git_binary is None:
        raise ProtocolError("OWNER_AUTHORIZED_GIT_EXECUTABLE_MISSING")
    result = subprocess.run(  # noqa: S603  # nosec B603 - internal fixed Git subcommands, no shell
        [git_binary, "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
    )
    if result.returncode:
        raise ProtocolError(f"OWNER_AUTHORIZED_GIT_COMMAND_FAILED:{args[0]}")
    return result.stdout.strip()


def _pinned_input_paths(repository: Path) -> list[str]:
    readiness = _json(repository / READINESS_RELATIVE)
    paths = {
        row["path"]
        for row in readiness.get("source_artifacts", [])
        if isinstance(row, dict) and isinstance(row.get("path"), str)
    }
    method = readiness.get("method_candidate", {})
    for key in ("source_digests", "schema_digests", "configuration_digests"):
        paths.update(
            row["path"]
            for row in method.get(key, [])
            if isinstance(row, dict) and isinstance(row.get("path"), str)
        )
    paths.update(
        {
            "experiments/execution/tooling/mono_ci_psi_a05.py",
            "experiments/execution/tooling/mono_ci_psi_transition.py",
            "experiments/execution/tooling/mono_ci_psi_evidence.py",
            "experiments/execution/tooling/mono_ci_psi_coverage.py",
            "experiments/execution/tooling/mono_ci_b0_psi_archive.py",
            "experiments/execution/tooling/mono_ci_b0_psi_execution.py",
            "experiments/execution/tooling/p_input_export_v2.py",
            "experiments/execution/tooling/p_input_validation.py",
            "experiments/execution/tooling/p_policy_source_v3.py",
            "experiments/execution/tooling/p_governance.py",
            "experiments/execution/tooling/contracts.py",
            "experiments/execution/tooling/hashing.py",
            "experiments/execution/policy-pilot/v1/source/fitness/policy/registry.json",
            "pyproject.toml",
            "uv.lock",
        }
    )
    return sorted(paths)


def create_freeze(repository: Path) -> dict[str, Any]:
    """Create the pre-run source-and-protocol freeze record from the clean implementation commit."""
    repo = repository.resolve(strict=True)
    if _git(repo, "status", "--porcelain"):
        raise ProtocolError("OWNER_AUTHORIZED_FREEZE_REQUIRES_CLEAN_CHECKOUT")
    current = _git(repo, "rev-parse", "HEAD")
    if (
        not (repo / PROTOCOL_JSON).is_file()
        or not (repo / HISTORICAL_PROBE_ROOT / "source.patch").is_file()
    ):
        raise ProtocolError("OWNER_AUTHORIZED_PROTOCOL_INPUTS_MISSING")
    validate_payload(
        "mono_ci_psi_owner_authorized_protocol_v1.schema.json", _json(repo / PROTOCOL_JSON)
    )
    input_paths = _pinned_input_paths(repo)
    missing = [path for path in input_paths if not (repo / path).is_file()]
    if missing:
        raise ProtocolError("OWNER_AUTHORIZED_FROZEN_INPUT_MISSING:" + ",".join(missing))
    values = {
        path: _sha256(repo / path)
        for path in [
            "experiments/execution/mono-ci-b0-psi-delta-a5-owner-authorized-v1/CONTEXT.md",
            "experiments/execution/mono-ci-b0-psi-delta-a5-owner-authorized-v1/PROTOCOL_V1.md",
            "experiments/execution/mono-ci-b0-psi-delta-a5-owner-authorized-v1/PROTOCOL_V1.json",
            "experiments/execution/mono-ci-b0-psi-delta-a5-owner-authorized-v1/REVIEW_DECISIONS.md",
            "experiments/execution/mono-ci-b0-psi-delta-a5-owner-authorized-v1/"
            "EVALUATOR_CAPABILITY_REVIEW_V1.md",
            "experiments/execution/mono-ci-b0-psi-delta-a5-owner-authorized-v1/"
            "inputs/historical-probe/probe-manifest.json",
            "experiments/execution/mono-ci-b0-psi-delta-a5-owner-authorized-v1/"
            "inputs/historical-probe/source.patch",
            "experiments/execution/mono-ci-b0-psi-delta-a5-owner-authorized-v1/"
            "inputs/historical-probe/source-files/app/modules/tasks/repository.py",
            "experiments/execution/tooling/mono_ci_psi_owner_authorized.py",
            "experiments/execution/tooling/mono_ci_psi_owner_authorized_analysis.py",
            ".github/workflows/ci.yml",
            "experiments/execution/schemas/mono_ci_psi_owner_authorized_protocol_v1.schema.json",
            "experiments/execution/schemas/mono_ci_psi_owner_authorized_"
            "pre_run_freeze_v1.schema.json",
            "experiments/execution/schemas/mono_ci_psi_owner_authorized_execution_v1.schema.json",
            "experiments/execution/schemas/mono_ci_psi_owner_authorized_"
            "calibration_archive_v1.schema.json",
        ]
        + input_paths
    }
    freeze = {
        "schema_version": "MONO_CI_PSI_OWNER_AUTHORIZED_PRE_RUN_FREEZE_V1",
        "study_id": "MONO_CI_B0_PSI_DELTA_A5_OWNER_AUTHORIZED_DEV_V1",
        "classification": "PRE_REGISTERED_EXPLORATORY_DEVELOPMENT",
        "freeze_created_at_utc": datetime.now(UTC).isoformat(),
        "implementation_commit": current,
        "source_identities": {
            "a04_commit": A04_COMMIT,
            "a04_repository_tree": A04_TREE,
            "a04_application_tree": A04_APP_TREE,
            "a05_commit": A05_COMMIT,
            "a05_repository_tree": A05_TREE,
            "a05_application_tree": A05_APP_TREE,
        },
        "baseline": {
            "path": B0_RELATIVE.as_posix(),
            "sha256": _sha256(repo / B0_RELATIVE),
            "identity": "PROSPECTIVE_RECONSTRUCTION_NOT_HISTORICAL",
            "approval": "NOT_APPROVED",
        },
        "historical_probe": {
            "manifest_sha256": _sha256(repo / HISTORICAL_PROBE_ROOT / "probe-manifest.json"),
            "patch_sha256": _sha256(repo / HISTORICAL_PROBE_ROOT / "source.patch"),
            "modified_source_sha256": _sha256(
                repo / HISTORICAL_PROBE_ROOT / "source-files/app/modules/tasks/repository.py"
            ),
            "historical_inner_archive_sha256": (
                "6e1b39df457d3053487a3123ab4f29e78467515c0925a58a36bb2dea26f7c563"
            ),
        },
        "protocol_and_execution_inputs_sha256": values,
        "measurement_plan": {
            "calibration_warmups_per_cell": CALIBRATION_WARMUPS,
            "calibration_measured_repetitions_per_cell": CALIBRATION_REPETITIONS,
            "transition_warmups": TRANSITION_WARMUPS,
            "transition_measured_repetitions": TRANSITION_REPETITIONS,
            "random_seed": 20261027,
            "calibration_budget_seconds": CALIBRATION_BUDGET_SECONDS,
            "transition_budget_seconds": TRANSITION_BUDGET_SECONDS,
            "total_execution_budget_seconds": MAX_TOTAL_EXECUTION_SECONDS,
            "scoring": "NOT_EXECUTED",
            "coverage": "UNKNOWN",
            "official_g1": "INCOMPLETE",
            "official_g4": "NOT_AUTHORIZED",
        },
    }
    validate_payload("mono_ci_psi_owner_authorized_pre_run_freeze_v1.schema.json", freeze)
    return freeze


def verify_freeze(repository: Path, frozen_revision: str) -> dict[str, Any]:
    """Fail closed unless execution begins from the exact preregistered freeze commit."""
    repo = repository.resolve(strict=True)
    freeze = _json(repo / FREEZE_PATH)
    validate_payload("mono_ci_psi_owner_authorized_pre_run_freeze_v1.schema.json", freeze)
    head = _git(repo, "rev-parse", "HEAD")
    parent = _git(repo, "rev-parse", "HEAD^")
    changed = _git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines()
    expected_freeze_path = FREEZE_PATH.as_posix()
    if (
        freeze.get("schema_version") != "MONO_CI_PSI_OWNER_AUTHORIZED_PRE_RUN_FREEZE_V1"
        or head != frozen_revision
        or parent != freeze.get("implementation_commit")
        or changed != [expected_freeze_path]
        or _git(repo, "status", "--porcelain")
    ):
        raise ProtocolError("OWNER_AUTHORIZED_FREEZE_COMMIT_OR_WORKTREE_MISMATCH")
    for relative, digest in freeze["protocol_and_execution_inputs_sha256"].items():
        path = repo / relative
        if not path.is_file() or _sha256(path) != digest:
            raise ProtocolError("OWNER_AUTHORIZED_FROZEN_INPUT_DIGEST_MISMATCH:" + relative)
    protocol = _json(repo / PROTOCOL_JSON)
    validate_payload("mono_ci_psi_owner_authorized_protocol_v1.schema.json", protocol)
    if (
        protocol.get("study_id") != freeze["study_id"]
        or _sha256(repo / B0_RELATIVE) != freeze["baseline"]["sha256"]
        or protocol.get("gates", {}).get("G1") != "INCOMPLETE"
        or protocol.get("gates", {}).get("G4") != "NOT_AUTHORIZED"
    ):
        raise ProtocolError("OWNER_AUTHORIZED_PROTOCOL_OR_GATE_MISMATCH")
    return freeze


def _usage_snapshot() -> dict[str, float]:
    process = resource.getrusage(resource.RUSAGE_SELF)
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    return {
        "self_user_seconds": process.ru_utime,
        "self_system_seconds": process.ru_stime,
        "child_user_seconds": children.ru_utime,
        "child_system_seconds": children.ru_stime,
    }


def _usage_delta(before: Mapping[str, float], after: Mapping[str, float]) -> dict[str, float]:
    return {f"{key}_delta": round(after[key] - value, 6) for key, value in before.items()}


def _runner_identity(uv_version: str) -> dict[str, Any]:
    return {
        "python_version": sys.version.split()[0],
        "python_implementation": platform.python_implementation(),
        "operating_system": platform.platform(),
        "architecture": platform.machine(),
        "cpu_count": os.cpu_count(),
        "runner_class": os.environ.get("RUNNER_OS", "LOCAL"),
        "runner_image_os": os.environ.get("ImageOS"),
        "runner_image_version": os.environ.get("ImageVersion"),
        "uv_version": uv_version,
        "network_isolation_binary": shutil.which("bwrap") or shutil.which("sandbox-exec"),
        "hostname_recorded": False,
        "peak_rss_per_process": "NOT_AVAILABLE",
    }


def _clone_subject(repository: Path, destination: Path) -> Path:
    git_binary = shutil.which("git")
    if git_binary is None:
        raise ProtocolError("OWNER_AUTHORIZED_GIT_EXECUTABLE_MISSING")
    result = subprocess.run(  # noqa: S603  # nosec B603 - fixed Git clone argv, no shell
        [
            git_binary,
            "clone",
            "--quiet",
            "--shared",
            "--no-checkout",
            str(repository),
            str(destination),
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
    )
    if result.returncode:
        raise ProtocolError("OWNER_AUTHORIZED_SUBJECT_CLONE_FAILED")
    _git(destination, "checkout", "--quiet", "--detach", A05_COMMIT)
    if (
        _git(destination, "rev-parse", "HEAD") != A05_COMMIT
        or _git(destination, "rev-parse", "HEAD^{tree}") != A05_TREE
        or _git(destination, "rev-parse", "HEAD:app") != A05_APP_TREE
    ):
        raise ProtocolError("OWNER_AUTHORIZED_A05_SOURCE_IDENTITY_MISMATCH")
    return destination


def _verify_subject_inputs(repository: Path, subject: Path, freeze: Mapping[str, Any]) -> None:
    for relative, digest in freeze["protocol_and_execution_inputs_sha256"].items():
        path = Path(relative)
        if (
            path.parts[0] in {"architecture", "experiments", "fitness"}
            and (subject / path).is_file()
            and _sha256(subject / path) != digest
        ):
            raise ProtocolError("OWNER_AUTHORIZED_SUBJECT_INPUT_DIGEST_MISMATCH:" + relative)
    if _git(subject, "rev-parse", f"{A04_COMMIT}^{{tree}}") != A04_TREE:
        raise ProtocolError("OWNER_AUTHORIZED_A04_SOURCE_IDENTITY_MISMATCH")
    if _git(subject, "rev-parse", f"{A04_COMMIT}:app") != A04_APP_TREE:
        raise ProtocolError("OWNER_AUTHORIZED_A04_APPLICATION_TREE_MISMATCH")


def _safe_member_path(value: str) -> None:
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not value
        or "\\" in value
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ContractValidationError("OWNER_AUTHORIZED_ARCHIVE_MEMBER_PATH_INVALID")


def pack_calibration_archive(source_root: Path, archive_path: Path) -> dict[str, Any]:
    """Create a deterministic ZIP and digest sidecar for raw evaluator calibration evidence."""
    source = source_root.resolve(strict=True)
    if any(path.is_symlink() for path in source.rglob("*")):
        raise ProtocolError("OWNER_AUTHORIZED_CALIBRATION_SYMLINK_FORBIDDEN")
    members = []
    for path in sorted(source.rglob("*")):
        if path.is_file():
            relative = path.relative_to(source).as_posix()
            _safe_member_path(relative)
            members.append(
                {"path": relative, "size_bytes": path.stat().st_size, "sha256": _sha256(path)}
            )
    manifest = {
        "schema_version": CALIBRATION_SCHEMA,
        "classification": "DEVELOPMENT_CALIBRATION",
        "member_count": len(members),
        "members": members,
    }
    validate_payload("mono_ci_psi_owner_authorized_calibration_archive_v1.schema.json", manifest)
    destination = archive_path.resolve()
    if destination.exists() or Path(f"{destination}.sha256").exists():
        raise ProtocolError("OWNER_AUTHORIZED_CALIBRATION_ARCHIVE_MUST_BE_NEW")
    manifest_bytes = pretty_json_bytes(manifest)
    with zipfile.ZipFile(
        destination, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as zipped:
        info = zipfile.ZipInfo("CALIBRATION_ARCHIVE_MANIFEST.json", date_time=(1980, 1, 1, 0, 0, 0))
        info.external_attr = 0o100644 << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        zipped.writestr(info, manifest_bytes)
        for row in members:
            path = source / row["path"]
            info = zipfile.ZipInfo(row["path"], date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zipped.writestr(info, path.read_bytes())
    digest = _sha256(destination)
    Path(f"{destination}.sha256").write_text(f"{digest}  {destination.name}\n", encoding="utf-8")
    verified = verify_calibration_archive(destination)
    return {
        "archive_name": destination.name,
        "archive_sha256": digest,
        "member_count": verified["member_count"],
        "verification_status": "PASS",
    }


def verify_calibration_archive(
    archive_path: Path, extract_to: Path | None = None
) -> dict[str, Any]:
    """Verify calibration ZIP, digest sidecar, every raw member and optional safe readback."""
    archive = archive_path.resolve(strict=True)
    sidecar = Path(f"{archive}.sha256")
    digest = _sha256(archive)
    if (
        not sidecar.is_file()
        or sidecar.read_text(encoding="utf-8").strip() != f"{digest}  {archive.name}"
    ):
        raise ContractValidationError("OWNER_AUTHORIZED_CALIBRATION_ARCHIVE_SIDECAR_MISMATCH")
    try:
        with zipfile.ZipFile(archive, "r") as zipped:
            names = zipped.namelist()
            if len(names) != len(set(names)) or "CALIBRATION_ARCHIVE_MANIFEST.json" not in names:
                raise ContractValidationError(
                    "OWNER_AUTHORIZED_CALIBRATION_ARCHIVE_INVENTORY_INVALID"
                )
            manifest = json.loads(zipped.read("CALIBRATION_ARCHIVE_MANIFEST.json"))
            validate_payload(
                "mono_ci_psi_owner_authorized_calibration_archive_v1.schema.json", manifest
            )
            if manifest.get("schema_version") != CALIBRATION_SCHEMA:
                raise ContractValidationError("OWNER_AUTHORIZED_CALIBRATION_ARCHIVE_SCHEMA_INVALID")
            declared = {row["path"]: row for row in manifest.get("members", [])}
            if (
                manifest.get("member_count") != len(declared)
                or len(declared) != len(manifest.get("members", []))
                or set(names) != set(declared) | {"CALIBRATION_ARCHIVE_MANIFEST.json"}
            ):
                raise ContractValidationError(
                    "OWNER_AUTHORIZED_CALIBRATION_ARCHIVE_MEMBER_SET_MISMATCH"
                )
            for name, row in declared.items():
                _safe_member_path(name)
                content = zipped.read(name)
                if (
                    len(content) != row["size_bytes"]
                    or hashlib.sha256(content).hexdigest() != row["sha256"]
                ):
                    raise ContractValidationError(
                        "OWNER_AUTHORIZED_CALIBRATION_MEMBER_DIGEST_MISMATCH"
                    )
                if extract_to is not None:
                    target = extract_to / Path(*PurePosixPath(name).parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if target.exists() or target.is_symlink():
                        raise ContractValidationError(
                            "OWNER_AUTHORIZED_CALIBRATION_READBACK_NOT_NEW"
                        )
                    target.write_bytes(content)
    except (OSError, zipfile.BadZipFile, KeyError, json.JSONDecodeError) as error:
        raise ContractValidationError("OWNER_AUTHORIZED_CALIBRATION_ARCHIVE_READ_FAILED") from error
    return {
        "archive_path": str(archive),
        "archive_sha256": digest,
        "member_count": len(declared),
        "verification_status": "PASS",
    }


def pack_partial_execution_archive(
    run_root: Path,
    archive_path: Path,
    *,
    study_id: str,
    execution_id: str,
    run_role: str,
    sandbox_preflight_id: str,
    archive_failure: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Seal an incomplete transition separately from the complete-run archive format."""
    if run_root.is_symlink():
        raise ProtocolError("OWNER_AUTHORIZED_PARTIAL_EVIDENCE_SOURCE_INVALID")
    source = run_root.resolve(strict=True)
    if not source.is_dir() or any(path.is_symlink() for path in source.rglob("*")):
        raise ProtocolError("OWNER_AUTHORIZED_PARTIAL_EVIDENCE_SOURCE_INVALID")
    progress_path = source / "partial-execution.json"
    full_record_path = source / "development_run.json"
    if progress_path.is_file():
        progress = _json(progress_path)
        phase_status = progress.get("phase_status", {})
        method_status = progress.get("scientific_status", {}).get("method_decision", "NOT_OBSERVED")
        method_process = progress.get("method_subprocess")
        method_observation = progress.get("method_observation")
        source_identities = progress.get("source_identities", {})
        error = progress.get("error")
        ended_at = progress.get("ended_at_utc")
    elif full_record_path.is_file():
        full_record = _json(full_record_path)
        phase_status = {
            "source_identity": "COMPLETED",
            "baseline_identity": "COMPLETED",
            "b0_evaluator_matrix": "COMPLETED",
            "method_input_bundle": "COMPLETED",
            "method_execution": "OBSERVED",
            "candidate_validation": "COMPLETED",
            "complete_transition_verification": "PASS",
        }
        method_status = "OBSERVED"
        method_process = {
            "status": full_record.get("psi", {}).get("status"),
            "exit_code": 0,
            "execution_duration_ms": full_record.get("psi", {}).get("execution_duration_ms"),
        }
        method_path = source / full_record.get("psi", {}).get("raw_result_path", "")
        if method_path.is_file() and not method_path.is_symlink():
            method = _json(method_path)
            governance = method.get("governance", {})
            plan = method.get("operation_plan", {})
            candidate = method.get("candidate")
            method_observation = {
                "raw_result_path": method_path.relative_to(source).as_posix(),
                "raw_result_sha256": _sha256(method_path),
                "governance_decision": governance.get("result"),
                "governance_reason_codes": governance.get("reason_codes", []),
                "operations": plan.get("operations", []),
                "operation_hold_reasons": plan.get("hold_reasons", []),
                "candidate_state": "NOT_MATERIALIZED"
                if candidate is None
                else "MATERIALIZED_UNAPPLIED",
                "candidate_sha256": method.get("candidate_sha256"),
                "parse_status": "JSON_READBACK_ONLY",
            }
        else:
            method_observation = None
        transition = full_record.get("transition", {})
        source_identities = {
            key: transition.get(key)
            for key in (
                "before_commit_sha",
                "before_repository_tree_sha",
                "before_application_tree_sha",
                "after_commit_sha",
                "after_repository_tree_sha",
                "after_application_tree_sha",
            )
        }
        error = None
        ended_at = datetime.now(UTC).isoformat()
    else:
        raise ProtocolError("OWNER_AUTHORIZED_PARTIAL_EVIDENCE_STATUS_MISSING")
    members = []
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(source).as_posix()
        _safe_member_path(relative)
        members.append(
            {"path": relative, "size_bytes": path.stat().st_size, "sha256": _sha256(path)}
        )
    manifest = {
        "schema_version": "MONO_CI_PSI_PARTIAL_EXECUTION_ARCHIVE_V1",
        "classification": "PARTIAL_EXECUTION_EVIDENCE",
        "study_id": study_id,
        "execution_id": execution_id,
        "run_role": run_role,
        "source_identities": source_identities,
        "sandbox_preflight_id": sandbox_preflight_id,
        "phase_status": phase_status,
        "method_observation_status": method_status,
        "method_subprocess": method_process,
        "method_observation": method_observation,
        "error": error,
        "archive_error": dict(archive_failure) if archive_failure is not None else None,
        "ended_at_utc": ended_at,
        "member_count": len(members),
        "members": members,
    }
    validate_payload("mono_ci_psi_partial_execution_archive_v1.schema.json", manifest)
    destination = archive_path.resolve()
    if destination.exists() or Path(f"{destination}.sha256").exists():
        raise ProtocolError("OWNER_AUTHORIZED_PARTIAL_ARCHIVE_MUST_BE_NEW")
    with zipfile.ZipFile(
        destination, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as zipped:
        info = zipfile.ZipInfo("PARTIAL_EVIDENCE_MANIFEST.json", date_time=(1980, 1, 1, 0, 0, 0))
        info.external_attr = 0o100644 << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        zipped.writestr(info, pretty_json_bytes(manifest))
        for row in members:
            path = source / row["path"]
            info = zipfile.ZipInfo(f"run/{row['path']}", date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zipped.writestr(info, path.read_bytes())
    digest = _sha256(destination)
    Path(f"{destination}.sha256").write_text(f"{digest}  {destination.name}\n", encoding="ascii")
    verified = verify_partial_execution_archive(destination)
    return {
        "archive_name": destination.name,
        "archive_sha256": digest,
        "member_count": verified["member_count"],
        "verification_status": "PASS",
    }


def verify_partial_execution_archive(archive_path: Path) -> dict[str, Any]:
    """Verify a partial evidence archive without weakening complete-run verification."""
    archive = archive_path.resolve(strict=True)
    digest = _sha256(archive)
    sidecar = Path(f"{archive}.sha256")
    if (
        not sidecar.is_file()
        or sidecar.read_text(encoding="ascii").strip() != f"{digest}  {archive.name}"
    ):
        raise ContractValidationError("OWNER_AUTHORIZED_PARTIAL_ARCHIVE_SIDECAR_MISMATCH")
    try:
        with zipfile.ZipFile(archive) as zipped:
            names = zipped.namelist()
            if len(names) != len(set(names)) or "PARTIAL_EVIDENCE_MANIFEST.json" not in names:
                raise ContractValidationError("OWNER_AUTHORIZED_PARTIAL_ARCHIVE_INVENTORY_INVALID")
            manifest = json.loads(zipped.read("PARTIAL_EVIDENCE_MANIFEST.json"))
            validate_payload("mono_ci_psi_partial_execution_archive_v1.schema.json", manifest)
            declared = {row["path"]: row for row in manifest["members"]}
            expected = {f"run/{path}" for path in declared} | {"PARTIAL_EVIDENCE_MANIFEST.json"}
            if (
                manifest["member_count"] != len(declared)
                or len(declared) != len(manifest["members"])
                or set(names) != expected
            ):
                raise ContractValidationError(
                    "OWNER_AUTHORIZED_PARTIAL_ARCHIVE_MEMBER_SET_MISMATCH"
                )
            for relative, row in declared.items():
                _safe_member_path(relative)
                content = zipped.read(f"run/{relative}")
                if (
                    len(content) != row["size_bytes"]
                    or hashlib.sha256(content).hexdigest() != row["sha256"]
                ):
                    raise ContractValidationError(
                        "OWNER_AUTHORIZED_PARTIAL_ARCHIVE_MEMBER_DIGEST_MISMATCH"
                    )
    except (OSError, zipfile.BadZipFile, KeyError, json.JSONDecodeError) as error:
        raise ContractValidationError("OWNER_AUTHORIZED_PARTIAL_ARCHIVE_READ_FAILED") from error
    return {
        "archive_path": str(archive),
        "archive_sha256": digest,
        "member_count": len(declared),
        "verification_status": "PASS",
        "classification": "PARTIAL_EXECUTION_EVIDENCE",
        "method_observation_status": manifest["method_observation_status"],
    }


def verify_analysis_checksums(bundle: Path) -> list[dict[str, str]]:
    """Read back every generated analysis file listed in its checksum inventory."""
    checksums_path = bundle / "analysis/ANALYSIS_SHA256SUMS.json"
    if not checksums_path.is_file():
        return []
    checksums = _json(checksums_path)
    if not isinstance(checksums, dict) or not checksums:
        raise ContractValidationError("OWNER_AUTHORIZED_ANALYSIS_CHECKSUMS_INVALID")
    verified = []
    for relative, digest in checksums.items():
        _safe_member_path(relative)
        path = bundle / "analysis" / Path(*PurePosixPath(relative).parts)
        if (
            not isinstance(digest, str)
            or not path.is_file()
            or path.is_symlink()
            or _sha256(path) != digest
        ):
            raise ContractValidationError("OWNER_AUTHORIZED_ANALYSIS_DIGEST_MISMATCH:" + relative)
        verified.append({"path": relative, "sha256": digest})
    return verified


def _write_jsonl(path: Path, records: Iterable[Mapping[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False))
            handle.write("\n")


def _calibration_schedule(
    source_conditions: tuple[str, ...] = SOURCE_CONDITIONS,
) -> list[dict[str, Any]]:
    if not source_conditions or any(
        condition not in SOURCE_CONDITIONS for condition in source_conditions
    ):
        raise ProtocolError("OWNER_AUTHORIZED_CALIBRATION_SOURCE_CONDITIONS_INVALID")
    rng = random.Random(20261027)  # noqa: S311  # nosec B311 - preregistered order only
    cells = [
        {"evaluator_id": evaluator, "source_condition": condition}
        for condition in SOURCE_CONDITIONS
        for evaluator in EVALUATORS
        if condition in source_conditions
    ]
    schedule: list[dict[str, Any]] = []
    for repetition in range(CALIBRATION_WARMUPS + CALIBRATION_REPETITIONS):
        round_cells = list(cells)
        rng.shuffle(round_cells)
        for cell in round_cells:
            schedule.append(
                {
                    **cell,
                    "repetition_index": repetition,
                    "is_warmup": repetition < CALIBRATION_WARMUPS,
                }
            )
    return schedule


def _run_calibration(
    *,
    repository: Path,
    subject: Path,
    probe_checkout: Path,
    run_root: Path,
    uv_version: str,
    study_id: str = "MONO_CI_B0_PSI_DELTA_A5_OWNER_AUTHORIZED_DEV_V1",
    source_conditions: tuple[str, ...] = SOURCE_CONDITIONS,
    bind_source_repository: bool = False,
    require_source_readback: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    run_root.mkdir(parents=True, exist_ok=False)
    state_manifest_bytes = (
        subject / "architecture/states/A0_5_MODULE_DATA_OWNERSHIP.yaml"
    ).read_bytes()
    schedule = _calibration_schedule(source_conditions)
    start_budget = time.perf_counter()
    records: list[dict[str, Any]] = []
    for index, planned in enumerate(schedule):
        base = {
            "execution_id": study_id,
            "classification": "DEVELOPMENT_CALIBRATION",
            **planned,
            "attempt_index": index + 1,
            "runner_identity": _runner_identity(uv_version),
            "source_commit_sha": (
                A05_COMMIT
                if planned["source_condition"] == "A0_5_CLEAN"
                else _git(probe_checkout, "rev-parse", "HEAD")
            ),
            "source_tree_sha": None,
            "application_tree_sha": None,
            "evaluator_version": None,
            "configuration_sha256": _sha256(
                subject
                / EVALUATOR_CONFIGS.get(
                    planned["evaluator_id"], "architecture/acceptance/a1/data_ownership_v1.yaml"
                )
            ),
            "evaluator_source_sha256": None,
            "process_duration_ms": None,
            "scope_verification_duration_ms": None,
            "cpu_user_seconds": None,
            "cpu_system_seconds": None,
            "peak_rss_bytes": None,
            "memory_status": "NOT_AVAILABLE_PER_PROCESS",
            "process_exit_code": None,
            "execution_status": None,
            "compliance": None,
            "inspection_status": None,
            "inspection_counts": None,
            "finding_codes": [],
            "raw_output_path": None,
            "raw_output_sha256": None,
            "raw_stdout_sha256": None,
            "raw_stderr_sha256": None,
            "sample_status": None,
            "error": None,
            "started_at_utc": None,
            "ended_at_utc": None,
        }
        if time.perf_counter() - start_budget >= CALIBRATION_BUDGET_SECONDS:
            base["sample_status"] = "NOT_RUN_BUDGET_EXHAUSTED"
            records.append(base)
            continue
        checkout = subject if planned["source_condition"] == "A0_5_CLEAN" else probe_checkout
        source_sha = (
            A05_COMMIT
            if planned["source_condition"] == "A0_5_CLEAN"
            else _git(checkout, "rev-parse", "HEAD")
        )
        folder = (
            run_root
            / "PSI"
            / "evaluator-observations"
            / f"{planned['source_condition']}-{planned['evaluator_id']}"
            / f"round-{planned['repetition_index']:02d}"
        )
        before = _usage_snapshot()
        base["started_at_utc"] = datetime.now(UTC).isoformat()
        started = time.perf_counter()
        try:
            run, row = _run_bound_evaluator(
                repository=subject,
                source_checkout=checkout,
                source_repository=checkout if bind_source_repository else None,
                source_commit=source_sha,
                architecture_state=AFTER_STATE,
                evaluator_id=planned["evaluator_id"],
                output_directory=folder,
                configuration_bytes=(
                    subject
                    / EVALUATOR_CONFIGS.get(
                        planned["evaluator_id"], "architecture/acceptance/a1/data_ownership_v1.yaml"
                    )
                ).read_bytes(),
                state_manifest_bytes=state_manifest_bytes,
            )
            ended = time.perf_counter()
            base["ended_at_utc"] = datetime.now(UTC).isoformat()
            after = _usage_snapshot()
            coverage_path = run_root / row["coverage_path"]
            coverage = _json(coverage_path)
            expected_source_tree = _git(checkout, "rev-parse", "HEAD^{tree}")
            if require_source_readback and (
                row["source_commit_sha"] != source_sha
                or row["source_tree_sha"] != expected_source_tree
                or row["inspection_status"] != "COMPLETE"
                or coverage.get("source_inspection_status") != "COMPLETE"
                or coverage.get("counts", {}).get("missing_count") != 0
                or coverage.get("counts", {}).get("altered_count") != 0
                or coverage.get("counts", {}).get("unexpected_count") != 0
            ):
                raise ContractValidationError("OWNER_AUTHORIZED_CALIBRATION_SOURCE_READBACK_FAILED")
            base.update(
                {
                    "evaluator_source_sha256": row["evaluator_source_sha256"],
                    "source_tree_sha": row["source_tree_sha"],
                    "application_tree_sha": row["application_tree_sha"],
                    "evaluator_version": run.get("evidence", {})
                    .get("evaluator", {})
                    .get("version"),
                    "process_duration_ms": row["duration_ms"],
                    "scope_verification_duration_ms": round((ended - started) * 1000, 3),
                    "cpu_user_seconds": round(
                        _usage_delta(before, after)["self_user_seconds_delta"]
                        + _usage_delta(before, after)["child_user_seconds_delta"],
                        6,
                    ),
                    "cpu_system_seconds": round(
                        _usage_delta(before, after)["self_system_seconds_delta"]
                        + _usage_delta(before, after)["child_system_seconds_delta"],
                        6,
                    ),
                    "process_exit_code": row["process_exit_code"],
                    "execution_status": row["execution_status"],
                    "compliance": row["compliance"],
                    "inspection_status": coverage["source_inspection_status"],
                    "inspection_counts": coverage.get("counts"),
                    "finding_codes": row.get("finding_codes", []),
                    "raw_output_path": row["output_path"],
                    "raw_output_sha256": row["output_sha256"],
                    "raw_stdout_sha256": row["stdout_sha256"],
                    "raw_stderr_sha256": row["stderr_sha256"],
                    "sample_status": "MEASURED",
                }
            )
        except Exception as error:  # Preserve an actual failed or missing measurement.
            base["ended_at_utc"] = datetime.now(UTC).isoformat()
            after = _usage_snapshot()
            base.update(
                {
                    "scope_verification_duration_ms": round(
                        (time.perf_counter() - started) * 1000, 3
                    ),
                    "cpu_user_seconds": round(
                        _usage_delta(before, after)["self_user_seconds_delta"]
                        + _usage_delta(before, after)["child_user_seconds_delta"],
                        6,
                    ),
                    "cpu_system_seconds": round(
                        _usage_delta(before, after)["self_system_seconds_delta"]
                        + _usage_delta(before, after)["child_system_seconds_delta"],
                        6,
                    ),
                    "sample_status": "FAILED",
                    "error": {"type": type(error).__name__, "message": str(error)[:1000]},
                }
            )
        records.append(base)
    _write_jsonl(run_root / "measurement-records.jsonl", records)
    summary = {
        "planned_calls": len(schedule),
        "attempted_calls": sum(row["sample_status"] in {"MEASURED", "FAILED"} for row in records),
        "measured_calls": sum(row["sample_status"] == "MEASURED" for row in records),
        "failed_calls": sum(row["sample_status"] == "FAILED" for row in records),
        "not_run_calls": sum(row["sample_status"] == "NOT_RUN_BUDGET_EXHAUSTED" for row in records),
        "wall_duration_ms": round((time.perf_counter() - start_budget) * 1000, 3),
        "record_sha256": _sha256(run_root / "measurement-records.jsonl"),
    }
    _write_new_json(run_root / "calibration-summary.json", summary)
    return records, summary


def _method_outcome(run_root: Path, record: Mapping[str, Any]) -> dict[str, Any]:
    method_path = run_root / record["psi"]["raw_result_path"]
    method = _json(method_path)
    governance = method.get("governance", {})
    plan = method.get("operation_plan", {})
    candidate = method.get("candidate")
    return {
        "decision": governance.get("result"),
        "reason_codes": governance.get("reason_codes", []),
        "operation_plan": plan.get("operations", []),
        "operation_hold_reasons": plan.get("hold_reasons", []),
        "prediction_emitted": record["psi"].get("prediction_emitted"),
        "candidate_state": "NOT_MATERIALIZED" if candidate is None else "MATERIALIZED_UNAPPLIED",
        "candidate_sha256": method.get("candidate_sha256"),
        "candidate_changes": candidate.get("changes", []) if isinstance(candidate, dict) else [],
        "method_result_sha256": record["psi"]["raw_result_sha256"],
        "method_duration_ms": record["psi"]["execution_duration_ms"],
        "scoring": record["psi"]["scoring"],
    }


def _transition_outcome(run_root: Path, record: Mapping[str, Any]) -> dict[str, Any]:
    b0 = [
        {
            "architecture_state": row["architecture_state"],
            "evaluator_id": row["evaluator_id"],
            "duration_ms": row["duration_ms"],
            "exit_code": row["process_exit_code"],
            "execution_status": row["execution_status"],
            "compliance": row["compliance"],
            "source_commit_sha": row["source_commit_sha"],
            "output_sha256": row["output_sha256"],
        }
        for row in record["evaluator_observations"]
        if row["evaluator_id"] in {"AC_PUBLIC_API", "AC_MODULE_GRAPH"}
    ]
    extension = _json(run_root / record["a05_extension"]["path"])
    clean_ownership = extension["positive_condition"]["evaluator"]
    negative = extension["negative_condition"]["evaluators"]
    return {
        "execution_id": record["execution_id"],
        "source_revision_sha": record["source_revision_sha"],
        "study_readiness": record["study_readiness"],
        "measurement_status": record["measurement_status"],
        "p_algorithm_status": record["p_algorithm_status"],
        "g1": record["g1"],
        "g4": record["g4"],
        "reference_gate": record["reference_gate"],
        "B0": b0,
        "A0_5_clean_ownership": {
            "evaluator_id": clean_ownership["evaluator_id"],
            "compliance": clean_ownership["compliance"],
            "duration_ms": clean_ownership["duration_ms"],
            "finding_codes": clean_ownership["finding_codes"],
            "inspection_status": clean_ownership["inspection_status"],
            "output_sha256": clean_ownership["output_sha256"],
        },
        "existing_negative_probe": [
            {
                "evaluator_id": row["evaluator_id"],
                "compliance": row["compliance"],
                "duration_ms": row["duration_ms"],
                "finding_codes": row["finding_codes"],
                "inspection_status": row["inspection_status"],
                "output_sha256": row["output_sha256"],
            }
            for row in negative
        ],
        "Psi": _method_outcome(run_root, record),
    }


def _run_transitions(
    *,
    repository: Path,
    subject: Path,
    output_root: Path,
    artifact_root: Path,
    uv_version: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw_root = output_root / "transition-runs"
    raw_root.mkdir(parents=True, exist_ok=False)
    artifact_root.mkdir(parents=True, exist_ok=True)
    schedule = [
        {"role": "WARMUP", "index": 0, "measured": False},
        *[
            {"role": "MEASURED", "index": index, "measured": True}
            for index in range(1, TRANSITION_REPETITIONS + 1)
        ],
    ]
    records: list[dict[str, Any]] = []
    budget_start = time.perf_counter()
    for planned in schedule:
        execution_id = _transition_execution_id(planned["role"], planned["index"])
        run_root = raw_root / execution_id
        archive_path = artifact_root / (
            "transition-warmup.zip"
            if not planned["measured"]
            else f"transition-{planned['index']:02d}.zip"
        )
        row: dict[str, Any] = {
            **planned,
            "execution_id": execution_id,
            "classification": "EXPLORATORY_DEVELOPMENT",
            "run_archive": archive_path.name,
            "run_archive_sha256": None,
            "run_archive_verification": None,
            "full_transition_duration_ms": None,
            "cpu_user_seconds": None,
            "cpu_system_seconds": None,
            "run_status": None,
            "error": None,
            "outcome": None,
        }
        if planned["measured"] and time.perf_counter() - budget_start >= TRANSITION_BUDGET_SECONDS:
            row["run_status"] = "NOT_RUN_BUDGET_EXHAUSTED"
            records.append(row)
            continue
        before = _usage_snapshot()
        started = time.perf_counter()
        try:
            record = run_a05_transition(subject, run_root, execution_id)
            ended = time.perf_counter()
            after = _usage_snapshot()
            packed = pack_psi_transition_archive(
                run_root,
                archive_path,
                subject,
                "LOCAL_EXECUTION_NO_WORKFLOW",
                f"mono-ci-psi-a05-local-{execution_id}",
                uv_version,
                execution_origin="LOCAL",
            )
            verified = verify_psi_transition_archive(archive_path, repository=subject)
            row.update(
                {
                    "run_archive_sha256": packed["archive_sha256"],
                    "run_archive_verification": verified["verification_status"],
                    "full_transition_duration_ms": round((ended - started) * 1000, 3),
                    "cpu_user_seconds": round(
                        _usage_delta(before, after)["self_user_seconds_delta"]
                        + _usage_delta(before, after)["child_user_seconds_delta"],
                        6,
                    ),
                    "cpu_system_seconds": round(
                        _usage_delta(before, after)["self_system_seconds_delta"]
                        + _usage_delta(before, after)["child_system_seconds_delta"],
                        6,
                    ),
                    "run_status": "COMPLETED",
                    "outcome": _transition_outcome(run_root, record),
                }
            )
        except Exception as error:  # Preserve a failed execution without inventing a result.
            after = _usage_snapshot()
            row.update(
                {
                    "full_transition_duration_ms": round((time.perf_counter() - started) * 1000, 3),
                    "cpu_user_seconds": round(
                        _usage_delta(before, after)["self_user_seconds_delta"]
                        + _usage_delta(before, after)["child_user_seconds_delta"],
                        6,
                    ),
                    "cpu_system_seconds": round(
                        _usage_delta(before, after)["self_system_seconds_delta"]
                        + _usage_delta(before, after)["child_system_seconds_delta"],
                        6,
                    ),
                    "run_status": "FAILED",
                    "error": {"type": type(error).__name__, "message": str(error)[:1000]},
                }
            )
        records.append(row)
    summary = {
        "planned_runs": len(schedule),
        "completed_runs": sum(row["run_status"] == "COMPLETED" for row in records),
        "failed_runs": sum(row["run_status"] == "FAILED" for row in records),
        "not_run_runs": sum(row["run_status"] == "NOT_RUN_BUDGET_EXHAUSTED" for row in records),
        "wall_duration_ms": round((time.perf_counter() - budget_start) * 1000, 3),
        "technical_repetitions": TRANSITION_REPETITIONS,
        "architecture_level_units": 1,
    }
    return records, summary


def _transition_execution_id(role: str, index: int) -> str:
    return f"DEV_PSI_TRANSITION_OADEV_DELTA_A5_20261027_{role}_{index:02d}"


def run_study(
    repository: Path, output_root: Path, frozen_revision: str, uv_version: str
) -> dict[str, Any]:
    """Execute frozen calibration and full transition repetitions into a new output directory."""
    repo = repository.resolve(strict=True)
    freeze = verify_freeze(repo, frozen_revision)
    if not (shutil.which("bwrap") or shutil.which("sandbox-exec")):
        raise ProtocolError("OWNER_AUTHORIZED_NETWORK_ISOLATION_UNAVAILABLE")
    output = output_root.expanduser().absolute()
    if output.exists() or output.is_symlink() or output.is_relative_to(repo):
        raise ProtocolError("OWNER_AUTHORIZED_OUTPUT_MUST_BE_NEW_AND_EXTERNAL")
    output.mkdir(parents=True)
    subject = _clone_subject(repo, output / "subject-a05")
    _verify_subject_inputs(repo, subject, freeze)
    probe_output = output / "probe-source"
    with replay_negative_probe(
        subject,
        repo / HISTORICAL_PROBE_ROOT,
        expected_parent_commit=A05_COMMIT,
        expected_parent_tree=A05_TREE,
        expected_parent_application_tree=A05_APP_TREE,
        output=probe_output,
    ) as (probe_checkout, probe_manifest):
        probe_replay = {
            "status": "PASS",
            "source_commit_sha": probe_manifest["probe_commit_sha"],
            "repository_tree_sha": probe_manifest["probe_repository_tree_sha"],
            "application_tree_sha": probe_manifest["probe_application_tree_sha"],
            "changed_paths": probe_manifest["changed_paths"],
            "manifest_sha256": _sha256(repo / HISTORICAL_PROBE_ROOT / "probe-manifest.json"),
            "patch_sha256": _sha256(repo / HISTORICAL_PROBE_ROOT / "source.patch"),
            "historical_archive_sha256": freeze["historical_probe"][
                "historical_inner_archive_sha256"
            ],
            "classification": "HISTORICAL_PROBE_REPLAYED_FOR_NEW_CALIBRATION",
        }
    _write_new_json(output / "probe-replay.json", probe_replay)
    calibration_root = output / "calibration-raw"
    calibration_records, calibration_summary = _run_calibration(
        repository=repo,
        subject=subject,
        probe_checkout=probe_output,
        run_root=calibration_root,
        uv_version=uv_version,
    )
    protocol_snapshot = calibration_root / "protocol-inputs"
    protocol_snapshot.mkdir(parents=True, exist_ok=False)
    snapshot_paths = [
        PROTOCOL_ROOT / "CONTEXT.md",
        PROTOCOL_ROOT / "PROTOCOL_V1.md",
        PROTOCOL_JSON,
        FREEZE_PATH,
        PROTOCOL_ROOT / "REVIEW_DECISIONS.md",
        PROTOCOL_ROOT / "EVALUATOR_CAPABILITY_REVIEW_V1.md",
        Path("experiments/execution/schemas/mono_ci_psi_owner_authorized_protocol_v1.schema.json"),
        Path(
            "experiments/execution/schemas/mono_ci_psi_owner_authorized_pre_run_freeze_v1.schema.json"
        ),
        Path("experiments/execution/schemas/mono_ci_psi_owner_authorized_execution_v1.schema.json"),
        Path(
            "experiments/execution/schemas/mono_ci_psi_owner_authorized_calibration_archive_v1.schema.json"
        ),
        HISTORICAL_PROBE_ROOT / "probe-manifest.json",
        HISTORICAL_PROBE_ROOT / "source.patch",
        HISTORICAL_PROBE_ROOT / "source-files/app/modules/tasks/repository.py",
    ]
    for relative in snapshot_paths:
        destination = protocol_snapshot / relative.name
        shutil.copyfile(repo / relative, destination)
    calibration_archive = output / "artifact-bundle/calibration.zip"
    calibration_archive.parent.mkdir(parents=True, exist_ok=False)
    calibration_archive_record = pack_calibration_archive(calibration_root, calibration_archive)
    transition_records, transition_summary = _run_transitions(
        repository=repo,
        subject=subject,
        output_root=output,
        artifact_root=calibration_archive.parent,
        uv_version=uv_version,
    )
    execution = {
        "schema_version": "MONO_CI_PSI_OWNER_AUTHORIZED_EXECUTION_V1",
        "study_id": freeze["study_id"],
        "classification": "RESEARCH_OWNER_AUTHORIZED_EXPLORATORY_DEVELOPMENT",
        "freeze_commit": frozen_revision,
        "freeze_record_sha256": _sha256(repo / FREEZE_PATH),
        "protocol_sha256": _sha256(repo / PROTOCOL_JSON),
        "runner_identity": _runner_identity(uv_version),
        "authorization": {
            "provenance": "DIRECT_USER_CONVERSATION_INSTRUCTION",
            "identity_independently_verified": False,
            "signature_artifact": None,
        },
        "source_identities": freeze["source_identities"],
        "baseline": freeze["baseline"],
        "historical_probe_replay": probe_replay,
        "calibration": {
            **calibration_summary,
            "archive": calibration_archive_record,
            "classification": "DEVELOPMENT_CALIBRATION",
        },
        "transition_runs": transition_records,
        "transition_summary": transition_summary,
        "gates": {
            "study_readiness": "NO_GO_WITH_EXPLICIT_BLOCKERS",
            "P_ALGORITHM_STATUS": "NOT_READY",
            "G1": "INCOMPLETE",
            "G4": "NOT_AUTHORIZED",
            "reference": "NOT_READY",
            "scoring": "NOT_EXECUTED",
            "coverage": "UNKNOWN",
        },
        "interpretation_boundary": {
            "architecture_level_units": 1,
            "technical_repetitions": TRANSITION_REPETITIONS,
            "independent_validation": "NOT_PERFORMED",
            "candidate_application": "NOT_PERFORMED_BY_THIS_STUDY",
        },
    }
    validate_payload("mono_ci_psi_owner_authorized_execution_v1.schema.json", execution)
    _write_new_json(output / "artifact-bundle/study-execution.json", execution)
    _write_new_json(
        output / "artifact-bundle/study-execution.json.sha256.json",
        {"sha256": _sha256(output / "artifact-bundle/study-execution.json")},
    )
    return execution


def verify_bundle(bundle_root: Path, repository: Path) -> dict[str, Any]:
    """Verify all outer study artifacts and every nested transition archive."""
    bundle = bundle_root.resolve(strict=True)
    calibration = verify_calibration_archive(bundle / "calibration.zip")
    execution = _json(bundle / "study-execution.json")
    validate_payload("mono_ci_psi_owner_authorized_execution_v1.schema.json", execution)
    if execution.get("study_id") != "MONO_CI_B0_PSI_DELTA_A5_OWNER_AUTHORIZED_DEV_V1":
        raise ContractValidationError("OWNER_AUTHORIZED_STUDY_MANIFEST_INVALID")
    if (
        _sha256(bundle / "study-execution.json")
        != _json(bundle / "study-execution.json.sha256.json")["sha256"]
    ):
        raise ContractValidationError("OWNER_AUTHORIZED_STUDY_MANIFEST_DIGEST_MISMATCH")
    transition_results = []
    for row in execution["transition_runs"]:
        if row.get("run_archive_sha256") is None:
            continue
        path = bundle / row["run_archive"]
        verified = verify_psi_transition_archive(path, repository=repository)
        if (
            verified["archive_sha256"] != row["run_archive_sha256"]
            or verified["verification_status"] != "PASS"
        ):
            raise ContractValidationError("OWNER_AUTHORIZED_TRANSITION_ARCHIVE_BINDING_MISMATCH")
        transition_results.append(
            {
                "archive": path.name,
                "sha256": verified["archive_sha256"],
                "status": verified["verification_status"],
            }
        )
    verified_analysis = verify_analysis_checksums(bundle)
    return {
        "study_id": execution["study_id"],
        "classification": execution["classification"],
        "calibration_archive": calibration,
        "transition_archives": transition_results,
        "analysis_files": verified_analysis,
        "gates": execution["gates"],
        "verification_status": "PASS",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    freeze_parser = subparsers.add_parser("freeze")
    freeze_parser.add_argument("--repository", type=Path, required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--repository", type=Path, required=True)
    run_parser.add_argument("--output", type=Path, required=True)
    run_parser.add_argument("--frozen-revision", required=True)
    run_parser.add_argument("--uv-version", required=True)
    verify_parser = subparsers.add_parser("verify-bundle")
    verify_parser.add_argument("--bundle", type=Path, required=True)
    verify_parser.add_argument("--repository", type=Path, required=True)
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "freeze":
            result = create_freeze(arguments.repository)
            _write_new_json(arguments.repository / FREEZE_PATH, result)
        elif arguments.command == "run":
            result = run_study(
                arguments.repository,
                arguments.output,
                arguments.frozen_revision,
                arguments.uv_version,
            )
        else:
            result = verify_bundle(arguments.bundle, arguments.repository)
    except (ContractValidationError, ProtocolError, OSError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
