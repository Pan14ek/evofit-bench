"""State-aware provenance records for future execution evidence."""

from __future__ import annotations

import platform
import sys
from collections.abc import Mapping, Sequence
from typing import Any

from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ProtocolError


def build_provenance(
    *,
    execution_id: str,
    architecture_state: str,
    architecture_source_sha: str,
    infrastructure_revision: str,
    method_id: str,
    method_version: str,
    fitness_configuration_version: str,
    fitness_configuration_sha256: str,
    input_bundle_sha256: str,
    prediction_sha256: str,
    dependency_lock_sha256: str,
    started_at_utc: str,
    ended_at_utc: str,
    timings_ms: Mapping[str, float | None],
    failure_statuses: Sequence[str] = (),
    evaluator_runs: Sequence[Mapping[str, Any]] = (),
    architecture_tree_sha: str | None = None,
    method_source_revision: str | None = None,
    prediction_sealed_at_utc: str | None = None,
    workload_profile_identity: str | None = None,
    workload_profile_sha256: str | None = None,
    evaluator_version: str | None = None,
    container_image_digest: str | None = None,
) -> dict[str, Any]:
    """Create and validate a state-aware manifest without guessing provenance."""
    if (workload_profile_identity is None) != (workload_profile_sha256 is None):
        raise ProtocolError(
            "Workload profile identity and hash must both be present or both be null"
        )
    if (
        architecture_state == "A0_MONOLITH"
        and architecture_source_sha != "b78b0967be937634b7762baccf5ac6892b279a73"
    ):
        raise ProtocolError("A0_MONOLITH provenance must reference the frozen A0 source commit")
    record: dict[str, Any] = {
        "schema_version": 1,
        "execution_id": execution_id,
        "architecture_state": architecture_state,
        "architecture_source_sha": architecture_source_sha,
        "architecture_tree_sha": architecture_tree_sha,
        "infrastructure_revision": infrastructure_revision,
        "method_id": method_id,
        "method_version": method_version,
        "method_source_revision": method_source_revision,
        "fitness_configuration_version": fitness_configuration_version,
        "fitness_configuration_sha256": fitness_configuration_sha256,
        "input_bundle_sha256": input_bundle_sha256,
        "prediction_sha256": prediction_sha256,
        "prediction_sealed_at_utc": prediction_sealed_at_utc,
        "workload_profile_identity": workload_profile_identity,
        "workload_profile_sha256": workload_profile_sha256,
        "dependency_lock_sha256": dependency_lock_sha256,
        "python_version": platform.python_version(),
        "evaluator_version": evaluator_version,
        "container_image_digest": container_image_digest,
        "operating_system": f"{platform.system()} {platform.release()} {platform.machine()}",
        "started_at_utc": started_at_utc,
        "ended_at_utc": ended_at_utc,
        "timings_ms": dict(timings_ms),
        "failure_statuses": list(failure_statuses),
        "evaluator_runs": [dict(run) for run in evaluator_runs],
    }
    validate_payload("provenance.schema.json", record)
    return record


def runtime_python_version() -> str:
    """Return the interpreter version recorded in method provenance."""
    return sys.version.split()[0]


__all__ = ["build_provenance", "runtime_python_version"]
