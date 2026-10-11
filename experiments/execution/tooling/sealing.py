"""Write-once, deterministic prediction sealing and read-only verification."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from experiments.execution.tooling.contracts import validate_payload, validate_prediction
from experiments.execution.tooling.errors import SealedArtifactError
from experiments.execution.tooling.hashing import canonical_json_bytes, sha256_bytes

PREDICTION_NAME = "prediction.json"
SEAL_NAME = "prediction.seal.json"


@dataclass(frozen=True)
class SealedPrediction:
    """Verified prediction bytes and their immutable seal metadata."""

    path: Path
    payload: dict[str, Any]
    sha256: str
    sealed_at_utc: str


def seal_prediction(
    payload: dict[str, Any],
    output_directory: Path,
    sealed_at_utc: str | None = None,
) -> SealedPrediction:
    """Persist canonical prediction bytes and a seal record without overwrite."""
    validate_prediction(payload)
    output_directory.mkdir(parents=True, exist_ok=True)
    prediction_path = output_directory / PREDICTION_NAME
    seal_path = output_directory / SEAL_NAME
    if prediction_path.exists() or seal_path.exists():
        raise SealedArtifactError(
            "Prediction or seal already exists; sealed outputs are write-once"
        )

    timestamp = sealed_at_utc or _utc_now()
    content = canonical_json_bytes(payload) + b"\n"
    digest = sha256_bytes(content)
    seal = {
        "schema_version": 1,
        "filename": PREDICTION_NAME,
        "sha256": digest,
        "sealed_at_utc": timestamp,
        "method_id": payload["method_id"],
        "architecture_source_sha": payload["architecture_source_sha"],
        "input_bundle_sha256": payload["input_bundle_sha256"],
    }
    validate_payload("prediction_seal.schema.json", seal)

    _write_exclusive(prediction_path, content, read_only=True)
    try:
        _write_exclusive(
            seal_path,
            (json.dumps(seal, indent=2, sort_keys=True) + "\n").encode("utf-8"),
            read_only=True,
        )
    except OSError as error:
        raise SealedArtifactError(
            "Prediction bytes were written but the seal record failed"
        ) from error
    return SealedPrediction(prediction_path, payload, digest, timestamp)


def load_verified_prediction(output_directory: Path) -> SealedPrediction:
    """Read a prediction and reject any change since its write-once seal."""
    prediction_path = output_directory / PREDICTION_NAME
    seal_path = output_directory / SEAL_NAME
    try:
        content = prediction_path.read_bytes()
        seal = cast(dict[str, Any], json.loads(seal_path.read_text(encoding="utf-8")))
    except OSError as error:
        raise SealedArtifactError("Prediction or write-once seal is missing") from error
    except json.JSONDecodeError as error:
        raise SealedArtifactError("Prediction seal is not valid JSON") from error
    validate_payload("prediction_seal.schema.json", seal)
    actual_digest = sha256_bytes(content)
    if actual_digest != seal["sha256"]:
        raise SealedArtifactError("Prediction hash does not match its immutable seal")
    try:
        payload = cast(dict[str, Any], json.loads(content))
    except json.JSONDecodeError as error:
        raise SealedArtifactError("Sealed prediction is not valid JSON") from error
    validate_prediction(payload)
    for field in ("method_id", "architecture_source_sha", "input_bundle_sha256"):
        if payload[field] != seal[field]:
            raise SealedArtifactError(f"Prediction and seal disagree on {field}")
    return SealedPrediction(prediction_path, payload, actual_digest, str(seal["sealed_at_utc"]))


def _write_exclusive(path: Path, content: bytes, read_only: bool) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    file_descriptor = os.open(path, flags, 0o444 if read_only else 0o644)
    try:
        with os.fdopen(file_descriptor, "wb") as file_handle:
            file_handle.write(content)
            file_handle.flush()
            os.fsync(file_handle.fileno())
    except OSError:
        path.unlink(missing_ok=True)
        raise
    if read_only:
        path.chmod(0o444)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


__all__ = [
    "PREDICTION_NAME",
    "SEAL_NAME",
    "SealedPrediction",
    "load_verified_prediction",
    "seal_prediction",
]
