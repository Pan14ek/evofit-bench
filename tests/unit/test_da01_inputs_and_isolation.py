"""Allowlist exporter and container-boundary tests using synthetic Git repositories."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from experiments.execution.tooling.errors import IsolationError, ProtocolError
from experiments.execution.tooling.hashing import bundle_sha256, sha256_bytes
from experiments.execution.tooling.inputs import (
    export_method_inputs,
    verify_method_bundle,
)
from experiments.execution.tooling.isolation import build_docker_command, run_isolated_method


def _git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(  # noqa: S603 - test uses a fixed local Git executable and argv
        [_git_executable(), "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _commit_all(repository: Path, message: str) -> str:
    _git(repository, "add", "-A")
    _git(
        repository,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-m",
        message,
    )
    return _git(repository, "rev-parse", "HEAD")


def _git_executable() -> str:
    executable = shutil.which("git")
    if executable is None:
        raise AssertionError("Git is required for the synthetic repository test")
    return executable


def _synthetic_repository(root: Path) -> tuple[Path, str, str]:
    repository = root / "synthetic-repo"
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.name", "Test")
    _git(repository, "config", "user.email", "test@example.invalid")
    before_files = {
        "app/__init__.py": '"""Synthetic application."""\n',
        "app/api/__init__.py": '"""API."""\n',
        "app/api/entry.py": "def handle() -> None:\n    return None\n",
        "app/services/__init__.py": '"""Services."""\n',
        "app/services/logic.py": "def run() -> None:\n    return None\n",
        "app/repositories/__init__.py": '"""Repositories."""\n',
        "app/repositories/store.py": "def read() -> None:\n    return None\n",
        "app/models/__init__.py": '"""Models."""\n',
        "app/models/entity.py": "class Entity:\n    pass\n",
        "fitness/configs/a0-monolith.yaml": (
            "architecture_state: A0_MONOLITH\nrepresentations: []\n"
        ),
        "fitness/catalog/a0-fitness-elements.yaml": "schema_version: 1\nrepresentations: []\n",
        "fitness/catalog/architectural-obligations.yaml": "schema_version: 1\nobligations: []\n",
        "fitness/evaluators/a0/importlinter.toml": "[tool.importlinter]\nroot_packages = ['app']\n",
        "fitness/traceability/a0-traceability.yaml": "schema_version: 1\nelements: []\n",
        "experiments/scenarios/DA99/ground_truth.yaml": "GT_SENTINEL_EXPECTED_OPERATION: replace\n",
        "experiments/scenarios/DA99/scenario.yaml": "new_obligations: [GT_SENTINEL]\n",
        "architecture/acceptance/importlinter.toml": "GT_SENTINEL_REFERENCE_CHECKER\n",
    }
    for relative, content in before_files.items():
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    before_sha = _commit_all(repository, "synthetic source architecture")

    for relative in ("app/api", "app/services", "app/repositories", "app/models"):
        shutil.rmtree(repository / relative)
    target_files = {
        "app/modules/__init__.py": '"""Capabilities."""\n',
        "app/modules/billing/__init__.py": '"""Billing."""\n',
        "app/modules/billing/api.py": "def handle() -> None:\n    return None\n",
        "app/modules/billing/service.py": "def run() -> None:\n    return None\n",
        "app/modules/billing/repository.py": "def read() -> None:\n    return None\n",
        "architecture/states/A0_1_CAPABILITY_MODULES.yaml": (
            "architecture_state: SYNTHETIC_MODULES\n"
            "source_state: SYNTHETIC_SOURCE\n"
            "scenario_id: DA99\n"
            "governance:\n  answer_key: GT_SENTINEL\n"
            "modules:\n  billing:\n    package: app.modules.billing\n"
            "    required_files: [__init__.py, api.py, service.py, repository.py]\n"
        ),
    }
    for relative, content in target_files.items():
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    after_sha = _commit_all(repository, "synthetic target architecture")
    return repository, before_sha, after_sha


@pytest.fixture
def synthetic_repository(tmp_path: Path) -> tuple[Path, str, str]:
    return _synthetic_repository(tmp_path)


def test_method_export_is_allowlisted_versioned_and_separate(
    synthetic_repository: tuple[Path, str, str], tmp_path: Path
) -> None:
    repository, before_sha, after_sha = synthetic_repository
    b1_root = tmp_path / "bundles" / "B1"
    p_root = tmp_path / "bundles" / "P"
    b1 = export_method_inputs(repository, b1_root, "B1", before_sha, after_sha)
    p = export_method_inputs(repository, p_root, "P", before_sha, after_sha)

    assert b1["method_id"] == "B1"
    assert b1["architecture_source_sha"] == after_sha
    assert "fitness/a0-traceability.yaml" not in {item["path"] for item in b1["files"]}
    assert "fitness/a0-traceability.yaml" in {item["path"] for item in p["files"]}
    assert "fitness/evaluator-capabilities.json" in {item["path"] for item in b1["files"]}
    assert "fitness/evaluator-capabilities.json" in {item["path"] for item in p["files"]}
    for bundle in (b1_root, p_root):
        verified = verify_method_bundle(bundle)
        assert verified["bundle_sha256"] == bundle_sha256(verified["files"])
        content = b"\n".join(path.read_bytes() for path in bundle.rglob("*") if path.is_file())
        assert b"GT_SENTINEL" not in content
        assert b"new_obligations" not in content
        assert not any(".git" in path.parts for path in bundle.rglob("*"))
        assert str(repository).encode() not in content


def test_exporter_omits_forbidden_sentinel_and_rejects_in_repo_output(
    synthetic_repository: tuple[Path, str, str],
    tmp_path: Path,
) -> None:
    repository, before_sha, after_sha = synthetic_repository
    with pytest.raises(ProtocolError, match="outside the repository"):
        export_method_inputs(repository, repository / "method-inputs", "B0", before_sha, after_sha)

    bundle = tmp_path / "clean-bundle"
    export_method_inputs(repository, bundle, "B0", before_sha, after_sha)
    all_bytes = b"\n".join(path.read_bytes() for path in bundle.rglob("*") if path.is_file())
    assert b"GT_SENTINEL_EXPECTED_OPERATION" not in all_bytes
    assert b"GT_SENTINEL_REFERENCE_CHECKER" not in all_bytes
    manifest = json.loads((bundle / "method_input.json").read_text(encoding="utf-8"))
    assert manifest["method_id"] == "B0"
    assert all("experiments" not in entry["path"].split("/") for entry in manifest["files"])


def test_bundle_verifier_detects_unlisted_or_modified_files(
    synthetic_repository: tuple[Path, str, str],
    tmp_path: Path,
) -> None:
    repository, before_sha, after_sha = synthetic_repository
    bundle = tmp_path / "tampered-bundle"
    export_method_inputs(repository, bundle, "P", before_sha, after_sha)
    (bundle / "other_method_output.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ProtocolError, match="inventory mismatch"):
        verify_method_bundle(bundle)


def _local_image_digest() -> str | None:
    configured = os.environ.get("DA01_SANDBOX_IMAGE_DIGEST")
    if configured:
        return configured
    docker_executable = shutil.which("docker")
    if docker_executable is None:
        return None
    info = subprocess.run(  # noqa: S603 - test uses a fixed local Docker executable and argv
        [docker_executable, "info"],
        check=False,
        capture_output=True,
        timeout=10,
    )
    if info.returncode != 0:
        return None
    inspect = subprocess.run(  # noqa: S603 - test uses a fixed local Docker executable and argv
        [
            docker_executable,
            "image",
            "inspect",
            "--format",
            "{{.Id}}",
            "evofit-bench-app:latest",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if inspect.returncode != 0:
        return None
    return inspect.stdout.strip()


def test_docker_command_mounts_only_method_input_and_output(
    synthetic_repository: tuple[Path, str, str],
    tmp_path: Path,
) -> None:
    repository, before_sha, after_sha = synthetic_repository
    bundle = tmp_path / "B1-input"
    export_method_inputs(repository, bundle, "B1", before_sha, after_sha)
    output = tmp_path / "B1-output"
    output.mkdir()
    digest = "sha256:" + "1" * 64
    command = build_docker_command(bundle, output, digest, ["python", "--version"], "B1", 10)
    assert "--network=none" in command
    assert "--read-only" in command
    assert "--cap-drop=ALL" in command
    assert "--security-opt=no-new-privileges" in command
    mount_values = [
        command[index + 1] for index, item in enumerate(command[:-1]) if item == "--mount"
    ]
    assert len(mount_values) == 2
    assert all(
        "target=/input,readonly" in mount or "target=/output" in mount for mount in mount_values
    )
    assert str(repository) not in " ".join(command)
    with pytest.raises(IsolationError, match="full SHA-256"):
        build_docker_command(bundle, output, "python:3.12", ["python"], "B1", 10)


def test_container_negative_probes_cannot_reach_oracle_history_network_or_other_output(
    synthetic_repository: tuple[Path, str, str],
    tmp_path: Path,
) -> None:
    image_digest = _local_image_digest()
    if image_digest is None:
        pytest.skip("No local Docker runtime image digest is available for the isolation probe")

    repository, before_sha, after_sha = synthetic_repository
    bundle = tmp_path / "P-input"
    export_method_inputs(repository, bundle, "P", before_sha, after_sha)
    output = tmp_path / "P-output"
    output.mkdir()
    other_output = tmp_path / "B1-output" / "sealed-secret.json"
    other_output.parent.mkdir()
    other_output.write_text("private sibling output", encoding="utf-8")
    private_ground_truth = repository / "experiments/scenarios/DA99/ground_truth.yaml"
    script = (
        "import json, pathlib, socket\n"
        f"private = {str(private_ground_truth)!r}\n"
        f"other = {str(other_output)!r}\n"
        "def denied(path):\n"
        "    try:\n"
        "        pathlib.Path(path).read_bytes()\n"
        "    except OSError:\n"
        "        return True\n"
        "    return False\n"
        "result = {\n"
        "    'ground_truth_denied': denied(private),\n"
        "    'other_output_denied': denied(other),\n"
        "    'git_history_absent': not pathlib.Path('/input/.git').exists() "
        "and not pathlib.Path('/repo/.git').exists(),\n"
        "    'input_write_denied': False,\n"
        "    'network_denied': False,\n"
        "}\n"
        "try:\n"
        "    pathlib.Path('/input/attempt.txt').write_text('bad')\n"
        "except OSError:\n"
        "    result['input_write_denied'] = True\n"
        "try:\n"
        "    socket.create_connection(('1.1.1.1', 443), timeout=0.5)\n"
        "except OSError:\n"
        "    result['network_denied'] = True\n"
        "pathlib.Path('/output/probe.json').write_text(json.dumps(result))\n"
    )
    execution = run_isolated_method(
        bundle,
        output,
        image_digest,
        ["python", "-c", script],
        "P",
        timeout_seconds=15,
    )
    assert execution.exit_code == 0
    result = json.loads((output / "probe.json").read_text(encoding="utf-8"))
    assert all(result.values())
    assert execution.stdout_sha256 == sha256_bytes(execution.stdout_path.read_bytes())
    assert execution.stderr_sha256 == sha256_bytes(execution.stderr_path.read_bytes())
