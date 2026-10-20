"""Write-once execution continuation for a prepared B0/P DEVELOPMENT comparison."""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess  # nosec B404 - fixed Git, Docker, and evaluator argv
import time
import zipfile
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path, PurePosixPath
from typing import Any, cast

from experiments.execution.tooling.b0p_development import verify_study_manifest
from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ProtocolError
from experiments.execution.tooling.hashing import pretty_json_bytes, sha256_bytes, sha256_file
from experiments.execution.tooling.inputs import verify_method_bundle
from experiments.execution.tooling.p_policy_source_v3 import verify_method_bundle_v3
from experiments.execution.tooling.sealing import load_verified_prediction
from experiments.execution.tooling.validity import inspect_import_linter_scope

ROOT = Path(__file__).resolve().parents[3]
EXECUTION_SCHEMA = "b0p_development_execution_v1.schema.json"
RUN_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$", re.ASCII)
BASE_IMAGE = (
    "python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1"
)
RUNTIME_REQUIREMENTS = (
    "attrs==26.1.0 --hash=sha256:c647aa4a12dfbad9333ca4e71fe62ddc36f4e63b2d260a37a8b83d2f043ac309 "
    "--hash=sha256:d03ceb89cb322a8fd706d4fb91940737b6642aa36998fe130a9bc96c985eff32\n"
    "jsonschema==4.26.0 "
    "--hash=sha256:d489f15263b8d200f8387e64b4c3a75f06629559fb73deb8fdfb525f2dab50ce "
    "--hash=sha256:0c26707e2efad8aa1bfc5b7ce170f3fccc2e4918ff85989ba9ffa9facb2be326\n"
    "jsonschema-specifications==2025.9.1 "
    "--hash=sha256:98802fee3a11ee76ecaca44429fda8a41bff98b00a0f2838151b113f210cc6fe "
    "--hash=sha256:b540987f239e745613c7a9176f3edb72b832a4ac465cf02712288397832b5e8d\n"
    "PyYAML==6.0.3 "
    "--hash=sha256:ba1cc08a7ccde2d2ec775841541641e4548226580ab850948cbfda66a1befcdc "
    "--hash=sha256:9149cad251584d5fb4981be1ecde53a1ca46c891a79788c0df828d2f166bda28 "
    "--hash=sha256:d76623373421df22fb4cf8817020cbb7ef15c725b9d5e45f17e189bfc384190f\n"
    "referencing==0.37.0 "
    "--hash=sha256:381329a9f99628c9069361716891d34ad94af76e461dcb0335825aecc7692231 "
    "--hash=sha256:44aefc3142c5b842538163acb373e24cce6632bd54bdb01b21ad5863489f50d8\n"
    "rpds-py==2026.9.1 "
    "--hash=sha256:2693b2728bbcc48d09a981a356954b0c47c53ff25b545856f28a889ea619f69a "
    "--hash=sha256:addeda51556dac7c1a2f14cda62db8b621cd12afba3091d03a96c72932387eab "
    "--hash=sha256:4793ef7f78268b124b73fa933440f01d258bbae01de9fa53e9080c9ab0425a12\n"
    "typing-extensions==4.16.0 "
    "--hash=sha256:481caa481374e813c1b176ada14e97f1f67a4539ce9cfeb3f350d78d6370c2e8 "
    "--hash=sha256:dc983d19a509c94dba722ee6abd33940f7c05a89e243c47e907eb4db6f1a43e5\n"
)
SCORER_SCHEMA_FILES = {"ground_truth_hash.schema.json", "scored_result.schema.json"}
EVALUATOR_PATHS = (
    "app",
    "tests/architecture",
    "fitness/evaluators/a0/importlinter.toml",
)


class B0PExecutionError(ProtocolError):
    """A prepared study could not be continued without violating its bindings."""


def perform_development_execution(
    preparation_directory: Path,
    *,
    run_id: str,
    repository: Path | None = None,
    docker_executable: str = "docker",
    uv_executable: str = "uv",
) -> dict[str, Any]:
    """Execute B0 and frozen P, then collect fresh evaluator observations and archive outputs."""
    repository_root = (repository or ROOT).resolve(strict=True)
    if preparation_directory.is_symlink():
        raise B0PExecutionError("Preparation run directory must not be a symlink")
    prep_root = preparation_directory.resolve(strict=True)
    if (
        prep_root.is_symlink()
        or prep_root.parent != (repository_root / "experiments/results").resolve()
    ):
        raise B0PExecutionError(
            "Preparation must be an existing run directly under experiments/results"
        )
    if RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise B0PExecutionError(
            "Execution run ID must use lowercase letters, digits, dot, dash or underscore"
        )
    results_root = (repository_root / "experiments/results").resolve(strict=True)
    run_root = results_root / run_id
    if run_root.exists() or run_root.is_symlink():
        raise B0PExecutionError(f"Execution output already exists and is write-once: {run_root}")

    prep_manifest = verify_study_manifest(prep_root, repository_root)
    prep_manifest_bytes = (prep_root / "study_manifest.json").read_bytes()
    prep_digest = sha256_bytes(prep_manifest_bytes)
    run_root.mkdir(mode=0o755)
    try:
        snapshot = run_root / "preparation_snapshot"
        shutil.copytree(prep_root, snapshot, copy_function=shutil.copy2)
        if sha256_file(snapshot / "study_manifest.json") != prep_digest:
            raise B0PExecutionError(
                "Preparation snapshot differs from independently verified manifest"
            )
        _write_reference_availability(run_root, prep_manifest)
        _record_host_environment(
            run_root,
            docker_executable=docker_executable,
            uv_executable=uv_executable,
            repository=repository_root,
        )

        b0_context, b0_context_digest = _build_runtime_context(
            run_root,
            method_id="B0",
            source_sha=prep_manifest["source_revisions"]["b0_source_sha"],
            prep_manifest=prep_manifest,
            repository=repository_root,
        )
        p_context, p_context_digest = _build_runtime_context(
            run_root,
            method_id="P",
            source_sha=prep_manifest["source_revisions"]["p_source_sha"],
            prep_manifest=prep_manifest,
            repository=repository_root,
        )
        b0_image = _build_image(b0_context, run_id, "b0", docker_executable, repository_root)
        p_image = _build_image(p_context, run_id, "p", docker_executable, repository_root)

        input_root = snapshot / "method_inputs"
        b0_output = run_root / "B0"
        p_output = run_root / "P"
        b0_output.mkdir(mode=0o777)
        p_output.mkdir(mode=0o777)
        b0_execution = _run_isolated_arm(
            method_id="B0",
            image=b0_image,
            input_directory=input_root / "b0",
            output_directory=b0_output,
            preparation=prep_manifest,
            docker_executable=docker_executable,
            repository=repository_root,
        )
        p_execution = _run_isolated_arm(
            method_id="P",
            image=p_image,
            input_directory=input_root / "p",
            output_directory=p_output,
            preparation=prep_manifest,
            docker_executable=docker_executable,
            repository=repository_root,
        )

        # Evaluators run only after both method outputs have been sealed or explicitly withheld.
        evaluator_started_ns = time.perf_counter_ns()
        evaluator_records, evaluator_duration_ns = _run_evaluators(
            run_root,
            prep_manifest,
            uv_executable=uv_executable,
            repository=repository_root,
        )
        verification_started_ns = time.perf_counter_ns()
        _verify_evaluator_records(run_root, evaluator_records, prep_manifest)
        pair_verification = _unknown_pair_verification(run_root, p_output)
        verification_duration_ns = time.perf_counter_ns() - verification_started_ns
        _write_once(run_root / "semantic_pair_verification.json", pair_verification)
        if time.perf_counter_ns() < evaluator_started_ns:
            raise B0PExecutionError("Monotonic evaluator timer moved backwards")

        execution_manifest = _make_execution_manifest(
            run_root,
            preparation=prep_manifest,
            preparation_digest=prep_digest,
            runtime_contexts={"B0": b0_context_digest, "P": p_context_digest},
            runtime_images={"B0": b0_image, "P": p_image},
            b0_execution=b0_execution,
            p_execution=p_execution,
            evaluator_records=evaluator_records,
            evaluator_duration_ns=evaluator_duration_ns,
            verification_duration_ns=verification_duration_ns,
            pair_verification=pair_verification,
            execution_mode={
                "kind": "DIRECT",
                "source_attempt_run_id": None,
                "method_invocations_reused": False,
                "detail": "Both method arms executed in this run directory.",
            },
        )
        validate_payload(EXECUTION_SCHEMA, execution_manifest)
        _write_once(run_root / "execution_manifest.json", execution_manifest)
        _write_run_checksums(run_root)
        _verify_run_inventory(run_root)
        return execution_manifest
    except Exception as error:
        failure = {
            "schema_version": 1,
            "run_id": run_id,
            "execution_status": "EXECUTION_FAILED",
            "error_type": type(error).__name__,
            "error": str(error),
            "failed_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
        failure_path = run_root / "execution_failure.json"
        if not failure_path.exists():
            _write_once(failure_path, failure)
        _write_run_checksums(run_root)
        raise


def finalize_post_execution_failure(
    run_directory: Path,
    *,
    repository: Path | None = None,
    docker_executable: str = "docker",
    uv_executable: str = "uv",
    attempt_id: str = "a01",
) -> dict[str, Any]:
    """Append a manifest after post-arm aggregation failed, without rerunning either method."""
    repository_root = (repository or ROOT).resolve(strict=True)
    if run_directory.is_symlink():
        raise B0PExecutionError("Execution directory must not be a symlink")
    run_root = run_directory.resolve(strict=True)
    if run_root.parent != (repository_root / "experiments/results").resolve():
        raise B0PExecutionError("Recovery requires a run directly under experiments/results")
    if not RUN_ID_PATTERN.fullmatch(run_root.name) or not re.fullmatch(r"a[0-9]{2}", attempt_id):
        raise B0PExecutionError("Recovery run or attempt ID is invalid")
    if any(
        (run_root / name).exists()
        for name in ("execution_manifest.json", "execution_recovery.json", "FINAL_SHA256SUMS")
    ):
        raise B0PExecutionError("Execution recovery is write-once and has already been finalized")
    _verify_run_inventory(run_root)
    failure_path = run_root / "execution_failure.json"
    failure = cast(dict[str, Any], json.loads(failure_path.read_text(encoding="utf-8")))
    if (
        failure.get("run_id") != run_root.name
        or failure.get("error_type") != "KeyError"
        or failure.get("error") != "'candidate_validation'"
    ):
        raise B0PExecutionError(
            "This recovery path only accepts the known post-arm aggregation failure"
        )

    prep_root = run_root / "preparation_snapshot"
    prep_manifest_path = prep_root / "study_manifest.json"
    prep_digest = sha256_file(prep_manifest_path)
    snapshot_manifest = cast(
        dict[str, Any], json.loads(prep_manifest_path.read_text(encoding="utf-8"))
    )
    original_prep = repository_root / "experiments/results" / str(snapshot_manifest["run_id"])
    prep_manifest = verify_study_manifest(original_prep, repository_root)
    if sha256_file(original_prep / "study_manifest.json") != prep_digest:
        raise B0PExecutionError("Original preparation package changed after the execution attempt")
    _verify_preparation_snapshot(prep_root, prep_manifest)

    runtime_contexts = {
        method_id: _directory_digest(run_root / "container_context" / method_id)
        for method_id in ("B0", "P")
    }
    _verify_runtime_contexts(
        run_root,
        {
            "runtime_contexts": runtime_contexts,
            "source_revisions": prep_manifest["source_revisions"],
        },
    )
    runtime_images = {
        method_id: _recover_runtime_image(run_root, method_id, docker_executable)
        for method_id in ("B0", "P")
    }
    b0_execution = _recover_completed_arm(run_root, "B0", runtime_images["B0"])
    p_execution = _recover_completed_arm(run_root, "P", runtime_images["P"])
    _verify_recovered_predictions(run_root, prep_manifest, p_execution)

    evaluator_started_ns = time.perf_counter_ns()
    evaluator_records, evaluator_duration_ns = _run_evaluators(
        run_root,
        prep_manifest,
        uv_executable=uv_executable,
        repository=repository_root,
        label_prefix=f"recovery_{attempt_id}_",
    )
    verification_started_ns = time.perf_counter_ns()
    _verify_evaluator_records(run_root, evaluator_records, prep_manifest)
    pair_verification = _unknown_pair_verification(run_root, run_root / "P")
    existing_pairs = json.loads(
        (run_root / "semantic_pair_verification.json").read_text(encoding="utf-8")
    )
    if pair_verification != existing_pairs:
        raise B0PExecutionError("Recovery readback differs from the original P trace diagnostics")
    verification_duration_ns = time.perf_counter_ns() - verification_started_ns
    if time.perf_counter_ns() < evaluator_started_ns:
        raise B0PExecutionError("Monotonic evaluator timer moved backwards")

    recovery_record = {
        "schema_version": 1,
        "run_id": run_root.name,
        "recovered_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "original_failure_path": "execution_failure.json",
        "original_failure_sha256": sha256_file(failure_path),
        "original_checksum_inventory_path": "SHA256SUMS",
        "original_checksum_inventory_sha256": sha256_file(run_root / "SHA256SUMS"),
        "method_outputs_reused": True,
        "method_invocations_repeated": False,
        "prediction_seals_reused": True,
        "recovery_evaluator_label_prefix": f"recovery_{attempt_id}_",
        "reason": (
            "Both isolated arms and the first fresh evaluators completed, but the orchestrator "
            "lost in-memory method result fields while assembling its manifest. This append-only "
            "finalization reuses the existing method outputs and records new post-arm evaluator "
            "streams; neither method container is invoked again."
        ),
    }
    _write_once(run_root / "execution_recovery.json", recovery_record)
    manifest = _make_execution_manifest(
        run_root,
        preparation=prep_manifest,
        preparation_digest=prep_digest,
        runtime_contexts=runtime_contexts,
        runtime_images=runtime_images,
        b0_execution=b0_execution,
        p_execution=p_execution,
        evaluator_records=evaluator_records,
        evaluator_duration_ns=evaluator_duration_ns,
        verification_duration_ns=verification_duration_ns,
        pair_verification=pair_verification,
        execution_mode={
            "kind": "POST_EXECUTION_FINALIZATION",
            "source_attempt_run_id": run_root.name,
            "method_invocations_reused": True,
            "detail": (
                "The original B0 and P outputs were verified and reused byte-for-byte; only "
                "post-arm evaluators were rerun to persist their lost result records."
            ),
        },
    )
    validate_payload(EXECUTION_SCHEMA, manifest)
    _write_once(run_root / "execution_manifest.json", manifest)
    _write_final_checksums(run_root)
    _verify_run_inventory(run_root)
    return manifest


def _make_execution_manifest(
    run_root: Path,
    *,
    preparation: Mapping[str, Any],
    preparation_digest: str,
    runtime_contexts: Mapping[str, str],
    runtime_images: Mapping[str, Mapping[str, str]],
    b0_execution: Mapping[str, Any],
    p_execution: Mapping[str, Any],
    evaluator_records: Sequence[Mapping[str, Any]],
    evaluator_duration_ns: int,
    verification_duration_ns: int,
    pair_verification: Mapping[str, Any],
    execution_mode: Mapping[str, Any],
) -> dict[str, Any]:
    run_id = run_root.name
    arm_records = {
        "B0": _arm_manifest_record(
            "B0", run_root / "B0", b0_execution, preparation, runtime_images["B0"]
        ),
        "P": _arm_manifest_record(
            "P", run_root / "P", p_execution, preparation, runtime_images["P"]
        ),
    }
    p_governance = str(p_execution["governance_result"])
    rq1 = {
        "status": "NOT_EVALUABLE",
        "reason": (
            "No exact-after-SHA target-operation reference was fixed and sealed before the "
            "predictions. A retrospective reference would not be admissible for this run."
        ),
        "reference_path": "reference/reference_availability.json",
        "reference_sha256": sha256_file(run_root / "reference/reference_availability.json"),
        "scorer_invoked": False,
        "result_path": None,
    }
    reference_record = json.loads(
        (run_root / "reference/reference_availability.json").read_text(encoding="utf-8")
    )
    _validate_rq1_claims(rq1, reference_record)
    rq2 = {
        "status": "UNKNOWN",
        "reason": (
            "No complete obligation denominator is bound to this exact A0.1 target; the "
            "historical six-obligation count and two PILOT-02 diagnostics do not establish it. "
            "Exact-pair semantic proofs are also absent."
        ),
        "required_obligation_set_bound": False,
        "same_denominator_for_arms": False,
        "result_path": None,
        "diagnostic_pairs_path": "semantic_pair_verification.json",
    }
    incomplete = [
        "RQ1 target-operation reference unavailable",
        "RQ2 target-bound complete obligation denominator unavailable",
        "independent exact-pair semantic proofs unavailable",
    ]
    linter = next(
        (row for row in evaluator_records if row.get("evaluator_id") == "import_linter"), None
    )
    if linter is None or linter.get("compliance_verdict") == "NOT_EVALUABLE":
        incomplete.append("B0 Import Linter scope does not resolve against A0.1 modules")
    elif linter.get("compliance_verdict") == "UNKNOWN":
        incomplete.append("B0 Import Linter outcome is unresolved")
    if p_governance != "ACCEPT":
        incomplete.append(
            "P produced no governance-accepted prediction under the DRAFT/OPEN policy source"
        )
    all_artifacts = _artifact_inventory(
        run_root,
        excluded={"execution_manifest.json", "SHA256SUMS", "FINAL_SHA256SUMS"},
    )
    return {
        "schema_version": 1,
        "study_id": "DEV-B0P-V1",
        "run_id": run_id,
        "execution_status": "EXECUTED_PARTIAL",
        "execution_mode": dict(execution_mode),
        "exposure_class": "CALIBRATION_EXPOSED",
        "preparation": {
            "run_id": preparation["run_id"],
            "manifest_path": "preparation_snapshot/study_manifest.json",
            "manifest_sha256": preparation_digest,
            "verified": True,
            "snapshot_path": "preparation_snapshot",
        },
        "source_revisions": {
            key: preparation["source_revisions"][key]
            for key in (
                "architecture_before_sha",
                "architecture_after_sha",
                "b0_source_sha",
                "p_source_sha",
                "policy_source_sha",
            )
        },
        "arms": arm_records,
        "candidate_validation": {
            "B0": str(b0_execution["candidate_validation"]),
            "P": str(p_execution["candidate_validation"]),
        },
        "governance_decision": {
            "B0": "NOT_APPLICABLE",
            "P": p_governance,
            "P_reason_codes": list(p_execution["governance_reason_codes"]),
        },
        "evaluator_execution": {
            "status": "COMPLETED" if len(evaluator_records) == 2 else "PARTIAL",
            "observations": list(evaluator_records),
            "evaluator_time_ns": evaluator_duration_ns,
            "verification_time_ns": verification_duration_ns,
        },
        "semantic_pair_verification": {
            "status": "UNKNOWN",
            "independently_verified_pair_count": 0,
            "unknown_pair_count": len(pair_verification["pairs"]),
            "pairs": list(pair_verification["pairs"]),
            "reason_codes": list(pair_verification["reason_codes"]),
        },
        "rq1_scoring": rq1,
        "rq2_scoring": rq2,
        "evidence_completeness": {"status": "PARTIAL", "missing_or_unknown": incomplete},
        "research_gates": {
            "G1": "INCOMPLETE",
            "G4": "NOT AUTHORIZED",
            "P_ALGORITHM_STATUS": "NOT_READY",
        },
        "runtime_contexts": dict(runtime_contexts),
        "runtime_images": {key: dict(value) for key, value in runtime_images.items()},
        "resource_metrics": {
            "status": "UNKNOWN",
            "host_cpu_time_ns": None,
            "container_cpu_time_ns": None,
            "peak_rss_bytes": None,
            "reason": "No resource sampler was configured for this DEVELOPMENT run.",
        },
        "artifacts": all_artifacts,
    }


def verify_development_execution(
    run_directory: Path,
    *,
    repository: Path | None = None,
) -> dict[str, Any]:
    """Verify the execution contract, copied preparation, sealed outputs and all artifact hashes."""
    if run_directory.is_symlink():
        raise B0PExecutionError("Execution directory must not be a symlink")
    root = run_directory.resolve(strict=True)
    manifest_path = root / "execution_manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise B0PExecutionError("Execution manifest is missing or a symlink")
    manifest = cast(dict[str, Any], json.loads(manifest_path.read_text(encoding="utf-8")))
    validate_payload(EXECUTION_SCHEMA, manifest)
    if manifest["run_id"] != root.name:
        raise B0PExecutionError("Execution run ID differs from its directory")
    execution_mode = manifest["execution_mode"]
    recovery_path = root / "execution_recovery.json"
    if execution_mode["kind"] == "POST_EXECUTION_FINALIZATION":
        if execution_mode["source_attempt_run_id"] != root.name or not recovery_path.is_file():
            raise B0PExecutionError("Post-execution finalization lacks its recovery record")
        recovery = cast(dict[str, Any], json.loads(recovery_path.read_text(encoding="utf-8")))
        if (
            recovery.get("run_id") != root.name
            or recovery.get("method_outputs_reused") is not True
            or recovery.get("method_invocations_repeated") is not False
            or recovery.get("prediction_seals_reused") is not True
            or recovery.get("original_failure_sha256")
            != sha256_file(_safe_path(root, str(recovery.get("original_failure_path"))))
            or recovery.get("original_checksum_inventory_sha256")
            != sha256_file(_safe_path(root, str(recovery.get("original_checksum_inventory_path"))))
        ):
            raise B0PExecutionError("Post-execution recovery record is inconsistent")
    elif recovery_path.exists() or (root / "FINAL_SHA256SUMS").exists():
        raise B0PExecutionError("Direct execution cannot contain post-execution recovery artifacts")
    prep_root = _safe_path(root, manifest["preparation"]["snapshot_path"])
    prep_manifest_path = _safe_path(root, manifest["preparation"]["manifest_path"])
    if sha256_file(prep_manifest_path) != manifest["preparation"]["manifest_sha256"]:
        raise B0PExecutionError("Copied preparation manifest digest mismatch")
    prep_manifest = cast(dict[str, Any], json.loads(prep_manifest_path.read_text(encoding="utf-8")))
    if prep_manifest.get("run_id") != manifest["preparation"]["run_id"]:
        raise B0PExecutionError("Execution continuation references another preparation run")
    _verify_preparation_snapshot(prep_root, prep_manifest)
    _verify_runtime_contexts(root, manifest)
    _verify_runtime_images(root, manifest)
    for arm_key, arm in manifest["arms"].items():
        _validate_completed_arm_prediction(arm_key, arm)
        if arm["status"] != "COMPLETED":
            continue
        expected_source = manifest["source_revisions"][
            "b0_source_sha" if arm_key == "B0" else "p_source_sha"
        ]
        expected_bundle = prep_manifest["b0" if arm_key == "B0" else "method_p"][
            "input_bundle_sha256"
        ]
        if arm["source_sha"] != expected_source or arm["input_bundle_sha256"] != expected_bundle:
            raise B0PExecutionError(f"{arm_key} arm source or input bundle binding mismatch")
        if arm["runtime_image_id"] != manifest["runtime_images"][arm_key]["image_id"]:
            raise B0PExecutionError(f"{arm_key} arm runtime image identity mismatch")
        for stream in ("stdout", "stderr"):
            path = _safe_path(root, arm[f"{stream}_path"])
            if sha256_file(path) != arm[f"{stream}_sha256"]:
                raise B0PExecutionError(f"{arm_key} container {stream} digest mismatch")
        trace_path = _safe_path(root, arm["trace_path"])
        if sha256_file(trace_path) != arm["trace_sha256"]:
            raise B0PExecutionError(f"{arm_key} method trace digest mismatch")
        if arm.get("candidate_path") is not None:
            candidate_path = _safe_path(root, arm["candidate_path"])
            if sha256_file(candidate_path) != arm["candidate_sha256"]:
                raise B0PExecutionError(f"{arm_key} candidate digest mismatch")
        prediction_path = arm.get("prediction_path")
        if arm["prediction_status"] == "SEALED":
            if not isinstance(prediction_path, str):
                raise B0PExecutionError(f"{arm_key} sealed prediction path is missing")
            sealed = load_verified_prediction(_safe_path(root, prediction_path))
            if sealed.sha256 != arm["prediction_sha256"]:
                raise B0PExecutionError(f"{arm_key} sealed prediction digest mismatch")
            binding_error = _prediction_binding_error(
                sealed.payload,
                method_id=arm_key,
                architecture_source_sha=manifest["source_revisions"]["architecture_after_sha"],
                input_bundle_sha256=expected_bundle,
            )
            if binding_error:
                raise B0PExecutionError(f"{arm_key} sealed prediction {binding_error}")
            if arm_key == "P" and manifest["governance_decision"]["P"] != "ACCEPT":
                raise B0PExecutionError("P cannot seal a prediction unless governance accepted")
        elif arm_key == "P":
            if not isinstance(prediction_path, str):
                raise B0PExecutionError("P HOLD marker path is missing")
            marker_path = _safe_path(root, prediction_path)
            if sha256_file(marker_path) != arm["prediction_sha256"]:
                raise B0PExecutionError("P no-prediction marker digest mismatch")
            marker = cast(dict[str, Any], json.loads(marker_path.read_text(encoding="utf-8")))
            _verify_p_unsealed_marker(
                marker,
                governance_result=manifest["governance_decision"]["P"],
                arm_prediction_status=arm["prediction_status"],
                architecture_source_sha=manifest["source_revisions"]["architecture_after_sha"],
                input_bundle_sha256=expected_bundle,
            )
    for observation in manifest["evaluator_execution"]["observations"]:
        if observation["run_id"] != manifest["run_id"]:
            raise B0PExecutionError("Evaluator output was reused from another run")
        for stream in ("stdout", "stderr"):
            path = _safe_path(root, observation[f"{stream}_path"])
            if sha256_file(path) != observation[f"{stream}_sha256"]:
                raise B0PExecutionError(f"Evaluator {stream} digest mismatch")
        if observation["source_revision"] != manifest["source_revisions"]["architecture_after_sha"]:
            raise B0PExecutionError("Evaluator evidence is bound to another target source")
        if (
            observation["evaluator_id"] == "import_linter"
            and observation["configuration_sha256"]
            != prep_manifest["b0"]["evaluator_configuration_sha256"]
        ):
            raise B0PExecutionError("Import Linter configuration digest differs from frozen B0")
    reference_path = _safe_path(root, manifest["rq1_scoring"]["reference_path"])
    if sha256_file(reference_path) != manifest["rq1_scoring"]["reference_sha256"]:
        raise B0PExecutionError("RQ1 reference-availability record digest mismatch")
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    _validate_rq1_claims(manifest["rq1_scoring"], reference)
    _validate_rq2_claims(manifest["rq2_scoring"], manifest["semantic_pair_verification"])
    _validate_unknown_resource_metrics(manifest["resource_metrics"])
    if manifest["semantic_pair_verification"]["independently_verified_pair_count"]:
        if manifest["semantic_pair_verification"]["status"] not in {"VERIFIED", "PARTIAL"}:
            raise B0PExecutionError("Verified pair count conflicts with semantic-pair status")
    artifact_inventory = manifest["artifacts"]
    for relative_path, expected_sha in artifact_inventory.items():
        path = _safe_path(root, relative_path)
        if sha256_file(path) != expected_sha:
            raise B0PExecutionError(f"Execution artifact digest mismatch: {relative_path}")
    _verify_run_inventory(root)
    if repository is not None:
        source_root = repository.resolve(strict=True)
        original_prep = source_root / "experiments/results" / str(manifest["preparation"]["run_id"])
        if original_prep.is_dir() and not original_prep.is_symlink():
            original_manifest = verify_study_manifest(original_prep, source_root)
            if (
                sha256_file(original_prep / "study_manifest.json")
                != manifest["preparation"]["manifest_sha256"]
            ):
                raise B0PExecutionError(
                    "Original preparation manifest differs from the execution continuation"
                )
            _verify_preparation_snapshot(prep_root, original_manifest)
        else:
            # Clean archive extraction has no repository-side preparation directory.
            _verify_preparation_snapshot(prep_root, prep_manifest)
    return {
        "execution_status": manifest["execution_status"],
        "run_id": manifest["run_id"],
        "artifact_count": len(artifact_inventory),
        "preparation_manifest_sha256": manifest["preparation"]["manifest_sha256"],
        "B0_prediction_status": manifest["arms"]["B0"]["prediction_status"],
        "P_prediction_status": manifest["arms"]["P"]["prediction_status"],
        "governance_status": manifest["governance_decision"]["P"],
        "verified": True,
    }


def create_evidence_archive(run_directory: Path) -> tuple[Path, str]:
    """Create an external ZIP and SHA-256 sidecar for a finalized execution package."""
    run_root = run_directory.resolve(strict=True)
    _verify_run_inventory(run_root)
    archive = run_root.parent / f"{run_root.name}.zip"
    sidecar = run_root.parent / f"{run_root.name}.zip.sha256"
    if archive.exists() or sidecar.exists():
        raise B0PExecutionError("Evidence archive paths are write-once")
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for path in sorted(item for item in run_root.rglob("*") if item.is_file()):
            output.write(path, Path(run_root.name) / path.relative_to(run_root))
    digest = sha256_file(archive)
    sidecar_content = f"{digest}  {archive.name}\n".encode("ascii")
    descriptor = os.open(sidecar, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(descriptor, "wb") as output:
        output.write(sidecar_content)
        output.flush()
        os.fsync(output.fileno())
    sidecar.chmod(0o444)
    return archive, digest


def _write_reference_availability(run_root: Path, preparation: Mapping[str, Any]) -> None:
    payload = {
        "schema_version": 1,
        "study_id": "DEV-B0P-V1",
        "run_id": run_root.name,
        "status": "NOT_ESTABLISHED_BEFORE_PREDICTIONS",
        "exposure_class": "CALIBRATION_EXPOSED",
        "architecture_source_sha": preparation["source_revisions"]["architecture_after_sha"],
        "expected_operations": None,
        "complete_typed_target_universe": None,
        "reason": (
            "The independently verified preparation contains no exact-target expected-operation "
            "map. No source-grounded reference was fixed and sealed before arm outputs. The scorer "
            "was not invoked and no private DA01 ground-truth file was read."
        ),
    }
    _write_once(run_root / "reference/reference_availability.json", payload)


def _record_host_environment(
    run_root: Path,
    *,
    docker_executable: str,
    uv_executable: str,
    repository: Path,
) -> None:
    docker = shutil.which(docker_executable)
    uv = shutil.which(uv_executable)
    if docker is None or uv is None:
        raise B0PExecutionError("Docker and uv are required to record the execution environment")
    docker_version = (
        _run_checked(
            [docker, "version", "--format", "{{.Client.Version}}/{{.Server.Version}}"],
            cwd=repository,
            label="record Docker client/server versions",
            timeout=30,
        )
        .stdout.decode("utf-8")
        .strip()
    )
    uv_version = (
        _run_checked(
            [uv, "--version"],
            cwd=repository,
            label="record uv version",
            timeout=30,
        )
        .stdout.decode("utf-8")
        .strip()
    )
    _write_once(
        run_root / "execution_environment.json",
        {
            "schema_version": 1,
            "host_python": platform.python_version(),
            "docker_client_server": docker_version,
            "uv": uv_version,
            "method_base_image": BASE_IMAGE,
            "method_runtime_requirements": RUNTIME_REQUIREMENTS.splitlines(),
            "method_runtime_network": "disabled",
        },
    )


def _verify_evaluator_records(
    run_root: Path,
    records: Sequence[Mapping[str, Any]],
    preparation: Mapping[str, Any],
) -> None:
    expected_ids = {"import_linter", "pytest_architecture"}
    if {str(record.get("evaluator_id")) for record in records} != expected_ids:
        raise B0PExecutionError("Fresh evaluator record set is incomplete or duplicated")
    target_sha = preparation["source_revisions"]["architecture_after_sha"]
    for record in records:
        if record.get("run_id") != run_root.name:
            raise B0PExecutionError("Evaluator record is bound to another run ID")
        if record.get("source_revision") != target_sha:
            raise B0PExecutionError("Evaluator record is bound to another architecture SHA")
    b0_input_manifest = json.loads(
        (run_root / "preparation_snapshot/method_inputs/b0/method_input.json").read_text(
            encoding="utf-8"
        )
    )
    target_tree_sha = b0_input_manifest["after_tree_sha"]
    for record in records:
        if record.get("source_tree_sha") != target_tree_sha:
            raise B0PExecutionError("Evaluator record is bound to another target source tree")
        for stream in ("stdout", "stderr"):
            path = _safe_path(run_root, str(record[f"{stream}_path"]))
            if sha256_file(path) != record[f"{stream}_sha256"]:
                raise B0PExecutionError(f"Fresh evaluator {stream} digest mismatch")
        if (
            record.get("evaluator_id") == "import_linter"
            and record.get("configuration_sha256")
            != preparation["b0"]["evaluator_configuration_sha256"]
        ):
            raise B0PExecutionError("Fresh Import Linter configuration is not frozen B0")


def _build_runtime_context(
    run_root: Path,
    *,
    method_id: str,
    source_sha: str,
    prep_manifest: Mapping[str, Any],
    repository: Path,
) -> tuple[Path, str]:
    context = run_root / "container_context" / method_id
    context.mkdir(parents=True)
    source_rows: dict[str, str] = {}
    if method_id == "P":
        rows = prep_manifest["method_p"]["source_inventory"]
        row_map = {str(row["path"]): str(row["sha256"]) for row in rows}
        selected = sorted(
            path for path in row_map if path.startswith("experiments/execution/tooling/p_")
        )
        selected.extend(
            path
            for path in row_map
            if path
            in {
                "experiments/execution/tooling/contracts.py",
                "experiments/execution/tooling/errors.py",
                "experiments/execution/tooling/hashing.py",
                "experiments/execution/tooling/inputs.py",
            }
        )
        for path in selected:
            _copy_git_blob(repository, source_sha, path, context, row_map[path])
            source_rows[path] = row_map[path]
        for path in (
            "experiments/execution/contracts/fact_vocabulary_v1.json",
            "fitness/catalog/architectural-obligations.yaml",
        ):
            content = _git_blob(repository, source_sha, path)
            _write_context_file(context, path, content)
            source_rows[path] = sha256_bytes(content)
        _copy_git_blob(
            repository,
            prep_manifest["source_revisions"]["b0_source_sha"],
            "experiments/execution/tooling/sealing.py",
            context,
            prep_manifest["instrumentation"]["prediction_sealer_sha256"],
        )
        source_rows["experiments/execution/tooling/sealing.py"] = prep_manifest["instrumentation"][
            "prediction_sealer_sha256"
        ]
        runner = Path(__file__).with_name("b0p_isolated_p_runner.py")
    else:
        rows = prep_manifest["b0"]["source_inventory"]
        row_map = {str(row["path"]): str(row["sha256"]) for row in rows}
        selected = sorted(row_map)
        for path in selected:
            _copy_git_blob(repository, source_sha, path, context, row_map[path])
            source_rows[path] = row_map[path]
        input_path = "experiments/execution/tooling/inputs.py"
        input_source_sha = prep_manifest["source_revisions"]["b0_source_sha"]
        input_bytes = _git_blob(repository, input_source_sha, input_path)
        input_sha = sha256_bytes(input_bytes)
        _write_context_file(context, input_path, input_bytes)
        source_rows[input_path] = input_sha
        _copy_git_blob(
            repository,
            source_sha,
            "experiments/execution/tooling/sealing.py",
            context,
            prep_manifest["instrumentation"]["prediction_sealer_sha256"],
        )
        source_rows["experiments/execution/tooling/sealing.py"] = prep_manifest["instrumentation"][
            "prediction_sealer_sha256"
        ]
        runner = Path(__file__).with_name("b0p_isolated_b0_runner.py")

    schema_source_sha = source_sha
    schema_paths = sorted(
        PurePosixPath(path).name
        for path in _git_paths(repository, schema_source_sha, "experiments/execution/schemas")
        if PurePosixPath(path).name.endswith(".schema.json")
        and PurePosixPath(path).name not in SCORER_SCHEMA_FILES
    )
    for name in schema_paths:
        relative = f"experiments/execution/schemas/{name}"
        content = _git_blob(repository, schema_source_sha, relative)
        _write_context_file(context, relative, content)
        source_rows[relative] = sha256_bytes(content)

    runner_bytes = runner.read_bytes()
    runner_rel = f"experiments/execution/tooling/{runner.name}"
    _write_context_file(context, runner_rel, runner_bytes)
    source_rows[runner_rel] = sha256_bytes(runner_bytes)
    for init in (
        "experiments/__init__.py",
        "experiments/execution/__init__.py",
        "experiments/execution/tooling/__init__.py",
    ):
        _write_context_file(context, init, b'"""Isolated EvoFitBench runtime package."""\n')
        source_rows[init] = sha256_bytes((context / init).read_bytes())

    _write_bytes_once(context / "requirements.txt", RUNTIME_REQUIREMENTS.encode("ascii"))
    source_rows["requirements.txt"] = sha256_file(context / "requirements.txt")
    fitness_copy = "COPY fitness /opt/evofit/fitness\n" if method_id == "P" else ""
    dockerfile = (
        f"FROM {BASE_IMAGE}\n"
        "ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/opt/evofit\n"
        "WORKDIR /opt/evofit\n"
        "COPY requirements.txt /tmp/requirements.txt\n"
        "RUN python -m pip install --no-cache-dir --require-hashes "
        "--requirement /tmp/requirements.txt\n"
        "COPY experiments /opt/evofit/experiments\n"
        + fitness_copy
        + "USER 65532:65532\n"
        + 'ENTRYPOINT ["python", "-m", "experiments.execution.tooling.'
        + runner.stem
        + '"]\n'
    )
    _write_bytes_once(context / "Dockerfile", dockerfile.encode("ascii"))
    source_rows["Dockerfile"] = sha256_file(context / "Dockerfile")
    source_manifest = {
        "schema_version": 1,
        "method_id": method_id,
        "algorithm_source_sha": source_sha,
        "base_image": BASE_IMAGE,
        "files": dict(sorted(source_rows.items())),
    }
    _write_once(context / "runtime_source_manifest.json", source_manifest)
    _write_context_sha256sums(context)
    context_digest = _directory_digest(context)
    return context, context_digest


def _build_image(
    context: Path,
    run_id: str,
    method_label: str,
    docker_executable: str,
    repository: Path,
) -> dict[str, str]:
    executable = shutil.which(docker_executable)
    if executable is None:
        raise B0PExecutionError(
            "Docker executable is unavailable; isolated method execution was not attempted"
        )
    tag = f"evofitbench:{run_id}-{method_label}"
    build = _run_checked(
        [executable, "build", "--pull=false", "--tag", tag, str(context)],
        cwd=repository,
        label=f"build {method_label} runtime image",
        timeout=600,
    )
    run_root = context.parent.parent
    stdout_path = run_root / "raw" / f"{method_label}_image_build.stdout.bin"
    stderr_path = run_root / "raw" / f"{method_label}_image_build.stderr.bin"
    _write_bytes_once(stdout_path, build.stdout)
    _write_bytes_once(stderr_path, build.stderr)
    inspect = _run_checked(
        [executable, "image", "inspect", "--format", "{{.Id}}", tag],
        cwd=repository,
        label=f"inspect {method_label} runtime image",
        timeout=30,
    )
    image_id = inspect.stdout.decode().strip()
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", image_id):
        raise B0PExecutionError(f"Docker returned an invalid image identity for {method_label}")
    return {
        "tag": tag,
        "image_id": image_id,
        "context_sha256": _directory_digest(context),
        "build_stdout_path": stdout_path.relative_to(run_root).as_posix(),
        "build_stdout_sha256": sha256_bytes(build.stdout),
        "build_stderr_path": stderr_path.relative_to(run_root).as_posix(),
        "build_stderr_sha256": sha256_bytes(build.stderr),
    }


def _recover_runtime_image(
    run_root: Path,
    method_id: str,
    docker_executable: str,
) -> dict[str, str]:
    """Read back the run-unique image and build streams without rebuilding it."""
    method_label = method_id.lower()
    tag = f"evofitbench:{run_root.name}-{method_label}"
    docker = shutil.which(docker_executable)
    if docker is None:
        raise B0PExecutionError("Docker is unavailable for image identity readback")
    image_id = (
        _run_checked(
            [docker, "image", "inspect", "--format", "{{.Id}}", tag],
            cwd=run_root,
            label=f"read back {method_id} runtime image identity",
            timeout=30,
        )
        .stdout.decode("utf-8")
        .strip()
    )
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", image_id):
        raise B0PExecutionError(f"Docker returned an invalid image identity for {method_id}")
    context = run_root / "container_context" / method_id
    build_stdout = run_root / "raw" / f"{method_label}_image_build.stdout.bin"
    build_stderr = run_root / "raw" / f"{method_label}_image_build.stderr.bin"
    for path in (build_stdout, build_stderr):
        if not path.is_file() or path.is_symlink():
            raise B0PExecutionError(f"{method_id} image build stream is missing")
    return {
        "tag": tag,
        "image_id": image_id,
        "context_sha256": _directory_digest(context),
        "build_stdout_path": build_stdout.relative_to(run_root).as_posix(),
        "build_stdout_sha256": sha256_file(build_stdout),
        "build_stderr_path": build_stderr.relative_to(run_root).as_posix(),
        "build_stderr_sha256": sha256_file(build_stderr),
    }


def _recover_completed_arm(
    run_root: Path,
    method_id: str,
    runtime_image: Mapping[str, str],
) -> dict[str, Any]:
    """Reconstruct an arm record from its persisted runner response and output files."""
    output = run_root / method_id
    label = method_id.lower()
    stdout_path = run_root / "raw" / f"{label}_container.stdout.bin"
    stderr_path = run_root / "raw" / f"{label}_container.stderr.bin"
    if any(not path.is_file() or path.is_symlink() for path in (stdout_path, stderr_path)):
        raise B0PExecutionError(f"{method_id} persisted container streams are incomplete")
    try:
        stdout_result = cast(dict[str, Any], json.loads(stdout_path.read_bytes()))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise B0PExecutionError(
            f"{method_id} persisted container stdout is not result JSON"
        ) from error
    if method_id == "B0":
        result_path = output / "execution_trace.json"
        result = cast(dict[str, Any], json.loads(result_path.read_text(encoding="utf-8")))
        if stdout_result.get("execution_trace_sha256") != sha256_file(result_path):
            raise B0PExecutionError("B0 persisted stdout does not bind its execution trace")
    else:
        result_path = output / "execution_result.json"
        result = cast(dict[str, Any], json.loads(result_path.read_text(encoding="utf-8")))
        if stdout_result.get("execution_result_sha256") != sha256_file(result_path):
            raise B0PExecutionError("P persisted stdout does not bind its execution result")
    for key in (
        "method_id",
        "method_version",
        "architecture_source_sha",
        "input_bundle_sha256",
        "method_execution_time_ns",
        "adaptation_time_ns",
        "candidate_validation",
    ):
        if stdout_result.get(key) != result.get(key):
            raise B0PExecutionError(f"{method_id} stdout/result mismatch for {key}")
    if method_id == "P":
        for key in (
            "governance_result",
            "governance_reason_codes",
            "prediction_status",
            "prediction_sha256",
        ):
            if stdout_result.get(key) != result.get(key):
                raise B0PExecutionError(f"P stdout/result mismatch for {key}")
    return {
        **result,
        "docker_exit_status": 0,
        "docker_runtime_ns": None,
        "runtime_image_id": runtime_image["image_id"],
        "stdout_path": stdout_path.relative_to(run_root).as_posix(),
        "stdout_sha256": sha256_file(stdout_path),
        "stderr_path": stderr_path.relative_to(run_root).as_posix(),
        "stderr_sha256": sha256_file(stderr_path),
    }


def _verify_recovered_predictions(
    run_root: Path,
    preparation: Mapping[str, Any],
    p_execution: Mapping[str, Any],
) -> None:
    architecture_sha = str(preparation["source_revisions"]["architecture_after_sha"])
    b0_bundle = str(preparation["b0"]["input_bundle_sha256"])
    b0 = load_verified_prediction(run_root / "B0/prediction")
    if (
        b0.sha256
        != json.loads((run_root / "B0/execution_trace.json").read_text(encoding="utf-8"))[
            "prediction_sha256"
        ]
    ):
        raise B0PExecutionError("Recovered B0 seal differs from its execution trace")
    binding_error = _prediction_binding_error(
        b0.payload,
        method_id="B0",
        architecture_source_sha=architecture_sha,
        input_bundle_sha256=b0_bundle,
    )
    if binding_error:
        raise B0PExecutionError(f"Recovered B0 prediction {binding_error}")
    p_bundle = str(preparation["method_p"]["input_bundle_sha256"])
    if p_execution.get("prediction_status") == "SEALED":
        p = load_verified_prediction(run_root / "P/prediction")
        if p.sha256 != p_execution.get("prediction_sha256"):
            raise B0PExecutionError("Recovered P seal differs from its execution result")
        binding_error = _prediction_binding_error(
            p.payload,
            method_id="P",
            architecture_source_sha=architecture_sha,
            input_bundle_sha256=p_bundle,
        )
        if binding_error:
            raise B0PExecutionError(f"Recovered P prediction {binding_error}")
    else:
        marker_path = run_root / "P/prediction_not_emitted.json"
        marker = cast(dict[str, Any], json.loads(marker_path.read_text(encoding="utf-8")))
        if sha256_file(marker_path) != p_execution.get("prediction_sha256"):
            raise B0PExecutionError("Recovered P no-prediction marker digest mismatch")
        _verify_p_unsealed_marker(
            marker,
            governance_result=str(p_execution["governance_result"]),
            arm_prediction_status=str(p_execution["prediction_status"]),
            architecture_source_sha=architecture_sha,
            input_bundle_sha256=p_bundle,
        )


def _run_isolated_arm(
    *,
    method_id: str,
    image: Mapping[str, str],
    input_directory: Path,
    output_directory: Path,
    preparation: Mapping[str, Any],
    docker_executable: str,
    repository: Path,
) -> dict[str, Any]:
    docker = shutil.which(docker_executable)
    if docker is None:
        raise B0PExecutionError("Docker executable disappeared before arm execution")
    input_root = input_directory.resolve(strict=True)
    output_root = output_directory.resolve(strict=True)
    if input_root.is_symlink() or output_root.is_symlink():
        raise B0PExecutionError(f"{method_id} input/output directory must not be a symlink")
    output_root.chmod(0o777)
    command = [
        docker,
        "run",
        "--rm",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=128",
        "--memory=1g",
        "--cpus=2",
        "--user=65532:65532",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=64m",  # nosec B108 - bounded container-local tmpfs  # noqa: S108
        "--mount",
        f"type=bind,source={input_root},target=/input,readonly",
        "--mount",
        f"type=bind,source={output_root},target=/output",
        str(image["tag"]),
    ]
    source = preparation["source_revisions"]
    if method_id == "B0":
        command.extend(
            [
                "--architecture-source-sha",
                source["architecture_after_sha"],
                "--expected-bundle-sha256",
                preparation["b0"]["input_bundle_sha256"],
                "--configuration-sha256",
                preparation["b0"]["configuration_sha256"],
                "--evaluator-configuration-sha256",
                preparation["b0"]["evaluator_configuration_sha256"],
            ]
        )
    else:
        command.extend(
            [
                "--architecture-source-sha",
                source["architecture_after_sha"],
                "--expected-bundle-sha256",
                preparation["method_p"]["input_bundle_sha256"],
            ]
        )
    raw_root = output_directory.parent / "raw"
    raw_root.mkdir(exist_ok=True)
    stdout_path = raw_root / f"{method_id.lower()}_container.stdout.bin"
    stderr_path = raw_root / f"{method_id.lower()}_container.stderr.bin"
    started_ns = time.perf_counter_ns()
    completed = subprocess.run(  # nosec B603 - fixed Docker argv with verified bind mounts  # noqa: S603
        command,
        cwd=repository,
        check=False,
        capture_output=True,
        timeout=900,
    )
    duration_ns = time.perf_counter_ns() - started_ns
    _write_bytes_once(stdout_path, completed.stdout)
    _write_bytes_once(stderr_path, completed.stderr)
    if completed.returncode != 0:
        raise B0PExecutionError(
            f"{method_id} container exited {completed.returncode}; "
            f"stdout={stdout_path.relative_to(output_directory.parent)}, "
            f"stderr={stderr_path.relative_to(output_directory.parent)}"
        )
    try:
        stdout_result = cast(dict[str, Any], json.loads(completed.stdout))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise B0PExecutionError(f"{method_id} container did not emit its result JSON") from error
    if method_id == "B0":
        trace = cast(
            dict[str, Any],
            json.loads((output_directory / "execution_trace.json").read_text(encoding="utf-8")),
        )
        if stdout_result.get("execution_trace_sha256") != sha256_file(
            output_directory / "execution_trace.json"
        ):
            raise B0PExecutionError("B0 stdout result differs from its persisted execution trace")
        result_fields = {
            "candidate_validation": trace["candidate_validation"],
            "method_version": trace["method_version"],
            "method_execution_time_ns": trace["method_execution_time_ns"],
            "adaptation_time_ns": trace["adaptation_time_ns"],
        }
    else:
        result_path = output_directory / "execution_result.json"
        result = cast(dict[str, Any], json.loads(result_path.read_text(encoding="utf-8")))
        if stdout_result.get("execution_result_sha256") != sha256_file(result_path):
            raise B0PExecutionError("P stdout result differs from its persisted execution result")
        result_fields = result
    return {
        "docker_exit_status": completed.returncode,
        "docker_runtime_ns": duration_ns,
        "stdout_path": stdout_path.relative_to(output_directory.parent).as_posix(),
        "stdout_sha256": sha256_bytes(completed.stdout),
        "stderr_path": stderr_path.relative_to(output_directory.parent).as_posix(),
        "stderr_sha256": sha256_bytes(completed.stderr),
        "runtime_image_id": image["image_id"],
        "command": command,
        **result_fields,
    }


def _run_evaluators(
    run_root: Path,
    preparation: Mapping[str, Any],
    *,
    uv_executable: str,
    repository: Path,
    label_prefix: str = "",
) -> tuple[list[dict[str, Any]], int]:
    uv = shutil.which(uv_executable)
    if uv is None:
        raise B0PExecutionError("uv is unavailable; fresh evaluator execution was not attempted")
    source = preparation["source_revisions"]
    after_sha = source["architecture_after_sha"]
    b0_input_manifest = json.loads(
        (run_root / "preparation_snapshot/method_inputs/b0/method_input.json").read_text(
            encoding="utf-8"
        )
    )
    source_tree_sha = str(b0_input_manifest["after_tree_sha"])
    _assert_evaluator_source(repository, after_sha)
    input_b0 = run_root / "preparation_snapshot/method_inputs/b0"
    evaluator_config = input_b0 / "fitness/a0-importlinter.toml"
    configuration = evaluator_config.read_bytes()
    if sha256_bytes(configuration) != preparation["b0"]["evaluator_configuration_sha256"]:
        raise B0PExecutionError("Fresh evaluator configuration no longer matches frozen B0 bytes")
    facts = json.loads((run_root / "preparation_snapshot/architecture_facts.json").read_text())
    module_scope = inspect_import_linter_scope(
        configuration,
        set(str(item) for item in facts.get("after_module_names", [])),
    )
    command = [uv, "run", "--frozen", "lint-imports", "--config", str(evaluator_config)]
    record, duration_ns = _run_evaluator_command(
        run_root,
        f"{label_prefix}b0_import_linter",
        command,
        evaluator_id="import_linter",
        source_revision=after_sha,
        source_tree_sha=source_tree_sha,
        configuration_path="preparation_snapshot/method_inputs/b0/fitness/a0-importlinter.toml",
        configuration_sha256=preparation["b0"]["evaluator_configuration_sha256"],
        scope_assessment=module_scope,
        repository=repository,
        validity_verifier=lambda exit_status: "VALID" if exit_status is not None else "UNKNOWN",
        compliance_verifier=lambda exit_status: _import_linter_compliance(
            exit_status, module_scope
        ),
        version_package="import-linter",
    )
    records = [record]

    architecture_files = sorted(
        path
        for path in (repository / "tests/architecture").rglob("*")
        if path.is_file() and not path.is_symlink()
    )
    test_tree_digest = _paths_digest(repository, architecture_files)
    test_command = [
        uv,
        "run",
        "--frozen",
        "python",
        "-m",
        "pytest",
        "--no-cov",
        "-q",
        "tests/architecture",
    ]
    test_record, test_duration_ns = _run_evaluator_command(
        run_root,
        f"{label_prefix}architecture_pytest",
        test_command,
        evaluator_id="pytest_architecture",
        source_revision=after_sha,
        source_tree_sha=source_tree_sha,
        configuration_path="tests/architecture",
        configuration_sha256=test_tree_digest,
        scope_assessment={
            "test_file_count": len(architecture_files),
            "controlled_probes": "NOT_RUN",
        },
        repository=repository,
        validity_verifier=lambda exit_status: "VALID" if exit_status is not None else "UNKNOWN",
        compliance_verifier=lambda exit_status: (
            "COMPLIANT" if exit_status == 0 else "NON_COMPLIANT" if exit_status == 1 else "UNKNOWN"
        ),
        version_package="pytest",
    )
    records.append(test_record)
    return records, duration_ns + test_duration_ns


def _run_evaluator_command(
    run_root: Path,
    label: str,
    command: list[str],
    *,
    evaluator_id: str,
    source_revision: str,
    source_tree_sha: str,
    configuration_path: str,
    configuration_sha256: str,
    scope_assessment: Mapping[str, Any],
    repository: Path,
    validity_verifier: Any,
    compliance_verifier: Any,
    version_package: str,
) -> tuple[dict[str, Any], int]:
    started_ns = time.perf_counter_ns()
    try:
        completed = subprocess.run(  # nosec B603 - fixed uv evaluator argv  # noqa: S603
            command,
            cwd=repository,
            check=False,
            capture_output=True,
            timeout=600,
        )
        exit_status: int | None = completed.returncode
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
    stdout_path = run_root / "raw" / f"{label}.stdout.bin"
    stderr_path = run_root / "raw" / f"{label}.stderr.bin"
    _write_bytes_once(stdout_path, stdout)
    _write_bytes_once(stderr_path, stderr)
    try:
        evaluator_version = version(version_package)
    except PackageNotFoundError:
        evaluator_version = "UNKNOWN"
    return {
        "run_id": run_root.name,
        "evaluator_id": evaluator_id,
        "command": command,
        "exit_status": exit_status,
        "duration_ns": duration_ns,
        "source_revision": source_revision,
        "source_tree_sha": source_tree_sha,
        "configuration_path": configuration_path,
        "configuration_sha256": configuration_sha256,
        "stdout_path": stdout_path.relative_to(run_root).as_posix(),
        "stdout_sha256": sha256_bytes(stdout),
        "stderr_path": stderr_path.relative_to(run_root).as_posix(),
        "stderr_sha256": sha256_bytes(stderr),
        "evidence_validity": validity_verifier(exit_status),
        "compliance_verdict": compliance_verifier(exit_status),
        "semantic_adequacy": "UNKNOWN",
        "scope_assessment": {**dict(scope_assessment), "evaluator_version": evaluator_version},
    }, duration_ns


def _unknown_pair_verification(run_root: Path, p_output: Path) -> dict[str, Any]:
    trace_path = p_output / "method_p_trace.json"
    pairs: list[dict[str, Any]] = []
    if trace_path.is_file():
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        for role in ("current_pairs", "candidate_pairs"):
            for row in trace.get(role, []):
                pairs.append(
                    {
                        "representation_id": row.get("representation_id"),
                        "obligation_id": row.get("obligation_id"),
                        "architecture_source_sha": row.get("architecture_source_sha"),
                        "method_p_status": row.get("status"),
                        "method_p_semantic_proof_status": row.get("semantic_proof_status"),
                        "independent_verification": "UNKNOWN",
                        "reason_codes": ["NO_CURRENT_RUN_INDEPENDENT_EXACT_PAIR_PROOF"],
                        "source_role": role,
                    }
                )
    return {
        "schema_version": 1,
        "run_id": run_root.name,
        "status": "UNKNOWN",
        "independently_verified_pair_count": 0,
        "pairs": pairs,
        "reason_codes": [
            "NO_CURRENT_RUN_INDEPENDENT_EXACT_PAIR_PROOF",
            "P_TRACE_PAIR_VERDICTS_ARE_NOT_AN_INDEPENDENT_REFERENCE",
            "PILOT02_HISTORICAL_PAIR_OUTPUTS_NOT_REUSED",
        ],
    }


def _arm_manifest_record(
    method_id: str,
    output_directory: Path,
    execution: Mapping[str, Any],
    preparation: Mapping[str, Any],
    image: Mapping[str, str],
) -> dict[str, Any]:
    p_source = preparation["source_revisions"]["p_source_sha"]
    b0_source = preparation["source_revisions"]["b0_source_sha"]
    if method_id == "B0":
        trace = json.loads((output_directory / "execution_trace.json").read_text())
        prediction_status = "SEALED"
        prediction_path = "B0/prediction"
        prediction_sha = trace["prediction_sha256"]
        candidate_path = "B0/candidate_configuration.json"
        candidate_sha = sha256_file(output_directory / "candidate_configuration.json")
        method_version = trace["method_version"]
        input_sha = preparation["b0"]["input_bundle_sha256"]
        method_time = trace["method_execution_time_ns"]
        adaptation_time = 0
        trace_path = "B0/execution_trace.json"
        trace_sha = sha256_file(output_directory / "execution_trace.json")
    else:
        result = json.loads((output_directory / "execution_result.json").read_text())
        prediction_status = result["prediction_status"]
        prediction_path = (
            "P/prediction" if prediction_status == "SEALED" else "P/prediction_not_emitted.json"
        )
        prediction_sha = result["prediction_sha256"]
        candidate_path = (
            "P/candidate_configuration.json" if result["candidate_configuration_sha256"] else None
        )
        candidate_sha = result["candidate_configuration_sha256"]
        method_version = result["method_version"]
        input_sha = preparation["method_p"]["input_bundle_sha256"]
        method_time = result["method_execution_time_ns"]
        adaptation_time = result["adaptation_time_ns"]
        trace_path = "P/method_p_trace.json"
        trace_sha = sha256_file(output_directory / "method_p_trace.json")
    return {
        "method_id": method_id,
        "status": "COMPLETED",
        "method_version": method_version,
        "source_sha": b0_source if method_id == "B0" else p_source,
        "input_bundle_sha256": input_sha,
        "method_execution_time_ns": method_time,
        "adaptation_time_ns": adaptation_time,
        "prediction_status": prediction_status,
        "prediction_sha256": prediction_sha,
        "prediction_path": prediction_path,
        "trace_path": trace_path,
        "trace_sha256": trace_sha,
        "candidate_path": candidate_path,
        "candidate_sha256": candidate_sha,
        "runtime_image_id": image["image_id"],
        "stdout_path": execution["stdout_path"],
        "stdout_sha256": execution["stdout_sha256"],
        "stderr_path": execution["stderr_path"],
        "stderr_sha256": execution["stderr_sha256"],
    }


def _assert_evaluator_source(repository: Path, target_sha: str) -> None:
    command = ["git", "diff", "--quiet", target_sha, "--", *EVALUATOR_PATHS]
    completed = subprocess.run(  # nosec B603 - fixed Git argv with validated source SHA  # noqa: S603
        command, cwd=repository, check=False, capture_output=True, timeout=30
    )
    if completed.returncode != 0:
        raise B0PExecutionError(
            "Evaluator source checkout is not byte-identical to the target architecture revision"
        )


def _verify_preparation_snapshot(root: Path, manifest: Mapping[str, Any]) -> None:
    sums_path = root / "SHA256SUMS"
    if not sums_path.is_file() or sums_path.is_symlink():
        raise B0PExecutionError("Preparation snapshot checksum inventory is missing")
    declared: set[str] = set()
    for line in sums_path.read_text(encoding="ascii").splitlines():
        try:
            expected, relative = line.split("  ", maxsplit=1)
        except ValueError as error:
            raise B0PExecutionError("Malformed preparation checksum row") from error
        path = _safe_path(root, relative)
        if sha256_file(path) != expected:
            raise B0PExecutionError(f"Copied preparation artifact mismatch: {relative}")
        declared.add(relative)
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path != sums_path
    }
    if declared != actual:
        raise B0PExecutionError("Preparation snapshot checksum inventory is incomplete")
    b0 = verify_method_bundle(root / "method_inputs/b0", expected_method_id="B0")
    p = verify_method_bundle_v3(root / "method_inputs/p", expected_method_id="P")
    if b0.get("bundle_sha256") != manifest["b0"]["input_bundle_sha256"]:
        raise B0PExecutionError("Copied B0 bundle differs from the preparation manifest")
    if p.get("bundle_sha256") != manifest["method_p"]["input_bundle_sha256"]:
        raise B0PExecutionError("Copied P bundle differs from the preparation manifest")
    p_root = root / "method_inputs/p"
    p_manifest = json.loads((p_root / "method_input_v3.json").read_text(encoding="utf-8"))
    p_paths = [str(row["path"]).lower() for row in p_manifest.get("files", [])]
    if _contains_forbidden_method_input_path(p_paths):
        raise B0PExecutionError("P method input contains an oracle, scorer, or Git-history path")


def _contains_forbidden_method_input_path(paths: Sequence[str]) -> bool:
    markers = (".git", "ground_truth", "expected_operations", "scorer")
    return any(marker in path.lower() for path in paths for marker in markers)


def _prediction_binding_error(
    prediction: Mapping[str, Any],
    *,
    method_id: str,
    architecture_source_sha: str,
    input_bundle_sha256: str,
) -> str | None:
    if prediction.get("method_id") != method_id:
        return "method identity mismatch"
    if prediction.get("architecture_source_sha") != architecture_source_sha:
        return "architecture source mismatch"
    if prediction.get("input_bundle_sha256") != input_bundle_sha256:
        return "input bundle digest mismatch"
    return None


def _validate_completed_arm_prediction(arm_key: str, arm: Mapping[str, Any]) -> None:
    if arm_key == "B0" and arm.get("status") == "COMPLETED":
        if arm.get("prediction_status") != "SEALED":
            raise B0PExecutionError("A completed B0 arm must have a sealed prediction")
        if not isinstance(arm.get("prediction_path"), str) or not arm.get("prediction_path"):
            raise B0PExecutionError("A completed B0 arm prediction path is missing")
        if not isinstance(arm.get("prediction_sha256"), str):
            raise B0PExecutionError("A completed B0 arm prediction digest is missing")


def _validate_rq2_claims(
    rq2: Mapping[str, Any],
    semantic_pair_verification: Mapping[str, Any] | None = None,
) -> None:
    if rq2.get("status") in {"UNKNOWN", "NOT_EVALUABLE"} and (
        rq2.get("required_obligation_set_bound") or rq2.get("same_denominator_for_arms")
    ):
        raise B0PExecutionError(
            "Unknown RQ2 result cannot claim a bound shared obligation denominator"
        )
    if rq2.get("status") in {"SCORED", "PARTIAL"}:
        if not rq2.get("required_obligation_set_bound") or not rq2.get("same_denominator_for_arms"):
            raise B0PExecutionError("RQ2 score requires a bound shared obligation denominator")
        if semantic_pair_verification is None:
            raise B0PExecutionError("RQ2 score lacks independent exact-pair semantic proofs")
        pair_status = semantic_pair_verification.get("status")
        verified_pair_count = semantic_pair_verification.get("independently_verified_pair_count")
        verified_rows = sum(
            row.get("independent_verification") == "VERIFIED"
            for row in semantic_pair_verification.get("pairs", [])
            if isinstance(row, Mapping)
        )
        if (
            not isinstance(verified_pair_count, int)
            or verified_pair_count <= 0
            or verified_pair_count > verified_rows
            or pair_status not in {"VERIFIED", "PARTIAL"}
        ):
            raise B0PExecutionError("RQ2 score lacks independent exact-pair semantic proofs")
        if rq2.get("status") == "SCORED" and pair_status != "VERIFIED":
            raise B0PExecutionError("A complete RQ2 score requires fully verified exact pairs")


def _validate_rq1_claims(rq1: Mapping[str, Any], reference: Mapping[str, Any] | None) -> None:
    if reference is None:
        raise B0PExecutionError("RQ1 reference-availability record is missing")
    if rq1.get("status") == "SCORED":
        raise B0PExecutionError("This continuation has no admissible RQ1 scoring reference")
    if rq1.get("scorer_invoked"):
        raise B0PExecutionError("RQ1 scorer cannot run without an admissible reference")
    if reference.get("status") != "NOT_ESTABLISHED_BEFORE_PREDICTIONS":
        raise B0PExecutionError("Unavailable RQ1 reference record has an incompatible status")


def _validate_unknown_resource_metrics(metrics: Mapping[str, Any]) -> None:
    if metrics.get("status") == "UNKNOWN" and any(
        metrics.get(field) is not None
        for field in ("host_cpu_time_ns", "container_cpu_time_ns", "peak_rss_bytes")
    ):
        raise B0PExecutionError("Unknown resource metrics cannot contain measured values")


def _expected_prediction_status(governance_result: str) -> str:
    if governance_result == "ACCEPT":
        return "SEALED"
    if governance_result == "HOLD":
        return "NOT_EMITTED_GOVERNANCE_HOLD"
    if governance_result in {"REJECT", "INPUT_REJECTED"}:
        return f"NOT_EMITTED_{governance_result}"
    raise B0PExecutionError("P governance result is outside the V1 prediction contract")


def _verify_p_unsealed_marker(
    marker: Mapping[str, Any],
    *,
    governance_result: str,
    arm_prediction_status: str,
    architecture_source_sha: str,
    input_bundle_sha256: str,
) -> None:
    expected_status = _expected_prediction_status(governance_result)
    if marker.get("prediction_status") != expected_status:
        raise B0PExecutionError("P no-prediction marker conflicts with governance status")
    if marker.get("architecture_source_sha") != architecture_source_sha:
        raise B0PExecutionError("P no-prediction marker is bound to another architecture")
    if marker.get("input_bundle_sha256") != input_bundle_sha256:
        raise B0PExecutionError("P no-prediction marker is bound to another input bundle")
    if arm_prediction_status != expected_status:
        raise B0PExecutionError("P arm prediction status conflicts with governance result")


def _import_linter_compliance(
    exit_status: int | None,
    scope_assessment: Mapping[str, Any],
) -> str:
    if scope_assessment.get("missing_targets") or scope_assessment.get("vacuous"):
        return "NOT_EVALUABLE"
    if exit_status == 0:
        return "COMPLIANT"
    if exit_status == 1:
        return "NON_COMPLIANT"
    return "UNKNOWN"


def _copy_git_blob(
    repository: Path,
    revision: str,
    relative: str,
    destination: Path,
    expected_sha256: str,
) -> None:
    content = _git_blob(repository, revision, relative)
    if sha256_bytes(content) != expected_sha256:
        raise B0PExecutionError(f"Pinned runtime source digest mismatch: {relative}")
    _write_context_file(destination, relative, content)


def _verify_runtime_contexts(root: Path, manifest: Mapping[str, Any]) -> None:
    for method_id, expected_digest in manifest["runtime_contexts"].items():
        context = _safe_path(root, f"container_context/{method_id}")
        _verify_context_inventory(context)
        if _directory_digest(context) != expected_digest:
            raise B0PExecutionError(f"{method_id} container source context digest mismatch")
        source_manifest = json.loads(
            (context / "runtime_source_manifest.json").read_text(encoding="utf-8")
        )
        expected_source = manifest["source_revisions"][
            "b0_source_sha" if method_id == "B0" else "p_source_sha"
        ]
        if source_manifest.get("algorithm_source_sha") != expected_source:
            raise B0PExecutionError(f"{method_id} runtime source is bound to another revision")
        for path in source_manifest.get("files", {}):
            normalized = str(path).lower()
            if any(
                marker in normalized for marker in ("scoring.py", "ground_truth", "scored_result")
            ):
                raise B0PExecutionError(f"{method_id} runtime context contains scorer material")


def _verify_context_inventory(context: Path) -> None:
    sums_path = context / "SHA256SUMS"
    if not sums_path.is_file() or sums_path.is_symlink():
        raise B0PExecutionError("Runtime context checksum inventory is missing")
    declared: set[str] = set()
    for line in sums_path.read_text(encoding="ascii").splitlines():
        try:
            expected, relative = line.split("  ", maxsplit=1)
        except ValueError as error:
            raise B0PExecutionError("Malformed runtime context checksum row") from error
        if relative in declared or re.fullmatch(r"[a-f0-9]{64}", expected) is None:
            raise B0PExecutionError("Duplicate or malformed runtime context checksum row")
        artifact = _safe_path(context, relative)
        if sha256_file(artifact) != expected:
            raise B0PExecutionError(f"Runtime context checksum mismatch: {relative}")
        declared.add(relative)
    actual = {
        path.relative_to(context).as_posix()
        for path in context.rglob("*")
        if path.is_file() and path != sums_path
    }
    if declared != actual:
        raise B0PExecutionError("Runtime context checksum inventory is incomplete")


def _verify_runtime_images(root: Path, manifest: Mapping[str, Any]) -> None:
    for method_id, image in manifest["runtime_images"].items():
        if image["context_sha256"] != manifest["runtime_contexts"][method_id]:
            raise B0PExecutionError(f"{method_id} runtime image was built from another context")
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", image["image_id"]):
            raise B0PExecutionError(f"{method_id} runtime image ID is malformed")
        for stream in ("build_stdout", "build_stderr"):
            path = _safe_path(root, image[f"{stream}_path"])
            if sha256_file(path) != image[f"{stream}_sha256"]:
                raise B0PExecutionError(f"{method_id} image build {stream} digest mismatch")


def _git_blob(repository: Path, revision: str, relative: str) -> bytes:
    if (
        not re.fullmatch(r"[a-f0-9]{40}", revision)
        or PurePosixPath(relative).is_absolute()
        or ".." in PurePosixPath(relative).parts
    ):
        raise B0PExecutionError("Invalid Git blob binding in runtime image source list")
    completed = _run_checked(
        ["git", "show", f"{revision}:{relative}"],
        cwd=repository,
        label=f"read pinned runtime source {relative}",
        timeout=30,
    )
    return completed.stdout


def _git_paths(repository: Path, revision: str, prefix: str) -> list[str]:
    completed = _run_checked(
        ["git", "ls-tree", "-r", "--name-only", revision, "--", prefix],
        cwd=repository,
        label=f"list pinned runtime sources beneath {prefix}",
        timeout=30,
    )
    return [line for line in completed.stdout.decode("utf-8").splitlines() if line]


def _write_context_file(context: Path, relative: str, content: bytes) -> None:
    path = context.joinpath(*PurePosixPath(relative).parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_bytes_once(path, content)


def _write_once(path: Path, payload: Any) -> str:
    content = pretty_json_bytes(payload)
    _write_bytes_once(path, content)
    return sha256_bytes(content)


def _write_bytes_once(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as output:
        output.write(content)
        output.flush()
        os.fsync(output.fileno())
    path.chmod(0o444)


def _write_context_sha256sums(root: Path) -> None:
    files = sorted(path for path in root.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    lines = [f"{sha256_file(path)}  {path.relative_to(root).as_posix()}\n" for path in files]
    _write_bytes_once(root / "SHA256SUMS", "".join(lines).encode("ascii"))


def _write_run_checksums(root: Path) -> None:
    if (root / "SHA256SUMS").exists():
        (root / "SHA256SUMS").chmod(0o644)
        (root / "SHA256SUMS").unlink()
    files = sorted(path for path in root.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    lines = [f"{sha256_file(path)}  {path.relative_to(root).as_posix()}\n" for path in files]
    _write_bytes_once(root / "SHA256SUMS", "".join(lines).encode("ascii"))


def _write_final_checksums(root: Path) -> None:
    """Add a complete inventory while retaining the original failed-attempt inventory."""
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.name not in {"SHA256SUMS", "FINAL_SHA256SUMS"}
    )
    lines = [f"{sha256_file(path)}  {path.relative_to(root).as_posix()}\n" for path in files]
    _write_bytes_once(root / "FINAL_SHA256SUMS", "".join(lines).encode("ascii"))


def _verify_run_inventory(root: Path) -> None:
    sums_path = root / "SHA256SUMS"
    if not sums_path.is_file() or sums_path.is_symlink():
        raise B0PExecutionError("Run checksum inventory is missing or a symlink")
    final_path = root / "FINAL_SHA256SUMS"
    has_final = final_path.exists()
    if has_final and (not final_path.is_file() or final_path.is_symlink()):
        raise B0PExecutionError("Final run checksum inventory is invalid")
    inventory_files = [sums_path, final_path] if has_final else [sums_path]
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and path.name not in {"SHA256SUMS", "FINAL_SHA256SUMS"}
        and path not in inventory_files
    }

    def read_inventory(path: Path) -> set[str]:
        declared: set[str] = set()
        for line in path.read_text(encoding="ascii").splitlines():
            try:
                expected, relative = line.split("  ", maxsplit=1)
            except ValueError as error:
                raise B0PExecutionError("Malformed run checksum row") from error
            if relative in declared or re.fullmatch(r"[a-f0-9]{64}", expected) is None:
                raise B0PExecutionError("Duplicate or malformed run checksum row")
            artifact = _safe_path(root, relative)
            if sha256_file(artifact) != expected:
                raise B0PExecutionError(f"Run checksum mismatch: {relative}")
            declared.add(relative)
        return declared

    declared = read_inventory(sums_path)
    if not has_final:
        if declared != actual:
            raise B0PExecutionError(
                f"Run checksum inventory differs: missing={sorted(actual - declared)} "
                f"extra={sorted(declared - actual)}"
            )
        return
    if not declared.issubset(actual):
        raise B0PExecutionError("Original failed-attempt inventory references a missing artifact")
    final_declared = read_inventory(final_path)
    if final_declared != actual:
        raise B0PExecutionError(
            f"Final run checksum inventory differs: missing={sorted(actual - final_declared)} "
            f"extra={sorted(final_declared - actual)}"
        )


def _artifact_inventory(root: Path, *, excluded: set[str]) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.relative_to(root).as_posix() not in excluded
    }


def _paths_digest(repository: Path, paths: Sequence[Path]) -> str:
    rows = [(path.relative_to(repository).as_posix(), sha256_file(path)) for path in paths]
    return sha256_bytes(json.dumps(rows, separators=(",", ":")).encode())


def _directory_digest(root: Path) -> str:
    rows = [
        (path.relative_to(root).as_posix(), sha256_file(path))
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]
    return sha256_bytes(json.dumps(rows, separators=(",", ":")).encode())


def _safe_path(root: Path, relative: str) -> Path:
    path_value = PurePosixPath(relative)
    if path_value.is_absolute() or ".." in path_value.parts or not path_value.parts:
        raise B0PExecutionError(
            "Artifact path must be relative and contained in the execution package"
        )
    path = root.joinpath(*path_value.parts)
    if path.is_symlink() or not path.resolve(strict=True).is_relative_to(root.resolve(strict=True)):
        raise B0PExecutionError(f"Unsafe execution artifact path: {relative}")
    return path


def _run_checked(
    command: list[str],
    *,
    cwd: Path,
    label: str,
    timeout: int,
) -> subprocess.CompletedProcess[bytes]:
    try:
        completed = subprocess.run(  # nosec B603 - fixed tool argv created by this module  # noqa: S603
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise B0PExecutionError(f"{label} could not complete: {error}") from error
    if completed.returncode != 0:
        stderr = completed.stderr.decode(errors="replace")[-2000:]
        raise B0PExecutionError(f"{label} exited {completed.returncode}: {stderr}")
    return completed


__all__ = [
    "B0PExecutionError",
    "create_evidence_archive",
    "perform_development_execution",
    "verify_development_execution",
]
