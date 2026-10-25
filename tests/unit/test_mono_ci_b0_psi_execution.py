"""Contracts for the MONO CI B0/Ψ DEVELOPMENT execution supplement."""

from __future__ import annotations

import copy
import json
import zipfile
from pathlib import Path
from typing import Any, cast

import pytest

from architecture.acceptance.a1.engine import inspect_source_scope, load_configuration
from experiments.execution.tooling import mono_ci_b0_psi_archive as archive_module
from experiments.execution.tooling import mono_ci_b0_psi_execution as execution_module
from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import (
    ContractValidationError,
    MethodNotReadyError,
)
from experiments.execution.tooling.hashing import pretty_json_bytes, sha256_bytes, sha256_file
from experiments.execution.tooling.mono_ci_b0_psi_execution import (
    DEV_RUN_SCHEMA,
    _validate_bundle_file,
    _validate_raw_evaluator_evidence,
    _verify_evaluator_binding,
    _verify_execution_input_binding,
    materialize_development_inputs,
    verify_arm_input_bundle,
    verify_development_result,
    verify_execution_proposal,
)
from experiments.execution.tooling.mono_ci_b0_psi_execution import (
    execute_official_study as _execute_official_study,
)
from experiments.execution.tooling.mono_ci_b0_psi_scoring import (
    score_development_run,
    verify_scoring_assessment,
)

ROOT = Path(__file__).resolve().parents[2]


def _materialize(tmp_path: Path, execution_id: str = "DEV_MONO_CI_TEST") -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    output = tmp_path / execution_id
    materialize_development_inputs(ROOT, output, execution_id)
    return output


def _development_record(execution_id: str, output_checksums: dict[str, str]) -> dict[str, Any]:
    cases = []
    for case_number in range(1, 5):
        case_id = f"CASE_0{case_number}"
        evaluator_records = []
        for evaluator_id in ("AC_PUBLIC_API", "AC_MODULE_GRAPH"):
            raw_path = f"B0/raw/{case_id}/{evaluator_id}.json"
            evaluator_records.append(
                {
                    "evaluator_id": evaluator_id,
                    "version": "1.0.0",
                    "source_sha256": "d" * 64,
                    "configuration_sha256": "e" * 64,
                    "exit_code": 0,
                    "compliance": "COMPLIANT",
                    "raw_output_path": raw_path,
                    "raw_output_sha256": output_checksums.get(raw_path, "f" * 64),
                }
            )
        cases.append(
            {
                "case_id": case_id,
                "source_commit_sha": "a" * 40,
                "repository_tree_sha": "b" * 40,
                "application_tree_sha": "c" * 40,
                "status": "DEVELOPMENT_ONLY_EXECUTED",
                "scientific_applicability": "UNKNOWN",
                "fitness_validity": "UNKNOWN",
                "input_bundle_sha256": "0" * 64,
                "execution_binding": {
                    "workspace_kind": "GIT_CHECKOUT_BYTE_EQUIVALENT_TO_VERIFIED_BUNDLE",
                    "checkout_commit_sha": "a" * 40,
                    "repository_tree_sha": "b" * 40,
                    "application_tree_sha": "c" * 40,
                    "source_file_count": 1,
                    "source_file_map_sha256": "1" * 64,
                    "input_bundle_sha256": "0" * 64,
                    "target_state_manifest_path": "architecture/state-target.yaml",
                    "target_state_manifest_sha256": "2" * 64,
                    "evaluator_configurations": [
                        {
                            "evaluator_id": "AC_PUBLIC_API",
                            "bundle_path": "evaluators/AC_PUBLIC_API.yaml",
                            "configuration_sha256": "e" * 64,
                        },
                        {
                            "evaluator_id": "AC_MODULE_GRAPH",
                            "bundle_path": "evaluators/AC_MODULE_GRAPH.yaml",
                            "configuration_sha256": "e" * 64,
                        },
                    ],
                },
                "evaluators": evaluator_records,
                "technical_duration_ns": 10,
                "result_paths": [item["raw_output_path"] for item in evaluator_records],
            }
        )
    return {
        "schema_version": "MONO_CI_B0_PSI_DEV_RUN_V1",
        "execution_id": execution_id,
        "study_id": "MONO_CI_B0_PSI_DEVELOPMENT_TECHNICAL_VALIDATION",
        "parent_study_id": "MONO_CI_B0_PSI_COMPARISON_V1",
        "mode": "DEVELOPMENT_TECHNICAL_VALIDATION_ONLY",
        "study_readiness": "NO_GO",
        "measurement_status": "NOT_EXECUTED",
        "baseline": {
            "configuration_id": "MONO_CI_RECONSTRUCTED_B0_A03_V1",
            "configuration_sha256": "a" * 64,
            "identity_status": "PROSPECTIVE_RECONSTRUCTION_NOT_HISTORICAL",
            "approval_status": "NOT_APPROVED",
        },
        "common_input_parity": {
            "status": "PASS_DEVELOPMENT_COMMON_INPUTS_ONLY",
            "case_count": 4,
            "common_input_ids": ["SOURCE"],
        },
        "arms": {
            "B0": {
                "status": "DEVELOPMENT_EVALUATOR_PROBE_ONLY",
                "case_results": cases,
                "adaptation_operation": None,
                "governance_decision": None,
                "technical_duration_boundary": (
                    "CASE_START_THROUGH_RAW_EVALUATOR_OUTPUT_CHECKSUM_SEAL"
                ),
            },
            "PSI": {
                "status": "BLOCKED_NOT_EXECUTED",
                "reason": "P_ALGORITHM_STATUS_NOT_READY",
                "prediction_emitted": False,
                "operation_emitted": False,
                "governance_decision_emitted": False,
            },
        },
        "metrics": {
            "operation_selection_correctness": {"B0": "N/A", "PSI": "NOT_EVALUABLE"},
            "governance_decision_correctness": {"B0": "N/A", "PSI": "NOT_EVALUABLE"},
            "current_configuration_verified_coverage": {
                "B0": "NOT_EVALUABLE",
                "PSI": "NOT_EVALUABLE",
            },
            "controlled_violation_detection": {"B0": "NOT_MEASURED", "PSI": "NOT_MEASURED"},
            "stale_or_semantically_invalid_representations": {
                "B0": "NOT_EVALUABLE",
                "PSI": "NOT_EVALUABLE",
            },
            "assessed_candidate_coverage": {"B0": "N/A", "PSI": "NOT_MEASURED"},
            "actual_post_adaptation_coverage": {"B0": "N/A", "PSI": "NOT_MEASURED"},
            "end_to_end_case_execution_duration": {"B0": "NOT_MEASURED", "PSI": "NOT_MEASURED"},
        },
        "scoring": "NOT_EXECUTED_NO_SCORER_REFERENCE",
        "output_checksums": output_checksums or {"B0/raw/CASE_01/AC_PUBLIC_API.json": "f" * 64},
    }


def _case_execution_context(
    tmp_path: Path,
) -> tuple[Path, Path, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], Path, Path]:
    run_root = _materialize(tmp_path / "run", "DEV_MONO_CI_BINDING")
    case_manifest = json.loads(
        (ROOT / "experiments/execution/mono-ci-b0-psi-v1/CASE_MANIFEST_V1.json").read_text()
    )
    inputs = json.loads(
        (ROOT / "experiments/execution/mono-ci-b0-psi-v1/INPUTS_V1.json").read_text()
    )
    source = next(row for row in inputs["case_sources"] if row["case_id"] == "CASE_01")
    bare = tmp_path / "case-source.git"
    execution_module._git_run(ROOT, ("clone", "--bare", "--shared", str(ROOT), str(bare)))
    execution_module._fetch_case_bundles(ROOT, bare, case_manifest)
    checkout = tmp_path / "CASE_01"
    execution_module._git_run(
        ROOT,
        ("clone", "--quiet", "--shared", "--no-checkout", str(bare), str(checkout)),
    )
    execution_module._git_run(
        ROOT,
        ("-C", str(checkout), "checkout", "--quiet", "--detach", source["source_commit_sha"]),
    )
    proposal_root = ROOT / "experiments/execution/mono-ci-b0-psi-execution-v1"
    baseline_config = json.loads((proposal_root / "RECONSTRUCTED_B0_A03_V1.json").read_text())
    baseline = verify_execution_proposal(ROOT)
    bundle_root = run_root / "B0/input_bundle/CASE_01"
    manifest = verify_arm_input_bundle(bundle_root, expected_arm="B0")
    return run_root, bundle_root, manifest, source, baseline_config, baseline, bare, checkout


def _reseal_bundle_with_modified_target_state(bundle_root: Path) -> dict[str, Any]:
    manifest_path = bundle_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    state_path = bundle_root / "architecture/state-target.yaml"
    state_bytes = state_path.read_bytes() + b"# resealed tamper\n"
    state_path.write_bytes(state_bytes)
    for record in manifest["files"]:
        if record["path"] == "architecture/state-target.yaml":
            record["size_bytes"] = len(state_bytes)
            record["sha256"] = sha256_bytes(state_bytes)
            break
    manifest["common_input_sha256"] = sha256_bytes(
        execution_module._canonical_json(
            {
                "case": manifest["case"],
                "baseline_configuration_sha256": manifest["baseline_configuration_sha256"],
                "common_input_ids": manifest["common_input_ids"],
                "files": manifest["files"],
            }
        )
    )
    manifest["bundle_sha256"] = execution_module._bundle_digest(manifest)
    manifest_path.write_bytes(pretty_json_bytes(manifest))
    (bundle_root / "SHA256SUMS").unlink()
    execution_module._write_checksums(bundle_root, exclude={"SHA256SUMS"})
    return cast(dict[str, Any], manifest)


def _development_fake_evaluator(
    baseline: dict[str, Any], received_inputs: list[tuple[Path, Path, Path]] | None = None
) -> Any:
    representations = {row["evaluator_id"]: row for row in baseline["representations"]}

    def fake_evaluator(
        evaluator_id: str,
        repository: Path,
        configuration_path: Path,
        state_manifest_path: Path,
        _state_id: str,
        source_commit_sha: str,
        _analyzer: Any,
        *,
        evidence_root: Path | None = None,
    ) -> dict[str, Any]:
        representation = representations[evaluator_id]
        if evidence_root is None:
            raise AssertionError("evaluator evidence root must be the arm input bundle")
        if configuration_path != evidence_root / "evaluators" / f"{evaluator_id}.yaml":
            raise AssertionError("evaluator configuration did not come from the arm bundle")
        if state_manifest_path != evidence_root / "architecture/state-target.yaml":
            raise AssertionError("evaluator state manifest did not come from the arm bundle")
        if received_inputs is not None:
            received_inputs.append((configuration_path, state_manifest_path, evidence_root))
        inventory = inspect_source_scope(repository, load_configuration(configuration_path))
        return {
            "architecture": {
                "target_source_sha": source_commit_sha,
                "expected_source_sha": source_commit_sha,
                "manifest_state_status": "MATCHED",
                "source_sha_status": "MATCHED",
                "manifest_root": "evidence",
                "manifest_path": "architecture/state-target.yaml",
                "manifest_digest": sha256_file(state_manifest_path),
                "subject_source_dirty": False,
            },
            "evaluator": {
                "id": evaluator_id,
                "version": representation["evaluator_version"],
                "source_digest": representation["evaluator_source_sha256"],
                "configuration_digest": sha256_file(configuration_path),
            },
            "source_scope": {
                "inspected_paths": inventory.source_files,
                "source_file_digests": inventory.file_digests,
            },
            "result": {"execution_status": "COMPLETED", "compliance": "COMPLIANT"},
        }

    return fake_evaluator


def test_reconstruction_is_explicitly_prospective_and_source_pinned() -> None:
    result = verify_execution_proposal(ROOT)
    assert result["identity_status"] == "PROSPECTIVE_RECONSTRUCTION_NOT_HISTORICAL"
    assert result["approval_status"] == "NOT_APPROVED"
    assert result["study_readiness"] == "NO_GO"


def test_official_execution_stops_at_existing_readiness_and_method_guards() -> None:
    with pytest.raises(MethodNotReadyError, match="STUDY_NO_GO"):
        _execute_official_study()


def test_development_runner_records_b0_probe_and_keeps_psi_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    received_inputs: list[tuple[Path, Path, Path]] = []
    baseline = json.loads(
        (
            ROOT / "experiments/execution/mono-ci-b0-psi-execution-v1/RECONSTRUCTED_B0_A03_V1.json"
        ).read_text()
    )
    monkeypatch.setattr(
        execution_module, "run_evaluator", _development_fake_evaluator(baseline, received_inputs)
    )
    output = tmp_path / "runner-output"
    result = execution_module.run_development_validation(ROOT, output, "DEV_MONO_CI_RUNNER_TEST")
    run = verify_development_result(output)

    assert result["B0"] == "DEVELOPMENT_EVALUATOR_PROBE_ONLY"
    assert result["PSI"] == "BLOCKED_NOT_EXECUTED"
    assert run["study_readiness"] == "NO_GO"
    assert run["measurement_status"] == "NOT_EXECUTED"
    assert run["arms"]["B0"]["adaptation_operation"] is None
    assert run["arms"]["B0"]["governance_decision"] is None
    assert run["arms"]["PSI"]["operation_emitted"] is False
    assert len(received_inputs) == 8
    assert all("B0/input_bundle/" in str(bundle) for _, _, bundle in received_inputs)
    assert len(run["arms"]["B0"]["case_results"]) == 4
    assert all(
        case["status"] == "DEVELOPMENT_ONLY_EXECUTED"
        and case["technical_duration_ns"] >= 0
        and len(case["evaluators"]) == 2
        and case["execution_binding"]["workspace_kind"]
        == "GIT_CHECKOUT_BYTE_EQUIVALENT_TO_VERIFIED_BUNDLE"
        for case in run["arms"]["B0"]["case_results"]
    )


def test_execution_binding_proves_checkout_source_matches_sealed_bundle(tmp_path: Path) -> None:
    (
        _run_root,
        bundle_root,
        manifest,
        source,
        baseline_config,
        baseline,
        bare,
        checkout,
    ) = _case_execution_context(tmp_path)

    binding = _verify_execution_input_binding(
        bare, checkout, bundle_root, manifest, source, baseline_config, baseline
    )

    bundled_source = execution_module._bundle_application_files(bundle_root, manifest)
    checkout_source = execution_module._checkout_application_files(checkout)
    assert bundled_source == checkout_source
    assert binding["source_file_count"] == len(bundled_source)
    assert binding["source_file_map_sha256"] == sha256_bytes(
        execution_module._canonical_json(
            [
                {"path": path, "sha256": sha256_bytes(content)}
                for path, content in sorted(bundled_source.items())
            ]
        )
    )
    assert (
        binding["target_state_manifest_sha256"]
        == manifest["files"][
            next(
                index
                for index, item in enumerate(manifest["files"])
                if item["path"] == "architecture/state-target.yaml"
            )
        ]["sha256"]
    )


def test_runner_rejects_modified_checkout_source_before_evaluator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = execution_module._verify_checkout_identity
    changed = False
    evaluator_called = False

    def mutate_after_identity(checkout: Path, source: dict[str, Any]) -> None:
        nonlocal changed
        original(checkout, source)
        if source["case_id"] == "CASE_01" and not changed:
            source_file = next((checkout / "app").rglob("*.py"))
            source_file.write_bytes(source_file.read_bytes() + b"# post-verification mutation\n")
            changed = True

    def forbidden_evaluator(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        nonlocal evaluator_called
        evaluator_called = True
        return {}

    monkeypatch.setattr(execution_module, "_verify_checkout_identity", mutate_after_identity)
    monkeypatch.setattr(execution_module, "run_evaluator", forbidden_evaluator)
    with pytest.raises(ContractValidationError, match="EXECUTION_SOURCE_BYTES_MISMATCH"):
        execution_module.run_development_validation(
            ROOT, tmp_path / "tampered-run", "DEV_MONO_CI_SOURCE_TAMPER"
        )
    assert changed
    assert evaluator_called is False


def test_execution_binding_rejects_mismatched_evaluator_configuration(
    tmp_path: Path,
) -> None:
    _, bundle_root, manifest, source, baseline_config, baseline, bare, checkout = (
        _case_execution_context(tmp_path)
    )
    altered = copy.deepcopy(baseline_config)
    altered["representations"][0]["evaluator_configuration_sha256"] = "0" * 64

    with pytest.raises(ContractValidationError, match="EXECUTION_CONFIG_DIGEST_MISMATCH"):
        _verify_execution_input_binding(
            bare, checkout, bundle_root, manifest, source, altered, baseline
        )


def test_execution_binding_rejects_mismatched_state_manifest(tmp_path: Path) -> None:
    _, bundle_root, _, source, baseline_config, baseline, bare, checkout = _case_execution_context(
        tmp_path
    )
    resealed_manifest = _reseal_bundle_with_modified_target_state(bundle_root)
    assert verify_arm_input_bundle(bundle_root, expected_arm="B0") == resealed_manifest

    with pytest.raises(ContractValidationError, match="EXECUTION_STATE_MANIFEST_MISMATCH"):
        _verify_execution_input_binding(
            bare,
            checkout,
            bundle_root,
            resealed_manifest,
            source,
            baseline_config,
            baseline,
        )


def test_execution_binding_rejects_stale_git_tree_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, bundle_root, manifest, source, baseline_config, baseline, bare, checkout = (
        _case_execution_context(tmp_path)
    )
    original_git_text = execution_module._git_text

    def stale_tree(repository: Path, *arguments: str) -> str:
        if repository == bare and arguments == (
            "rev-parse",
            f"{source['source_commit_sha']}^{{tree}}",
        ):
            return "0" * 40
        return original_git_text(repository, *arguments)

    monkeypatch.setattr(execution_module, "_git_text", stale_tree)
    with pytest.raises(ContractValidationError, match="REPOSITORY_TREE_MISMATCH"):
        _verify_execution_input_binding(
            bare, checkout, bundle_root, manifest, source, baseline_config, baseline
        )


def test_common_inputs_are_repeatable_equal_and_separate_by_arm(tmp_path: Path) -> None:
    first = _materialize(tmp_path / "first")
    second = _materialize(tmp_path / "second")

    for case_id in ("CASE_01", "CASE_02", "CASE_03", "CASE_04"):
        first_common: dict[str, str] = {}
        second_common: dict[str, str] = {}
        for arm in ("B0", "PSI"):
            first_bundle = first / arm / "input_bundle" / case_id
            second_bundle = second / arm / "input_bundle" / case_id
            first_manifest = verify_arm_input_bundle(first_bundle, expected_arm=arm)
            second_manifest = verify_arm_input_bundle(second_bundle, expected_arm=arm)
            first_common[arm] = first_manifest["common_input_sha256"]
            second_common[arm] = second_manifest["common_input_sha256"]
            assert first_manifest["bundle_sha256"] == second_manifest["bundle_sha256"]
            assert not (first_bundle / ".git").exists()
            assert not list(first_bundle.rglob("*.bundle"))
            assert not list(first_bundle.rglob("*expected*"))
            assert not list(first_bundle.rglob("*scorer*"))
            assert not list(first_bundle.rglob("*reference*"))
        assert first_common["B0"] == first_common["PSI"]
        assert second_common == first_common

        b0_output = first / "B0/raw" / case_id
        psi_output = first / "PSI/raw" / case_id
        assert not b0_output.exists()
        assert not psi_output.exists()
        assert not b0_output.resolve().is_relative_to((first / "B0/input_bundle").resolve())
        assert (
            not (first / "B0/input_bundle" / case_id)
            .resolve()
            .is_relative_to((first / "PSI/input_bundle" / case_id).resolve())
        )


def test_arm_bundle_readback_detects_tampering_and_symlinks(tmp_path: Path) -> None:
    run_root = _materialize(tmp_path)
    bundle = run_root / "B0/input_bundle/CASE_01"
    source = next(path for path in bundle.rglob("*.py"))
    source.write_bytes(source.read_bytes() + b"# tamper\n")
    with pytest.raises(ContractValidationError, match="FILE_DIGEST_MISMATCH"):
        verify_arm_input_bundle(bundle, expected_arm="B0")

    clean_root = _materialize(tmp_path / "clean", "DEV_MONO_CI_CLEAN")
    clean_bundle = clean_root / "PSI/input_bundle/CASE_01"
    (clean_bundle / "unlisted").symlink_to(clean_bundle / "manifest.json")
    with pytest.raises(ContractValidationError, match="SYMLINK_FORBIDDEN"):
        verify_arm_input_bundle(clean_bundle, expected_arm="PSI")


@pytest.mark.parametrize(
    "relative",
    [
        "scorer/reference.json",
        "scoring/assessment.json",
        "expected_outputs/prediction.json",
        "architecture/.git/config",
        "experiments/results/result.json",
    ],
)
def test_method_input_rejects_scorer_expected_and_git_paths(relative: str) -> None:
    with pytest.raises(ContractValidationError, match="FORBIDDEN_INPUT_PATH"):
        _validate_bundle_file(relative, b"safe content")


def test_method_input_rejects_oracle_markers_included_as_content() -> None:
    with pytest.raises(ContractValidationError, match="FORBIDDEN_INPUT_CONTENT"):
        _validate_bundle_file("case/source.json", b'{"expected_operations": []}')


@pytest.mark.parametrize(
    "forbidden_field",
    ["scorer", "scoring", "oracle", "ground_truth", "expected_outputs", "expected_operations"],
)
def test_raw_evaluator_evidence_rejects_forbidden_reference_fields(
    forbidden_field: str,
) -> None:
    with pytest.raises(ContractValidationError, match="RAW_EVIDENCE_CONTAINS_FORBIDDEN_FIELD"):
        _validate_raw_evaluator_evidence({forbidden_field: {"value": "forbidden"}})


def test_evaluator_records_reject_stale_or_wrong_evaluator_bindings() -> None:
    source = {
        "source_commit_sha": "a" * 40,
        "repository_tree_sha": "b" * 40,
        "application_tree_sha": "c" * 40,
    }
    evidence: dict[str, Any] = {
        "architecture": {
            "target_source_sha": source["source_commit_sha"],
            "expected_source_sha": source["source_commit_sha"],
            "manifest_state_status": "MATCHED",
            "source_sha_status": "MATCHED",
        },
        "evaluator": {"source_digest": "d" * 64, "configuration_digest": "e" * 64},
    }
    _verify_evaluator_binding(evidence, source, "d" * 64, "e" * 64)

    stale = copy.deepcopy(evidence)
    stale["architecture"]["target_source_sha"] = "f" * 40
    with pytest.raises(ContractValidationError, match="SOURCE_BINDING_MISMATCH"):
        _verify_evaluator_binding(stale, source, "d" * 64, "e" * 64)

    wrong_evaluator = copy.deepcopy(evidence)
    wrong_evaluator["evaluator"]["source_digest"] = "0" * 64
    with pytest.raises(ContractValidationError, match="SOURCE_DIGEST_MISMATCH"):
        _verify_evaluator_binding(wrong_evaluator, source, "d" * 64, "e" * 64)


def test_metric_statuses_remain_categorical_and_no_scoring_is_emitted() -> None:
    run = _development_record("DEV_MONO_CI_STATUS_TEST", {})
    validate_payload(DEV_RUN_SCHEMA, run)
    assert run["measurement_status"] == "NOT_EXECUTED"
    assert run["metrics"]["controlled_violation_detection"] == {
        "B0": "NOT_MEASURED",
        "PSI": "NOT_MEASURED",
    }
    run["metrics"]["current_configuration_verified_coverage"]["B0"] = 0
    with pytest.raises(ContractValidationError, match="validation failed"):
        validate_payload(DEV_RUN_SCHEMA, run)


def test_development_result_readback_rejects_changed_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    baseline = json.loads(
        (
            ROOT / "experiments/execution/mono-ci-b0-psi-execution-v1/RECONSTRUCTED_B0_A03_V1.json"
        ).read_text()
    )
    monkeypatch.setattr(execution_module, "run_evaluator", _development_fake_evaluator(baseline))
    run_root = tmp_path / "DEV_MONO_CI_READBACK"
    execution_module.run_development_validation(ROOT, run_root, "DEV_MONO_CI_READBACK")
    verify_development_result(run_root)
    score_root = run_root.parent / "separate-scoring-output"
    score_record = score_development_run(run_root, score_root)
    assert score_record["scoring_status"] == "NOT_EVALUABLE"
    assert score_record["reference_status"] == "NOT_ESTABLISHED"
    assert score_record["numeric_results"] == {}
    assert verify_scoring_assessment(score_root) == score_record
    assert not score_root.is_relative_to(run_root / "B0")
    assert not score_root.is_relative_to(run_root / "PSI")

    assessment_path = score_root / "scoring_assessment.json"
    assessment_path.write_text('{"tampered":true}\n', encoding="utf-8")
    with pytest.raises(ContractValidationError, match="validation failed"):
        verify_scoring_assessment(score_root)

    raw_path = run_root / "B0/raw/CASE_01/AC_PUBLIC_API.json"
    raw_path.write_text('{"tampered":true}\n', encoding="utf-8")
    with pytest.raises(ContractValidationError, match="RAW_OUTPUT_DIGEST_MISMATCH"):
        verify_development_result(run_root)


@pytest.fixture
def completed_development_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    baseline = json.loads(
        (
            ROOT / "experiments/execution/mono-ci-b0-psi-execution-v1/RECONSTRUCTED_B0_A03_V1.json"
        ).read_text()
    )
    monkeypatch.setattr(execution_module, "run_evaluator", _development_fake_evaluator(baseline))
    output = tmp_path / "archive-run"
    execution_module.run_development_validation(ROOT, output, "DEV_MONO_CI_ARCHIVE_TEST")
    return output


def test_development_archive_is_complete_deterministic_and_verifiable(
    tmp_path: Path, completed_development_run: Path
) -> None:
    artifact_name = "mono-ci-b0-psi-development-12345-1"
    run_url = "https://github.com/Pan14ek/evofit-bench/actions/runs/12345"
    first_archive = tmp_path / "first.zip"
    second_archive = tmp_path / "second.zip"
    first = archive_module.pack_development_archive(
        completed_development_run,
        first_archive,
        ROOT,
        run_url,
        artifact_name,
        "uv 0.9.0",
    )
    second = archive_module.pack_development_archive(
        completed_development_run,
        second_archive,
        ROOT,
        run_url,
        artifact_name,
        "uv 0.9.0",
    )
    assert first["archive_sha256"] == second["archive_sha256"]
    with zipfile.ZipFile(first_archive) as zipped:
        names = set(zipped.namelist())
        assert "development_run.json" in names
        assert "development_run.json.sha256" in names
        assert "SHA256SUMS" in names
        assert (
            len([name for name in names if name.startswith("B0/raw/") and name.endswith(".json")])
            == 8
        )
        assert all(
            not {part.lower() for part in Path(name).parts}.intersection(
                {"scorer", "scoring", "oracle", "reference", "expected_outputs", ".git"}
            )
            for name in names
        )
        archive_manifest = json.loads(zipped.read(archive_module.ARCHIVE_MANIFEST_NAME))
    run = verify_development_result(completed_development_run)
    assert archive_manifest["execution_id"] == run["execution_id"]
    assert archive_manifest["baseline"] == run["baseline"]
    assert archive_manifest["authorization_boundary"] == {
        "study_readiness": "NO_GO",
        "measurement_status": "NOT_EXECUTED",
        "p_algorithm_status": "NOT_READY",
        "g1": "INCOMPLETE",
        "g4": "NOT_AUTHORIZED",
        "reference_gate": "NOT_READY",
        "psi_status": "BLOCKED_NOT_EXECUTED",
        "scoring": "NOT_EXECUTED_NO_SCORER_REFERENCE",
    }
    assert archive_manifest["workflow"]["retention_days"] == 90
    assert len(archive_manifest["cases"]) == 4
    assert (
        archive_manifest["cases"][0]["execution_binding"]["input_bundle_sha256"]
        == run["arms"]["B0"]["case_results"][0]["input_bundle_sha256"]
    )

    extracted = tmp_path / "archive-extracted"
    verified = archive_module.verify_development_archive(first_archive, extract_to=extracted)
    assert verified["verification_status"] == "PASS"
    assert verified["execution_id"] == run["execution_id"]
    assert verify_development_result(extracted)["execution_id"] == run["execution_id"]


@pytest.mark.parametrize("damage", ["missing", "modified"])
def test_development_archive_rejects_missing_or_modified_members(
    tmp_path: Path, completed_development_run: Path, damage: str
) -> None:
    archive_path = tmp_path / "source.zip"
    archive_module.pack_development_archive(
        completed_development_run,
        archive_path,
        ROOT,
        "https://github.com/Pan14ek/evofit-bench/actions/runs/12345",
        "mono-ci-b0-psi-development-12345-1",
        "uv 0.9.0",
    )
    damaged_archive = tmp_path / f"{damage}.zip"
    with zipfile.ZipFile(archive_path) as original:
        entries = [(info, original.read(info.filename)) for info in original.infolist()]
    target = "B0/raw/CASE_01/AC_PUBLIC_API.json"
    with zipfile.ZipFile(damaged_archive, "w", compression=zipfile.ZIP_STORED) as damaged:
        for info, content in entries:
            if damage == "missing" and info.filename == target:
                continue
            if damage == "modified" and info.filename == target:
                content += b"tampered\n"
            damaged.writestr(info, content)
    Path(f"{damaged_archive}.sha256").write_text(
        f"{sha256_file(damaged_archive)}  {damaged_archive.name}\n", encoding="utf-8"
    )
    with pytest.raises(ContractValidationError, match="ARCHIVE_MEMBER_(SET|DIGEST)_MISMATCH"):
        archive_module.verify_development_archive(damaged_archive)


def test_development_archive_rejects_forbidden_run_files(
    tmp_path: Path, completed_development_run: Path
) -> None:
    forbidden = completed_development_run / "scorer/reference.json"
    forbidden.parent.mkdir()
    forbidden.write_text("{}\n", encoding="utf-8")
    (completed_development_run / "SHA256SUMS").unlink()
    execution_module._write_checksums(completed_development_run, exclude={"SHA256SUMS"})

    with pytest.raises(ContractValidationError, match="DEVELOPMENT_RUN_FILE_FORBIDDEN"):
        archive_module.pack_development_archive(
            completed_development_run,
            tmp_path / "forbidden.zip",
            ROOT,
            "https://github.com/Pan14ek/evofit-bench/actions/runs/12345",
            "mono-ci-b0-psi-development-12345-1",
            "uv 0.9.0",
        )
