"""Structural and adversarial checks for the MONO-E1 policy review proposal."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

import pytest
import yaml

from experiments.execution.tooling.mono_policy_review_inventory import (
    DEFAULT_CATALOG,
    DEFAULT_INVENTORY,
    DEFAULT_SCHEMA,
    assess_decision_readiness,
    validate_inventory_object,
)


def _load_inputs() -> tuple[dict[str, Any], dict[str, Any], bytes, dict[str, Any]]:
    inventory = json.loads(DEFAULT_INVENTORY.read_text(encoding="utf-8"))
    catalog_bytes = DEFAULT_CATALOG.read_bytes()
    catalog = yaml.safe_load(catalog_bytes)
    schema = json.loads(DEFAULT_SCHEMA.read_text(encoding="utf-8"))
    return inventory, catalog, catalog_bytes, schema


def _validate(inventory: dict[str, Any]) -> dict[str, Any]:
    _, catalog, catalog_bytes, schema = _load_inputs()
    return validate_inventory_object(inventory, catalog, catalog_bytes, schema)


def _synthetic_supplied_decision() -> dict[str, Any]:
    return {
        "review_roles": {
            "accountable_policy_authority": "TEST_ONLY_ROLE",
            "independent_methods_reviewer": "TEST_ONLY_ROLE",
            "lifecycle_protocol_reviewer": "TEST_ONLY_ROLE",
        },
        "obligations": [
            {
                "obligation_id": "SYNTHETIC_OBLIGATION_A",
                "decision_state": {
                    "applicability": "ACTIVE",
                    "mandatory_status": "MANDATORY",
                    "lifecycle_stage_requirements": {
                        "status": "REQUIRED",
                        "required_stages": ["CI_TEST"],
                        "rationale": "Synthetic fixture only.",
                    },
                    "source_fact_bindings": {
                        "status": "BOUND",
                        "facts": [
                            {
                                "fact_id": "SYNTHETIC_FACT_A",
                                "architecture_state": "SYNTHETIC_STATE",
                                "architecture_source_sha": "a" * 40,
                                "source_locator": "synthetic://source/fact-a",
                                "claim": "Synthetic source fact.",
                                "observation_type": "SYNTHETIC_FIXTURE",
                                "evidence_sha256": "b" * 64,
                                "verification_artifact_sha256": "c" * 64,
                                "status": "VERIFIED",
                                "freshness_status": "CURRENT",
                            }
                        ],
                    },
                    "representation_evidence_requirements": {
                        "status": "DEFINED",
                        "pairs": [
                            {
                                "representation_id": "SYNTHETIC_REPRESENTATION_A",
                                "obligation_id": "SYNTHETIC_OBLIGATION_A",
                                "architecture_state": "SYNTHETIC_STATE",
                                "architecture_source_sha": "a" * 40,
                                "lifecycle_stage": "CI_TEST",
                                "evaluator_id": "SYNTHETIC_EVALUATOR_A",
                                "evaluator_version": "synthetic-v1",
                                "evaluator_source_sha": "b" * 40,
                                "evaluator_tree_sha": "c" * 40,
                                "evaluator_artifact_sha256": "d" * 64,
                                "evaluator_configuration_sha256": "e" * 64,
                                "evidence_scope": "synthetic test scope",
                                "evidence_scope_sha256": "f" * 64,
                                "raw_artifact_sha256s": ["1" * 64],
                                "semantic_assessment_sha256": "2" * 64,
                                "positive_control_sha256": "3" * 64,
                                "negative_control_sha256": "4" * 64,
                                "independent_review_artifact_sha256": "5" * 64,
                                "independent_reviewer_role": "TEST_ONLY_ROLE",
                            }
                        ],
                    },
                },
            }
        ],
    }


def test_current_inventory_is_catalog_complete_but_not_an_approved_denominator() -> None:
    inventory, catalog, catalog_bytes, schema = _load_inputs()

    report = validate_inventory_object(inventory, catalog, catalog_bytes, schema)

    assert report["catalog_inventory_status"] == "COMPLETE_AGAINST_PINNED_CATALOG"
    assert report["catalog_row_count"] == 18
    assert report["result"] == "PASS_CATALOG_INVENTORY_ONLY"
    assert report["scientific_approval"] == "NOT_CERTIFIED"
    assert report["decision_dimensions"]["approved_scientific_denominator"] == "NOT_ESTABLISHED"
    assert report["decision_dimensions"]["policy_authority"] == "UNASSIGNED"
    assert report["decision_dimensions"]["authority_backed_applicability_decisions"] == "INCOMPLETE"
    assert report["decision_dimensions"]["mandatory_status_decisions"] == "INCOMPLETE"
    assert report["decision_dimensions"]["lifecycle_stage_requirements"] == "INCOMPLETE"
    assert report["decision_dimensions"]["source_fact_bindings"] == "INCOMPLETE"
    assert report["decision_dimensions"]["representation_evidence_requirements"] == "INCOMPLETE"


@pytest.mark.parametrize(
    ("mutation", "expected_issue"),
    [
        ("missing", "missing_obligation"),
        ("duplicate", "duplicate_obligation"),
        ("unknown", "unknown_obligation_id"),
        ("catalog_version", "catalog_version_mismatch"),
        ("catalog_digest", "catalog_digest_mismatch"),
    ],
)
def test_catalog_inventory_rejects_incomplete_or_mismatched_inputs(
    mutation: str, expected_issue: str
) -> None:
    inventory, _, _, _ = _load_inputs()
    changed = deepcopy(inventory)
    if mutation == "missing":
        changed["obligations"].pop(0)
    elif mutation == "duplicate":
        changed["obligations"].append(deepcopy(changed["obligations"][0]))
    elif mutation == "unknown":
        changed["obligations"][0]["obligation_id"] = "UNLISTED_TEST_ID"
    elif mutation == "catalog_version":
        changed["catalog_pin"]["schema_version"] += 1
    else:
        changed["catalog_pin"]["sha256"] = "0" * 64

    report = _validate(changed)

    assert report["catalog_inventory_status"] == "INCOMPLETE"
    assert expected_issue in report["issue_codes"]


def test_inventory_rejects_target_level_decisions_in_public_skeleton() -> None:
    inventory, _, _, _ = _load_inputs()
    changed = deepcopy(inventory)
    changed["obligations"][0]["decision_state"]["applicability"] = "ACTIVE"

    report = _validate(changed)

    assert "schema_validation_failed" in report["issue_codes"]
    assert report["scientific_approval"] == "NOT_CERTIFIED"


def test_missing_authority_does_not_back_structurally_supplied_decisions() -> None:
    candidate = _synthetic_supplied_decision()
    del candidate["review_roles"]["accountable_policy_authority"]

    report = assess_decision_readiness(candidate)

    assert report["policy_authority"] == "UNASSIGNED"
    assert report["authority_backed_applicability_decisions"] == "UNVERIFIED_AUTHORITY"
    assert report["mandatory_status_decisions"] == "UNVERIFIED_AUTHORITY"
    assert report["scientific_approval"] == "NOT_CERTIFIED"


def test_unresolved_possibly_mandatory_obligation_stays_incomplete() -> None:
    candidate = _synthetic_supplied_decision()
    candidate["obligations"][0]["decision_state"]["mandatory_status"] = (
        "UNRESOLVED_POSSIBLY_MANDATORY"
    )

    report = assess_decision_readiness(candidate)

    assert report["mandatory_status_decisions"] == "INCOMPLETE"
    assert report["approved_scientific_denominator"] == "NOT_ESTABLISHED"


def test_missing_required_lifecycle_stage_stays_incomplete() -> None:
    candidate = _synthetic_supplied_decision()
    candidate["obligations"][0]["decision_state"]["lifecycle_stage_requirements"][
        "required_stages"
    ] = []

    report = assess_decision_readiness(candidate)

    assert report["lifecycle_stage_requirements"] == "INCOMPLETE"


def test_missing_source_fact_binding_stays_incomplete() -> None:
    candidate = _synthetic_supplied_decision()
    candidate["obligations"][0]["decision_state"]["source_fact_bindings"]["facts"] = []

    report = assess_decision_readiness(candidate)

    assert report["source_fact_bindings"] == "INCOMPLETE"


def test_conflicting_source_fact_bindings_remain_conflicting() -> None:
    candidate = _synthetic_supplied_decision()
    facts = candidate["obligations"][0]["decision_state"]["source_fact_bindings"]["facts"]
    facts.append(
        {
            "fact_id": "SYNTHETIC_FACT_A",
            "architecture_state": "SYNTHETIC_STATE",
            "architecture_source_sha": "a" * 40,
            "source_locator": "synthetic://source/fact-a",
            "claim": "Synthetic source fact.",
            "observation_type": "SYNTHETIC_FIXTURE",
            "evidence_sha256": "9" * 64,
            "verification_artifact_sha256": "c" * 64,
            "status": "VERIFIED",
            "freshness_status": "CURRENT",
        }
    )

    report = assess_decision_readiness(candidate)

    assert report["source_fact_bindings"] == "CONFLICTING"


@pytest.mark.parametrize("fact_status", ["UNKNOWN", "CONFLICTING"])
def test_unknown_or_conflicting_fact_status_never_becomes_verified(fact_status: str) -> None:
    candidate = _synthetic_supplied_decision()
    fact = candidate["obligations"][0]["decision_state"]["source_fact_bindings"]["facts"][0]
    fact["status"] = fact_status

    report = assess_decision_readiness(candidate)

    assert report["source_fact_bindings"] == (
        "CONFLICTING" if fact_status == "CONFLICTING" else "INCOMPLETE"
    )


def test_stale_source_fact_does_not_complete_source_fact_bindings() -> None:
    candidate = _synthetic_supplied_decision()
    fact = candidate["obligations"][0]["decision_state"]["source_fact_bindings"]["facts"][0]
    fact["freshness_status"] = "STALE"

    report = assess_decision_readiness(candidate)

    assert report["source_fact_bindings"] == "INCOMPLETE"


def test_missing_representation_evidence_binding_stays_incomplete() -> None:
    candidate = _synthetic_supplied_decision()
    pair = candidate["obligations"][0]["decision_state"]["representation_evidence_requirements"][
        "pairs"
    ][0]
    del pair["negative_control_sha256"]

    report = assess_decision_readiness(candidate)

    assert report["representation_evidence_requirements"] == "INCOMPLETE"


def test_structural_fields_never_certify_authority_or_scientific_approval() -> None:
    candidate = _synthetic_supplied_decision()

    report = assess_decision_readiness(candidate)

    assert report["policy_authority"] == "SUPPLIED_UNVERIFIED"
    assert report["authority_backed_applicability_decisions"] == "SUPPLIED_UNVERIFIED"
    assert report["source_fact_bindings"] == "SUPPLIED_UNVERIFIED"
    assert report["representation_evidence_requirements"] == "SUPPLIED_UNVERIFIED"
    assert report["approved_scientific_denominator"] == "NOT_ESTABLISHED"
    assert report["scientific_approval"] == "NOT_CERTIFIED"
