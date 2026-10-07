"""Validate the pre-registered research schema foundation without running experiments."""

import json
import re
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
DESIGN_PATH = ROOT / "experiments/design/ARCHITECTURE_EVOLUTION_SCENARIOS_V1.md"


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


def test_traceability_obligations_resolve_to_design_and_covered_representations() -> None:
    """Ensure each A0 obligation in the graph exists and has current representation coverage."""
    catalog = load_yaml(REPRESENTATIONS_PATH)
    traceability = load_yaml(TRACEABILITY_PATH)
    design = DESIGN_PATH.read_text(encoding="utf-8")
    design_obligations = set(re.findall(r"\| `([A-Z][A-Z0-9_]+)` \|", design))
    representation_ids = {item["id"] for item in catalog["representations"]}
    covered = {obligation for item in catalog["representations"] for obligation in item["covers"]}
    element_ids = [item["id"] for item in traceability["elements"]]
    assert len(element_ids) == len(set(element_ids))
    for element in traceability["elements"]:
        assert element["representations"]
        for obligation in element["obligations"]:
            assert obligation in design_obligations
            assert obligation in covered
        for representation in element["representations"]:
            assert representation["id"] in representation_ids
    for obligation in covered:
        assert any(obligation in element["obligations"] for element in traceability["elements"])


def test_da01_rq1_universe_and_frozen_ground_truth_are_exact() -> None:
    """Lock the classification unit, positive targets, operations, and criterion context."""
    ground_truth = load_yaml(GROUND_TRUTH_PATH)
    catalog = load_yaml(REPRESENTATIONS_PATH)
    expected_representations = [item["id"] for item in catalog["representations"]]
    universe = ground_truth["classification_universe"]
    assert universe["existing_representations"] == expected_representations
    assert universe["new_obligations"] == ["AC_MODULE_STRUCTURE"]

    target_ids = [item["target_id"] for item in ground_truth["affected_targets"]]
    assert len(target_ids) == len(set(target_ids))
    assert set(target_ids) == {"REP_A0_ARCH_CI_LAYERING", "AC_MODULE_STRUCTURE"}
    operations = {
        item["target_id"]: item["expected_operation"] for item in ground_truth["affected_targets"]
    }
    assert operations == {
        "REP_A0_ARCH_CI_LAYERING": "replace",
        "AC_MODULE_STRUCTURE": "add",
    }
    assert ground_truth["expected_operations"] == operations
    assert ground_truth["criteria_assessment"] == {
        "performance": {"affected": False},
        "reliability": {"affected": False},
        "architecture_compliance": {"affected": True},
    }
    assert ground_truth["frozen_before_implementation"] is True
    assert set(ground_truth["retained_representations"]) == set(expected_representations) - {
        "REP_A0_ARCH_CI_LAYERING"
    }
