"""Contract and adapter tests for EXP-02 DEVELOPMENT representation evidence."""

import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts import exp01_evidence
from scripts import exp01_evidence_contract as contract
from scripts import exp02_fitness_evidence as exp02

SOURCE_SHA = "a" * 40
RUN_ID = "exp02-adapter-test"


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


def _valid_record(
    run_dir: Path,
    *,
    record_id: str,
    stage: str,
    evaluator_name: str,
    scope_id: str,
    source_revision: str = SOURCE_SHA,
    status: str = "available",
    execution_verdict: str = "passed",
    measurements: dict[str, Any] | None = None,
    configuration_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    start = datetime(2026, 10, 18, tzinfo=UTC)
    raw = contract.write_artifact(
        run_dir,
        f"raw/{record_id}.stdout.txt",
        f"evaluator output for {record_id}\n".encode(),
        media_type="text/plain",
        role="stdout",
    )
    return {
        "record_id": record_id,
        "run_id": RUN_ID,
        "lifecycle_stage": stage,
        "status": status,
        "evaluator_name": evaluator_name,
        "evaluator_version": "1.0.0",
        "executable": "/usr/bin/python3",
        "executable_sha256": None,
        "command": ["python", "-m", evaluator_name],
        "started_at_utc": start.isoformat(),
        "ended_at_utc": (start + timedelta(seconds=1)).isoformat(),
        "duration_seconds": 1.0,
        "exit_status": 0 if execution_verdict == "passed" else 1,
        "execution_verdict": execution_verdict,
        "scope": f"Synthetic {scope_id} evaluator scope.",
        "scope_id": scope_id,
        "source_revision": source_revision,
        "source_binding": _source_binding(source_revision) if stage == "runtime" else None,
        "configuration_artifact": configuration_artifact,
        "input_artifacts": [],
        "raw_output_artifacts": [raw],
        "measurements": measurements or {},
        "errors": [],
        "limitations": [],
    }


def _valid_bundle(tmp_path: Path) -> tuple[Path, dict[str, Any], bytes]:
    run_dir = tmp_path / RUN_ID
    run_dir.mkdir(parents=True)
    input_artifacts = [
        contract.copy_input_artifact(run_dir, source_path, "source_or_configuration")
        for source_path in exp01_evidence.SUPPORTED_INPUTS
    ]
    inputs_by_source = {item["source_path"]: item for item in input_artifacts}
    configuration_bytes = (contract.ROOT / exp02.FITNESS_CONFIGURATION_PATH).read_bytes()
    configuration = exp02.load_fitness_configuration(
        configuration_bytes,
        (
            run_dir / inputs_by_source["fitness/catalog/architectural-obligations.yaml"]["path"]
        ).read_bytes(),
    )
    config_ref = inputs_by_source[exp02.FITNESS_CONFIGURATION_PATH]
    manifest_ref = inputs_by_source[exp01_evidence.ARCHITECTURE_MANIFEST]
    schema_ref = inputs_by_source["experiments/schemas/development_evidence_bundle_v1.schema.json"]
    acceptance_ref = inputs_by_source[exp01_evidence.ARCHITECTURE_ACCEPTANCE]

    records = [
        _valid_record(
            run_dir,
            record_id="exp01-ci-import-linter-v1",
            stage="ci_test",
            evaluator_name="import-linter",
            scope_id="architecture.internal_dependencies",
            measurements={"dependency_rule_violations": 0},
            configuration_artifact=acceptance_ref,
        ),
        _valid_record(
            run_dir,
            record_id="exp02-ci-module-structure-v1",
            stage="ci_test",
            evaluator_name="pytest-architecture-module-structure",
            scope_id="architecture.capability_modules",
            measurements={"module_structure_test_failures": 0, "tests_passed": 1},
            configuration_artifact=manifest_ref,
        ),
        _valid_record(
            run_dir,
            record_id="exp01-deployment-compose-v1",
            stage="deployment",
            evaluator_name="docker-compose-read-only-observer",
            scope_id="deployment.compose_observation",
            execution_verdict="inconclusive",
        ),
        _valid_record(
            run_dir,
            record_id="exp01-runtime-v1",
            stage="runtime",
            evaluator_name="prometheus-runtime-collector",
            scope_id="runtime.business_api",
            measurements={
                "metrics": {
                    "counters": {
                        "http_responses_total_business_5xx": {"status": "available", "value": 0},
                        "business_operation_failures_total": {"status": "available", "value": 0},
                    },
                    "histogram": {
                        "status": "available",
                        "series": [
                            {
                                "metric": "http_request_duration_seconds_bucket",
                                "labels": {"le": "0.5"},
                                "delta": 1.0,
                            }
                        ],
                        "quantiles": None,
                        "limitations": ["p95 is not calculated from bucket data."],
                    },
                }
            },
        ),
    ]
    bundle = {
        "schema_version": "1.2.0",
        "run_id": RUN_ID,
        "bundle_status": "complete",
        "created_at_utc": datetime(2026, 10, 18, 0, 0, tzinfo=UTC).isoformat(),
        "source_revision": {"commit_sha": SOURCE_SHA, "git_dirty": False},
        "architecture": {
            "state": "A0_1_CAPABILITY_MODULES",
            "manifest_artifact": manifest_ref,
        },
        "fitness_configuration": {
            "status": "selected",
            "declared_architecture_state": configuration["architecture_state"],
            "configuration_version": configuration["configuration_version"],
            "configuration_sha256": contract.sha256_bytes(configuration_bytes),
            "configuration_artifact": config_ref,
            "applicable_to_target": True,
            "provenance_status": "manual_development_reference",
        },
        "execution_context": {
            "python_version": "3.12.1",
            "platform": "test platform",
            "base_url": "http://localhost:8000",
            "schema_artifact": schema_ref,
        },
        "supported_stages": ["ci_test", "deployment", "runtime"],
        "input_artifacts": input_artifacts,
        "artifact_inventory": [],
        "records": records,
        "coverage_claims": {
            "Coverage_P": "not_assessed",
            "Coverage_ref": "not_established",
            "measured_results": "not_run",
        },
        "limitations": ["Synthetic test fixture; not a measured run."],
    }
    return run_dir, bundle, configuration_bytes


def _build_evidence(
    tmp_path: Path,
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    run_dir, bundle, configuration_bytes = _valid_bundle(tmp_path)
    evidence = exp02.build_representation_evidence(bundle, run_dir, configuration_bytes)
    return run_dir, bundle, evidence


def test_a01_fitness_configuration_validates_as_manual_development_reference() -> None:
    configuration = exp02.load_fitness_configuration(
        (contract.ROOT / exp02.FITNESS_CONFIGURATION_PATH).read_bytes()
    )

    assert configuration["architecture_state"] == "A0_1_CAPABILITY_MODULES"
    assert configuration["status"] == "development_reference"
    assert configuration["provenance"]["established_by"] == "manual"
    assert configuration["provenance"]["method_p_adaptation"] is False
    assert configuration["provenance"]["b1_adaptation"] is False
    assert {
        "AC_MODULE_STRUCTURE",
        "AC_LAYERING",
        "R_HTTP_5XX",
        "R_BUSINESS_FAILURE",
        "P_EXT_LATENCY",
    } <= {
        obligation
        for representation in configuration["representations"]
        for obligation in representation["declared_obligations"]
    }


def test_configuration_rejects_a0_identity_mismatch() -> None:
    configuration = yaml.safe_load((contract.ROOT / exp02.FITNESS_CONFIGURATION_PATH).read_bytes())
    configuration["architecture_state"] = "A0_MONOLITH"

    with pytest.raises(ValueError, match="schema violation"):
        exp02.load_fitness_configuration(yaml.safe_dump(configuration).encode())


@pytest.mark.parametrize(
    "source_path",
    [
        exp02.FITNESS_CONFIGURATION_PATH,
        "architecture/acceptance/importlinter.toml",
    ],
)
def test_configuration_and_evaluator_artifact_digests_are_verified(
    tmp_path: Path, source_path: str
) -> None:
    run_dir, bundle, configuration_bytes = _valid_bundle(tmp_path)
    input_ref = next(
        item for item in bundle["input_artifacts"] if item["source_path"] == source_path
    )
    (run_dir / input_ref["path"]).write_bytes(b"tampered artifact")

    with pytest.raises(ValueError, match="artifact (size|digest) mismatch"):
        exp02.build_representation_evidence(bundle, run_dir, configuration_bytes)


def test_real_evaluator_records_map_to_representation_evidence(tmp_path: Path) -> None:
    run_dir, bundle, evidence = _build_evidence(tmp_path)
    by_id = {item["representation_id"]: item for item in evidence["representations"]}

    module_structure = by_id["REP_A01_ARCH_MODULE_STRUCTURE_CI"]
    assert module_structure["evaluator_execution"]["status"] == "available"
    assert module_structure["compliance_observation"]["status"] == "conforming"
    assert by_id["REP_A01_ARCH_INTERNAL_LAYERING_CI"]["metrics"][0]["value"] == 0
    assert by_id["REP_A01_REL_HTTP_5XX_RUNTIME"]["metrics"][0]["value"] == 0
    assert by_id["REP_A01_REL_BUSINESS_FAILURE_RUNTIME"]["metrics"][0]["status"] == "available"
    latency = by_id["REP_A01_PERF_HTTP_DURATION_RUNTIME"]["metrics"][0]["value"]
    assert latency["quantiles"] is None
    assert latency["series"][0]["metric"] == "http_request_duration_seconds_bucket"
    assert by_id["REP_A01_PERF_HTTP_DURATION_RUNTIME"]["independent_coverage"] == "not_established"
    assert evidence["coverage_claims"]["Coverage_P"] == "not_assessed"
    assert evidence["coverage_claims"]["Coverage_ref"] == "not_established"
    raw_paths = {
        item["path"] for item in by_id["REP_A01_ARCH_INTERNAL_LAYERING_CI"]["evidence_references"]
    }
    assert any(path.endswith("exp01-ci-import-linter-v1.stdout.txt") for path in raw_paths)

    representation_ref = contract.write_artifact(
        run_dir,
        exp02.REPRESENTATION_EVIDENCE_FILENAME,
        (json.dumps(evidence, indent=2, sort_keys=True) + "\n").encode(),
        media_type="application/json",
        role="fitness_representation_evidence",
    )
    bundle["fitness_representation_evidence"] = representation_ref
    _, validated = contract.write_bundle(run_dir, bundle)
    assert exp02.validate_representation_evidence(run_dir, validated)["run_id"] == RUN_ID


def test_missing_evaluator_or_metric_remains_explicit(tmp_path: Path) -> None:
    run_dir, bundle, configuration_bytes = _valid_bundle(tmp_path)
    bundle["records"] = [
        record
        for record in bundle["records"]
        if record["record_id"] != "exp02-ci-module-structure-v1"
    ]
    runtime_record = next(
        record for record in bundle["records"] if record["record_id"] == "exp01-runtime-v1"
    )
    runtime_record["measurements"]["metrics"]["counters"]["business_operation_failures_total"] = {
        "status": "missing",
        "value": None,
    }

    evidence = exp02.build_representation_evidence(bundle, run_dir, configuration_bytes)
    by_id = {item["representation_id"]: item for item in evidence["representations"]}
    structure = by_id["REP_A01_ARCH_MODULE_STRUCTURE_CI"]
    business_failure = by_id["REP_A01_REL_BUSINESS_FAILURE_RUNTIME"]

    assert structure["evaluator_execution"]["status"] == "missing"
    assert any(item["status"] == "missing_evaluator" for item in evidence["unresolved_mappings"])
    assert business_failure["metrics"][0]["status"] == "missing"
    assert business_failure["metrics"][0]["value"] is None


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("lifecycle_stage", "runtime", "lifecycle stage conflicts"),
        ("scope_id", "architecture.other_scope", "architecture scope conflicts"),
        ("evaluator_name", "unrelated-evaluator", "evaluator identity conflicts"),
    ],
)
def test_conflicting_evaluator_stage_scope_or_identity_is_rejected(
    tmp_path: Path, field: str, value: str, message: str
) -> None:
    run_dir, bundle, configuration_bytes = _valid_bundle(tmp_path)
    module_record = next(
        record
        for record in bundle["records"]
        if record["record_id"] == "exp02-ci-module-structure-v1"
    )
    module_record[field] = value

    with pytest.raises(ValueError, match=message):
        exp02.build_representation_evidence(bundle, run_dir, configuration_bytes)


def test_conflicting_source_revision_is_rejected(tmp_path: Path) -> None:
    run_dir, bundle, configuration_bytes = _valid_bundle(tmp_path)
    next(record for record in bundle["records"] if record["record_id"] == "exp01-runtime-v1")[
        "source_revision"
    ] = "b" * 40

    with pytest.raises(ValueError, match="source revision conflicts"):
        exp02.build_representation_evidence(bundle, run_dir, configuration_bytes)


def test_conflicting_evaluator_configuration_artifact_is_rejected(tmp_path: Path) -> None:
    run_dir, bundle, configuration_bytes = _valid_bundle(tmp_path)
    module_structure = next(
        record
        for record in bundle["records"]
        if record["record_id"] == "exp02-ci-module-structure-v1"
    )
    module_structure["configuration_artifact"] = next(
        item
        for item in bundle["input_artifacts"]
        if item["source_path"] == "architecture/acceptance/importlinter.toml"
    )

    with pytest.raises(ValueError, match="configuration artifact conflicts"):
        exp02.build_representation_evidence(bundle, run_dir, configuration_bytes)


@pytest.mark.parametrize(
    ("exit_status", "stdout", "expected_verdict", "expected_failures"),
    [
        (0, "1 passed in 0.01s\n", "passed", 0),
        (1, "1 failed in 0.01s\n", "violations_detected", 1),
    ],
)
def test_module_structure_runner_preserves_pass_and_architecture_violation_results(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    exit_status: int,
    stdout: str,
    expected_verdict: str,
    expected_failures: int,
) -> None:
    run_dir = tmp_path / "runner"
    run_dir.mkdir()
    manifest = contract.write_artifact(
        run_dir,
        "inputs/architecture.yaml",
        b"architecture_state: A0_1_CAPABILITY_MODULES\n",
        media_type="application/yaml",
        role="configuration",
        source_path="architecture/states/A0_1_CAPABILITY_MODULES.yaml",
    )
    monkeypatch.setattr(exp01_evidence, "RUNNER_EXECUTABLE", "/usr/bin/python3")
    monkeypatch.setattr(exp01_evidence, "_distribution_version", lambda _: "8.4.2")
    monkeypatch.setattr(
        "scripts.exp01_evidence.subprocess.run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, exit_status, stdout, ""),
    )

    result = exp01_evidence.run_module_structure_acceptance(
        run_dir,
        RUN_ID,
        SOURCE_SHA,
        [manifest],
        manifest,
    )

    assert result["status"] == "available"
    assert result["execution_verdict"] == expected_verdict
    assert result["measurements"]["module_structure_test_failures"] == expected_failures
    assert len(result["raw_output_artifacts"]) == 2


def test_noncompliant_architecture_result_is_not_hidden_by_execution_success(
    tmp_path: Path,
) -> None:
    run_dir, bundle, configuration_bytes = _valid_bundle(tmp_path)
    linter = next(
        record for record in bundle["records"] if record["record_id"] == "exp01-ci-import-linter-v1"
    )
    linter["execution_verdict"] = "violations_detected"
    linter["exit_status"] = 1
    linter["measurements"]["dependency_rule_violations"] = 2

    evidence = exp02.build_representation_evidence(bundle, run_dir, configuration_bytes)
    layering = next(
        item
        for item in evidence["representations"]
        if item["representation_id"] == "REP_A01_ARCH_INTERNAL_LAYERING_CI"
    )

    assert layering["evaluator_execution"]["status"] == "available"
    assert layering["compliance_observation"]["status"] == "nonconforming"
    assert layering["metrics"][0]["value"] == 2
    assert layering["independent_coverage"] == "not_established"


def test_invalid_or_stale_runtime_record_never_yields_available_metrics(tmp_path: Path) -> None:
    run_dir, bundle, configuration_bytes = _valid_bundle(tmp_path)
    runtime_record = next(
        record for record in bundle["records"] if record["record_id"] == "exp01-runtime-v1"
    )
    runtime_record["status"] = "invalid"

    evidence = exp02.build_representation_evidence(bundle, run_dir, configuration_bytes)
    runtime_entries = [
        item for item in evidence["representations"] if item["lifecycle_stage"] == "runtime"
    ]

    assert all(item["evaluator_execution"]["status"] == "invalid" for item in runtime_entries)
    assert all(
        metric["status"] == "invalid" for item in runtime_entries for metric in item["metrics"]
    )
    assert all(item["independent_coverage"] == "not_established" for item in runtime_entries)


def test_unverified_application_identity_is_preserved_as_unknown(tmp_path: Path) -> None:
    run_dir, bundle, configuration_bytes = _valid_bundle(tmp_path)

    evidence = exp02.build_representation_evidence(bundle, run_dir, configuration_bytes)
    runtime_entry = next(
        item
        for item in evidence["representations"]
        if item["representation_id"] == "REP_A01_PERF_HTTP_DURATION_RUNTIME"
    )

    assert runtime_entry["evaluator_execution"]["runtime_source_binding_status"] == "unverified"
    assert runtime_entry["compliance_observation"]["status"] == "not_assessed"
    assert any(
        item["status"] == "unverified_source_identity" for item in evidence["unresolved_mappings"]
    )


def test_legacy_exp01_schema_versions_1_0_and_1_1_remain_readable(tmp_path: Path) -> None:
    for schema_version in ("1.0.0", "1.1.0"):
        run_dir, bundle, _ = _valid_bundle(tmp_path / schema_version)
        bundle["schema_version"] = schema_version
        bundle.pop("fitness_representation_evidence", None)
        bundle["records"] = [
            record
            for record in bundle["records"]
            if record["record_id"] != "exp02-ci-module-structure-v1"
        ]
        for record in bundle["records"]:
            record.pop("scope_id", None)
            if schema_version == "1.0.0":
                record.pop("source_binding", None)
        historical_config_reference = next(
            item
            for item in bundle["input_artifacts"]
            if item["source_path"] == exp01_evidence.HISTORICAL_FITNESS_CONFIG
        )
        bundle["fitness_configuration"] = exp01_evidence._fitness_configuration_from_source(
            {exp01_evidence.HISTORICAL_FITNESS_CONFIG: historical_config_reference}
        )
        bundle["bundle_status"] = "complete"

        _, validated = contract.write_bundle(run_dir, bundle)
        assert validated["schema_version"] == schema_version


def test_exp02_inputs_remain_isolated_from_oracle_and_scorer_sources() -> None:
    configuration = exp02.load_fitness_configuration(
        (contract.ROOT / exp02.FITNESS_CONFIGURATION_PATH).read_bytes()
    )
    declared_sources = {
        path
        for representation in configuration["representations"]
        for path in representation["evaluator"]["source_artifacts"]
    }
    all_sources = set(exp01_evidence.SUPPORTED_INPUTS) | declared_sources

    assert all("ground_truth" not in path and "scorer" not in path for path in all_sources)
    assert "experiments/scenarios/DA01/ground_truth.yaml" not in all_sources


def test_representation_schema_rejects_unearned_coverage_claim(tmp_path: Path) -> None:
    run_dir, bundle, evidence = _build_evidence(tmp_path)
    evidence["coverage_claims"]["Coverage_P"] = "established"
    ref = contract.write_artifact(
        run_dir,
        exp02.REPRESENTATION_EVIDENCE_FILENAME,
        (json.dumps(evidence, indent=2, sort_keys=True) + "\n").encode(),
        media_type="application/json",
        role="fitness_representation_evidence",
    )
    bundle["fitness_representation_evidence"] = ref

    with pytest.raises(ValueError, match="representation evidence schema violation"):
        contract.write_bundle(run_dir, bundle)
