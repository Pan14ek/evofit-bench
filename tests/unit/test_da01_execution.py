"""Synthetic protocol, sealing, scoring, and semantic-validity tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, cast

import pytest

import experiments.execution.tooling.scoring as scoring
from experiments.execution.tooling.b0 import (
    build_b0_candidate,
    build_b0_prediction,
    copy_frozen_configuration,
)
from experiments.execution.tooling.b1 import operator_readiness
from experiments.execution.tooling.contracts import (
    SCHEMA_DIR,
    load_schema,
    validate_candidate,
    validate_legacy_result,
    validate_payload,
    validate_prediction,
)
from experiments.execution.tooling.errors import (
    ContractValidationError,
    MethodNotReadyError,
    ProtocolError,
    SealedArtifactError,
)
from experiments.execution.tooling.hashing import sha256_bytes, sha256_file
from experiments.execution.tooling.p_interface import require_p_algorithm
from experiments.execution.tooling.scoring import (
    build_scored_result,
    record_private_ground_truth_hash,
    score_rq1,
    score_rq2,
    score_sealed_prediction,
)
from experiments.execution.tooling.sealing import load_verified_prediction, seal_prediction
from experiments.execution.tooling.validity import (
    assess_obligation,
    assess_representation,
    inspect_import_linter_scope,
    validate_layer_edges,
    validate_module_structure,
    verify_evidence_artifacts,
)

ARCH_SHA = "a" * 40
OTHER_ARCH_SHA = "b" * 40
BUNDLE_SHA = "c" * 64
EVIDENCE_SHA = "d" * 64


def _prediction(
    *,
    method_id: str = "B1",
    affected: list[dict[str, str]] | None = None,
    operations: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "method_id": method_id,
        "architecture_source_sha": ARCH_SHA,
        "method_version": "synthetic-v1",
        "input_bundle_sha256": BUNDLE_SHA,
        "predicted_affected": affected or [],
        "proposed_operations": operations or [],
        "explanations": [],
        "artifact_hashes": {},
    }


def _synthetic_oracle() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "scenario_id": "DA99",
        "frozen_before_implementation": True,
        "source_architecture_tag": "synthetic-source",
        "source_architecture_revision": OTHER_ARCH_SHA,
        "criteria_assessment": {"architecture_compliance": {"affected": True}},
        "classification_universe": {
            "existing_representations": [
                "REP_RETAIN",
                "REP_REPLACE",
                "REP_DEACTIVATE",
                "REP_ADJUST",
            ],
            "new_obligations": ["AC_NEW"],
        },
        "expected_operations": {
            "REP_RETAIN": "retain",
            "REP_REPLACE": "replace",
            "REP_DEACTIVATE": "deactivate",
            "REP_ADJUST": "adjust",
            "AC_NEW": "add",
        },
        "affected_targets": [
            {
                "target_type": "representation",
                "target_id": "REP_REPLACE",
                "expected_operation": "replace",
                "rationale": "Synthetic representation change.",
            },
            {
                "target_type": "representation",
                "target_id": "REP_DEACTIVATE",
                "expected_operation": "deactivate",
                "rationale": "Synthetic representation change.",
            },
            {
                "target_type": "representation",
                "target_id": "REP_ADJUST",
                "expected_operation": "adjust",
                "rationale": "Synthetic representation change.",
            },
            {
                "target_type": "obligation",
                "target_id": "AC_NEW",
                "expected_operation": "add",
                "rationale": "Synthetic obligation.",
            },
        ],
        "required_obligations_after": ["Q_ONE", "Q_TWO", "Q_THREE"],
        "retained_representations": ["REP_RETAIN"],
        "seeded_faults": [],
        "prohibited_unplanned_changes": [],
    }


def _valid_evidence(
    representation_id: str = "REP_VALID",
    *,
    architecture_sha: str = ARCH_SHA,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "representation_id": representation_id,
        "architecture_source_sha": architecture_sha,
        "evaluator_id": "architecture_checker",
        "infrastructure_status": "completed",
        "process_exit_code": 0,
        "configured_targets": ["package.layer"],
        "resolved_targets": ["package.layer"],
        "inspected_subjects": ["package.layer.api", "package.layer.service"],
        "missing_targets": [],
        "inspected_edge_count": 2,
        "stage_applicable": True,
        "semantic_compatible": True,
        "mapping_resolved": True,
        "evidence_contract_satisfied": True,
        "adequacy_proven": True,
        "clean_probe": "pass",
        "fault_probe": "detected",
        "evidence_artifacts": [{"path": "logs/evaluator.txt", "sha256": EVIDENCE_SHA}],
        "stdout_sha256": EVIDENCE_SHA,
        "stderr_sha256": EVIDENCE_SHA,
    }


def _verdict(representation_id: str, status: str = "VALID_APPLICABLE") -> dict[str, Any]:
    return {
        "schema_version": 1,
        "representation_id": representation_id,
        "architecture_source_sha": ARCH_SHA,
        "status": status,
        "reason_codes": [] if status == "VALID_APPLICABLE" else [status],
        "active": True,
        "mapping_resolved": status == "VALID_APPLICABLE",
        "stage_applicable": status == "VALID_APPLICABLE",
        "semantic_compatible": status == "VALID_APPLICABLE",
        "executable_nonvacuous": status == "VALID_APPLICABLE",
        "evidence_contract_satisfied": status == "VALID_APPLICABLE",
        "evidence_refs": ["logs/synthetic.txt"] if status == "VALID_APPLICABLE" else [],
    }


def _synthetic_known_targets(
    *extra_targets: tuple[Literal["representation", "obligation"], str],
) -> set[tuple[Literal["representation", "obligation"], str]]:
    oracle = _synthetic_oracle()
    universe = oracle["classification_universe"]
    return {
        *(("representation", item) for item in universe["existing_representations"]),
        *(("obligation", item) for item in universe["new_obligations"]),
        *extra_targets,
    }


def _obligation_verdict(
    representation_id: str,
    obligation_id: str,
    *,
    status: str = "VALID_APPLICABLE",
    architecture_sha: str = ARCH_SHA,
    semantic_match: bool | None = True,
    evidence_contract_adequate: bool = True,
    evidence_refs: list[str] | None = None,
) -> dict[str, Any]:
    if evidence_refs is None:
        evidence_refs = [f"evidence/{representation_id}-{obligation_id}.json"]
    return {
        "schema_version": 1,
        "representation_id": representation_id,
        "obligation_id": obligation_id,
        "architecture_source_sha": architecture_sha,
        "semantic_match": semantic_match,
        "evidence_contract_adequate": evidence_contract_adequate,
        "evidence_refs": evidence_refs,
        "status": status,
        "reason_codes": [] if status == "VALID_APPLICABLE" else [status],
    }


def test_all_execution_schemas_validate_and_legacy_result_contract_is_unchanged() -> None:
    for schema_path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        load_schema(schema_path.name)

    legacy = {
        "scenario_id": "DA99",
        "method": "B0",
        "source_revision": ARCH_SHA,
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
    validate_legacy_result(legacy)


def test_b0_prediction_is_empty_and_configuration_copy_is_byte_identical(tmp_path: Path) -> None:
    original = b"architecture_state: A0_MONOLITH\nrepresentations: []\n"
    source = tmp_path / "a0.yaml"
    destination = tmp_path / "method-output" / "candidate.yaml"
    source.write_bytes(original)
    prediction = build_b0_prediction(ARCH_SHA, BUNDLE_SHA)
    validate_prediction(prediction)
    assert prediction["predicted_affected"] == []
    assert prediction["proposed_operations"] == []
    digest = copy_frozen_configuration(source, destination, sha256_bytes(original))
    assert destination.read_bytes() == original
    assert digest == sha256_file(source)
    with pytest.raises(ProtocolError, match="allowlisted input hash"):
        copy_frozen_configuration(source, tmp_path / "wrong.yaml", "0" * 64)


def test_b0_candidate_retains_original_representation_semantics() -> None:
    configuration = {
        "configuration_version": 1,
        "criteria": [{"id": "architecture_compliance", "active": True}],
        "representations": [
            {
                "criterion": "architecture_compliance",
                "stage": "ci",
                "evaluator": "import_linter",
                "metrics": ["violations"],
            }
        ],
    }
    catalog = {
        "representations": [
            {
                "id": "REP_LAYERING",
                "criterion": "architecture_compliance",
                "stage": "ci",
                "evaluator": "import_linter",
                "metrics": ["violations"],
                "covers": ["AC_LAYERING"],
            }
        ]
    }
    candidate = build_b0_candidate(configuration, catalog, ARCH_SHA, EVIDENCE_SHA, BUNDLE_SHA)
    validate_candidate(candidate)
    assert candidate["representations"][0]["id"] == "REP_LAYERING"
    assert candidate["representations"][0]["active"] is True
    assert candidate["changes"] == []
    assert candidate["candidate_validation"]["status"] == "not_run"


def test_b1_requires_a_blind_independent_operator_record() -> None:
    assert operator_readiness(None)["status"] == "NOT READY"
    operator = {
        "operator_id": "operator-1",
        "experience": "architecture testing",
        "prior_exposure": "no reference answer exposure",
        "access_recorded": True,
        "time_budget_recorded": True,
        "independent_of_method_development": True,
        "blind_to_reference_answers": True,
    }
    assert operator_readiness(operator)["status"] == "READY"
    operator["blind_to_reference_answers"] = False
    assert operator_readiness(operator)["status"] == "NOT READY"


def test_p_interface_refuses_to_claim_an_unfrozen_algorithm() -> None:
    with pytest.raises(MethodNotReadyError, match="Impact"):
        require_p_algorithm()


def test_private_ground_truth_hash_record_contains_no_oracle_content(tmp_path: Path) -> None:
    ground_truth = tmp_path / "ground_truth.yaml"
    ground_truth.write_text("private_answer: synthetic-only\n", encoding="utf-8")
    scorer_directory = tmp_path / "private-scorer"
    record = record_private_ground_truth_hash(
        ground_truth,
        scorer_directory,
        "2026-10-09T12:00:00Z",
    )
    record_path = scorer_directory / "ground_truth_hash.json"
    assert record["sha256"] == sha256_file(ground_truth)
    assert b"synthetic-only" not in record_path.read_bytes()
    with pytest.raises(ProtocolError, match="write-once"):
        record_private_ground_truth_hash(ground_truth, scorer_directory, "2026-10-09T12:00:00Z")


def test_prediction_sealing_is_deterministic_write_once_and_hash_verified(tmp_path: Path) -> None:
    payload = _prediction()
    fixed_time = "2026-10-09T12:00:00Z"
    first = seal_prediction(payload, tmp_path / "sealed", fixed_time)
    assert first.sha256 == sha256_file(first.path)
    assert first.path.read_bytes().startswith(b'{"architecture_source_sha":')
    verified = load_verified_prediction(tmp_path / "sealed")
    assert verified.payload == payload
    assert verified.sha256 == first.sha256
    with pytest.raises(SealedArtifactError, match="write-once"):
        seal_prediction(payload, tmp_path / "sealed", fixed_time)

    prediction_path = first.path
    prediction_path.chmod(0o644)
    prediction_path.write_bytes(prediction_path.read_bytes() + b" ")
    with pytest.raises(SealedArtifactError, match="does not match"):
        load_verified_prediction(tmp_path / "sealed")


def test_prediction_schema_rejects_duplicate_and_contradictory_operations() -> None:
    duplicate = _prediction(
        affected=[
            {
                "target_type": "representation",
                "target_id": "REP_X",
                "predicted_operation": "replace",
            },
            {
                "target_type": "representation",
                "target_id": "REP_X",
                "predicted_operation": "replace",
            },
        ],
        operations=[
            {"target_type": "representation", "target_id": "REP_X", "operation": "replace"}
        ],
    )
    with pytest.raises(ContractValidationError, match="duplicate decision"):
        validate_prediction(duplicate)

    contradiction = _prediction(
        affected=[
            {
                "target_type": "representation",
                "target_id": "REP_X",
                "predicted_operation": "replace",
            }
        ],
        operations=[{"target_type": "representation", "target_id": "REP_X", "operation": "adjust"}],
    )
    with pytest.raises(ContractValidationError, match="does not match"):
        validate_prediction(contradiction)


def test_rq1_scores_all_operations_implicit_retain_and_missing_add() -> None:
    affected = [
        {
            "target_type": "representation",
            "target_id": "REP_REPLACE",
            "predicted_operation": "replace",
        },
        {
            "target_type": "representation",
            "target_id": "REP_DEACTIVATE",
            "predicted_operation": "deactivate",
        },
        {
            "target_type": "representation",
            "target_id": "REP_ADJUST",
            "predicted_operation": "adjust",
        },
        {"target_type": "obligation", "target_id": "AC_NEW", "predicted_operation": "add"},
    ]
    operations = [
        {"target_type": "representation", "target_id": "REP_REPLACE", "operation": "replace"},
        {"target_type": "representation", "target_id": "REP_DEACTIVATE", "operation": "deactivate"},
        {"target_type": "representation", "target_id": "REP_ADJUST", "operation": "adjust"},
        {"target_type": "obligation", "target_id": "AC_NEW", "operation": "add"},
    ]
    result = score_rq1(
        _prediction(affected=affected, operations=operations),
        _synthetic_oracle(),
        _synthetic_known_targets(),
    )
    assert (result["tp"], result["fp_in"], result["fn"], result["tn"]) == (4, 0, 0, 1)
    assert result["precision"] == result["recall"] == result["f1"] == 1.0
    assert result["operation_accuracy"] == 1.0
    assert result["implicit_retain_count"] == 1
    assert result["normalized_operations"][-1]["normalized_operation"] == "add"


def test_rq1_b0_missed_add_and_empty_prediction_conventions() -> None:
    result = score_rq1(_prediction(method_id="B0"), _synthetic_oracle(), _synthetic_known_targets())
    assert (result["tp"], result["fp_total"], result["fn"], result["tn"]) == (0, 0, 4, 1)
    assert result["precision"] == result["recall"] == result["f1"] == 0.0
    assert result["implicit_retain_count"] == 4
    missing_add = next(
        item for item in result["normalized_operations"] if item["target_type"] == "obligation"
    )
    assert missing_add["normalized_operation"] == "missing_add"

    empty_oracle = {
        "classification_universe": {
            "existing_representations": ["REP_ONLY"],
            "new_obligations": [],
        },
        "expected_operations": {"REP_ONLY": "retain"},
    }
    empty_result = score_rq1(_prediction(), empty_oracle, {("representation", "REP_ONLY")})
    assert empty_result["precision"] is None
    assert empty_result["recall"] is None
    assert empty_result["f1"] is None
    assert empty_result["correct_empty_set_detection"] is True

    with pytest.raises(ProtocolError, match="trusted known-target registry"):
        score_rq1(_prediction(method_id="B0"), _synthetic_oracle())


def test_rq1_counts_extra_false_positives_and_reports_unknown_ids() -> None:
    affected = [
        {"target_type": "obligation", "target_id": "AC_EXTERNAL", "predicted_operation": "add"},
        {
            "target_type": "representation",
            "target_id": "REP_UNKNOWN",
            "predicted_operation": "adjust",
        },
    ]
    operations = [
        {"target_type": "obligation", "target_id": "AC_EXTERNAL", "operation": "add"},
        {"target_type": "representation", "target_id": "REP_UNKNOWN", "operation": "adjust"},
    ]
    known = _synthetic_known_targets(("obligation", "AC_EXTERNAL"))
    result = score_rq1(
        _prediction(affected=affected, operations=operations), _synthetic_oracle(), known
    )
    assert result["fp_extra"] == 2
    assert result["fp_total"] == 2
    assert {item["code"] for item in result["diagnostics"]} >= {
        "EXTRA_PREDICTED_TARGET",
        "UNKNOWN_TARGET",
    }
    assert any(item["target_id"] == "REP_UNKNOWN" for item in result["extra_predicted_targets"])
    extra_by_id = {
        item["target_id"]: item["known_target"] for item in result["extra_predicted_targets"]
    }
    assert extra_by_id == {"AC_EXTERNAL": True, "REP_UNKNOWN": False}
    unknown_ids = {
        item["target_id"] for item in result["diagnostics"] if item["code"] == "UNKNOWN_TARGET"
    }
    assert unknown_ids == {"REP_UNKNOWN"}


@pytest.mark.parametrize(
    ("target_type", "target_id", "operation"),
    [
        ("representation", "REP_EXTERNAL", "adjust"),
        ("obligation", "Q_EXTERNAL", "add"),
    ],
)
def test_rq1_known_out_of_universe_targets_are_false_positives_not_violations(
    target_type: str,
    target_id: str,
    operation: str,
) -> None:
    target = {"target_type": target_type, "target_id": target_id}
    prediction = _prediction(
        affected=[{**target, "predicted_operation": operation}],
        operations=[{**target, "operation": operation}],
    )
    known = _synthetic_known_targets(
        (cast(Literal["representation", "obligation"], target_type), target_id)
    )
    result = score_rq1(prediction, _synthetic_oracle(), known)
    assert result["fp_extra"] == 1
    assert result["extra_predicted_targets"] == [
        {**target, "operation": operation, "known_target": True}
    ]
    assert not any(item["code"] == "UNKNOWN_TARGET" for item in result["diagnostics"])
    scored = build_scored_result(
        prediction,
        EVIDENCE_SHA,
        result,
        score_rq2(_synthetic_oracle(), ARCH_SHA, [], {}, [], {}),
    )
    assert "PROTOCOL_VIOLATION" not in scored["failure_statuses"]


@pytest.mark.parametrize(
    ("target_type", "target_id", "operation"),
    [
        ("representation", "REP_UNREGISTERED", "adjust"),
        ("obligation", "Q_UNREGISTERED", "add"),
    ],
)
def test_unknown_rq1_target_propagates_protocol_violation_to_sealed_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target_type: str,
    target_id: str,
    operation: str,
) -> None:
    monkeypatch.setattr(scoring, "load_trusted_known_targets", lambda _: _synthetic_known_targets())
    target = {"target_type": target_type, "target_id": target_id}
    prediction = _prediction(
        affected=[{**target, "predicted_operation": operation}],
        operations=[{**target, "operation": operation}],
    )
    sealed_directory = tmp_path / f"sealed-{target_type}"
    seal_prediction(prediction, sealed_directory, "2026-10-09T12:00:00Z")
    ground_truth_path = tmp_path / "ground_truth.yaml"
    ground_truth_path.write_text(json.dumps(_synthetic_oracle()), encoding="utf-8")

    result = score_sealed_prediction(
        sealed_directory,
        ground_truth_path,
        ARCH_SHA,
        [],
        {},
        [],
        {},
        failure_statuses=(),
    )

    assert result["rq1"]["fp_extra"] == 1
    assert any(
        item["code"] == "UNKNOWN_TARGET" and item["target_id"] == target_id
        for item in result["rq1"]["diagnostics"]
    )
    assert result["failure_statuses"] == ["PROTOCOL_VIOLATION"]


def test_rq1_known_and_unknown_extra_targets_keep_separate_classifications() -> None:
    affected = [
        {
            "target_type": "representation",
            "target_id": "REP_EXTERNAL",
            "predicted_operation": "adjust",
        },
        {"target_type": "obligation", "target_id": "Q_UNKNOWN", "predicted_operation": "add"},
    ]
    operations = [
        {"target_type": "representation", "target_id": "REP_EXTERNAL", "operation": "adjust"},
        {"target_type": "obligation", "target_id": "Q_UNKNOWN", "operation": "add"},
    ]
    known = _synthetic_known_targets(("representation", "REP_EXTERNAL"))
    result = score_rq1(
        _prediction(affected=affected, operations=operations), _synthetic_oracle(), known
    )
    assert result["fp_extra"] == 2
    assert {
        item["target_id"] for item in result["diagnostics"] if item["code"] == "UNKNOWN_TARGET"
    } == {"Q_UNKNOWN"}
    assert {
        item["target_id"]: item["known_target"] for item in result["extra_predicted_targets"]
    } == {
        "REP_EXTERNAL": True,
        "Q_UNKNOWN": False,
    }


def test_scored_result_envelope_is_schema_valid_and_read_only(tmp_path: Path) -> None:
    prediction = _prediction(method_id="B0")
    sealed = seal_prediction(prediction, tmp_path / "sealed", "2026-10-09T12:00:00Z")
    before = sealed.path.read_bytes()
    rq1 = score_rq1(
        load_verified_prediction(tmp_path / "sealed").payload,
        _synthetic_oracle(),
        _synthetic_known_targets(),
    )
    rq2 = score_rq2(
        _synthetic_oracle(),
        ARCH_SHA,
        [],
        {},
        [],
        {},
    )
    result = build_scored_result(prediction, sealed.sha256, rq1, rq2)
    validate_payload("scored_result.schema.json", result)
    assert sealed.path.read_bytes() == before


def test_rq2_counts_each_obligation_once_and_reports_invalid_evidence() -> None:
    before_config = [{"id": "REP_BEFORE", "active": True, "covers": ["Q_ONE"]}]
    after_config = [
        {"id": "REP_MAIN", "active": True, "covers": ["Q_ONE", "Q_TWO"]},
        {"id": "REP_DUP", "active": True, "covers": ["Q_ONE"]},
        {"id": "REP_BAD", "active": True, "covers": ["Q_THREE"]},
    ]
    result = score_rq2(
        _synthetic_oracle(),
        ARCH_SHA,
        before_config,
        {"REP_BEFORE": _verdict("REP_BEFORE")},
        after_config,
        {
            "REP_MAIN": _verdict("REP_MAIN"),
            "REP_DUP": _verdict("REP_DUP"),
            "REP_BAD": _verdict("REP_BAD", "SEMANTIC_MISMATCH"),
        },
        obligation_verdicts_before=[
            _obligation_verdict("REP_BEFORE", "Q_ONE"),
        ],
        obligation_verdicts_after=[
            _obligation_verdict("REP_MAIN", "Q_ONE"),
            _obligation_verdict("REP_MAIN", "Q_TWO"),
            _obligation_verdict("REP_DUP", "Q_ONE"),
        ],
    )
    assert result["coverage_before"] == pytest.approx(1 / 3)
    assert result["coverage_after"] == pytest.approx(2 / 3)
    assert result["coverage_delta"] == pytest.approx(1 / 3)
    assert result["uncovered_obligations"] == ["Q_THREE"]
    assert result["invalid_representations"] == ["REP_BAD"]
    assert result["semantic_violation_denominator"] == 3
    assert len(result["coverage_after_assessment"]["valid_cover_pairs"]) == 3


@pytest.mark.parametrize(
    ("first_pair", "second_pair", "expected_coverage"),
    [
        ("valid", "missing", 0.5),
        ("missing", "valid", 0.5),
        ("valid", "valid", 1.0),
        ("missing", "missing", 0.0),
        ("valid", "absent", 0.5),
    ],
)
def test_rq2_requires_independent_verdicts_for_each_obligation(
    first_pair: str,
    second_pair: str,
    expected_coverage: float,
) -> None:
    obligations = ["Q_FAILURE", "Q_5XX"]
    oracle = {**_synthetic_oracle(), "required_obligations_after": obligations}
    representation = {
        "id": "REP_RUNTIME",
        "active": True,
        "covers": obligations,
    }
    pair_verdicts: list[dict[str, Any]] = []
    for obligation, state in zip(obligations, (first_pair, second_pair), strict=True):
        if state == "absent":
            continue
        if state == "valid":
            pair_verdicts.append(_obligation_verdict("REP_RUNTIME", obligation))
        else:
            pair_verdicts.append(
                _obligation_verdict(
                    "REP_RUNTIME",
                    obligation,
                    status="MISSING_EVIDENCE",
                    evidence_contract_adequate=False,
                    evidence_refs=[],
                )
            )

    result = score_rq2(
        oracle,
        ARCH_SHA,
        [],
        {},
        [representation],
        {"REP_RUNTIME": _verdict("REP_RUNTIME")},
        obligation_verdicts_after=pair_verdicts,
    )

    assert result["coverage_before"] == 0.0
    assert result["coverage_after"] == pytest.approx(expected_coverage)
    assert result["coverage_delta"] == pytest.approx(expected_coverage)
    assessment = result["coverage_after_assessment"]
    assert assessment["denominator"] == 2
    assert assessment["required_obligations"] == obligations
    assert assessment["architecture_source_sha"] == ARCH_SHA
    if expected_coverage == 0.5:
        assert assessment["covered_count"] == 1
        assert len(assessment["valid_cover_pairs"]) == 1
        assert assessment["valid_cover_pairs"][0]["evidence_refs"]
        assert assessment["invalid_representations"] == []
        assert result["semantic_violation_denominator"] == 1


def test_rq2_general_execution_success_does_not_infer_obligation_validity() -> None:
    representation = {
        "id": "REP_RUNTIME",
        "active": True,
        "covers": ["Q_FAILURE"],
    }
    execution_verdict = assess_representation(
        representation,
        _valid_evidence("REP_RUNTIME"),
        ARCH_SHA,
    )
    assert execution_verdict["status"] == "VALID_APPLICABLE"

    result = score_rq2(
        {**_synthetic_oracle(), "required_obligations_after": ["Q_FAILURE"]},
        ARCH_SHA,
        [],
        {},
        [representation],
        {"REP_RUNTIME": execution_verdict},
    )
    assert result["coverage_after"] == 0.0
    assert (
        result["coverage_after_assessment"]["pair_assessments"][0]["status"] == "MISSING_EVIDENCE"
    )


def test_rq2_da01_runtime_representation_partial_obligation_coverage_is_one_half() -> None:
    obligations = ["Q_FAILURE", "Q_5XX"]
    oracle = {**_synthetic_oracle(), "required_obligations_after": obligations}
    representation = {
        "id": "REP_RUNTIME",
        "active": True,
        "covers": obligations,
    }
    result = score_rq2(
        oracle,
        ARCH_SHA,
        [],
        {},
        [representation],
        {"REP_RUNTIME": _verdict("REP_RUNTIME")},
        obligation_verdicts_after=[
            _obligation_verdict(
                "REP_RUNTIME",
                "Q_FAILURE",
                evidence_refs=["evidence/business-failures.json"],
            ),
            _obligation_verdict(
                "REP_RUNTIME",
                "Q_5XX",
                status="MISSING_EVIDENCE",
                evidence_contract_adequate=False,
                evidence_refs=[],
            ),
        ],
    )

    assessment = result["coverage_after_assessment"]
    pair_statuses = {
        (item["representation_id"], item["obligation_id"]): item["status"]
        for item in assessment["pair_assessments"]
    }
    assert result["coverage_after"] == 0.5
    assert assessment["required_obligations"] == obligations
    assert pair_statuses == {
        ("REP_RUNTIME", "Q_FAILURE"): "VALID_APPLICABLE",
        ("REP_RUNTIME", "Q_5XX"): "MISSING_EVIDENCE",
    }
    assert assessment["valid_cover_pairs"] == [
        {
            "representation_id": "REP_RUNTIME",
            "obligation_id": "Q_FAILURE",
            "architecture_source_sha": ARCH_SHA,
            "evidence_refs": ["evidence/business-failures.json"],
        }
    ]
    assert assessment["invalid_representations"] == []
    assert result["semantic_violation_denominator"] == 1


def test_rq2_obligation_assessor_requires_specific_evidence_even_after_exit_zero() -> None:
    representation = {
        "id": "REP_RUNTIME",
        "active": True,
        "covers": ["Q_FAILURE", "Q_5XX"],
    }
    execution_verdict = assess_representation(
        representation,
        _valid_evidence("REP_RUNTIME"),
        ARCH_SHA,
    )
    failure = assess_obligation(
        representation,
        execution_verdict,
        "Q_FAILURE",
        ARCH_SHA,
        semantic_match=True,
        evidence_contract_adequate=True,
        evidence_refs=["evidence/business-failures.json"],
    )
    http_5xx = assess_obligation(
        representation,
        execution_verdict,
        "Q_5XX",
        ARCH_SHA,
        semantic_match=True,
        evidence_contract_adequate=False,
        evidence_refs=[],
    )
    assert failure["status"] == "VALID_APPLICABLE"
    assert http_5xx["status"] == "MISSING_EVIDENCE"
    assert http_5xx["reason_codes"] == ["OBLIGATION_EVIDENCE_INADEQUATE"]
    assert "obligation_id" in http_5xx
    assert http_5xx["representation_id"] == failure["representation_id"]


def test_rq2_union_semantics_count_duplicate_valid_representations_once() -> None:
    oracle = {**_synthetic_oracle(), "required_obligations_after": ["Q_ONE", "Q_TWO"]}
    configuration = [
        {"id": "REP_A", "active": True, "covers": ["Q_ONE"]},
        {"id": "REP_B", "active": True, "covers": ["Q_ONE"]},
    ]
    result = score_rq2(
        oracle,
        ARCH_SHA,
        [],
        {},
        configuration,
        {"REP_A": _verdict("REP_A"), "REP_B": _verdict("REP_B")},
        obligation_verdicts_after=[
            _obligation_verdict("REP_A", "Q_ONE"),
            _obligation_verdict("REP_B", "Q_ONE"),
        ],
    )
    assessment = result["coverage_after_assessment"]
    assert result["coverage_after"] == 0.5
    assert assessment["covered_count"] == 1
    assert assessment["valid_cover_pairs"] == [
        {
            "representation_id": "REP_A",
            "obligation_id": "Q_ONE",
            "architecture_source_sha": ARCH_SHA,
            "evidence_refs": ["evidence/REP_A-Q_ONE.json"],
        },
        {
            "representation_id": "REP_B",
            "obligation_id": "Q_ONE",
            "architecture_source_sha": ARCH_SHA,
            "evidence_refs": ["evidence/REP_B-Q_ONE.json"],
        },
    ]


def test_rq2_pair_architecture_mismatch_and_conflicting_duplicates_fail_closed() -> None:
    oracle = {**_synthetic_oracle(), "required_obligations_after": ["Q_ONE"]}
    representation = {"id": "REP_A", "active": True, "covers": ["Q_ONE"]}
    mismatch = score_rq2(
        oracle,
        ARCH_SHA,
        [],
        {},
        [representation],
        {"REP_A": _verdict("REP_A")},
        obligation_verdicts_after=[
            _obligation_verdict("REP_A", "Q_ONE", architecture_sha=OTHER_ARCH_SHA),
        ],
    )
    pair = mismatch["coverage_after_assessment"]["pair_assessments"][0]
    assert mismatch["coverage_after"] == 0.0
    assert pair["status"] == "STALE_ARCHITECTURE_SCOPE"

    valid_pair = _obligation_verdict("REP_A", "Q_ONE")
    conflicting_pair = _obligation_verdict(
        "REP_A", "Q_ONE", status="SEMANTIC_MISMATCH", semantic_match=False
    )
    with pytest.raises(ProtocolError, match="Conflicting duplicate"):
        score_rq2(
            oracle,
            ARCH_SHA,
            [],
            {},
            [representation],
            {"REP_A": _verdict("REP_A")},
            obligation_verdicts_after=[valid_pair, conflicting_pair],
        )


def test_rq2_rejects_duplicate_obligations_and_reports_stale_scope() -> None:
    duplicate_oracle = {**_synthetic_oracle(), "required_obligations_after": ["Q_ONE", "Q_ONE"]}
    with pytest.raises(ProtocolError, match="unique complete"):
        score_rq2(duplicate_oracle, ARCH_SHA, [], {}, [], {})
    stale = _verdict("REP_OLD", "STALE_ARCHITECTURE_SCOPE")
    stale["architecture_source_sha"] = OTHER_ARCH_SHA
    one_obligation_oracle = {**_synthetic_oracle(), "required_obligations_after": ["Q_ONE"]}
    result = score_rq2(
        one_obligation_oracle,
        ARCH_SHA,
        [],
        {},
        [{"id": "REP_OLD", "active": True, "covers": ["Q_ONE"]}],
        {"REP_OLD": stale},
    )
    assert result["coverage_after"] == 0.0
    assert result["stale_representations"] == ["REP_OLD"]


def test_private_scorer_verifies_seal_derives_full_oracle_and_leaves_prediction_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(scoring, "load_trusted_known_targets", lambda _: _synthetic_known_targets())
    oracle = _synthetic_oracle()
    ground_truth_path = tmp_path / "ground_truth.yaml"
    ground_truth_path.write_text(json.dumps(oracle), encoding="utf-8")
    prediction_directory = tmp_path / "sealed"
    prediction = _prediction(method_id="B0")
    sealed = seal_prediction(prediction, prediction_directory, "2026-10-09T12:00:00Z")
    prediction_bytes = sealed.path.read_bytes()

    result = score_sealed_prediction(
        prediction_directory,
        ground_truth_path,
        ARCH_SHA,
        [],
        {},
        [],
        {},
    )

    assert result["prediction_sha256"] == sealed.sha256
    assert result["rq1"]["fn"] == 4
    assert any(
        item["normalized_operation"] == "missing_add"
        for item in result["rq1"]["normalized_operations"]
    )
    assert result["rq2"]["required_obligations"] == oracle["required_obligations_after"]
    assert "PROTOCOL_VIOLATION" not in result["failure_statuses"]
    assert sealed.path.read_bytes() == prediction_bytes


@pytest.mark.parametrize(
    ("updates", "expected_status"),
    [
        ({}, "VALID_APPLICABLE"),
        ({"semantic_compatible": False}, "SEMANTIC_MISMATCH"),
        ({"architecture_source_sha": OTHER_ARCH_SHA}, "STALE_ARCHITECTURE_SCOPE"),
        ({"missing_targets": ["package.layer.repository"]}, "MISSING_ARCHITECTURE_TARGET"),
        ({"inspected_subjects": [], "inspected_edge_count": 0}, "VACUOUS_SUCCESS"),
        ({"evidence_contract_satisfied": False}, "MISSING_EVIDENCE"),
        ({"process_exit_code": 2}, "EXECUTION_FAILURE"),
        ({"infrastructure_status": "infrastructure_failure"}, "INFRASTRUCTURE_FAILURE"),
        ({"stage_applicable": False}, "STAGE_OR_CONTEXT_MISMATCH"),
        ({"mapping_resolved": False}, "OBLIGATION_MAPPING_MISMATCH"),
    ],
)
def test_semantic_validity_distinguishes_failure_modes(
    updates: dict[str, Any],
    expected_status: str,
) -> None:
    evidence = {**_valid_evidence(), **updates}
    representation = {"id": "REP_VALID", "active": True, "covers": ["Q_ONE"]}
    verdict = assess_representation(representation, evidence, ARCH_SHA)
    assert verdict["status"] == expected_status


def test_old_a0_importlinter_scope_is_stale_after_package_reorganization() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    config = (repository_root / "fitness/evaluators/a0/importlinter.toml").read_bytes()
    before_modules = {"app.api", "app.services", "app.repositories", "app.models"}
    after_modules = {
        "app.api",
        "app.services.errors",
        "app.models.base",
        "app.modules.users.api",
        "app.modules.users.service",
        "app.modules.users.repository",
        "app.modules.users.model",
    }
    assert inspect_import_linter_scope(config, before_modules)["stale"] is False
    after = inspect_import_linter_scope(config, after_modules)
    assert after["stale"] is True
    assert "app.repositories" in after["missing_targets"]
    assert after["inspected_module_count"] > 0


def test_synthetic_layer_fault_is_detected_and_clean_structure_passes(tmp_path: Path) -> None:
    layer_order = [
        "sample.api",
        "sample.service",
        "sample.repository",
        "sample.model",
    ]
    clean_edges = [
        ("sample.api.handlers", "sample.service.logic"),
        ("sample.service.logic", "sample.repository.store"),
        ("sample.repository.store", "sample.model.entity"),
    ]
    clean = validate_layer_edges(layer_order, clean_edges)
    assert clean["compliant"] is True
    assert clean["inspected_edge_count"] == 3
    faulty = validate_layer_edges(
        layer_order,
        [*clean_edges, ("sample.repository.store", "sample.api.handlers")],
    )
    assert faulty["compliant"] is False
    assert faulty["violations"] == [
        {"source": "sample.repository.store", "target": "sample.api.handlers"}
    ]

    package = tmp_path / "sample" / "capabilities" / "billing"
    package.mkdir(parents=True)
    for filename in ("__init__.py", "api.py", "service.py"):
        (package / filename).write_text("", encoding="utf-8")
    manifest = {
        "modules": {
            "billing": {
                "package": "sample.capabilities.billing",
                "required_files": ["__init__.py", "api.py", "service.py"],
            }
        }
    }
    root = tmp_path
    structure = validate_module_structure(root, manifest)
    assert structure["compliant"] is True
    (package / "service.py").unlink()
    corrupted = validate_module_structure(root, manifest)
    assert corrupted["compliant"] is False
    assert corrupted["missing_targets"] == ["sample.capabilities.billing.service.py"]


def test_evidence_artifacts_are_hash_checked_and_path_confined(tmp_path: Path) -> None:
    evidence_root = tmp_path / "evidence"
    artifact = evidence_root / "logs" / "run.txt"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("synthetic evidence\n", encoding="utf-8")
    evidence = {
        "evidence_artifacts": [
            {"path": "logs/run.txt", "sha256": sha256_file(artifact)},
        ]
    }
    assert verify_evidence_artifacts(evidence_root, evidence) == ["logs/run.txt"]
    evidence["evidence_artifacts"][0]["path"] = "../outside.txt"
    with pytest.raises(ProtocolError, match="Unsafe evidence path"):
        verify_evidence_artifacts(evidence_root, evidence)
