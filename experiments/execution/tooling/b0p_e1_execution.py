"""Evidence-sufficient, calibration-exposed B0/P DEVELOPMENT execution.

This versioned E1 envelope composes the existing isolated B0/P runners with the
PILOT-02 TEST_ONLY evidence contracts. It does not change the frozen P algorithm
or the legacy B0/P continuation manifest.
"""

from __future__ import annotations

import base64
import copy
import json
import os
import shutil
import time
import zipfile
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import yaml

from experiments.execution.tooling import b0p_execution as execution
from experiments.execution.tooling.b0p_development import verify_study_manifest
from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.hashing import pretty_json_bytes, sha256_bytes, sha256_file
from experiments.execution.tooling.p_policy_source_v3 import verify_method_bundle_v3
from experiments.execution.tooling.scoring import (
    load_private_ground_truth,
    load_trusted_known_targets,
    score_rq1,
)
from experiments.pilots.pilot02_semantic_validation import load_verified_pair_inputs
from experiments.pilots.pilot02_testonly_execution import (
    build_testonly_fact_verifier,
    verify_testonly_sidecar_signature,
)

ROOT = Path(__file__).resolve().parents[3]
REFERENCE = ROOT / "experiments/pilots/DEV_B0P_E1_REFERENCE_V1.json"
E1_SCHEMA = "b0p_evidence_sufficient_execution_v1.schema.json"


class B0PE1ExecutionError(execution.B0PExecutionError):
    """Evidence-sufficient E1 execution could not preserve its source bindings."""


def perform_e1_execution(
    preparation_directory: Path,
    *,
    method_p_input_directory: Path,
    adaptation_evidence_sidecar: Path,
    semantic_verification_directory: Path,
    run_id: str,
    repository: Path | None = None,
    docker_executable: str = "docker",
    uv_executable: str = "uv",
    reference_path: Path = REFERENCE,
) -> dict[str, Any]:
    """Run B0 and frozen P in separate isolated containers using verified E1 inputs."""
    repository_root = (repository or ROOT).resolve(strict=True)
    prep_root = preparation_directory.resolve(strict=True)
    if preparation_directory.is_symlink() or prep_root.parent != (
        repository_root / "experiments/results"
    ).resolve(strict=True):
        raise B0PE1ExecutionError("Preparation must be a regular run under experiments/results")
    if execution.RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise B0PE1ExecutionError("E1 run ID is invalid")
    run_root = repository_root / "experiments/results" / run_id
    _require_new_run_directory(run_root)

    prep_manifest = verify_study_manifest(prep_root, repository_root)
    reference_payload, reference_sha = _verify_reference(
        reference_path, prep_manifest, repository_root
    )
    p_input = method_p_input_directory.resolve(strict=True)
    if method_p_input_directory.is_symlink() or not p_input.is_dir():
        raise B0PE1ExecutionError("P method input must be a regular directory")
    p_bundle = verify_method_bundle_v3(p_input, expected_method_id="P")
    p_bundle_sha = str(p_bundle["bundle_sha256"])
    sidecar_source = adaptation_evidence_sidecar.resolve(strict=True)
    sidecar = cast(dict[str, Any], json.loads(sidecar_source.read_bytes()))
    if adaptation_evidence_sidecar.is_symlink() or not sidecar_source.is_file():
        raise B0PE1ExecutionError("PILOT-02 TEST_ONLY sidecar is not a regular file")
    validate_e1_sidecar_binding(
        sidecar,
        p_bundle,
        input_bundle_sha256=p_bundle_sha,
        run_id=run_id,
        architecture_before_sha=prep_manifest["source_revisions"]["architecture_before_sha"],
        architecture_after_sha=prep_manifest["source_revisions"]["architecture_after_sha"],
    )
    try:
        build_testonly_fact_verifier(sidecar, expected_input_bundle_sha256=p_bundle_sha)
        _verify_no_oracle_contamination(p_input, sidecar)
    except ValueError as error:
        raise B0PE1ExecutionError(str(error)) from error
    semantic_root = semantic_verification_directory.resolve(strict=True)
    if semantic_verification_directory.is_symlink() or not semantic_root.is_dir():
        raise B0PE1ExecutionError("Independent semantic evidence directory is missing")
    verified_pairs = load_verified_pair_inputs(
        semantic_root,
        repository_root=repository_root,
        expected_architecture_source_sha=prep_manifest["source_revisions"][
            "architecture_after_sha"
        ],
    )
    if len(verified_pairs) != 2:
        raise B0PE1ExecutionError("E1 requires the two predeclared PILOT-02 exact-pair controls")

    effective_prep = copy.deepcopy(prep_manifest)
    effective_prep["method_p"]["input_bundle_sha256"] = p_bundle_sha
    effective_prep["method_p"]["input_bundle_path"] = "e1_method_input"
    effective_prep["method_p"]["policy_source_revision"] = p_bundle["policy_source_revision"]
    run_root.mkdir(mode=0o755)
    try:
        snapshot = run_root / "preparation_snapshot"
        shutil.copytree(prep_root, snapshot, copy_function=shutil.copy2)
        if sha256_file(snapshot / "study_manifest.json") != sha256_file(
            prep_root / "study_manifest.json"
        ):
            raise B0PE1ExecutionError("E1 preparation snapshot changed during copy")
        copied_p_input = run_root / "e1_method_input"
        shutil.copytree(p_input, copied_p_input, copy_function=shutil.copy2)
        copied_sidecar = run_root / "adaptation_evidence_test_only.json"
        shutil.copyfile(sidecar_source, copied_sidecar)
        shutil.copytree(
            semantic_root, run_root / "semantic_verification", copy_function=shutil.copy2
        )
        _write_once(run_root / "reference/reference.json", reference_payload)
        _record_e1_environment(run_root, docker_executable, uv_executable, repository_root)

        b0_context, b0_context_sha = execution._build_runtime_context(
            run_root,
            method_id="B0",
            source_sha=prep_manifest["source_revisions"]["b0_source_sha"],
            prep_manifest=prep_manifest,
            repository=repository_root,
        )
        p_context, p_context_sha = execution._build_runtime_context(
            run_root,
            method_id="P",
            source_sha=prep_manifest["source_revisions"]["p_source_sha"],
            prep_manifest=prep_manifest,
            repository=repository_root,
        )
        b0_image = execution._build_image(
            b0_context, run_id, "b0", docker_executable, repository_root
        )
        p_image = execution._build_image(p_context, run_id, "p", docker_executable, repository_root)
        (run_root / "B0").mkdir(mode=0o777)
        (run_root / "P").mkdir(mode=0o777)
        b0_execution = execution._run_isolated_arm(
            method_id="B0",
            image=b0_image,
            input_directory=snapshot / "method_inputs/b0",
            output_directory=run_root / "B0",
            preparation=prep_manifest,
            docker_executable=docker_executable,
            repository=repository_root,
        )
        p_execution = execution._run_isolated_arm(
            method_id="P",
            image=p_image,
            input_directory=copied_p_input,
            output_directory=run_root / "P",
            preparation=effective_prep,
            docker_executable=docker_executable,
            repository=repository_root,
            evidence_sidecar=copied_sidecar,
        )
        _write_once(
            run_root / "container_invocations.json",
            {"B0": b0_execution["command"], "P": p_execution["command"]},
        )
        if str(reference_path.resolve()) in " ".join(p_execution["command"]):
            raise B0PE1ExecutionError("E1 reference was mounted into the Method P environment")

        evaluator_start = time.perf_counter_ns()
        evaluator_records, evaluator_duration = execution._run_evaluators(
            run_root, prep_manifest, uv_executable=uv_executable, repository=repository_root
        )
        verification_start = time.perf_counter_ns()
        execution._verify_evaluator_records(run_root, evaluator_records, prep_manifest)
        pair_record = _pair_verification_record(
            run_id, verified_pairs, reference_payload["rq2_required_obligations_after"]
        )
        _write_once(run_root / "semantic_pair_verification.json", pair_record)
        verification_duration = time.perf_counter_ns() - verification_start
        if time.perf_counter_ns() < evaluator_start:
            raise B0PE1ExecutionError("Monotonic E1 evaluator timer moved backwards")

        rq1 = _score_or_explain_rq1(
            run_root,
            reference_payload,
            reference_sha,
            b0_execution,
            p_execution,
            repository_root,
        )
        _write_once(run_root / "rq1_scoring.json", rq1)
        p_trace = cast(dict[str, Any], json.loads((run_root / "P/method_p_trace.json").read_text()))
        candidate_config_path = run_root / "P/candidate_configuration.json"
        candidate_config = (
            cast(dict[str, Any], json.loads(candidate_config_path.read_text()))
            if candidate_config_path.is_file()
            else None
        )
        rq2_detail = _rq2_obligation_table(
            run_id,
            reference_payload["rq2_required_obligations_after"],
            pair_record,
            b0_execution,
            p_execution,
            p_trace,
            candidate_config,
        )
        validate_payload("b0p_e1_rq2_obligation_evidence_v1.schema.json", rq2_detail)
        _write_once(run_root / "rq2_obligation_evidence.json", rq2_detail)
        e1_binding = {
            "reference_path": "reference/reference.json",
            "reference_sha256": reference_sha,
            "reference_status": reference_payload["status"],
            "p_input_path": "e1_method_input",
            "p_input_bundle_sha256": p_bundle_sha,
            "p_policy_source_revision": p_bundle["policy_source_revision"],
            "adaptation_evidence_sidecar_path": "adaptation_evidence_test_only.json",
            "adaptation_evidence_sidecar_sha256": sha256_file(copied_sidecar),
            "adaptation_evidence_trust_scope": "TEST_ONLY",
            "semantic_verification_path": "semantic_verification",
            "semantic_pair_count": len(verified_pairs),
            "reference_mounted_in_method_environment": False,
            "e0_run_id": "dev-b0p-20261020-execution-a04",
            "e0_reused_or_modified": False,
        }
        manifest = _build_manifest(
            run_root,
            prep_manifest=prep_manifest,
            preparation_sha=sha256_file(prep_root / "study_manifest.json"),
            effective_prep=effective_prep,
            e1_binding=e1_binding,
            reference_payload=reference_payload,
            reference_sha=reference_sha,
            runtime_contexts={"B0": b0_context_sha, "P": p_context_sha},
            runtime_images={"B0": b0_image, "P": p_image},
            b0_execution=b0_execution,
            p_execution=p_execution,
            evaluator_records=evaluator_records,
            evaluator_duration_ns=evaluator_duration,
            verification_duration_ns=verification_duration,
            pair_record=pair_record,
            rq1=rq1,
            rq2_detail=rq2_detail,
        )
        validate_payload(E1_SCHEMA, manifest)
        _write_once(run_root / "e1_execution_manifest.json", manifest)
        execution._write_run_checksums(run_root)
        verify_e1_execution(run_root, repository=repository_root)
        return manifest
    except Exception as error:
        failure = {
            "schema_version": 1,
            "run_id": run_id,
            "execution_status": "EXECUTION_FAILED",
            "error_type": type(error).__name__,
            "error": str(error),
            "failed_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
        if not (run_root / "execution_failure.json").exists():
            _write_once(run_root / "execution_failure.json", failure)
        execution._write_run_checksums(run_root)
        raise


def verify_e1_execution(run_directory: Path, *, repository: Path | None = None) -> dict[str, Any]:
    """Read back E1 bindings, results, independent pairs, and complete run inventory."""
    root = run_directory.resolve(strict=True)
    manifest = cast(
        dict[str, Any],
        json.loads((root / "e1_execution_manifest.json").read_text(encoding="utf-8")),
    )
    validate_payload(E1_SCHEMA, manifest)
    repository_root = repository.resolve(strict=True) if repository else None
    prep_snapshot = root / "preparation_snapshot"
    prep_manifest = cast(
        dict[str, Any], json.loads((prep_snapshot / "study_manifest.json").read_bytes())
    )
    if (
        sha256_file(prep_snapshot / "study_manifest.json")
        != manifest["preparation"]["manifest_sha256"]
    ):
        raise B0PE1ExecutionError("E1 preparation snapshot digest changed")
    validate_payload(
        "b0p_e1_rq2_obligation_evidence_v1.schema.json",
        json.loads((root / "rq2_obligation_evidence.json").read_bytes()),
    )
    reference_path = _safe(root, manifest["e1_evidence"]["reference_path"])
    if sha256_file(reference_path) != manifest["e1_evidence"]["reference_sha256"]:
        raise B0PE1ExecutionError("Pre-execution reference digest changed")
    reference = cast(dict[str, Any], json.loads(reference_path.read_text(encoding="utf-8")))
    if reference.get("frozen_before_execution") is not True:
        raise B0PE1ExecutionError("E1 reference does not attest pre-execution freeze")
    if repository_root is not None:
        _validate_reference_payload(reference, prep_manifest, repository_root)
    rq2_detail = cast(
        dict[str, Any], json.loads((root / "rq2_obligation_evidence.json").read_bytes())
    )
    validate_rq2_denominator(rq2_detail, reference.get("rq2_required_obligations_after", []))
    if (
        manifest["rq1_scoring"]["reference_sha256"] != manifest["e1_evidence"]["reference_sha256"]
        or manifest["rq1_scoring"]["reference_path"] != manifest["e1_evidence"]["reference_path"]
    ):
        raise B0PE1ExecutionError("E1 RQ1 result is bound to another reference")
    sidecar_path = _safe(root, manifest["e1_evidence"]["adaptation_evidence_sidecar_path"])
    sidecar = cast(dict[str, Any], json.loads(sidecar_path.read_bytes()))
    if (
        sha256_file(sidecar_path) != manifest["e1_evidence"]["adaptation_evidence_sidecar_sha256"]
        or not verify_testonly_sidecar_signature(sidecar)
        or sidecar.get("input_bundle_sha256") != manifest["e1_evidence"]["p_input_bundle_sha256"]
        or sidecar.get("policy_source_revision")
        != manifest["e1_evidence"]["p_policy_source_revision"]
        or manifest["e1_evidence"]["p_policy_source_revision"] != f"PILOT02_TEST_ONLY_{root.name}"
    ):
        raise B0PE1ExecutionError("E1 TEST_ONLY sidecar failed readback verification")
    p_bundle = _verify_e1_method_input(root, manifest["e1_evidence"])
    validate_e1_sidecar_binding(
        sidecar,
        p_bundle,
        input_bundle_sha256=str(manifest["e1_evidence"]["p_input_bundle_sha256"]),
        run_id=root.name,
        architecture_before_sha=str(manifest["source_revisions"]["architecture_before_sha"]),
        architecture_after_sha=str(manifest["source_revisions"]["architecture_after_sha"]),
    )
    invocations = json.loads((root / "container_invocations.json").read_bytes())
    p_command = " ".join(str(item) for item in invocations.get("P", []))
    if (
        "--network=none" not in p_command
        or "--evidence-sidecar" not in p_command
        or manifest["e1_evidence"]["reference_path"] in p_command
    ):
        raise B0PE1ExecutionError("E1 Method P isolation or reference exclusion failed")
    if repository_root:
        pairs = _load_e1_semantic_pairs(
            root,
            manifest["e1_evidence"],
            repository_root=repository_root,
            expected_architecture_source_sha=manifest["source_revisions"]["architecture_after_sha"],
        )
        pair_record = _pair_verification_record(
            root.name, pairs, reference["rq2_required_obligations_after"]
        )
        if pair_record != json.loads((root / "semantic_pair_verification.json").read_text()):
            raise B0PE1ExecutionError("Independent semantic pair readback differs")
    execution._verify_preparation_snapshot(prep_snapshot, prep_manifest)
    execution._verify_runtime_contexts(root, manifest)
    execution._verify_runtime_images(root, manifest)
    execution._verify_evaluator_records(
        root, manifest["evaluator_execution"]["observations"], prep_manifest
    )
    execution._validate_completed_arm_prediction("B0", manifest["arms"]["B0"])
    if manifest["arms"]["B0"]["prediction_status"] != "SEALED":
        raise B0PE1ExecutionError("E1 B0 prediction was not sealed")
    for arm_id in ("B0", "P"):
        arm = manifest["arms"][arm_id]
        expected_source = manifest["source_revisions"][
            "b0_source_sha" if arm_id == "B0" else "p_source_sha"
        ]
        expected_bundle = (
            prep_manifest["b0"]["input_bundle_sha256"]
            if arm_id == "B0"
            else manifest["e1_evidence"]["p_input_bundle_sha256"]
        )
        if arm["source_sha"] != expected_source or arm["input_bundle_sha256"] != expected_bundle:
            raise B0PE1ExecutionError(f"E1 {arm_id} arm source or bundle binding changed")
        if arm_id == "P" and arm["prediction_status"] != "SEALED":
            marker = cast(
                dict[str, Any], json.loads(_safe(root, arm["prediction_path"]).read_bytes())
            )
            execution._verify_p_unsealed_marker(
                marker,
                governance_result=manifest["governance_decision"]["P"],
                arm_prediction_status=arm["prediction_status"],
                architecture_source_sha=manifest["source_revisions"]["architecture_after_sha"],
                input_bundle_sha256=expected_bundle,
            )
        else:
            sealed = execution.load_verified_prediction(_safe_dir(root, arm["prediction_path"]))
            error = execution._prediction_binding_error(
                sealed.payload,
                method_id=arm_id,
                architecture_source_sha=manifest["source_revisions"]["architecture_after_sha"],
                input_bundle_sha256=expected_bundle,
            )
            if error or sealed.sha256 != arm["prediction_sha256"]:
                raise B0PE1ExecutionError(f"E1 {arm_id} prediction binding failed: {error}")
    for relative, digest in manifest["artifacts"].items():
        if sha256_file(_safe(root, relative)) != digest:
            raise B0PE1ExecutionError(f"E1 artifact digest mismatch: {relative}")
    validate_e1_rq1_gate(
        manifest["rq1_scoring"],
        p_prediction_status=manifest["arms"]["P"]["prediction_status"],
    )
    execution._verify_run_inventory(root)
    return {
        "run_id": root.name,
        "verified": True,
        "artifact_count": len(manifest["artifacts"]),
        "B0_prediction_status": manifest["arms"]["B0"]["prediction_status"],
        "P_prediction_status": manifest["arms"]["P"]["prediction_status"],
        "P_governance": manifest["governance_decision"]["P"],
        "RQ1": manifest["rq1_scoring"]["status"],
        "RQ2": manifest["rq2_scoring"]["status"],
    }


def create_e1_archive(run_directory: Path) -> tuple[Path, str]:
    """Create a write-once ZIP and SHA-256 sidecar for E1 evidence."""
    root = run_directory.resolve(strict=True)
    verify_e1_execution(root)
    archive = root.parent / f"{root.name}.zip"
    sidecar = root.parent / f"{root.name}.zip.sha256"
    if archive.exists() or sidecar.exists():
        raise B0PE1ExecutionError("E1 evidence archive is write-once")
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            output.write(path, Path(root.name) / path.relative_to(root))
    digest = sha256_file(archive)
    descriptor = os.open(sidecar, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(f"{digest}  {archive.name}\n".encode("ascii"))
        stream.flush()
        os.fsync(stream.fileno())
    sidecar.chmod(0o444)
    return archive, digest


def _verify_reference(
    path: Path, preparation: Mapping[str, Any], repository: Path
) -> tuple[dict[str, Any], str]:
    if path.is_symlink():
        raise B0PE1ExecutionError("E1 reference must be a regular sealed file")
    source = path.resolve(strict=True)
    digest = sha256_file(source)
    checksum = source.with_name(source.name + ".sha256")
    if checksum.read_text(encoding="ascii") != f"{digest}  {source.name}\n":
        raise B0PE1ExecutionError("E1 reference SHA-256 sidecar mismatch")
    payload = cast(dict[str, Any], json.loads(source.read_bytes()))
    _validate_reference_payload(payload, preparation, repository)
    return payload, digest


def _validate_reference_payload(
    payload: Mapping[str, Any], preparation: Mapping[str, Any], repository: Path
) -> None:
    revisions = preparation["source_revisions"]
    target_sha = str(revisions["architecture_after_sha"])
    source_hashes_match = True
    sources = payload.get("sources", {})
    expected_source_paths = {
        "a0_representation_catalog": "fitness/catalog/a0-fitness-elements.yaml",
        "architecture_evolution_spec": "experiments/design/ARCHITECTURE_EVOLUTION_SCENARIOS_V1.md",
        "da01_scenario_denominator": "experiments/scenarios/DA01/scenario.yaml",
        "obligation_catalog": "fitness/catalog/architectural-obligations.yaml",
    }
    if not isinstance(sources, Mapping) or set(sources) != set(expected_source_paths):
        source_hashes_match = False
    for source_id, source in sources.items() if isinstance(sources, Mapping) else ():
        if not isinstance(source, Mapping):
            source_hashes_match = False
            break
        if source.get("git_revision") != target_sha or source.get(
            "path"
        ) != expected_source_paths.get(str(source_id)):
            source_hashes_match = False
            break
        try:
            content = execution._git_blob(
                repository,
                str(source["git_revision"]),
                str(source["path"]),
            )
        except Exception:
            source_hashes_match = False
            break
        if sha256_bytes(content) != source.get("sha256"):
            source_hashes_match = False
            break
    try:
        scenario = yaml.safe_load(
            execution._git_blob(
                repository,
                str(revisions["architecture_after_sha"]),
                "experiments/scenarios/DA01/scenario.yaml",
            )
        )
        obligation_catalog = yaml.safe_load(
            execution._git_blob(
                repository,
                str(revisions["architecture_after_sha"]),
                "fitness/catalog/architectural-obligations.yaml",
            )
        )
        catalog_ids = {
            str(row.get("id"))
            for row in obligation_catalog.get("obligations", [])
            if isinstance(row, Mapping)
        }
        denominator_match = (
            payload.get("rq2_required_obligations_after")
            == scenario.get("required_obligations_after")
            and set(payload.get("rq2_required_obligations_after", [])) <= catalog_ids
        )
        representation_catalog = yaml.safe_load(
            execution._git_blob(
                repository,
                target_sha,
                "fitness/catalog/a0-fitness-elements.yaml",
            )
        )
        representation_ids = {
            str(row.get("id"))
            for row in representation_catalog.get("representations", [])
            if isinstance(row, Mapping)
        }
    except (KeyError, TypeError, AttributeError, yaml.YAMLError):
        denominator_match = False
        representation_ids = set()
    classification = payload.get("classification_universe")
    expected_operations = payload.get("expected_operations")
    existing_ids = (
        classification.get("existing_representations")
        if isinstance(classification, Mapping)
        else None
    )
    new_ids = classification.get("new_obligations") if isinstance(classification, Mapping) else None
    classification_valid = (
        isinstance(existing_ids, list)
        and isinstance(new_ids, list)
        and all(isinstance(item, str) and item for item in existing_ids + new_ids)
        and len(existing_ids) == len(set(existing_ids))
        and len(new_ids) == len(set(new_ids))
    )
    operation_universe = set()
    if classification_valid:
        operation_universe.update(existing_ids)
        operation_universe.update(new_ids)
    if (
        payload.get("status") != "AUTHOR_DECLARED_CALIBRATION_EXPOSED"
        or payload.get("frozen_before_execution") is not True
        or payload.get("architecture", {}).get("before_sha") != revisions["architecture_before_sha"]
        or payload.get("architecture", {}).get("after_sha") != revisions["architecture_after_sha"]
        or payload.get("exposure_class") != "CALIBRATION_EXPOSED"
        or len(payload.get("rq2_required_obligations_after", [])) != 6
        or not source_hashes_match
        or not denominator_match
        or not classification_valid
        or not isinstance(expected_operations, Mapping)
        or set(expected_operations) != operation_universe
        or set(existing_ids) != representation_ids
        or set(existing_ids) != set(expected_operations) - set(new_ids)
        or not set(new_ids) <= catalog_ids
        or any(
            operation not in {"retain", "replace", "add", "deactivate", "adjust"}
            for operation in expected_operations.values()
        )
    ):
        raise B0PE1ExecutionError("E1 reference is incomplete or bound to another calibration")


def _require_new_run_directory(run_root: Path) -> None:
    if run_root.exists() or run_root.is_symlink():
        raise B0PE1ExecutionError(f"E1 evidence output is write-once: {run_root}")


def validate_e1_sidecar_binding(
    sidecar: Mapping[str, Any],
    p_bundle: Mapping[str, Any],
    *,
    input_bundle_sha256: str,
    run_id: str,
    architecture_before_sha: str,
    architecture_after_sha: str,
) -> None:
    """Fail closed on signature, exact run, policy revision, or source mismatch."""
    expected_policy_revision = f"PILOT02_TEST_ONLY_{run_id}"
    if (
        not verify_testonly_sidecar_signature(sidecar)
        or sidecar.get("input_bundle_sha256") != input_bundle_sha256
        or p_bundle.get("bundle_sha256") != input_bundle_sha256
        or sidecar.get("architecture_before_sha") != architecture_before_sha
        or sidecar.get("architecture_after_sha") != architecture_after_sha
        or sidecar.get("policy_source_revision") != expected_policy_revision
        or p_bundle.get("policy_source_revision") != expected_policy_revision
    ):
        raise B0PE1ExecutionError("PILOT-02 TEST_ONLY sidecar is invalid or bound to another run")


def validate_rq2_denominator(
    rq2_detail: Mapping[str, Any], expected_denominator: list[str]
) -> None:
    """Require exact, complete denominator binding while keeping unsupported scoring UNKNOWN."""
    rows = rq2_detail.get("rows")
    actual = (
        [str(row.get("obligation_id")) for row in rows if isinstance(row, Mapping)]
        if isinstance(rows, list)
        else []
    )
    if (
        not expected_denominator
        or len(expected_denominator) != len(set(expected_denominator))
        or actual != expected_denominator
        or rq2_detail.get("status") != "UNKNOWN"
        or rq2_detail.get("required_obligation_set_bound") is not True
        or rq2_detail.get("same_denominator_for_arms") is not True
        or rq2_detail.get("coverage_percentage") is not None
    ):
        raise B0PE1ExecutionError("E1 RQ2 evidence has an incomplete or unbound denominator")


def validate_e1_rq1_gate(rq1: Mapping[str, Any], *, p_prediction_status: str) -> None:
    """Prohibit scorer invocation when P emitted no governance-sealed prediction."""
    if p_prediction_status != "SEALED" and (
        rq1.get("status") != "NOT_EVALUABLE"
        or rq1.get("scorer_invoked") is not False
        or rq1.get("results") != {}
    ):
        raise B0PE1ExecutionError(
            "E1 RQ1 cannot score or manufacture a prediction after P abstains"
        )
    if p_prediction_status == "SEALED" and (
        rq1.get("status") != "SCORED" or rq1.get("scorer_invoked") is not True
    ):
        raise B0PE1ExecutionError("E1 sealed predictions require the canonical RQ1 scorer")


def _verify_no_oracle_contamination(p_input: Path, sidecar: Mapping[str, Any]) -> None:
    manifest_path = p_input / "method_input_v3.json"
    manifest = cast(dict[str, Any], json.loads(manifest_path.read_bytes()))
    paths = [str(row.get("path", "")).lower() for row in manifest.get("files", [])]
    forbidden = (".git", "ground_truth", "expected_operations", "scorer", "other_arm")
    if any(marker in path for path in paths for marker in forbidden):
        raise B0PE1ExecutionError("E1 P input contains a prohibited oracle or cross-arm artifact")
    payload = sidecar.get("payload")
    artifacts = payload.get("artifact_bytes") if isinstance(payload, Mapping) else None
    if not isinstance(artifacts, list):
        raise B0PE1ExecutionError("E1 TEST_ONLY sidecar artifact inventory is missing")
    for row in artifacts:
        if not isinstance(row, Mapping):
            raise B0PE1ExecutionError("E1 TEST_ONLY sidecar artifact row is malformed")
        relative = str(row.get("path", "")).lower()
        if any(marker in relative for marker in forbidden):
            raise B0PE1ExecutionError("E1 sidecar contains a prohibited oracle or cross-arm path")
        try:
            content = base64.b64decode(str(row.get("content_base64", "")), validate=True)
        except ValueError as error:
            raise B0PE1ExecutionError("E1 sidecar artifact encoding is invalid") from error
        if relative.endswith(".json"):
            try:
                artifact = json.loads(content)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if _has_forbidden_json_key(artifact):
                raise B0PE1ExecutionError(
                    "E1 sidecar JSON contains reference labels or scorer output"
                )


def _has_forbidden_json_key(value: Any) -> bool:
    forbidden_keys = {
        "expected_operations",
        "ground_truth",
        "scorer_output",
        "other_arm_prediction",
    }
    if isinstance(value, Mapping):
        return any(
            str(key).lower() in forbidden_keys or _has_forbidden_json_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_has_forbidden_json_key(item) for item in value)
    return False


def _record_e1_environment(root: Path, docker: str, uv: str, repository: Path) -> None:
    execution._record_host_environment(
        root, docker_executable=docker, uv_executable=uv, repository=repository
    )


def _score_or_explain_rq1(
    root: Path,
    reference: Mapping[str, Any],
    reference_sha: str,
    b0: Mapping[str, Any],
    p: Mapping[str, Any],
    repository: Path,
) -> dict[str, Any]:
    b0_sealed = b0.get("docker_exit_status") == 0 and (root / "B0/prediction").is_dir()
    p_sealed = p.get("prediction_status") == "SEALED"
    result: dict[str, Any] = {
        "schema_version": 1,
        "status": "NOT_EVALUABLE",
        "reason": (
            "Frozen Method P emitted no prediction; canonical comparative scoring is withheld."
        ),
        "reference_path": "reference/reference.json",
        "reference_sha256": reference_sha,
        "scorer_invoked": False,
        "results": {},
    }
    if not (b0_sealed and p_sealed):
        return result
    # Oracle bytes are opened only after both predictions are sealed.
    ground_truth = load_private_ground_truth(
        str(repository / "experiments/scenarios/DA01/ground_truth.yaml")
    )
    if ground_truth.get("expected_operations") != reference.get(
        "expected_operations"
    ) or ground_truth.get("required_obligations_after") != reference.get(
        "rq2_required_obligations_after"
    ):
        raise B0PE1ExecutionError("Sealed E1 reference differs from canonical scorer target labels")
    known_targets = load_trusted_known_targets(
        str(reference["architecture"]["after_sha"]), repository
    )
    arm_results: dict[str, Any] = {}
    for method_id in ("B0", "P"):
        sealed = execution.load_verified_prediction(root / method_id / "prediction")
        arm_results[method_id] = {
            "prediction_sha256": sealed.sha256,
            "score": score_rq1(sealed.payload, ground_truth, known_targets),
        }
    result.update(
        {
            "status": "SCORED",
            "reason": (
                "Both sealed predictions were scored by the frozen canonical RQ1 scorer "
                "against the pre-execution reference."
            ),
            "scorer_invoked": True,
            "results": arm_results,
        }
    )
    return result


def _pair_verification_record(
    run_id: str,
    pairs: Mapping[tuple[str, str], Mapping[str, Any]],
    denominator: list[str],
) -> dict[str, Any]:
    pair_rows = []
    for (representation_id, obligation_id), value in sorted(pairs.items()):
        report = value["report"]
        pair_rows.append(
            {
                "representation_id": representation_id,
                "obligation_id": obligation_id,
                "architecture_source_sha": report["architecture_source_sha"],
                "independent_verification": "VERIFIED"
                if report.get("status") == "VALID"
                else "UNKNOWN",
                "semantic_status": report.get("status"),
                "trust_scope": "TEST_ONLY",
                "report_sha256": sha256_bytes(pretty_json_bytes(report)),
                "evaluator_artifact_sha256": report.get("evaluator_artifact_sha256"),
                "evidence_artifacts": list(value["evidence_artifacts"]),
                "reason_codes": list(report.get("reason_codes", [])),
            }
        )
    return {
        "schema_version": 1,
        "run_id": run_id,
        "status": "PARTIAL" if len(pair_rows) < len(denominator) else "VERIFIED",
        "independently_verified_pair_count": sum(
            row["independent_verification"] == "VERIFIED" for row in pair_rows
        ),
        "unknown_pair_count": len(denominator)
        - sum(row["independent_verification"] == "VERIFIED" for row in pair_rows),
        "required_obligations": list(denominator),
        "pairs": pair_rows,
        "reason_codes": ["TEST_ONLY_SEMANTIC_CONTROLS_DO_NOT_ESTABLISH_PRODUCTION_AUTHORITY"],
    }


def _rq2_obligation_table(
    run_id: str,
    denominator: list[str],
    pair_record: Mapping[str, Any],
    b0: Mapping[str, Any],
    p: Mapping[str, Any],
    p_trace: Mapping[str, Any],
    candidate_config: Mapping[str, Any] | None,
) -> dict[str, Any]:
    pairs_by_obligation: dict[str, list[Mapping[str, Any]]] = {}
    for pair in pair_record["pairs"]:
        pairs_by_obligation.setdefault(str(pair["obligation_id"]), []).append(pair)
    rows = []
    candidate_representations = {
        str(row.get("id")): str(row.get("evaluator_artifact", {}).get("sha256"))
        for row in (candidate_config or {}).get("representations", [])
        if isinstance(row, Mapping)
        and row.get("active") is True
        and isinstance(row.get("evaluator_artifact"), Mapping)
    }
    candidate_pair_ids = {
        (str(row.get("representation_id")), str(row.get("obligation_id")))
        for row in p_trace.get("candidate_pairs", [])
        if isinstance(row, Mapping)
    }
    candidate_valid = p.get("candidate_validation") == "VALID"
    for obligation in denominator:
        pair_rows = pairs_by_obligation.get(obligation, [])
        valid_candidate_pairs = [
            row
            for row in pair_rows
            if row.get("independent_verification") == "VERIFIED"
            and candidate_representations.get(str(row.get("representation_id")))
            == row.get("evaluator_artifact_sha256")
            and (str(row.get("representation_id")), obligation) in candidate_pair_ids
            and candidate_valid
        ]
        pair_valid = bool(valid_candidate_pairs)
        rows.append(
            {
                "obligation_id": obligation,
                "applicability": "APPLICABLE_PUBLIC_DA01_DENOMINATOR",
                "B0_coverage": "UNKNOWN",
                "P_candidate_potential": "DIAGNOSTIC_ONLY" if pair_valid else "UNKNOWN",
                "P_governance_accepted_coverage": "ABSENT"
                if p.get("governance_result") != "ACCEPT"
                else "UNKNOWN",
                "exact_pair_evidence": valid_candidate_pairs,
                "final_result": "UNKNOWN",
                "missing_proof": None
                if pair_valid
                else (
                    "No valid P candidate representation has a current E1 exact-pair proof "
                    "for this obligation."
                ),
            }
        )
    return {
        "schema_version": 1,
        "run_id": run_id,
        "status": "UNKNOWN",
        "required_obligation_set_bound": True,
        "same_denominator_for_arms": True,
        "denominator_source": {
            "reference_id": "DEV_B0P_E1_DELTA_A1_REFERENCE_V1",
            "reference_sha256": sha256_file(REFERENCE),
            "count": len(denominator),
        },
        "rows": rows,
        "coverage_percentage": None,
        "reason": (
            "The complete six-obligation denominator is bound, but B0 and P lack complete "
            "independently verified exact-pair evidence."
        ),
        "P_governance": str(p.get("governance_result", "UNKNOWN")),
        "B0_execution_status": "COMPLETED" if b0.get("docker_exit_status") == 0 else "UNKNOWN",
    }


def _build_manifest(
    run_root: Path,
    *,
    prep_manifest: Mapping[str, Any],
    preparation_sha: str,
    effective_prep: Mapping[str, Any],
    e1_binding: Mapping[str, Any],
    reference_payload: Mapping[str, Any],
    reference_sha: str,
    runtime_contexts: Mapping[str, str],
    runtime_images: Mapping[str, Mapping[str, str]],
    b0_execution: Mapping[str, Any],
    p_execution: Mapping[str, Any],
    evaluator_records: list[dict[str, Any]],
    evaluator_duration_ns: int,
    verification_duration_ns: int,
    pair_record: Mapping[str, Any],
    rq1: Mapping[str, Any],
    rq2_detail: Mapping[str, Any],
) -> dict[str, Any]:
    b0_record = execution._arm_manifest_record(
        "B0", run_root / "B0", b0_execution, prep_manifest, runtime_images["B0"]
    )
    p_record = execution._arm_manifest_record(
        "P", run_root / "P", p_execution, effective_prep, runtime_images["P"]
    )
    artifacts = execution._artifact_inventory(
        run_root,
        excluded={"e1_execution_manifest.json", "SHA256SUMS", "FINAL_SHA256SUMS"},
    )
    p_trace = cast(dict[str, Any], json.loads((run_root / "P/method_p_trace.json").read_text()))
    evaluator_source = _git_text(run_root, "rev-parse", "HEAD")
    manifest = {
        "schema_version": 1,
        "study_id": "DEV-B0P-V1-E1",
        "run_id": run_root.name,
        "execution_status": _execution_status(b0_execution, p_execution, evaluator_records),
        "exposure_class": "CALIBRATION_EXPOSED",
        "e0": {
            "run_id": "dev-b0p-20261020-execution-a04",
            "status": "PRESERVED_IMMUTABLE_HISTORICAL_OBSERVATION",
            "reused_or_modified": False,
            "known_outcome_summary": (
                "B0 sealed; P HOLD; P candidate INVALID; no P operations; "
                "RQ1 NOT_EVALUABLE; RQ2 UNKNOWN."
            ),
        },
        "preparation": {
            "run_id": prep_manifest["run_id"],
            "manifest_sha256": preparation_sha,
            "verified": True,
        },
        "source_revisions": {
            key: prep_manifest["source_revisions"][key]
            for key in (
                "architecture_before_sha",
                "architecture_after_sha",
                "b0_source_sha",
                "p_source_sha",
                "policy_source_sha",
            )
        },
        "evaluator_source_revision": evaluator_source,
        "evaluator_source_scope": (
            "Current committed harness with app tree verified identical to the target "
            "architecture SHA."
        ),
        "runtime_contexts": dict(runtime_contexts),
        "runtime_images": {key: dict(value) for key, value in runtime_images.items()},
        "e1_evidence": dict(e1_binding),
        "arms": {"B0": b0_record, "P": p_record},
        "P_outcomes": {
            "before_applicability": p_trace.get("before_applicability"),
            "after_applicability": p_trace.get("after_applicability"),
            "impact_assessment": p_trace.get("impact_assessment"),
            "operation_plan": p_trace.get("operation_plan"),
            "candidate_validation": p_execution.get("candidate_validation"),
            "candidate_configuration_path": "P/candidate_configuration.json"
            if p_execution.get("candidate_configuration_sha256")
            else None,
            "candidate_configuration_sha256": p_execution.get("candidate_configuration_sha256"),
            "current_coverage_diagnostic": p_trace.get("current_coverage"),
            "candidate_coverage_diagnostic": p_trace.get("candidate_coverage"),
            "current_pairs": p_trace.get("current_pairs"),
            "candidate_pairs": p_trace.get("candidate_pairs"),
            "governance": p_execution.get("governance_result"),
            "governance_reason_codes": p_execution.get("governance_reason_codes"),
            "unresolved_prerequisites": p_trace.get("unresolved_prerequisites"),
        },
        "governance_decision": {
            "B0": "NOT_APPLICABLE",
            "P": p_execution.get("governance_result"),
            "P_reason_codes": p_execution.get("governance_reason_codes", []),
        },
        "evaluator_execution": {
            "status": "COMPLETED" if len(evaluator_records) == 2 else "PARTIAL",
            "observations": evaluator_records,
            "evaluator_time_ns": evaluator_duration_ns,
            "verification_time_ns": verification_duration_ns,
        },
        "semantic_pair_verification": dict(pair_record),
        "rq1_scoring": dict(rq1),
        "rq2_scoring": {
            "status": "UNKNOWN",
            "reason": rq2_detail["reason"],
            "required_obligation_set_bound": True,
            "same_denominator_for_arms": True,
            "result_path": "rq2_obligation_evidence.json",
            "diagnostic_pairs_path": "semantic_pair_verification.json",
        },
        "resource_metrics": {
            "status": "UNKNOWN",
            "host_cpu_time_ns": None,
            "container_cpu_time_ns": None,
            "peak_rss_bytes": None,
            "execution_overhead": {
                "B0_container_wall_ns": b0_execution.get("docker_runtime_ns"),
                "P_container_wall_ns": p_execution.get("docker_runtime_ns"),
                "P_adaptation_ns": p_execution.get("adaptation_time_ns"),
                "evaluator_wall_ns": evaluator_duration_ns,
            },
        },
        "research_gates": {
            "G1": "INCOMPLETE",
            "G4": "NOT AUTHORIZED",
            "P_ALGORITHM_STATUS": "NOT_READY",
        },
        "limitations": [
            "E1 is calibration-exposed and is not a blind holdout.",
            "TEST_ONLY signatures and applicability assumptions are not production authority.",
            "RQ2 remains UNKNOWN over the complete six-obligation denominator.",
            "One architecture transition does not support statistical significance.",
        ],
        "artifacts": artifacts,
    }
    return manifest


def _git_text(cwd: Path, *args: str) -> str:
    return (
        execution._run_checked(["git", *args], cwd=cwd, label="read E1 git revision", timeout=30)
        .stdout.decode("utf-8")
        .strip()
    )


def _write_once(path: Path, payload: Any) -> str:
    return execution._write_once(path, payload)


def _safe(root: Path, relative: str) -> Path:
    path = root.joinpath(*Path(relative).parts)
    if Path(relative).is_absolute() or ".." in Path(relative).parts or path.is_symlink():
        raise B0PE1ExecutionError("E1 artifact path is unsafe")
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root.resolve(strict=True)) or not resolved.is_file():
        raise B0PE1ExecutionError("E1 artifact is outside its run or is not a regular file")
    return resolved


def _safe_dir(root: Path, relative: str) -> Path:
    path = root.joinpath(*Path(relative).parts)
    if Path(relative).is_absolute() or ".." in Path(relative).parts or path.is_symlink():
        raise B0PE1ExecutionError("E1 directory path is unsafe")
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root.resolve(strict=True)) or not resolved.is_dir():
        raise B0PE1ExecutionError("E1 directory is outside its run or is not a regular directory")
    return resolved


def _verify_e1_method_input(root: Path, evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Verify the P input directory and its exact digest and policy revision bindings."""
    bundle = verify_method_bundle_v3(
        _safe_dir(root, str(evidence["p_input_path"])), expected_method_id="P"
    )
    if bundle["bundle_sha256"] != evidence["p_input_bundle_sha256"]:
        raise B0PE1ExecutionError("E1 P input bundle digest changed")
    if bundle["policy_source_revision"] != evidence["p_policy_source_revision"]:
        raise B0PE1ExecutionError("E1 policy revision binding changed")
    return cast(dict[str, Any], bundle)


def _load_e1_semantic_pairs(
    root: Path,
    evidence: Mapping[str, Any],
    *,
    repository_root: Path,
    expected_architecture_source_sha: str,
) -> list[dict[str, Any]]:
    """Read exact-pair proofs from the copied, run-contained verification directory."""
    return load_verified_pair_inputs(
        _safe_dir(root, str(evidence["semantic_verification_path"])),
        repository_root=repository_root,
        expected_architecture_source_sha=expected_architecture_source_sha,
    )


def _execution_status(
    b0_execution: Mapping[str, Any],
    p_execution: Mapping[str, Any],
    evaluator_records: list[Mapping[str, Any]],
) -> str:
    """Distinguish completed executions from missing arms or evaluator streams."""
    if (
        b0_execution.get("docker_exit_status") == 0
        and p_execution.get("docker_exit_status") == 0
        and len(evaluator_records) == 2
    ):
        return "EXECUTED_COMPLETE"
    return "EXECUTED_PARTIAL"
