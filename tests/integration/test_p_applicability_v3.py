"""Isolation tests for the independently pinned policy source V3 candidate."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from experiments.execution.tooling.errors import ProtocolError
from experiments.execution.tooling.inputs import FITNESS_INPUTS, TRACEABILITY_INPUT
from experiments.execution.tooling.p_input_export_v2 import (
    STRUCTURAL_MANIFEST_PATH,
)
from experiments.execution.tooling.p_policy_source_v3 import (
    export_method_inputs_v3,
    package_policy_source_v3,
    verify_method_bundle_v3,
)

REPOSITORY_ROOT = Path(__file__).parents[2]
POLICY_SOURCE = REPOSITORY_ROOT / "experiments/execution/policy-pilot/v1/source"
EVALUATION_AS_OF = "2026-10-14T00:00:00Z"


def _git(repository: Path, *arguments: str) -> str:
    executable = shutil.which("git")
    if executable is None:
        raise AssertionError("Git is required for V3 isolation tests")
    result = subprocess.run(  # noqa: S603 - fixed local Git executable and argument list
        [executable, "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _write(repository: Path, relative: str, content: bytes) -> None:
    destination = repository / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)


def _commit(repository: Path, message: str) -> str:
    _git(repository, "add", "-A")
    _git(
        repository,
        "-c",
        "user.name=Applicability V3 Test",
        "-c",
        "user.email=applicability-v3@example.invalid",
        "commit",
        "-m",
        message,
    )
    return _git(repository, "rev-parse", "HEAD")


def _synthetic_architecture_repository(root: Path) -> tuple[Path, str, str]:
    repository = root / "synthetic-architecture"
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.name", "Applicability V3 Test")
    _git(repository, "config", "user.email", "applicability-v3@example.invalid")

    shutil.copytree(REPOSITORY_ROOT / "app", repository / "app")
    paths = [STRUCTURAL_MANIFEST_PATH, *(entry[0] for entry in FITNESS_INPUTS)]
    paths.append(TRACEABILITY_INPUT[0])
    for relative in paths:
        _write(repository, relative, (REPOSITORY_ROOT / relative).read_bytes())
    before_sha = _commit(repository, "synthetic architecture before")

    app_init = repository / "app/__init__.py"
    app_init.write_bytes(app_init.read_bytes() + b"\n# synthetic target revision\n")
    after_sha = _commit(repository, "synthetic architecture after")
    return repository, before_sha, after_sha


def _export(
    repository: Path,
    policy_bundle: Path,
    destination: Path,
    method_id: str,
    before_sha: str,
    after_sha: str,
) -> dict[str, Any]:
    return export_method_inputs_v3(
        repository,
        policy_bundle,
        destination,
        method_id,  # type: ignore[arg-type]
        before_sha,
        after_sha,
        EVALUATION_AS_OF,
    )


def _role_records(manifest: dict[str, Any], role: str) -> list[dict[str, Any]]:
    return [record for record in manifest["files"] if record["role"] == role]


def test_b1_and_p_receive_identical_policy_and_common_snapshot(
    tmp_path: Path,
) -> None:
    repository, before_sha, after_sha = _synthetic_architecture_repository(tmp_path)
    policy_bundle = tmp_path / "policy-bundles/shared-v1"
    source_manifest = package_policy_source_v3(
        POLICY_SOURCE, policy_bundle, "controlled-policy-pilot-candidates-v1"
    )
    b1_root = tmp_path / "method-inputs/B1"
    p_root = tmp_path / "method-inputs/P"
    b1 = _export(repository, policy_bundle, b1_root, "B1", before_sha, after_sha)
    p = _export(repository, policy_bundle, p_root, "P", before_sha, after_sha)

    assert b1["profile_status"] == p["profile_status"] == "DEVELOPMENT_UNFROZEN"
    assert b1["architecture_source_sha"] == p["architecture_source_sha"] == after_sha
    assert b1["before_tree_sha"] == p["before_tree_sha"]
    assert b1["after_tree_sha"] == p["after_tree_sha"]
    assert b1["common_snapshot_sha256"] == p["common_snapshot_sha256"]
    assert b1["policy_source_revision"] == p["policy_source_revision"]
    assert b1["policy_bundle_sha256"] == p["policy_bundle_sha256"]
    assert b1["policy_bundle_sha256"] == source_manifest["policy_bundle_sha256"]
    snapshot_bytes = (b1_root / "architecture-policy-snapshot.json").read_bytes()
    assert snapshot_bytes == (p_root / "architecture-policy-snapshot.json").read_bytes()
    snapshot = json.loads(snapshot_bytes)
    assert snapshot["policy_registry"]["closure"] == "OPEN"
    assert len(snapshot["policies"]) == 18
    assert all(policy["normative_status"] == "DRAFT" for policy in snapshot["policies"])
    assert "approval_evidence" not in {record["role"] for record in source_manifest["files"]}
    assert (b1_root / "fitness/policy/registry.json").read_bytes() == (
        p_root / "fitness/policy/registry.json"
    ).read_bytes()
    assert _role_records(b1, "architecture_before_source") == _role_records(
        p, "architecture_before_source"
    )
    assert _role_records(b1, "architecture_after_source") == _role_records(
        p, "architecture_after_source"
    )
    assert "fitness/a0-traceability.yaml" not in {record["path"] for record in b1["files"]}
    assert "fitness/a0-traceability.yaml" in {record["path"] for record in p["files"]}
    assert verify_method_bundle_v3(b1_root)["method_id"] == "B1"
    assert verify_method_bundle_v3(p_root)["method_id"] == "P"

    tampered_registry = b1_root / "fitness/policy/registry.json"
    tampered_registry.write_bytes(tampered_registry.read_bytes() + b" ")
    with pytest.raises(ProtocolError, match="hash mismatch"):
        verify_method_bundle_v3(b1_root)


def test_policy_revision_changes_without_changing_pinned_architecture(
    tmp_path: Path,
) -> None:
    repository, before_sha, after_sha = _synthetic_architecture_repository(tmp_path)
    first_source = tmp_path / "policy-source-v1"
    second_source = tmp_path / "policy-source-v2"
    shutil.copytree(POLICY_SOURCE, first_source)
    shutil.copytree(POLICY_SOURCE, second_source)
    registry_path = second_source / "fitness/policy/registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["registry_version"] = "controlled-policy-pilot-candidates-v2"
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n")

    first_bundle = tmp_path / "policy-bundles/v1"
    second_bundle = tmp_path / "policy-bundles/v2"
    first_policy = package_policy_source_v3(first_source, first_bundle, "policy-source-v1")
    second_policy = package_policy_source_v3(second_source, second_bundle, "policy-source-v2")
    first_root = tmp_path / "method-inputs/revision-v1"
    second_root = tmp_path / "method-inputs/revision-v2"
    first = _export(repository, first_bundle, first_root, "B1", before_sha, after_sha)
    second = _export(repository, second_bundle, second_root, "B1", before_sha, after_sha)

    assert first_policy["policy_bundle_sha256"] != second_policy["policy_bundle_sha256"]
    assert first["policy_bundle_sha256"] != second["policy_bundle_sha256"]
    assert first["architecture_before_sha"] == second["architecture_before_sha"] == before_sha
    assert first["architecture_source_sha"] == second["architecture_source_sha"] == after_sha
    assert first["before_tree_sha"] == second["before_tree_sha"]
    assert first["after_tree_sha"] == second["after_tree_sha"]
    assert _role_records(first, "architecture_before_source") == _role_records(
        second, "architecture_before_source"
    )
    assert _role_records(first, "architecture_after_source") == _role_records(
        second, "architecture_after_source"
    )
    assert first["common_snapshot_sha256"] != second["common_snapshot_sha256"]


def test_policy_source_rejects_answer_markers_and_unallowlisted_files(tmp_path: Path) -> None:
    source = tmp_path / "policy-source"
    shutil.copytree(POLICY_SOURCE, source)
    registry_path = source / "fitness/policy/registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["expected_operations"] = ["SYNTHETIC_FORBIDDEN_FIELD"]
    registry_path.write_text(json.dumps(registry), encoding="utf-8")

    with pytest.raises(ProtocolError, match="Forbidden oracle/answer marker"):
        package_policy_source_v3(source, tmp_path / "rejected-output", "reject-answer-data")

    registry.pop("expected_operations")
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    (source / "unexpected.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ProtocolError, match="allowlist mismatch"):
        package_policy_source_v3(source, tmp_path / "rejected-inventory", "reject-extra-file")
