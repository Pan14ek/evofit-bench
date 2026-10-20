"""Live PILOT-02 semantic controls and digest-resealed adversarial readback."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from experiments.pilots import pilot02_semantic_validation as semantic

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def verified_controls(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Execute both real evaluators and controls once against the pinned source."""
    revision = semantic._run_git(ROOT, "rev-parse", "HEAD", text=True).stdout.strip()
    evidence_root = tmp_path_factory.mktemp("pilot02-semantic-controls") / "evidence"
    result = semantic.run_semantic_controls(ROOT, evidence_root, revision)
    assert result["status"] == "validated"
    assert all(row["status"] == "VALID" for row in result["reports"].values())
    return evidence_root


def _copy_evidence(source: Path, destination: Path) -> Path:
    target = destination / "evidence"
    shutil.copytree(source, target)
    return target


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def _reseal_inventory(root: Path) -> None:
    _write_json(root / "sha256_inventory.json", semantic._inventory_outputs(root))


def _tamper(root: Path, case: str) -> None:
    if case == "missing_expected_module":
        path = root / "inspection_scope/REP_A01_ARCH_MODULE_STRUCTURE_CI.json"
        value = _read_json(path)
        value["expected_subjects"].remove("audit")
        _write_json(path, value)
    elif case == "missing_layer_target":
        path = root / "inspection_scope/REP_A01_ARCH_INTERNAL_LAYERING_CI.json"
        value = _read_json(path)
        value["expected_subjects"].pop()
        _write_json(path, value)
    elif case == "successful_without_inspection":
        path = root / "controls/AC_LAYERING_positive.json"
        value = _read_json(path)
        stdout = root / value["stdout_artifact"]["path"]
        stdout.write_bytes(b"0 contracts inspected\n")
        value["stdout_artifact"]["sha256"] = semantic._sha(stdout)
        _write_json(path, value)
    elif case == "evaluator_artifact_sha":
        path = root / "semantic_verification/REP_A01_ARCH_INTERNAL_LAYERING_CI.json"
        value = _read_json(path)
        value["evaluator_artifact_sha256"] = "0" * 64
        _write_json(path, value)
    elif case == "architecture_revision":
        path = root / "inputs/method_source_binding.json"
        value = _read_json(path)
        value["architecture_source_sha"] = semantic.SOURCE_REVISION
        _write_json(path, value)
    elif case == "wrong_obligation":
        path = root / "semantic_verification/REP_A01_ARCH_INTERNAL_LAYERING_CI.json"
        value = _read_json(path)
        value["obligation"]["id"] = "AC_MODULE_STRUCTURE"
        _write_json(path, value)
    elif case == "wrong_representation":
        path = root / "semantic_verification/REP_A01_ARCH_INTERNAL_LAYERING_CI.json"
        value = _read_json(path)
        value["representation_id"] = "REP_A01_ARCH_MODULE_STRUCTURE_CI"
        _write_json(path, value)
    elif case in {"stdout_tamper", "stderr_tamper"}:
        path = root / "controls/AC_LAYERING_positive.json"
        value = _read_json(path)
        stream = "stdout_artifact" if case == "stdout_tamper" else "stderr_artifact"
        (root / value[stream]["path"]).write_bytes(b"tampered stream\n")
    elif case == "inspection_evidence_tamper":
        path = root / "inspection_scope/REP_A01_ARCH_MODULE_STRUCTURE_CI.json"
        value = _read_json(path)
        value["measured_count"] -= 1
        _write_json(path, value)
    elif case == "negative_control_unsuccessful":
        path = root / "controls/AC_LAYERING_negative.json"
        value = _read_json(path)
        value["exit_code"] = 0
        _write_json(path, value)
    else:
        raise AssertionError(f"unknown tamper case: {case}")
    _reseal_inventory(root)


def test_real_controls_establish_two_testonly_semantic_pairs(verified_controls: Path) -> None:
    reports = semantic.verify_semantic_evidence_directory(
        verified_controls,
        repository_root=ROOT,
        expected_architecture_source_sha=semantic._run_git(
            ROOT, "rev-parse", "HEAD", text=True
        ).stdout.strip(),
    )

    assert set(reports) == {
        "REP_A01_ARCH_INTERNAL_LAYERING_CI",
        "REP_A01_ARCH_MODULE_STRUCTURE_CI",
    }
    assert all(report["status"] == "VALID" for report in reports.values())
    assert reports["REP_A01_ARCH_INTERNAL_LAYERING_CI"]["inspection_scope"]["measured_count"] > 0
    assert reports["REP_A01_ARCH_MODULE_STRUCTURE_CI"]["inspection_scope"]["measured_count"] == 5


@pytest.mark.parametrize(
    "case",
    [
        "missing_expected_module",
        "missing_layer_target",
        "successful_without_inspection",
        "evaluator_artifact_sha",
        "architecture_revision",
        "wrong_obligation",
        "wrong_representation",
        "stdout_tamper",
        "stderr_tamper",
        "inspection_evidence_tamper",
        "negative_control_unsuccessful",
    ],
)
def test_readback_rejects_digest_resealed_adversarial_evidence(
    case: str,
    verified_controls: Path,
    tmp_path: Path,
) -> None:
    evidence_root = _copy_evidence(verified_controls, tmp_path)
    _tamper(evidence_root, case)

    with pytest.raises((semantic.SemanticValidationError, subprocess.SubprocessError)):
        semantic.verify_semantic_evidence_directory(
            evidence_root,
            repository_root=ROOT,
            expected_architecture_source_sha=semantic._run_git(
                ROOT, "rev-parse", "HEAD", text=True
            ).stdout.strip(),
        )
