"""Contract and evidence checks for the proposed MONO-E1 A0.3 fitness config."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from experiments.execution.tooling.mono_e1_a03_fitness_config import (
    FitnessConfigurationValidationError,
    validate_document,
    validate_evidence_bindings,
    validate_project,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "fitness/configs/mono-e1-b0-dev-a03-v1.yaml"
SCHEMA_PATH = ROOT / "fitness/configs/mono-e1-b0-dev-a03-v1.schema.json"


def _load_config() -> dict[str, Any]:
    return cast(dict[str, Any], yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")))


def _load_schema() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def test_configuration_schema_source_provenance_and_frozen_a0_bytes_validate() -> None:
    result = validate_project(ROOT)

    assert result["schema_status"] == "PASS"
    assert result["historical_a0_b0_bytes"] == "PRESERVED"
    assert result["canonical_source_and_checkpoint_provenance"] == "PASS"
    assert (
        result["configuration_sha256"]
        == CONFIG_PATH.with_suffix(".yaml.sha256").read_text(encoding="utf-8").split()[0]
    )

    config = _load_config()
    assert config["provenance"]["historical_a03_parent_configuration_status"] == "NOT_IDENTIFIED"
    assert config["baseline"]["id"] == "B0_DEV_A03"
    assert config["baseline"]["semantics"] == "UNCHANGED_PROPOSED_A0_3_CONFIGURATION"
    assert config["baseline"]["retain_interpretation"].startswith("NOT_EVALUABLE")


def test_representation_ids_are_unique_and_separate_from_evaluator_ids() -> None:
    config = _load_config()
    validate_document(config, _load_schema())

    duplicate = copy.deepcopy(config)
    duplicate["representations"][1]["id"] = duplicate["representations"][0]["id"]
    with pytest.raises(FitnessConfigurationValidationError, match="identities must be unique"):
        validate_document(duplicate, _load_schema())

    collision = copy.deepcopy(config)
    collision["representations"][0]["evaluator"]["id"] = collision["representations"][0]["id"]
    with pytest.raises(FitnessConfigurationValidationError):
        validate_document(collision, _load_schema())


def test_existing_evaluator_archives_contain_positive_and_negative_controls() -> None:
    result = validate_project(ROOT)

    eval01 = result["evaluator_control_evidence"]["EVAL-01"]
    eval02 = result["evaluator_control_evidence"]["EVAL-02"]
    for summary in (eval01, eval02):
        assert summary["calls_completed"] > 0
        for matrix in summary["confusion_matrices"].values():
            assert matrix["tp"] > 0
            assert matrix["tn"] > 0
            assert matrix["fp"] == 0
            assert matrix["fn"] == 0

    assert eval01["diagnostic_mismatches"] == 0
    assert eval02["diagnostic_mismatches"] == 3


def test_missing_or_contradictory_source_evidence_is_rejected() -> None:
    missing = _load_config()
    missing["representations"][0]["evidence_by_state"][0]["observation"]["path"] = (
        "architecture/acceptance/a1/missing-observation.json"
    )
    with pytest.raises(FitnessConfigurationValidationError, match="Missing evidence artifact"):
        validate_evidence_bindings(ROOT, missing)

    contradictory = _load_config()
    contradictory["representations"][0]["evidence_by_state"][0]["compliance"] = "NON_COMPLIANT"
    with pytest.raises(FitnessConfigurationValidationError, match="Checkpoint record contradicts"):
        validate_evidence_bindings(ROOT, contradictory)


def test_incorrect_evaluator_binding_is_rejected() -> None:
    config = _load_config()
    config["representations"][0]["evaluator"]["id"] = "AC_MODULE_GRAPH"

    with pytest.raises(FitnessConfigurationValidationError):
        validate_evidence_bindings(ROOT, config)


def test_unknown_semantic_validity_and_open_scientific_gates_cannot_be_promoted() -> None:
    result = validate_project(ROOT)
    config = _load_config()

    assert result["semantic_fitness_validity"] == "UNKNOWN"
    assert result["method_input_component_status"] == "PROPOSED_COMPONENT_ONLY"
    assert result["complete_method_input_bundle"] is False
    assert result["method_p_execution_authorized"] is False
    assert result["P_ALGORITHM_STATUS"] == "NOT_READY"
    assert result["G1"] == "INCOMPLETE"
    assert result["G4"] == "NOT_AUTHORIZED"
    assert result["MONO_E1"] == "NO_GO"

    promoted = copy.deepcopy(config)
    promoted["representations"][0]["semantic_validity_status"] = "VALID"
    with pytest.raises(FitnessConfigurationValidationError):
        validate_document(promoted, _load_schema())

    promoted = copy.deepcopy(config)
    promoted["authorization"]["scientific_approval"] = True
    with pytest.raises(FitnessConfigurationValidationError):
        validate_document(promoted, _load_schema())

    promoted = copy.deepcopy(config)
    promoted["baseline"]["official_mono_e1_baseline_authorized"] = True
    with pytest.raises(FitnessConfigurationValidationError):
        validate_document(promoted, _load_schema())
