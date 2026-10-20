"""Adversarial checks for the B0/P DEVELOPMENT execution continuation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from experiments.execution.tooling.b0 import build_b0_prediction
from experiments.execution.tooling.b0p_execution import (
    B0PExecutionError,
    _expected_prediction_status,
    _import_linter_compliance,
    _prediction_binding_error,
    _unknown_pair_verification,
    _validate_completed_arm_prediction,
    _validate_rq1_claims,
    _validate_rq2_claims,
    _validate_unknown_resource_metrics,
    _verify_evaluator_records,
    _verify_p_unsealed_marker,
    _verify_run_inventory,
    _write_bytes_once,
    _write_final_checksums,
    _write_once,
    _write_run_checksums,
)
from experiments.execution.tooling.errors import SealedArtifactError
from experiments.execution.tooling.hashing import sha256_bytes
from experiments.execution.tooling.sealing import load_verified_prediction, seal_prediction

ARCH_SHA = "a" * 40
BUNDLE_SHA = "b" * 64


def test_prediction_must_bind_method_architecture_and_bundle() -> None:
    prediction = build_b0_prediction(ARCH_SHA, BUNDLE_SHA)

    assert (
        _prediction_binding_error(
            prediction,
            method_id="B0",
            architecture_source_sha=ARCH_SHA,
            input_bundle_sha256=BUNDLE_SHA,
        )
        is None
    )
    assert "architecture" in str(
        _prediction_binding_error(
            prediction,
            method_id="B0",
            architecture_source_sha="c" * 40,
            input_bundle_sha256=BUNDLE_SHA,
        )
    )
    assert "bundle" in str(
        _prediction_binding_error(
            prediction,
            method_id="B0",
            architecture_source_sha=ARCH_SHA,
            input_bundle_sha256="d" * 64,
        )
    )
    assert "method" in str(
        _prediction_binding_error(
            prediction,
            method_id="P",
            architecture_source_sha=ARCH_SHA,
            input_bundle_sha256=BUNDLE_SHA,
        )
    )
    assert (
        _prediction_binding_error(
            {},
            method_id="B0",
            architecture_source_sha=ARCH_SHA,
            input_bundle_sha256=BUNDLE_SHA,
        )
        == "method identity mismatch"
    )


def test_sealed_prediction_tampering_is_rejected(tmp_path: Path) -> None:
    output = tmp_path / "prediction"
    sealed = seal_prediction(build_b0_prediction(ARCH_SHA, BUNDLE_SHA), output)
    assert load_verified_prediction(output).sha256 == sealed.sha256

    prediction = output / "prediction.json"
    prediction.chmod(0o644)
    payload = json.loads(prediction.read_text(encoding="utf-8"))
    payload["input_bundle_sha256"] = "c" * 64
    prediction.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(SealedArtifactError, match="hash does not match"):
        load_verified_prediction(output)


def test_p_hold_requires_matching_no_prediction_marker() -> None:
    assert _expected_prediction_status("HOLD") == "NOT_EMITTED_GOVERNANCE_HOLD"
    marker: dict[str, Any] = {
        "prediction_status": "NOT_EMITTED_GOVERNANCE_HOLD",
        "architecture_source_sha": ARCH_SHA,
        "input_bundle_sha256": BUNDLE_SHA,
    }
    _verify_p_unsealed_marker(
        marker,
        governance_result="HOLD",
        arm_prediction_status="NOT_EMITTED_GOVERNANCE_HOLD",
        architecture_source_sha=ARCH_SHA,
        input_bundle_sha256=BUNDLE_SHA,
    )

    with pytest.raises(B0PExecutionError, match="another input bundle"):
        _verify_p_unsealed_marker(
            marker,
            governance_result="HOLD",
            arm_prediction_status="NOT_EMITTED_GOVERNANCE_HOLD",
            architecture_source_sha=ARCH_SHA,
            input_bundle_sha256="c" * 64,
        )
    with pytest.raises(B0PExecutionError, match="outside the V1 prediction contract"):
        _expected_prediction_status("NOT_RUN")


def test_completed_b0_arm_cannot_omit_its_sealed_prediction() -> None:
    arm = {
        "status": "COMPLETED",
        "prediction_status": "NOT_RUN",
        "prediction_path": None,
        "prediction_sha256": None,
    }
    with pytest.raises(B0PExecutionError, match="must have a sealed prediction"):
        _validate_completed_arm_prediction("B0", arm)

    arm["prediction_status"] = "SEALED"
    with pytest.raises(B0PExecutionError, match="prediction path is missing"):
        _validate_completed_arm_prediction("B0", arm)


def test_oracle_git_and_scorer_paths_are_forbidden_method_inputs() -> None:
    from experiments.execution.tooling.b0p_execution import (
        _contains_forbidden_method_input_path,
    )

    assert not _contains_forbidden_method_input_path(["fitness/obligations.yaml"])
    for forbidden in (
        ".git/config",
        "private/ground_truth.yaml",
        "scenario/expected_operations.json",
        "experiments/scorer.py",
    ):
        assert _contains_forbidden_method_input_path([forbidden])


def test_unknown_rq2_cannot_claim_shared_or_bound_denominator() -> None:
    _validate_rq2_claims(
        {
            "status": "UNKNOWN",
            "required_obligation_set_bound": False,
            "same_denominator_for_arms": False,
        }
    )
    with pytest.raises(B0PExecutionError, match="shared obligation denominator"):
        _validate_rq2_claims(
            {
                "status": "UNKNOWN",
                "required_obligation_set_bound": False,
                "same_denominator_for_arms": True,
            }
        )


def test_rq2_cannot_score_method_pair_diagnostics_as_independent_proof(
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run-current"
    p_output = run_root / "P"
    p_output.mkdir(parents=True)
    (p_output / "method_p_trace.json").write_text(
        json.dumps(
            {
                "current_pairs": [
                    {
                        "representation_id": "rep-a",
                        "obligation_id": "obl-a",
                        "status": "COMPLIANT",
                        "semantic_proof_status": "VERIFIED",
                    }
                ],
                "candidate_pairs": [],
            }
        ),
        encoding="utf-8",
    )
    pair_evidence = _unknown_pair_verification(run_root, p_output)
    assert pair_evidence["status"] == "UNKNOWN"
    assert pair_evidence["independently_verified_pair_count"] == 0
    assert pair_evidence["pairs"][0]["independent_verification"] == "UNKNOWN"

    with pytest.raises(B0PExecutionError, match="independent exact-pair semantic proofs"):
        _validate_rq2_claims(
            {
                "status": "SCORED",
                "required_obligation_set_bound": True,
                "same_denominator_for_arms": True,
            },
            pair_evidence,
        )


def test_rq1_scorer_requires_a_reference_established_before_predictions() -> None:
    rq1 = {"status": "NOT_EVALUABLE", "scorer_invoked": False}
    reference = {"status": "NOT_ESTABLISHED_BEFORE_PREDICTIONS"}
    _validate_rq1_claims(rq1, reference)

    with pytest.raises(B0PExecutionError, match="reference-availability record is missing"):
        _validate_rq1_claims(rq1, None)
    with pytest.raises(B0PExecutionError, match="incompatible status"):
        _validate_rq1_claims(rq1, {"status": "SEALED_AFTER_PREDICTIONS"})
    with pytest.raises(B0PExecutionError, match="cannot run without"):
        _validate_rq1_claims({"status": "NOT_EVALUABLE", "scorer_invoked": True}, reference)
    with pytest.raises(B0PExecutionError, match="no admissible RQ1 scoring reference"):
        _validate_rq1_claims({"status": "SCORED", "scorer_invoked": False}, reference)


def test_unknown_resource_metrics_do_not_encode_zero_or_estimates() -> None:
    _validate_unknown_resource_metrics(
        {
            "status": "UNKNOWN",
            "host_cpu_time_ns": None,
            "container_cpu_time_ns": None,
            "peak_rss_bytes": None,
        }
    )
    with pytest.raises(B0PExecutionError, match="cannot contain measured values"):
        _validate_unknown_resource_metrics(
            {
                "status": "UNKNOWN",
                "host_cpu_time_ns": 0,
                "container_cpu_time_ns": None,
                "peak_rss_bytes": None,
            }
        )


def test_import_linter_scope_mismatch_is_not_evaluable_even_on_exit_zero() -> None:
    assert (
        _import_linter_compliance(0, {"missing_targets": ["app.legacy"], "vacuous": False})
        == "NOT_EVALUABLE"
    )
    assert _import_linter_compliance(0, {"missing_targets": [], "vacuous": True}) == "NOT_EVALUABLE"
    assert _import_linter_compliance(0, {"missing_targets": [], "vacuous": False}) == "COMPLIANT"


def test_reused_evaluator_record_from_another_run_is_rejected(tmp_path: Path) -> None:
    run_root = tmp_path / "run-current"
    run_root.mkdir()
    prep: dict[str, Any] = {"source_revisions": {"architecture_after_sha": ARCH_SHA}}
    records = [
        {"evaluator_id": "import_linter", "run_id": "run-prior"},
        {"evaluator_id": "pytest_architecture", "run_id": "run-current"},
    ]

    with pytest.raises(B0PExecutionError, match="another run ID"):
        _verify_evaluator_records(run_root, records, prep)


def test_evaluator_rejects_wrong_source_revision_and_configuration(tmp_path: Path) -> None:
    run_root = tmp_path / "run-current"
    b0_manifest = run_root / "preparation_snapshot/method_inputs/b0/method_input.json"
    b0_manifest.parent.mkdir(parents=True)
    b0_manifest.write_text(json.dumps({"after_tree_sha": "tree-current"}), encoding="utf-8")
    raw = run_root / "raw"
    raw.mkdir()
    outputs: list[dict[str, Any]] = []
    for evaluator_id in ("import_linter", "pytest_architecture"):
        streams: dict[str, str] = {}
        for stream in ("stdout", "stderr"):
            path = raw / f"{evaluator_id}.{stream}"
            path.write_bytes(b"")
            streams[f"{stream}_path"] = path.relative_to(run_root).as_posix()
            streams[f"{stream}_sha256"] = sha256_bytes(b"")
        outputs.append(
            {
                "evaluator_id": evaluator_id,
                "run_id": "run-current",
                "source_revision": ARCH_SHA,
                "source_tree_sha": "tree-current",
                "configuration_sha256": "c" * 64,
                **streams,
            }
        )
    prep: dict[str, Any] = {
        "source_revisions": {"architecture_after_sha": ARCH_SHA},
        "b0": {"evaluator_configuration_sha256": "d" * 64},
    }

    outputs[1]["source_revision"] = "e" * 40
    with pytest.raises(B0PExecutionError, match="another architecture SHA"):
        _verify_evaluator_records(run_root, outputs, prep)

    outputs[1]["source_revision"] = ARCH_SHA
    with pytest.raises(B0PExecutionError, match="not frozen B0"):
        _verify_evaluator_records(run_root, outputs, prep)


def test_execution_artifacts_are_write_once(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.bin"
    _write_bytes_once(artifact, b"first")

    with pytest.raises(FileExistsError):
        _write_bytes_once(artifact, b"replacement")

    assert artifact.read_bytes() == b"first"


def test_execution_manifest_record_cannot_be_overwritten(tmp_path: Path) -> None:
    manifest = tmp_path / "execution_manifest.json"
    _write_once(manifest, {"run_id": "run-first"})

    with pytest.raises(FileExistsError):
        _write_once(manifest, {"run_id": "run-replacement"})

    assert json.loads(manifest.read_text(encoding="utf-8")) == {"run_id": "run-first"}


def test_post_execution_inventory_preserves_original_and_covers_appended_files(
    tmp_path: Path,
) -> None:
    original = tmp_path / "original.bin"
    _write_bytes_once(original, b"original")
    _write_run_checksums(tmp_path)
    original_inventory = (tmp_path / "SHA256SUMS").read_bytes()

    appended = tmp_path / "recovery.bin"
    _write_bytes_once(appended, b"recovery")
    _write_final_checksums(tmp_path)
    _verify_run_inventory(tmp_path)
    assert (tmp_path / "SHA256SUMS").read_bytes() == original_inventory

    appended.chmod(0o644)
    appended.write_bytes(b"tampered")
    with pytest.raises(B0PExecutionError, match="checksum mismatch"):
        _verify_run_inventory(tmp_path)


def test_direct_inventory_rejects_unlisted_files(tmp_path: Path) -> None:
    _write_bytes_once(tmp_path / "first.bin", b"first")
    _write_run_checksums(tmp_path)
    _write_bytes_once(tmp_path / "unlisted.bin", b"unlisted")

    with pytest.raises(B0PExecutionError, match="inventory differs"):
        _verify_run_inventory(tmp_path)


def test_run_inventory_leaves_nested_checksum_manifests_to_their_scope(
    tmp_path: Path,
) -> None:
    nested = tmp_path / "container_context/B0"
    nested.mkdir(parents=True)
    _write_bytes_once(nested / "source.py", b"source")
    nested_checksum = nested / "SHA256SUMS"
    _write_bytes_once(nested_checksum, b"nested checksum manifest")
    _write_bytes_once(tmp_path / "root-file.bin", b"root")
    _write_run_checksums(tmp_path)

    _verify_run_inventory(tmp_path)
    assert nested_checksum.exists()
