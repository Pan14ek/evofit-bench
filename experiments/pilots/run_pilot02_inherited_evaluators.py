"""Run PILOT-02's four inherited A0 evaluators against the A0.1 application."""

from __future__ import annotations

import argparse
import atexit
import importlib.metadata
import json
import os
import platform
import re
import shutil
import subprocess  # nosec B404 - fixed evaluator argv, no shell
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx
import yaml

from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.hashing import sha256_bytes
from experiments.pilots.run_pilot01_measurement import _locust_aggregate
from load.workload_profile import validate_request_mix
from scripts.exp01_evidence_contract import BUNDLE_FILENAME, validate_bundle
from scripts.exp02_fitness_evidence import validate_representation_evidence

ROOT = Path(__file__).resolve().parents[2]
APP_TREE_SHA = "cdff9a6c3cee870e1eca2a5f5f3eb3202b0b1f08"
FITNESS_CONFIG = "fitness/configs/a0_1-capability-modules.dev.yaml"
WORKLOAD_PROFILE = ROOT / "experiments/pilots/PILOT_01_WORKLOAD.yaml"
RUN_ID_PATTERN = re.compile(r"^pilot02-inherited-[A-Za-z0-9][A-Za-z0-9._-]{0,48}$")
INTEGRATION_NODE = (
    "tests/integration/test_api_flows.py::"
    "test_enabled_faults_delay_fail_deterministically_and_reset"
)


def _sha256_file(path: Path) -> str:
    """Hash a regular evidence file."""
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"expected regular evidence file: {path}")
    return sha256_bytes(path.read_bytes())


def _git(*arguments: str) -> str:
    """Run a bounded read-only Git query against this source checkout."""
    executable = shutil.which("git")
    if executable is None:
        raise RuntimeError("git executable is unavailable")
    result = subprocess.run(  # noqa: S603 - fixed Git argv, no shell
        [executable, *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip()


def _validate_database_url(database_url: str) -> dict[str, Any]:
    """Require a PostgreSQL URL scoped to a disposable EvoFit database."""
    parsed = urlsplit(database_url)
    database_name = parsed.path.lstrip("/")
    if (
        parsed.scheme not in {"postgresql", "postgresql+psycopg"}
        or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
        or not database_name
        or "evofit" not in database_name.lower()
    ):
        raise ValueError(
            "TEST_DATABASE_URL must target a disposable PostgreSQL database named with evofit"
        )
    return {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "database_name": database_name,
        "container_id": None,
        "credentials_recorded": False,
        "isolation_requirement": (
            "dedicated disposable database; integration fixture drops public schema"
        ),
    }


def _docker_port_map_contains_host_port(port_map: Any, host_port: int) -> bool:
    """Return whether Docker inspect output maps a container port to the host port."""
    if not isinstance(port_map, dict):
        return False
    for bindings in port_map.values():
        if not isinstance(bindings, list):
            continue
        if any(
            isinstance(binding, dict) and binding.get("HostPort") == str(host_port)
            for binding in bindings
        ):
            return True
    return False


def _docker_container_id_for_host_port(docker: str, host_port: int) -> str | None:
    """Resolve one running Docker container whose published port matches the test DB URL."""
    try:
        containers = subprocess.run(  # noqa: S603 - fixed read-only Docker argv
            [docker, "ps", "--quiet"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if containers.returncode != 0:
            return None
        matching_ids: list[str] = []
        for container_id in containers.stdout.splitlines():
            inspected = subprocess.run(  # noqa: S603 - fixed read-only Docker argv
                [
                    docker,
                    "inspect",
                    "--format",
                    "{{.Id}} {{json .NetworkSettings.Ports}}",
                    container_id,
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if inspected.returncode != 0:
                continue
            try:
                full_id, serialized_ports = inspected.stdout.strip().split(" ", maxsplit=1)
                port_map = json.loads(serialized_ports)
            except (ValueError, json.JSONDecodeError):
                continue
            if re.fullmatch(r"[0-9a-f]{64}", full_id) and _docker_port_map_contains_host_port(
                port_map, host_port
            ):
                matching_ids.append(full_id)
    except (OSError, subprocess.SubprocessError):
        return None
    return matching_ids[0] if len(matching_ids) == 1 else None


def _run_captured(
    label: str,
    argv: list[str],
    *,
    run_dir: Path,
    environment: dict[str, str],
    timeout_seconds: int,
) -> dict[str, Any]:
    """Run a fixed command and preserve byte-exact standard streams and duration."""
    started_at = datetime.now(UTC)
    started_ns = time.perf_counter_ns()
    try:
        completed = subprocess.run(  # noqa: S603 - fixed evaluator argv, no shell
            argv,
            cwd=ROOT,
            env=environment,
            check=False,
            capture_output=True,
            timeout=timeout_seconds,
        )
        exit_status = completed.returncode
        stdout, stderr = completed.stdout, completed.stderr
    except subprocess.TimeoutExpired as error:
        exit_status = None
        stdout = (
            error.stdout if isinstance(error.stdout, bytes) else str(error.stdout or "").encode()
        )
        stderr = (
            error.stderr if isinstance(error.stderr, bytes) else str(error.stderr or "").encode()
        )
    duration_ns = time.perf_counter_ns() - started_ns
    ended_at = datetime.now(UTC)
    stdout_path = run_dir / "raw" / f"{label}.stdout.bin"
    stderr_path = run_dir / "raw" / f"{label}.stderr.bin"
    stdout_path.write_bytes(stdout)
    stderr_path.write_bytes(stderr)
    return {
        "argv": argv,
        "exit_status": exit_status,
        "duration_ns": duration_ns,
        "duration_seconds": duration_ns / 1_000_000_000,
        "started_at_utc": started_at.isoformat().replace("+00:00", "Z"),
        "ended_at_utc": ended_at.isoformat().replace("+00:00", "Z"),
        "stdout": {
            "path": stdout_path.relative_to(run_dir).as_posix(),
            "sha256": sha256_bytes(stdout),
        },
        "stderr": {
            "path": stderr_path.relative_to(run_dir).as_posix(),
            "sha256": sha256_bytes(stderr),
        },
    }


def _write_json_artifact(
    run_dir: Path, relative_path: str, payload: dict[str, Any]
) -> dict[str, str]:
    """Write a canonical evaluator configuration and return its exact artifact reference."""
    path = run_dir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"
    path.write_bytes(content)
    return {"path": relative_path, "sha256": sha256_bytes(content)}


def _verified_source_reference(reference: dict[str, Any]) -> dict[str, str]:
    """Verify a source reference from the pinned profile against the clean checkout."""
    relative_path = reference.get("path")
    expected_digest = reference.get("sha256")
    if not isinstance(relative_path, str) or not isinstance(expected_digest, str):
        raise ValueError("invalid source artifact reference in PILOT-02 profile")
    relative = Path(relative_path)
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or not path.resolve(strict=True).is_relative_to(ROOT)
    ):
        raise ValueError(f"source artifact path escapes the checkout: {relative_path}")
    actual_digest = _sha256_file(path)
    if actual_digest != expected_digest:
        raise ValueError(f"source artifact digest mismatch: {relative_path}")
    return {"path": relative_path, "sha256": actual_digest}


def _representation_result(
    *,
    run_id: str,
    representation_id: str,
    source_revision: str,
    architecture_source_sha: str,
    command_record: dict[str, Any],
    command: list[str],
    evaluator_version: str,
    configuration_artifact: dict[str, str],
    metric_value: Any,
    metric_unit: str,
    metric_details: dict[str, Any],
    evaluation_status: str,
    execution_status: str,
    source_provenance_status: str,
    raw_output_artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create one fully source-, config-, command-, and raw-bound evaluator record."""
    catalog_row = yaml.safe_load((ROOT / "fitness/catalog/a0-fitness-elements.yaml").read_bytes())[
        "representations"
    ]
    definition = next(row for row in catalog_row if row["id"] == representation_id)
    binding = next(
        row
        for row in json.loads(
            (ROOT / "experiments/pilots/PILOT_02_A0_1_METHOD_INPUT_PROFILE_V2.json").read_bytes()
        )["parent_evaluator_bindings"]
        if row["representation_id"] == representation_id
    )
    evaluator_artifact = _verified_source_reference(binding["evaluator_artifact"])
    supporting_artifacts = [
        _verified_source_reference(row) for row in binding["evaluator_source_artifacts"]
    ]
    stdout_reference = command_record["stdout"]
    stderr_reference = command_record["stderr"]
    metric_names = list(definition["metrics"])
    return {
        "run_id": run_id,
        "representation_id": representation_id,
        "evaluator_id": definition["evaluator"],
        "evaluator": definition["evaluator"],
        "status": execution_status,
        "architecture_source_sha": architecture_source_sha,
        "application_tree_sha": APP_TREE_SHA,
        "source_revision": source_revision,
        "lifecycle_stage": definition["stage"],
        "metric_name": ";".join(metric_names),
        "metric_names": metric_names,
        "metric_unit": metric_unit,
        "metric_value": metric_value,
        "metric_status": "available" if metric_value is not None else "unavailable",
        "evaluation_status": evaluation_status,
        "execution_status": execution_status,
        "execution_command": command,
        "evaluator_version": evaluator_version,
        "started_at_utc": command_record["started_at_utc"],
        "ended_at_utc": command_record["ended_at_utc"],
        "duration_ns": command_record["duration_ns"],
        "exit_code": command_record["exit_status"],
        "source_artifact_path": evaluator_artifact["path"],
        "source_artifact_sha256": evaluator_artifact["sha256"],
        "supporting_source_artifacts": supporting_artifacts,
        "configuration_artifact_path": configuration_artifact["path"],
        "configuration_artifact_sha256": configuration_artifact["sha256"],
        "raw_stdout_path": stdout_reference["path"],
        "raw_stdout_sha256": stdout_reference["sha256"],
        "raw_stderr_path": stderr_reference["path"],
        "raw_stderr_sha256": stderr_reference["sha256"],
        "raw_output_artifacts": raw_output_artifacts,
        "source_provenance_status": source_provenance_status,
        "binding_status": binding["binding_status"],
        "metrics": metric_details,
    }


def _run_artifact_path(run_dir: Path, relative_path: str) -> Path:
    """Resolve a regular evidence file strictly inside the run directory."""
    relative = Path(relative_path)
    path = run_dir / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve(strict=True).is_relative_to(run_dir.resolve(strict=True))
    ):
        raise ValueError(f"invalid run evidence path: {relative_path}")
    return path


def _verify_run_artifact_digest(run_dir: Path, reference: dict[str, Any]) -> Path:
    """Verify that a run-local artifact matches its declared SHA-256 digest."""
    relative_path = reference.get("path")
    expected_digest = reference.get("sha256")
    if not isinstance(relative_path, str) or not isinstance(expected_digest, str):
        raise ValueError("run artifact reference requires path and sha256")
    path = _run_artifact_path(run_dir, relative_path)
    if _sha256_file(path) != expected_digest:
        raise ValueError(f"run artifact digest mismatch: {relative_path}")
    return path


def _validate_evidence_integrity(run_dir: Path) -> dict[str, Any]:
    """Recompute the full artifact inventory and all result-level digest references."""
    manifest_path = _run_artifact_path(run_dir, "run_manifest.json")
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    validate_payload("pilot02_inherited_evaluator_manifest_v1.schema.json", manifest)
    sidecar_path = _run_artifact_path(run_dir, "run_manifest.sha256")
    expected_sidecar = f"{sha256_bytes(manifest_bytes)}  run_manifest.json\n"
    if sidecar_path.read_text(encoding="ascii") != expected_sidecar:
        raise ValueError("run manifest checksum sidecar does not match manifest bytes")

    inventory_path = _run_artifact_path(run_dir, "inventory.json")
    inventory_bytes = inventory_path.read_bytes()
    if sha256_bytes(inventory_bytes) != manifest.get("artifact_inventory_sha256"):
        raise ValueError("run artifact inventory digest mismatch")
    inventory = json.loads(inventory_bytes)
    if not isinstance(inventory, list):
        raise ValueError("run artifact inventory must be a JSON array")
    declared_paths: set[str] = set()
    for row in inventory:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            raise ValueError("run artifact inventory contains an invalid row")
        relative_path = row["path"]
        if relative_path in declared_paths:
            raise ValueError(f"duplicate run artifact inventory path: {relative_path}")
        declared_paths.add(relative_path)
        path = _verify_run_artifact_digest(run_dir, row)
        if path.stat().st_size != row.get("size_bytes"):
            raise ValueError(f"run artifact inventory digest mismatch: {relative_path}")
    excluded = {"inventory.json", "run_manifest.json", "run_manifest.sha256"}
    observed_paths = {
        path.relative_to(run_dir).as_posix()
        for path in run_dir.rglob("*")
        if path.is_file() and not path.is_symlink() and path.name not in excluded
    }
    if declared_paths != observed_paths:
        raise ValueError("run artifact inventory does not cover the exact run-directory file set")

    results_path = _run_artifact_path(run_dir, "evaluator_results.json")
    results_bytes = results_path.read_bytes()
    if sha256_bytes(results_bytes) != manifest.get("evaluator_results_sha256"):
        raise ValueError("evaluator results digest differs from the run manifest")
    results = json.loads(results_bytes)
    validate_payload("pilot02_inherited_evaluator_results_v1.schema.json", results)
    evaluator_inventory_path = _run_artifact_path(run_dir, "evaluator_inventory.json")
    evaluator_inventory_bytes = evaluator_inventory_path.read_bytes()
    if sha256_bytes(evaluator_inventory_bytes) != results.get("evaluator_inventory_sha256"):
        raise ValueError("evaluator inventory digest differs from evaluator results")
    evaluator_inventory = json.loads(evaluator_inventory_bytes)
    validate_payload("pilot02_inherited_evaluator_inventory_v1.schema.json", evaluator_inventory)
    expected_ids = {
        "REP_A0_PERF_TEST_HTTP_P95",
        "REP_A0_PERF_RUNTIME_HTTP_DURATION",
        "REP_A0_REL_TEST_INTEGRATION",
        "REP_A0_REL_RUNTIME_FAILURES",
    }
    if {row["representation_id"] for row in results["representations"]} != expected_ids:
        raise ValueError("evaluator result set does not contain each inherited representation once")
    if {row["representation_id"] for row in evaluator_inventory["representations"]} != expected_ids:
        raise ValueError("evaluator inventory does not contain each inherited representation once")
    for row in results["representations"]:
        if (
            row["run_id"] != results["run_id"]
            or row["source_revision"] != manifest["source_revision"]
        ):
            raise ValueError("evaluator row run or source identity differs from the manifest")
        source_refs = [
            {"path": row["source_artifact_path"], "sha256": row["source_artifact_sha256"]},
            *row["supporting_source_artifacts"],
        ]
        for reference in source_refs:
            _verified_source_reference(reference)
        run_refs = [
            {
                "path": row["configuration_artifact_path"],
                "sha256": row["configuration_artifact_sha256"],
            },
            {"path": row["raw_stdout_path"], "sha256": row["raw_stdout_sha256"]},
            {"path": row["raw_stderr_path"], "sha256": row["raw_stderr_sha256"]},
            *row["raw_output_artifacts"],
        ]
        for reference in run_refs:
            _verify_run_artifact_digest(run_dir, reference)
    return {
        "status": "validated",
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "inventory_sha256": sha256_bytes(inventory_bytes),
        "evaluator_inventory_sha256": sha256_bytes(evaluator_inventory_bytes),
        "evaluator_results_sha256": sha256_bytes(results_bytes),
        "artifact_count": len(declared_paths),
    }


def _copy_tree(source: Path, destination: Path) -> list[dict[str, Any]]:
    """Copy a collector run directory and return references to every copied file."""
    shutil.copytree(source, destination)
    copied: list[dict[str, Any]] = []
    for path in sorted(destination.rglob("*")):
        if path.is_file():
            copied.append(
                {
                    "path": path.relative_to(destination.parent.parent).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": _sha256_file(path),
                }
            )
    return copied


def _run_id(value: str | None) -> str:
    suffix = value or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_id = suffix if suffix.startswith("pilot02-inherited-") else f"pilot02-inherited-{suffix}"
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError("run ID must match pilot02-inherited-<safe-suffix>")
    return run_id


def run_evaluators(
    *,
    base_url: str,
    test_database_url: str,
    compose_project: str,
    execute_method_p: bool = True,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Collect fresh Locust, runtime and integration evidence for PILOT-02."""
    source_revision = _git("rev-parse", "HEAD")
    if _git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("source checkout must be clean before inherited evaluator execution")
    if _git("rev-parse", f"{source_revision}:app") != APP_TREE_SHA:
        raise ValueError("application tree differs from the PILOT-02 A0.1 protocol pin")
    profile_path = ROOT / "experiments/pilots/PILOT_02_A0_1_METHOD_INPUT_PROFILE_V2.json"
    profile_bytes = profile_path.read_bytes()
    profile = json.loads(profile_bytes)
    profile_bindings = profile.get("parent_evaluator_bindings")
    if not isinstance(profile_bindings, list):
        raise ValueError("PILOT-02 V2 profile has no inherited evaluator bindings")
    binding_by_id: dict[str, dict[str, Any]] = {}
    for binding in profile_bindings:
        if not isinstance(binding, dict) or not isinstance(binding.get("representation_id"), str):
            raise ValueError("PILOT-02 V2 profile contains an invalid inherited binding")
        representation_id = binding["representation_id"]
        if representation_id in binding_by_id:
            raise ValueError("PILOT-02 V2 profile contains a duplicate inherited binding")
        binding_by_id[representation_id] = binding
        primary = binding.get("evaluator_artifact")
        supporting = binding.get("evaluator_source_artifacts")
        if not isinstance(primary, dict) or not isinstance(supporting, list):
            raise ValueError(f"inherited evaluator artifacts are invalid: {representation_id}")
        for reference in [primary, *supporting]:
            if not isinstance(reference, dict):
                raise ValueError(f"inherited evaluator source is invalid: {representation_id}")
            _verified_source_reference(reference)
    expected_representation_ids = {
        "REP_A0_PERF_TEST_HTTP_P95",
        "REP_A0_PERF_RUNTIME_HTTP_DURATION",
        "REP_A0_REL_TEST_INTEGRATION",
        "REP_A0_REL_RUNTIME_FAILURES",
    }
    if set(binding_by_id) != expected_representation_ids:
        raise ValueError("PILOT-02 V2 bindings do not cover the four inherited representations")
    catalog = yaml.safe_load((ROOT / "fitness/catalog/a0-fitness-elements.yaml").read_bytes())
    catalog_rows = {
        str(row.get("id")): row
        for row in catalog.get("representations", [])
        if isinstance(row, dict)
    }
    if not expected_representation_ids.issubset(catalog_rows):
        raise ValueError("frozen A0 catalog lacks one or more inherited representations")
    base = urlsplit(base_url)
    if base.scheme != "http" or base.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("base URL must be a loopback HTTP endpoint")
    database = _validate_database_url(test_database_url)
    if not re.fullmatch(r"evofit-pilot02-[a-z0-9][a-z0-9_-]{0,47}", compose_project):
        raise ValueError("compose project must use a unique evofit-pilot02- identifier")
    docker = shutil.which("docker")
    if docker is not None:
        database["container_id"] = _docker_container_id_for_host_port(docker, database["port"])
    selected_run_id = _run_id(run_id)
    run_dir = ROOT / "experiments/results" / selected_run_id
    if run_dir.exists():
        raise FileExistsError(f"PILOT-02 result directory already exists: {run_dir}")
    run_dir.mkdir(parents=True)
    raw_dir = run_dir / "raw"
    raw_dir.mkdir()

    workload_bytes = WORKLOAD_PROFILE.read_bytes()
    workload = yaml.safe_load(workload_bytes)
    if (
        not isinstance(workload, dict)
        or workload.get("architecture_state") != "A0_1_CAPABILITY_MODULES"
    ):
        raise ValueError("workload profile must be the pinned A0.1 pilot profile")
    if workload.get("warmup", {}).get("duration_seconds") != 0:
        raise ValueError("PILOT-02 workload profile must specify no warm-up")
    mix = validate_request_mix(workload.get("request_mix"))
    users = workload.get("users")
    spawn_rate = workload.get("spawn_rate_per_second")
    duration_seconds = workload.get("measurement", {}).get("duration_seconds")
    if (
        not isinstance(users, int)
        or not isinstance(spawn_rate, (int, float))
        or duration_seconds != 30
    ):
        raise ValueError("PILOT-02 workload controls differ from the predefined profile")
    workload_path = run_dir / "workload_profile.yaml"
    workload_path.write_bytes(workload_bytes)
    protocol_path = ROOT / "experiments/pilots/PILOT_02_INHERITED_EVALUATOR_PROTOCOL_V1.md"
    protocol_reference = {
        "path": "experiments/pilots/PILOT_02_INHERITED_EVALUATOR_PROTOCOL_V1.md",
        "sha256": _sha256_file(protocol_path),
    }
    fitness_config_reference = {
        "path": FITNESS_CONFIG,
        "sha256": _sha256_file(ROOT / FITNESS_CONFIG),
    }
    workload_reference = {
        "path": "workload_profile.yaml",
        "sha256": sha256_bytes(workload_bytes),
    }
    evaluator_configs: dict[str, dict[str, str]] = {
        "REP_A0_PERF_TEST_HTTP_P95": _write_json_artifact(
            run_dir,
            "raw/evaluator_configs/locust.json",
            {
                "representation_id": "REP_A0_PERF_TEST_HTTP_P95",
                "workload_profile": workload_reference,
                "protocol": protocol_reference,
                "users": users,
                "spawn_rate_per_second": spawn_rate,
                "duration_seconds": duration_seconds,
                "warmup_seconds": 0,
                "request_mix": mix,
            },
        ),
        "REP_A0_PERF_RUNTIME_HTTP_DURATION": _write_json_artifact(
            run_dir,
            "raw/evaluator_configs/runtime_http_duration.json",
            {
                "representation_id": "REP_A0_PERF_RUNTIME_HTTP_DURATION",
                "fitness_configuration": fitness_config_reference,
                "protocol": protocol_reference,
                "runtime_duration_seconds": 15,
                "sample_interval_seconds": 1,
                "quantile_estimation": "prohibited",
            },
        ),
        "REP_A0_REL_TEST_INTEGRATION": _write_json_artifact(
            run_dir,
            "raw/evaluator_configs/integration_test.json",
            {
                "representation_id": "REP_A0_REL_TEST_INTEGRATION",
                "protocol": protocol_reference,
                "test_node_id": INTEGRATION_NODE,
                "database_isolation": (
                    "dedicated disposable PostgreSQL database named with evofit; "
                    "public schema is reset"
                ),
            },
        ),
        "REP_A0_REL_RUNTIME_FAILURES": _write_json_artifact(
            run_dir,
            "raw/evaluator_configs/runtime_failures.json",
            {
                "representation_id": "REP_A0_REL_RUNTIME_FAILURES",
                "fitness_configuration": fitness_config_reference,
                "protocol": protocol_reference,
                "runtime_duration_seconds": 15,
                "sample_interval_seconds": 1,
                "business_rejection_metric": "business_rule_rejections_total",
                "failure_metric": "business_operation_failures_total",
                "http_5xx_label_filters": {"traffic_class": "business", "status_class": "5xx"},
            },
        ),
    }

    environment = {
        **os.environ,
        "COMPOSE_PROJECT_NAME": compose_project,
        "COMPOSE_FILE": "docker-compose.yml",
        "A0_REQUEST_MIX_JSON": json.dumps(mix, sort_keys=True, separators=(",", ":")),
        "EXPERIMENT_MODE": "false",
        "SEED_ID": "a0-v1",
    }
    cleanup_state = [True]

    def cleanup_compose_on_exit() -> None:
        """Stop only this uniquely named Compose project after an exceptional exit."""
        if not cleanup_state[0]:
            return
        docker_executable = shutil.which("docker")
        if docker_executable is None:
            return
        try:
            subprocess.run(  # noqa: S603 - fixed Compose cleanup argv, no shell
                [docker_executable, "compose", "down"],
                cwd=ROOT,
                env=environment,
                check=False,
                capture_output=True,
                timeout=180,
            )
        except (OSError, subprocess.SubprocessError):
            pass

    atexit.register(cleanup_compose_on_exit)
    setup_commands: list[dict[str, Any]] = []
    for label, argv, timeout_seconds in [
        (
            "compose_up",
            ["docker", "compose", "up", "-d", "--build", "--wait"],
            900,
        ),
        (
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
            180,
        ),
        (
            "app_recreate",
            ["docker", "compose", "up", "-d", "--force-recreate", "--wait", "app"],
            240,
        ),
    ]:
        setup_record = _run_captured(
            label,
            argv,
            run_dir=run_dir,
            environment=environment,
            timeout_seconds=timeout_seconds,
        )
        setup_commands.append(setup_record)
        if setup_record["exit_status"] != 0:
            raise RuntimeError(f"PILOT-02 setup command failed: {label}")
    readiness = httpx.get(f"{base_url.rstrip('/')}/health/ready", timeout=10, trust_env=False)
    readiness.raise_for_status()
    exp01_run_id = f"{selected_run_id}-exp01"
    locust_prefix = str(run_dir / "raw/locust")
    locust_argv = [
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
        base_url,
        "--csv",
        locust_prefix,
    ]
    locust_started_at = datetime.now(UTC)
    locust_started_ns = time.perf_counter_ns()
    with (
        (raw_dir / "locust.stdout.bin").open("wb") as stdout,
        (raw_dir / "locust.stderr.bin").open("wb") as stderr,
    ):
        locust_process = subprocess.Popen(  # noqa: S603 - fixed Locust argv, no shell
            locust_argv,
            cwd=ROOT,
            env=environment,
            stdout=stdout,
            stderr=stderr,
        )
        exp01_argv = [
            sys.executable,
            "-m",
            "scripts.exp01_evidence",
            "--architecture-state",
            "A0_1_CAPABILITY_MODULES",
            "--fitness-config",
            FITNESS_CONFIG,
            "--base-url",
            base_url,
            "--run-id",
            exp01_run_id,
            "--runtime-duration-seconds",
            "15",
            "--sample-interval-seconds",
            "1",
        ]
        exp01_result = _run_captured(
            "exp01_collection",
            exp01_argv,
            run_dir=run_dir,
            environment=environment,
            timeout_seconds=300,
        )
        try:
            locust_exit = locust_process.wait(timeout=int(duration_seconds) + 180)
        except subprocess.TimeoutExpired:
            locust_process.kill()
            locust_exit = locust_process.wait(timeout=10)
            exp01_result["locust_timeout"] = True
    locust_duration_ns = time.perf_counter_ns() - locust_started_ns
    locust_stdout = (raw_dir / "locust.stdout.bin").read_bytes()
    locust_stderr = (raw_dir / "locust.stderr.bin").read_bytes()
    locust_ended_at = datetime.now(UTC)
    exp01_result["locust_process_exit_status"] = locust_exit
    locust_files = {path.name: path for path in run_dir.glob("raw/locust_*") if path.is_file()}
    aggregate_path = run_dir / "raw/locust_stats.csv"
    aggregate_path = locust_files.get("locust_stats.csv", aggregate_path)
    locust_metrics: dict[str, Any] | None = None
    locust_parse_error: str | None = None
    try:
        locust_metrics = _locust_aggregate(aggregate_path)
    except (OSError, ValueError) as error:
        locust_parse_error = str(error)
    locust_usable = bool(
        locust_metrics is not None
        and locust_metrics["request_count"] > 0
        and locust_metrics["failure_count"] >= 0
        and locust_metrics["p99_ms"] >= locust_metrics["p95_ms"] >= locust_metrics["p50_ms"]
        and locust_exit == 0
    )

    exp01_source_dir = ROOT / "experiments/results" / exp01_run_id
    exp01_summary: dict[str, Any] = {"status": "unavailable", "reason": "EXP-01 output not found"}
    runtime_record: dict[str, Any] | None = None
    copied_exp01: list[dict[str, Any]] = []
    if exp01_source_dir.is_dir():
        copied_exp01 = _copy_tree(exp01_source_dir, run_dir / "raw/exp01")
        try:
            exp01_bundle = validate_bundle(exp01_source_dir)
            representation_evidence = validate_representation_evidence(
                exp01_source_dir, exp01_bundle
            )
            if exp01_bundle["source_revision"]["commit_sha"] != source_revision:
                raise ValueError("EXP-01 source revision differs from evaluator source revision")
            if exp01_bundle["source_revision"]["git_dirty"]:
                raise ValueError("EXP-01 source checkout was dirty")
            runtime_record = next(
                row for row in exp01_bundle["records"] if row.get("record_id") == "exp01-runtime-v1"
            )
            exp01_summary = {
                "status": "validated",
                "run_id": exp01_run_id,
                "bundle_sha256": _sha256_file(exp01_source_dir / BUNDLE_FILENAME),
                "bundle_status": exp01_bundle["bundle_status"],
                "representation_evidence_sha256": exp01_bundle["fitness_representation_evidence"][
                    "sha256"
                ],
                "representation_validation": representation_evidence.get("validation_status"),
                "runtime_record_status": runtime_record.get("status"),
                "runtime_sampling_status": runtime_record.get("measurements", {})
                .get("runtime_sampling", {})
                .get("status"),
                "copied_artifact_count": len(copied_exp01),
                "source_binding": runtime_record.get("source_binding"),
            }
        except (OSError, ValueError, KeyError, StopIteration) as error:
            exp01_summary = {"status": "invalid", "run_id": exp01_run_id, "reason": str(error)}

    junit_path = raw_dir / "integration-junit.xml"
    integration_command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        INTEGRATION_NODE,
        f"--junitxml={junit_path}",
    ]
    integration_environment = {**environment, "TEST_DATABASE_URL": test_database_url}
    integration_process = _run_captured(
        "integration_pytest",
        integration_command,
        run_dir=run_dir,
        environment=integration_environment,
        timeout_seconds=300,
    )
    junit_summary: dict[str, Any] | None = None
    if junit_path.is_file():
        root = ET.parse(junit_path).getroot()  # noqa: S314 - locally generated pytest JUnit output
        suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
        cases = [case for suite in suites for case in suite.findall("testcase")]
        junit_summary = {
            "tests": sum(int(suite.attrib.get("tests", "0")) for suite in suites),
            "failures": sum(int(suite.attrib.get("failures", "0")) for suite in suites),
            "errors": sum(int(suite.attrib.get("errors", "0")) for suite in suites),
            "skipped": sum(int(suite.attrib.get("skipped", "0")) for suite in suites),
            "case_names": [case.attrib.get("name") for case in cases],
        }

    method_p_summary: dict[str, Any] = {"status": "not_run"}
    method_p_command: dict[str, Any] | None = None
    if execute_method_p:
        temporary_parent = Path(tempfile.mkdtemp(prefix="pilot02-method-p-"))
        method_p_output = temporary_parent / "run"
        assumptions_path = ROOT / "experiments/pilots/PILOT_02_DEVELOPMENT_ASSUMPTIONS_V2.json"
        method_p_argv = [
            sys.executable,
            "-m",
            "experiments.pilots.run_pilot02_method_p",
            "--exp02-run-dir",
            str(exp01_source_dir),
            "--output-dir",
            str(method_p_output),
            "--profile-version",
            "2",
            "--test-only-continuation",
            "--test-only-assumptions",
            str(assumptions_path),
        ]
        method_p_command = _run_captured(
            "method_p_run",
            method_p_argv,
            run_dir=run_dir,
            environment=environment,
            timeout_seconds=600,
        )
        if method_p_output.is_dir():
            shutil.copytree(method_p_output, run_dir / "method_p")
            method_manifest_path = run_dir / "method_p/run_manifest.json"
            try:
                method_manifest = json.loads(method_manifest_path.read_bytes())
                method_p_summary = {
                    "status": "measured" if method_p_command["exit_status"] == 0 else "partial",
                    "execution_status": method_manifest.get("execution_status"),
                    "manifest_sha256": _sha256_file(method_manifest_path),
                    "method_p": method_manifest.get("method_p"),
                    "b0": method_manifest.get("b0"),
                    "p_method_input": method_manifest.get("p_method_input"),
                    "research_gates": method_manifest.get("research_gates"),
                    "total_process_duration_ns": method_p_command["duration_ns"],
                }
            except (OSError, json.JSONDecodeError) as error:
                method_p_summary = {"status": "invalid", "reason": str(error)}
        elif method_p_command["exit_status"] != 0:
            method_p_summary = {
                "status": "failed",
                "exit_status": method_p_command["exit_status"],
            }
        shutil.rmtree(temporary_parent, ignore_errors=True)

    runtime_measurements = (
        runtime_record.get("measurements", {}).get("metrics", {})
        if isinstance(runtime_record, dict)
        else {}
    )
    locust_stdout_reference = {
        "path": "raw/locust.stdout.bin",
        "sha256": sha256_bytes(locust_stdout),
        "role": "stdout",
    }
    locust_stderr_reference = {
        "path": "raw/locust.stderr.bin",
        "sha256": sha256_bytes(locust_stderr),
        "role": "stderr",
    }
    locust_raw_artifacts = [locust_stdout_reference, locust_stderr_reference]
    for path in sorted(locust_files.values()):
        locust_raw_artifacts.append(
            {
                "path": path.relative_to(run_dir).as_posix(),
                "sha256": _sha256_file(path),
                "role": "locust_measurement_output",
            }
        )
    locust_command_record = {
        "argv": locust_argv,
        "exit_status": locust_exit,
        "duration_ns": locust_duration_ns,
        "started_at_utc": locust_started_at.isoformat().replace("+00:00", "Z"),
        "ended_at_utc": locust_ended_at.isoformat().replace("+00:00", "Z"),
        "stdout": locust_stdout_reference,
        "stderr": locust_stderr_reference,
    }
    runtime_source_binding = (
        runtime_record.get("source_binding", {}) if isinstance(runtime_record, dict) else {}
    )
    runtime_binding_status = runtime_source_binding.get("status", "unverified")
    runtime_provenance = f"source_revision_pinned;container_identity_{runtime_binding_status}"
    runtime_raw_artifacts: list[dict[str, Any]] = []
    if isinstance(runtime_record, dict):
        for reference in runtime_record.get("raw_output_artifacts", []):
            if not isinstance(reference, dict) or not isinstance(reference.get("path"), str):
                continue
            relative_path = Path(reference["path"])
            copied_path = run_dir / "raw/exp01" / relative_path
            if (
                relative_path.is_absolute()
                or ".." in relative_path.parts
                or not copied_path.is_file()
            ):
                continue
            actual_digest = _sha256_file(copied_path)
            if actual_digest != reference.get("sha256"):
                raise ValueError(f"copied EXP-01 raw artifact digest mismatch: {reference['path']}")
            runtime_raw_artifacts.append(
                {
                    "path": copied_path.relative_to(run_dir).as_posix(),
                    "sha256": actual_digest,
                    "role": reference.get("role", "exp01_runtime_output"),
                }
            )
    runtime_raw_artifacts.extend([exp01_result["stdout"], exp01_result["stderr"]])
    locust_metric_value = locust_metrics.get("p95_ms") if locust_usable and locust_metrics else None
    locust_record = _representation_result(
        run_id=selected_run_id,
        representation_id="REP_A0_PERF_TEST_HTTP_P95",
        source_revision=source_revision,
        architecture_source_sha=profile["a0_1_source_basis_sha"],
        command_record=locust_command_record,
        command=locust_argv,
        evaluator_version=importlib.metadata.version("locust"),
        configuration_artifact=evaluator_configs["REP_A0_PERF_TEST_HTTP_P95"],
        metric_value=locust_metric_value,
        metric_unit="ms",
        metric_details={"locust_aggregate": locust_metrics, "parse_error": locust_parse_error},
        evaluation_status="NOT_EVALUATED" if locust_metric_value is not None else "UNKNOWN",
        execution_status="measured" if locust_usable else "partial",
        source_provenance_status=runtime_provenance,
        raw_output_artifacts=locust_raw_artifacts,
    )
    histogram = (
        runtime_measurements.get("histogram") if isinstance(runtime_measurements, dict) else None
    )
    runtime_metric_available = (
        isinstance(histogram, dict) and histogram.get("status") == "available"
    )
    runtime_record_command = exp01_result
    runtime_evaluator_version = (
        str(runtime_record.get("evaluator_version"))
        if isinstance(runtime_record, dict) and runtime_record.get("evaluator_version")
        else "source-sha256:"
        + binding_by_id["REP_A0_PERF_RUNTIME_HTTP_DURATION"]["evaluator_artifact"]["sha256"]
    )
    runtime_duration_record = _representation_result(
        run_id=selected_run_id,
        representation_id="REP_A0_PERF_RUNTIME_HTTP_DURATION",
        source_revision=source_revision,
        architecture_source_sha=profile["a0_1_source_basis_sha"],
        command_record=runtime_record_command,
        command=exp01_result["argv"],
        evaluator_version=runtime_evaluator_version,
        configuration_artifact=evaluator_configs["REP_A0_PERF_RUNTIME_HTTP_DURATION"],
        metric_value=histogram if runtime_metric_available else None,
        metric_unit="seconds_histogram_buckets_count_sum",
        metric_details={
            "histogram": histogram,
            "process": runtime_measurements.get("process")
            if isinstance(runtime_measurements, dict)
            else None,
            "snapshot_capture_times": runtime_measurements.get("snapshot_capture_times")
            if isinstance(runtime_measurements, dict)
            else None,
            "exp01_run_id": exp01_run_id,
            "exp01_bundle_sha256": exp01_summary.get("bundle_sha256"),
            "source_binding": runtime_source_binding,
        },
        evaluation_status="NOT_EVALUATED" if runtime_metric_available else "UNKNOWN",
        execution_status="measured"
        if runtime_metric_available and exp01_summary.get("status") == "validated"
        else "partial",
        source_provenance_status=runtime_provenance,
        raw_output_artifacts=runtime_raw_artifacts,
    )
    counters = (
        runtime_measurements.get("counters", {}) if isinstance(runtime_measurements, dict) else {}
    )
    business_rate = (
        runtime_measurements.get("business_5xx_rate")
        if isinstance(runtime_measurements, dict)
        else None
    )
    operation_failures = (
        counters.get("business_operation_failures_total") if isinstance(counters, dict) else None
    )
    failure_metric_available = bool(
        isinstance(business_rate, dict)
        and business_rate.get("status") == "available"
        and isinstance(operation_failures, dict)
        and operation_failures.get("status") == "available"
    )
    failure_details = {
        "business_http_5xx_rate": business_rate,
        "http_requests_total_business": counters.get("http_requests_total_business")
        if isinstance(counters, dict)
        else None,
        "http_responses_total_business_5xx": counters.get("http_responses_total_business_5xx")
        if isinstance(counters, dict)
        else None,
        "business_operation_failures_total": operation_failures,
        "business_rule_rejections_total": counters.get("business_rule_rejections_total")
        if isinstance(counters, dict)
        else None,
        "snapshot_capture_times": runtime_measurements.get("snapshot_capture_times")
        if isinstance(runtime_measurements, dict)
        else None,
        "source_binding": runtime_source_binding,
    }
    failure_record = _representation_result(
        run_id=selected_run_id,
        representation_id="REP_A0_REL_RUNTIME_FAILURES",
        source_revision=source_revision,
        architecture_source_sha=profile["a0_1_source_basis_sha"],
        command_record=runtime_record_command,
        command=exp01_result["argv"],
        evaluator_version=runtime_evaluator_version,
        configuration_artifact=evaluator_configs["REP_A0_REL_RUNTIME_FAILURES"],
        metric_value=failure_details if failure_metric_available else None,
        metric_unit="ratio_and_operation_counter",
        metric_details=failure_details,
        evaluation_status="NOT_EVALUATED" if failure_metric_available else "UNKNOWN",
        execution_status="measured"
        if failure_metric_available and exp01_summary.get("status") == "validated"
        else "partial",
        source_provenance_status=runtime_provenance,
        raw_output_artifacts=runtime_raw_artifacts,
    )
    integration_raw_artifacts = [
        integration_process["stdout"],
        integration_process["stderr"],
    ]
    if junit_path.is_file():
        integration_raw_artifacts.append(
            {
                "path": junit_path.relative_to(run_dir).as_posix(),
                "sha256": _sha256_file(junit_path),
                "role": "pytest_junit_xml",
            }
        )
    if junit_summary is None or integration_process["exit_status"] is None:
        integration_evaluation_status = "UNKNOWN"
        integration_metric_value = None
    elif junit_summary["errors"] > 0:
        integration_evaluation_status = "UNKNOWN"
        integration_metric_value = None
    elif junit_summary["failures"] > 0:
        integration_evaluation_status = "FAIL"
        integration_metric_value = False
    elif junit_summary["skipped"] > 0:
        integration_evaluation_status = "NOT_EVALUATED"
        integration_metric_value = None
    elif integration_process["exit_status"] == 0 and junit_summary["tests"] == 1:
        integration_evaluation_status = "PASS"
        integration_metric_value = True
    else:
        integration_evaluation_status = "UNKNOWN"
        integration_metric_value = None
    integration_record = _representation_result(
        run_id=selected_run_id,
        representation_id="REP_A0_REL_TEST_INTEGRATION",
        source_revision=source_revision,
        architecture_source_sha=profile["a0_1_source_basis_sha"],
        command_record=integration_process,
        command=integration_command,
        evaluator_version=importlib.metadata.version("pytest"),
        configuration_artifact=evaluator_configs["REP_A0_REL_TEST_INTEGRATION"],
        metric_value=integration_metric_value,
        metric_unit="boolean_test_outcome",
        metric_details={"junit": junit_summary, "database": database, "node_id": INTEGRATION_NODE},
        evaluation_status=integration_evaluation_status,
        execution_status="measured"
        if integration_process["exit_status"] is not None and junit_summary is not None
        else "partial",
        source_provenance_status="clean_source_revision_pinned_test_source_sha256_verified",
        raw_output_artifacts=integration_raw_artifacts,
    )
    representation_records = [
        locust_record,
        runtime_duration_record,
        integration_record,
        failure_record,
    ]
    inventory_representations = [
        {
            key: row[key]
            for key in (
                "representation_id",
                "evaluator_id",
                "lifecycle_stage",
                "metric_names",
                "metric_unit",
                "evaluator_version",
                "source_artifact_path",
                "source_artifact_sha256",
                "supporting_source_artifacts",
                "configuration_artifact_path",
                "configuration_artifact_sha256",
                "execution_command",
                "binding_status",
            )
        }
        for row in representation_records
    ]
    evaluator_inventory = {
        "schema_version": "1.0.0",
        "run_id": selected_run_id,
        "source_revision": source_revision,
        "architecture_source_sha": profile["a0_1_source_basis_sha"],
        "application_tree_sha": APP_TREE_SHA,
        "profile_id": profile["profile_id"],
        "profile_sha256": sha256_bytes(profile_bytes),
        "representations": inventory_representations,
    }
    validate_payload("pilot02_inherited_evaluator_inventory_v1.schema.json", evaluator_inventory)
    evaluator_inventory_bytes = (
        json.dumps(evaluator_inventory, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"
    )
    evaluator_inventory_path = run_dir / "evaluator_inventory.json"
    evaluator_inventory_path.write_bytes(evaluator_inventory_bytes)
    results = {
        "schema_version": "1.0.0",
        "run_id": selected_run_id,
        "source_revision": source_revision,
        "architecture_state": "A0_1_CAPABILITY_MODULES",
        "compose_project": compose_project,
        "comparison_role": (
            "shared unchanged evaluator observations for B0 and materialized P candidate"
        ),
        "representations": representation_records,
        "profile_sha256": sha256_bytes(profile_bytes),
        "evaluator_inventory_sha256": sha256_bytes(evaluator_inventory_bytes),
        "comparison_interpretation": (
            "These evaluator definitions are unchanged rows shared by B0 and P. Each was executed "
            "once on the same A0.1 source and the same fresh run; results are not independent "
            "replicates and do not establish pair semantics or coverage."
        ),
        "exp01": exp01_summary,
        "exp01_command": exp01_result,
        "integration_command": integration_process,
        "method_p": method_p_summary,
        "method_p_command": method_p_command,
        "setup_commands": setup_commands,
        "limitations": [
            (
                "Runtime histogram buckets/count/sum are preserved; no quantile is derived "
                "from buckets."
            ),
            (
                "The EXP-01 runtime source-to-container identity is reported as observed and "
                "may remain unverified."
            ),
            (
                "A0.1 runtime collection adapter postdates A0 and is not represented as a "
                "frozen A0 artifact."
            ),
            (
                "These observations do not establish applicability, evaluator adequacy, "
                "semantic validity, coverage, G1/G4 or DA01 results."
            ),
        ],
    }
    if (
        locust_record["status"] == "partial"
        or exp01_summary.get("status") != "validated"
        or exp01_summary.get("bundle_status") != "complete"
        or exp01_summary.get("runtime_sampling_status") != "available"
    ):
        results["execution_status"] = "partial"
    elif integration_record["execution_status"] == "partial":
        results["execution_status"] = "partial"
    elif execute_method_p and method_p_summary.get("status") != "measured":
        results["execution_status"] = "partial"
    else:
        results["execution_status"] = "completed_development_evidence"
    cleanup_command = _run_captured(
        "compose_down",
        ["docker", "compose", "down"],
        run_dir=run_dir,
        environment=environment,
        timeout_seconds=180,
    )
    cleanup_state[0] = cleanup_command["exit_status"] != 0
    if cleanup_state[0]:
        results["execution_status"] = "partial"
    results["setup_commands"] = setup_commands
    results["cleanup_command"] = cleanup_command
    results_path = run_dir / "evaluator_results.json"
    validate_payload("pilot02_inherited_evaluator_results_v1.schema.json", results)
    results_path.write_text(json.dumps(results, indent=2, sort_keys=True, allow_nan=False) + "\n")

    inventory: list[dict[str, Any]] = []
    for path in sorted(run_dir.rglob("*")):
        if path.is_file() and path.name not in {
            "inventory.json",
            "run_manifest.json",
            "run_manifest.sha256",
        }:
            inventory.append(
                {
                    "path": path.relative_to(run_dir).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": _sha256_file(path),
                }
            )
    inventory_bytes = (
        json.dumps(inventory, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"
    )
    (run_dir / "inventory.json").write_bytes(inventory_bytes)
    manifest = {
        "schema_version": "1.0.0",
        "run_id": selected_run_id,
        "created_at_utc": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "execution_status": results["execution_status"],
        "source_revision": source_revision,
        "app_tree_sha": _git("rev-parse", f"{source_revision}:app"),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "workload_profile_sha256": sha256_bytes(workload_bytes),
        "test_database": database,
        "compose_project": compose_project,
        "exp01_run_id": exp01_run_id,
        "artifact_inventory_sha256": sha256_bytes(inventory_bytes),
        "evaluator_results_sha256": _sha256_file(results_path),
        "artifact_count": len(inventory),
        "evidence_integrity_status": "pending",
    }
    validate_payload("pilot02_inherited_evaluator_manifest_v1.schema.json", manifest)
    manifest_bytes = (
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"
    )
    (run_dir / "run_manifest.json").write_bytes(manifest_bytes)
    (run_dir / "run_manifest.sha256").write_text(
        f"{sha256_bytes(manifest_bytes)}  run_manifest.json\n", encoding="ascii"
    )
    _validate_evidence_integrity(run_dir)
    manifest["evidence_integrity_status"] = "validated"
    manifest_bytes = (
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"
    )
    (run_dir / "run_manifest.json").write_bytes(manifest_bytes)
    (run_dir / "run_manifest.sha256").write_text(
        f"{sha256_bytes(manifest_bytes)}  run_manifest.json\n", encoding="ascii"
    )
    integrity_validation = _validate_evidence_integrity(run_dir)
    if integrity_validation["status"] != "validated":
        raise RuntimeError("PILOT-02 evidence integrity readback did not validate")
    return manifest


def main(argv: list[str] | None = None) -> int:
    """Run the protocol's evaluator set and emit an evidence inventory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--test-database-url", required=True)
    parser.add_argument("--compose-project", required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--skip-method-p", action="store_true")
    args = parser.parse_args(argv)
    try:
        manifest = run_evaluators(
            base_url=args.base_url,
            test_database_url=args.test_database_url,
            compose_project=args.compose_project,
            execute_method_p=not args.skip_method_p,
            run_id=args.run_id,
        )
    except (
        ContractValidationError,
        OSError,
        ValueError,
        KeyError,
        RuntimeError,
        subprocess.SubprocessError,
    ) as error:
        print(json.dumps({"status": "failed", "error": str(error)}, sort_keys=True))
        return 2
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if manifest["execution_status"] == "completed_development_evidence" else 1


if __name__ == "__main__":
    raise SystemExit(main())
