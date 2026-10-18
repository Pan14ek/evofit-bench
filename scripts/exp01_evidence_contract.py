"""Versioned artifact and validation helpers for EXP-01 DEVELOPMENT evidence."""

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "experiments/schemas/development_evidence_bundle_v1.schema.json"
BUNDLE_FILENAME = "evidence_bundle.json"
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
EXPECTED_STAGES = ("ci_test", "deployment", "runtime")


def sha256_bytes(content: bytes) -> str:
    """Return the lowercase SHA-256 digest of exact artifact bytes."""
    return hashlib.sha256(content).hexdigest()


def validate_run_id(run_id: str) -> str:
    """Accept one short filesystem-safe path component."""
    if not RUN_ID_PATTERN.fullmatch(run_id) or run_id in {".", ".."}:
        raise ValueError("run-id must be 1-64 ASCII letters, digits, dots, underscores, or hyphens")
    return run_id


def _safe_relative_path(path_text: str) -> PurePosixPath:
    """Reject absolute paths, traversal, and platform-specific separators."""
    if "\\" in path_text:
        raise ValueError("artifact path contains a backslash")
    path = PurePosixPath(path_text)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("artifact path must be a safe relative path")
    return path


def write_artifact(
    run_dir: Path,
    relative_path: str,
    content: bytes,
    *,
    media_type: str,
    role: str,
    source_path: str | None = None,
) -> dict[str, Any]:
    """Write one immutable run artifact and return its digest-bound reference."""
    relative = _safe_relative_path(relative_path)
    run_root = run_dir.resolve()
    target = run_root.joinpath(*relative.parts)
    if target.exists() or target.is_symlink():
        raise FileExistsError(f"refusing to overwrite run artifact {relative_path}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return {
        "path": relative.as_posix(),
        "sha256": sha256_bytes(content),
        "size_bytes": len(content),
        "media_type": media_type,
        "role": role,
        "source_path": source_path,
    }


def copy_input_artifact(run_dir: Path, relative_source_path: str, role: str) -> dict[str, Any]:
    """Copy a repository input into the run so its exact bytes travel with the bundle."""
    source_relative = _safe_relative_path(relative_source_path)
    source = ROOT.joinpath(*source_relative.parts)
    if not source.is_file() or source.is_symlink():
        raise FileNotFoundError(f"required repository input is unavailable: {relative_source_path}")
    suffix = source.suffix.lower()
    media_type = {
        ".json": "application/json",
        ".toml": "application/toml",
        ".yaml": "application/yaml",
        ".yml": "application/yaml",
        ".py": "text/x-python",
        ".md": "text/markdown",
    }.get(suffix, "application/octet-stream")
    return write_artifact(
        run_dir,
        f"inputs/{source_relative.as_posix()}",
        source.read_bytes(),
        media_type=media_type,
        role=role,
        source_path=source_relative.as_posix(),
    )


def _artifact_references(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect every artifact reference, including nested stage outputs."""
    references = list(bundle["input_artifacts"])
    references.extend(
        [
            bundle["architecture"]["manifest_artifact"],
            bundle["fitness_configuration"]["configuration_artifact"],
            bundle["execution_context"]["schema_artifact"],
        ]
    )
    for record in bundle["records"]:
        for field in ("configuration_artifact", "input_artifacts", "raw_output_artifacts"):
            value = record[field]
            if isinstance(value, list):
                references.extend(value)
            elif value is not None:
                references.append(value)
    return references


def make_artifact_inventory(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    """Return one stable artifact reference per relative path."""
    references_by_path: dict[str, dict[str, Any]] = {}
    for reference in _artifact_references(bundle):
        path = reference["path"]
        previous = references_by_path.get(path)
        if previous is not None and previous != reference:
            raise ValueError(f"artifact references disagree for {path}")
        references_by_path[path] = reference
    return [references_by_path[path] for path in sorted(references_by_path)]


def _validate_schema(bundle: dict[str, Any]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(bundle), key=lambda error: list(error.absolute_path))
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "<root>"
        raise ValueError(f"evidence bundle schema violation at {location}: {first.message}")


def validate_bundle(run_dir: Path) -> dict[str, Any]:
    """Read back and fail closed on malformed, cross-revision, or tampered bundles."""
    if run_dir.is_symlink() or not run_dir.is_dir():
        raise ValueError("evidence run directory must be a real directory")
    bundle_path = run_dir / BUNDLE_FILENAME
    if bundle_path.is_symlink() or not bundle_path.is_file():
        raise ValueError("evidence bundle file is missing or is a symlink")
    try:
        bundle: dict[str, Any] = json.loads(bundle_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("evidence bundle is not readable JSON") from error
    _validate_schema(bundle)
    validate_run_id(bundle["run_id"])

    if bundle["run_id"] != run_dir.name:
        raise ValueError("bundle run-id does not match its output directory")
    stage_list = [record["lifecycle_stage"] for record in bundle["records"]]
    if sorted(stage_list) != sorted(EXPECTED_STAGES):
        raise ValueError("bundle must contain exactly one record for each supported stage")
    expected_status = (
        "complete"
        if all(record["status"] == "available" for record in bundle["records"])
        else "incomplete"
    )
    if bundle["bundle_status"] != expected_status:
        raise ValueError("bundle status does not match stage evidence availability")

    source_revision = bundle["source_revision"]["commit_sha"]
    for record in bundle["records"]:
        if record["run_id"] != bundle["run_id"]:
            raise ValueError("stage record run-id differs from the bundle run-id")
        if record["source_revision"] != source_revision:
            raise ValueError("stage record source revision differs from the bundle revision")
        started = datetime.fromisoformat(record["started_at_utc"].replace("Z", "+00:00"))
        ended = datetime.fromisoformat(record["ended_at_utc"].replace("Z", "+00:00"))
        if ended < started:
            raise ValueError("stage record end time precedes its start time")

    inventory: dict[str, dict[str, Any]] = {}
    root = run_dir.resolve()
    for reference in bundle["artifact_inventory"]:
        path_text = reference["path"]
        relative = _safe_relative_path(path_text)
        if path_text in inventory:
            raise ValueError(f"duplicate artifact inventory path: {path_text}")
        target = root.joinpath(*relative.parts)
        if target.is_symlink() or not target.is_file():
            raise ValueError(f"artifact is missing or is a symlink: {path_text}")
        try:
            target.resolve().relative_to(root)
        except ValueError as error:
            raise ValueError(f"artifact resolves outside the run directory: {path_text}") from error
        content = target.read_bytes()
        if len(content) != reference["size_bytes"]:
            raise ValueError(f"artifact size mismatch: {path_text}")
        if sha256_bytes(content) != reference["sha256"]:
            raise ValueError(f"artifact digest mismatch: {path_text}")
        inventory[path_text] = reference

    referenced_paths = {reference["path"] for reference in _artifact_references(bundle)}
    if referenced_paths != set(inventory):
        raise ValueError("artifact inventory does not exactly match bundle references")
    for reference in _artifact_references(bundle):
        if inventory.get(reference["path"]) != reference:
            raise ValueError(f"artifact reference digest mismatch: {reference['path']}")
    return bundle


def write_bundle(run_dir: Path, bundle: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    """Persist a bundle once, read it back, and validate its schema and artifacts."""
    bundle_path = run_dir / BUNDLE_FILENAME
    if bundle_path.exists() or bundle_path.is_symlink():
        raise FileExistsError("refusing to overwrite evidence_bundle.json")
    bundle["artifact_inventory"] = make_artifact_inventory(bundle)
    _validate_schema(bundle)
    bundle_path.write_text(
        json.dumps(bundle, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    validated = validate_bundle(run_dir)
    return bundle_path, validated
