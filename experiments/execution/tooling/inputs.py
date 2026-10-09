"""Export pinned, allowlisted method inputs without copying a repository checkout."""

from __future__ import annotations

import io
import json
import re
import shutil
import subprocess  # nosec B404 - fixed Git executable and validated argv, never a shell
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any, Literal, cast

import yaml

from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError, ProtocolError
from experiments.execution.tooling.hashing import bundle_sha256, pretty_json_bytes, sha256_bytes

MethodId = Literal["B0", "B1", "P"]
ALLOWLIST_VERSION = "DA01_METHOD_INPUTS_V1"
FORBIDDEN_PATH_PARTS = {
    ".git",
    "acceptance",
    "answers",
    "experiments",
    "ground_truth",
    "groundtruth",
    "oracle",
    "reference",
    "scorer",
    "scenario.yaml",
    "scenario",
    "readme.md",
    "validation.md",
    "results",
}
FORBIDDEN_CONTENT_MARKERS = (
    b"expected_operations",
    b"affected_targets",
    b"ground_truth_path",
    b"new_obligations",
)
FITNESS_INPUTS: tuple[tuple[str, str, str], ...] = (
    ("fitness/configs/a0-monolith.yaml", "fitness/a0-monolith.yaml", "fitness_configuration"),
    (
        "fitness/catalog/a0-fitness-elements.yaml",
        "fitness/a0-representations.yaml",
        "representation_catalog",
    ),
    (
        "fitness/catalog/architectural-obligations.yaml",
        "fitness/obligations.yaml",
        "obligation_registry",
    ),
    (
        "fitness/evaluators/a0/importlinter.toml",
        "fitness/a0-importlinter.toml",
        "legacy_evaluator",
    ),
)
TRACEABILITY_INPUT = (
    "fitness/traceability/a0-traceability.yaml",
    "fitness/a0-traceability.yaml",
    "traceability",
)
CAPABILITIES_PATH = "fitness/evaluator-capabilities.json"


def export_method_inputs(
    repository: Path,
    output_directory: Path,
    method_id: MethodId,
    architecture_before_sha: str,
    architecture_source_sha: str,
) -> dict[str, Any]:
    """Create a new method bundle from exact Git blobs and verify its allowlist.

    The bundle excludes the repository metadata and all experiment/scorer files.
    Output must be a new directory outside the checkout.
    """
    root = repository.resolve(strict=True)
    destination = output_directory.resolve()
    _validate_repository_root(root)
    _validate_commit_id(architecture_before_sha, "architecture_before_sha")
    _validate_commit_id(architecture_source_sha, "architecture_source_sha")
    if destination.exists():
        raise ProtocolError(f"Bundle output already exists: {destination}")
    if destination.is_relative_to(root):
        raise ProtocolError("Method input bundles must be created outside the repository checkout")
    if "," in str(destination):
        raise ProtocolError("Docker bind-mount paths cannot contain commas")

    files: list[dict[str, Any]] = []
    destination.mkdir(parents=True)
    try:
        before_tree_sha = _git_text(root, "rev-parse", f"{architecture_before_sha}:app").strip()
        after_tree_sha = _git_text(root, "rev-parse", f"{architecture_source_sha}:app").strip()
        before_source = _export_app_tree(
            root, architecture_before_sha, destination / "architecture/before"
        )
        after_source = _export_app_tree(
            root, architecture_source_sha, destination / "architecture/after"
        )
        files.extend(_file_records(before_source, "architecture_before_source", destination))
        files.extend(_file_records(after_source, "architecture_after_source", destination))

        observations = _architecture_observations(
            root,
            architecture_source_sha,
            before_source,
            after_source,
        )
        observation_path = destination / "architecture/observations.json"
        _write_new_file(observation_path, pretty_json_bytes(observations))
        files.extend(_file_records([observation_path], "architecture_observations", destination))

        for source_path, bundle_path, role in FITNESS_INPUTS:
            content = _git_blob(root, architecture_source_sha, source_path)
            path = destination / bundle_path
            _write_new_file(path, content)
            files.extend(_file_records([path], role, destination))

        if method_id in ("B1", "P"):
            capabilities = {
                "schema_version": 1,
                "inventory_version": "EVALUATOR_CAPABILITIES_V1",
                "evaluators": [
                    {"id": "import_linter", "stages": ["ci"]},
                    {"id": "pytest", "stages": ["test"]},
                    {"id": "locust", "stages": ["test"]},
                    {"id": "prometheus", "stages": ["runtime"]},
                ],
                "generic_candidate_templates": [],
                "prepared_reference_checkers_included": False,
            }
            capabilities_path = destination / CAPABILITIES_PATH
            _write_new_file(capabilities_path, pretty_json_bytes(capabilities))
            files.extend(_file_records([capabilities_path], "evaluator_capabilities", destination))

        if method_id == "P":
            source_path, bundle_path, role = TRACEABILITY_INPUT
            traceability = _git_blob(root, architecture_source_sha, source_path)
            path = destination / bundle_path
            _write_new_file(path, traceability)
            files.extend(_file_records([path], role, destination))

        manifest: dict[str, Any] = {
            "schema_version": 1,
            "allowlist_version": ALLOWLIST_VERSION,
            "method_id": method_id,
            "architecture_before_sha": architecture_before_sha,
            "architecture_source_sha": architecture_source_sha,
            "before_tree_sha": before_tree_sha,
            "after_tree_sha": after_tree_sha,
            "files": sorted(files, key=lambda entry: str(entry["path"])),
        }
        manifest["bundle_sha256"] = bundle_sha256(manifest["files"])
        validate_payload("method_input.schema.json", manifest)
        _write_new_file(destination / "method_input.json", pretty_json_bytes(manifest))
        verify_method_bundle(destination, expected_method_id=method_id)
        return manifest
    except (
        ContractValidationError,
        OSError,
        ProtocolError,
        subprocess.SubprocessError,
        tarfile.TarError,
    ):
        shutil.rmtree(destination, ignore_errors=True)
        raise


def verify_method_bundle(
    bundle_directory: Path,
    expected_method_id: MethodId | None = None,
) -> dict[str, Any]:
    """Verify the manifest, exact file inventory, hashes, and forbidden content."""
    bundle_root = bundle_directory.resolve(strict=True)
    if not bundle_root.is_dir():
        raise ProtocolError(f"Method bundle is not a directory: {bundle_root}")
    manifest_path = bundle_root / "method_input.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ProtocolError("Method bundle manifest must be a regular file")
    manifest = cast(dict[str, Any], json.loads(manifest_path.read_text(encoding="utf-8")))
    validate_payload("method_input.schema.json", manifest)
    method_id = cast(MethodId, manifest["method_id"])
    if expected_method_id is not None and method_id != expected_method_id:
        raise ProtocolError(f"Expected {expected_method_id} bundle, found {method_id}")

    declared: dict[str, dict[str, Any]] = {}
    for entry in cast(list[dict[str, Any]], manifest["files"]):
        bundle_relative = PurePosixPath(str(entry["path"]))
        _validate_bundle_relative_path(bundle_relative)
        relative_path = bundle_relative.as_posix()
        _verify_path_role(bundle_relative, str(entry["role"]), method_id)
        if relative_path in declared:
            raise ProtocolError(f"Duplicate bundle manifest path: {relative_path}")
        declared[relative_path] = entry

    actual_files: set[str] = set()
    for path in bundle_root.rglob("*"):
        if path.is_symlink():
            raise ProtocolError(
                f"Method bundle contains a symlink: {path.relative_to(bundle_root)}"
            )
        if path.is_file() and path != manifest_path:
            relative = path.relative_to(bundle_root).as_posix()
            _validate_bundle_relative_path(PurePosixPath(relative))
            actual_files.add(relative)
    if actual_files != set(declared):
        missing = sorted(set(declared) - actual_files)
        unexpected = sorted(actual_files - set(declared))
        raise ProtocolError(
            f"Bundle inventory mismatch; missing={missing}, unexpected={unexpected}"
        )

    for relative, entry in declared.items():
        file_path = bundle_root / relative
        content = file_path.read_bytes()
        if len(content) != entry["size_bytes"] or sha256_bytes(content) != entry["sha256"]:
            raise ProtocolError(f"Method input hash mismatch: {relative}")
        lowered = content.lower()
        marker = next((value for value in FORBIDDEN_CONTENT_MARKERS if value in lowered), None)
        if marker is not None:
            raise ProtocolError(
                f"Forbidden oracle-field marker in method input {relative}: {marker!r}"
            )

    if bundle_sha256(manifest["files"]) != manifest["bundle_sha256"]:
        raise ProtocolError("Method input bundle hash does not match its manifest")
    required_roles = {
        "architecture_before_source",
        "architecture_after_source",
        "architecture_observations",
        "fitness_configuration",
        "representation_catalog",
        "obligation_registry",
        "legacy_evaluator",
    }
    if method_id in ("B1", "P"):
        required_roles.add("evaluator_capabilities")
    if method_id == "P":
        required_roles.add("traceability")
    observed_roles = {str(entry["role"]) for entry in manifest["files"]}
    if observed_roles != required_roles:
        raise ProtocolError(
            f"Method bundle roles do not match {method_id} allowlist; "
            f"expected={sorted(required_roles)}, observed={sorted(observed_roles)}"
        )
    return manifest


def _validate_repository_root(repository: Path) -> None:
    top_level = Path(_git_text(repository, "rev-parse", "--show-toplevel").strip()).resolve()
    if top_level != repository:
        raise ProtocolError(f"Repository path must be the Git root: {top_level}")


def _validate_commit_id(revision: str, field_name: str) -> None:
    if re.fullmatch(r"[a-f0-9]{40}", revision) is None:
        raise ProtocolError(f"{field_name} must be a full lowercase Git commit SHA")


def _git_text(repository: Path, *arguments: str) -> str:
    try:
        result = subprocess.run(  # noqa: S603  # nosec B603 - fixed local Git executable and argv
            [_git_executable(), "-C", str(repository), *arguments],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except subprocess.CalledProcessError as error:
        raise ProtocolError(f"Git command failed: git {' '.join(arguments)}") from error
    return result.stdout


def _export_app_tree(repository: Path, revision: str, bundle_directory: Path) -> list[Path]:
    try:
        archive = subprocess.run(  # noqa: S603  # nosec B603 - fixed local Git executable and argv
            [
                _git_executable(),
                "-C",
                str(repository),
                "archive",
                "--format=tar",
                revision,
                "app",
            ],
            check=True,
            capture_output=True,
        ).stdout
    except subprocess.CalledProcessError as error:
        raise ProtocolError(f"Could not export app source at {revision}") from error

    exported: list[Path] = []
    bundle_directory.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as archive_file:
        for member in archive_file.getmembers():
            if member.issym() or member.islnk():
                raise ProtocolError(f"Architecture source contains a symlink: {member.name}")
            if not member.isfile() or not member.name.endswith(".py"):
                continue
            relative = PurePosixPath(member.name)
            if relative.parts[0] != "app" or ".." in relative.parts or ".git" in relative.parts:
                raise ProtocolError(f"Unexpected architecture source path: {member.name}")
            file_content = archive_file.extractfile(member)
            if file_content is None:
                raise ProtocolError(f"Could not read architecture source: {member.name}")
            destination = bundle_directory / Path(*relative.parts[1:])
            _write_new_file(destination, file_content.read())
            exported.append(destination)
    if not exported:
        raise ProtocolError(
            f"No Python application files found at architecture revision {revision}"
        )
    return exported


def _architecture_observations(
    repository: Path,
    revision: str,
    before_files: list[Path],
    after_files: list[Path],
) -> dict[str, Any]:
    manifest_bytes = _git_blob(
        repository,
        revision,
        "architecture/states/A0_1_CAPABILITY_MODULES.yaml",
    )
    raw_manifest = yaml.safe_load(manifest_bytes)
    if not isinstance(raw_manifest, dict):
        raise ProtocolError("Architecture state manifest must be a mapping")
    structural_keys = (
        "architecture_state",
        "source_state",
        "deployment",
        "shared_infrastructure",
        "modules",
        "preserved_cross_module_dependencies",
    )
    structural_manifest = {key: raw_manifest[key] for key in structural_keys if key in raw_manifest}
    before_modules = sorted(_module_names(before_files))
    after_modules = sorted(_module_names(after_files))
    return {
        "schema_version": 1,
        "before_module_names": before_modules,
        "after_module_names": after_modules,
        "added_module_names": sorted(set(after_modules) - set(before_modules)),
        "removed_module_names": sorted(set(before_modules) - set(after_modules)),
        "target_structural_manifest": structural_manifest,
    }


def _module_names(files: list[Path]) -> set[str]:
    result: set[str] = set()
    for path in files:
        relative = path.parts
        if "app" not in relative:
            continue
        app_index = max(index for index, part in enumerate(relative) if part == "app")
        module_parts = list(relative[app_index:])
        module_parts[-1] = module_parts[-1][:-3]
        if module_parts[-1] == "__init__":
            module_parts.pop()
        if module_parts:
            result.add(".".join(module_parts))
    return result


def _git_blob(repository: Path, revision: str, relative_path: str) -> bytes:
    pure_path = PurePosixPath(relative_path)
    if pure_path.is_absolute() or ".." in pure_path.parts:
        raise ProtocolError(f"Unsafe Git path: {relative_path}")
    try:
        entry = subprocess.run(  # noqa: S603  # nosec B603 - validated commit and allowlisted path
            [_git_executable(), "-C", str(repository), "ls-tree", revision, "--", relative_path],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip()
        if not entry or not entry.startswith(("100644 blob ", "100755 blob ")):
            raise ProtocolError(
                f"Allowlisted Git path is missing or not a regular file: {relative_path}"
            )
        return subprocess.run(  # noqa: S603  # nosec B603 - validated commit and allowlisted path
            [_git_executable(), "-C", str(repository), "show", f"{revision}:{relative_path}"],
            check=True,
            capture_output=True,
        ).stdout
    except subprocess.CalledProcessError as error:
        raise ProtocolError(f"Could not read allowlisted Git path: {relative_path}") from error


def _file_records(files: list[Path], role: str, bundle_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in files:
        relative = path.relative_to(bundle_root).as_posix()
        _validate_bundle_relative_path(PurePosixPath(relative))
        content = path.read_bytes()
        records.append(
            {
                "path": relative,
                "role": role,
                "size_bytes": len(content),
                "sha256": sha256_bytes(content),
            }
        )
    return records


def _validate_bundle_relative_path(path: PurePosixPath) -> None:
    lowered_parts = {part.lower() for part in path.parts}
    forbidden = lowered_parts.intersection(FORBIDDEN_PATH_PARTS)
    if path.is_absolute() or ".." in path.parts or forbidden or "\\" in path.as_posix():
        raise ProtocolError(f"Forbidden or unsafe method-input path: {path.as_posix()}")


def _verify_path_role(path: PurePosixPath, role: str, method_id: MethodId) -> None:
    fixed_roles = {
        "architecture/observations.json": "architecture_observations",
        "fitness/a0-monolith.yaml": "fitness_configuration",
        "fitness/a0-representations.yaml": "representation_catalog",
        "fitness/obligations.yaml": "obligation_registry",
        "fitness/a0-importlinter.toml": "legacy_evaluator",
        CAPABILITIES_PATH: "evaluator_capabilities",
        TRACEABILITY_INPUT[1]: "traceability",
    }
    relative = path.as_posix()
    if fixed_roles.get(relative) == role:
        if role == "evaluator_capabilities" and method_id == "B0":
            raise ProtocolError("B0 may not receive the B1/P evaluator capability inventory")
        if role == "traceability" and method_id != "P":
            raise ProtocolError("Only P may receive the A0 traceability model")
        return
    source_roles = (
        ("architecture/before/", "architecture_before_source"),
        ("architecture/after/", "architecture_after_source"),
    )
    for prefix, expected_role in source_roles:
        if relative.startswith(prefix) and relative.endswith(".py") and role == expected_role:
            return
    raise ProtocolError(f"Path and role are not in the {method_id} allowlist: {relative} ({role})")


def _write_new_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as file_handle:
        file_handle.write(content)


def _git_executable() -> str:
    executable = shutil.which("git")
    if executable is None:
        raise ProtocolError("Git executable is unavailable")
    return executable


__all__ = ["ALLOWLIST_VERSION", "MethodId", "export_method_inputs", "verify_method_bundle"]
