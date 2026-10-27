"""Contracts for ΔA5 local evidence and semantic inventory; no test grants authority."""

from __future__ import annotations

import copy
import json
from datetime import date
from pathlib import Path
from typing import Any, cast

import jsonschema  # type: ignore[import-untyped]
import yaml

from experiments.execution.tooling.mono_ci_b0_psi_delta_a5 import (
    PACKAGE_RELATIVE,
    SCHEMA_RELATIVE,
    classify_semantic_inventory_row,
    evaluate_applicability_profile,
    is_verified_semantic_coverage,
    validate_semantic_inventory,
    verify_historical_archive,
    verify_package,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _package() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((REPOSITORY_ROOT / PACKAGE_RELATIVE).read_text()))


def _temporary_package(tmp_path: Path) -> tuple[dict[str, Any], Path]:
    package = _package()
    path = tmp_path / "readiness-package.json"
    path.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n")
    return package, path


def _catalog_ids() -> list[str]:
    catalog_path = REPOSITORY_ROOT / "fitness/catalog/architectural-obligations.yaml"
    catalog = yaml.safe_load(catalog_path.read_text())
    return [str(row["id"]) for row in catalog["obligations"]]


def _profile() -> tuple[dict[str, Any], list[str], str, str]:
    profile = copy.deepcopy(_package()["applicability_profile"])
    ids = _catalog_ids()
    return profile, ids, profile["catalog_sha256"], profile["state_manifest_sha256"]


def test_package_v2_verifies_only_local_evidence_and_does_not_replay_archive() -> None:
    result = verify_package(REPOSITORY_ROOT)
    assert result["verification_status"] == "LOCALLY_VERIFIED"
    assert result["local_repository_evidence_status"] == "LOCALLY_VERIFIED"
    assert result["historical_evidence_status"] == "HISTORICAL_VERIFICATION_REFERENCED"
    assert result["independent_archive_replay"]["status"] == "NOT_EXECUTED"
    assert result["independent_archive_replay"]["verified_claim_ids"] == []
    assert result["study_readiness"] == "NO_GO_WITH_EXPLICIT_BLOCKERS"
    assert result["catalog_rows"] == 18
    assert result["applicability_scoring_authorized"] is False

    package = _package()
    schema = json.loads((REPOSITORY_ROOT / SCHEMA_RELATIVE).read_text())
    jsonschema.Draft202012Validator(schema).validate(package)
    assert package["historical_development_run"]["verification_status"] == (
        "HISTORICAL_VERIFICATION_REFERENCED"
    )
    assert package["historical_development_run"]["reported_verification_status"] == (
        "PASS_ARCHIVE_READBACK"
    )
    assert package["historical_development_run"]["method_decision"] == "HOLD"
    assert package["historical_development_run"]["operation_plan"] == []
    assert package["historical_development_run"]["scoring_status"] == "NOT_EXECUTED"
    assert package["verification_scope"]["independent_archive_replay"]["status"] == ("NOT_EXECUTED")
    assert verify_package(REPOSITORY_ROOT) == result


def test_modified_local_source_artifact_digest_fails_local_verification(tmp_path: Path) -> None:
    package, path = _temporary_package(tmp_path)
    package["source_artifacts"][0]["sha256"] = "0" * 64
    path.write_text(json.dumps(package))
    result = verify_package(REPOSITORY_ROOT, path)
    assert result["verification_status"] == "VERIFICATION_FAILED"
    assert any(error.startswith("SOURCE_ARTIFACT_DIGEST_MISMATCH:") for error in result["errors"])


def test_modified_method_implementation_digest_fails_local_verification(tmp_path: Path) -> None:
    package, path = _temporary_package(tmp_path)
    package["method_candidate"]["source_digests"][0]["sha256"] = "0" * 64
    path.write_text(json.dumps(package))
    result = verify_package(REPOSITORY_ROOT, path)
    assert result["verification_status"] == "VERIFICATION_FAILED"
    assert any(error.startswith("METHOD_ARTIFACT_BINDING_MISMATCH:") for error in result["errors"])


def test_changed_historical_result_cannot_claim_archive_replay(tmp_path: Path) -> None:
    package, path = _temporary_package(tmp_path)
    package["historical_development_run"]["method_result_sha256"] = "f" * 64
    path.write_text(json.dumps(package))
    result = verify_package(REPOSITORY_ROOT, path)
    assert result["verification_status"] == "LOCALLY_VERIFIED"
    assert result["historical_evidence_status"] == "HISTORICAL_VERIFICATION_REFERENCED"
    assert result["independent_archive_replay"]["status"] == "NOT_EXECUTED"
    assert result["independent_archive_replay"]["verified_claim_ids"] == []

    package["historical_development_run"]["method_decision"] = "REJECT"
    path.write_text(json.dumps(package))
    rejected = verify_package(REPOSITORY_ROOT, path)
    assert rejected["verification_status"] == "VERIFICATION_FAILED"
    assert rejected["independent_archive_replay"]["status"] == "NOT_EXECUTED"


def test_changed_historical_timing_remains_referenced_not_newly_measured(
    tmp_path: Path,
) -> None:
    package, path = _temporary_package(tmp_path)
    package["cost_profile"]["samples"][0]["milliseconds"] += 1.0
    path.write_text(json.dumps(package))
    result = verify_package(REPOSITORY_ROOT, path)
    assert result["verification_status"] == "LOCALLY_VERIFIED"
    assert result["historical_timing_status"] == "HISTORICAL_TIMING_OBSERVATION_REFERENCED"
    assert result["independent_archive_replay"]["status"] == "NOT_EXECUTED"
    sample = package["cost_profile"]["samples"][0]
    assert sample["evidence_classification"] == "HISTORICAL_TIMING_OBSERVATION_REFERENCED"
    assert sample["measured_by_current_verifier"] is False


def test_mismatched_historical_archive_digest_fails_replay(tmp_path: Path) -> None:
    archive_path = tmp_path / "wrong-archive.zip"
    archive_path.write_bytes(b"not the pinned historical archive")
    result = verify_package(REPOSITORY_ROOT, historical_archive_path=archive_path)
    replay = result["independent_archive_replay"]
    assert result["verification_status"] == "LOCALLY_VERIFIED"
    assert replay["status"] == "VERIFICATION_FAILED"
    assert replay["errors"] == ["HISTORICAL_ARCHIVE_DIGEST_MISMATCH"]
    assert replay["verified_claim_ids"] == []


def test_unavailable_archive_is_not_reported_as_replayed() -> None:
    package = _package()
    replay = verify_historical_archive(REPOSITORY_ROOT, package, None)
    assert replay["status"] == "NOT_EXECUTED"
    assert replay["observed_archive_sha256"] is None
    assert replay["observed_source_revision_sha"] is None
    assert replay["verified_claim_ids"] == []


def test_semantic_inventory_distinguishes_pair_candidate_from_capability() -> None:
    matrix = _package()["semantic_adequacy"]["matrix"]
    declared = next(
        row
        for row in matrix
        if row["representation_id"] is not None
        and row["declared_mapping_status"] == "ENGINEERING_DECLARATION_ONLY"
    )
    assert classify_semantic_inventory_row(declared) == (
        "PROPOSED_REPRESENTATION_OBLIGATION_PAIR",
        "NOT_COUNTED_PAIR_VALIDITY_UNKNOWN",
    )
    assert declared["pair_validity"] == "UNKNOWN"
    assert is_verified_semantic_coverage(declared) is False

    capability = next(row for row in matrix if row["representation_id"] is None)
    assert classify_semantic_inventory_row(capability) == (
        "EVALUATOR_CAPABILITY_CANDIDATE",
        "NOT_COUNTED_NO_MATERIALIZED_REPRESENTATION",
    )
    assert is_verified_semantic_coverage(capability) is False


def test_undeclared_mapping_is_not_counted_as_verified_coverage() -> None:
    matrix = _package()["semantic_adequacy"]["matrix"]
    undeclared = next(
        row for row in matrix if row["declared_mapping_status"] == "NO_DECLARED_PAIR_MAPPING"
    )
    promoted = copy.deepcopy(undeclared)
    promoted.update(
        pair_validity="VALID",
        independent_review_status="INDEPENDENTLY_REVIEWED",
        evidence_reference="synthetic-test-reference",
    )
    assert classify_semantic_inventory_row(undeclared) == (
        "UNDECLARED_REPRESENTATION_OBLIGATION_MAPPING",
        "NOT_COUNTED_UNDECLARED_MAPPING",
    )
    assert is_verified_semantic_coverage(promoted) is False


def test_duplicate_and_conflicting_semantic_identities_are_rejected() -> None:
    matrix = copy.deepcopy(_package()["semantic_adequacy"]["matrix"])
    duplicate = copy.deepcopy(matrix[0])
    errors, _ = validate_semantic_inventory(matrix + [duplicate])
    assert "SEMANTIC_MATRIX_DUPLICATE_EVALUATOR_OBLIGATION_CELL" in errors
    assert "SEMANTIC_INVENTORY_DUPLICATE_IDENTITY" in errors

    conflicting = copy.deepcopy(matrix[0])
    conflicting["evaluator_id"] = "AC_MODULE_GRAPH"
    conflicting["declared_mapping_status"] = "NO_DECLARED_PAIR_MAPPING"
    conflicting["inventory_class"] = "UNDECLARED_REPRESENTATION_OBLIGATION_MAPPING"
    conflicting["coverage_status"] = "NOT_COUNTED_UNDECLARED_MAPPING"
    errors, _ = validate_semantic_inventory(matrix + [conflicting])
    assert "SEMANTIC_INVENTORY_IDENTITY_CONFLICT" in errors


def test_unknown_pair_is_never_promoted_to_valid() -> None:
    matrix = copy.deepcopy(_package()["semantic_adequacy"]["matrix"])
    matrix[0]["pair_validity"] = "VALID"
    errors, _ = validate_semantic_inventory(matrix)
    assert "UNREVIEWED_PAIR_PROMOTION" in errors


def test_nine_cell_inventory_is_reproducible_and_not_a_denominator() -> None:
    package = _package()
    semantic = package["semantic_adequacy"]
    matrix = semantic["matrix"]
    cells = {(row["evaluator_id"], row["obligation_id"]) for row in matrix}
    assert len(matrix) == 9
    assert len(cells) == 9
    assert all(row["pair_validity"] == "UNKNOWN" for row in matrix)
    assert semantic["inventory_purpose"] == "REVIEW_INVENTORY_NOT_SCORING_DENOMINATOR"
    assert semantic["inventory_counts"] == {
        "proposed_representation_obligation_pairs": 2,
        "undeclared_representation_obligation_mappings": 4,
        "evaluator_capability_candidates": 3,
        "verified_coverage_pairs": 0,
    }


def test_applicability_proposal_keeps_all_unapproved_rows_unknown() -> None:
    profile, ids, catalog_sha, state_sha = _profile()
    result = evaluate_applicability_profile(
        profile,
        catalog_ids=ids,
        catalog_sha256=catalog_sha,
        state_manifest_sha256=state_sha,
        authority_verified=False,
        independent_review_verified=False,
        as_of=date(2026, 10, 27),
    )
    assert result["scoring_authorized"] is False
    assert set(result["classifications"]) == set(ids)
    assert {row["applicability"] for row in result["classifications"].values()} == {"UNKNOWN"}
    assert {row["mandatory_status"] for row in result["classifications"].values()} == {"UNKNOWN"}


def test_fully_reviewed_synthetic_profile_exercises_resolved_path_only() -> None:
    profile, ids, catalog_sha, state_sha = _profile()
    profile["catalog_closure_status"] = "COMPLETE"
    profile["authority_status"] = "NORMATIVELY_AUTHORIZED"
    profile["independent_review_status"] = "INDEPENDENTLY_REVIEWED"
    for index, row in enumerate(profile["rows"]):
        row.update(
            applicability="ACTIVE" if index % 2 == 0 else "INACTIVE",
            mandatory_status="MANDATORY" if index % 2 == 0 else "OPTIONAL",
            lifecycle_status="RESOLVED",
            lifecycle_stages=["CI_TEST"],
            conflict=False,
        )
    result = evaluate_applicability_profile(
        profile,
        catalog_ids=ids,
        catalog_sha256=catalog_sha,
        state_manifest_sha256=state_sha,
        authority_verified=True,
        independent_review_verified=True,
        as_of=date(2026, 10, 27),
    )
    assert result["scoring_authorized"] is True
    assert result["issues"] == []


def test_missing_catalog_row_remains_unknown_and_blocks_denominator() -> None:
    profile, ids, catalog_sha, state_sha = _profile()
    profile["rows"] = profile["rows"][:-1]
    result = evaluate_applicability_profile(
        profile,
        catalog_ids=ids,
        catalog_sha256=catalog_sha,
        state_manifest_sha256=state_sha,
        as_of=date(2026, 10, 27),
    )
    missing_id = ids[-1]
    assert result["classifications"][missing_id]["applicability"] == "UNKNOWN"
    assert "CATALOG_INVENTORY_INCOMPLETE" in result["issues"]
    assert result["scoring_authorized"] is False


def test_conflicting_applicability_facts_remain_unknown() -> None:
    profile, ids, catalog_sha, state_sha = _profile()
    profile["rows"][0].update(applicability="ACTIVE", conflict=True)
    result = evaluate_applicability_profile(
        profile,
        catalog_ids=ids,
        catalog_sha256=catalog_sha,
        state_manifest_sha256=state_sha,
        authority_verified=True,
        independent_review_verified=True,
        as_of=date(2026, 10, 27),
    )
    assert result["classifications"][ids[0]]["applicability"] == "UNKNOWN"
    assert "CONFLICT_UNRESOLVED" in result["issues"]


def test_open_or_incomplete_catalog_cannot_support_active_or_inactive() -> None:
    profile, ids, catalog_sha, state_sha = _profile()
    profile["catalog_closure_status"] = "OPEN"
    profile["rows"][0].update(applicability="ACTIVE", mandatory_status="MANDATORY")
    result = evaluate_applicability_profile(
        profile,
        catalog_ids=ids,
        catalog_sha256=catalog_sha,
        state_manifest_sha256=state_sha,
        authority_verified=True,
        independent_review_verified=True,
        as_of=date(2026, 10, 27),
    )
    assert all(row["applicability"] == "UNKNOWN" for row in result["classifications"].values())
    assert "CATALOG_CLOSURE_UNRESOLVED" in result["issues"]
    assert result["scoring_authorized"] is False


def test_outdated_profile_is_downgraded_to_unknown() -> None:
    profile, ids, catalog_sha, state_sha = _profile()
    profile["valid_until"] = "2026-10-26"
    profile["rows"][0].update(applicability="ACTIVE", mandatory_status="MANDATORY")
    result = evaluate_applicability_profile(
        profile,
        catalog_ids=ids,
        catalog_sha256=catalog_sha,
        state_manifest_sha256=state_sha,
        authority_verified=True,
        independent_review_verified=True,
        as_of=date(2026, 10, 27),
    )
    assert all(row["applicability"] == "UNKNOWN" for row in result["classifications"].values())
    assert "PROFILE_OUTDATED" in result["issues"]


def test_unauthorized_active_claim_cannot_become_applicable() -> None:
    profile, ids, catalog_sha, state_sha = _profile()
    profile["rows"][0].update(applicability="ACTIVE", mandatory_status="MANDATORY")
    result = evaluate_applicability_profile(
        profile,
        catalog_ids=ids,
        catalog_sha256=catalog_sha,
        state_manifest_sha256=state_sha,
        authority_verified=False,
        independent_review_verified=False,
        as_of=date(2026, 10, 27),
    )
    assert result["classifications"][ids[0]]["applicability"] == "UNKNOWN"
    assert result["classifications"][ids[0]]["mandatory_status"] == "UNKNOWN"
    assert "AUTHORITY_UNVERIFIED" in result["issues"]
    assert result["scoring_authorized"] is False
