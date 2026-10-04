"""Collect reproducibility metadata for one controlled load run."""

import argparse
import json
import platform
import resource
import subprocess  # nosec B404
from datetime import UTC, datetime
from pathlib import Path

import httpx
from sqlalchemy import text

from app.config import get_settings
from app.db.engine import engine


def command_output(command: list[str]) -> str | None:
    """Return a command's stdout when the command is available and succeeds."""
    try:
        return subprocess.run(  # noqa: S603  # nosec B603
            command, check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def collect(
    run_id: str,
    load_profile: str,
    run_duration_seconds: float | None,
    base_url: str,
) -> Path:
    """Write run metadata under experiments/results/<run-id>."""
    settings = get_settings()
    if Path(run_id).name != run_id or run_id in {"", ".", ".."}:
        raise ValueError("run-id must be a single path-safe name")
    try:
        with engine.connect() as connection:
            database_version = str(connection.scalar(text("SELECT version()")))
    except Exception:
        database_version = "unavailable"
    usage = resource.getrusage(resource.RUSAGE_SELF)
    process_cpu_seconds = usage.ru_utime + usage.ru_stime
    max_rss = int(usage.ru_maxrss)
    # macOS reports ru_maxrss in bytes; Linux reports KiB.
    max_rss_bytes = max_rss if platform.system() == "Darwin" else max_rss * 1024
    run_dir = Path("experiments/results") / run_id
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    fault_config = {
        "notification_delay_ms": 0,
        "task_delay_ms": 0,
        "fail_next_n_notifications": 0,
    }
    if settings.experiment_mode:
        fault_response = httpx.get(f"{base_url.rstrip('/')}/internal/experiment/faults", timeout=5)
        fault_response.raise_for_status()
        fault_config = fault_response.json()
    metadata = {
        "run_id": run_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "git_commit_sha": command_output(["git", "rev-parse", "HEAD"]),
        "architecture_state": "A0_MONOLITH",
        "fitness_configuration_version": 1,
        "python_version": platform.python_version(),
        "application_version": settings.app_version,
        "docker_image_id": command_output(
            ["docker", "image", "inspect", "--format", "{{.Id}}", "evofit-bench-app"]
        ),
        "os_platform": platform.platform(),
        "cpu_information": platform.processor() or platform.machine(),
        "process_cpu_time_seconds": process_cpu_seconds,
        "process_max_rss_bytes": max_rss_bytes,
        "database_version": database_version,
        "load_profile": load_profile,
        "run_duration_seconds": run_duration_seconds,
        "seed_identifier": settings.seed_id,
        "experiment_mode": settings.experiment_mode,
        "experiment_fault_configuration": fault_config,
    }
    target = run_dir / "metadata.json"
    target.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--load-profile", default="smoke")
    parser.add_argument("--run-duration-seconds", type=float)
    parser.add_argument("--url", default="http://localhost:8000")
    arguments = parser.parse_args()
    print(
        collect(
            arguments.run_id,
            arguments.load_profile,
            arguments.run_duration_seconds,
            arguments.url,
        )
    )
