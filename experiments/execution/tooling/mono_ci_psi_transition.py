"""Execute one isolated, DEVELOPMENT-only Method P A0.3 to A0.4 transition."""

from __future__ import annotations

import argparse
import base64
import importlib.metadata
import importlib.util
import json
import os
import platform
import re
import shutil
import socket
import subprocess  # nosec B404 - fixed interpreter and generated runtime script
import sys
import tempfile
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

import experiments.execution.tooling.p_policy_source_v3 as p_policy_source_v3
from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError, ProtocolError
from experiments.execution.tooling.hashing import (
    bundle_sha256,
    canonical_json_bytes,
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
from experiments.execution.tooling.mono_ci_psi_coverage import (
    _REQUIREMENT_CAPABILITY_MAPPINGS,
    _manifest_requires_evaluator,
    assess_adaptation_necessity,
    verify_inspection_coverage,
)
from experiments.execution.tooling.mono_ci_psi_evidence import (
    EVALUATOR_CONFIGS,
    EVALUATOR_IDS,
    TEST_ONLY_VERIFIER_ID,
    TestOnlyEvidenceTrustContext,
    adapt_evaluator_evidence,
    adapt_legacy_evaluator_evidence,
    build_inspection_scope_artifact,
    build_legacy_inspection_scope_artifact,
    build_source_inventory_fact_ledger,
    create_test_only_sidecar,
    evaluator_source_artifacts,
    run_fresh_evaluator,
)
from experiments.execution.tooling.p_adaptation import verify_v3_p_bundle
from experiments.execution.tooling.p_adaptation_evidence import verify_adaptation_evidence
from experiments.execution.tooling.p_candidate import candidate_sha256
from experiments.execution.tooling.p_input_export_v2 import (
    STRUCTURAL_SOURCE_PATH,
    _project_structural_manifest,
)
from experiments.execution.tooling.p_policy_source_v3 import (
    METHOD_INPUT_MANIFEST,
    package_policy_source_v3,
    verify_method_bundle_v3,
    verify_policy_source_bundle_v3,
)
from experiments.execution.tooling.p_semantic import pair_proof_subject

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BEFORE_COMMIT = "26a9bb667da7d0938e38aca15d2bf29fd1de4829"
AFTER_COMMIT = "d3101c0d3aa9b7b709253b6ec7518416f05f65b9"
BEFORE_REPOSITORY_TREE = "7b951421395f532ca403dab09d76902ff08a807d"
AFTER_REPOSITORY_TREE = "2b436e0aaf09403ea516d73d20a466a122f86592"
BEFORE_APP_TREE = "b147b8961ea9e76c966663d4832e4c303581151a"
AFTER_APP_TREE = "007196f68652bc13f6798805793ffdfae96f95f7"
BEFORE_STATE = "A0_3_GOVERNED_MODULE_GRAPH"
AFTER_STATE = "A0_4_REPORT_QUERY_PORT"
STATE_MANIFESTS_PATH = "provenance/transition-state-manifests.json"
TRANSITION_SCHEMA_V1 = "mono_ci_psi_transition_run_v1.schema.json"
TRANSITION_SCHEMA_V2 = "mono_ci_psi_transition_run_v2.schema.json"
TRANSITION_SCHEMA_V3 = "mono_ci_psi_transition_run_v3.schema.json"
TRANSITION_SCHEMA_V4 = "mono_ci_psi_transition_run_v4.schema.json"
TRANSITION_SCHEMA_V5 = "mono_ci_psi_transition_run_v5.schema.json"
TRANSITION_SCHEMA_V6 = "mono_ci_psi_transition_run_v6.schema.json"
INSPECTION_COVERAGE_SCHEMA = "mono_ci_psi_inspection_coverage_v1.schema.json"
ADAPTATION_NECESSITY_SCHEMA_V1 = "mono_ci_psi_adaptation_necessity_v1.schema.json"
ADAPTATION_NECESSITY_SCHEMA_V2 = "mono_ci_psi_adaptation_necessity_v2.schema.json"
ADAPTATION_NECESSITY_SCHEMA_V3 = "mono_ci_psi_adaptation_necessity_v3.schema.json"
TRANSITION_RUN_SCHEMA_VERSION = "MONO_CI_PSI_TRANSITION_RUN_V2"
TRANSITION_UNIT_OF_ANALYSIS = "ONE_A0_3_TO_A0_4_ARCHITECTURE_TRANSITION"
ADAPTATION_NECESSITY_SCHEMA_VERSION = "MONO_CI_PSI_ADAPTATION_NECESSITY_V2"
TRANSITION_RUN_EXTENSION_BUILDER = None
A05_EXPERIMENT_EVIDENCE_SCHEMA = "mono_ci_psi_a05_experiment_evidence_v1.schema.json"
RUN_ID_PATTERN = re.compile(r"^DEV_PSI_TRANSITION_[A-Za-z0-9_-]{1,48}$")
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
ISOLATED_METHOD_IMAGE = (
    "python:3.12.15-slim-bookworm@sha256:"
    "6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70"
)
ISOLATED_METHOD_PLATFORM = "linux/amd64"
ISOLATED_METHOD_PYTHON = "/usr/local/bin/python"
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
    "mono_ci_psi_evidence.py",
    "mono_ci_psi_a05_positive_add.py",
)
RUNTIME_SCHEMAS = (
    "applicability_ruleset_v1.schema.json",
    "architecture_policy_snapshot_v1_1.schema.json",
    "architecture_policy_snapshot_v1_2.schema.json",
    "evaluator_evidence.schema.json",
    "method_input_v2.schema.json",
    "method_input_v3_candidate.schema.json",
    "mono_ci_psi_positive_add_profile_v1.schema.json",
    "mono_ci_psi_positive_add_c2_profile_v1.schema.json",
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
import hashlib
import sys
from pathlib import Path

runtime_root = Path(__file__).resolve().parent
sys.path.insert(0, str(runtime_root))
sys.path.insert(0, str(runtime_root / "vendor"))
from experiments.execution.tooling.p_adaptation import (
    run_adaptation,
    verify_v3_p_bundle,
)
from experiments.execution.tooling.mono_ci_psi_evidence import (
    TestOnlyEvidenceTrustContext,
    build_source_inventory_fact_ledger,
)

bundle_path = Path(sys.argv[1]).resolve(strict=True)
sidecar_path = Path(sys.argv[2]).resolve(strict=True)
key_path = Path(sys.argv[3]).resolve(strict=True)
result_path = Path(sys.argv[4]).resolve()
ledger, ledger_summary = build_source_inventory_fact_ledger(bundle_path)
trust_context = TestOnlyEvidenceTrustContext(key_path.read_bytes())
capabilities = json.loads((bundle_path / "fitness/evaluator-capabilities.json").read_text())
positive_add_input = isinstance(capabilities, dict) and any(
    key in capabilities
    for key in ("positive_add_test_only_profile_v1", "positive_add_test_only_profile_v2")
)
if positive_add_input:
    from experiments.execution.tooling.mono_ci_psi_a05_positive_add import (
        build_verified_bundle,
    )
    verified, positive_context = build_verified_bundle(bundle_path, key_path.read_bytes())
    ledger_summary = positive_context.ledger_summary
else:
    verified = verify_v3_p_bundle(
        bundle_path, evidence_ledger=ledger, trust_context=trust_context
    )
sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
result = run_adaptation(verified, evidence_context=sidecar)
payload = {
    "result_contract_version": "MONO_CI_PSI_METHOD_RESULT_V2",
    "method_version": "P_GOVERNED_ADAPTATION_DEVELOPMENT_V1",
    "input_bundle_sha256": verified.manifest["bundle_sha256"],
    "adaptation_evidence_sidecar_sha256": hashlib.sha256(sidecar_path.read_bytes()).hexdigest(),
    "evidence_ledger": ledger_summary,
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


def run_transition(
    repository: Path,
    output_root: Path,
    execution_id: str,
    *,
    isolation_backend: str | None = None,
    preserve_partial_evidence: bool = False,
    sandbox_preflight_id: str | None = None,
    positive_add_profile_path: Path | None = None,
) -> dict[str, Any]:
    """Build source-pinned inputs and execute the existing P DEVELOPMENT API once."""
    repo = repository.resolve(strict=True)
    if RUN_ID_PATTERN.fullmatch(execution_id) is None:
        raise ProtocolError("MONO_CI_PSI_TRANSITION_EXECUTION_ID_INVALID")
    root = output_root.expanduser().absolute()
    if root.exists() or root.is_symlink() or root.is_relative_to(repo):
        raise ProtocolError("MONO_CI_PSI_TRANSITION_OUTPUT_MUST_BE_NEW_AND_EXTERNAL")
    root.mkdir(parents=True)
    started_at = datetime.now(UTC).isoformat()
    phases = {
        "source_identity": "NOT_EXECUTED",
        "baseline_identity": "NOT_EXECUTED",
        "b0_evaluator_matrix": "NOT_EXECUTED",
        "method_input_bundle": "NOT_EXECUTED",
        "method_execution": "NOT_OBSERVED",
        "candidate_validation": "NOT_EXECUTED",
        "complete_transition_verification": "NOT_EXECUTED",
    }
    try:
        if isolation_backend == "docker":
            if not isinstance(sandbox_preflight_id, str) or not SHA256_PATTERN.fullmatch(
                sandbox_preflight_id
            ):
                raise ProtocolError("MONO_CI_PSI_TRANSITION_DOCKER_PREFLIGHT_BINDING_MISSING")
            _write_new_file(
                root / "provenance/sandbox-preflight-binding.json",
                pretty_json_bytes(
                    {
                        "schema_version": "MONO_CI_PSI_DOCKER_PREFLIGHT_BINDING_V1",
                        "classification": "DEVELOPMENT_SANDBOX_CAPABILITY_PREFLIGHT",
                        "preflight_id": sandbox_preflight_id,
                    }
                ),
            )
        phases["source_identity"] = "IN_PROGRESS"
        _verify_transition_sources(repo)
        phases["source_identity"] = "COMPLETED"
        phases["baseline_identity"] = "IN_PROGRESS"
        baseline = verify_execution_proposal(repo)
        phases["baseline_identity"] = "COMPLETED"
        psi = root / "PSI"
        psi.mkdir()
        phases["b0_evaluator_matrix"] = "IN_PROGRESS"
        evaluator_runs, evaluator_bindings, evaluator_artifacts, coverage_assessments = (
            _collect_evaluator_matrix(repo, root)
        )
        phases["b0_evaluator_matrix"] = "COMPLETED"
        proposal_path = repo / PROPOSAL_RELATIVE / BASELINE_NAME
        proposal_bytes = proposal_path.read_bytes()
        _write_new_file(root / "provenance/reconstructed-b0-proposal.json", proposal_bytes)
        orchestrator_bytes = Path(__file__).read_bytes()
        _write_new_file(root / "provenance/transition-runner.py", orchestrator_bytes)

        policy_root = psi / "policy-source"
        policy_root.parent.mkdir(parents=True, exist_ok=True)
        positive_add = positive_add_profile_path is not None
        if positive_add:
            from experiments.execution.tooling.mono_ci_psi_a05_positive_add import (
                create_policy_source as create_positive_policy_source,
            )

            profile_path = positive_add_profile_path.expanduser().resolve(strict=True)
            _write_new_file(
                root / "provenance/positive-add-study-profile.json",
                profile_path.read_bytes(),
            )
            profile = json.loads(profile_path.read_bytes())
            policy = create_positive_policy_source(
                repo,
                psi / "policy-working",
                policy_root,
                evaluation_as_of=str(profile["evaluation_as_of"]),
                before_sha=BEFORE_COMMIT,
                after_sha=AFTER_COMMIT,
                obligation_catalog_sha256=sha256_file(
                    repo / "fitness/catalog/architectural-obligations.yaml"
                ),
                policy_source_revision=str(profile["profile_id"]),
            )
        else:
            policy = package_policy_source_v3(
                repo / "experiments/execution/policy-pilot/v1/source",
                policy_root,
                "POLICY_PILOT_V1_DRAFT_OPEN_SOURCE",
            )
        registry = json.loads((policy_root / "fitness/policy/registry.json").read_text())
        bundle_root = psi / "method-input"
        method_manifest = _export_transition_method_inputs(
            repo, policy_root, bundle_root, str(registry["as_of"])
        )
        _bind_reconstructed_baseline(bundle_root, proposal_bytes, policy, evaluator_bindings)
        if positive_add:
            from experiments.execution.tooling.mono_ci_psi_a05_positive_add import (
                prepare_method_inputs,
            )

            prepare_method_inputs(
                repo,
                root,
                bundle_root,
                root / "provenance/positive-add-study-profile.json",
            )
        source_binding = _source_binding(repo)
        source_binding["state_manifest_path"] = STATE_MANIFESTS_PATH
        _add_state_manifest_sidecar(repo, root, source_binding)
        method_manifest = _reseal_method_bundle(bundle_root)
        verify_method_bundle_v3(bundle_root, expected_method_id="P")

        test_key = os.urandom(32)
        if positive_add:
            from experiments.execution.tooling.mono_ci_psi_a05_positive_add import (
                build_verified_bundle as build_positive_bundle,
            )

            verified_bundle, positive_context = build_positive_bundle(bundle_root, test_key)
            ledger_summary = positive_context.ledger_summary
        else:
            ledger, ledger_summary = build_source_inventory_fact_ledger(bundle_root)
            trust_context = TestOnlyEvidenceTrustContext(test_key)
            verified_bundle = verify_v3_p_bundle(
                bundle_root, evidence_ledger=ledger, trust_context=trust_context
            )
        after_runs = {
            run["evaluator_id"]: run
            for run in evaluator_runs
            if run["architecture_state"] == AFTER_STATE
        }
        representations = {str(row["id"]): row for row in verified_bundle.representations}
        obligations = {str(row["id"]): row for row in verified_bundle.obligations}
        pair_evidence: list[dict[str, Any]] = []
        pair_proofs: list[dict[str, Any]] = []
        adaptation_artifacts: dict[str, bytes] = {}
        for evaluator_id in EVALUATOR_IDS:
            representation_id = evaluator_bindings[evaluator_id]["representation_id"]
            obligation_id = evaluator_id
            representation = representations[representation_id]
            run = after_runs[evaluator_id]
            artifact_refs = _evaluator_artifact_references(
                root, run, evaluator_bindings[evaluator_id], evaluator_artifacts[evaluator_id]
            )
            adaptation_artifacts.update(
                {relative: (root / relative).read_bytes() for relative, _ in artifact_refs}
            )
            evidence = adapt_evaluator_evidence(
                representation=representation,
                obligation_id=obligation_id,
                run=run,
                artifact_refs=[{"path": path, "sha256": digest} for path, digest in artifact_refs],
                coverage_verification=coverage_assessments[(AFTER_STATE, evaluator_id)],
            )
            pair_evidence.append(
                {
                    "representation_id": representation_id,
                    "obligation_id": obligation_id,
                    "evidence": evidence,
                }
            )
            proof_subject = pair_proof_subject(
                representation,
                obligations[obligation_id],
                str(evidence["architecture_source_sha"]),
                evidence,
            )
            proof_bindings = [
                {"source_id": source_id, "sha256": verified_bundle.source_digests[source_id]}
                for source_id in ("ARCH_AFTER", "P_CAPABILITIES", "P_TRACEABILITY")
            ]
            proof_bindings.sort(key=lambda row: row["source_id"])
            pair_proofs.append(
                {
                    "representation_id": representation_id,
                    "obligation_id": obligation_id,
                    "status": "UNDETERMINED",
                    "subject_sha256": sha256_bytes(canonical_json_bytes(proof_subject)),
                    "verifier_id": TEST_ONLY_VERIFIER_ID,
                    "source_bindings": proof_bindings,
                    "evidence_refs": [f"FRESH_A04_{evaluator_id}"],
                    "reason_codes": [
                        "INDEPENDENT_SEMANTIC_ADEQUACY_NOT_ESTABLISHED",
                        "NORMATIVE_MAPPING_UNAPPROVED",
                    ],
                }
            )
        if positive_add:
            from experiments.execution.tooling.mono_ci_psi_a05_positive_add import (
                create_positive_sidecar,
            )

            sidecar = create_positive_sidecar(
                repository=repo,
                run_root=root,
                bundle=verified_bundle,
                evaluator_runs=evaluator_runs,
                evaluator_bindings=evaluator_bindings,
                evaluator_artifacts=evaluator_artifacts,
                key=test_key,
            )
        else:
            sidecar = create_test_only_sidecar(
                bundle=verified_bundle,
                pair_evidence=pair_evidence,
                pair_proofs=pair_proofs,
                artifact_bytes=adaptation_artifacts,
                key=test_key,
            )
        evidence_root = psi / "method-evidence"
        evidence_root.mkdir()
        evidence_path = evidence_root / "adaptation-evidence.json"
        _write_new_file(evidence_path, pretty_json_bytes(sidecar))
        key_path = root / "provenance/test-only-evidence-verifier.key"
        _write_new_file(key_path, test_key)

        runtime_root = psi / "method-runtime"
        runtime_inventory = _build_isolated_runtime(repo, runtime_root)
        _write_new_file(
            root / "provenance/runtime-inventory.json", pretty_json_bytes(runtime_inventory)
        )
        adaptation_path = "experiments/execution/tooling/p_adaptation.py"
        adaptation_digest = _runtime_module_sha256(runtime_inventory, adaptation_path)
        phases["method_input_bundle"] = "COMPLETED"
        raw_root = psi / "raw"
        raw_root.mkdir()
        result_path = raw_root / "method-result.json"
        execution_started = time.perf_counter()
        phases["method_execution"] = "IN_PROGRESS"
        _execute_isolated_method(
            repo,
            runtime_root,
            bundle_root,
            evidence_path,
            key_path,
            psi / "evaluator-observations",
            result_path,
            isolation_backend=isolation_backend or "legacy",
            sandbox_preflight_id=sandbox_preflight_id,
        )
        phases["method_execution"] = "PROCESS_COMPLETED"
        execution_duration_ms = round((time.perf_counter() - execution_started) * 1000, 3)
        result_digest = sha256_file(result_path)
        method_result = json.loads(result_path.read_text(encoding="utf-8"))
        if (
            method_result.get("result_contract_version") != "MONO_CI_PSI_METHOD_RESULT_V2"
            or method_result.get("method_version") != "P_GOVERNED_ADAPTATION_DEVELOPMENT_V1"
        ):
            raise ProtocolError("MONO_CI_PSI_TRANSITION_METHOD_IDENTITY_MISMATCH")
        decision = _governance_decision(method_result)
        _validate_method_result_v2(method_result)
        phases["method_execution"] = "OBSERVED"
        phases["candidate_validation"] = "IN_PROGRESS"
        adaptation_assessment = _build_adaptation_necessity_report(
            repo=repo,
            run_root=root,
            execution_id=execution_id,
            baseline={
                "configuration_id": baseline["baseline_id"],
                "configuration_sha256": baseline["baseline_configuration_sha256"],
                "identity_status": baseline["identity_status"],
                "approval_status": baseline["approval_status"],
            },
            evaluator_runs=evaluator_runs,
            coverage_assessments=coverage_assessments,
            method_result=method_result,
            method_result_sha256=result_digest,
            state_manifest_sidecar=json.loads(
                (root / STATE_MANIFESTS_PATH).read_text(encoding="utf-8")
            ),
        )
        adaptation_assessment_path = root / "diagnostics/adaptation-necessity-assessment.json"
        _write_new_file(adaptation_assessment_path, pretty_json_bytes(adaptation_assessment))
        record = {
            "schema_version": (
                "MONO_CI_PSI_TRANSITION_RUN_V6"
                if positive_add
                and profile.get("profile_id") == "MONO_CI_A05_POSITIVE_ADD_C2_TEST_ONLY_PROFILE_V1"
                else "MONO_CI_PSI_TRANSITION_RUN_V5"
                if positive_add
                else TRANSITION_RUN_SCHEMA_VERSION
            ),
            "execution_id": execution_id,
            "source_revision_sha": _git_text(repo, "rev-parse", "HEAD").strip(),
            "study_id": (
                "MONO_CI_A05_POSITIVE_ADD_C2_TEST_ONLY_V1"
                if positive_add
                and profile.get("profile_id") == "MONO_CI_A05_POSITIVE_ADD_C2_TEST_ONLY_PROFILE_V1"
                else "MONO_CI_A05_POSITIVE_ADD_TEST_ONLY_V1"
                if positive_add
                else "MONO_CI_B0_PSI_DEVELOPMENT_TECHNICAL_VALIDATION"
            ),
            "mode": "DEVELOPMENT_METHOD_EXECUTION_ONLY",
            "unit_of_analysis": TRANSITION_UNIT_OF_ANALYSIS,
            "study_readiness": "NO_GO",
            "measurement_status": "NOT_EXECUTED",
            "p_algorithm_status": "NOT_READY",
            "g1": "INCOMPLETE",
            "g4": "NOT_AUTHORIZED",
            "reference_gate": "NOT_READY",
            "method_implementation": {
                "identity": method_result["method_version"],
                "source_path": adaptation_path,
                "sha256": adaptation_digest,
            },
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
                "authority_status": (
                    "TEST_ONLY_AUTHOR_DECLARED_SCOPED_PROFILE"
                    if positive_add
                    else "DRAFT_OPEN_UNAPPROVED"
                ),
            },
            "method_input": {
                "path": "PSI/method-input",
                "bundle_sha256": method_manifest["bundle_sha256"],
                "common_snapshot_sha256": method_manifest["common_snapshot_sha256"],
                "baseline_proposal_sha256": baseline["baseline_configuration_sha256"],
                "structural_manifest_path": f"architecture/states/{AFTER_STATE}.yaml",
            },
            "adaptation_evidence": {
                "path": "PSI/method-evidence/adaptation-evidence.json",
                "sha256": sha256_file(evidence_path),
                "verifier_id": TEST_ONLY_VERIFIER_ID,
                "trust_scope": "TEST_ONLY",
                "key_path": "provenance/test-only-evidence-verifier.key",
                "key_sha256": sha256_file(key_path),
            },
            "runtime": {
                "path": "PSI/method-runtime",
                "inventory_sha256": runtime_inventory["inventory_sha256"],
                "isolation": (
                    "PYTHON_ISOLATED_MODE; NO_NETWORK; SOURCE_REPOSITORIES_DENIED; "
                    "OTHER_SOURCE_OBSERVATIONS_DENIED"
                ),
            },
            "execution_engine": {
                "path": "provenance/transition-runner.py",
                "sha256": sha256_bytes(orchestrator_bytes),
            },
            "evaluator_observations": [_evaluator_run_record(run, root) for run in evaluator_runs],
            "evidence_ledger": ledger_summary,
            "psi": {
                "status": "DEVELOPMENT_METHOD_EXECUTED",
                "decision": decision,
                "raw_result_path": "PSI/raw/method-result.json",
                "raw_result_sha256": result_digest,
                "operation_emitted": True,
                "governance_decision_emitted": True,
                "prediction_emitted": method_result.get("prediction_v1") is not None,
                "scoring": "NOT_EXECUTED",
                "execution_duration_ms": execution_duration_ms,
            },
            "other_arms_or_case_outputs_used": False,
            "metrics": "NOT_MEASURED",
            "output_checksums": {
                "PSI/raw/method-result.json": result_digest,
                f"PSI/method-input/{METHOD_INPUT_MANIFEST}": sha256_file(
                    bundle_root / METHOD_INPUT_MANIFEST
                ),
                STATE_MANIFESTS_PATH: sha256_file(root / STATE_MANIFESTS_PATH),
                "PSI/method-evidence/adaptation-evidence.json": sha256_file(evidence_path),
                **{
                    _coverage_assessment_path(state, evaluator_id).as_posix(): sha256_file(
                        root / _coverage_assessment_path(state, evaluator_id)
                    )
                    for state in (BEFORE_STATE, AFTER_STATE)
                    for evaluator_id in EVALUATOR_IDS
                },
                "diagnostics/adaptation-necessity-assessment.json": sha256_file(
                    adaptation_assessment_path
                ),
            },
        }
        if positive_add:
            record["positive_add_profile"] = {
                "profile_id": str(profile["profile_id"]),
                "path": "provenance/positive-add-study-profile.json",
                "sha256": sha256_file(root / "provenance/positive-add-study-profile.json"),
                "classification": "TEST_ONLY_AUTHOR_DECLARED_SCOPED_INPUT",
                "selected_obligation_id": "AC_DATA_OWNERSHIP",
            }
            if profile.get("profile_id") == "MONO_CI_A05_POSITIVE_ADD_C2_TEST_ONLY_PROFILE_V1":
                record["positive_add_profile"]["selected_obligation_ids"] = [
                    "AC_DATA_OWNERSHIP",
                    "AC_MODULE_GRAPH",
                    "AC_PUBLIC_API",
                ]
            record["output_checksums"]["provenance/positive-add-study-profile.json"] = record[
                "positive_add_profile"
            ]["sha256"]
            positive_input_path = root / "diagnostics/positive-add-input-evaluator.json"
            record["output_checksums"]["diagnostics/positive-add-input-evaluator.json"] = (
                sha256_file(positive_input_path)
            )
        if TRANSITION_RUN_EXTENSION_BUILDER is not None:
            extension = TRANSITION_RUN_EXTENSION_BUILDER(repo, root, record)
            if (
                not isinstance(extension, dict)
                or extension.get("path") != "diagnostics/a05-experiment-evidence.json"
                or not isinstance(extension.get("sha256"), str)
            ):
                raise ProtocolError("MONO_CI_PSI_TRANSITION_EXTENSION_INVALID")
            record["a05_extension"] = extension
            record["output_checksums"][extension["path"]] = extension["sha256"]
        phases["candidate_validation"] = "COMPLETED"
        _write_new_file(root / "development_run.json", pretty_json_bytes(record))
        _seal_run(root)
        verify_transition_run(root)
        phases["complete_transition_verification"] = "PASS"
        return {
            "execution_id": execution_id,
            "study_readiness": record["study_readiness"],
            "measurement_status": record["measurement_status"],
            "psi_status": record["psi"]["status"],
            "psi_decision": record["psi"]["decision"],
            "method_input_bundle_sha256": method_manifest["bundle_sha256"],
            "raw_result_sha256": result_digest,
            "adaptation_assessment_sha256": sha256_file(adaptation_assessment_path),
            "result_path": str(root / "development_run.json"),
            "inventory_sha256": sha256_file(root / "SHA256SUMS"),
        }
    except Exception as error:
        if preserve_partial_evidence:
            _write_partial_execution_status(
                root=root,
                execution_id=execution_id,
                started_at=started_at,
                phases=phases,
                error=error,
                sandbox_preflight_id=sandbox_preflight_id,
            )
        else:
            shutil.rmtree(root, ignore_errors=True)
        raise


def _write_partial_execution_status(
    *,
    root: Path,
    execution_id: str,
    started_at: str,
    phases: dict[str, str],
    error: Exception,
    sandbox_preflight_id: str | None,
) -> None:
    """Record authentic completed phases and artifacts for a failed DEVELOPMENT run."""
    artifacts = [
        {
            "path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink() and path.name != "partial-execution.json"
    ]
    process_record = None
    sandbox_record = root / "PSI/raw/sandbox-execution.json"
    if sandbox_record.is_file() and not sandbox_record.is_symlink():
        try:
            sandbox = json.loads(sandbox_record.read_text(encoding="utf-8"))
            process_record = {
                "status": sandbox.get("status", "NOT_OBSERVED"),
                "exit_code": sandbox.get("exit_code"),
                "execution_duration_ms": sandbox.get("execution_duration_ms"),
                "record_path": "PSI/raw/sandbox-execution.json",
                "record_sha256": sha256_file(sandbox_record),
                "stdout_path": "PSI/raw/method-process.stdout.bin"
                if (root / "PSI/raw/method-process.stdout.bin").is_file()
                else None,
                "stderr_path": "PSI/raw/method-process.stderr.bin"
                if (root / "PSI/raw/method-process.stderr.bin").is_file()
                else None,
            }
        except (OSError, json.JSONDecodeError):
            process_record = {"status": "RECORD_UNREADABLE"}
    method_observed = phases.get("method_execution") == "OBSERVED"
    partial = {
        "schema_version": "MONO_CI_PSI_PARTIAL_TRANSITION_V1",
        "classification": "PARTIAL_EXECUTION_EVIDENCE",
        "execution_id": execution_id,
        "started_at_utc": started_at,
        "ended_at_utc": datetime.now(UTC).isoformat(),
        "source_identities": {
            "verification_status": "VERIFIED"
            if phases.get("source_identity") == "COMPLETED"
            else "NOT_VERIFIED",
            "expected": {
                "before_commit_sha": BEFORE_COMMIT,
                "before_repository_tree_sha": BEFORE_REPOSITORY_TREE,
                "before_application_tree_sha": BEFORE_APP_TREE,
                "after_commit_sha": AFTER_COMMIT,
                "after_repository_tree_sha": AFTER_REPOSITORY_TREE,
                "after_application_tree_sha": AFTER_APP_TREE,
            },
            "observed": {
                "before_commit_sha": BEFORE_COMMIT
                if phases.get("source_identity") == "COMPLETED"
                else None,
                "before_repository_tree_sha": BEFORE_REPOSITORY_TREE
                if phases.get("source_identity") == "COMPLETED"
                else None,
                "before_application_tree_sha": BEFORE_APP_TREE
                if phases.get("source_identity") == "COMPLETED"
                else None,
                "after_commit_sha": AFTER_COMMIT
                if phases.get("source_identity") == "COMPLETED"
                else None,
                "after_repository_tree_sha": AFTER_REPOSITORY_TREE
                if phases.get("source_identity") == "COMPLETED"
                else None,
                "after_application_tree_sha": AFTER_APP_TREE
                if phases.get("source_identity") == "COMPLETED"
                else None,
            },
        },
        "sandbox_preflight_id": sandbox_preflight_id,
        "phase_status": dict(phases),
        "method_subprocess": process_record,
        "error": {"type": type(error).__name__, "message": str(error)[:2000]},
        "available_artifacts": artifacts,
        "scientific_status": {
            "method_decision": "OBSERVED" if method_observed else "NOT_OBSERVED",
            "operation_plan": "OBSERVED" if method_observed else "NOT_OBSERVED",
            "candidate": "NOT_OBSERVED",
            "official_measurement_status": "NOT_EXECUTED",
            "g1": "INCOMPLETE",
            "g4": "NOT_AUTHORIZED",
        },
    }
    method_path = root / "PSI/raw/method-result.json"
    if method_path.is_file() and not method_path.is_symlink():
        try:
            method = json.loads(method_path.read_text(encoding="utf-8"))
            if not isinstance(method, dict):
                raise ValueError("Method output must be a JSON object")
            governance = method.get("governance", {})
            plan = method.get("operation_plan", {})
            governance = governance if isinstance(governance, dict) else {}
            plan = plan if isinstance(plan, dict) else {}
            candidate = method.get("candidate")
            partial["method_observation"] = {
                "raw_result_path": "PSI/raw/method-result.json",
                "raw_result_sha256": sha256_file(method_path),
                "governance_decision": governance.get("result"),
                "governance_reason_codes": governance.get("reason_codes", []),
                "operations": plan.get("operations", []),
                "operation_hold_reasons": plan.get("hold_reasons", []),
                "candidate_state": "NOT_MATERIALIZED"
                if candidate is None
                else "MATERIALIZED_UNAPPLIED",
                "candidate_sha256": method.get("candidate_sha256"),
                "parse_status": "JSON_READBACK_ONLY",
            }
            partial["scientific_status"]["candidate"] = (
                "NOT_PRODUCED" if candidate is None else "OBSERVED"
            )
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            partial["method_observation"] = {
                "raw_result_path": "PSI/raw/method-result.json",
                "raw_result_sha256": sha256_file(method_path),
                "parse_status": "UNREADABLE",
            }
    _write_new_file(root / "partial-execution.json", pretty_json_bytes(partial))


def verify_transition_run(run_root: Path, *, repository: Path | None = None) -> dict[str, Any]:
    """Verify the run, exact P input bundle, raw result, and complete file inventory."""
    root = run_root.resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_RUN_ROOT_INVALID")
    record = json.loads((root / "development_run.json").read_text(encoding="utf-8"))
    if record.get("schema_version") in {
        "MONO_CI_PSI_TRANSITION_RUN_V3",
        "MONO_CI_PSI_TRANSITION_RUN_V4",
        "MONO_CI_PSI_TRANSITION_RUN_V5",
        "MONO_CI_PSI_TRANSITION_RUN_V6",
    } and (
        AFTER_STATE != "A0_5_MODULE_DATA_OWNERSHIP"
        or (repository is not None and REPOSITORY_ROOT.resolve() != repository.resolve())
    ):
        from experiments.execution.tooling.mono_ci_psi_a05 import a05_transition_context

        after_commit = record.get("transition", {}).get("after_commit_sha")
        with a05_transition_context(
            repository or REPOSITORY_ROOT,
            extension_builder=None,
            after_commit=after_commit,
            run_schema_version=record["schema_version"],
            extension_schema=(
                "mono_ci_psi_a05_experiment_evidence_v1.schema.json"
                if record["schema_version"] == "MONO_CI_PSI_TRANSITION_RUN_V3"
                else "mono_ci_psi_a05_experiment_evidence_v2.schema.json"
            ),
        ):
            return verify_transition_run(root, repository=repository or REPOSITORY_ROOT)
    schema_name = {
        "MONO_CI_PSI_TRANSITION_RUN_V1": TRANSITION_SCHEMA_V1,
        "MONO_CI_PSI_TRANSITION_RUN_V2": TRANSITION_SCHEMA_V2,
        "MONO_CI_PSI_TRANSITION_RUN_V3": TRANSITION_SCHEMA_V3,
        "MONO_CI_PSI_TRANSITION_RUN_V4": TRANSITION_SCHEMA_V4,
        "MONO_CI_PSI_TRANSITION_RUN_V5": TRANSITION_SCHEMA_V5,
        "MONO_CI_PSI_TRANSITION_RUN_V6": TRANSITION_SCHEMA_V6,
    }.get(record.get("schema_version"))
    if schema_name is None:
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_SCHEMA_UNSUPPORTED")
    validate_payload(schema_name, record)
    if record["study_readiness"] != "NO_GO" or record["measurement_status"] != "NOT_EXECUTED":
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_OFFICIAL_GATE_PROMOTED")
    if record["p_algorithm_status"] != "NOT_READY" or record["g1"] != "INCOMPLETE":
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_METHOD_GATE_PROMOTED")
    raw_path = root / record["psi"]["raw_result_path"]
    if sha256_file(raw_path) != record["psi"]["raw_result_sha256"]:
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_RAW_RESULT_DIGEST_MISMATCH")
    bundle_root = root / record["method_input"]["path"]
    manifest = verify_method_bundle_v3(bundle_root, expected_method_id="P")
    if (
        manifest["bundle_sha256"] != record["method_input"]["bundle_sha256"]
        or manifest["common_snapshot_sha256"] != record["method_input"]["common_snapshot_sha256"]
        or manifest["policy_bundle_sha256"] != record["policy_source"]["bundle_sha256"]
    ):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_METHOD_INPUT_BINDING_MISMATCH")
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    if raw.get("input_bundle_sha256") != manifest["bundle_sha256"]:
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_RAW_INPUT_BINDING_MISMATCH")
    if record["psi"]["decision"] != _governance_decision(raw):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_DECISION_MISMATCH")
    if record["schema_version"] == "MONO_CI_PSI_TRANSITION_RUN_V1":
        if raw.get("prediction_v1") is not None or record["psi"]["decision"] not in {
            "HOLD",
            "REJECT",
        }:
            raise ContractValidationError("MONO_CI_PSI_TRANSITION_UNEXPECTED_METHOD_DECISION")
    else:
        if raw.get("result_contract_version") != "MONO_CI_PSI_METHOD_RESULT_V2":
            raise ContractValidationError("MONO_CI_PSI_TRANSITION_RESULT_SCHEMA_MISMATCH")
        _validate_method_result_v2(raw)
        if raw.get("evidence_trust_scope") != "TEST_ONLY":
            raise ContractValidationError("MONO_CI_PSI_TRANSITION_EVIDENCE_TRUST_SCOPE_MISMATCH")
        _verify_evidence_backed_run(root, record, bundle_root, manifest, raw)
    for relative, digest in record["output_checksums"].items():
        path = root / relative
        if not path.is_file() or sha256_file(path) != digest:
            raise ContractValidationError("MONO_CI_PSI_TRANSITION_OUTPUT_CHECKSUM_MISMATCH")
    if record["schema_version"] in {
        "MONO_CI_PSI_TRANSITION_RUN_V2",
        "MONO_CI_PSI_TRANSITION_RUN_V3",
        "MONO_CI_PSI_TRANSITION_RUN_V4",
        "MONO_CI_PSI_TRANSITION_RUN_V5",
        "MONO_CI_PSI_TRANSITION_RUN_V6",
    }:
        _verify_adaptation_necessity_report(root, record, raw)
    if record["schema_version"] == "MONO_CI_PSI_TRANSITION_RUN_V3":
        _verify_a05_experiment_extension(root, record)
    elif record["schema_version"] == "MONO_CI_PSI_TRANSITION_RUN_V4":
        _verify_a05_experiment_extension_v2(root, record, repository or REPOSITORY_ROOT)
    elif record["schema_version"] in {
        "MONO_CI_PSI_TRANSITION_RUN_V5",
        "MONO_CI_PSI_TRANSITION_RUN_V6",
    }:
        _verify_a05_experiment_extension_v2(root, record, repository or REPOSITORY_ROOT)
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
    _verify_transition_state_sidecar(root, record["transition"])
    sidecar = json.loads(
        (root / record["transition"]["state_manifest_path"]).read_text(encoding="utf-8")
    )
    after_manifest = next(row for row in sidecar["manifests"] if row["state"] == "after")
    expected_projection = _project_structural_manifest(yaml.safe_load(after_manifest["content"]))
    structural_observation = json.loads(
        (bundle_root / STRUCTURAL_SOURCE_PATH).read_text(encoding="utf-8")
    )
    if (
        structural_observation.get("source_state") != "after"
        or structural_observation.get("source_commit_sha")
        != record["transition"]["after_commit_sha"]
        or structural_observation.get("source_tree_sha")
        != record["transition"]["after_application_tree_sha"]
        or structural_observation.get("target_structural_manifest") != expected_projection
    ):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_STRUCTURAL_PROJECTION_MISMATCH")
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
    implementation = record["method_implementation"]
    if (
        implementation["identity"] != raw.get("method_version")
        or implementation["source_path"] != "experiments/execution/tooling/p_adaptation.py"
        or implementation["sha256"]
        != _runtime_module_sha256(runtime_inventory, implementation["source_path"])
    ):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_METHOD_IDENTITY_MISMATCH")
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
    if record["schema_version"] == "MONO_CI_PSI_TRANSITION_RUN_V5":
        selected = policy_registry.get("policies", [])
        if (
            policy_registry.get("closure") != "CLAIMED_CLOSED"
            or len(selected) != 1
            or selected[0].get("obligation_ids") != ["AC_DATA_OWNERSHIP"]
            or selected[0].get("normative_status") != "APPROVED"
            or record["policy_source"].get("authority_status")
            != "TEST_ONLY_AUTHOR_DECLARED_SCOPED_PROFILE"
        ):
            raise ContractValidationError("MONO_CI_PSI_TRANSITION_TEST_ONLY_POLICY_SCOPE_INVALID")
        profile_path = root / record["positive_add_profile"]["path"]
        if (
            not profile_path.is_file()
            or sha256_file(profile_path) != record["positive_add_profile"]["sha256"]
        ):
            raise ContractValidationError(
                "MONO_CI_PSI_TRANSITION_POSITIVE_PROFILE_BINDING_MISMATCH"
            )
    elif record["schema_version"] == "MONO_CI_PSI_TRANSITION_RUN_V6":
        selected = policy_registry.get("policies", [])
        profile_path = root / record["positive_add_profile"]["path"]
        profile = (
            json.loads(profile_path.read_text(encoding="utf-8")) if profile_path.is_file() else {}
        )
        expected_obligations = {"AC_DATA_OWNERSHIP", "AC_MODULE_GRAPH", "AC_PUBLIC_API"}
        observed_obligations = {
            str(obligation_id)
            for row in selected
            if isinstance(row, dict)
            for obligation_id in row.get("obligation_ids", [])
        }
        if (
            policy_registry.get("closure") != "CLAIMED_CLOSED"
            or len(selected) != 3
            or observed_obligations != expected_obligations
            or any(row.get("normative_status") != "APPROVED" for row in selected)
            or record["policy_source"].get("authority_status")
            != "TEST_ONLY_AUTHOR_DECLARED_SCOPED_PROFILE"
            or profile.get("profile_id") != record["positive_add_profile"].get("profile_id")
            or record["positive_add_profile"].get("selected_obligation_ids")
            != sorted(expected_obligations)
            or not profile_path.is_file()
            or sha256_file(profile_path) != record["positive_add_profile"].get("sha256")
        ):
            raise ContractValidationError(
                "MONO_CI_PSI_TRANSITION_TEST_ONLY_C2_POLICY_SCOPE_INVALID"
            )
    elif policy_registry.get("closure") != "OPEN" or any(
        row.get("normative_status") != "DRAFT"
        for row in policy_registry.get("policies", [])
        if isinstance(row, dict)
    ):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_POLICY_AUTHORITY_CHANGED")
    sidecar = (root / "development_run.json.sha256").read_text(encoding="utf-8").strip()
    if sidecar != f"{sha256_file(root / 'development_run.json')}  development_run.json":
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_RUN_SEAL_MISMATCH")
    if _read_checksums(root / "SHA256SUMS") != _directory_checksums(root, {"SHA256SUMS"}):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_RUN_INVENTORY_MISMATCH")
    return record


def _verify_a05_experiment_extension(run_root: Path, record: dict[str, Any]) -> None:
    """Bind the A0.5 ownership probe and independent adequacy diagnostic to raw evidence."""
    extension_ref = record.get("a05_extension")
    if not isinstance(extension_ref, dict) or set(extension_ref) != {"path", "sha256"}:
        raise ContractValidationError("MONO_CI_PSI_A05_EXTENSION_BINDING_INVALID")
    extension_path = run_root / extension_ref["path"]
    if (
        extension_ref["path"] != "diagnostics/a05-experiment-evidence.json"
        or not extension_path.is_file()
        or sha256_file(extension_path) != extension_ref["sha256"]
    ):
        raise ContractValidationError("MONO_CI_PSI_A05_EXTENSION_DIGEST_MISMATCH")
    try:
        extension = json.loads(extension_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ContractValidationError("MONO_CI_PSI_A05_EXTENSION_INVALID") from error
    validate_payload(A05_EXPERIMENT_EVIDENCE_SCHEMA, extension)
    transition = extension["transition"]
    if (
        extension["execution_id"] != record["execution_id"]
        or transition["before_state"] != record["transition"]["before_state"]
        or transition["after_state"] != record["transition"]["after_state"]
        or transition["before_commit_sha"] != record["transition"]["before_commit_sha"]
        or transition["after_commit_sha"] != record["transition"]["after_commit_sha"]
        or transition["probe_parent_commit_sha"] != record["transition"]["after_commit_sha"]
        or extension["baseline"]["configuration_sha256"]
        != record["baseline"]["configuration_sha256"]
        or extension["scientific_boundary"]["method_decision"] != record["psi"]["decision"]
        or extension["scientific_boundary"]["operation_plan"]
        != json.loads((run_root / record["psi"]["raw_result_path"]).read_text())["operation_plan"][
            "operations"
        ]
    ):
        raise ContractValidationError("MONO_CI_PSI_A05_EXTENSION_RUN_BINDING_MISMATCH")
    positive = extension["positive_condition"]["evaluator"]
    negative = extension["negative_condition"]["evaluators"]
    negative_by_id = {row["evaluator_id"]: row for row in negative}
    if set(negative_by_id) != {"AC_PUBLIC_API", "AC_MODULE_GRAPH", "AC_DATA_OWNERSHIP"}:
        raise ContractValidationError("MONO_CI_PSI_A05_PROBE_EVALUATOR_SET_INVALID")
    if (
        positive["evaluator_id"] != "AC_DATA_OWNERSHIP"
        or positive["compliance"] != "COMPLIANT"
        or negative_by_id["AC_PUBLIC_API"]["compliance"] != "COMPLIANT"
        or negative_by_id["AC_MODULE_GRAPH"]["compliance"] != "COMPLIANT"
        or negative_by_id["AC_DATA_OWNERSHIP"]["compliance"] != "NON_COMPLIANT"
        or "FOREIGN_TABLE_ACCESS" not in negative_by_id["AC_DATA_OWNERSHIP"]["finding_codes"]
        or extension["adequacy_diagnostic"]["old_controls_detected_probe"] is not False
        or extension["adequacy_diagnostic"]["ownership_evaluator_detected_probe"] is not True
    ):
        raise ContractValidationError("MONO_CI_PSI_A05_PROBE_RESULT_MISMATCH")
    for row in [positive, *negative]:
        output_path = run_root / row["output_path"]
        coverage_path = run_root / row["coverage_path"]
        if (
            not output_path.is_file()
            or sha256_file(output_path) != row["output_sha256"]
            or not coverage_path.is_file()
            or sha256_file(coverage_path) != row["coverage_sha256"]
        ):
            raise ContractValidationError("MONO_CI_PSI_A05_PROBE_ARTIFACT_DIGEST_MISMATCH")
        evidence = json.loads(output_path.read_text(encoding="utf-8"))
        coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
        if (
            evidence.get("evaluator", {}).get("id") != row["evaluator_id"]
            or evidence.get("evaluator", {}).get("configuration_digest")
            != row["configuration_sha256"]
            or evidence.get("evaluator", {}).get("source_digest") != row["evaluator_source_sha256"]
            or evidence.get("architecture", {}).get("target_source_sha") != row["source_commit_sha"]
            or evidence.get("result", {}).get("execution_status") != row["execution_status"]
            or evidence.get("result", {}).get("compliance") != row["compliance"]
            or coverage.get("source_inspection_status") != row["inspection_status"]
            or row["inspection_status"] != "COMPLETE"
        ):
            raise ContractValidationError("MONO_CI_PSI_A05_PROBE_EVIDENCE_BINDING_MISMATCH")
    _verify_a05_candidate_extension(run_root, record, extension)


def _verify_a05_experiment_extension_v2(
    run_root: Path, record: dict[str, Any], repository: Path
) -> None:
    """Verify V4 ΔA5 evidence without using observed outcomes as validity criteria."""
    from experiments.execution.tooling.mono_ci_psi_a05 import (
        PROBE_PATH,
        PROBE_RELATIVE_ROOT,
        _verify_probe_detection_diagnostic,
        replay_negative_probe,
    )

    reference = record.get("a05_extension")
    if not isinstance(reference, dict) or set(reference) != {"path", "sha256"}:
        raise ContractValidationError("MONO_CI_PSI_A05_EXTENSION_BINDING_INVALID")
    if (
        reference["path"] != "diagnostics/a05-experiment-evidence.json"
        or _checked_run_artifact(run_root, reference["path"], reference["sha256"]) is None
    ):
        raise ContractValidationError("MONO_CI_PSI_A05_EXTENSION_DIGEST_MISMATCH")
    extension_path = run_root / reference["path"]
    extension = json.loads(extension_path.read_text(encoding="utf-8"))
    validate_payload(A05_EXPERIMENT_EVIDENCE_SCHEMA, extension)
    transition = extension["transition"]
    if (
        extension["execution_id"] != record["execution_id"]
        or transition["before_state"] != record["transition"]["before_state"]
        or transition["after_state"] != record["transition"]["after_state"]
        or transition["before_commit_sha"] != record["transition"]["before_commit_sha"]
        or transition["after_commit_sha"] != record["transition"]["after_commit_sha"]
        or transition["after_repository_tree_sha"]
        != record["transition"]["after_repository_tree_sha"]
        or transition["after_application_tree_sha"]
        != record["transition"]["after_application_tree_sha"]
        or extension["baseline"]["configuration_sha256"]
        != record["baseline"]["configuration_sha256"]
        or extension["scientific_boundary"]["method_decision"] != record["psi"]["decision"]
        or extension["scientific_boundary"]["operation_plan"]
        != json.loads((run_root / record["psi"]["raw_result_path"]).read_text())["operation_plan"][
            "operations"
        ]
    ):
        raise ContractValidationError("MONO_CI_PSI_A05_EXTENSION_RUN_BINDING_MISMATCH")

    probe_artifact_root = run_root / PROBE_RELATIVE_ROOT
    manifest_path = _checked_run_artifact(
        run_root, transition["probe_manifest_path"], transition["probe_manifest_sha256"]
    )
    patch_path = _checked_run_artifact(
        run_root, transition["probe_patch_path"], transition["probe_patch_sha256"]
    )
    source_path = _checked_run_artifact(
        run_root, transition["probe_source_path"], transition["probe_source_sha256"]
    )
    if (
        transition["probe_manifest_path"] != f"{PROBE_RELATIVE_ROOT}/probe-manifest.json"
        or transition["probe_patch_path"] != f"{PROBE_RELATIVE_ROOT}/source.patch"
        or transition["probe_source_path"] != f"{PROBE_RELATIVE_ROOT}/source-files/{PROBE_PATH}"
        or manifest_path is None
        or patch_path is None
        or source_path is None
    ):
        raise ContractValidationError("MONO_CI_PSI_A05_PROBE_ARTIFACT_BINDING_INVALID")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_payload("mono_ci_psi_a05_probe_manifest_v1.schema.json", manifest)
    if (
        manifest["parent_commit_sha"] != record["transition"]["after_commit_sha"]
        or manifest["parent_repository_tree_sha"]
        != record["transition"]["after_repository_tree_sha"]
        or manifest["parent_application_tree_sha"]
        != record["transition"]["after_application_tree_sha"]
        or manifest["probe_commit_sha"] != transition["probe_commit_sha"]
        or manifest["probe_repository_tree_sha"] != transition["probe_repository_tree_sha"]
        or manifest["probe_application_tree_sha"] != transition["probe_application_tree_sha"]
        or manifest["changed_paths"] != transition["probe_changed_paths"]
        or manifest["patch_sha256"] != transition["probe_patch_sha256"]
        or manifest["changed_sources"][0]["modified_file_sha256"]
        != transition["probe_source_sha256"]
        or manifest["remote_commit_required"] is not False
        or manifest["probe_commit_provenance"]["availability"] != "LOCAL_ONLY_RECREATED_FROM_PATCH"
    ):
        raise ContractValidationError("MONO_CI_PSI_A05_PROBE_MANIFEST_BINDING_MISMATCH")
    if (
        extension["negative_condition"]["source_commit_sha"] != manifest["probe_commit_sha"]
        or extension["negative_condition"]["changed_paths"] != manifest["changed_paths"]
        or transition["probe_parent_commit_sha"] != manifest["parent_commit_sha"]
        or transition["probe_commit_provenance"] != "LOCAL_ONLY_RECREATED_FROM_ARCHIVED_PATCH"
    ):
        raise ContractValidationError("MONO_CI_PSI_A05_PROBE_SOURCE_IDENTITY_MISMATCH")

    state_sidecar = json.loads(
        (run_root / record["transition"]["state_manifest_path"]).read_text(encoding="utf-8")
    )
    after_manifest = next(row for row in state_sidecar["manifests"] if row["state"] == "after")
    state_manifest_bytes = after_manifest["content"].encode("utf-8")
    if sha256_bytes(state_manifest_bytes) != record["transition"]["after_state_manifest_sha256"]:
        raise ContractValidationError("MONO_CI_PSI_A05_STATE_MANIFEST_BINDING_MISMATCH")

    positive = extension["positive_condition"]["evaluator"]
    negative_rows = extension["negative_condition"]["evaluators"]
    negative_by_id = {row["evaluator_id"]: row for row in negative_rows}
    if set(negative_by_id) != {"AC_PUBLIC_API", "AC_MODULE_GRAPH", "AC_DATA_OWNERSHIP"}:
        raise ContractValidationError("MONO_CI_PSI_A05_PROBE_EVALUATOR_SET_INVALID")
    config_rows = {row["evaluator_id"]: row for row in manifest["evaluator_configurations"]}
    bindings = {row["evaluator_id"]: row for row in manifest["evaluator_evidence_bindings"]}
    if set(config_rows) != set(negative_by_id) or set(bindings) != set(negative_by_id):
        raise ContractValidationError("MONO_CI_PSI_A05_PROBE_EVALUATOR_BINDING_SET_INVALID")

    with replay_negative_probe(
        repository,
        probe_artifact_root,
        expected_parent_commit=record["transition"]["after_commit_sha"],
        expected_parent_tree=record["transition"]["after_repository_tree_sha"],
        expected_parent_application_tree=record["transition"]["after_application_tree_sha"],
    ) as (probe_repository, replay_manifest):
        if replay_manifest != manifest:
            raise ContractValidationError("MONO_CI_PSI_A05_PROBE_REPLAY_MANIFEST_MISMATCH")
        positive_config_path = (
            run_root
            / "PSI/evaluator-observations/implementation/AC_DATA_OWNERSHIP/data_ownership_v1.yaml"
        )
        if positive_config_path.is_symlink() or not positive_config_path.is_file():
            raise ContractValidationError("MONO_CI_PSI_A05_POSITIVE_CONFIG_MISSING")
        positive_config_bytes = positive_config_path.read_bytes()
        _verify_a05_evaluator_row(
            run_root,
            positive,
            repository=repository,
            expected_commit=record["transition"]["after_commit_sha"],
            expected_tree=record["transition"]["after_repository_tree_sha"],
            expected_application_tree=record["transition"]["after_application_tree_sha"],
            configuration_bytes=positive_config_bytes,
            state_manifest_bytes=state_manifest_bytes,
            architecture_state="A0_5_MODULE_DATA_OWNERSHIP",
        )
        for evaluator_id, row in sorted(negative_by_id.items()):
            config_ref = config_rows[evaluator_id]
            config_path = _checked_run_artifact(
                run_root,
                config_ref["artifact_path"],
                config_ref["configuration_sha256"],
            )
            if (
                config_path is None
                or config_ref["configuration_path"]
                != EVALUATOR_CONFIGS.get(
                    evaluator_id, "architecture/acceptance/a1/data_ownership_v1.yaml"
                )
                or config_ref["configuration_sha256"] != row["configuration_sha256"]
                or bindings[evaluator_id] != _a05_evidence_binding(row)
            ):
                raise ContractValidationError(
                    "MONO_CI_PSI_A05_PROBE_EVALUATOR_CONFIG_BINDING_MISMATCH"
                )
            configuration_bytes = config_path.read_bytes()
            _verify_a05_evaluator_row(
                run_root,
                row,
                repository=probe_repository,
                expected_commit=manifest["probe_commit_sha"],
                expected_tree=manifest["probe_repository_tree_sha"],
                expected_application_tree=manifest["probe_application_tree_sha"],
                configuration_bytes=configuration_bytes,
                state_manifest_bytes=state_manifest_bytes,
                architecture_state="A0_5_MODULE_DATA_OWNERSHIP",
            )
        diagnostic = extension["adequacy_diagnostic"]
        _verify_probe_detection_diagnostic(
            run_root,
            negative_rows,
            diagnostic,
            source_condition_verified=True,
        )
        if (
            diagnostic["evidence_integrity"]
            != "VERIFIED_BY_SOURCE_REPLAY_AND_RAW_EVIDENCE_READBACK"
        ):
            raise ContractValidationError("MONO_CI_PSI_A05_DERIVED_DIAGNOSTIC_MISMATCH")

        baseline_bytes = (run_root / "provenance/reconstructed-b0-proposal.json").read_bytes()
        generic_diagnostic = json.loads(
            (run_root / "diagnostics/adaptation-necessity-assessment.json").read_text(
                encoding="utf-8"
            )
        )
        old_capabilities: dict[str, dict[str, Any]] = {}
        for assessment in generic_diagnostic.get("assessments", []):
            for capability in assessment.get("capability_inventory", {}).get(
                "capabilities_after", []
            ):
                old_capabilities[capability["capability_type"]] = capability
        before_observations = [
            row
            for row in record["evaluator_observations"]
            if row["architecture_state"] == "A0_4_REPORT_QUERY_PORT"
        ]
        before_coverage = [
            json.loads(
                (
                    run_root
                    / _coverage_assessment_path("A0_4_REPORT_QUERY_PORT", row["evaluator_id"])
                ).read_text(encoding="utf-8")
            )
            for row in before_observations
        ]
        before_scope_complete = bool(before_coverage) and all(
            row.get("source_inspection_status") == "COMPLETE" for row in before_coverage
        )
        before_compliance = (
            "COMPLIANT"
            if before_observations
            and all(
                row["execution_status"] == "COMPLETED" and row["compliance"] == "COMPLIANT"
                for row in before_observations
            )
            else "NOT_EVALUABLE"
        )
        capability_scope_verified = bool(old_capabilities) and all(
            row.get("verification_status") == "VERIFIED_STATIC_SCOPE"
            for row in old_capabilities.values()
        )
        independent = extension["independent_requirement"]
        requirement = {
            "control_id": independent["requirement_id"],
            "requirement_type": independent["requirement_type"],
            "detail_status": "SPECIFIED",
            "value": independent["value"],
            "source_kind": independent["source_kind"],
            "source_ref": {
                "path": independent["source_path"],
                "sha256": independent["source_sha256"],
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
        expected_adequacy = assess_adaptation_necessity(
            {
                "configuration_sha256_before": sha256_bytes(baseline_bytes),
                "configuration_sha256_after": sha256_bytes(baseline_bytes),
                "requirements_after": [requirement],
                "capabilities_after": list(old_capabilities.values()),
                "requirement_capability_mappings": [mapping],
                "unresolved_requirements_after": [],
                "evaluator_identity_verified": bool(positive["evaluator_source_sha256"])
                and all(bool(row["evaluator_source_sha256"]) for row in before_observations),
                "architecture_identity_verified": all(
                    row["source_commit_sha"] == record["transition"]["before_commit_sha"]
                    for row in before_observations
                )
                and positive["source_commit_sha"] == record["transition"]["after_commit_sha"],
                "configuration_identity_verified": sha256_bytes(baseline_bytes)
                == record["baseline"]["configuration_sha256"],
                "source_inspection_before": "COMPLETE" if before_scope_complete else "INCOMPLETE",
                "source_inspection_after": positive["inspection_status"],
                "evaluator_compliance_before": before_compliance,
                "evaluator_compliance_after": positive["compliance"],
                "rule_scope_match_before": before_scope_complete,
                "rule_scope_match_after": positive["inspection_status"] == "COMPLETE",
                "requirement_inventory_status_after": "COMPLETE_FOR_DECLARED_MANIFEST_TYPES",
                "requirement_universe_completeness_after": "UNKNOWN",
                "capability_inventory_status_after": (
                    "VERIFIED_FOR_DECLARED_STATIC_SCOPE"
                    if capability_scope_verified
                    else "INCOMPLETE_OR_UNVERIFIED"
                ),
                "architecture_state_after": "A0_5_MODULE_DATA_OWNERSHIP",
                "pair_semantic_validity": "UNKNOWN",
                "normative_applicability": "DECLARED_NOT_APPROVED",
                "baseline_identity": "PROSPECTIVE_RECONSTRUCTION_NOT_HISTORICAL",
                "independent_review": False,
            }
        )
        if (
            diagnostic["assessment_status"] != expected_adequacy["assessment_status"]
            or diagnostic["missing_post_transition_controls"]
            != expected_adequacy["missing_post_transition_controls"]
            or diagnostic["requirement_capability_comparison"]
            != expected_adequacy["requirement_capability_comparison"]
        ):
            raise ContractValidationError("MONO_CI_PSI_A05_ADEQUACY_DIAGNOSTIC_MISMATCH")
        _verify_a05_candidate_extension(
            run_root,
            record,
            extension,
            outcome_neutral=True,
            positive_repository=repository,
            probe_repository=probe_repository,
            state_manifest_bytes=state_manifest_bytes,
        )


def _checked_run_artifact(run_root: Path, relative: str, digest: str) -> Path | None:
    if (
        not isinstance(relative, str)
        or not relative
        or "\\" in relative
        or Path(relative).is_absolute()
        or any(part in {"", ".", ".."} for part in Path(relative).parts)
    ):
        return None
    root = run_root.resolve(strict=True)
    path = root / relative
    try:
        path.resolve(strict=True).relative_to(root)
    except (OSError, ValueError):
        return None
    current = root
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            return None
    if not path.is_file() or sha256_file(path) != digest:
        return None
    return path


def _a05_evidence_binding(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: row[key]
        for key in (
            "source_commit_sha",
            "source_tree_sha",
            "application_tree_sha",
            "evaluator_id",
            "process_exit_code",
            "execution_status",
            "compliance",
            "configuration_sha256",
            "evaluator_source_sha256",
            "output_path",
            "output_sha256",
            "coverage_path",
            "coverage_sha256",
            "stdout_path",
            "stdout_sha256",
            "stderr_path",
            "stderr_sha256",
        )
    }


def _expected_a05_evaluator_exit_code(execution_status: str, compliance: str) -> int:
    if execution_status == "FAILED":
        return 2
    return _expected_evaluator_exit_code(compliance)


def _verify_a05_evaluator_row(
    run_root: Path,
    row: dict[str, Any],
    *,
    repository: Path,
    expected_commit: str,
    expected_tree: str,
    expected_application_tree: str,
    configuration_bytes: bytes,
    state_manifest_bytes: bytes,
    architecture_state: str,
) -> None:
    output_path = _checked_run_artifact(run_root, row["output_path"], row["output_sha256"])
    stdout_path = _checked_run_artifact(run_root, row["stdout_path"], row["stdout_sha256"])
    stderr_path = _checked_run_artifact(run_root, row["stderr_path"], row["stderr_sha256"])
    coverage_path = _checked_run_artifact(run_root, row["coverage_path"], row["coverage_sha256"])
    if output_path is None or stdout_path is None or stderr_path is None or coverage_path is None:
        raise ContractValidationError("MONO_CI_PSI_A05_PROBE_ARTIFACT_DIGEST_MISMATCH")
    output_bytes = output_path.read_bytes()
    stdout_bytes = stdout_path.read_bytes()
    evidence = json.loads(output_bytes)
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    if (
        json.loads(stdout_bytes) != evidence
        or row["source_commit_sha"] != expected_commit
        or row["source_tree_sha"] != expected_tree
        or row["application_tree_sha"] != expected_application_tree
        or evidence.get("evaluator", {}).get("id") != row["evaluator_id"]
        or evidence.get("evaluator", {}).get("configuration_digest")
        != sha256_bytes(configuration_bytes)
        or evidence.get("evaluator", {}).get("source_digest") != row["evaluator_source_sha256"]
        or evidence.get("architecture", {}).get("state") != architecture_state
        or evidence.get("architecture", {}).get("target_source_sha") != expected_commit
        or evidence.get("architecture", {}).get("source_sha_status") != "MATCHED"
        or evidence.get("architecture", {}).get("manifest_state_status") != "MATCHED"
        or evidence.get("architecture", {}).get("manifest_digest")
        != sha256_bytes(state_manifest_bytes)
        or evidence.get("result", {}).get("execution_status") != row["execution_status"]
        or evidence.get("result", {}).get("compliance") != row["compliance"]
        or row["process_exit_code"]
        != _expected_a05_evaluator_exit_code(row["execution_status"], row["compliance"])
        or coverage.get("source_inspection_status") != row["inspection_status"]
    ):
        raise ContractValidationError("MONO_CI_PSI_A05_PROBE_EVIDENCE_BINDING_MISMATCH")
    diagnostics = evidence.get("diagnostics", {})
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
    if finding_codes != row["finding_codes"]:
        raise ContractValidationError("MONO_CI_PSI_A05_PROBE_FINDING_BINDING_MISMATCH")
    expected_coverage = verify_inspection_coverage(
        repository=repository,
        source_commit_sha=expected_commit,
        source_tree_sha=expected_tree,
        architecture_state=architecture_state,
        evaluator_id=row["evaluator_id"],
        evaluator_configuration_bytes=configuration_bytes,
        state_manifest_bytes=state_manifest_bytes,
        evaluator_output_bytes=output_bytes,
        evaluator_evidence=evidence,
    )
    if canonical_json_bytes(coverage) != canonical_json_bytes(expected_coverage):
        raise ContractValidationError("MONO_CI_PSI_A05_PROBE_COVERAGE_RECOMPUTE_MISMATCH")
    source_rows = evidence.get("evaluator", {}).get("source_artifacts")
    implementation_root = (
        run_root / "PSI/evaluator-observations/implementation" / row["evaluator_id"]
    )
    source_manifest_path = implementation_root / "source-manifest.json"
    if (
        not isinstance(source_rows, list)
        or sha256_bytes(canonical_json_bytes(source_rows)) != row["evaluator_source_sha256"]
        or source_manifest_path.is_symlink()
        or not source_manifest_path.is_file()
        or source_manifest_path.read_bytes() != canonical_json_bytes(source_rows)
    ):
        raise ContractValidationError("MONO_CI_PSI_A05_EVALUATOR_SOURCE_MANIFEST_MISMATCH")
    for source in source_rows:
        source_file = implementation_root / "source" / source["path"]
        if (
            source_file.is_symlink()
            or not source_file.is_file()
            or sha256_file(source_file) != source["sha256"]
        ):
            raise ContractValidationError("MONO_CI_PSI_A05_EVALUATOR_SOURCE_FILE_MISMATCH")


def _verify_a05_candidate_extension(
    run_root: Path,
    record: dict[str, Any],
    extension: dict[str, Any],
    *,
    outcome_neutral: bool = False,
    positive_repository: Path | None = None,
    probe_repository: Path | None = None,
    state_manifest_bytes: bytes | None = None,
) -> None:
    """Read back the exact materialized candidate and both independent executions."""
    report = extension["candidate_verification"]
    method_result = json.loads(
        (run_root / record["psi"]["raw_result_path"]).read_text(encoding="utf-8")
    )
    candidate = method_result.get("candidate")
    if candidate is None:
        if report["candidate_present"] or report["status"] != "NOT_EXECUTED":
            raise ContractValidationError("MONO_CI_PSI_A05_CANDIDATE_ABSENCE_MISMATCH")
        return
    validate_payload("p_candidate_configuration_v1.schema.json", candidate)
    candidate_path = run_root / report["materialized_candidate_path"]
    if (
        report["candidate_present"] is not True
        or report["materialized_candidate_path"] != "diagnostics/materialized-method-candidate.json"
        or candidate_path.is_symlink()
        or not candidate_path.is_file()
        or sha256_file(candidate_path) != report["materialized_candidate_file_sha256"]
        or json.loads(candidate_path.read_text(encoding="utf-8")) != candidate
        or report["candidate_configuration_sha256"] != candidate_sha256(candidate)
        or report["candidate_configuration_sha256"]
        != method_result.get("governance", {}).get("candidate_configuration_sha256")
        or candidate.get("architecture_source_sha") != record["transition"]["after_commit_sha"]
        or candidate.get("input_bundle_sha256") != record["method_input"]["bundle_sha256"]
        or report["configuration_version"] != candidate.get("configuration_version")
        or report["method_candidate_validation_status"]
        != candidate.get("candidate_validation", {}).get("status")
    ):
        raise ContractValidationError("MONO_CI_PSI_A05_CANDIDATE_MATERIALIZATION_MISMATCH")

    parent = candidate.get("parent_configuration", {})
    parent_file = run_root / "PSI/method-input" / str(parent.get("path", ""))
    if (
        parent_file.is_symlink()
        or not parent_file.is_file()
        or sha256_file(parent_file) != parent.get("sha256")
    ):
        raise ContractValidationError("MONO_CI_PSI_A05_CANDIDATE_PARENT_BINDING_MISMATCH")

    active_rows = [
        row
        for row in candidate.get("representations", [])
        if isinstance(row, dict) and row.get("active") is True
    ]
    expected_bindings = []
    for row in active_rows:
        evaluator_id = row.get("evaluator")
        contract = row.get("evidence_contract", {})
        artifact = row.get("evaluator_artifact", {})
        binding = {
            "representation_id": row.get("id"),
            "evaluator_id": evaluator_id,
            "covers": row.get("covers", []),
            "configuration_path": contract.get("configuration_path"),
            "configuration_sha256": contract.get("configuration_sha256"),
            "evaluator_source_sha256": contract.get("evaluator_source_sha256"),
            "evaluator_artifact_path": artifact.get("path"),
            "evaluator_artifact_sha256": artifact.get("sha256"),
        }
        expected_bindings.append(binding)
        evaluator_root = run_root / "PSI/evaluator-observations/implementation" / str(evaluator_id)
        config_copy = evaluator_root / Path(str(contract.get("configuration_path"))).name
        source_manifest = evaluator_root / "source-manifest.json"
        artifact_copy = run_root / str(artifact.get("path", ""))
        if (
            config_copy.is_symlink()
            or not config_copy.is_file()
            or sha256_file(config_copy) != contract.get("configuration_sha256")
            or artifact_copy.is_symlink()
            or not artifact_copy.is_file()
            or sha256_file(artifact_copy) != artifact.get("sha256")
            or artifact.get("path") != source_manifest.relative_to(run_root).as_posix()
            or artifact.get("sha256") != contract.get("evaluator_source_sha256")
        ):
            raise ContractValidationError("MONO_CI_PSI_A05_CANDIDATE_ACTIVE_BINDING_MISMATCH")
    if expected_bindings != report["active_representations"]:
        raise ContractValidationError("MONO_CI_PSI_A05_CANDIDATE_ACTIVE_BINDING_MISMATCH")

    ownership_representation_ids = sorted(
        str(row["id"])
        for row in active_rows
        if isinstance(row.get("covers"), list) and "AC_DATA_OWNERSHIP" in row["covers"]
    )
    target = report["target_obligation"]
    if (
        target["obligation_id"] != "AC_DATA_OWNERSHIP"
        or target["representation_ids"] != ownership_representation_ids
        or target["coverage_status"]
        != ("COVERED" if ownership_representation_ids else "NOT_COVERED")
        or target["adequacy_status"]
        != (
            "NOT_ESTABLISHED_BY_STATIC_EXECUTION" if ownership_representation_ids else "NOT_COVERED"
        )
    ):
        raise ContractValidationError("MONO_CI_PSI_A05_CANDIDATE_OBLIGATION_BINDING_MISMATCH")

    positive_rows = report["positive_evaluations"]
    negative_rows = report["negative_evaluations"]
    representation_ids = sorted(row["representation_id"] for row in expected_bindings)
    if (
        sorted(row["representation_id"] for row in positive_rows) != representation_ids
        or sorted(row["representation_id"] for row in negative_rows) != representation_ids
    ):
        raise ContractValidationError("MONO_CI_PSI_A05_CANDIDATE_EVALUATION_SET_MISMATCH")

    conditions = (
        (
            positive_rows,
            record["transition"]["after_commit_sha"],
            record["transition"]["after_repository_tree_sha"],
            record["transition"]["after_application_tree_sha"],
        ),
        (
            negative_rows,
            extension["transition"]["probe_commit_sha"],
            extension["transition"]["probe_repository_tree_sha"],
            extension["transition"]["probe_application_tree_sha"],
        ),
    )
    for condition_rows, commit_sha, tree_sha, application_tree_sha in conditions:
        for row in condition_rows:
            binding = next(
                item
                for item in expected_bindings
                if item["representation_id"] == row["representation_id"]
            )
            output_path = run_root / row["output_path"]
            coverage_path = run_root / row["coverage_path"]
            if (
                row["source_commit_sha"] != commit_sha
                or row["source_tree_sha"] != tree_sha
                or row["application_tree_sha"] != application_tree_sha
                or row["evaluator_id"] != binding["evaluator_id"]
                or row["configuration_sha256"] != binding["configuration_sha256"]
                or row["evaluator_source_sha256"] != binding["evaluator_source_sha256"]
                or (
                    not outcome_neutral
                    and (
                        row["execution_status"] != "COMPLETED"
                        or row["inspection_status"] != "COMPLETE"
                    )
                )
                or not output_path.is_file()
                or sha256_file(output_path) != row["output_sha256"]
                or not coverage_path.is_file()
                or sha256_file(coverage_path) != row["coverage_sha256"]
            ):
                raise ContractValidationError("MONO_CI_PSI_A05_CANDIDATE_EVIDENCE_BINDING_MISMATCH")
            evidence = json.loads(output_path.read_text(encoding="utf-8"))
            coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
            if (
                evidence.get("architecture", {}).get("target_source_sha") != commit_sha
                or evidence.get("evaluator", {}).get("configuration_digest")
                != binding["configuration_sha256"]
                or evidence.get("evaluator", {}).get("source_digest")
                != binding["evaluator_source_sha256"]
                or coverage.get("source_inspection_status") != row["inspection_status"]
                or coverage.get("architecture_state") != AFTER_STATE
            ):
                raise ContractValidationError("MONO_CI_PSI_A05_CANDIDATE_RAW_EVIDENCE_MISMATCH")
            if outcome_neutral:
                stdout_path = run_root / row["stdout_path"]
                stderr_path = run_root / row["stderr_path"]
                if (
                    stdout_path.is_symlink()
                    or stderr_path.is_symlink()
                    or not stdout_path.is_file()
                    or not stderr_path.is_file()
                    or sha256_file(stdout_path) != row["stdout_sha256"]
                    or sha256_file(stderr_path) != row["stderr_sha256"]
                    or json.loads(stdout_path.read_text(encoding="utf-8")) != evidence
                    or evidence.get("result", {}).get("execution_status") != row["execution_status"]
                    or evidence.get("result", {}).get("compliance") != row["compliance"]
                    or row["process_exit_code"]
                    != _expected_a05_evaluator_exit_code(row["execution_status"], row["compliance"])
                ):
                    raise ContractValidationError(
                        "MONO_CI_PSI_A05_CANDIDATE_PROCESS_BINDING_MISMATCH"
                    )
                source_repository = (
                    probe_repository
                    if commit_sha == extension["transition"]["probe_commit_sha"]
                    else positive_repository
                )
                if source_repository is None or state_manifest_bytes is None:
                    raise ContractValidationError("MONO_CI_PSI_A05_CANDIDATE_REPLAY_SOURCE_MISSING")
                implementation_root = (
                    run_root / "PSI/evaluator-observations/implementation" / binding["evaluator_id"]
                )
                config_file = implementation_root / Path(str(binding["configuration_path"])).name
                if config_file.is_symlink() or not config_file.is_file():
                    raise ContractValidationError("MONO_CI_PSI_A05_CANDIDATE_CONFIGURATION_MISSING")
                expected_coverage = verify_inspection_coverage(
                    repository=source_repository,
                    source_commit_sha=commit_sha,
                    source_tree_sha=tree_sha,
                    architecture_state=AFTER_STATE,
                    evaluator_id=binding["evaluator_id"],
                    evaluator_configuration_bytes=config_file.read_bytes(),
                    state_manifest_bytes=state_manifest_bytes,
                    evaluator_output_bytes=output_path.read_bytes(),
                    evaluator_evidence=evidence,
                )
                if canonical_json_bytes(coverage) != canonical_json_bytes(expected_coverage):
                    raise ContractValidationError(
                        "MONO_CI_PSI_A05_CANDIDATE_COVERAGE_RECOMPUTE_MISMATCH"
                    )

    baseline = json.loads(
        (run_root / "provenance/reconstructed-b0-proposal.json").read_text(encoding="utf-8")
    )
    baseline_by_id = {row["representation_id"]: row for row in baseline["representations"]}
    candidate_by_id = {row["representation_id"]: row for row in expected_bindings}
    baseline_ids = sorted(baseline_by_id)
    added = sorted(set(candidate_by_id) - set(baseline_by_id))
    removed = sorted(set(baseline_by_id) - set(candidate_by_id))
    changed = sorted(
        identity
        for identity in set(candidate_by_id) & set(baseline_by_id)
        if candidate_by_id[identity]["evaluator_id"] != baseline_by_id[identity]["evaluator_id"]
        or candidate_by_id[identity]["configuration_sha256"]
        != baseline_by_id[identity]["evaluator_configuration_sha256"]
        or candidate_by_id[identity]["evaluator_source_sha256"]
        != baseline_by_id[identity]["evaluator_source_sha256"]
    )
    prior_positive = {
        row["evaluator_id"]: row
        for row in record["evaluator_observations"]
        if row["architecture_state"] == AFTER_STATE
    }
    prior_negative = {
        row["evaluator_id"]: row for row in extension["negative_condition"]["evaluators"]
    }
    candidate_positive = {row["representation_id"]: row for row in positive_rows}
    candidate_negative = {row["representation_id"]: row for row in negative_rows}
    comparisons = []
    for identity in sorted(candidate_by_id):
        binding = candidate_by_id[identity]
        baseline_row = baseline_by_id.get(identity)
        binding_matches = bool(
            baseline_row is not None
            and baseline_row["evaluator_id"] == binding["evaluator_id"]
            and baseline_row["evaluator_configuration_sha256"] == binding["configuration_sha256"]
            and baseline_row["evaluator_source_sha256"] == binding["evaluator_source_sha256"]
        )
        old_positive = prior_positive.get(binding["evaluator_id"])
        old_negative = prior_negative.get(binding["evaluator_id"])
        new_positive = candidate_positive[identity]
        new_negative = candidate_negative[identity]
        positive_outcome = _a05_evaluator_outcome(run_root, new_positive)
        negative_outcome = _a05_evaluator_outcome(run_root, new_negative)
        old_positive_outcome = (
            _a05_evaluator_outcome(run_root, old_positive)
            if binding_matches and old_positive is not None
            else None
        )
        old_negative_outcome = (
            _a05_evaluator_outcome(run_root, old_negative)
            if binding_matches and old_negative is not None
            else None
        )
        comparisons.append(
            {
                "representation_id": identity,
                "baseline_binding_matches": binding_matches,
                "candidate_positive_outcome": positive_outcome,
                "reconstructed_b0_positive_outcome": old_positive_outcome,
                "positive_outcome_parity": (
                    positive_outcome == old_positive_outcome
                    if old_positive_outcome is not None
                    else None
                ),
                "candidate_negative_outcome": negative_outcome,
                "reconstructed_b0_negative_outcome": old_negative_outcome,
                "negative_outcome_parity": (
                    negative_outcome == old_negative_outcome
                    if old_negative_outcome is not None
                    else None
                ),
            }
        )
    comparable = [item for item in comparisons if item["baseline_binding_matches"]]
    parity = all(
        item["positive_outcome_parity"] is True and item["negative_outcome_parity"] is True
        for item in comparable
    )
    baseline_comparison = report["reconstructed_b0_comparison"]
    if (
        report["outcome_comparisons"] != comparisons
        or baseline_comparison["baseline_identity"] != "PROSPECTIVE_RECONSTRUCTION_NOT_HISTORICAL"
        or baseline_comparison["baseline_active_representation_ids"] != baseline_ids
        or baseline_comparison["candidate_active_representation_ids"] != representation_ids
        or baseline_comparison["added_representation_ids"] != added
        or baseline_comparison["removed_representation_ids"] != removed
        or baseline_comparison["changed_representation_ids"] != changed
        or baseline_comparison["active_control_set_unchanged"]
        != (not (added or removed or changed))
        or baseline_comparison["matching_control_outcomes_equal"] != parity
    ):
        raise ContractValidationError("MONO_CI_PSI_A05_CANDIDATE_BASELINE_COMPARISON_MISMATCH")

    positive_cost = round(sum(float(row["duration_ms"]) for row in positive_rows), 3)
    negative_cost = round(sum(float(row["duration_ms"]) for row in negative_rows), 3)
    additional_cost = round(
        sum(
            float(row["duration_ms"]) for row in positive_rows if row["representation_id"] in added
        ),
        3,
    )
    cost = report["execution_cost"]
    if (
        cost["candidate_positive_total_ms"] != positive_cost
        or cost["candidate_negative_total_ms"] != negative_cost
        or cost["candidate_validation_total_ms"] != round(positive_cost + negative_cost, 3)
        or cost["additional_active_representations_per_ci_build"] != len(added)
        or cost["estimated_additional_ci_execution_ms_per_build"] != additional_cost
    ):
        raise ContractValidationError("MONO_CI_PSI_A05_CANDIDATE_COST_BINDING_MISMATCH")

    runs_complete = bool(expected_bindings) and all(
        row["execution_status"] == "COMPLETED" and row["inspection_status"] == "COMPLETE"
        for row in [*positive_rows, *negative_rows]
    )
    positive_controls_compliant = all(
        _a05_evaluator_outcome(run_root, row)["compliance"] == "COMPLIANT" for row in positive_rows
    )
    expected_status = (
        "PASS"
        if candidate.get("candidate_validation", {}).get("status") == "valid"
        and runs_complete
        and positive_controls_compliant
        and parity
        else "FAIL"
    )
    if report["status"] != expected_status:
        raise ContractValidationError("MONO_CI_PSI_A05_CANDIDATE_STATUS_MISMATCH")


def _a05_evaluator_outcome(run_root: Path, row: dict[str, Any]) -> dict[str, Any]:
    evidence = json.loads((run_root / row["output_path"]).read_text(encoding="utf-8"))
    diagnostics = evidence.get("diagnostics", {})
    codes = sorted(
        {
            item["code"]
            for item in diagnostics.get("policy_findings", [])
            if isinstance(item, dict) and isinstance(item.get("code"), str)
        }
    )
    if not codes:
        codes = sorted(
            {
                item["code"]
                for values in diagnostics.values()
                if isinstance(values, list)
                for item in values
                if isinstance(item, dict) and isinstance(item.get("code"), str)
            }
        )
    return {
        "evaluator_id": row["evaluator_id"],
        "execution_status": evidence.get("result", {}).get("execution_status"),
        "compliance": evidence.get("result", {}).get("compliance"),
        "finding_codes": codes,
    }


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


def _export_transition_method_inputs(
    repository: Path,
    policy_source_bundle: Path,
    output_directory: Path,
    evaluation_as_of: str,
) -> dict[str, Any]:
    """Configure the pinned exporter for the A0.4 endpoint state, then restore it."""
    previous_manifest_path = p_policy_source_v3.STRUCTURAL_MANIFEST_PATH
    p_policy_source_v3.STRUCTURAL_MANIFEST_PATH = f"architecture/states/{AFTER_STATE}.yaml"
    try:
        return p_policy_source_v3.export_method_inputs_v3(
            repository,
            policy_source_bundle,
            output_directory,
            "P",
            BEFORE_COMMIT,
            AFTER_COMMIT,
            evaluation_as_of,
        )
    finally:
        p_policy_source_v3.STRUCTURAL_MANIFEST_PATH = previous_manifest_path


def _verify_transition_state_sidecar(root: Path, binding: dict[str, Any]) -> None:
    path = root / binding["state_manifest_path"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_STATE_MANIFESTS_INVALID") from error
    if (
        not isinstance(payload, dict)
        or set(payload) != {"schema_version", "transition", "manifests"}
        or payload["schema_version"] != "MONO_CI_B0_PSI_ARCHITECTURE_STATE_MANIFESTS_V1"
        or not isinstance(payload["transition"], dict)
        or not isinstance(payload["manifests"], list)
        or len(payload["manifests"]) != 2
    ):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_STATE_MANIFESTS_INVALID")
    transition = payload["transition"]
    expected_transition = {
        "before_state": binding["before_state"],
        "after_state": binding["after_state"],
        "before_commit_sha": binding["before_commit_sha"],
        "after_commit_sha": binding["after_commit_sha"],
        "before_tree_sha": binding["before_application_tree_sha"],
        "after_tree_sha": binding["after_application_tree_sha"],
    }
    if transition != expected_transition:
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_STATE_BINDING_MISMATCH")
    expected_manifests = (
        ("before", "before_state", "before_commit_sha", "before_state_manifest_sha256"),
        ("after", "after_state", "after_commit_sha", "after_state_manifest_sha256"),
    )
    for row, (label, state_key, commit_key, digest_key) in zip(
        payload["manifests"], expected_manifests, strict=True
    ):
        if not isinstance(row, dict) or set(row) != {
            "state",
            "path",
            "source_commit_sha",
            "sha256",
            "content",
        }:
            raise ContractValidationError("MONO_CI_PSI_TRANSITION_STATE_MANIFESTS_INVALID")
        content = row["content"]
        expected_state = binding[state_key]
        if (
            row["state"] != label
            or row["path"] != f"architecture/states/{expected_state}.yaml"
            or row["source_commit_sha"] != binding[commit_key]
            or not isinstance(content, str)
            or sha256_bytes(content.encode("utf-8")) != binding[digest_key]
            or row["sha256"] != binding[digest_key]
        ):
            raise ContractValidationError("MONO_CI_PSI_TRANSITION_STATE_BINDING_MISMATCH")
        try:
            manifest = yaml.safe_load(content)
        except yaml.YAMLError as error:
            raise ContractValidationError(
                "MONO_CI_PSI_TRANSITION_STATE_MANIFESTS_INVALID"
            ) from error
        if not isinstance(manifest, dict) or manifest.get("architecture_state") != expected_state:
            raise ContractValidationError("MONO_CI_PSI_TRANSITION_STATE_MANIFESTS_INVALID")


def _add_state_manifest_sidecar(repository: Path, run_root: Path, binding: dict[str, Any]) -> None:
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
    _write_new_file(run_root / STATE_MANIFESTS_PATH, pretty_json_bytes(payload))


def _collect_evaluator_matrix(
    repository: Path, run_root: Path
) -> tuple[
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, bytes]],
    dict[tuple[str, str], dict[str, Any]],
]:
    proposal = json.loads(
        (repository / PROPOSAL_RELATIVE / BASELINE_NAME).read_text(encoding="utf-8")
    )
    proposal_rows = {row["evaluator_id"]: row for row in proposal["representations"]}
    implementation_root = run_root / "PSI/evaluator-observations/implementation"
    implementation_root.mkdir(parents=True)
    bindings: dict[str, dict[str, Any]] = {}
    artifact_content: dict[str, dict[str, bytes]] = {}
    for evaluator_id in EVALUATOR_IDS:
        source_rows, source_manifest_bytes, source_digest = evaluator_source_artifacts(repository)
        source_manifest_path = (
            Path("PSI/evaluator-observations/implementation")
            / evaluator_id
            / "source-manifest.json"
        ).as_posix()
        source_directory = implementation_root / evaluator_id / "source"
        source_directory.mkdir(parents=True)
        sources: dict[str, bytes] = {}
        for row in source_rows:
            path = repository / "architecture/acceptance/a1" / row["path"]
            content = path.read_bytes()
            if sha256_bytes(content) != row["sha256"]:
                raise ContractValidationError("PSI_EVALUATOR_SOURCE_DIGEST_MISMATCH")
            relative = (
                Path("PSI/evaluator-observations/implementation")
                / evaluator_id
                / "source"
                / row["path"]
            ).as_posix()
            destination = run_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            _write_new_file(destination, content)
            sources[relative] = content
        manifest_disk_path = run_root / source_manifest_path
        _write_new_file(manifest_disk_path, source_manifest_bytes)
        config_relative = EVALUATOR_CONFIGS[evaluator_id]
        config_bytes = (repository / config_relative).read_bytes()
        config_digest = sha256_bytes(config_bytes)
        if config_digest != proposal_rows[evaluator_id]["evaluator_configuration_sha256"]:
            raise ContractValidationError("PSI_EVALUATOR_CONFIGURATION_IDENTITY_MISMATCH")
        if source_digest != proposal_rows[evaluator_id]["evaluator_source_sha256"]:
            raise ContractValidationError("PSI_EVALUATOR_SOURCE_IDENTITY_MISMATCH")
        config_path = (
            Path("PSI/evaluator-observations/implementation")
            / evaluator_id
            / Path(config_relative).name
        ).as_posix()
        config_destination = run_root / config_path
        _write_new_file(config_destination, config_bytes)
        config = yaml.safe_load(config_bytes)
        if not isinstance(config, dict):
            raise ContractValidationError("PSI_EVALUATOR_CONFIGURATION_INVALID")
        states = config.get("states")
        if not isinstance(states, dict):
            raise ContractValidationError("PSI_EVALUATOR_STATE_SCOPE_MISSING")
        supported_states = [
            state
            for state in (BEFORE_STATE, AFTER_STATE)
            if isinstance(states.get(state), dict)
            and states[state].get("applicability") == "ACTIVE"
        ]
        source_scope = config.get("source_scope")
        if not isinstance(source_scope, dict):
            raise ContractValidationError("PSI_EVALUATOR_SOURCE_SCOPE_INVALID")
        evaluator_row = proposal_rows[evaluator_id]
        architecture_revisions = {
            BEFORE_STATE: {
                "commit_sha": BEFORE_COMMIT,
                "repository_tree_sha": BEFORE_REPOSITORY_TREE,
                "application_tree_sha": BEFORE_APP_TREE,
            },
            AFTER_STATE: {
                "commit_sha": AFTER_COMMIT,
                "repository_tree_sha": AFTER_REPOSITORY_TREE,
                "application_tree_sha": AFTER_APP_TREE,
            },
        }
        semantic_config_key = "public_api" if evaluator_id == "AC_PUBLIC_API" else "module_graph"
        binding = {
            "representation_id": evaluator_row["representation_id"],
            "obligation_id": evaluator_row["obligation_id"],
            "criterion_id": evaluator_row["criterion_id"],
            "evaluator_id": evaluator_id,
            "evaluator_version": evaluator_row["evaluator_version"],
            "evaluator_source_sha256": source_digest,
            "source_artifacts": source_rows,
            "source_manifest_path": source_manifest_path,
            "configuration_path": config_path,
            "configuration_source_path": config_relative,
            "configuration_sha256": config_digest,
            "supported_states": supported_states,
            "state_applicability": {
                state: states[state]["applicability"] for state in supported_states
            },
            "architecture_revisions": {
                state: architecture_revisions[state] for state in supported_states
            },
            "source_scope": source_scope,
            "coverage_limits": config.get("coverage_limits", []),
            "semantics": config.get(semantic_config_key),
            "semantics_summary": (
                "Static source evaluation; exact evaluator rules and scope limits are "
                "bound by the recorded configuration digest."
            ),
        }
        bindings[evaluator_id] = binding
        artifact_content[evaluator_id] = {
            source_manifest_path: source_manifest_bytes,
            config_path: config_bytes,
            **sources,
        }

    runs: list[dict[str, Any]] = []
    source_binding = _source_binding(repository)
    coverage_assessments: dict[tuple[str, str], dict[str, Any]] = {}
    for state, commit, architecture_state in (
        ("before", BEFORE_COMMIT, BEFORE_STATE),
        ("after", AFTER_COMMIT, AFTER_STATE),
    ):
        with tempfile.TemporaryDirectory(prefix="psi-evaluator-source-") as temporary:
            checkout = Path(temporary) / "source"
            _git_worktree(repository, "add", "--detach", str(checkout), commit)
            try:
                if _git_text(checkout, "rev-parse", "HEAD").strip() != commit:
                    raise ContractValidationError("PSI_EVALUATOR_SOURCE_REVISION_MISMATCH")
                for evaluator_id in EVALUATOR_IDS:
                    run = run_fresh_evaluator(
                        repository=repository,
                        source_checkout=checkout,
                        evaluator_id=evaluator_id,
                        architecture_state=architecture_state,
                        source_commit_sha=commit,
                        output_directory=(
                            run_root / "PSI/evaluator-observations" / state / evaluator_id
                        ),
                    )
                    output_bytes = (run_root / run["output_path"]).read_bytes()
                    configuration_bytes = (
                        repository / EVALUATOR_CONFIGS[evaluator_id]
                    ).read_bytes()
                    state_manifest_bytes = _git_bytes(
                        repository,
                        commit,
                        f"architecture/states/{architecture_state}.yaml",
                    )
                    coverage = verify_inspection_coverage(
                        repository=repository,
                        source_commit_sha=commit,
                        source_tree_sha=run["source_tree_sha"],
                        architecture_state=architecture_state,
                        evaluator_id=evaluator_id,
                        evaluator_configuration_bytes=configuration_bytes,
                        state_manifest_bytes=state_manifest_bytes,
                        evaluator_output_bytes=output_bytes,
                        evaluator_evidence=run["evidence"],
                    )
                    coverage_relative = _coverage_assessment_path(architecture_state, evaluator_id)
                    coverage_bytes = pretty_json_bytes(coverage)
                    _write_new_file(run_root / coverage_relative, coverage_bytes)
                    coverage_assessments[(architecture_state, evaluator_id)] = coverage
                    inspection_scope_path = (
                        Path(run["output_path"]).parent / "inspection-scope.json"
                    ).as_posix()
                    inspection_scope_bytes = pretty_json_bytes(
                        build_inspection_scope_artifact(
                            run["evidence"],
                            sha256_file(run_root / run["output_path"]),
                            coverage,
                        )
                    )
                    _write_new_file(run_root / inspection_scope_path, inspection_scope_bytes)
                    run["inspection_scope_path"] = inspection_scope_path
                    run["inspection_scope_sha256"] = sha256_bytes(inspection_scope_bytes)
                    if (
                        run["target_source_sha256"] != commit
                        or run["evaluator_source_sha256"]
                        != bindings[evaluator_id]["evaluator_source_sha256"]
                        or run["configuration_sha256"]
                        != bindings[evaluator_id]["configuration_sha256"]
                        or run["source_tree_sha"]
                        != (
                            source_binding["before_repository_tree_sha"]
                            if state == "before"
                            else source_binding["after_repository_tree_sha"]
                        )
                        or run["target_application_tree_sha"]
                        != (
                            source_binding["before_application_tree_sha"]
                            if state == "before"
                            else source_binding["after_application_tree_sha"]
                        )
                    ):
                        raise ContractValidationError("PSI_EVALUATOR_OUTPUT_BINDING_MISMATCH")
                    runs.append(run)
            finally:
                _git_worktree(repository, "remove", "--force", str(checkout), check=False)
    return runs, bindings, artifact_content, coverage_assessments


def _coverage_assessment_path(state: str, evaluator_id: str) -> Path:
    label = "before" if state == BEFORE_STATE else "after"
    return Path("PSI/evaluator-observations") / label / evaluator_id / "inspection-coverage.json"


def _build_adaptation_necessity_report(
    *,
    repo: Path,
    run_root: Path,
    execution_id: str,
    baseline: dict[str, Any],
    evaluator_runs: list[dict[str, Any]],
    coverage_assessments: dict[tuple[str, str], dict[str, Any]],
    method_result: dict[str, Any],
    method_result_sha256: str,
    state_manifest_sidecar: dict[str, Any],
) -> dict[str, Any]:
    """Build a source-bound diagnostic separate from Method P inputs and outputs."""
    proposal_path = run_root / "provenance/reconstructed-b0-proposal.json"
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    proposal_rows = {row["evaluator_id"]: row for row in proposal["representations"]}
    manifest_source_rows = {row["state"]: row for row in state_manifest_sidecar["manifests"]}
    manifest_rows = {
        row["state"]: yaml.safe_load(row["content"]) for row in state_manifest_sidecar["manifests"]
    }
    run_index = {(row["architecture_state"], row["evaluator_id"]): row for row in evaluator_runs}
    manifest_by_state = {
        "before": manifest_rows["before"],
        "after": manifest_rows["after"],
    }
    requirement_sources = _transition_requirement_sources(repo, run_root)
    requirement_mappings = [
        {
            "requirement_type": requirement_type,
            "capability_type": mapping["capability_type"],
            "mapping_id": mapping["mapping_id"],
            "comparison_rule": mapping["comparison_rule"],
            "status": "VERIFIED_RULE_IMPLEMENTATION",
        }
        for requirement_type, mapping in sorted(_REQUIREMENT_CAPABILITY_MAPPINGS.items())
    ]
    changed_paths = _git_text(
        repo,
        "diff-tree",
        "--no-commit-id",
        "--name-only",
        "-r",
        BEFORE_COMMIT,
        AFTER_COMMIT,
        "--",
        "app",
    ).splitlines()
    changed_application_files = []
    for path in sorted(path for path in changed_paths if path):
        before_bytes = _git_bytes(repo, BEFORE_COMMIT, path)
        after_bytes = _git_bytes(repo, AFTER_COMMIT, path)
        changed_application_files.append(
            {
                "path": path,
                "before_sha256": sha256_bytes(before_bytes),
                "after_sha256": sha256_bytes(after_bytes),
            }
        )

    before_manifest = manifest_by_state["before"]
    after_manifest = manifest_by_state["after"]
    before_invariants = before_manifest.get("invariants", {})
    after_invariants = after_manifest.get("invariants", {})
    invariant_names = (
        "deployment_units",
        "application_processes",
        "database_instances",
        "database_product",
        "internal_communication",
        "message_broker",
        "rest_behavior",
        "transaction_ownership",
    )
    unchanged_invariants = [
        f"{name}={before_invariants[name]}"
        for name in invariant_names
        if name in before_invariants and before_invariants.get(name) == after_invariants.get(name)
    ]
    before_allowed = before_manifest.get("allowed_dependencies", [])
    after_allowed = after_manifest.get("allowed_dependencies", [])
    if before_allowed == after_allowed:
        unchanged_invariants.append(f"allowed_dependencies={len(before_allowed)} edges")

    source_change_summary = list(after_manifest.get("implementation_scope", []))
    before_exceptions = before_manifest.get("temporary_exceptions", [])
    after_exceptions = after_manifest.get("temporary_exceptions", [])
    if before_exceptions != after_exceptions:
        before_ids = sorted(row.get("id", "") for row in before_exceptions if isinstance(row, dict))
        after_ids = sorted(row.get("id", "") for row in after_exceptions if isinstance(row, dict))
        source_change_summary.append(
            "Temporary exception identifiers changed from "
            f"{before_ids!r} to {after_ids!r} across the pinned state manifests."
        )
    if before_manifest.get("governance_requirements") != after_manifest.get(
        "governance_requirements"
    ):
        source_change_summary.append(
            "State-manifest governance requirements differ; per-control details are recorded below."
        )

    assessments: list[dict[str, Any]] = []
    for evaluator_id in EVALUATOR_IDS:
        proposal_row = proposal_rows[evaluator_id]
        config_path = EVALUATOR_CONFIGS[evaluator_id]
        implementation_root = run_root / "PSI/evaluator-observations/implementation" / evaluator_id
        config_bytes = (implementation_root / Path(config_path).name).read_bytes()
        config = yaml.safe_load(config_bytes)
        configuration_sha = sha256_bytes(config_bytes)
        bound_representation = (
            proposal_row.get("evaluator_id") == evaluator_id
            and proposal_row.get("evaluator_configuration_sha256") == configuration_sha
            and proposal_row.get("evaluator_source_sha256")
            == run_index[(AFTER_STATE, evaluator_id)]["evaluator_source_sha256"]
        )
        before_run = run_index[(BEFORE_STATE, evaluator_id)]
        after_run = run_index[(AFTER_STATE, evaluator_id)]
        before_coverage = coverage_assessments[(BEFORE_STATE, evaluator_id)]
        after_coverage = coverage_assessments[(AFTER_STATE, evaluator_id)]
        before_state_name = BEFORE_STATE
        after_state_name = AFTER_STATE
        before_config_state = config.get("states", {}).get(before_state_name, {})
        after_config_state = config.get("states", {}).get(after_state_name, {})
        before_scope = before_coverage["source_inspection_status"]
        after_scope = after_coverage["source_inspection_status"]
        before_compliance = before_run["evidence"]["result"]["compliance"]
        after_compliance = after_run["evidence"]["result"]["compliance"]
        before_manifest_required = _manifest_requires_evaluator(before_manifest, evaluator_id)
        after_manifest_required = _manifest_requires_evaluator(after_manifest, evaluator_id)
        rule_scope_before = (
            before_scope == "COMPLETE"
            and before_manifest_required
            and before_config_state.get("applicability") == "ACTIVE"
        )
        rule_scope_after = (
            after_scope == "COMPLETE"
            and after_manifest_required
            and after_config_state.get("applicability") == "ACTIVE"
            and (
                after_coverage.get("dependency_analysis") is None
                or (
                    after_coverage["dependency_analysis"].get("static_relationship_comparison")
                    == "MATCHED"
                    and after_coverage["dependency_analysis"].get("cycle_comparison") == "MATCHED"
                )
            )
        )
        requirements_before = _manifest_requirements_for_evaluator(
            evaluator_id,
            before_manifest,
            before_state_name,
            manifest_source_rows["before"],
        )
        requirements_after = _manifest_requirements_for_evaluator(
            evaluator_id,
            after_manifest,
            after_state_name,
            manifest_source_rows["after"],
        )
        unresolved_requirements = _unresolved_architecture_requirements(
            evaluator_id=evaluator_id,
            manifest=after_manifest,
            manifest_source=manifest_source_rows["after"],
            sources=requirement_sources,
        )
        capability_inventory_before = _evaluator_capabilities(
            evaluator_id=evaluator_id,
            state=before_state_name,
            config=config,
            run=before_run,
            coverage=before_coverage,
            representation_bound=bound_representation,
            configuration_sha256=configuration_sha,
            run_root=run_root,
            config_path=config_path,
        )
        capability_inventory_after = _evaluator_capabilities(
            evaluator_id=evaluator_id,
            state=after_state_name,
            config=config,
            run=after_run,
            coverage=after_coverage,
            representation_bound=bound_representation,
            configuration_sha256=configuration_sha,
            run_root=run_root,
            config_path=config_path,
        )
        pair = next(
            (
                row
                for row in method_result.get("current_pairs", [])
                if row.get("representation_id") == proposal_row["representation_id"]
                and row.get("obligation_id") == evaluator_id
            ),
            None,
        )
        pair_semantic_status = pair.get("status") if isinstance(pair, dict) else None
        pair_semantic_validity = (
            pair_semantic_status
            if pair_semantic_status in {"VALID", "INVALID", "UNKNOWN"}
            else "NOT_AVAILABLE"
        )
        applicability = next(
            (
                row.get("status")
                for row in method_result.get("after_applicability", {}).get("results", [])
                if row.get("obligation_id") == evaluator_id
            ),
            "UNKNOWN",
        )
        case = {
            "configuration_sha256_before": configuration_sha,
            "configuration_sha256_after": configuration_sha,
            "evaluator_identity_verified": bound_representation,
            "architecture_identity_verified": (
                before_run["source_commit_sha"] == BEFORE_COMMIT
                and after_run["source_commit_sha"] == AFTER_COMMIT
            ),
            "configuration_identity_verified": (
                proposal_row.get("evaluator_configuration_sha256") == configuration_sha
            ),
            "source_inspection_before": before_scope,
            "source_inspection_after": after_scope,
            "evaluator_compliance_before": before_compliance,
            "evaluator_compliance_after": after_compliance,
            "rule_scope_match_before": rule_scope_before,
            "rule_scope_match_after": rule_scope_after,
            "architecture_state_after": after_state_name,
            "requirements_after": requirements_after,
            "capabilities_after": capability_inventory_after["capabilities"],
            "requirement_capability_mappings": requirement_mappings,
            "unresolved_requirements_after": unresolved_requirements,
            "requirement_inventory_status_after": ("COMPLETE_FOR_DECLARED_MANIFEST_TYPES"),
            "requirement_universe_completeness_after": "UNKNOWN",
            "capability_inventory_status_after": capability_inventory_after["status"],
            "pair_semantic_validity": pair_semantic_validity,
            "normative_applicability": applicability,
            "baseline_identity": baseline["identity_status"],
            "independent_review": False,
        }
        diagnosis = assess_adaptation_necessity(case)
        relevant_changes = _control_transition_summary(
            evaluator_id,
            config,
            before_manifest,
            after_manifest,
            before_coverage,
            after_coverage,
        )
        evidence_refs = []
        for state in (BEFORE_STATE, AFTER_STATE):
            run = run_index[(state, evaluator_id)]
            coverage_path = _coverage_assessment_path(state, evaluator_id).as_posix()
            evidence_refs.extend(
                [
                    {
                        "path": run["output_path"],
                        "sha256": sha256_file(run_root / run["output_path"]),
                    },
                    {"path": coverage_path, "sha256": sha256_file(run_root / coverage_path)},
                ]
            )
        evidence_refs.extend(
            [
                {
                    "path": (
                        f"PSI/evaluator-observations/implementation/{evaluator_id}/"
                        f"{Path(config_path).name}"
                    ),
                    "sha256": configuration_sha,
                },
                {
                    "path": STATE_MANIFESTS_PATH,
                    "sha256": sha256_file(run_root / STATE_MANIFESTS_PATH),
                },
                {
                    "path": "PSI/raw/method-result.json",
                    "sha256": method_result_sha256,
                },
            ]
        )
        inspection = {
            "before_status": before_scope,
            "after_status": after_scope,
            "before_expected_count": before_coverage["counts"]["expected_count"],
            "before_inspected_count": before_coverage["counts"]["inspected_count"],
            "after_expected_count": after_coverage["counts"]["expected_count"],
            "after_inspected_count": after_coverage["counts"]["inspected_count"],
            "static_relationship_comparison_after": (
                after_coverage["dependency_analysis"]["static_relationship_comparison"]
                if after_coverage.get("dependency_analysis") is not None
                else "NOT_APPLICABLE"
            ),
            "cycle_comparison_after": (
                after_coverage["dependency_analysis"]["cycle_comparison"]
                if after_coverage.get("dependency_analysis") is not None
                else "NOT_APPLICABLE"
            ),
            "exact_dependency_edge_completeness_after": (
                after_coverage["dependency_analysis"]["exact_dependency_edge_completeness"]
                if after_coverage.get("dependency_analysis") is not None
                else "NOT_APPLICABLE"
            ),
        }
        compliance = {
            "before": before_compliance,
            "after": after_compliance,
            "before_execution_status": before_run["evidence"]["result"]["execution_status"],
            "after_execution_status": after_run["evidence"]["result"]["execution_status"],
        }
        missing_proofs = list(diagnosis["missing_proofs"])
        if (
            after_coverage.get("dependency_analysis") is not None
            and after_coverage["dependency_analysis"].get("exact_dependency_edge_completeness")
            == "UNKNOWN"
        ):
            missing_proofs.append("DYNAMIC_DEPENDENCY_EDGE_COMPLETENESS_UNKNOWN")
        if diagnosis["assessment_status"] == "ADAPTATION_NEEDED":
            change_necessity = "REQUIRED"
        elif diagnosis["assessment_status"] == "RETAIN_CANDIDATE":
            change_necessity = "NOT_DEMONSTRATED_WITHIN_VERIFIED_SCOPE"
        else:
            change_necessity = "NOT_EVALUABLE"
        assessments.append(
            {
                "control_id": evaluator_id,
                "assessment_status": diagnosis["assessment_status"],
                "configuration_change_necessity": change_necessity,
                "relevant_architecture_changes": relevant_changes,
                "previous_representation_identity": {
                    "representation_id": proposal_row["representation_id"],
                    "criterion_id": proposal_row["criterion_id"],
                    "obligation_id": proposal_row["obligation_id"],
                    "evaluator_version": proposal_row["evaluator_version"],
                    "mapping_status": proposal_row["mapping_status"],
                    "applicability": proposal_row["applicability"],
                    "semantic_validity": proposal_row["semantic_validity"],
                    "historical_identity": baseline["identity_status"],
                },
                "evaluator_identity": {
                    "evaluator_id": evaluator_id,
                    "version": proposal_row["evaluator_version"],
                    "source_sha256": proposal_row["evaluator_source_sha256"],
                    "configuration_sha256": configuration_sha,
                    "identity_matches_proposal": bound_representation,
                },
                "configuration_identity": {
                    "before_sha256": configuration_sha,
                    "after_sha256": configuration_sha,
                    "unchanged": True,
                    "state_scope_before": before_config_state.get("applicability", "UNKNOWN"),
                    "state_scope_after": after_config_state.get("applicability", "UNKNOWN"),
                },
                "inspection_completeness": inspection,
                "compliance_observations": compliance,
                "rule_semantics": {
                    "required_controls_before": [row["control_id"] for row in requirements_before],
                    "required_controls_after": [row["control_id"] for row in requirements_after],
                    "represented_controls_before": [
                        row["capability_id"] for row in capability_inventory_before["capabilities"]
                    ],
                    "represented_controls_after": [
                        row["capability_id"] for row in capability_inventory_after["capabilities"]
                    ],
                    "scope_limitations": sorted(
                        set(config.get("coverage_limits", []))
                        | set(after_coverage.get("uncertainties", []))
                        | (
                            {"Exact dynamic dependency-edge completeness remains UNKNOWN."}
                            if after_coverage.get("dependency_analysis") is not None
                            else set()
                        )
                    ),
                },
                "requirement_inventory": {
                    "declared_scope": (
                        "VERSIONED_STATE_MANIFEST_ALLOWED_DEPENDENCIES_QUERY_PORTS_AND_EXCEPTIONS"
                    ),
                    "completeness_within_declared_scope": ("COMPLETE_FOR_DECLARED_MANIFEST_TYPES"),
                    "universe_completeness": "UNKNOWN",
                    "authority_status": (
                        "VERSIONED_MANIFESTS_SOURCE_BOUND; "
                        "CATALOG_DETAIL_AND_POLICY_APPROVAL_UNRESOLVED"
                    ),
                    "requirements_before": requirements_before,
                    "requirements_after": requirements_after,
                    "unresolved_requirements": unresolved_requirements,
                    "governance_requirements_before": _manifest_governance_requirements(
                        before_manifest, manifest_source_rows["before"]
                    ),
                    "governance_requirements_after": _manifest_governance_requirements(
                        after_manifest, manifest_source_rows["after"]
                    ),
                    "source_refs": requirement_sources["source_refs"]
                    + [
                        {
                            "path": manifest_source_rows["before"]["path"],
                            "sha256": manifest_source_rows["before"]["sha256"],
                            "source_kind": "VERSIONED_ARCHITECTURE_STATE_MANIFEST",
                        },
                        {
                            "path": manifest_source_rows["after"]["path"],
                            "sha256": manifest_source_rows["after"]["sha256"],
                            "source_kind": "VERSIONED_ARCHITECTURE_STATE_MANIFEST",
                        },
                    ],
                },
                "capability_inventory": {
                    "before_status": capability_inventory_before["status"],
                    "after_status": capability_inventory_after["status"],
                    "capabilities_before": capability_inventory_before["capabilities"],
                    "capabilities_after": capability_inventory_after["capabilities"],
                    "mapping_catalog_id": "A1_ARCHITECTURE_REQUIREMENT_TO_CAPABILITY_V1",
                    "mapping_authority": (
                        "VERIFIED_RULE_IMPLEMENTATION_NOT_INDEPENDENT_SEMANTIC_APPROVAL"
                    ),
                },
                "requirement_capability_comparison": diagnosis["requirement_capability_comparison"],
                "pair_semantic_validity": pair_semantic_validity,
                "reason_codes": sorted(
                    set(diagnosis["reason_codes"])
                    | (
                        {"DYNAMIC_DEPENDENCY_EDGE_COMPLETENESS_UNKNOWN"}
                        if "DYNAMIC_DEPENDENCY_EDGE_COMPLETENESS_UNKNOWN" in missing_proofs
                        else set()
                    )
                ),
                "evidence_refs": evidence_refs,
                "missing_proofs": sorted(set(missing_proofs)),
                "operation_justification": diagnosis["operation_justification"],
            }
        )

    method_operations = method_result.get("operation_plan", {}).get("operations", [])
    governance = method_result.get("governance", {})
    return {
        "schema_version": ADAPTATION_NECESSITY_SCHEMA_VERSION,
        "execution_id": execution_id,
        "assessment_scope": "SOURCE_BOUND_DEVELOPMENT_DIAGNOSTIC_NOT_INDEPENDENTLY_REVIEWED",
        "transition": {
            "before_state": BEFORE_STATE,
            "after_state": AFTER_STATE,
            "before_commit_sha": BEFORE_COMMIT,
            "after_commit_sha": AFTER_COMMIT,
            "changed_application_files": changed_application_files,
            "source_change_summary": source_change_summary,
            "unchanged_architecture_invariants": sorted(unchanged_invariants),
        },
        "baseline": {
            "configuration_id": baseline["configuration_id"],
            "configuration_sha256": baseline["configuration_sha256"],
            "identity_status": baseline["identity_status"],
            "approval_status": baseline["approval_status"],
        },
        "method_result": {
            "path": "PSI/raw/method-result.json",
            "sha256": method_result_sha256,
            "governance_decision": governance.get("result", _governance_decision(method_result)),
            "operation_count": len(method_operations),
            "candidate_status": (
                "MATERIALIZED" if method_result.get("candidate") is not None else "NOT_MATERIALIZED"
            ),
            "prediction_status": (
                "EMITTED" if method_result.get("prediction_v1") is not None else "NOT_EMITTED"
            ),
        },
        "assessments": assessments,
        "scientific_boundary": {
            "is_independent_reference": False,
            "is_human_review": False,
            "official_comparison": "NOT_EXECUTED",
            "study_readiness": "NO_GO",
            "p_algorithm_status": "NOT_READY",
            "g1": "INCOMPLETE",
            "g4": "NOT_AUTHORIZED",
            "reference_gate": "NOT_READY",
        },
    }


def _transition_requirement_sources(repo: Path, run_root: Path) -> dict[str, Any]:
    catalog_path = "fitness/catalog/architectural-obligations.yaml"
    runtime_catalog_path = run_root / "PSI/method-runtime" / catalog_path
    runtime_inventory = json.loads(
        (run_root / "provenance/runtime-inventory.json").read_text(encoding="utf-8")
    )
    runtime_rows = {
        row["path"]: row for row in runtime_inventory.get("files", []) if isinstance(row, dict)
    }
    catalog_bytes = _git_bytes(repo, AFTER_COMMIT, catalog_path)
    catalog_sha = sha256_bytes(catalog_bytes)
    if (
        not runtime_catalog_path.is_file()
        or sha256_file(runtime_catalog_path) != catalog_sha
        or runtime_rows.get(catalog_path, {}).get("sha256") != catalog_sha
    ):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_REQUIREMENT_CATALOG_BINDING_INVALID")

    registry_path = "experiments/execution/policy-pilot/v1/source/fitness/policy/registry.json"
    registry_bytes = _git_bytes(repo, AFTER_COMMIT, registry_path)
    try:
        catalog = yaml.safe_load(catalog_bytes)
        registry = json.loads(registry_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError, yaml.YAMLError) as error:
        raise ContractValidationError(
            "MONO_CI_PSI_TRANSITION_REQUIREMENT_SOURCE_INVALID"
        ) from error
    if not isinstance(catalog, dict) or not isinstance(registry, dict):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_REQUIREMENT_SOURCE_INVALID")
    return {
        "catalog": catalog,
        "policy_registry": registry,
        "source_refs": [
            {
                "path": catalog_path,
                "sha256": catalog_sha,
                "source_kind": "ARCHITECTURAL_OBLIGATION_CATALOG",
            },
            {
                "path": registry_path,
                "sha256": sha256_bytes(registry_bytes),
                "source_kind": "DRAFT_POLICY_REGISTRY",
            },
        ],
    }


def _requirement_record(
    *,
    control_id: str,
    requirement_type: str,
    detail_status: str,
    value: Any,
    source_kind: str,
    source: dict[str, Any],
) -> dict[str, Any]:
    return {
        "control_id": control_id,
        "requirement_type": requirement_type,
        "detail_status": detail_status,
        "value": value,
        "source_kind": source_kind,
        "source_ref": {"path": source["path"], "sha256": source["sha256"]},
    }


def _manifest_requirements_for_evaluator(
    evaluator_id: str,
    manifest: dict[str, Any],
    state: str,
    source: dict[str, Any],
) -> list[dict[str, Any]]:
    """Extract only structured controls from architecture-side state sources."""
    requirements: list[dict[str, Any]] = []
    if evaluator_id == "AC_MODULE_GRAPH":
        for edge in manifest.get("allowed_dependencies", []):
            if (
                not isinstance(edge, dict)
                or not isinstance(edge.get("from"), str)
                or not isinstance(edge.get("to"), str)
            ):
                raise ContractValidationError(
                    "MONO_CI_PSI_TRANSITION_ARCHITECTURE_REQUIREMENT_INVALID"
                )
            requirements.append(
                _requirement_record(
                    control_id=(
                        f"architecture.module_graph.allowed_dependency:{edge['from']}->{edge['to']}"
                    ),
                    requirement_type="architecture.module_graph.allowed_dependency",
                    detail_status="SPECIFIED",
                    value={"from": edge["from"], "to": edge["to"]},
                    source_kind="VERSIONED_ARCHITECTURE_STATE_MANIFEST",
                    source=source,
                )
            )
    if evaluator_id == "AC_PUBLIC_API":
        query_port = manifest.get("reporting_query_port")
        if isinstance(query_port, dict):
            requirements.append(
                _requirement_record(
                    control_id="architecture.public_api.reporting_query_port",
                    requirement_type="architecture.public_api.reporting_query_port",
                    detail_status="SPECIFIED",
                    value=query_port,
                    source_kind="VERSIONED_ARCHITECTURE_STATE_MANIFEST",
                    source=source,
                )
            )
        for exception in manifest.get("temporary_exceptions", []):
            if not isinstance(exception, dict) or not isinstance(exception.get("id"), str):
                raise ContractValidationError(
                    "MONO_CI_PSI_TRANSITION_ARCHITECTURE_REQUIREMENT_INVALID"
                )
            requirements.append(
                _requirement_record(
                    control_id=f"architecture.public_api.temporary_exception:{exception['id']}",
                    requirement_type="architecture.public_api.temporary_exception",
                    detail_status="SPECIFIED",
                    value=exception,
                    source_kind="VERSIONED_ARCHITECTURE_STATE_MANIFEST",
                    source=source,
                )
            )
    return sorted(requirements, key=lambda row: row["control_id"])


def _manifest_governance_requirements(
    manifest: dict[str, Any], source: dict[str, Any]
) -> list[dict[str, Any]]:
    governance = manifest.get("governance_requirements", {})
    if not isinstance(governance, dict):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_GOVERNANCE_REQUIREMENTS_INVALID")
    return [
        {
            "control_id": "architecture.governance_requirements",
            "classification": "EVIDENCE_GOVERNANCE_NOT_FITNESS_CONTROL",
            "value": governance,
            "source_ref": {"path": source["path"], "sha256": source["sha256"]},
        }
    ]


def _unresolved_architecture_requirements(
    *,
    evaluator_id: str,
    manifest: dict[str, Any],
    manifest_source: dict[str, Any],
    sources: dict[str, Any],
) -> list[dict[str, Any]]:
    unresolved: list[dict[str, Any]] = []
    obligation = next(
        (
            row
            for row in sources["catalog"].get("obligations", [])
            if isinstance(row, dict) and row.get("id") == evaluator_id
        ),
        None,
    )
    if isinstance(obligation, dict):
        catalog_source = next(
            row
            for row in sources["source_refs"]
            if row["source_kind"] == "ARCHITECTURAL_OBLIGATION_CATALOG"
        )
        unresolved.append(
            _requirement_record(
                control_id=f"catalog.{evaluator_id}",
                requirement_type="catalog.architectural_obligation",
                detail_status="PARTIAL",
                value={
                    "criterion": obligation.get("criterion"),
                    "intent": obligation.get("intent"),
                },
                source_kind="ARCHITECTURAL_OBLIGATION_CATALOG",
                source=catalog_source,
            )
        )
    registry = sources["policy_registry"]
    registry_source = next(
        row for row in sources["source_refs"] if row["source_kind"] == "DRAFT_POLICY_REGISTRY"
    )
    policies = registry.get("policies", [])
    matched_policies = [
        row
        for row in policies
        if isinstance(row, dict) and evaluator_id in row.get("obligation_ids", [])
    ]
    for policy in matched_policies:
        unresolved.append(
            _requirement_record(
                control_id=f"policy_authority.{policy.get('id', evaluator_id)}",
                requirement_type="policy.authority_status",
                detail_status="UNRESOLVED",
                value={
                    "policy_id": policy.get("id"),
                    "normative_status": policy.get("normative_status"),
                    "approval_source_id": policy.get("approval_source_id"),
                    "registry_closure": registry.get("closure"),
                },
                source_kind="DRAFT_POLICY_REGISTRY",
                source=registry_source,
            )
        )
    invariants = manifest.get("invariants", {})
    if isinstance(invariants, dict) and invariants:
        unresolved.append(
            _requirement_record(
                control_id="manifest.architecture_invariants_outside_selected_evaluator_scope",
                requirement_type="architecture.invariants_without_selected_mapping",
                detail_status="UNRESOLVED",
                value=invariants,
                source_kind="VERSIONED_ARCHITECTURE_STATE_MANIFEST",
                source=manifest_source,
            )
        )
    return sorted(unresolved, key=lambda row: row["control_id"])


def _evaluator_capabilities(
    *,
    evaluator_id: str,
    state: str,
    config: dict[str, Any],
    run: dict[str, Any],
    coverage: dict[str, Any],
    representation_bound: bool,
    configuration_sha256: str,
    run_root: Path,
    config_path: str,
) -> dict[str, Any]:
    evidence = run.get("evidence", {})
    result = evidence.get("result", {})
    diagnostics = evidence.get("diagnostics", {})
    evaluator_evidence = evidence.get("evaluator", {})
    expected_commit = BEFORE_COMMIT if state == BEFORE_STATE else AFTER_COMMIT
    config_relpath = (
        f"PSI/evaluator-observations/implementation/{evaluator_id}/{Path(config_path).name}"
    )
    source_manifest_relpath = (
        f"PSI/evaluator-observations/implementation/{evaluator_id}/source-manifest.json"
    )
    output_path = run.get("output_path")
    coverage_path = _coverage_assessment_path(state, evaluator_id).as_posix()
    source_refs = [
        {"path": config_relpath, "sha256": configuration_sha256},
        {
            "path": source_manifest_relpath,
            "sha256": sha256_file(run_root / source_manifest_relpath),
        },
        {"path": str(output_path), "sha256": sha256_file(run_root / str(output_path))},
        {"path": coverage_path, "sha256": sha256_file(run_root / coverage_path)},
    ]
    run_configuration_sha256 = run.get("configuration_sha256")
    configuration_digest_verified = (
        isinstance(configuration_sha256, str)
        and SHA256_PATTERN.fullmatch(configuration_sha256) is not None
        and isinstance(run_configuration_sha256, str)
        and SHA256_PATTERN.fullmatch(run_configuration_sha256) is not None
        and run_configuration_sha256 == configuration_sha256
        and isinstance(evaluator_evidence, dict)
        and evaluator_evidence.get("configuration_digest") == configuration_sha256
    )
    base_verified = (
        representation_bound
        and run.get("source_commit_sha") == expected_commit
        and configuration_digest_verified
        and coverage.get("source_inspection_status") == "COMPLETE"
        and result.get("execution_status") == "COMPLETED"
        and result.get("compliance") == "COMPLIANT"
        and run.get("evidence", {}).get("architecture", {}).get("source_sha_status") == "MATCHED"
        and run.get("evidence", {}).get("architecture", {}).get("manifest_state_status")
        == "MATCHED"
    )
    capabilities: list[dict[str, Any]] = []

    def add_capability(
        capability_id: str, capability_type: str, verified: bool, value: dict[str, Any]
    ) -> None:
        capabilities.append(
            {
                "capability_id": capability_id,
                "capability_type": capability_type,
                "verification_status": "VERIFIED_STATIC_SCOPE" if verified else "UNVERIFIED",
                "value": value,
                "source_refs": source_refs,
            }
        )

    if evaluator_id == "AC_MODULE_GRAPH":
        graph_config = config.get("module_graph", {})
        configured_edges = graph_config.get("allowed_dependencies_by_state", {}).get(state, [])
        configured_edges = sorted(
            (dict(edge) for edge in configured_edges if isinstance(edge, dict)),
            key=lambda edge: (edge.get("from", ""), edge.get("to", "")),
        )
        analysis = coverage.get("dependency_analysis") or {}
        graph_verified = (
            base_verified
            and isinstance(diagnostics, dict)
            and diagnostics.get("allowed_edges") == configured_edges
            and analysis.get("static_relationship_comparison") == "MATCHED"
            and analysis.get("cycle_comparison") == "MATCHED"
        )
        add_capability(
            "evaluator.module_graph.allowed_dependency_policy",
            "evaluator.module_graph.allowed_dependency_policy",
            graph_verified,
            {"edges": configured_edges},
        )
        add_capability(
            "evaluator.module_graph.acyclicity",
            "evaluator.module_graph.acyclicity",
            graph_verified,
            {
                "reported_cycles": diagnostics.get("cycles", [])
                if isinstance(diagnostics, dict)
                else []
            },
        )
    else:
        public_config = config.get("public_api", {})
        public_verified = (
            base_verified
            and isinstance(diagnostics, dict)
            and diagnostics.get("public_module_pattern")
            == public_config.get("public_module_pattern")
            and diagnostics.get("interfaces_by_capability")
            == public_config.get("interfaces_by_capability")
            and diagnostics.get("legacy_exception") == public_config.get("legacy_exception")
            and isinstance(diagnostics.get("exports_by_capability"), dict)
            and isinstance(diagnostics.get("cross_capability_imports"), list)
        )
        public_value = {
            "state": state,
            "public_module_pattern": diagnostics.get("public_module_pattern")
            if isinstance(diagnostics, dict)
            else None,
            "interfaces_by_capability": diagnostics.get("interfaces_by_capability", {})
            if isinstance(diagnostics, dict)
            else {},
            "exports_by_capability": diagnostics.get("exports_by_capability", {})
            if isinstance(diagnostics, dict)
            else {},
            "cross_capability_imports": diagnostics.get("cross_capability_imports", [])
            if isinstance(diagnostics, dict)
            else [],
            "legacy_exception": diagnostics.get("legacy_exception")
            if isinstance(diagnostics, dict)
            else None,
        }
        add_capability(
            "evaluator.public_api.reporting_query_port_boundary",
            "evaluator.public_api.reporting_query_port_boundary",
            public_verified,
            public_value,
        )
        add_capability(
            "evaluator.public_api.temporary_exception_scope",
            "evaluator.public_api.temporary_exception_scope",
            public_verified,
            {"state": state, "legacy_exception": public_value["legacy_exception"]},
        )

    all_verified = bool(capabilities) and all(
        row["verification_status"] == "VERIFIED_STATIC_SCOPE" for row in capabilities
    )
    return {
        "status": (
            "VERIFIED_FOR_DECLARED_STATIC_SCOPE" if all_verified else "INCOMPLETE_OR_UNVERIFIED"
        ),
        "capabilities": sorted(capabilities, key=lambda row: row["capability_id"]),
    }


def _control_transition_summary(
    evaluator_id: str,
    config: dict[str, Any],
    before_manifest: dict[str, Any],
    after_manifest: dict[str, Any],
    before_coverage: dict[str, Any],
    after_coverage: dict[str, Any],
) -> list[str]:
    changes: list[str] = []
    if evaluator_id == "AC_PUBLIC_API":
        before_exception = config.get("public_api", {}).get("legacy_exception", {})
        before_states = before_exception.get("allowed_architecture_states", [])
        before_manifest_exceptions = before_manifest.get("temporary_exceptions", [])
        after_manifest_exceptions = after_manifest.get("temporary_exceptions", [])
        if before_manifest_exceptions != after_manifest_exceptions:
            changes.append(
                "The A0.3 Reporting-to-Tasks.service exception is absent from the A0.4 manifest; "
                "the bound configuration limits it to its listed A0.2/A0.3 states."
            )
        if AFTER_STATE not in before_states and BEFORE_STATE in before_states:
            changes.append("The configuration's legacy exception does not apply to the A0.4 state.")
    else:
        before_allowed = before_manifest.get("allowed_dependencies", [])
        after_allowed = after_manifest.get("allowed_dependencies", [])
        if before_allowed == after_allowed:
            changes.append(
                f"Both manifests retain {len(after_allowed)} module-level allowed dependency edges."
            )
        before_edges = (before_coverage.get("dependency_analysis") or {}).get(
            "expected_edge_subjects", []
        )
        after_edges = (after_coverage.get("dependency_analysis") or {}).get(
            "expected_edge_subjects", []
        )
        if before_edges != after_edges:
            changes.append(
                "Source-derived module dependency edge subjects changed from "
                f"{before_edges!r} to {after_edges!r}; policy edges remained separately defined."
            )
        else:
            changes.append("Source-derived module dependency edge subjects are unchanged.")
    if not changes:
        changes.append("No evaluator-specific control-scope change was identified.")
    return changes


def _evaluator_artifact_references(
    run_root: Path,
    run: dict[str, Any],
    binding: dict[str, Any],
    implementation_artifacts: dict[str, bytes],
) -> list[tuple[str, str]]:
    paths = [
        *implementation_artifacts,
        run["output_path"],
        run["stdout_path"],
        run["stderr_path"],
        run["inspection_scope_path"],
    ]
    refs = []
    for relative in sorted(set(paths)):
        path = run_root / relative
        if not path.is_file() or path.is_symlink():
            raise ContractValidationError("PSI_EVALUATOR_EVIDENCE_ARTIFACT_MISSING")
        refs.append((relative, sha256_file(path)))
    expected_manifest = run_root / binding["source_manifest_path"]
    if sha256_file(expected_manifest) != binding["evaluator_source_sha256"]:
        raise ContractValidationError("PSI_EVALUATOR_SOURCE_MANIFEST_DIGEST_MISMATCH")
    return refs


def _evaluator_run_record(run: dict[str, Any], run_root: Path) -> dict[str, Any]:
    return {
        "architecture_state": run["architecture_state"],
        "source_commit_sha": run["source_commit_sha"],
        "source_tree_sha": run["source_tree_sha"],
        "application_tree_sha": run["target_application_tree_sha"],
        "evaluator_id": run["evaluator_id"],
        "execution_status": run["execution_status"],
        "compliance": run["compliance"],
        "process_exit_code": run["process_exit_code"],
        "configuration_path": run["configuration_path"],
        "configuration_sha256": run["configuration_sha256"],
        "evaluator_source_sha256": run["evaluator_source_sha256"],
        "target_state_manifest_sha256": run["target_state_manifest_sha256"],
        "output_path": run["output_path"],
        "output_sha256": sha256_file(run_root / run["output_path"]),
        "stdout_path": run["stdout_path"],
        "stdout_sha256": run["stdout_sha256"],
        "stderr_path": run["stderr_path"],
        "stderr_sha256": run["stderr_sha256"],
        "inspection_scope_path": run["inspection_scope_path"],
        "inspection_scope_sha256": run["inspection_scope_sha256"],
        "started_at_utc": run["started_at_utc"],
        "ended_at_utc": run["ended_at_utc"],
        "duration_ms": run["duration_ms"],
    }


def _validate_method_result_v2(method_result: dict[str, Any]) -> None:
    decision = _governance_decision(method_result)
    prediction = method_result.get("prediction_v1")
    candidate = method_result.get("candidate_v1")
    if decision not in {"HOLD", "REJECT", "ACCEPT"}:
        raise ProtocolError("MONO_CI_PSI_TRANSITION_UNEXPECTED_METHOD_DECISION")
    if decision == "ACCEPT":
        if not isinstance(prediction, dict) or not isinstance(candidate, dict):
            raise ProtocolError("MONO_CI_PSI_TRANSITION_ACCEPT_OUTPUT_MISSING")
    elif prediction is not None or candidate is not None:
        raise ProtocolError("MONO_CI_PSI_TRANSITION_NONACCEPT_PREDICTION_PRESENT")


def _expected_evidence_obligation_ids(*, positive_add: bool) -> set[str]:
    """Return the exact TEST_ONLY evidence obligation set for a transition archive."""
    return set(EVALUATOR_IDS) | ({"AC_DATA_OWNERSHIP"} if positive_add else set())


def _verify_evidence_backed_run(
    run_root: Path,
    record: dict[str, Any],
    bundle_root: Path,
    manifest: dict[str, Any],
    method_result: dict[str, Any],
) -> None:
    positive_add = record.get("schema_version") in {
        "MONO_CI_PSI_TRANSITION_RUN_V5",
        "MONO_CI_PSI_TRANSITION_RUN_V6",
    }
    positive_context = None
    if positive_add:
        from experiments.execution.tooling.mono_ci_psi_a05_positive_add import (
            build_verified_bundle as build_positive_bundle,
        )

        key = (run_root / record["adaptation_evidence"]["key_path"]).read_bytes()
        verified, positive_context = build_positive_bundle(bundle_root, key)
        ledger_summary = positive_context.ledger_summary
    else:
        ledger, ledger_summary = build_source_inventory_fact_ledger(bundle_root)
        verified = None
    if (
        record["evidence_ledger"] != ledger_summary
        or method_result.get("evidence_ledger") != ledger_summary
    ):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_EVIDENCE_LEDGER_READBACK_MISMATCH")
    key_path = run_root / record["adaptation_evidence"]["key_path"]
    sidecar_path = run_root / record["adaptation_evidence"]["path"]
    key = key_path.read_bytes()
    sidecar_bytes = sidecar_path.read_bytes()
    sidecar = json.loads(sidecar_bytes)
    if (
        sha256_bytes(key) != record["adaptation_evidence"]["key_sha256"]
        or sha256_bytes(sidecar_bytes) != record["adaptation_evidence"]["sha256"]
        or method_result.get("adaptation_evidence_sidecar_sha256")
        != record["adaptation_evidence"]["sha256"]
    ):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_ADAPTATION_EVIDENCE_DIGEST_MISMATCH")
    trust_context = (
        positive_context.trust_context
        if positive_context is not None
        else TestOnlyEvidenceTrustContext(key)
    )
    if verified is None:
        verified = verify_v3_p_bundle(
            bundle_root, evidence_ledger=ledger, trust_context=trust_context
        )
    architecture = verified.snapshot["architecture"]
    registry = verified.snapshot["policy_registry"]
    expected_bindings = {
        "input_bundle_sha256": str(verified.manifest["bundle_sha256"]),
        "architecture_before_sha": str(architecture["before_commit"]),
        "architecture_after_sha": str(architecture["after_commit"]),
        "policy_source_revision": str(verified.manifest["policy_source_revision"]),
        "policy_bundle_sha256": str(verified.manifest["policy_bundle_sha256"]),
        "evaluation_as_of": str(architecture["evaluation_as_of"]),
        "scope": str(registry["scope"]),
    }
    verified_sidecar = verify_adaptation_evidence(
        sidecar,
        expected_bindings=expected_bindings,
        expected_source_digests=verified.source_digests,
        verifier_registry=trust_context.adaptation_evidence_verifiers,
        allow_test_only=True,
        expected_trust_scope="TEST_ONLY",
    )
    if verified_sidecar is None or verified_sidecar.trust_scope != "TEST_ONLY":
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_ADAPTATION_EVIDENCE_UNVERIFIED")
    if (
        sidecar.get("verifier_id") != TEST_ONLY_VERIFIER_ID
        or record["adaptation_evidence"]["trust_scope"] != "TEST_ONLY"
        or manifest["bundle_sha256"] != record["method_input"]["bundle_sha256"]
    ):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_ADAPTATION_EVIDENCE_BINDING_MISMATCH")

    artifact_bytes: dict[str, bytes] = {}
    for item in sidecar["payload"]["artifact_bytes"]:
        content = base64.b64decode(item["content_base64"], validate=True)
        relative = item["path"]
        if (
            sha256_bytes(content) != item["sha256"]
            or relative in artifact_bytes
            or not (run_root / relative).is_file()
            or sha256_file(run_root / relative) != item["sha256"]
        ):
            raise ContractValidationError("MONO_CI_PSI_TRANSITION_ADAPTATION_ARTIFACT_MISMATCH")
        artifact_bytes[relative] = content

    observation_index: dict[tuple[str, str], dict[str, Any]] = {}
    for row in record["evaluator_observations"]:
        key = (row["architecture_state"], row["evaluator_id"])
        if key in observation_index:
            raise ContractValidationError("MONO_CI_PSI_TRANSITION_EVALUATOR_OBSERVATION_DUPLICATE")
        observation_index[key] = row
        _verify_evaluator_observation(run_root, bundle_root, record, row)
    if set(observation_index) != {
        (state, evaluator_id)
        for state in (BEFORE_STATE, AFTER_STATE)
        for evaluator_id in EVALUATOR_IDS
    }:
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_EVALUATOR_MATRIX_INCOMPLETE")

    evidence_rows = sidecar["payload"]["evaluator_evidence"]
    proof_rows = sidecar["payload"]["pair_proofs"]
    if (
        len(evidence_rows) != (3 if positive_add else 2)
        or len(proof_rows) != (3 if positive_add else 2)
        or (sidecar["payload"].get("test_only_mandatory_classification") is not None)
        != positive_add
    ):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_PAIR_EVIDENCE_SCOPE_INVALID")
    representations = {str(row["id"]): row for row in verified.representations}
    obligations = {str(row["id"]): row for row in verified.obligations}
    if positive_add:
        ownership_template = next(
            row
            for row in verified.templates
            if row.get("template_id") == "TEMPLATE_POSITIVE_ADD_AC_DATA_OWNERSHIP_V1"
        )
        ownership_representation = ownership_template["representation"]
        representations[str(ownership_representation["id"])] = ownership_representation
    evidence_index: dict[tuple[str, str], dict[str, Any]] = {}
    for row in evidence_rows:
        pair = (row["representation_id"], row["obligation_id"])
        allowed_obligation_ids = set(EVALUATOR_IDS) | (
            {"AC_DATA_OWNERSHIP"} if positive_add else set()
        )
        if pair in evidence_index or row["obligation_id"] not in allowed_obligation_ids:
            raise ContractValidationError("MONO_CI_PSI_TRANSITION_PAIR_EVIDENCE_INVALID")
        evidence_index[pair] = row
        evidence = row["evidence"]
        refs = evidence["evidence_artifacts"]
        if positive_add and row["obligation_id"] == "AC_DATA_OWNERSHIP":
            positive_input_path = run_root / "diagnostics/positive-add-input-evaluator.json"
            positive_input = json.loads(positive_input_path.read_text(encoding="utf-8"))
            if (
                positive_input.get("schema_version")
                != "MONO_CI_A05_POSITIVE_ADD_INPUT_EVALUATOR_V1"
                or positive_input.get("classification")
                != "ACTUAL_A1_EVALUATOR_OUTPUT_USED_AS_TEST_ONLY_METHOD_INPUT"
            ):
                raise ContractValidationError(
                    "MONO_CI_PSI_TRANSITION_POSITIVE_INPUT_EVALUATOR_INVALID"
                )
            run_view = positive_input["evaluator_run"]
            coverage = positive_input["inspection_coverage"]
            expected_evidence = adapt_evaluator_evidence(
                representation=representations[row["representation_id"]],
                obligation_id=row["obligation_id"],
                run=run_view,
                artifact_refs=refs,
                coverage_verification=coverage,
            )
            expected_evidence["semantic_compatible"] = True
            expected_evidence["adequacy_proven"] = True
        else:
            observation = observation_index[(AFTER_STATE, row["obligation_id"])]
            run_view = {
                "architecture_state": observation["architecture_state"],
                "execution_status": observation["execution_status"],
                "process_exit_code": observation["process_exit_code"],
                "stdout_sha256": observation["stdout_sha256"],
                "stderr_sha256": observation["stderr_sha256"],
                "started_at_utc": observation["started_at_utc"],
                "ended_at_utc": observation["ended_at_utc"],
                "evidence": json.loads((run_root / observation["output_path"]).read_text()),
            }
            if evidence.get("schema_version") == 1:
                expected_evidence = adapt_legacy_evaluator_evidence(
                    representation=representations[row["representation_id"]],
                    obligation_id=row["obligation_id"],
                    run=run_view,
                    artifact_refs=refs,
                )
            elif evidence.get("schema_version") == 2:
                coverage_path = _coverage_assessment_path(AFTER_STATE, row["obligation_id"])
                coverage = json.loads((run_root / coverage_path).read_text(encoding="utf-8"))
                expected_evidence = adapt_evaluator_evidence(
                    representation=representations[row["representation_id"]],
                    obligation_id=row["obligation_id"],
                    run=run_view,
                    artifact_refs=refs,
                    coverage_verification=coverage,
                )
            else:
                raise ContractValidationError("MONO_CI_PSI_TRANSITION_ADAPTER_SCHEMA_UNSUPPORTED")
            if positive_add:
                expected_evidence["semantic_compatible"] = True
                expected_evidence["adequacy_proven"] = True
        if canonical_json_bytes(expected_evidence) != canonical_json_bytes(evidence):
            raise ContractValidationError("MONO_CI_PSI_TRANSITION_ADAPTER_READBACK_MISMATCH")
        if positive_add:
            if (
                evidence.get("semantic_compatible") is not True
                or evidence.get("adequacy_proven") is not True
            ):
                raise ContractValidationError(
                    "MONO_CI_PSI_TRANSITION_TEST_ONLY_PAIR_DECLARATION_INVALID"
                )
        elif (
            evidence.get("semantic_compatible") is not None
            or evidence.get("adequacy_proven") is not False
        ):
            raise ContractValidationError("MONO_CI_PSI_TRANSITION_SEMANTIC_CLAIM_UNSUPPORTED")
    expected_pairs = {
        (str(row["id"]), str(row["evaluator"]))
        for row in verified.representations
        if str(row.get("evaluator")) in EVALUATOR_IDS
    }
    if positive_add:
        expected_pairs.add((str(ownership_template["representation"]["id"]), "AC_DATA_OWNERSHIP"))
    expected_obligation_ids = _expected_evidence_obligation_ids(positive_add=positive_add)
    if (
        len(expected_pairs) != (len(EVALUATOR_IDS) + 1 if positive_add else len(EVALUATOR_IDS))
        or {obligation_id for _, obligation_id in expected_pairs} != expected_obligation_ids
        or set(evidence_index) != expected_pairs
    ):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_SELECTED_PAIR_SET_MISMATCH")

    proof_index = {(row["representation_id"], row["obligation_id"]): row for row in proof_rows}
    if set(proof_index) != set(evidence_index):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_PAIR_PROOF_SET_MISMATCH")
    for pair, pair_row in evidence_index.items():
        proof = proof_index[pair]
        subject = pair_proof_subject(
            representations[pair[0]],
            obligations[pair[1]],
            str(pair_row["evidence"]["architecture_source_sha"]),
            pair_row["evidence"],
        )
        expected_status = "VALID" if positive_add else "UNDETERMINED"
        reasons_valid = (
            proof["reason_codes"] == []
            if positive_add
            else "INDEPENDENT_SEMANTIC_ADEQUACY_NOT_ESTABLISHED" in proof["reason_codes"]
            and "NORMATIVE_MAPPING_UNAPPROVED" in proof["reason_codes"]
        )
        if (
            proof["status"] != expected_status
            or proof["verifier_id"] != TEST_ONLY_VERIFIER_ID
            or proof["subject_sha256"] != sha256_bytes(canonical_json_bytes(subject))
            or not reasons_valid
        ):
            raise ContractValidationError("MONO_CI_PSI_TRANSITION_PAIR_PROOF_AUTHORITY_INVALID")


def _verify_adaptation_necessity_report(
    run_root: Path, record: dict[str, Any], method_result: dict[str, Any]
) -> None:
    """Recompute the optional post-method diagnostic after member checksums pass."""
    if not all(
        json.loads((run_root / row["inspection_scope_path"]).read_text(encoding="utf-8")).get(
            "schema_version"
        )
        == 2
        for row in record["evaluator_observations"]
    ):
        return
    assessment_path = run_root / "diagnostics/adaptation-necessity-assessment.json"
    try:
        actual_assessment = json.loads(assessment_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ContractValidationError(
            "MONO_CI_PSI_TRANSITION_ADAPTATION_ASSESSMENT_MISSING"
        ) from error
    if not isinstance(actual_assessment, dict):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_ADAPTATION_ASSESSMENT_SCHEMA_INVALID")
    schema_version = actual_assessment.get("schema_version")
    if schema_version == "MONO_CI_PSI_ADAPTATION_NECESSITY_V1":
        # Historical V1 reports were produced by the circular token-set rule.
        # Keep their strict schema/checksum readback, but never reinterpret them
        # with the corrected V2 requirement-to-capability semantics.
        validate_payload(ADAPTATION_NECESSITY_SCHEMA_V1, actual_assessment)
        return
    if schema_version not in {
        "MONO_CI_PSI_ADAPTATION_NECESSITY_V2",
        "MONO_CI_PSI_ADAPTATION_NECESSITY_V3",
    }:
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_ADAPTATION_ASSESSMENT_SCHEMA_INVALID")
    required_diagnostic_outputs = {
        _coverage_assessment_path(state, evaluator_id).as_posix()
        for state in (BEFORE_STATE, AFTER_STATE)
        for evaluator_id in EVALUATOR_IDS
    } | {"diagnostics/adaptation-necessity-assessment.json"}
    if not required_diagnostic_outputs.issubset(record.get("output_checksums", {})):
        raise ContractValidationError(
            "MONO_CI_PSI_TRANSITION_DIAGNOSTIC_OUTPUT_CHECKSUMS_INCOMPLETE"
        )
    coverage_assessments = {
        (state, evaluator_id): json.loads(
            (run_root / _coverage_assessment_path(state, evaluator_id)).read_text(encoding="utf-8")
        )
        for state in (BEFORE_STATE, AFTER_STATE)
        for evaluator_id in EVALUATOR_IDS
    }
    evaluator_runs = []
    for observation in record["evaluator_observations"]:
        row = dict(observation)
        row["evidence"] = json.loads(
            (run_root / observation["output_path"]).read_text(encoding="utf-8")
        )
        evaluator_runs.append(row)
    assessment_schema = (
        ADAPTATION_NECESSITY_SCHEMA_V3
        if schema_version == "MONO_CI_PSI_ADAPTATION_NECESSITY_V3"
        else ADAPTATION_NECESSITY_SCHEMA_V2
    )
    validate_payload(assessment_schema, actual_assessment)
    expected_assessment = _build_adaptation_necessity_report(
        repo=REPOSITORY_ROOT,
        run_root=run_root,
        execution_id=record["execution_id"],
        baseline=record["baseline"],
        evaluator_runs=evaluator_runs,
        coverage_assessments=coverage_assessments,
        method_result=method_result,
        method_result_sha256=record["psi"]["raw_result_sha256"],
        state_manifest_sidecar=json.loads(
            (run_root / record["transition"]["state_manifest_path"]).read_text(encoding="utf-8")
        ),
    )
    if canonical_json_bytes(actual_assessment) != canonical_json_bytes(expected_assessment):
        raise ContractValidationError(
            "MONO_CI_PSI_TRANSITION_ADAPTATION_ASSESSMENT_READBACK_MISMATCH"
        )


def _verify_evaluator_observation(
    run_root: Path,
    bundle_root: Path,
    run_record: dict[str, Any],
    observation: dict[str, Any],
) -> None:
    state = observation["architecture_state"]
    before = state == BEFORE_STATE
    expected_commit = BEFORE_COMMIT if before else AFTER_COMMIT
    expected_repo_tree = BEFORE_REPOSITORY_TREE if before else AFTER_REPOSITORY_TREE
    expected_app_tree = BEFORE_APP_TREE if before else AFTER_APP_TREE
    expected_manifest_sha = (
        run_record["transition"]["before_state_manifest_sha256"]
        if before
        else run_record["transition"]["after_state_manifest_sha256"]
    )
    output_path = run_root / observation["output_path"]
    stdout_path = run_root / observation["stdout_path"]
    stderr_path = run_root / observation["stderr_path"]
    output_bytes = output_path.read_bytes()
    stdout_bytes = stdout_path.read_bytes()
    stderr_bytes = stderr_path.read_bytes()
    evidence = json.loads(output_bytes)
    inspection_scope_path = run_root / observation["inspection_scope_path"]
    inspection_scope_bytes = inspection_scope_path.read_bytes()
    expected_inspection_scope_path = (
        Path("PSI/evaluator-observations")
        / ("before" if before else "after")
        / observation["evaluator_id"]
        / "inspection-scope.json"
    ).as_posix()
    try:
        inspection_scope_record = json.loads(inspection_scope_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ContractValidationError(
            "MONO_CI_PSI_TRANSITION_EVALUATOR_INSPECTION_SCOPE_INVALID"
        ) from error
    if inspection_scope_record.get("schema_version") == 1:
        expected_inspection_scope = build_legacy_inspection_scope_artifact(
            evidence, observation["output_sha256"]
        )
    elif inspection_scope_record.get("schema_version") == 2:
        coverage_path = _coverage_assessment_path(state, observation["evaluator_id"])
        try:
            coverage_record = json.loads((run_root / coverage_path).read_text(encoding="utf-8"))
            validate_payload(INSPECTION_COVERAGE_SCHEMA, coverage_record)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ContractValidationError(
                "MONO_CI_PSI_TRANSITION_INSPECTION_COVERAGE_MISSING"
            ) from error
        implementation_root = (
            run_root / "PSI/evaluator-observations/implementation" / observation["evaluator_id"]
        )
        config_path = implementation_root / Path(observation["configuration_path"]).name
        config_bytes = config_path.read_bytes()
        state_sidecar = json.loads(
            (run_root / run_record["transition"]["state_manifest_path"]).read_text(encoding="utf-8")
        )
        manifest_label = "before" if before else "after"
        manifest_row = next(
            row for row in state_sidecar["manifests"] if row["state"] == manifest_label
        )
        expected_coverage = verify_inspection_coverage(
            repository=REPOSITORY_ROOT,
            source_commit_sha=expected_commit,
            source_tree_sha=expected_repo_tree,
            architecture_state=state,
            evaluator_id=observation["evaluator_id"],
            evaluator_configuration_bytes=config_bytes,
            state_manifest_bytes=manifest_row["content"].encode("utf-8"),
            evaluator_output_bytes=output_bytes,
            evaluator_evidence=evidence,
        )
        if canonical_json_bytes(coverage_record) != canonical_json_bytes(expected_coverage):
            raise ContractValidationError(
                "MONO_CI_PSI_TRANSITION_INSPECTION_COVERAGE_READBACK_MISMATCH"
            )
        expected_inspection_scope = build_inspection_scope_artifact(
            evidence, observation["output_sha256"], coverage_record
        )
    else:
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_INSPECTION_SCOPE_SCHEMA_UNSUPPORTED")
    if (
        sha256_bytes(output_bytes) != observation["output_sha256"]
        or sha256_bytes(stdout_bytes) != observation["stdout_sha256"]
        or sha256_bytes(stderr_bytes) != observation["stderr_sha256"]
        or observation["inspection_scope_path"] != expected_inspection_scope_path
        or sha256_bytes(inspection_scope_bytes) != observation["inspection_scope_sha256"]
        or inspection_scope_record != expected_inspection_scope
        or json.loads(stdout_bytes) != evidence
        or observation["source_commit_sha"] != expected_commit
        or observation["source_tree_sha"] != expected_repo_tree
        or observation["application_tree_sha"] != expected_app_tree
        or observation["target_state_manifest_sha256"] != expected_manifest_sha
        or observation["configuration_path"] != EVALUATOR_CONFIGS[observation["evaluator_id"]]
        or evidence["architecture"]["state"] != state
        or evidence["architecture"]["target_source_sha"] != expected_commit
        or evidence["architecture"]["manifest_digest"] != expected_manifest_sha
        or evidence["evaluator"]["source_digest"] != observation["evaluator_source_sha256"]
        or evidence["evaluator"]["configuration_digest"] != observation["configuration_sha256"]
        or evidence["result"]["execution_status"] != observation["execution_status"]
        or evidence["result"]["compliance"] != observation["compliance"]
        or _expected_evaluator_exit_code(observation["compliance"])
        != observation["process_exit_code"]
    ):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_EVALUATOR_RESULT_BINDING_MISMATCH")

    implementation_root = (
        run_root / "PSI/evaluator-observations/implementation" / observation["evaluator_id"]
    )
    source_rows = evidence["evaluator"]["source_artifacts"]
    if (
        not source_rows
        or sha256_bytes(canonical_json_bytes(source_rows)) != observation["evaluator_source_sha256"]
    ):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_EVALUATOR_SOURCE_MANIFEST_INVALID")
    for source in source_rows:
        source_file = implementation_root / "source" / source["path"]
        if not source_file.is_file() or sha256_file(source_file) != source["sha256"]:
            raise ContractValidationError("MONO_CI_PSI_TRANSITION_EVALUATOR_SOURCE_FILE_MISMATCH")
    source_manifest = implementation_root / "source-manifest.json"
    if source_manifest.read_bytes() != canonical_json_bytes(source_rows):
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_EVALUATOR_SOURCE_MANIFEST_MISMATCH")
    config_file = implementation_root / Path(observation["configuration_path"]).name
    if not config_file.is_file() or sha256_file(config_file) != observation["configuration_sha256"]:
        raise ContractValidationError("MONO_CI_PSI_TRANSITION_EVALUATOR_CONFIGURATION_MISMATCH")

    source_directory = "before" if before else "after"
    for item in evidence["source_scope"]["source_file_digests"]:
        relative = str(item["path"])
        if not relative.startswith("app/"):
            raise ContractValidationError("MONO_CI_PSI_TRANSITION_EVALUATOR_SCOPE_PATH_INVALID")
        source_file = (
            bundle_root / "architecture" / source_directory / relative.removeprefix("app/")
        )
        if not source_file.is_file() or sha256_file(source_file) != item["sha256"]:
            raise ContractValidationError("MONO_CI_PSI_TRANSITION_EVALUATOR_SCOPE_DIGEST_MISMATCH")


def _expected_evaluator_exit_code(compliance: str) -> int:
    return {
        "COMPLIANT": 0,
        "NON_COMPLIANT": 1,
        "NOT_EVALUABLE": 2,
        "UNKNOWN": 2,
        "NOT_APPLICABLE": 3,
    }[compliance]


def _git_worktree(
    repository: Path, *arguments: str, check: bool = True
) -> subprocess.CompletedProcess[str]:
    git_binary = shutil.which("git")
    if git_binary is None:
        raise ProtocolError("PSI_GIT_EXECUTABLE_MISSING")
    result = subprocess.run(  # nosec B603 # noqa: S603 - fixed Git worktree commands
        [git_binary, "worktree", *arguments],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if check and result.returncode != 0:
        raise ProtocolError("PSI_EVALUATOR_WORKTREE_OPERATION_FAILED")
    return result


def _bind_reconstructed_baseline(
    bundle_root: Path,
    proposal_bytes: bytes,
    policy: dict[str, Any],
    evaluator_bindings: dict[str, dict[str, Any]],
) -> None:
    proposal = json.loads(proposal_bytes)
    rows = []
    for row in proposal["representations"]:
        binding = evaluator_bindings[row["evaluator_id"]]
        rows.append(
            {
                "id": row["representation_id"],
                "criterion": row["criterion_id"],
                "stage": row["stage"],
                "evaluator": row["evaluator_id"],
                "covers": [row["obligation_id"]],
                "evaluator_artifact": {
                    "path": binding["source_manifest_path"],
                    "sha256": binding["evaluator_source_sha256"],
                },
                "applicability_scope": {
                    "supported_architecture_states": binding["supported_states"],
                    "state_applicability": binding["state_applicability"],
                    "supported_architecture_revisions": binding["architecture_revisions"],
                    "source_scope": binding["source_scope"],
                    "evaluation_semantics": binding["semantics"],
                    "evaluation_semantics_summary": binding["semantics_summary"],
                    "coverage_limits": binding["coverage_limits"],
                    "source_revision_binding": "EXACT_ARCHITECTURE_COMMIT_AND_TREE",
                    "approval_status": "PROPOSED_UNREVIEWED",
                },
                "evidence_contract": {
                    "schema_version": 1,
                    "contract_id": "SOURCE_BOUND_A1_EVALUATOR_EVIDENCE_V1",
                    "evaluator_evidence_schema": "evaluator_evidence.schema.json",
                    "configuration_path": binding["configuration_source_path"],
                    "configuration_sha256": binding["configuration_sha256"],
                    "evaluator_source_sha256": binding["evaluator_source_sha256"],
                    "target_manifest_digest_required": True,
                    "raw_process_streams_required": True,
                    "semantic_adequacy": "NOT_ESTABLISHED_BY_EXECUTION",
                },
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
    capabilities_path = bundle_root / "fitness/evaluator-capabilities.json"
    capabilities = json.loads(capabilities_path.read_text(encoding="utf-8"))
    capabilities["development_evaluator_bindings"] = [
        {
            "representation_id": binding["representation_id"],
            "obligation_id": binding["obligation_id"],
            "criterion_id": binding["criterion_id"],
            "evaluator_id": evaluator_id,
            "evaluator_version": binding["evaluator_version"],
            "evaluator_source_sha256": binding["evaluator_source_sha256"],
            "configuration_path": binding["configuration_source_path"],
            "configuration_sha256": binding["configuration_sha256"],
            "supported_architecture_states": binding["supported_states"],
            "state_applicability": binding["state_applicability"],
            "supported_architecture_revisions": binding["architecture_revisions"],
            "mapping_status": "PROPOSED_UNREVIEWED",
            "semantic_adequacy": "UNKNOWN",
        }
        for evaluator_id, binding in sorted(evaluator_bindings.items())
    ]
    capabilities_path.write_bytes(pretty_json_bytes(capabilities))
    _write_selected_traceability(bundle_root, evaluator_bindings, proposal)


def _write_selected_traceability(
    bundle_root: Path,
    evaluator_bindings: dict[str, dict[str, Any]],
    proposal: dict[str, Any],
) -> None:
    snapshot = json.loads((bundle_root / "architecture-policy-snapshot.json").read_text())
    registry = snapshot["policy_registry"]
    scope = str(registry["scope"])
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    node_versions: dict[str, str] = {}
    for fact in snapshot["facts"]:
        if fact.get("method_id") != "git_tree_py_module_inventory_v1":
            continue
        source_refs = list(fact.get("source_ids", []))
        nodes.append(
            {
                "id": fact["id"],
                "kind": "fact",
                "scope": scope,
                "version": "git_tree_py_module_inventory_v1",
                "source_refs": source_refs,
            }
        )
        node_versions[str(fact["id"])] = "git_tree_py_module_inventory_v1"
    for row in proposal["representations"]:
        evaluator_id = row["evaluator_id"]
        binding = evaluator_bindings[evaluator_id]
        obligation_id = row["obligation_id"]
        criterion_id = row["criterion_id"]
        representation_id = row["representation_id"]
        evaluator_node_id = f"EVALUATOR_{evaluator_id}"
        contract_node_id = f"EVIDENCE_CONTRACT_{representation_id}"
        for node_id, kind, version in (
            (obligation_id, "obligation", "PROPOSED_CATALOG_MAPPING"),
            (criterion_id, "criterion", "PROPOSED_CRITERION_MAPPING"),
            (representation_id, "representation", "RECONSTRUCTION_PROPOSAL_NOT_APPROVED"),
            (evaluator_node_id, "evaluator", binding["evaluator_version"]),
            (contract_node_id, "evidence_contract", "evaluator_evidence.schema.json:v1"),
        ):
            if not any(item["id"] == node_id for item in nodes):
                nodes.append(
                    {
                        "id": node_id,
                        "kind": kind,
                        "scope": scope,
                        "version": version,
                        "source_refs": ["P_CAPABILITIES"],
                    }
                )
                node_versions[node_id] = version
        for source_id, target_id, kind in (
            (obligation_id, criterion_id, "obligation_to_criterion"),
            (criterion_id, representation_id, "criterion_to_representation"),
            (representation_id, evaluator_node_id, "representation_to_evaluator"),
            (representation_id, contract_node_id, "representation_to_evidence_contract"),
            (evaluator_node_id, contract_node_id, "evaluator_to_evidence_contract"),
        ):
            edges.append(
                {
                    "source_id": source_id,
                    "target_id": target_id,
                    "kind": kind,
                    "source_refs": ["P_CAPABILITIES"],
                    "scope": scope,
                    "source_version": node_versions[source_id],
                    "target_version": node_versions[target_id],
                }
            )
    graph = {
        "schema_version": 1,
        "inventory_complete": False,
        "nodes": nodes,
        "edges": edges,
    }
    validate_payload("p_traceability_graph_v1.schema.json", graph)
    (bundle_root / "fitness/a0-traceability.yaml").write_text(
        yaml.safe_dump(graph, sort_keys=False), encoding="utf-8"
    )


def _reseal_method_bundle(bundle_root: Path) -> dict[str, Any]:
    manifest_path = bundle_root / METHOD_INPUT_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = {row["path"]: row for row in manifest["files"]}
    for relative, role in (
        ("fitness/a0-representations.yaml", "representation_catalog"),
        ("fitness/a0-traceability.yaml", "traceability"),
        ("fitness/evaluator-capabilities.json", "evaluator_capabilities"),
    ):
        path = bundle_root / relative
        if path.is_file():
            records[relative] = {
                "path": relative,
                "role": role,
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
        runtime_root / "experiments/pilots/__init__.py",
        package_root / "__init__.py",
    ):
        package_path.parent.mkdir(parents=True, exist_ok=True)
        package_path.write_bytes(b'"""Isolated Method P runtime package."""\n')
    shutil.copyfile(
        repository / "experiments/pilots/pilot02_testonly_execution.py",
        runtime_root / "experiments/pilots/pilot02_testonly_execution.py",
    )
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


def _runtime_module_sha256(inventory: dict[str, Any], relative_path: str) -> str:
    for row in inventory.get("files", []):
        if isinstance(row, dict) and row.get("path") == relative_path:
            digest = row.get("sha256")
            if isinstance(digest, str):
                return digest
    raise ProtocolError("MONO_CI_PSI_TRANSITION_METHOD_IDENTITY_MISSING")


class IsolatedMethodExecutionError(ProtocolError):
    """A failed isolated launch with an explicit distinction from a method result."""

    def __init__(self, message: str, *, process_started: bool, exit_code: int | None) -> None:
        super().__init__(message)
        self.process_started = process_started
        self.exit_code = exit_code


def _docker_binary() -> str:
    docker = shutil.which("docker")
    if docker is None:
        raise ProtocolError("MONO_CI_PSI_TRANSITION_DOCKER_UNAVAILABLE")
    return docker


def _docker_host_command(*args: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 # nosec B603 - fixed Docker CLI with fixed arguments
        [_docker_binary(), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
        env={"PATH": os.defpath, "LANG": "C.UTF-8"},
    )


def _uv_version_for_preflight() -> str | None:
    uv_binary = shutil.which("uv")
    if uv_binary is None:
        return None
    try:
        result = subprocess.run(  # noqa: S603 # nosec B603 - fixed uv executable and --version argv
            [uv_binary, "--version"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=10,
            env={"PATH": os.defpath, "LANG": "C.UTF-8"},
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _docker_image_platform() -> str:
    result = _docker_host_command(
        "image", "inspect", "--format", "{{.Os}}/{{.Architecture}}", ISOLATED_METHOD_IMAGE
    )
    if result.returncode != 0:
        raise ProtocolError("MONO_CI_PSI_TRANSITION_PINNED_DOCKER_IMAGE_UNAVAILABLE")
    return result.stdout.strip()


def _mount_argument(source: Path, target: str, *, read_only: bool) -> str:
    resolved = source.resolve(strict=True)
    if source.is_symlink() or "," in str(resolved):
        raise ProtocolError("MONO_CI_PSI_TRANSITION_SANDBOX_MOUNT_INVALID")
    mode = ",readonly" if read_only else ""
    return f"type=bind,source={resolved},target={target}{mode}"


def _docker_container_base_args(
    *,
    name: str,
    mounts: list[tuple[Path, str, bool]],
    network_probe_host: bool = False,
) -> list[str]:
    if _docker_image_platform() != ISOLATED_METHOD_PLATFORM:
        raise ProtocolError("MONO_CI_PSI_TRANSITION_DOCKER_PLATFORM_MISMATCH")
    uid = os.getuid()
    gid = os.getgid()
    args = [
        "create",
        "--name",
        name,
        "--pull=never",
        "--platform",
        ISOLATED_METHOD_PLATFORM,
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        "64",
        "--memory",
        "512m",
        "--cpus",
        "1.0",
        "--user",
        f"{uid}:{gid}",
        "--workdir",
        "/tmp",  # nosec B108  # noqa: S108 - private, bounded container tmpfs
        "--tmpfs",
        "/tmp:rw,nosuid,nodev,noexec,size=16777216",  # nosec B108  # noqa: S108 - private tmpfs
    ]
    if network_probe_host:
        args.extend(("--add-host", "host.docker.internal:host-gateway"))
    for source, target, read_only in mounts:
        args.extend(("--mount", _mount_argument(source, target, read_only=read_only)))
    return args


def _inspect_docker_container(
    container_id: str,
    expected_mounts: list[tuple[Path, str, bool]],
    *,
    require_network_probe_host: bool = False,
) -> dict[str, Any]:
    result = _docker_host_command("inspect", "--format", "{{json .}}", container_id)
    if result.returncode != 0:
        raise ProtocolError("MONO_CI_PSI_TRANSITION_DOCKER_INSPECT_FAILED")
    try:
        item = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ProtocolError("MONO_CI_PSI_TRANSITION_DOCKER_INSPECT_INVALID") from error
    config = item.get("Config", {})
    host = item.get("HostConfig", {})
    mounts = item.get("Mounts", [])
    actual_mounts = {
        row.get("Destination"): (Path(row.get("Source", "")).resolve(), row.get("RW"))
        for row in mounts
        if isinstance(row, dict)
    }
    expected = {
        target: (source.resolve(strict=True), not read_only)
        for source, target, read_only in expected_mounts
    }
    security_options = host.get("SecurityOpt") or []
    expected_no_new_privs = any(
        option in {"no-new-privileges", "no-new-privileges=true", "no-new-privileges:true"}
        for option in security_options
    )
    sensitive_env = {
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "ACTIONS_RUNTIME_TOKEN",
        "DOCKER_HOST",
        "DOCKER_CONFIG",
    }
    environment_names = {
        value.partition("=")[0] for value in config.get("Env", []) if isinstance(value, str)
    }
    if (
        host.get("NetworkMode") != "none"
        or host.get("ReadonlyRootfs") is not True
        or set(host.get("CapDrop") or []) != {"ALL"}
        or host.get("CapAdd")
        or not expected_no_new_privs
        or host.get("Privileged") is not False
        or host.get("Devices")
        or host.get("DeviceRequests")
        or host.get("PortBindings")
        or host.get("PidMode") == "host"
        or host.get("IpcMode") == "host"
        or config.get("User") != f"{os.getuid()}:{os.getgid()}"
        or actual_mounts != expected
        or environment_names & sensitive_env
    ):
        raise ProtocolError("MONO_CI_PSI_TRANSITION_DOCKER_ISOLATION_CONTRACT_FAILED")
    if require_network_probe_host and not any(
        isinstance(value, str) and value.startswith("host.docker.internal:")
        for value in host.get("ExtraHosts") or []
    ):
        raise ProtocolError("MONO_CI_PSI_TRANSITION_DOCKER_CANARY_MAPPING_MISSING")
    return {
        "container_id": item.get("Id"),
        "image_id": item.get("Image"),
        "network_mode": host.get("NetworkMode"),
        "readonly_rootfs": host.get("ReadonlyRootfs"),
        "cap_drop": host.get("CapDrop"),
        "security_options": security_options,
        "privileged": host.get("Privileged"),
        "user": config.get("User"),
        "mounts": [
            {
                "source": str(source),
                "target": target,
                "read_only": read_only,
            }
            for source, target, read_only in expected_mounts
        ],
        "published_ports": host.get("PortBindings"),
        "sensitive_environment_names_present": sorted(environment_names & sensitive_env),
        "verified": True,
    }


def _write_sandbox_record(path: Path, payload: dict[str, Any]) -> None:
    path.write_bytes(pretty_json_bytes(payload))


def _docker_isolation_preflight_program() -> str:
    """Return the fixed program run inside the disposable preflight container."""
    return """
import json
import os
import socket
import sys

input_path, output_path, expected, host, port, repo_git, scorer, other = sys.argv[1:]
result = {
    "python_version": sys.version.split()[0],
    "implementation": sys.implementation.name,
}
with open(input_path, encoding="utf-8") as stream:
    result["input_value"] = stream.read().strip()
output_probe_path = output_path + ".probe"
with open(output_probe_path, "w", encoding="utf-8") as stream:
    stream.write("writable\\n")
with open(output_probe_path, encoding="utf-8") as stream:
    result["output_value"] = stream.read().strip()

def denied(path):
    try:
        with open(path, "rb") as stream:
            stream.read(1)
        return False
    except OSError:
        return True

result["protected"] = {
    "repo_git": denied(repo_git),
    "scorer": denied(scorer),
    "other_arm": denied(other),
}
result["sensitive_environment_absent"] = not any(
    name in os.environ
    for name in (
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "ACTIONS_RUNTIME_TOKEN",
        "DOCKER_HOST",
        "DOCKER_CONFIG",
    )
)

def network_denied(target, target_port):
    try:
        connection = socket.create_connection((target, int(target_port)), timeout=1)
        connection.close()
        return {"denied": False}
    except OSError as error:
        return {"denied": True, "error": type(error).__name__, "errno": error.errno}

result["network"] = {
    "host_canary": network_denied(host, port),
    "external_test_target": network_denied("1.1.1.1", 443),
}
with open(output_path, "w", encoding="utf-8") as stream:
    json.dump(result, stream, sort_keys=True)
print(json.dumps(result, sort_keys=True))
ok = (
    result["python_version"] == "3.12.15"
    and result["implementation"] == "cpython"
    and result["input_value"] == expected
    and result["output_value"] == "writable"
    and all(result["protected"].values())
    and result["sensitive_environment_absent"]
    and result["network"]["host_canary"]["denied"]
    and result["network"]["external_test_target"]["denied"]
)
raise SystemExit(0 if ok else 23)
""".lstrip()


def run_docker_isolation_preflight(
    repository: Path,
    output_root: Path,
    *,
    expected_host_identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Exercise the pinned no-network container against isolated canary inputs."""
    output = output_root.expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise ProtocolError("MONO_CI_PSI_ISOLATION_PREFLIGHT_OUTPUT_MUST_BE_NEW")
    output.mkdir(parents=True)
    canary_root = output / "canaries"
    input_root = canary_root / "input"
    output_mount = canary_root / "writable-output"
    protected_root = canary_root / "protected"
    input_root.mkdir(parents=True)
    output_mount.mkdir()
    protected_root.mkdir()
    input_path = input_root / "required-input.json"
    input_path.write_text('{"probe":"readable"}\n', encoding="utf-8")
    scorer_canary = protected_root / "scorer-reference-canary.json"
    other_arm_canary = protected_root / "other-arm-canary.json"
    scorer_canary.write_text('{"canary":"protected"}\n', encoding="utf-8")
    other_arm_canary.write_text('{"canary":"protected"}\n', encoding="utf-8")
    image_digest = ISOLATED_METHOD_IMAGE.rsplit("@", 1)[-1]
    record: dict[str, Any] = {
        "schema_version": "MONO_CI_PSI_DOCKER_ISOLATION_PREFLIGHT_V1",
        "classification": "DEVELOPMENT_SANDBOX_CAPABILITY_PREFLIGHT",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "image": ISOLATED_METHOD_IMAGE,
        "image_digest": image_digest,
        "required_python_version": "3.12.15",
        "platform": ISOLATED_METHOD_PLATFORM,
        "host_identity": {},
        "network_canary": {"status": "NOT_RUN"},
        "sandbox_container": {"status": "NOT_RUN"},
        "probes": {
            "runtime_started": False,
            "required_inputs_read": False,
            "permitted_output_writable": False,
            "scorer_file_unreadable": False,
            "other_arm_file_unreadable": False,
            "repository_history_unreadable": False,
            "outbound_network_denied": False,
            "test_canary_network_denied": False,
            "sensitive_environment_absent": False,
            "docker_socket_unmounted": False,
        },
        "verification_status": "FAIL",
        "error": None,
    }
    canary_listener: socket.socket | None = None
    canary_thread: threading.Thread | None = None
    canary_state: dict[str, Any] = {"received": False, "error": None}
    container_id: str | None = None
    try:
        docker_version = _docker_host_command(
            "version", "--format", "{{.Client.Version}}|{{.Server.Version}}"
        )
        docker_info = _docker_host_command(
            "info", "--format", "{{.OSType}}|{{.Architecture}}|{{.KernelVersion}}"
        )
        if docker_version.returncode or docker_info.returncode:
            raise ProtocolError("MONO_CI_PSI_ISOLATION_PREFLIGHT_DOCKER_DAEMON_UNAVAILABLE")
        record["host_identity"] = {
            "host_os": platform.platform(),
            "host_architecture": platform.machine(),
            "runner_os": os.environ.get("RUNNER_OS", "LOCAL"),
            "runner_image_os": os.environ.get("ImageOS"),
            "runner_image_version": os.environ.get("ImageVersion"),
            "host_python_version": sys.version.split()[0],
            "host_python_implementation": platform.python_implementation(),
            "host_cpu_count": os.cpu_count(),
            "host_uid": os.getuid(),
            "host_gid": os.getgid(),
            "uv_version": _uv_version_for_preflight(),
            "docker_client_version": docker_version.stdout.strip().split("|", 1)[0],
            "docker_server_version": docker_version.stdout.strip().split("|", 1)[-1],
            "docker_daemon_platform": docker_info.stdout.strip().split("|", 2)[:2],
            "docker_kernel_version": docker_info.stdout.strip().split("|", 2)[-1],
            "python_runtime_image": ISOLATED_METHOD_IMAGE,
            "python_runtime_platform": _docker_image_platform(),
        }
        if (
            record["host_identity"]["python_runtime_platform"] != ISOLATED_METHOD_PLATFORM
            or record["host_identity"]["docker_daemon_platform"][0] != "linux"
            or not record["host_identity"]["uv_version"]
        ):
            raise ProtocolError("MONO_CI_PSI_ISOLATION_PREFLIGHT_PLATFORM_MISMATCH")
        if expected_host_identity is not None and record["host_identity"] != expected_host_identity:
            raise ProtocolError("MONO_CI_PSI_ISOLATION_PREFLIGHT_RUNNER_IDENTITY_MISMATCH")

        canary_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        canary_listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        canary_listener.bind(("0.0.0.0", 0))  # nosec B104  # noqa: S104 - ephemeral Docker bridge canary
        canary_listener.listen(1)
        canary_listener.settimeout(20)
        canary_port = canary_listener.getsockname()[1]
        canary_token = uuid.uuid4().hex

        def accept_canary() -> None:
            try:
                connection, _address = canary_listener.accept()  # type: ignore[union-attr]
                with connection:
                    canary_state["received"] = connection.recv(256).decode("ascii") == canary_token
                    connection.sendall(b"ACK")
            except (OSError, UnicodeDecodeError) as error:
                canary_state["error"] = type(error).__name__

        canary_thread = threading.Thread(target=accept_canary, daemon=True)
        canary_thread.start()
        control_code = (
            "import socket,sys;"
            "s=socket.create_connection((sys.argv[1],int(sys.argv[2])),timeout=5);"
            "s.sendall(sys.argv[3].encode());"
            "assert s.recv(16)==b'ACK';s.close()"
        )
        control_args = [
            "run",
            "--rm",
            "--pull=never",
            "--platform",
            ISOLATED_METHOD_PLATFORM,
            "--network",
            "bridge",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "16",
            "--memory",
            "128m",
            "--cpus",
            "0.25",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
        ]
        if platform.system() == "Linux":
            control_args.extend(("--add-host", "host.docker.internal:host-gateway"))
        control_args.extend(
            (
                ISOLATED_METHOD_IMAGE,
                ISOLATED_METHOD_PYTHON,
                "-I",
                "-B",
                "-c",
                control_code,
                "host.docker.internal",
                str(canary_port),
                canary_token,
            )
        )
        control = _docker_host_command(*control_args, timeout=15)
        (output / "network-canary-control.stdout.bin").write_bytes(control.stdout.encode("utf-8"))
        (output / "network-canary-control.stderr.bin").write_bytes(control.stderr.encode("utf-8"))
        canary_thread.join(timeout=2)
        if control.returncode != 0 or canary_state["received"] is not True:
            raise ProtocolError("MONO_CI_PSI_ISOLATION_PREFLIGHT_CANARY_CONTROL_FAILED")
        record["network_canary"] = {
            "status": "CONTROL_REACHABLE_FROM_BRIDGE_CONTAINER",
            "target": "host.docker.internal",
            "port": canary_port,
            "control_stdout_sha256": sha256_bytes(control.stdout.encode("utf-8")),
            "control_stderr_sha256": sha256_bytes(control.stderr.encode("utf-8")),
            "control_exit_code": control.returncode,
            "isolated_attempt_expected": "DENIED",
        }

        script = _docker_isolation_preflight_program()
        mounts = [
            (input_path, "/canary/required-input.json", True),
            (output_mount, "/canary-output", False),
        ]
        name = f"efb-preflight-{uuid.uuid4().hex}"
        command = _docker_container_base_args(name=name, mounts=mounts, network_probe_host=True)
        command.extend(
            (
                ISOLATED_METHOD_IMAGE,
                ISOLATED_METHOD_PYTHON,
                "-I",
                "-B",
                "-c",
                script,
                "/canary/required-input.json",
                "/canary-output/preflight-result.json",
                '{"probe":"readable"}',
                "host.docker.internal",
                str(canary_port),
                str(repository.resolve(strict=True) / ".git/config"),
                str(scorer_canary),
                str(other_arm_canary),
            )
        )
        created = _docker_host_command(*command)
        (output / "preflight-create.stdout.bin").write_bytes(created.stdout.encode("utf-8"))
        (output / "preflight-create.stderr.bin").write_bytes(created.stderr.encode("utf-8"))
        if created.returncode != 0:
            raise ProtocolError("MONO_CI_PSI_ISOLATION_PREFLIGHT_CONTAINER_CREATE_FAILED")
        container_id = created.stdout.strip()
        record["sandbox_container"] = _inspect_docker_container(
            container_id, mounts, require_network_probe_host=True
        )
        (output / "preflight-container-inspection.json").write_bytes(
            pretty_json_bytes(record["sandbox_container"])
        )
        execution = _docker_host_command("start", "--attach", container_id, timeout=30)
        (output / "preflight.stdout.bin").write_bytes(execution.stdout.encode("utf-8"))
        (output / "preflight.stderr.bin").write_bytes(execution.stderr.encode("utf-8"))
        inspected = _docker_host_command("inspect", "--format", "{{.State.ExitCode}}", container_id)
        exit_code = (
            int(inspected.stdout.strip()) if inspected.returncode == 0 else execution.returncode
        )
        result_path = output_mount / "preflight-result.json"
        if not result_path.is_file() or result_path.is_symlink():
            raise ProtocolError("MONO_CI_PSI_ISOLATION_PREFLIGHT_RESULT_MISSING")
        result = json.loads(result_path.read_text(encoding="utf-8"))
        record["sandbox_container"]["process_exit_code"] = exit_code
        record["sandbox_container"]["process_result"] = result
        record["probes"].update(
            {
                "runtime_started": result.get("implementation") == "cpython"
                and result.get("python_version") == "3.12.15",
                "required_inputs_read": result.get("input_value") == '{"probe":"readable"}',
                "permitted_output_writable": result.get("output_value") == "writable",
                "scorer_file_unreadable": result.get("protected", {}).get("scorer") is True,
                "other_arm_file_unreadable": result.get("protected", {}).get("other_arm") is True,
                "repository_history_unreadable": result.get("protected", {}).get("repo_git")
                is True,
                "outbound_network_denied": result.get("network", {})
                .get("external_test_target", {})
                .get("denied")
                is True,
                "test_canary_network_denied": result.get("network", {})
                .get("host_canary", {})
                .get("denied")
                is True,
                "sensitive_environment_absent": result.get("sensitive_environment_absent") is True,
                "docker_socket_unmounted": "/var/run/docker.sock"
                not in {row.get("Destination") for row in _docker_inspect_mounts(container_id)},
            }
        )
        if exit_code != 0 or not all(record["probes"].values()):
            raise ProtocolError("MONO_CI_PSI_ISOLATION_PREFLIGHT_PROBE_FAILED")
        record["verification_status"] = "PASS"
    except Exception as error:
        record["verification_status"] = "FAIL"
        record["error"] = {"type": type(error).__name__, "message": str(error)[:2000]}
    finally:
        if canary_listener is not None:
            canary_listener.close()
        if canary_thread is not None:
            canary_thread.join(timeout=1)
        if container_id is not None:
            _docker_host_command("rm", "--force", container_id)
        preflight_path = output / "sandbox-preflight.json"
        _write_sandbox_record(preflight_path, record)
        digest = sha256_file(preflight_path)
        (output / "sandbox-preflight.json.sha256").write_text(
            f"{digest}  sandbox-preflight.json\n", encoding="ascii"
        )
        record["preflight_id"] = digest
    return record


def _docker_inspect_mounts(container_id: str) -> list[dict[str, Any]]:
    inspected = _docker_host_command("inspect", "--format", "{{json .Mounts}}", container_id)
    if inspected.returncode != 0:
        raise ProtocolError("MONO_CI_PSI_TRANSITION_DOCKER_MOUNTS_UNAVAILABLE")
    value = json.loads(inspected.stdout)
    return value if isinstance(value, list) else []


def _execute_docker_isolated_method(
    repository: Path,
    runtime_root: Path,
    bundle_root: Path,
    evidence_sidecar: Path,
    verifier_key: Path,
    output: Path,
    sandbox_preflight_id: str | None = None,
) -> None:
    if sys.platform != "linux":
        raise ProtocolError("MONO_CI_PSI_TRANSITION_DOCKER_SANDBOX_REQUIRES_LINUX")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() or output.is_symlink():
        raise ProtocolError("MONO_CI_PSI_TRANSITION_METHOD_OUTPUT_PATH_INVALID")
    mounts = [
        (runtime_root, "/mnt/method-runtime", True),
        (bundle_root, "/mnt/method-input", True),
        (evidence_sidecar, "/mnt/method-evidence.json", True),
        (verifier_key, "/mnt/verifier-key", True),
        (output.parent, "/mnt/method-output", False),
    ]
    name = f"efb-method-{uuid.uuid4().hex}"
    record_path = output.parent / "sandbox-execution.json"
    stdout_path = output.parent / "method-process.stdout.bin"
    stderr_path = output.parent / "method-process.stderr.bin"
    record: dict[str, Any] = {
        "schema_version": "MONO_CI_PSI_DOCKER_SANDBOX_EXECUTION_V1",
        "backend": "PINNED_DOCKER_CONTAINER_NETWORK_NONE",
        "image": ISOLATED_METHOD_IMAGE,
        "platform": ISOLATED_METHOD_PLATFORM,
        "sandbox_preflight_id": sandbox_preflight_id,
        "container_name": name,
        "status": "CONTAINER_CREATE_IN_PROGRESS",
        "process_started": False,
        "exit_code": None,
        "started_at_utc": datetime.now(UTC).isoformat(),
        "stdout_path": "PSI/raw/method-process.stdout.bin",
        "stderr_path": "PSI/raw/method-process.stderr.bin",
        "inspection_path": "PSI/raw/sandbox-container-inspection.json",
    }
    _write_sandbox_record(record_path, record)
    container_id: str | None = None
    process_started_at = time.perf_counter()
    try:
        command = _docker_container_base_args(name=name, mounts=mounts)
        command.extend(
            (
                ISOLATED_METHOD_IMAGE,
                ISOLATED_METHOD_PYTHON,
                "-I",
                "-B",
                "/mnt/method-runtime/execute_method.py",
                "/mnt/method-input",
                "/mnt/method-evidence.json",
                "/mnt/verifier-key",
                f"/mnt/method-output/{output.name}",
            )
        )
        created = _docker_host_command(*command)
        (output.parent / "sandbox-create.stdout.bin").write_bytes(created.stdout.encode("utf-8"))
        (output.parent / "sandbox-create.stderr.bin").write_bytes(created.stderr.encode("utf-8"))
        if created.returncode != 0:
            record.update(
                {
                    "status": "CONTAINER_CREATE_FAILED",
                    "create_exit_code": created.returncode,
                    "ended_at_utc": datetime.now(UTC).isoformat(),
                }
            )
            _write_sandbox_record(record_path, record)
            raise IsolatedMethodExecutionError(
                "MONO_CI_PSI_TRANSITION_SANDBOX_CREATE_FAILED",
                process_started=False,
                exit_code=created.returncode,
            )
        container_id = created.stdout.strip()
        inspection = _inspect_docker_container(container_id, mounts)
        (output.parent / "sandbox-container-inspection.json").write_bytes(
            pretty_json_bytes(inspection)
        )
        record["container_id"] = container_id
        record["isolation_verification"] = "PASS"
        record["status"] = "CONTAINER_READY"
        _write_sandbox_record(record_path, record)
        record["status"] = "METHOD_PROCESS_RUNNING"
        record["process_started"] = True
        _write_sandbox_record(record_path, record)
        try:
            started = _docker_host_command("start", "--attach", container_id, timeout=180)
        except subprocess.TimeoutExpired as error:
            (output.parent / "method-process.stdout.bin").write_bytes(
                error.stdout if isinstance(error.stdout, bytes) else (error.stdout or "").encode()
            )
            (output.parent / "method-process.stderr.bin").write_bytes(
                error.stderr if isinstance(error.stderr, bytes) else (error.stderr or "").encode()
            )
            _docker_host_command("kill", container_id)
            record.update(
                {
                    "status": "METHOD_PROCESS_TIMED_OUT",
                    "execution_duration_ms": round(
                        (time.perf_counter() - process_started_at) * 1000, 3
                    ),
                    "ended_at_utc": datetime.now(UTC).isoformat(),
                }
            )
            _write_sandbox_record(record_path, record)
            raise IsolatedMethodExecutionError(
                "MONO_CI_PSI_TRANSITION_METHOD_PROCESS_TIMED_OUT",
                process_started=True,
                exit_code=None,
            ) from error
        stdout_path.write_bytes(started.stdout.encode("utf-8"))
        stderr_path.write_bytes(started.stderr.encode("utf-8"))
        inspected = _docker_host_command("inspect", "--format", "{{.State.ExitCode}}", container_id)
        exit_code = (
            int(inspected.stdout.strip()) if inspected.returncode == 0 else started.returncode
        )
        record.update(
            {
                "status": "COMPLETED" if exit_code == 0 else "METHOD_PROCESS_FAILED",
                "exit_code": exit_code,
                "execution_duration_ms": round(
                    (time.perf_counter() - process_started_at) * 1000, 3
                ),
                "stdout_sha256": sha256_bytes(stdout_path.read_bytes()),
                "stderr_sha256": sha256_bytes(stderr_path.read_bytes()),
                "ended_at_utc": datetime.now(UTC).isoformat(),
            }
        )
        _write_sandbox_record(record_path, record)
        if exit_code != 0:
            raise IsolatedMethodExecutionError(
                "MONO_CI_PSI_TRANSITION_METHOD_PROCESS_FAILED",
                process_started=True,
                exit_code=exit_code,
            )
    finally:
        if container_id is not None:
            _docker_host_command("rm", "--force", container_id)
    if not output.is_file() or output.is_symlink():
        raise IsolatedMethodExecutionError(
            "MONO_CI_PSI_TRANSITION_METHOD_OUTPUT_MISSING",
            process_started=True,
            exit_code=0,
        )


def _execute_isolated_method(
    repository: Path,
    runtime_root: Path,
    bundle_root: Path,
    evidence_sidecar: Path,
    verifier_key: Path,
    other_observations_root: Path,
    output: Path,
    *,
    isolation_backend: str = "legacy",
    sandbox_preflight_id: str | None = None,
) -> None:
    if isolation_backend == "docker":
        _execute_docker_isolated_method(
            repository,
            runtime_root,
            bundle_root,
            evidence_sidecar,
            verifier_key,
            output,
            sandbox_preflight_id=sandbox_preflight_id,
        )
        return
    if isolation_backend != "legacy":
        raise ProtocolError("MONO_CI_PSI_TRANSITION_ISOLATION_BACKEND_UNSUPPORTED")
    interpreter = Path(sys.executable).resolve(strict=True)
    args = [
        str(interpreter),
        "-I",
        "-B",
        str(runtime_root / "execute_method.py"),
        str(bundle_root),
        str(evidence_sidecar),
        str(verifier_key),
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
        profile.append(
            f'(deny file-read* (subpath "{_sbpl_escape(str(other_observations_root.resolve()))}"))'
        )
        profile.append(
            f'(deny file-write* (subpath "{_sbpl_escape(str(other_observations_root.resolve()))}"))'
        )
        profile.append("(allow default)")
        command = ["/usr/bin/sandbox-exec", "-p", "".join(profile), *args]
    elif sys.platform.startswith("linux") and shutil.which("bwrap"):
        command = [shutil.which("bwrap") or "bwrap", "--unshare-net", "--ro-bind", "/", "/"]
        for protected in sorted(_protected_repository_paths(repository)):
            command.extend(("--tmpfs", str(protected)))
        command.extend(("--tmpfs", str(other_observations_root.resolve())))
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
