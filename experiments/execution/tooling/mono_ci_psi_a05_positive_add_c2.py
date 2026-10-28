"""Execute and verify the bounded C2 TEST_ONLY positive ADD study."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from experiments.execution.tooling import mono_ci_psi_a05 as a05
from experiments.execution.tooling import mono_ci_psi_a05_positive_add as positive_add
from experiments.execution.tooling import mono_ci_psi_transition as transition
from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError, ProtocolError
from experiments.execution.tooling.hashing import (
    canonical_json_bytes,
    pretty_json_bytes,
    sha256_bytes,
    sha256_file,
)
from experiments.execution.tooling.mono_ci_b0_psi_archive import (
    pack_psi_transition_archive,
    verify_psi_transition_archive,
)

STUDY_ID = "MONO_CI_A05_POSITIVE_ADD_C2_TEST_ONLY_V1"
PROFILE_PATH = Path(
    "experiments/execution/mono-ci-b0-psi-delta-a5-positive-add-c2-v1/inputs/"
    "POSITIVE_ADD_C2_PROFILE_V1.json"
)
STUDY_ROOT = Path("experiments/execution/mono-ci-b0-psi-delta-a5-positive-add-c2-v1")
PROTOCOL_JSON = STUDY_ROOT / "PROTOCOL_C2_V1.json"
PROTOCOL_MD = STUDY_ROOT / "PROTOCOL_C2_V1.md"
PROFILE_SCHEMA = "mono_ci_psi_positive_add_c2_profile_v1.schema.json"
PROTOCOL_SCHEMA = "mono_ci_psi_positive_add_c2_protocol_v1.schema.json"
FREEZE_SCHEMA = "mono_ci_psi_positive_add_c2_freeze_v1.schema.json"
RESULTS_SCHEMA = "mono_ci_psi_positive_add_c2_results_v1.schema.json"
STUDY_ID_V2 = "MONO_CI_A05_POSITIVE_ADD_C2_TEST_ONLY_V2"
PROFILE_PATH_V2 = Path(
    "experiments/execution/mono-ci-b0-psi-delta-a5-positive-add-c2-v2/inputs/"
    "POSITIVE_ADD_C2_PROFILE_V2.json"
)
STUDY_ROOT_V2 = Path("experiments/execution/mono-ci-b0-psi-delta-a5-positive-add-c2-v2")
PROTOCOL_JSON_V2 = STUDY_ROOT_V2 / "PROTOCOL_C2_V2.json"
PROTOCOL_MD_V2 = STUDY_ROOT_V2 / "PROTOCOL_C2_V2.md"
PROFILE_SCHEMA_V2 = "mono_ci_psi_positive_add_c2_profile_v2.schema.json"
PROTOCOL_SCHEMA_V2 = "mono_ci_psi_positive_add_c2_protocol_v2.schema.json"
FREEZE_SCHEMA_V2 = "mono_ci_psi_positive_add_c2_freeze_v2.schema.json"
RESULTS_SCHEMA_V2 = "mono_ci_psi_positive_add_c2_results_v2.schema.json"
GATES = {
    "study_readiness": "NO_GO",
    "measurement_status": "NOT_EXECUTED",
    "P_ALGORITHM_STATUS": "NOT_READY",
    "G1": "INCOMPLETE",
    "G4": "NOT_AUTHORIZED",
    "reference": "NOT_READY",
    "scoring": "NOT_EXECUTED",
}
OWNER_REPRESENTATION = "REP_POSITIVE_ADD_AC_DATA_OWNERSHIP"


@dataclass(frozen=True)
class C2StudyContract:
    """Versioned file and identity pins for one bounded C2 contract."""

    study_id: str
    profile_path: Path
    protocol_json: Path
    protocol_md: Path
    profile_schema: str
    protocol_schema: str
    freeze_schema: str
    results_schema: str
    freeze_version: str
    results_version: str
    method_version: str


C2_V1 = C2StudyContract(
    STUDY_ID,
    PROFILE_PATH,
    PROTOCOL_JSON,
    PROTOCOL_MD,
    PROFILE_SCHEMA,
    PROTOCOL_SCHEMA,
    FREEZE_SCHEMA,
    RESULTS_SCHEMA,
    "MONO_CI_A05_POSITIVE_ADD_C2_FREEZE_V1",
    "MONO_CI_A05_POSITIVE_ADD_C2_RESULTS_V1",
    "P_GOVERNED_ADAPTATION_DEVELOPMENT_V1",
)
C2_V2 = C2StudyContract(
    STUDY_ID_V2,
    PROFILE_PATH_V2,
    PROTOCOL_JSON_V2,
    PROTOCOL_MD_V2,
    PROFILE_SCHEMA_V2,
    PROTOCOL_SCHEMA_V2,
    FREEZE_SCHEMA_V2,
    RESULTS_SCHEMA_V2,
    "MONO_CI_A05_POSITIVE_ADD_C2_FREEZE_V2",
    "MONO_CI_A05_POSITIVE_ADD_C2_RESULTS_V2",
    "P_GOVERNED_ADAPTATION_DEVELOPMENT_V2_TEST_ONLY_EXACT_SET",
)


def _read_json(path: Path, code: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ContractValidationError(code)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ContractValidationError(code) from error
    if not isinstance(value, dict):
        raise ContractValidationError(code)
    return value


def _write_new(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise ProtocolError("POSITIVE_ADD_C2_OUTPUT_MUST_BE_NEW")
    path.write_bytes(content)


def _read_preflight(output_root: Path) -> dict[str, Any]:
    path = output_root / "sandbox-preflight.json"
    sidecar = Path(f"{path}.sha256")
    record = _read_json(path, "POSITIVE_ADD_C2_PREFLIGHT_MISSING")
    digest = sha256_file(path)
    if (
        sidecar.is_symlink()
        or not sidecar.is_file()
        or sidecar.read_text().strip() != f"{digest}  sandbox-preflight.json"
    ):
        raise ContractValidationError("POSITIVE_ADD_C2_PREFLIGHT_SIDECAR_MISMATCH")
    validate_payload("mono_ci_psi_docker_isolation_preflight_v1.schema.json", record)
    if record.get("verification_status") != "PASS" or not all(record.get("probes", {}).values()):
        raise ProtocolError("POSITIVE_ADD_C2_DOCKER_PREFLIGHT_FAILED")
    return {**record, "preflight_id": digest, "record_path": str(path)}


def run_preflight(repository: Path, output_root: Path) -> dict[str, Any]:
    """Run the same digest-pinned Docker capability check used by the C1 study."""
    return transition.run_docker_isolation_preflight(repository.resolve(strict=True), output_root)


def _profile(repository: Path, contract: C2StudyContract = C2_V1) -> dict[str, Any]:
    profile = _read_json(repository / contract.profile_path, "POSITIVE_ADD_C2_PROFILE_MISSING")
    validate_payload(contract.profile_schema, profile)
    positive_add._validate_static_profile(profile)
    return profile


def _protocol(repository: Path, contract: C2StudyContract = C2_V1) -> dict[str, Any]:
    protocol = _read_json(repository / contract.protocol_json, "POSITIVE_ADD_C2_PROTOCOL_MISSING")
    validate_payload(contract.protocol_schema, protocol)
    return protocol


def _freeze(
    repository: Path,
    profile: dict[str, Any],
    protocol: dict[str, Any],
    preflight: dict[str, Any],
    uv_version: str,
    contract: C2StudyContract = C2_V1,
) -> dict[str, Any]:
    repo = repository.resolve(strict=True)
    if a05._git_text(repo, "status", "--porcelain"):
        raise ProtocolError("POSITIVE_ADD_C2_FREEZE_REQUIRES_CLEAN_CHECKOUT")
    head = a05._git_text(repo, "rev-parse", "HEAD")
    app_tree = a05._git_text(repo, "rev-parse", "HEAD:app")
    if app_tree != protocol["transition"]["after_application_tree_sha"]:
        raise ProtocolError("POSITIVE_ADD_C2_APPLICATION_TREE_MISMATCH")
    evaluator_rows, _source_bytes, source_digest = transition.evaluator_source_artifacts(repo)
    if any(
        row["evaluator_source_manifest_sha256"] != source_digest
        for row in profile["additional_retain_obligations"]
    ):
        raise ContractValidationError("POSITIVE_ADD_C2_RETAIN_SOURCE_MANIFEST_MISMATCH")
    evaluator = {
        "source_manifest_sha256": source_digest,
        "public_api_configuration_sha256": sha256_file(
            repo / "architecture/acceptance/a1/public_api_v1.yaml"
        ),
        "module_graph_configuration_sha256": sha256_file(
            repo / "architecture/acceptance/a1/module_graph_v1.yaml"
        ),
        "ownership_configuration_sha256": sha256_file(
            repo / "architecture/acceptance/a1/data_ownership_v1.yaml"
        ),
        "source_files": evaluator_rows,
    }
    method_paths = (
        "experiments/execution/tooling/p_adaptation.py",
        "experiments/execution/tooling/p_applicability.py",
        "experiments/execution/tooling/p_semantic.py",
        "experiments/execution/tooling/p_candidate.py",
        "experiments/execution/tooling/p_adaptation_evidence.py",
        "experiments/execution/tooling/p_input_validation.py",
        "experiments/execution/tooling/p_impact.py",
        "experiments/execution/tooling/p_operations.py",
        "experiments/execution/tooling/p_governance.py",
        "experiments/execution/tooling/mono_ci_psi_a05_positive_add.py",
        "experiments/execution/tooling/mono_ci_psi_transition.py",
        "experiments/execution/tooling/mono_ci_psi_a05.py",
        "experiments/execution/tooling/mono_ci_psi_a05_positive_add_c2.py",
        "experiments/execution/tooling/mono_ci_b0_psi_archive.py",
        "experiments/execution/tooling/contracts.py",
    )
    if contract.study_id == C2_V2.study_id:
        method_paths += (
            "experiments/execution/tooling/p_adaptation_c2_v2.py",
            "experiments/execution/tooling/p_applicability_c2_v2.py",
        )
    method = {path: sha256_file(repo / path) for path in method_paths}
    transition_schema = (
        "mono_ci_psi_transition_run_v7.schema.json"
        if contract.study_id == C2_V2.study_id
        else "mono_ci_psi_transition_run_v6.schema.json"
    )
    schema_paths = tuple(
        f"experiments/execution/schemas/{schema}"
        for schema in (
            contract.profile_schema,
            contract.protocol_schema,
            contract.freeze_schema,
            contract.results_schema,
            transition_schema,
        )
    )
    freeze = {
        "schema_version": contract.freeze_version,
        "study_id": contract.study_id,
        "classification": "PRE_RUN_FREEZE_TEST_ONLY_AUTHOR_DECLARED_DEVELOPMENT",
        "implementation_commit": head,
        "protocol_sha256": sha256_file(repo / contract.protocol_json),
        "profile_sha256": sha256_file(repo / contract.profile_path),
        "source_identities": {
            "before_commit_sha": a05.BEFORE_COMMIT,
            "after_commit_sha": head,
            "before_application_tree_sha": a05.BEFORE_APPLICATION_TREE,
            "after_application_tree_sha": app_tree,
            "before_state_manifest_sha256": sha256_file(
                repo / "architecture/states/A0_4_REPORT_QUERY_PORT.yaml"
            ),
            "after_state_manifest_sha256": sha256_file(
                repo / "architecture/states/A0_5_MODULE_DATA_OWNERSHIP.yaml"
            ),
        },
        "method": method,
        "schema_sha256": {path: sha256_file(repo / path) for path in schema_paths},
        "evaluators": evaluator,
        "docker": {
            "image": transition.ISOLATED_METHOD_IMAGE,
            "platform": transition.ISOLATED_METHOD_PLATFORM,
            "network": "none",
            "method_input_mount": "read-only",
            "writable_output_mounts": 1,
        },
        "preflight_sha256": preflight["preflight_id"],
        "host_identity": preflight["host_identity"],
        "uv_version": uv_version,
        "repetitions": {"warmup": 1, "measured": 3},
        "cost_rule": {
            "incremental_evaluator_id": "AC_DATA_OWNERSHIP",
            "max_incremental_cost_ms": 225,
            "max_search_nodes": 2,
            "unavailable_or_exceeded_behavior": "HOLD_AND_DO_NOT_SELECT_TEMPLATE",
        },
        "official_boundary": GATES,
    }
    validate_payload(contract.freeze_schema, freeze)
    return freeze


def _row_outcome(row: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "evaluator_id",
        "representation_id",
        "execution_status",
        "compliance",
        "inspection_status",
        "finding_codes",
        "duration_ms",
        "source_commit_sha",
        "source_tree_sha",
        "inspection_scope_path",
        "inspection_scope_sha256",
        "configuration_sha256",
        "evaluator_source_sha256",
        "process_exit_code",
    )
    return {field: row.get(field) for field in fields}


def _foreign_table_detected(row: dict[str, Any] | None) -> bool:
    return bool(
        isinstance(row, dict)
        and row.get("compliance") == "NON_COMPLIANT"
        and "FOREIGN_TABLE_ACCESS" in row.get("finding_codes", [])
    )


def _summarize_run(
    run_root: Path, archive_sha256: str, contract: C2StudyContract = C2_V1
) -> dict[str, Any]:
    record = _read_json(run_root / "development_run.json", "POSITIVE_ADD_C2_RUN_RECORD_MISSING")
    expected_transition_schema = (
        "MONO_CI_PSI_TRANSITION_RUN_V7"
        if contract.study_id == C2_V2.study_id
        else "MONO_CI_PSI_TRANSITION_RUN_V6"
    )
    if (
        record.get("schema_version") != expected_transition_schema
        or record.get("study_id") != contract.study_id
    ):
        raise ContractValidationError("POSITIVE_ADD_C2_TRANSITION_SCHEMA_MISMATCH")
    method_result = _read_json(
        run_root / record["psi"]["raw_result_path"], "POSITIVE_ADD_C2_METHOD_RESULT_MISSING"
    )
    extension = _read_json(
        run_root / record["a05_extension"]["path"], "POSITIVE_ADD_C2_EXTENSION_MISSING"
    )
    verification = extension.get("candidate_verification", {})
    positive = verification.get("positive_evaluations", [])
    negative = verification.get("negative_evaluations", [])
    owner_clean = next(
        (row for row in positive if row.get("representation_id") == OWNER_REPRESENTATION), None
    )
    owner_negative = next(
        (row for row in negative if row.get("representation_id") == OWNER_REPRESENTATION), None
    )
    baseline = _read_json(
        run_root / "provenance/reconstructed-b0-proposal.json", "POSITIVE_ADD_C2_BASELINE_MISSING"
    )
    baseline_ids = {str(row["evaluator_id"]) for row in baseline.get("representations", [])}
    clean_b0 = [
        _row_outcome(row)
        for row in record.get("evaluator_observations", [])
        if row.get("architecture_state") == "A0_5_MODULE_DATA_OWNERSHIP"
        and row.get("evaluator_id") in baseline_ids
    ]
    negative_b0 = [
        _row_outcome(row)
        for row in extension.get("negative_condition", {}).get("evaluators", [])
        if row.get("evaluator_id") in baseline_ids
    ]
    operations = method_result.get("operation_plan", {}).get("operations", [])
    owner_add = any(
        row.get("operation") == "add"
        and row.get("target_type") == "obligation"
        and row.get("target_id") == "AC_DATA_OWNERSHIP"
        and row.get("payload", {}).get("id") == OWNER_REPRESENTATION
        for row in operations
    )
    retain_targets = sorted(
        str(row.get("target_id"))
        for row in operations
        if row.get("operation") == "retain" and row.get("target_type") == "representation"
    )
    decision = str(method_result.get("governance", {}).get("result", record["psi"]["decision"]))
    candidate_exercised = bool(owner_clean and owner_negative)
    candidate_accepted = decision == "ACCEPT"
    application_status = (
        "NOT_APPLICABLE_GOVERNANCE_NOT_ACCEPTED"
        if not candidate_accepted
        else "APPLIED_TO_ISOLATED_CANDIDATE_EVALUATION_CONTEXT"
        if candidate_exercised
        and all(row.get("execution_status") == "COMPLETED" for row in positive + negative)
        else "ACCEPTED_BUT_EVALUATOR_APPLICATION_INCOMPLETE"
    )
    owner_clean_ms = owner_clean.get("duration_ms") if isinstance(owner_clean, dict) else None
    owner_negative_ms = (
        owner_negative.get("duration_ms") if isinstance(owner_negative, dict) else None
    )
    owner_total_ms = (
        round(float(owner_clean_ms) + float(owner_negative_ms), 3)
        if isinstance(owner_clean_ms, (int, float)) and isinstance(owner_negative_ms, (int, float))
        else None
    )
    summary = {
        "execution_id": record["execution_id"],
        "archive_sha256": archive_sha256,
        "decision": decision,
        "governance_reasons": method_result.get("governance", {}).get("reason_codes", []),
        "operation_plan": operations,
        "hold_reasons": method_result.get("operation_plan", {}).get("hold_reasons", []),
        "owner_add_emitted": owner_add,
        "retain_targets_emitted": retain_targets,
        "candidate_validation_status": verification.get(
            "method_candidate_validation_status", "NOT_EXECUTED"
        ),
        "candidate_accepted": candidate_accepted,
        "candidate_application_status": application_status,
        "candidate_state": (
            "MATERIALIZED_AND_EXERCISED_UNAPPLIED"
            if candidate_exercised and not candidate_accepted
            else "MATERIALIZED_AND_EXERCISED_ACCEPTED"
            if candidate_exercised and candidate_accepted
            else "MATERIALIZED_NOT_EXERCISED"
            if verification.get("candidate_present") is True
            else "NOT_MATERIALIZED"
        ),
        "candidate_clean": [_row_outcome(row) for row in positive],
        "candidate_negative": [_row_outcome(row) for row in negative],
        "clean_b0": clean_b0,
        "negative_b0": negative_b0,
        "incremental_owner_cost_ms": {
            "clean": owner_clean_ms,
            "ownership_negative": owner_negative_ms,
            "two_condition_total": owner_total_ms,
            "per_invocation_limit": 225,
            "clean_within_limit": isinstance(owner_clean_ms, (int, float))
            and owner_clean_ms <= 225,
            "negative_within_limit": isinstance(owner_negative_ms, (int, float))
            and owner_negative_ms <= 225,
        },
        "method_execution_ms": record["psi"].get("execution_duration_ms"),
    }
    if contract.study_id == C2_V2.study_id:
        profile = _read_json(
            run_root / "provenance/positive-add-study-profile.json",
            "POSITIVE_ADD_C2_PROFILE_MISSING",
        )
        selected_ids = sorted(
            {
                str(profile["selected_obligation"]["id"]),
                *(str(row["id"]) for row in profile["additional_retain_obligations"]),
            }
        )
        before_rows = method_result.get("before_applicability", {}).get("results", [])
        after_rows = method_result.get("after_applicability", {}).get("results", [])
        outside_statuses = [
            str(row.get("status"))
            for row in after_rows
            if row.get("obligation_id") not in selected_ids
        ]
        if not outside_statuses or any(status != "UNKNOWN" for status in outside_statuses):
            raise ContractValidationError("POSITIVE_ADD_C2_V2_OUTSIDE_SCOPE_NOT_UNKNOWN")
        retain_pairs = [
            {
                "representation_id": row.get("representation_id"),
                "obligation_id": row.get("obligation_id"),
                "status": row.get("status"),
                "compliance_status": row.get("compliance_status"),
                "architecture_source_sha": row.get("architecture_source_sha"),
            }
            for row in method_result.get("candidate_pairs", [])
            if row.get("obligation_id") in {"AC_PUBLIC_API", "AC_MODULE_GRAPH"}
        ]
        summary.update(
            {
                "method_version": method_result.get("method_version"),
                "before_selected_applicability": [
                    {"obligation_id": row.get("obligation_id"), "status": row.get("status")}
                    for row in before_rows
                    if row.get("obligation_id") in selected_ids
                ],
                "after_selected_applicability": [
                    {"obligation_id": row.get("obligation_id"), "status": row.get("status")}
                    for row in after_rows
                    if row.get("obligation_id") in selected_ids
                ],
                "outside_scope_applicability_counts": {
                    status: outside_statuses.count(status)
                    for status in sorted(set(outside_statuses))
                },
                "retained_pair_statuses": retain_pairs,
                "current_coverage_status": method_result.get("current_coverage", {}).get("status"),
                "candidate_coverage_status": method_result.get("candidate_coverage", {}).get(
                    "status"
                ),
                "invariant_verdicts": method_result.get("governance", {}).get(
                    "invariant_verdicts", {}
                ),
                "cost_verdict": method_result.get("governance", {}).get("cost_verdict"),
                "candidate_sha256": method_result.get("candidate_sha256"),
                "candidate_configuration_sha256": method_result.get("governance", {}).get(
                    "candidate_configuration_sha256"
                ),
                "all_outside_scope_unknown": bool(outside_statuses)
                and all(status == "UNKNOWN" for status in outside_statuses),
            }
        )
    return summary


def _extract_run(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive, "r") as zipped:
        infos = zipped.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise ContractValidationError("POSITIVE_ADD_C2_ARCHIVE_DUPLICATE_MEMBER")
        for info in infos:
            path = PurePosixPath(info.filename)
            if (
                path.is_absolute()
                or any(part in {"", ".", ".."} for part in path.parts)
                or ".git" in path.parts
            ):
                raise ContractValidationError("POSITIVE_ADD_C2_ARCHIVE_MEMBER_PATH_INVALID")
            if info.is_dir():
                continue
            target = destination / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zipped.read(info))


def _inventory(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink() and path.name != "SHA256SUMS"
    ]


def _commit_file_sha256(repository: Path, commit: str, relative_path: str) -> str:
    content = a05._git_bytes(repository, "show", f"{commit}:{relative_path}")
    return sha256_bytes(content)


def _verify_frozen_source_bindings(repository: Path, freeze: dict[str, Any]) -> None:
    """Read back the source and schema digests from the pre-run implementation commit."""
    commit = str(freeze["implementation_commit"])
    for path, expected in freeze["method"].items():
        if _commit_file_sha256(repository, commit, path) != expected:
            raise ContractValidationError("POSITIVE_ADD_C2_METHOD_SOURCE_FREEZE_MISMATCH")
    for path, expected in freeze["schema_sha256"].items():
        if _commit_file_sha256(repository, commit, path) != expected:
            raise ContractValidationError("POSITIVE_ADD_C2_SCHEMA_FREEZE_MISMATCH")
    source_rows = freeze["evaluators"]["source_files"]
    for row in source_rows:
        path = f"architecture/acceptance/a1/{row['path']}"
        if _commit_file_sha256(repository, commit, path) != row["sha256"]:
            raise ContractValidationError("POSITIVE_ADD_C2_EVALUATOR_SOURCE_FREEZE_MISMATCH")
    if (
        sha256_bytes(canonical_json_bytes(source_rows))
        != freeze["evaluators"]["source_manifest_sha256"]
    ):
        raise ContractValidationError("POSITIVE_ADD_C2_EVALUATOR_MANIFEST_FREEZE_MISMATCH")
    configuration_paths = {
        "public_api_configuration_sha256": "architecture/acceptance/a1/public_api_v1.yaml",
        "module_graph_configuration_sha256": "architecture/acceptance/a1/module_graph_v1.yaml",
        "ownership_configuration_sha256": "architecture/acceptance/a1/data_ownership_v1.yaml",
    }
    for field, path in configuration_paths.items():
        if _commit_file_sha256(repository, commit, path) != freeze["evaluators"][field]:
            raise ContractValidationError("POSITIVE_ADD_C2_EVALUATOR_CONFIGURATION_FREEZE_MISMATCH")
    if (
        a05._git_text(repository, "rev-parse", f"{commit}:app")
        != freeze["source_identities"]["after_application_tree_sha"]
    ):
        raise ContractValidationError("POSITIVE_ADD_C2_APPLICATION_TREE_FREEZE_MISMATCH")


def _write_checksums(evidence_root: Path) -> None:
    rows = _inventory(evidence_root)
    _write_new(
        evidence_root / "SHA256SUMS",
        "".join(f"{row['sha256']}  {row['path']}\n" for row in rows).encode("ascii"),
    )


def run_study(
    repository: Path,
    output_root: Path,
    preflight_root: Path,
    *,
    workflow_run_url: str,
    run_id: str,
    run_attempt: str,
    uv_version: str,
    contract: C2StudyContract = C2_V1,
) -> dict[str, Any]:
    """Freeze C2, execute one warmup and three measured runs, and verify raw archives."""
    repo = repository.resolve(strict=True)
    if not run_id.isdecimal() or not run_attempt.isdecimal():
        raise ProtocolError("POSITIVE_ADD_C2_WORKFLOW_RUN_ID_INVALID")
    output = output_root.expanduser().absolute()
    if output.exists() or output.is_symlink() or output.is_relative_to(repo):
        raise ProtocolError("POSITIVE_ADD_C2_OUTPUT_MUST_BE_NEW_AND_EXTERNAL")
    profile = _profile(repo, contract)
    protocol = _protocol(repo, contract)
    preflight = _read_preflight(preflight_root)
    if preflight.get("host_identity", {}).get("uv_version") != uv_version:
        raise ProtocolError("POSITIVE_ADD_C2_PREFLIGHT_UV_VERSION_MISMATCH")
    output.mkdir(parents=True)
    evidence = output / "evidence"
    evidence.mkdir()
    for source, destination in (
        (repo / contract.protocol_md, evidence / f"protocol/{contract.protocol_md.name}"),
        (repo / contract.protocol_json, evidence / f"protocol/{contract.protocol_json.name}"),
        (repo / contract.profile_path, evidence / f"protocol/inputs/{contract.profile_path.name}"),
        (
            repo / "experiments/execution/schemas" / contract.profile_schema,
            evidence / "protocol/schemas" / contract.profile_schema,
        ),
        (
            repo / "experiments/execution/schemas" / contract.protocol_schema,
            evidence / "protocol/schemas" / contract.protocol_schema,
        ),
        (
            repo / "experiments/execution/schemas" / contract.freeze_schema,
            evidence / "protocol/schemas" / contract.freeze_schema,
        ),
        (
            repo / "experiments/execution/schemas" / contract.results_schema,
            evidence / "protocol/schemas" / contract.results_schema,
        ),
    ):
        _write_new(destination, source.read_bytes())
    preflight_copy = evidence / "sandbox-preflight"
    shutil.copytree(preflight_root, preflight_copy)
    freeze = _freeze(repo, profile, protocol, preflight, uv_version, contract)
    freeze_bytes = pretty_json_bytes(freeze)
    _write_new(evidence / "PRE_RUN_FREEZE_C2.json", freeze_bytes)
    freeze_sha = sha256_bytes(freeze_bytes)
    _write_new(
        evidence / "PRE_RUN_FREEZE_C2.json.sha256",
        f"{freeze_sha}  PRE_RUN_FREEZE_C2.json\n".encode("ascii"),
    )

    schedule = [
        {"role": "WARMUP", "index": 0, "measured": False},
        {"role": "MEASURED", "index": 1, "measured": True},
        {"role": "MEASURED", "index": 2, "measured": True},
        {"role": "MEASURED", "index": 3, "measured": True},
    ]
    archive_root = evidence / "transition-archives"
    run_root = output / "raw-runs"
    archive_root.mkdir()
    run_root.mkdir()
    run_rows: list[dict[str, Any]] = []
    stop_after_failure = False
    for planned in schedule:
        suffix = "WARMUP" if not planned["measured"] else f"MEASURED_{planned['index']:02d}"
        execution_id = f"DEV_PSI_TRANSITION_A05C2_{run_id}_{run_attempt}_{suffix}"
        archive_name = (
            "transition-warmup.zip"
            if not planned["measured"]
            else f"transition-{planned['index']:02d}.zip"
        )
        archive = archive_root / archive_name
        row: dict[str, Any] = {
            **planned,
            "execution_id": execution_id,
            "run_status": "NOT_RUN_AFTER_PRIOR_FAILURE" if stop_after_failure else "NOT_STARTED",
            "archive_path": f"transition-archives/{archive_name}",
            "archive_sha256": None,
            "archive_verification": None,
            "full_transition_wall_ms": None,
            "summary": None,
            "error": None,
        }
        if stop_after_failure:
            run_rows.append(row)
            continue
        destination = run_root / execution_id
        started = time.perf_counter()
        try:
            a05.run_a05_transition(
                repo,
                destination,
                execution_id,
                isolation_backend="docker",
                preserve_partial_evidence=True,
                sandbox_preflight_id=preflight["preflight_id"],
                positive_add_profile_path=repo / contract.profile_path,
                positive_add_study_id=contract.study_id,
            )
            row["full_transition_wall_ms"] = round((time.perf_counter() - started) * 1000, 3)
            _read_json(destination / "development_run.json", "POSITIVE_ADD_C2_RUN_RECORD_MISSING")
            packed = pack_psi_transition_archive(
                destination,
                archive,
                repo,
                workflow_run_url,
                f"mono-ci-psi-a05-c2-{run_id}-{run_attempt}-{suffix.lower()}",
                uv_version,
                execution_origin="HOSTED_CI",
            )
            verification = verify_psi_transition_archive(archive, repository=repo)
            if verification["verification_status"] != "PASS":
                raise ContractValidationError("POSITIVE_ADD_C2_TRANSITION_ARCHIVE_READBACK_FAILED")
            with tempfile.TemporaryDirectory(prefix="positive-add-c2-readback-") as temporary:
                readback = Path(temporary)
                _extract_run(archive, readback)
                summary = _summarize_run(readback, packed["archive_sha256"], contract)
            row.update(
                {
                    "run_status": "COMPLETED",
                    "archive_sha256": packed["archive_sha256"],
                    "archive_verification": "PASS",
                    "summary": summary,
                }
            )
        except Exception as error:
            row.update(
                {
                    "run_status": "FAILED",
                    "error": {"type": type(error).__name__, "message": str(error)[:2000]},
                }
            )
            if destination.exists() and destination.is_dir() and not destination.is_symlink():
                shutil.copytree(destination, evidence / "partial-runs" / execution_id)
            stop_after_failure = True
        run_rows.append(row)
    measured_count = sum(row["run_status"] == "COMPLETED" and row["measured"] for row in run_rows)
    warmup = next(row for row in run_rows if not row["measured"])
    results = {
        "schema_version": contract.results_version,
        "study_id": contract.study_id,
        "classification": "TEST_ONLY_AUTHOR_DECLARED_DEVELOPMENT",
        "workflow": {"run_id": run_id, "run_attempt": run_attempt, "run_url": workflow_run_url},
        "freeze_sha256": freeze_sha,
        "execution_status": "COMPLETED"
        if all(row["run_status"] == "COMPLETED" for row in run_rows)
        else "PARTIAL",
        "warmup_status": warmup["run_status"],
        "measured_repetitions_completed": measured_count,
        "runs": run_rows,
        "official_boundary": GATES,
    }
    validate_payload(contract.results_schema, results)
    result_path = evidence / "C2_RESULTS.json"
    _write_new(result_path, pretty_json_bytes(results))
    _write_new(
        Path(f"{result_path}.sha256"),
        f"{sha256_file(result_path)}  C2_RESULTS.json\n".encode("ascii"),
    )
    _write_checksums(evidence)
    readback = verify_results(evidence, repo, contract)
    return {
        "study_id": contract.study_id,
        "execution_status": results["execution_status"],
        "measured_repetitions_completed": measured_count,
        "freeze_sha256": freeze_sha,
        "verification_status": readback["verification_status"],
        "evidence_path": str(evidence),
    }


def verify_results(
    evidence_root: Path,
    repository: Path,
    contract: C2StudyContract = C2_V1,
) -> dict[str, Any]:
    """Verify C2 freeze, inventory checksums, and every archived transition by readback."""
    evidence = evidence_root.resolve(strict=True)
    repo = repository.resolve(strict=True)
    result_path = evidence / "C2_RESULTS.json"
    result = _read_json(result_path, "POSITIVE_ADD_C2_RESULTS_MISSING")
    validate_payload(contract.results_schema, result)
    result_sha = sha256_file(result_path)
    if (
        Path(f"{result_path}.sha256").read_text(encoding="ascii").strip()
        != f"{result_sha}  C2_RESULTS.json"
    ):
        raise ContractValidationError("POSITIVE_ADD_C2_RESULTS_SIDECAR_MISMATCH")
    freeze_path = evidence / "PRE_RUN_FREEZE_C2.json"
    freeze = _read_json(freeze_path, "POSITIVE_ADD_C2_FREEZE_MISSING")
    validate_payload(contract.freeze_schema, freeze)
    freeze_sha = sha256_file(freeze_path)
    if (
        result.get("freeze_sha256") != freeze_sha
        or Path(f"{freeze_path}.sha256").read_text(encoding="ascii").strip()
        != f"{freeze_sha}  PRE_RUN_FREEZE_C2.json"
        or freeze.get("protocol_sha256")
        != sha256_file(evidence / "protocol" / contract.protocol_json.name)
        or freeze.get("profile_sha256")
        != sha256_file(evidence / "protocol/inputs" / contract.profile_path.name)
    ):
        raise ContractValidationError("POSITIVE_ADD_C2_FREEZE_BINDING_MISMATCH")
    _verify_frozen_source_bindings(repo, freeze)
    for row in result["runs"]:
        if row["run_status"] != "COMPLETED":
            continue
        archive = evidence / row["archive_path"]
        verified = verify_psi_transition_archive(archive, repository=repo)
        if (
            verified["verification_status"] != "PASS"
            or verified["archive_sha256"] != row["archive_sha256"]
        ):
            raise ContractValidationError("POSITIVE_ADD_C2_ARCHIVE_BINDING_MISMATCH")
        with tempfile.TemporaryDirectory(prefix="positive-add-c2-verify-") as temporary:
            readback = Path(temporary)
            _extract_run(archive, readback)
            run_record = _read_json(
                readback / "development_run.json", "POSITIVE_ADD_C2_RUN_RECORD_MISSING"
            )
            if run_record.get("source_revision_sha") != freeze["implementation_commit"]:
                raise ContractValidationError("POSITIVE_ADD_C2_RUN_COMMIT_FREEZE_MISMATCH")
            summary = _summarize_run(readback, row["archive_sha256"], contract)
        if summary != row["summary"]:
            raise ContractValidationError("POSITIVE_ADD_C2_SUMMARY_READBACK_MISMATCH")
    expected = _inventory(evidence)
    expected_text = "".join(f"{row['sha256']}  {row['path']}\n" for row in expected)
    if (evidence / "SHA256SUMS").read_text(encoding="ascii") != expected_text:
        raise ContractValidationError("POSITIVE_ADD_C2_CHECKSUM_INVENTORY_MISMATCH")
    return {
        "verification_status": "PASS",
        "archive_count": sum(row["run_status"] == "COMPLETED" for row in result["runs"]),
        "results_sha256": result_sha,
        "freeze_sha256": freeze_sha,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    preflight = commands.add_parser("preflight")
    preflight.add_argument("--repository", type=Path, required=True)
    preflight.add_argument("--output", type=Path, required=True)
    preflight.add_argument("--version", choices=("1", "2"), default="1")
    run = commands.add_parser("run")
    run.add_argument("--repository", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--preflight", type=Path, required=True)
    run.add_argument("--workflow-run-url", required=True)
    run.add_argument("--run-id", required=True)
    run.add_argument("--run-attempt", required=True)
    run.add_argument("--uv-version", required=True)
    run.add_argument("--version", choices=("1", "2"), default="1")
    verify = commands.add_parser("verify")
    verify.add_argument("--evidence", type=Path, required=True)
    verify.add_argument("--repository", type=Path, required=True)
    verify.add_argument("--version", choices=("1", "2"), default="1")
    return parser


def main() -> int:
    args = _parser().parse_args()
    contract = C2_V2 if getattr(args, "version", "1") == "2" else C2_V1
    try:
        if args.command == "preflight":
            result = run_preflight(args.repository, args.output)
        elif args.command == "run":
            result = run_study(
                args.repository,
                args.output,
                args.preflight,
                workflow_run_url=args.workflow_run_url,
                run_id=args.run_id,
                run_attempt=args.run_attempt,
                uv_version=args.uv_version,
                contract=contract,
            )
        else:
            result = verify_results(args.evidence, args.repository, contract)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (ContractValidationError, ProtocolError, OSError, ValueError) as error:
        print(f"C2 study failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
