"""Summarize a Locust aggregate CSV row into a compact run summary."""

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def summarize(csv_path: Path, run_id: str, profile: str) -> Path:
    """Write request count, failure rate, percentiles, and throughput to summary.json."""
    if Path(run_id).name != run_id or run_id in {"", ".", ".."}:
        raise ValueError("run-id must be a single path-safe name")
    with csv_path.open(newline="", encoding="utf-8") as input_file:
        rows = list(csv.DictReader(input_file))
    aggregate = next((row for row in rows if row.get("Name") == "Aggregated"), None)
    if aggregate is None:
        raise ValueError(f"No Aggregated row found in {csv_path}")

    def numeric(name: str) -> float:
        value = aggregate.get(name, "")
        return float(value) if value else 0.0

    request_count = int(numeric("Request Count"))
    failures = int(numeric("Failure Count"))
    summary: dict[str, Any] = {
        "architecture_state": "A0_MONOLITH",
        "load_profile": profile,
        "request_count": request_count,
        "failure_count": failures,
        "failure_rate": failures / request_count if request_count else 0.0,
        "p50_ms": numeric("50%"),
        "p95_ms": numeric("95%"),
        "p99_ms": numeric("99%"),
        "throughput_requests_per_second": numeric("Requests/s"),
    }
    run_dir = Path("experiments/results") / run_id
    target = run_dir / "summary.json"
    target.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--profile", required=True)
    options = parser.parse_args()
    print(summarize(options.csv, options.run_id, options.profile))
