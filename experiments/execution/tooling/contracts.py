"""Load and validate DA01 execution JSON Schemas and payload invariants."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]

from experiments.execution.tooling.errors import ContractValidationError

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schemas"
LEGACY_RESULT_SCHEMA = Path(__file__).resolve().parents[2] / "schemas" / "result.schema.json"


def load_schema(schema_name: str) -> dict[str, Any]:
    """Load a versioned schema and validate its own structure."""
    path = SCHEMA_DIR / schema_name
    if path.parent != SCHEMA_DIR or not path.is_file():
        raise ContractValidationError(f"Unknown execution schema: {schema_name}")
    schema = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    Draft202012Validator.check_schema(schema)
    return schema


def validate_payload(schema_name: str, payload: dict[str, Any]) -> None:
    """Raise a readable contract error when a JSON payload is invalid."""
    validator = Draft202012Validator(load_schema(schema_name), format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.absolute_path))
    if errors:
        details = "; ".join(
            f"/{'/'.join(str(part) for part in error.absolute_path)}: {error.message}"
            for error in errors
        )
        raise ContractValidationError(f"{schema_name} validation failed: {details}")


def validate_prediction(payload: dict[str, Any]) -> None:
    """Validate prediction shape and reject duplicate or contradictory target decisions."""
    validate_payload("prediction.schema.json", payload)
    affected = _target_operation_map(
        cast(list[dict[str, Any]], payload["predicted_affected"]), "predicted_operation"
    )
    proposed = _target_operation_map(
        cast(list[dict[str, Any]], payload["proposed_operations"]), "operation"
    )
    if any(operation == "retain" for operation in affected.values()):
        raise ContractValidationError("predicted_affected must contain only non-retain decisions")
    for target, operation in affected.items():
        if proposed.get(target) != operation:
            raise ContractValidationError(
                f"predicted_affected decision for {target[0]}:{target[1]} "
                "does not match proposed_operations"
            )
    for target, operation in proposed.items():
        if operation != "retain" and target not in affected:
            raise ContractValidationError(
                f"non-retain operation for {target[0]}:{target[1]} is missing from "
                "predicted_affected"
            )


def validate_candidate(payload: dict[str, Any]) -> None:
    """Validate a candidate configuration and enforce unique representation IDs."""
    validate_payload("candidate_configuration.schema.json", payload)
    identifiers = [str(item["id"]) for item in payload["representations"]]
    if len(identifiers) != len(set(identifiers)):
        raise ContractValidationError(
            "candidate configuration contains duplicate representation IDs"
        )


def validate_legacy_result(payload: dict[str, Any]) -> None:
    """Validate a compatibility projection against the unchanged result schema."""
    schema = cast(dict[str, Any], json.loads(LEGACY_RESULT_SCHEMA.read_text(encoding="utf-8")))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.absolute_path))
    if errors:
        details = "; ".join(error.message for error in errors)
        raise ContractValidationError(f"legacy result compatibility validation failed: {details}")


def _target_operation_map(
    decisions: list[dict[str, Any]], operation_key: str
) -> dict[tuple[str, str], str]:
    result: dict[tuple[str, str], str] = {}
    for decision in decisions:
        target = (str(decision["target_type"]), str(decision["target_id"]))
        if target in result:
            raise ContractValidationError(
                f"duplicate decision for {target[0]}:{target[1]} is contradictory or redundant"
            )
        result[target] = str(decision[operation_key])
    return result


__all__ = [
    "LEGACY_RESULT_SCHEMA",
    "SCHEMA_DIR",
    "load_schema",
    "validate_candidate",
    "validate_legacy_result",
    "validate_payload",
    "validate_prediction",
]
