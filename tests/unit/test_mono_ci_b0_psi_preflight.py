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
    ):
        load_schema(schema_name)
    validate_payload("mono_ci_b0_psi_case_manifest_v1.schema.json", _json("CASE_MANIFEST_V1.json"))
    validate_payload("mono_ci_b0_psi_inputs_v1.schema.json", _json("INPUTS_V1.json"))
    validate_payload(
        "mono_ci_b0_psi_evaluator_expectations_v1.schema.json",
        _json("EVALUATOR_CONTROL_EXPECTATIONS_V1.json"),
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
