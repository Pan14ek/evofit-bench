"""Contract and adapter tests for the EXP-01 DEVELOPMENT evidence pipeline."""

import csv
import json
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from scripts import exp01_evidence
from scripts import exp01_evidence_contract as contract
from scripts import exp01_evidence_runtime as runtime
from scripts.prometheus_snapshot import parse_snapshot

SOURCE_SHA = "a" * 40


def _source_binding(source_revision: str) -> dict[str, Any]:
    return {
        "status": "unverified",
        "collector_source_revision": source_revision,
        "observed_application_revision": None,
        "revision_observation_source": "none",
        "revision_authority": "unverified",
        "endpoint_binding_status": "unverified",
        "endpoint_port": 8000,
        "container_id": None,
        "image_id": None,
        "image_reference": None,
        "identity_stable": None,
        "reason": "No authoritative target source identity is available.",
    }


def _target_observation(application_revision: str | None) -> dict[str, Any]:
    return {
        "observation_status": "available",
        "endpoint_port": 8000,
        "app_container_count": 1,
        "endpoint_candidate_count": 1,
        "endpoint_container": {
            "service": "app",
            "state": "running",
            "container_id": "1" * 64,
            "image_id": f"sha256:{'2' * 64}",
            "image_reference": "evofit-bench-app:latest",
            "published_ports": [
                {
                    "host_ip": "127.0.0.1",
                    "published_port": 8000,
                    "target_port": 8000,
                    "protocol": "tcp",
                }
            ],
            "observed_application_revision": application_revision,
        },
        "reason": None,
    }


def _write_input(run_dir: Path, name: str, content: bytes) -> dict[str, Any]:
    return contract.write_artifact(
        run_dir,
        f"inputs/{name}",
        content,
        media_type="text/plain",
        role="source_or_configuration",
        source_path=f"repo/{name}",
    )


def _valid_record(
    run_dir: Path,
    stage: str,
    source_revision: str,
    *,
    status: str = "available",
    configuration: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raw = contract.write_artifact(
        run_dir,
        f"raw/{stage}.txt",
        f"raw {stage}\n".encode(),
        media_type="text/plain",
        role="stdout",
    )
    start = datetime(2026, 10, 18, tzinfo=UTC)
    return {
        "record_id": f"test-{stage}",
        "run_id": run_dir.name,
        "lifecycle_stage": stage,
        "status": status,
        "evaluator_name": f"test-{stage}",
        "evaluator_version": "1.2.3",
        "executable": "/usr/bin/example",
        "executable_sha256": None,
        "command": ["example", "--fixed"],
        "started_at_utc": start.isoformat(),
        "ended_at_utc": (start + timedelta(seconds=1)).isoformat(),
        "duration_seconds": 1.0,
        "exit_status": 0,
        "execution_verdict": "passed" if stage == "ci_test" else "inconclusive",
        "scope": f"controlled {stage} fixture",
        "source_revision": source_revision,
        "source_binding": _source_binding(source_revision) if stage == "runtime" else None,
        "configuration_artifact": configuration,
        "input_artifacts": [],
        "raw_output_artifacts": [raw],
        "measurements": {},
        "errors": [],
        "limitations": [],
    }


def _valid_bundle(run_dir: Path) -> dict[str, Any]:
    run_dir.mkdir()
    manifest = _write_input(run_dir, "architecture.yaml", b"state: A0_1_CAPABILITY_MODULES\n")
    acceptance = _write_input(run_dir, "acceptance.toml", b"contracts = []\n")
    fitness = _write_input(run_dir, "fitness.yaml", b"architecture_state: A0_MONOLITH\n")
    schema = _write_input(run_dir, "evidence.schema.json", b"{}\n")
    other = _write_input(run_dir, "compose.yml", b"services: {}\n")
    records = [
        _valid_record(run_dir, "ci_test", SOURCE_SHA, configuration=acceptance),
        _valid_record(run_dir, "deployment", SOURCE_SHA),
        _valid_record(run_dir, "runtime", SOURCE_SHA),
    ]
    return {
        "schema_version": "1.1.0",
        "run_id": run_dir.name,
        "bundle_status": "complete",
        "created_at_utc": datetime(2026, 10, 18, 0, 0, tzinfo=UTC).isoformat(),
        "source_revision": {"commit_sha": SOURCE_SHA, "git_dirty": False},
        "architecture": {"state": "A0_1_CAPABILITY_MODULES", "manifest_artifact": manifest},
        "fitness_configuration": {
            "status": "mismatch",
            "declared_architecture_state": "A0_MONOLITH",
            "configuration_version": "1",
            "configuration_artifact": fitness,
            "applicable_to_target": False,
            "reason": "Historical profile does not match A0.1.",
        },
        "execution_context": {
            "python_version": "3.12.1",
            "platform": "test platform",
            "base_url": "http://localhost:8000",
            "schema_artifact": schema,
        },
        "supported_stages": ["ci_test", "deployment", "runtime"],
        "input_artifacts": [manifest, acceptance, fitness, schema, other],
        "artifact_inventory": [],
        "records": records,
        "coverage_claims": {
            "Coverage_P": "not_assessed",
            "Coverage_ref": "not_established",
            "measured_results": "not_run",
        },
        "limitations": ["Fixture only; no coverage is established."],
    }


@pytest.mark.parametrize("run_id", ["", ".", "..", "../escape", "a/b", "a\\b", "has space"])
def test_run_id_rejects_empty_or_path_unsafe_values(run_id: str) -> None:
    with pytest.raises(ValueError, match="run-id"):
        contract.validate_run_id(run_id)


@pytest.mark.parametrize("run_id", ["exp01-dev-smoke", "R1_20261018", "run.01"])
def test_run_id_accepts_safe_identifiers(run_id: str) -> None:
    assert contract.validate_run_id(run_id) == run_id


@pytest.mark.parametrize(
    "url",
    [
        "https://localhost:8000",
        "http://example.com:8000",
        "http://127.0.0.1:8000/api",
        "http://localhost:8000?token=secret",
        "http://user:pass@localhost:8000",
    ],
)
def test_runtime_url_rejects_remote_or_unbounded_endpoints(url: str) -> None:
    with pytest.raises(ValueError):
        runtime.validate_local_base_url(url)


@pytest.mark.parametrize("url", ["http://localhost:8000", "http://127.0.0.1", "http://[::1]:8000/"])
def test_runtime_url_accepts_loopback_only(url: str) -> None:
    assert runtime.validate_local_base_url(url).startswith("http://")


def test_runtime_missing_target_identity_stays_unverified() -> None:
    binding = runtime.assess_runtime_source_binding(SOURCE_SHA, None, None, 8000)

    assert binding["status"] == "unverified"
    assert binding["endpoint_binding_status"] == "unverified"
    assert binding["collector_source_revision"] == SOURCE_SHA
    assert binding["observed_application_revision"] is None
    assert binding["container_id"] is None


def test_runtime_mismatched_target_revision_is_not_bound_to_collector() -> None:
    target = _target_observation("b" * 40)

    binding = runtime.assess_runtime_source_binding(SOURCE_SHA, target, target, 8000)

    assert binding["endpoint_binding_status"] == "verified"
    assert binding["status"] == "mismatch"
    assert binding["collector_source_revision"] == SOURCE_SHA
    assert binding["observed_application_revision"] == "b" * 40
    assert binding["revision_authority"] == "unverified"


def test_runtime_changed_target_container_is_a_mismatch() -> None:
    before = _target_observation(SOURCE_SHA)
    after = _target_observation(SOURCE_SHA)
    after["endpoint_container"]["container_id"] = "3" * 64
    after["endpoint_container"]["image_id"] = f"sha256:{'4' * 64}"

    binding = runtime.assess_runtime_source_binding(SOURCE_SHA, before, after, 8000)

    assert binding["status"] == "mismatch"
    assert binding["endpoint_binding_status"] == "mismatch"
    assert binding["identity_stable"] is False
    assert binding["observed_application_revision"] is None


def test_matching_oci_revision_label_does_not_verify_source_binding() -> None:
    target = _target_observation(SOURCE_SHA)

    binding = runtime.assess_runtime_source_binding(SOURCE_SHA, target, target, 8000)

    assert binding["endpoint_binding_status"] == "verified"
    assert binding["status"] == "unverified"
    assert "not authoritative" in binding["reason"]


def test_missing_application_revision_label_stays_unverified_with_bound_endpoint() -> None:
    target = _target_observation(None)

    binding = runtime.assess_runtime_source_binding(SOURCE_SHA, target, target, 8000)

    assert binding["endpoint_binding_status"] == "verified"
    assert binding["status"] == "unverified"
    assert "no application revision label" in binding["reason"]


def test_docker_target_observation_binds_published_loopback_port(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    docker = tmp_path / "docker"
    docker.write_text("docker fixture", encoding="utf-8")
    container_id = "1" * 64
    image_id = f"sha256:{'2' * 64}"
    commands: list[list[str]] = []
    completed = [
        subprocess.CompletedProcess(
            ["docker"],
            0,
            json.dumps({"ID": container_id[:12], "Service": "app", "State": "running"}),
            "",
        ),
        subprocess.CompletedProcess(
            ["docker"],
            0,
            f"{container_id}\n{image_id}\nevofit-bench-app:latest\n"
            '{"8000/tcp":[{"HostIp":"127.0.0.1","HostPort":"8000"}]}\n',
            "",
        ),
        subprocess.CompletedProcess(["docker"], 0, f"{image_id}\n{SOURCE_SHA}\n", ""),
    ]

    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        assert kwargs["check"] is False
        assert kwargs["timeout"] <= 8
        assert "shell" not in kwargs
        return completed.pop(0)

    monkeypatch.setattr("scripts.exp01_evidence_runtime.shutil.which", lambda _: str(docker))
    monkeypatch.setattr("scripts.exp01_evidence_runtime.subprocess.run", run)

    observation = runtime._docker_target_observation("http://localhost:8000")

    assert observation["observation_status"] == "available"
    assert observation["endpoint_candidate_count"] == 1
    assert observation["endpoint_container"]["container_id"] == container_id
    assert observation["endpoint_container"]["image_id"] == image_id
    assert observation["endpoint_container"]["observed_application_revision"] == SOURCE_SHA
    assert commands[0][1:] == ["compose", "ps", "--format", "json"]
    assert commands[1][1:3] == ["inspect", "--format"]
    assert commands[2][1:4] == ["image", "inspect", "--format"]


def test_exact_digest_is_reproducible_and_a0_config_is_explicitly_mismatched(
    tmp_path: Path,
) -> None:
    ref = contract.copy_input_artifact(
        tmp_path, exp01_evidence.HISTORICAL_FITNESS_CONFIG, "configuration"
    )
    config = exp01_evidence._fitness_configuration_from_source(
        {exp01_evidence.HISTORICAL_FITNESS_CONFIG: ref}
    )
    original = (contract.ROOT / exp01_evidence.HISTORICAL_FITNESS_CONFIG).read_bytes()
    assert ref["sha256"] == contract.sha256_bytes(original)
    assert ref["sha256"] == contract.sha256_bytes(original)
    assert config["status"] == "mismatch"
    assert config["declared_architecture_state"] == "A0_MONOLITH"
    assert config["applicable_to_target"] is False


def test_import_linter_captures_real_exit_version_duration_and_raw_outputs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    executable = tmp_path / "python-runner"
    executable.write_text("Python runner fixture\n", encoding="utf-8")
    config = contract.write_artifact(
        run_dir,
        "inputs/importlinter.toml",
        b"[tool.importlinter]\nroot_packages=['app']\n",
        media_type="application/toml",
        role="configuration",
    )
    monkeypatch.setattr(exp01_evidence, "RUNNER_EXECUTABLE", str(executable))
    monkeypatch.setattr(exp01_evidence, "_distribution_version", lambda _: "2.3.0")
    monkeypatch.setattr(
        "scripts.exp01_evidence.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, "Import Linter has not found any broken contracts.\n", ""
        ),
    )

    result = exp01_evidence.run_architecture_acceptance(
        run_dir, run_dir.name, SOURCE_SHA, [config], config
    )

    assert result["status"] == "available"
    assert result["execution_verdict"] == "passed"
    assert result["exit_status"] == 0
    assert result["duration_seconds"] >= 0
    assert result["evaluator_version"] == "2.3.0"
    assert result["executable_sha256"] == contract.sha256_bytes(executable.read_bytes())
    assert {item["role"] for item in result["raw_output_artifacts"]} == {"stdout", "stderr"}
    assert all(
        contract.sha256_bytes((run_dir / item["path"]).read_bytes()) == item["sha256"]
        for item in result["raw_output_artifacts"]
    )


def test_import_linter_nonzero_rule_finding_is_preserved_as_violation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    executable = tmp_path / "python-runner"
    executable.write_text("Python runner fixture", encoding="utf-8")
    config = contract.write_artifact(
        run_dir,
        "inputs/importlinter.toml",
        b"config",
        media_type="application/toml",
        role="configuration",
    )
    monkeypatch.setattr(exp01_evidence, "RUNNER_EXECUTABLE", str(executable))
    monkeypatch.setattr(exp01_evidence, "_distribution_version", lambda _: "2.3.0")
    monkeypatch.setattr(
        "scripts.exp01_evidence.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 1, "Import Linter has found 1 broken contract.\n", ""
        ),
    )

    result = exp01_evidence.run_architecture_acceptance(
        run_dir, run_dir.name, SOURCE_SHA, [config], config
    )

    assert result["status"] == "available"
    assert result["execution_verdict"] == "violations_detected"
    assert result["exit_status"] == 1
    stdout = next(item for item in result["raw_output_artifacts"] if item["role"] == "stdout")
    assert b"found 1 broken contract" in (run_dir / stdout["path"]).read_bytes()


def test_import_linter_missing_executable_is_not_positive_evidence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    monkeypatch.setattr(exp01_evidence, "RUNNER_EXECUTABLE", str(tmp_path / "missing-python"))
    monkeypatch.setattr(exp01_evidence, "_distribution_version", lambda _: "2.3.0")
    config = {
        "path": "inputs/config.toml",
        "sha256": "b" * 64,
        "size_bytes": 0,
        "media_type": "application/toml",
        "role": "configuration",
        "source_path": None,
    }

    result = exp01_evidence.run_architecture_acceptance(
        run_dir, run_dir.name, SOURCE_SHA, [], config
    )

    assert result["status"] == "missing"
    assert result["execution_verdict"] == "execution_failure"
    assert result["exit_status"] is None
    assert result["raw_output_artifacts"] == []


def test_import_linter_nonzero_execution_error_is_not_relabelled_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    executable = tmp_path / "python-runner"
    executable.write_text("fixture", encoding="utf-8")
    config = {
        "path": "inputs/config.toml",
        "sha256": "b" * 64,
        "size_bytes": 0,
        "media_type": "application/toml",
        "role": "configuration",
        "source_path": None,
    }
    monkeypatch.setattr(exp01_evidence, "RUNNER_EXECUTABLE", str(executable))
    monkeypatch.setattr(exp01_evidence, "_distribution_version", lambda _: "2.3.0")
    monkeypatch.setattr(
        "scripts.exp01_evidence.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 2, "Traceback: config error", ""
        ),
    )

    result = exp01_evidence.run_architecture_acceptance(
        run_dir, run_dir.name, SOURCE_SHA, [], config
    )

    assert result["status"] == "invalid"
    assert result["execution_verdict"] == "execution_failure"
    assert result["exit_status"] == 2
    assert len(result["raw_output_artifacts"]) == 2


def test_compose_observation_keeps_process_and_semantics_unknown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    docker = tmp_path / "docker"
    docker.write_text("docker fixture", encoding="utf-8")
    compose = contract.write_artifact(
        run_dir,
        "inputs/docker-compose.yml",
        b"services: {app: {}, postgres: {}}\n",
        media_type="application/yaml",
        role="configuration",
        source_path="docker-compose.yml",
    )
    manifest = contract.write_artifact(
        run_dir,
        "inputs/architecture.yaml",
        b"state: A0_1_CAPABILITY_MODULES\n",
        media_type="application/yaml",
        role="source",
    )
    monkeypatch.setattr("scripts.exp01_evidence.shutil.which", lambda _: str(docker))
    completed = [
        subprocess.CompletedProcess(["docker"], 0, "2.30.0\n", ""),
        subprocess.CompletedProcess(
            ["docker"],
            0,
            '[{"Service":"app","Name":"exp01-app-1","State":"running","Image":"app"},'
            '{"Service":"postgres","Name":"exp01-db-1","State":"running","Image":"postgres"}]\n',
            "",
        ),
    ]
    monkeypatch.setattr(
        "scripts.exp01_evidence.subprocess.run", lambda *args, **kwargs: completed.pop(0)
    )
    architecture = yaml_state()

    result = exp01_evidence.collect_deployment_observation(
        run_dir, run_dir.name, SOURCE_SHA, [manifest, compose], architecture
    )

    assert result["status"] == "available"
    assert result["execution_verdict"] == "inconclusive"
    assert result["evaluator_version"] == "2.30.0"
    measurements = result["measurements"]
    assert measurements["running_container_counts_by_service"] == {"app": 1, "postgres": 1}
    assert measurements["state_comparisons"]["application_processes"]["status"] == "not_observed"
    assert measurements["state_comparisons"]["internal_communication"]["status"] == "not_observed"
    assert measurements["architecture_compliance"] == "not_established"
    assert len(result["raw_output_artifacts"]) == 3


def yaml_state() -> dict[str, Any]:
    return {
        "deployment": {
            "deployment_units": 1,
            "application_processes": 1,
            "database_instances": 1,
            "internal_communication": "synchronous_python_calls",
            "message_broker": "none",
        }
    }


def test_compose_observation_missing_docker_is_not_observed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    monkeypatch.setattr("scripts.exp01_evidence.shutil.which", lambda _: None)

    result = exp01_evidence.collect_deployment_observation(
        run_dir, run_dir.name, SOURCE_SHA, [], yaml_state()
    )

    assert result["status"] == "missing"
    assert result["execution_verdict"] == "not_observed"
    assert result["exit_status"] is None


def _snapshot(
    *,
    cpu: float,
    requests: float,
    responses: float,
    histogram_count: float,
    histogram_bucket: float,
) -> str:
    labels = 'method="GET",path="/api/v1/tasks",traffic_class="business"'
    return (
        f"process_start_time_seconds 100\n"
        f"process_cpu_seconds_total {cpu}\n"
        "process_resident_memory_bytes 2048\n"
        "process_virtual_memory_bytes 4096\n"
        f"http_requests_total{{{labels}}} {requests}\n"
        f'http_responses_total{{{labels},status_class="2xx"}} {responses}\n'
        f'http_request_duration_seconds_bucket{{{labels},le="0.5"}} {histogram_bucket}\n'
        f'http_request_duration_seconds_bucket{{{labels},le="+Inf"}} {histogram_count}\n'
        f"http_request_duration_seconds_count{{{labels}}} {histogram_count}\n"
        f"http_request_duration_seconds_sum{{{labels}}} {histogram_count / 10}\n"
    )


def test_realistic_prometheus_samples_preserve_business_dimensions_and_histogram_buckets() -> None:
    before = parse_snapshot(
        _snapshot(cpu=10, requests=0, responses=0, histogram_count=0, histogram_bucket=0)
    )
    after = parse_snapshot(
        _snapshot(cpu=12, requests=5, responses=5, histogram_count=5, histogram_bucket=3)
    )
    requests = runtime._counter_interval(
        before, after, "http_requests_total", filters={"traffic_class": "business"}
    )
    histogram = runtime._histogram_interval(before, after)

    assert requests["status"] == "available"
    assert requests["value"] == 5
    assert histogram["status"] == "available"
    assert histogram["quantiles"] is None
    assert any(item["labels"].get("traffic_class") == "business" for item in histogram["series"])


def test_nonfinite_values_and_incompatible_labels_are_reported() -> None:
    nonfinite = parse_snapshot("process_cpu_seconds_total NaN\n")
    incompatible = parse_snapshot('http_requests_total{method="GET",path="/x"} 1\n')
    duplicate_series = parse_snapshot(
        'http_requests_total{method="GET",path="/x",traffic_class="business"} 1\n'
        'http_requests_total{method="GET",path="/x",traffic_class="business"} 2\n'
    )

    assert runtime._finite_issues(nonfinite)[0]["value"] == "nan"
    assert runtime._label_issues(incompatible)
    assert runtime._label_issues(duplicate_series) == [
        "http_requests_total contains duplicate label dimensions"
    ]


def test_counter_decrease_and_process_restart_do_not_become_valid_rates() -> None:
    before = parse_snapshot(
        'http_requests_total{method="GET",path="/api/v1/tasks",traffic_class="business"} 10\n'
    )
    after = parse_snapshot(
        'http_requests_total{method="GET",path="/api/v1/tasks",traffic_class="business"} 2\n'
    )
    delta = runtime._counter_interval(before, after, "http_requests_total")

    assert delta["status"] == "invalid"
    assert delta["value"] is None
    assert delta["counter_reset"] is True
    with pytest.raises(RuntimeError, match="process changed"):
        from scripts.runtime_validation import validate_process_continuity

        validate_process_continuity(
            "process_start_time_seconds 100\n", "process_start_time_seconds 101\n"
        )


def test_stale_snapshot_interval_is_rejected() -> None:
    start = datetime(2026, 10, 18, tzinfo=UTC)
    with pytest.raises(ValueError, match="stale"):
        runtime.validate_snapshot_interval(
            (start + timedelta(seconds=1)).isoformat(),
            (start + timedelta(seconds=2)).isoformat(),
            start.isoformat(),
            (start + timedelta(seconds=100)).isoformat(),
        )


@pytest.mark.parametrize(
    (
        "application_revision",
        "expected_binding_status",
        "expected_runtime_status",
        "expected_bundle_status",
        "expected_cli_exit",
    ),
    [
        ("b" * 40, "mismatch", "invalid", "incomplete", 2),
        (SOURCE_SHA, "unverified", "available", "complete", 0),
    ],
)
def test_runtime_source_binding_controls_bundle_and_cli_outcome(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    application_revision: str,
    expected_binding_status: str,
    expected_runtime_status: str,
    expected_bundle_status: str,
    expected_cli_exit: int,
) -> None:
    repository_root = tmp_path / "repository"
    repository_root.mkdir()
    historical_config = repository_root / exp01_evidence.HISTORICAL_FITNESS_CONFIG
    historical_config.parent.mkdir(parents=True)
    historical_config.write_text(
        "architecture_state: A0_MONOLITH\nconfiguration_version: 1\n", encoding="utf-8"
    )
    monkeypatch.setattr(exp01_evidence, "ROOT", repository_root)
    monkeypatch.setattr(exp01_evidence, "_load_architecture_manifest", yaml_state)
    monkeypatch.setattr("scripts.exp01_evidence.platform.platform", lambda: "test platform")
    monkeypatch.setattr(
        exp01_evidence,
        "_git_revision",
        lambda: {"commit_sha": SOURCE_SHA, "git_dirty": False},
    )

    def copy_inputs(run_dir: Path) -> list[dict[str, Any]]:
        return [
            contract.write_artifact(
                run_dir,
                f"inputs/source-{index:02}-{Path(source_path).name}",
                f"synthetic input for {source_path}\n".encode(),
                media_type="text/plain",
                role="source_or_configuration",
                source_path=source_path,
            )
            for index, source_path in enumerate(exp01_evidence.SUPPORTED_INPUTS)
        ]

    monkeypatch.setattr(exp01_evidence, "_copy_inputs", copy_inputs)
    monkeypatch.setattr(
        exp01_evidence,
        "run_architecture_acceptance",
        lambda run_dir, run_id, source_revision, inputs, configuration: _valid_record(
            run_dir, "ci_test", source_revision, configuration=configuration
        ),
    )
    monkeypatch.setattr(
        exp01_evidence,
        "collect_deployment_observation",
        lambda run_dir, run_id, source_revision, inputs, architecture, *, skipped=False: (
            _valid_record(run_dir, "deployment", source_revision)
        ),
    )
    before = _snapshot(cpu=10, requests=0, responses=0, histogram_count=0, histogram_bucket=0)
    after = _snapshot(cpu=12, requests=5, responses=5, histogram_count=5, histogram_bucket=3)

    class Response:
        status_code = 200
        headers: dict[str, str] = {}

        def __init__(self, content: str) -> None:
            self.content = content.encode()
            self.text = content

        def raise_for_status(self) -> None:
            return None

    class Client:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.metric_calls = 0

        def __enter__(self) -> "Client":
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def get(self, url: str) -> Response:
            if url.endswith("/health/ready"):
                return Response('{"status":"ready"}')
            if url.endswith("/metrics"):
                self.metric_calls += 1
                if self.metric_calls > 1:
                    time.sleep(0.02)
                return Response(before if self.metric_calls == 1 else after)
            return Response("[]")

    class Sampler:
        def __init__(self, command: list[str], **kwargs: Any) -> None:
            assert "--output" in command, command
            output_path = Path(command[command.index("--output") + 1])
            start = datetime.now(UTC) + timedelta(milliseconds=2)
            fields = [
                "timestamp_utc",
                "process_cpu_seconds_total",
                "process_resident_memory_bytes",
                "process_virtual_memory_bytes",
            ]
            with output_path.open("w", newline="", encoding="utf-8") as output:
                writer = csv.DictWriter(output, fieldnames=fields)
                writer.writeheader()
                for index in range(6):
                    writer.writerow(
                        {
                            "timestamp_utc": (start + timedelta(milliseconds=index)).isoformat(),
                            "process_cpu_seconds_total": 10 + index * 0.1,
                            "process_resident_memory_bytes": 2048 + index,
                            "process_virtual_memory_bytes": 4096 + index,
                        }
                    )
            self.returncode: int | None = None

        def communicate(self, timeout: float | None = None) -> tuple[str, str]:
            self.returncode = 0
            return "sampled\n", ""

        def poll(self) -> int | None:
            return self.returncode

        def terminate(self) -> None:
            self.returncode = -15

    monkeypatch.setattr("scripts.exp01_evidence_runtime.httpx.Client", Client)
    monkeypatch.setattr("scripts.exp01_evidence_runtime.subprocess.Popen", Sampler)
    monkeypatch.setattr(runtime, "_distribution_version", lambda _: "0.21.0")
    target_identity = _target_observation(application_revision)
    monkeypatch.setattr(runtime, "_docker_target_observation", lambda _: target_identity)

    exit_code = exp01_evidence.main(
        [
            "--architecture-state",
            exp01_evidence.ARCHITECTURE_STATE,
            "--run-id",
            f"runtime-{expected_binding_status}",
        ]
    )

    run_dir = repository_root / "experiments/results" / f"runtime-{expected_binding_status}"
    bundle = contract.validate_bundle(run_dir)
    result = next(record for record in bundle["records"] if record["lifecycle_stage"] == "runtime")
    assert exit_code == expected_cli_exit
    assert bundle["bundle_status"] == expected_bundle_status
    assert result["status"] == expected_runtime_status
    assert result["exit_status"] == 0
    assert result["executable_sha256"] == contract.sha256_bytes(Path(sys.executable).read_bytes())
    assert result["measurements"]["runtime_sampling"]["status"] == "available"
    assert result["measurements"]["runtime_sampling"]["sample_count"] == 6
    assert result["source_revision"] == SOURCE_SHA
    assert result["source_binding"]["status"] == expected_binding_status
    assert result["source_binding"]["endpoint_binding_status"] == "verified"
    assert (
        result["measurements"]["metrics"]["counters"]["http_requests_total_business"]["value"] == 5
    )
    assert (
        result["measurements"]["metrics"]["counters"]["http_responses_total_business_5xx"]["status"]
        == "missing"
    )
    assert result["measurements"]["metrics"]["histogram"]["quantiles"] is None
    assert any(item["role"] == "raw_metrics" for item in result["raw_output_artifacts"])
    assert any(item["role"] == "runtime_samples" for item in result["raw_output_artifacts"])
    identity_artifact = next(
        item
        for item in result["raw_output_artifacts"]
        if item["role"] == "target_identity_observation"
    )
    assert (
        json.loads((run_dir / identity_artifact["path"]).read_text(encoding="utf-8"))[
            "before_runtime_collection"
        ]["endpoint_container"]["observed_application_revision"]
        == application_revision
    )
    if expected_binding_status == "mismatch":
        assert result["execution_verdict"] == "no_usable_evidence"
        assert any("source binding mismatch" in error for error in result["errors"])
    else:
        assert result["execution_verdict"] == "passed"
        assert not any("source binding mismatch" in error for error in result["errors"])
    cli_summary = json.loads(capsys.readouterr().out)
    assert cli_summary["bundle_status"] == expected_bundle_status
    assert cli_summary["stage_results"]["runtime"]["status"] == expected_runtime_status


def test_runtime_readiness_failure_is_an_explicit_not_run_outcome(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class Response:
        status_code = 503
        text = '{"status":"not_ready"}'
        content = text.encode()

        def raise_for_status(self) -> None:
            return None

    class Client:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def __enter__(self) -> "Client":
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def get(self, url: str) -> Response:
            return Response()

    monkeypatch.setattr("scripts.exp01_evidence_runtime.httpx.Client", Client)
    run_dir = tmp_path / "not-ready"
    run_dir.mkdir()

    result = runtime.collect_runtime_evidence(
        run_dir, run_dir.name, "http://localhost:8000", SOURCE_SHA, []
    )

    assert result["status"] == "missing"
    assert result["execution_verdict"] == "not_run"
    assert result["measurements"]["runtime_sampling"]["status"] == "not_run"
    assert result["source_binding"]["status"] == "unverified"
    assert result["raw_output_artifacts"][0]["role"] == "readiness"


def test_bundle_round_trips_schema_and_all_artifact_digests(tmp_path: Path) -> None:
    run_dir = tmp_path / "exp01-dev-smoke"
    bundle = _valid_bundle(run_dir)

    path, validated = contract.write_bundle(run_dir, bundle)

    assert path.is_file()
    assert validated["bundle_status"] == "complete"
    assert len(validated["artifact_inventory"]) == 8
    assert contract.validate_bundle(run_dir)["coverage_claims"]["Coverage_ref"] == "not_established"


def test_bundle_v1_0_remains_readable_without_source_binding(tmp_path: Path) -> None:
    run_dir = tmp_path / "legacy-v1-bundle"
    bundle = _valid_bundle(run_dir)
    bundle["schema_version"] = "1.0.0"
    for record in bundle["records"]:
        record.pop("source_binding")

    _, validated = contract.write_bundle(run_dir, bundle)

    assert validated["schema_version"] == "1.0.0"
    assert "source_binding" not in next(
        record for record in validated["records"] if record["lifecycle_stage"] == "runtime"
    )


def test_bundle_detects_corrupted_artifact_digest(tmp_path: Path) -> None:
    run_dir = tmp_path / "exp01-dev-smoke"
    bundle = _valid_bundle(run_dir)
    contract.write_bundle(run_dir, bundle)
    artifact = next(
        item for item in bundle["artifact_inventory"] if item["path"] == "raw/runtime.txt"
    )
    (run_dir / artifact["path"]).write_text("tampered\n", encoding="utf-8")

    with pytest.raises(ValueError, match="artifact (size|digest) mismatch"):
        contract.validate_bundle(run_dir)


def test_bundle_rejects_wrong_architecture_and_cross_revision_evidence(tmp_path: Path) -> None:
    run_dir = tmp_path / "wrong-state"
    bundle = _valid_bundle(run_dir)
    contract.write_bundle(run_dir, bundle)
    bundle["architecture"]["state"] = "A0_MONOLITH"
    (run_dir / contract.BUNDLE_FILENAME).write_text(json.dumps(bundle), encoding="utf-8")
    with pytest.raises(ValueError, match="schema violation"):
        contract.validate_bundle(run_dir)

    revision_dir = tmp_path / "cross-revision"
    revision_bundle = _valid_bundle(revision_dir)
    contract.write_bundle(revision_dir, revision_bundle)
    revision_bundle["records"][0]["source_revision"] = "b" * 40
    (revision_dir / contract.BUNDLE_FILENAME).write_text(
        json.dumps(revision_bundle), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="source revision"):
        contract.validate_bundle(revision_dir)

    run_id_dir = tmp_path / "cross-run-id"
    run_id_bundle = _valid_bundle(run_id_dir)
    contract.write_bundle(run_id_dir, run_id_bundle)
    run_id_bundle["records"][0]["run_id"] = "other-run"
    (run_id_dir / contract.BUNDLE_FILENAME).write_text(json.dumps(run_id_bundle), encoding="utf-8")
    with pytest.raises(ValueError, match="run-id"):
        contract.validate_bundle(run_id_dir)


def test_missing_evaluator_cannot_create_positive_coverage_or_overwrite_run(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "incomplete"
    bundle = _valid_bundle(run_dir)
    bundle["records"][0]["status"] = "missing"
    bundle["records"][0]["raw_output_artifacts"] = []
    bundle["bundle_status"] = "incomplete"
    _, validated = contract.write_bundle(run_dir, bundle)
    assert validated["coverage_claims"]["Coverage_P"] == "not_assessed"
    assert validated["coverage_claims"]["Coverage_ref"] == "not_established"
    with pytest.raises(FileExistsError, match="overwrite"):
        contract.write_bundle(run_dir, bundle)


def test_bundle_cannot_claim_coverage_ref(tmp_path: Path) -> None:
    run_dir = tmp_path / "no-positive-coverage"
    bundle = _valid_bundle(run_dir)
    bundle["coverage_claims"]["Coverage_ref"] = "established"
    with pytest.raises(ValueError, match="schema violation"):
        contract.write_bundle(run_dir, bundle)


def test_bundle_rejects_promotion_of_unverified_runtime_binding(tmp_path: Path) -> None:
    run_dir = tmp_path / "promoted-source-binding"
    bundle = _valid_bundle(run_dir)
    contract.write_bundle(run_dir, bundle)
    bundle["records"][2]["source_binding"]["status"] = "verified"
    (run_dir / contract.BUNDLE_FILENAME).write_text(json.dumps(bundle), encoding="utf-8")

    with pytest.raises(ValueError, match="cannot be verified"):
        contract.validate_bundle(run_dir)


def test_bundle_rejects_available_runtime_with_mismatched_source_binding(tmp_path: Path) -> None:
    run_dir = tmp_path / "promoted-mismatched-source-binding"
    bundle = _valid_bundle(run_dir)
    binding = bundle["records"][2]["source_binding"]
    assert binding is not None
    binding.update(
        status="mismatch",
        endpoint_binding_status="mismatch",
        identity_stable=False,
        reason="Endpoint identity changed during collection.",
    )

    with pytest.raises(ValueError, match="cannot be available with a mismatched source binding"):
        contract.write_bundle(run_dir, bundle)


def test_runtime_inputs_do_not_include_private_or_scorer_sources() -> None:
    assert not any(
        "ground_truth" in path or "scorer" in path for path in exp01_evidence.SUPPORTED_INPUTS
    )


def test_existing_run_directory_is_never_overwritten(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    results = tmp_path / "experiments/results"
    (results / "existing-run").mkdir(parents=True)
    monkeypatch.setattr("scripts.exp01_evidence.ROOT", tmp_path)
    monkeypatch.setattr(exp01_evidence, "_load_architecture_manifest", yaml_state)
    monkeypatch.setattr(
        exp01_evidence, "_git_revision", lambda: {"commit_sha": SOURCE_SHA, "git_dirty": False}
    )

    with pytest.raises(FileExistsError):
        exp01_evidence.collect_evidence(
            architecture_state="A0_1_CAPABILITY_MODULES",
            base_url="http://localhost:8000",
            run_id="existing-run",
        )
