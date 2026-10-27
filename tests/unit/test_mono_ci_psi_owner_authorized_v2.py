"""Contracts for the separately frozen owner-authorized ΔA5 DEVELOPMENT V2 run."""

from __future__ import annotations

import hashlib
import json
import socket
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml

from experiments.execution.tooling import mono_ci_psi_a05 as a05
from experiments.execution.tooling import mono_ci_psi_evidence as evidence
from experiments.execution.tooling import mono_ci_psi_owner_authorized as owner
from experiments.execution.tooling import mono_ci_psi_owner_authorized_v2 as v2
from experiments.execution.tooling import mono_ci_psi_owner_authorized_v2_analysis as analysis
from experiments.execution.tooling import mono_ci_psi_transition as transition
from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError, ProtocolError

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_ROOT = ROOT / v2.PROTOCOL_ROOT


def _preflight_record() -> dict[str, Any]:
    return {
        "schema_version": "MONO_CI_PSI_DOCKER_ISOLATION_PREFLIGHT_V1",
        "classification": "DEVELOPMENT_SANDBOX_CAPABILITY_PREFLIGHT",
        "created_at_utc": "2026-10-27T12:00:00+00:00",
        "image": transition.ISOLATED_METHOD_IMAGE,
        "image_digest": transition.ISOLATED_METHOD_IMAGE.rsplit("@", 1)[-1],
        "required_python_version": "3.12.15",
        "platform": "linux/amd64",
        "host_identity": {
            "host_os": "Linux-test",
            "host_architecture": "x86_64",
            "runner_os": "Linux",
            "runner_image_os": "ubuntu24",
            "runner_image_version": "20261026.354.1",
            "host_python_version": "3.12.15",
            "host_python_implementation": "CPython",
            "host_cpu_count": 4,
            "host_uid": 1001,
            "host_gid": 123,
            "uv_version": "uv 0.13.6",
            "docker_client_version": "29.8.2",
            "docker_server_version": "29.8.2",
            "docker_daemon_platform": ["linux", "x86_64"],
            "docker_kernel_version": "test-kernel",
            "python_runtime_image": transition.ISOLATED_METHOD_IMAGE,
            "python_runtime_platform": "linux/amd64",
        },
        "network_canary": {"status": "CONTROL_REACHABLE_FROM_BRIDGE_CONTAINER"},
        "sandbox_container": {"status": "VERIFIED"},
        "probes": {
            key: True
            for key in (
                "runtime_started",
                "required_inputs_read",
                "permitted_output_writable",
                "scorer_file_unreadable",
                "other_arm_file_unreadable",
                "repository_history_unreadable",
                "outbound_network_denied",
                "test_canary_network_denied",
                "sensitive_environment_absent",
                "docker_socket_unmounted",
            )
        },
        "verification_status": "PASS",
        "error": None,
    }


def _write_preflight(path: Path, record: dict[str, Any]) -> str:
    path.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


@pytest.mark.parametrize(
    ("different_runtime", "expected"),
    [
        (False, ("EXISTING_NEGATIVE_PROBE",)),
        (True, ("A0_5_CLEAN", "EXISTING_NEGATIVE_PROBE")),
    ],
)
def test_protocol_schema_freezes_v2_scope_and_runner_comparison_rule(
    different_runtime: bool, expected: tuple[str, ...]
) -> None:
    protocol = json.loads((PROTOCOL_ROOT / "PROTOCOL_V2.json").read_text(encoding="utf-8"))
    v1_execution = json.loads((ROOT / v2.V1_EXECUTION).read_text(encoding="utf-8"))
    prior = v1_execution["runner_identity"]
    host_identity = {
        current: prior[previous] for current, previous in v2.V1_RUNNER_COMPARISON_FIELDS
    }
    if different_runtime:
        host_identity["runner_image_version"] = "different-hosted-image"
    validate_payload(v2.PROTOCOL_SCHEMA, protocol)
    assert protocol["study_id"] == v2.STUDY_ID
    assert protocol["authorization"]["explicit_exclusions"] == [
        "independent_review",
        "G1_completion",
        "G4_authorization",
        "normative_policy_approval",
        "official_measured_study",
    ]
    assert protocol["gates"]["P_ALGORITHM_STATUS"] == "NOT_READY"
    assert protocol["gates"]["G1"] == "INCOMPLETE"
    assert protocol["gates"]["G4"] == "NOT_AUTHORIZED"
    assert v2._calibration_source_conditions(host_identity) == expected


def test_freeze_schema_accepts_generated_timestamp_and_v1_runtime_comparison(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository = tmp_path / "repository"
    protocol_path = repository / v2.PROTOCOL_JSON
    protocol_path.parent.mkdir(parents=True)
    protocol_path.write_bytes((PROTOCOL_ROOT / "PROTOCOL_V2.json").read_bytes())

    preflight = _preflight_record()
    artifact = tmp_path / "preflight-artifact"
    artifact.mkdir()
    artifact_record = artifact / "sandbox-preflight.json"
    digest = _write_preflight(artifact_record, preflight)
    preserved_record = repository / v2.PRE_RUN_PREFLIGHT
    preserved_record.parent.mkdir(parents=True, exist_ok=True)
    preserved_record.write_bytes(artifact_record.read_bytes())
    Path(f"{preserved_record}.sha256").write_text(
        f"{digest}  {preserved_record.name}\n", encoding="ascii"
    )

    baseline = repository / owner.B0_RELATIVE
    baseline.parent.mkdir(parents=True)
    baseline.write_text("synthetic baseline fixture\n", encoding="utf-8")
    probe_root = repository / owner.HISTORICAL_PROBE_ROOT
    probe_manifest = probe_root / "probe-manifest.json"
    probe_source = probe_root / "source-files/app/modules/tasks/repository.py"
    probe_manifest.parent.mkdir(parents=True)
    probe_source.parent.mkdir(parents=True)
    probe_manifest.write_text("{}\n", encoding="utf-8")
    (probe_root / "source.patch").write_text("synthetic patch fixture\n", encoding="utf-8")
    probe_source.write_text("synthetic source fixture\n", encoding="utf-8")

    analysis_path = repository / (
        "experiments/execution/tooling/mono_ci_psi_owner_authorized_v2_analysis.py"
    )
    analysis_path.parent.mkdir(parents=True)
    analysis_path.write_text("synthetic analysis fixture\n", encoding="utf-8")
    v1_execution = repository / "fixtures/v1-execution.json"
    v1_execution.parent.mkdir(parents=True)
    host_identity = preflight["host_identity"]
    v1_execution.write_text(
        json.dumps(
            {
                "runner_identity": {
                    prior: host_identity[current]
                    for current, prior in v2.V1_RUNNER_COMPARISON_FIELDS
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(v2, "V1_EXECUTION", v1_execution)
    monkeypatch.setattr(
        v2,
        "_freeze_input_paths",
        lambda _repository: [
            v2.PROTOCOL_JSON.as_posix(),
            v2.PRE_RUN_PREFLIGHT.as_posix(),
            v2.PRE_RUN_PREFLIGHT_SIDECAR.as_posix(),
        ],
    )

    def fake_git(_repository: Path, *arguments: str) -> str:
        if arguments == ("status", "--porcelain"):
            return ""
        if arguments == ("rev-parse", "HEAD"):
            return "b" * 40
        raise AssertionError(f"Unexpected git command: {arguments}")

    monkeypatch.setattr(owner, "_git", fake_git)
    freeze = v2.create_freeze(repository, artifact)

    assert freeze["freeze_created_at_utc"]
    assert freeze["implementation_commit"] == "b" * 40
    assert freeze["evaluator_runtime_comparison_to_v1"] == {
        "fields_compared": [current for current, _ in v2.V1_RUNNER_COMPARISON_FIELDS],
        "differences": [],
        "same_evaluator_runtime": True,
    }


def _run_one_calibration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, complete: bool
) -> tuple[list[dict[str, Any]], list[Path]]:
    subject = tmp_path / "subject"
    probe = tmp_path / "probe"
    subject_config = subject / "architecture/acceptance/a1/public_api_v1.yaml"
    subject_config.parent.mkdir(parents=True)
    subject_config.write_text("evaluator: fixture\n", encoding="utf-8")
    state_manifest = subject / "architecture/states/A0_5_MODULE_DATA_OWNERSHIP.yaml"
    state_manifest.parent.mkdir(parents=True)
    state_manifest.write_text("state: fixture\n", encoding="utf-8")
    schedule = [
        {
            "evaluator_id": "AC_PUBLIC_API",
            "source_condition": "EXISTING_NEGATIVE_PROBE",
            "repetition_index": 1,
            "is_warmup": False,
        }
    ]
    monkeypatch.setattr(owner, "_calibration_schedule", lambda _conditions: schedule)
    monkeypatch.setattr(
        owner,
        "_git",
        lambda repository, *args: "c" * 40 if args[-1] == "HEAD" else "d" * 40,
    )
    seen_sources: list[Path] = []

    def bound_evaluator(**kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        seen_sources.append(kwargs["source_repository"])
        assert kwargs["repository"] == subject
        assert kwargs["source_checkout"] == probe
        output_directory = kwargs["output_directory"]
        output_directory.mkdir(parents=True)
        run_root = output_directory.parents[3]
        coverage_path = run_root / "coverage.json"
        coverage = {
            "source_inspection_status": "COMPLETE" if complete else "INCOMPLETE",
            "counts": {
                "missing_count": 0 if complete else 1,
                "altered_count": 0,
                "unexpected_count": 0,
            },
        }
        coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
        return (
            {"evidence": {"evaluator": {"version": "fixture"}}},
            {
                "source_commit_sha": "c" * 40,
                "source_tree_sha": "d" * 40,
                "application_tree_sha": "e" * 40,
                "evaluator_source_sha256": "f" * 64,
                "duration_ms": 12.5,
                "process_exit_code": 2,
                "execution_status": "COMPLETED",
                "compliance": "NON_COMPLIANT",
                "coverage_path": "coverage.json",
                "inspection_status": "COMPLETE" if complete else "INCOMPLETE",
                "finding_codes": ["FOREIGN_TABLE_ACCESS"],
                "output_path": "output.json",
                "output_sha256": "a" * 64,
                "stdout_sha256": "b" * 64,
                "stderr_sha256": "c" * 64,
            },
        )

    monkeypatch.setattr(owner, "_run_bound_evaluator", bound_evaluator)
    rows, _summary = owner._run_calibration(
        repository=tmp_path,
        subject=subject,
        probe_checkout=probe,
        run_root=tmp_path / "calibration",
        uv_version="uv fixture",
        study_id=v2.STUDY_ID,
        source_conditions=("EXISTING_NEGATIVE_PROBE",),
        bind_source_repository=True,
        require_source_readback=True,
    )
    return rows, seen_sources


def test_negative_probe_inspection_uses_probe_git_repository_and_records_raw_exit_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    rows, seen_sources = _run_one_calibration(monkeypatch, tmp_path, complete=True)
    assert seen_sources == [tmp_path / "probe"]
    assert rows[0]["sample_status"] == "MEASURED"
    assert rows[0]["process_exit_code"] == 2
    assert rows[0]["compliance"] == "NON_COMPLIANT"
    assert rows[0]["source_commit_sha"] == "c" * 40


def test_missing_or_incomplete_probe_inspection_stays_a_failed_measurement(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    rows, seen_sources = _run_one_calibration(monkeypatch, tmp_path, complete=False)
    assert seen_sources == [tmp_path / "probe"]
    assert rows[0]["sample_status"] == "FAILED"
    assert rows[0]["process_duration_ms"] is None
    assert rows[0]["error"]["message"] == "OWNER_AUTHORIZED_CALIBRATION_SOURCE_READBACK_FAILED"


def test_v1_post_run_readback_checks_all_archived_rows_without_promoting_failed_samples(
    tmp_path: Path,
) -> None:
    probe_output = tmp_path / "probe-replay"
    with a05.replay_negative_probe(
        ROOT,
        ROOT / v2.HISTORICAL_PROBE_ROOT,
        expected_parent_commit=owner.A05_COMMIT,
        expected_parent_tree=owner.A05_TREE,
        expected_parent_application_tree=owner.A05_APP_TREE,
        output=probe_output,
    ) as (probe_checkout, _manifest):
        capability = v2._v1_inspection_capability(ROOT, ROOT, probe_checkout)
    assert capability["verification_status"] == "PASS"
    assert capability["source_inspection_rows"] == 33
    assert capability["post_run_scope_pass_rows"] == 33
    assert capability["original_measurement_status_preserved"] is True
    assert all(row["original_sample_status"] == "FAILED" for row in capability["probe_rows"])


def test_partial_archive_retains_method_observation_and_separates_archive_error(
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "partial"
    run_root.mkdir()
    progress = {
        "phase_status": {
            "source_identity": "COMPLETED",
            "baseline_identity": "COMPLETED",
            "b0_evaluator_matrix": "COMPLETED",
            "method_input_bundle": "COMPLETED",
            "method_execution": "OBSERVED",
            "candidate_validation": "FAILED",
            "complete_transition_verification": "FAILED",
        },
        "scientific_status": {"method_decision": "OBSERVED"},
        "method_subprocess": {"status": "PROCESS_COMPLETED", "exit_code": 0},
        "method_observation": {
            "governance_decision": "HOLD",
            "operations": [],
            "operation_hold_reasons": ["COST_MODEL_UNRESOLVED"],
            "candidate_state": "NOT_MATERIALIZED",
            "raw_result_sha256": "a" * 64,
        },
        "source_identities": {"verification_status": "PASS"},
        "error": {"type": "ProtocolError", "message": "candidate check failed"},
        "ended_at_utc": "2026-10-27T12:00:00+00:00",
    }
    (run_root / "partial-execution.json").write_text(json.dumps(progress), encoding="utf-8")
    (run_root / "method-result.json").write_text('{"governance":{"result":"HOLD"}}\n')
    archive = tmp_path / "partial.zip"
    packed = owner.pack_partial_execution_archive(
        run_root,
        archive,
        study_id=v2.STUDY_ID,
        execution_id="DEV_PSI_TRANSITION_OADEV_V2_DELTA_A5_MEASURED_01",
        run_role="MEASURED",
        sandbox_preflight_id="b" * 64,
        archive_failure={"type": "ArchiveError", "message": "sealing retry"},
    )
    verified = owner.verify_partial_execution_archive(archive)
    assert packed["verification_status"] == verified["verification_status"] == "PASS"
    with zipfile.ZipFile(archive) as zipped:
        manifest = json.loads(zipped.read("PARTIAL_EVIDENCE_MANIFEST.json"))
    assert manifest["method_observation"]["governance_decision"] == "HOLD"
    assert manifest["error"]["message"] == "candidate check failed"
    assert manifest["archive_error"]["message"] == "sealing retry"
    assert "run/method-result.json" in zipfile.ZipFile(archive).namelist()


def test_partial_archive_rejects_changed_member_even_with_sidecar_rewritten(
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "partial"
    run_root.mkdir()
    progress = {
        "phase_status": {
            "source_identity": "NOT_EXECUTED",
            "baseline_identity": "NOT_EXECUTED",
            "b0_evaluator_matrix": "NOT_EXECUTED",
            "method_input_bundle": "NOT_EXECUTED",
            "method_execution": "NOT_OBSERVED",
            "candidate_validation": "NOT_EXECUTED",
            "complete_transition_verification": "NOT_EXECUTED",
        },
        "scientific_status": {"method_decision": "NOT_OBSERVED"},
        "ended_at_utc": "2026-10-27T12:00:00+00:00",
    }
    (run_root / "partial-execution.json").write_text(json.dumps(progress), encoding="utf-8")
    archive = tmp_path / "partial.zip"
    owner.pack_partial_execution_archive(
        run_root,
        archive,
        study_id=v2.STUDY_ID,
        execution_id="DEV_PSI_TRANSITION_OADEV_V2_DELTA_A5_WARMUP_00",
        run_role="WARMUP",
        sandbox_preflight_id="b" * 64,
    )
    replacement = tmp_path / "replacement.zip"
    with zipfile.ZipFile(archive) as original, zipfile.ZipFile(replacement, "w") as updated:
        for name in original.namelist():
            data = original.read(name)
            if name == "run/partial-execution.json":
                data += b"tampered\n"
            updated.writestr(name, data)
    replacement.replace(archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    Path(f"{archive}.sha256").write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    with pytest.raises(ContractValidationError, match="MEMBER_DIGEST_MISMATCH"):
        owner.verify_partial_execution_archive(archive)


def test_full_record_partial_archive_keeps_method_result_after_archive_failure(
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "complete-run"
    method_path = run_root / "PSI/raw/method-result.json"
    method_path.parent.mkdir(parents=True)
    method_path.write_text(
        json.dumps(
            {
                "governance": {"result": "REJECT", "reason_codes": ["NO_VALID_ACTION"]},
                "operation_plan": {"operations": [], "hold_reasons": []},
                "candidate": None,
            }
        ),
        encoding="utf-8",
    )
    transition = {
        "before_commit_sha": "a" * 40,
        "before_repository_tree_sha": "b" * 40,
        "before_application_tree_sha": "c" * 40,
        "after_commit_sha": "d" * 40,
        "after_repository_tree_sha": "e" * 40,
        "after_application_tree_sha": "f" * 40,
    }
    (run_root / "development_run.json").write_text(
        json.dumps(
            {
                "transition": transition,
                "psi": {
                    "status": "DEVELOPMENT_METHOD_EXECUTED",
                    "execution_duration_ms": 17.5,
                    "raw_result_path": "PSI/raw/method-result.json",
                },
            }
        ),
        encoding="utf-8",
    )
    archive = tmp_path / "full-record-partial.zip"
    owner.pack_partial_execution_archive(
        run_root,
        archive,
        study_id=v2.STUDY_ID,
        execution_id="DEV_PSI_TRANSITION_OADEV_V2_DELTA_A5_MEASURED_02",
        run_role="MEASURED",
        sandbox_preflight_id="b" * 64,
        archive_failure={"type": "ArchiveError", "message": "complete archive failed"},
    )
    with zipfile.ZipFile(archive) as zipped:
        manifest = json.loads(zipped.read("PARTIAL_EVIDENCE_MANIFEST.json"))
    assert manifest["method_observation"]["governance_decision"] == "REJECT"
    assert (
        manifest["method_observation"]["raw_result_sha256"]
        == hashlib.sha256(method_path.read_bytes()).hexdigest()
    )
    assert manifest["archive_error"]["message"] == "complete archive failed"


def test_v2_preserves_a_partial_record_when_transition_fails_before_creating_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    subject = tmp_path / "subject"
    subject.mkdir()
    output = tmp_path / "run-output"
    artifacts = tmp_path / "artifacts"

    def fail_before_output(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise ProtocolError("fixture precondition failure")

    monkeypatch.setattr(v2, "run_a05_transition", fail_before_output)
    records, summary = v2._run_transitions(
        repository=tmp_path,
        subject=subject,
        output_root=output,
        artifact_root=artifacts,
        uv_version="uv fixture",
        sandbox_preflight_id="b" * 64,
    )
    assert len(records) == 4
    assert summary["partial_archives"] == 4
    assert summary["partial_raw_only"] == 0
    assert all(row["run_status"] == "FAILED" for row in records)
    for row in records:
        archive_path = artifacts / row["evidence_archive"]
        assert owner.verify_partial_execution_archive(archive_path)["verification_status"] == "PASS"
        with zipfile.ZipFile(archive_path) as zipped:
            partial = json.loads(zipped.read("run/partial-execution.json"))
        assert partial["error"]["message"] == "fixture precondition failure"


def test_v2_transition_readback_uses_persisted_record_when_wrapper_summary_is_compact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    subject = tmp_path / "subject"
    subject.mkdir()
    output = tmp_path / "run-output"
    artifacts = tmp_path / "artifacts"

    def execute_with_compact_return(
        _subject: Path,
        run_root: Path,
        execution_id: str,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        run_root.mkdir(parents=True)
        (run_root / "development_run.json").write_text(
            json.dumps(
                {
                    "execution_id": execution_id,
                    "evaluator_observations": [{"evaluator_id": "AC_PUBLIC_API"}],
                }
            ),
            encoding="utf-8",
        )
        return {"execution_id": execution_id}

    def transition_outcome(_run_root: Path, record: dict[str, Any]) -> dict[str, Any]:
        assert record["evaluator_observations"] == [{"evaluator_id": "AC_PUBLIC_API"}]
        return {
            "Psi": {
                "decision": "HOLD",
                "method_duration_ms": 12.5,
                "operation_plan": [],
                "candidate_state": "MATERIALIZED_UNAPPLIED",
            }
        }

    def pack_archive(
        _run_root: Path, archive_path: Path, *_args: Any, **_kwargs: Any
    ) -> dict[str, str]:
        archive_path.write_bytes(b"complete archive fixture")
        return {"archive_sha256": "a" * 64}

    monkeypatch.setattr(v2, "run_a05_transition", execute_with_compact_return)
    monkeypatch.setattr(owner, "_transition_outcome", transition_outcome)
    monkeypatch.setattr(v2, "pack_psi_transition_archive", pack_archive)
    monkeypatch.setattr(
        v2,
        "verify_psi_transition_archive",
        lambda *_args, **_kwargs: {"verification_status": "PASS"},
    )

    records, summary = v2._run_transitions(
        repository=tmp_path,
        subject=subject,
        output_root=output,
        artifact_root=artifacts,
        uv_version="uv fixture",
        sandbox_preflight_id="b" * 64,
    )

    assert summary["completed_runs"] == 4
    assert all(row["run_status"] == "COMPLETED" for row in records)
    assert all(row["method_decision"] == "HOLD" for row in records)
    assert all(row["method_execution_duration_ms"] == 12.5 for row in records)


@pytest.mark.parametrize(
    ("failure_stage", "phase_status", "method_subprocess", "method_observation", "expected_phase"),
    [
        (
            "AFTER_B0_BEFORE_PSI",
            {
                "source_identity": "COMPLETED",
                "baseline_identity": "COMPLETED",
                "b0_evaluator_matrix": "COMPLETED",
                "method_input_bundle": "NOT_EXECUTED",
                "method_execution": "NOT_OBSERVED",
                "candidate_validation": "NOT_EXECUTED",
                "complete_transition_verification": "NOT_EXECUTED",
            },
            None,
            None,
            "b0_evaluator_matrix",
        ),
        (
            "SANDBOX_CREATION",
            {
                "source_identity": "COMPLETED",
                "baseline_identity": "COMPLETED",
                "b0_evaluator_matrix": "COMPLETED",
                "method_input_bundle": "COMPLETED",
                "method_execution": "NOT_OBSERVED",
                "candidate_validation": "NOT_EXECUTED",
                "complete_transition_verification": "NOT_EXECUTED",
            },
            {"status": "SANDBOX_CREATE_FAILED", "exit_code": None},
            None,
            "method_execution",
        ),
        (
            "PSI_EXECUTION",
            {
                "source_identity": "COMPLETED",
                "baseline_identity": "COMPLETED",
                "b0_evaluator_matrix": "COMPLETED",
                "method_input_bundle": "COMPLETED",
                "method_execution": "IN_PROGRESS",
                "candidate_validation": "NOT_EXECUTED",
                "complete_transition_verification": "NOT_EXECUTED",
            },
            {"status": "PROCESS_FAILED", "exit_code": 1},
            None,
            "method_execution",
        ),
        (
            "CANDIDATE_VALIDATION",
            {
                "source_identity": "COMPLETED",
                "baseline_identity": "COMPLETED",
                "b0_evaluator_matrix": "COMPLETED",
                "method_input_bundle": "COMPLETED",
                "method_execution": "OBSERVED",
                "candidate_validation": "FAILED",
                "complete_transition_verification": "NOT_EXECUTED",
            },
            {"status": "PROCESS_COMPLETED", "exit_code": 0},
            {
                "governance_decision": "HOLD",
                "operations": [],
                "operation_hold_reasons": ["UNKNOWN_MANDATORY_LINK_PREVENTS_TRANSITION"],
                "candidate_state": "MATERIALIZED_UNAPPLIED",
                "raw_result_sha256": "f" * 64,
            },
            "candidate_validation",
        ),
    ],
)
def test_transition_stage_failures_preserve_completed_phases_and_raw_marker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failure_stage: str,
    phase_status: dict[str, str],
    method_subprocess: dict[str, Any] | None,
    method_observation: dict[str, Any] | None,
    expected_phase: str,
) -> None:
    subject = tmp_path / "subject"
    subject.mkdir()
    output = tmp_path / "run-output"
    artifacts = tmp_path / "artifacts"
    marker = b"authentic stage evidence\n"

    def fail_after_stage(
        _subject: Path,
        run_root: Path,
        execution_id: str,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        run_root.mkdir(parents=True)
        marker_path = run_root / "PSI/evaluator-observations/before/AC_PUBLIC_API/stdout.bin"
        marker_path.parent.mkdir(parents=True)
        marker_path.write_bytes(marker)
        partial = {
            "schema_version": "MONO_CI_PSI_PARTIAL_TRANSITION_V1",
            "classification": "PARTIAL_EXECUTION_EVIDENCE",
            "execution_id": execution_id,
            "started_at_utc": "2026-10-27T12:00:00+00:00",
            "ended_at_utc": "2026-10-27T12:00:01+00:00",
            "source_identities": {"verification_status": "PASS"},
            "phase_status": phase_status,
            "method_subprocess": method_subprocess,
            "method_observation": method_observation,
            "scientific_status": {
                "method_decision": "OBSERVED" if method_observation else "NOT_OBSERVED",
                "operation_plan": "OBSERVED" if method_observation else "NOT_OBSERVED",
                "candidate": "OBSERVED" if method_observation else "NOT_OBSERVED",
                "official_measurement_status": "NOT_EXECUTED",
                "g1": "INCOMPLETE",
                "g4": "NOT_AUTHORIZED",
            },
            "error": {"type": "ProtocolError", "message": f"fixture {failure_stage}"},
            "available_artifacts": [
                {
                    "path": marker_path.relative_to(run_root).as_posix(),
                    "sha256": hashlib.sha256(marker).hexdigest(),
                }
            ],
        }
        (run_root / "partial-execution.json").write_text(json.dumps(partial), encoding="utf-8")
        raise ProtocolError(f"fixture {failure_stage}")

    monkeypatch.setattr(v2, "run_a05_transition", fail_after_stage)
    records, summary = v2._run_transitions(
        repository=tmp_path,
        subject=subject,
        output_root=output,
        artifact_root=artifacts,
        uv_version="uv fixture",
        sandbox_preflight_id="b" * 64,
    )

    assert summary["partial_archives"] == 4
    for row in records:
        with zipfile.ZipFile(artifacts / row["evidence_archive"]) as zipped:
            manifest = json.loads(zipped.read("PARTIAL_EVIDENCE_MANIFEST.json"))
            assert (
                zipped.read("run/PSI/evaluator-observations/before/AC_PUBLIC_API/stdout.bin")
                == marker
            )
        assert manifest["phase_status"][expected_phase] == phase_status[expected_phase]
        assert manifest["error"]["message"] == f"fixture {failure_stage}"
        if method_observation:
            assert manifest["method_observation"]["governance_decision"] == "HOLD"
        else:
            assert manifest["method_observation"] is None


def test_postrun_wrapper_failure_is_sealed_with_actual_method_observation(
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run"
    method_path = run_root / "PSI/raw/method-result.json"
    method_path.parent.mkdir(parents=True)
    method_path.write_text(
        json.dumps(
            {
                "governance": {"result": "HOLD", "reason_codes": ["APPLICABILITY_UNKNOWN"]},
                "operation_plan": {
                    "operations": [],
                    "hold_reasons": ["MANDATORY_APPLICABILITY_UNKNOWN"],
                },
                "candidate": {"changes": []},
                "candidate_sha256": "a" * 64,
            }
        ),
        encoding="utf-8",
    )
    sandbox_path = run_root / "PSI/raw/sandbox-execution.json"
    sandbox_path.parent.mkdir(parents=True, exist_ok=True)
    sandbox_path.write_text(
        json.dumps({"status": "DEVELOPMENT_METHOD_EXECUTED", "exit_code": 0}),
        encoding="utf-8",
    )
    extension_path = run_root / "diagnostics/a05-experiment-evidence.json"
    extension_path.parent.mkdir(parents=True)
    extension_path.write_text(
        json.dumps({"candidate_verification": {"method_candidate_validation_status": "valid"}}),
        encoding="utf-8",
    )
    record: dict[str, Any] = {
        "execution_id": "DEV_PSI_TRANSITION_OADEV_V2_DELTA_A5_MEASURED_01",
        "transition": {
            "before_commit_sha": "b" * 40,
            "before_repository_tree_sha": "c" * 40,
            "before_application_tree_sha": "d" * 40,
            "after_commit_sha": "e" * 40,
            "after_repository_tree_sha": "f" * 40,
            "after_application_tree_sha": "0" * 40,
        },
        "psi": {
            "status": "DEVELOPMENT_METHOD_EXECUTED",
            "execution_duration_ms": 1875.0,
            "raw_result_path": "PSI/raw/method-result.json",
        },
        "a05_extension": {"path": "diagnostics/a05-experiment-evidence.json"},
    }
    (run_root / "development_run.json").write_text(json.dumps(record), encoding="utf-8")

    v2._write_postrun_failure_progress(
        run_root,
        error=KeyError("evaluator_observations"),
        started_at=datetime(2026, 10, 27, 12, 0, tzinfo=UTC),
        complete_archive_verification="PASS",
    )
    archive = tmp_path / "postrun-partial.zip"
    owner.pack_partial_execution_archive(
        run_root,
        archive,
        study_id=v2.STUDY_ID,
        execution_id=record["execution_id"],
        run_role="MEASURED",
        sandbox_preflight_id="b" * 64,
    )
    assert owner.verify_partial_execution_archive(archive)["verification_status"] == "PASS"
    with zipfile.ZipFile(archive) as zipped:
        manifest = json.loads(zipped.read("PARTIAL_EVIDENCE_MANIFEST.json"))

    assert manifest["error"] == {
        "type": "KeyError",
        "message": "'evaluator_observations'",
    }
    assert manifest["method_observation"]["governance_decision"] == "HOLD"
    assert manifest["method_observation"]["operations"] == []
    assert manifest["method_observation"]["candidate_state"] == "MATERIALIZED_UNAPPLIED"
    assert manifest["method_subprocess"]["exit_code"] == 0
    assert manifest["phase_status"]["candidate_validation"] == "COMPLETED"
    assert manifest["phase_status"]["complete_transition_verification"] == "PASS"


def test_partial_archive_analysis_reads_method_and_candidate_observations(
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run"
    method_path = run_root / "PSI/raw/method-result.json"
    method_path.parent.mkdir(parents=True)
    method_path.write_text(
        json.dumps(
            {
                "governance": {
                    "result": "HOLD",
                    "reason_codes": ["APPLICABILITY_UNKNOWN"],
                },
                "operation_plan": {
                    "operations": [],
                    "hold_reasons": ["MANDATORY_APPLICABILITY_UNKNOWN"],
                },
                "candidate": {"changes": []},
                "candidate_sha256": "a" * 64,
            }
        ),
        encoding="utf-8",
    )
    extension_path = run_root / "diagnostics/a05-experiment-evidence.json"
    extension_path.parent.mkdir(parents=True)
    extension_path.write_text(
        json.dumps(
            {
                "candidate_verification": {
                    "method_candidate_validation_status": "valid",
                    "execution_cost": {
                        "candidate_validation_total_ms": 644.012,
                        "estimated_additional_ci_execution_ms_per_build": 0,
                    },
                    "outcome_comparisons": [
                        {
                            "representation_id": "REP_TEST",
                            "candidate_positive_outcome": "COMPLIANT",
                            "candidate_negative_outcome": "COMPLIANT",
                            "positive_outcome_parity": True,
                            "negative_outcome_parity": True,
                        }
                    ],
                }
            }
        ),
        encoding="utf-8",
    )
    for state_dir in ("before", "after"):
        for evaluator_id in ("AC_PUBLIC_API", "AC_MODULE_GRAPH"):
            evaluator_root = run_root / "PSI/evaluator-observations" / state_dir / evaluator_id
            evaluator_root.mkdir(parents=True)
            (evaluator_root / "process-execution.json").write_text(
                json.dumps(
                    {
                        "status": "OUTPUT_PARSED",
                        "exit_code": 0,
                        "stdout_sha256": "b" * 64,
                        "stderr_sha256": "c" * 64,
                    }
                ),
                encoding="utf-8",
            )
            (evaluator_root / "evaluator-output.json").write_text(
                json.dumps(
                    {
                        "result": {"execution_status": "COMPLETED", "compliance": "COMPLIANT"},
                        "architecture": {"target_source_sha": "d" * 40},
                    }
                ),
                encoding="utf-8",
            )
            (evaluator_root / "inspection-coverage.json").write_text(
                json.dumps({"source_inspection_status": "COMPLETE"}),
                encoding="utf-8",
            )
    record: dict[str, Any] = {
        "execution_id": "DEV_PSI_TRANSITION_FIXTURE_MEASURED_01",
        "source_revision_sha": "d" * 40,
        "a05_extension": {"path": "diagnostics/a05-experiment-evidence.json"},
        "transition": {
            "before_commit_sha": "a" * 40,
            "before_repository_tree_sha": "b" * 40,
            "before_application_tree_sha": "c" * 40,
            "after_commit_sha": "d" * 40,
            "after_repository_tree_sha": "e" * 40,
            "after_application_tree_sha": "f" * 40,
        },
        "psi": {
            "status": "DEVELOPMENT_METHOD_EXECUTED",
            "execution_duration_ms": 1918.254,
            "raw_result_path": "PSI/raw/method-result.json",
        },
    }
    (run_root / "development_run.json").write_text(json.dumps(record), encoding="utf-8")
    archive = tmp_path / "partial.zip"
    owner.pack_partial_execution_archive(
        run_root,
        archive,
        study_id=v2.STUDY_ID,
        execution_id=record["execution_id"],
        run_role="MEASURED",
        sandbox_preflight_id="e" * 64,
    )
    digest = v2._sha256(archive)
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    archive_copy = bundle / "partial.zip"
    archive_copy.write_bytes(archive.read_bytes())
    Path(f"{archive_copy}.sha256").write_text(f"{digest}  {archive_copy.name}\n", encoding="ascii")

    observed = analysis._read_partial_archive_row(
        bundle,
        {
            "execution_id": record["execution_id"],
            "role": "MEASURED",
            "measured": True,
            "run_status": "FAILED",
            "evidence_archive": "partial.zip",
            "evidence_sha256": digest,
            "evidence_classification": "PARTIAL_EXECUTION_EVIDENCE",
        },
    )

    assert observed["b0_execution_status"] == "ALL_OUTPUTS_PARSED"
    assert observed["method_process_status"] == "DEVELOPMENT_METHOD_EXECUTED"
    assert observed["method_decision"] == "HOLD"
    assert observed["governance_reason_codes"] == ["APPLICABILITY_UNKNOWN"]
    assert observed["hold_reasons"] == ["MANDATORY_APPLICABILITY_UNKNOWN"]
    assert observed["operation_plan"] == []
    assert observed["candidate_state"] == "MATERIALIZED_UNAPPLIED"
    assert observed["candidate_verification_status"] == "valid"
    assert observed["candidate_validation_cost_ms"] == 644.012
    assert observed["candidate_evaluators"][0]["positive_outcome_parity"] is True


def test_evaluator_invalid_output_preserves_exit_stdout_and_stderr(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository = tmp_path / "repository"
    cli = repository / "architecture/acceptance/a1/cli.py"
    cli.parent.mkdir(parents=True)
    cli.write_text("# fixed evaluator placeholder\n", encoding="utf-8")
    output = tmp_path / "evaluator-output"
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=2,
            stdout=b"invalid json output\n",
            stderr=b"diagnostic stream\n",
        ),
    )
    with pytest.raises(ProtocolError, match="OUTPUT_INVALID_JSON"):
        evidence.run_fresh_evaluator(
            repository=repository,
            source_checkout=repository,
            evaluator_id="AC_PUBLIC_API",
            architecture_state="A0_5_MODULE_DATA_OWNERSHIP",
            source_commit_sha="a" * 40,
            output_directory=output,
        )
    process = json.loads((output / "process-execution.json").read_text(encoding="utf-8"))
    assert process["exit_code"] == 2
    assert process["status"] == "OUTPUT_INVALID"
    assert (output / "stdout.bin").read_bytes() == b"invalid json output\n"
    assert (output / "stderr.bin").read_bytes() == b"diagnostic stream\n"
    assert (
        process["stdout_sha256"] == hashlib.sha256((output / "stdout.bin").read_bytes()).hexdigest()
    )
    assert (
        process["stderr_sha256"] == hashlib.sha256((output / "stderr.bin").read_bytes()).hexdigest()
    )


def test_preflight_sidecar_and_all_probes_are_required(tmp_path: Path) -> None:
    record_path = tmp_path / "sandbox-preflight.json"
    record = _preflight_record()
    validate_payload(v2.PREFLIGHT_SCHEMA, record)
    digest = _write_preflight(record_path, record)
    validated = v2._read_preflight(tmp_path)
    assert validated["preflight_id"] == digest
    record["probes"]["outbound_network_denied"] = False
    _write_preflight(record_path, record)
    with pytest.raises(ProtocolError, match="ISOLATION_PREFLIGHT_FAILED"):
        v2._read_preflight(tmp_path)


def test_technical_preflight_uses_a04_baseline_validator(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository = tmp_path / "repository"
    baseline_path = repository / owner.B0_RELATIVE
    baseline_path.parent.mkdir(parents=True)
    baseline_path.write_text("pinned A0.4 baseline\n", encoding="utf-8")
    probe = tmp_path / "probe"
    probe.mkdir()
    output = tmp_path / "output"
    output.mkdir()
    expected_digest = v2._sha256(baseline_path)
    calls: list[Path] = []

    def validate_a04(subject: Path) -> dict[str, str]:
        calls.append(subject)
        return {
            "baseline_configuration_sha256": expected_digest,
            "identity_status": "PROSPECTIVE_RECONSTRUCTION_NOT_HISTORICAL",
            "approval_status": "NOT_APPROVED",
        }

    monkeypatch.setattr(a05, "_validate_a04_proposal", validate_a04)
    monkeypatch.setattr(
        transition,
        "verify_execution_proposal",
        lambda *_args, **_kwargs: pytest.fail("legacy transition validator must not be called"),
    )
    monkeypatch.setattr(owner, "_git", lambda *_args: "c" * 40)
    monkeypatch.setattr(
        v2,
        "_v1_inspection_capability",
        lambda *_args: {"verification_status": "PASS", "inspection_status": "COMPLETE"},
    )

    result = v2._technical_preflight(
        repository,
        repository,
        probe,
        {"verification_status": "PASS", "preflight_id": "a" * 64},
        output,
    )

    assert calls == [repository]
    assert result["baseline_identity"]["configuration_sha256"] == expected_digest
    assert result["pre_measurement_execution_count"] == 0


def test_technical_preflight_failure_preserves_raw_premeasurement_evidence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output = tmp_path / "output"
    output.mkdir()
    protocol_root = tmp_path / "protocol"
    protocol_root.mkdir()
    (protocol_root / "PROTOCOL_V2.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(v2, "PROTOCOL_ROOT", protocol_root)
    preflight_root = tmp_path / "hosted-preflight"
    preflight_root.mkdir()
    record_path = preflight_root / "sandbox-preflight.json"
    record_path.write_text('{"verification_status":"PASS"}\n', encoding="utf-8")
    (preflight_root / "preflight.stdout.bin").write_bytes(b"hosted preflight output\n")
    (output / "output-permission-probe.txt").write_text("writable\n", encoding="ascii")

    preserved = v2._preserve_technical_preflight_failure(
        output,
        {"record_path": str(record_path), "preflight_id": "a" * 64},
        {"status": "PASS", "source_commit_sha": "b" * 40},
        ContractValidationError("OWNER_AUTHORIZED_V2_BASELINE_IDENTITY_MISMATCH"),
    )

    record = json.loads((preserved / "PREMEASUREMENT_FAILURE.json").read_text(encoding="utf-8"))
    assert record["verification_status"] == "FAIL"
    assert record["calibration_status"] == "NOT_STARTED"
    assert record["transition_attempts_started"] == 0
    assert record["method_psi_status"] == "NOT_OBSERVED"
    assert (preserved / "sandbox-preflight/preflight.stdout.bin").read_bytes() == (
        b"hosted preflight output\n"
    )
    assert (preserved / "protocol-snapshot/PROTOCOL_V2.json").is_file()
    assert (preserved / "output-permission-probe.txt").is_file()


def test_analysis_verifies_preserved_premeasurement_attempt_zip(tmp_path: Path) -> None:
    protocol_snapshot = tmp_path / "bundle/protocol-snapshot"
    protocol_snapshot.mkdir(parents=True)
    for source in (
        PROTOCOL_ROOT / v2.PREMEASUREMENT_FAILURE.name,
        PROTOCOL_ROOT / v2.PREMEASUREMENT_ARTIFACT.name,
        PROTOCOL_ROOT / v2.PREMEASUREMENT_ARTIFACT_SIDECAR.name,
    ):
        (protocol_snapshot / source.name).write_bytes(source.read_bytes())

    verified = analysis._read_preserved_premeasurement_failure(tmp_path / "bundle")

    assert verified is not None
    assert verified["archive_readback_status"] == "PASS"
    assert verified["archive_sha256"] == (
        "dbd0b4724aae79db3c9d0b0d472470b31f00287edbae3b11068795b1bc3df65f"
    )
    assert verified["calibration_calls_started"] == 0

    archive = protocol_snapshot / v2.PREMEASUREMENT_ARTIFACT.name
    archive.write_bytes(archive.read_bytes() + b"tamper")
    with pytest.raises(ContractValidationError, match="PREMEASUREMENT_RECORD_MISMATCH"):
        analysis._read_preserved_premeasurement_failure(tmp_path / "bundle")


def test_analysis_verifies_preserved_first_postexecution_readback_failure(
    tmp_path: Path,
) -> None:
    protocol_snapshot = tmp_path / "bundle/protocol-snapshot"
    protocol_snapshot.mkdir(parents=True)
    for source in (
        v2.POSTEXECUTION_READBACK_FAILURE,
        v2.POSTEXECUTION_READBACK_FAILURE_SIDECAR,
        v2.PREVIOUS_FREEZE,
        v2.PREVIOUS_FREEZE_SIDECAR,
    ):
        (protocol_snapshot / source.name).write_bytes((ROOT / source).read_bytes())

    verified = analysis._read_preserved_postexecution_readback_failure(tmp_path / "bundle")

    assert verified is not None
    assert verified["workflow_run_id"] == 40574090499
    assert len(verified["transition_attempts"]) == 4
    assert all(row["wrapper_run_status"] == "FAILED" for row in verified["transition_attempts"])
    assert all(row["method_decision"] == "HOLD" for row in verified["transition_attempts"])
    assert all(
        row["candidate_validation_status"] == "valid" for row in verified["transition_attempts"]
    )

    preserved_freeze = protocol_snapshot / v2.PREVIOUS_FREEZE.name
    preserved_freeze.write_bytes(preserved_freeze.read_bytes() + b"tamper")
    with pytest.raises(ContractValidationError, match="PRIOR_FREEZE_READBACK_MISMATCH"):
        analysis._read_preserved_postexecution_readback_failure(tmp_path / "bundle")


def test_docker_container_command_is_locked_to_isolation_contract(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(transition, "_docker_image_platform", lambda: "linux/amd64")
    source = tmp_path / "input.json"
    source.write_text("{}\n", encoding="utf-8")
    args = transition._docker_container_base_args(
        name="evofit-test",
        mounts=[(source, "/input.json", True), (tmp_path, "/output", False)],
    )
    for flag in (
        "--pull=never",
        "--platform",
        "linux/amd64",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
    ):
        assert flag in args
    assert any("target=/input.json,readonly" in value for value in args)
    assert any("target=/output" in value and "readonly" not in value for value in args)


def test_preflight_program_writes_structured_result_after_output_probe(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    input_path = tmp_path / "required-input.json"
    output_path = tmp_path / "preflight-result.json"
    input_path.write_text('{"probe":"readable"}\n', encoding="utf-8")

    def deny_network(*_args: Any, **_kwargs: Any) -> None:
        raise OSError(101, "blocked by fixture")

    monkeypatch.setattr(socket, "create_connection", deny_network)
    monkeypatch.setattr(sys, "version", "3.12.15 (fixture)")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "preflight-probe",
            str(input_path),
            str(output_path),
            '{"probe":"readable"}',
            "127.0.0.1",
            "1",
            str(tmp_path / "repository/.git/config"),
            str(tmp_path / "scorer.json"),
            str(tmp_path / "other-arm.json"),
        ],
    )
    for name in (
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "ACTIONS_RUNTIME_TOKEN",
        "DOCKER_HOST",
        "DOCKER_CONFIG",
    ):
        monkeypatch.delenv(name, raising=False)
    program = transition._docker_isolation_preflight_program()
    with pytest.raises(SystemExit) as exit_result:
        exec(compile(program, "<docker-isolation-preflight>", "exec"), {})  # noqa: S102
    assert exit_result.value.code == 0
    result = json.loads(output_path.read_text(encoding="utf-8"))
    assert result["output_value"] == "writable"
    assert Path(f"{output_path}.probe").read_text(encoding="utf-8") == "writable\n"
    assert result["network"]["host_canary"]["denied"] is True
    assert result["network"]["external_test_target"]["denied"] is True


def test_analysis_counts_parsed_observations_without_inferring_compliance() -> None:
    assert analysis._b0_summary([]) == "NOT_EXECUTED"
    rows = [
        {"process_observation_status": "OUTPUT_PARSED", "exit_code": 2, "compliance": "UNKNOWN"},
        {
            "process_observation_status": "OUTPUT_PARSED",
            "exit_code": 3,
            "compliance": "NOT_EVALUABLE",
        },
    ]
    assert analysis._b0_summary(rows) == "PARTIAL_2_OF_4"
    assert analysis._b0_summary(rows * 2) == "ALL_OUTPUTS_PARSED"


def test_analysis_separates_calibration_and_transition_b0_process_times() -> None:
    summaries = analysis._measured_timing_summaries(
        [
            {
                "measured": True,
                "b0_evaluator_outcomes": [{"duration_ms": 200.0}, {"duration_ms": 300.0}],
            },
            {"measured": False, "b0_evaluator_outcomes": [{"duration_ms": 999.0}]},
        ],
        [
            {"sample_status": "MEASURED", "is_warmup": False, "process_duration_ms": 100.0},
            {"sample_status": "MEASURED", "is_warmup": True, "process_duration_ms": 999.0},
            {"sample_status": "FAILED", "is_warmup": False, "process_duration_ms": 888.0},
        ],
    )

    transition_stats = summaries["measured_transition_b0_evaluator_process_times"]
    calibration_stats = summaries["measured_calibration_evaluator_process_times"]
    assert transition_stats["n"] == 2
    assert transition_stats["mean_ms"] == 250.0
    assert calibration_stats["n"] == 1
    assert calibration_stats["mean_ms"] == 100.0


def test_analysis_calibration_completeness_counts_exclude_warmups_from_measured_rows() -> None:
    counts = analysis._calibration_call_summary(
        {
            "measured_successful_samples": 30,
            "measured_failed_samples": 30,
            "measured_not_run_samples": 0,
            "warmup_samples": 6,
        },
        planned_calls=66,
    )

    assert counts == {
        "planned_calls": 66,
        "measured_successful_calls": 30,
        "measured_failed_calls": 30,
        "warmup_calls": 6,
        "not_run_measured_calls": 0,
    }


def test_analysis_strips_renderer_added_trailing_whitespace_from_svg(tmp_path: Path) -> None:
    figure = tmp_path / "figure.svg"
    figure.write_text('<svg>  \n<path d="M 0 0 " /> \n</svg>\n', encoding="utf-8")

    analysis._strip_trailing_whitespace(figure)

    assert figure.read_text(encoding="utf-8") == '<svg>\n<path d="M 0 0 " />\n</svg>\n'


def test_analysis_normalizes_csv_line_endings(tmp_path: Path) -> None:
    table = tmp_path / "samples.csv"
    table.write_bytes(b"header,value\r\nrow,1\r\n")

    analysis._normalize_csv_line_endings(table)

    assert table.read_bytes() == b"header,value\nrow,1\n"


def test_ci_runs_v2_preflight_and_study_only_on_the_dedicated_push() -> None:
    ci = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    preflight = ci["jobs"]["delta-a5-v2-sandbox-preflight"]
    study = ci["jobs"]["owner-authorized-delta-a5-v2"]
    assert preflight["runs-on"] == "ubuntu-24.04"
    assert any(
        "docker pull --platform linux/amd64" in step.get("run", "") for step in preflight["steps"]
    )
    assert "needs" in study and "development-quality" in study["needs"]
    assert "delta-a5-v2-sandbox-preflight" in study["needs"]
    assert "V2 PRE-RUN FREEZE" in study["if"]
    assert any(
        "preflight --repository" in step.get("run", "") and "--freeze" in step.get("run", "")
        for step in study["steps"]
    )
    assert any('PREFLIGHT_OUTPUT="$RUNNER_TEMP/' in step.get("run", "") for step in study["steps"])
    assert any('RUN_OUTPUT="$RUNNER_TEMP/' in step.get("run", "") for step in study["steps"])
    assert any(
        "measurement-preflight" in step.get("with", {}).get("name", "") for step in study["steps"]
    )
    raw_upload = next(
        step
        for step in study["steps"]
        if "owner-authorized-v2-raw" in step.get("with", {}).get("name", "")
    )
    assert "early-failure-evidence/" in raw_upload["with"]["path"]
    assert any("release download" in step.get("run", "") for step in study["steps"])
    assemble = next(
        step
        for step in study["steps"]
        if step.get("name") == "Assemble durable outer evidence archive"
    )
    assert 'sha256sum "$OUTER_ARCHIVE_NAME"' in assemble["run"]
    assert 'sha256sum "$OUTER_ARCHIVE" > "$OUTER_ARCHIVE.sha256"' not in assemble["run"]
