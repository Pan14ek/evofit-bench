"""Collect a versioned, fail-closed DEVELOPMENT evidence bundle for A0.1."""

import argparse
import hashlib
import importlib.metadata
import json
import platform
import re
import shutil
import subprocess  # nosec B404
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from scripts.exp01_evidence_contract import (
    ROOT,
    copy_input_artifact,
    sha256_bytes,
    validate_run_id,
    write_artifact,
    write_bundle,
)
from scripts.exp01_evidence_runtime import collect_runtime_evidence, validate_local_base_url

ARCHITECTURE_STATE = "A0_1_CAPABILITY_MODULES"
ARCHITECTURE_MANIFEST = "architecture/states/A0_1_CAPABILITY_MODULES.yaml"
ARCHITECTURE_ACCEPTANCE = "architecture/acceptance/importlinter.toml"
HISTORICAL_FITNESS_CONFIG = "fitness/configs/a0-monolith.yaml"
COMPOSE_CONFIG = "docker-compose.yml"
RUNNER_EXECUTABLE = sys.executable
SUPPORTED_INPUTS = (
    ARCHITECTURE_MANIFEST,
    ARCHITECTURE_ACCEPTANCE,
    HISTORICAL_FITNESS_CONFIG,
    COMPOSE_CONFIG,
    "experiments/schemas/development_evidence_bundle_v1.schema.json",
    "app/observability/metrics.py",
    "scripts/prometheus_snapshot.py",
    "scripts/runtime_validation.py",
    "scripts/sample_runtime_metrics.py",
    "scripts/exp01_evidence.py",
    "scripts/exp01_evidence_contract.py",
    "scripts/exp01_evidence_runtime.py",
)
VIOLATION_OUTPUT = re.compile(r"found\s+\d+\s+broken contract", re.IGNORECASE)
IMPORT_LINTER_ENTRYPOINT = "import importlinter.cli as c; c.lint_imports_command()"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _distribution_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _executable_sha256(executable: str | None) -> str | None:
    if executable is None:
        return None
    path = Path(executable)
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_revision() -> dict[str, Any]:
    git_executable = shutil.which("git")
    if git_executable is None:
        raise RuntimeError("git executable is unavailable")
    try:
        commit_result = subprocess.run(  # noqa: S603  # nosec B603 -- fixed Git argv, no shell
            [git_executable, "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        status_result = subprocess.run(  # noqa: S603  # nosec B603 -- fixed Git argv, no shell
            [git_executable, "status", "--porcelain", "--untracked-files=all"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise RuntimeError("unable to record Git source revision and dirty state") from error
    commit_sha = commit_result.stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
        raise RuntimeError("Git returned an invalid source revision")
    return {"commit_sha": commit_sha, "git_dirty": bool(status_result.stdout.strip())}


def _finish_record(record: dict[str, Any], started: datetime, monotonic_started: float) -> None:
    ended = _utc_now()
    record["ended_at_utc"] = ended.isoformat()
    record["duration_seconds"] = max(0.0, time.monotonic() - monotonic_started)


def _record(
    *,
    record_id: str,
    run_id: str,
    stage: str,
    evaluator_name: str,
    source_revision: str,
    scope: str,
    started: datetime,
    executable: str | None,
    version: str | None,
    command: list[str],
    configuration_artifact: dict[str, Any] | None,
    input_artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "record_id": record_id,
        "run_id": run_id,
        "lifecycle_stage": stage,
        "status": "missing",
        "evaluator_name": evaluator_name,
        "evaluator_version": version,
        "executable": executable,
        "executable_sha256": _executable_sha256(executable),
        "command": command,
        "started_at_utc": started.isoformat(),
        "ended_at_utc": started.isoformat(),
        "duration_seconds": 0.0,
        "exit_status": None,
        "execution_verdict": "not_run",
        "scope": scope,
        "source_revision": source_revision,
        "source_binding": None,
        "configuration_artifact": configuration_artifact,
        "input_artifacts": input_artifacts,
        "raw_output_artifacts": [],
        "measurements": {},
        "errors": [],
        "limitations": [],
    }


def run_architecture_acceptance(
    run_dir: Path,
    run_id: str,
    source_revision: str,
    input_artifacts: list[dict[str, Any]],
    config_artifact: dict[str, Any],
) -> dict[str, Any]:
    """Execute the current A0.1 Import Linter acceptance configuration."""
    started = _utc_now()
    monotonic_started = time.monotonic()
    executable = RUNNER_EXECUTABLE
    version = _distribution_version("import-linter")
    command = [
        executable,
        "-c",
        IMPORT_LINTER_ENTRYPOINT,
        "--config",
        ARCHITECTURE_ACCEPTANCE,
        "--no-cache",
        "--no-logo",
    ]
    record = _record(
        record_id="exp01-ci-import-linter-v1",
        run_id=run_id,
        stage="ci_test",
        evaluator_name="import-linter",
        source_revision=source_revision,
        scope=(
            "Current A0.1 engineering acceptance contracts in "
            "architecture/acceptance/importlinter.toml."
        ),
        started=started,
        executable=executable,
        version=version,
        command=command,
        configuration_artifact=config_artifact,
        input_artifacts=input_artifacts,
    )
    if not Path(executable).is_file() or version is None:
        record["status"] = "missing"
        record["execution_verdict"] = "execution_failure"
        record["errors"].append(
            "Import Linter runner executable or package is not available in this environment"
        )
        record["limitations"].append("No Import Linter contract execution was performed.")
        _finish_record(record, started, monotonic_started)
        return record

    try:
        result = subprocess.run(  # noqa: S603  # nosec B603 -- fixed executable and checked-in config path
            command,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        record["exit_status"] = result.returncode
        stdout = result.stdout
        stderr = result.stderr
    except (OSError, subprocess.TimeoutExpired) as error:
        record["status"] = "invalid"
        record["execution_verdict"] = "execution_failure"
        record["errors"].append(f"Import Linter could not complete: {type(error).__name__}")
        stdout_value = error.stdout if isinstance(error, subprocess.TimeoutExpired) else ""
        stderr_value = error.stderr if isinstance(error, subprocess.TimeoutExpired) else str(error)
        stdout = (
            stdout_value.decode("utf-8", errors="replace")
            if isinstance(stdout_value, bytes)
            else stdout_value or ""
        )
        stderr = (
            stderr_value.decode("utf-8", errors="replace")
            if isinstance(stderr_value, bytes)
            else stderr_value or ""
        )
    record["raw_output_artifacts"] = [
        write_artifact(
            run_dir,
            "raw/import_linter.stdout.txt",
            stdout.encode("utf-8"),
            media_type="text/plain",
            role="stdout",
        ),
        write_artifact(
            run_dir,
            "raw/import_linter.stderr.txt",
            stderr.encode("utf-8"),
            media_type="text/plain",
            role="stderr",
        ),
    ]
    output = f"{stdout}\n{stderr}".strip()
    if record["status"] == "invalid":
        pass
    elif (
        record["exit_status"] == 0
        and output
        and (
            "not found any broken contracts" in output.lower()
            or "no broken contracts" in output.lower()
            or "0 broken" in output.lower()
        )
    ):
        record["status"] = "available"
        record["execution_verdict"] = "passed"
    elif record["exit_status"] != 0 and VIOLATION_OUTPUT.search(output):
        record["status"] = "available"
        record["execution_verdict"] = "violations_detected"
    elif record["exit_status"] == 0:
        record["status"] = "inconclusive"
        record["execution_verdict"] = "no_usable_evidence"
        record["errors"].append(
            "Import Linter returned success without a recognizable result summary"
        )
    else:
        record["status"] = "invalid"
        record["execution_verdict"] = "execution_failure"
        if not record["errors"]:
            record["errors"].append(
                "Import Linter exited unsuccessfully without a violation summary"
            )
    record["measurements"] = {
        "exit_status": record["exit_status"],
        "stdout_sha256": sha256_bytes(stdout.encode("utf-8")),
        "stderr_sha256": sha256_bytes(stderr.encode("utf-8")),
        "stdout_bytes": len(stdout.encode("utf-8")),
        "stderr_bytes": len(stderr.encode("utf-8")),
        "configuration_sha256": config_artifact["sha256"],
        "version_source": "importlib.metadata distribution metadata in the runner environment",
        "executable_sha256": record["executable_sha256"],
    }
    _finish_record(record, started, monotonic_started)
    return record


def _parse_compose_ps(text: str) -> list[dict[str, str]]:
    """Parse Docker Compose JSON output while retaining only non-secret topology fields."""
    if not text.strip():
        return []
    parsed: Any
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        try:
            parsed = [json.loads(line) for line in text.splitlines() if line.strip()]
        except json.JSONDecodeError as error:
            raise ValueError("Docker Compose returned malformed JSON") from error
    rows = parsed if isinstance(parsed, list) else [parsed]
    containers: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Docker Compose JSON row is not an object")
        service = row.get("Service") or row.get("service")
        name = row.get("Name") or row.get("name")
        state = row.get("State") or row.get("state")
        if not isinstance(service, str) or not isinstance(name, str) or not isinstance(state, str):
            raise ValueError("Docker Compose JSON row lacks service, name, or state")
        containers.append(
            {
                "service": service,
                "name": name,
                "state": state.lower(),
                "health": str(row.get("Health") or row.get("health") or "unknown"),
                "image": str(row.get("Image") or row.get("image") or "unknown"),
            }
        )
    return containers


def collect_deployment_observation(
    run_dir: Path,
    run_id: str,
    source_revision: str,
    input_artifacts: list[dict[str, Any]],
    architecture: dict[str, Any],
    *,
    skipped: bool = False,
) -> dict[str, Any]:
    """Collect a read-only Compose container snapshot without claiming logical topology."""
    started = _utc_now()
    monotonic_started = time.monotonic()
    docker_path = shutil.which("docker")
    executable = str(Path(docker_path).resolve()) if docker_path else None
    command = [executable, "compose", "ps", "--format", "json"] if executable else []
    record = _record(
        record_id="exp01-deployment-compose-v1",
        run_id=run_id,
        stage="deployment",
        evaluator_name="docker-compose-read-only-observer",
        source_revision=source_revision,
        scope="Running containers visible to the local Docker Compose project in this worktree.",
        started=started,
        executable=executable,
        version=None,
        command=command,
        configuration_artifact=next(
            (item for item in input_artifacts if item.get("source_path") == COMPOSE_CONFIG), None
        ),
        input_artifacts=input_artifacts,
    )
    record["executable_sha256"] = _executable_sha256(executable)
    if skipped:
        record["status"] = "skipped"
        record["execution_verdict"] = "not_run"
        record["errors"].append("deployment observation was explicitly skipped by the CLI")
        record["limitations"].append("No local container observations were collected.")
        _finish_record(record, started, monotonic_started)
        return record
    if executable is None:
        record["status"] = "missing"
        record["execution_verdict"] = "not_observed"
        record["errors"].append("docker executable is not available on PATH")
        record["limitations"].append("Compose runtime topology was not observed.")
        _finish_record(record, started, monotonic_started)
        return record

    try:
        version_result = subprocess.run(  # noqa: S603  # nosec B603 -- fixed read-only version command
            [executable, "compose", "version", "--short"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        version_text = (version_result.stdout or version_result.stderr).strip()
        if version_result.returncode != 0 or not version_text:
            raise RuntimeError("Docker Compose version is unavailable")
        record["evaluator_version"] = version_text
        result = subprocess.run(  # noqa: S603  # nosec B603 -- fixed read-only command, no shell
            command,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
        record["exit_status"] = result.returncode
        stdout = result.stdout
        stderr = result.stderr
        version_ref = write_artifact(
            run_dir,
            "raw/docker_compose_version.txt",
            (version_text + "\n").encode("utf-8"),
            media_type="text/plain",
            role="version",
        )
        stdout_ref = write_artifact(
            run_dir,
            "raw/docker_compose_ps.jsonl",
            stdout.encode("utf-8"),
            media_type="application/x-ndjson",
            role="deployment_observation",
        )
        stderr_ref = write_artifact(
            run_dir,
            "raw/docker_compose_ps.stderr.txt",
            stderr.encode("utf-8"),
            media_type="text/plain",
            role="stderr",
        )
        record["raw_output_artifacts"] = [version_ref, stdout_ref, stderr_ref]
        if result.returncode != 0:
            record["status"] = "inconclusive"
            record["execution_verdict"] = "execution_failure"
            record["errors"].append("docker compose ps returned a nonzero exit status")
        else:
            containers = _parse_compose_ps(stdout)
            running = [item for item in containers if item["state"] == "running"]
            counts: dict[str, int] = {}
            for container in running:
                counts[container["service"]] = counts.get(container["service"], 0) + 1
            declared_deployment = architecture["deployment"]
            app_count = counts.get("app", 0)
            db_count = counts.get("postgres", 0)
            comparisons = {
                "app_service_container_count": {
                    "declared_proxy": declared_deployment["deployment_units"],
                    "observed": app_count,
                    "status": "consistent_at_container_scope"
                    if app_count == 1
                    else "different_at_container_scope",
                    "limitation": (
                        "A Compose container count does not establish logical deployment units "
                        "or process count."
                    ),
                },
                "postgres_service_container_count": {
                    "declared_proxy": declared_deployment["database_instances"],
                    "observed": db_count,
                    "status": "consistent_at_container_scope"
                    if db_count == 1
                    else "different_at_container_scope",
                    "limitation": (
                        "A PostgreSQL container count does not establish database-instance count."
                    ),
                },
                "application_processes": {
                    "declared": declared_deployment["application_processes"],
                    "observed": None,
                    "status": "not_observed",
                },
                "internal_communication": {
                    "declared": declared_deployment["internal_communication"],
                    "observed": None,
                    "status": "not_observed",
                },
                "message_broker": {
                    "declared": declared_deployment["message_broker"],
                    "observed": None,
                    "status": "not_observed",
                },
            }
            record["status"] = "available"
            record["execution_verdict"] = "inconclusive"
            record["measurements"] = {
                "compose_project_scope": ROOT.name,
                "running_containers": running,
                "running_container_counts_by_service": counts,
                "state_comparisons": comparisons,
                "architecture_compliance": "not_established",
            }
            record["limitations"].extend(
                [
                    "Only running containers in this local Compose project were observed.",
                    (
                        "Container counts do not establish application process count, logical "
                        "deployment units, database internals, communication semantics, or "
                        "external brokers."
                    ),
                    "No deployment compliance or independent representation coverage is inferred.",
                ]
            )
    except (OSError, subprocess.TimeoutExpired, RuntimeError, ValueError) as error:
        record["status"] = "invalid" if isinstance(error, ValueError) else "inconclusive"
        record["execution_verdict"] = (
            "no_usable_evidence" if isinstance(error, ValueError) else "execution_failure"
        )
        record["errors"].append(f"Docker Compose observation unavailable: {type(error).__name__}")
        record["limitations"].append("Deployment facts remain UNKNOWN/NOT_OBSERVED.")
    _finish_record(record, started, monotonic_started)
    return record


def _load_architecture_manifest() -> dict[str, Any]:
    document = yaml.safe_load((ROOT / ARCHITECTURE_MANIFEST).read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("architecture_state") != ARCHITECTURE_STATE:
        raise ValueError("architecture manifest does not identify A0_1_CAPABILITY_MODULES")
    return document


def _copy_inputs(run_dir: Path) -> list[dict[str, Any]]:
    return [
        copy_input_artifact(run_dir, path, "source_or_configuration") for path in SUPPORTED_INPUTS
    ]


def collect_evidence(
    *,
    architecture_state: str,
    base_url: str,
    run_id: str,
    runtime_duration_seconds: float = 3.0,
    sample_interval_seconds: float = 0.5,
    skip_deployment_observation: bool = False,
) -> tuple[Path, dict[str, Any]]:
    """Collect and validate the three supported EXP-01 lifecycle-stage records."""
    run_id = validate_run_id(run_id)
    if architecture_state != ARCHITECTURE_STATE:
        raise ValueError(f"unsupported architecture state: {architecture_state}")
    base_url = validate_local_base_url(base_url)
    architecture = _load_architecture_manifest()
    source_revision = _git_revision()
    results_root = ROOT / "experiments/results"
    results_root.mkdir(parents=True, exist_ok=True)
    run_dir = results_root / run_id
    run_dir.mkdir(exist_ok=False)

    inputs = _copy_inputs(run_dir)
    by_source = {reference["source_path"]: reference for reference in inputs}
    manifest_ref = by_source[ARCHITECTURE_MANIFEST]
    schema_ref = by_source["experiments/schemas/development_evidence_bundle_v1.schema.json"]
    ci_inputs = [by_source[ARCHITECTURE_MANIFEST], by_source[ARCHITECTURE_ACCEPTANCE], schema_ref]
    deployment_inputs = [manifest_ref, by_source[COMPOSE_CONFIG], schema_ref]
    runtime_inputs = [
        manifest_ref,
        by_source["app/observability/metrics.py"],
        by_source["scripts/prometheus_snapshot.py"],
        by_source["scripts/runtime_validation.py"],
        by_source["scripts/sample_runtime_metrics.py"],
        by_source["scripts/exp01_evidence_runtime.py"],
        schema_ref,
    ]
    ci_record = run_architecture_acceptance(
        run_dir,
        run_id,
        source_revision["commit_sha"],
        ci_inputs,
        by_source[ARCHITECTURE_ACCEPTANCE],
    )
    deployment_record = collect_deployment_observation(
        run_dir,
        run_id,
        source_revision["commit_sha"],
        deployment_inputs,
        architecture,
        skipped=skip_deployment_observation,
    )
    runtime_record = collect_runtime_evidence(
        run_dir,
        run_id,
        base_url,
        source_revision["commit_sha"],
        runtime_inputs,
        duration_seconds=runtime_duration_seconds,
        interval_seconds=sample_interval_seconds,
    )
    records = [ci_record, deployment_record, runtime_record]
    bundle_status = (
        "complete" if all(record["status"] == "available" for record in records) else "incomplete"
    )
    bundle = {
        "schema_version": "1.1.0",
        "run_id": run_id,
        "bundle_status": bundle_status,
        "created_at_utc": _utc_now().isoformat(),
        "source_revision": source_revision,
        "architecture": {
            "state": architecture_state,
            "manifest_artifact": manifest_ref,
        },
        "fitness_configuration": _fitness_configuration_from_source(by_source),
        "execution_context": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "base_url": base_url,
            "schema_artifact": schema_ref,
        },
        "supported_stages": ["ci_test", "deployment", "runtime"],
        "input_artifacts": inputs,
        "artifact_inventory": [],
        "records": records,
        "coverage_claims": {
            "Coverage_P": "not_assessed",
            "Coverage_ref": "not_established",
            "measured_results": "not_run",
        },
        "limitations": [
            (
                "This bundle records evaluator execution and observations; it does not establish "
                "normative compliance or positive semantic coverage."
            ),
            (
                "No A0.1 fitness configuration is declared; the captured A0 configuration is "
                "explicitly mismatched and not applied."
            ),
            "Coverage_P is not assessed and independent Coverage_ref is not established.",
            (
                "This is DEVELOPMENT evidence only; it does not authorize or report measured "
                "DA01 B0/B1/P results."
            ),
        ],
    }
    return write_bundle(run_dir, bundle)


def _fitness_configuration_from_source(
    inputs_by_source: dict[str | None, dict[str, Any]],
) -> dict[str, Any]:
    source = yaml.safe_load((ROOT / HISTORICAL_FITNESS_CONFIG).read_text(encoding="utf-8"))
    if not isinstance(source, dict) or source.get("architecture_state") != "A0_MONOLITH":
        raise ValueError("historical fitness configuration identity is unexpected")
    return {
        "status": "mismatch",
        "declared_architecture_state": source["architecture_state"],
        "configuration_version": str(source["configuration_version"]),
        "configuration_artifact": inputs_by_source[HISTORICAL_FITNESS_CONFIG],
        "applicable_to_target": False,
        "reason": (
            "The checked-in fitness configuration is for A0_MONOLITH; "
            "no matching A0_1_CAPABILITY_MODULES fitness configuration is declared."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    """Run the development evidence collection CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--architecture-state", required=True, choices=[ARCHITECTURE_STATE])
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--runtime-duration-seconds", type=float, default=3.0)
    parser.add_argument("--sample-interval-seconds", type=float, default=0.5)
    parser.add_argument("--skip-deployment-observation", action="store_true")
    args = parser.parse_args(argv)
    try:
        bundle_path, bundle = collect_evidence(
            architecture_state=args.architecture_state,
            base_url=args.base_url,
            run_id=args.run_id,
            runtime_duration_seconds=args.runtime_duration_seconds,
            sample_interval_seconds=args.sample_interval_seconds,
            skip_deployment_observation=args.skip_deployment_observation,
        )
    except (FileExistsError, OSError, RuntimeError, ValueError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}, sort_keys=True))
        return 1
    summary = {
        "run_id": bundle["run_id"],
        "bundle_path": str(bundle_path),
        "bundle_sha256": hashlib.sha256(bundle_path.read_bytes()).hexdigest(),
        "bundle_status": bundle["bundle_status"],
        "stage_results": {
            record["lifecycle_stage"]: {
                "status": record["status"],
                "execution_verdict": record["execution_verdict"],
                "exit_status": record["exit_status"],
            }
            for record in bundle["records"]
        },
        "coverage_P": bundle["coverage_claims"]["Coverage_P"],
        "coverage_ref": bundle["coverage_claims"]["Coverage_ref"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    if bundle["bundle_status"] != "complete":
        return 2
    if (
        next(record for record in bundle["records"] if record["lifecycle_stage"] == "ci_test")[
            "execution_verdict"
        ]
        != "passed"
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
