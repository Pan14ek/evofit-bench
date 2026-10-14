"""Structural tests for the canonical synthetic P input Snapshot v1.1."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, cast

import pytest
from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]

from experiments.execution.tooling.contracts import load_schema
from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.p_input_validation import (
    P_INPUT_SCHEMA_NAME,
    SourceReference,
    ValidationStatus,
    load_fact_vocabulary,
    validate_facts,
    validate_snapshot_schema,
)

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "p_input_contract_v11_snapshot.json"


@pytest.fixture
def valid_snapshot() -> dict[str, Any]:
    """Load the canonical synthetic example, which is not DA01 data."""
    return cast(dict[str, Any], json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))


def test_canonical_schema_is_valid_draft_2020_12() -> None:
    schema = load_schema(P_INPUT_SCHEMA_NAME)
    Draft202012Validator.check_schema(schema)
    assert schema["$id"] == "urn:evofitbench:versioned-architecture-policy-snapshot:v1.1"


def test_canonical_synthetic_snapshot_passes_schema_with_format_checker(
    valid_snapshot: dict[str, Any],
) -> None:
    schema = load_schema(P_INPUT_SCHEMA_NAME)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    assert list(validator.iter_errors(valid_snapshot)) == []
    validate_snapshot_schema(valid_snapshot)


@pytest.mark.parametrize(
    ("path", "key"),
    [
        ((), "scenario_id"),
        (("sources", 0), "future"),
        (("facts", 0), "verified"),
        (("policies", 0), "enforced"),
    ],
)
def test_schema_rejects_additional_properties_at_every_contract_level(
    valid_snapshot: dict[str, Any], path: tuple[str | int, ...], key: str
) -> None:
    payload = copy.deepcopy(valid_snapshot)
    target: Any = payload
    for part in path:
        target = target[part]
    target[key] = "must-not-be-accepted"

    with pytest.raises(ContractValidationError, match="validation failed"):
        validate_snapshot_schema(payload)


def test_unknown_fact_value_must_be_null(valid_snapshot: dict[str, Any]) -> None:
    payload = copy.deepcopy(valid_snapshot)
    payload["facts"][2]["value"] = "none"

    with pytest.raises(ContractValidationError, match=r"/facts/2/value"):
        validate_snapshot_schema(payload)


def test_extracted_fact_requires_method_id(valid_snapshot: dict[str, Any]) -> None:
    payload = copy.deepcopy(valid_snapshot)
    del payload["facts"][1]["method_id"]

    with pytest.raises(ContractValidationError, match=r"/facts/1"):
        validate_snapshot_schema(payload)


def test_observed_fact_requires_observation_window(valid_snapshot: dict[str, Any]) -> None:
    payload = copy.deepcopy(valid_snapshot)
    payload["facts"][1]["epistemic_kind"] = "OBSERVED"
    del payload["facts"][1]["method_id"]

    with pytest.raises(ContractValidationError, match=r"/facts/1"):
        validate_snapshot_schema(payload)


def test_conditional_mandate_requires_condition_reference(
    valid_snapshot: dict[str, Any],
) -> None:
    payload = copy.deepcopy(valid_snapshot)
    payload["policies"][0]["kind"] = "CONDITIONAL_MANDATE"

    with pytest.raises(ContractValidationError, match=r"/policies/0"):
        validate_snapshot_schema(payload)


@pytest.mark.parametrize("kind", ["EXCEPTION", "RETIREMENT"])
def test_exception_and_retirement_require_targets(
    valid_snapshot: dict[str, Any], kind: str
) -> None:
    payload = copy.deepcopy(valid_snapshot)
    payload["policies"][0]["kind"] = kind

    with pytest.raises(ContractValidationError, match=r"/policies/0/target_policy_ids"):
        validate_snapshot_schema(payload)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("architecture", "evaluation_as_of"), "not-a-date"),
        (("sources", 0, "sha256"), "abc"),
    ],
)
def test_invalid_datetime_and_sha_are_rejected(
    valid_snapshot: dict[str, Any], path: tuple[str | int, ...], value: str
) -> None:
    payload = copy.deepcopy(valid_snapshot)
    target: Any = payload
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value

    with pytest.raises(ContractValidationError, match="validation failed"):
        validate_snapshot_schema(payload)


def test_unknown_predicate_is_rejected_by_contract_schema(
    valid_snapshot: dict[str, Any],
) -> None:
    payload = copy.deepcopy(valid_snapshot)
    payload["facts"][0]["predicate"] = "architecture.state_id"

    with pytest.raises(ContractValidationError, match=r"/facts/0/predicate"):
        validate_snapshot_schema(payload)


def _allowed_sources(snapshot: dict[str, Any]) -> dict[str, SourceReference]:
    architecture = snapshot["architecture"]
    return {
        source["id"]: SourceReference(
            source_id=source["id"],
            kind=source["kind"],
            path=source["path"],
            sha256=source["sha256"],
            state="after",
            revision=architecture["after_commit"],
        )
        for source in snapshot["sources"]
    }


def test_fact_vocabulary_has_exactly_twelve_activation_predicates() -> None:
    vocabulary = load_fact_vocabulary()
    names = [item["name"] for item in vocabulary["predicates"]]
    assert len(names) == 12
    assert "architecture.state_id" not in names
    assert "architecture.source_state_id" not in names
    assert "runtime.telemetry_window" not in names


def test_extracted_facts_remain_undetermined_without_an_independent_verifier(
    valid_snapshot: dict[str, Any],
) -> None:
    report = validate_facts(
        valid_snapshot, load_fact_vocabulary(), _allowed_sources(valid_snapshot)
    )

    assert report.status is ValidationStatus.UNDETERMINED
    assert report.reason_codes == ("EXTRACTED_FACT_UNVERIFIED",)
    assert "ARCH_OBS" in report.evidence_refs


def test_unknown_fact_does_not_create_evidence(valid_snapshot: dict[str, Any]) -> None:
    payload = copy.deepcopy(valid_snapshot)
    payload["facts"] = [payload["facts"][2]]
    report = validate_facts(payload, load_fact_vocabulary(), _allowed_sources(payload))

    assert report.status is ValidationStatus.VALID
    assert report.evidence_refs == ()


def test_extracted_fact_requires_matching_source_and_method(
    valid_snapshot: dict[str, Any],
) -> None:
    payload = copy.deepcopy(valid_snapshot)
    payload["facts"][1]["method_id"] = "unreviewed-method"
    report = validate_facts(payload, load_fact_vocabulary(), _allowed_sources(payload))

    assert report.status is ValidationStatus.INVALID
    assert "FACT_METHOD_INVALID" in report.reason_codes


def test_independent_extraction_verifier_can_confirm_synthetic_fact(
    valid_snapshot: dict[str, Any],
) -> None:
    payload = copy.deepcopy(valid_snapshot)
    report = validate_facts(
        payload,
        load_fact_vocabulary(),
        _allowed_sources(payload),
        fact_verifier=lambda _fact, _sources, _snapshot: True,
    )

    assert report.status is ValidationStatus.VALID


@pytest.mark.parametrize(
    ("predicate", "value"),
    [
        ("deployment.unit_count_declared", True),
        ("deployment.unit_count_declared", -1),
        ("component.python_module_identity", ["app.beta", "app.alpha"]),
        ("component.python_module_identity", ["app.alpha", "app.alpha"]),
        (
            "component.declared_cross_module_dependency",
            {"from": "app.a", "to": "app.b", "rationale": "secret"},
        ),
    ],
)
def test_fact_value_types_are_strict(
    valid_snapshot: dict[str, Any], predicate: str, value: Any
) -> None:
    payload = copy.deepcopy(valid_snapshot)
    target = next((item for item in payload["facts"] if item["predicate"] == predicate), None)
    if target is None:
        target = {
            "id": "F_ADDED",
            "state": "after",
            "predicate": predicate,
            "subject": "app.modules.a",
            "scope": "application",
            "value": value,
            "epistemic_kind": "DECLARED",
            "source_ids": ["ARCH_OBS"],
        }
        payload["facts"].append(target)
    target["value"] = value
    report = validate_facts(payload, load_fact_vocabulary(), _allowed_sources(payload))

    assert report.status is ValidationStatus.INVALID
    assert "FACT_TYPE_MISMATCH" in report.reason_codes


@pytest.mark.parametrize(
    "predicate",
    ["architecture.state_id", "architecture.source_state_id", "runtime.telemetry_window"],
)
def test_provenance_and_reserved_names_are_not_fact_predicates(
    valid_snapshot: dict[str, Any], predicate: str
) -> None:
    payload = copy.deepcopy(valid_snapshot)
    payload["facts"][0]["predicate"] = predicate
    report = validate_facts(payload, load_fact_vocabulary(), _allowed_sources(payload))

    assert report.status is ValidationStatus.INVALID
    assert "UNKNOWN_PREDICATE" in report.reason_codes


def test_fact_scope_source_role_and_pinned_revision_are_checked(
    valid_snapshot: dict[str, Any],
) -> None:
    payload = copy.deepcopy(valid_snapshot)
    payload["facts"][0]["scope"] = "runtime"
    allowed_sources = _allowed_sources(payload)
    allowed_sources["ARCH_OBS"] = SourceReference(
        source_id="ARCH_OBS",
        kind="POLICY_REGISTRY",
        path="policies/registry.json",
        sha256="3" * 64,
        state="before",
        revision=payload["architecture"]["before_commit"],
    )
    report = validate_facts(payload, load_fact_vocabulary(), allowed_sources)

    assert report.status is ValidationStatus.INVALID
    assert {"FACT_SCOPE_INVALID", "SOURCE_NOT_ALLOWLISTED", "VERSION_MISMATCH"}.issubset(
        report.reason_codes
    )
