"""Contracts for the ΔA5 readiness package; fixtures do not approve policies."""

from __future__ import annotations

import copy
import json
from datetime import date
from pathlib import Path
from typing import Any

import jsonschema  # type: ignore[import-untyped]
import yaml

from experiments.execution.tooling.mono_ci_b0_psi_delta_a5 import (
    PACKAGE_RELATIVE,
    SCHEMA_RELATIVE,
    evaluate_applicability_profile,
    verify_package,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _catalog_ids() -> list[str]:
    catalog_path = REPOSITORY_ROOT / "fitness/catalog/architectural-obligations.yaml"
    catalog = yaml.safe_load(catalog_path.read_text())
    return [str(row["id"]) for row in catalog["obligations"]]


def _profile() -> tuple[dict[str, Any], list[str], str, str]:
    package = json.loads((REPOSITORY_ROOT / PACKAGE_RELATIVE).read_text())
    profile = copy.deepcopy(package["applicability_profile"])
    ids = _catalog_ids()
    return profile, ids, profile["catalog_sha256"], profile["state_manifest_sha256"]


def test_delta_a5_package_schema_and_repository_pins_verify_without_scoring() -> None:
    result = verify_package(REPOSITORY_ROOT)
    assert result["verification_status"] == "PASS"
    assert result["study_readiness"] == "NO_GO_WITH_EXPLICIT_BLOCKERS"
    assert result["catalog_rows"] == 18
    assert result["applicability_scoring_authorized"] is False

    package = json.loads((REPOSITORY_ROOT / PACKAGE_RELATIVE).read_text())
    schema = json.loads((REPOSITORY_ROOT / SCHEMA_RELATIVE).read_text())
    jsonschema.Draft202012Validator(schema).validate(package)
    assert package["readiness"]["p_algorithm_status"] == "NOT_READY"
    assert package["historical_development_run"]["method_decision"] == "HOLD"
    assert package["historical_development_run"]["operation_plan"] == []
    assert package["historical_development_run"]["scoring_status"] == "NOT_EXECUTED"
    assert package["comparison_contract"]["scorer"]["reference_status"] == "NOT_CREATED_OR_APPROVED"
    isolation_status = package["comparison_contract"]["isolation"]["status"]
    assert isolation_status.startswith("HISTORICAL_DEVELOPMENT_ISOLATION_VERIFIED")
    assert package["historical_development_run"]["not_a_comparison"] is True
    assert package["historical_development_run"]["other_arms_or_case_outputs_used"] is False
    assert package["historical_development_run"]["scorer_reference_accessed"] is False
    assert all(row["pair_validity"] == "UNKNOWN" for row in package["semantic_adequacy"]["matrix"])
    assert verify_package(REPOSITORY_ROOT) == result


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
