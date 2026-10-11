"""Frozen, no-adaptation B0 baseline helpers."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from experiments.execution.tooling.contracts import validate_candidate
from experiments.execution.tooling.errors import ProtocolError
from experiments.execution.tooling.hashing import sha256_bytes, sha256_file

B0_METHOD_VERSION = "B0_UNCHANGED_V1"


def build_b0_prediction(
    architecture_source_sha: str,
    input_bundle_sha256: str,
) -> dict[str, Any]:
    """Build B0's empty impact and operation prediction without oracle access."""
    return {
        "schema_version": 1,
        "method_id": "B0",
        "architecture_source_sha": architecture_source_sha,
        "method_version": B0_METHOD_VERSION,
        "input_bundle_sha256": input_bundle_sha256,
        "predicted_affected": [],
        "proposed_operations": [],
        "explanations": [],
        "artifact_hashes": {},
    }


def copy_frozen_configuration(source: Path, destination: Path, expected_sha256: str) -> str:
    """Copy a frozen A0 fitness configuration byte-for-byte into method output."""
    if not source.is_file() or source.is_symlink():
        raise ProtocolError("Frozen B0 configuration must be a regular file")
    if destination.exists():
        raise ProtocolError(
            "B0 candidate path already exists; configuration outputs are write-once"
        )
    content = source.read_bytes()
    if sha256_bytes(content) != expected_sha256:
        raise ProtocolError("B0 configuration does not match its allowlisted input hash")
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    except FileExistsError as error:
        raise ProtocolError(
            "B0 candidate path already exists; configuration outputs are write-once"
        ) from error
    with os.fdopen(descriptor, "wb") as file_handle:
        file_handle.write(content)
        file_handle.flush()
        os.fsync(file_handle.fileno())
    destination.chmod(0o444)
    digest = sha256_file(destination)
    if digest != sha256_bytes(content):
        raise ProtocolError("B0 configuration copy differs from frozen source bytes")
    return digest


def build_b0_candidate(
    configuration: Mapping[str, Any],
    representation_catalog: Mapping[str, Any],
    architecture_source_sha: str,
    configuration_sha256: str,
    legacy_evaluator_sha256: str,
) -> dict[str, Any]:
    """Describe the unchanged A0 configuration for assessment on the target state."""
    configured = configuration.get("representations")
    catalog = representation_catalog.get("representations")
    if not isinstance(configured, list) or not isinstance(catalog, list):
        raise ProtocolError("B0 requires the frozen configuration and representation catalog")
    by_semantics = _representation_semantics(configured)
    catalog_semantics = _representation_semantics(catalog)
    if len(configured) != len(catalog) or by_semantics != catalog_semantics:
        raise ProtocolError("Frozen B0 configuration and representation catalog do not match")
    active_criteria = {
        str(item["id"]): bool(item.get("active", False))
        for item in configuration.get("criteria", [])
    }
    representations: list[dict[str, Any]] = []
    for item in catalog:
        evaluator_artifact = None
        if item["evaluator"] == "import_linter":
            evaluator_artifact = {
                "path": "fitness/a0-importlinter.toml",
                "sha256": legacy_evaluator_sha256,
            }
        representations.append(
            {
                "id": item["id"],
                "active": active_criteria.get(str(item["criterion"]), False),
                "criterion": item["criterion"],
                "stage": item["stage"],
                "evaluator": item["evaluator"],
                "evaluator_artifact": evaluator_artifact,
                "covers": list(item.get("covers", [])),
                "applicability_scope": {"declared_architecture_state": "A0_MONOLITH"},
                "evidence_contract": {"metrics": list(item["metrics"])},
            }
        )
    candidate = {
        "schema_version": 1,
        "method_id": "B0",
        "architecture_source_sha": architecture_source_sha,
        "configuration_version": "B0_UNCHANGED_A0_V1",
        "parent_configuration": {
            "path": "fitness/configs/a0-monolith.yaml",
            "sha256": configuration_sha256,
        },
        "representations": representations,
        "changes": [],
        "candidate_validation": {"status": "not_run", "reason_codes": ["PHASE_A_ONLY"]},
    }
    validate_candidate(candidate)
    return candidate


def _representation_semantics(
    items: list[dict[str, Any]],
) -> set[tuple[str, str, str, tuple[str, ...]]]:
    return {
        (
            str(item["criterion"]),
            str(item["stage"]),
            str(item["evaluator"]),
            tuple(str(metric) for metric in item["metrics"]),
        )
        for item in items
    }


__all__ = [
    "B0_METHOD_VERSION",
    "build_b0_candidate",
    "build_b0_prediction",
    "copy_frozen_configuration",
]
