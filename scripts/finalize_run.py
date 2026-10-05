"""Combine measured Locust, HTTP, and application process samples."""

import argparse
import csv
import json
from pathlib import Path

from scripts.prometheus_snapshot import aggregate, delta, parse_snapshot, value
from scripts.runtime_validation import validate_process_continuity


def finalize(run_id: str) -> Path:
    """Add measured-interval counters and sampled app process resources."""
    run_dir = Path("experiments/results") / run_id
    summary_path = run_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    before = parse_snapshot((run_dir / "metrics_before.txt").read_text(encoding="utf-8"))
    after = parse_snapshot((run_dir / "metrics_after.txt").read_text(encoding="utf-8"))
    process_start_time = validate_process_continuity(
        (run_dir / "metrics_before.txt").read_text(encoding="utf-8"),
        (run_dir / "metrics_after.txt").read_text(encoding="utf-8"),
    )
    before_requests = aggregate(before, "http_requests_total", {"traffic_class": "business"})
    after_requests = aggregate(after, "http_requests_total", {"traffic_class": "business"})
    before_5xx = aggregate(
        before, "http_responses_total", {"traffic_class": "business", "status_class": "5xx"}
    )
    after_5xx = aggregate(
        after, "http_responses_total", {"traffic_class": "business", "status_class": "5xx"}
    )
    if "http_requests_total" in before and before_requests is None:
        before_requests = 0.0
    if "http_requests_total" in after and after_requests is None:
        after_requests = 0.0
    if "http_responses_total" in before and before_5xx is None:
        before_5xx = 0.0
    if "http_responses_total" in after and after_5xx is None:
        after_5xx = 0.0
    business_count = delta(after_requests, before_requests)
    business_5xx = delta(after_5xx, before_5xx)
    summary["business_5xx_count"] = business_5xx
    summary["business_5xx_rate"] = (
        business_5xx / business_count if business_5xx is not None and business_count else None
    )
    cpu_after = value(after, "process_cpu_seconds_total")
    cpu_before = value(before, "process_cpu_seconds_total")
    if cpu_after is None or cpu_before is None or cpu_after < cpu_before:
        raise RuntimeError("application process CPU counter is missing or decreased")
    cpu_delta = cpu_after - cpu_before
    summary["application_cpu_seconds_delta"] = cpu_delta
    summary["application_process_start_time_seconds"] = process_start_time
    if cpu_delta is None:
        summary["application_cpu_seconds_delta_reason"] = (
            "process CPU counter missing from a metrics snapshot"
        )
    samples: list[dict[str, str]] = []
    with (run_dir / "runtime_metrics.csv").open(newline="", encoding="utf-8") as runtime_file:
        samples = list(csv.DictReader(runtime_file))
    resident = [
        int(float(row["process_resident_memory_bytes"]))
        for row in samples
        if row.get("process_resident_memory_bytes")
    ]
    virtual = [
        int(float(row["process_virtual_memory_bytes"]))
        for row in samples
        if row.get("process_virtual_memory_bytes")
    ]
    summary["application_resident_memory_start_bytes"] = resident[0] if resident else None
    summary["application_resident_memory_end_bytes"] = resident[-1] if resident else None
    summary["application_resident_memory_max_bytes"] = max(resident) if resident else None
    summary["application_virtual_memory_max_bytes"] = max(virtual) if virtual else None
    if not resident:
        summary["application_resident_memory_reason"] = "no resident-memory samples were collected"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    print(finalize(args.run_id))
