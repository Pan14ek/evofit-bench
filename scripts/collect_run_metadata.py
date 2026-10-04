"""Collect source, configuration, seed, and environment provenance."""

import argparse
import hashlib
import json
import platform
import subprocess  # nosec B404
from datetime import UTC, datetime
from pathlib import Path

import httpx
import yaml
from sqlalchemy import text

from app.config import get_settings
from app.db.engine import engine
from scripts.seed_fingerprint import fingerprint

ROOT = Path(__file__).resolve().parents[1]
FITNESS_CONFIG = ROOT / "fitness/configs/a0-monolith.yaml"
WARMUP_PROFILE = ROOT / "load/profiles/a0-warmup-v1.yaml"


def command_output(command: list[str]) -> str | None:
    """Return stdout when a local diagnostic command succeeds."""
    try:
        return subprocess.run(  # noqa: S603  # nosec B603
            command, check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def sha256_file(path: Path) -> str:
    """Return a SHA-256 digest over a file's exact bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect(
    run_id: str,
    workload_profile: Path,
    started_at: str,
    base_url: str,
    warmup_duration_seconds: float,
    measurement_duration_seconds: float,
    sampling_interval_seconds: float,
) -> Path:
    """Write metadata for an already completed run and preserve its source profile."""
    settings = get_settings()
    if Path(run_id).name != run_id or run_id in {"", ".", ".."}:
        raise ValueError("run-id must be a single path-safe name")
    profile = yaml.safe_load(workload_profile.read_text(encoding="utf-8"))
    if profile.get("architecture_state") != "A0_MONOLITH":
        raise ValueError("workload profile must identify A0_MONOLITH")
    valid_profiles = {
        (ROOT / "load/profiles/a0-baseline-v1.yaml").resolve(),
        (ROOT / "load/profiles/a0-smoke-v1.yaml").resolve(),
    }
    if workload_profile.resolve() not in valid_profiles:
        raise ValueError("profile path must be a checked-in A0 workload profile")
    if platform.python_version_tuple()[0] != "3":
        raise RuntimeError("Python runtime is unavailable")
    with engine.connect() as connection:
        database_version = str(connection.scalar(text("SELECT version()")))
    run_dir = Path("experiments/results") / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    initial_seed_file = run_dir / "seed_fingerprint_before_warmup.json"
    seed_state = (
        json.loads(initial_seed_file.read_text(encoding="utf-8"))
        if initial_seed_file.exists()
        else fingerprint()
    )
    fingerprint_path = run_dir / "seed_fingerprint.json"
    fingerprint_path.write_text(
        json.dumps(seed_state, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    fitness = yaml.safe_load(FITNESS_CONFIG.read_text(encoding="utf-8"))
    profile_copy = run_dir / "workload_profile.yaml"
    profile_copy.write_bytes(workload_profile.read_bytes())
    warmup_copy = run_dir / "warmup_profile.yaml"
    warmup_copy.write_bytes(WARMUP_PROFILE.read_bytes())
    warmup = yaml.safe_load(WARMUP_PROFILE.read_text(encoding="utf-8"))
    fault_config = {
        "notification_delay_ms": 0,
        "task_delay_ms": 0,
        "fail_next_n_notifications": 0,
    }
    if settings.experiment_mode:
        response = httpx.get(f"{base_url.rstrip('/')}/internal/experiment/faults", timeout=5)
        response.raise_for_status()
        fault_config = response.json()
    status = command_output(["git", "status", "--porcelain"])
    dirty = status is None or bool(status)
    if dirty:
        print("WARNING: run uses a dirty Git working tree; git_dirty=true in metadata.")
    metadata = {
        "run_id": run_id,
        "run_started_at_utc": started_at,
        "run_completed_at_utc": datetime.now(UTC).isoformat(),
        "architecture_state": "A0_MONOLITH",
        "application_version": settings.app_version,
        "git_commit_sha": command_output(["git", "rev-parse", "HEAD"]),
        "git_dirty": dirty,
        "fitness_configuration_path": "fitness/configs/a0-monolith.yaml",
        "fitness_configuration_version": fitness["configuration_version"],
        "fitness_configuration_sha256": sha256_file(FITNESS_CONFIG),
        "seed_identifier": settings.seed_id,
        "seed_fingerprint_sha256": seed_state["sha256"],
        "workload_profile_id": profile["id"],
        "workload_profile_sha256": sha256_file(workload_profile),
        "warmup_profile_id": warmup["id"],
        "warmup_profile_sha256": sha256_file(WARMUP_PROFILE),
        "python_version": platform.python_version(),
        "os_platform": platform.platform(),
        "cpu_information": platform.processor() or platform.machine(),
        "database_version": database_version,
        "docker_image_id": command_output(
            ["docker", "image", "inspect", "--format", "{{.Id}}", "evofit-bench-app"]
        ),
        "experiment_mode": settings.experiment_mode,
        "experiment_fault_configuration": fault_config,
        "warmup_duration_seconds": warmup_duration_seconds,
        "measurement_duration_seconds": measurement_duration_seconds,
        "runtime_metrics_sampling_interval_seconds": sampling_interval_seconds,
    }
    target = run_dir / "metadata.json"
    target.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--workload-profile", type=Path, required=True)
    parser.add_argument("--run-started-at-utc", required=True)
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--warmup-duration-seconds", type=float, default=0)
    parser.add_argument("--measurement-duration-seconds", type=float, required=True)
    parser.add_argument("--sampling-interval-seconds", type=float, default=1)
    args = parser.parse_args()
    print(
        collect(
            args.run_id,
            args.workload_profile,
            args.run_started_at_utc,
            args.url,
            args.warmup_duration_seconds,
            args.measurement_duration_seconds,
            args.sampling_interval_seconds,
        )
    )
