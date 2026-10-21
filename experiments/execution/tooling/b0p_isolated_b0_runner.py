"""Run the unchanged B0 arm inside its restricted DEVELOPMENT container."""

from __future__ import annotations

import argparse
import json
import os
import platform
import time
from pathlib import Path
from typing import Any, cast

import yaml

from experiments.execution.tooling.b0 import (
    build_b0_candidate,
    build_b0_prediction,
    copy_frozen_configuration,
)
from experiments.execution.tooling.contracts import validate_candidate
from experiments.execution.tooling.hashing import pretty_json_bytes, sha256_bytes
from experiments.execution.tooling.inputs import verify_method_bundle
from experiments.execution.tooling.sealing import seal_prediction


def _write_once(path: Path, payload: Any) -> str:
    """Write canonical run output without replacing an existing artifact."""
    content = pretty_json_bytes(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(descriptor, "wb") as output:
        output.write(content)
        output.flush()
        os.fsync(output.fileno())
    path.chmod(0o444)
    return sha256_bytes(content)


def run_b0(
    input_directory: Path,
    output_directory: Path,
    *,
    architecture_source_sha: str,
    expected_bundle_sha256: str,
    configuration_sha256: str,
    evaluator_configuration_sha256: str,
) -> dict[str, Any]:
    """Build and seal the frozen B0 prediction from its isolated input bundle."""
    started_ns = time.perf_counter_ns()
    bundle = verify_method_bundle(input_directory, expected_method_id="B0")
    if bundle.get("bundle_sha256") != expected_bundle_sha256:
        raise ValueError("B0 input bundle digest does not match the execution manifest")
    if bundle.get("architecture_source_sha") != architecture_source_sha:
        raise ValueError("B0 input is bound to another architecture revision")
    files = cast(list[dict[str, Any]], bundle.get("files", []))
    by_role = {str(row["role"]): row for row in files}
    configuration_bytes = (input_directory / by_role["fitness_configuration"]["path"]).read_bytes()
    representation_bytes = (
        input_directory / by_role["representation_catalog"]["path"]
    ).read_bytes()
    evaluator_bytes = (input_directory / by_role["legacy_evaluator"]["path"]).read_bytes()
    if sha256_bytes(configuration_bytes) != configuration_sha256:
        raise ValueError("B0 configuration differs from its frozen digest")
    if sha256_bytes(evaluator_bytes) != evaluator_configuration_sha256:
        raise ValueError("B0 evaluator configuration differs from its frozen digest")
    configuration = yaml.safe_load(configuration_bytes)
    representation_catalog = yaml.safe_load(representation_bytes)
    if not isinstance(configuration, dict) or not isinstance(representation_catalog, dict):
        raise ValueError("B0 configuration or catalog is not a YAML mapping")

    saved_configuration = output_directory / "configuration/a0-monolith.yaml"
    copied_configuration_sha256 = copy_frozen_configuration(
        input_directory / by_role["fitness_configuration"]["path"],
        saved_configuration,
        configuration_sha256,
    )
    candidate = build_b0_candidate(
        configuration,
        representation_catalog,
        architecture_source_sha,
        configuration_sha256,
        evaluator_configuration_sha256,
    )
    validate_candidate(candidate)
    candidate_sha256 = _write_once(output_directory / "candidate_configuration.json", candidate)
    prediction = build_b0_prediction(architecture_source_sha, expected_bundle_sha256)
    sealed = seal_prediction(prediction, output_directory / "prediction")
    elapsed_ns = time.perf_counter_ns() - started_ns
    trace = {
        "schema_version": 1,
        "method_id": "B0",
        "method_version": prediction["method_version"],
        "architecture_source_sha": architecture_source_sha,
        "input_bundle_sha256": expected_bundle_sha256,
        "configuration_sha256": copied_configuration_sha256,
        "evaluator_configuration_sha256": evaluator_configuration_sha256,
        "candidate_configuration_sha256": candidate_sha256,
        "candidate_validation": "VALID",
        "adaptation_operations": [],
        "adaptation_time_ns": 0,
        "method_execution_time_ns": elapsed_ns,
        "prediction_sha256": sealed.sha256,
        "prediction_sealed_at_utc": sealed.sealed_at_utc,
        "runtime": {"python": platform.python_version(), "platform": platform.platform()},
    }
    trace_sha256 = _write_once(output_directory / "execution_trace.json", trace)
    return {**trace, "execution_trace_sha256": trace_sha256}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("/input"))
    parser.add_argument("--output", type=Path, default=Path("/output"))
    parser.add_argument("--architecture-source-sha", required=True)
    parser.add_argument("--expected-bundle-sha256", required=True)
    parser.add_argument("--configuration-sha256", required=True)
    parser.add_argument("--evaluator-configuration-sha256", required=True)
    args = parser.parse_args()
    result = run_b0(
        args.input,
        args.output,
        architecture_source_sha=args.architecture_source_sha,
        expected_bundle_sha256=args.expected_bundle_sha256,
        configuration_sha256=args.configuration_sha256,
        evaluator_configuration_sha256=args.evaluator_configuration_sha256,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
