"""A0.5 transition adapter identity and noncontamination contracts."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema  # type: ignore[import-untyped]
import yaml

from experiments.execution.tooling.mono_ci_psi_a05 import (
    AFTER_STATE,
    BASELINE_ID,
    BEFORE_COMMIT,
    BEFORE_STATE,
    PROBE_PATH,
    PROBE_SOURCE,
    _candidate_obligation_coverage,
    _validate_a04_proposal,
)
from experiments.execution.tooling.mono_ci_psi_coverage import (
    _REQUIREMENT_CAPABILITY_MAPPINGS,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_a05_baseline_is_an_a04_two_control_reconstruction() -> None:
    binding = _validate_a04_proposal(REPOSITORY_ROOT)
    proposal = json.loads(
        (
            REPOSITORY_ROOT
            / "experiments/execution/mono-ci-b0-psi-execution-a05-v1/RECONSTRUCTED_B0_A04_V1.json"
        ).read_text(encoding="utf-8")
    )
    schema_path = (
        REPOSITORY_ROOT
        / "experiments/execution/schemas"
        / "mono_ci_b0_psi_reconstructed_baseline_a04_v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(proposal)
    assert proposal["configuration_id"] == BASELINE_ID
    assert proposal["architecture_state"] == BEFORE_STATE
    assert proposal["target_state"] == AFTER_STATE
    assert proposal["historical_identity"] == "NOT_FOUND"
    assert {row["evaluator_id"] for row in proposal["representations"]} == {
        "AC_PUBLIC_API",
        "AC_MODULE_GRAPH",
    }
    assert "AC_DATA_OWNERSHIP" not in {row["evaluator_id"] for row in proposal["representations"]}
    assert proposal["authorization"]["study_readiness"] == "NO_GO"
    assert binding["identity_status"] == "PROSPECTIVE_RECONSTRUCTION_NOT_HISTORICAL"
    assert binding["approval_status"] == "NOT_APPROVED"


def test_a05_adapter_pins_canonical_a04_and_declares_an_unapproved_policy() -> None:
    manifest = yaml.safe_load(
        (REPOSITORY_ROOT / "architecture/states/A0_5_MODULE_DATA_OWNERSHIP.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert BEFORE_COMMIT == "d3101c0d3aa9b7b709253b6ec7518416f05f65b9"
    assert manifest["predecessor_state"] == BEFORE_STATE
    assert manifest["source_provenance"]["predecessor_commit"] == BEFORE_COMMIT
    assert manifest["authority_status"] == (
        "DECLARED_ENGINEERING_REQUIREMENT_NOT_INDEPENDENTLY_APPROVED"
    )
    assert manifest["evaluator_applicability"]["required_evaluators"] == [
        "AC_PUBLIC_API",
        "AC_MODULE_GRAPH",
        "AC_DATA_OWNERSHIP",
    ]
    mapping = _REQUIREMENT_CAPABILITY_MAPPINGS["architecture.data_ownership.persistence_ownership"]
    assert mapping["capability_type"] == "evaluator.data_ownership.table_and_access_policy"
    assert mapping["mapping_id"] == "MAP-PERSISTENCE-OWNERSHIP-TO-A1-DATA-OWNERSHIP-V1"


def test_negative_probe_is_isolated_and_uses_a_static_table_access_the_evaluator_inspects() -> None:
    assert PROBE_PATH == "app/modules/tasks/repository.py"
    assert 'Table("notifications", MetaData(), autoload_with=session.bind)' in PROBE_SOURCE
    assert "session.execute(select(foreign_table))" in PROBE_SOURCE
    assert "expected_operations" not in PROBE_SOURCE
    assert "ground_truth" not in PROBE_SOURCE


def test_materialized_candidate_coverage_is_derived_from_its_active_rows() -> None:
    candidate_rows = [
        {
            "id": "REP_RECON_B0_A04_MODULE_GRAPH_CI_V1",
            "active": True,
            "covers": ["AC_MODULE_GRAPH"],
        },
        {
            "id": "REP_INACTIVE_OWNERSHIP",
            "active": False,
            "covers": ["AC_DATA_OWNERSHIP"],
        },
    ]

    assert _candidate_obligation_coverage(candidate_rows, "AC_DATA_OWNERSHIP") == []

    candidate_rows.append(
        {
            "id": "REP_CANDIDATE_OWNERSHIP",
            "active": True,
            "covers": ["AC_DATA_OWNERSHIP"],
        }
    )
    assert _candidate_obligation_coverage(candidate_rows, "AC_DATA_OWNERSHIP") == [
        "REP_CANDIDATE_OWNERSHIP"
    ]
