"""Tests for the separate owner-authorized DEVELOPMENT protocol and raw evidence handling."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

import pytest
import yaml

from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.mono_ci_psi_owner_authorized import (
    _method_outcome,
    pack_calibration_archive,
    verify_analysis_checksums,
    verify_calibration_archive,
)
from experiments.execution.tooling.mono_ci_psi_owner_authorized_analysis import (
    _budget_sensitivity,
    _summarize_calibration,
    descriptive_statistics,
    nearest_rank,
    resource_statistics,
)

PROTOCOL = Path(
    "experiments/execution/mono-ci-b0-psi-delta-a5-owner-authorized-v1/PROTOCOL_V1.json"
)


def test_nearest_rank_quantile_uses_preregistered_rank_without_interpolation() -> None:
    assert nearest_rank([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 0.9) == 9
    assert nearest_rank([], 0.9) is None


def test_descriptive_statistics_preserve_empty_and_single_sample_states() -> None:
    empty = descriptive_statistics([])
    assert empty["n"] == 0
    assert empty["mean_ms"] is None
    single = descriptive_statistics([12.5])
    assert single["n"] == 1
    assert single["median_ms"] == 12.5
    assert single["sample_standard_deviation_ms"] is None


def test_resource_statistics_preserve_missing_values_and_summarize_cpu_seconds() -> None:
    assert resource_statistics([None, None]) == {
        "n": 0,
        "mean_seconds": None,
        "sample_standard_deviation_seconds": None,
        "minimum_seconds": None,
        "maximum_seconds": None,
    }
    assert resource_statistics([0.25, None, 0.75]) == {
        "n": 2,
        "mean_seconds": 0.5,
        "sample_standard_deviation_seconds": 0.353553,
        "minimum_seconds": 0.25,
        "maximum_seconds": 0.75,
    }


def test_calibration_summary_excludes_warmup_and_retains_failed_and_missing_samples() -> None:
    rows = [
        {
            "source_condition": "A0_5_CLEAN",
            "evaluator_id": "AC_PUBLIC_API",
            "is_warmup": True,
            "sample_status": "MEASURED",
            "process_duration_ms": 100,
            "scope_verification_duration_ms": 110,
            "compliance": "COMPLIANT",
            "finding_codes": [],
            "inspection_status": "COMPLETE",
        },
        {
            "source_condition": "A0_5_CLEAN",
            "evaluator_id": "AC_PUBLIC_API",
            "is_warmup": False,
            "sample_status": "MEASURED",
            "process_duration_ms": 120,
            "scope_verification_duration_ms": 130,
            "compliance": "COMPLIANT",
            "finding_codes": [],
            "inspection_status": "COMPLETE",
        },
        {
            "source_condition": "A0_5_CLEAN",
            "evaluator_id": "AC_PUBLIC_API",
            "is_warmup": False,
            "sample_status": "FAILED",
            "process_duration_ms": None,
            "scope_verification_duration_ms": 140,
            "compliance": None,
            "finding_codes": [],
            "inspection_status": None,
        },
        {
            "source_condition": "A0_5_CLEAN",
            "evaluator_id": "AC_PUBLIC_API",
            "is_warmup": False,
            "sample_status": "NOT_RUN_BUDGET_EXHAUSTED",
            "process_duration_ms": None,
            "scope_verification_duration_ms": None,
            "compliance": None,
            "finding_codes": [],
            "inspection_status": None,
        },
    ]
    summary = _summarize_calibration(rows)
    cell = summary["cells"][0]
    assert summary["warmup_samples"] == 1
    assert cell["planned_measured_samples"] == 3
    assert cell["measured_samples"] == 1
    assert cell["failed_samples"] == 1
    assert cell["not_run_samples"] == 1
    assert cell["process_duration"]["mean_ms"] == 120


def test_method_outcome_preserves_hold_empty_plan_and_unapplied_candidate(tmp_path: Path) -> None:
    method = {
        "governance": {
            "result": "HOLD",
            "reason_codes": ["COST_MODEL_UNRESOLVED"],
        },
        "operation_plan": {"operations": [], "hold_reasons": ["COST_MODEL_UNRESOLVED"]},
        "candidate": {"changes": []},
        "candidate_sha256": "a" * 64,
    }
    method_path = tmp_path / "method-result.json"
    method_path.write_text(json.dumps(method), encoding="utf-8")
    result = _method_outcome(
        tmp_path,
        {
            "psi": {
                "raw_result_path": "method-result.json",
                "raw_result_sha256": hashlib.sha256(method_path.read_bytes()).hexdigest(),
                "prediction_emitted": False,
                "execution_duration_ms": 15.0,
                "scoring": "NOT_EXECUTED",
            }
        },
    )
    assert result["decision"] == "HOLD"
    assert result["operation_plan"] == []
    assert result["prediction_emitted"] is False
    assert result["candidate_state"] == "MATERIALIZED_UNAPPLIED"
    assert result["candidate_changes"] == []


def test_calibration_archive_round_trips_all_members_and_rejects_sidecar_tampering(
    tmp_path: Path,
) -> None:
    source = tmp_path / "raw"
    source.mkdir()
    (source / "measurement-records.jsonl").write_text('{"sample_status":"MEASURED"}\n')
    (source / "raw-output.json").write_text('{"result":{"compliance":"COMPLIANT"}}\n')
    archive = tmp_path / "calibration.zip"
    packed = pack_calibration_archive(source, archive)
    assert packed["verification_status"] == "PASS"
    assert verify_calibration_archive(archive)["member_count"] == 2
    Path(f"{archive}.sha256").write_text("0" * 64 + "  calibration.zip\n")
    with pytest.raises(ContractValidationError, match="SIDECAR_MISMATCH"):
        verify_calibration_archive(archive)


def test_calibration_archive_rejects_parent_traversal_even_with_matching_digest(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "unsafe.zip"
    content = b"should not be extracted"
    manifest = {
        "schema_version": "MONO_CI_PSI_OWNER_AUTHORIZED_CALIBRATION_ARCHIVE_V1",
        "classification": "DEVELOPMENT_CALIBRATION",
        "member_count": 1,
        "members": [
            {
                "path": "../escape.json",
                "size_bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        ],
    }
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("CALIBRATION_ARCHIVE_MANIFEST.json", json.dumps(manifest))
        zipped.writestr("../escape.json", content)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    Path(f"{archive}.sha256").write_text(f"{digest}  {archive.name}\n")
    with pytest.raises(ContractValidationError, match="MEMBER_PATH_INVALID"):
        verify_calibration_archive(archive)


def test_analysis_readback_verifies_each_derived_artifact_digest(tmp_path: Path) -> None:
    analysis = tmp_path / "analysis"
    analysis.mkdir()
    report = analysis / "report.md"
    report.write_text("derived from raw observations\n", encoding="utf-8")
    digest = hashlib.sha256(report.read_bytes()).hexdigest()
    (analysis / "ANALYSIS_SHA256SUMS.json").write_text(
        json.dumps({"report.md": digest}), encoding="utf-8"
    )
    assert verify_analysis_checksums(tmp_path) == [{"path": "report.md", "sha256": digest}]
    report.write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ContractValidationError, match="ANALYSIS_DIGEST_MISMATCH"):
        verify_analysis_checksums(tmp_path)


def test_analysis_readback_rejects_checksum_path_traversal(tmp_path: Path) -> None:
    analysis = tmp_path / "analysis"
    analysis.mkdir()
    (analysis / "ANALYSIS_SHA256SUMS.json").write_text(
        json.dumps({"../outside.json": "a" * 64}), encoding="utf-8"
    )
    with pytest.raises(ContractValidationError, match="ARCHIVE_MEMBER_PATH_INVALID"):
        verify_analysis_checksums(tmp_path)


def test_protocol_records_owner_authorization_without_promoting_official_gates() -> None:
    protocol: dict[str, Any] = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    validate_payload("mono_ci_psi_owner_authorized_protocol_v1.schema.json", protocol)
    assert protocol["authorization"]["provenance"] == "DIRECT_USER_CONVERSATION_INSTRUCTION"
    assert protocol["authorization"]["identity_independently_verified"] is False
    assert protocol["authorization"]["signature_artifact"] is None
    assert protocol["gates"]["G1"] == "INCOMPLETE"
    assert protocol["gates"]["G4"] == "NOT_AUTHORIZED"
    assert protocol["gates"]["P_ALGORITHM_STATUS"] == "NOT_READY"
    assert protocol["statistics"]["coverage_percentage"] == "NOT_COMPUTED"
    assert protocol["transition_runs"]["measured_runs"] == 3
    assert protocol["calibration"]["planned_total_process_calls_including_warmups"] == 66


def test_protocol_schema_rejects_gate_promotion_and_unapproved_baseline() -> None:
    protocol: dict[str, Any] = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    protocol["gates"]["G4"] = "AUTHORIZED"
    with pytest.raises(ContractValidationError):
        validate_payload("mono_ci_psi_owner_authorized_protocol_v1.schema.json", protocol)
    protocol["gates"]["G4"] = "NOT_AUTHORIZED"
    protocol["baseline"]["approval"] = "APPROVED"
    with pytest.raises(ContractValidationError):
        validate_payload("mono_ci_psi_owner_authorized_protocol_v1.schema.json", protocol)


def test_ci_calls_owner_authorized_reusable_workflow_only_on_its_branch_push() -> None:
    ci = yaml.safe_load(Path(".github/workflows/ci.yml").read_text(encoding="utf-8"))
    reusable = yaml.safe_load(
        Path(".github/workflows/mono-ci-psi-owner-authorized.yml").read_text(encoding="utf-8")
    )
    caller = ci["jobs"]["owner-authorized-delta-a5"]
    reusable_events = reusable.get("on", reusable.get(True, {}))

    assert caller["if"] == (
        "github.event_name == 'push' && "
        "github.ref == 'refs/heads/codex/research-owner-authorized-delta-a5'"
    )
    assert caller["needs"] == "development-quality"
    assert caller["uses"] == "./.github/workflows/mono-ci-psi-owner-authorized.yml"
    assert caller["permissions"] == {"contents": "write"}
    assert "workflow_call" in reusable_events
    assert "push" not in reusable_events
    assert "if" not in reusable["jobs"]["authorized-development-run"]


def test_execution_schema_requires_actual_run_statuses_and_preserves_gate_states() -> None:
    execution: dict[str, Any] = {
        "schema_version": "MONO_CI_PSI_OWNER_AUTHORIZED_EXECUTION_V1",
        "study_id": "MONO_CI_B0_PSI_DELTA_A5_OWNER_AUTHORIZED_DEV_V1",
        "classification": "RESEARCH_OWNER_AUTHORIZED_EXPLORATORY_DEVELOPMENT",
        "freeze_commit": "a" * 40,
        "freeze_record_sha256": "b" * 64,
        "protocol_sha256": "c" * 64,
        "runner_identity": {},
        "authorization": {
            "provenance": "DIRECT_USER_CONVERSATION_INSTRUCTION",
            "identity_independently_verified": False,
            "signature_artifact": None,
        },
        "source_identities": {},
        "baseline": {},
        "historical_probe_replay": {},
        "calibration": {},
        "transition_runs": [
            {"execution_id": f"run-{index}", "measured": index > 0, "run_status": "COMPLETED"}
            for index in range(4)
        ],
        "transition_summary": {},
        "gates": {
            "P_ALGORITHM_STATUS": "NOT_READY",
            "G1": "INCOMPLETE",
            "G4": "NOT_AUTHORIZED",
            "scoring": "NOT_EXECUTED",
            "coverage": "UNKNOWN",
        },
        "interpretation_boundary": {},
    }
    validate_payload("mono_ci_psi_owner_authorized_execution_v1.schema.json", execution)
    execution["transition_runs"][1]["run_status"] = "SUCCESSFUL_ADAPTATION"
    with pytest.raises(ContractValidationError):
        validate_payload("mono_ci_psi_owner_authorized_execution_v1.schema.json", execution)


def test_budget_sensitivity_keeps_the_psi_cost_model_unresolved() -> None:
    rows = [
        {"sample_status": "MEASURED", "is_warmup": False, "scope_verification_duration_ms": 1000},
        {"sample_status": "MEASURED", "is_warmup": False, "scope_verification_duration_ms": 2000},
    ]
    result = _budget_sensitivity(rows)
    assert result["scope_call_duration_p90_ms"] == 2000
    assert [row["estimated_evaluator_calls_at_p90"] for row in result["scenarios"]] == [
        450,
        900,
        1350,
    ]
    assert "does not estimate Ψ candidate cost" in result["interpretation"]
