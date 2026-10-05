"""Validation and Locust task construction for versioned workload profiles."""

import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import yaml

SUPPORTED_OPERATIONS = (
    "get_task",
    "list_tasks",
    "create_task",
    "assign_task",
    "change_status",
    "task_summary",
)
READ_ONLY_OPERATIONS = ("get_task", "list_tasks", "task_summary")


def validate_request_mix(
    request_mix: object, *, required_operations: tuple[str, ...] = SUPPORTED_OPERATIONS
) -> dict[str, int]:
    """Validate profile operation identifiers and integer weights."""
    if not isinstance(request_mix, dict):
        raise ValueError("request_mix must be a mapping")
    unknown = set(request_mix) - set(SUPPORTED_OPERATIONS)
    missing = set(required_operations) - set(request_mix)
    disallowed = set(request_mix) - set(required_operations)
    if unknown:
        raise ValueError(f"unknown workload operations: {sorted(unknown)}")
    if missing:
        raise ValueError(f"missing workload operations: {sorted(missing)}")
    if disallowed:
        raise ValueError(f"operations are not allowed in this profile: {sorted(disallowed)}")
    weights: dict[str, int] = {}
    for operation, weight in request_mix.items():
        if not isinstance(weight, int) or isinstance(weight, bool) or weight < 0:
            raise ValueError(f"workload weight for {operation} must be a non-negative integer")
        weights[operation] = weight
    if not any(weights.values()):
        raise ValueError("at least one workload weight must be greater than zero")
    return weights


def load_profile(path: Path, *, read_only: bool = False) -> dict[str, Any]:
    """Load and validate a versioned workload profile before invoking Locust."""
    profile = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(profile, dict):
        raise ValueError("workload profile must be a mapping")
    required = READ_ONLY_OPERATIONS if read_only else SUPPORTED_OPERATIONS
    profile["request_mix"] = validate_request_mix(
        profile.get("request_mix"), required_operations=required
    )
    return profile


def task_schedule(
    operations: Mapping[str, Callable[..., object]], weights: Mapping[str, int]
) -> list[Callable[..., object]]:
    """Expand effective weights into Locust's weighted callable task schedule."""
    return [operations[name] for name, weight in weights.items() for _ in range(weight)]


def request_mix_environment(weights: Mapping[str, int]) -> str:
    """Serialize already validated effective weights for a Locust subprocess."""
    return json.dumps(weights, sort_keys=True)


def weights_from_environment(
    raw: str | None, *, required_operations: tuple[str, ...] = SUPPORTED_OPERATIONS
) -> dict[str, int]:
    """Load the run-specific profile weights supplied to a Locust process."""
    if raw is None:
        raise RuntimeError("A0_REQUEST_MIX_JSON must be set from a validated workload profile")
    try:
        return validate_request_mix(json.loads(raw), required_operations=required_operations)
    except (json.JSONDecodeError, ValueError) as error:
        raise RuntimeError(f"invalid A0_REQUEST_MIX_JSON: {error}") from error
