"""A0.5 transition adapter identity and noncontamination contracts."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import jsonschema  # type: ignore[import-untyped]
import pytest
import yaml

from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.hashing import sha256_bytes
from experiments.execution.tooling.mono_ci_psi_a05 import (
    AFTER_STATE,
    BASELINE_ID,
    BEFORE_COMMIT,
    BEFORE_STATE,
    PROBE_PATH,
    PROBE_SOURCE,
    _candidate_obligation_coverage,
    _classify_probe_detection,
    _combine_old_detection,
    _deterministic_probe_commit,
    _git_bytes,
    _git_text,
    _probe_case_interpretation,
    _validate_a04_proposal,
    replay_negative_probe,
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


def _detection_fixture(
    tmp_path: Path,
    *,
    evaluator_id: str = "AC_PUBLIC_API",
    compliance: str = "COMPLIANT",
    execution_status: str = "COMPLETED",
    inspection_status: str = "COMPLETE",
    finding_codes: tuple[str, ...] = (),
    process_exit_code: int | None = None,
) -> tuple[Path, dict[str, object]]:
    result_exit = (
        2
        if execution_status == "FAILED"
        else {
            "COMPLIANT": 0,
            "NON_COMPLIANT": 1,
            "NOT_EVALUABLE": 2,
            "UNKNOWN": 2,
            "NOT_APPLICABLE": 3,
        }[compliance]
    )
    evidence = {
        "evaluator": {
            "id": evaluator_id,
            "configuration_digest": "c" * 64,
            "source_digest": "d" * 64,
        },
        "architecture": {
            "target_source_sha": "a" * 40,
            "source_sha_status": "MATCHED",
            "manifest_state_status": "MATCHED",
        },
        "result": {"execution_status": execution_status, "compliance": compliance},
        "diagnostics": {"policy_findings": [{"code": code} for code in finding_codes]},
    }
    coverage = {"source_inspection_status": inspection_status}
    output_path = tmp_path / "evaluator-output.json"
    coverage_path = tmp_path / "inspection-coverage.json"
    output_path.write_text(json.dumps(evidence), encoding="utf-8")
    coverage_path.write_text(json.dumps(coverage), encoding="utf-8")
    row: dict[str, object] = {
        "evaluator_id": evaluator_id,
        "source_commit_sha": "a" * 40,
        "execution_status": execution_status,
        "compliance": compliance,
        "process_exit_code": result_exit if process_exit_code is None else process_exit_code,
        "configuration_sha256": "c" * 64,
        "evaluator_source_sha256": "d" * 64,
        "output_path": output_path.name,
        "output_sha256": sha256_bytes(output_path.read_bytes()),
        "coverage_path": coverage_path.name,
        "coverage_sha256": sha256_bytes(coverage_path.read_bytes()),
        "inspection_status": inspection_status,
    }
    return tmp_path, row


def test_three_state_detection_keeps_unknown_incomplete_and_unattributable_results_uncertain(
    tmp_path: Path,
) -> None:
    cases = [
        ("COMPLIANT", "COMPLETED", "COMPLETE", (), "NOT_DETECTED"),
        ("NON_COMPLIANT", "COMPLETED", "COMPLETE", ("FOREIGN_TABLE_ACCESS",), "DETECTED"),
        ("UNKNOWN", "COMPLETED", "COMPLETE", (), "NOT_EVALUABLE"),
        ("NOT_EVALUABLE", "COMPLETED", "COMPLETE", (), "NOT_EVALUABLE"),
        ("UNKNOWN", "FAILED", "COMPLETE", (), "NOT_EVALUABLE"),
        ("NON_COMPLIANT", "COMPLETED", "COMPLETE", ("UNRELATED_POLICY_FINDING",), "NOT_EVALUABLE"),
        ("COMPLIANT", "COMPLETED", "INCOMPLETE", (), "NOT_EVALUABLE"),
    ]
    for index, (compliance, execution, inspection, findings, expected) in enumerate(cases):
        case_root = tmp_path / str(index)
        case_root.mkdir()
        case_root, row = _detection_fixture(
            case_root,
            compliance=compliance,
            execution_status=execution,
            inspection_status=inspection,
            finding_codes=findings,
        )
        result = _classify_probe_detection(case_root, row, source_condition_verified=True)
        assert result["detection_status"] == expected

    mismatch_root = tmp_path / "exit-mismatch"
    mismatch_root.mkdir()
    case_root, row = _detection_fixture(mismatch_root, process_exit_code=1, compliance="COMPLIANT")
    assert (
        _classify_probe_detection(case_root, row, source_condition_verified=True)[
            "detection_status"
        ]
        == "NOT_EVALUABLE"
    )
    assert _classify_probe_detection(case_root, row)["detection_status"] == "NOT_EVALUABLE"


def test_combined_old_control_detection_preserves_uncertainty() -> None:
    assert _combine_old_detection("NOT_DETECTED", "NOT_DETECTED") == "NOT_DETECTED"
    assert _combine_old_detection("DETECTED", "NOT_EVALUABLE") == "DETECTED"
    assert _combine_old_detection("NOT_DETECTED", "NOT_EVALUABLE") == "NOT_EVALUABLE"
    assert _probe_case_interpretation("NOT_DETECTED", "DETECTED") == "OLD_BASELINE_GAP_SUPPORTED"
    assert _probe_case_interpretation("NOT_EVALUABLE", "DETECTED") == "NOT_EVALUABLE"


def test_v2_evidence_schema_resolves_local_refs_and_allows_inconclusive_results() -> None:
    def assert_refs_resolve(value: Any, root_schema: dict[str, Any]) -> None:
        if isinstance(value, dict):
            reference = value.get("$ref")
            if isinstance(reference, str) and reference.startswith("#/"):
                target: Any = root_schema
                for token in reference[2:].split("/"):
                    token = token.replace("~1", "/").replace("~0", "~")
                    assert isinstance(target, dict) and token in target
                    target = target[token]
            for child in value.values():
                assert_refs_resolve(child, root_schema)
        elif isinstance(value, list):
            for child in value:
                assert_refs_resolve(child, root_schema)

    schema_paths = (
        "mono_ci_psi_a05_experiment_evidence_v2.schema.json",
        "mono_ci_psi_a05_probe_manifest_v1.schema.json",
        "mono_ci_psi_transition_run_v4.schema.json",
        "mono_ci_psi_transition_archive_v4.schema.json",
    )
    schemas: dict[str, dict[str, Any]] = {}
    for name in schema_paths:
        current_schema = json.loads(
            (REPOSITORY_ROOT / "experiments/execution/schemas" / name).read_text(encoding="utf-8")
        )
        jsonschema.validators.validator_for(current_schema).check_schema(current_schema)
        assert_refs_resolve(current_schema, current_schema)
        schemas[name] = current_schema

    schema = schemas["mono_ci_psi_a05_experiment_evidence_v2.schema.json"]
    compliance = schema["properties"]["negative_condition"]["properties"]["evaluators"]["items"][
        "properties"
    ]["compliance"]["enum"]
    detection = schema["properties"]["adequacy_diagnostic"]["properties"][
        "per_evaluator_detection"
    ]["items"]["properties"]["detection_status"]["enum"]
    assert {"UNKNOWN", "NOT_EVALUABLE", "COMPLIANT", "NON_COMPLIANT"} <= set(compliance)
    assert {"DETECTED", "NOT_DETECTED", "NOT_EVALUABLE"} == set(detection)


def _make_replayable_probe_artifacts(tmp_path: Path) -> tuple[Path, Path, dict[str, Any]]:
    parent = "d0be79a5a89e6a84e8b2b09307b0998b11681ac9"
    seed = tmp_path / "seed"
    git = shutil.which("git")
    assert git is not None
    subprocess.run(  # nosec B603 # noqa: S603 - fixed local Git fixture command
        [git, "clone", "--quiet", "--shared", "--no-checkout", str(REPOSITORY_ROOT), str(seed)],
        check=True,
    )
    subprocess.run(  # nosec B603 # noqa: S603 - fixed local Git fixture command
        [git, "-C", str(seed), "checkout", "--quiet", "--detach", parent], check=True
    )
    source_path = seed / PROBE_PATH
    original = source_path.read_bytes()
    modified = original + PROBE_SOURCE.encode("utf-8")
    source_path.write_bytes(modified)
    probe_commit = _deterministic_probe_commit(seed)
    tree = _git_text(seed, "rev-parse", "HEAD^{tree}")
    app_tree = _git_text(seed, "rev-parse", "HEAD:app")
    parent_tree = _git_text(seed, "rev-parse", f"{parent}^{{tree}}")
    parent_app_tree = _git_text(seed, "rev-parse", f"{parent}:app")
    patch_bytes = _git_bytes(
        seed, "diff", "--binary", "--no-ext-diff", parent, probe_commit, "--", PROBE_PATH
    )
    artifact_root = tmp_path / "probe-artifacts"
    (artifact_root / "source-files" / Path(PROBE_PATH).parent).mkdir(parents=True)
    (artifact_root / "evaluator-configs").mkdir(parents=True)
    (artifact_root / "source.patch").write_bytes(patch_bytes)
    (artifact_root / "source-files" / PROBE_PATH).write_bytes(modified)
    config_rows = []
    evidence_rows = []
    for evaluator_id in ("AC_PUBLIC_API", "AC_MODULE_GRAPH", "AC_DATA_OWNERSHIP"):
        config_path = f"architecture/acceptance/a1/{evaluator_id.lower()}.yaml"
        config_bytes = b"fixture config\n"
        artifact_path = f"probes/ownership-negative/evaluator-configs/{evaluator_id}.yaml"
        (artifact_root / "evaluator-configs" / f"{evaluator_id}.yaml").write_bytes(config_bytes)
        config_rows.append(
            {
                "evaluator_id": evaluator_id,
                "configuration_path": config_path,
                "artifact_path": artifact_path,
                "configuration_sha256": sha256_bytes(config_bytes),
            }
        )
        evidence_rows.append(
            {
                "source_commit_sha": probe_commit,
                "source_tree_sha": tree,
                "application_tree_sha": app_tree,
                "evaluator_id": evaluator_id,
                "process_exit_code": 0,
                "execution_status": "COMPLETED",
                "compliance": "COMPLIANT",
                "configuration_sha256": "1" * 64,
                "evaluator_source_sha256": "2" * 64,
                "output_path": f"outputs/{evaluator_id}.json",
                "output_sha256": "3" * 64,
                "coverage_path": f"outputs/{evaluator_id}-coverage.json",
                "coverage_sha256": "4" * 64,
                "stdout_path": f"outputs/{evaluator_id}.stdout",
                "stdout_sha256": "5" * 64,
                "stderr_path": f"outputs/{evaluator_id}.stderr",
                "stderr_sha256": "6" * 64,
            }
        )
    manifest = {
        "schema_version": "MONO_CI_PSI_A05_PROBE_MANIFEST_V1",
        "source_provenance": "DETERMINISTIC_LOCAL_PROBE_COMMIT_RECONSTRUCTED_FROM_ARCHIVED_PATCH",
        "remote_commit_required": False,
        "parent_commit_sha": parent,
        "parent_repository_tree_sha": parent_tree,
        "parent_application_tree_sha": parent_app_tree,
        "probe_commit_sha": probe_commit,
        "probe_repository_tree_sha": tree,
        "probe_application_tree_sha": app_tree,
        "probe_commit_provenance": {
            "availability": "LOCAL_ONLY_RECREATED_FROM_PATCH",
            "author": "EvoFitBench A05 Probe",
            "email": "a05-probe@example.invalid",
            "commit_date": "2026-10-26T00:00:00+0000",
            "message": "isolated A0.5 ownership violation probe",
        },
        "changed_paths": [PROBE_PATH],
        "changed_sources": [
            {
                "path": PROBE_PATH,
                "artifact_path": f"source-files/{PROBE_PATH}",
                "original_file_sha256": sha256_bytes(original),
                "modified_file_sha256": sha256_bytes(modified),
            }
        ],
        "patch_path": "probes/ownership-negative/source.patch",
        "patch_sha256": sha256_bytes(patch_bytes),
        "evaluator_configurations": config_rows,
        "evaluator_evidence_bindings": evidence_rows,
    }
    (artifact_root / "probe-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    shutil.rmtree(seed)
    return artifact_root, tmp_path / "reconstructed", manifest


def test_probe_patch_replays_exact_source_without_remote_probe_commit(tmp_path: Path) -> None:
    artifact_root, output, manifest = _make_replayable_probe_artifacts(tmp_path)
    git = shutil.which("git")
    assert git is not None
    unavailable = subprocess.run(  # nosec B603 # noqa: S603 - fixed local Git read-only fixture command
        [git, "-C", str(REPOSITORY_ROOT), "cat-file", "-e", manifest["probe_commit_sha"]],
        check=False,
        capture_output=True,
    )
    assert unavailable.returncode != 0
    with replay_negative_probe(
        REPOSITORY_ROOT,
        artifact_root,
        expected_parent_commit=manifest["parent_commit_sha"],
        expected_parent_tree=manifest["parent_repository_tree_sha"],
        expected_parent_application_tree=manifest["parent_application_tree_sha"],
        output=output,
    ) as (checkout, replayed):
        assert replayed["probe_commit_sha"] == manifest["probe_commit_sha"]
        assert (
            _git_text(checkout, "rev-parse", "HEAD^{tree}") == manifest["probe_repository_tree_sha"]
        )
        assert (
            _git_text(checkout, "rev-parse", "HEAD:app") == manifest["probe_application_tree_sha"]
        )
        assert (checkout / PROBE_PATH).read_bytes() == (
            artifact_root / "source-files" / PROBE_PATH
        ).read_bytes()


def test_probe_replay_rejects_patch_source_and_parent_tampering(tmp_path: Path) -> None:
    artifact_root, _output, manifest = _make_replayable_probe_artifacts(tmp_path)
    patch_path = artifact_root / "source.patch"
    original_patch = patch_path.read_bytes()
    patch_path.write_bytes(original_patch + b"tamper")
    with pytest.raises(ContractValidationError, match="PROBE_MANIFEST_BINDING_MISMATCH"):
        with replay_negative_probe(
            REPOSITORY_ROOT,
            artifact_root,
            expected_parent_commit=manifest["parent_commit_sha"],
            expected_parent_tree=manifest["parent_repository_tree_sha"],
            expected_parent_application_tree=manifest["parent_application_tree_sha"],
        ):
            pass
    patch_path.write_bytes(original_patch)
    with pytest.raises(ContractValidationError, match="PROBE_MANIFEST_BINDING_MISMATCH"):
        with replay_negative_probe(
            REPOSITORY_ROOT,
            artifact_root,
            expected_parent_commit="0" * 40,
            expected_parent_tree=manifest["parent_repository_tree_sha"],
            expected_parent_application_tree=manifest["parent_application_tree_sha"],
        ):
            pass
    source_path = artifact_root / "source-files" / PROBE_PATH
    source_path.write_bytes(source_path.read_bytes() + b"tamper")
    with pytest.raises(ContractValidationError, match="PROBE_SOURCE_DIGEST_MISMATCH"):
        with replay_negative_probe(
            REPOSITORY_ROOT,
            artifact_root,
            expected_parent_commit=manifest["parent_commit_sha"],
            expected_parent_tree=manifest["parent_repository_tree_sha"],
            expected_parent_application_tree=manifest["parent_application_tree_sha"],
        ):
            pass


def test_probe_replay_rejects_missing_and_escaping_patch_paths(tmp_path: Path) -> None:
    artifact_root, _output, manifest = _make_replayable_probe_artifacts(tmp_path)
    patch_path = artifact_root / "source.patch"
    original_patch = patch_path.read_bytes()
    patch_path.unlink()
    with pytest.raises(ContractValidationError, match="PROBE_ARTIFACT_MISSING"):
        with replay_negative_probe(
            REPOSITORY_ROOT,
            artifact_root,
            expected_parent_commit=manifest["parent_commit_sha"],
            expected_parent_tree=manifest["parent_repository_tree_sha"],
            expected_parent_application_tree=manifest["parent_application_tree_sha"],
        ):
            pass

    escaping_patch = original_patch.replace(b"app/modules/tasks/repository.py", b"../outside.py")
    patch_path.write_bytes(escaping_patch)
    manifest["patch_sha256"] = sha256_bytes(escaping_patch)
    (artifact_root / "probe-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ContractValidationError, match="PROBE_PATH_INVALID"):
        with replay_negative_probe(
            REPOSITORY_ROOT,
            artifact_root,
            expected_parent_commit=manifest["parent_commit_sha"],
            expected_parent_tree=manifest["parent_repository_tree_sha"],
            expected_parent_application_tree=manifest["parent_application_tree_sha"],
        ):
            pass


def test_probe_replay_rejects_undeclared_patch_paths(tmp_path: Path) -> None:
    artifact_root, _output, manifest = _make_replayable_probe_artifacts(tmp_path)
    patch_path = artifact_root / "source.patch"
    patch = patch_path.read_bytes() + (
        b"\ndiff --git a/other.py b/other.py\n"
        b"--- a/other.py\n+++ b/other.py\n@@ -1 +1 @@\n-old\n+new\n"
    )
    patch_path.write_bytes(patch)
    manifest["patch_sha256"] = sha256_bytes(patch)
    (artifact_root / "probe-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ContractValidationError, match="PROBE_PATH_INVENTORY_MISMATCH"):
        with replay_negative_probe(
            REPOSITORY_ROOT,
            artifact_root,
            expected_parent_commit=manifest["parent_commit_sha"],
            expected_parent_tree=manifest["parent_repository_tree_sha"],
            expected_parent_application_tree=manifest["parent_application_tree_sha"],
        ):
            pass
