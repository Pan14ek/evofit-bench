"""Real-source DEVELOPMENT execution and archive-readback contract tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError, ProtocolError
from experiments.execution.tooling.mono_ci_b0_psi_archive import _validate_archive_metadata
from experiments.execution.tooling.mono_ci_psi_evidence import (
    EVALUATOR_CONFIGS,
    evaluator_source_artifacts,
)
from experiments.execution.tooling.mono_ci_psi_transition import (
    AFTER_COMMIT,
    AFTER_STATE,
    _coverage_assessment_path,
    _evaluator_capabilities,
    _manifest_requirements_for_evaluator,
    _validate_method_result_v2,
    _verify_adaptation_necessity_report,
    pack_transition_archive,
    run_transition,
    verify_transition_archive,
    verify_transition_run,
)

ROOT = Path(__file__).resolve().parents[2]


def test_archive_metadata_accepts_a05_namespace_and_preserves_transition_names() -> None:
    workflow_url = "https://github.com/Pan14ek/evofit-bench/actions/runs/123456"

    _validate_archive_metadata(workflow_url, "mono-ci-psi-a05-123456-1", "uv 0.9.0")
    _validate_archive_metadata(workflow_url, "mono-ci-psi-transition-test-1", "uv 0.9.0")

    with pytest.raises(ProtocolError, match="ARCHIVE_ARTIFACT_NAME_INVALID"):
        _validate_archive_metadata(workflow_url, "mono-ci-psi-a05-bad/tag", "uv 0.9.0")


def test_a05_archive_schema_pins_the_prospective_a04_baseline() -> None:
    schema = json.loads(
        (
            ROOT
            / "experiments/execution/schemas/mono_ci_psi_transition_archive_v3.schema.json"
        ).read_text(encoding="utf-8")
    )

    assert (
        schema["$defs"]["baseline"]["properties"]["configuration_id"]["const"]
        == "MONO_CI_RECONSTRUCTED_B0_A04_V1"
    )


def _evaluator_capability_case(tmp_path: Path, evaluator_id: str) -> dict[str, Any]:
    config_path = ROOT / EVALUATOR_CONFIGS[evaluator_id]
    config_bytes = config_path.read_bytes()
    config = yaml.safe_load(config_bytes)
    configuration_sha256 = hashlib.sha256(config_bytes).hexdigest()
    config_artifact = (
        Path("PSI/evaluator-observations/implementation") / evaluator_id / config_path.name
    )
    manifest_artifact = (
        Path("PSI/evaluator-observations/implementation") / evaluator_id / "source-manifest.json"
    )
    output_path = Path("PSI/evaluator-observations/after") / evaluator_id / "evaluator-output.json"
    coverage_path = _coverage_assessment_path(AFTER_STATE, evaluator_id)
    for relative_path in (config_artifact, manifest_artifact, output_path, coverage_path):
        (tmp_path / relative_path).parent.mkdir(parents=True, exist_ok=True)

    _, source_manifest_bytes, _ = evaluator_source_artifacts(ROOT)
    (tmp_path / config_artifact).write_bytes(config_bytes)
    (tmp_path / manifest_artifact).write_bytes(source_manifest_bytes)

    if evaluator_id == "AC_PUBLIC_API":
        public_api = config["public_api"]
        diagnostics = {
            "public_module_pattern": public_api["public_module_pattern"],
            "interfaces_by_capability": public_api["interfaces_by_capability"],
            "legacy_exception": public_api["legacy_exception"],
            "exports_by_capability": {},
            "cross_capability_imports": [],
        }
        coverage: dict[str, Any] = {"source_inspection_status": "COMPLETE"}
    else:
        graph = config["module_graph"]
        diagnostics = {
            "allowed_edges": sorted(
                graph["allowed_dependencies_by_state"][AFTER_STATE],
                key=lambda edge: (edge.get("from", ""), edge.get("to", "")),
            ),
            "cycles": [],
        }
        coverage = {
            "source_inspection_status": "COMPLETE",
            "dependency_analysis": {
                "static_relationship_comparison": "MATCHED",
                "cycle_comparison": "MATCHED",
            },
        }

    evidence = {
        "evaluator": {
            "id": evaluator_id,
            "obligation_id": evaluator_id,
            "configuration_digest": configuration_sha256,
        },
        "architecture": {
            "source_sha_status": "MATCHED",
            "manifest_state_status": "MATCHED",
        },
        "diagnostics": diagnostics,
        "result": {"execution_status": "COMPLETED", "compliance": "COMPLIANT"},
    }
    (tmp_path / output_path).write_text(json.dumps(evidence), encoding="utf-8")
    (tmp_path / coverage_path).write_text(json.dumps(coverage), encoding="utf-8")

    # Match the record fields returned by run_fresh_evaluator(). In particular,
    # the producer's configuration digest field is named configuration_sha256.
    run = {
        "evaluator_id": evaluator_id,
        "architecture_state": AFTER_STATE,
        "source_commit_sha": AFTER_COMMIT,
        "configuration_path": EVALUATOR_CONFIGS[evaluator_id],
        "configuration_sha256": configuration_sha256,
        "execution_status": "COMPLETED",
        "compliance": "COMPLIANT",
        "output_path": output_path.as_posix(),
        "evidence": evidence,
    }
    return {
        "run_root": tmp_path,
        "evaluator_id": evaluator_id,
        "config": config,
        "run": run,
        "coverage": coverage,
        "configuration_sha256": configuration_sha256,
    }


def _evaluate_capability_case(
    case: dict[str, Any], *, representation_bound: bool = True
) -> dict[str, Any]:
    return _evaluator_capabilities(
        evaluator_id=case["evaluator_id"],
        state=AFTER_STATE,
        config=case["config"],
        run=case["run"],
        coverage=case["coverage"],
        representation_bound=representation_bound,
        configuration_sha256=case["configuration_sha256"],
        run_root=case["run_root"],
        config_path=EVALUATOR_CONFIGS[case["evaluator_id"]],
    )


def test_architecture_requirements_are_derived_from_versioned_state_manifests() -> None:
    before_path = ROOT / "architecture/states/A0_3_GOVERNED_MODULE_GRAPH.yaml"
    after_path = ROOT / "architecture/states/A0_4_REPORT_QUERY_PORT.yaml"
    before = yaml.safe_load(before_path.read_text(encoding="utf-8"))
    after = yaml.safe_load(after_path.read_text(encoding="utf-8"))
    before_source = {
        "path": before_path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(before_path.read_bytes()).hexdigest(),
    }
    after_source = {
        "path": after_path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(after_path.read_bytes()).hexdigest(),
    }

    public_before = _manifest_requirements_for_evaluator(
        "AC_PUBLIC_API", before, "A0_3_GOVERNED_MODULE_GRAPH", before_source
    )
    public_after = _manifest_requirements_for_evaluator(
        "AC_PUBLIC_API", after, "A0_4_REPORT_QUERY_PORT", after_source
    )
    graph_before = _manifest_requirements_for_evaluator(
        "AC_MODULE_GRAPH", before, "A0_3_GOVERNED_MODULE_GRAPH", before_source
    )
    graph_after = _manifest_requirements_for_evaluator(
        "AC_MODULE_GRAPH", after, "A0_4_REPORT_QUERY_PORT", after_source
    )

    assert public_before[0]["control_id"] == (
        "architecture.public_api.temporary_exception:reporting_tasks_query_intermediate_v1"
    )
    assert public_after[0]["control_id"] == "architecture.public_api.reporting_query_port"
    assert public_after[0]["value"] == after["reporting_query_port"]
    assert [row["control_id"] for row in graph_before] == [row["control_id"] for row in graph_after]


def test_historical_v1_adaptation_report_is_schema_readable_without_reinterpretation(
    tmp_path: Path,
) -> None:
    report = {
        "schema_version": "MONO_CI_PSI_ADAPTATION_NECESSITY_V1",
        "execution_id": "DEV_PSI_TRANSITION_HISTORICAL_V1",
        "assessment_scope": "SOURCE_BOUND_DEVELOPMENT_DIAGNOSTIC_NOT_INDEPENDENTLY_REVIEWED",
        "transition": {
            "before_state": "A0_3_GOVERNED_MODULE_GRAPH",
            "after_state": "A0_4_REPORT_QUERY_PORT",
            "before_commit_sha": "a" * 40,
            "after_commit_sha": "b" * 40,
            "changed_application_files": [],
            "source_change_summary": ["Historical archive fixture."],
            "unchanged_architecture_invariants": [],
        },
        "baseline": {
            "configuration_id": "HISTORICAL_FIXTURE",
            "configuration_sha256": "c" * 64,
            "identity_status": "PROSPECTIVE_RECONSTRUCTION_NOT_HISTORICAL",
            "approval_status": "NOT_APPROVED",
        },
        "method_result": {
            "path": "PSI/raw/method-result.json",
            "sha256": "d" * 64,
            "governance_decision": "HOLD",
            "operation_count": 0,
            "candidate_status": "NOT_MATERIALIZED",
            "prediction_status": "NOT_EMITTED",
        },
        "assessments": [
            {
                "control_id": "AC_MODULE_GRAPH",
                "assessment_status": "RETAIN_CANDIDATE",
                "configuration_change_necessity": "NOT_DEMONSTRATED_WITHIN_VERIFIED_SCOPE",
                "relevant_architecture_changes": [],
                "previous_representation_identity": {"representation_id": "REP_FIXTURE"},
                "evaluator_identity": {"evaluator_id": "AC_MODULE_GRAPH"},
                "configuration_identity": {"before_sha256": "e" * 64},
                "inspection_completeness": {"after_status": "COMPLETE"},
                "compliance_observations": {"after": "COMPLIANT"},
                "rule_semantics": {
                    "required_controls_before": ["legacy-control"],
                    "required_controls_after": ["legacy-control"],
                    "represented_controls_before": ["legacy-control"],
                    "represented_controls_after": ["legacy-control"],
                    "scope_limitations": [],
                },
                "pair_semantic_validity": "UNKNOWN",
                "reason_codes": ["HISTORICAL_V1"],
                "evidence_refs": [],
                "missing_proofs": [],
                "operation_justification": {
                    "ADD": "UNSUPPORTED",
                    "REPLACE": "UNSUPPORTED",
                    "RETAIN": "TECHNICAL_CANDIDATE_ONLY",
                    "HOLD": "REQUIRED",
                },
            }
        ],
        "scientific_boundary": {
            "is_independent_reference": False,
            "is_human_review": False,
            "official_comparison": "NOT_EXECUTED",
            "study_readiness": "NO_GO",
            "p_algorithm_status": "NOT_READY",
            "g1": "INCOMPLETE",
            "g4": "NOT_AUTHORIZED",
            "reference_gate": "NOT_READY",
        },
    }
    diagnostic_path = tmp_path / "diagnostics/adaptation-necessity-assessment.json"
    diagnostic_path.parent.mkdir(parents=True)
    diagnostic_path.write_text(json.dumps(report), encoding="utf-8")
    scope_path = tmp_path / "inspection-scope.json"
    scope_path.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")

    _verify_adaptation_necessity_report(
        tmp_path,
        {"evaluator_observations": [{"inspection_scope_path": "inspection-scope.json"}]},
        {},
    )


@pytest.mark.parametrize("evaluator_id", ["AC_PUBLIC_API", "AC_MODULE_GRAPH"])
def test_runner_configuration_digest_verifies_static_capabilities(
    tmp_path: Path, evaluator_id: str
) -> None:
    case = _evaluator_capability_case(tmp_path, evaluator_id)

    inventory = _evaluate_capability_case(case)

    assert inventory["status"] == "VERIFIED_FOR_DECLARED_STATIC_SCOPE"
    assert len(inventory["capabilities"]) == 2
    assert {row["verification_status"] for row in inventory["capabilities"]} == {
        "VERIFIED_STATIC_SCOPE"
    }


@pytest.mark.parametrize("evaluator_id", ["AC_PUBLIC_API", "AC_MODULE_GRAPH"])
def test_mismatched_runner_configuration_digest_fails_closed(
    tmp_path: Path, evaluator_id: str
) -> None:
    case = _evaluator_capability_case(tmp_path, evaluator_id)
    case["run"]["configuration_sha256"] = "0" * 64

    inventory = _evaluate_capability_case(case)

    assert inventory["status"] == "INCOMPLETE_OR_UNVERIFIED"
    assert {row["verification_status"] for row in inventory["capabilities"]} == {"UNVERIFIED"}


@pytest.mark.parametrize("evaluator_id", ["AC_PUBLIC_API", "AC_MODULE_GRAPH"])
def test_missing_runner_configuration_digest_fails_closed(
    tmp_path: Path, evaluator_id: str
) -> None:
    case = _evaluator_capability_case(tmp_path, evaluator_id)
    del case["run"]["configuration_sha256"]

    inventory = _evaluate_capability_case(case)

    assert inventory["status"] == "INCOMPLETE_OR_UNVERIFIED"
    assert {row["verification_status"] for row in inventory["capabilities"]} == {"UNVERIFIED"}


@pytest.mark.parametrize("evaluator_id", ["AC_PUBLIC_API", "AC_MODULE_GRAPH"])
@pytest.mark.parametrize(
    "invalid_evidence",
    [
        "malformed_digest",
        "malformed_expected_digest",
        "wrong_source",
        "incomplete_scope",
        "diagnostics",
        "evidence_digest",
        "representation",
    ],
)
def test_configuration_digest_alone_does_not_verify_capability(
    tmp_path: Path, evaluator_id: str, invalid_evidence: str
) -> None:
    case = _evaluator_capability_case(tmp_path, evaluator_id)
    representation_bound = True
    if invalid_evidence == "malformed_digest":
        case["run"]["configuration_sha256"] = "not-a-sha256"
    elif invalid_evidence == "malformed_expected_digest":
        case["configuration_sha256"] = "not-a-sha256"
    elif invalid_evidence == "wrong_source":
        case["run"]["source_commit_sha"] = "0" * 40
    elif invalid_evidence == "incomplete_scope":
        case["coverage"]["source_inspection_status"] = "INCOMPLETE"
    elif invalid_evidence == "diagnostics":
        if evaluator_id == "AC_PUBLIC_API":
            case["run"]["evidence"]["diagnostics"]["public_module_pattern"] = "mismatch"
        else:
            case["run"]["evidence"]["diagnostics"]["allowed_edges"] = []
    elif invalid_evidence == "evidence_digest":
        case["run"]["evidence"]["evaluator"]["configuration_digest"] = "0" * 64
    else:
        representation_bound = False

    inventory = _evaluate_capability_case(case, representation_bound=representation_bound)

    assert inventory["status"] == "INCOMPLETE_OR_UNVERIFIED"
    assert {row["verification_status"] for row in inventory["capabilities"]} == {"UNVERIFIED"}


def test_real_transition_executes_psi_and_archive_round_trips(tmp_path: Path) -> None:
    run_root = tmp_path / "transition-run"
    result = run_transition(ROOT, run_root, "DEV_PSI_TRANSITION_UNIT_01")

    record = verify_transition_run(run_root)
    raw_path = run_root / record["psi"]["raw_result_path"]
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    state_manifest_path = run_root / record["transition"]["state_manifest_path"]
    state_manifest = json.loads(state_manifest_path.read_text(encoding="utf-8"))
    method_manifest = json.loads(
        (run_root / record["method_input"]["path"] / "method_input_v3.json").read_text()
    )
    adaptation_assessment_path = run_root / "diagnostics/adaptation-necessity-assessment.json"
    adaptation_assessment = json.loads(adaptation_assessment_path.read_text(encoding="utf-8"))
    assert adaptation_assessment["execution_id"] == record["execution_id"]
    assert adaptation_assessment["schema_version"] == "MONO_CI_PSI_ADAPTATION_NECESSITY_V2"
    assert adaptation_assessment["assessment_scope"] == (
        "SOURCE_BOUND_DEVELOPMENT_DIAGNOSTIC_NOT_INDEPENDENTLY_REVIEWED"
    )
    assert adaptation_assessment["method_result"]["sha256"] == record["psi"]["raw_result_sha256"]
    assert (
        adaptation_assessment["method_result"]["governance_decision"] == raw["governance"]["result"]
    )
    assert adaptation_assessment["method_result"]["operation_count"] == len(
        raw["operation_plan"]["operations"]
    )
    assert adaptation_assessment["scientific_boundary"]["official_comparison"] == ("NOT_EXECUTED")
    assert {row["assessment_status"] for row in adaptation_assessment["assessments"]} <= {
        "RETAIN_CANDIDATE",
        "ADAPTATION_NEEDED",
        "NOT_EVALUABLE",
        "MISMATCH_DETECTED",
    }
    assert all(
        row["requirement_inventory"]["universe_completeness"] == "UNKNOWN"
        for row in adaptation_assessment["assessments"]
    )
    assert all(
        "fitness/catalog/architectural-obligations.yaml"
        in {source["path"] for source in row["requirement_inventory"]["source_refs"]}
        for row in adaptation_assessment["assessments"]
    )
    assert not any(
        "adaptation-necessity" in item["path"] or "inspection-coverage" in item["path"]
        for item in method_manifest["files"]
    )
    for observation in record["evaluator_observations"]:
        state_label = "before" if observation["architecture_state"].startswith("A0_3") else "after"
        configuration_artifact = (
            run_root
            / "PSI/evaluator-observations/implementation"
            / observation["evaluator_id"]
            / Path(observation["configuration_path"]).name
        )
        assert (
            hashlib.sha256(configuration_artifact.read_bytes()).hexdigest()
            == observation["configuration_sha256"]
        )
        coverage_path = (
            run_root
            / "PSI/evaluator-observations"
            / state_label
            / observation["evaluator_id"]
            / "inspection-coverage.json"
        )
        coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
        assert coverage["counts"]["expected_count"] == coverage["counts"]["verified_matching_count"]
        assert coverage["source_inspection_status"] == "COMPLETE"
        assert coverage_path.relative_to(run_root).as_posix() in record["output_checksums"]
    for assessment in adaptation_assessment["assessments"]:
        capability_inventory = assessment["capability_inventory"]
        assert capability_inventory["before_status"] == "VERIFIED_FOR_DECLARED_STATIC_SCOPE"
        assert capability_inventory["after_status"] == "VERIFIED_FOR_DECLARED_STATIC_SCOPE"
        assert {
            row["verification_status"] for row in capability_inventory["capabilities_before"]
        } == {"VERIFIED_STATIC_SCOPE"}
        assert {
            row["verification_status"] for row in capability_inventory["capabilities_after"]
        } == {"VERIFIED_STATIC_SCOPE"}
        assert {
            row["comparison_result"] for row in assessment["requirement_capability_comparison"]
        } == {"COVERED"}
    assert adaptation_assessment_path.relative_to(run_root).as_posix() in record["output_checksums"]
    runtime_inventory = json.loads((run_root / "provenance/runtime-inventory.json").read_text())
    adaptation_runtime_row = next(
        row
        for row in runtime_inventory["files"]
        if row["path"] == "experiments/execution/tooling/p_adaptation.py"
    )
    assert state_manifest_path.is_relative_to(run_root / "provenance")
    assert (
        state_manifest["manifests"][0]["sha256"]
        == record["transition"]["before_state_manifest_sha256"]
    )
    assert (
        state_manifest["manifests"][1]["sha256"]
        == record["transition"]["after_state_manifest_sha256"]
    )
    assert record["method_input"]["structural_manifest_path"] == (
        "architecture/states/A0_4_REPORT_QUERY_PORT.yaml"
    )
    observation = json.loads(
        (
            run_root / record["method_input"]["path"] / "architecture/structural-observations.json"
        ).read_text()
    )
    assert observation["source_commit_sha"] == record["transition"]["after_commit_sha"]
    assert observation["source_state"] == "after"
    assert raw["method_version"] == record["method_implementation"]["identity"]
    assert record["method_implementation"]["sha256"] == adaptation_runtime_row["sha256"]
    assert record["psi"]["execution_duration_ms"] >= 0
    assert record["psi"]["decision"] in {"HOLD", "REJECT", "ACCEPT"}
    assert all(row["path"] != state_manifest_path.name for row in method_manifest["files"])
    assert result["psi_decision"] == record["psi"]["decision"]
    assert record["transition"]["before_commit_sha"] == "26a9bb667da7d0938e38aca15d2bf29fd1de4829"
    assert record["transition"]["after_commit_sha"] == "d3101c0d3aa9b7b709253b6ec7518416f05f65b9"
    assert record["study_readiness"] == "NO_GO"
    assert record["measurement_status"] == "NOT_EXECUTED"
    assert record["p_algorithm_status"] == "NOT_READY"
    assert record["g1"] == "INCOMPLETE"
    assert record["g4"] == "NOT_AUTHORIZED"
    assert record["reference_gate"] == "NOT_READY"
    assert record["baseline"]["identity_status"] == "PROSPECTIVE_RECONSTRUCTION_NOT_HISTORICAL"
    assert record["baseline"]["approval_status"] == "NOT_APPROVED"
    assert record["baseline"]["method_input_authorized"] is False
    assert record["other_arms_or_case_outputs_used"] is False
    assert record["metrics"] == "NOT_MEASURED"
    assert record["psi"]["scoring"] == "NOT_EXECUTED"
    assert record["psi"]["prediction_emitted"] is (raw.get("prediction_v1") is not None)
    assert raw["result_contract_version"] == "MONO_CI_PSI_METHOD_RESULT_V2"
    assert raw["governance"]["result"] in {"HOLD", "REJECT", "ACCEPT"}
    if raw["governance"]["result"] == "ACCEPT":
        assert isinstance(raw.get("prediction_v1"), dict)
        assert isinstance(raw.get("candidate_v1"), dict)
    else:
        assert raw.get("prediction_v1") is None
        assert raw.get("candidate_v1") is None
    assert len(record["evaluator_observations"]) == 4
    assert {row["architecture_state"] for row in record["evaluator_observations"]} == {
        "A0_3_GOVERNED_MODULE_GRAPH",
        "A0_4_REPORT_QUERY_PORT",
    }
    assert all(row["execution_status"] == "COMPLETED" for row in record["evaluator_observations"])
    assert all(row["inspection_scope_sha256"] for row in record["evaluator_observations"])
    assert record["adaptation_evidence"]["trust_scope"] == "TEST_ONLY"
    assert raw["evidence_trust_scope"] == "TEST_ONLY"
    assert record["evidence_ledger"]["verified_fact_ids"] == [
        "FV01_AFTER",
        "FV01_BEFORE",
        "FV02_MODULES_ADDED",
        "FV03_MODULES_REMOVED",
    ]
    assert all(row["status"] == "UNKNOWN" for row in raw["after_applicability"]["results"])
    assert all(row["status"] == "UNKNOWN" for row in raw["candidate_coverage"]["obligations"])
    assert all(row["status"] == "UNKNOWN" for row in raw["current_pairs"])
    assert all(row["compliance_status"] == "COMPLIANT" for row in raw["current_pairs"])
    assert all(
        "EVALUATOR_INSPECTION_SCOPE_UNKNOWN" not in row["reason_codes"]
        for row in raw["current_pairs"]
    )

    inventory_paths = {
        path.relative_to(run_root).as_posix() for path in run_root.rglob("*") if path.is_file()
    }
    assert not any(
        path.startswith(("B0/", "CASE_", "EVAL-01", "EVAL-02")) for path in inventory_paths
    )
    assert not any("scorer" in path.lower() or "oracle" in path.lower() for path in inventory_paths)

    archive_path = tmp_path / "transition.zip"
    packed = pack_transition_archive(
        run_root,
        archive_path,
        ROOT,
        "https://github.com/Pan14ek/evofit-bench/actions/runs/123456",
        "mono-ci-psi-transition-test-1",
        "uv 0.9.0",
    )
    assert packed["verification_status"] == "PASS"
    extracted = tmp_path / "archive-readback"
    verified = verify_transition_archive(archive_path, extract_to=extracted)
    assert verified["verification_status"] == "PASS"
    extracted_record = verify_transition_run(extracted)
    assert extracted_record["psi"]["raw_result_sha256"] == record["psi"]["raw_result_sha256"]

    sidecar_bytes = state_manifest_path.read_bytes()
    state_manifest_path.write_bytes(sidecar_bytes + b" ")
    with pytest.raises(ContractValidationError, match="OUTPUT_CHECKSUM_MISMATCH"):
        verify_transition_run(run_root)
    state_manifest_path.write_bytes(sidecar_bytes)

    raw_path.write_bytes(raw_path.read_bytes() + b" ")
    with pytest.raises(ContractValidationError, match="RAW_RESULT_DIGEST_MISMATCH"):
        verify_transition_run(run_root)
    raw_path.write_bytes(raw_path.read_bytes()[:-1])

    evidence_path = run_root / record["adaptation_evidence"]["path"]
    evidence_bytes = evidence_path.read_bytes()
    evidence_path.write_bytes(evidence_bytes + b" ")
    with pytest.raises(ContractValidationError, match="ADAPTATION_EVIDENCE_DIGEST_MISMATCH"):
        verify_transition_run(run_root)
    evidence_path.write_bytes(evidence_bytes)


def test_transition_contract_rejects_official_status_promotion(tmp_path: Path) -> None:
    with pytest.raises(ProtocolError, match="OUTPUT_MUST_BE_NEW_AND_EXTERNAL"):
        run_transition(ROOT, ROOT / "temporary-psi-run", "DEV_PSI_TRANSITION_UNIT_02")
    assert not (ROOT / "temporary-psi-run").exists()

    invalid = {
        "schema_version": "MONO_CI_PSI_TRANSITION_RUN_V1",
        "execution_id": "DEV_PSI_TRANSITION_UNIT_02",
        "study_id": "MONO_CI_B0_PSI_DEVELOPMENT_TECHNICAL_VALIDATION",
        "mode": "DEVELOPMENT_METHOD_EXECUTION_ONLY",
        "unit_of_analysis": "ONE_A0_3_TO_A0_4_ARCHITECTURE_TRANSITION",
        "study_readiness": "GO",
        "measurement_status": "NOT_EXECUTED",
        "p_algorithm_status": "NOT_READY",
        "g1": "INCOMPLETE",
        "g4": "NOT_AUTHORIZED",
        "reference_gate": "NOT_READY",
    }
    with pytest.raises(ContractValidationError, match="validation failed"):
        validate_payload("mono_ci_psi_transition_run_v1.schema.json", invalid)


def test_v2_method_result_allows_each_decision_with_bounded_prediction_shape() -> None:
    _validate_method_result_v2(
        {"governance": {"result": "HOLD"}, "prediction_v1": None, "candidate_v1": None}
    )
    _validate_method_result_v2(
        {"governance": {"result": "REJECT"}, "prediction_v1": None, "candidate_v1": None}
    )
    _validate_method_result_v2(
        {
            "governance": {"result": "ACCEPT"},
            "prediction_v1": {"prediction_id": "synthetic"},
            "candidate_v1": {"candidate_id": "synthetic"},
        }
    )

    with pytest.raises(ProtocolError, match="ACCEPT_OUTPUT_MISSING"):
        _validate_method_result_v2(
            {"governance": {"result": "ACCEPT"}, "prediction_v1": None, "candidate_v1": None}
        )
    with pytest.raises(ProtocolError, match="NONACCEPT_PREDICTION_PRESENT"):
        _validate_method_result_v2(
            {
                "governance": {"result": "HOLD"},
                "prediction_v1": {"prediction_id": "synthetic"},
                "candidate_v1": {"candidate_id": "synthetic"},
            }
        )
