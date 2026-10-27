"""Execute, freeze, and verify owner-authorized ΔA5 DEVELOPMENT V2."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
import zipfile
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from experiments.execution.tooling import mono_ci_psi_a05 as a05
from experiments.execution.tooling import mono_ci_psi_owner_authorized as owner
from experiments.execution.tooling import mono_ci_psi_transition as transition
from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError, ProtocolError
from experiments.execution.tooling.hashing import (
    canonical_json_bytes,
    pretty_json_bytes,
    sha256_file,
)
from experiments.execution.tooling.mono_ci_b0_psi_archive import (
    pack_psi_transition_archive,
    verify_psi_transition_archive,
)
from experiments.execution.tooling.mono_ci_psi_a05 import (
    AFTER_STATE,
    replay_negative_probe,
    run_a05_transition,
)
from experiments.execution.tooling.mono_ci_psi_coverage import verify_inspection_coverage
from experiments.execution.tooling.mono_ci_psi_evidence import EVALUATOR_CONFIGS

STUDY_ID = "MONO_CI_B0_PSI_DELTA_A5_OWNER_AUTHORIZED_DEV_V2"
PROTOCOL_ROOT = Path("experiments/execution/mono-ci-b0-psi-delta-a5-owner-authorized-v2")
PROTOCOL_JSON = PROTOCOL_ROOT / "PROTOCOL_V2.json"
PROTOCOL_MD = PROTOCOL_ROOT / "PROTOCOL_V2.md"
FREEZE_PATH = PROTOCOL_ROOT / "PRE_RUN_FREEZE.json"
PRE_RUN_PREFLIGHT = PROTOCOL_ROOT / "PRE_RUN_SANDBOX_PREFLIGHT.json"
PRE_RUN_PREFLIGHT_SIDECAR = Path(f"{PRE_RUN_PREFLIGHT}.sha256")
PREMEASUREMENT_FAILURE = PROTOCOL_ROOT / "PREMEASUREMENT_FAILURE_40569757224.json"
PREMEASUREMENT_ARTIFACT = PROTOCOL_ROOT / "PREMEASUREMENT_PREFLIGHT_ARTIFACT_40569757224.zip"
PREMEASUREMENT_ARTIFACT_SIDECAR = Path(f"{PREMEASUREMENT_ARTIFACT}.sha256")
HISTORICAL_PROBE_ROOT = owner.HISTORICAL_PROBE_ROOT
V1_EXECUTION = (
    Path("experiments/execution/mono-ci-b0-psi-delta-a5-owner-authorized-v1")
    / "evidence/40499692594/study-execution.json"
)
V1_CALIBRATION = (
    Path("experiments/execution/mono-ci-b0-psi-delta-a5-owner-authorized-v1")
    / "evidence/40499692594/calibration.zip"
)
V1_CALIBRATION_SIDECAR = Path(f"{V1_CALIBRATION}.sha256")
V1_READBACK = (
    Path("experiments/execution/mono-ci-b0-psi-delta-a5-owner-authorized-v1")
    / "evidence/40499692594/POST_RUN_PROBE_READBACK.json"
)
V1_RECEIPT = (
    Path("experiments/execution/mono-ci-b0-psi-delta-a5-owner-authorized-v1")
    / "evidence/40499692594/EVIDENCE_RECEIPT.json"
)
PROTOCOL_SCHEMA = "mono_ci_psi_owner_authorized_protocol_v2.schema.json"
FREEZE_SCHEMA = "mono_ci_psi_owner_authorized_pre_run_freeze_v2.schema.json"
EXECUTION_SCHEMA = "mono_ci_psi_owner_authorized_execution_v2.schema.json"
PREFLIGHT_SCHEMA = "mono_ci_psi_docker_isolation_preflight_v1.schema.json"
PARTIAL_ARCHIVE_SCHEMA = "mono_ci_psi_partial_execution_archive_v1.schema.json"
TRANSITION_WARMUPS = 1
TRANSITION_REPETITIONS = 3
CALIBRATION_WARMUPS = 1
CALIBRATION_REPETITIONS = 10
CALIBRATION_BUDGET_SECONDS = 900
TRANSITION_BUDGET_SECONDS = 1800
TOTAL_BUDGET_SECONDS = 2700
V1_RUNNER_COMPARISON_FIELDS = (
    ("host_os", "operating_system"),
    ("host_architecture", "architecture"),
    ("host_python_version", "python_version"),
    ("host_python_implementation", "python_implementation"),
    ("host_cpu_count", "cpu_count"),
    ("runner_os", "runner_class"),
    ("runner_image_os", "runner_image_os"),
    ("runner_image_version", "runner_image_version"),
    ("uv_version", "uv_version"),
)


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return sha256_file(path)


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def _copy_tree(source: Path, destination: Path) -> None:
    if any(path.is_symlink() for path in source.rglob("*")):
        raise ProtocolError("OWNER_AUTHORIZED_V2_INPUT_SYMLINK_FORBIDDEN")
    shutil.copytree(source, destination)


def _read_preflight(
    path: Path, *, expected_host_identity: dict[str, Any] | None = None
) -> dict[str, Any]:
    root = path.resolve(strict=True)
    record_path = root / "sandbox-preflight.json" if root.is_dir() else root
    if record_path.name != "sandbox-preflight.json" or record_path.is_symlink():
        raise ContractValidationError("OWNER_AUTHORIZED_V2_PREFLIGHT_PATH_INVALID")
    sidecar_path = Path(f"{record_path}.sha256")
    if not sidecar_path.is_file() or sidecar_path.is_symlink():
        raise ContractValidationError("OWNER_AUTHORIZED_V2_PREFLIGHT_SIDECAR_MISSING")
    digest = _sha256(record_path)
    if sidecar_path.read_text(encoding="ascii").strip() != f"{digest}  {record_path.name}":
        raise ContractValidationError("OWNER_AUTHORIZED_V2_PREFLIGHT_SIDECAR_MISMATCH")
    record = _json(record_path)
    validate_payload(PREFLIGHT_SCHEMA, record)
    if record.get("verification_status") != "PASS" or not all(record["probes"].values()):
        raise ProtocolError("OWNER_AUTHORIZED_V2_ISOLATION_PREFLIGHT_FAILED")
    if expected_host_identity is not None and record.get("host_identity") != expected_host_identity:
        raise ProtocolError("OWNER_AUTHORIZED_V2_RUNNER_IDENTITY_MISMATCH")
    record["preflight_id"] = digest
    record["record_sha256"] = digest
    record["record_path"] = str(record_path)
    return record


def _evaluator_runtime_differences(host_identity: Mapping[str, Any]) -> list[dict[str, Any]]:
    v1 = _json(V1_EXECUTION)["runner_identity"]
    differences = []
    for current_key, v1_key in V1_RUNNER_COMPARISON_FIELDS:
        current = host_identity.get(current_key)
        previous = v1.get(v1_key)
        if current != previous:
            differences.append({"field": current_key, "v1_value": previous, "v2_value": current})
    return differences


def _calibration_source_conditions(host_identity: Mapping[str, Any]) -> tuple[str, ...]:
    if _evaluator_runtime_differences(host_identity):
        return ("A0_5_CLEAN", "EXISTING_NEGATIVE_PROBE")
    return ("EXISTING_NEGATIVE_PROBE",)


def _freeze_input_paths(repository: Path) -> list[str]:
    paths = set(owner._pinned_input_paths(repository))
    paths.update(
        {
            "AGENTS.md",
            "CONTEXT.md",
            "docs/RESEARCH_CONTEXT.md",
            "docs/TESTING.md",
            "experiments/execution/CONTEXT.md",
            "experiments/execution/tooling/CONTEXT.md",
            "experiments/execution/schemas/CONTEXT.md",
            "tests/CONTEXT.md",
            "tests/unit/CONTEXT.md",
            ".github/CONTEXT.md",
            ".github/workflows/CONTEXT.md",
            "Makefile",
            ".github/workflows/ci.yml",
            "experiments/execution/mono-ci-b0-psi-delta-a5-owner-authorized-v2/CONTEXT.md",
            PROTOCOL_MD.as_posix(),
            PROTOCOL_JSON.as_posix(),
            PREMEASUREMENT_FAILURE.as_posix(),
            PREMEASUREMENT_ARTIFACT.as_posix(),
            PREMEASUREMENT_ARTIFACT_SIDECAR.as_posix(),
            PRE_RUN_PREFLIGHT.as_posix(),
            PRE_RUN_PREFLIGHT_SIDECAR.as_posix(),
            "experiments/execution/tooling/mono_ci_psi_owner_authorized.py",
            "experiments/execution/tooling/mono_ci_psi_owner_authorized_analysis.py",
            "experiments/execution/tooling/mono_ci_psi_owner_authorized_v2.py",
            "experiments/execution/tooling/mono_ci_psi_owner_authorized_v2_analysis.py",
            "experiments/execution/tooling/mono_ci_psi_transition.py",
            "experiments/execution/tooling/mono_ci_psi_a05.py",
            "experiments/execution/tooling/mono_ci_psi_evidence.py",
            "experiments/execution/tooling/mono_ci_psi_coverage.py",
            "experiments/execution/tooling/mono_ci_b0_psi_archive.py",
            "experiments/execution/tooling/p_adaptation.py",
            "experiments/execution/tooling/p_governance.py",
            f"experiments/execution/schemas/{PROTOCOL_SCHEMA}",
            f"experiments/execution/schemas/{FREEZE_SCHEMA}",
            f"experiments/execution/schemas/{EXECUTION_SCHEMA}",
            f"experiments/execution/schemas/{PREFLIGHT_SCHEMA}",
            f"experiments/execution/schemas/{PARTIAL_ARCHIVE_SCHEMA}",
            "experiments/execution/schemas/mono_ci_psi_transition_run_v4.schema.json",
            "experiments/execution/schemas/mono_ci_psi_transition_archive_v4.schema.json",
            V1_EXECUTION.as_posix(),
            V1_CALIBRATION.as_posix(),
            V1_CALIBRATION_SIDECAR.as_posix(),
            V1_READBACK.as_posix(),
            V1_RECEIPT.as_posix(),
            "experiments/execution/mono-ci-b0-psi-delta-a5-owner-authorized-v1/analysis/RESULTS_RUN_40499692594_UK_V1.md",
            "tests/unit/test_mono_ci_psi_owner_authorized_v2.py",
            "tests/unit/test_mono_ci_psi_transition.py",
            "tests/unit/test_mono_ci_psi_evidence.py",
            "pyproject.toml",
            "uv.lock",
            "research_dashboard/requirements.lock",
        }
    )
    preflight_root = PROTOCOL_ROOT / "pre-run-preflight"
    if preflight_root.is_dir():
        for path in preflight_root.rglob("*"):
            if path.is_file():
                paths.add(path.as_posix())
    return sorted(paths)


def create_freeze(repository: Path, preflight_path: Path) -> dict[str, Any]:
    """Create the write-once V2 freeze from a successful hosted capability preflight."""
    repo = repository.resolve(strict=True)
    if owner._git(repo, "status", "--porcelain"):
        raise ProtocolError("OWNER_AUTHORIZED_V2_FREEZE_REQUIRES_CLEAN_CHECKOUT")
    if not (repo / PROTOCOL_JSON).is_file() or (repo / FREEZE_PATH).exists():
        raise ProtocolError("OWNER_AUTHORIZED_V2_PROTOCOL_OR_FREEZE_STATE_INVALID")
    validate_payload(PROTOCOL_SCHEMA, _json(repo / PROTOCOL_JSON))
    preflight = _read_preflight(preflight_path)
    preflight_file = Path(preflight["record_path"])
    expected_preflight = repo / PRE_RUN_PREFLIGHT
    expected_sidecar = repo / PRE_RUN_PREFLIGHT_SIDECAR
    if (
        not expected_preflight.is_file()
        or not expected_sidecar.is_file()
        or _sha256(expected_preflight) != _sha256(preflight_file)
        or expected_sidecar.read_text(encoding="ascii").strip()
        != f"{_sha256(expected_preflight)}  {expected_preflight.name}"
    ):
        raise ProtocolError("OWNER_AUTHORIZED_V2_PRE_RUN_PREFLIGHT_NOT_PRESERVED")
    host_identity = preflight["host_identity"]
    runtime_differences = _evaluator_runtime_differences(host_identity)
    source_conditions = _calibration_source_conditions(host_identity)
    paths = _freeze_input_paths(repo)
    missing = [value for value in paths if not (repo / value).is_file()]
    if missing:
        raise ProtocolError("OWNER_AUTHORIZED_V2_FREEZE_INPUT_MISSING:" + ",".join(missing))
    digests = {value: _sha256(repo / value) for value in paths}
    probe_root = repo / HISTORICAL_PROBE_ROOT
    freeze = {
        "schema_version": "MONO_CI_PSI_OWNER_AUTHORIZED_PRE_RUN_FREEZE_V2",
        "study_id": STUDY_ID,
        "classification": "PRE_REGISTERED_EXPLORATORY_DEVELOPMENT",
        "freeze_created_at_utc": datetime.now(UTC).isoformat(),
        "implementation_commit": owner._git(repo, "rev-parse", "HEAD"),
        "protocol_sha256": _sha256(repo / PROTOCOL_JSON),
        "pre_run_preflight_sha256": preflight["preflight_id"],
        "expected_host_identity": host_identity,
        "evaluator_runtime_comparison_to_v1": {
            "fields_compared": [item[0] for item in V1_RUNNER_COMPARISON_FIELDS],
            "differences": runtime_differences,
            "same_evaluator_runtime": not runtime_differences,
        },
        "source_identities": {
            "a04_commit": owner.A04_COMMIT,
            "a04_repository_tree": owner.A04_TREE,
            "a04_application_tree": owner.A04_APP_TREE,
            "a05_commit": owner.A05_COMMIT,
            "a05_repository_tree": owner.A05_TREE,
            "a05_application_tree": owner.A05_APP_TREE,
        },
        "baseline_sha256": _sha256(repo / owner.B0_RELATIVE),
        "historical_probe": {
            "manifest_sha256": _sha256(probe_root / "probe-manifest.json"),
            "patch_sha256": _sha256(probe_root / "source.patch"),
            "modified_source_sha256": _sha256(
                probe_root / "source-files/app/modules/tasks/repository.py"
            ),
            "historical_inner_archive_sha256": (
                "6e1b39df457d3053487a3123ab4f29e78467515c0925a58a36bb2dea26f7c563"
            ),
        },
        "input_sha256": digests,
        "measurement_plan": {
            "calibration_warmups_per_cell": CALIBRATION_WARMUPS,
            "calibration_measured_repetitions_per_cell": CALIBRATION_REPETITIONS,
            "calibration_source_conditions": list(source_conditions),
            "calibration_planned_process_calls": len(source_conditions)
            * 3
            * (1 + CALIBRATION_REPETITIONS),
            "transition_warmups": TRANSITION_WARMUPS,
            "transition_measured_repetitions": TRANSITION_REPETITIONS,
            "random_seed": 20261027,
            "calibration_budget_seconds": CALIBRATION_BUDGET_SECONDS,
            "transition_budget_seconds": TRANSITION_BUDGET_SECONDS,
            "total_execution_budget_seconds": TOTAL_BUDGET_SECONDS,
            "scoring": "NOT_EXECUTED",
            "coverage": "UNKNOWN",
            "official_g1": "INCOMPLETE",
            "official_g4": "NOT_AUTHORIZED",
        },
        "analysis_version": {
            "module": "experiments.execution.tooling.mono_ci_psi_owner_authorized_v2_analysis",
            "sha256": _sha256(
                repo / "experiments/execution/tooling/mono_ci_psi_owner_authorized_v2_analysis.py"
            ),
        },
    }
    validate_payload(FREEZE_SCHEMA, freeze)
    return freeze


def verify_freeze(repository: Path, frozen_revision: str) -> dict[str, Any]:
    """Require the exact pre-run freeze commit, its parent implementation, and digests."""
    repo = repository.resolve(strict=True)
    freeze = _json(repo / FREEZE_PATH)
    validate_payload(FREEZE_SCHEMA, freeze)
    changed = owner._git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD")
    if (
        owner._git(repo, "rev-parse", "HEAD") != frozen_revision
        or owner._git(repo, "rev-parse", "HEAD^") != freeze.get("implementation_commit")
        or changed.splitlines() != [FREEZE_PATH.as_posix()]
        or owner._git(repo, "status", "--porcelain")
    ):
        raise ProtocolError("OWNER_AUTHORIZED_V2_FREEZE_COMMIT_OR_WORKTREE_MISMATCH")
    for relative, digest in freeze["input_sha256"].items():
        path = repo / relative
        if not path.is_file() or path.is_symlink() or _sha256(path) != digest:
            raise ProtocolError("OWNER_AUTHORIZED_V2_FROZEN_INPUT_DIGEST_MISMATCH:" + relative)
    if (
        _sha256(repo / PROTOCOL_JSON) != freeze["protocol_sha256"]
        or _sha256(repo / owner.B0_RELATIVE) != freeze["baseline_sha256"]
        or _sha256(repo / PRE_RUN_PREFLIGHT) != freeze["pre_run_preflight_sha256"]
        or _json(repo / PROTOCOL_JSON)["study_id"] != STUDY_ID
    ):
        raise ProtocolError("OWNER_AUTHORIZED_V2_FREEZE_BINDING_MISMATCH")
    return freeze


def _runner_identity(uv_version: str, host_identity: Mapping[str, Any]) -> dict[str, Any]:
    result = owner._runner_identity(uv_version)
    result["network_isolation_binary"] = "docker"
    result["sandbox_image"] = transition.ISOLATED_METHOD_IMAGE
    result["sandbox_platform"] = transition.ISOLATED_METHOD_PLATFORM
    result["docker_client_version"] = host_identity["docker_client_version"]
    result["docker_server_version"] = host_identity["docker_server_version"]
    result["docker_kernel_version"] = host_identity["docker_kernel_version"]
    result["sandbox_host_uid"] = host_identity["host_uid"]
    result["sandbox_host_gid"] = host_identity["host_gid"]
    return result


def _v1_inspection_capability(
    repository: Path, subject: Path, probe_checkout: Path
) -> dict[str, Any]:
    """Recheck all preserved V1 probe bytes without rerunning or changing them."""
    with tempfile.TemporaryDirectory(prefix="mono-ci-a05-v1-scope-preflight-") as temporary:
        extraction = Path(temporary) / "calibration"
        owner.verify_calibration_archive(repository / V1_CALIBRATION, extract_to=extraction)
        records_path = extraction / "measurement-records.jsonl"
        records = [
            json.loads(line) for line in records_path.read_text().splitlines() if line.strip()
        ]
        readback_path = repository / V1_READBACK
        readback = _json(readback_path)
        probe_manifest = _json(repository / HISTORICAL_PROBE_ROOT / "probe-manifest.json")
        if (
            _sha256(repository / V1_CALIBRATION) != readback.get("calibration_archive_sha256")
            or _sha256(records_path) != readback.get("measurement_records_sha256")
            or readback.get("not_a_reexecution") is not True
            or readback.get("protocol_or_raw_outcomes_modified") is not False
            or readback.get("probe_replay", {}).get("source_commit_sha")
            != owner._git(probe_checkout, "rev-parse", "HEAD")
            or readback.get("probe_replay", {}).get("repository_tree_sha")
            != owner._git(probe_checkout, "rev-parse", "HEAD^{tree}")
            or readback.get("probe_replay", {}).get("application_tree_sha")
            != owner._git(probe_checkout, "rev-parse", "HEAD:app")
            or readback.get("probe_replay", {}).get("manifest_sha256")
            != _sha256(repository / HISTORICAL_PROBE_ROOT / "probe-manifest.json")
            or readback.get("probe_replay", {}).get("patch_sha256")
            != _sha256(repository / HISTORICAL_PROBE_ROOT / "source.patch")
            or probe_manifest.get("probe_commit_sha")
            != owner._git(probe_checkout, "rev-parse", "HEAD")
        ):
            raise ContractValidationError("OWNER_AUTHORIZED_V2_V1_READBACK_BINDING_MISMATCH")
        readback_rows = {
            (row.get("evaluator_id"), row.get("round")): row for row in readback.get("rows", [])
        }
        state_manifest = (
            subject / "architecture/states/A0_5_MODULE_DATA_OWNERSHIP.yaml"
        ).read_bytes()
        checked = []
        negative_records = [
            row for row in records if row["source_condition"] == "EXISTING_NEGATIVE_PROBE"
        ]
        if len(negative_records) != readback.get("counts", {}).get("archived_evaluator_outputs"):
            raise ContractValidationError("OWNER_AUTHORIZED_V2_V1_READBACK_ROW_COUNT_MISMATCH")
        for row in negative_records:
            evaluator_id = row["evaluator_id"]
            repetition_index = row["repetition_index"]
            readback_row = readback_rows.get((evaluator_id, repetition_index))
            output_path = (
                extraction
                / "PSI/evaluator-observations"
                / f"EXISTING_NEGATIVE_PROBE-{evaluator_id}"
                / f"round-{repetition_index:02d}"
                / "evaluator-output.json"
            )
            if readback_row is None or not output_path.is_file() or output_path.is_symlink():
                raise ContractValidationError("OWNER_AUTHORIZED_V2_V1_RAW_OUTPUT_MISSING")
            output_bytes = output_path.read_bytes()
            evidence = json.loads(output_bytes)
            expected_commit = owner._git(probe_checkout, "rev-parse", "HEAD")
            expected_tree = owner._git(probe_checkout, "rev-parse", "HEAD^{tree}")
            output_sha256 = _sha256(output_path)
            if (
                readback_row.get("source_commit_sha") != expected_commit
                or readback_row.get("source_tree_sha") != expected_tree
                or readback_row.get("raw_output_sha256") != output_sha256
                or readback_row.get("raw_sample_status") != row.get("sample_status")
                or row.get("sample_status") != "FAILED"
            ):
                raise ContractValidationError("OWNER_AUTHORIZED_V2_PROBE_READBACK_COMMIT_MISMATCH")
            coverage = verify_inspection_coverage(
                repository=probe_checkout,
                source_commit_sha=expected_commit,
                source_tree_sha=expected_tree,
                architecture_state=AFTER_STATE,
                evaluator_id=evaluator_id,
                evaluator_configuration_bytes=(
                    subject
                    / EVALUATOR_CONFIGS.get(
                        evaluator_id, "architecture/acceptance/a1/data_ownership_v1.yaml"
                    )
                ).read_bytes(),
                state_manifest_bytes=state_manifest,
                evaluator_output_bytes=output_bytes,
                evaluator_evidence=evidence,
            )
            counts = coverage.get("counts", {})
            if (
                coverage.get("source_inspection_status") != "COMPLETE"
                or counts.get("missing_count") != 0
                or counts.get("altered_count") != 0
                or counts.get("unexpected_count") != 0
                or readback_row.get("post_run_scope_status") != "COMPLETE"
                or readback_row.get("inspection_counts") != counts
            ):
                raise ContractValidationError("OWNER_AUTHORIZED_V2_SCOPE_PREFLIGHT_INCOMPLETE")
            checked.append(
                {
                    "evaluator_id": evaluator_id,
                    "round": repetition_index,
                    "original_sample_status": row.get("sample_status"),
                    "original_error": (row.get("error") or {}).get("message"),
                    "source_commit_sha": expected_commit,
                    "source_tree_sha": expected_tree,
                    "output_sha256": output_sha256,
                    "coverage_sha256": hashlib.sha256(canonical_json_bytes(coverage)).hexdigest(),
                    "source_inspection_status": coverage["source_inspection_status"],
                    "counts": counts,
                    "origin": (
                        "V1_PRESERVED_OUTPUT_RECOMPUTED_WITH_CURRENT_VERIFIER_"
                        "NO_NEW_EVALUATOR_PROCESS"
                    ),
                }
            )
        return {
            "verification_status": "PASS",
            "probe_rows": checked,
            "source_inspection_rows": len(checked),
            "post_run_scope_pass_rows": len(checked),
            "original_measurement_status_preserved": all(
                row["original_sample_status"] == "FAILED" for row in checked
            ),
        }


def _technical_preflight(
    repository: Path,
    subject: Path,
    probe_checkout: Path,
    preflight: Mapping[str, Any],
    output_root: Path,
) -> dict[str, Any]:
    output_probe = output_root / "output-permission-probe.txt"
    output_probe.write_text("writable\n", encoding="ascii")
    if output_probe.read_text(encoding="ascii") != "writable\n":
        raise ProtocolError("OWNER_AUTHORIZED_V2_OUTPUT_PERMISSION_CHECK_FAILED")
    baseline = a05._validate_a04_proposal(subject)
    if baseline.get("baseline_configuration_sha256") != _sha256(repository / owner.B0_RELATIVE):
        raise ContractValidationError("OWNER_AUTHORIZED_V2_BASELINE_IDENTITY_MISMATCH")
    inspection = _v1_inspection_capability(repository, subject, probe_checkout)
    if preflight.get("verification_status") != "PASS":
        raise ProtocolError("OWNER_AUTHORIZED_V2_ISOLATION_PREFLIGHT_REQUIRED")
    return {
        "schema_version": "MONO_CI_PSI_V2_TECHNICAL_PREFLIGHT_V1",
        "classification": "DEVELOPMENT_PRE_MEASUREMENT_PREFLIGHT",
        "verification_status": "PASS",
        "baseline_identity": {
            "status": baseline.get("identity_status"),
            "approval_status": baseline.get("approval_status"),
            "configuration_sha256": baseline.get("baseline_configuration_sha256"),
        },
        "probe_replay": {
            "source_commit_sha": owner._git(probe_checkout, "rev-parse", "HEAD"),
            "repository_tree_sha": owner._git(probe_checkout, "rev-parse", "HEAD^{tree}"),
            "application_tree_sha": owner._git(probe_checkout, "rev-parse", "HEAD:app"),
            "status": "PASS",
        },
        "source_inspection_capability": inspection,
        "sandbox_preflight_id": preflight["preflight_id"],
        "output_permission_probe_sha256": _sha256(output_probe),
        "archive_writer_imported": callable(owner.pack_partial_execution_archive),
        "partial_archive_verifier_imported": callable(owner.verify_partial_execution_archive),
        "complete_archive_verifier_imported": callable(verify_psi_transition_archive),
        "pre_measurement_execution_count": 0,
    }


def _preserve_technical_preflight_failure(
    output_root: Path,
    preflight: Mapping[str, Any],
    probe_replay: Mapping[str, Any],
    error: Exception,
) -> Path:
    """Preserve authentic pre-measurement inputs and diagnostics after a technical stop."""
    evidence_root = output_root / "early-failure-evidence"
    evidence_root.mkdir(parents=True, exist_ok=False)
    record = {
        "schema_version": "MONO_CI_PSI_V2_PREMEASUREMENT_FAILURE_V1",
        "classification": "PRE_MEASUREMENT_TECHNICAL_PREFLIGHT_FAILURE",
        "study_id": STUDY_ID,
        "failure_stage": "TECHNICAL_PREFLIGHT",
        "verification_status": "FAIL",
        "error_type": type(error).__name__,
        "error": str(error),
        "sandbox_preflight_id": preflight.get("preflight_id"),
        "calibration_status": "NOT_STARTED",
        "calibration_calls_started": 0,
        "transition_status": "NOT_STARTED",
        "transition_attempts_started": 0,
        "method_psi_status": "NOT_OBSERVED",
        "pre_measurement_execution_count": 0,
        "recorded_at_utc": datetime.now(UTC).isoformat(),
    }
    _write_json_new(evidence_root / "PREMEASUREMENT_FAILURE.json", record)
    _write_json_new(evidence_root / "probe-replay.json", dict(probe_replay))
    _copy_tree(Path(preflight["record_path"]).parent, evidence_root / "sandbox-preflight")
    _copy_tree(PROTOCOL_ROOT, evidence_root / "protocol-snapshot")
    output_probe = output_root / "output-permission-probe.txt"
    if output_probe.is_file() and not output_probe.is_symlink():
        _copy_file(output_probe, evidence_root / output_probe.name)
    return evidence_root


def _tree_inventory(root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ProtocolError("OWNER_AUTHORIZED_V2_PARTIAL_RAW_SYMLINK_FORBIDDEN")
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            owner._safe_member_path(relative)
            rows.append(
                {"path": relative, "size_bytes": path.stat().st_size, "sha256": _sha256(path)}
            )
    return rows


def _tree_digest(rows: list[dict[str, Any]]) -> str:
    return hashlib.sha256(canonical_json_bytes(rows)).hexdigest()


def _copy_partial_raw(run_root: Path, destination: Path) -> tuple[list[dict[str, Any]], str]:
    if destination.exists() or destination.is_symlink():
        raise ProtocolError("OWNER_AUTHORIZED_V2_PARTIAL_RAW_DESTINATION_MUST_BE_NEW")
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.rename(run_root, destination)
    except OSError:
        _copy_tree(run_root, destination)
    rows = _tree_inventory(destination)
    return rows, _tree_digest(rows)


def _run_transitions(
    *,
    repository: Path,
    subject: Path,
    output_root: Path,
    artifact_root: Path,
    uv_version: str,
    sandbox_preflight_id: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw_root = output_root / "transition-runs"
    raw_root.mkdir(parents=True, exist_ok=False)
    partial_root = artifact_root / "partial-runs"
    archive_root = artifact_root / "transition-archives"
    archive_root.mkdir(parents=True, exist_ok=True)
    schedule = [
        {"role": "WARMUP", "index": 0, "measured": False},
        *({"role": "MEASURED", "index": index, "measured": True} for index in range(1, 4)),
    ]
    records: list[dict[str, Any]] = []
    budget_start = time.perf_counter()
    for planned in schedule:
        execution_id = (
            f"DEV_PSI_TRANSITION_OADEV_V2_DELTA_A5_20261027_"
            f"{planned['role']}_{planned['index']:02d}"
        )
        run_root = raw_root / execution_id
        archive_name = (
            "transition-warmup.zip"
            if not planned["measured"]
            else f"transition-{planned['index']:02d}.zip"
        )
        archive_path = archive_root / archive_name
        row: dict[str, Any] = {
            **planned,
            "execution_id": execution_id,
            "classification": "EXPLORATORY_DEVELOPMENT",
            "run_status": None,
            "evidence_classification": "NO_ATTEMPT",
            "evidence_archive": None,
            "evidence_sha256": None,
            "evidence_verification": None,
            "raw_preservation_path": None,
            "raw_preservation_digest": None,
            "raw_preservation_members": [],
            "full_transition_duration_ms": None,
            "cpu_user_seconds": None,
            "cpu_system_seconds": None,
            "method_process_status": "NOT_OBSERVED",
            "method_decision": None,
            "method_execution_duration_ms": None,
            "operation_plan": None,
            "candidate_state": "NOT_OBSERVED",
            "outcome": None,
            "error": None,
        }
        if planned["measured"] and time.perf_counter() - budget_start >= TRANSITION_BUDGET_SECONDS:
            row["run_status"] = "NOT_RUN_BUDGET_EXHAUSTED"
            records.append(row)
            continue
        before = owner._usage_snapshot()
        started_at = datetime.now(UTC)
        started = time.perf_counter()
        try:
            run_record = run_a05_transition(
                subject,
                run_root,
                execution_id,
                isolation_backend="docker",
                preserve_partial_evidence=True,
                sandbox_preflight_id=sandbox_preflight_id,
            )
            ended = time.perf_counter()
            after = owner._usage_snapshot()
            packed = pack_psi_transition_archive(
                run_root,
                archive_path,
                subject,
                (
                    f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/"
                    f"{os.environ.get('GITHUB_REPOSITORY', 'Pan14ek/evofit-bench')}/actions/runs/"
                    f"{os.environ.get('GITHUB_RUN_ID')}"
                    if os.environ.get("GITHUB_RUN_ID")
                    else "LOCAL_EXECUTION_NO_WORKFLOW"
                ),
                (
                    f"mono-ci-psi-a05-v2-{execution_id}"
                    if os.environ.get("GITHUB_RUN_ID")
                    else f"mono-ci-psi-a05-local-{execution_id}"
                ),
                uv_version,
                execution_origin="HOSTED_CI" if os.environ.get("GITHUB_RUN_ID") else "LOCAL",
            )
            verified = verify_psi_transition_archive(archive_path, repository=subject)
            outcome = owner._transition_outcome(run_root, run_record)
            row.update(
                {
                    "run_status": "COMPLETED",
                    "evidence_classification": "COMPLETE_TRANSITION_ARCHIVE",
                    "evidence_archive": f"transition-archives/{archive_name}",
                    "evidence_sha256": packed["archive_sha256"],
                    "evidence_verification": verified["verification_status"],
                    "full_transition_duration_ms": round((ended - started) * 1000, 3),
                    "cpu_user_seconds": round(
                        owner._usage_delta(before, after)["self_user_seconds_delta"]
                        + owner._usage_delta(before, after)["child_user_seconds_delta"],
                        6,
                    ),
                    "cpu_system_seconds": round(
                        owner._usage_delta(before, after)["self_system_seconds_delta"]
                        + owner._usage_delta(before, after)["child_system_seconds_delta"],
                        6,
                    ),
                    "method_process_status": "COMPLETED",
                    "method_decision": outcome["Psi"]["decision"],
                    "method_execution_duration_ms": outcome["Psi"]["method_duration_ms"],
                    "operation_plan": outcome["Psi"]["operation_plan"],
                    "candidate_state": outcome["Psi"]["candidate_state"],
                    "outcome": outcome,
                }
            )
            if (run_root / "development_run.json").is_file():
                try:
                    successful_record = _json(run_root / "development_run.json")
                    observed = owner._transition_outcome(run_root, successful_record)
                    row.update(
                        {
                            "method_process_status": "COMPLETED",
                            "method_decision": observed["Psi"]["decision"],
                            "method_execution_duration_ms": observed["Psi"]["method_duration_ms"],
                            "operation_plan": observed["Psi"]["operation_plan"],
                            "candidate_state": observed["Psi"]["candidate_state"],
                            "outcome": observed,
                        }
                    )
                except Exception as readback_error:
                    row["method_readback_error"] = {
                        "type": type(readback_error).__name__,
                        "message": str(readback_error)[:1000],
                    }
        except Exception as error:  # Retain authentic raw data before returning a failure row.
            after = owner._usage_snapshot()
            row.update(
                {
                    "run_status": "FAILED",
                    "full_transition_duration_ms": round((time.perf_counter() - started) * 1000, 3),
                    "cpu_user_seconds": round(
                        owner._usage_delta(before, after)["self_user_seconds_delta"]
                        + owner._usage_delta(before, after)["child_user_seconds_delta"],
                        6,
                    ),
                    "cpu_system_seconds": round(
                        owner._usage_delta(before, after)["self_system_seconds_delta"]
                        + owner._usage_delta(before, after)["child_system_seconds_delta"],
                        6,
                    ),
                    "error": {"type": type(error).__name__, "message": str(error)[:2000]},
                }
            )
            if not run_root.exists():
                run_root.mkdir(parents=True)
                _write_json_new(
                    run_root / "partial-execution.json",
                    {
                        "schema_version": "MONO_CI_PSI_PARTIAL_TRANSITION_V1",
                        "classification": "PARTIAL_EXECUTION_EVIDENCE",
                        "execution_id": execution_id,
                        "started_at_utc": started_at.isoformat(),
                        "ended_at_utc": datetime.now(UTC).isoformat(),
                        "source_identities": {},
                        "phase_status": {
                            "source_identity": "NOT_EXECUTED",
                            "baseline_identity": "NOT_EXECUTED",
                            "b0_evaluator_matrix": "NOT_EXECUTED",
                            "method_input_bundle": "NOT_EXECUTED",
                            "method_execution": "NOT_OBSERVED",
                            "candidate_validation": "NOT_EXECUTED",
                            "complete_transition_verification": "NOT_EXECUTED",
                        },
                        "method_subprocess": None,
                        "method_observation": None,
                        "scientific_status": {
                            "method_decision": "NOT_OBSERVED",
                            "operation_plan": "NOT_OBSERVED",
                            "candidate": "NOT_OBSERVED",
                        },
                        "error": row["error"],
                        "available_artifacts": [],
                    },
                )
            if run_root.is_dir() and not run_root.is_symlink():
                try:
                    partial_root.mkdir(parents=True, exist_ok=True)
                    raw_destination = partial_root / execution_id
                    member_rows, raw_digest = _copy_partial_raw(run_root, raw_destination)
                    row.update(
                        {
                            "evidence_classification": "PARTIAL_EXECUTION_EVIDENCE",
                            "raw_preservation_path": f"partial-runs/{execution_id}",
                            "raw_preservation_digest": raw_digest,
                            "raw_preservation_members": member_rows,
                        }
                    )
                    partial_name = (
                        "transition-warmup-partial.zip"
                        if not planned["measured"]
                        else f"transition-{planned['index']:02d}-partial.zip"
                    )
                    partial_path = artifact_root / partial_name
                    packed_partial = owner.pack_partial_execution_archive(
                        raw_destination,
                        partial_path,
                        study_id=STUDY_ID,
                        execution_id=execution_id,
                        run_role=planned["role"],
                        sandbox_preflight_id=sandbox_preflight_id,
                    )
                    verified_partial = owner.verify_partial_execution_archive(partial_path)
                    row.update(
                        {
                            "evidence_archive": partial_name,
                            "evidence_sha256": packed_partial["archive_sha256"],
                            "evidence_verification": verified_partial["verification_status"],
                        }
                    )
                    progress = (
                        _json(raw_destination / "partial-execution.json")
                        if (raw_destination / "partial-execution.json").is_file()
                        else {}
                    )
                    row["method_process_status"] = (progress.get("method_subprocess") or {}).get(
                        "status", "NOT_OBSERVED"
                    )
                    observation = progress.get("method_observation") or {}
                    row["method_decision"] = observation.get("governance_decision")
                    row["operation_plan"] = observation.get("operations")
                    row["candidate_state"] = observation.get("candidate_state", "NOT_OBSERVED")
                    row["method_execution_duration_ms"] = (
                        progress.get("method_subprocess") or {}
                    ).get("execution_duration_ms")
                except Exception as archive_error:
                    row["partial_archive_error"] = {
                        "type": type(archive_error).__name__,
                        "message": str(archive_error)[:2000],
                    }
                    # Raw copy is still included by the outer bundle when partial archiving fails.
        records.append(row)
    summary = {
        "planned_runs": len(schedule),
        "completed_runs": sum(row["run_status"] == "COMPLETED" for row in records),
        "failed_runs": sum(row["run_status"] == "FAILED" for row in records),
        "not_run_runs": sum(row["run_status"] == "NOT_RUN_BUDGET_EXHAUSTED" for row in records),
        "complete_archives": sum(
            row["evidence_classification"] == "COMPLETE_TRANSITION_ARCHIVE" for row in records
        ),
        "partial_archives": sum(
            row["evidence_verification"] == "PASS"
            and row["evidence_classification"] == "PARTIAL_EXECUTION_EVIDENCE"
            for row in records
        ),
        "partial_raw_only": sum(
            row["raw_preservation_path"] is not None and row["evidence_verification"] is None
            for row in records
        ),
        "wall_duration_ms": round((time.perf_counter() - budget_start) * 1000, 3),
        "technical_repetitions": TRANSITION_REPETITIONS,
        "architecture_level_units": 1,
    }
    return records, summary


def run_study(
    repository: Path,
    output_root: Path,
    frozen_revision: str,
    uv_version: str,
    preflight_path: Path,
) -> dict[str, Any]:
    """Run the frozen V2 calibration and transition schedule after a fresh preflight."""
    repo = repository.resolve(strict=True)
    freeze = verify_freeze(repo, frozen_revision)
    preflight = _read_preflight(
        preflight_path,
        expected_host_identity=freeze["expected_host_identity"],
    )
    if preflight.get("host_identity", {}).get("uv_version") != uv_version:
        raise ProtocolError("OWNER_AUTHORIZED_V2_UV_VERSION_MISMATCH")
    output = output_root.expanduser().absolute()
    if output.exists() or output.is_symlink() or output.is_relative_to(repo):
        raise ProtocolError("OWNER_AUTHORIZED_V2_OUTPUT_MUST_BE_NEW_AND_EXTERNAL")
    output.mkdir(parents=True)
    subject = owner._clone_subject(repo, output / "subject-a05")
    subject_freeze = {
        **freeze,
        "protocol_and_execution_inputs_sha256": {
            relative: digest
            for relative, digest in freeze["input_sha256"].items()
            if relative.startswith(("architecture/", "fitness/"))
            or relative == owner.B0_RELATIVE.as_posix()
        },
    }
    owner._verify_subject_inputs(repo, subject, subject_freeze)
    probe_output = output / "probe-source"
    with replay_negative_probe(
        subject,
        repo / HISTORICAL_PROBE_ROOT,
        expected_parent_commit=owner.A05_COMMIT,
        expected_parent_tree=owner.A05_TREE,
        expected_parent_application_tree=owner.A05_APP_TREE,
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
            "historical_inner_archive_sha256": freeze["historical_probe"][
                "historical_inner_archive_sha256"
            ],
            "classification": "HISTORICAL_PROBE_REPLAYED_FOR_NEW_CALIBRATION",
        }
        try:
            technical_preflight = _technical_preflight(
                repo,
                subject,
                probe_checkout,
                preflight,
                output,
            )
        except Exception as error:
            try:
                _preserve_technical_preflight_failure(output, preflight, probe_replay, error)
            except Exception as preserve_error:
                error.add_note(
                    f"Pre-measurement evidence preservation also failed: {preserve_error}"
                )
            raise
        _write_json_new(output / "technical-preflight.json", technical_preflight)
        calibration_root = output / "calibration-raw"
    _calibration_records, calibration_summary = owner._run_calibration(
        repository=repo,
        subject=subject,
        probe_checkout=probe_checkout,
        run_root=calibration_root,
        uv_version=uv_version,
        study_id=STUDY_ID,
        source_conditions=tuple(freeze["measurement_plan"]["calibration_source_conditions"]),
        bind_source_repository=True,
        require_source_readback=True,
    )
    artifact_root = output / "artifact-bundle"
    artifact_root.mkdir(parents=True, exist_ok=False)
    _write_json_new(artifact_root / "probe-replay.json", probe_replay)
    _write_json_new(artifact_root / "technical-preflight.json", technical_preflight)
    _copy_tree(Path(preflight["record_path"]).parent, artifact_root / "sandbox-preflight")
    _copy_tree(PROTOCOL_ROOT, artifact_root / "protocol-snapshot")
    _copy_tree(repo / HISTORICAL_PROBE_ROOT, artifact_root / "probe-inputs")
    history = artifact_root / "historical-v1"
    history.mkdir()
    for relative in (
        V1_EXECUTION,
        V1_CALIBRATION,
        V1_CALIBRATION_SIDECAR,
        V1_READBACK,
        V1_RECEIPT,
    ):
        _copy_file(repo / relative, history / relative.name)
    calibration_archive_path = artifact_root / "calibration.zip"
    calibration_archive = owner.pack_calibration_archive(calibration_root, calibration_archive_path)
    transition_rows, transition_summary = _run_transitions(
        repository=repo,
        subject=subject,
        output_root=output,
        artifact_root=artifact_root,
        uv_version=uv_version,
        sandbox_preflight_id=preflight["preflight_id"],
    )
    record = {
        "schema_version": "MONO_CI_PSI_OWNER_AUTHORIZED_EXECUTION_V2",
        "study_id": STUDY_ID,
        "classification": "RESEARCH_OWNER_AUTHORIZED_EXPLORATORY_DEVELOPMENT",
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "workflow_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "workflow_run_url": (
            f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/"
            f"{os.environ.get('GITHUB_REPOSITORY', 'Pan14ek/evofit-bench')}/actions/runs/"
            f"{os.environ.get('GITHUB_RUN_ID')}/attempts/{os.environ.get('GITHUB_RUN_ATTEMPT')}"
            if os.environ.get("GITHUB_RUN_ID") and os.environ.get("GITHUB_RUN_ATTEMPT")
            else None
        ),
        "freeze_commit": frozen_revision,
        "freeze_record_sha256": _sha256(repo / FREEZE_PATH),
        "protocol_sha256": _sha256(repo / PROTOCOL_JSON),
        "runner_identity": _runner_identity(uv_version, preflight["host_identity"]),
        "sandbox_preflight": {
            "preflight_id": preflight["preflight_id"],
            "verification_status": preflight["verification_status"],
            "record_sha256": preflight["record_sha256"],
            "host_identity": preflight["host_identity"],
        },
        "authorization": {
            "provenance": "DIRECT_USER_CONVERSATION_INSTRUCTION",
            "identity_independently_verified": False,
            "signature_artifact": None,
        },
        "source_identities": freeze["source_identities"],
        "baseline": {
            "path": owner.B0_RELATIVE.as_posix(),
            "sha256": freeze["baseline_sha256"],
            "identity": "PROSPECTIVE_RECONSTRUCTED_NOT_HISTORICAL",
            "approval": "NOT_APPROVED",
        },
        "historical_v1": {
            "study_id": _json(repo / V1_EXECUTION)["study_id"],
            "workflow_run_id": 40499692594,
            "calibration_archive_sha256": _sha256(repo / V1_CALIBRATION),
            "post_run_readback_sha256": _sha256(repo / V1_READBACK),
            "evidence_receipt_sha256": _sha256(repo / V1_RECEIPT),
        },
        "historical_probe_replay": probe_replay,
        "technical_preflight": technical_preflight,
        "calibration": {
            **calibration_summary,
            "archive": calibration_archive,
            "classification": "DEVELOPMENT_CALIBRATION",
            "source_conditions": freeze["measurement_plan"]["calibration_source_conditions"],
            "runner_comparison_to_v1": freeze["evaluator_runtime_comparison_to_v1"],
        },
        "transition_runs": transition_rows,
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
            "v1_clean_samples_pooled": False,
        },
    }
    validate_payload(EXECUTION_SCHEMA, record)
    _write_json_new(artifact_root / "study-execution.json", record)
    _write_json_new(
        artifact_root / "study-execution.json.sha256.json",
        {"sha256": _sha256(artifact_root / "study-execution.json")},
    )
    return record


def _write_json_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(pretty_json_bytes(value))


def verify_bundle(bundle_root: Path, repository: Path) -> dict[str, Any]:
    """Verify V2 outer records, every complete/partial transition, and analysis checksums."""
    bundle = bundle_root.resolve(strict=True)
    repo = repository.resolve(strict=True)
    execution = _json(bundle / "study-execution.json")
    validate_payload(EXECUTION_SCHEMA, execution)
    if execution["study_id"] != STUDY_ID:
        raise ContractValidationError("OWNER_AUTHORIZED_V2_STUDY_MANIFEST_INVALID")
    freeze = verify_freeze(repo, execution["freeze_commit"])
    if (
        _sha256(repo / FREEZE_PATH) != execution["freeze_record_sha256"]
        or _sha256(repo / PROTOCOL_JSON) != execution["protocol_sha256"]
        or _sha256(bundle / "protocol-snapshot/PRE_RUN_FREEZE.json")
        != execution["freeze_record_sha256"]
        or freeze["expected_host_identity"] != execution["sandbox_preflight"]["host_identity"]
    ):
        raise ContractValidationError("OWNER_AUTHORIZED_V2_FREEZE_BINDING_MISMATCH")
    if (
        _sha256(bundle / "study-execution.json")
        != _json(bundle / "study-execution.json.sha256.json")["sha256"]
    ):
        raise ContractValidationError("OWNER_AUTHORIZED_V2_STUDY_MANIFEST_DIGEST_MISMATCH")
    calibration = owner.verify_calibration_archive(bundle / "calibration.zip")
    historical_calibration = owner.verify_calibration_archive(
        bundle / "historical-v1/calibration.zip"
    )
    historical_readback = _json(bundle / "historical-v1/POST_RUN_PROBE_READBACK.json")
    historical_record = execution.get("historical_v1", {})
    if (
        historical_calibration["archive_sha256"]
        != historical_readback.get("calibration_archive_sha256")
        or historical_calibration["archive_sha256"]
        != historical_record.get("calibration_archive_sha256")
        or _sha256(bundle / "historical-v1/POST_RUN_PROBE_READBACK.json")
        != historical_record.get("post_run_readback_sha256")
        or _sha256(bundle / "historical-v1/EVIDENCE_RECEIPT.json")
        != historical_record.get("evidence_receipt_sha256")
    ):
        raise ContractValidationError("OWNER_AUTHORIZED_V2_HISTORICAL_V1_BINDING_MISMATCH")
    transition_results = []
    for row in execution["transition_runs"]:
        if row["evidence_classification"] == "NO_ATTEMPT":
            if row["evidence_archive"] or row["evidence_sha256"] or row["raw_preservation_path"]:
                raise ContractValidationError("OWNER_AUTHORIZED_V2_NO_ATTEMPT_HAS_EVIDENCE")
            continue
        if row["evidence_archive"]:
            archive = bundle / row["evidence_archive"]
            if row["evidence_classification"] == "COMPLETE_TRANSITION_ARCHIVE":
                verified = verify_psi_transition_archive(archive, repository=repo)
            else:
                verified = owner.verify_partial_execution_archive(archive)
            if (
                verified["archive_sha256"] != row["evidence_sha256"]
                or verified["verification_status"] != "PASS"
            ):
                raise ContractValidationError(
                    "OWNER_AUTHORIZED_V2_TRANSITION_ARCHIVE_BINDING_MISMATCH"
                )
            transition_results.append(
                {
                    "archive": row["evidence_archive"],
                    "sha256": verified["archive_sha256"],
                    "classification": row["evidence_classification"],
                    "verification_status": "PASS",
                }
            )
        elif row["raw_preservation_path"]:
            raw_root = bundle / row["raw_preservation_path"]
            actual = _tree_inventory(raw_root)
            if (
                actual != row["raw_preservation_members"]
                or _tree_digest(actual) != row["raw_preservation_digest"]
            ):
                raise ContractValidationError("OWNER_AUTHORIZED_V2_PARTIAL_RAW_DIGEST_MISMATCH")
            transition_results.append(
                {
                    "path": row["raw_preservation_path"],
                    "sha256": row["raw_preservation_digest"],
                    "classification": "PARTIAL_EXECUTION_EVIDENCE_RAW_ONLY",
                    "verification_status": "PASS",
                }
            )
        else:
            raise ContractValidationError("OWNER_AUTHORIZED_V2_ATTEMPT_EVIDENCE_MISSING")
    sandbox = _read_preflight(bundle / "sandbox-preflight")
    if sandbox["preflight_id"] != execution["sandbox_preflight"]["preflight_id"]:
        raise ContractValidationError("OWNER_AUTHORIZED_V2_SANDBOX_PREFLIGHT_BINDING_MISMATCH")
    verified_analysis = owner.verify_analysis_checksums(bundle)
    return {
        "study_id": execution["study_id"],
        "classification": execution["classification"],
        "freeze_commit": execution["freeze_commit"],
        "workflow_run_id": execution.get("workflow_run_id"),
        "calibration_archive": calibration,
        "historical_v1_calibration_archive": historical_calibration,
        "transition_evidence": transition_results,
        "analysis_files": verified_analysis,
        "gates": execution["gates"],
        "verification_status": "PASS",
    }


def _preflight_cli(repository: Path, output: Path, freeze_path: Path | None) -> dict[str, Any]:
    expected = None
    if freeze_path is not None:
        freeze = _json(freeze_path)
        validate_payload(FREEZE_SCHEMA, freeze)
        expected = freeze["expected_host_identity"]
    result = transition.run_docker_isolation_preflight(
        repository, output, expected_host_identity=expected
    )
    validate_payload(
        PREFLIGHT_SCHEMA, {key: value for key, value in result.items() if key != "preflight_id"}
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    preflight_parser = subparsers.add_parser("preflight")
    preflight_parser.add_argument("--repository", type=Path, required=True)
    preflight_parser.add_argument("--output", type=Path, required=True)
    preflight_parser.add_argument("--freeze", type=Path)
    freeze_parser = subparsers.add_parser("freeze")
    freeze_parser.add_argument("--repository", type=Path, required=True)
    freeze_parser.add_argument("--preflight", type=Path, required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--repository", type=Path, required=True)
    run_parser.add_argument("--output", type=Path, required=True)
    run_parser.add_argument("--frozen-revision", required=True)
    run_parser.add_argument("--uv-version", required=True)
    run_parser.add_argument("--preflight", type=Path, required=True)
    verify_parser = subparsers.add_parser("verify-bundle")
    verify_parser.add_argument("--bundle", type=Path, required=True)
    verify_parser.add_argument("--repository", type=Path, required=True)
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "preflight":
            result = _preflight_cli(arguments.repository, arguments.output, arguments.freeze)
        elif arguments.command == "freeze":
            result = create_freeze(arguments.repository, arguments.preflight)
            _write_json_new(arguments.repository / FREEZE_PATH, result)
        elif arguments.command == "run":
            result = run_study(
                arguments.repository,
                arguments.output,
                arguments.frozen_revision,
                arguments.uv_version,
                arguments.preflight,
            )
        else:
            result = verify_bundle(arguments.bundle, arguments.repository)
    except (
        ContractValidationError,
        ProtocolError,
        OSError,
        json.JSONDecodeError,
        zipfile.BadZipFile,
    ) as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, indent=2))
    if arguments.command == "preflight" and result.get("verification_status") != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
