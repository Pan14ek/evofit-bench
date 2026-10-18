"""End-to-end contract tests for the EXP-03 DEVELOPMENT evidence bridge."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from experiments.execution.tooling.p_adaptation import verify_v3_p_bundle
from experiments.execution.tooling.p_applicability import EvidenceLedger
from experiments.execution.tooling.p_policy_source_v3 import (
    export_method_inputs_v3,
    package_policy_source_v3,
)
from scripts import exp01_evidence_contract as contract
from scripts import exp02_fitness_evidence as exp02
from scripts.exp03_method_bridge import (
    MANIFEST_FILENAME,
    P_TRACE_FILENAME,
    _load_exp02,
    _map_representations,
    _record_bindings,
    build_integration_artifact,
    validate_integration_output,
    write_integration_run,
)
from tests.unit.test_exp02_fitness_evidence import _valid_bundle

BASE_REVISION = "5bb4354822a390f068c259cc2fe3caa44568b7d1"
FROZEN_A0_REVISION = "b78b0967be937634b7762baccf5ac6892b279a73"
ALTERNATE_A0_1_REVISION = "2faf19204fc8c8e67a6cf05cdf71291f997658e9"
POLICY_AS_OF = "2026-10-14T00:00:00Z"
POLICY_SOURCE = contract.ROOT / "experiments/execution/policy-pilot/v1/source"


def _write_exp02_run(
    temporary_directory: Path,
    *,
    missing_evaluator: bool = False,
    missing_metric: bool = False,
    noncompliant_layering: bool = False,
) -> tuple[Path, dict[str, Any]]:
    """Create a digest-valid EXP-02 fixture using the repository's real adapter."""
    run_dir, bundle, configuration_bytes = _valid_bundle(temporary_directory)
    bundle["source_revision"]["commit_sha"] = BASE_REVISION
    for record in bundle["records"]:
        record["source_revision"] = BASE_REVISION
        if record["lifecycle_stage"] == "runtime":
            record["source_binding"]["collector_source_revision"] = BASE_REVISION
            if missing_evaluator:
                record["record_id"] = "unconfigured-runtime-record"
            if missing_metric:
                record["measurements"] = {}
        if noncompliant_layering and record["record_id"] == "exp01-ci-import-linter-v1":
            record["execution_verdict"] = "violations_detected"
            record["exit_status"] = 1
            record["measurements"]["dependency_rule_violations"] = 1

    evidence = exp02.build_representation_evidence(bundle, run_dir, configuration_bytes)
    evidence_reference = contract.write_artifact(
        run_dir,
        exp02.REPRESENTATION_EVIDENCE_FILENAME,
        (json.dumps(evidence, indent=2, sort_keys=True) + "\n").encode(),
        media_type="application/json",
        role="fitness_representation_evidence",
    )
    bundle["fitness_representation_evidence"] = evidence_reference
    _, validated_bundle = contract.write_bundle(run_dir, bundle)
    return run_dir, validated_bundle


@pytest.fixture(scope="session")
def p_input_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Export the real DRAFT/OPEN policy-pilot source through the existing V3 exporter."""
    root = tmp_path_factory.mktemp("exp03-v3-p")
    policy_bundle = root / "policy-source"
    method_bundle = root / "method-input"
    package_policy_source_v3(POLICY_SOURCE, policy_bundle, "EXP03_DRAFT_OPEN_TEST")
    export_method_inputs_v3(
        contract.ROOT,
        policy_bundle,
        method_bundle,
        "P",
        FROZEN_A0_REVISION,
        BASE_REVISION,
        POLICY_AS_OF,
    )
    return method_bundle


@pytest.fixture(scope="session")
def mismatched_p_input_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Export a valid V3 input whose after revision predates the EXP-02 source."""
    root = tmp_path_factory.mktemp("exp03-mismatched-v3-p")
    policy_bundle = root / "policy-source"
    method_bundle = root / "method-input"
    package_policy_source_v3(POLICY_SOURCE, policy_bundle, "EXP03_DRAFT_OPEN_MISMATCH_TEST")
    export_method_inputs_v3(
        contract.ROOT,
        policy_bundle,
        method_bundle,
        "P",
        FROZEN_A0_REVISION,
        ALTERNATE_A0_1_REVISION,
        POLICY_AS_OF,
    )
    return method_bundle


def _mapping_by_obligation(manifest: dict[str, Any], obligation: str) -> dict[str, Any]:
    return next(
        item for item in manifest["representation_mappings"] if item["obligation_id"] == obligation
    )


def test_real_exp02_run_executes_existing_p_pipeline_and_preserves_hold(
    tmp_path: Path, p_input_dir: Path
) -> None:
    run_dir, _ = _write_exp02_run(tmp_path)

    output_dir = tmp_path / "exp03-output"
    manifest, digest = write_integration_run(run_dir, output_dir, p_input_dir=p_input_dir)
    trace = json.loads((output_dir / P_TRACE_FILENAME).read_text(encoding="utf-8"))

    assert digest == contract.sha256_bytes((output_dir / MANIFEST_FILENAME).read_bytes())
    assert manifest["integration_status"] == "completed_with_hold"
    assert manifest["method_p"]["input_status"] == "verified"
    assert (
        manifest["method_p"]["input_manifest_reference"]["sha256"]
        == manifest["method_p"]["input_manifest_sha256"]
    )
    assert manifest["method_p"]["delta_a1_revision_binding"] == "verified"
    assert manifest["method_p"]["execution_status"] == "completed"
    assert manifest["method_p"]["governance_result"] == "HOLD"
    assert manifest["method_p"]["prediction_v1_emitted"] is False
    assert trace["exp02_observations_used_as_semantic_pair_evidence"] is False
    assert trace["adaptation_evidence_sidecar_supplied"] is False
    assert trace["prediction_v1"] is None
    assert trace["current_coverage"]["status"] == "UNKNOWN"
    assert "MANDATORY_CLASSIFICATION_UNRESOLVED" in manifest["method_p"]["reason_codes"]
    assert manifest["coverage_claims"] == {
        "Coverage_P": "not_assessed",
        "Coverage_ref": "not_established",
        "semantic_validity": "not_independently_validated",
    }
    assert (
        sum(
            item["mapping_status"] == "candidate_only"
            for item in manifest["representation_mappings"]
        )
        == 4
    )
    assert (
        sum(item["mapping_status"] == "unsupported" for item in manifest["representation_mappings"])
        == 1
    )


def test_original_evaluator_artifact_references_survive_unchanged(
    tmp_path: Path, p_input_dir: Path
) -> None:
    run_dir, bundle = _write_exp02_run(tmp_path)

    manifest, _ = build_integration_artifact(run_dir, p_input_dir=p_input_dir)

    assert manifest["exp02_input"]["input_artifacts"] == bundle["input_artifacts"]
    by_id = {record["record_id"]: record for record in manifest["exp02_input"]["evaluator_records"]}
    original = {record["record_id"]: record for record in bundle["records"]}
    assert set(by_id) == set(original)
    for record_id, record in by_id.items():
        assert record["raw_output_artifacts"] == original[record_id]["raw_output_artifacts"]
    mappings = manifest["representation_mappings"]
    assert all(mapping["source_revision"] == BASE_REVISION for mapping in mappings)
    assert all(mapping["semantic_pair_proof_status"] == "not_supplied" for mapping in mappings)


def test_incompatible_architecture_revision_blocks_method_p_execution(
    tmp_path: Path, mismatched_p_input_dir: Path
) -> None:
    run_dir, _ = _write_exp02_run(tmp_path)

    manifest, trace = build_integration_artifact(run_dir, p_input_dir=mismatched_p_input_dir)

    assert trace is None
    assert manifest["method_p"]["input_status"] == "incompatible"
    assert manifest["method_p"]["delta_a1_revision_binding"] == "mismatch"
    assert manifest["method_p"]["execution_status"] == "not_run"
    assert any(item["code"] == "P_INPUT_AFTER_REVISION_MISMATCH" for item in manifest["blockers"])


def test_modified_representation_evidence_is_rejected(tmp_path: Path) -> None:
    run_dir, bundle = _write_exp02_run(tmp_path)
    evidence_path = run_dir / bundle["fitness_representation_evidence"]["path"]
    evidence_path.write_bytes(evidence_path.read_bytes() + b" ")

    with pytest.raises(ValueError, match="artifact (size|digest) mismatch"):
        build_integration_artifact(run_dir)


@pytest.mark.parametrize(
    ("fixture_options", "representation_id", "expected_status"),
    [
        (
            {"missing_evaluator": True},
            "REP_A01_REL_HTTP_5XX_RUNTIME",
            "missing",
        ),
        (
            {"missing_metric": True},
            "REP_A01_REL_HTTP_5XX_RUNTIME",
            "missing",
        ),
    ],
)
def test_missing_evaluator_or_metric_remains_unresolved(
    tmp_path: Path,
    fixture_options: dict[str, bool],
    representation_id: str,
    expected_status: str,
) -> None:
    run_dir, _ = _write_exp02_run(tmp_path, **fixture_options)

    manifest, _ = build_integration_artifact(run_dir)

    mapping = next(
        item
        for item in manifest["representation_mappings"]
        if item["exp02_representation_id"] == representation_id
    )
    if fixture_options.get("missing_evaluator"):
        assert mapping["evaluator_execution"]["status"] == expected_status
        assert mapping["compliance_observation"]["status"] == "unknown"
    else:
        assert mapping["metrics"][0]["status"] == expected_status
    assert mapping["semantic_pair_proof_status"] == "not_supplied"
    assert mapping["coverage_claim_status"] == "not_established"


def test_unverified_runtime_identity_never_becomes_semantic_pair_proof(
    tmp_path: Path, p_input_dir: Path
) -> None:
    run_dir, _ = _write_exp02_run(tmp_path)

    manifest, _ = build_integration_artifact(run_dir, p_input_dir=p_input_dir)

    runtime = _mapping_by_obligation(manifest, "R_HTTP_5XX")
    assert runtime["evaluator_execution"]["runtime_source_binding_status"] == "unverified"
    assert runtime["semantic_pair_proof_status"] == "not_supplied"
    assert runtime["coverage_claim_status"] == "not_established"
    assert any(
        "not verified against the application source revision" in limitation
        for limitation in runtime["limitations"]
    )


def test_actual_evaluator_noncompliance_is_separate_from_pair_validity(
    tmp_path: Path, p_input_dir: Path
) -> None:
    run_dir, _ = _write_exp02_run(tmp_path, noncompliant_layering=True)

    manifest, _ = build_integration_artifact(run_dir, p_input_dir=p_input_dir)

    layering = _mapping_by_obligation(manifest, "AC_LAYERING")
    assert layering["evaluator_execution"]["execution_verdict"] == "violations_detected"
    assert layering["compliance_observation"]["status"] == "nonconforming"
    assert layering["mapping_status"] == "candidate_only"
    assert layering["semantic_pair_proof_status"] == "not_supplied"


def test_unsupported_stage_and_unrepresented_scope_fail_closed(
    tmp_path: Path, p_input_dir: Path
) -> None:
    run_dir, _ = _write_exp02_run(tmp_path)
    _, evidence, configuration, _ = _load_exp02(run_dir)
    unsupported_evidence = copy.deepcopy(evidence)
    unsupported_evidence["representations"][0]["lifecycle_stage"] = "deployment"

    mappings = _map_representations(
        unsupported_evidence,
        configuration,
        verify_v3_p_bundle(
            p_input_dir,
            evidence_ledger=EvidenceLedger({}, {}, {}),
        ).representations,
        p_after_revision=BASE_REVISION,
    )

    unsupported = next(item for item in mappings if item["source_stage"] == "deployment")
    assert unsupported["stage_mapping_status"] == "unsupported"
    assert "UNSUPPORTED_LIFECYCLE_STAGE" in unsupported["reason_codes"]
    assert any(item["scope_mapping_status"] == "unrepresented" for item in mappings)
    assert all(item["semantic_pair_proof_status"] == "not_supplied" for item in mappings)
    assert evidence["run_id"] == "exp02-adapter-test"


def test_missing_policy_authority_and_exact_pair_proof_produce_unknown_hold(
    tmp_path: Path, p_input_dir: Path
) -> None:
    run_dir, _ = _write_exp02_run(tmp_path)

    manifest, trace = build_integration_artifact(run_dir, p_input_dir=p_input_dir)

    assert trace is not None
    assert manifest["method_p"]["governance_result"] == "HOLD"
    assert trace["governance"]["result"] == "HOLD"
    assert "POLICY_AUTHORITY_UNVERIFIED" in manifest["method_p"]["reason_codes"] or any(
        "AUTHORITY" in code for code in manifest["method_p"]["reason_codes"]
    )
    assert "MANDATORY_CLASSIFICATION_UNRESOLVED" in manifest["method_p"]["reason_codes"]
    assert all(pair["status"] == "UNKNOWN" for pair in trace["current_pairs"])
    assert trace["current_coverage"]["status"] == "UNKNOWN"
    assert trace["exp02_observations_used_as_semantic_pair_evidence"] is False


def test_integration_does_not_emit_measured_da01_prediction(
    tmp_path: Path, p_input_dir: Path
) -> None:
    run_dir, _ = _write_exp02_run(tmp_path)

    manifest, trace = build_integration_artifact(run_dir, p_input_dir=p_input_dir)

    assert trace is not None
    assert manifest["exp02_input"]["bundle_status"] == "complete"
    assert manifest["method_p"]["prediction_v1_emitted"] is False
    assert trace["prediction_v1"] is None
    assert "measured_results" not in manifest
    assert manifest["coverage_claims"]["Coverage_ref"] == "not_established"


def test_no_private_oracle_or_scorer_artifacts_are_required(tmp_path: Path) -> None:
    run_dir, _ = _write_exp02_run(tmp_path)

    manifest, trace = build_integration_artifact(run_dir)

    source_paths = [
        item["source_path"] or "" for item in manifest["exp02_input"]["input_artifacts"]
    ]
    assert all("ground_truth" not in path and "scorer" not in path for path in source_paths)
    assert trace is None
    assert manifest["method_p"]["execution_status"] == "not_run"
    assert manifest["coverage_claims"]["Coverage_P"] == "not_assessed"


def test_complete_integration_artifact_round_trips_and_checks_digests(
    tmp_path: Path, p_input_dir: Path
) -> None:
    run_dir, _ = _write_exp02_run(tmp_path)
    output_dir = tmp_path / "round-trip"
    expected, _ = write_integration_run(run_dir, output_dir, p_input_dir=p_input_dir)

    actual = validate_integration_output(output_dir)

    assert actual == expected
    trace_reference = actual["method_p"]["trace_reference"]
    assert trace_reference["path"] == P_TRACE_FILENAME
    (output_dir / P_TRACE_FILENAME).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="output digest mismatch"):
        validate_integration_output(output_dir)


def test_conflicting_source_revision_is_rejected_before_packaging(tmp_path: Path) -> None:
    run_dir, bundle, configuration_bytes = _valid_bundle(tmp_path)
    bundle["source_revision"]["commit_sha"] = BASE_REVISION
    for record in bundle["records"]:
        record["source_revision"] = BASE_REVISION
    bundle["records"][-1]["source_revision"] = "c" * 40

    with pytest.raises(ValueError, match="source revision conflicts"):
        exp02.build_representation_evidence(bundle, run_dir, configuration_bytes)


def test_contradictory_evaluator_binding_is_rejected(tmp_path: Path) -> None:
    _, _, configuration_bytes = _valid_bundle(tmp_path)
    configuration = exp02.load_fitness_configuration(configuration_bytes)
    conflicting = copy.deepcopy(configuration)
    conflicting["representations"][-1]["evaluator"]["scope_id"] = "different.scope"

    with pytest.raises(ValueError, match="contradictory evaluator record binding"):
        _record_bindings(conflicting)


def test_duplicate_canonical_pair_binding_is_rejected(tmp_path: Path, p_input_dir: Path) -> None:
    run_dir, _ = _write_exp02_run(tmp_path)
    _, evidence, configuration, _ = _load_exp02(run_dir)
    duplicate_pair_evidence = copy.deepcopy(evidence)
    duplicate_pair_evidence["representations"].append(
        copy.deepcopy(duplicate_pair_evidence["representations"][1])
    )
    p_bundle = verify_v3_p_bundle(
        p_input_dir,
        evidence_ledger=EvidenceLedger({}, {}, {}),
    )

    with pytest.raises(ValueError, match="duplicate or contradictory canonical pair binding"):
        _map_representations(
            duplicate_pair_evidence,
            configuration,
            p_bundle.representations,
            p_after_revision=BASE_REVISION,
        )


def test_no_v3_input_is_reported_as_an_explicit_blocker(tmp_path: Path) -> None:
    run_dir, _ = _write_exp02_run(tmp_path)

    manifest, trace = build_integration_artifact(run_dir)

    assert trace is None
    assert manifest["method_p"]["input_status"] == "not_supplied"
    assert manifest["method_p"]["execution_status"] == "not_run"
    assert any(item["code"] == "P_V3_INPUT_REQUIRED" for item in manifest["blockers"])
