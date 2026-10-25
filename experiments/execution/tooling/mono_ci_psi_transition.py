"""Execute one isolated, DEVELOPMENT-only Method P A0.3 to A0.4 transition."""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import os
import re
import shutil
import subprocess  # nosec B404 - fixed interpreter and generated runtime script
import sys
from pathlib import Path
from typing import Any

import yaml

from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError, ProtocolError
from experiments.execution.tooling.hashing import (
    bundle_sha256,
    pretty_json_bytes,
    sha256_bytes,
    sha256_file,
)
from experiments.execution.tooling.mono_ci_b0_psi_execution import (
    BASELINE_NAME,
    PROPOSAL_RELATIVE,
    _git_bytes,
    _git_text,
    _write_new_file,
    verify_execution_proposal,
)
from experiments.execution.tooling.p_policy_source_v3 import (
    METHOD_INPUT_MANIFEST,
    export_method_inputs_v3,
    package_policy_source_v3,
    verify_method_bundle_v3,
    verify_policy_source_bundle_v3,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BEFORE_COMMIT = "26a9bb667da7d0938e38aca15d2bf29fd1de4829"
AFTER_COMMIT = "d3101c0d3aa9b7b709253b6ec7518416f05f65b9"
BEFORE_REPOSITORY_TREE = "7b951421395f532ca403dab09d76902ff08a807d"
AFTER_REPOSITORY_TREE = "2b436e0aaf09403ea516d73d20a466a122f86592"
BEFORE_APP_TREE = "b147b8961ea9e76c966663d4832e4c303581151a"
AFTER_APP_TREE = "007196f68652bc13f6798805793ffdfae96f95f7"
BEFORE_STATE = "A0_3_GOVERNED_MODULE_GRAPH"
AFTER_STATE = "A0_4_REPORT_QUERY_PORT"
STATE_MANIFESTS_PATH = "architecture/state-manifests.json"
TRANSITION_SCHEMA = "mono_ci_psi_transition_run_v1.schema.json"
RUN_ID_PATTERN = re.compile(r"^DEV_PSI_TRANSITION_[A-Za-z0-9_-]{1,48}$")
RUNTIME_MODULES = (
    "contracts.py",
    "errors.py",
    "hashing.py",
    "inputs.py",
    "p_adaptation.py",
    "p_adaptation_evidence.py",
    "p_applicability.py",
    "p_candidate.py",
    "p_governance.py",
    "p_impact.py",
    "p_input_export_v2.py",
    "p_input_validation.py",
    "p_operations.py",
    "p_policy_source_v3.py",
    "p_semantic.py",
)
RUNTIME_SCHEMAS = (
    "applicability_ruleset_v1.schema.json",
    "architecture_policy_snapshot_v1_1.schema.json",
    "architecture_policy_snapshot_v1_2.schema.json",
    "evaluator_evidence.schema.json",
    "method_input_v2.schema.json",
    "method_input_v3_candidate.schema.json",
    "p_adaptation_evidence_v1.schema.json",
    "p_adaptation_evidence_v2.schema.json",
    "p_adaptation_trace_v1.schema.json",
    "p_candidate_configuration_v1.schema.json",
    "p_coverage_assessment_v1.schema.json",
    "p_governance_decision_v1.schema.json",
    "p_impact_assessment_v1.schema.json",
    "p_operation_plan_v1.schema.json",
    "p_pair_assessment_v1.schema.json",
    "policy_source_v3.schema.json",
)
RUNTIME_VENDOR_PACKAGES = (
    ("yaml", "PyYAML"),
    ("jsonschema", "jsonschema"),
    ("attrs", "attrs"),
    ("attr", "attrs"),
    ("jsonschema_specifications", "jsonschema-specifications"),
    ("referencing", "referencing"),
    ("rpds", "rpds-py"),
    ("typing_extensions", "typing-extensions"),
)
RUNTIME_SOURCE = r"""from __future__ import annotations
import json
import sys
from pathlib import Path

runtime_root = Path(__file__).resolve().parent
sys.path.insert(0, str(runtime_root))
sys.path.insert(0, str(runtime_root / "vendor"))
from experiments.execution.tooling.p_adaptation import (
    EvidenceLedger,
    run_adaptation,
    verify_v3_p_bundle,
)

bundle_path = Path(sys.argv[1]).resolve(strict=True)
result_path = Path(sys.argv[2]).resolve()
verified = verify_v3_p_bundle(bundle_path, evidence_ledger=EvidenceLedger({}, {}, {}))
result = run_adaptation(verified, evidence_context=None)
payload = {
    "method_version": "P_GOVERNED_ADAPTATION_DEVELOPMENT_V1",
    "input_bundle_sha256": verified.manifest["bundle_sha256"],
    "before_applicability": result.before_applicability.to_dict(),
    "after_applicability": result.after_applicability.to_dict(),
    "impact": result.impact.to_dict(),
    "current_pairs": [item.to_dict() for item in result.current_pairs],
    "candidate_pairs": [item.to_dict() for item in result.candidate_pairs],
    "current_coverage": result.current_coverage.to_dict(),
    "candidate_coverage": (
        result.candidate_coverage.to_dict() if result.candidate_coverage else None
    ),
    "operation_plan": result.operation_plan.to_dict(),
    "candidate": dict(result.candidate) if result.candidate is not None else None,
    "candidate_sha256": result.candidate_sha256,
    "governance": result.governance.to_dict(),
    "prediction_v1": dict(result.prediction_v1) if result.prediction_v1 is not None else None,
    "candidate_v1": dict(result.candidate_v1) if result.candidate_v1 is not None else None,
    "evidence_trust_scope": result.evidence_trust_scope,
}
result_path.write_bytes(
    (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
)
"""


def run_transition(repository: Path, output_root: Path, execution_id: str) -> dict[str, Any]:
    """Build source-pinned inputs and execute the existing P DEVELOPMENT API once."""
    repo = repository.resolve(strict=True)
    if RUN_ID_PATTERN.fullmatch(execution_id) is None:
        raise ProtocolError("MONO_CI_PSI_TRANSITION_EXECUTION_ID_INVALID")
    root = output_root.expanduser().absolute()
    if root.exists() or root.is_symlink() or root.is_relative_to(repo):
        raise ProtocolError("MONO_CI_PSI_TRANSITION_OUTPUT_MUST_BE_NEW_AND_EXTERNAL")
    _verify_transition_sources(repo)
    baseline = verify_execution_proposal(repo)
    root.mkdir(parents=True)
    try:
        psi = root / "PSI"
        psi.mkdir()
        proposal_path = repo / PROPOSAL_RELATIVE / BASELINE_NAME
        proposal_bytes = proposal_path.read_bytes()
        _write_new_file(root / "provenance/reconstructed-b0-proposal.json", proposal_bytes)
        orchestrator_bytes = Path(__file__).read_bytes()
        _write_new_file(root / "provenance/transition-runner.py", orchestrator_bytes)

        policy_root = psi / "policy-source"
        policy_root.parent.mkdir(parents=True, exist_ok=True)
        policy = package_policy_source_v3(
            repo / "experiments/execution/policy-pilot/v1/source",
            policy_root,
            "POLICY_PILOT_V1_DRAFT_OPEN_SOURCE",
        )
        registry = json.loads((policy_root / "fitness/policy/registry.json").read_text())
        bundle_root = psi / "method-input"
        export_method_inputs_v3(
            repo,
            policy_root,
            bundle_root,
            "P",
            BEFORE_COMMIT,
            AFTER_COMMIT,
            str(registry["as_of"]),
            structural_manifest_path=f"architecture/states/{AFTER_STATE}.yaml",
        )
        _bind_reconstructed_baseline(bundle_root, proposal_bytes, policy)
        source_binding = _source_binding(repo)
        _add_state_manifest_sidecar(repo, bundle_root, source_binding)
        method_manifest = _reseal_method_bundle(bundle_root)
        verify_method_bundle_v3(bundle_root, expected_method_id="P")

        runtime_root = psi / "method-runtime"
        runtime_inventory = _build_isolated_runtime(repo, runtime_root)
        _write_new_file(
            root / "provenance/runtime-inventory.json", pretty_json_bytes(runtime_inventory)
        )
        raw_root = psi / "raw"
        raw_root.mkdir()
        result_path = raw_root / "method-result.json"
        _execute_isolated_method(repo, runtime_root, bundle_root, result_path)
        result_digest = sha256_file(result_path)
        method_result = json.loads(result_path.read_text(encoding="utf-8"))
        decision = _governance_decision(method_result)
        if decision not in {"HOLD", "REJECT"} or method_result.get("prediction_v1") is not None:
            raise ProtocolError("MONO_CI_PSI_TRANSITION_UNEXPECTED_METHOD_DECISION")
        record = {
            "schema_version": "MONO_CI_PSI_TRANSITION_RUN_V1",
            "execution_id": execution_id,
            "source_revision_sha": _git_text(repo, "rev-parse", "HEAD").strip(),
            "study_id": "MONO_CI_B0_PSI_DEVELOPMENT_TECHNICAL_VALIDATION",
            "mode": "DEVELOPMENT_METHOD_EXECUTION_ONLY",
            "unit_of_analysis": "ONE_A0_3_TO_A0_4_ARCHITECTURE_TRANSITION",
            "study_readiness": "NO_GO",
            "measurement_status": "NOT_EXECUTED",
            "p_algorithm_status": "NOT_READY",
            "g1": "INCOMPLETE",
            "g4": "NOT_AUTHORIZED",
            "reference_gate": "NOT_READY",
            "baseline": {
                "configuration_id": baseline["baseline_id"],
                "configuration_sha256": baseline["baseline_configuration_sha256"],
                "identity_status": baseline["identity_status"],
                "approval_status": baseline["approval_status"],
                "method_input_authorized": False,
            },
            "transition": source_binding,
            "policy_source": {
                "revision": policy["policy_source_revision"],
                "bundle_sha256": policy["policy_bundle_sha256"],
                "authority_status": "DRAFT_OPEN_UNAPPROVED",
            },
            "method_input": {
                "path": "PSI/method-input",
                "bundle_sha256": method_manifest["bundle_sha256"],
                "common_snapshot_sha256": method_manifest["common_snapshot_sha256"],
                "baseline_proposal_sha256": baseline["baseline_configuration_sha256"],
                "source_manifest_path": STATE_MANIFESTS_PATH,
            },
            "runtime": {
                "path": "PSI/method-runtime",
                "inventory_sha256": runtime_inventory["inventory_sha256"],
                "isolation": "PYTHON_ISOLATED_MODE; NO_NETWORK; SOURCE_REPOSITORIES_DENIED",
            },
            "execution_engine": {
                "path": "provenance/transition-runner.py",
                "sha256": sha256_bytes(orchestrator_bytes),
            },
            "psi": {
                "status": "DEVELOPMENT_METHOD_EXECUTED",
                "decision": decision,
                "raw_result_path": "PSI/raw/method-result.json",
                "raw_result_sha256": result_digest,
                "operation_emitted": True,
                "governance_decision_emitted": True,
                "prediction_emitted": method_result.get("prediction_v1") is not None,
                "scoring": "NOT_EXECUTED",
            },
            "other_arms_or_case_outputs_used": False,
            "metrics": "NOT_MEASURED",
            "output_checksums": {
                "PSI/raw/method-result.json": result_digest,
                "PSI/method-input/method_input_v3.json": sha256_file(
                    bundle_root / METHOD_INPUT_MANIFEST
                ),
            },
        }
        _write_new_file(root / "development_run.json", pretty_json_bytes(record))
        _seal_run(root)
        verify_transition_run(root)
        return {
            "execution_id": execution_id,
            "study_readiness": record["study_readiness"],
            "measurement_status": record["measurement_status"],
            "psi_status": record["psi"]["status"],
            "psi_decision": record["psi"]["decision"],
            "method_input_bundle_sha256": method_manifest["bundle_sha256"],
            "raw_result_sha256": result_digest,
            "result_path": str(root / "development_run.json"),
            "inventory_sha256": sha256_file(root / "SHA256SUMS"),
        }
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise


def verify_transition_run(run_root: Path) -> dict[str, Any]:
    """Verify the run, exact P input bundle, raw result, and complete file inventory."""
    root = run_root.resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_RUN_ROOT_INVALID")
    record = json.loads((root / "development_run.json").read_text(encoding="utf-8"))
    validate_payload(TRANSITION_SCHEMA, record)
    if record["study_readiness"] != "NO_GO" or record["measurement_status"] != "NOT_EXECUTED":
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_OFFICIAL_GATE_PROMOTED")
    if record["p_algorithm_status"] != "NOT_READY" or record["g1"] != "INCOMPLETE":
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_METHOD_GATE_PROMOTED")
    bundle_root = root / record["method_input"]["path"]
    manifest = verify_method_bundle_v3(bundle_root, expected_method_id="P")
    if (
        manifest["bundle_sha256"] != record["method_input"]["bundle_sha256"]
        or manifest["common_snapshot_sha256"] != record["method_input"]["common_snapshot_sha256"]
        or manifest["policy_bundle_sha256"] != record["policy_source"]["bundle_sha256"]
    ):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_METHOD_INPUT_BINDING_MISMATCH")
    raw_path = root / record["psi"]["raw_result_path"]
    if sha256_file(raw_path) != record["psi"]["raw_result_sha256"]:
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_RAW_RESULT_DIGEST_MISMATCH")
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    if raw.get("input_bundle_sha256") != manifest["bundle_sha256"]:
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_RAW_INPUT_BINDING_MISMATCH")
    if record["psi"]["decision"] != _governance_decision(raw):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_DECISION_MISMATCH")
    if raw.get("prediction_v1") is not None or record["psi"]["decision"] not in {"HOLD", "REJECT"}:
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_UNEXPECTED_METHOD_DECISION")
    if (
        record["other_arms_or_case_outputs_used"] is not False
        or record["metrics"] != "NOT_MEASURED"
    ):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_SCOPE_PROMOTED")
    if not (root / "provenance/reconstructed-b0-proposal.json").is_file():
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_BASELINE_PROVENANCE_MISSING")
    proposal_digest = sha256_file(root / "provenance/reconstructed-b0-proposal.json")
    if proposal_digest != record["baseline"]["configuration_sha256"]:
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_BASELINE_DIGEST_MISMATCH")
    proposal = json.loads((root / "provenance/reconstructed-b0-proposal.json").read_text())
    authorization = proposal.get("authorization")
    if (
        proposal.get("status") != "RECONSTRUCTION_PROPOSAL_NOT_APPROVED"
        or proposal.get("historical_identity") != "NOT_FOUND"
        or not isinstance(authorization, dict)
        or authorization.get("baseline_approval") is not False
        or authorization.get("method_input_authorized") is not False
        or authorization.get("scientific_measurement_authorized") is not False
    ):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_BASELINE_AUTHORITY_CHANGED")
    if (
        sha256_file(root / record["execution_engine"]["path"])
        != record["execution_engine"]["sha256"]
    ):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_RUNNER_SOURCE_MISMATCH")
    state_sidecar = json.loads((bundle_root / STATE_MANIFESTS_PATH).read_text(encoding="utf-8"))
    transition = state_sidecar["transition"]
    for key in (
        "before_state",
        "after_state",
        "before_commit_sha",
        "after_commit_sha",
    ):
        if transition[key] != record["transition"][key]:
            raise ContractValidationError("MONO_CI_PSI_TRANSITION_STATE_BINDING_MISMATCH")
    if (
        transition["before_tree_sha"] != record["transition"]["before_application_tree_sha"]
        or transition["after_tree_sha"] != record["transition"]["after_application_tree_sha"]
        or state_sidecar["manifests"][0]["sha256"]
        != record["transition"]["before_state_manifest_sha256"]
        or state_sidecar["manifests"][1]["sha256"]
        != record["transition"]["after_state_manifest_sha256"]
    ):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_STATE_BINDING_MISMATCH")
    representation_catalog = yaml.safe_load(
        (bundle_root / "fitness/a0-representations.yaml").read_text(encoding="utf-8")
    )
    provenance = (
        representation_catalog.get("provenance")
        if isinstance(representation_catalog, dict)
        else None
    )
    if (
        not isinstance(provenance, dict)
        or provenance.get("configuration_sha256") != proposal_digest
        or provenance.get("status") != "RECONSTRUCTION_PROPOSAL_NOT_APPROVED"
        or provenance.get("historical_identity") != "NOT_FOUND"
        or provenance.get("baseline_approval") is not False
        or provenance.get("method_input_authorized") is not False
        or provenance.get("policy_bundle_sha256") != record["policy_source"]["bundle_sha256"]
    ):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_PARENT_PROVENANCE_MISMATCH")
    runtime_inventory = json.loads(
        (root / "provenance/runtime-inventory.json").read_text(encoding="utf-8")
    )
    _verify_runtime_inventory(root / "PSI/method-runtime", runtime_inventory)
    if runtime_inventory["inventory_sha256"] != record["runtime"]["inventory_sha256"]:
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_RUNTIME_BINDING_MISMATCH")
    if (
        verify_policy_source_bundle_v3(root / "PSI/policy-source")["policy_bundle_sha256"]
        != record["policy_source"]["bundle_sha256"]
    ):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_POLICY_SOURCE_BINDING_MISMATCH")
    policy_registry = json.loads(
        (root / "PSI/policy-source/fitness/policy/registry.json").read_text(encoding="utf-8")
    )
    if policy_registry.get("closure") != "OPEN" or any(
        row.get("normative_status") != "DRAFT"
        for row in policy_registry.get("policies", [])
        if isinstance(row, dict)
    ):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_POLICY_AUTHORITY_CHANGED")
    for relative, digest in record["output_checksums"].items():
        path = root / relative
        if not path.is_file() or sha256_file(path) != digest:
            raise ContractValidationError("MONO_CI_PSI_TRANSITION_OUTPUT_CHECKSUM_MISMATCH")
    sidecar = (root / "development_run.json.sha256").read_text(encoding="utf-8").strip()
    if sidecar != f"{sha256_file(root / 'development_run.json')}  development_run.json":
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_RUN_SEAL_MISMATCH")
    if _read_checksums(root / "SHA256SUMS") != _directory_checksums(root, {"SHA256SUMS"}):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_RUN_INVENTORY_MISMATCH")
    return record


def pack_transition_archive(
    run_root: Path,
    archive_path: Path,
    repository: Path,
    workflow_run_url: str,
    artifact_name: str,
    uv_version: str,
) -> dict[str, Any]:
    """Use the shared persistent DEVELOPMENT archive implementation."""
    from experiments.execution.tooling.mono_ci_b0_psi_archive import (
        pack_psi_transition_archive,
    )

    return pack_psi_transition_archive(
        run_root, archive_path, repository, workflow_run_url, artifact_name, uv_version
    )


def verify_transition_archive(
    archive_path: Path, *, extract_to: Path | None = None
) -> dict[str, Any]:
    """Use the shared DEVELOPMENT archive verifier for a transition-level run."""
    from experiments.execution.tooling.mono_ci_b0_psi_archive import (
        verify_psi_transition_archive,
    )

    return verify_psi_transition_archive(archive_path, extract_to=extract_to)


def _verify_transition_sources(repository: Path) -> None:
    expected = (
        (BEFORE_COMMIT, BEFORE_REPOSITORY_TREE, BEFORE_APP_TREE),
        (AFTER_COMMIT, AFTER_REPOSITORY_TREE, AFTER_APP_TREE),
    )
    for commit, repository_tree, app_tree in expected:
        if _git_text(repository, "rev-parse", f"{commit}^{{tree}}").strip() != repository_tree:
            raise ContractValidationError("MONO_CI_PSI_TRANSITION_REPOSITORY_TREE_MISMATCH")
        if _git_text(repository, "rev-parse", f"{commit}:app").strip() != app_tree:
            raise ContractValidationError("MONO_CI_PSI_TRANSITION_APP_TREE_MISMATCH")


def _source_binding(repository: Path) -> dict[str, Any]:
    return {
        "before_state": BEFORE_STATE,
        "after_state": AFTER_STATE,
        "before_commit_sha": BEFORE_COMMIT,
        "after_commit_sha": AFTER_COMMIT,
        "before_repository_tree_sha": BEFORE_REPOSITORY_TREE,
        "after_repository_tree_sha": AFTER_REPOSITORY_TREE,
        "before_application_tree_sha": BEFORE_APP_TREE,
        "after_application_tree_sha": AFTER_APP_TREE,
        "before_state_manifest_sha256": sha256_bytes(
            _git_bytes(repository, BEFORE_COMMIT, f"architecture/states/{BEFORE_STATE}.yaml")
        ),
        "after_state_manifest_sha256": sha256_bytes(
            _git_bytes(repository, AFTER_COMMIT, f"architecture/states/{AFTER_STATE}.yaml")
        ),
    }


def _add_state_manifest_sidecar(
    repository: Path, bundle_root: Path, binding: dict[str, Any]
) -> None:
    rows = []
    for state, label, commit_key, digest_key in (
        ("before", BEFORE_STATE, "before_commit_sha", "before_state_manifest_sha256"),
        ("after", AFTER_STATE, "after_commit_sha", "after_state_manifest_sha256"),
    ):
        path = f"architecture/states/{label}.yaml"
        content = _git_bytes(repository, binding[commit_key], path)
        rows.append(
            {
                "state": state,
                "path": path,
                "source_commit_sha": binding[commit_key],
                "sha256": binding[digest_key],
                "content": content.decode("utf-8"),
            }
        )
    payload = {
        "schema_version": "MONO_CI_B0_PSI_ARCHITECTURE_STATE_MANIFESTS_V1",
        "transition": {
            "before_state": BEFORE_STATE,
            "after_state": AFTER_STATE,
            "before_commit_sha": binding["before_commit_sha"],
            "after_commit_sha": binding["after_commit_sha"],
            "before_tree_sha": BEFORE_APP_TREE,
            "after_tree_sha": AFTER_APP_TREE,
        },
        "manifests": rows,
    }
    _write_new_file(bundle_root / STATE_MANIFESTS_PATH, pretty_json_bytes(payload))


def _bind_reconstructed_baseline(
    bundle_root: Path, proposal_bytes: bytes, policy: dict[str, Any]
) -> None:
    proposal = json.loads(proposal_bytes)
    rows = []
    for row in proposal["representations"]:
        rows.append(
            {
                "id": row["representation_id"],
                "criterion": row["criterion_id"],
                "stage": row["stage"],
                "evaluator": row["evaluator_id"],
                "covers": [row["obligation_id"]],
                "evaluator_artifact": None,
                "applicability_scope": {},
                "evidence_contract": {},
            }
        )
    representation_catalog = {
        "schema_version": 1,
        "provenance": {
            "configuration_id": proposal["configuration_id"],
            "configuration_sha256": sha256_bytes(proposal_bytes),
            "status": proposal["status"],
            "historical_identity": proposal["historical_identity"],
            "baseline_approval": proposal["authorization"]["baseline_approval"],
            "method_input_authorized": proposal["authorization"]["method_input_authorized"],
            "policy_source_revision": policy["policy_source_revision"],
            "policy_bundle_sha256": policy["policy_bundle_sha256"],
        },
        "representations": rows,
    }
    (bundle_root / "fitness/a0-representations.yaml").write_text(
        yaml.safe_dump(representation_catalog, sort_keys=False), encoding="utf-8"
    )
    _reseal_method_bundle(bundle_root)


def _reseal_method_bundle(bundle_root: Path) -> dict[str, Any]:
    manifest_path = bundle_root / METHOD_INPUT_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = {row["path"]: row for row in manifest["files"]}
    for relative in ("fitness/a0-representations.yaml", STATE_MANIFESTS_PATH):
        path = bundle_root / relative
        if path.is_file():
            records[relative] = {
                "path": relative,
                "role": "representation_catalog"
                if relative.startswith("fitness/")
                else "structural_observations",
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
    manifest["files"] = sorted(records.values(), key=lambda row: row["path"])
    manifest["bundle_sha256"] = bundle_sha256(manifest["files"])
    manifest_path.write_bytes(pretty_json_bytes(manifest))
    return manifest


def _build_isolated_runtime(repository: Path, runtime_root: Path) -> dict[str, Any]:
    tooling_source = repository / "experiments/execution/tooling"
    package_root = runtime_root / "experiments/execution/tooling"
    package_root.mkdir(parents=True)
    for name in RUNTIME_MODULES:
        shutil.copyfile(tooling_source / name, package_root / name)
    for package_path in (
        runtime_root / "experiments/__init__.py",
        runtime_root / "experiments/execution/__init__.py",
        package_root / "__init__.py",
    ):
        package_path.write_bytes(b'"""Isolated Method P runtime package."""\n')
    schema_source = repository / "experiments/execution/schemas"
    schema_root = runtime_root / "experiments/execution/schemas"
    schema_root.mkdir(parents=True)
    for name in RUNTIME_SCHEMAS:
        shutil.copyfile(schema_source / name, schema_root / name)
    contract_source = repository / "experiments/execution/contracts/fact_vocabulary_v1.json"
    contract_root = runtime_root / "experiments/execution/contracts"
    contract_root.mkdir()
    shutil.copyfile(contract_source, contract_root / contract_source.name)
    catalog_source = repository / "fitness/catalog/architectural-obligations.yaml"
    catalog_root = runtime_root / "fitness/catalog"
    catalog_root.mkdir(parents=True)
    shutil.copyfile(catalog_source, catalog_root / catalog_source.name)
    vendor_root = runtime_root / "vendor"
    vendor_root.mkdir()
    copied_packages: set[str] = set()
    copied_distributions: set[str] = set()
    for package_name, distribution_name in RUNTIME_VENDOR_PACKAGES:
        package_spec = importlib.util.find_spec(package_name)
        if package_spec is None or package_spec.origin is None:
            raise ProtocolError("MONO_CI_PSI_TRANSITION_RUNTIME_DEPENDENCY_MISSING")
        package_directories = package_spec.submodule_search_locations
        if package_directories is not None:
            source_package = Path(next(iter(package_directories))).resolve()
            if source_package.name not in copied_packages:
                shutil.copytree(source_package, vendor_root / source_package.name)
                copied_packages.add(source_package.name)
        else:
            source_module = Path(package_spec.origin).resolve()
            if source_module.name not in copied_packages:
                shutil.copyfile(source_module, vendor_root / source_module.name)
                copied_packages.add(source_module.name)
        distribution = importlib.metadata.distribution(distribution_name)
        distribution_path = Path(distribution._path).resolve()  # type: ignore[attr-defined]
        if distribution_path.name not in copied_distributions:
            shutil.copytree(distribution_path, vendor_root / distribution_path.name)
            copied_distributions.add(distribution_path.name)
    (runtime_root / "execute_method.py").write_text(RUNTIME_SOURCE, encoding="utf-8")
    files = [
        path.relative_to(runtime_root).as_posix()
        for path in sorted(runtime_root.rglob("*"))
        if path.is_file()
    ]
    rows = [
        {"path": relative, "sha256": sha256_file(runtime_root / relative)} for relative in files
    ]
    return {"files": rows, "inventory_sha256": bundle_sha256(rows)}


def _verify_runtime_inventory(runtime_root: Path, inventory: dict[str, Any]) -> None:
    if runtime_root.is_symlink() or not runtime_root.is_dir():
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_RUNTIME_INVALID")
    rows = inventory.get("files")
    if not isinstance(rows, list) or bundle_sha256(rows) != inventory.get("inventory_sha256"):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_RUNTIME_INVENTORY_INVALID")
    declared = {row["path"]: row for row in rows}
    actual = {
        path.relative_to(runtime_root).as_posix()
        for path in runtime_root.rglob("*")
        if path.is_file()
    }
    if actual != set(declared) or any(path.is_symlink() for path in runtime_root.rglob("*")):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_RUNTIME_FILE_SET_MISMATCH")
    for relative, row in declared.items():
        if sha256_file(runtime_root / relative) != row["sha256"]:
            raise ContractValidationError("MONO_CI_PSI_TRANSITION_RUNTIME_DIGEST_MISMATCH")


def _execute_isolated_method(
    repository: Path, runtime_root: Path, bundle_root: Path, output: Path
) -> None:
    interpreter = Path(sys.executable).resolve(strict=True)
    args = [
        str(interpreter),
        "-I",
        "-B",
        str(runtime_root / "execute_method.py"),
        str(bundle_root),
        str(output),
    ]
    if sys.platform == "darwin":
        profile = ["(version 1)", "(deny network*)"]
        for protected in _protected_repository_paths(repository):
            profile.append(f'(deny file-read* (subpath "{_sbpl_escape(str(protected))}"))')
            profile.append(f'(deny file-write* (subpath "{_sbpl_escape(str(protected))}"))')
        profile.append(
            f'(deny file-write* (subpath "{_sbpl_escape(str(runtime_root.resolve()))}"))'
        )
        profile.append(f'(deny file-write* (subpath "{_sbpl_escape(str(bundle_root.resolve()))}"))')
        profile.append("(allow default)")
        command = ["/usr/bin/sandbox-exec", "-p", "".join(profile), *args]
    elif sys.platform.startswith("linux") and shutil.which("bwrap"):
        command = [shutil.which("bwrap") or "bwrap", "--unshare-net", "--ro-bind", "/", "/"]
        for protected in sorted(_protected_repository_paths(repository)):
            command.extend(("--tmpfs", str(protected)))
        command.extend(
            (
                "--bind",
                str(output.parent.resolve()),
                str(output.parent.resolve()),
                "--chdir",
                str(runtime_root),
                *args,
            )
        )
    else:
        raise ProtocolError("MONO_CI_PSI_TRANSITION_NETWORK_ISOLATION_UNAVAILABLE")
    # The OS sandbox wrapper and validated runtime paths are fixed; no shell is used.
    result = subprocess.run(  # nosec B603 # noqa: S603
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=runtime_root,
        env={"PATH": os.defpath, "LANG": "C.UTF-8"},
        timeout=180,
    )
    if result.returncode != 0:
        raise ProtocolError(
            "MONO_CI_PSI_TRANSITION_METHOD_EXECUTION_FAILED: " + result.stderr[-2000:]
        )
    if not output.is_file() or output.is_symlink():
        raise ProtocolError("MONO_CI_PSI_TRANSITION_METHOD_OUTPUT_MISSING")


def _governance_decision(result: dict[str, Any]) -> str:
    governance = result.get("governance")
    if not isinstance(governance, dict) or not isinstance(governance.get("result"), str):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_GOVERNANCE_DECISION_MISSING")
    return governance["result"]


def _protected_repository_paths(repository: Path) -> set[Path]:
    protected = {repository.resolve()}
    for command in ("--git-common-dir", "--git-dir"):
        path = Path(_git_text(repository, "rev-parse", command).strip())
        protected.add((repository / path).resolve() if not path.is_absolute() else path.resolve())
    for line in _git_text(repository, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            protected.add(Path(line.removeprefix("worktree ")).resolve())
    return protected


def _seal_run(root: Path) -> None:
    checksums = _checksums_bytes(root)
    (root / "SHA256SUMS").write_bytes(checksums)
    record_path = root / "development_run.json"
    (root / "development_run.json.sha256").write_text(
        f"{sha256_file(record_path)}  development_run.json\n", encoding="utf-8"
    )
    (root / "SHA256SUMS").write_bytes(_checksums_bytes(root, exclude={"SHA256SUMS"}))


def _checksums_bytes(root: Path, exclude: set[str] | None = None) -> bytes:
    excluded = exclude or set()
    lines = [
        f"{sha256_file(path)}  {path.relative_to(root).as_posix()}"
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.relative_to(root).as_posix() not in excluded
    ]
    return ("\n".join(lines) + "\n").encode()


def _read_checksums(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        result[relative] = digest
    return result


def _directory_checksums(root: Path, exclude: set[str]) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in root.rglob("*")
        if path.is_file() and path.relative_to(root).as_posix() not in exclude
    }


def _sbpl_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _dispatch(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run")
    run_parser.add_argument("--repository", type=Path, default=REPOSITORY_ROOT)
    run_parser.add_argument("--output", type=Path, required=True)
    run_parser.add_argument("--execution-id", required=True)
    pack_parser = commands.add_parser("pack")
    pack_parser.add_argument("--run", type=Path, required=True)
    pack_parser.add_argument("--archive", type=Path, required=True)
    pack_parser.add_argument("--repository", type=Path, default=REPOSITORY_ROOT)
    pack_parser.add_argument("--workflow-run-url", required=True)
    pack_parser.add_argument("--artifact-name", required=True)
    pack_parser.add_argument("--uv-version", required=True)
    verify_parser = commands.add_parser("verify")
    verify_parser.add_argument("--archive", type=Path, required=True)
    verify_parser.add_argument("--extract-to", type=Path)
    args = parser.parse_args(argv)
    if args.command == "run":
        result = run_transition(args.repository, args.output, args.execution_id)
    elif args.command == "pack":
        result = pack_transition_archive(
            args.run,
            args.archive,
            args.repository,
            args.workflow_run_url,
            args.artifact_name,
            args.uv_version,
        )
    else:
        result = verify_transition_archive(args.archive, extract_to=args.extract_to)
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_dispatch())
