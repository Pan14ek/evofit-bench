"""Run a versioned load profile against one already-reset app process."""

import argparse
import json
import os
import subprocess  # nosec B404
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
import yaml

from app.config import get_settings
from scripts.seed_fingerprint import fingerprint

ROOT = Path(__file__).resolve().parents[1]


def snapshot(url: str, output: Path) -> None:
    """Save exact Prometheus exposition text for an interval boundary."""
    response = httpx.get(f"{url.rstrip('/')}/metrics", timeout=10)
    response.raise_for_status()
    output.write_text(response.text, encoding="utf-8")


def run(run_id: str, profile_path: Path, url: str) -> Path:
    """Execute read-only warm-up and a measured load on the same app process."""
    if Path(run_id).name != run_id or run_id in {"", ".", ".."}:
        raise ValueError("run-id must be a single path-safe name")
    profile_path = profile_path.resolve()
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    run_dir = Path("experiments/results") / run_id
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    run_started = datetime.now(UTC).isoformat()
    settings = get_settings()
    if os.environ.get("SEED_ID", settings.seed_id) != settings.seed_id:
        raise RuntimeError("SEED_ID differs from application SEED_ID; refusing inconsistent run")
    child_environment = {**os.environ, "SEED_ID": settings.seed_id}
    workload_copy = run_dir / "workload_profile.yaml"
    workload_copy.write_bytes(profile_path.read_bytes())
    warmup_seconds = float(profile["warmup"]["duration_seconds"])
    warmup_profile = yaml.safe_load(
        (ROOT / "load/profiles/a0-warmup-v1.yaml").read_text(encoding="utf-8")
    )
    if warmup_seconds and not warmup_profile["read_only"]:
        raise RuntimeError("warm-up workload profile must be read-only")
    measurement = profile["measurement"]
    duration = float(measurement["duration_seconds"])
    interval = float(measurement.get("sampling_interval_seconds", 1))
    started_fingerprint = fingerprint()
    if warmup_seconds:
        subprocess.run(  # noqa: S603  # nosec B603
            [
                sys.executable,
                "-m",
                "locust",
                "-f",
                "load/warmup_locustfile.py",
                "--headless",
                "-u",
                str(warmup_profile["users"]),
                "-r",
                str(warmup_profile["spawn_rate_per_second"]),
                "--run-time",
                f"{int(warmup_seconds)}s",
                "--host",
                url,
            ],
            check=True,
            env=child_environment,
        )
        if fingerprint() != started_fingerprint:
            raise RuntimeError("read-only warm-up changed the deterministic dataset")
    (run_dir / "seed_fingerprint_before_warmup.json").write_text(
        json.dumps(started_fingerprint, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (run_dir / "seed_fingerprint_after_warmup.json").write_text(
        json.dumps(fingerprint(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    snapshot(url, run_dir / "metrics_before.txt")
    sampler = subprocess.Popen(  # noqa: S603  # nosec B603
        [
            sys.executable,
            "-m",
            "scripts.sample_runtime_metrics",
            "--url",
            url,
            "--output",
            str(run_dir / "runtime_metrics.csv"),
            "--interval-seconds",
            str(interval),
        ]
    )  # nosec B603 -- invokes the current Python interpreter with a fixed module.
    try:
        time.sleep(min(0.2, interval))
        if sampler.poll() is not None:
            raise RuntimeError("application runtime metrics sampler exited before measured load")
        subprocess.run(  # noqa: S603  # nosec B603
            [
                sys.executable,
                "-m",
                "locust",
                "-f",
                "load/locustfile.py",
                "--headless",
                "-u",
                str(profile["users"]),
                "-r",
                str(profile["spawn_rate_per_second"]),
                "--run-time",
                f"{int(duration)}s",
                "--host",
                url,
                "--csv",
                str(run_dir / "locust"),
            ],
            check=True,
            env=child_environment,
        )
    finally:
        if sampler.poll() is None:
            sampler.terminate()
        sampler.wait(timeout=10)
    snapshot(url, run_dir / "metrics_after.txt")
    stats = run_dir / "locust_stats.csv"
    if not stats.exists():
        raise RuntimeError("Locust did not produce locust_stats.csv")
    subprocess.run(  # noqa: S603  # nosec B603
        [
            sys.executable,
            "-m",
            "scripts.summarize_load",
            "--csv",
            str(stats),
            "--run-id",
            run_id,
            "--profile",
            str(profile["id"]),
        ],
        check=True,
    )
    subprocess.run(  # noqa: S603  # nosec B603
        [sys.executable, "-m", "scripts.finalize_run", "--run-id", run_id],
        check=True,
    )
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    if summary["business_5xx_count"] not in (0, 0.0):
        raise RuntimeError(
            f"measured workload returned {summary['business_5xx_count']} business 5xx responses"
        )
    subprocess.run(  # noqa: S603  # nosec B603
        [
            sys.executable,
            "-m",
            "scripts.collect_run_metadata",
            "--run-id",
            run_id,
            "--workload-profile",
            str(profile_path),
            "--run-started-at-utc",
            run_started,
            "--url",
            url,
            "--warmup-duration-seconds",
            str(warmup_seconds),
            "--measurement-duration-seconds",
            str(duration),
            "--sampling-interval-seconds",
            str(interval),
        ],
        check=True,
    )
    return run_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args()
    print(run(args.run_id, args.profile, args.url))
