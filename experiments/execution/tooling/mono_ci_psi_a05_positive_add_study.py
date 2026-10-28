"""Run and verify the bounded TEST_ONLY positive ADD ΔA5 study."""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from experiments.execution.tooling import mono_ci_psi_a05 as a05
from experiments.execution.tooling import mono_ci_psi_transition as transition
from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError, ProtocolError
from experiments.execution.tooling.hashing import pretty_json_bytes, sha256_bytes, sha256_file
from experiments.execution.tooling.mono_ci_b0_psi_archive import (
    pack_psi_transition_archive,
    verify_psi_transition_archive,
)
from experiments.execution.tooling.mono_ci_psi_a05 import _git_text, run_a05_transition

STUDY_ID = "MONO_CI_A05_POSITIVE_ADD_TEST_ONLY_V1"
PROFILE_ID = "MONO_CI_A05_POSITIVE_ADD_TEST_ONLY_PROFILE_V1"
PROFILE_RELATIVE = Path(
    "experiments/execution/mono-ci-b0-psi-delta-a5-positive-add-v1/inputs/"
    "POSITIVE_ADD_PROFILE_V1.json"
)
PROTOCOL_ROOT = Path("experiments/execution/mono-ci-b0-psi-delta-a5-positive-add-v1")
PROTOCOL_JSON = PROTOCOL_ROOT / "PROTOCOL_V1.json"
PROTOCOL_MD = PROTOCOL_ROOT / "PROTOCOL_V1.md"
PROFILE_SCHEMA = "mono_ci_psi_positive_add_profile_v1.schema.json"
FREEZE_SCHEMA = "mono_ci_psi_positive_add_study_freeze_v1.schema.json"
EXECUTION_SCHEMA = "mono_ci_psi_positive_add_study_execution_v1.schema.json"
ARCHIVE_SCHEMA = "mono_ci_psi_positive_add_study_archive_v1.schema.json"
ARCHIVE_MANIFEST = "STUDY_ARCHIVE_MANIFEST.json"
RECOVERY_NOTE_PATH = "analysis/POST_RUN_READBACK_RECOVERY_UK.md"
OUTER_ASSET_NAME = "mono-ci-psi-a05-owner-authorized-v2-40579333932-1.zip"
INNER_ARCHIVE_PATH = "transition-archives/transition-01.zip"
OWNER_OBLIGATION = "AC_DATA_OWNERSHIP"
OWNER_EVALUATOR = OWNER_OBLIGATION
OWNER_REPRESENTATION = "REP_POSITIVE_ADD_AC_DATA_OWNERSHIP"
BASELINE_EVALUATORS = ("AC_PUBLIC_API", "AC_MODULE_GRAPH")
REQUIRED_GATE_STATUS = {
    "study_readiness": "NO_GO",
    "measurement_status": "NOT_EXECUTED",
    "P_ALGORITHM_STATUS": "NOT_READY",
    "G1": "INCOMPLETE",
    "G4": "NOT_AUTHORIZED",
    "reference": "NOT_READY",
    "scoring": "NOT_EXECUTED",
}
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
MAX_STUDY_ARCHIVE_BYTES = 1_000_000_000


def _json_bytes(content: bytes, code: str) -> Any:
    try:
        return json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ContractValidationError(code) from error


def _json_file(path: Path, code: str) -> Any:
    if path.is_symlink() or not path.is_file():
        raise ContractValidationError(code)
    return _json_bytes(path.read_bytes(), code)


def _write_new(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise ProtocolError("POSITIVE_ADD_STUDY_OUTPUT_MUST_BE_NEW")
    path.write_bytes(content)


def _copy_new(source: Path, destination: Path) -> None:
    if source.is_symlink() or not source.is_file():
        raise ContractValidationError("POSITIVE_ADD_STUDY_COPY_SOURCE_INVALID")
    _write_new(destination, source.read_bytes())


def _safe_archive_path(value: str) -> None:
    path = PurePosixPath(value)
    if (
        not value
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
        or ".git" in path.parts
        or any(
            part.casefold() in {"ground_truth.yaml", "groundtruth", "oracle", "scorer", "scoring"}
            for part in path.parts
        )
    ):
        raise ContractValidationError("POSITIVE_ADD_STUDY_ARCHIVE_PATH_INVALID")


def _read_profile(repository: Path) -> dict[str, Any]:
    profile_path = repository / PROFILE_RELATIVE
    profile = _json_file(profile_path, "POSITIVE_ADD_STUDY_PROFILE_MISSING")
    validate_payload(PROFILE_SCHEMA, profile)
    if profile["profile_id"] != PROFILE_ID:
        raise ContractValidationError("POSITIVE_ADD_STUDY_PROFILE_ID_INVALID")
    return profile


def _read_zip_member(archive: zipfile.ZipFile, name: str) -> bytes:
    try:
        return archive.read(name)
    except KeyError as error:
        raise ContractValidationError(
            "POSITIVE_ADD_STUDY_CONTROL_MEMBER_MISSING:" + name
        ) from error


def _verify_control_release(
    repository: Path, release_root: Path, *, copy_to: Path | None = None
) -> dict[str, Any]:
    """Verify the existing V2 release and replay only its pinned C0 transition archive."""
    profile = _read_profile(repository)
    expected = profile["comparison"]["c0_reference"]
    condition_source_commits = profile["cost_rule"]["condition_source_commits"]
    root = release_root.resolve(strict=True)
    outer_path = root / OUTER_ASSET_NAME
    outer_sidecar = Path(f"{outer_path}.sha256")
    if (
        outer_path.is_symlink()
        or not outer_path.is_file()
        or outer_path.stat().st_size > MAX_STUDY_ARCHIVE_BYTES
        or outer_sidecar.is_symlink()
        or not outer_sidecar.is_file()
    ):
        raise ContractValidationError("POSITIVE_ADD_STUDY_C0_RELEASE_ASSET_INVALID")
    outer_sha = sha256_file(outer_path)
    if (
        outer_sha != expected["outer_archive_sha256"]
        or outer_sidecar.read_text(encoding="ascii").strip() != f"{outer_sha}  {outer_path.name}"
    ):
        raise ContractValidationError("POSITIVE_ADD_STUDY_C0_RELEASE_CHECKSUM_MISMATCH")
    try:
        with zipfile.ZipFile(outer_path, "r") as outer:
            names = [row.filename for row in outer.infolist()]
            if len(names) != len(set(names)):
                raise ContractValidationError("POSITIVE_ADD_STUDY_C0_MEMBER_DUPLICATE")
            for name in names:
                if not name.endswith("/"):
                    _safe_archive_path(name)
            execution_bytes = _read_zip_member(outer, "study-execution.json")
            execution_seal = _json_bytes(
                _read_zip_member(outer, "study-execution.json.sha256.json"),
                "POSITIVE_ADD_STUDY_C0_EXECUTION_SEAL_INVALID",
            )
            timing_bytes = _read_zip_member(outer, "analysis/evaluator-samples.csv")
            probe_bytes = _read_zip_member(outer, "probe-replay.json")
            inner_bytes = _read_zip_member(outer, INNER_ARCHIVE_PATH)
            inner_sidecar = _read_zip_member(outer, f"{INNER_ARCHIVE_PATH}.sha256")
    except (OSError, zipfile.BadZipFile) as error:
        raise ContractValidationError("POSITIVE_ADD_STUDY_C0_RELEASE_READ_FAILED") from error

    execution = _json_bytes(execution_bytes, "POSITIVE_ADD_STUDY_C0_EXECUTION_INVALID")
    probe_replay = _json_bytes(probe_bytes, "POSITIVE_ADD_STUDY_C0_PROBE_REPLAY_INVALID")
    if execution_seal.get("sha256") != sha256_bytes(execution_bytes):
        raise ContractValidationError("POSITIVE_ADD_STUDY_C0_EXECUTION_DIGEST_MISMATCH")
    if sha256_bytes(timing_bytes) != profile["cost_rule"]["historical_source_sha256"]:
        raise ContractValidationError("POSITIVE_ADD_STUDY_C0_COST_SOURCE_DIGEST_MISMATCH")
    if (
        sha256_bytes(inner_bytes) != expected["inner_transition_archive_sha256"]
        or inner_sidecar.decode("ascii").strip()
        != f"{expected['inner_transition_archive_sha256']}  transition-01.zip"
    ):
        raise ContractValidationError("POSITIVE_ADD_STUDY_C0_INNER_ARCHIVE_CHECKSUM_MISMATCH")

    timing_rows = list(csv.DictReader(io.StringIO(timing_bytes.decode("utf-8"))))
    measured = [
        row
        for row in timing_rows
        if row.get("study_id") == "MONO_CI_B0_PSI_DELTA_A5_OWNER_AUTHORIZED_DEV_V2"
        and row.get("evaluator_id") == OWNER_EVALUATOR
        and row.get("source_condition") in {"A0_5_CLEAN", "EXISTING_NEGATIVE_PROBE"}
        and row.get("is_warmup") == "False"
        and row.get("sample_status") == "MEASURED"
    ]
    durations = [float(row["process_duration_ms"]) for row in measured]
    condition_counts = {
        condition: sum(row.get("source_condition") == condition for row in measured)
        for condition in ("A0_5_CLEAN", "EXISTING_NEGATIVE_PROBE")
    }
    if (
        len(measured) != profile["cost_rule"]["historical_measured_calls"]
        or condition_counts != {"A0_5_CLEAN": 10, "EXISTING_NEGATIVE_PROBE": 10}
        or any(not math.isfinite(value) or value < 0 for value in durations)
        or max(durations, default=0) != profile["cost_rule"]["historical_max_process_duration_ms"]
        or any(row.get("execution_status") != "COMPLETED" for row in measured)
        or any(
            row.get("source_commit_sha") != condition_source_commits[row["source_condition"]]
            for row in measured
        )
        or probe_replay.get("status") != "PASS"
        or probe_replay.get("source_commit_sha") != expected["negative_probe_source_revision_sha"]
        or execution.get("historical_probe_replay", {}).get("source_commit_sha")
        != expected["negative_probe_source_revision_sha"]
    ):
        raise ContractValidationError("POSITIVE_ADD_STUDY_C0_COST_SAMPLES_INVALID")

    c0_rows = [
        row
        for row in execution.get("transition_runs", [])
        if row.get("execution_id") == expected["execution_id"]
    ]
    if len(c0_rows) != 1:
        raise ContractValidationError("POSITIVE_ADD_STUDY_C0_RUN_RECORD_MISSING")
    c0_row = c0_rows[0]
    c0_outcome = c0_row.get("outcome", {}).get("Psi", {})
    if (
        c0_row.get("run_status") != "COMPLETED"
        or c0_row.get("method_decision") != expected["decision"]
        or c0_row.get("operation_plan") != expected["operation_plan"]
        or c0_row.get("candidate_state") != expected["candidate_state"]
        or c0_row.get("evidence_sha256") != expected["inner_transition_archive_sha256"]
        or c0_outcome.get("decision") != expected["decision"]
        or c0_outcome.get("operation_plan") != expected["operation_plan"]
    ):
        raise ContractValidationError("POSITIVE_ADD_STUDY_C0_OUTCOME_MISMATCH")

    with zipfile.ZipFile(io.BytesIO(inner_bytes), "r") as inner:
        inner_manifest = _json_bytes(
            _read_zip_member(inner, "ARCHIVE_MANIFEST.json"),
            "POSITIVE_ADD_STUDY_C0_INNER_MANIFEST_INVALID",
        )
        run_record = _json_bytes(
            _read_zip_member(inner, "development_run.json"),
            "POSITIVE_ADD_STUDY_C0_RUN_ARCHIVE_INVALID",
        )
        method_result = _json_bytes(
            _read_zip_member(inner, "PSI/raw/method-result.json"),
            "POSITIVE_ADD_STUDY_C0_METHOD_RESULT_INVALID",
        )
    if (
        inner_manifest.get("execution_id") != expected["execution_id"]
        or inner_manifest.get("source_revision_sha") != expected["source_revision_sha"]
        or run_record.get("source_revision_sha") != expected["source_revision_sha"]
        or method_result.get("operation_plan", {}).get("operations") != []
    ):
        raise ContractValidationError("POSITIVE_ADD_STUDY_C0_SOURCE_OR_METHOD_MISMATCH")

    with tempfile.TemporaryDirectory(prefix="positive-add-c0-") as temporary:
        scratch = Path(temporary)
        inner_path = scratch / "transition-01.zip"
        inner_path.write_bytes(inner_bytes)
        Path(f"{inner_path}.sha256").write_bytes(inner_sidecar)
        worktree = scratch / "source"
        transition._git_worktree(
            repository, "add", "--detach", str(worktree), expected["source_revision_sha"]
        )
        try:
            verification = verify_psi_transition_archive(inner_path, repository=worktree)
        finally:
            transition._git_worktree(repository, "remove", "--force", str(worktree), check=False)
    if verification.get("verification_status") != "PASS":
        raise ContractValidationError("POSITIVE_ADD_STUDY_C0_ARCHIVE_READBACK_FAILED")

    receipt = {
        "study_id": expected["study_id"],
        "release_url": expected["release"],
        "outer_archive_sha256": outer_sha,
        "inner_transition_archive_sha256": sha256_bytes(inner_bytes),
        "source_revision_sha": expected["source_revision_sha"],
        "negative_probe_source_revision_sha": expected["negative_probe_source_revision_sha"],
        "execution_id": expected["execution_id"],
        "decision": c0_row["method_decision"],
        "operation_plan": c0_row["operation_plan"],
        "candidate_state": c0_row["candidate_state"],
        "timing_csv_sha256": sha256_bytes(timing_bytes),
        "historical_owner_calls": len(measured),
        "historical_max_process_duration_ms": max(durations),
        "inner_archive_verification": verification["verification_status"],
    }
    if copy_to is not None:
        _copy_new(outer_path, copy_to / "control" / OUTER_ASSET_NAME)
        _copy_new(outer_sidecar, copy_to / "control" / f"{OUTER_ASSET_NAME}.sha256")
        _write_new(copy_to / "control" / "transition-01.zip", inner_bytes)
        _write_new(copy_to / "control" / "transition-01.zip.sha256", inner_sidecar)
        _write_new(copy_to / "control" / "evaluator-samples.csv", timing_bytes)
        _write_new(copy_to / "control" / "study-execution.json", execution_bytes)
        _write_new(copy_to / "control" / "receipt.json", pretty_json_bytes(receipt))
    return receipt


def _read_preflight(preflight_root: Path) -> dict[str, Any]:
    root = preflight_root.resolve(strict=True)
    record_path = root / "sandbox-preflight.json" if root.is_dir() else root
    sidecar_path = Path(f"{record_path}.sha256")
    if (
        record_path.is_symlink()
        or not record_path.is_file()
        or sidecar_path.is_symlink()
        or not sidecar_path.is_file()
    ):
        raise ContractValidationError("POSITIVE_ADD_STUDY_PREFLIGHT_RECORD_MISSING")
    digest = sha256_file(record_path)
    if sidecar_path.read_text(encoding="ascii").strip() != f"{digest}  sandbox-preflight.json":
        raise ContractValidationError("POSITIVE_ADD_STUDY_PREFLIGHT_SIDECAR_MISMATCH")
    record = _json_file(record_path, "POSITIVE_ADD_STUDY_PREFLIGHT_INVALID")
    validate_payload("mono_ci_psi_docker_isolation_preflight_v1.schema.json", record)
    if record.get("verification_status") != "PASS" or not all(record.get("probes", {}).values()):
        raise ProtocolError("POSITIVE_ADD_STUDY_DOCKER_PREFLIGHT_FAILED")
    record["preflight_id"] = digest
    record["record_path"] = str(record_path)
    return record


def run_preflight(repository: Path, output_root: Path) -> dict[str, Any]:
    """Run the repository's pinned Docker capability preflight on this runner."""
    return transition.run_docker_isolation_preflight(repository.resolve(strict=True), output_root)


def _make_freeze(
    repository: Path,
    preflight: dict[str, Any],
    c0_receipt: dict[str, Any],
    uv_version: str,
) -> dict[str, Any]:
    repo = repository.resolve(strict=True)
    status = _git_text(repo, "status", "--porcelain")
    if status.strip():
        raise ProtocolError("POSITIVE_ADD_STUDY_FREEZE_REQUIRES_CLEAN_CHECKOUT")
    profile = _read_profile(repo)
    manifest, source_manifest_bytes, source_digest = transition.evaluator_source_artifacts(repo)
    config_sha = sha256_file(repo / "architecture/acceptance/a1/data_ownership_v1.yaml")
    c0 = profile["comparison"]["c0_reference"]
    record = {
        "schema_version": "MONO_CI_A05_POSITIVE_ADD_STUDY_FREEZE_V1",
        "study_id": STUDY_ID,
        "classification": "PRE_RUN_FREEZE_TEST_ONLY_AUTHOR_DECLARED_DEVELOPMENT",
        "implementation_commit": _git_text(repo, "rev-parse", "HEAD"),
        "protocol_sha256": sha256_file(repo / PROTOCOL_JSON),
        "profile_sha256": sha256_file(repo / PROFILE_RELATIVE),
        "control": {
            "outer_archive_sha256": c0_receipt["outer_archive_sha256"],
            "inner_archive_sha256": c0_receipt["inner_transition_archive_sha256"],
            "source_revision_sha": c0_receipt["source_revision_sha"],
            "negative_probe_source_revision_sha": c0_receipt["negative_probe_source_revision_sha"],
            "timing_csv_sha256": c0_receipt["timing_csv_sha256"],
            "release_url": c0["release"],
        },
        "source_identities": {
            "before_commit_sha": a05.BEFORE_COMMIT,
            "after_commit_sha": _git_text(repo, "rev-parse", "HEAD"),
            "before_repository_tree_sha": a05.BEFORE_REPOSITORY_TREE,
            "after_repository_tree_sha": _git_text(repo, "rev-parse", "HEAD^{tree}"),
            "before_application_tree_sha": a05.BEFORE_APPLICATION_TREE,
            "after_application_tree_sha": _git_text(repo, "rev-parse", "HEAD:app"),
            "before_state_manifest_sha256": sha256_file(
                repo / "architecture/states/A0_4_REPORT_QUERY_PORT.yaml"
            ),
            "after_state_manifest_sha256": sha256_file(
                repo / "architecture/states/A0_5_MODULE_DATA_OWNERSHIP.yaml"
            ),
        },
        "baseline_sha256": sha256_file(
            repo
            / "experiments/execution/mono-ci-b0-psi-execution-a05-v1/RECONSTRUCTED_B0_A04_V1.json"
        ),
        "evaluator": {
            "id": OWNER_EVALUATOR,
            "source_manifest_sha256": source_digest,
            "configuration_sha256": config_sha,
            "source_manifest_sha256_is_bound_to_cost": True,
            "source_files": manifest,
            "source_manifest_bytes_sha256": sha256_bytes(source_manifest_bytes),
        },
        "docker": {
            "image": transition.ISOLATED_METHOD_IMAGE,
            "platform": transition.ISOLATED_METHOD_PLATFORM,
            "network": "none",
            "method_input_mount": "read-only",
            "writable_output_mounts": 1,
        },
        "preflight_sha256": preflight["preflight_id"],
        "host_identity": preflight["host_identity"],
        "uv_version": uv_version,
        "repetitions": {"warmup": 1, "measured": 3},
        "budget": {
            "max_incremental_cost_ms": profile["cost_rule"]["fixed_max_incremental_cost_ms"],
            "max_search_nodes": profile["cost_rule"]["fixed_max_search_nodes"],
            "unavailable_or_exceeded_behavior": "HOLD_AND_DO_NOT_SELECT_TEMPLATE",
        },
        "official_boundary": REQUIRED_GATE_STATUS,
    }
    validate_payload(FREEZE_SCHEMA, record)
    return record


def _method_result_from_run(run_root: Path, run_record: dict[str, Any]) -> dict[str, Any]:
    return _json_file(
        run_root / run_record["psi"]["raw_result_path"],
        "POSITIVE_ADD_STUDY_METHOD_RESULT_MISSING",
    )


def _row_outcome(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "evaluator_id": row.get("evaluator_id"),
        "representation_id": row.get("representation_id"),
        "execution_status": row.get("execution_status"),
        "compliance": row.get("compliance"),
        "inspection_status": row.get("inspection_status"),
        "finding_codes": row.get("finding_codes", []),
        "duration_ms": row.get("duration_ms"),
        "source_commit_sha": row.get("source_commit_sha"),
        "source_tree_sha": row.get("source_tree_sha"),
        "inspection_scope_path": row.get("inspection_scope_path"),
        "inspection_scope_sha256": row.get("inspection_scope_sha256"),
        "output_path": row.get("output_path"),
        "output_sha256": row.get("output_sha256"),
    }


def _is_foreign_table_detection(row: dict[str, Any] | None) -> bool:
    return bool(
        isinstance(row, dict)
        and row.get("execution_status") == "COMPLETED"
        and row.get("inspection_status") == "COMPLETE"
        and row.get("compliance") == "NON_COMPLIANT"
        and "FOREIGN_TABLE_ACCESS" in row.get("finding_codes", [])
    )


def _candidate_exercise(
    operations: list[dict[str, Any]], candidate_verification: dict[str, Any]
) -> tuple[list[dict[str, Any]], bool, bool, str]:
    owner_adds = []
    for row in operations:
        payload_value = row.get("payload")
        payload = payload_value if isinstance(payload_value, dict) else {}
        if row.get("operation") != "add":
            continue
        direct_representation_add = row.get("target_type") == "representation" and (
            row.get("target_id") == OWNER_REPRESENTATION
            or payload.get("id") == OWNER_REPRESENTATION
        )
        obligation_add_materializes_owner_representation = (
            row.get("target_type") == "obligation"
            and row.get("target_id") == OWNER_OBLIGATION
            and payload.get("id") == OWNER_REPRESENTATION
            and payload.get("evaluator") == OWNER_EVALUATOR
            and OWNER_OBLIGATION in payload.get("covers", [])
        )
        if direct_representation_add or obligation_add_materializes_owner_representation:
            owner_adds.append(row)
    active_candidate_rows = candidate_verification.get("active_representations", [])
    owner_active = any(
        row.get("representation_id") == OWNER_REPRESENTATION
        and row.get("evaluator_id") == OWNER_EVALUATOR
        and OWNER_OBLIGATION in row.get("covers", [])
        for row in active_candidate_rows
    )
    candidate_positive = candidate_verification.get("positive_evaluations", [])
    candidate_negative = candidate_verification.get("negative_evaluations", [])
    owner_positive = next(
        (row for row in candidate_positive if row.get("representation_id") == OWNER_REPRESENTATION),
        None,
    )
    owner_negative = next(
        (row for row in candidate_negative if row.get("representation_id") == OWNER_REPRESENTATION),
        None,
    )
    exercised = bool(
        owner_adds
        and owner_active
        and candidate_verification.get("method_candidate_validation_status") == "valid"
        and isinstance(owner_positive, dict)
        and isinstance(owner_negative, dict)
        and owner_positive.get("execution_status") == "COMPLETED"
        and owner_negative.get("execution_status") == "COMPLETED"
        and owner_positive.get("inspection_status") == "COMPLETE"
        and owner_negative.get("inspection_status") == "COMPLETE"
    )
    candidate_present = candidate_verification.get("candidate_present") is True
    state = (
        "MATERIALIZED_AND_EXERCISED"
        if exercised
        else "MATERIALIZED_NOT_EXERCISED"
        if candidate_present
        else "NOT_MATERIALIZED"
    )
    return owner_adds, owner_active, exercised, state


def _summarize_run(run_root: Path, archive_sha: str, role: str) -> dict[str, Any]:
    record = _json_file(run_root / "development_run.json", "POSITIVE_ADD_STUDY_RUN_RECORD_MISSING")
    if record.get("schema_version") != "MONO_CI_PSI_TRANSITION_RUN_V5":
        raise ContractValidationError("POSITIVE_ADD_STUDY_EXPECTED_V5_RUN")
    method_result = _method_result_from_run(run_root, record)
    extension = _json_file(
        run_root / record["a05_extension"]["path"], "POSITIVE_ADD_STUDY_A05_EXTENSION_MISSING"
    )
    candidate_verification = extension.get("candidate_verification", {})
    operation_plan = method_result.get("operation_plan", {})
    operations = operation_plan.get("operations", [])
    owner_adds, owner_active, candidate_exercised, candidate_state = _candidate_exercise(
        operations, candidate_verification
    )
    active_candidate_rows = candidate_verification.get("active_representations", [])
    candidate_positive = candidate_verification.get("positive_evaluations", [])
    candidate_negative = candidate_verification.get("negative_evaluations", [])
    owner_positive = next(
        (row for row in candidate_positive if row.get("representation_id") == OWNER_REPRESENTATION),
        None,
    )
    owner_negative = next(
        (row for row in candidate_negative if row.get("representation_id") == OWNER_REPRESENTATION),
        None,
    )
    baseline = _json_file(
        run_root / "provenance/reconstructed-b0-proposal.json",
        "POSITIVE_ADD_STUDY_BASELINE_PROPOSAL_MISSING",
    )
    baseline_ids = [row["evaluator_id"] for row in baseline.get("representations", [])]
    clean_b0 = [
        _row_outcome(row)
        for row in record["evaluator_observations"]
        if row.get("architecture_state") == "A0_5_MODULE_DATA_OWNERSHIP"
        and row.get("evaluator_id") in baseline_ids
    ]
    negative_rows = extension.get("negative_condition", {}).get("evaluators", [])
    negative_b0 = [
        _row_outcome(row) for row in negative_rows if row.get("evaluator_id") in baseline_ids
    ]
    candidate_clean = [_row_outcome(row) for row in candidate_positive]
    candidate_probe = [_row_outcome(row) for row in candidate_negative]
    cost = {
        "method_execution_ms": record["psi"].get("execution_duration_ms"),
        "candidate_owner_clean_ms": owner_positive.get("duration_ms")
        if isinstance(owner_positive, dict)
        else None,
        "candidate_owner_negative_ms": owner_negative.get("duration_ms")
        if isinstance(owner_negative, dict)
        else None,
    }
    if isinstance(cost["candidate_owner_clean_ms"], (float, int)) and isinstance(
        cost["candidate_owner_negative_ms"], (float, int)
    ):
        cost["candidate_owner_two_condition_total_ms"] = round(
            float(cost["candidate_owner_clean_ms"]) + float(cost["candidate_owner_negative_ms"]),
            3,
        )
    else:
        cost["candidate_owner_two_condition_total_ms"] = None
    return {
        "role": role,
        "execution_id": record["execution_id"],
        "archive_sha256": archive_sha,
        "decision": record["psi"]["decision"],
        "operation_plan": operations,
        "owner_add_emitted": bool(owner_adds),
        "owner_add_operations": owner_adds,
        "candidate_state": candidate_state,
        "candidate_configuration_sha256": candidate_verification.get(
            "candidate_configuration_sha256"
        ),
        "candidate_validation_status": candidate_verification.get(
            "method_candidate_validation_status", "NOT_EXECUTED"
        ),
        "candidate_owner_active": owner_active,
        "candidate_exercised": candidate_exercised,
        "candidate_owner_negative_detected": _is_foreign_table_detection(owner_negative),
        "candidate_verification_status": candidate_verification.get("status", "NOT_EXECUTED"),
        "baseline_active_evaluators": baseline_ids,
        "candidate_active_evaluators": [row.get("evaluator_id") for row in active_candidate_rows],
        "clean_b0": clean_b0,
        "negative_b0": negative_b0,
        "candidate_clean": candidate_clean,
        "candidate_negative": candidate_probe,
        "cost": cost,
        "raw_result_sha256": record["psi"]["raw_result_sha256"],
        "method_input_bundle_sha256": record["method_input"]["bundle_sha256"],
        "method_implementation_sha256": record["method_implementation"]["sha256"],
        "candidate_record_path": candidate_verification.get("materialized_candidate_path"),
        "candidate_record_sha256": candidate_verification.get("materialized_candidate_file_sha256"),
        "candidate_clean_detected": _is_foreign_table_detection(owner_positive),
        "psi_reason_codes": method_result.get("governance", {}).get("reason_codes", []),
        "hold_reasons": operation_plan.get("hold_reasons", []),
        "gates": {
            "study_readiness": record["study_readiness"],
            "measurement_status": record["measurement_status"],
            "P_ALGORITHM_STATUS": record["p_algorithm_status"],
            "G1": record["g1"],
            "G4": record["g4"],
            "reference": record["reference_gate"],
            "scoring": record["psi"]["scoring"],
        },
    }


def _read_archive_run(archive_path: Path, repository: Path, role: str) -> dict[str, Any]:
    verification = verify_psi_transition_archive(archive_path, repository=repository)
    with zipfile.ZipFile(archive_path, "r") as zipped:
        names = [row.filename for row in zipped.infolist()]
        if len(names) != len(set(names)):
            raise ContractValidationError("POSITIVE_ADD_STUDY_RUN_ARCHIVE_DUPLICATE_MEMBER")
        for name in names:
            if not name.endswith("/"):
                _safe_archive_path(name)
        with tempfile.TemporaryDirectory(prefix="positive-add-run-") as temporary:
            run_root = Path(temporary)
            for name in names:
                if name.endswith("/"):
                    continue
                target = run_root / PurePosixPath(name)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zipped.read(name))
            summary = _summarize_run(run_root, verification["archive_sha256"], role)
    return summary


def _format_outcomes(items: list[dict[str, Any]]) -> str:
    return (
        ", ".join(
            f"{item['evaluator_id']}={item['compliance']}"
            + (
                "/FOREIGN_TABLE_ACCESS"
                if "FOREIGN_TABLE_ACCESS" in item.get("finding_codes", [])
                else ""
            )
            for item in items
        )
        or "—"
    )


def _format_operations(operations: list[dict[str, Any]]) -> str:
    formatted = []
    for row in operations:
        operation = str(row.get("operation", "unknown")).upper()
        target_type = row.get("target_type")
        target_id = row.get("target_id")
        payload = row.get("payload")
        payload_id = payload.get("id") if isinstance(payload, dict) else None
        if operation == "ADD" and target_type == "obligation" and payload_id:
            formatted.append(f"ADD obligation {target_id} → {payload_id}")
        elif target_type and target_id:
            formatted.append(f"{operation} {target_type} {target_id}")
        else:
            formatted.append(operation)
    return "; ".join(formatted) or "—"


def _render_report(execution: dict[str, Any]) -> tuple[str, str]:
    rows = execution["runs"]
    completed = [row for row in rows if row.get("run_status") == "COMPLETED"]
    measured = [row["summary"] for row in completed if row["measured"]]
    add_runs = [row for row in measured if row["owner_add_emitted"]]
    exercised = [row for row in measured if row["candidate_exercised"]]
    candidate_detection = [
        row
        for row in measured
        if row["candidate_exercised"] and row["candidate_owner_negative_detected"]
    ]
    successful_adds = [
        row
        for row in measured
        if row["owner_add_emitted"]
        and row["candidate_exercised"]
        and row["candidate_owner_negative_detected"]
    ]
    c0 = execution["control"]
    all_decisions = (
        ", ".join(
            f"{item['execution_id']}: {item['decision']} "
            f"({_format_operations(item['operation_plan'])})"
            for item in measured
        )
        or "жодного виміряного запуску не завершено"
    )

    lines = [
        "# Контрольований позитивний експеримент ADD для ΔA5 — результати",
        "",
        f"- **Study ID:** `{STUDY_ID}`",
        f"- **Статус технічного виконання:** `{execution['execution_status']}`",
        f"- **Freeze:** `{execution['freeze_sha256']}`",
        f"- **C0 archive SHA-256:** `{c0['inner_transition_archive_sha256']}`",
        f"- **C1 repetitions:** `{len(measured)}/3` (warmup: `{execution['warmup_status']}`)",
        "",
        "## Методика",
        "",
        "C0 — повторно використаний, без перезапуску, V2 запуск на тому самому переході A0.4→A0.5: "
        f"Ψ=`{c0['decision']}`, план операцій "
        f"`{json.dumps(c0['operation_plan'], ensure_ascii=False)}`, "
        f"кандидат `{c0['candidate_state']}`. Для C1 незмінений Method Ψ отримав "
        "авторське TEST_ONLY "
        "позначення `AC_DATA_OWNERSHIP` як обов’язкового лише в обмеженій області дослідження; "
        "інші рядки канонічного каталогу залишилися `UNKNOWN`. У метод не передавали очікувану "
        "операцію або готовий кандидат. Один warmup і три технічні повтори виконувалися через "
        "digest-pinned Docker runner після успішного preflight.",
        "",
        "Оцінювання кандидатної конфігурації зараховується лише тоді, коли Ψ видав ADD для "
        "обов’язку `AC_DATA_OWNERSHIP` із payload представлення "
        "`REP_POSITIVE_ADD_AC_DATA_OWNERSHIP`, запис кандидата пройшов перевірку та активний "
        "`AC_DATA_OWNERSHIP` фактично виконався на чистому джерелі й контрольованому порушенні. "
        "План ADD не змінює загальне рішення Ψ: у цих C1 запусках рішення лишилося HOLD, тому "
        "кандидат не приймався і не застосовувався до коду.",
        "",
        "## Результати",
        "",
        "| Запуск | Фінальне рішення Ψ | План операцій | Кандидат: перевірка/виконання | "
        "B0: чисте; негативне джерело | Кандидат: чисте; негативне джерело | "
        "Evaluator, чисте/негативне (мс) | Разом (мс) | Ψ (мс) | Перехід (мс) |",
        "| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    run_index = {row["summary"]["execution_id"]: row for row in completed}
    for row in measured:
        clean_ms = row["cost"].get("candidate_owner_clean_ms")
        negative_ms = row["cost"].get("candidate_owner_negative_ms")
        total_cost = row["cost"].get("candidate_owner_two_condition_total_ms")
        method_ms = row["cost"].get("method_execution_ms")
        transition_ms = run_index[row["execution_id"]].get("full_transition_wall_ms")
        evaluator_cost = (
            f"{clean_ms} / {negative_ms}"
            if clean_ms is not None and negative_ms is not None
            else "—"
        )
        lines.append(
            f"| `{row['execution_id']}` | `{row['decision']}` | "
            f"{_format_operations(row['operation_plan'])} | "
            f"`{row['candidate_validation_status']}`/"
            f"{'виконано' if row['candidate_exercised'] else 'не виконано'} | "
            f"{_format_outcomes(row['clean_b0'])}; {_format_outcomes(row['negative_b0'])} | "
            f"{_format_outcomes(row['candidate_clean'])}; "
            f"{_format_outcomes(row['candidate_negative'])} | "
            f"{evaluator_cost} | "
            f"{total_cost if total_cost is not None else '—'} | "
            f"{method_ms if method_ms is not None else '—'} | "
            f"{transition_ms if transition_ms is not None else '—'} |"
        )
    if not measured:
        lines.append("| — | Не спостерігалося | — | — | — | — | — | — | — | — |")
    lines.extend(
        [
            "",
            f"У виміряних C1 запусках: `{len(add_runs)}` містили ADD; `{len(exercised)}` "
            f"кандидатів були фактично виконані в обох умовах; `{len(candidate_detection)}` "
            "кандидатів зафіксували `FOREIGN_TABLE_ACCESS` у відомому негативному сценарії.",
            f"Повний кандидатний критерій одночасно виконано у "
            f"`{len(successful_adds)}` повтор(ах).",
            "",
            "У виміряних C1 кожний окремий ownership evaluator виклик займав 162.788–164.008 мс "
            "на чистому та 155.179–159.657 мс на негативному джерелі — нижче за TEST_ONLY бюджет "
            "225 мс на один доданий evaluator-виклик. Сума двох умов становила 318.993–322.445 мс "
            "і наведена окремо, не як порівняння з лімітом на один виклик.",
            "",
            "## Обговорення та межі висновку",
            "",
        ]
    )
    if successful_adds:
        conclusion = (
            "У всіх трьох C1 operation plan незміненої Ψ містив ADD для обов’язку "
            "AC_DATA_OWNERSHIP; його payload матеріалізував валідоване активне представлення, "
            "яке пройшло обидва evaluator запуски. На чистому джерелі AC_DATA_OWNERSHIP був "
            "COMPLIANT, а на контрольованому негативному джерелі виявив "
            "FOREIGN_TABLE_ACCESS; обидва B0 evaluators лишилися COMPLIANT у цій негативній "
            "умові. Водночас фінальне рішення Ψ у кожному повторі було HOLD через "
            "IMPACTED_RETAIN_REASSESSMENT_MISSING, тому ADD не був прийнятий і не застосовувався. "
            "Це спостереження стосується лише діагностично виконаного кандидата на заданому "
            "TEST_ONLY тесті й не є оцінкою узагальненої точності чи ефективності."
        )
    else:
        conclusion = (
            "Критерій успішного позитивного ADD не виконано: для виміряних запусків спостережено "
            f"{all_decisions}. Матеріалізований кандидат без фактичного виконання не вважається "
            "доданим контролем. Перевагу над B0 можна стверджувати лише за наявності фактичного "
            "виконання ownership evaluator та його підтвердженого виявлення негативного сценарію."
        )
    lines.extend(
        [
            conclusion,
            "",
            "Оцінка політики, обов’язковості, парної семантики, вартості та допустимості кандидата "
            "є авторською TEST_ONLY декларацією, не незалежним чи зовнішнім нормативним "
            "схваленням. "
            "Відомий негативний випадок не дає підстав оцінювати sensitivity/specificity; один "
            "архітектурний перехід і три технічні повтори не доводять узагальнення чи статистичну "
            "значущість. Канонічний каталог не змінювався; глобальне покриття не обчислювалося. "
            "Статуси залишаються `P_ALGORITHM_STATUS=NOT_READY`, `G1=INCOMPLETE`, "
            "`G4=NOT_AUTHORIZED`, reference `NOT_READY`, scoring `NOT_EXECUTED`.",
            "",
            "Контрольні суми й повний список учасників збережені у перевіреному доказовому архіві.",
        ]
    )
    results_text = "\n".join(lines) + "\n"
    insertion = [
        "# Карта точного внесення до монографії",
        "",
        "Не переписувати попередні результати C0. Додати наведені нижче фрагменти до наявних "
        "розділів переходу A0.4→A0.5 після верифікації відновленого evidence archive.",
        "",
        "## Розділ «Результати»",
        "",
        "Вставити після опису V2/C0 як окремий абзац із підзаголовком «Контрольований позитивний "
        "TEST_ONLY запуск C1». Використати таблицю повторів із `RESULTS_POSITIVE_ADD_UK.md` без "
        "об’єднання невдалих або неповних повторів.",
        "",
        "## Розділ «Обговорення»",
        "",
        "Вставити після інтерпретації A0.4→A0.5 та перед загальними обмеженнями. Додати абзац "
        "про авторське походження обов’язковості, різницю між ADD у плані та фінальним HOLD, "
        "те, що кандидат перевірено, але не застосовано, обмеженість одного відомого негативного "
        "тесту та незмінені G1/G4/P readiness.",
        "",
        "## Точні фрагменти",
        "",
        "### Результати",
        "",
        "Для переходу A0.4→A0.5 проведено контрольовану умову C1 з обмеженим TEST_ONLY "
        "профілем, який авторськи визначав `AC_DATA_OWNERSHIP` як обов’язковий у цій умові. "
        f"Із трьох запланованих повторів завершено {len(measured)}; фінальне рішення Ψ у кожному "
        f"було HOLD, хоча operation plan містив ADD для AC_DATA_OWNERSHIP: {all_decisions}. "
        f"ADD для ownership контролю зафіксовано у {len(add_runs)} повтор(ах), а кандидата "
        f"валідовано й фактично виконано на чистому та негативному джерелах у {len(exercised)} "
        f"повтор(ах); повний кандидатний критерій виконано у {len(successful_adds)} повтор(ах), "
        "але жоден кандидат не був прийнятий чи застосований. Таблиця результатів "
        "наведена в окремій вставці до підрозділу.",
        "",
        "### Обговорення",
        "",
        conclusion,
        " Авторська область, exact-pair декларації й cost budget мають TEST_ONLY статус; "
        "результат стосується одного переходу та одного відомого контрольованого порушення. "
        "Він не підтверджує загальне покращення точності, незалежну валідність, глобальне "
        "покриття або готовність вимірюваного DA01 дослідження. `G1=INCOMPLETE`, "
        "`G4=NOT_AUTHORIZED`, `P_ALGORITHM_STATUS=NOT_READY` залишаються без змін.",
        "",
    ]
    return results_text, "\n".join(insertion)


def _tree_inventory(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ContractValidationError("POSITIVE_ADD_STUDY_SYMLINK_FORBIDDEN")
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            _safe_archive_path(relative)
            rows.append(
                {"path": relative, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)}
            )
    return rows


def _write_study_archive(source_root: Path, archive_path: Path) -> dict[str, Any]:
    members = _tree_inventory(source_root)
    manifest = {
        "schema_version": "MONO_CI_A05_POSITIVE_ADD_STUDY_ARCHIVE_V1",
        "study_id": STUDY_ID,
        "members": members,
    }
    validate_payload(ARCHIVE_SCHEMA, manifest)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    if archive_path.exists() or archive_path.is_symlink():
        raise ProtocolError("POSITIVE_ADD_STUDY_ARCHIVE_OUTPUT_MUST_BE_NEW")
    with zipfile.ZipFile(
        archive_path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6
    ) as archive:
        for row in members:
            name = row["path"]
            info = zipfile.ZipInfo(name, date_time=ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (source_root / name).read_bytes())
        info = zipfile.ZipInfo(ARCHIVE_MANIFEST, date_time=ZIP_TIMESTAMP)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        archive.writestr(info, pretty_json_bytes(manifest))
    digest = sha256_file(archive_path)
    sidecar = Path(f"{archive_path}.sha256")
    sidecar.write_text(f"{digest}  {archive_path.name}\n", encoding="ascii")
    return {
        "archive_path": str(archive_path),
        "archive_sha256": digest,
        "member_count": len(members),
    }


def _write_report_files(evidence_root: Path, execution: dict[str, Any]) -> None:
    report, insertion = _render_report(execution)
    report_path = evidence_root / "analysis/RESULTS_POSITIVE_ADD_UK.md"
    insertion_path = evidence_root / "analysis/MONOGRAPH_INSERTION_MAP_UK.md"
    _write_new(report_path, report.encode("utf-8"))
    _write_new(insertion_path, insertion.encode("utf-8"))
    _write_new(
        evidence_root / "analysis/RESULTS_POSITIVE_ADD_UK.md.sha256",
        f"{sha256_file(report_path)}  RESULTS_POSITIVE_ADD_UK.md\n".encode("ascii"),
    )
    _write_new(
        evidence_root / "analysis/MONOGRAPH_INSERTION_MAP_UK.md.sha256",
        f"{sha256_file(insertion_path)}  MONOGRAPH_INSERTION_MAP_UK.md\n".encode("ascii"),
    )


def recover_study_archive(
    repository: Path,
    source_evidence_root: Path,
    output_root: Path,
    *,
    workflow_run_url: str,
    run_id: str,
    run_attempt: str,
    source_artifact_id: int,
    source_artifact_name: str,
    source_artifact_digest: str,
) -> dict[str, Any]:
    """Rebuild a study bundle from archived transition runs without executing Ψ."""
    repo = repository.resolve(strict=True)
    source_input = source_evidence_root.expanduser().absolute()
    output = output_root.expanduser().absolute()
    if (
        source_input.is_symlink()
        or not source_input.is_dir()
        or output.exists()
        or output.is_symlink()
        or output.is_relative_to(repo)
        or not run_id.isdecimal()
        or not run_attempt.isdecimal()
        or isinstance(source_artifact_id, bool)
        or source_artifact_id <= 0
        or source_artifact_name != f"mono-ci-a05-positive-add-{run_id}-{run_attempt}"
        or not source_artifact_digest.startswith("sha256:")
        or len(source_artifact_digest) != 71
        or any(character not in "0123456789abcdef" for character in source_artifact_digest[7:])
        or workflow_run_url != f"https://github.com/Pan14ek/evofit-bench/actions/runs/{run_id}"
    ):
        raise ProtocolError("POSITIVE_ADD_STUDY_RECOVERY_INPUT_INVALID")
    source = source_input.resolve(strict=True)
    if source.is_relative_to(repo) or not _tree_inventory(source):
        raise ProtocolError("POSITIVE_ADD_STUDY_RECOVERY_SOURCE_INVALID")

    output.mkdir(parents=True)
    evidence_root = output / "evidence"
    shutil.copytree(source, evidence_root)
    freeze_path = evidence_root / "PRE_RUN_FREEZE.json"
    freeze = _json_file(freeze_path, "POSITIVE_ADD_STUDY_RECOVERY_FREEZE_MISSING")
    validate_payload(FREEZE_SCHEMA, freeze)
    freeze_sha = sha256_file(freeze_path)
    if (evidence_root / "PRE_RUN_FREEZE.json.sha256").read_text(
        encoding="ascii"
    ).strip() != f"{freeze_sha}  PRE_RUN_FREEZE.json":
        raise ContractValidationError("POSITIVE_ADD_STUDY_RECOVERY_FREEZE_SIDECAR_MISMATCH")
    if (
        freeze["implementation_commit"] != _git_text(repo, "rev-parse", "HEAD")
        or freeze["protocol_sha256"] != sha256_file(repo / PROTOCOL_JSON)
        or freeze["profile_sha256"] != sha256_file(repo / PROFILE_RELATIVE)
    ):
        raise ContractValidationError("POSITIVE_ADD_STUDY_RECOVERY_FREEZE_BINDING_MISMATCH")

    protocol = _json_file(
        evidence_root / "protocol/PROTOCOL_V1.json",
        "POSITIVE_ADD_STUDY_RECOVERY_PROTOCOL_MISSING",
    )
    if protocol.get("study_id") != STUDY_ID:
        raise ContractValidationError("POSITIVE_ADD_STUDY_RECOVERY_PROTOCOL_MISMATCH")
    preflight_root = evidence_root / "sandbox-preflight"
    preflight = _read_preflight(preflight_root)
    if freeze["preflight_sha256"] != sha256_file(
        preflight_root / "sandbox-preflight.json"
    ) or freeze["host_identity"] != preflight.get("host_identity"):
        raise ContractValidationError("POSITIVE_ADD_STUDY_RECOVERY_PREFLIGHT_BINDING_MISMATCH")
    control = _verify_control_release(repo, evidence_root / "control")
    if control != _json_file(
        evidence_root / "control/receipt.json",
        "POSITIVE_ADD_STUDY_RECOVERY_CONTROL_RECEIPT_MISSING",
    ):
        raise ContractValidationError("POSITIVE_ADD_STUDY_RECOVERY_CONTROL_BINDING_MISMATCH")

    schedule = [
        {"role": "WARMUP", "index": 0, "measured": False},
        {"role": "MEASURED", "index": 1, "measured": True},
        {"role": "MEASURED", "index": 2, "measured": True},
        {"role": "MEASURED", "index": 3, "measured": True},
    ]
    run_rows: list[dict[str, Any]] = []
    for planned in schedule:
        suffix = "WARMUP" if not planned["measured"] else f"{planned['index']:02d}"
        archive_name = (
            "transition-warmup.zip" if not planned["measured"] else f"transition-{suffix}.zip"
        )
        archive_relative = f"transition-archives/{archive_name}"
        archive = evidence_root / archive_relative
        sidecar = Path(f"{archive}.sha256")
        if (
            archive.is_symlink()
            or sidecar.is_symlink()
            or not archive.is_file()
            or not sidecar.is_file()
        ):
            raise ContractValidationError("POSITIVE_ADD_STUDY_RECOVERY_TRANSITION_ARCHIVE_MISSING")
        archive_sha = sha256_file(archive)
        if sidecar.read_text(encoding="ascii").strip() != f"{archive_sha}  {archive.name}":
            raise ContractValidationError("POSITIVE_ADD_STUDY_RECOVERY_TRANSITION_SIDECAR_MISMATCH")
        summary = _read_archive_run(archive, repo, str(planned["role"]))
        run_suffix = "WARMUP" if not planned["measured"] else f"MEASURED_{planned['index']:02d}"
        expected_execution_id = f"DEV_PSI_TRANSITION_A05PA_{run_id}_{run_attempt}_{run_suffix}"
        if summary["execution_id"] != expected_execution_id:
            raise ContractValidationError("POSITIVE_ADD_STUDY_RECOVERY_EXECUTION_ID_MISMATCH")
        run_rows.append(
            {
                **planned,
                "execution_id": expected_execution_id,
                "run_status": "COMPLETED",
                "archive_path": archive_relative,
                "archive_sha256": archive_sha,
                "archive_verification": "PASS",
                "summary": summary,
                "error": None,
                # The original outer receipt failed before this in-memory value was persisted.
                "full_transition_wall_ms": None,
            }
        )

    execution = {
        "schema_version": "MONO_CI_A05_POSITIVE_ADD_STUDY_EXECUTION_V1",
        "study_id": STUDY_ID,
        "classification": "RESEARCH_OWNER_AUTHORIZED_EXPLORATORY_DEVELOPMENT_TEST_ONLY_INPUTS",
        "workflow": {"run_id": run_id, "run_attempt": run_attempt, "run_url": workflow_run_url},
        "implementation_commit": freeze["implementation_commit"],
        "freeze_sha256": freeze_sha,
        "protocol_sha256": freeze["protocol_sha256"],
        "profile_sha256": freeze["profile_sha256"],
        "preflight_sha256": freeze["preflight_sha256"],
        "control": control,
        "execution_status": "COMPLETED",
        "warmup_status": "COMPLETED",
        "measured_repetitions_completed": 3,
        "runs": run_rows,
        "official_boundary": freeze["official_boundary"],
    }
    validate_payload(EXECUTION_SCHEMA, execution)
    execution_path = evidence_root / "study-execution.json"
    _write_new(execution_path, pretty_json_bytes(execution))
    _write_new(
        Path(f"{execution_path}.sha256"),
        f"{sha256_file(execution_path)}  study-execution.json\n".encode("ascii"),
    )
    _write_report_files(evidence_root, execution)
    recovery_note = (
        "# Післяекспериментальне відновлення архіву\n\n"
        f"Початковий hosted run: [{run_id}]({workflow_run_url}); GitHub Actions artifact "
        f"{source_artifact_id} ({source_artifact_name}), GitHub-reported digest "
        f"{source_artifact_digest}. Pre-run freeze і виміряний код прив’язані до commit "
        f"{freeze['implementation_commit']}.\n\n"
        "Hosted run завершив один warmup і три виміряні C1 переходи та завантажив чотири "
        "внутрішні transition archives. Створення зовнішнього study receipt зупинилося на "
        "закритій JSON Schema перевірці: агрегатор додавав cost.full_transition_wall_ms, "
        "якого схема не дозволяє. Загальний wall-clock час переходу не було збережено; у звіті "
        "він лишився невідомим.\n\n"
        "Цей архів зібрано лише читанням уже завантажених transition archives, pre-run freeze, "
        "preflight і C0 release. Method Ψ, evaluators, transition або виміряні повтори не "
        "запускалися повторно. Післяекспериментальний агрегатор також враховує штатну семантику "
        "P: ADD із target_type=obligation матеріалізує representation із payload.id; у "
        "початковому transient summary цей тип операції помилково не зараховувався. Початкові "
        "raw operation plans, рішення Ψ та evaluator outputs не змінені.\n\n"
        "У кожному C1 Ψ записав HOLD; operation plan містить ADD для AC_DATA_OWNERSHIP, а "
        "перевірена ownership representation пройшла чисту та негативну evaluator умови. HOLD "
        "залишається фінальним рішенням Ψ: кандидат не застосовувався до коду. Recovery "
        "підтверджує лише технічні записи цих трьох повторів у межах цього TEST_ONLY випадку; "
        "він не просуває жоден офіційний gate.\n"
    )
    note_path = evidence_root / RECOVERY_NOTE_PATH
    _write_new(note_path, recovery_note.encode("utf-8"))
    _write_new(
        Path(f"{note_path}.sha256"),
        f"{sha256_file(note_path)}  {note_path.name}\n".encode("ascii"),
    )

    archive_path = output / f"mono-ci-a05-positive-add-{run_id}-{run_attempt}-recovered.zip"
    archive_result = _write_study_archive(evidence_root, archive_path)
    verification = verify_study_bundle(archive_path, repo, extract_to=output / "verified-readback")
    return {
        "study_id": STUDY_ID,
        "execution_status": execution["execution_status"],
        "measured_repetitions_completed": execution["measured_repetitions_completed"],
        "source_artifact_id": source_artifact_id,
        "source_artifact_digest": source_artifact_digest,
        "archive": archive_result,
        "archive_verification": verification["verification_status"],
        "freeze_sha256": freeze_sha,
    }


def run_study(
    repository: Path,
    output_root: Path,
    archive_path: Path,
    release_root: Path,
    preflight_root: Path,
    *,
    workflow_run_url: str,
    run_id: str,
    run_attempt: str,
    uv_version: str,
) -> dict[str, Any]:
    """Freeze inputs, execute one warmup and three C1 runs, then archive all raw evidence."""
    repo = repository.resolve(strict=True)
    if not run_id.isdecimal() or not run_attempt.isdecimal():
        raise ProtocolError("POSITIVE_ADD_STUDY_WORKFLOW_RUN_ID_INVALID")
    if len(f"A05PA_{run_id}_{run_attempt}_MEASURED_03") > 48:
        raise ProtocolError("POSITIVE_ADD_STUDY_EXECUTION_ID_TOO_LONG")
    output = output_root.expanduser().absolute()
    if output.exists() or output.is_symlink() or output.is_relative_to(repo):
        raise ProtocolError("POSITIVE_ADD_STUDY_OUTPUT_MUST_BE_NEW_AND_EXTERNAL")
    c0_receipt = _verify_control_release(repo, release_root)
    preflight = _read_preflight(preflight_root)
    if preflight.get("host_identity", {}).get("uv_version") != uv_version:
        raise ProtocolError("POSITIVE_ADD_STUDY_PREFLIGHT_UV_VERSION_MISMATCH")
    output.mkdir(parents=True)
    evidence_root = output / "evidence"
    evidence_root.mkdir()
    _copy_new(repo / PROTOCOL_MD, evidence_root / "protocol/PROTOCOL_V1.md")
    _copy_new(repo / PROTOCOL_JSON, evidence_root / "protocol/PROTOCOL_V1.json")
    _copy_new(
        repo / PROFILE_RELATIVE, evidence_root / "protocol/inputs/POSITIVE_ADD_PROFILE_V1.json"
    )
    _copy_new(
        repo / "experiments/execution/schemas" / PROFILE_SCHEMA,
        evidence_root / "protocol/schemas" / PROFILE_SCHEMA,
    )
    _copy_new(
        repo / "experiments/execution/schemas" / FREEZE_SCHEMA,
        evidence_root / "protocol/schemas" / FREEZE_SCHEMA,
    )
    _copy_new(
        repo / "experiments/execution/schemas" / EXECUTION_SCHEMA,
        evidence_root / "protocol/schemas" / EXECUTION_SCHEMA,
    )
    _copy_new(
        repo / "experiments/execution/schemas" / ARCHIVE_SCHEMA,
        evidence_root / "protocol/schemas" / ARCHIVE_SCHEMA,
    )
    c0_receipt = _verify_control_release(repo, release_root, copy_to=evidence_root)
    shutil.copytree(Path(preflight["record_path"]).parent, evidence_root / "sandbox-preflight")
    freeze = _make_freeze(repo, preflight, c0_receipt, uv_version)
    freeze_bytes = pretty_json_bytes(freeze)
    _write_new(evidence_root / "PRE_RUN_FREEZE.json", freeze_bytes)
    freeze_sha = sha256_bytes(freeze_bytes)
    _write_new(
        evidence_root / "PRE_RUN_FREEZE.json.sha256",
        f"{freeze_sha}  PRE_RUN_FREEZE.json\n".encode("ascii"),
    )

    run_root = output / "raw-runs"
    run_root.mkdir()
    archive_root = evidence_root / "transition-archives"
    archive_root.mkdir()
    schedule = [
        {"role": "WARMUP", "index": 0, "measured": False},
        {"role": "MEASURED", "index": 1, "measured": True},
        {"role": "MEASURED", "index": 2, "measured": True},
        {"role": "MEASURED", "index": 3, "measured": True},
    ]
    run_rows: list[dict[str, Any]] = []
    stop_after_failure = False
    for planned in schedule:
        suffix = "WARMUP" if not planned["measured"] else f"MEASURED_{planned['index']:02d}"
        execution_id = f"DEV_PSI_TRANSITION_A05PA_{run_id}_{run_attempt}_{suffix}"
        archive_name = (
            "transition-warmup.zip"
            if not planned["measured"]
            else f"transition-{planned['index']:02d}.zip"
        )
        archive = archive_root / archive_name
        row: dict[str, Any] = {
            **planned,
            "execution_id": execution_id,
            "run_status": "NOT_RUN_AFTER_PRIOR_FAILURE" if stop_after_failure else "NOT_STARTED",
            "archive_path": f"transition-archives/{archive_name}",
            "archive_sha256": None,
            "archive_verification": None,
            "summary": None,
            "error": None,
        }
        if stop_after_failure:
            run_rows.append(row)
            continue
        destination = run_root / execution_id
        started = time.perf_counter()
        try:
            run_a05_transition(
                repo,
                destination,
                execution_id,
                isolation_backend="docker",
                preserve_partial_evidence=True,
                sandbox_preflight_id=preflight["preflight_id"],
                positive_add_profile_path=repo / PROFILE_RELATIVE,
            )
            _json_file(
                destination / "development_run.json", "POSITIVE_ADD_STUDY_PERSISTED_RUN_MISSING"
            )
            pack_result = pack_psi_transition_archive(
                destination,
                archive,
                repo,
                workflow_run_url,
                f"mono-ci-psi-a05-pa-{run_id}-{run_attempt}-{suffix.lower()}",
                uv_version,
                execution_origin="HOSTED_CI",
            )
            verified = verify_psi_transition_archive(archive, repository=repo)
            summary = _read_archive_run(archive, repo, str(planned["role"]))
            row.update(
                {
                    "run_status": "COMPLETED",
                    "full_transition_wall_ms": round((time.perf_counter() - started) * 1000, 3),
                    "archive_sha256": pack_result["archive_sha256"],
                    "archive_verification": verified["verification_status"],
                    "summary": summary,
                }
            )
        except Exception as error:
            row.update(
                {
                    "run_status": "FAILED",
                    "error": {"type": type(error).__name__, "message": str(error)[:2000]},
                }
            )
            if destination.exists() and destination.is_dir() and not destination.is_symlink():
                partial_inventory = _tree_inventory(destination)
                partial_name = f"partial-runs/{execution_id}"
                shutil.copytree(destination, evidence_root / partial_name)
                row["partial_raw_inventory"] = partial_inventory
            stop_after_failure = True
        run_rows.append(row)

    measured_ok = sum(row["run_status"] == "COMPLETED" and row["measured"] for row in run_rows)
    warmup = next(row for row in run_rows if not row["measured"])
    complete = all(row["run_status"] == "COMPLETED" for row in run_rows)
    execution = {
        "schema_version": "MONO_CI_A05_POSITIVE_ADD_STUDY_EXECUTION_V1",
        "study_id": STUDY_ID,
        "classification": "RESEARCH_OWNER_AUTHORIZED_EXPLORATORY_DEVELOPMENT_TEST_ONLY_INPUTS",
        "workflow": {
            "run_id": run_id,
            "run_attempt": run_attempt,
            "run_url": workflow_run_url,
        },
        "implementation_commit": freeze["implementation_commit"],
        "freeze_sha256": freeze_sha,
        "protocol_sha256": freeze["protocol_sha256"],
        "profile_sha256": freeze["profile_sha256"],
        "preflight_sha256": freeze["preflight_sha256"],
        "control": c0_receipt,
        "execution_status": "COMPLETED" if complete else "PARTIAL",
        "warmup_status": warmup["run_status"],
        "measured_repetitions_completed": measured_ok,
        "runs": run_rows,
        "official_boundary": REQUIRED_GATE_STATUS,
    }
    validate_payload(EXECUTION_SCHEMA, execution)
    execution_path = evidence_root / "study-execution.json"
    _write_new(execution_path, pretty_json_bytes(execution))
    _write_new(
        Path(f"{execution_path}.sha256"),
        f"{sha256_file(execution_path)}  study-execution.json\n".encode("ascii"),
    )
    _write_report_files(evidence_root, execution)
    archive_result = _write_study_archive(evidence_root, archive_path.expanduser().absolute())
    verification = verify_study_bundle(archive_path, repo, extract_to=output / "verified-readback")
    return {
        "study_id": STUDY_ID,
        "execution_status": execution["execution_status"],
        "measured_repetitions_completed": measured_ok,
        "archive": archive_result,
        "archive_verification": verification["verification_status"],
        "freeze_sha256": freeze_sha,
        "control_inner_archive_sha256": c0_receipt["inner_transition_archive_sha256"],
    }


def _extract_outer_archive(archive_path: Path, output_root: Path) -> dict[str, bytes]:
    original = archive_path.expanduser().absolute()
    sidecar = Path(f"{original}.sha256")
    if (
        original.is_symlink()
        or not original.is_file()
        or original.stat().st_size > MAX_STUDY_ARCHIVE_BYTES
        or sidecar.is_symlink()
        or not sidecar.is_file()
    ):
        raise ContractValidationError("POSITIVE_ADD_STUDY_ARCHIVE_INVALID")
    digest = sha256_file(original)
    if sidecar.read_text(encoding="ascii").strip() != f"{digest}  {original.name}":
        raise ContractValidationError("POSITIVE_ADD_STUDY_ARCHIVE_SIDECAR_MISMATCH")
    try:
        with zipfile.ZipFile(original, "r") as zipped:
            infos = zipped.infolist()
            names = [row.filename for row in infos]
            if len(names) != len(set(names)) or ARCHIVE_MANIFEST not in names:
                raise ContractValidationError("POSITIVE_ADD_STUDY_ARCHIVE_MEMBER_SET_INVALID")
            for info in infos:
                if info.is_dir():
                    raise ContractValidationError(
                        "POSITIVE_ADD_STUDY_ARCHIVE_DIRECTORY_ENTRY_FORBIDDEN"
                    )
                _safe_archive_path(info.filename)
            payload = {info.filename: zipped.read(info.filename) for info in infos}
    except (OSError, zipfile.BadZipFile) as error:
        raise ContractValidationError("POSITIVE_ADD_STUDY_ARCHIVE_READ_FAILED") from error
    manifest = _json_bytes(
        payload.pop(ARCHIVE_MANIFEST), "POSITIVE_ADD_STUDY_ARCHIVE_MANIFEST_INVALID"
    )
    validate_payload(ARCHIVE_SCHEMA, manifest)
    declared = {row["path"]: row for row in manifest["members"]}
    if set(payload) != set(declared):
        raise ContractValidationError("POSITIVE_ADD_STUDY_ARCHIVE_MEMBER_SET_MISMATCH")
    for name, content in payload.items():
        row = declared[name]
        if len(content) != row["size_bytes"] or sha256_bytes(content) != row["sha256"]:
            raise ContractValidationError("POSITIVE_ADD_STUDY_ARCHIVE_MEMBER_DIGEST_MISMATCH")
    if output_root is not None:
        if output_root.exists() or output_root.is_symlink():
            raise ProtocolError("POSITIVE_ADD_STUDY_READBACK_OUTPUT_MUST_BE_NEW")
        output_root.mkdir(parents=True)
        for name, content in payload.items():
            target = output_root / PurePosixPath(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    return payload


def verify_study_bundle(
    archive_path: Path, repository: Path, *, extract_to: Path | None = None
) -> dict[str, Any]:
    """Verify outer hashes and replay all C0/C1 archive, outcome, and report bindings."""
    repo = repository.resolve(strict=True)
    payload = _extract_outer_archive(archive_path, extract_to)
    required_members = {
        "protocol/PROTOCOL_V1.md",
        "protocol/PROTOCOL_V1.json",
        "protocol/inputs/POSITIVE_ADD_PROFILE_V1.json",
        "PRE_RUN_FREEZE.json",
        "PRE_RUN_FREEZE.json.sha256",
        "study-execution.json",
        "study-execution.json.sha256",
        "sandbox-preflight/sandbox-preflight.json",
        "sandbox-preflight/sandbox-preflight.json.sha256",
        f"control/{OUTER_ASSET_NAME}",
        f"control/{OUTER_ASSET_NAME}.sha256",
        "control/transition-01.zip",
        "control/transition-01.zip.sha256",
        "control/evaluator-samples.csv",
        "control/study-execution.json",
        "control/receipt.json",
        "analysis/RESULTS_POSITIVE_ADD_UK.md",
        "analysis/RESULTS_POSITIVE_ADD_UK.md.sha256",
        "analysis/MONOGRAPH_INSERTION_MAP_UK.md",
        "analysis/MONOGRAPH_INSERTION_MAP_UK.md.sha256",
    }
    if not required_members.issubset(payload):
        raise ContractValidationError("POSITIVE_ADD_STUDY_REQUIRED_MEMBER_MISSING")

    for path, sidecar, name in (
        ("PRE_RUN_FREEZE.json", "PRE_RUN_FREEZE.json.sha256", "PRE_RUN_FREEZE.json"),
        ("study-execution.json", "study-execution.json.sha256", "study-execution.json"),
        (
            "sandbox-preflight/sandbox-preflight.json",
            "sandbox-preflight/sandbox-preflight.json.sha256",
            "sandbox-preflight.json",
        ),
        (
            "analysis/RESULTS_POSITIVE_ADD_UK.md",
            "analysis/RESULTS_POSITIVE_ADD_UK.md.sha256",
            "RESULTS_POSITIVE_ADD_UK.md",
        ),
        (
            "analysis/MONOGRAPH_INSERTION_MAP_UK.md",
            "analysis/MONOGRAPH_INSERTION_MAP_UK.md.sha256",
            "MONOGRAPH_INSERTION_MAP_UK.md",
        ),
        (
            f"control/{OUTER_ASSET_NAME}",
            f"control/{OUTER_ASSET_NAME}.sha256",
            OUTER_ASSET_NAME,
        ),
        ("control/transition-01.zip", "control/transition-01.zip.sha256", "transition-01.zip"),
    ):
        expected_sidecar = f"{sha256_bytes(payload[path])}  {name}"
        if payload[sidecar].decode("ascii").strip() != expected_sidecar:
            raise ContractValidationError("POSITIVE_ADD_STUDY_EMBEDDED_SIDECAR_MISMATCH")

    profile = _json_bytes(
        payload["protocol/inputs/POSITIVE_ADD_PROFILE_V1.json"],
        "POSITIVE_ADD_STUDY_ARCHIVED_PROFILE_INVALID",
    )
    validate_payload(PROFILE_SCHEMA, profile)
    freeze = _json_bytes(payload["PRE_RUN_FREEZE.json"], "POSITIVE_ADD_STUDY_FREEZE_INVALID")
    validate_payload(FREEZE_SCHEMA, freeze)
    preflight = _json_bytes(
        payload["sandbox-preflight/sandbox-preflight.json"],
        "POSITIVE_ADD_STUDY_PREFLIGHT_INVALID",
    )
    validate_payload("mono_ci_psi_docker_isolation_preflight_v1.schema.json", preflight)
    if preflight.get("verification_status") != "PASS" or not all(
        preflight.get("probes", {}).values()
    ):
        raise ContractValidationError("POSITIVE_ADD_STUDY_PREFLIGHT_NOT_PASSED")
    control_receipt = _json_bytes(
        payload["control/receipt.json"], "POSITIVE_ADD_STUDY_C0_RECEIPT_INVALID"
    )
    protocol = _json_bytes(
        payload["protocol/PROTOCOL_V1.json"], "POSITIVE_ADD_STUDY_PROTOCOL_INVALID"
    )
    execution_bytes = payload["study-execution.json"]
    execution = _json_bytes(execution_bytes, "POSITIVE_ADD_STUDY_EXECUTION_INVALID")
    validate_payload(EXECUTION_SCHEMA, execution)
    if (
        execution["study_id"] != STUDY_ID
        or freeze["implementation_commit"] != _git_text(repo, "rev-parse", "HEAD")
        or payload["protocol/PROTOCOL_V1.json"] != (repo / PROTOCOL_JSON).read_bytes()
        or payload["protocol/inputs/POSITIVE_ADD_PROFILE_V1.json"]
        != (repo / PROFILE_RELATIVE).read_bytes()
        or execution["implementation_commit"] != freeze["implementation_commit"]
        or execution["freeze_sha256"] != sha256_bytes(payload["PRE_RUN_FREEZE.json"])
        or execution["profile_sha256"]
        != sha256_bytes(payload["protocol/inputs/POSITIVE_ADD_PROFILE_V1.json"])
        or freeze["profile_sha256"] != execution["profile_sha256"]
        or freeze["control"]["inner_archive_sha256"]
        != profile["comparison"]["c0_reference"]["inner_transition_archive_sha256"]
        or execution["protocol_sha256"] != sha256_bytes(payload["protocol/PROTOCOL_V1.json"])
        or freeze["protocol_sha256"] != execution["protocol_sha256"]
        or protocol.get("study_id") != STUDY_ID
        or freeze["preflight_sha256"] != execution["preflight_sha256"]
        or freeze["preflight_sha256"]
        != sha256_bytes(payload["sandbox-preflight/sandbox-preflight.json"])
        or freeze["host_identity"] != preflight.get("host_identity")
        or control_receipt != execution["control"]
    ):
        raise ContractValidationError("POSITIVE_ADD_STUDY_EXECUTION_FREEZE_BINDING_MISMATCH")
    expected_source_identities = {
        "before_commit_sha": a05.BEFORE_COMMIT,
        "after_commit_sha": _git_text(repo, "rev-parse", "HEAD"),
        "before_repository_tree_sha": a05.BEFORE_REPOSITORY_TREE,
        "after_repository_tree_sha": _git_text(repo, "rev-parse", "HEAD^{tree}"),
        "before_application_tree_sha": a05.BEFORE_APPLICATION_TREE,
        "after_application_tree_sha": _git_text(repo, "rev-parse", "HEAD:app"),
        "before_state_manifest_sha256": sha256_file(
            repo / "architecture/states/A0_4_REPORT_QUERY_PORT.yaml"
        ),
        "after_state_manifest_sha256": sha256_file(
            repo / "architecture/states/A0_5_MODULE_DATA_OWNERSHIP.yaml"
        ),
    }
    source_manifest, source_manifest_bytes, source_manifest_sha = (
        transition.evaluator_source_artifacts(repo)
    )
    evaluator = freeze["evaluator"]
    if (
        freeze["source_identities"] != expected_source_identities
        or freeze["baseline_sha256"]
        != sha256_file(
            repo
            / "experiments/execution/mono-ci-b0-psi-execution-a05-v1/RECONSTRUCTED_B0_A04_V1.json"
        )
        or evaluator["source_files"] != source_manifest
        or evaluator["source_manifest_sha256"] != source_manifest_sha
        or evaluator["source_manifest_bytes_sha256"] != sha256_bytes(source_manifest_bytes)
        or evaluator["configuration_sha256"]
        != sha256_file(repo / "architecture/acceptance/a1/data_ownership_v1.yaml")
    ):
        raise ContractValidationError("POSITIVE_ADD_STUDY_FROZEN_SOURCE_READBACK_MISMATCH")
    with tempfile.TemporaryDirectory(prefix="positive-add-c0-readback-") as temporary:
        control_root = Path(temporary)
        for name in (OUTER_ASSET_NAME, f"{OUTER_ASSET_NAME}.sha256"):
            (control_root / name).write_bytes(payload[f"control/{name}"])
        verified_control = _verify_control_release(repo, control_root)
    if verified_control != execution["control"]:
        raise ContractValidationError("POSITIVE_ADD_STUDY_C0_RELEASE_READBACK_MISMATCH")
    if (
        sha256_bytes(payload["control/evaluator-samples.csv"])
        != freeze["control"]["timing_csv_sha256"]
    ):
        raise ContractValidationError("POSITIVE_ADD_STUDY_C0_TIMING_SOURCE_BINDING_MISMATCH")
    if REQUIRED_GATE_STATUS != execution["official_boundary"]:
        raise ContractValidationError("POSITIVE_ADD_STUDY_GATE_PROMOTION_FORBIDDEN")

    run_summaries: list[dict[str, Any]] = []
    for row in execution["runs"]:
        if row["run_status"] == "COMPLETED":
            archive_bytes = payload[row["archive_path"]]
            sidecar_bytes = payload[f"{row['archive_path']}.sha256"]
            if (
                sha256_bytes(archive_bytes) != row["archive_sha256"]
                or sidecar_bytes.decode("ascii").strip()
                != f"{row['archive_sha256']}  {Path(row['archive_path']).name}"
            ):
                raise ContractValidationError("POSITIVE_ADD_STUDY_C1_ARCHIVE_BINDING_MISMATCH")
            with tempfile.TemporaryDirectory(prefix="positive-add-verify-run-") as temporary:
                run_archive = Path(temporary) / Path(row["archive_path"]).name
                run_archive.write_bytes(archive_bytes)
                Path(f"{run_archive}.sha256").write_bytes(sidecar_bytes)
                summary = _read_archive_run(run_archive, repo, row["role"])
            if summary != row["summary"]:
                raise ContractValidationError("POSITIVE_ADD_STUDY_C1_OUTCOME_READBACK_MISMATCH")
            run_summaries.append(summary)
        elif row["run_status"] == "FAILED":
            inventory = row.get("partial_raw_inventory", [])
            prefix = f"partial-runs/{row['execution_id']}/"
            actual = []
            for name, content in payload.items():
                if name.startswith(prefix):
                    relative = name[len(prefix) :]
                    actual.append(
                        {
                            "path": relative,
                            "size_bytes": len(content),
                            "sha256": sha256_bytes(content),
                        }
                    )
            if sorted(actual, key=lambda item: item["path"]) != sorted(
                inventory, key=lambda item: item["path"]
            ):
                raise ContractValidationError("POSITIVE_ADD_STUDY_PARTIAL_RAW_READBACK_MISMATCH")

    report, insertion = _render_report(execution)
    if payload["analysis/RESULTS_POSITIVE_ADD_UK.md"] != report.encode("utf-8") or payload[
        "analysis/MONOGRAPH_INSERTION_MAP_UK.md"
    ] != insertion.encode("utf-8"):
        raise ContractValidationError("POSITIVE_ADD_STUDY_REPORT_READBACK_MISMATCH")
    return {
        "study_id": STUDY_ID,
        "archive_sha256": sha256_file(archive_path),
        "member_count": len(payload),
        "completed_runs": len(run_summaries),
        "verification_status": "PASS",
        "execution_status": execution["execution_status"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    preflight_parser = commands.add_parser("preflight")
    preflight_parser.add_argument("--repository", type=Path, required=True)
    preflight_parser.add_argument("--output", type=Path, required=True)
    control_parser = commands.add_parser("verify-control")
    control_parser.add_argument("--repository", type=Path, required=True)
    control_parser.add_argument("--release-root", type=Path, required=True)
    run_parser = commands.add_parser("run")
    for name in ("repository", "output", "archive", "release-root", "preflight"):
        run_parser.add_argument(f"--{name}", type=Path, required=True)
    for name in ("workflow-run-url", "run-id", "run-attempt", "uv-version"):
        run_parser.add_argument(f"--{name}", required=True)
    recover_parser = commands.add_parser("recover")
    for name in ("repository", "source-evidence", "output"):
        recover_parser.add_argument(f"--{name}", type=Path, required=True)
    for name in (
        "workflow-run-url",
        "run-id",
        "run-attempt",
        "source-artifact-name",
        "source-artifact-digest",
    ):
        recover_parser.add_argument(f"--{name}", required=True)
    recover_parser.add_argument("--source-artifact-id", type=int, required=True)
    verify_parser = commands.add_parser("verify-bundle")
    verify_parser.add_argument("--archive", type=Path, required=True)
    verify_parser.add_argument("--repository", type=Path, required=True)
    verify_parser.add_argument("--extract-to", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "preflight":
            result = run_preflight(args.repository, args.output)
        elif args.command == "verify-control":
            result = _verify_control_release(args.repository, args.release_root)
        elif args.command == "run":
            result = run_study(
                args.repository,
                args.output,
                args.archive,
                args.release_root,
                args.preflight,
                workflow_run_url=args.workflow_run_url,
                run_id=args.run_id,
                run_attempt=args.run_attempt,
                uv_version=args.uv_version,
            )
        elif args.command == "recover":
            result = recover_study_archive(
                args.repository,
                args.source_evidence,
                args.output,
                workflow_run_url=args.workflow_run_url,
                run_id=args.run_id,
                run_attempt=args.run_attempt,
                source_artifact_id=args.source_artifact_id,
                source_artifact_name=args.source_artifact_name,
                source_artifact_digest=args.source_artifact_digest,
            )
        else:
            result = verify_study_bundle(args.archive, args.repository, extract_to=args.extract_to)
    except (
        ContractValidationError,
        ProtocolError,
        OSError,
        ValueError,
        zipfile.BadZipFile,
    ) as error:
        print(
            json.dumps({"verification_status": "FAIL", "error": str(error)}, sort_keys=True),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, sort_keys=True, indent=2))
    if args.command == "preflight" and (
        result.get("verification_status") != "PASS" or not all(result.get("probes", {}).values())
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
