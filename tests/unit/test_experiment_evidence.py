"""Fast regression checks for the experiment evidence primitives."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.config import get_settings
from app.main import classify_traffic
from scripts import collect_run_metadata
from scripts.prometheus_snapshot import aggregate, delta, parse_snapshot, value
from scripts.seed_db import seeded_uuid as seed_script_uuid
from scripts.seed_identity import seeded_uuid_value


def test_prometheus_snapshot_aggregates_business_counters_and_cpu_delta() -> None:
    """Calculate business counter and target-process deltas from exposition text."""
    before = parse_snapshot(
        "# HELP http_requests_total HTTP requests\n"
        'http_requests_total{method="GET",path="/api/v1/tasks",traffic_class="business"} 10\n'
        'http_responses_total{method="GET",path="/api/v1/tasks",'
        'status_class="5xx",traffic_class="business"} 2\n'
        "process_cpu_seconds_total 25.5\n"
    )
    after = parse_snapshot(
        'http_requests_total{method="GET",path="/api/v1/tasks",traffic_class="business"} 16\n'
        'http_requests_total{method="GET",path="/health/ready",traffic_class="operational"} 200\n'
        'http_responses_total{method="GET",path="/api/v1/tasks",'
        'status_class="5xx",traffic_class="business"} 3\n'
        "process_cpu_seconds_total 28.0\n"
    )
    assert (
        delta(
            aggregate(after, "http_requests_total", {"traffic_class": "business"}),
            aggregate(before, "http_requests_total", {"traffic_class": "business"}),
        )
        == 6
    )
    assert (
        delta(
            aggregate(
                after, "http_responses_total", {"traffic_class": "business", "status_class": "5xx"}
            ),
            aggregate(
                before, "http_responses_total", {"traffic_class": "business", "status_class": "5xx"}
            ),
        )
        == 1
    )
    assert (
        delta(value(after, "process_cpu_seconds_total"), value(before, "process_cpu_seconds_total"))
        == 2.5
    )


def test_traffic_classification_is_stable_and_separates_operational_calls() -> None:
    """Keep health/scrapes and experiment controls out of business traffic."""
    assert classify_traffic("/api/v1/tasks") == "business"
    assert classify_traffic("/api/v1/tasks/{task_id}") == "business"
    assert classify_traffic("/health/ready") == "operational"
    assert classify_traffic("/metrics") == "operational"
    assert classify_traffic("/internal/experiment/faults") == "experiment"
    assert classify_traffic("/unknown") == "unmatched"


def test_seed_uuid_identity_is_shared_between_application_seed_and_locust(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The seed script and Locust generator honor the same configured identifier."""
    monkeypatch.setenv("SEED_ID", "research-seed-7")
    get_settings.cache_clear()
    try:
        assert get_settings().seed_id == "research-seed-7"
        assert seed_script_uuid("task", 1) == seeded_uuid_value("task", 1, get_settings().seed_id)
    finally:
        get_settings.cache_clear()


def test_metadata_contains_stable_source_and_experiment_fingerprints(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Write provenance using exact config/profile hashes and portable Git fields."""
    fake_engine = MagicMock()
    fake_engine.connect.return_value.__enter__.return_value.scalar.return_value = "PostgreSQL test"
    monkeypatch.setattr(collect_run_metadata, "engine", fake_engine)
    monkeypatch.setattr(
        collect_run_metadata,
        "fingerprint",
        lambda: {"seed_identifier": "test-seed", "sha256": "seed-hash"},
    )

    def command_output_stub(command: list[str]) -> str:
        return "" if command[:2] == ["git", "status"] else "portable-commit-or-image"

    monkeypatch.setattr(collect_run_metadata, "command_output", command_output_stub)
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    target = collect_run_metadata.collect(
        "metadata-test",
        collect_run_metadata.ROOT / "load/profiles/a0-smoke-v1.yaml",
        "2026-10-04T00:00:00+00:00",
        "http://localhost:8000",
        0,
        30,
        1,
    )
    metadata: dict[str, Any] = json.loads(target.read_text(encoding="utf-8"))
    assert metadata["git_commit_sha"] == "portable-commit-or-image"
    assert metadata["git_dirty"] is False
    assert metadata["fitness_configuration_sha256"] == collect_run_metadata.sha256_file(
        collect_run_metadata.FITNESS_CONFIG
    )
    assert metadata["seed_fingerprint_sha256"] == "seed-hash"
    assert metadata["workload_profile_sha256"] == collect_run_metadata.sha256_file(
        collect_run_metadata.ROOT / "load/profiles/a0-smoke-v1.yaml"
    )
    assert metadata["warmup_profile_sha256"] == collect_run_metadata.sha256_file(
        collect_run_metadata.WARMUP_PROFILE
    )
