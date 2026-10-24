"""Contract and provenance checks for the separate monograph CI preparation."""

from __future__ import annotations

import copy
import json
import zipfile
from pathlib import Path
from typing import Any, cast

import pytest

from experiments.execution.tooling.contracts import load_schema, validate_payload
from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.hashing import sha256_file
from experiments.execution.tooling.mono_ci_b0_psi_preflight import (
    PACKAGE_RELATIVE,
    _compare_case_archive_manifest,
    _parse_archive_checksums,
    _repository_file,
    _verify_case_bindings,
    _verify_case_specific_observation_binding,
    _verify_metric_contract,
    _verify_package_checksums,
    verify_preflight,
)

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / PACKAGE_RELATIVE


def _json(name: str) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((PACKAGE / name).read_text(encoding="utf-8")))


def _archive_manifest() -> dict[str, Any]:
    with zipfile.ZipFile(ROOT / "experiments/pilots/EVAL01_RAW_EVIDENCE_V1.zip") as archive:
        return cast(dict[str, Any], json.loads(archive.read("run-manifest.json")))


def test_preparation_schemas_are_valid_and_current_payloads_validate() -> None:
    for schema_name in (
        "mono_ci_b0_psi_case_manifest_v1.schema.json",
        "mono_ci_b0_psi_inputs_v1.schema.json",
        "mono_ci_b0_psi_evaluator_expectations_v1.schema.json",
        "mono_ci_b0_psi_metric_contract_v1.schema.json",
    ):
        load_schema(schema_name)
    validate_payload("mono_ci_b0_psi_case_manifest_v1.schema.json", _json("CASE_MANIFEST_V1.json"))
    validate_payload("mono_ci_b0_psi_inputs_v1.schema.json", _json("INPUTS_V1.json"))
    validate_payload(
        "mono_ci_b0_psi_evaluator_expectations_v1.schema.json",
        _json("EVALUATOR_CONTROL_EXPECTATIONS_V1.json"),
    )
    validate_payload(
        "mono_ci_b0_psi_metric_contract_v1.schema.json",
        _json("METRIC_CONTRACT_V1.json"),
    )


def test_preflight_is_repeatable_no_go_and_never_reports_measurements() -> None:
    before = {
        artifact["id"]: sha256_file(ROOT / artifact["path"])
        for artifact in _json("INPUTS_V1.json")["source_artifacts"]
    }
    first = verify_preflight(ROOT)
    second = verify_preflight(ROOT)
    after = {
        artifact["id"]: sha256_file(ROOT / artifact["path"])
        for artifact in _json("INPUTS_V1.json")["source_artifacts"]
    }

    assert first == second
    assert first["integrity_status"] == "PASS"
    assert first["readiness"] == "NO_GO"
    assert first["measurement_status"] == "NOT_EXECUTED"
    assert first["arms"] == {"B0": "NOT_EXECUTED", "PSI": "NOT_EXECUTED"}
    assert first["evaluator_execution"] == "NOT_EXECUTED"
    assert first["scoring"] == "NOT_EXECUTED"
    assert before == after


def test_b0_independence_and_paired_input_parity_remain_blocked() -> None:
    inputs = _json("INPUTS_V1.json")
    assert inputs["arms"]["B0"]["baseline_configuration_status"] == "NOT_IDENTIFIED"
    assert inputs["arms"]["B0"]["bundle_status"] == "NOT_CREATED"
    assert inputs["arms"]["B0"]["bundle_sha256"] is None
    assert inputs["arms"]["B0"]["common_input_ids"] == inputs["arms"]["PSI"]["common_input_ids"]
    assert inputs["arms"]["B0"]["planned_case_ids"] == inputs["arms"]["PSI"]["planned_case_ids"]
    assert "CANONICAL_SOURCE_OBSERVATIONS" not in inputs["common_input_ids_plan"]
    assert all(row["case_specific_evidence"] == [] for row in inputs["case_sources"])

    altered = copy.deepcopy(inputs)
    altered["arms"]["PSI"]["common_input_ids"].append("UNMATCHED_INPUT")
    with pytest.raises(ContractValidationError, match="COMMON_INPUT_PARITY_MISMATCH"):
        _verify_case_bindings(
            ROOT,
            altered,
            _json("CASE_MANIFEST_V1.json"),
            _json("EVALUATOR_CONTROL_EXPECTATIONS_V1.json"),
        )

    promoted = copy.deepcopy(inputs)
    promoted["arms"]["B0"]["baseline_configuration_status"] = "IDENTIFIED"
    with pytest.raises(ContractValidationError, match="validation failed"):
        validate_payload("mono_ci_b0_psi_inputs_v1.schema.json", promoted)

    promoted = copy.deepcopy(inputs)
    promoted["arms"]["PSI"]["algorithm_status"] = "READY"
    with pytest.raises(ContractValidationError, match="validation failed"):
        validate_payload("mono_ci_b0_psi_inputs_v1.schema.json", promoted)


def test_canonical_clean_a04_observations_cannot_be_current_evidence_for_mutated_cases() -> None:
    inputs = _json("INPUTS_V1.json")
    artifacts = {row["id"]: row for row in inputs["source_artifacts"]}
    case_sources = {row["case_id"]: row for row in inputs["case_sources"]}
    canonical_binding = artifacts["A04_PUBLIC_API_OBSERVATION"]["source_binding"]

    for case_id in ("CASE_02", "CASE_03", "CASE_04"):
        case_observation = {
            "case_id": case_id,
            "source_commit_sha": canonical_binding["source_commit_sha"],
            "repository_tree_sha": canonical_binding["repository_tree_sha"],
            "application_tree_sha": canonical_binding["application_tree_sha"],
            "independent_execution_status": "INDEPENDENTLY_EXECUTED",
            "raw_output_sha256": "a" * 64,
        }
        with pytest.raises(
            ContractValidationError,
            match=f"CASE_EVIDENCE_SOURCE_MISMATCH:{case_id}:source_commit_sha",
        ):
            _verify_case_specific_observation_binding(case_observation, case_sources[case_id])

    assert artifacts["A04_PUBLIC_API_OBSERVATION"]["method_input_eligible"] is False
    assert artifacts["A04_PUBLIC_API_OBSERVATION"]["case_evidence_eligible"] is False
    assert artifacts["A04_PUBLIC_API_OBSERVATION"]["evidence_scope"] == "HISTORICAL_CONTEXT_ONLY"


def test_case_specific_observation_requires_an_independent_execution_record() -> None:
    case_source = _json("INPUTS_V1.json")["case_sources"][0]
    observation = {
        "observation_id": "FUTURE_CASE_OBSERVATION",
        "evidence_scope": "CASE_SPECIFIC",
        "case_id": case_source["case_id"],
        "source_commit_sha": case_source["source_commit_sha"],
        "repository_tree_sha": case_source["repository_tree_sha"],
        "application_tree_sha": case_source["application_tree_sha"],
        "independent_execution_status": "HISTORICAL_CANONICAL_OBSERVATION",
        "raw_output_sha256": "b" * 64,
    }
    with pytest.raises(ContractValidationError, match="CASE_EVIDENCE_NOT_INDEPENDENTLY_EXECUTED"):
        _verify_case_specific_observation_binding(observation, case_source)

    historical = copy.deepcopy(observation)
    historical["observation_id"] = "A04_PUBLIC_API_OBSERVATION"
    historical["evidence_scope"] = "HISTORICAL_CONTEXT_ONLY"
    historical["independent_execution_status"] = "INDEPENDENTLY_EXECUTED"
    with pytest.raises(ContractValidationError, match="HISTORICAL_OBSERVATION_NOT_CASE_EVIDENCE"):
        _verify_case_specific_observation_binding(historical, case_source)


def test_unknown_applicability_incomplete_denominator_and_missing_reference_stay_explicit() -> None:
    inputs = _json("INPUTS_V1.json")
    cases = _json("CASE_MANIFEST_V1.json")
    expectations = _json("EVALUATOR_CONTROL_EXPECTATIONS_V1.json")
    assert inputs["shared_policy_context"]["applicability"] == "UNKNOWN"
    assert cases["case_boundary"]["obligation_denominator"] == "INCOMPLETE"
    assert inputs["reference_separation"]["expected_operations_status"] == "NOT_CREATED"
    assert inputs["reference_separation"]["governance_labels_status"] == "NOT_CREATED"
    assert expectations["fitness_operation_reference"] == "NOT_ESTABLISHED"
    assert expectations["coverage_denominator"] == "INCOMPLETE"
    assert "coverage_percentage" not in expectations

    promoted = copy.deepcopy(inputs)
    promoted["shared_policy_context"]["applicability"] = "INACTIVE"
    with pytest.raises(ContractValidationError, match="validation failed"):
        validate_payload("mono_ci_b0_psi_inputs_v1.schema.json", promoted)


def test_metric_contract_keeps_arm_applicability_and_statuses_distinct() -> None:
    contract = _json("METRIC_CONTRACT_V1.json")
    _verify_metric_contract(contract)
    by_id = {row["metric_id"]: row for row in contract["metrics"]}
    assert by_id["OPERATION_SELECTION_CORRECTNESS"]["current_status_by_arm"] == {
        "B0": "N/A",
        "PSI": "NOT_EVALUABLE",
    }
    assert by_id["GOVERNANCE_DECISION_CORRECTNESS"]["current_status_by_arm"]["B0"] == "N/A"
    assert by_id["CURRENT_CONFIGURATION_VERIFIED_COVERAGE"]["current_status_by_arm"] == {
        "B0": "NOT_EVALUABLE",
        "PSI": "NOT_EVALUABLE",
    }
    assert by_id["END_TO_END_CASE_EXECUTION_DURATION"]["current_status_by_arm"] == {
        "B0": "NOT_MEASURED",
        "PSI": "NOT_MEASURED",
    }
    assert contract["status_semantics"]["numeric_substitution_prohibited"] is True

    mislabeled = copy.deepcopy(contract)
    mislabeled["metrics"][0]["current_status_by_arm"]["B0"] = "NOT_EVALUABLE"
    with pytest.raises(ContractValidationError, match="METRIC_ARM_STATUS_MISMATCH"):
        _verify_metric_contract(mislabeled)

    invalid_status = copy.deepcopy(contract)
    invalid_status["metrics"][0]["current_status_by_arm"]["B0"] = "0"
    with pytest.raises(ContractValidationError, match="validation failed"):
        validate_payload("mono_ci_b0_psi_metric_contract_v1.schema.json", invalid_status)


def test_evaluator_expectations_are_review_only_and_scope_is_exactly_two_controls() -> None:
    inputs = _json("INPUTS_V1.json")
    cases = _json("CASE_MANIFEST_V1.json")
    expectations = _json("EVALUATOR_CONTROL_EXPECTATIONS_V1.json")
    assert expectations["reference_status"] == "AUTHOR_DECLARED_UNREVIEWED_DIAGNOSTIC_ONLY"
    assert expectations["independently_reviewed"] is False
    assert expectations["frozen_for_new_study"] is False
    assert expectations["included_in_method_inputs"] is False
    assert inputs["reference_separation"]["included_in_either_method_bundle"] is False
    archive = cases["source_case_archive"]
    assert expectations["source"]["preregistered_catalog_path"] == archive["case_catalog_path"]
    assert expectations["source"]["preregistered_catalog_sha256"] == archive["case_catalog_sha256"]
    assert expectations["source"]["raw_archive_sha256"] == archive["sha256"]
    eligible_ids = {
        item["id"] for item in inputs["source_artifacts"] if item["method_input_eligible"]
    }
    assert "EVALUATOR_EXPECTATIONS" not in eligible_ids
    assert "EVAL01_RAW_ARCHIVE" not in eligible_ids
    assert all(
        set(row["evaluator_statuses"]) == {"AC_PUBLIC_API", "AC_MODULE_GRAPH"}
        for row in expectations["expectations"]
    )

    extra_control = copy.deepcopy(expectations)
    extra_control["expectations"][0]["evaluator_statuses"]["AC_LAYERING"] = "COMPLIANT"
    with pytest.raises(ContractValidationError, match="validation failed"):
        validate_payload("mono_ci_b0_psi_evaluator_expectations_v1.schema.json", extra_control)


def test_archive_mutation_provenance_mismatch_fails_closed() -> None:
    cases = _json("CASE_MANIFEST_V1.json")
    manifest = _archive_manifest()
    _compare_case_archive_manifest(cases, manifest)

    altered = copy.deepcopy(cases)
    altered["cases"][1]["repository_tree_sha"] = "0" * 40
    with pytest.raises(ContractValidationError, match="ARCHIVE_PROVENANCE_MISMATCH"):
        _compare_case_archive_manifest(altered, manifest)

    altered = copy.deepcopy(cases)
    altered["cases"][1]["source_parent_sha"] = None
    with pytest.raises(ContractValidationError, match="ARCHIVE_PARENT_MISMATCH"):
        _compare_case_archive_manifest(altered, manifest)


def test_archive_checksum_inventory_and_package_digest_tampering_are_rejected(
    tmp_path: Path,
) -> None:
    with pytest.raises(ContractValidationError, match="ARCHIVE_CHECKSUMS_INVENTORY_MISMATCH"):
        _parse_archive_checksums(b"", {"raw.json", "SHA256SUMS"})

    package = tmp_path / "package"
    package.mkdir()
    payload = package / "payload.json"
    payload.write_text("original", encoding="utf-8")
    checksum_file = package / "SHA256SUMS"
    checksum_file.write_text(f"{sha256_file(payload)}  payload.json\n", encoding="utf-8")
    _verify_package_checksums(package)
    payload.write_text("tampered", encoding="utf-8")
    with pytest.raises(ContractValidationError, match="PACKAGE_DIGEST_MISMATCH"):
        _verify_package_checksums(package)


def test_unsafe_artifact_paths_are_rejected() -> None:
    with pytest.raises(ContractValidationError, match="UNSAFE_PATH"):
        _repository_file(ROOT, "../outside.json")
    with pytest.raises(ContractValidationError, match="UNSAFE_PATH"):
        _repository_file(ROOT, "/outside.json")
