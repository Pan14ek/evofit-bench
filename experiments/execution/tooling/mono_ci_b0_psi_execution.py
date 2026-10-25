"""DEVELOPMENT-only execution contracts for the separately proposed MONO CI B0/Ψ study.

The runner materializes source-pinned common inputs, executes only the bounded
B0 evaluator probe in a clearly labeled DEVELOPMENT run, and preserves the
existing measured-P and study authorization guards. It never scores results.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess  # nosec B404
import sys
import tarfile
import tempfile
import time
import zipfile
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import Any, cast

from architecture.acceptance.a1.analyzers import ANALYZERS
from architecture.acceptance.a1.engine import run_evaluator
from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import (
    ContractValidationError,
    MethodNotReadyError,
    ProtocolError,
)
from experiments.execution.tooling.hashing import pretty_json_bytes, sha256_bytes, sha256_file
from experiments.execution.tooling.mono_ci_b0_psi_preflight import (
    CASE_MANIFEST_NAME,
    PACKAGE_RELATIVE,
    verify_preflight,
)
from experiments.execution.tooling.p_interface import P_ALGORITHM_STATUS, require_p_algorithm

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PROPOSAL_RELATIVE = Path("experiments/execution/mono-ci-b0-psi-execution-v1")
BASELINE_NAME = "RECONSTRUCTED_B0_A03_V1.json"
RECONSTRUCTION_NAME = "BASELINE_RECONSTRUCTION_V1.json"
PACKAGE_CHECKSUMS_NAME = "SHA256SUMS"
ARM_INPUT_SCHEMA = "mono_ci_b0_psi_arm_input_v1.schema.json"
DEV_RUN_SCHEMA = "mono_ci_b0_psi_dev_run_v1.schema.json"
BASELINE_SCHEMA = "mono_ci_b0_psi_reconstructed_baseline_v1.schema.json"
RECONSTRUCTION_SCHEMA = "mono_ci_b0_psi_baseline_reconstruction_v1.schema.json"
CONTROL_IDS = ("AC_PUBLIC_API", "AC_MODULE_GRAPH")
COMMON_INPUT_IDS = [
    "A03_ARCHITECTURE_SOURCE",
    "CASE_A04_ARCHITECTURE_SOURCE",
    "A03_A04_STATE_MANIFESTS",
    "RECONSTRUCTED_B0_CONFIGURATION_PROPOSAL",
    "OBLIGATION_CATALOG_CONTEXT",
    "EVALUATOR_CONFIGURATIONS",
]
FORBIDDEN_PATH_PARTS = {
    ".git",
    "scorer",
    "scoring",
    "oracle",
    "reference",
    "expected_outputs",
    "ground_truth",
    "groundtruth",
    "results",
    "eval01",
    "eval02",
    "evaluator_control_expectations",
}
FORBIDDEN_CONTENT_MARKERS = (
    b"expected_operations",
    b"affected_targets",
    b"ground_truth_path",
)
SHA1_PATTERN = re.compile(r"^[a-f0-9]{40}$")
RUN_ID_PATTERN = re.compile(r"^DEV_MONO_CI_[A-Za-z0-9_-]{1,48}$")


def verify_execution_proposal(repository: Path = REPOSITORY_ROOT) -> dict[str, Any]:
    """Verify the reconstruction proposal and exact canonical source identities."""
    root = repository.resolve(strict=True)
    proposal_root = root / PROPOSAL_RELATIVE
    config = _read_json(proposal_root / BASELINE_NAME)
    reconstruction = _read_json(proposal_root / RECONSTRUCTION_NAME)
    validate_payload(BASELINE_SCHEMA, config)
    validate_payload(RECONSTRUCTION_SCHEMA, reconstruction)
    _verify_proposal_inventory(proposal_root)

    configuration_bytes = (proposal_root / BASELINE_NAME).read_bytes()
    configuration_digest = sha256_bytes(configuration_bytes)
    sidecar = (proposal_root / f"{BASELINE_NAME}.sha256").read_text(encoding="utf-8").strip()
    if sidecar != f"{configuration_digest}  {BASELINE_NAME}":
        raise ContractValidationError("MONO_CI_B0_PSI_RECONSTRUCTION_SIDECAR_MISMATCH")
    if reconstruction["configuration_sha256"] != configuration_digest:
        raise ContractValidationError("MONO_CI_B0_PSI_RECONSTRUCTION_DIGEST_MISMATCH")
    if reconstruction["historical_configuration_search"]["later_B0_DEV_A03_is_historical"]:
        raise ContractValidationError("MONO_CI_B0_PSI_DEV_A03_CANNOT_BE_HISTORICAL")

    before_sha = config["derivation"]["source_commit_sha"]
    expected_before_tree = config["derivation"]["source_repository_tree_sha"]
    expected_before_app_tree = config["derivation"]["source_application_tree_sha"]
    after_sha = "d3101c0d3aa9b7b709253b6ec7518416f05f65b9"
    _verify_git_commit(root, before_sha, expected_before_tree, expected_before_app_tree)
    _verify_git_commit(
        root,
        after_sha,
        "2b436e0aaf09403ea516d73d20a466a122f86592",
        "007196f68652bc13f6798805793ffdfae96f95f7",
    )

    state_manifest = config["derivation"]["state_manifest_path"]
    state_bytes = _git_bytes(root, before_sha, state_manifest)
    if sha256_bytes(state_bytes) != config["derivation"]["state_manifest_sha256"]:
        raise ContractValidationError("MONO_CI_B0_PSI_A03_STATE_MANIFEST_DIGEST_MISMATCH")
    import yaml

    before_state = yaml.safe_load(state_bytes)
    after_state = yaml.safe_load(
        _git_bytes(root, after_sha, "architecture/states/A0_4_REPORT_QUERY_PORT.yaml")
    )
    before_evaluators = before_state.get("governance_requirements", {}).get("required_evaluators")
    after_evaluators = after_state.get("governance_requirements", {}).get("required_evaluators")
    if before_evaluators != list(CONTROL_IDS):
        raise ContractValidationError("MONO_CI_B0_PSI_A03_REQUIRED_CONTROLS_MISMATCH")
    if after_evaluators != list(CONTROL_IDS):
        raise ContractValidationError("MONO_CI_B0_PSI_A04_REQUIRED_CONTROLS_MISMATCH")

    for representation in config["representations"]:
        config_path = root / representation["evaluator_configuration_path"]
        if (
            config_path.is_symlink()
            or sha256_file(config_path) != representation["evaluator_configuration_sha256"]
        ):
            raise ContractValidationError(
                f"MONO_CI_B0_PSI_EVALUATOR_CONFIGURATION_DIGEST_MISMATCH:{representation['evaluator_id']}"
            )
    return {
        "baseline_id": config["configuration_id"],
        "baseline_configuration_sha256": configuration_digest,
        "identity_status": "PROSPECTIVE_RECONSTRUCTION_NOT_HISTORICAL",
        "approval_status": "NOT_APPROVED",
        "study_readiness": "NO_GO",
    }


def materialize_development_inputs(
    repository: Path,
    output_root: Path,
    execution_id: str,
) -> dict[str, Any]:
    """Build separate, digest-bound DEVELOPMENT common-input bundles for B0 and Ψ.

    The bundles contain source/configuration bytes only. They omit `.git`, all
    evaluator observations, scorer/reference materials, and arm outputs.
    """
    root = repository.resolve(strict=True)
    if RUN_ID_PATTERN.fullmatch(execution_id) is None:
        raise ProtocolError("MONO_CI_B0_PSI_EXECUTION_ID_INVALID")
    destination = output_root.expanduser().absolute()
    _require_new_external_directory(root, destination)

    preflight = verify_preflight(root)
    if preflight["integrity_status"] != "PASS" or preflight["readiness"] != "NO_GO":
        raise ProtocolError("MONO_CI_B0_PSI_STUDY_PREFLIGHT_STATUS_CHANGED_REQUIRES_REVIEW")
    baseline = verify_execution_proposal(root)

    case_manifest_path = root / PACKAGE_RELATIVE / CASE_MANIFEST_NAME
    case_manifest = _read_json(case_manifest_path)
    inputs = _read_json(root / PACKAGE_RELATIVE / "INPUTS_V1.json")
    case_sources = {row["case_id"]: row for row in inputs["case_sources"]}
    proposal_root = root / PROPOSAL_RELATIVE
    config_bytes = (proposal_root / BASELINE_NAME).read_bytes()
    catalog_path = root / "fitness/catalog/architectural-obligations.yaml"
    before_source_sha = case_manifest["architecture_transition"]["before_commit_sha"]
    before_app = _git_archive_application(root, before_source_sha)
    destination.mkdir(parents=True, exist_ok=False)

    try:
        with tempfile.TemporaryDirectory(prefix="mono-ci-b0-psi-git-") as temporary:
            bare = Path(temporary) / "case-source.git"
            _git_run(root, ("clone", "--bare", "--shared", str(root), str(bare)))
            _fetch_case_bundles(root, bare, case_manifest)

            case_digests: dict[str, dict[str, str]] = {}
            for case in case_manifest["cases"]:
                case_id = case["case_id"]
                source = case_sources[case_id]
                _verify_git_commit(
                    bare,
                    case["source_commit_sha"],
                    case["repository_tree_sha"],
                    case["application_tree_sha"],
                )
                target_app = _git_archive_application(bare, case["source_commit_sha"])
                before_manifest = _git_bytes(
                    root,
                    before_source_sha,
                    "architecture/states/A0_3_GOVERNED_MODULE_GRAPH.yaml",
                )
                target_manifest = _git_bytes(
                    bare,
                    case["source_commit_sha"],
                    "architecture/states/A0_4_REPORT_QUERY_PORT.yaml",
                )
                common_files: dict[str, tuple[str, bytes]] = {
                    **_prefixed_files(
                        before_app, "architecture/before", "architecture_before_source"
                    ),
                    **_prefixed_files(target_app, "architecture/case", "architecture_case_source"),
                    "architecture/state-before.yaml": (
                        "architecture_state_manifest",
                        before_manifest,
                    ),
                    "architecture/state-target.yaml": (
                        "architecture_state_manifest",
                        target_manifest,
                    ),
                    "fitness/reconstructed-b0.json": ("baseline_configuration", config_bytes),
                    "fitness/obligations.yaml": ("obligation_catalog", catalog_path.read_bytes()),
                }
                for representation in _read_json(proposal_root / BASELINE_NAME)["representations"]:
                    evaluator_name = representation["evaluator_id"]
                    relative = representation["evaluator_configuration_path"]
                    common_files[f"evaluators/{evaluator_name}.yaml"] = (
                        "evaluator_configuration",
                        (root / relative).read_bytes(),
                    )

                case_binding = {
                    "case_id": case_id,
                    "source_commit_sha": source["source_commit_sha"],
                    "repository_tree_sha": source["repository_tree_sha"],
                    "application_tree_sha": source["application_tree_sha"],
                }
                arm_bundles: dict[str, dict[str, Any]] = {}
                for arm_id in ("B0", "PSI"):
                    bundle_root = destination / arm_id / "input_bundle" / case_id
                    bundle_root.mkdir(parents=True, exist_ok=False)
                    file_records: list[dict[str, Any]] = []
                    for relative, (role, content) in sorted(common_files.items()):
                        _validate_bundle_file(relative, content)
                        _write_new_bytes(bundle_root, relative, content)
                        file_records.append(
                            {
                                "path": relative,
                                "role": role,
                                "size_bytes": len(content),
                                "sha256": sha256_bytes(content),
                            }
                        )
                    common_digest = sha256_bytes(
                        _canonical_json(
                            {
                                "case": case_binding,
                                "baseline_configuration_sha256": baseline[
                                    "baseline_configuration_sha256"
                                ],
                                "common_input_ids": COMMON_INPUT_IDS,
                                "files": file_records,
                            }
                        )
                    )
                    manifest_body = {
                        "schema_version": "MONO_CI_B0_PSI_ARM_INPUT_V1",
                        "execution_id": execution_id,
                        "study_id": "MONO_CI_B0_PSI_DEVELOPMENT_TECHNICAL_VALIDATION",
                        "mode": "DEVELOPMENT_TECHNICAL_VALIDATION_ONLY",
                        "arm_id": arm_id,
                        "case": case_binding,
                        "baseline_configuration_sha256": baseline["baseline_configuration_sha256"],
                        "allowlist_version": "MONO_CI_B0_PSI_COMMON_INPUTS_DEV_V1",
                        "common_input_ids": COMMON_INPUT_IDS,
                        "common_input_sha256": common_digest,
                        "files": file_records,
                    }
                    manifest_body["bundle_sha256"] = sha256_bytes(_canonical_json(manifest_body))
                    validate_payload(ARM_INPUT_SCHEMA, manifest_body)
                    manifest_bytes = pretty_json_bytes(manifest_body)
                    _write_new_bytes(bundle_root, "manifest.json", manifest_bytes)
                    checksums = _write_checksums(bundle_root, exclude={"SHA256SUMS"})
                    verified = verify_arm_input_bundle(bundle_root, expected_arm=arm_id)
                    arm_bundles[arm_id] = verified
                    if checksums != _read_checksums(bundle_root / "SHA256SUMS"):
                        raise ContractValidationError("MONO_CI_B0_PSI_INPUT_BUNDLE_SEAL_MISMATCH")
                if (
                    arm_bundles["B0"]["common_input_sha256"]
                    != arm_bundles["PSI"]["common_input_sha256"]
                ):
                    raise ContractValidationError(
                        f"MONO_CI_B0_PSI_DEVELOPMENT_INPUT_PARITY_FAILED:{case_id}"
                    )
                case_digests[case_id] = {
                    "B0": str(arm_bundles["B0"]["bundle_sha256"]),
                    "PSI": str(arm_bundles["PSI"]["bundle_sha256"]),
                    "common_input_sha256": str(arm_bundles["B0"]["common_input_sha256"]),
                }
    except (OSError, subprocess.SubprocessError, tarfile.TarError, zipfile.BadZipFile):
        # Preserve partial artifacts for inspection; the unique run path is write-once.
        raise

    return {
        "execution_id": execution_id,
        "output_root": str(destination),
        "baseline": baseline,
        "case_count": len(case_digests),
        "case_digests": case_digests,
    }


def verify_arm_input_bundle(
    bundle_root: Path, *, expected_arm: str | None = None
) -> dict[str, Any]:
    """Read back one sealed input bundle and reject unsafe or unexpected files."""
    root = bundle_root.resolve(strict=True)
    manifest = _read_json(root / "manifest.json")
    validate_payload(ARM_INPUT_SCHEMA, manifest)
    if expected_arm is not None and manifest["arm_id"] != expected_arm:
        raise ContractValidationError("MONO_CI_B0_PSI_ARM_INPUT_ID_MISMATCH")
    if manifest["bundle_sha256"] != _bundle_digest(manifest):
        raise ContractValidationError("MONO_CI_B0_PSI_ARM_INPUT_BUNDLE_DIGEST_MISMATCH")

    declared = {record["path"]: record for record in manifest["files"]}
    observed: set[str] = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ContractValidationError("MONO_CI_B0_PSI_ARM_INPUT_SYMLINK_FORBIDDEN")
        if not path.is_file() or path.name == "SHA256SUMS":
            continue
        relative = path.relative_to(root).as_posix()
        if relative == "manifest.json":
            continue
        _validate_relative_path(relative)
        observed.add(relative)
        record = declared.get(relative)
        if record is None:
            raise ContractValidationError("MONO_CI_B0_PSI_ARM_INPUT_UNDECLARED_FILE")
        content = path.read_bytes()
        _validate_bundle_file(relative, content)
        if len(content) != record["size_bytes"] or sha256_bytes(content) != record["sha256"]:
            raise ContractValidationError("MONO_CI_B0_PSI_ARM_INPUT_FILE_DIGEST_MISMATCH")
    if observed != set(declared):
        raise ContractValidationError("MONO_CI_B0_PSI_ARM_INPUT_INVENTORY_MISMATCH")
    checksums = _read_checksums(root / "SHA256SUMS")
    actual = {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in root.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS"
    }
    if checksums != actual:
        raise ContractValidationError("MONO_CI_B0_PSI_ARM_INPUT_CHECKSUMS_MISMATCH")
    return manifest


def run_development_validation(
    repository: Path,
    output_root: Path,
    execution_id: str,
) -> dict[str, Any]:
    """Run source-pinned evaluator probes under a DEVELOPMENT-only identity.

    The reconstructed baseline is unapproved, so these raw evaluator outputs
    are technical harness evidence. No operation, governance decision, metric,
    or comparison score is produced. Ψ remains blocked by its existing guard.
    """
    root = repository.resolve(strict=True)
    materialized = materialize_development_inputs(root, output_root, execution_id)
    run_root = Path(materialized["output_root"])
    baseline = materialized["baseline"]
    baseline_config = _read_json(root / PROPOSAL_RELATIVE / BASELINE_NAME)
    inputs = _read_json(root / PACKAGE_RELATIVE / "INPUTS_V1.json")
    case_sources = {row["case_id"]: row for row in inputs["case_sources"]}
    case_manifest = _read_json(root / PACKAGE_RELATIVE / CASE_MANIFEST_NAME)
    output_checksums: dict[str, str] = {}
    b0_case_results: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="mono-ci-b0-psi-evaluator-") as temporary:
        bare = Path(temporary) / "case-source.git"
        _git_run(root, ("clone", "--bare", "--shared", str(root), str(bare)))
        _fetch_case_bundles(root, bare, case_manifest)
        for case_id in sorted(case_sources):
            source = case_sources[case_id]
            subject = Path(temporary) / case_id
            _git_run(
                root,
                ("clone", "--quiet", "--shared", "--no-checkout", str(bare), str(subject)),
            )
            _git_run(
                root,
                (
                    "-C",
                    str(subject),
                    "checkout",
                    "--quiet",
                    "--detach",
                    source["source_commit_sha"],
                ),
            )
            _verify_checkout_identity(subject, source)

            input_bundle = run_root / "B0/input_bundle" / case_id
            b0_manifest = verify_arm_input_bundle(input_bundle, expected_arm="B0")
            input_binding = _verify_execution_input_binding(
                bare, subject, input_bundle, b0_manifest, source, baseline_config, baseline
            )
            raw_root = run_root / "B0/raw" / case_id
            raw_root.mkdir(parents=True, exist_ok=False)
            timer_start = time.monotonic_ns()
            evaluator_records: list[dict[str, Any]] = []
            for evaluator_id in CONTROL_IDS:
                representation = _representation_for(baseline_config, evaluator_id)
                config_path = input_bundle / "evaluators" / f"{evaluator_id}.yaml"
                manifest_path = input_bundle / "architecture/state-target.yaml"
                current_binding = _verify_execution_input_binding(
                    bare, subject, input_bundle, b0_manifest, source, baseline_config, baseline
                )
                if current_binding != input_binding:
                    raise ContractValidationError(
                        "MONO_CI_B0_PSI_EXECUTION_INPUTS_CHANGED_BEFORE_EVALUATOR"
                    )
                evidence = run_evaluator(
                    evaluator_id,
                    subject,
                    config_path,
                    manifest_path,
                    "A0_4_REPORT_QUERY_PORT",
                    source["source_commit_sha"],
                    ANALYZERS[evaluator_id],
                    evidence_root=input_bundle,
                )
                after_binding = _verify_execution_input_binding(
                    bare, subject, input_bundle, b0_manifest, source, baseline_config, baseline
                )
                if after_binding != input_binding:
                    raise ContractValidationError(
                        "MONO_CI_B0_PSI_EXECUTION_INPUTS_CHANGED_DURING_EVALUATOR"
                    )
                _verify_evaluator_binding(
                    evidence,
                    source,
                    representation["evaluator_source_sha256"],
                    representation["evaluator_configuration_sha256"],
                )
                _verify_evaluator_input_binding(evidence, input_binding, evaluator_id, input_bundle)
                raw_path = raw_root / f"{evaluator_id}.json"
                raw_bytes = pretty_json_bytes(evidence)
                _write_new_file(raw_path, raw_bytes)
                raw_digest = sha256_bytes(raw_bytes)
                output_relative = raw_path.relative_to(run_root).as_posix()
                output_checksums[output_relative] = raw_digest
                evaluator_records.append(
                    {
                        "evaluator_id": evaluator_id,
                        "version": representation["evaluator_version"],
                        "source_sha256": evidence["evaluator"]["source_digest"],
                        "configuration_sha256": evidence["evaluator"]["configuration_digest"],
                        "exit_code": _evaluator_exit_code(evidence),
                        "compliance": evidence["result"]["compliance"],
                        "raw_output_path": output_relative,
                        "raw_output_sha256": raw_digest,
                    }
                )
            _write_checksums(raw_root, exclude={"SHA256SUMS"})
            timer_end = time.monotonic_ns()
            b0_case_results.append(
                {
                    "case_id": case_id,
                    "source_commit_sha": source["source_commit_sha"],
                    "repository_tree_sha": source["repository_tree_sha"],
                    "application_tree_sha": source["application_tree_sha"],
                    "status": "DEVELOPMENT_ONLY_EXECUTED",
                    "scientific_applicability": "UNKNOWN",
                    "fitness_validity": "UNKNOWN",
                    "input_bundle_sha256": b0_manifest["bundle_sha256"],
                    "execution_binding": input_binding,
                    "evaluators": evaluator_records,
                    "technical_duration_ns": timer_end - timer_start,
                    "result_paths": [item["raw_output_path"] for item in evaluator_records],
                }
            )

    try:
        require_p_algorithm()
    except MethodNotReadyError:
        psi_status = {
            "status": "BLOCKED_NOT_EXECUTED",
            "reason": "P_ALGORITHM_STATUS_NOT_READY",
            "prediction_emitted": False,
            "operation_emitted": False,
            "governance_decision_emitted": False,
        }
    else:
        raise ProtocolError("MONO_CI_B0_PSI_MEASURED_P_GUARD_CHANGED_REQUIRES_REVIEW")

    contract_statuses = {
        "operation_selection_correctness": {"B0": "N/A", "PSI": "NOT_EVALUABLE"},
        "governance_decision_correctness": {"B0": "N/A", "PSI": "NOT_EVALUABLE"},
        "current_configuration_verified_coverage": {
            "B0": "NOT_EVALUABLE",
            "PSI": "NOT_EVALUABLE",
        },
        "controlled_violation_detection": {"B0": "NOT_MEASURED", "PSI": "NOT_MEASURED"},
        "stale_or_semantically_invalid_representations": {
            "B0": "NOT_EVALUABLE",
            "PSI": "NOT_EVALUABLE",
        },
        "assessed_candidate_coverage": {"B0": "N/A", "PSI": "NOT_MEASURED"},
        "actual_post_adaptation_coverage": {"B0": "N/A", "PSI": "NOT_MEASURED"},
        "end_to_end_case_execution_duration": {"B0": "NOT_MEASURED", "PSI": "NOT_MEASURED"},
    }
    record = {
        "schema_version": "MONO_CI_B0_PSI_DEV_RUN_V1",
        "execution_id": execution_id,
        "study_id": "MONO_CI_B0_PSI_DEVELOPMENT_TECHNICAL_VALIDATION",
        "parent_study_id": "MONO_CI_B0_PSI_COMPARISON_V1",
        "mode": "DEVELOPMENT_TECHNICAL_VALIDATION_ONLY",
        "study_readiness": "NO_GO",
        "measurement_status": "NOT_EXECUTED",
        "baseline": {
            "configuration_id": baseline["baseline_id"],
            "configuration_sha256": baseline["baseline_configuration_sha256"],
            "identity_status": baseline["identity_status"],
            "approval_status": baseline["approval_status"],
        },
        "common_input_parity": {
            "status": "PASS_DEVELOPMENT_COMMON_INPUTS_ONLY",
            "case_count": len(b0_case_results),
            "common_input_ids": COMMON_INPUT_IDS,
        },
        "arms": {
            "B0": {
                "status": "DEVELOPMENT_EVALUATOR_PROBE_ONLY",
                "case_results": b0_case_results,
                "adaptation_operation": None,
                "governance_decision": None,
                "technical_duration_boundary": (
                    "CASE_START_THROUGH_RAW_EVALUATOR_OUTPUT_CHECKSUM_SEAL"
                ),
            },
            "PSI": psi_status,
        },
        "metrics": contract_statuses,
        "scoring": "NOT_EXECUTED_NO_SCORER_REFERENCE",
        "output_checksums": output_checksums,
    }
    validate_payload(DEV_RUN_SCHEMA, record)
    result_path = run_root / "development_run.json"
    _write_new_file(result_path, pretty_json_bytes(record))
    result_digest = sha256_file(result_path)
    _write_new_file(
        run_root / "development_run.json.sha256",
        f"{result_digest}  development_run.json\n".encode(),
    )
    all_checksums = _write_checksums(run_root, exclude={"SHA256SUMS"})
    verify_development_result(run_root)
    return {
        "execution_id": execution_id,
        "study_readiness": "NO_GO",
        "measurement_status": "NOT_EXECUTED",
        "B0": "DEVELOPMENT_EVALUATOR_PROBE_ONLY",
        "PSI": "BLOCKED_NOT_EXECUTED",
        "P_ALGORITHM_STATUS": P_ALGORITHM_STATUS,
        "scoring": "NOT_EXECUTED",
        "result_path": str(result_path),
        "result_sha256": result_digest,
        "checksums": all_checksums,
        "case_count": len(b0_case_results),
    }


def verify_development_result(run_root: Path) -> dict[str, Any]:
    """Verify development result checksums and preserve the nonmeasurement status."""
    root = run_root.resolve(strict=True)
    record = _read_json(root / "development_run.json")
    validate_payload(DEV_RUN_SCHEMA, record)
    if record["study_readiness"] != "NO_GO" or record["measurement_status"] != "NOT_EXECUTED":
        raise ContractValidationError("MONO_CI_B0_PSI_DEVELOPMENT_RESULT_PROMOTED")
    if record["arms"]["PSI"]["prediction_emitted"] or record["arms"]["PSI"]["operation_emitted"]:
        raise ContractValidationError("MONO_CI_B0_PSI_PREDICTION_EMITTED_WITHOUT_METHOD")
    expected_cases = [f"CASE_0{number}" for number in range(1, 5)]
    case_results = record["arms"]["B0"]["case_results"]
    if [case["case_id"] for case in case_results] != expected_cases:
        raise ContractValidationError("MONO_CI_B0_PSI_DEVELOPMENT_CASE_INVENTORY_MISMATCH")
    expected_raw_paths = {
        f"B0/raw/{case_id}/{evaluator_id}.json"
        for case_id in expected_cases
        for evaluator_id in CONTROL_IDS
    }
    if set(record["output_checksums"]) != expected_raw_paths:
        raise ContractValidationError("MONO_CI_B0_PSI_DEVELOPMENT_RAW_OUTPUT_INVENTORY_MISMATCH")
    for relative, expected in record["output_checksums"].items():
        path = _safe_child(root, relative)
        if sha256_file(path) != expected:
            raise ContractValidationError("MONO_CI_B0_PSI_DEVELOPMENT_RAW_OUTPUT_DIGEST_MISMATCH")
    for case in case_results:
        case_id = case["case_id"]
        bundle_manifests: dict[str, dict[str, Any]] = {}
        for arm in ("B0", "PSI"):
            bundle_root = root / arm / "input_bundle" / case_id
            manifest = verify_arm_input_bundle(bundle_root, expected_arm=arm)
            if manifest["execution_id"] != record["execution_id"]:
                raise ContractValidationError("MONO_CI_B0_PSI_DEVELOPMENT_BUNDLE_RUN_MISMATCH")
            binding = {
                "case_id": case_id,
                "source_commit_sha": case["source_commit_sha"],
                "repository_tree_sha": case["repository_tree_sha"],
                "application_tree_sha": case["application_tree_sha"],
            }
            if manifest["case"] != binding:
                raise ContractValidationError("MONO_CI_B0_PSI_DEVELOPMENT_CASE_SOURCE_MISMATCH")
            if (
                manifest["baseline_configuration_sha256"]
                != record["baseline"]["configuration_sha256"]
            ):
                raise ContractValidationError(
                    "MONO_CI_B0_PSI_DEVELOPMENT_BASELINE_BINDING_MISMATCH"
                )
            bundle_manifests[arm] = manifest
        if (
            bundle_manifests["B0"]["common_input_sha256"]
            != bundle_manifests["PSI"]["common_input_sha256"]
            or case["input_bundle_sha256"] != bundle_manifests["B0"]["bundle_sha256"]
        ):
            raise ContractValidationError("MONO_CI_B0_PSI_DEVELOPMENT_BUNDLE_BINDING_MISMATCH")
        expected_execution_binding = _execution_binding_from_bundle(
            root / "B0/input_bundle" / case_id, bundle_manifests["B0"]
        )
        if case["execution_binding"] != expected_execution_binding:
            raise ContractValidationError("MONO_CI_B0_PSI_DEVELOPMENT_EXECUTION_BINDING_MISMATCH")
        evaluator_bindings = {
            item["evaluator_id"]: item["configuration_sha256"]
            for item in expected_execution_binding["evaluator_configurations"]
        }
        baseline_config = _read_json(
            _safe_child(root / "B0/input_bundle" / case_id, "fitness/reconstructed-b0.json")
        )
        if {item["evaluator_id"] for item in case["evaluators"]} != set(CONTROL_IDS):
            raise ContractValidationError("MONO_CI_B0_PSI_DEVELOPMENT_EVALUATOR_INVENTORY_MISMATCH")
        if set(case["result_paths"]) != {item["raw_output_path"] for item in case["evaluators"]}:
            raise ContractValidationError("MONO_CI_B0_PSI_DEVELOPMENT_RESULT_PATH_MISMATCH")
        for evaluator in case["evaluators"]:
            if evaluator["configuration_sha256"] != evaluator_bindings.get(
                evaluator["evaluator_id"]
            ):
                raise ContractValidationError("MONO_CI_B0_PSI_DEVELOPMENT_CONFIG_BINDING_MISMATCH")
            representation = _representation_for(baseline_config, evaluator["evaluator_id"])
            if (
                evaluator["source_sha256"] != representation["evaluator_source_sha256"]
                or evaluator["configuration_sha256"]
                != representation["evaluator_configuration_sha256"]
                or evaluator["version"] != representation["evaluator_version"]
            ):
                raise ContractValidationError(
                    "MONO_CI_B0_PSI_DEVELOPMENT_EVALUATOR_IDENTITY_MISMATCH"
                )
            evidence = _read_json(_safe_child(root, evaluator["raw_output_path"]))
            _verify_evaluator_binding(
                evidence,
                case,
                representation["evaluator_source_sha256"],
                representation["evaluator_configuration_sha256"],
            )
            _verify_evaluator_input_binding(
                evidence,
                case["execution_binding"],
                evaluator["evaluator_id"],
                root / "B0/input_bundle" / case_id,
            )
            _validate_raw_evaluator_evidence(evidence)
            if (
                evidence["evaluator"].get("version") != evaluator["version"]
                or evidence["result"].get("compliance") != evaluator["compliance"]
                or _evaluator_exit_code(evidence) != evaluator["exit_code"]
            ):
                raise ContractValidationError(
                    "MONO_CI_B0_PSI_DEVELOPMENT_EVALUATOR_RESULT_MISMATCH"
                )
    expected_result = record["execution_id"]
    sidecar = (root / "development_run.json.sha256").read_text(encoding="utf-8").strip()
    if sidecar != f"{sha256_file(root / 'development_run.json')}  development_run.json":
        raise ContractValidationError("MONO_CI_B0_PSI_DEVELOPMENT_RESULT_SEAL_MISMATCH")
    if not expected_result or _read_checksums(root / "SHA256SUMS") != _directory_checksums(
        root, exclude={"SHA256SUMS"}
    ):
        raise ContractValidationError("MONO_CI_B0_PSI_DEVELOPMENT_RUN_CHECKSUM_INVENTORY_MISMATCH")
    _validate_development_run_inventory(root, expected_raw_paths)
    return record


def execute_official_study(*_args: Any, **_kwargs: Any) -> None:
    """Fail closed until this separate study is approved and Ψ is ready."""
    preflight = verify_preflight(REPOSITORY_ROOT)
    if preflight["integrity_status"] != "PASS" or preflight["readiness"] != "GO":
        raise MethodNotReadyError(
            "MONO_CI_B0_PSI_STUDY_NO_GO: official execution is not authorized"
        )
    require_p_algorithm()


def _verify_proposal_inventory(proposal_root: Path) -> None:
    checksum_path = proposal_root / PACKAGE_CHECKSUMS_NAME
    if not checksum_path.is_file() or checksum_path.is_symlink():
        raise ContractValidationError("MONO_CI_B0_PSI_PROPOSAL_CHECKSUMS_MISSING")
    declared = _read_checksums(checksum_path)
    actual = _directory_checksums(proposal_root, exclude={PACKAGE_CHECKSUMS_NAME})
    if declared != actual:
        raise ContractValidationError("MONO_CI_B0_PSI_PROPOSAL_CHECKSUM_INVENTORY_MISMATCH")


def _verify_git_commit(
    repository: Path, commit: str, expected_tree: str, expected_app_tree: str
) -> None:
    if not SHA1_PATTERN.fullmatch(commit):
        raise ProtocolError("MONO_CI_B0_PSI_SOURCE_COMMIT_SHA_INVALID")
    if _git_text(repository, "rev-parse", f"{commit}^{{tree}}") != expected_tree:
        raise ContractValidationError("MONO_CI_B0_PSI_REPOSITORY_TREE_MISMATCH")
    if _git_text(repository, "rev-parse", f"{commit}:app") != expected_app_tree:
        raise ContractValidationError("MONO_CI_B0_PSI_APPLICATION_TREE_MISMATCH")


def _verify_checkout_identity(checkout: Path, source: dict[str, Any]) -> None:
    if _git_text(checkout, "rev-parse", "HEAD") != source["source_commit_sha"]:
        raise ContractValidationError("MONO_CI_B0_PSI_CHECKOUT_COMMIT_MISMATCH")
    _verify_git_commit(
        checkout,
        source["source_commit_sha"],
        source["repository_tree_sha"],
        source["application_tree_sha"],
    )


def _verify_execution_input_binding(
    git_repository: Path,
    checkout: Path,
    bundle_root: Path,
    initial_manifest: dict[str, Any],
    source: dict[str, Any],
    baseline_config: dict[str, Any],
    baseline: dict[str, Any],
) -> dict[str, Any]:
    """Prove that evaluator source/config/state bytes are the sealed case inputs."""
    manifest = verify_arm_input_bundle(bundle_root, expected_arm="B0")
    if manifest != initial_manifest:
        raise ContractValidationError("MONO_CI_B0_PSI_EXECUTION_INPUT_BUNDLE_CHANGED")
    expected_case = {
        key: source[key]
        for key in (
            "case_id",
            "source_commit_sha",
            "repository_tree_sha",
            "application_tree_sha",
        )
    }
    if manifest["case"] != expected_case:
        raise ContractValidationError("MONO_CI_B0_PSI_EXECUTION_INPUT_CASE_BINDING_MISMATCH")
    if manifest["baseline_configuration_sha256"] != baseline["baseline_configuration_sha256"]:
        raise ContractValidationError("MONO_CI_B0_PSI_EXECUTION_INPUT_BASELINE_MISMATCH")

    _verify_git_commit(
        git_repository,
        source["source_commit_sha"],
        source["repository_tree_sha"],
        source["application_tree_sha"],
    )
    _verify_checkout_identity(checkout, source)
    bundled_source = _bundle_application_files(bundle_root, manifest)
    git_source = _git_archive_application(git_repository, source["source_commit_sha"])
    checkout_source = _checkout_application_files(checkout)
    if bundled_source != git_source or bundled_source != checkout_source:
        raise ContractValidationError("MONO_CI_B0_PSI_EXECUTION_SOURCE_BYTES_MISMATCH")

    state_path = "architecture/state-target.yaml"
    state_record = _bundle_file_record(manifest, state_path, "architecture_state_manifest")
    state_bytes = _safe_child(bundle_root, state_path).read_bytes()
    pinned_state = _git_bytes(
        git_repository,
        source["source_commit_sha"],
        "architecture/states/A0_4_REPORT_QUERY_PORT.yaml",
    )
    if state_bytes != pinned_state or sha256_bytes(state_bytes) != state_record["sha256"]:
        raise ContractValidationError("MONO_CI_B0_PSI_EXECUTION_STATE_MANIFEST_MISMATCH")

    evaluator_configurations: list[dict[str, str]] = []
    for evaluator_id in CONTROL_IDS:
        representation = _representation_for(baseline_config, evaluator_id)
        config_path = f"evaluators/{evaluator_id}.yaml"
        config_record = _bundle_file_record(manifest, config_path, "evaluator_configuration")
        config_bytes = _safe_child(bundle_root, config_path).read_bytes()
        expected_digest = representation["evaluator_configuration_sha256"]
        if (
            sha256_bytes(config_bytes) != expected_digest
            or config_record["sha256"] != expected_digest
        ):
            raise ContractValidationError(
                f"MONO_CI_B0_PSI_EXECUTION_CONFIG_DIGEST_MISMATCH:{evaluator_id}"
            )
        evaluator_configurations.append(
            {
                "evaluator_id": evaluator_id,
                "bundle_path": config_path,
                "configuration_sha256": expected_digest,
            }
        )

    source_file_digests = [
        {"path": path, "sha256": sha256_bytes(content)}
        for path, content in sorted(bundled_source.items())
    ]
    return {
        "workspace_kind": "GIT_CHECKOUT_BYTE_EQUIVALENT_TO_VERIFIED_BUNDLE",
        "checkout_commit_sha": source["source_commit_sha"],
        "repository_tree_sha": source["repository_tree_sha"],
        "application_tree_sha": source["application_tree_sha"],
        "source_file_count": len(source_file_digests),
        "source_file_map_sha256": sha256_bytes(_canonical_json(source_file_digests)),
        "input_bundle_sha256": manifest["bundle_sha256"],
        "target_state_manifest_path": state_path,
        "target_state_manifest_sha256": sha256_bytes(state_bytes),
        "evaluator_configurations": evaluator_configurations,
    }


def _bundle_application_files(bundle_root: Path, manifest: dict[str, Any]) -> dict[str, bytes]:
    prefix = "architecture/case/"
    files: dict[str, bytes] = {}
    for record in manifest["files"]:
        relative = record["path"]
        if not relative.startswith(prefix):
            continue
        if record["role"] != "architecture_case_source":
            raise ContractValidationError("MONO_CI_B0_PSI_EXECUTION_SOURCE_ROLE_MISMATCH")
        app_relative = f"app/{relative.removeprefix(prefix)}"
        _validate_relative_path(app_relative)
        files[app_relative] = _safe_child(bundle_root, relative).read_bytes()
    if not files:
        raise ContractValidationError("MONO_CI_B0_PSI_EXECUTION_SOURCE_BUNDLE_EMPTY")
    return files


def _execution_binding_from_bundle(bundle_root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    source_files = _bundle_application_files(bundle_root, manifest)
    source_file_digests = [
        {"path": path, "sha256": sha256_bytes(content)}
        for path, content in sorted(source_files.items())
    ]
    case = manifest["case"]
    state_path = "architecture/state-target.yaml"
    state_record = _bundle_file_record(manifest, state_path, "architecture_state_manifest")
    evaluator_configurations = []
    for evaluator_id in CONTROL_IDS:
        config_path = f"evaluators/{evaluator_id}.yaml"
        config_record = _bundle_file_record(manifest, config_path, "evaluator_configuration")
        evaluator_configurations.append(
            {
                "evaluator_id": evaluator_id,
                "bundle_path": config_path,
                "configuration_sha256": config_record["sha256"],
            }
        )
    return {
        "workspace_kind": "GIT_CHECKOUT_BYTE_EQUIVALENT_TO_VERIFIED_BUNDLE",
        "checkout_commit_sha": case["source_commit_sha"],
        "repository_tree_sha": case["repository_tree_sha"],
        "application_tree_sha": case["application_tree_sha"],
        "source_file_count": len(source_file_digests),
        "source_file_map_sha256": sha256_bytes(_canonical_json(source_file_digests)),
        "input_bundle_sha256": manifest["bundle_sha256"],
        "target_state_manifest_path": state_path,
        "target_state_manifest_sha256": state_record["sha256"],
        "evaluator_configurations": evaluator_configurations,
    }


def _validate_development_run_inventory(root: Path, expected_raw_paths: set[str]) -> None:
    allowed_exact = {"development_run.json", "development_run.json.sha256", "SHA256SUMS"}
    actual: set[str] = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ContractValidationError("MONO_CI_B0_PSI_DEVELOPMENT_RUN_SYMLINK_FORBIDDEN")
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        actual.add(relative)
        if relative in allowed_exact:
            continue
        if relative.startswith(("B0/input_bundle/", "PSI/input_bundle/")):
            continue
        if relative.startswith("B0/raw/") and (
            relative in expected_raw_paths or relative.endswith("/SHA256SUMS")
        ):
            continue
        raise ContractValidationError("MONO_CI_B0_PSI_DEVELOPMENT_RUN_FILE_FORBIDDEN")
    for case_number in range(1, 5):
        case_id = f"CASE_0{case_number}"
        for arm in ("B0", "PSI"):
            prefix = f"{arm}/input_bundle/{case_id}/"
            if not any(path.startswith(prefix) for path in actual):
                raise ContractValidationError("MONO_CI_B0_PSI_DEVELOPMENT_BUNDLE_MISSING")
        expected_case_raw = {
            f"B0/raw/{case_id}/{evaluator_id}.json" for evaluator_id in CONTROL_IDS
        }
        expected_case_raw.add(f"B0/raw/{case_id}/SHA256SUMS")
        actual_case_raw = {path for path in actual if path.startswith(f"B0/raw/{case_id}/")}
        if actual_case_raw != expected_case_raw:
            raise ContractValidationError("MONO_CI_B0_PSI_DEVELOPMENT_RAW_CASE_INVENTORY_MISMATCH")
        raw_root = root / "B0/raw" / case_id
        if _read_checksums(raw_root / "SHA256SUMS") != _directory_checksums(
            raw_root, exclude={"SHA256SUMS"}
        ):
            raise ContractValidationError("MONO_CI_B0_PSI_DEVELOPMENT_RAW_CASE_CHECKSUM_MISMATCH")


def _validate_raw_evaluator_evidence(evidence: dict[str, Any]) -> None:
    forbidden_keys = {
        "scorer",
        "scoring",
        "oracle",
        "ground_truth",
        "groundtruth",
        "expected_outputs",
        "expected_operations",
        "predicted_operations",
        "reference_answer",
        "reference_result",
        "score",
        "scores",
    }

    def inspect(value: Any) -> None:
        if isinstance(value, dict):
            if any(str(key).lower() in forbidden_keys for key in value):
                raise ContractValidationError(
                    "MONO_CI_B0_PSI_RAW_EVIDENCE_CONTAINS_FORBIDDEN_FIELD"
                )
            for item in value.values():
                inspect(item)
        elif isinstance(value, list):
            for item in value:
                inspect(item)
        elif isinstance(value, str):
            lowered = value.lower().replace("\\", "/")
            if any(
                marker in lowered
                for marker in (
                    "scorer/reference",
                    "expected_outputs/",
                    "expected_operations",
                    "ground_truth",
                    "groundtruth",
                    "oracle/",
                )
            ):
                raise ContractValidationError(
                    "MONO_CI_B0_PSI_RAW_EVIDENCE_CONTAINS_FORBIDDEN_CONTENT"
                )

    inspect(evidence)


def _checkout_application_files(checkout: Path) -> dict[str, bytes]:
    app_root = checkout / "app"
    if not app_root.is_dir() or app_root.is_symlink():
        raise ContractValidationError("MONO_CI_B0_PSI_EXECUTION_CHECKOUT_APP_MISSING")
    files: dict[str, bytes] = {}
    for path in app_root.rglob("*"):
        if path.is_symlink():
            raise ContractValidationError("MONO_CI_B0_PSI_EXECUTION_CHECKOUT_SYMLINK_FORBIDDEN")
        if path.is_file():
            relative = path.relative_to(checkout).as_posix()
            _validate_relative_path(relative)
            files[relative] = path.read_bytes()
    return files


def _bundle_file_record(
    manifest: dict[str, Any], relative: str, expected_role: str
) -> dict[str, Any]:
    matches = [item for item in manifest["files"] if item["path"] == relative]
    if len(matches) != 1 or matches[0]["role"] != expected_role:
        raise ContractValidationError("MONO_CI_B0_PSI_EXECUTION_BUNDLE_ROLE_OR_PATH_MISMATCH")
    return matches[0]


def _verify_evaluator_input_binding(
    evidence: dict[str, Any],
    input_binding: dict[str, Any],
    evaluator_id: str,
    bundle_root: Path,
) -> None:
    manifest = verify_arm_input_bundle(bundle_root, expected_arm="B0")
    state_record = _bundle_file_record(
        manifest, input_binding["target_state_manifest_path"], "architecture_state_manifest"
    )
    architecture = evidence.get("architecture", {})
    evaluator = evidence.get("evaluator", {})
    source_scope = evidence.get("source_scope", {})
    if (
        architecture.get("manifest_root") != "evidence"
        or architecture.get("manifest_path") != input_binding["target_state_manifest_path"]
        or architecture.get("manifest_digest") != state_record["sha256"]
        or evaluator.get("id") != evaluator_id
        or evaluator.get("configuration_digest")
        != _configuration_binding(input_binding, evaluator_id)
        or architecture.get("subject_source_dirty") is not False
    ):
        raise ContractValidationError("MONO_CI_B0_PSI_EVALUATOR_INPUT_BINDING_MISMATCH")

    expected_source = _bundle_application_files(bundle_root, manifest)
    reported = source_scope.get("source_file_digests", [])
    reported_paths = [item.get("path") for item in reported]
    if not reported or sorted(reported_paths) != sorted(set(reported_paths)):
        raise ContractValidationError("MONO_CI_B0_PSI_EVALUATOR_SOURCE_DIGEST_INVENTORY_INVALID")
    if sorted(source_scope.get("inspected_paths", [])) != sorted(reported_paths):
        raise ContractValidationError("MONO_CI_B0_PSI_EVALUATOR_SOURCE_DIGEST_SCOPE_MISMATCH")
    for item in reported:
        if item["path"] not in expected_source or sha256_bytes(
            expected_source[item["path"]]
        ) != item.get("sha256"):
            raise ContractValidationError("MONO_CI_B0_PSI_EVALUATOR_SOURCE_BYTES_MISMATCH")


def _configuration_binding(input_binding: dict[str, Any], evaluator_id: str) -> str | None:
    matches = [
        item
        for item in input_binding["evaluator_configurations"]
        if item["evaluator_id"] == evaluator_id
    ]
    return matches[0]["configuration_sha256"] if len(matches) == 1 else None


def _fetch_case_bundles(repository: Path, bare: Path, case_manifest: dict[str, Any]) -> None:
    archive_record = case_manifest["source_case_archive"]
    archive_path = repository / archive_record["path"]
    with zipfile.ZipFile(archive_path) as archive:
        for case in case_manifest["cases"]:
            bundle_digest = case["mutation_bundle_sha256"]
            if bundle_digest is None:
                continue
            bundle_relative = f"cases/{case['source_case_id']}/mutation.bundle"
            bundle_bytes = archive.read(bundle_relative)
            if sha256_bytes(bundle_bytes) != bundle_digest:
                raise ContractValidationError("MONO_CI_B0_PSI_CASE_BUNDLE_DIGEST_MISMATCH")
            with tempfile.NamedTemporaryFile(prefix="mono-ci-case-", suffix=".bundle") as handle:
                handle.write(bundle_bytes)
                handle.flush()
                _git_run(bare, ("bundle", "verify", handle.name))
                _git_run(bare, ("fetch", handle.name))
            _verify_git_commit(
                bare,
                case["source_commit_sha"],
                case["repository_tree_sha"],
                case["application_tree_sha"],
            )


def _git_archive_application(repository: Path, commit: str) -> dict[str, bytes]:
    archive = _git_run_bytes(repository, ("archive", "--format=tar", commit, "app"))
    result: dict[str, bytes] = {}
    with tarfile.open(fileobj=BytesIO(archive), mode="r:") as archive_file:
        for member in archive_file.getmembers():
            member_path = PurePosixPath(member.name)
            if member_path.is_absolute() or ".." in member_path.parts or not member_path.parts:
                raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_PATH_INVALID")
            if member.issym() or member.islnk() or member.isdev() or member.isfifo():
                raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_LINK_OR_DEVICE_FORBIDDEN")
            if member.isdir():
                continue
            if not member.isfile() or member_path.parts[0] != "app":
                raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_MEMBER_FORBIDDEN")
            file_handle = archive_file.extractfile(member)
            if file_handle is None:
                raise ContractValidationError("MONO_CI_B0_PSI_ARCHIVE_MEMBER_READ_FAILED")
            relative = PurePosixPath(*member_path.parts[1:]).as_posix()
            _validate_relative_path(relative)
            result[f"app/{relative}"] = file_handle.read()
    if not result:
        raise ContractValidationError("MONO_CI_B0_PSI_APPLICATION_SOURCE_EMPTY")
    return result


def _prefixed_files(
    source_files: dict[str, bytes], prefix: str, role: str
) -> dict[str, tuple[str, bytes]]:
    return {
        f"{prefix}/{relative.removeprefix('app/')}": (role, content)
        for relative, content in source_files.items()
    }


def _representation_for(baseline: dict[str, Any], evaluator_id: str) -> dict[str, Any]:
    matches = [row for row in baseline["representations"] if row["evaluator_id"] == evaluator_id]
    if len(matches) != 1:
        raise ContractValidationError("MONO_CI_B0_PSI_BASELINE_REPRESENTATION_AMBIGUOUS")
    return matches[0]


def _evaluator_exit_code(evidence: dict[str, Any]) -> int:
    result = evidence["result"]
    if result["execution_status"] == "FAILED" or result["compliance"] in {
        "NOT_EVALUABLE",
        "UNKNOWN",
    }:
        return 2
    if result["compliance"] == "NON_COMPLIANT":
        return 1
    if result["compliance"] == "NOT_APPLICABLE":
        return 3
    return 0


def _verify_evaluator_binding(
    evidence: dict[str, Any],
    source: dict[str, Any],
    expected_evaluator_source_sha256: str,
    expected_configuration_sha256: str,
) -> None:
    architecture = evidence.get("architecture", {})
    evaluator = evidence.get("evaluator", {})
    if (
        architecture.get("target_source_sha") != source["source_commit_sha"]
        or architecture.get("expected_source_sha") != source["source_commit_sha"]
        or architecture.get("manifest_state_status") != "MATCHED"
        or architecture.get("source_sha_status") != "MATCHED"
    ):
        raise ContractValidationError("MONO_CI_B0_PSI_EVALUATOR_SOURCE_BINDING_MISMATCH")
    if evaluator.get("source_digest") != expected_evaluator_source_sha256:
        raise ContractValidationError("MONO_CI_B0_PSI_EVALUATOR_SOURCE_DIGEST_MISMATCH")
    if evaluator.get("configuration_digest") != expected_configuration_sha256:
        raise ContractValidationError("MONO_CI_B0_PSI_EVALUATOR_CONFIG_DIGEST_MISMATCH")


def _validate_bundle_file(relative: str, content: bytes) -> None:
    _validate_relative_path(relative)
    lowered_parts = {part.lower() for part in PurePosixPath(relative).parts}
    if lowered_parts.intersection(FORBIDDEN_PATH_PARTS):
        raise ContractValidationError("MONO_CI_B0_PSI_FORBIDDEN_INPUT_PATH")
    if any(marker in content.lower() for marker in FORBIDDEN_CONTENT_MARKERS):
        raise ContractValidationError("MONO_CI_B0_PSI_FORBIDDEN_INPUT_CONTENT")


def _validate_relative_path(relative: str) -> None:
    path = PurePosixPath(relative)
    if path.is_absolute() or not path.parts or ".." in path.parts or "\\" in relative:
        raise ContractValidationError("MONO_CI_B0_PSI_UNSAFE_RELATIVE_PATH")


def _require_new_external_directory(repository: Path, destination: Path) -> None:
    if destination.exists() or destination.is_symlink():
        raise ProtocolError("MONO_CI_B0_PSI_OUTPUT_PATH_MUST_BE_NEW")
    parent = destination.parent.resolve(strict=True)
    if (
        destination == parent
        or destination.is_relative_to(repository)
        or parent.is_relative_to(repository)
    ):
        raise ProtocolError("MONO_CI_B0_PSI_OUTPUT_MUST_BE_OUTSIDE_REPOSITORY")
    if "," in str(destination):
        raise ProtocolError("MONO_CI_B0_PSI_OUTPUT_PATH_INVALID_FOR_CONTAINER_MOUNT")


def _write_new_bytes(root: Path, relative: str, content: bytes) -> Path:
    _validate_relative_path(relative)
    path = root.joinpath(*PurePosixPath(relative).parts)
    if not path.resolve(strict=False).is_relative_to(root.resolve(strict=True)):
        raise ProtocolError("MONO_CI_B0_PSI_OUTPUT_PATH_ESCAPES_ROOT")
    path.parent.mkdir(parents=True, exist_ok=True)
    if any(part.is_symlink() for part in (path, *path.parents) if part.exists()):
        raise ProtocolError("MONO_CI_B0_PSI_OUTPUT_SYMLINK_FORBIDDEN")
    try:
        with path.open("xb") as file_handle:
            file_handle.write(content)
    except FileExistsError as error:
        raise ProtocolError("MONO_CI_B0_PSI_OUTPUT_IS_WRITE_ONCE") from error
    return path


def _write_new_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as file_handle:
            file_handle.write(content)
    except FileExistsError as error:
        raise ProtocolError("MONO_CI_B0_PSI_OUTPUT_IS_WRITE_ONCE") from error


def _write_checksums(root: Path, *, exclude: set[str]) -> dict[str, str]:
    actual = _directory_checksums(root, exclude=exclude)
    content = "".join(f"{digest}  {relative}\n" for relative, digest in sorted(actual.items()))
    _write_new_file(root / "SHA256SUMS", content.encode())
    return actual


def _read_checksums(path: Path) -> dict[str, str]:
    if not path.is_file() or path.is_symlink():
        raise ContractValidationError("MONO_CI_B0_PSI_CHECKSUM_FILE_MISSING")
    checksums: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([a-f0-9]{64})  (.+)", line)
        if not match:
            raise ContractValidationError("MONO_CI_B0_PSI_CHECKSUM_FILE_INVALID")
        digest, relative = match.groups()
        _validate_relative_path(relative)
        if relative in checksums:
            raise ContractValidationError("MONO_CI_B0_PSI_CHECKSUM_DUPLICATE_PATH")
        checksums[relative] = digest
    return checksums


def _directory_checksums(root: Path, *, exclude: set[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ContractValidationError("MONO_CI_B0_PSI_OUTPUT_SYMLINK_FORBIDDEN")
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            if relative not in exclude:
                result[relative] = sha256_file(path)
    return result


def _safe_child(root: Path, relative: str) -> Path:
    _validate_relative_path(relative)
    path = root.joinpath(*PurePosixPath(relative).parts)
    if path.is_symlink() or not path.resolve(strict=True).is_relative_to(root):
        raise ContractValidationError("MONO_CI_B0_PSI_OUTPUT_PATH_INVALID")
    return path


def _bundle_digest(manifest: dict[str, Any]) -> str:
    payload = {key: value for key, value in manifest.items() if key != "bundle_sha256"}
    return sha256_bytes(_canonical_json(payload))


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContractValidationError(f"MONO_CI_B0_PSI_JSON_READ_FAILED:{path.name}") from error
    if not isinstance(payload, dict):
        raise ContractValidationError(f"MONO_CI_B0_PSI_JSON_OBJECT_REQUIRED:{path.name}")
    return cast(dict[str, Any], payload)


def _git_executable() -> str:
    executable = shutil.which("git")
    if executable is None or not Path(executable).is_absolute():
        raise ProtocolError("MONO_CI_B0_PSI_GIT_UNAVAILABLE")
    return str(Path(executable).resolve(strict=True))


def _git_run(repository: Path, arguments: tuple[str, ...]) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(  # noqa: S603  # nosec B603
            [_git_executable(), "-C", str(repository), *arguments],
            check=True,
            capture_output=True,
            timeout=60,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise ProtocolError("MONO_CI_B0_PSI_GIT_COMMAND_FAILED") from error


def _git_run_bytes(repository: Path, arguments: tuple[str, ...]) -> bytes:
    return _git_run(repository, arguments).stdout


def _git_text(repository: Path, *arguments: str) -> str:
    completed = _git_run(repository, arguments)
    return completed.stdout.decode("utf-8").strip()


def _git_bytes(repository: Path, revision: str, path: str) -> bytes:
    pure_path = PurePosixPath(path)
    if pure_path.is_absolute() or ".." in pure_path.parts:
        raise ProtocolError("MONO_CI_B0_PSI_GIT_PATH_INVALID")
    return _git_run_bytes(repository, ("show", f"{revision}:{path}"))


def _cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--development-validation", action="store_true")
    parser.add_argument("--repository", type=Path, default=REPOSITORY_ROOT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execution-id", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Execute an explicitly requested DEVELOPMENT-only validation."""
    args = _cli().parse_args(argv)
    if not args.development_validation:
        print(json.dumps({"readiness": "NO_GO", "error": "DEVELOPMENT flag is required"}))
        return 2
    execution_id = args.execution_id or (
        "DEV_MONO_CI_" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    )
    try:
        result = run_development_validation(args.repository, args.output, execution_id)
    except (ContractValidationError, MethodNotReadyError, ProtocolError) as error:
        print(json.dumps({"readiness": "NO_GO", "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "execute_official_study",
    "main",
    "materialize_development_inputs",
    "run_development_validation",
    "verify_arm_input_bundle",
    "verify_development_result",
    "verify_execution_proposal",
]
