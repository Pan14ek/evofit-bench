"""Focused tests for PILOT-01 parsing and digest checks."""

import csv
import hashlib
import json
from pathlib import Path

import pytest

from experiments.pilots.generate_pilot01_results import (
    NUMERIC_FIELDS,
    cross_check_runtime_measurements,
    descriptive_statistics,
    sha256_file,
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


def _write_raw_measurements(run_dir: Path) -> dict[str, int | float]:
    run_dir.mkdir(parents=True)
    with (run_dir / "locust_stats.csv").open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "Name",
                "Request Count",
                "Failure Count",
                "Requests/s",
                "50%",
                "95%",
                "99%",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "Name": "Aggregated",
                "Request Count": 10,
                "Failure Count": 1,
                "Requests/s": 5.5,
                "50%": 2,
                "95%": 6,
                "99%": 9,
            }
        )
    with (run_dir / "runtime_metrics.csv").open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=["process_cpu_seconds_total", "process_resident_memory_bytes"],
        )
        writer.writeheader()
        writer.writerows(
            [
                {"process_cpu_seconds_total": "1.25", "process_resident_memory_bytes": "100.0"},
                {"process_cpu_seconds_total": "1.50", "process_resident_memory_bytes": "150.0"},
                {"process_cpu_seconds_total": "1.75", "process_resident_memory_bytes": "125.0"},
            ]
        )
    return {
        "request_count": 10,
        "failure_count": 1,
        "p50_ms": 2.0,
        "p95_ms": 6.0,
        "p99_ms": 9.0,
        "throughput_requests_per_second": 5.5,
        "application_cpu_seconds_delta": 0.5,
        "application_rss_max_bytes": 150,
        "sample_count": 3,
    }


@pytest.mark.parametrize(
    ("field", "altered_value"),
    [
        ("request_count", 11),
        ("failure_count", 2),
        ("p50_ms", 3.0),
        ("p95_ms", 7.0),
        ("p99_ms", 10.0),
        ("throughput_requests_per_second", 5.5001),
        ("application_cpu_seconds_delta", 0.6),
        ("application_rss_max_bytes", 151),
        ("sample_count", 2),
    ],
)
def test_runtime_manifest_mismatch_fails_even_with_valid_artifact_digests(
    tmp_path: Path, field: str, altered_value: int | float
) -> None:
    """Valid updated hashes do not make manifest-only metric edits trustworthy."""
    run_dir = tmp_path / "pilot01-s0-r01"
    runtime = _write_raw_measurements(run_dir)
    runtime[field] = altered_value
    references = [
        {
            "path": path.relative_to(tmp_path).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted(run_dir.glob("*.csv"))
    ]
    manifest_path = run_dir / "run_manifest.json"
    manifest_path.write_text(
        json.dumps({"runtime": runtime, "artifact_references": references}),
        encoding="utf-8",
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    verify_artifact_inventory(tmp_path, manifest["artifact_references"])
    with pytest.raises(ValueError, match=field):
        cross_check_runtime_measurements(run_dir, manifest["runtime"])


def test_runtime_manifest_accepts_only_documented_float_tolerance(tmp_path: Path) -> None:
    """Raw float fields allow only their documented serialization tolerances."""
    run_dir = tmp_path / "pilot01-s0-r01"
    runtime = _write_raw_measurements(run_dir)
    runtime["throughput_requests_per_second"] = 5.5000000000005
    runtime["application_cpu_seconds_delta"] = 0.5000000005

    measured = cross_check_runtime_measurements(run_dir, runtime)

    assert measured["throughput_requests_per_second"] == 5.5
    assert measured["application_cpu_seconds_delta"] == 0.5
