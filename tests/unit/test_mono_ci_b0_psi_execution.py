"""Contracts for the MONO CI B0/Ψ DEVELOPMENT execution supplement."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from experiments.execution.tooling import mono_ci_b0_psi_execution as execution_module
from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import (
    ContractValidationError,
    MethodNotReadyError,
)
from experiments.execution.tooling.hashing import sha256_file
from experiments.execution.tooling.mono_ci_b0_psi_execution import (
    DEV_RUN_SCHEMA,
    _validate_bundle_file,
    _verify_evaluator_binding,
    materialize_development_inputs,
    verify_arm_input_bundle,
    verify_development_result,
    verify_execution_proposal,
)
from experiments.execution.tooling.mono_ci_b0_psi_execution import (
    execute_official_study as _execute_official_study,
)
from experiments.execution.tooling.mono_ci_b0_psi_scoring import (
    score_development_run,
    verify_scoring_assessment,
)

ROOT = Path(__file__).resolve().parents[2]


def _materialize(tmp_path: Path, execution_id: str = "DEV_MONO_CI_TEST") -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    output = tmp_path / execution_id
    materialize_development_inputs(ROOT, output, execution_id)
    return output


def _development_record(execution_id: str, output_checksums: dict[str, str]) -> dict[str, Any]:
    cases = []
    for case_number in range(1, 5):
        case_id = f"CASE_0{case_number}"
        evaluator_records = []
        for evaluator_id in ("AC_PUBLIC_API", "AC_MODULE_GRAPH"):
            raw_path = f"B0/raw/{case_id}/{evaluator_id}.json"
            evaluator_records.append(
                {
                    "evaluator_id": evaluator_id,
                    "version": "1.0.0",
                    "source_sha256": "d" * 64,
                    "configuration_sha256": "e" * 64,
                    "exit_code": 0,
                    "compliance": "COMPLIANT",
                    "raw_output_path": raw_path,
                    "raw_output_sha256": output_checksums.get(raw_path, "f" * 64),
                }
            )
        cases.append(
            {
                "case_id": case_id,
                "source_commit_sha": "a" * 40,
                "repository_tree_sha": "b" * 40,
                "application_tree_sha": "c" * 40,
                "status": "DEVELOPMENT_ONLY_EXECUTED",
                "scientific_applicability": "UNKNOWN",
                "fitness_validity": "UNKNOWN",
                "input_bundle_sha256": "0" * 64,
                "evaluators": evaluator_records,
                "technical_duration_ns": 10,
                "result_paths": [item["raw_output_path"] for item in evaluator_records],
            }
        )
    return {
        "schema_version": "MONO_CI_B0_PSI_DEV_RUN_V1",
        "execution_id": execution_id,
        "study_id": "MONO_CI_B0_PSI_DEVELOPMENT_TECHNICAL_VALIDATION",
        "parent_study_id": "MONO_CI_B0_PSI_COMPARISON_V1",
        "mode": "DEVELOPMENT_TECHNICAL_VALIDATION_ONLY",
        "study_readiness": "NO_GO",
        "measurement_status": "NOT_EXECUTED",
        "baseline": {
            "configuration_id": "MONO_CI_RECONSTRUCTED_B0_A03_V1",
            "configuration_sha256": "a" * 64,
            "identity_status": "PROSPECTIVE_RECONSTRUCTION_NOT_HISTORICAL",
            "approval_status": "NOT_APPROVED",
        },
        "common_input_parity": {
            "status": "PASS_DEVELOPMENT_COMMON_INPUTS_ONLY",
            "case_count": 4,
            "common_input_ids": ["SOURCE"],
        },
        "arms": {
            "B0": {
                "status": "DEVELOPMENT_EVALUATOR_PROBE_ONLY",
                "case_results": cases,
                "adaptation_operation": None,
                "governance_decision": None,
                "technical_duration_boundary": (
                    "CASE_START_THROUGH_RAW_EVALUATOR_OUTPUT_CHECKSUM_SEAL"
                ),
            },
            "PSI": {
                "status": "BLOCKED_NOT_EXECUTED",
                "reason": "P_ALGORITHM_STATUS_NOT_READY",
                "prediction_emitted": False,
                "operation_emitted": False,
                "governance_decision_emitted": False,
            },
        },
        "metrics": {
            "operation_selection_correctness": {"B0": "N/A", "PSI": "NOT_EVALUABLE"},
            "governance_decision_correctness": {"B0": "N/A", "PSI": "NOT_EVALUABLE"},
            "current_configuration_verified_coverage": {
                "B0": "NOT_EVALUABLE",
                "PSI": "NOT_EVALUABLE",
            },
            "controlled_violation_detection": {"B0": "NOT_MEASURED", "PSI": "NOT_MEASURED"},
            "stale_or_semantically_invalid_representations": {
                "B0": "NOT_EVALUABLE",
                "PSI": "NOT_EVALUABLE",
            },
            "assessed_candidate_coverage": {"B0": "N/A", "PSI": "NOT_MEASURED"},
            "actual_post_adaptation_coverage": {"B0": "N/A", "PSI": "NOT_MEASURED"},
            "end_to_end_case_execution_duration": {"B0": "NOT_MEASURED", "PSI": "NOT_MEASURED"},
        },
        "scoring": "NOT_EXECUTED_NO_SCORER_REFERENCE",
        "output_checksums": output_checksums or {"B0/raw/CASE_01/AC_PUBLIC_API.json": "f" * 64},
    }


def test_reconstruction_is_explicitly_prospective_and_source_pinned() -> None:
    result = verify_execution_proposal(ROOT)
    assert result["identity_status"] == "PROSPECTIVE_RECONSTRUCTION_NOT_HISTORICAL"
    assert result["approval_status"] == "NOT_APPROVED"
    assert result["study_readiness"] == "NO_GO"


def test_official_execution_stops_at_existing_readiness_and_method_guards() -> None:
    with pytest.raises(MethodNotReadyError, match="STUDY_NO_GO"):
        _execute_official_study()


def test_development_runner_records_b0_probe_and_keeps_psi_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    baseline_path = (
        ROOT / "experiments/execution/mono-ci-b0-psi-execution-v1/RECONSTRUCTED_B0_A03_V1.json"
    )
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    representations = {row["evaluator_id"]: row for row in baseline["representations"]}

    def fake_evaluator(
        evaluator_id: str,
        _repository: Path,
        configuration_path: Path,
        _state_manifest_path: Path,
        _state_id: str,
        source_commit_sha: str,
        _analyzer: Any,
    ) -> dict[str, Any]:
        representation = representations[evaluator_id]
        return {
            "architecture": {
                "target_source_sha": source_commit_sha,
                "expected_source_sha": source_commit_sha,
                "manifest_state_status": "MATCHED",
                "source_sha_status": "MATCHED",
            },
            "evaluator": {
                "source_digest": representation["evaluator_source_sha256"],
                "configuration_digest": sha256_file(configuration_path),
            },
            "result": {"execution_status": "COMPLETED", "compliance": "COMPLIANT"},
        }

    monkeypatch.setattr(execution_module, "run_evaluator", fake_evaluator)
    output = tmp_path / "runner-output"
    result = execution_module.run_development_validation(ROOT, output, "DEV_MONO_CI_RUNNER_TEST")
    run = verify_development_result(output)

    assert result["B0"] == "DEVELOPMENT_EVALUATOR_PROBE_ONLY"
    assert result["PSI"] == "BLOCKED_NOT_EXECUTED"
    assert run["study_readiness"] == "NO_GO"
    assert run["measurement_status"] == "NOT_EXECUTED"
    assert run["arms"]["B0"]["adaptation_operation"] is None
    assert run["arms"]["B0"]["governance_decision"] is None
    assert run["arms"]["PSI"]["operation_emitted"] is False
    assert len(run["arms"]["B0"]["case_results"]) == 4
    assert all(
        case["status"] == "DEVELOPMENT_ONLY_EXECUTED"
        and case["technical_duration_ns"] >= 0
        and len(case["evaluators"]) == 2
        for case in run["arms"]["B0"]["case_results"]
    )


def test_common_inputs_are_repeatable_equal_and_separate_by_arm(tmp_path: Path) -> None:
    first = _materialize(tmp_path / "first")
    second = _materialize(tmp_path / "second")

    for case_id in ("CASE_01", "CASE_02", "CASE_03", "CASE_04"):
        first_common: dict[str, str] = {}
        second_common: dict[str, str] = {}
        for arm in ("B0", "PSI"):
            first_bundle = first / arm / "input_bundle" / case_id
            second_bundle = second / arm / "input_bundle" / case_id
            first_manifest = verify_arm_input_bundle(first_bundle, expected_arm=arm)
            second_manifest = verify_arm_input_bundle(second_bundle, expected_arm=arm)
            first_common[arm] = first_manifest["common_input_sha256"]
            second_common[arm] = second_manifest["common_input_sha256"]
            assert first_manifest["bundle_sha256"] == second_manifest["bundle_sha256"]
            assert not (first_bundle / ".git").exists()
            assert not list(first_bundle.rglob("*.bundle"))
            assert not list(first_bundle.rglob("*expected*"))
            assert not list(first_bundle.rglob("*scorer*"))
            assert not list(first_bundle.rglob("*reference*"))
        assert first_common["B0"] == first_common["PSI"]
        assert second_common == first_common

        b0_output = first / "B0/raw" / case_id
        psi_output = first / "PSI/raw" / case_id
        assert not b0_output.exists()
        assert not psi_output.exists()
        assert not b0_output.resolve().is_relative_to((first / "B0/input_bundle").resolve())
        assert (
            not (first / "B0/input_bundle" / case_id)
            .resolve()
            .is_relative_to((first / "PSI/input_bundle" / case_id).resolve())
        )


def test_arm_bundle_readback_detects_tampering_and_symlinks(tmp_path: Path) -> None:
    run_root = _materialize(tmp_path)
    bundle = run_root / "B0/input_bundle/CASE_01"
    source = next(path for path in bundle.rglob("*.py"))
    source.write_bytes(source.read_bytes() + b"# tamper\n")
    with pytest.raises(ContractValidationError, match="FILE_DIGEST_MISMATCH"):
        verify_arm_input_bundle(bundle, expected_arm="B0")

    clean_root = _materialize(tmp_path / "clean", "DEV_MONO_CI_CLEAN")
    clean_bundle = clean_root / "PSI/input_bundle/CASE_01"
    (clean_bundle / "unlisted").symlink_to(clean_bundle / "manifest.json")
    with pytest.raises(ContractValidationError, match="SYMLINK_FORBIDDEN"):
        verify_arm_input_bundle(clean_bundle, expected_arm="PSI")


@pytest.mark.parametrize(
    "relative",
    [
        "scorer/reference.json",
        "scoring/assessment.json",
        "expected_outputs/prediction.json",
        "architecture/.git/config",
        "experiments/results/result.json",
    ],
)
def test_method_input_rejects_scorer_expected_and_git_paths(relative: str) -> None:
    with pytest.raises(ContractValidationError, match="FORBIDDEN_INPUT_PATH"):
        _validate_bundle_file(relative, b"safe content")


def test_method_input_rejects_oracle_markers_included_as_content() -> None:
    with pytest.raises(ContractValidationError, match="FORBIDDEN_INPUT_CONTENT"):
        _validate_bundle_file("case/source.json", b'{"expected_operations": []}')


def test_evaluator_records_reject_stale_or_wrong_evaluator_bindings() -> None:
    source = {
        "source_commit_sha": "a" * 40,
        "repository_tree_sha": "b" * 40,
        "application_tree_sha": "c" * 40,
    }
    evidence: dict[str, Any] = {
        "architecture": {
            "target_source_sha": source["source_commit_sha"],
            "expected_source_sha": source["source_commit_sha"],
            "manifest_state_status": "MATCHED",
            "source_sha_status": "MATCHED",
        },
        "evaluator": {"source_digest": "d" * 64, "configuration_digest": "e" * 64},
    }
    _verify_evaluator_binding(evidence, source, "d" * 64, "e" * 64)

    stale = copy.deepcopy(evidence)
    stale["architecture"]["target_source_sha"] = "f" * 40
    with pytest.raises(ContractValidationError, match="SOURCE_BINDING_MISMATCH"):
        _verify_evaluator_binding(stale, source, "d" * 64, "e" * 64)

    wrong_evaluator = copy.deepcopy(evidence)
    wrong_evaluator["evaluator"]["source_digest"] = "0" * 64
    with pytest.raises(ContractValidationError, match="SOURCE_DIGEST_MISMATCH"):
        _verify_evaluator_binding(wrong_evaluator, source, "d" * 64, "e" * 64)


def test_metric_statuses_remain_categorical_and_no_scoring_is_emitted() -> None:
    run = _development_record("DEV_MONO_CI_STATUS_TEST", {})
    validate_payload(DEV_RUN_SCHEMA, run)
    assert run["measurement_status"] == "NOT_EXECUTED"
    assert run["metrics"]["controlled_violation_detection"] == {
        "B0": "NOT_MEASURED",
        "PSI": "NOT_MEASURED",
    }
    run["metrics"]["current_configuration_verified_coverage"]["B0"] = 0
    with pytest.raises(ContractValidationError, match="validation failed"):
        validate_payload(DEV_RUN_SCHEMA, run)


def test_development_result_readback_rejects_changed_output(tmp_path: Path) -> None:
    run_root = _materialize(tmp_path)
    output_checksums: dict[str, str] = {}
    raw_paths: list[Path] = []
    for case_number in range(1, 5):
        case_id = f"CASE_0{case_number}"
        raw_root = run_root / "B0/raw" / case_id
        raw_root.mkdir(parents=True)
        for evaluator_id in ("AC_PUBLIC_API", "AC_MODULE_GRAPH"):
            raw = raw_root / f"{evaluator_id}.json"
            raw.write_text("{}\n", encoding="utf-8")
            raw_paths.append(raw)
            output_checksums[raw.relative_to(run_root).as_posix()] = sha256_file(raw)
    record = _development_record("DEV_MONO_CI_READBACK", output_checksums)
    record_path = run_root / "development_run.json"
    record_path.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
    record_digest = sha256_file(record_path)
    (run_root / "development_run.json.sha256").write_text(
        f"{record_digest}  development_run.json\n", encoding="utf-8"
    )
    checksum_files = sorted(
        path
        for path in run_root.rglob("*")
        if path.is_file() and path.relative_to(run_root).as_posix() != "SHA256SUMS"
    )
    (run_root / "SHA256SUMS").write_text(
        "".join(
            f"{sha256_file(path)}  {path.relative_to(run_root).as_posix()}\n"
            for path in checksum_files
        ),
        encoding="utf-8",
    )

    verify_development_result(run_root)
    score_root = run_root.parent / "separate-scoring-output"
    score_record = score_development_run(run_root, score_root)
    assert score_record["scoring_status"] == "NOT_EVALUABLE"
    assert score_record["reference_status"] == "NOT_ESTABLISHED"
    assert score_record["numeric_results"] == {}
    assert verify_scoring_assessment(score_root) == score_record
    assert not score_root.is_relative_to(run_root / "B0")
    assert not score_root.is_relative_to(run_root / "PSI")

    assessment_path = score_root / "scoring_assessment.json"
    assessment_path.write_text('{"tampered":true}\n', encoding="utf-8")
    with pytest.raises(ContractValidationError, match="validation failed"):
        verify_scoring_assessment(score_root)

    raw_paths[0].write_text('{"tampered":true}\n', encoding="utf-8")
    with pytest.raises(ContractValidationError, match="RAW_OUTPUT_DIGEST_MISMATCH"):
        verify_development_result(run_root)
