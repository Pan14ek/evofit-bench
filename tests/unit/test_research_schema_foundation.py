"""Validate the pre-registered research schema foundation without running experiments."""

import json
from collections import Counter
from pathlib import Path
from typing import Any, cast

import yaml
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "experiments/schemas"
SCENARIO_PATH = ROOT / "experiments/scenarios/DA01/scenario.yaml"
GROUND_TRUTH_PATH = ROOT / "experiments/scenarios/DA01/ground_truth.yaml"
REPRESENTATIONS_PATH = ROOT / "fitness/catalog/a0-fitness-elements.yaml"
TRACEABILITY_PATH = ROOT / "fitness/traceability/a0-traceability.yaml"
OBLIGATIONS_PATH = ROOT / "fitness/catalog/architectural-obligations.yaml"


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a repository YAML artifact as a mapping."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return cast(dict[str, Any], data)


def load_schema(name: str) -> dict[str, Any]:
    """Load and check a JSON Schema document."""
    schema = cast(dict[str, Any], json.loads((SCHEMAS / name).read_text(encoding="utf-8")))
    Draft202012Validator.check_schema(schema)
    return schema


def test_da01_scenario_and_ground_truth_validate_against_json_schemas() -> None:
    """Validate the registered DA01 YAML documents against their JSON contracts."""
    Draft202012Validator(load_schema("scenario.schema.json")).validate(load_yaml(SCENARIO_PATH))
    Draft202012Validator(load_schema("ground_truth.schema.json")).validate(
        load_yaml(GROUND_TRUTH_PATH)
    )


def test_result_schema_supports_future_methods_and_rq1_target_operations() -> None:
    """Accept B0/B1/P result shapes and reject operations invalid for target types."""
    schema = load_schema("result.schema.json")
    validator = Draft202012Validator(schema)
    result: dict[str, Any] = {
        "scenario_id": "DA01",
        "method": "B0",
        "source_revision": "b78b0967be937634b7762baccf5ac6892b279a73",
        "predicted_affected": [],
        "applied_operations": [],
        "coverage_before": 0.0,
        "coverage_after": 0.0,
        "semantic_violations_before": 0,
        "semantic_violations_after": 0,
        "adaptation_time_ms": 0,
        "fitness_validation_time_ms": 0,
        "ci_time_ms": 0,
        "active_signal_count": 0,
        "runtime_overhead": {},
        "fault_runs": [],
    }
    for method in ("B0", "B1", "P"):
        result["method"] = method
        validator.validate(result)

    for target_type, target_id, operation in (
        ("representation", "REP_A0_PERF_TEST_HTTP_P95", "retain"),
        ("representation", "REP_A0_ARCH_CI_LAYERING", "replace"),
        ("representation", "REP_A0_PERF_TEST_HTTP_P95", "deactivate"),
        ("representation", "REP_A0_PERF_TEST_HTTP_P95", "adjust"),
        ("obligation", "AC_MODULE_STRUCTURE", "add"),
    ):
        result["applied_operations"] = [
            {"target_type": target_type, "target_id": target_id, "operation": operation}
        ]
        validator.validate(result)

    invalid_obligation_operation = {
        **result,
        "applied_operations": [
            {
                "target_type": "obligation",
                "target_id": "AC_MODULE_STRUCTURE",
                "operation": "replace",
            }
        ],
    }
    assert not validator.is_valid(invalid_obligation_operation)


def test_a0_catalog_representation_ids_are_unique_and_match_frozen_configuration() -> None:
    """Keep the stable representation catalog aligned with the unchanged A0 config."""
    catalog = load_yaml(REPRESENTATIONS_PATH)
    ids = [entry["id"] for entry in catalog["representations"]]
    assert len(ids) == len(set(ids))
    assert ids == [
        "REP_A0_PERF_TEST_HTTP_P95",
        "REP_A0_PERF_RUNTIME_HTTP_DURATION",
        "REP_A0_REL_TEST_INTEGRATION",
        "REP_A0_REL_RUNTIME_FAILURES",
        "REP_A0_ARCH_CI_LAYERING",
    ]
    configuration = load_yaml(ROOT / "fitness/configs/a0-monolith.yaml")
    observed = [
        (item["criterion"], item["stage"], item["evaluator"], item["metrics"])
        for item in configuration["representations"]
    ]
    declared = [
        (item["criterion"], item["stage"], item["evaluator"], item["metrics"])
        for item in catalog["representations"]
    ]
    assert declared == observed
    assert catalog["provenance"]["source_configuration_sha256"] == (
        "5ad60e373463ea459e192bf85d82704ca9aa1c217c4abf4d8caeb66924059ecb"
    )


def test_obligation_registry_contains_complete_design_universe() -> None:
    """Keep every design obligation in the canonical machine-readable registry."""
    registry = load_yaml(OBLIGATIONS_PATH)
    entries = registry["obligations"]
    ids = [item["id"] for item in entries]
    assert registry["schema_version"] == 1
    assert len(ids) == len(set(ids))
    assert set(ids) == {
        "P_EXT_LATENCY",
        "P_REMOTE_LATENCY",
        "P_ASYNC_LAG",
        "R_BUSINESS_FAILURE",
        "R_HTTP_5XX",
        "R_LOCAL_ATOMICITY",
        "R_REMOTE_DEPENDENCY",
        "R_EVENT_DELIVERY",
        "R_IDEMPOTENCY",
        "R_READMODEL_CONVERGENCE",
        "AC_LAYERING",
        "AC_MODULE_STRUCTURE",
        "AC_PUBLIC_API",
        "AC_MODULE_GRAPH",
        "AC_DATA_OWNERSHIP",
        "AC_SERVICE_BOUNDARY",
        "AC_COMMUNICATION_POLICY",
        "AC_DEPLOYMENT_TOPOLOGY",
    }
    for item in entries:
        assert item["criterion"] in {"performance", "reliability", "architecture_compliance"}
        assert item["intent"].strip()
        assert item["default_weight"] == 1.0


def test_traceability_obligations_resolve_to_registry_and_covered_representations() -> None:
    """Resolve the A0 graph against stable registry and representation IDs."""
    catalog = load_yaml(REPRESENTATIONS_PATH)
    traceability = load_yaml(TRACEABILITY_PATH)
    registry = load_yaml(OBLIGATIONS_PATH)
    obligation_ids = {item["id"] for item in registry["obligations"]}
    representation_ids = {item["id"] for item in catalog["representations"]}
    covered = {obligation for item in catalog["representations"] for obligation in item["covers"]}
    element_ids = [item["id"] for item in traceability["elements"]]
    assert len(element_ids) == len(set(element_ids))
    for element in traceability["elements"]:
        assert element["representations"]
        for obligation in element["obligations"]:
            assert obligation in obligation_ids
            assert obligation in covered
        for representation in element["representations"]:
            assert representation["id"] in representation_ids
    for obligation in covered:
        assert any(obligation in element["obligations"] for element in traceability["elements"])


def test_ground_truth_schema_enforces_preregistration_freeze() -> None:
    """Reject registered ground truth that is not frozen before implementation."""
    schema = load_schema("ground_truth.schema.json")
    assert schema["properties"]["frozen_before_implementation"] == {
        "const": True,
        "description": "Registered ground truth must be frozen before implementation.",
    }
    ground_truth = load_yaml(GROUND_TRUTH_PATH)
    ground_truth["frozen_before_implementation"] = False
    validator = Draft202012Validator(schema)
    assert not validator.is_valid(ground_truth)


def test_da01_cross_artifact_obligations_and_classification_are_consistent() -> None:
    """Lock DA01's full obligation set and total RQ1 operation mapping."""
    scenario = load_yaml(SCENARIO_PATH)
    ground_truth = load_yaml(GROUND_TRUTH_PATH)
    catalog = load_yaml(REPRESENTATIONS_PATH)
    traceability = load_yaml(TRACEABILITY_PATH)
    registry = load_yaml(OBLIGATIONS_PATH)
    expected_representations = [item["id"] for item in catalog["representations"]]
    universe = ground_truth["classification_universe"]

    expected_after = [
        "P_EXT_LATENCY",
        "R_BUSINESS_FAILURE",
        "R_HTTP_5XX",
        "R_LOCAL_ATOMICITY",
        "AC_LAYERING",
        "AC_MODULE_STRUCTURE",
    ]
    assert scenario["required_obligations_after"] == expected_after
    assert ground_truth["required_obligations_after"] == expected_after
    assert scenario["required_obligations_after"] == ground_truth["required_obligations_after"]
    assert scenario["new_obligations"] == ["AC_MODULE_STRUCTURE"]
    assert set(scenario["new_obligations"]).issubset(set(expected_after))
    assert set(universe["new_obligations"]).issubset(
        set(ground_truth["required_obligations_after"])
    )
    assert len(expected_after) == 6

    assert universe["existing_representations"] == expected_representations
    assert universe["new_obligations"] == ["AC_MODULE_STRUCTURE"]
    assert len(universe["existing_representations"]) == 5
    assert len(universe["new_obligations"]) == 1
    classification_universe = set(universe["existing_representations"]) | set(
        universe["new_obligations"]
    )

    expected_operations = {
        "REP_A0_PERF_TEST_HTTP_P95": "retain",
        "REP_A0_PERF_RUNTIME_HTTP_DURATION": "retain",
        "REP_A0_REL_TEST_INTEGRATION": "retain",
        "REP_A0_REL_RUNTIME_FAILURES": "retain",
        "REP_A0_ARCH_CI_LAYERING": "replace",
        "AC_MODULE_STRUCTURE": "add",
    }
    operations = ground_truth["expected_operations"]
    assert len(classification_universe) == 6
    assert set(operations) == classification_universe
    assert operations == expected_operations
    assert Counter(operations.values()) == Counter(
        {
            "retain": 4,
            "replace": 1,
            "add": 1,
        }
    )
    assert "deactivate" not in operations.values()
    assert "adjust" not in operations.values()

    target_ids = [item["target_id"] for item in ground_truth["affected_targets"]]
    assert len(target_ids) == len(set(target_ids))
    non_retain = {target_id for target_id, operation in operations.items() if operation != "retain"}
    assert (
        set(target_ids)
        == non_retain
        == {
            "REP_A0_ARCH_CI_LAYERING",
            "AC_MODULE_STRUCTURE",
        }
    )
    assert {
        item["target_id"]: item["expected_operation"] for item in ground_truth["affected_targets"]
    } == {target_id: operations[target_id] for target_id in non_retain}
    assert all(operations[target_id] != "retain" for target_id in target_ids)

    retained_representations = [
        representation_id
        for representation_id in universe["existing_representations"]
        if operations[representation_id] == "retain"
    ]
    assert ground_truth["retained_representations"] == retained_representations

    assert ground_truth["criteria_assessment"] == {
        "performance": {"affected": False},
        "reliability": {"affected": False},
        "architecture_compliance": {"affected": True},
    }
    assert ground_truth["frozen_before_implementation"] is True

    obligation_ids = {item["id"] for item in registry["obligations"]}
    referenced_obligations = set(scenario["required_obligations_after"])
    referenced_obligations.update(scenario["new_obligations"])
    referenced_obligations.update(ground_truth["required_obligations_after"])
    referenced_obligations.update(universe["new_obligations"])
    referenced_obligations.update(
        item["target_id"]
        for item in ground_truth["affected_targets"]
        if item["target_type"] == "obligation"
    )
    referenced_obligations.update(
        obligation
        for representation in catalog["representations"]
        for obligation in representation["covers"]
    )
    referenced_obligations.update(
        obligation for element in traceability["elements"] for obligation in element["obligations"]
    )
    assert referenced_obligations <= obligation_ids

    representation_ids = {item["id"] for item in catalog["representations"]}
    assert set(universe["existing_representations"]) <= representation_ids
    assert all(
        item["target_id"] in representation_ids
        for item in ground_truth["affected_targets"]
        if item["target_type"] == "representation"
    )

    frozen_a0_obligations = set(expected_after) - set(scenario["new_obligations"])
    assert frozen_a0_obligations == {
        "P_EXT_LATENCY",
        "R_BUSINESS_FAILURE",
        "R_HTTP_5XX",
        "R_LOCAL_ATOMICITY",
        "AC_LAYERING",
    }
    coverage_by_obligation = {
        obligation: {
            item["id"] for item in catalog["representations"] if obligation in item["covers"]
        }
        for obligation in frozen_a0_obligations
    }
    assert all(coverage_by_obligation.values())
    assert coverage_by_obligation == {
        "P_EXT_LATENCY": {
            "REP_A0_PERF_TEST_HTTP_P95",
            "REP_A0_PERF_RUNTIME_HTTP_DURATION",
        },
        "R_BUSINESS_FAILURE": {"REP_A0_REL_RUNTIME_FAILURES"},
        "R_HTTP_5XX": {"REP_A0_REL_RUNTIME_FAILURES"},
        "R_LOCAL_ATOMICITY": {"REP_A0_REL_TEST_INTEGRATION"},
        "AC_LAYERING": {"REP_A0_ARCH_CI_LAYERING"},
    }
