"""Run one reproducible PILOT-01 A0.1 evaluator and runtime measurement."""

import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import shutil
import subprocess  # nosec B404
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import psutil
import yaml

from load.workload_profile import validate_request_mix
from scripts.exp01_evidence_contract import BUNDLE_FILENAME, validate_bundle
from scripts.exp02_fitness_evidence import validate_representation_evidence
from scripts.runtime_validation import validate_process_continuity, validate_runtime_samples

ROOT = Path(__file__).resolve().parents[2]
BASE_SHA = "5d285a04da00863088f8cd88a10afb3faaf02ddb"
S1_SHA = "ccbfb002e1fc71d9dcaadf11635d449b8a881cac"
FITNESS_CONFIG = "fitness/configs/a0_1-capability-modules.dev.yaml"
IMPORT_CONFIG = "architecture/acceptance/importlinter.toml"
MANIFEST = "architecture/states/A0_1_CAPABILITY_MODULES.yaml"
PROFILE = ROOT / "experiments/pilots/PILOT_01_WORKLOAD.yaml"
BASE_URL = "http://localhost:8000"
RUN_ID_PATTERN = re.compile(r"pilot01-s[01]-r[0-9]{2}")
FAULT_DESCRIPTION = (
    "app.modules.notifications.repository imports app.modules.notifications.api.router"
)


def sha256_bytes(content: bytes) -> str:
    """Return the SHA-256 digest of exact file bytes."""
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    """Hash a regular file without following symlinks."""
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"expected a regular artifact file: {path}")
    return sha256_bytes(path.read_bytes())


def git_output(checkout: Path, *arguments: str) -> str:
    """Run a bounded read-only Git query in the selected source worktree."""
    git_executable = shutil.which("git")
    if git_executable is None:
        raise RuntimeError("git executable is unavailable")
    result = subprocess.run(  # noqa: S603  # nosec B603 -- fixed read-only Git argv
        [git_executable, *arguments],
        cwd=checkout,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip()


def verify_source(checkout: Path, condition: str) -> tuple[str, bytes]:
    """Require the exact clean S0 or isolated S1 source revision."""
    source_revision = git_output(checkout, "rev-parse", "HEAD")
    expected_revision = BASE_SHA if condition == "S0" else S1_SHA
    if source_revision != expected_revision:
        raise ValueError(f"{condition} source revision must be {expected_revision}")
    if git_output(checkout, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError(f"{condition} source worktree must be clean before measurement")

    changed_paths = git_output(checkout, "diff", "--name-only", BASE_SHA, source_revision)
    if condition == "S0" and changed_paths:
        raise ValueError("S0 must have no source changes from the frozen A0.1 base")
    if condition == "S1" and changed_paths.splitlines() != [
        "app/modules/notifications/repository.py"
    ]:
        raise ValueError("S1 must contain only the predeclared notification source injection")
    git_executable = shutil.which("git")
    if git_executable is None:
        raise RuntimeError("git executable is unavailable")
    source_diff = subprocess.run(  # noqa: S603  # nosec B603 -- fixed Git diff argv
        [git_executable, "diff", "--binary", BASE_SHA, source_revision, "--", "app"],
        cwd=checkout,
        check=True,
        capture_output=True,
        timeout=10,
    ).stdout
    if condition == "S1" and b"app.modules.notifications.api" not in source_diff:
        raise ValueError("S1 source diff does not contain the predeclared forbidden edge")
    return source_revision, source_diff


def run_command(
    label: str,
    command: list[str],
    *,
    checkout: Path,
    raw_dir: Path,
    environment: dict[str, str],
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    """Run one command, preserving exact stdout, stderr, argv, duration, and exit code."""
    started = time.monotonic()
    result = subprocess.run(  # noqa: S603  # nosec B603 -- fixed pilot command vectors, no shell
        command,
        cwd=checkout,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    duration = time.monotonic() - started
    (raw_dir / f"{label}.stdout.txt").write_text(result.stdout, encoding="utf-8")
    (raw_dir / f"{label}.stderr.txt").write_text(result.stderr, encoding="utf-8")
    return {
        "argv": command,
        "exit_code": result.returncode,
        "duration_seconds": duration,
        "stdout_path": f"raw/{label}.stdout.txt",
        "stderr_path": f"raw/{label}.stderr.txt",
    }


def http_snapshot(url: str, output_path: Path) -> str:
    """Save exact Prometheus exposition text from the local application."""
    response = httpx.get(f"{url.rstrip('/')}/metrics", timeout=10)
    response.raise_for_status()
    output_path.write_text(response.text, encoding="utf-8")
    return response.text


def distribution_version(name: str) -> str | None:
    """Return an installed package version when its distribution metadata exists."""
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def docker_value(
    command: list[str], *, checkout: Path, environment: dict[str, str], timeout: int = 30
) -> str | None:
    """Return a successful Docker diagnostic without hiding its unavailable state."""
    try:
        result = subprocess.run(  # noqa: S603  # nosec B603 -- fixed Docker diagnostics, no shell
            command,
            cwd=checkout,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip()


def _locust_aggregate(path: Path) -> dict[str, float | int]:
    """Read actual aggregate statistics emitted by Locust."""
    with path.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    row = next((item for item in rows if item.get("Name") == "Aggregated"), None)
    if row is None:
        raise ValueError("Locust output is missing its Aggregated statistics row")

    def number(field: str) -> float:
        value = row.get(field, "")
        return float(value) if value else 0.0

    return {
        "request_count": int(number("Request Count")),
        "failure_count": int(number("Failure Count")),
        "p50_ms": number("50%"),
        "p95_ms": number("95%"),
        "p99_ms": number("99%"),
        "throughput_requests_per_second": number("Requests/s"),
    }


def _artifact_inventory(checkout: Path, directories: list[Path]) -> list[dict[str, Any]]:
    """List exact local artifact paths and SHA-256 digests, excluding run manifests."""
    references: list[dict[str, Any]] = []
    for directory in directories:
        for path in sorted(directory.rglob("*")):
            if not path.is_file() or path.name == "run_manifest.json":
                continue
            references.append(
                {
                    "path": path.relative_to(checkout).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return references


def run_measurement(checkout: Path, condition: str, repetition: int) -> dict[str, Any]:
    """Execute one condition using the existing collectors and A0.1 workload tools."""
    checkout = checkout.resolve(strict=True)
    if condition not in {"S0", "S1"} or repetition < 1 or repetition > 99:
        raise ValueError("condition must be S0/S1 and repetition must be from 1 to 99")
    run_id = f"pilot01-{condition.lower()}-r{repetition:02d}"
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError("generated run ID is not path-safe")
    source_revision, source_diff = verify_source(checkout, condition)

    profile_bytes = PROFILE.read_bytes()
    profile = yaml.safe_load(profile_bytes)
    if (
        not isinstance(profile, dict)
        or profile.get("architecture_state") != "A0_1_CAPABILITY_MODULES"
    ):
        raise ValueError("PILOT-01 workload profile must target A0.1")
    weights = validate_request_mix(profile.get("request_mix"))
    measurement = profile.get("measurement", {})
    users = profile.get("users")
    spawn_rate = profile.get("spawn_rate_per_second")
    duration_seconds = measurement.get("duration_seconds")
    interval_seconds = measurement.get("sampling_interval_seconds", 1)
    if (
        not isinstance(users, int)
        or not isinstance(spawn_rate, (int, float))
        or not isinstance(duration_seconds, (int, float))
        or not isinstance(interval_seconds, (int, float))
        or duration_seconds <= 0
        or interval_seconds <= 0
    ):
        raise ValueError("PILOT-01 workload profile has invalid numeric controls")
    if profile.get("warmup", {}).get("duration_seconds") != 0:
        raise ValueError("PILOT-01 uses no warm-up; the run must begin from the reset seed")

    run_dir = checkout / "experiments/results" / run_id
    evidence_id = f"{run_id}-exp01"
    evidence_dir = checkout / "experiments/results" / evidence_id
    if run_dir.exists() or evidence_dir.exists():
        raise FileExistsError(f"PILOT-01 output already exists for {run_id}")
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True)
    (run_dir / "workload_profile.yaml").write_bytes(profile_bytes)
    compose_project = f"evofit-pilot01-{condition.lower()}"
    environment = {
        **os.environ,
        "COMPOSE_PROJECT_NAME": compose_project,
        "COMPOSE_FILE": "docker-compose.yml",
        "EXPERIMENT_MODE": "false",
        "SEED_ID": "a0-v1",
    }

    commands: dict[str, Any] = {}
    commands["compose_up"] = run_command(
        "compose_up",
        ["docker", "compose", "up", "-d", "--build", "--wait"],
        checkout=checkout,
        raw_dir=raw_dir,
        environment=environment,
        timeout_seconds=600,
    )
    commands["database_reset"] = run_command(
        "database_reset",
        [
            "docker",
            "compose",
            "run",
            "--rm",
            "--no-deps",
            "app",
            "python",
            "-m",
            "scripts.reset_db",
        ],
        checkout=checkout,
        raw_dir=raw_dir,
        environment=environment,
        timeout_seconds=180,
    )
    commands["app_recreate"] = run_command(
        "app_recreate",
        ["docker", "compose", "up", "-d", "--force-recreate", "--wait", "app"],
        checkout=checkout,
        raw_dir=raw_dir,
        environment=environment,
        timeout_seconds=180,
    )
    health = httpx.get(f"{BASE_URL}/health/ready", timeout=10)
    health.raise_for_status()

    workload_env = {
        **environment,
        "A0_REQUEST_MIX_JSON": json.dumps(weights, sort_keys=True, separators=(",", ":")),
    }
    http_snapshot(BASE_URL, run_dir / "prometheus_before.txt")
    sampler_command = [
        sys.executable,
        "-m",
        "scripts.sample_runtime_metrics",
        "--url",
        BASE_URL,
        "--output",
        str(run_dir / "runtime_metrics.csv"),
        "--interval-seconds",
        str(interval_seconds),
        "--duration-seconds",
        str(duration_seconds + 2),
    ]
    locust_command = [
        sys.executable,
        "-m",
        "locust",
        "-f",
        "load/locustfile.py",
        "--headless",
        "-u",
        str(users),
        "-r",
        str(spawn_rate),
        "--run-time",
        f"{int(duration_seconds)}s",
        "--host",
        BASE_URL,
        "--csv",
        str(run_dir / "locust"),
    ]
    with (raw_dir / "runtime_sampler.stdout.txt").open("w", encoding="utf-8") as sampler_stdout:
        with (raw_dir / "runtime_sampler.stderr.txt").open("w", encoding="utf-8") as sampler_stderr:
            sampler = subprocess.Popen(  # noqa: S603  # nosec B603 -- fixed local sampler argv
                sampler_command,
                cwd=checkout,
                env=workload_env,
                stdout=sampler_stdout,
                stderr=sampler_stderr,
                text=True,
            )
            time.sleep(0.2)
            with (raw_dir / "locust.stdout.txt").open("w", encoding="utf-8") as locust_stdout:
                with (raw_dir / "locust.stderr.txt").open("w", encoding="utf-8") as locust_stderr:
                    locust = subprocess.Popen(  # noqa: S603  # nosec B603 -- fixed Locust argv
                        locust_command,
                        cwd=checkout,
                        env=workload_env,
                        stdout=locust_stdout,
                        stderr=locust_stderr,
                        text=True,
                    )
                    time.sleep(0.5)
                    exp01_command = [
                        sys.executable,
                        "-m",
                        "scripts.exp01_evidence",
                        "--architecture-state",
                        "A0_1_CAPABILITY_MODULES",
                        "--fitness-config",
                        FITNESS_CONFIG,
                        "--base-url",
                        BASE_URL,
                        "--run-id",
                        evidence_id,
                        "--runtime-duration-seconds",
                        "15",
                        "--sample-interval-seconds",
                        "1",
                    ]
                    commands["exp01_collection"] = run_command(
                        "exp01_collection",
                        exp01_command,
                        checkout=checkout,
                        raw_dir=raw_dir,
                        environment=workload_env,
                        timeout_seconds=240,
                    )
                    locust_exit = locust.wait(timeout=int(duration_seconds) + 120)
            sampler_exit = sampler.wait(timeout=int(duration_seconds) + 30)

    http_snapshot(BASE_URL, run_dir / "prometheus_after.txt")
    commands["locust"] = {"argv": locust_command, "exit_code": locust_exit}
    commands["runtime_sampler"] = {"argv": sampler_command, "exit_code": sampler_exit}
    if locust_exit != 0 or sampler_exit != 0:
        raise RuntimeError(f"workload failed: Locust={locust_exit}, sampler={sampler_exit}")

    sample_result = validate_runtime_samples(
        run_dir / "runtime_metrics.csv", duration_seconds + 2, interval_seconds
    )
    before_text = (run_dir / "prometheus_before.txt").read_text(encoding="utf-8")
    after_text = (run_dir / "prometheus_after.txt").read_text(encoding="utf-8")
    process_start_time = validate_process_continuity(before_text, after_text)
    load_metrics = _locust_aggregate(run_dir / "locust_stats.csv")
    if load_metrics["request_count"] <= 0 or load_metrics["throughput_requests_per_second"] <= 0:
        raise ValueError("Locust workload did not produce measurable request throughput")
    if load_metrics["failure_count"] != 0:
        raise ValueError("Locust recorded failed requests in the controlled profile")
    if (
        load_metrics["p99_ms"] < load_metrics["p95_ms"]
        or load_metrics["p95_ms"] < load_metrics["p50_ms"]
    ):
        raise ValueError("Locust percentile order is invalid")

    expected_exp01_exit = 0 if condition == "S0" else 1
    if commands["exp01_collection"]["exit_code"] != expected_exp01_exit:
        raise RuntimeError(
            f"EXP-01 returned {commands['exp01_collection']['exit_code']} for {condition}; "
            f"expected {expected_exp01_exit}"
        )
    evidence_validation = run_command(
        "exp02_validation",
        [sys.executable, "-m", "scripts.exp02_fitness_evidence", "--run-dir", str(evidence_dir)],
        checkout=checkout,
        raw_dir=raw_dir,
        environment=environment,
        timeout_seconds=120,
    )
    commands["exp02_validation"] = evidence_validation
    if evidence_validation["exit_code"] != 0:
        raise RuntimeError("EXP-02 evidence validation failed")

    bundle = validate_bundle(evidence_dir)
    representation_evidence = validate_representation_evidence(evidence_dir, bundle)
    if bundle["source_revision"]["commit_sha"] != source_revision:
        raise ValueError("EXP-01 source revision differs from the measured source worktree")
    if bundle["source_revision"]["git_dirty"]:
        raise ValueError("EXP-01 reports a dirty source worktree")
    if bundle["bundle_status"] != "complete":
        raise ValueError("EXP-01 evidence bundle is incomplete")
    if representation_evidence["coverage_claims"]["Coverage_P"] != "not_assessed":
        raise ValueError("PILOT-01 must not claim Coverage_P")

    records = {record["record_id"]: record for record in bundle["records"]}
    import_record = records["exp01-ci-import-linter-v1"]
    module_record = records["exp02-ci-module-structure-v1"]
    runtime_record = records["exp01-runtime-v1"]
    violations = import_record["measurements"]["dependency_rule_violations"]
    expected_violations = 0 if condition == "S0" else 1
    if violations != expected_violations:
        raise ValueError(f"{condition} produced {violations} contract violations")
    if module_record["execution_verdict"] != "passed":
        raise ValueError("the existing A0.1 module-structure test must pass in both conditions")

    resource_samples = []
    with (run_dir / "runtime_metrics.csv").open(newline="", encoding="utf-8") as source:
        resource_samples = list(csv.DictReader(source))
    cpu_delta = float(resource_samples[-1]["process_cpu_seconds_total"]) - float(
        resource_samples[0]["process_cpu_seconds_total"]
    )
    rss_max = max(int(float(row["process_resident_memory_bytes"])) for row in resource_samples)
    app_image_id = docker_value(
        ["docker", "image", "inspect", "--format", "{{.Id}}", "evofit-bench-app"],
        checkout=checkout,
        environment=environment,
    )
    postgres_image_id = docker_value(
        ["docker", "image", "inspect", "--format", "{{.Id}}", "postgres:16"],
        checkout=checkout,
        environment=environment,
    )
    postgres_version = docker_value(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            "evofit",
            "-d",
            "evofit",
            "-Atc",
            "SHOW server_version",
        ],
        checkout=checkout,
        environment=environment,
    )
    app_record = runtime_record.get("source_binding") or {}
    copied_inputs = {item.get("source_path"): item for item in bundle["input_artifacts"]}
    fitness_config_sha = bundle["fitness_configuration"]["configuration_sha256"]
    evaluator_config_sha = copied_inputs[IMPORT_CONFIG]["sha256"]
    if fitness_config_sha != sha256_file(checkout / FITNESS_CONFIG):
        raise ValueError("fitness configuration changed between S0 and S1 source revisions")
    if evaluator_config_sha != sha256_file(checkout / IMPORT_CONFIG):
        raise ValueError("Import Linter configuration digest does not match the source worktree")

    environment_metadata = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or platform.machine(),
        "logical_cpu_count": psutil.cpu_count(logical=True),
        "physical_cpu_count": psutil.cpu_count(logical=False),
        "host_memory_total_bytes": psutil.virtual_memory().total,
        "docker_server_version": docker_value(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            checkout=checkout,
            environment=environment,
        ),
        "docker_compose_version": docker_value(
            ["docker", "compose", "version", "--short"],
            checkout=checkout,
            environment=environment,
        ),
        "app_image_id": app_image_id,
        "postgres_image_id": postgres_image_id,
        "postgres_server_version": postgres_version,
        "compose_resource_limits_configured": any(
            key
            in yaml.safe_load((checkout / "docker-compose.yml").read_text(encoding="utf-8"))[
                "services"
            ][service]
            for service in ("app", "postgres")
            for key in ("cpus", "mem_limit", "deploy")
        ),
        "import_linter_version": import_record["evaluator_version"],
        "pytest_version": module_record["evaluator_version"],
        "locust_version": distribution_version("locust"),
    }
    manifest = {
        "schema_version": "1.0.0",
        "experiment_id": "PILOT-01",
        "condition": condition,
        "repetition_id": f"{condition}-r{repetition:02d}",
        "run_id": run_id,
        "exp01_run_id": evidence_id,
        "measured_at_utc": datetime.now(UTC).isoformat(),
        "source_revision": source_revision,
        "source_git_dirty": False,
        "injected_architectural_change": FAULT_DESCRIPTION if condition == "S1" else None,
        "source_diff_sha256": sha256_bytes(source_diff) if source_diff else None,
        "fitness_configuration_sha256": fitness_config_sha,
        "evaluator_configuration_sha256": evaluator_config_sha,
        "workload_profile_id": profile["id"],
        "workload_profile_sha256": sha256_bytes(profile_bytes),
        "import_linter": {
            "exit_code": import_record["exit_status"],
            "broken_contract_count": violations,
            "duration_seconds": import_record["duration_seconds"],
            "evaluator_version": import_record["evaluator_version"],
        },
        "module_structure_test": {
            "exit_code": module_record["exit_status"],
            "outcome": module_record["execution_verdict"],
            "duration_seconds": module_record["duration_seconds"],
        },
        "evidence": {
            "exp01_bundle_status": bundle["bundle_status"],
            "exp01_bundle_sha256": sha256_file(evidence_dir / BUNDLE_FILENAME),
            "exp02_validation": "valid",
            "representation_evidence_sha256": bundle["fitness_representation_evidence"]["sha256"],
            "Coverage_P": representation_evidence["coverage_claims"]["Coverage_P"],
            "Coverage_ref": representation_evidence["coverage_claims"]["Coverage_ref"],
        },
        "runtime": {
            **load_metrics,
            "application_cpu_seconds_delta": cpu_delta,
            "application_rss_max_bytes": rss_max,
            "sample_count": sample_result["sample_count"],
            "process_start_time_seconds": process_start_time,
            "runtime_application_identity_status": app_record.get("status", "unavailable"),
            "application_image_id": app_record.get("image_id"),
        },
        "environment": environment_metadata,
        "commands": commands,
        "artifact_references": _artifact_inventory(checkout, [run_dir, evidence_dir]),
    }
    manifest_path = run_dir / "run_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    """Run one clean S0/S1 repetition and print a compact evidence summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--condition", choices=("S0", "S1"), required=True)
    parser.add_argument("--repetition", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        manifest = run_measurement(args.checkout, args.condition, args.repetition)
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "status": "complete",
                "run_id": manifest["run_id"],
                "source_revision": manifest["source_revision"],
                "import_linter_exit_code": manifest["import_linter"]["exit_code"],
                "contract_violations": manifest["import_linter"]["broken_contract_count"],
                "evidence_status": manifest["evidence"]["exp01_bundle_status"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
