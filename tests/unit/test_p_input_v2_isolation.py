"""Synthetic isolation and reproducibility tests for the V2 candidate exporter."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from experiments.execution.tooling.errors import ContractValidationError, ProtocolError
from experiments.execution.tooling.hashing import bundle_sha256, sha256_bytes
from experiments.execution.tooling.p_input_export_v2 import (
    V2_ALLOWLIST_VERSION,
    export_method_inputs_v2,
    verify_method_bundle_v2,
)
from experiments.execution.tooling.p_input_validation import (
    ValidationStatus,
    load_and_validate_snapshot,
    validate_snapshot_schema,
)

_EVALUATION_AS_OF = "2026-10-13T00:00:00Z"


def _git(repository: Path, *arguments: str) -> str:
    executable = shutil.which("git")
    if executable is None:
        raise AssertionError("Git is required for the synthetic repository test")
    result = subprocess.run(  # noqa: S603 - fixed local Git executable and arguments
        [executable, "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _write(repository: Path, relative: str, content: str) -> None:
    path = repository / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _commit(repository: Path, message: str) -> str:
    _git(repository, "add", "-A")
    _git(
        repository,
        "-c",
        "user.name=V2 Synthetic Test",
        "-c",
        "user.email=v2-test@example.invalid",
        "commit",
        "-m",
        message,
    )
    return _git(repository, "rev-parse", "HEAD")


def _charter() -> dict[str, Any]:
    return {
        "schema_version": "1.1",
        "charter_id": "SYNTHETIC_V2_CHARTER",
        "version": "synthetic-v2-charter-v1",
        "effective_from": "2026-01-01T00:00:00Z",
        "effective_until": None,
        "role_permissions": {},
        "scope_hierarchy": [],
        "source_allowlist": [
            {"kind": "ARCHITECTURE_SOURCE", "path_prefix": "architecture/"},
            {
                "kind": "STRUCTURAL_OBSERVATION",
                "path_prefix": "architecture/structural-observations.json",
            },
            {"kind": "POLICY_REGISTRY", "path_prefix": "fitness/policy/registry.json"},
            {"kind": "APPROVAL", "path_prefix": "fitness/policy/approvals/"},
            {"kind": "EVIDENCE", "path_prefix": "fitness/policy/evidence/"},
        ],
        "precedence": [],
        "evidence_source_ids": ["AUTHORITY_EVIDENCE"],
    }


def _json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _synthetic_repository(root: Path) -> tuple[Path, str, str]:
    repository = root / "synthetic-v2-repo"
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.name", "V2 Synthetic Test")
    _git(repository, "config", "user.email", "v2-test@example.invalid")
    for relative, content in {
        "app/__init__.py": '"""Synthetic app."""\n',
        "app/api.py": "def handle() -> None:\n    return None\n",
        "app/storage.py": "def get() -> None:\n    return None\n",
        "fitness/configs/a0-monolith.yaml": (
            "architecture_state: SYNTHETIC_A0\nrepresentations: []\n"
        ),
        "fitness/catalog/a0-fitness-elements.yaml": "schema_version: 1\nrepresentations: []\n",
        "fitness/catalog/architectural-obligations.yaml": "schema_version: 1\nobligations: []\n",
        "fitness/evaluators/a0/importlinter.toml": "[tool.importlinter]\nroot_packages = ['app']\n",
        "fitness/traceability/a0-traceability.yaml": "schema_version: 1\nelements: []\n",
    }.items():
        _write(repository, relative, content)
    before_sha = _commit(repository, "synthetic before source")

    (repository / "app/api.py").unlink()
    _write(repository, "app/modules/__init__.py", '"""Synthetic modules."""\n')
    _write(repository, "app/modules/billing/__init__.py", '"""Billing module."""\n')
    _write(repository, "app/modules/billing/service.py", "def run() -> None:\n    return None\n")
    _write(
        repository,
        "architecture/states/A0_1_CAPABILITY_MODULES.yaml",
        """schema_version: 1
architecture_state: SYNTHETIC_TARGET
source_state: SYNTHETIC_SOURCE
scenario_id: DO_NOT_COPY_ME
deployment:
  deployment_units: 1
  application_processes: 1
  database_instances: 1
  database_product: PostgreSQL
  internal_communication: synchronous_python_calls
  message_broker: none
  expected_operations: NEVER_COPY
shared_infrastructure:
  - app.config
modules:
  billing:
    package: app.modules.billing
    required_files: [__init__.py, service.py]
    future: NEVER_COPY
preserved_cross_module_dependencies:
  - from: app.modules.billing.service
    to: app.storage
    rationale: SYNTHETIC_SECRET_SENTINEL_REDACT_THIS
    expected_operations: NEVER_COPY
governance:
  cross_module_public_api_enforcement: false
""",
    )
    _write(
        repository,
        "fitness/policy/authority-charter.json",
        _json(_charter()),
    )
    registry: dict[str, Any] = {
        "schema_version": "1.1",
        "registry_version": "synthetic-v2-registry-v1",
        "scope": "application",
        "as_of": _EVALUATION_AS_OF,
        "closure": "OPEN",
        "closure_claim_id": None,
        "authority_charter_source_id": "CHARTER",
        "policies": [],
    }
    _write(repository, "fitness/policy/registry.json", _json(registry))
    _write(
        repository,
        "fitness/policy/evidence/AUTHORITY_EVIDENCE.json",
        _json({"synthetic_only": True, "purpose": "test charter trust anchor"}),
    )
    after_sha = _commit(repository, "synthetic target with explicit open registry")
    return repository, before_sha, after_sha


@pytest.fixture
def synthetic_repository(tmp_path: Path) -> tuple[Path, str, str]:
    return _synthetic_repository(tmp_path)


def test_v2_schema_and_snapshot_projection_are_typed_and_strict() -> None:
    from experiments.execution.tooling.contracts import load_schema

    schema = load_schema("method_input_v2.schema.json")
    assert schema["properties"]["allowlist_version"]["const"] == V2_ALLOWLIST_VERSION

    snapshot = json.loads(
        (Path(__file__).parents[1] / "fixtures/p_input_contract_v11_snapshot.json").read_text(
            encoding="utf-8"
        )
    )
    validate_snapshot_schema(snapshot)
    snapshot["scenario_id"] = "FORBIDDEN"
    with pytest.raises(ContractValidationError):
        validate_snapshot_schema(snapshot)


def test_v2_b1_p_exports_share_snapshot_and_remove_nested_hints(
    synthetic_repository: tuple[Path, str, str], tmp_path: Path
) -> None:
    repository, before_sha, after_sha = synthetic_repository
    b1_root = tmp_path / "bundles/one/B1"
    p_root = tmp_path / "different/path/P"
    b1 = export_method_inputs_v2(
        repository, b1_root, "B1", before_sha, after_sha, _EVALUATION_AS_OF
    )
    p = export_method_inputs_v2(repository, p_root, "P", before_sha, after_sha, _EVALUATION_AS_OF)

    assert b1["profile_status"] == "DEVELOPMENT_UNFROZEN"
    assert b1["common_snapshot_sha256"] == p["common_snapshot_sha256"]
    assert (b1_root / "architecture-policy-snapshot.json").read_bytes() == (
        p_root / "architecture-policy-snapshot.json"
    ).read_bytes()
    assert "fitness/a0-traceability.yaml" not in {item["path"] for item in b1["files"]}
    assert "fitness/a0-traceability.yaml" in {item["path"] for item in p["files"]}
    bundle_bytes = b"\n".join(path.read_bytes() for path in p_root.rglob("*") if path.is_file())
    assert b"SYNTHETIC_SECRET_SENTINEL" not in bundle_bytes
    assert b"DO_NOT_COPY_ME" not in bundle_bytes
    assert b"NEVER_COPY" not in bundle_bytes

    before_inventory = json.loads(
        (b1_root / "architecture/before-inventory.json").read_text(encoding="utf-8")
    )
    before_init = next(
        item for item in before_inventory["files"] if item["path"] == "app/__init__.py"
    )
    assert before_init["git_blob_sha1"] == _git(
        repository, "rev-parse", f"{before_sha}:app/__init__.py"
    )

    snapshot = json.loads((p_root / "architecture-policy-snapshot.json").read_text())
    validate_snapshot_schema(snapshot)
    assert snapshot["policies"] == []
    fact_by_predicate = {fact["predicate"]: fact for fact in snapshot["facts"]}
    assert fact_by_predicate["deployment.unit_count_declared"]["value"] == 1
    assert fact_by_predicate["communication.broker_declared"]["value"] == "none"
    assert all("runtime" not in fact["predicate"] for fact in snapshot["facts"])
    assert verify_method_bundle_v2(b1_root)["bundle_sha256"] == bundle_sha256(b1["files"])
    assert verify_method_bundle_v2(p_root)["method_id"] == "P"

    result = load_and_validate_snapshot(p_root, p)
    assert result.schema_status is ValidationStatus.VALID
    assert result.integrity_status is ValidationStatus.VALID
    assert result.authority_status is ValidationStatus.UNDETERMINED
    assert result.fact_status is ValidationStatus.UNDETERMINED
    assert "REGISTRY_CLOSURE_UNVERIFIED" in result.reason_codes


def test_v2_missing_authority_fails_before_creating_output(
    synthetic_repository: tuple[Path, str, str], tmp_path: Path
) -> None:
    repository, before_sha, after_sha = synthetic_repository
    (repository / "fitness/policy/registry.json").unlink()
    _commit(repository, "remove explicit synthetic registry")
    after_sha = _git(repository, "rev-parse", "HEAD")
    output = tmp_path / "missing-authority"

    with pytest.raises(ContractValidationError, match="MISSING_AUTHORITY"):
        export_method_inputs_v2(repository, output, "B1", before_sha, after_sha, _EVALUATION_AS_OF)
    assert not output.exists()


def test_v2_rejects_malformed_extraction_and_cleans_partial_output(
    synthetic_repository: tuple[Path, str, str], tmp_path: Path
) -> None:
    repository, before_sha, _after_sha = synthetic_repository
    _write(
        repository,
        "architecture/states/A0_1_CAPABILITY_MODULES.yaml",
        "deployment:\n  deployment_units: true\n",
    )
    after_sha = _commit(repository, "malformed typed deployment source")
    output = tmp_path / "failed-extraction"

    with pytest.raises(ContractValidationError, match="nonnegative integer"):
        export_method_inputs_v2(repository, output, "B1", before_sha, after_sha, _EVALUATION_AS_OF)
    assert not output.exists()


def test_v2_verifier_rejects_nested_fields_even_with_rehashed_bundle(
    synthetic_repository: tuple[Path, str, str], tmp_path: Path
) -> None:
    repository, before_sha, after_sha = synthetic_repository
    output = tmp_path / "tampered"
    export_method_inputs_v2(repository, output, "B1", before_sha, after_sha, _EVALUATION_AS_OF)
    observation_path = output / "architecture/structural-observations.json"
    observation = json.loads(observation_path.read_text(encoding="utf-8"))
    observation["target_structural_manifest"]["preserved_cross_module_dependencies"][0][
        "rationale"
    ] = "SYNTHETIC_SECRET_SENTINEL"
    observation_bytes = (json.dumps(observation, sort_keys=True, indent=2) + "\n").encode()
    observation_path.write_bytes(observation_bytes)

    manifest_path = output / "method_input_v2.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = next(
        item
        for item in manifest["files"]
        if item["path"] == observation_path.relative_to(output).as_posix()
    )
    entry["size_bytes"] = len(observation_bytes)
    entry["sha256"] = sha256_bytes(observation_bytes)
    manifest["bundle_sha256"] = bundle_sha256(manifest["files"])
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")

    with pytest.raises(ProtocolError, match="only from and to"):
        verify_method_bundle_v2(output)


def test_v2_verifier_rejects_fact_tampering_after_rehash(
    synthetic_repository: tuple[Path, str, str], tmp_path: Path
) -> None:
    repository, before_sha, after_sha = synthetic_repository
    output = tmp_path / "tampered-fact"
    export_method_inputs_v2(repository, output, "B1", before_sha, after_sha, _EVALUATION_AS_OF)
    snapshot_path = output / "architecture-policy-snapshot.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    module_fact = next(
        fact
        for fact in snapshot["facts"]
        if fact["predicate"] == "component.python_module_identity" and fact["state"] == "after"
    )
    module_fact["value"] = ["app.fake"]
    snapshot_bytes = (json.dumps(snapshot, sort_keys=True, indent=2) + "\n").encode()
    snapshot_path.write_bytes(snapshot_bytes)
    manifest_path = output / "method_input_v2.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    snapshot_record = next(
        item for item in manifest["files"] if item["path"] == "architecture-policy-snapshot.json"
    )
    snapshot_record["size_bytes"] = len(snapshot_bytes)
    snapshot_record["sha256"] = sha256_bytes(snapshot_bytes)
    manifest["common_snapshot_sha256"] = sha256_bytes(snapshot_bytes)
    manifest["bundle_sha256"] = bundle_sha256(manifest["files"])
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")

    with pytest.raises(ProtocolError, match="COMMON_PROJECTION_MISMATCH"):
        verify_method_bundle_v2(output)


def test_v2_verifier_rejects_symlink_source_even_with_matching_hash(
    synthetic_repository: tuple[Path, str, str], tmp_path: Path
) -> None:
    repository, before_sha, after_sha = synthetic_repository
    output = tmp_path / "symlink-source"
    export_method_inputs_v2(repository, output, "B1", before_sha, after_sha, _EVALUATION_AS_OF)
    source = output / "architecture/before/__init__.py"
    outside = tmp_path / "outside.py"
    outside.write_bytes(source.read_bytes())
    source.unlink()
    source.symlink_to(outside)
    manifest_path = output / "method_input_v2.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    record = next(
        item for item in manifest["files"] if item["path"] == "architecture/before/__init__.py"
    )
    record["size_bytes"] = outside.stat().st_size
    record["sha256"] = sha256_bytes(outside.read_bytes())
    manifest["bundle_sha256"] = bundle_sha256(manifest["files"])
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")

    with pytest.raises(ProtocolError, match="symlink"):
        verify_method_bundle_v2(output)


def test_v2_verifier_rejects_architecture_source_with_matching_bundle_hash_but_wrong_git_blob(
    synthetic_repository: tuple[Path, str, str], tmp_path: Path
) -> None:
    repository, before_sha, after_sha = synthetic_repository
    output = tmp_path / "tampered-architecture"
    export_method_inputs_v2(repository, output, "B1", before_sha, after_sha, _EVALUATION_AS_OF)
    source_path = output / "architecture/after/modules/billing/service.py"
    changed = source_path.read_bytes() + b"\n# edited after export\n"
    source_path.write_bytes(changed)

    manifest_path = output / "method_input_v2.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    record = next(
        item
        for item in manifest["files"]
        if item["path"] == source_path.relative_to(output).as_posix()
    )
    record["size_bytes"] = len(changed)
    record["sha256"] = sha256_bytes(changed)
    manifest["bundle_sha256"] = bundle_sha256(manifest["files"])
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")

    with pytest.raises(ProtocolError, match="Git blob mismatch"):
        verify_method_bundle_v2(output)


def test_v2_verifier_rejects_structural_observation_with_wrong_source_pin(
    synthetic_repository: tuple[Path, str, str], tmp_path: Path
) -> None:
    repository, before_sha, after_sha = synthetic_repository
    output = tmp_path / "wrong-observation-pin"
    export_method_inputs_v2(repository, output, "B1", before_sha, after_sha, _EVALUATION_AS_OF)
    observation_path = output / "architecture/structural-observations.json"
    observation = json.loads(observation_path.read_text(encoding="utf-8"))
    observation["source_commit_sha"] = before_sha
    changed = (json.dumps(observation, sort_keys=True, indent=2) + "\n").encode()
    observation_path.write_bytes(changed)

    manifest_path = output / "method_input_v2.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    record = next(
        item
        for item in manifest["files"]
        if item["path"] == observation_path.relative_to(output).as_posix()
    )
    record["size_bytes"] = len(changed)
    record["sha256"] = sha256_bytes(changed)
    manifest["bundle_sha256"] = bundle_sha256(manifest["files"])
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")

    with pytest.raises(ProtocolError, match="VERSION_MISMATCH: structural observation source pin"):
        verify_method_bundle_v2(output)
