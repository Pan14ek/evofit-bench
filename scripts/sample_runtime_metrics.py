"""Sample CPU and memory from the running application Prometheus endpoint."""

import argparse
import csv
import signal
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

from scripts.prometheus_snapshot import parse_snapshot, value

FIELDS = [
    "timestamp_utc",
    "process_cpu_seconds_total",
    "process_resident_memory_bytes",
    "process_virtual_memory_bytes",
]
_stop_requested = False


def _request_stop(_signal: int, _frame: object) -> None:
    global _stop_requested
    _stop_requested = True


def sample(base_url: str, output: Path, interval: float, duration: float | None) -> Path:
    """Write target-process samples until duration expires or SIGTERM arrives."""
    if interval <= 0 or (duration is not None and duration <= 0):
        raise ValueError("sampling interval and duration must be positive")
    output.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + duration if duration is not None else None
    old_handler = signal.signal(signal.SIGTERM, _request_stop)
    try:
        with output.open("w", newline="", encoding="utf-8") as target:
            writer = csv.DictWriter(target, fieldnames=FIELDS)
            writer.writeheader()
            with httpx.Client(timeout=5) as client:
                while not _stop_requested and (deadline is None or time.monotonic() < deadline):
                    response = client.get(f"{base_url.rstrip('/')}/metrics")
                    response.raise_for_status()
                    snapshot = parse_snapshot(response.text)
                    row = {field: value(snapshot, field) for field in FIELDS[1:]}
                    if (
                        row["process_cpu_seconds_total"] is None
                        or row["process_resident_memory_bytes"] is None
                    ):
                        raise RuntimeError(
                            "/metrics is missing required application process metrics"
                        )
                    writer.writerow({"timestamp_utc": datetime.now(UTC).isoformat(), **row})
                    target.flush()
                    if deadline is None:
                        time.sleep(interval)
                    else:
                        time.sleep(min(interval, max(0.0, deadline - time.monotonic())))
    finally:
        signal.signal(signal.SIGTERM, old_handler)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--interval-seconds", type=float, default=1.0)
    parser.add_argument("--duration-seconds", type=float)
    args = parser.parse_args()
    print(sample(args.url, args.output, args.interval_seconds, args.duration_seconds))
