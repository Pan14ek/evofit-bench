"""Focused tests for PILOT-01 parsing and digest checks."""

import hashlib
from pathlib import Path

import pytest

from experiments.pilots.generate_pilot01_results import (
    NUMERIC_FIELDS,
    descriptive_statistics,
    verify_artifact_inventory,
)
from experiments.pilots.run_pilot01_measurement import _locust_aggregate


def test_locust_aggregate_reads_saved_statistics(tmp_path: Path) -> None:
    """The pilot reads actual Locust aggregate fields without re-estimating percentiles."""
    source = tmp_path / "locust_stats.csv"
    source.write_text(
        "Name,Request Count,Failure Count,Requests/s,50%,95%,99%\nAggregated,900,0,30,3,9,14\n",
        encoding="utf-8",
    )

    assert _locust_aggregate(source) == {
        "request_count": 900,
        "failure_count": 0,
        "p50_ms": 3.0,
        "p95_ms": 9.0,
        "p99_ms": 14.0,
        "throughput_requests_per_second": 30.0,
    }


def test_artifact_inventory_rejects_changed_bytes(tmp_path: Path) -> None:
    """Evidence inventory verification rejects a post-collection byte change."""
    artifact = tmp_path / "bundle.json"
    artifact.write_text('{"status":"complete"}\n', encoding="utf-8")
    reference = {
        "path": "bundle.json",
        "size_bytes": artifact.stat().st_size,
        "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
    }

    verify_artifact_inventory(tmp_path, [reference])
    artifact.write_text('{"status":"changed"}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="size mismatch|digest mismatch"):
        verify_artifact_inventory(tmp_path, [reference])


def test_statistics_label_repetitions_as_non_inferential() -> None:
    """Repeated technical runs produce only descriptive min/mean/max values."""
    rows = []
    for condition, values in (("S0", (2.0, 4.0, 6.0)), ("S1", (3.0, 6.0, 9.0))):
        for value in values:
            rows.append(
                {
                    "condition": condition,
                    **{field: value for field in NUMERIC_FIELDS},
                }
            )

    result = descriptive_statistics(rows)

    assert result["independent_architecture_change_count"] == 1
    assert result["inferential_statistics"] == "not_applicable"
    assert result["conditions"]["S0"]["metrics"]["p95_ms"] == {
        "n": 3,
        "min": 2.0,
        "mean": 4.0,
        "max": 6.0,
    }
