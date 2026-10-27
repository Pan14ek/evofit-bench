"""Contracts for the separately frozen owner-authorized ΔA5 DEVELOPMENT V2 run."""

from __future__ import annotations

import hashlib
import json
import socket
import subprocess
import sys
import zipfile
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
    assert any("release download" in step.get("run", "") for step in study["steps"])
