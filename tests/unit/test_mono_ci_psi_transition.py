"""Real-source DEVELOPMENT execution and archive-readback contract tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError, ProtocolError
from experiments.execution.tooling.mono_ci_psi_transition import (
    _validate_method_result_v2,
    pack_transition_archive,
    run_transition,
    verify_transition_archive,
    verify_transition_run,
)

ROOT = Path(__file__).resolve().parents[2]


def test_real_transition_executes_psi_and_archive_round_trips(tmp_path: Path) -> None:
    run_root = tmp_path / "transition-run"
    result = run_transition(ROOT, run_root, "DEV_PSI_TRANSITION_UNIT_01")

    record = verify_transition_run(run_root)
    raw_path = run_root / record["psi"]["raw_result_path"]
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    state_manifest_path = run_root / record["transition"]["state_manifest_path"]
    state_manifest = json.loads(state_manifest_path.read_text(encoding="utf-8"))
    method_manifest = json.loads(
        (run_root / record["method_input"]["path"] / "method_input_v3.json").read_text()
    )
    runtime_inventory = json.loads((run_root / "provenance/runtime-inventory.json").read_text())
    adaptation_runtime_row = next(
        row
        for row in runtime_inventory["files"]
        if row["path"] == "experiments/execution/tooling/p_adaptation.py"
    )
    assert state_manifest_path.is_relative_to(run_root / "provenance")
    assert (
        state_manifest["manifests"][0]["sha256"]
        == record["transition"]["before_state_manifest_sha256"]
    )
    assert (
        state_manifest["manifests"][1]["sha256"]
        == record["transition"]["after_state_manifest_sha256"]
    )
    assert record["method_input"]["structural_manifest_path"] == (
        "architecture/states/A0_4_REPORT_QUERY_PORT.yaml"
    )
    observation = json.loads(
        (
            run_root / record["method_input"]["path"] / "architecture/structural-observations.json"
        ).read_text()
    )
    assert observation["source_commit_sha"] == record["transition"]["after_commit_sha"]
    assert observation["source_state"] == "after"
    assert raw["method_version"] == record["method_implementation"]["identity"]
    assert record["method_implementation"]["sha256"] == adaptation_runtime_row["sha256"]
    assert record["psi"]["execution_duration_ms"] >= 0
    assert record["psi"]["decision"] in {"HOLD", "REJECT", "ACCEPT"}
    assert all(row["path"] != state_manifest_path.name for row in method_manifest["files"])
    assert result["psi_decision"] == record["psi"]["decision"]
    assert record["transition"]["before_commit_sha"] == "26a9bb667da7d0938e38aca15d2bf29fd1de4829"
    assert record["transition"]["after_commit_sha"] == "d3101c0d3aa9b7b709253b6ec7518416f05f65b9"
    assert record["study_readiness"] == "NO_GO"
    assert record["measurement_status"] == "NOT_EXECUTED"
    assert record["p_algorithm_status"] == "NOT_READY"
    assert record["g1"] == "INCOMPLETE"
    assert record["g4"] == "NOT_AUTHORIZED"
    assert record["reference_gate"] == "NOT_READY"
    assert record["baseline"]["identity_status"] == "PROSPECTIVE_RECONSTRUCTION_NOT_HISTORICAL"
    assert record["baseline"]["approval_status"] == "NOT_APPROVED"
    assert record["baseline"]["method_input_authorized"] is False
    assert record["other_arms_or_case_outputs_used"] is False
    assert record["metrics"] == "NOT_MEASURED"
    assert record["psi"]["scoring"] == "NOT_EXECUTED"
    assert record["psi"]["prediction_emitted"] is (raw.get("prediction_v1") is not None)
    assert raw["result_contract_version"] == "MONO_CI_PSI_METHOD_RESULT_V2"
    assert raw["governance"]["result"] in {"HOLD", "REJECT", "ACCEPT"}
    if raw["governance"]["result"] == "ACCEPT":
        assert isinstance(raw.get("prediction_v1"), dict)
        assert isinstance(raw.get("candidate_v1"), dict)
    else:
        assert raw.get("prediction_v1") is None
        assert raw.get("candidate_v1") is None
    assert len(record["evaluator_observations"]) == 4
    assert {row["architecture_state"] for row in record["evaluator_observations"]} == {
        "A0_3_GOVERNED_MODULE_GRAPH",
        "A0_4_REPORT_QUERY_PORT",
    }
    assert all(row["execution_status"] == "COMPLETED" for row in record["evaluator_observations"])
    assert record["adaptation_evidence"]["trust_scope"] == "TEST_ONLY"
    assert raw["evidence_trust_scope"] == "TEST_ONLY"
    assert record["evidence_ledger"]["verified_fact_ids"] == [
        "FV01_AFTER",
        "FV01_BEFORE",
        "FV02_MODULES_ADDED",
        "FV03_MODULES_REMOVED",
    ]
    assert all(row["status"] == "UNKNOWN" for row in raw["after_applicability"]["results"])
    assert all(row["status"] == "UNKNOWN" for row in raw["candidate_coverage"]["obligations"])

    inventory_paths = {
        path.relative_to(run_root).as_posix() for path in run_root.rglob("*") if path.is_file()
    }
    assert not any(
        path.startswith(("B0/", "CASE_", "EVAL-01", "EVAL-02")) for path in inventory_paths
    )
    assert not any("scorer" in path.lower() or "oracle" in path.lower() for path in inventory_paths)

    archive_path = tmp_path / "transition.zip"
    packed = pack_transition_archive(
        run_root,
        archive_path,
        ROOT,
        "https://github.com/Pan14ek/evofit-bench/actions/runs/123456",
        "mono-ci-psi-transition-test-1",
        "uv 0.9.0",
    )
    assert packed["verification_status"] == "PASS"
    extracted = tmp_path / "archive-readback"
    verified = verify_transition_archive(archive_path, extract_to=extracted)
    assert verified["verification_status"] == "PASS"
    extracted_record = verify_transition_run(extracted)
    assert extracted_record["psi"]["raw_result_sha256"] == record["psi"]["raw_result_sha256"]

    sidecar_bytes = state_manifest_path.read_bytes()
    state_manifest_path.write_bytes(sidecar_bytes + b" ")
    with pytest.raises(ContractValidationError, match="OUTPUT_CHECKSUM_MISMATCH"):
        verify_transition_run(run_root)
    state_manifest_path.write_bytes(sidecar_bytes)

    raw_path.write_bytes(raw_path.read_bytes() + b" ")
    with pytest.raises(ContractValidationError, match="RAW_RESULT_DIGEST_MISMATCH"):
        verify_transition_run(run_root)
    raw_path.write_bytes(raw_path.read_bytes()[:-1])

    evidence_path = run_root / record["adaptation_evidence"]["path"]
    evidence_bytes = evidence_path.read_bytes()
    evidence_path.write_bytes(evidence_bytes + b" ")
    with pytest.raises(ContractValidationError, match="ADAPTATION_EVIDENCE_DIGEST_MISMATCH"):
        verify_transition_run(run_root)
    evidence_path.write_bytes(evidence_bytes)


def test_transition_contract_rejects_official_status_promotion(tmp_path: Path) -> None:
    with pytest.raises(ProtocolError, match="OUTPUT_MUST_BE_NEW_AND_EXTERNAL"):
        run_transition(ROOT, ROOT / "temporary-psi-run", "DEV_PSI_TRANSITION_UNIT_02")
    assert not (ROOT / "temporary-psi-run").exists()

    invalid = {
        "schema_version": "MONO_CI_PSI_TRANSITION_RUN_V1",
        "execution_id": "DEV_PSI_TRANSITION_UNIT_02",
        "study_id": "MONO_CI_B0_PSI_DEVELOPMENT_TECHNICAL_VALIDATION",
        "mode": "DEVELOPMENT_METHOD_EXECUTION_ONLY",
        "unit_of_analysis": "ONE_A0_3_TO_A0_4_ARCHITECTURE_TRANSITION",
        "study_readiness": "GO",
        "measurement_status": "NOT_EXECUTED",
        "p_algorithm_status": "NOT_READY",
        "g1": "INCOMPLETE",
        "g4": "NOT_AUTHORIZED",
        "reference_gate": "NOT_READY",
    }
    with pytest.raises(ContractValidationError, match="validation failed"):
        validate_payload("mono_ci_psi_transition_run_v1.schema.json", invalid)


def test_v2_method_result_allows_each_decision_with_bounded_prediction_shape() -> None:
    _validate_method_result_v2(
        {"governance": {"result": "HOLD"}, "prediction_v1": None, "candidate_v1": None}
    )
    _validate_method_result_v2(
        {"governance": {"result": "REJECT"}, "prediction_v1": None, "candidate_v1": None}
    )
    _validate_method_result_v2(
        {
            "governance": {"result": "ACCEPT"},
            "prediction_v1": {"prediction_id": "synthetic"},
            "candidate_v1": {"candidate_id": "synthetic"},
        }
    )

    with pytest.raises(ProtocolError, match="ACCEPT_OUTPUT_MISSING"):
        _validate_method_result_v2(
            {"governance": {"result": "ACCEPT"}, "prediction_v1": None, "candidate_v1": None}
        )
    with pytest.raises(ProtocolError, match="NONACCEPT_PREDICTION_PRESENT"):
        _validate_method_result_v2(
            {
                "governance": {"result": "HOLD"},
                "prediction_v1": {"prediction_id": "synthetic"},
                "candidate_v1": {"candidate_id": "synthetic"},
            }
        )
