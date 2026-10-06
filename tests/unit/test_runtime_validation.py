"""Regression checks for workload authority and sampler evidence validation."""

import csv
import importlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from load.workload_profile import load_profile, request_mix_environment
from scripts.runtime_validation import (
    stop_sampler,
    validate_process_continuity,
    validate_runtime_samples,
)


def test_profile_weights_drive_effective_locust_task_schedule(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Changing profile weights changes the task weights used by BaselineUser."""
    profile = load_profile(Path("load/profiles/a0-baseline-v1.yaml"))
    profile["request_mix"] = {
        "get_task": 1,
        "list_tasks": 2,
        "create_task": 3,
        "assign_task": 4,
        "change_status": 5,
        "task_summary": 6,
    }
    monkeypatch.setenv("A0_REQUEST_MIX_JSON", request_mix_environment(profile["request_mix"]))
    module = importlib.import_module("load.locustfile")
    module = importlib.reload(module)
    scheduled: list[Any] = module.BaselineUser.tasks
    effective = {
        name: sum(1 for task in scheduled if task.__name__ == name)
        for name in profile["request_mix"]
    }
    assert effective == profile["request_mix"]


@pytest.mark.parametrize(
    ("weights", "message"),
    [
        (
            {
                "get_task": 1,
                "list_tasks": 1,
                "create_task": 1,
                "assign_task": 1,
                "change_status": 1,
                "task_summary": 1,
                "unknown": 1,
            },
            "unknown workload",
        ),
        (
            {
                "get_task": 0,
                "list_tasks": 0,
                "create_task": 0,
                "assign_task": 0,
                "change_status": 0,
                "task_summary": 0,
            },
            "at least one",
        ),
        (
            {
                "get_task": -1,
                "list_tasks": 1,
                "create_task": 1,
                "assign_task": 1,
                "change_status": 1,
                "task_summary": 1,
            },
            "non-negative integer",
        ),
        (
            {
                "get_task": 1,
                "list_tasks": 1,
                "create_task": 1,
                "assign_task": 1,
                "change_status": 1,
            },
            "missing workload operations",
        ),
    ],
)
def test_invalid_workload_mix_is_rejected(weights: dict[str, int], message: str) -> None:
    """Unknown operations, zero-only mixes, and negative weights fail validation."""
    from load.workload_profile import validate_request_mix

    with pytest.raises(ValueError, match=message):
        validate_request_mix(weights)


class _Sampler:
    def __init__(self, return_code: int) -> None:
        self.return_code = return_code
        self.terminated = False

    def poll(self) -> int | None:
        return self.return_code if self.terminated else None

    def terminate(self) -> None:
        self.terminated = True

    def wait(self, timeout: float | None = None) -> int:
        return self.return_code


def test_nonzero_sampler_exit_fails_experiment() -> None:
    """Sampler failures are not accepted as complete experiment evidence."""
    with pytest.raises(RuntimeError, match="sampler exited with code 2"):
        stop_sampler(_Sampler(2))


def _write_samples(path: Path, cpu_values: list[float]) -> None:
    start = datetime(2026, 10, 5, tzinfo=UTC)
    with path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(
            target,
            fieldnames=[
                "timestamp_utc",
                "process_cpu_seconds_total",
                "process_resident_memory_bytes",
                "process_virtual_memory_bytes",
            ],
        )
        writer.writeheader()
        for index, cpu in enumerate(cpu_values):
            writer.writerow(
                {
                    "timestamp_utc": (start + timedelta(seconds=index)).isoformat(),
                    "process_cpu_seconds_total": cpu,
                    "process_resident_memory_bytes": 1000 + index,
                    "process_virtual_memory_bytes": "",
                }
            )


def test_insufficient_runtime_sample_count_fails(tmp_path: Path) -> None:
    """Measurements below the explicit 90 percent floor are invalid."""
    path = tmp_path / "runtime_metrics.csv"
    _write_samples(path, [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
    with pytest.raises(RuntimeError, match="minimum is 9"):
        validate_runtime_samples(path, duration_seconds=10, interval_seconds=1)


def test_cpu_counter_decrease_fails(tmp_path: Path) -> None:
    """A process CPU counter decrease indicates broken measurement continuity."""
    path = tmp_path / "runtime_metrics.csv"
    _write_samples(path, [1.0, 2.0, 1.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0])
    with pytest.raises(RuntimeError, match="CPU counter decreased"):
        validate_runtime_samples(path, duration_seconds=10, interval_seconds=1)


def test_process_start_time_change_fails() -> None:
    """A changed Prometheus process start time invalidates the measured interval."""
    before = "process_start_time_seconds 100\n"
    after = "process_start_time_seconds 101\n"
    with pytest.raises(RuntimeError, match="process changed"):
        validate_process_continuity(before, after)


def test_process_start_time_match_passes() -> None:
    """Matching process start-time evidence confirms boundary continuity."""
    text = "process_start_time_seconds 100\n"
    assert validate_process_continuity(text, text) == 100
