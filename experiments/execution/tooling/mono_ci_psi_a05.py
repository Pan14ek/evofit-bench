"""Bounded A0.4→A0.5 adapter over the existing isolated Method Ψ runner."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess  # nosec B404 - fixed Git argv only
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import yaml

import experiments.execution.tooling.mono_ci_psi_transition as transition
from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError, ProtocolError
from experiments.execution.tooling.hashing import (
    pretty_json_bytes,
    sha256_bytes,
    sha256_file,
)
from experiments.execution.tooling.mono_ci_psi_coverage import (
    _REQUIREMENT_CAPABILITY_MAPPINGS,
    assess_adaptation_necessity,
    verify_inspection_coverage,
)
from experiments.execution.tooling.mono_ci_psi_evidence import (
    build_inspection_scope_artifact,
    evaluator_source_artifacts,
    run_fresh_evaluator,
)

BEFORE_COMMIT = "d3101c0d3aa9b7b709253b6ec7518416f05f65b9"
BEFORE_REPOSITORY_TREE = "2b436e0aaf09403ea516d73d20a466a122f86592"
BEFORE_APPLICATION_TREE = "007196f68652bc13f6798805793ffdfae96f95f7"
BEFORE_STATE = "A0_4_REPORT_QUERY_PORT"
AFTER_STATE = "A0_5_MODULE_DATA_OWNERSHIP"
BASELINE_NAME = "RECONSTRUCTED_B0_A04_V1.json"
BASELINE_SCHEMA = "mono_ci_b0_psi_reconstructed_baseline_a04_v1.schema.json"
BASELINE_RELATIVE = "experiments/execution/mono-ci-b0-psi-execution-a05-v1"
BASELINE_ID = "MONO_CI_RECONSTRUCTED_B0_A04_V1"
OWNERSHIP_EVALUATOR = "AC_DATA_OWNERSHIP"
PROBE_PATH = "app/modules/tasks/repository.py"
PROBE_SOURCE = (
    "\n\nfrom sqlalchemy import MetaData, Table\n\n"
    "def _a05_probe_foreign_notification_table(session):\n"
    '    foreign_table = Table("notifications", MetaData(), autoload_with=session.bind)\n'
    "    return session.execute(select(foreign_table)).all()\n"
)


def _git_text(repository: Path, *args: str) -> str:
    git_binary = shutil.which("git")
    if git_binary is None:
        raise ProtocolError("MONO_CI_PSI_A05_GIT_EXECUTABLE_MISSING")
    result = subprocess.run(  # nosec B603 # noqa: S603 - fixed local Git argv only
        [git_binary, "-C", str(repository), *args],
        check=False,
        capture_output=True,
        text=True,
        env={"PATH": os.defpath, "LANG": "C.UTF-8"},
    )
    if result.returncode:
        raise ProtocolError("MONO_CI_PSI_A05_GIT_READ_FAILED")
    return result.stdout.strip()


def _validate_a04_proposal(repository: Path) -> dict[str, Any]:
    proposal_root = repository / BASELINE_RELATIVE
    checksum_path = proposal_root / "SHA256SUMS"
    if not checksum_path.is_file() or checksum_path.is_symlink():
        raise ContractValidationError("MONO_CI_PSI_A05_BASELINE_INVENTORY_MISSING")
    declared: dict[str, str] = {}
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([a-f0-9]{64})  (.+)", line)
        if match is None or match.group(2) in declared:
            raise ContractValidationError("MONO_CI_PSI_A05_BASELINE_INVENTORY_INVALID")
        declared[match.group(2)] = match.group(1)
    actual: dict[str, str] = {}
    for path in proposal_root.rglob("*"):
        if path.is_symlink():
            raise ContractValidationError("MONO_CI_PSI_A05_BASELINE_SYMLINK_FORBIDDEN")
        if path.is_file() and path != checksum_path:
            actual[path.relative_to(proposal_root).as_posix()] = sha256_file(path)
    if declared != actual:
        raise ContractValidationError("MONO_CI_PSI_A05_BASELINE_INVENTORY_MISMATCH")
    proposal_path = proposal_root / BASELINE_NAME
    proposal_bytes = proposal_path.read_bytes()
    proposal = json.loads(proposal_bytes)
    validate_payload(BASELINE_SCHEMA, proposal)
    digest = sha256_bytes(proposal_bytes)
    sidecar = (proposal_root / f"{BASELINE_NAME}.sha256").read_text(encoding="utf-8").strip()
    if sidecar != f"{digest}  {BASELINE_NAME}":
        raise ContractValidationError("MONO_CI_PSI_A05_BASELINE_SIDECAR_MISMATCH")
    if (
        _git_text(repository, "rev-parse", f"{BEFORE_COMMIT}^{{tree}}") != BEFORE_REPOSITORY_TREE
        or _git_text(repository, "rev-parse", f"{BEFORE_COMMIT}:app") != BEFORE_APPLICATION_TREE
    ):
        raise ContractValidationError("MONO_CI_PSI_A05_A04_BASELINE_SOURCE_MISMATCH")
    manifest_bytes = transition._git_bytes(
        repository, BEFORE_COMMIT, f"architecture/states/{BEFORE_STATE}.yaml"
    )
    if sha256_bytes(manifest_bytes) != proposal["derivation"]["state_manifest_sha256"]:
        raise ContractValidationError("MONO_CI_PSI_A05_BASELINE_MANIFEST_DIGEST_MISMATCH")
    rows = {row["evaluator_id"]: row for row in proposal["representations"]}
    if set(rows) != {"AC_PUBLIC_API", "AC_MODULE_GRAPH"}:
        raise ContractValidationError("MONO_CI_PSI_A05_BASELINE_CONTROL_SET_MISMATCH")
    for evaluator_id, config_path in transition.EVALUATOR_CONFIGS.items():
        source_rows, _source_manifest, source_digest = evaluator_source_artifacts(repository)
        row = rows[evaluator_id]
        if (
            row["evaluator_source_sha256"] != source_digest
            or row["evaluator_configuration_sha256"] != sha256_file(repository / config_path)
            or not source_rows
        ):
            raise ContractValidationError("MONO_CI_PSI_A05_BASELINE_EVALUATOR_BINDING_MISMATCH")
    return {
        "baseline_id": BASELINE_ID,
        "baseline_configuration_sha256": digest,
        "identity_status": "PROSPECTIVE_RECONSTRUCTION_NOT_HISTORICAL",
        "approval_status": "NOT_APPROVED",
    }


@contextmanager
def a05_transition_context(
    repository: Path,
    *,
    extension_builder: Any,
    after_commit: str | None = None,
) -> Iterator[None]:
    """Temporarily configure the immutable A0.4→A0.5 source pair."""
    repo = repository.resolve(strict=True)
    after_commit = after_commit or _git_text(repo, "rev-parse", "HEAD")
    if re.fullmatch(r"[a-f0-9]{40}", after_commit) is None:
        raise ContractValidationError("MONO_CI_PSI_A05_AFTER_COMMIT_INVALID")
    resolved_commit = _git_text(repo, "rev-parse", f"{after_commit}^{{commit}}")
    if resolved_commit != after_commit:
        raise ContractValidationError("MONO_CI_PSI_A05_AFTER_COMMIT_NOT_CANONICAL")
    after_repository_tree = _git_text(repo, "rev-parse", f"{after_commit}^{{tree}}")
    after_application_tree = _git_text(repo, "rev-parse", f"{after_commit}:app")
    assignments = {
        "BEFORE_COMMIT": BEFORE_COMMIT,
        "AFTER_COMMIT": after_commit,
        "BEFORE_REPOSITORY_TREE": BEFORE_REPOSITORY_TREE,
        "AFTER_REPOSITORY_TREE": after_repository_tree,
        "BEFORE_APP_TREE": BEFORE_APPLICATION_TREE,
        "AFTER_APP_TREE": after_application_tree,
        "BEFORE_STATE": BEFORE_STATE,
        "AFTER_STATE": AFTER_STATE,
        "BASELINE_NAME": BASELINE_NAME,
        "PROPOSAL_RELATIVE": BASELINE_RELATIVE,
        "verify_execution_proposal": _validate_a04_proposal,
        "TRANSITION_RUN_SCHEMA_VERSION": "MONO_CI_PSI_TRANSITION_RUN_V3",
        "TRANSITION_UNIT_OF_ANALYSIS": "ONE_A0_4_TO_A0_5_ARCHITECTURE_TRANSITION",
        "ADAPTATION_NECESSITY_SCHEMA_VERSION": "MONO_CI_PSI_ADAPTATION_NECESSITY_V3",
        "TRANSITION_RUN_EXTENSION_BUILDER": extension_builder,
        "REPOSITORY_ROOT": repo,
    }
    previous = {name: getattr(transition, name) for name in assignments}
    try:
        for name, value in assignments.items():
            setattr(transition, name, value)
        yield
    finally:
        for name, value in previous.items():
            setattr(transition, name, value)


def run_a05_transition(repository: Path, output_root: Path, execution_id: str) -> dict[str, Any]:
    """Execute the existing isolated P runner against the pinned ΔA5 transition."""
    repo = repository.resolve(strict=True)
    _validate_a04_proposal(repo)
    with a05_transition_context(repo, extension_builder=_build_a05_extension):
        return transition.run_transition(repo, output_root, execution_id)


def _build_a05_extension(
    repository: Path, run_root: Path, run_record: dict[str, Any]
) -> dict[str, str]:
    repo = repository.resolve(strict=True)
    after_commit = run_record["transition"]["after_commit_sha"]
    after_tree = run_record["transition"]["after_repository_tree_sha"]
    after_app_tree = run_record["transition"]["after_application_tree_sha"]
    manifest_bytes = transition._git_bytes(
        repo, after_commit, f"architecture/states/{AFTER_STATE}.yaml"
    )
    manifest = yaml.safe_load(manifest_bytes)
    ownership = manifest["persistence_ownership"]
    model_registry_exception = ownership["shared_infrastructure"]["model_registry_exception"]
    requirement_value = {
        "table_owners": ownership["table_owners"],
        "model_modules": ownership["model_modules"],
        "repository_modules": ownership["repository_modules"],
        "reporting_table_owner": ownership["reporting_table_owner"],
        "prohibited_access_patterns": ownership["prohibited_access_patterns"],
        "model_registry_exception": model_registry_exception,
    }

    implementation_root = run_root / "PSI/evaluator-observations/implementation/AC_DATA_OWNERSHIP"
    source_rows, source_manifest_bytes, evaluator_source_sha256 = evaluator_source_artifacts(repo)
    source_manifest_path = implementation_root / "source-manifest.json"
    transition._write_new_file(source_manifest_path, source_manifest_bytes)
    for source_row in source_rows:
        source_path = repo / "architecture/acceptance/a1" / source_row["path"]
        source_bytes = source_path.read_bytes()
        if sha256_bytes(source_bytes) != source_row["sha256"]:
            raise ContractValidationError("MONO_CI_PSI_A05_EVALUATOR_SOURCE_CHANGED")
        transition._write_new_file(
            implementation_root / "source" / source_row["path"], source_bytes
        )
    config_relative = "architecture/acceptance/a1/data_ownership_v1.yaml"
    config_bytes = (repo / config_relative).read_bytes()
    config_sha256 = sha256_bytes(config_bytes)
    transition._write_new_file(implementation_root / "data_ownership_v1.yaml", config_bytes)
    evaluator_config = yaml.safe_load(config_bytes)
    evaluator_version = str(evaluator_config["evaluator"]["version"])

    _positive_run, positive_row = _run_bound_evaluator(
        repository=repo,
        source_checkout=repo,
        source_commit=after_commit,
        architecture_state=AFTER_STATE,
        evaluator_id=OWNERSHIP_EVALUATOR,
        output_directory=run_root / "PSI/evaluator-observations/a05-positive/AC_DATA_OWNERSHIP",
        configuration_bytes=config_bytes,
        state_manifest_bytes=manifest_bytes,
    )

    probe_dir: Path | None = None
    temporary: tempfile.TemporaryDirectory[str] | None = None
    try:
        temporary = tempfile.TemporaryDirectory(prefix="mono-ci-psi-a05-probe-")
        probe_dir = Path(temporary.name) / "source"
        transition._git_worktree(repo, "add", "--detach", str(probe_dir), after_commit)
        probe_file = probe_dir / PROBE_PATH
        probe_file.write_text(
            probe_file.read_text(encoding="utf-8") + PROBE_SOURCE,
            encoding="utf-8",
        )
        _git_run(probe_dir, "add", "--", PROBE_PATH)
        _git_run(
            probe_dir,
            "-c",
            "user.name=EvoFitBench A05 Probe",
            "-c",
            "user.email=a05-probe@example.invalid",
            "commit",
            "--quiet",
            "-m",
            "isolated A0.5 ownership violation probe",
        )
        probe_commit = _git_text(probe_dir, "rev-parse", "HEAD")
        probe_parent = _git_text(probe_dir, "rev-parse", "HEAD^")
        if probe_parent != after_commit:
            raise ContractValidationError("MONO_CI_PSI_A05_PROBE_PARENT_MISMATCH")
        changed_paths = _git_text(
            probe_dir, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"
        ).splitlines()
        if changed_paths != [PROBE_PATH]:
            raise ContractValidationError("MONO_CI_PSI_A05_PROBE_SCOPE_INVALID")
        probe_tree = _git_text(probe_dir, "rev-parse", "HEAD^{tree}")
        probe_app_tree = _git_text(probe_dir, "rev-parse", "HEAD:app")
        negative_rows = []
        negative_ids = ("AC_PUBLIC_API", "AC_MODULE_GRAPH", "AC_DATA_OWNERSHIP")
        for evaluator_id in negative_ids:
            config_path = transition.EVALUATOR_CONFIGS.get(
                evaluator_id, "architecture/acceptance/a1/data_ownership_v1.yaml"
            )
            negative_config_bytes = (repo / config_path).read_bytes()
            _run, row = _run_bound_evaluator(
                repository=repo,
                source_checkout=probe_dir,
                source_commit=probe_commit,
                architecture_state=AFTER_STATE,
                evaluator_id=evaluator_id,
                output_directory=(
                    run_root / "PSI/evaluator-observations/a05-negative" / evaluator_id
                ),
                configuration_bytes=negative_config_bytes,
                state_manifest_bytes=manifest_bytes,
            )
            negative_rows.append(row)
        if _git_text(probe_dir, "status", "--porcelain"):
            raise ContractValidationError("MONO_CI_PSI_A05_PROBE_WORKTREE_DIRTY")
    finally:
        if probe_dir is not None:
            transition._git_worktree(repo, "remove", "--force", str(probe_dir), check=False)
        if temporary is not None:
            temporary.cleanup()

    baseline_bytes = (run_root / "provenance/reconstructed-b0-proposal.json").read_bytes()
    baseline = json.loads(baseline_bytes)
    requirement = {
        "control_id": "architecture.data_ownership.persistence_ownership",
        "requirement_type": "architecture.data_ownership.persistence_ownership",
        "detail_status": "SPECIFIED",
        "value": requirement_value,
        "source_kind": "VERSIONED_ARCHITECTURE_STATE_MANIFEST",
        "source_ref": {
            "path": f"architecture/states/{AFTER_STATE}.yaml",
            "sha256": sha256_bytes(manifest_bytes),
        },
    }
    mapping_spec = _REQUIREMENT_CAPABILITY_MAPPINGS[
        "architecture.data_ownership.persistence_ownership"
    ]
    mapping = {
        "requirement_type": "architecture.data_ownership.persistence_ownership",
        **mapping_spec,
        "status": "VERIFIED_RULE_IMPLEMENTATION",
    }
    old_diagnostic = json.loads(
        (run_root / "diagnostics/adaptation-necessity-assessment.json").read_text(encoding="utf-8")
    )
    old_capabilities: dict[str, dict[str, Any]] = {}
    for assessment in old_diagnostic.get("assessments", []):
        for row in assessment.get("capability_inventory", {}).get("capabilities_after", []):
            old_capabilities[row["capability_type"]] = row
    active_evaluators = ["AC_PUBLIC_API", "AC_MODULE_GRAPH"]
    probe_by_id = {row["evaluator_id"]: row for row in negative_rows}
    old_compliant = all(
        probe_by_id[evaluator_id]["compliance"] == "COMPLIANT" for evaluator_id in active_evaluators
    )
    ownership_detected = (
        probe_by_id[OWNERSHIP_EVALUATOR]["compliance"] == "NON_COMPLIANT"
        and "FOREIGN_TABLE_ACCESS" in probe_by_id[OWNERSHIP_EVALUATOR]["finding_codes"]
    )
    adaptation_assessment = assess_adaptation_necessity(
        {
            "configuration_sha256_before": sha256_bytes(baseline_bytes),
            "configuration_sha256_after": sha256_bytes(baseline_bytes),
            "requirements_after": [requirement],
            "capabilities_after": list(old_capabilities.values()),
            "requirement_capability_mappings": [mapping],
            "unresolved_requirements_after": [],
            "evaluator_identity_verified": True,
            "architecture_identity_verified": True,
            "configuration_identity_verified": True,
            "source_inspection_before": "COMPLETE",
            "source_inspection_after": "COMPLETE",
            "evaluator_compliance_before": "COMPLIANT",
            "evaluator_compliance_after": "COMPLIANT",
            "rule_scope_match_before": True,
            "rule_scope_match_after": True,
            "requirement_inventory_status_after": "COMPLETE_FOR_DECLARED_MANIFEST_TYPES",
            "requirement_universe_completeness_after": "UNKNOWN",
            "capability_inventory_status_after": "VERIFIED_FOR_DECLARED_STATIC_SCOPE",
            "architecture_state_after": AFTER_STATE,
            "pair_semantic_validity": "UNKNOWN",
            "normative_applicability": "DECLARED_NOT_APPROVED",
            "baseline_identity": "PROSPECTIVE_RECONSTRUCTION_NOT_HISTORICAL",
            "independent_review": False,
        }
    )
    method_result = json.loads(
        (run_root / run_record["psi"]["raw_result_path"]).read_text(encoding="utf-8")
    )
    positive = {
        "condition_status": "COMPLIANT_A05_SOURCE",
        "evaluator": positive_row,
    }
    negative = {
        "condition_status": "ISOLATED_TASKS_FOREIGN_NOTIFICATIONS_TABLE_ACCESS",
        "source_commit_sha": probe_commit,
        "changed_paths": changed_paths,
        "evaluators": sorted(negative_rows, key=lambda row: row["evaluator_id"]),
    }
    extension = {
        "schema_version": "MONO_CI_PSI_A05_EXPERIMENT_EVIDENCE_V1",
        "execution_id": run_record["execution_id"],
        "transition": {
            "before_state": BEFORE_STATE,
            "after_state": AFTER_STATE,
            "before_commit_sha": run_record["transition"]["before_commit_sha"],
            "after_commit_sha": after_commit,
            "after_repository_tree_sha": after_tree,
            "after_application_tree_sha": after_app_tree,
            "probe_parent_commit_sha": probe_parent,
            "probe_commit_sha": probe_commit,
            "probe_repository_tree_sha": probe_tree,
            "probe_application_tree_sha": probe_app_tree,
            "probe_changed_paths": changed_paths,
        },
        "baseline": {
            "configuration_id": BASELINE_ID,
            "configuration_sha256": sha256_bytes(baseline_bytes),
            "historical_identity": baseline["historical_identity"],
            "approval_status": "NOT_APPROVED",
            "active_representations": active_evaluators,
            "ownership_representation_active": False,
        },
        "independent_requirement": {
            "requirement_id": requirement["control_id"],
            "requirement_type": requirement["requirement_type"],
            "source_path": requirement["source_ref"]["path"],
            "source_sha256": requirement["source_ref"]["sha256"],
            "source_kind": requirement["source_kind"],
            "authority_status": manifest["authority_status"],
            "value": requirement_value,
            "mapping_id": mapping_spec["mapping_id"],
            "mapping_status": "VERIFIED_RULE_IMPLEMENTATION_NOT_SEMANTIC_APPROVAL",
        },
        "ownership_evaluator": {
            "evaluator_id": OWNERSHIP_EVALUATOR,
            "version": evaluator_version,
            "source_sha256": evaluator_source_sha256,
            "configuration_path": config_relative,
            "configuration_sha256": config_sha256,
            "a04_applicability": "NOT_APPLICABLE",
            "a05_applicability": "ACTIVE",
            "coverage_limits": evaluator_config.get("coverage_limits", []),
        },
        "positive_condition": positive,
        "negative_condition": negative,
        "adequacy_diagnostic": {
            "assessment_status": adaptation_assessment["assessment_status"],
            "missing_post_transition_controls": adaptation_assessment[
                "missing_post_transition_controls"
            ],
            "requirement_capability_comparison": adaptation_assessment[
                "requirement_capability_comparison"
            ],
            "old_controls_detected_probe": not old_compliant,
            "ownership_evaluator_detected_probe": ownership_detected,
            "old_configuration_insufficient_for_declared_obligation": bool(
                old_compliant and ownership_detected
            ),
            "known_limitations": list(evaluator_config.get("coverage_limits", []))
            + [
                "The A0.5 requirement is a declared engineering policy, not independently "
                "approved normative authority.",
                "The ownership capability was evaluated prospectively but was not active in "
                "the reconstructed A0.4 baseline.",
                "This static source probe does not establish runtime enforcement or semantic "
                "adequacy beyond the recorded detector scope.",
            ],
        },
        "candidate_verification": {
            "status": "NOT_EXECUTED",
            "candidate_present": method_result.get("candidate") is not None,
            "reason": (
                "No candidate was materialized by Method Ψ."
                if method_result.get("candidate") is None
                else "A candidate was materialized; independent candidate execution requires "
                "a separate candidate-verification pass."
            ),
        },
        "scientific_boundary": {
            "method_decision": run_record["psi"]["decision"],
            "operation_plan": method_result.get("operation_plan", {}).get("operations", []),
            "candidate_status": (
                "MATERIALIZED" if method_result.get("candidate") is not None else "NOT_MATERIALIZED"
            ),
            "study_readiness": run_record["study_readiness"],
            "measurement_status": run_record["measurement_status"],
            "p_algorithm_status": run_record["p_algorithm_status"],
            "g1": run_record["g1"],
            "g4": run_record["g4"],
            "reference_gate": run_record["reference_gate"],
            "scoring": run_record["psi"]["scoring"],
        },
    }
    extension_path = run_root / "diagnostics/a05-experiment-evidence.json"
    extension_bytes = pretty_json_bytes(extension)
    transition._write_new_file(extension_path, extension_bytes)
    validate_payload(
        transition.A05_EXPERIMENT_EVIDENCE_SCHEMA,
        extension,
    )
    return {
        "path": "diagnostics/a05-experiment-evidence.json",
        "sha256": sha256_bytes(extension_bytes),
    }


def _run_bound_evaluator(
    *,
    repository: Path,
    source_checkout: Path,
    source_commit: str,
    architecture_state: str,
    evaluator_id: str,
    output_directory: Path,
    configuration_bytes: bytes,
    state_manifest_bytes: bytes,
) -> tuple[dict[str, Any], dict[str, Any]]:
    run = run_fresh_evaluator(
        repository=repository,
        source_checkout=source_checkout,
        evaluator_id=evaluator_id,
        architecture_state=architecture_state,
        source_commit_sha=source_commit,
        output_directory=output_directory,
    )
    run_root = output_directory.parents[3]
    output_path = run_root / run["output_path"]
    output_bytes = output_path.read_bytes()
    coverage = verify_inspection_coverage(
        repository=repository,
        source_commit_sha=source_commit,
        source_tree_sha=run["source_tree_sha"],
        architecture_state=architecture_state,
        evaluator_id=evaluator_id,
        evaluator_configuration_bytes=configuration_bytes,
        state_manifest_bytes=state_manifest_bytes,
        evaluator_output_bytes=output_bytes,
        evaluator_evidence=run["evidence"],
    )
    coverage_path = output_directory / "inspection-coverage.json"
    transition._write_new_file(coverage_path, pretty_json_bytes(coverage))
    coverage_sha = sha256_file(coverage_path)
    inspection_path = output_directory / "inspection-scope.json"
    transition._write_new_file(
        inspection_path,
        pretty_json_bytes(
            build_inspection_scope_artifact(run["evidence"], sha256_file(output_path), coverage)
        ),
    )
    diagnostics = run["evidence"].get("diagnostics", {})
    finding_codes = sorted(
        {
            item["code"]
            for item in diagnostics.get("policy_findings", [])
            if isinstance(item, dict) and isinstance(item.get("code"), str)
        }
    )
    if not finding_codes:
        finding_codes = sorted(
            {
                item["code"]
                for value in diagnostics.values()
                if isinstance(value, list)
                for item in value
                if isinstance(item, dict) and isinstance(item.get("code"), str)
            }
        )
    evidence = run["evidence"]
    result = evidence.get("result", {})
    row = {
        "source_commit_sha": source_commit,
        "source_tree_sha": run["source_tree_sha"],
        "application_tree_sha": run["target_application_tree_sha"],
        "evaluator_id": evaluator_id,
        "execution_status": result.get("execution_status"),
        "compliance": result.get("compliance"),
        "configuration_sha256": run["configuration_sha256"],
        "evaluator_source_sha256": run["evaluator_source_sha256"],
        "output_path": run["output_path"],
        "output_sha256": sha256_file(output_path),
        "coverage_path": coverage_path.relative_to(run_root).as_posix(),
        "coverage_sha256": coverage_sha,
        "inspection_status": coverage["source_inspection_status"],
        "finding_codes": finding_codes,
    }
    return run, row


def _git_run(repository: Path, *args: str) -> None:
    git_binary = shutil.which("git")
    if git_binary is None:
        raise ProtocolError("MONO_CI_PSI_A05_GIT_EXECUTABLE_MISSING")
    result = subprocess.run(  # nosec B603 # noqa: S603 - fixed local Git argv only
        [git_binary, "-C", str(repository), *args],
        check=False,
        capture_output=True,
        text=True,
        env={"PATH": os.defpath, "LANG": "C.UTF-8"},
    )
    if result.returncode:
        raise ProtocolError("MONO_CI_PSI_A05_PROBE_GIT_COMMAND_FAILED")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execution-id", required=True)
    args = parser.parse_args(argv)
    try:
        result = run_a05_transition(args.repository, args.output, args.execution_id)
    except (ContractValidationError, ProtocolError) as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
