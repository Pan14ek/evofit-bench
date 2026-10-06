"""Fail-closed checks for application process continuity and runtime samples."""

import csv
import math
from datetime import datetime
from pathlib import Path
from typing import Protocol

from scripts.prometheus_snapshot import parse_snapshot, value

MINIMUM_SAMPLE_FRACTION = 0.90


class SamplerProcess(Protocol):
    """Small subprocess interface used by sampler shutdown validation."""

    def poll(self) -> int | None: ...

    def terminate(self) -> None: ...

    def wait(self, timeout: float | None = None) -> int: ...


def stop_sampler(sampler: SamplerProcess) -> int:
    """Request shutdown and fail when the runtime sampler exits unsuccessfully."""
    if sampler.poll() is None:
        sampler.terminate()
    return_code = sampler.wait(timeout=10)
    if return_code != 0:
        raise RuntimeError(f"runtime metrics sampler exited with code {return_code}")
    return return_code


def validate_process_continuity(before_text: str, after_text: str) -> float:
    """Require one stable process-start timestamp across measured boundaries."""
    before = value(parse_snapshot(before_text), "process_start_time_seconds")
    after = value(parse_snapshot(after_text), "process_start_time_seconds")
    if before is None or after is None:
        raise RuntimeError("process_start_time_seconds missing from a metrics snapshot")
    if before != after:
        raise RuntimeError("application process changed during measured interval")
    return before


def validate_runtime_samples(
    path: Path, duration_seconds: float, interval_seconds: float
) -> dict[str, int]:
    """Validate runtime sampler completeness and continuous metric values."""
    if duration_seconds <= 0 or interval_seconds <= 0:
        raise ValueError("measurement duration and sampling interval must be positive")
    with path.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    expected = duration_seconds / interval_seconds
    minimum = math.ceil(expected * MINIMUM_SAMPLE_FRACTION)
    if len(rows) < minimum:
        raise RuntimeError(f"runtime sampler collected {len(rows)} rows; minimum is {minimum}")
    previous_timestamp: datetime | None = None
    previous_cpu: float | None = None
    rss_values: list[int] = []
    for index, row in enumerate(rows, start=1):
        try:
            timestamp = datetime.fromisoformat(row["timestamp_utc"])
            cpu = float(row["process_cpu_seconds_total"])
            rss_value = float(row["process_resident_memory_bytes"])
            rss = int(rss_value)
        except (KeyError, TypeError, ValueError) as error:
            raise RuntimeError(f"runtime sample row {index} is incomplete or invalid") from error
        if timestamp.tzinfo is None:
            raise RuntimeError(f"runtime sample row {index} timestamp must include a timezone")
        if previous_timestamp is not None and timestamp <= previous_timestamp:
            raise RuntimeError("runtime sample timestamps must be strictly increasing")
        if not math.isfinite(cpu) or cpu < 0:
            raise RuntimeError(f"runtime sample row {index} CPU counter must be non-negative")
        if previous_cpu is not None and cpu < previous_cpu:
            raise RuntimeError("runtime sample CPU counter decreased")
        if not math.isfinite(rss_value) or rss_value <= 0 or rss_value != rss:
            raise RuntimeError(f"runtime sample row {index} RSS must be positive")
        previous_timestamp = timestamp
        previous_cpu = cpu
        rss_values.append(rss)
    return {"sample_count": len(rows), "rss_max_bytes": max(rss_values)}
