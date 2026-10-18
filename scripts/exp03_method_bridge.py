"""Bridge validated EXP-02 observations to the verified Method P development path."""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import tempfile
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, cast

import yaml

from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError, ProtocolError
from experiments.execution.tooling.hashing import pretty_json_bytes, sha256_bytes
from experiments.execution.tooling.p_adaptation import (
    _verify_adaptation_evidence,
    run_adaptation,
    verify_v3_p_bundle,
)
from experiments.execution.tooling.p_adaptation_evidence import VerifiedAdaptationEvidence
from experiments.execution.tooling.p_applicability import EvidenceLedger
from scripts import exp02_fitness_evidence as exp02
from scripts.exp01_evidence_contract import BUNDLE_FILENAME, _safe_relative_path, validate_bundle

BRIDGE_VERSION = "EXP03_METHOD_BRIDGE_V1"
MANIFEST_FILENAME = "integration_manifest.json"
MANIFEST_DIGEST_FILENAME = "integration_manifest.sha256"
P_TRACE_FILENAME = "method_p_trace.json"
INTEGRATION_SCHEMA = "exp03_method_integration_v1.schema.json"
TRACE_SCHEMA = "exp03_method_p_execution_trace_v1.schema.json"
EXP02_ADMISSION_BLOCKER = "EXP02_EVIDENCE_NOT_ADMITTED_TO_METHOD_P"
STAGE_TRANSLATIONS = {"ci_test": "ci", "runtime": "runtime"}


def _utc_now() -> str:
    """Return a stable UTC timestamp string for this integration artifact."""
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def verify_method_p_input(
    p_input_dir: Path,
    *,
    trust_context: Any | None = None,
) -> Any:
    """Verify an explicitly supplied V3 bundle through the existing EXP-03 entrypoint."""
    return verify_v3_p_bundle(
        p_input_dir,
        evidence_ledger=EvidenceLedger({}, {}, {}),
        trust_context=trust_context,
    )


def verify_method_p_evidence_sidecar(
    p_bundle: Any,
    evidence_context: Mapping[str, Any],
) -> VerifiedAdaptationEvidence | None:
    """Verify an external sidecar against the registered V3 bundle and verifier registry."""
    policy_revision = str(p_bundle.manifest.get("policy_source_revision", ""))
    policy_digest = str(p_bundle.manifest.get("policy_bundle_sha256", ""))
    return _verify_adaptation_evidence(
        p_bundle,
        evidence_context,
        policy_revision=policy_revision,
        policy_digest=policy_digest,
    )


def run_verified_method_p(
    p_bundle: Any,
    *,
    evidence_context: Mapping[str, Any] | None = None,
) -> tuple[Any, VerifiedAdaptationEvidence | None]:
    """Run the existing P engine only after any supplied sidecar verifies.

    An unavailable verifier produces the ordinary no-sidecar P result. Invalid
    sidecars raise the existing contract error and are never passed downstream.
    """
    verified_evidence = (
        verify_method_p_evidence_sidecar(p_bundle, evidence_context)
        if evidence_context is not None
        else None
    )
    result = run_adaptation(
        p_bundle,
        evidence_context=evidence_context if verified_evidence is not None else None,
    )
    return result, verified_evidence


def _artifact_bytes(run_dir: Path, reference: Mapping[str, Any]) -> bytes:
    """Read one already validated EXP-02 artifact through its safe relative path."""
    relative = _safe_relative_path(str(reference["path"]))
    root = run_dir.resolve(strict=True)
    target = root.joinpath(*relative.parts)
    if target.is_symlink() or not target.is_file():
        raise ValueError(f"EXP-02 artifact is missing or is a symlink: {reference['path']}")
    try:
        target.resolve(strict=True).relative_to(root)
    except ValueError as error:
        raise ValueError(
            f"EXP-02 artifact escapes its run directory: {reference['path']}"
        ) from error
    content = target.read_bytes()
    if len(content) != reference["size_bytes"] or sha256_bytes(content) != reference["sha256"]:
        raise ValueError(f"EXP-02 artifact digest mismatch: {reference['path']}")
    return content


def _configuration_for_run(
    run_dir: Path, bundle: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Load the exact configuration and validation inputs copied into EXP-01."""
    input_by_source = {
        str(reference["source_path"]): dict(reference)
        for reference in bundle["input_artifacts"]
        if isinstance(reference.get("source_path"), str)
    }
    selected = bundle["fitness_configuration"]
    configuration_reference = selected["configuration_artifact"]
    catalog_reference = input_by_source.get("fitness/catalog/architectural-obligations.yaml")
    schema_reference = input_by_source.get(
        "fitness/configs/a0_1-capability-modules.dev.schema.json"
    )
    if catalog_reference is None or schema_reference is None:
        raise ValueError("EXP-02 configuration validation artifacts are missing")
    configuration = exp02.load_fitness_configuration(
        _artifact_bytes(run_dir, configuration_reference),
        _artifact_bytes(run_dir, catalog_reference),
        _artifact_bytes(run_dir, schema_reference),
    )
    return configuration, input_by_source


def _record_bindings(configuration: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Reject one evaluator record ID being configured with contradictory identities."""
    bindings: dict[str, dict[str, Any]] = {}
    for representation in configuration["representations"]:
        evaluator = representation["evaluator"]
        record_id = str(evaluator["record_id"])
        binding = {
            "evaluator_id": evaluator["id"],
            "evaluator_name": evaluator["name"],
            "stage": representation["stage"],
            "scope_id": evaluator["scope_id"],
            "configuration_artifact_source": evaluator["configuration_artifact_source"],
        }
        previous = bindings.get(record_id)
        if previous is not None and previous != binding:
            raise ValueError(f"contradictory evaluator record binding: {record_id}")
        bindings[record_id] = binding
    return bindings


def _target_candidates(
    p_representations: Sequence[Mapping[str, Any]],
    *,
    criterion_id: str,
    obligation_id: str,
    stage: str,
) -> list[Mapping[str, Any]]:
    """Find exact criterion, obligation and translated-stage matches in verified P input."""
    return [
        representation
        for representation in p_representations
        if representation.get("criterion") == criterion_id
        and obligation_id in representation.get("covers", [])
        and representation.get("stage") == stage
    ]


def _map_representations(
    evidence: Mapping[str, Any],
    configuration: Mapping[str, Any],
    p_representations: Sequence[Mapping[str, Any]] | None,
    *,
    p_after_revision: str | None,
) -> list[dict[str, Any]]:
    """Map stable EXP-02 identities without turning observations into semantic proof."""
    configured_by_id = {str(item["id"]): item for item in configuration["representations"]}
    used_pairs: dict[tuple[str, str, str], tuple[str, str]] = {}
    mappings: list[dict[str, Any]] = []

    for item in evidence["representations"]:
        representation_id = str(item["representation_id"])
        configured = configured_by_id[representation_id]
        evaluator = configured["evaluator"]
        execution = item["evaluator_execution"]
        source_stage = str(item["lifecycle_stage"])
        target_stage = STAGE_TRANSLATIONS.get(source_stage)
        source_scope_id = str(evaluator["scope_id"])
        obligations = [str(value) for value in item["declared_obligations"]]
        if not obligations or len(obligations) != len(set(obligations)):
            raise ValueError(f"duplicate or empty obligation binding: {representation_id}")

        for obligation_id in obligations:
            target: Mapping[str, Any] | None = None
            mapping_status = "not_available"
            stage_status = "not_available" if p_representations is None else "unsupported"
            candidates: list[Mapping[str, Any]] = []
            if p_representations is not None and target_stage is not None:
                stage_status = "translated"
                candidates = _target_candidates(
                    p_representations,
                    criterion_id=str(item["criterion_id"]),
                    obligation_id=obligation_id,
                    stage=target_stage,
                )
                if len(candidates) > 1:
                    raise ValueError(
                        f"ambiguous EXP-02-to-P mapping for {representation_id}/{obligation_id}"
                    )
                if candidates:
                    target = candidates[0]
                    mapping_status = "candidate_only"
                else:
                    mapping_status = "unsupported"
            elif p_representations is not None:
                mapping_status = "unsupported"

            target_id = str(target["id"]) if target is not None else None
            pair_key = (target_id or "", obligation_id, str(evidence["source_revision"]))
            if target_id is not None:
                previous = used_pairs.get(pair_key)
                binding = (representation_id, str(execution["record_id"]))
                if previous is not None:
                    raise ValueError(
                        "duplicate or contradictory canonical pair binding: "
                        f"{target_id}/{obligation_id} from {previous} and {binding}"
                    )
                used_pairs[pair_key] = binding

            target_scope = (
                dict(target.get("applicability_scope", {}))
                if target is not None and isinstance(target.get("applicability_scope"), Mapping)
                else {}
            )
            target_scope_id = target_scope.get("scope_id")
            if target is None:
                scope_status = "not_available" if p_representations is None else "unrepresented"
            elif target_scope_id == source_scope_id:
                scope_status = "exact"
            elif not target_scope:
                scope_status = "unrepresented"
            else:
                scope_status = "mismatch"

            target_evaluator = str(target["evaluator"]) if target is not None else None
            if target is None:
                evaluator_status = "not_available" if p_representations is None else "unrepresented"
            elif target_evaluator in {str(evaluator["id"]), str(evaluator["name"])}:
                evaluator_status = "exact"
            else:
                evaluator_status = "unverified"

            source_metric_names = sorted({str(metric["name"]) for metric in item["metrics"]})
            target_metric_names = (
                {str(name) for name in target.get("metrics", [])} if target is not None else set()
            )
            matching_metrics = sorted(set(source_metric_names).intersection(target_metric_names))
            if not target_metric_names or not source_metric_names:
                metric_status = "unverified"
            elif set(source_metric_names) == target_metric_names:
                metric_status = "exact"
            elif matching_metrics:
                metric_status = "partial"
            else:
                metric_status = "unmatched"

            revision_status = (
                "exact_after_revision"
                if p_after_revision == evidence["source_revision"]
                else "unverified"
                if p_after_revision is None
                else "mismatch"
            )
            reason_codes: list[str] = []
            if mapping_status == "unsupported":
                reason_codes.append("P_CANONICAL_REPRESENTATION_UNAVAILABLE")
            if stage_status == "unsupported":
                reason_codes.append("UNSUPPORTED_LIFECYCLE_STAGE")
            if scope_status in {"unrepresented", "mismatch"}:
                reason_codes.append("P_SCOPE_MAPPING_UNVERIFIED")
            if evaluator_status in {"unrepresented", "unverified"}:
                reason_codes.append("P_EVALUATOR_BINDING_UNVERIFIED")
            if metric_status in {"partial", "unmatched", "unverified"}:
                reason_codes.append("P_METRIC_MAPPING_UNVERIFIED")
            if revision_status != "exact_after_revision":
                reason_codes.append("ARCHITECTURE_REVISION_NOT_BOUND")

            mappings.append(
                {
                    "exp02_representation_id": representation_id,
                    "criterion_id": str(item["criterion_id"]),
                    "obligation_id": obligation_id,
                    "evaluator_id": str(item["evaluator_id"]),
                    "evaluator_record_id": str(execution["record_id"]),
                    "evaluator_name": str(execution["evaluator_name"]),
                    "source_stage": source_stage,
                    "source_scope_id": source_scope_id,
                    "source_revision": str(evidence["source_revision"]),
                    "target_representation_id": target_id,
                    "target_stage": target_stage,
                    "target_evaluator": target_evaluator,
                    "target_scope": target_scope,
                    "mapping_status": mapping_status,
                    "stage_mapping_status": stage_status,
                    "evaluator_binding_status": evaluator_status,
                    "scope_mapping_status": scope_status,
                    "metric_mapping_status": metric_status,
                    "matching_metric_names": matching_metrics,
                    "revision_binding_status": revision_status,
                    "semantic_pair_proof_status": "not_supplied",
                    "coverage_claim_status": "not_established",
                    "evaluator_execution": dict(execution),
                    "compliance_observation": dict(item["compliance_observation"]),
                    "scope_binding_status": str(item["scope_binding_status"]),
                    "metrics": [dict(metric) for metric in item["metrics"]],
                    "evidence_references": [
                        dict(reference) for reference in item["evidence_references"]
                    ],
                    "limitations": sorted(
                        set(str(value) for value in item["limitations"]) | set(reason_codes)
                    ),
                    "reason_codes": sorted(set(reason_codes)),
                }
            )
    return mappings


def _a0_frozen_revision(p_bundle: Any) -> str | None:
    """Read the frozen A0 revision from the digest-verified parent representation catalog."""
    catalog_path = p_bundle.root / "fitness/a0-representations.yaml"
    if catalog_path.is_symlink() or not catalog_path.is_file():
        return None
    try:
        catalog_path.resolve(strict=True).relative_to(p_bundle.root.resolve(strict=True))
        catalog = yaml.safe_load(catalog_path.read_bytes())
    except (OSError, ValueError, yaml.YAMLError):
        return None
    provenance = catalog.get("provenance") if isinstance(catalog, Mapping) else None
    revision = provenance.get("frozen_source_revision") if isinstance(provenance, Mapping) else None
    return revision if isinstance(revision, str) else None


def _adaptation_trace(p_bundle: Any, result: Any) -> dict[str, Any]:
    """Serialize the existing Method P result without adding a second decision engine."""
    input_manifest_bytes = (p_bundle.root / "method_input_v3.json").read_bytes()
    return {
        "schema_version": "1.1.0",
        "trace_type": "development_method_p_execution",
        "input_bundle_sha256": p_bundle.manifest["bundle_sha256"],
        "input_manifest_sha256": sha256_bytes(input_manifest_bytes),
        "policy_source_revision": p_bundle.manifest["policy_source_revision"],
        "policy_bundle_sha256": p_bundle.manifest["policy_bundle_sha256"],
        "snapshot_validation": p_bundle.snapshot_validation.to_dict(),
        "architecture": {
            "before_commit": p_bundle.snapshot["architecture"]["before_commit"],
            "after_commit": p_bundle.snapshot["architecture"]["after_commit"],
        },
        "before_applicability": result.before_applicability.to_dict(),
        "after_applicability": result.after_applicability.to_dict(),
        "impact_assessment": result.impact.to_dict(),
        "current_pairs": [pair.to_dict() for pair in result.current_pairs],
        "candidate_pairs": [pair.to_dict() for pair in result.candidate_pairs],
        "current_coverage": result.current_coverage.to_dict(),
        "candidate_coverage": (
            result.candidate_coverage.to_dict() if result.candidate_coverage is not None else None
        ),
        "operation_plan": result.operation_plan.to_dict(),
        "candidate_configuration": (
            dict(result.candidate) if isinstance(result.candidate, Mapping) else None
        ),
        "candidate_sha256": result.candidate_sha256,
        "governance": result.governance.to_dict(),
        "candidate_v1": dict(result.candidate_v1) if result.candidate_v1 is not None else None,
        "prediction_v1": dict(result.prediction_v1) if result.prediction_v1 is not None else None,
        "adaptation_evidence_trust_scope": result.evidence_trust_scope,
        "exp02_observations_used_as_semantic_pair_evidence": False,
        "exp02_evidence_admission_status": "not_admitted",
        "exp02_evidence_admitted_to_p_calculations": False,
        "adaptation_evidence_sidecar_supplied": False,
        "unresolved_prerequisites": sorted(
            set(result.governance.to_dict()["reason_codes"])
            | set(result.operation_plan.hold_reasons)
            | set(result.operation_plan.reject_reasons)
        ),
    }


def _blocker(code: str, details: str) -> dict[str, str]:
    return {"code": code, "details": details}


def _load_exp02(
    exp02_run_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], bytes]:
    """Run both existing EXP-01 and EXP-02 validators and retain exact input bytes."""
    if exp02_run_dir.is_symlink():
        raise ValueError("EXP-02 run directory must not be a symlink")
    run_dir = exp02_run_dir.resolve(strict=True)
    bundle = validate_bundle(run_dir)
    evidence = exp02.validate_representation_evidence(run_dir, bundle)
    if bundle.get("schema_version") != "1.2.0":
        raise ValueError("EXP-03 requires an EXP-01 v1.2.0 bundle with EXP-02 evidence")
    if evidence.get("architecture_state") != exp02.EXPECTED_ARCHITECTURE_STATE:
        raise ValueError("EXP-02 architecture identity is incompatible with the bridge")
    configuration, _ = _configuration_for_run(run_dir, bundle)
    _record_bindings(configuration)
    bundle_bytes = (run_dir / BUNDLE_FILENAME).read_bytes()
    return bundle, evidence, configuration, bundle_bytes


def _exp02_input_payload(
    run_dir: Path,
    bundle: Mapping[str, Any],
    evidence: Mapping[str, Any],
    bundle_bytes: bytes,
) -> dict[str, Any]:
    """Serialize validated EXP-02 references without implying semantic proof."""
    representation_reference = bundle["fitness_representation_evidence"]
    return {
        "run_directory": str(run_dir.resolve(strict=True)),
        "run_id": str(bundle["run_id"]),
        "bundle_schema_version": str(bundle["schema_version"]),
        "bundle_status": str(bundle["bundle_status"]),
        "artifact_validation_status": "validated_by_exp01_exp02_contracts",
        "independent_semantic_validation_status": "not_independently_validated",
        "bundle_reference": {
            "path": BUNDLE_FILENAME,
            "sha256": sha256_bytes(bundle_bytes),
            "size_bytes": len(bundle_bytes),
            "media_type": "application/json",
            "role": "exp01_evidence_bundle",
            "source_path": None,
        },
        "representation_evidence_reference": dict(representation_reference),
        "source_revision": str(evidence["source_revision"]),
        "architecture_state": str(evidence["architecture_state"]),
        "fitness_configuration": {
            "configuration_id": evidence["fitness_configuration"]["configuration_id"],
            "configuration_version": evidence["fitness_configuration"]["configuration_version"],
            "configuration_sha256": evidence["fitness_configuration"]["configuration_sha256"],
            "configuration_artifact": dict(
                evidence["fitness_configuration"]["configuration_artifact"]
            ),
            "provenance_status": evidence["fitness_configuration"]["provenance_status"],
        },
        "input_artifacts": [dict(reference) for reference in bundle["input_artifacts"]],
        "evaluator_records": [
            {
                "record_id": str(record["record_id"]),
                "evaluator_name": str(record["evaluator_name"]),
                "lifecycle_stage": str(record["lifecycle_stage"]),
                "status": str(record["status"]),
                "execution_verdict": str(record["execution_verdict"]),
                "source_revision": str(record["source_revision"]),
                "scope_id": str(record["scope_id"]),
                "raw_output_artifacts": [
                    dict(reference) for reference in record["raw_output_artifacts"]
                ],
            }
            for record in bundle["records"]
        ],
        "coverage_claims": dict(evidence["coverage_claims"]),
        "limitations": sorted(set(str(value) for value in evidence["limitations"])),
    }


def build_integration_artifact(
    exp02_run_dir: Path,
    *,
    p_input_dir: Path | None = None,
    invocation: Sequence[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Validate EXP-02, optionally run verified V3 Method P, and build its manifest."""
    bundle, evidence, configuration, bundle_bytes = _load_exp02(exp02_run_dir)
    run_dir = exp02_run_dir.resolve(strict=True)
    exp02_input = _exp02_input_payload(run_dir, bundle, evidence, bundle_bytes)

    p_input_status = "not_supplied"
    p_verification_status = "not_supplied"
    p_manifest_sha: str | None = None
    p_manifest_reference: dict[str, Any] | None = None
    p_bundle_sha: str | None = None
    before_sha: str | None = None
    after_sha: str | None = None
    delta_a1_status = "not_assessed"
    p_execution_status = "not_run"
    p_governance_result = "not_run"
    p_reason_codes: list[str] = []
    p_trace: dict[str, Any] | None = None
    p_representations: Sequence[Mapping[str, Any]] | None = None
    blockers: list[dict[str, str]] = [
        _blocker(
            EXP02_ADMISSION_BLOCKER,
            "EXP-02 evidence is validated and mapped for diagnostics but is not admitted "
            "to Method P calculations by the current V3 trust and sidecar contracts.",
        )
    ]
    verified_p_bundle: Any | None = None

    if p_input_dir is None:
        blockers.append(
            _blocker(
                "P_V3_INPUT_REQUIRED",
                "Pass an explicitly prepared and verified V3 Method P input bundle.",
            )
        )
    else:
        if p_input_dir.is_symlink():
            p_input_status = "rejected"
            p_verification_status = "rejected"
            blockers.append(_blocker("P_V3_INPUT_REJECTED", "The P input root is a symlink."))
        else:
            try:
                verified_p_bundle = verify_v3_p_bundle(
                    p_input_dir,
                    evidence_ledger=EvidenceLedger({}, {}, {}),
                )
            except (OSError, ValueError, ProtocolError, ContractValidationError) as error:
                p_input_status = "rejected"
                p_verification_status = "rejected"
                blockers.append(_blocker("P_V3_INPUT_REJECTED", str(error)))
            else:
                p_input_status = "verified"
                p_verification_status = "verified"
                p_bundle_sha = str(verified_p_bundle.manifest["bundle_sha256"])
                manifest_path = verified_p_bundle.root / "method_input_v3.json"
                p_manifest_bytes = manifest_path.read_bytes()
                p_manifest_sha = sha256_bytes(p_manifest_bytes)
                p_manifest_reference = {
                    "path": "method_input_v3.json",
                    "sha256": p_manifest_sha,
                    "size_bytes": len(p_manifest_bytes),
                    "media_type": "application/json",
                    "role": "method_p_v3_input_manifest",
                    "source_path": None,
                }
                architecture = verified_p_bundle.snapshot["architecture"]
                before_sha = str(architecture["before_commit"])
                after_sha = str(architecture["after_commit"])
                p_representations = verified_p_bundle.representations
                frozen_a0_sha = _a0_frozen_revision(verified_p_bundle)
                if after_sha != evidence["source_revision"]:
                    p_input_status = "incompatible"
                    delta_a1_status = "mismatch"
                    blockers.append(
                        _blocker(
                            "P_INPUT_AFTER_REVISION_MISMATCH",
                            "The V3 P after revision does not equal the EXP-02 source revision.",
                        )
                    )
                elif frozen_a0_sha is None or before_sha != frozen_a0_sha:
                    p_input_status = "incompatible"
                    delta_a1_status = "mismatch"
                    blockers.append(
                        _blocker(
                            "DELTA_A1_BEFORE_REVISION_MISMATCH",
                            "The verified V3 P before revision is not the frozen A0 source "
                            "revision declared by its pinned representation catalog.",
                        )
                    )
                else:
                    delta_a1_status = "verified"

    mappings = _map_representations(
        evidence,
        configuration,
        p_representations,
        p_after_revision=after_sha,
    )
    if verified_p_bundle is not None and p_input_status == "verified":
        result = run_adaptation(verified_p_bundle)
        p_trace = _adaptation_trace(verified_p_bundle, result)
        p_execution_status = "completed"
        p_governance_result = result.governance.result.value
        p_reason_codes = list(p_trace["unresolved_prerequisites"])
        if p_governance_result == "HOLD":
            blockers.extend(
                _blocker(code, "Existing Method P governance returned HOLD.")
                for code in p_reason_codes
            )
        elif p_governance_result == "REJECT":
            blockers.extend(
                _blocker(code, "Existing Method P governance returned REJECT.")
                for code in p_reason_codes
            )

    output_inventory: list[dict[str, Any]] = []
    if p_trace is not None:
        trace_bytes = pretty_json_bytes(p_trace)
        output_inventory.append(
            {
                "path": P_TRACE_FILENAME,
                "sha256": sha256_bytes(trace_bytes),
                "size_bytes": len(trace_bytes),
                "media_type": "application/json",
                "role": "method_p_trace",
            }
        )

    integration_status = (
        "blocked"
        if p_execution_status != "completed"
        else "completed_with_hold"
        if p_governance_result == "HOLD"
        else "completed_with_reject"
        if p_governance_result == "REJECT"
        else "completed"
    )
    schema_directory = Path(__file__).resolve().parents[1] / "experiments/execution/schemas"
    schema_path = schema_directory / INTEGRATION_SCHEMA
    trace_schema_path = schema_path.with_name(TRACE_SCHEMA)
    if p_trace is not None:
        validate_payload(TRACE_SCHEMA, p_trace)
    manifest: dict[str, Any] = {
        "schema_version": "1.1.0",
        "artifact_type": "exp03_method_integration",
        "integration_status": integration_status,
        "created_at_utc": _utc_now(),
        "reproducibility": {
            "bridge_version": BRIDGE_VERSION,
            "bridge_source_sha256": sha256_bytes(Path(__file__).read_bytes()),
            "schema_sha256": sha256_bytes(schema_path.read_bytes()),
            "trace_schema_sha256": sha256_bytes(trace_schema_path.read_bytes()),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "invocation": list(invocation or sys.argv),
        },
        "exp02_input": exp02_input,
        "evidence_flow": {
            "exp02_contract_validation_status": "validated",
            "representation_mapping_status": "generated",
            "method_p_input_verification_status": p_verification_status,
            "method_p_execution_status": p_execution_status,
            "exp02_evidence_admission_status": "not_admitted",
            "admission_blocker_code": EXP02_ADMISSION_BLOCKER,
        },
        "representation_mappings": mappings,
        "coverage_claims": {
            "Coverage_P": "not_assessed",
            "Coverage_ref": "not_established",
            "semantic_validity": "not_independently_validated",
        },
        "method_p": {
            "input_status": p_input_status,
            "input_directory": str(p_input_dir.resolve(strict=False)) if p_input_dir else None,
            "input_bundle_sha256": p_bundle_sha,
            "input_manifest_sha256": p_manifest_sha,
            "input_manifest_reference": p_manifest_reference,
            "architecture_before_sha": before_sha,
            "architecture_after_sha": after_sha,
            "delta_a1_revision_binding": delta_a1_status,
            "trust_context_supplied": False,
            "adaptation_evidence_sidecar_supplied": False,
            "exp02_observations_used_as_semantic_pair_evidence": False,
            "execution_status": p_execution_status,
            "trace_reference": (dict(output_inventory[0]) if output_inventory else None),
            "governance_result": p_governance_result,
            "reason_codes": sorted(set(p_reason_codes)),
            "prediction_v1_emitted": bool(p_trace and p_trace["prediction_v1"] is not None),
        },
        "blockers": blockers,
        "artifact_inventory": output_inventory,
    }
    validate_payload(INTEGRATION_SCHEMA, manifest)
    return manifest, p_trace


def validate_integration_output(output_dir: Path) -> dict[str, Any]:
    """Read back a complete integration output and verify every generated digest."""
    if output_dir.is_symlink():
        raise ValueError("EXP-03 output directory must not be a symlink")
    root = output_dir.resolve(strict=True)
    manifest_path = root / MANIFEST_FILENAME
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("EXP-03 integration manifest is missing or is a symlink")
    manifest_bytes = manifest_path.read_bytes()
    try:
        parsed = json.loads(manifest_bytes)
    except json.JSONDecodeError as error:
        raise ValueError("EXP-03 integration manifest is invalid JSON") from error
    if not isinstance(parsed, dict):
        raise ValueError("EXP-03 integration manifest must be an object")
    validate_payload(INTEGRATION_SCHEMA, parsed)

    declared: dict[str, Mapping[str, Any]] = {}
    trace_payload: dict[str, Any] | None = None
    for reference in parsed["artifact_inventory"]:
        relative = PurePosixPath(str(reference["path"]))
        if relative.is_absolute() or ".." in relative.parts or str(reference["path"]) in declared:
            raise ValueError("EXP-03 output inventory contains an unsafe or duplicate path")
        target = root.joinpath(*relative.parts)
        if target.is_symlink() or not target.is_file():
            raise ValueError(f"EXP-03 generated artifact is missing: {relative.as_posix()}")
        try:
            target.resolve(strict=True).relative_to(root)
        except ValueError as error:
            raise ValueError(f"EXP-03 generated artifact escapes output: {relative}") from error
        content = target.read_bytes()
        if len(content) != reference["size_bytes"] or sha256_bytes(content) != reference["sha256"]:
            raise ValueError(f"EXP-03 output digest mismatch: {relative.as_posix()}")
        if reference["role"] == "method_p_trace":
            try:
                trace = json.loads(content)
            except json.JSONDecodeError as error:
                raise ValueError("EXP-03 Method P trace is invalid JSON") from error
            validate_payload(TRACE_SCHEMA, trace)
            if not isinstance(trace, dict):
                raise ValueError("EXP-03 Method P trace must be an object")
            trace_payload = trace
        declared[relative.as_posix()] = reference
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name not in {MANIFEST_FILENAME, MANIFEST_DIGEST_FILENAME}
    }
    if actual != set(declared):
        raise ValueError("EXP-03 output inventory does not exactly match generated artifacts")
    digest_path = root / MANIFEST_DIGEST_FILENAME
    if digest_path.is_symlink() or not digest_path.is_file():
        raise ValueError("EXP-03 manifest digest file is missing")
    expected_digest_line = f"{sha256_bytes(manifest_bytes)}  {MANIFEST_FILENAME}\n"
    if digest_path.read_text(encoding="ascii") != expected_digest_line:
        raise ValueError("EXP-03 manifest digest file does not match the manifest")
    _validate_exp02_source_references(parsed)
    _validate_v3_input_reference(parsed)
    _validate_manifest_trace_consistency(parsed, declared, trace_payload)
    return cast(dict[str, Any], parsed)


def _validate_exp02_source_references(manifest: Mapping[str, Any]) -> None:
    """Re-run the EXP-01/02 contracts before treating input digests as validated refs."""
    exp02_input = manifest["exp02_input"]
    source_dir = Path(str(exp02_input["run_directory"]))
    try:
        bundle, evidence, _, bundle_bytes = _load_exp02(source_dir)
        expected = _exp02_input_payload(
            source_dir.resolve(strict=True), bundle, evidence, bundle_bytes
        )
    except (OSError, ValueError, ProtocolError, ContractValidationError) as error:
        raise ValueError("EXP-03 referenced EXP-02 source failed contract revalidation") from error
    if exp02_input != expected:
        raise ValueError("EXP-03 EXP-02 source references disagree with validated source artifacts")


def _validate_v3_input_reference(manifest: Mapping[str, Any]) -> None:
    """Re-run the existing V3 verifier for an input claimed as independently verified."""
    method_p = manifest["method_p"]
    evidence_flow = manifest["evidence_flow"]
    verification_status = evidence_flow["method_p_input_verification_status"]
    expected_status = {
        "not_supplied": "not_supplied",
        "rejected": "rejected",
        "verified": "verified",
        "incompatible": "verified",
    }[method_p["input_status"]]
    if verification_status != expected_status:
        raise ValueError(
            "EXP-03 evidence-flow V3 verification status disagrees with Method P input status"
        )
    if verification_status != "verified":
        if (
            method_p["input_bundle_sha256"] is not None
            or method_p["input_manifest_sha256"] is not None
            or method_p["input_manifest_reference"] is not None
        ):
            raise ValueError("EXP-03 unverified V3 input cannot carry verified input references")
        return

    input_dir = Path(str(method_p["input_directory"]))
    try:
        p_bundle = verify_v3_p_bundle(input_dir, evidence_ledger=EvidenceLedger({}, {}, {}))
        manifest_bytes = (p_bundle.root / "method_input_v3.json").read_bytes()
    except (OSError, ValueError, ProtocolError, ContractValidationError) as error:
        raise ValueError(
            "EXP-03 referenced V3 Method P input failed verifier revalidation"
        ) from error
    expected_reference = {
        "path": "method_input_v3.json",
        "sha256": sha256_bytes(manifest_bytes),
        "size_bytes": len(manifest_bytes),
        "media_type": "application/json",
        "role": "method_p_v3_input_manifest",
        "source_path": None,
    }
    if (
        method_p["input_bundle_sha256"] != p_bundle.manifest["bundle_sha256"]
        or method_p["input_manifest_sha256"] != expected_reference["sha256"]
        or method_p["input_manifest_reference"] != expected_reference
        or method_p["architecture_before_sha"] != p_bundle.snapshot["architecture"]["before_commit"]
        or method_p["architecture_after_sha"] != p_bundle.snapshot["architecture"]["after_commit"]
    ):
        raise ValueError("EXP-03 V3 Method P input references disagree with the verified bundle")


def _validate_manifest_trace_consistency(
    manifest: Mapping[str, Any],
    declared: Mapping[str, Mapping[str, Any]],
    trace: Mapping[str, Any] | None,
) -> None:
    """Reject digest-valid outputs whose manifest and execution trace disagree."""
    method_p = manifest["method_p"]
    evidence_flow = manifest["evidence_flow"]
    trace_references = [
        reference
        for reference in manifest["artifact_inventory"]
        if reference["role"] == "method_p_trace"
    ]
    if len(manifest["artifact_inventory"]) != len(trace_references) or len(trace_references) > 1:
        raise ValueError("EXP-03 artifact inventory contains an unexpected generated artifact")
    execution_completed = method_p["execution_status"] == "completed"
    if execution_completed != (trace is not None and len(trace_references) == 1):
        raise ValueError("EXP-03 trace presence disagrees with Method P execution status")
    if execution_completed:
        trace_reference = trace_references[0]
        if method_p["trace_reference"] != trace_reference:
            raise ValueError("EXP-03 manifest and Method P trace disagree: trace reference")
    elif method_p["trace_reference"] is not None:
        raise ValueError("EXP-03 trace reference exists without a completed Method P execution")

    blocker_codes = {item["code"] for item in manifest["blockers"]}
    if evidence_flow["admission_blocker_code"] != EXP02_ADMISSION_BLOCKER:
        raise ValueError("EXP-03 EXP-02 evidence admission blocker is missing or invalid")
    if EXP02_ADMISSION_BLOCKER not in blocker_codes:
        raise ValueError("EXP-03 EXP-02 evidence admission blocker is absent from blockers")
    if evidence_flow["exp02_evidence_admission_status"] != "not_admitted":
        raise ValueError("EXP-03 cannot claim EXP-02 evidence was admitted to Method P")
    if evidence_flow["method_p_execution_status"] != method_p["execution_status"]:
        raise ValueError("EXP-03 evidence-flow execution status disagrees with Method P")
    expected_input_verification = {
        "not_supplied": "not_supplied",
        "rejected": "rejected",
        "verified": "verified",
        "incompatible": "verified",
    }[method_p["input_status"]]
    if evidence_flow["method_p_input_verification_status"] != expected_input_verification:
        raise ValueError("EXP-03 evidence-flow V3 verification status disagrees with Method P")

    expected_integration_status: str | None
    if trace is None:
        if method_p["governance_result"] != "not_run":
            raise ValueError("EXP-03 governance result exists without a Method P trace")
        if method_p["reason_codes"] or method_p["prediction_v1_emitted"]:
            raise ValueError("EXP-03 P-derived output claims exist without a Method P trace")
        expected_integration_status = "blocked"
    else:
        if trace["input_bundle_sha256"] != method_p["input_bundle_sha256"]:
            raise ValueError("EXP-03 manifest and Method P trace disagree: input bundle identity")
        if trace["input_manifest_sha256"] != method_p["input_manifest_sha256"]:
            raise ValueError("EXP-03 manifest and Method P trace disagree: input manifest identity")
        if trace["architecture"]["before_commit"] != method_p["architecture_before_sha"]:
            raise ValueError(
                "EXP-03 manifest and Method P trace disagree: before architecture revision"
            )
        if trace["architecture"]["after_commit"] != method_p["architecture_after_sha"]:
            raise ValueError(
                "EXP-03 manifest and Method P trace disagree: after architecture revision"
            )
        governance = trace["governance"]
        operation_plan = trace["operation_plan"]
        governance_reasons = governance["reason_codes"]
        operation_reasons = operation_plan["hold_reasons"] + operation_plan["reject_reasons"]
        expected_reasons = sorted(set(governance_reasons) | set(operation_reasons))
        if trace["unresolved_prerequisites"] != expected_reasons:
            raise ValueError(
                "EXP-03 governance/operation-plan reasons disagree with unresolved prerequisites"
            )
        if method_p["reason_codes"] != expected_reasons:
            raise ValueError("EXP-03 manifest and Method P trace disagree: reason codes")
        if method_p["governance_result"] != governance["result"]:
            raise ValueError("EXP-03 manifest and Method P trace disagree: governance result")
        if method_p["prediction_v1_emitted"] != (trace["prediction_v1"] is not None):
            raise ValueError(
                "EXP-03 manifest and Method P trace disagree: prediction emission status"
            )
        if (
            trace["exp02_evidence_admission_status"] != "not_admitted"
            or trace["exp02_evidence_admitted_to_p_calculations"] is not False
            or trace["exp02_observations_used_as_semantic_pair_evidence"] is not False
        ):
            raise ValueError("EXP-03 trace misrepresents EXP-02 evidence admission")
        expected_integration_status = {
            "ACCEPT": "completed",
            "HOLD": "completed_with_hold",
            "REJECT": "completed_with_reject",
        }.get(str(governance["result"]))
        if expected_integration_status is None:
            raise ValueError("EXP-03 completed trace has an unsupported governance outcome")
    if manifest["integration_status"] != expected_integration_status:
        raise ValueError(
            "EXP-03 integration status disagrees with Method P execution/governance outcome"
        )


def write_integration_run(
    exp02_run_dir: Path,
    output_dir: Path,
    *,
    p_input_dir: Path | None = None,
    invocation: Sequence[str] | None = None,
) -> tuple[dict[str, Any], str]:
    """Write one unique DEVELOPMENT output directory and validate it after writing."""
    destination = output_dir.resolve(strict=False)
    if output_dir.is_symlink() or destination.exists():
        raise FileExistsError(f"refusing to overwrite EXP-03 output directory: {destination}")
    if destination == exp02_run_dir.resolve(strict=True):
        raise ValueError("EXP-03 output directory must not replace the EXP-02 input run")
    manifest, p_trace = build_integration_artifact(
        exp02_run_dir,
        p_input_dir=p_input_dir,
        invocation=invocation,
    )
    parent = destination.parent
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{destination.name}.", dir=parent) as temporary:
        staging = Path(temporary) / "run"
        staging.mkdir()
        if p_trace is not None:
            (staging / P_TRACE_FILENAME).write_bytes(pretty_json_bytes(p_trace))
        manifest_bytes = pretty_json_bytes(manifest)
        (staging / MANIFEST_FILENAME).write_bytes(manifest_bytes)
        manifest_digest = sha256_bytes(manifest_bytes)
        (staging / MANIFEST_DIGEST_FILENAME).write_text(
            f"{manifest_digest}  {MANIFEST_FILENAME}\n",
            encoding="ascii",
        )
        validate_integration_output(staging)
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(f"refusing to overwrite EXP-03 output directory: {destination}")
        os.rename(staging, destination)
    return validate_integration_output(destination), manifest_digest


def main(argv: list[str] | None = None) -> int:
    """Run the bounded EXP-02-to-Method-P DEVELOPMENT bridge."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exp02-run-dir", required=True, type=Path)
    parser.add_argument(
        "--p-input-dir",
        type=Path,
        help="Explicit verified V3 Method P input bundle; no bundle is discovered automatically.",
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        manifest, manifest_digest = write_integration_run(
            args.exp02_run_dir,
            args.output_dir,
            p_input_dir=args.p_input_dir,
            invocation=["python", "-m", "scripts.exp03_method_bridge", *sys.argv[1:]],
        )
    except (OSError, ValueError, ProtocolError, ContractValidationError) as error:
        print(json.dumps({"status": "input_rejected", "error": str(error)}, sort_keys=True))
        return 1
    summary = {
        "status": manifest["integration_status"],
        "evidence_flow": manifest["evidence_flow"],
        "run_id": manifest["exp02_input"]["run_id"],
        "mapped_candidate_count": sum(
            item["mapping_status"] == "candidate_only"
            for item in manifest["representation_mappings"]
        ),
        "unsupported_mapping_count": sum(
            item["mapping_status"] == "unsupported" for item in manifest["representation_mappings"]
        ),
        "method_p_execution": manifest["method_p"]["execution_status"],
        "governance": manifest["method_p"]["governance_result"],
        "reason_codes": manifest["method_p"]["reason_codes"],
        "output_dir": str(args.output_dir.resolve(strict=True)),
        "manifest_sha256": manifest_digest,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if manifest["method_p"]["execution_status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
