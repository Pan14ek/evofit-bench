"""Preparation and readback tests for the B0/P DEVELOPMENT study package."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from experiments.execution.tooling.b0p_development import (
    B0PPreparationError,
    prepare_development_study,
    verify_study_manifest,
)
from experiments.execution.tooling.errors import ProtocolError

ARCHITECTURE_BEFORE = "b78b0967be937634b7762baccf5ac6892b279a73"
ARCHITECTURE_AFTER = "3fdd5c68f8f60fad5757eefa66cc2aa8b24d9306"
B0_SOURCE = "165a7d6ef31adbe8ce3abe9f72e59d74692c987e"
P_SOURCE = "984f75b11b3153c52275e223ce8ec23b8d0dd0e5"
POLICY_SOURCE = "165a7d6ef31adbe8ce3abe9f72e59d74692c987e"


def _git(repository: Path, *arguments: str) -> str:
    executable = shutil.which("git")
    assert executable is not None
    result = subprocess.run(  # noqa: S603 - test runs fixed Git argv only
        [executable, "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


@pytest.fixture(scope="module")
def repository_copy(tmp_path_factory: pytest.TempPathFactory) -> Path:
    source = Path(__file__).resolve().parents[2]
    destination = tmp_path_factory.mktemp("b0p-git-copy") / "repository"
    executable = shutil.which("git")
    assert executable is not None
    subprocess.run(  # noqa: S603 - test clones the fixed local repository with Git argv
        [
            executable,
            "clone",
            "--quiet",
            "--shared",
            "--no-checkout",
            str(source),
            str(destination),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    _git(destination, "checkout", "--quiet", "--detach", B0_SOURCE)
    return destination


def _prepare(repository: Path, run_id: str) -> dict[str, Any]:
    return prepare_development_study(
        repository,
        run_id=run_id,
        architecture_before_sha=ARCHITECTURE_BEFORE,
        architecture_after_sha=ARCHITECTURE_AFTER,
        b0_source_sha=B0_SOURCE,
        p_source_sha=P_SOURCE,
        policy_source_sha=POLICY_SOURCE,
    )


def test_preparation_exports_and_independently_verifies_pinned_inputs(
    repository_copy: Path,
) -> None:
    manifest = _prepare(repository_copy, "dev-b0p-test-prepared")
    run_directory = repository_copy / "experiments/results/dev-b0p-test-prepared"

    verified = verify_study_manifest(run_directory, repository_copy)

    assert verified["execution_status"] == "PREPARED_NOT_EXECUTED"
    assert verified["exposure_class"] == "CALIBRATION_EXPOSED"
    assert verified["source_revisions"]["p_source_sha"] == P_SOURCE
    assert manifest["architecture_facts"]["assessment"] == "VERIFIED_GIT_INVENTORY"
    assert manifest["b0"]["configuration_sha256"]
    assert manifest["b0"]["evaluator_configuration_sha256"]
    assert manifest["method_p"]["algorithm_status"] == "NOT_READY"
    assert manifest["reference"]["required_obligation_count"] == 6
    assert (
        "RQ2_RESULTS_NOT_AVAILABLE_UNTIL_SEALED_PREDICTIONS_AND_CURRENT_RUN_PAIR_EVIDENCE_EXIST"
        in manifest["blockers"]
    )
    assert manifest["research_gates"] == {"G1": "INCOMPLETE", "G4": "NOT AUTHORIZED"}
    assert not any("ground_truth" in path.name for path in run_directory.rglob("*"))
    assert not any(
        "scor" in path.name.lower() for path in (run_directory / "method_inputs").rglob("*")
    )


def test_preparation_output_is_write_once(repository_copy: Path) -> None:
    with pytest.raises(B0PPreparationError, match="write-once"):
        _prepare(repository_copy, "dev-b0p-test-prepared")


def test_manifest_artifact_paths_cannot_escape_study_directory(
    repository_copy: Path,
) -> None:
    run_directory = repository_copy / "experiments/results/dev-b0p-test-path"
    _prepare(repository_copy, run_directory.name)
    manifest_path = run_directory / "study_manifest.json"
    manifest_path.chmod(0o644)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["b0"]["input_bundle_path"] = "../../outside"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(B0PPreparationError, match="unsafe"):
        verify_study_manifest(run_directory, repository_copy)


def test_prospective_held_out_classification_requires_separate_custody(
    repository_copy: Path,
) -> None:
    with pytest.raises(B0PPreparationError, match="independently prepared and sealed"):
        prepare_development_study(
            repository_copy,
            run_id="dev-b0p-test-holdout",
            architecture_before_sha=ARCHITECTURE_BEFORE,
            architecture_after_sha=ARCHITECTURE_AFTER,
            b0_source_sha=B0_SOURCE,
            p_source_sha=P_SOURCE,
            policy_source_sha=POLICY_SOURCE,
            exposure_class="PROSPECTIVE_HELD_OUT",
        )


def test_evaluator_configuration_digest_is_recomputed_from_pinned_source(
    repository_copy: Path,
) -> None:
    run_directory = repository_copy / "experiments/results/dev-b0p-test-evaluator-digest"
    _prepare(repository_copy, run_directory.name)
    manifest_path = run_directory / "study_manifest.json"
    manifest_path.chmod(0o644)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["b0"]["evaluator_configuration_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(B0PPreparationError, match="Frozen B0 configuration or evaluator"):
        verify_study_manifest(run_directory, repository_copy)


def test_incomplete_obligation_denominator_is_rejected(repository_copy: Path) -> None:
    run_directory = repository_copy / "experiments/results/dev-b0p-test-denominator"
    _prepare(repository_copy, run_directory.name)
    manifest_path = run_directory / "study_manifest.json"
    manifest_path.chmod(0o644)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["reference"]["required_obligation_count"] = 5
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ProtocolError, match="required_obligation_count"):
        verify_study_manifest(run_directory, repository_copy)


def test_different_p_source_revision_is_rejected(repository_copy: Path) -> None:
    with pytest.raises(B0PPreparationError, match="frozen PILOT-02 baseline"):
        prepare_development_study(
            repository_copy,
            run_id="dev-b0p-test-wrong-p",
            architecture_before_sha=ARCHITECTURE_BEFORE,
            architecture_after_sha=ARCHITECTURE_AFTER,
            b0_source_sha=B0_SOURCE,
            p_source_sha=B0_SOURCE,
            policy_source_sha=POLICY_SOURCE,
        )
