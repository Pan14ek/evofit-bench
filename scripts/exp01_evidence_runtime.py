"""Bounded local application and Prometheus evidence collection for EXP-01."""

import csv
import hashlib
import ipaddress
import json
import math
import re
import shutil
import subprocess  # nosec B404
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

from scripts.exp01_evidence_contract import write_artifact
from scripts.prometheus_snapshot import parse_snapshot, value
from scripts.runtime_validation import validate_process_continuity, validate_runtime_samples

ROOT = Path(__file__).resolve().parents[1]
BUSINESS_REQUESTS = 6
MAX_ACTIVITY_SECONDS = 30.0
MAX_SAMPLE_INTERVAL_SECONDS = 5.0
MAX_SNAPSHOT_AGE_SECONDS = 60.0
SOURCE_REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")
COMPOSE_CONTAINER_ID_PATTERN = re.compile(r"^[0-9a-f]{12,64}$")
DOCKER_OBJECT_ID_PATTERN = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")
COUNTER_LABELS = {
    "http_requests_total": {"method", "path", "traffic_class"},
    "http_responses_total": {"method", "path", "status_class", "traffic_class"},
    "business_operation_failures_total": {"operation"},
    "business_rule_rejections_total": {"operation", "reason"},
}


def _docker_json_rows(output: str) -> list[dict[str, Any]]:
    """Parse Compose JSON output without retaining fields beyond the caller's allowlist."""
    if not output.strip():
        return []
    try:
        parsed: Any = json.loads(output)
    except json.JSONDecodeError:
        try:
            parsed = [json.loads(line) for line in output.splitlines() if line.strip()]
        except json.JSONDecodeError as error:
            raise ValueError("Docker Compose returned malformed JSON") from error
    rows = parsed if isinstance(parsed, list) else [parsed]
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("Docker Compose JSON rows must be objects")
    return rows


def _local_host_binding(host_ip: str) -> bool:
    """Accept Docker host bindings that can serve the validated loopback request."""
    if not host_ip:
        return True
    try:
        address = ipaddress.ip_address(host_ip)
        return address.is_loopback or address.is_unspecified
    except ValueError:
        return False


def _docker_target_observation(base_url: str) -> dict[str, Any]:
    """Read Compose/container/image identity and map the endpoint's published port."""
    parsed_url = urlsplit(base_url)
    endpoint_port = parsed_url.port or 80
    docker_path = shutil.which("docker")
    empty_observation = {
        "observation_status": "unavailable",
        "endpoint_port": endpoint_port,
        "app_container_count": 0,
        "endpoint_candidate_count": 0,
        "endpoint_container": None,
        "reason": "Docker target identity was unavailable.",
    }
    if docker_path is None:
        return {**empty_observation, "reason": "Docker is not available on PATH."}

    try:
        compose_result = subprocess.run(  # noqa: S603  # nosec B603 -- fixed read-only command, no shell
            [docker_path, "compose", "ps", "--format", "json"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=8,
        )
        if compose_result.returncode != 0:
            return {**empty_observation, "reason": "Docker Compose target listing failed."}
        rows = _docker_json_rows(compose_result.stdout)
    except (OSError, subprocess.SubprocessError, ValueError):
        return {**empty_observation, "reason": "Docker Compose target listing was unusable."}

    app_rows = [
        row
        for row in rows
        if (row.get("Service") or row.get("service")) == "app"
        and str(row.get("State") or row.get("state") or "").lower() == "running"
    ]
    targets: list[dict[str, Any]] = []
    container_format = "{{.Id}}\n{{.Image}}\n{{.Config.Image}}\n{{json .NetworkSettings.Ports}}"
    image_format = '{{.Id}}\n{{index .Config.Labels "org.opencontainers.image.revision"}}'
    for row in app_rows[:8]:
        short_id = row.get("ID") or row.get("Id") or row.get("id")
        if not isinstance(short_id, str) or not COMPOSE_CONTAINER_ID_PATTERN.fullmatch(short_id):
            continue
        try:
            inspect_result = subprocess.run(  # noqa: S603  # nosec B603 -- fixed allowlisted Docker format, no shell
                [docker_path, "inspect", "--format", container_format, short_id],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
                timeout=8,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if inspect_result.returncode != 0:
            continue
        lines = inspect_result.stdout.rstrip("\n").splitlines()
        if len(lines) < 4:
            continue
        container_id, image_id, image_reference, port_json = lines[:4]
        if not re.fullmatch(r"[0-9a-f]{64}", container_id):
            continue
        if not DOCKER_OBJECT_ID_PATTERN.fullmatch(image_id):
            continue
        image_id = image_id if image_id.startswith("sha256:") else f"sha256:{image_id}"
        try:
            port_map = json.loads(port_json)
        except json.JSONDecodeError:
            continue
        if not isinstance(port_map, dict):
            continue

        published_ports: list[dict[str, Any]] = []
        for container_port, bindings in port_map.items():
            port_and_protocol = container_port.split("/", maxsplit=1)
            if len(port_and_protocol) != 2 or port_and_protocol[1] != "tcp":
                continue
            if not port_and_protocol[0].isdigit() or not isinstance(bindings, list):
                continue
            for binding in bindings:
                if not isinstance(binding, dict):
                    continue
                host_ip = binding.get("HostIp")
                host_port = binding.get("HostPort")
                if not isinstance(host_ip, str) or not isinstance(host_port, str):
                    continue
                if not host_port.isdigit():
                    continue
                published_ports.append(
                    {
                        "host_ip": host_ip,
                        "published_port": int(host_port),
                        "target_port": int(port_and_protocol[0]),
                        "protocol": "tcp",
                    }
                )

        revision_label: str | None = None
        try:
            image_result = subprocess.run(  # noqa: S603  # nosec B603 -- read-only allowlisted image metadata, no shell
                [docker_path, "image", "inspect", "--format", image_format, image_id],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
                timeout=8,
            )
            image_lines = image_result.stdout.rstrip("\n").splitlines()
            if (
                image_result.returncode == 0
                and len(image_lines) >= 2
                and image_lines[0] == image_id
                and SOURCE_REVISION_PATTERN.fullmatch(image_lines[1])
            ):
                revision_label = image_lines[1]
        except (OSError, subprocess.SubprocessError):
            pass

        targets.append(
            {
                "service": "app",
                "state": "running",
                "container_id": container_id,
                "image_id": image_id,
                "image_reference": image_reference
                if image_reference and image_reference != "<no value>"
                else None,
                "published_ports": sorted(
                    published_ports,
                    key=lambda item: (
                        item["published_port"],
                        item["target_port"],
                        item["host_ip"],
                    ),
                ),
                "observed_application_revision": revision_label,
            }
        )

    matching_targets = [
        target
        for target in targets
        if any(
            port["published_port"] == endpoint_port and _local_host_binding(port["host_ip"])
            for port in target["published_ports"]
        )
    ]
    return {
        "observation_status": "available",
        "endpoint_port": endpoint_port,
        "app_container_count": len(app_rows),
        "endpoint_candidate_count": len(matching_targets),
        "endpoint_container": matching_targets[0] if len(matching_targets) == 1 else None,
        "reason": None
        if len(matching_targets) == 1
        else "No unique running Compose app container publishes the requested loopback port.",
    }


def assess_runtime_source_binding(
    collector_source_revision: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    endpoint_port: int,
) -> dict[str, Any]:
    """Classify target identity without treating local HEAD or OCI labels as authority."""
    if not SOURCE_REVISION_PATTERN.fullmatch(collector_source_revision):
        raise ValueError("collector source revision must be a full lowercase Git SHA")
    before = before or {}
    after = after or {}
    before_target = before.get("endpoint_container")
    after_target = after.get("endpoint_container")
    identity_stable: bool | None = None
    if isinstance(before_target, dict) and isinstance(after_target, dict):
        identity_stable = before_target == after_target

    if identity_stable is False:
        endpoint_status = "mismatch"
    elif (
        identity_stable is True
        and isinstance(after_target, dict)
        and after_target.get("service") == "app"
        and after_target.get("state") == "running"
        and isinstance(after_target.get("container_id"), str)
        and isinstance(after_target.get("image_id"), str)
        and after.get("endpoint_port") == endpoint_port
        and any(
            port.get("published_port") == endpoint_port
            and _local_host_binding(str(port.get("host_ip", "")))
            for port in after_target.get("published_ports", [])
            if isinstance(port, dict)
        )
    ):
        endpoint_status = "verified"
    else:
        endpoint_status = "unverified"

    observed_revision = (
        after_target.get("observed_application_revision")
        if endpoint_status == "verified" and isinstance(after_target, dict)
        else None
    )
    if endpoint_status == "mismatch":
        status = "mismatch"
        reason = (
            "The endpoint resolved to different Docker container or image identities "
            "during collection."
        )
    elif endpoint_status == "verified" and observed_revision is not None:
        if observed_revision != collector_source_revision:
            status = "mismatch"
            reason = (
                "The mapped image OCI revision label differs from the collector revision; "
                "the label is an unauthenticated claim."
            )
        else:
            status = "unverified"
            reason = (
                "The endpoint stayed bound to one Docker app container, but a matching OCI "
                "revision label is not authoritative source-to-image provenance."
            )
    elif endpoint_status == "verified":
        status = "unverified"
        reason = (
            "The endpoint stayed bound to one Docker app container, but no application "
            "revision label or authoritative source-to-image provenance was available."
        )
    else:
        status = "unverified"
        reason = "The endpoint could not be bound to one stable Docker app container."

    return {
        "status": status,
        "collector_source_revision": collector_source_revision,
        "observed_application_revision": observed_revision,
        "revision_observation_source": "oci_image_label" if observed_revision else "none",
        "revision_authority": "unverified",
        "endpoint_binding_status": endpoint_status,
        "endpoint_port": endpoint_port,
        "container_id": after_target.get("container_id")
        if isinstance(after_target, dict)
        else None,
        "image_id": after_target.get("image_id") if isinstance(after_target, dict) else None,
        "image_reference": after_target.get("image_reference")
        if isinstance(after_target, dict)
        else None,
        "identity_stable": identity_stable,
        "reason": reason,
    }


def _executable_sha256(executable: str) -> str | None:
    path = Path(executable)
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""
    return datetime.now(UTC)


def validate_local_base_url(base_url: str) -> str:
    """Allow bounded HTTP access to loopback only, with no credentials or URL payload."""
    try:
        parsed = urlsplit(base_url)
        port = parsed.port
    except ValueError as error:
        raise ValueError("base-url must be a valid loopback HTTP URL") from error
    hostname = parsed.hostname
    if not hostname or parsed.scheme != "http" or parsed.username or parsed.password:
        raise ValueError("base-url must be an unauthenticated loopback HTTP URL")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError("base-url must not include a path, query, or fragment")
    try:
        is_loopback = hostname.lower() == "localhost" or ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        is_loopback = False
    if not is_loopback:
        raise ValueError("base-url host must be localhost or a loopback IP address")
    netloc = f"[{hostname}]" if ":" in hostname else hostname
    if port is not None:
        netloc = f"{netloc}:{port}"
    return f"http://{netloc}"


def _finite_issues(snapshot: dict[str, list[tuple[dict[str, str], float]]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for metric, rows in snapshot.items():
        for labels, sample in rows:
            if not math.isfinite(sample):
                issues.append({"metric": metric, "labels": labels, "value": repr(sample)})
    return issues


def _label_issues(snapshot: dict[str, list[tuple[dict[str, str], float]]]) -> list[str]:
    issues: list[str] = []
    for metric, rows in snapshot.items():
        seen: set[tuple[tuple[str, str], ...]] = set()
        for labels, _ in rows:
            label_key = tuple(sorted(labels.items()))
            if label_key in seen:
                issues.append(f"{metric} contains duplicate label dimensions")
            seen.add(label_key)
    for metric, required in COUNTER_LABELS.items():
        for labels, _ in snapshot.get(metric, []):
            missing = sorted(required - labels.keys())
            if missing:
                issues.append(f"{metric} sample is missing required labels: {', '.join(missing)}")
    for metric in (
        "http_request_duration_seconds_bucket",
        "http_request_duration_seconds_count",
        "http_request_duration_seconds_sum",
    ):
        for labels, _ in snapshot.get(metric, []):
            required = {"method", "path", "traffic_class"}
            if metric.endswith("_bucket"):
                required.add("le")
            missing = sorted(required - labels.keys())
            if missing:
                issues.append(f"{metric} sample is missing required labels: {', '.join(missing)}")
    return issues


def _counter_interval(
    before: dict[str, list[tuple[dict[str, str], float]]],
    after: dict[str, list[tuple[dict[str, str], float]]],
    metric: str,
    *,
    filters: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Calculate deltas by exact label set and reject resets or disappearing series."""
    filters = filters or {}
    rows_before = before.get(metric, [])
    rows_after = after.get(metric, [])
    before_series = {
        tuple(sorted(labels.items())): sample
        for labels, sample in rows_before
        if all(labels.get(key) == expected for key, expected in filters.items())
    }
    after_series = {
        tuple(sorted(labels.items())): sample
        for labels, sample in rows_after
        if all(labels.get(key) == expected for key, expected in filters.items())
    }
    if not after_series:
        if before_series:
            return {
                "status": "invalid",
                "value": None,
                "reason": "counter series disappeared between snapshots",
                "counter_reset": True,
            }
        return {"status": "missing", "value": None, "reason": "no matching metric samples"}

    missing_after = before_series.keys() - after_series.keys()
    if missing_after:
        return {
            "status": "invalid",
            "value": None,
            "reason": "one or more counter series disappeared between snapshots",
            "counter_reset": True,
        }

    deltas: list[float] = []
    for labels, after_value in after_series.items():
        before_value = before_series.get(labels, 0.0)
        if after_value < before_value:
            return {
                "status": "invalid",
                "value": None,
                "reason": "counter decreased between snapshots",
                "counter_reset": True,
                "labels": dict(labels),
                "before": before_value,
                "after": after_value,
            }
        deltas.append(after_value - before_value)
    return {
        "status": "available",
        "value": sum(deltas),
        "series_count": len(after_series),
        "new_series_assumed_zero": any(labels not in before_series for labels in after_series),
    }


def _histogram_interval(
    before: dict[str, list[tuple[dict[str, str], float]]],
    after: dict[str, list[tuple[dict[str, str], float]]],
) -> dict[str, Any]:
    metric_names = (
        "http_request_duration_seconds_bucket",
        "http_request_duration_seconds_count",
        "http_request_duration_seconds_sum",
    )
    series: list[dict[str, Any]] = []
    errors: list[str] = []
    for metric in metric_names:
        previous = {
            tuple(sorted(labels.items())): sample for labels, sample in before.get(metric, [])
        }
        current = {
            tuple(sorted(labels.items())): sample for labels, sample in after.get(metric, [])
        }
        if previous.keys() - current.keys():
            errors.append(f"{metric} series disappeared between snapshots")
        for labels, after_value in current.items():
            before_value = previous.get(labels, 0.0)
            reset = after_value < before_value
            if reset:
                errors.append(f"{metric} counter decreased between snapshots")
            series.append(
                {
                    "metric": metric,
                    "labels": dict(labels),
                    "before": before_value,
                    "after": after_value,
                    "delta": None if reset else after_value - before_value,
                    "counter_reset": reset,
                }
            )
    if not series:
        return {"status": "missing", "series": [], "reason": "no histogram samples"}
    if errors:
        return {"status": "invalid", "series": series, "errors": errors}
    return {
        "status": "available",
        "series": series,
        "quantiles": None,
        "method": "Exact cumulative bucket/count/sum samples and same-series interval deltas.",
        "limitations": [
            "No p50, p95, or p99 is calculated from bucket-only data.",
            "Histogram bucket values remain cumulative counts, not latency quantiles.",
        ],
    }


def validate_snapshot_interval(
    before_time: str, after_time: str, started_at: str, ended_at: str
) -> None:
    """Require ordered, in-run scrape timestamps and reject stale end snapshots."""
    before = datetime.fromisoformat(before_time.replace("Z", "+00:00"))
    after = datetime.fromisoformat(after_time.replace("Z", "+00:00"))
    started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    ended = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
    if any(value_time.tzinfo is None for value_time in (before, after, started, ended)):
        raise ValueError("metrics snapshot timestamps must include a timezone")
    if not started <= before <= after <= ended:
        raise ValueError("metrics snapshot timestamps are stale or outside the collection interval")
    if (ended - after).total_seconds() > MAX_SNAPSHOT_AGE_SECONDS:
        raise ValueError("after metrics snapshot is stale")


def _validate_samples_inside_interval(path: Path, before_time: str, after_time: str) -> None:
    """Ensure every recorded process sample falls between the raw snapshots."""
    before = datetime.fromisoformat(before_time.replace("Z", "+00:00"))
    after = datetime.fromisoformat(after_time.replace("Z", "+00:00"))
    with path.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    for row in rows:
        sample_time = datetime.fromisoformat(row["timestamp_utc"])
        if not before <= sample_time <= after:
            raise ValueError("runtime sample timestamp is outside the snapshot interval")


def _base_record(
    *,
    run_id: str,
    source_revision: str,
    started: datetime,
    stage: str = "runtime",
) -> dict[str, Any]:
    return {
        "record_id": "exp01-runtime-v1",
        "run_id": run_id,
        "lifecycle_stage": stage,
        "status": "missing",
        "evaluator_name": "prometheus-runtime-collector",
        "evaluator_version": None,
        "executable": sys.executable,
        "executable_sha256": _executable_sha256(sys.executable),
        "command": [],
        "started_at_utc": started.isoformat(),
        "ended_at_utc": started.isoformat(),
        "duration_seconds": 0.0,
        "exit_status": None,
        "execution_verdict": "not_run",
        "scope": "Local A0.1 application process and bounded HTTP activity on loopback.",
        "source_revision": source_revision,
        "source_binding": None,
        "configuration_artifact": None,
        "input_artifacts": [],
        "raw_output_artifacts": [],
        "measurements": {},
        "errors": [],
        "limitations": [],
    }


def collect_runtime_evidence(
    run_dir: Path,
    run_id: str,
    base_url: str,
    source_revision: str,
    input_artifacts: list[dict[str, Any]],
    *,
    duration_seconds: float = 3.0,
    interval_seconds: float = 0.5,
) -> dict[str, Any]:
    """Scrape and preserve live metrics around bounded read-only local requests."""
    base_url = validate_local_base_url(base_url)
    if not 0 < duration_seconds <= MAX_ACTIVITY_SECONDS:
        raise ValueError(
            f"runtime duration must be greater than zero and at most {MAX_ACTIVITY_SECONDS}"
        )
    if not 0 < interval_seconds <= MAX_SAMPLE_INTERVAL_SECONDS:
        raise ValueError(
            f"sample interval must be greater than zero and at most {MAX_SAMPLE_INTERVAL_SECONDS}"
        )

    started = utc_now()
    record = _base_record(run_id=run_id, source_revision=source_revision, started=started)
    endpoint_port = urlsplit(base_url).port or 80
    record["source_binding"] = assess_runtime_source_binding(
        source_revision, None, None, endpoint_port
    )
    record["input_artifacts"] = input_artifacts
    record["evaluator_version"] = _distribution_version("prometheus-client")
    record["command"] = [
        sys.executable,
        "-m",
        "scripts.sample_runtime_metrics",
        "--url",
        base_url,
        "--interval-seconds",
        str(interval_seconds),
        "--duration-seconds",
        str(duration_seconds),
    ]
    metrics_url = f"{base_url}/metrics"
    readiness: dict[str, Any] = {"status": None, "captured_at_utc": None}
    before_text: str | None = None
    after_text: str | None = None
    before_time: str | None = None
    after_time: str | None = None
    activity: list[dict[str, Any]] = []
    activity_findings: list[str] = []
    sampler_stdout = ""
    sampler_stderr = ""
    sampler_return_code: int | None = None
    sampler_path = run_dir / ".runtime_metrics.tmp.csv"

    with httpx.Client(timeout=httpx.Timeout(3.0), trust_env=False) as client:
        try:
            ready_response = client.get(f"{base_url}/health/ready")
            readiness = {
                "status": ready_response.status_code,
                "captured_at_utc": utc_now().isoformat(),
            }
            readiness_ref = write_artifact(
                run_dir,
                "raw/readiness.json",
                json.dumps(
                    {"status_code": ready_response.status_code, "body": ready_response.text},
                    indent=2,
                    sort_keys=True,
                    allow_nan=False,
                ).encode("utf-8"),
                media_type="application/json",
                role="readiness",
            )
            record["raw_output_artifacts"].append(readiness_ref)
        except httpx.HTTPError as error:
            readiness["error"] = f"readiness request failed: {type(error).__name__}"
            record["errors"].append(str(readiness["error"]))

        if readiness.get("status") != 200:
            record["measurements"] = {
                "readiness": readiness,
                "activity_requests": [],
                "runtime_sampling": {"status": "not_run"},
                "metrics": {},
            }
            record["errors"].append(
                "runtime collection did not run because readiness was unavailable"
            )
            record["execution_verdict"] = "not_run"
            record["limitations"].append(
                "The application readiness endpoint did not establish a usable local runtime."
            )
            record["limitations"].append(
                "Runtime application source binding is unverified because the endpoint was not "
                "collected and no authoritative source-to-image provenance was available."
            )
            _finish_record(record, started)
            return record

        target_identity_before = _docker_target_observation(base_url)
        before_response, before_time, before_error = _fetch_metrics(client, metrics_url)
        if before_error:
            record["errors"].append(before_error)
        if before_response is not None:
            before_text = before_response
            record["raw_output_artifacts"].append(
                write_artifact(
                    run_dir,
                    "raw/metrics_before.txt",
                    before_response.encode("utf-8"),
                    media_type="text/plain",
                    role="raw_metrics",
                )
            )

        sampler_command = [
            sys.executable,
            "-m",
            "scripts.sample_runtime_metrics",
            "--url",
            base_url,
            "--output",
            str(sampler_path),
            "--interval-seconds",
            str(interval_seconds),
            "--duration-seconds",
            str(duration_seconds),
        ]
        record["command"] = sampler_command
        sampler: subprocess.Popen[str] | None = None
        try:
            sampler = subprocess.Popen(  # noqa: S603  # nosec B603 -- fixed local sampler module and bounded arguments
                sampler_command,
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for index in range(BUSINESS_REQUESTS):
                path = "/health/live" if index == 0 else "/api/v1/tasks?limit=1"
                request_started = utc_now()
                try:
                    response = client.get(f"{base_url}{path}")
                    activity.append(
                        {
                            "path": path,
                            "status_code": response.status_code,
                            "started_at_utc": request_started.isoformat(),
                            "ended_at_utc": utc_now().isoformat(),
                        }
                    )
                    if response.status_code >= 400:
                        activity_findings.append(
                            f"bounded read-only request {path} returned HTTP {response.status_code}"
                        )
                except httpx.HTTPError as error:
                    activity.append(
                        {
                            "path": path,
                            "status_code": None,
                            "started_at_utc": request_started.isoformat(),
                            "ended_at_utc": utc_now().isoformat(),
                            "error": type(error).__name__,
                        }
                    )
                    record["errors"].append(f"bounded request failed: {type(error).__name__}")
            try:
                sampler_stdout, sampler_stderr = sampler.communicate(timeout=duration_seconds + 10)
            except subprocess.TimeoutExpired:
                sampler.terminate()
                sampler_stdout, sampler_stderr = sampler.communicate(timeout=5)
                record["errors"].append("runtime sampler exceeded its bounded duration")
            sampler_return_code = sampler.returncode
            record["exit_status"] = sampler_return_code
        except OSError as error:
            record["errors"].append(f"runtime sampler could not start: {type(error).__name__}")
            if sampler is not None:
                sampler.terminate()
                sampler_stdout, sampler_stderr = sampler.communicate(timeout=5)
                sampler_return_code = sampler.returncode
        finally:
            if sampler is not None and sampler.poll() is None:
                sampler.terminate()
                sampler_stdout, sampler_stderr = sampler.communicate(timeout=5)
                sampler_return_code = sampler.returncode

        record["raw_output_artifacts"].extend(
            [
                write_artifact(
                    run_dir,
                    "raw/runtime_sampler.stdout.txt",
                    sampler_stdout.encode("utf-8"),
                    media_type="text/plain",
                    role="stdout",
                ),
                write_artifact(
                    run_dir,
                    "raw/runtime_sampler.stderr.txt",
                    sampler_stderr.encode("utf-8"),
                    media_type="text/plain",
                    role="stderr",
                ),
            ]
        )
        if sampler_path.is_file():
            sample_artifact_path = (
                "raw/runtime_metrics.csv"
                if sampler_return_code == 0
                else "raw/runtime_metrics.partial.csv"
            )
            record["raw_output_artifacts"].append(
                write_artifact(
                    run_dir,
                    sample_artifact_path,
                    sampler_path.read_bytes(),
                    media_type="text/csv",
                    role="runtime_samples"
                    if sampler_return_code == 0
                    else "runtime_samples_partial",
                )
            )
            sampler_path.unlink()
        elif sampler_return_code is not None:
            record["errors"].append(f"runtime sampler exited with code {sampler_return_code}")

        after_response, after_time, after_error = _fetch_metrics(client, metrics_url)
        if after_error:
            record["errors"].append(after_error)
        if after_response is not None:
            after_text = after_response
            record["raw_output_artifacts"].append(
                write_artifact(
                    run_dir,
                    "raw/metrics_after.txt",
                    after_response.encode("utf-8"),
                    media_type="text/plain",
                    role="raw_metrics",
                )
            )
        target_identity_after = _docker_target_observation(base_url)
        identity_observation = {
            "before_runtime_collection": target_identity_before,
            "after_runtime_collection": target_identity_after,
        }
        record["raw_output_artifacts"].append(
            write_artifact(
                run_dir,
                "raw/runtime_target_identity.json",
                json.dumps(
                    identity_observation,
                    indent=2,
                    sort_keys=True,
                    allow_nan=False,
                ).encode("utf-8"),
                media_type="application/json",
                role="target_identity_observation",
            )
        )
        record["source_binding"] = assess_runtime_source_binding(
            source_revision,
            target_identity_before,
            target_identity_after,
            endpoint_port,
        )

    metrics_result: dict[str, Any] = {}
    invalid_values: list[dict[str, Any]] = []
    label_errors: list[str] = []
    process_start_time: float | None = None
    sample_summary: dict[str, int] | None = None
    runtime_sample_status = "missing"
    try:
        if before_text is None or after_text is None:
            raise ValueError("one or both raw metrics snapshots are unavailable")
        before_snapshot = parse_snapshot(before_text)
        after_snapshot = parse_snapshot(after_text)
        invalid_values = _finite_issues(before_snapshot) + _finite_issues(after_snapshot)
        label_errors = _label_issues(before_snapshot) + _label_issues(after_snapshot)
        if invalid_values:
            raise ValueError("Prometheus snapshot contains non-finite sample values")
        if label_errors:
            raise ValueError("Prometheus samples have incompatible label dimensions")
        process_start_time = validate_process_continuity(before_text, after_text)
        if before_time is None or after_time is None:
            raise ValueError("metrics snapshot capture times are unavailable")
        validate_snapshot_interval(
            before_time, after_time, started.isoformat(), utc_now().isoformat()
        )
        if sampler_return_code != 0 or not any(
            reference["role"] == "runtime_samples" for reference in record["raw_output_artifacts"]
        ):
            raise ValueError("valid runtime sample CSV is unavailable")
        sample_summary = validate_runtime_samples(
            run_dir / "raw/runtime_metrics.csv", duration_seconds, interval_seconds
        )
        runtime_sample_status = "available"
        for metric in (
            "process_cpu_seconds_total",
            "process_resident_memory_bytes",
            "process_virtual_memory_bytes",
        ):
            if metric == "process_virtual_memory_bytes":
                continue
            if value(after_snapshot, metric) is None:
                raise ValueError(f"required runtime metric is missing or ambiguous: {metric}")
        _validate_samples_inside_interval(
            run_dir / "raw/runtime_metrics.csv", before_time, after_time
        )

        request_delta = _counter_interval(
            before_snapshot,
            after_snapshot,
            "http_requests_total",
            filters={"traffic_class": "business"},
        )
        response_5xx_delta = _counter_interval(
            before_snapshot,
            after_snapshot,
            "http_responses_total",
            filters={"traffic_class": "business", "status_class": "5xx"},
        )
        failures_delta = _counter_interval(
            before_snapshot, after_snapshot, "business_operation_failures_total"
        )
        rejections_delta = _counter_interval(
            before_snapshot, after_snapshot, "business_rule_rejections_total"
        )
        histogram = _histogram_interval(before_snapshot, after_snapshot)
        counters = {
            "http_requests_total_business": request_delta,
            "http_responses_total_business_5xx": response_5xx_delta,
            "business_operation_failures_total": failures_delta,
            "business_rule_rejections_total": rejections_delta,
        }
        resets = [
            name
            for name, observation in counters.items()
            if observation.get("counter_reset") is True
        ]
        if histogram.get("status") == "invalid":
            resets.append("http_request_duration_seconds_histogram")
        if resets:
            raise ValueError(f"counter reset detected: {', '.join(resets)}")
        request_count = request_delta.get("value")
        five_xx_count = response_5xx_delta.get("value")
        cpu_delta = _gauge_delta(before_snapshot, after_snapshot, "process_cpu_seconds_total")
        if cpu_delta is None:
            raise ValueError("process CPU counter is missing, ambiguous, or decreased")
        five_xx_rate = (
            five_xx_count / request_count
            if five_xx_count is not None and request_count is not None and request_count > 0
            else None
        )
        metrics_result = {
            "counters": counters,
            "business_5xx_rate": {
                "status": "available" if five_xx_rate is not None else "missing",
                "value": five_xx_rate,
                "reason": None
                if five_xx_rate is not None
                else "5xx or business-request counter data is unavailable",
            },
            "histogram": histogram,
            "process": {
                "start_time_seconds": process_start_time,
                "cpu_seconds_delta": cpu_delta,
                "resident_memory_bytes_start": _first_sample(
                    run_dir / "raw/runtime_metrics.csv", "process_resident_memory_bytes", first=True
                ),
                "resident_memory_bytes_end": _first_sample(
                    run_dir / "raw/runtime_metrics.csv",
                    "process_resident_memory_bytes",
                    first=False,
                ),
                "resident_memory_bytes_max": sample_summary["rss_max_bytes"]
                if sample_summary
                else None,
                "sample_count": sample_summary["sample_count"] if sample_summary else None,
                "sampling_interval_seconds": interval_seconds,
                "expected_sample_count": math.ceil(duration_seconds / interval_seconds),
                "sample_completeness_fraction": min(
                    1.0,
                    sample_summary["sample_count"] / math.ceil(duration_seconds / interval_seconds),
                )
                if sample_summary
                else None,
            },
            "snapshot_capture_times": {"before": before_time, "after": after_time},
            "activity_http_statuses": [item["status_code"] for item in activity],
        }
        if request_delta["status"] != "available":
            raise ValueError("business HTTP request counter evidence is unavailable")
        if any(item["status_code"] is None for item in activity):
            raise ValueError("one or more bounded runtime activity requests failed to return HTTP")
    except (ValueError, RuntimeError, OSError) as error:
        record["errors"].append(str(error))
        message = str(error).lower()
        invalid_evidence = (
            bool(invalid_values)
            or bool(label_errors)
            or any(
                phrase in message
                for phrase in (
                    "decreased",
                    "disappeared",
                    "counter reset",
                    "process changed",
                    "outside the snapshot interval",
                    "stale",
                    "row ",
                    "minimum is",
                )
            )
        )
        runtime_sample_status = "invalid" if invalid_evidence else "missing"

    record["measurements"] = {
        "readiness": readiness,
        "activity_requests": activity,
        "activity_findings": activity_findings,
        "runtime_sampling": {
            "status": runtime_sample_status,
            "duration_seconds": duration_seconds,
            "interval_seconds": interval_seconds,
            "sampler_exit_status": sampler_return_code,
            "sample_count": sample_summary["sample_count"] if sample_summary else None,
            "sample_completeness_floor": 0.9,
        },
        "invalid_metric_values": invalid_values,
        "label_compatibility_errors": label_errors,
        "metrics": metrics_result,
    }
    optional_missing = [
        name
        for name, observation in metrics_result.get("counters", {}).items()
        if observation.get("status") == "missing"
    ]
    if optional_missing:
        record["limitations"].append(
            "Some counters have no usable series in this interval: " + ", ".join(optional_missing)
        )
    if metrics_result.get("histogram", {}).get("status") == "missing":
        record["limitations"].append(
            "No latency histogram samples were present in the captured interval."
        )
    record["limitations"].append(
        "Prometheus exposition supplied scrape-time snapshots; no independent scrape timestamp "
        "or cache-age proof was available."
    )
    record["limitations"].append(
        "Histogram bucket evidence is preserved; p50, p95, and p99 are not asserted."
    )
    record["limitations"].append(
        "Runtime source revision remains unverified without authoritative source-to-image "
        "provenance; Docker identity and OCI labels are execution-context observations only."
    )
    if record["source_binding"]["status"] == "mismatch":
        record["status"] = "invalid"
        record["execution_verdict"] = "no_usable_evidence"
        record["errors"].append(
            "runtime source binding mismatch: observed application identity is inconsistent "
            "with the collector source revision"
        )
    elif runtime_sample_status == "available" and record["evaluator_version"] is None:
        record["status"] = "inconclusive"
        record["execution_verdict"] = "no_usable_evidence"
        record["errors"].append("prometheus-client version could not be established")
    elif runtime_sample_status == "available" and not record["errors"]:
        record["status"] = "available"
        record["execution_verdict"] = "inconclusive" if activity_findings else "passed"
    elif runtime_sample_status == "invalid":
        record["status"] = "invalid"
        record["execution_verdict"] = "inconclusive"
    else:
        record["status"] = "inconclusive"
        record["execution_verdict"] = "inconclusive"
    _finish_record(record, started)
    return record


def _fetch_metrics(
    client: httpx.Client, metrics_url: str
) -> tuple[str | None, str | None, str | None]:
    captured = utc_now()
    try:
        response = client.get(metrics_url)
        response.raise_for_status()
        return response.content.decode("utf-8"), utc_now().isoformat(), None
    except (httpx.HTTPError, UnicodeDecodeError) as error:
        return None, captured.isoformat(), f"metrics snapshot failed: {type(error).__name__}"


def _distribution_version(distribution: str) -> str | None:
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version(distribution)
    except PackageNotFoundError:
        return None


def _gauge_delta(
    before: dict[str, list[tuple[dict[str, str], float]]],
    after: dict[str, list[tuple[dict[str, str], float]]],
    metric: str,
) -> float | None:
    before_value = value(before, metric)
    after_value = value(after, metric)
    if before_value is None or after_value is None or after_value < before_value:
        return None
    return after_value - before_value


def _first_sample(path: Path, field: str, *, first: bool) -> int | None:
    if not path.is_file():
        return None
    with path.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    selected = rows[0] if first and rows else rows[-1] if rows else None
    if selected is None or not selected.get(field):
        return None
    value_number = float(selected[field])
    return int(value_number) if math.isfinite(value_number) else None


def _finish_record(record: dict[str, Any], started: datetime) -> None:
    ended = utc_now()
    record["ended_at_utc"] = ended.isoformat()
    record["duration_seconds"] = max(0.0, (ended - started).total_seconds())
