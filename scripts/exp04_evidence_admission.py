"""Admit verified EXP-02 evaluator observations at the existing Method P boundary."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import platform
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal, cast

from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError, ProtocolError
from experiments.execution.tooling.hashing import (
    canonical_json_bytes,
    pretty_json_bytes,
    sha256_bytes,
)
from experiments.execution.tooling.p_adaptation import VerifiedPBundle
from experiments.execution.tooling.p_adaptation_evidence import (
    AdaptationEvidenceVerifierRegistry,
    VerifiedAdaptationEvidence,
    thaw_verified_payload,
)
from experiments.execution.tooling.p_input_validation import SourceReference
from scripts import exp03_method_bridge as exp03
from scripts.exp01_evidence_contract import BUNDLE_FILENAME

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIRECTORY = ROOT / "experiments/execution/schemas"
ADMISSION_SCHEMA = "exp04_evidence_admission_v1.schema.json"
TRACE_SCHEMA = "exp04_method_p_execution_trace_v1.schema.json"
VERIFIER_CONFIG_SCHEMA = "exp04_evidence_verifier_config_v1.schema.json"
MANIFEST_FILENAME = "admission_manifest.json"
MANIFEST_DIGEST_FILENAME = "admission_manifest.sha256"
P_TRACE_FILENAME = "method_p_trace.json"
ARTIFACT_TYPE = "exp04_verified_evaluator_evidence_admission"
HMAC_ALGORITHM = "hmac-sha256"


@dataclass(frozen=True)
class _FileHmacVerifier:
    """TEST_ONLY verifier adapter backed by an external HMAC key file."""

    trust_scope: Literal["TEST_ONLY"]
    key: bytes = field(repr=False)

    def verify(self, verifier_id: str, content_sha256: str, signature: str) -> bool:
        del verifier_id
        expected = hmac.new(self.key, content_sha256.encode("ascii"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)


@dataclass(frozen=True)
class _ExternalEvidenceTrustContext:
    """Expose only the external adaptation-evidence verifier to the existing V3 path."""

    trust_scope: Literal["TEST_ONLY"]
    adaptation_evidence_verifiers: AdaptationEvidenceVerifierRegistry

    def verify_charter(
        self,
        charter: Mapping[str, Any],
        source: SourceReference,
        evaluation_as_of: str,
    ) -> bool | None:
        del charter, source, evaluation_as_of
        return None

    def verify_approval(
        self,
        policy: Mapping[str, Any],
        charter: Mapping[str, Any],
        source: SourceReference,
        evaluation_as_of: str,
    ) -> bool | None:
        del policy, charter, source, evaluation_as_of
        return None


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_regular_file(path: Path, label: str) -> tuple[Path, bytes]:
    if path.is_symlink():
        raise ValueError(f"{label} must not be a symlink")
    resolved = path.resolve(strict=True)
    if not resolved.is_file():
        raise ValueError(f"{label} must be a regular file")
    return resolved, resolved.read_bytes()


def _file_reference(path: Path, data: bytes, role: str) -> dict[str, Any]:
    return {
        "path": str(path.resolve(strict=True)),
        "sha256": sha256_bytes(data),
        "size_bytes": len(data),
        "role": role,
    }


def _load_json_file(path: Path, label: str) -> tuple[Path, bytes, dict[str, Any]]:
    resolved, content = _read_regular_file(path, label)
    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError(f"{label} is not valid JSON") from error
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return resolved, content, cast(dict[str, Any], parsed)


def _external_trust_context(path: Path) -> tuple[_ExternalEvidenceTrustContext, dict[str, Any]]:
    """Load a digest-pinned key without copying or serializing its secret bytes."""
    resolved_config, config_bytes, config = _load_json_file(path, "evidence verifier config")
    validate_payload(VERIFIER_CONFIG_SCHEMA, config)
    if config["trust_scope"] != "TEST_ONLY":
        raise ValueError("EXP-04 file verifier configuration is restricted to TEST_ONLY")
    key_path = Path(str(config["key_file"]))
    if not key_path.is_absolute():
        raise ValueError("evidence verifier key_file must be an absolute path")
    resolved_key, key_bytes = _read_regular_file(key_path, "evidence verifier key")
    try:
        resolved_key.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise ValueError("evidence verifier key must be provisioned outside the repository")
    key_digest = sha256_bytes(key_bytes)
    if key_digest != config["key_file_sha256"]:
        raise ValueError("evidence verifier key digest does not match its config")
    if len(key_bytes) < 32:
        raise ValueError("evidence verifier key must contain at least 32 bytes")
    scope: Literal["TEST_ONLY"] = "TEST_ONLY"
    verifier_id = str(config["verifier_id"])
    verifier = _FileHmacVerifier(scope, key_bytes)
    registry = AdaptationEvidenceVerifierRegistry({verifier_id: verifier})
    context = _ExternalEvidenceTrustContext(scope, registry)
    reference = {
        "config_reference": _file_reference(
            resolved_config, config_bytes, "evidence_verifier_config"
        ),
        "key_reference": _file_reference(resolved_key, key_bytes, "external_verifier_key"),
        "verifier_id": verifier_id,
        "trust_scope": scope,
        "algorithm": HMAC_ALGORITHM,
    }
    return context, reference


def _load_sidecar(path: Path) -> tuple[Path, bytes, dict[str, Any]]:
    resolved, content, sidecar = _load_json_file(path, "adaptation evidence sidecar")
    validate_payload("p_adaptation_evidence_v2.schema.json", sidecar)
    if sidecar.get("schema_version") != 2:
        raise ValueError("EXP-04 accepts only the existing adaptation evidence V2 sidecar")
    return resolved, content, sidecar


def _record_index(bundle: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(record["record_id"]): record
        for record in bundle.get("records", [])
        if isinstance(record, Mapping) and isinstance(record.get("record_id"), str)
    }


def _metric_contracts(target: Mapping[str, Any]) -> list[tuple[str, str]] | None:
    candidates = target.get("metrics")
    if not isinstance(candidates, list):
        evidence_contract = target.get("evidence_contract")
        candidates = (
            evidence_contract.get("metrics") if isinstance(evidence_contract, Mapping) else None
        )
    if not isinstance(candidates, list) or not candidates:
        return None
    if any(not isinstance(item, Mapping) for item in candidates):
        return None
    result: list[tuple[str, str]] = []
    for item in candidates:
        name, unit = item.get("name"), item.get("unit")
        if not isinstance(name, str) or not isinstance(unit, str):
            return None
        result.append((name, unit))
    return sorted(result)


def _source_artifact_rows(
    run_dir: Path,
    exp02_bundle: Mapping[str, Any],
    configured_evaluator: Mapping[str, Any],
    record: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    refs: list[Mapping[str, Any]] = []
    if record is not None:
        config_ref = record.get("configuration_artifact")
        if isinstance(config_ref, Mapping):
            refs.append(config_ref)
        raw_refs = record.get("raw_output_artifacts")
        if isinstance(raw_refs, list):
            refs.extend(item for item in raw_refs if isinstance(item, Mapping))
    source_paths = configured_evaluator.get("source_artifacts", [])
    by_source = {
        str(item.get("source_path")): item
        for item in exp02_bundle.get("input_artifacts", [])
        if isinstance(item, Mapping) and isinstance(item.get("source_path"), str)
    }
    refs.extend(
        by_source[str(source_path)]
        for source_path in source_paths
        if isinstance(source_path, str) and str(source_path) in by_source
    )
    seen: set[str] = set()
    for reference in refs:
        path = str(reference.get("path", ""))
        if path in seen:
            continue
        seen.add(path)
        content = exp03._artifact_bytes(run_dir, reference)
        rows.append(
            {
                "path": path,
                "source_path": reference.get("source_path"),
                "role": reference.get("role"),
                "sha256": sha256_bytes(content),
                "size_bytes": len(content),
            }
        )
    return sorted(rows, key=lambda item: (str(item["path"]), str(item["role"])))


def _strict_representation_mappings(
    *,
    run_dir: Path,
    exp02_bundle: Mapping[str, Any],
    evidence: Mapping[str, Any],
    configuration: Mapping[str, Any],
    p_bundle: Any | None,
) -> list[dict[str, Any]]:
    """Compare all required representation bindings without inferring equivalence."""
    configured_by_id = {str(item["id"]): item for item in configuration.get("representations", [])}
    criteria_by_id = {str(item["id"]): item for item in configuration.get("criteria", [])}
    p_rows = list(p_bundle.representations) if p_bundle is not None else []
    p_after = (
        str(p_bundle.snapshot["architecture"]["after_commit"]) if p_bundle is not None else None
    )
    records = _record_index(exp02_bundle)
    result: list[dict[str, Any]] = []

    for observation in evidence.get("representations", []):
        source_id = str(observation["representation_id"])
        configured = configured_by_id[source_id]
        evaluator = configured["evaluator"]
        criterion_id = str(observation["criterion_id"])
        criterion = criteria_by_id[criterion_id]
        execution = observation["evaluator_execution"]
        record = records.get(str(execution["record_id"]))
        source_stage = str(observation["lifecycle_stage"])
        translated_stage = exp03.STAGE_TRANSLATIONS.get(source_stage)
        obligations = [str(item) for item in observation["declared_obligations"]]
        source_revision = str(evidence["source_revision"])

        for obligation_id in obligations:
            candidates = [
                row
                for row in p_rows
                if row.get("criterion") == criterion_id and obligation_id in row.get("covers", [])
            ]
            exact_identity = [row for row in candidates if row.get("id") == source_id]
            stage_candidates = [row for row in candidates if row.get("stage") == translated_stage]
            selected_candidates = (
                exact_identity
                if len(exact_identity) == 1
                else stage_candidates
                if len(stage_candidates) == 1
                else candidates
                if len(candidates) == 1
                else []
            )
            target = selected_candidates[0] if len(selected_candidates) == 1 else None
            ambiguous_mapping = len(candidates) > 1 and target is None
            target_id = str(target["id"]) if target is not None else None
            target_stage = str(target.get("stage")) if target is not None else None
            record_artifact = (
                record.get("configuration_artifact") if isinstance(record, Mapping) else None
            )
            target_artifact = target.get("evaluator_artifact") if target is not None else None
            source_metrics = sorted(
                {
                    (str(item["name"]), str(item["unit"]))
                    for item in evaluator.get("metrics", [])
                    if isinstance(item, Mapping)
                }
            )
            target_metrics = _metric_contracts(target) if target is not None else None
            evidence_contract = target.get("evidence_contract") if target is not None else None
            metric_observation_rows = (
                evidence_contract.get("metric_observations")
                if isinstance(evidence_contract, Mapping)
                else None
            )
            metric_observation_pairs = (
                {
                    (str(row["name"]), str(row["unit"]))
                    for row in metric_observation_rows
                    if isinstance(row, Mapping)
                    and isinstance(row.get("name"), str)
                    and isinstance(row.get("unit"), str)
                }
                if isinstance(metric_observation_rows, list)
                else set()
            )
            metric_observation_contract_exact = (
                isinstance(metric_observation_rows, list)
                and len(metric_observation_rows) > 0
                and len(metric_observation_pairs) == len(metric_observation_rows)
                and metric_observation_pairs == set(source_metrics)
            )
            target_scope = target.get("applicability_scope") if target is not None else None
            source_scope_id = str(evaluator.get("scope_id", ""))
            target_scope_id = (
                target_scope.get("scope_id") if isinstance(target_scope, Mapping) else None
            )
            target_criterion_intent = target.get("criterion_intent") if target is not None else None
            target_source_artifacts = target.get("source_artifacts") if target is not None else None
            source_artifact_rows = _source_artifact_rows(run_dir, exp02_bundle, evaluator, record)
            expected_source_artifacts = {
                (str(row["source_path"]), str(row["sha256"]))
                for row in source_artifact_rows
                if row.get("source_path") is not None
            }
            target_source_artifact_pairs = (
                {
                    (str(row["source_path"]), str(row["sha256"]))
                    for row in target_source_artifacts
                    if isinstance(row, Mapping)
                    and isinstance(row.get("source_path"), str)
                    and isinstance(row.get("sha256"), str)
                }
                if isinstance(target_source_artifacts, list)
                else set()
            )
            target_source_artifact_inventory_exact = (
                isinstance(target_source_artifacts, list)
                and len(target_source_artifact_pairs) == len(target_source_artifacts)
                and target_source_artifact_pairs == expected_source_artifacts
            )
            target_artifact_digest = (
                target_artifact.get("sha256") if isinstance(target_artifact, Mapping) else None
            )
            source_artifact_digest = (
                record_artifact.get("sha256") if isinstance(record_artifact, Mapping) else None
            )

            checks = {
                "representation_identity": (
                    "not_available"
                    if target is None
                    else "exact"
                    if target_id == source_id
                    else "mismatch"
                ),
                "obligation_identity": (
                    "not_available"
                    if target is None
                    else "exact"
                    if obligation_id in target.get("covers", [])
                    else "mismatch"
                ),
                "criterion_identity": (
                    "not_available"
                    if target is None
                    else "exact"
                    if target.get("criterion") == criterion_id
                    else "mismatch"
                ),
                "criterion_intent": (
                    "not_available"
                    if target is None
                    else "exact"
                    if target_criterion_intent == criterion.get("intent")
                    else "unrepresented"
                    if target_criterion_intent is None
                    else "mismatch"
                ),
                "evaluator_identity": (
                    "not_available"
                    if target is None
                    else "exact"
                    if target.get("evaluator") == evaluator.get("id")
                    else "mismatch"
                ),
                "metric_identity_and_units": (
                    "not_available"
                    if target is None
                    else "unrepresented"
                    if target_metrics is None
                    else "exact"
                    if target_metrics == source_metrics
                    else "mismatch"
                ),
                "lifecycle_stage": (
                    "not_available"
                    if target is None or translated_stage is None
                    else "exact"
                    if target_stage == translated_stage
                    else "mismatch"
                ),
                "architecture_revision": (
                    "not_available"
                    if p_bundle is None
                    else "exact"
                    if p_after == source_revision
                    else "mismatch"
                ),
                "applicability_scope": (
                    "not_available"
                    if target is None
                    else "unrepresented"
                    if target_scope_id is None
                    else "exact"
                    if target_scope_id == source_scope_id
                    else "mismatch"
                ),
                "source_artifact_provenance": (
                    "not_available"
                    if target is None
                    else "unrepresented"
                    if not isinstance(target_source_artifacts, list)
                    or target_artifact_digest is None
                    or not expected_source_artifacts
                    else "exact"
                    if target_artifact_digest == source_artifact_digest
                    and target_source_artifact_inventory_exact
                    else "mismatch"
                ),
                "metric_observation_contract": (
                    "not_available"
                    if target is None
                    else "unrepresented"
                    if not isinstance(metric_observation_rows, list)
                    else "exact"
                    if metric_observation_contract_exact
                    else "mismatch"
                ),
            }
            checks["runtime_source_identity"] = (
                "not_applicable"
                if source_stage != "runtime"
                else "exact"
                if execution.get("runtime_source_binding_status") == "verified"
                else "unrepresented"
            )

            reason_map = {
                "representation_identity": "P_REPRESENTATION_IDENTITY_NOT_EXACT",
                "obligation_identity": "P_OBLIGATION_IDENTITY_NOT_EXACT",
                "criterion_identity": "P_CRITERION_IDENTITY_NOT_EXACT",
                "criterion_intent": "P_CRITERION_INTENT_NOT_REPRESENTED",
                "evaluator_identity": "P_EVALUATOR_IDENTITY_NOT_EXACT",
                "metric_identity_and_units": "P_METRIC_IDENTITY_OR_UNITS_NOT_EXACT",
                "lifecycle_stage": "P_LIFECYCLE_STAGE_NOT_EXACT",
                "architecture_revision": "ARCHITECTURE_REVISION_NOT_EXACT",
                "applicability_scope": "P_APPLICABILITY_SCOPE_NOT_REPRESENTED",
                "source_artifact_provenance": "P_SOURCE_ARTIFACT_PROVENANCE_NOT_EXACT",
                "metric_observation_contract": "P_METRIC_OBSERVATION_CONTRACT_NOT_REPRESENTED",
                "runtime_source_identity": "RUNTIME_APPLICATION_SOURCE_IDENTITY_UNVERIFIED",
            }
            reason_codes = sorted(
                reason_map[key]
                for key, value in checks.items()
                if value not in {"exact", "not_applicable"}
            )
            if ambiguous_mapping:
                reason_codes.append("P_CANONICAL_MAPPING_AMBIGUOUS")
            admission_status = (
                "validated_observation"
                if all(value in {"exact", "not_applicable"} for value in checks.values())
                else "mapping_unresolved"
            )
            record_status = str(record.get("status", "missing")) if record else "missing"
            execution_verdict = (
                str(record.get("execution_verdict", "not_run")) if record else "not_run"
            )
            exit_status = record.get("exit_status") if record else None
            if record_status != "available" or execution_verdict not in {
                "passed",
                "violations_detected",
            }:
                admission_status = "mapping_unresolved"
                reason_codes.append("EXP02_EXECUTION_OBSERVATION_NOT_USABLE")
            runtime_binding = record.get("source_binding") if isinstance(record, Mapping) else None
            runtime_identity_status = (
                runtime_binding.get("status", "not_observed")
                if isinstance(runtime_binding, Mapping)
                else "not_applicable"
            )
            metrics = [dict(item) for item in observation.get("metrics", [])]
            output_refs = (
                [dict(item) for item in record.get("raw_output_artifacts", [])]
                if isinstance(record, Mapping)
                else []
            )
            evaluator_artifact = (
                dict(record_artifact) if isinstance(record_artifact, Mapping) else None
            )

            result.append(
                {
                    "exp02_representation_id": source_id,
                    "criterion_id": criterion_id,
                    "criterion_intent": str(criterion.get("intent", "")),
                    "obligation_id": obligation_id,
                    "observation_status": "validated_observation",
                    "admission_status": admission_status,
                    "exp02_evaluator": {
                        "id": str(observation["evaluator_id"]),
                        "record_id": str(execution["record_id"]),
                        "name": str(execution["evaluator_name"]),
                        "configuration_artifact": evaluator_artifact,
                        "configuration_artifact_sha256": (
                            str(evaluator_artifact["sha256"])
                            if evaluator_artifact is not None
                            else None
                        ),
                        "raw_output_artifacts": output_refs,
                        "source_artifact_inventory": source_artifact_rows,
                    },
                    "execution": {
                        "status": str(execution["status"]),
                        "actual_verdict": execution_verdict,
                        "exit_status": exit_status,
                        "source_revision": str(execution["source_revision"]),
                        "runtime_application_identity_status": runtime_identity_status,
                    },
                    "scope": {
                        "lifecycle_stage": source_stage,
                        "scope_id": str(evaluator["scope_id"]),
                        "mapping_stage": translated_stage,
                    },
                    "metrics": metrics,
                    "observed_compliance": dict(observation["compliance_observation"]),
                    "target_p_representation_id": target_id,
                    "candidate_p_representation_ids": sorted(str(row["id"]) for row in candidates),
                    "binding_checks": checks,
                    "external_semantic_proof_status": "not_supplied",
                    "p_evidence_consumption_status": "not_attempted",
                    "reason_codes": sorted(set(reason_codes)),
                }
            )
    return result


def _sidecar_observation_match(
    *,
    verified: VerifiedAdaptationEvidence,
    admissions: Sequence[Mapping[str, Any]],
    run_id: str,
    run_dir: Path,
    exp02_bundle: Mapping[str, Any],
) -> tuple[bool, list[str]]:
    """Bind signed P evidence rows to the exact EXP-02 execution record and raw bytes."""
    payload = thaw_verified_payload(verified)
    rows = payload.get("evaluator_evidence", [])
    eligible = [
        row
        for row in admissions
        if row.get("admission_status") == "validated_observation"
        and row.get("target_p_representation_id") is not None
    ]
    reasons: list[str] = []
    expected_keys = {
        (str(row["target_p_representation_id"]), str(row["obligation_id"])) for row in eligible
    }
    row_by_key: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("evidence"), Mapping):
            reasons.append("P03_EVIDENCE_PAIR_RECORD_INVALID")
            continue
        try:
            validate_payload("evaluator_evidence.schema.json", dict(row["evidence"]))
        except ContractValidationError:
            reasons.append("P03_EVALUATOR_EVIDENCE_SCHEMA_INVALID")
        key = (str(row.get("representation_id", "")), str(row.get("obligation_id", "")))
        if key in row_by_key:
            reasons.append("P03_EVIDENCE_PAIR_RECORD_DUPLICATE")
        row_by_key[key] = row
    if not expected_keys or set(row_by_key) != expected_keys:
        reasons.append("SIDECAR_EVIDENCE_PAIR_SET_MISMATCH")
    records = _record_index(exp02_bundle)
    artifact_bytes: dict[str, tuple[str, bytes]] = {}
    for row in payload.get("artifact_bytes", []):
        if isinstance(row, Mapping) and isinstance(row.get("path"), str):
            try:
                decoded = base64.b64decode(str(row.get("content_base64", "")), validate=True)
            except ValueError:
                reasons.append("P03_EVIDENCE_ARTIFACT_ENCODING_INVALID")
                continue
            declared_digest = str(row.get("sha256", ""))
            if sha256_bytes(decoded) != declared_digest:
                reasons.append("P03_EVIDENCE_ARTIFACT_DIGEST_INVALID")
            artifact_path = str(row["path"])
            if artifact_path in artifact_bytes:
                reasons.append("P03_EVIDENCE_ARTIFACT_DUPLICATE_PATH")
            artifact_bytes[artifact_path] = (declared_digest, decoded)

    for admission in eligible:
        key = (str(admission["target_p_representation_id"]), str(admission["obligation_id"]))
        side_row = row_by_key.get(key)
        record_id = str(admission["exp02_evaluator"]["record_id"])
        record = records.get(record_id)
        if side_row is None or record is None:
            reasons.append("SIDECAR_EVIDENCE_PAIR_SOURCE_MISSING")
            continue
        evidence = side_row["evidence"]
        if (
            evidence.get("representation_id") != key[0]
            or evidence.get("architecture_source_sha")
            != exp02_bundle["source_revision"]["commit_sha"]
            or evidence.get("process_exit_code") != record.get("exit_status")
            or evidence.get("evaluator_id") != admission["exp02_evaluator"]["id"]
        ):
            reasons.append("SIDECAR_EVIDENCE_OBSERVATION_MISMATCH")
        expected_infrastructure = (
            "completed"
            if record.get("status") == "available" and record.get("exit_status") is not None
            else "infrastructure_failure"
            if record.get("status") in {"invalid", "inconclusive"}
            else "not_run"
        )
        if evidence.get("infrastructure_status") != expected_infrastructure:
            reasons.append("SIDECAR_EVIDENCE_EXECUTION_STATUS_MISMATCH")
        raw_refs = record.get("raw_output_artifacts", [])
        expected_refs: list[dict[str, str]] = []
        for reference in raw_refs:
            raw_path = str(reference["path"])
            prefixed_path = f"exp02/{run_id}/{raw_path}"
            expected_refs.append({"path": prefixed_path, "sha256": str(reference["sha256"])})
            data = exp03._artifact_bytes(run_dir, reference)
            supplied = artifact_bytes.get(prefixed_path)
            if supplied != (str(reference["sha256"]), data):
                reasons.append("SIDECAR_EVIDENCE_RAW_ARTIFACT_MISMATCH")
        if evidence.get("evidence_artifacts") != expected_refs:
            reasons.append("SIDECAR_EVIDENCE_ARTIFACT_REFERENCE_MISMATCH")
        expected_stdout = next(
            (
                str(reference["sha256"])
                for reference in raw_refs
                if reference.get("role") == "stdout"
            ),
            None,
        )
        expected_stderr = next(
            (
                str(reference["sha256"])
                for reference in raw_refs
                if reference.get("role") == "stderr"
            ),
            None,
        )
        if (
            evidence.get("stdout_sha256") != expected_stdout
            or evidence.get("stderr_sha256") != expected_stderr
        ):
            reasons.append("SIDECAR_EVIDENCE_STREAM_DIGEST_MISMATCH")
    return not reasons, sorted(set(reasons))


def _pair_proof_status(
    verified: VerifiedAdaptationEvidence | None,
    representation_id: str | None,
    obligation_id: str,
) -> str:
    if verified is None or representation_id is None:
        return "not_supplied"
    payload = thaw_verified_payload(verified)
    for row in payload.get("pair_proofs", []):
        if (
            isinstance(row, Mapping)
            and row.get("representation_id") == representation_id
            and row.get("obligation_id") == obligation_id
        ):
            return str(row.get("status", "not_supplied"))
    return "not_supplied"


def _trace_from_result(
    p_bundle: VerifiedPBundle,
    result: Any,
    *,
    evidence_admitted: bool,
    sidecar_supplied: bool,
) -> dict[str, Any]:
    trace = exp03._adaptation_trace(p_bundle, result)
    trace["schema_version"] = "1.0.0"
    trace["trace_type"] = "development_method_p_execution_with_exp04_admission"
    trace["exp02_evidence_admission_status"] = (
        "admitted_execution_evidence" if evidence_admitted else "not_admitted"
    )
    trace["exp02_evidence_admitted_to_p_calculations"] = evidence_admitted
    trace["exp02_observations_used_as_semantic_pair_evidence"] = False
    trace["adaptation_evidence_sidecar_supplied"] = sidecar_supplied
    validate_payload(TRACE_SCHEMA, trace)
    return trace


def build_admission_artifact(
    exp02_run_dir: Path,
    *,
    p_input_dir: Path | None = None,
    evidence_sidecar_path: Path | None = None,
    trust_config_path: Path | None = None,
    trust_context: Any | None = None,
    invocation: Sequence[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Validate observations, enforce exact mapping, and conditionally run existing Method P."""
    exp02_bundle, evidence, configuration, bundle_bytes = exp03._load_exp02(exp02_run_dir)
    exp02_dir = exp02_run_dir.resolve(strict=True)
    p_bundle: VerifiedPBundle | None = None
    p_status = "not_supplied"
    p_input_reference: dict[str, Any] | None = None
    trust_reference: dict[str, Any] | None = None
    sidecar: dict[str, Any] | None = None
    sidecar_reference: dict[str, Any] | None = None
    verified_sidecar: VerifiedAdaptationEvidence | None = None
    evidence_verification_status = "not_supplied"
    external_error: str | None = None
    p_trace: dict[str, Any] | None = None
    p_execution_status = "not_run"
    governance_result = "not_run"
    evidence_consumed = False
    blockers: list[dict[str, str]] = []

    if trust_config_path is not None and trust_context is not None:
        evidence_verification_status = "rejected"
        external_error = "pass either an existing V3 trust_context or a TEST_ONLY trust config"
        blockers.append({"code": "EXTERNAL_VERIFIER_CONFIG_REJECTED", "details": external_error})
    elif trust_config_path is not None:
        try:
            trust_context, trust_reference = _external_trust_context(trust_config_path)
        except (OSError, ValueError, ContractValidationError) as error:
            evidence_verification_status = "rejected"
            external_error = str(error)
            blockers.append({"code": "EXTERNAL_VERIFIER_CONFIG_REJECTED", "details": str(error)})

    if p_input_dir is not None:
        try:
            p_bundle = exp03.verify_method_p_input(p_input_dir, trust_context=trust_context)
            manifest_path = p_bundle.root / "method_input_v3.json"
            manifest_bytes = manifest_path.read_bytes()
            p_input_reference = {
                "directory": str(p_bundle.root),
                "bundle_sha256": str(p_bundle.manifest["bundle_sha256"]),
                "manifest": _file_reference(manifest_path, manifest_bytes, "method_p_v3_manifest"),
                "architecture_before_sha": str(p_bundle.snapshot["architecture"]["before_commit"]),
                "architecture_after_sha": str(p_bundle.snapshot["architecture"]["after_commit"]),
                "policy_source_revision": str(p_bundle.manifest["policy_source_revision"]),
                "policy_bundle_sha256": str(p_bundle.manifest["policy_bundle_sha256"]),
                "verification_status": "verified",
            }
            p_status = "verified"
        except (OSError, ValueError, ProtocolError, ContractValidationError) as error:
            p_status = "rejected"
            external_error = str(error)
            blockers.append({"code": "P_V3_INPUT_REJECTED", "details": str(error)})
    else:
        blockers.append(
            {
                "code": "P_V3_INPUT_REQUIRED",
                "details": "Pass an explicitly prepared V3 Method P input directory.",
            }
        )

    if evidence_sidecar_path is not None:
        try:
            resolved_sidecar, sidecar_bytes, sidecar = _load_sidecar(evidence_sidecar_path)
            sidecar_reference = _file_reference(
                resolved_sidecar, sidecar_bytes, "p_adaptation_evidence_v2_sidecar"
            )
        except (OSError, ValueError, ContractValidationError) as error:
            evidence_verification_status = "rejected"
            external_error = str(error)
            blockers.append({"code": "EXTERNAL_EVIDENCE_SIDECAR_REJECTED", "details": str(error)})
    elif trust_config_path is not None:
        evidence_verification_status = "authority_missing"
        blockers.append(
            {
                "code": "EXTERNAL_EVIDENCE_SIDECAR_MISSING",
                "details": "A verifier was configured but no external V2 sidecar was supplied.",
            }
        )

    admissions = _strict_representation_mappings(
        run_dir=exp02_dir,
        exp02_bundle=exp02_bundle,
        evidence=evidence,
        configuration=configuration,
        p_bundle=p_bundle,
    )
    if sidecar is not None and p_bundle is not None and evidence_verification_status != "rejected":
        try:
            verified_sidecar = exp03.verify_method_p_evidence_sidecar(p_bundle, sidecar)
            evidence_verification_status = (
                "verified" if verified_sidecar is not None else "authority_missing"
            )
        except (ValueError, ContractValidationError) as error:
            evidence_verification_status = "rejected"
            external_error = str(error)
            blockers.append({"code": "EXTERNAL_EVIDENCE_SIDECAR_REJECTED", "details": str(error)})
    elif sidecar is not None:
        evidence_verification_status = "not_verified_v3_input_rejected"
    elif evidence_sidecar_path is None and trust_config_path is None:
        evidence_verification_status = "authority_missing"

    sidecar_matches = False
    sidecar_match_reasons: list[str] = []
    if verified_sidecar is not None and p_bundle is not None and sidecar is not None:
        sidecar_matches, sidecar_match_reasons = _sidecar_observation_match(
            verified=verified_sidecar,
            admissions=admissions,
            run_id=str(exp02_bundle["run_id"]),
            run_dir=exp02_dir,
            exp02_bundle=exp02_bundle,
        )
        if verified_sidecar.trust_scope != "PRODUCTION":
            sidecar_matches = False
            sidecar_match_reasons.append("TEST_ONLY_EVIDENCE_CANNOT_AUTHORIZE_EXP04_ADMISSION")
        signed_pair_proofs = thaw_verified_payload(verified_sidecar).get("pair_proofs", [])
        if any(
            isinstance(row, Mapping) and row.get("status") == "VALID" for row in signed_pair_proofs
        ):
            sidecar_matches = False
            sidecar_match_reasons.append(
                "POSITIVE_SEMANTIC_PROOF_REQUIRES_SEPARATE_G1_G4_AUTHORIZATION"
            )
        if not sidecar_matches:
            blockers.extend(
                {"code": code, "details": "Signed sidecar does not bind exact EXP-02 observations."}
                for code in sidecar_match_reasons
            )

    for admission in admissions:
        admission["external_semantic_proof_status"] = _pair_proof_status(
            verified_sidecar,
            cast(str | None, admission["target_p_representation_id"]),
            str(admission["obligation_id"]),
        )
        if evidence_verification_status == "rejected":
            admission["admission_status"] = "rejected"
            admission["reason_codes"] = sorted(
                set(admission["reason_codes"]) | {"EXTERNAL_AUTHORIZATION_REJECTED"}
            )
        elif admission["admission_status"] != "validated_observation":
            admission["admission_status"] = "mapping_unresolved"
        elif verified_sidecar is None:
            admission["admission_status"] = "authority_missing"
            admission["reason_codes"] = sorted(
                set(admission["reason_codes"]) | {"EXTERNAL_VERIFIER_AUTHORITY_MISSING"}
            )
        elif not sidecar_matches:
            admission["admission_status"] = "rejected"
            admission["reason_codes"] = sorted(
                set(admission["reason_codes"]) | set(sidecar_match_reasons)
            )
        else:
            admission["admission_status"] = "admitted_execution_evidence"

    if verified_sidecar is not None and not any(
        row["admission_status"] == "admitted_execution_evidence" for row in admissions
    ):
        blockers.append(
            {
                "code": "P_CANONICAL_MAPPING_UNRESOLVED",
                "details": (
                    "V3 verified the sidecar, but the current V3 representation and evaluator "
                    "evidence contracts do not bind the A0.1 EXP-02 observations exactly."
                ),
            }
        )
    if any(row["admission_status"] == "mapping_unresolved" for row in admissions):
        reasons = sorted({code for row in admissions for code in row["reason_codes"]})
        blockers.append(
            {
                "code": "P_CANONICAL_MAPPING_UNRESOLVED",
                "details": "Exact A0.1-to-V3 binding is unavailable: " + ", ".join(reasons),
            }
        )
    if evidence_verification_status == "authority_missing":
        blockers.append(
            {
                "code": "EXTERNAL_VERIFIER_AUTHORITY_MISSING",
                "details": "No externally verified V2 sidecar is available for admission.",
            }
        )

    if p_bundle is not None and p_status == "verified":
        should_pass_sidecar = (
            verified_sidecar is not None
            and sidecar_matches
            and any(row["admission_status"] == "admitted_execution_evidence" for row in admissions)
        )
        result, used_sidecar = exp03.run_verified_method_p(
            p_bundle,
            evidence_context=sidecar if should_pass_sidecar and sidecar is not None else None,
        )
        p_execution_status = "completed"
        governance_result = result.governance.result.value
        if governance_result == "ACCEPT" or result.prediction_v1 is not None:
            raise ProtocolError("EXP04_UNAUTHORIZED_ACCEPT_OR_PREDICTION_BLOCKED")
        p_trace = _trace_from_result(
            p_bundle,
            result,
            evidence_admitted=False,
            sidecar_supplied=used_sidecar is not None,
        )
        p_pairs = {
            (str(row["representation_id"]), str(row["obligation_id"])): row
            for row in p_trace["current_pairs"]
        }
        consumed_pairs = {
            key
            for key, pair in p_pairs.items()
            if pair.get("evaluator_evidence_sha256") is not None
        }
        evidence_consumed = bool(
            should_pass_sidecar and used_sidecar is not None and consumed_pairs
        )
        p_trace["exp02_evidence_admission_status"] = (
            "admitted_execution_evidence" if evidence_consumed else "not_admitted"
        )
        p_trace["exp02_evidence_admitted_to_p_calculations"] = evidence_consumed
        validate_payload(TRACE_SCHEMA, p_trace)
        if should_pass_sidecar and not evidence_consumed:
            blockers.append(
                {
                    "code": "P_EVALUATOR_EVIDENCE_NOT_CONSUMED",
                    "details": (
                        "The verified sidecar was passed, but no exact current pair "
                        "referenced its evaluator evidence."
                    ),
                }
            )
        for admission in admissions:
            key = (
                str(admission["target_p_representation_id"] or ""),
                str(admission["obligation_id"]),
            )
            if evidence_consumed and key in consumed_pairs:
                admission["p_evidence_consumption_status"] = "consumed"
            else:
                admission["p_evidence_consumption_status"] = "not_consumed"
        if governance_result in {"HOLD", "REJECT"}:
            for code in p_trace["unresolved_prerequisites"]:
                blockers.append(
                    {
                        "code": str(code),
                        "details": f"Existing Method P governance returned {governance_result}.",
                    }
                )

    trace_reference = None
    artifact_inventory: list[dict[str, Any]] = []
    if p_trace is not None:
        trace_bytes = pretty_json_bytes(p_trace)
        trace_reference = {
            "path": P_TRACE_FILENAME,
            "sha256": sha256_bytes(trace_bytes),
            "size_bytes": len(trace_bytes),
            "role": "method_p_execution_trace",
        }
        artifact_inventory.append(trace_reference)

    p_after = str(p_bundle.snapshot["architecture"]["after_commit"]) if p_bundle else None
    p_before = str(p_bundle.snapshot["architecture"]["before_commit"]) if p_bundle else None
    unresolved = sorted(
        {
            (
                "A0.1 canonical representations are absent from the existing V3 "
                "P representation catalog."
            ),
            (
                "The V3 normalized representations do not carry criterion intent, "
                "applicability scope_id, metric units, or source artifact provenance."
            ),
            (
                "The existing evaluator_evidence contract has no field for EXP-02 "
                "metric identities and observed values."
            ),
            (
                "Runtime application source identity remains unverified without "
                "authoritative source-to-image provenance."
            ),
            (
                "The policy pilot is DRAFT/OPEN; G1 is INCOMPLETE, G4 is NOT "
                "AUTHORIZED, and P_ALGORITHM_STATUS remains NOT_READY."
            ),
        }
    )
    status = (
        "rejected"
        if evidence_verification_status == "rejected" or p_status == "rejected"
        else "blocked"
        if p_execution_status == "not_run"
        else "completed_with_blockers"
        if blockers
        else "completed"
    )
    manifest = {
        "schema_version": "1.0.0",
        "artifact_type": ARTIFACT_TYPE,
        "status": status,
        "created_at_utc": _utc_now(),
        "reproducibility": {
            "bridge_version": "EXP03_METHOD_BRIDGE_V1",
            "admission_source_sha256": sha256_bytes(Path(__file__).read_bytes()),
            "admission_schema_sha256": sha256_bytes(
                (SCHEMA_DIRECTORY / ADMISSION_SCHEMA).read_bytes()
            ),
            "trace_schema_sha256": sha256_bytes((SCHEMA_DIRECTORY / TRACE_SCHEMA).read_bytes()),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "invocation": list(invocation or sys.argv),
        },
        "exp02_input": {
            "run_directory": str(exp02_dir),
            "run_id": str(exp02_bundle["run_id"]),
            "bundle_schema_version": str(exp02_bundle["schema_version"]),
            "bundle_status": str(exp02_bundle["bundle_status"]),
            "bundle_reference": {
                "path": BUNDLE_FILENAME,
                "sha256": sha256_bytes(bundle_bytes),
                "size_bytes": len(bundle_bytes),
                "role": "exp01_evidence_bundle",
            },
            "representation_evidence_reference": dict(
                exp02_bundle["fitness_representation_evidence"]
            ),
            "source_revision": str(evidence["source_revision"]),
            "source_git_dirty": bool(exp02_bundle["source_revision"].get("git_dirty", False)),
            "architecture_state": str(evidence["architecture_state"]),
            "artifact_validation_status": "validated_by_exp01_exp02_contracts",
            "runtime_application_identity_status": sorted(
                {
                    str(item["evaluator_execution"]["runtime_source_binding_status"])
                    for item in evidence["representations"]
                    if item["lifecycle_stage"] == "runtime"
                }
            ),
        },
        "p_input": {
            "status": p_status,
            "reference": p_input_reference,
        },
        "external_evidence": {
            "sidecar_reference": sidecar_reference,
            "verifier_config_reference": trust_reference,
            "verification_status": evidence_verification_status,
            "trust_scope": (
                verified_sidecar.trust_scope
                if verified_sidecar is not None
                else trust_reference.get("trust_scope")
                if trust_reference
                else None
            ),
            "verifier_id": (
                verified_sidecar.verifier_id
                if verified_sidecar is not None
                else trust_reference.get("verifier_id")
                if trust_reference
                else None
            ),
            "error": external_error,
        },
        "representation_admissions": admissions,
        "method_p": {
            "execution_status": p_execution_status,
            "input_bundle_sha256": str(p_bundle.manifest["bundle_sha256"]) if p_bundle else None,
            "architecture_before_sha": p_before,
            "architecture_after_sha": p_after,
            "evidence_consumption_status": "consumed" if evidence_consumed else "not_consumed",
            "exp02_observations_used_as_semantic_pair_proof": False,
            "adaptation_evidence_trust_scope": (
                verified_sidecar.trust_scope if verified_sidecar is not None else None
            ),
            "governance_result": governance_result,
            "prediction_v1_emitted": bool(p_trace and p_trace["prediction_v1"] is not None),
            "trace_reference": trace_reference,
        },
        "coverage_claims": {
            "Coverage_P": "not_assessed",
            "Coverage_ref": "not_established",
            "semantic_validity": "not_independently_validated",
        },
        "blockers": sorted({(str(item["code"]), str(item["details"])) for item in blockers}),
        "unresolved_prerequisites": unresolved,
        "artifact_inventory": artifact_inventory,
    }
    manifest["blockers"] = [
        {"code": code, "details": details} for code, details in manifest["blockers"]
    ]
    validate_payload(ADMISSION_SCHEMA, manifest)
    return manifest, p_trace


def validate_admission_output(
    output_dir: Path, *, trust_context: Any | None = None
) -> dict[str, Any]:
    """Read back and verify the EXP-04 manifest, source bindings, trace and artifacts."""
    if output_dir.is_symlink():
        raise ValueError("EXP-04 output directory must not be a symlink")
    root = output_dir.resolve(strict=True)
    manifest_path = root / MANIFEST_FILENAME
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("EXP-04 admission manifest is missing or is a symlink")
    manifest_bytes = manifest_path.read_bytes()
    try:
        manifest = json.loads(manifest_bytes)
    except json.JSONDecodeError as error:
        raise ValueError("EXP-04 admission manifest is invalid JSON") from error
    if not isinstance(manifest, dict):
        raise ValueError("EXP-04 admission manifest must be an object")
    validate_payload(ADMISSION_SCHEMA, manifest)
    reproducibility = manifest["reproducibility"]
    if (
        reproducibility["admission_source_sha256"] != sha256_bytes(Path(__file__).read_bytes())
        or reproducibility["admission_schema_sha256"]
        != sha256_bytes((SCHEMA_DIRECTORY / ADMISSION_SCHEMA).read_bytes())
        or reproducibility["trace_schema_sha256"]
        != sha256_bytes((SCHEMA_DIRECTORY / TRACE_SCHEMA).read_bytes())
    ):
        raise ValueError("EXP-04 source or schema digest differs from the recorded run")

    declared: dict[str, Mapping[str, Any]] = {}
    trace: dict[str, Any] | None = None
    for reference in manifest["artifact_inventory"]:
        relative = PurePosixPath(str(reference["path"]))
        if relative.is_absolute() or ".." in relative.parts or relative.as_posix() in declared:
            raise ValueError("EXP-04 artifact inventory contains an unsafe or duplicate path")
        target = root.joinpath(*relative.parts)
        if target.is_symlink() or not target.is_file():
            raise ValueError(f"EXP-04 generated artifact is missing: {relative.as_posix()}")
        content = target.read_bytes()
        if len(content) != reference["size_bytes"] or sha256_bytes(content) != reference["sha256"]:
            raise ValueError(f"EXP-04 output digest mismatch: {relative.as_posix()}")
        if reference["role"] == "method_p_execution_trace":
            try:
                parsed_trace = json.loads(content)
            except json.JSONDecodeError as error:
                raise ValueError("EXP-04 Method P trace is invalid JSON") from error
            validate_payload(TRACE_SCHEMA, parsed_trace)
            trace = cast(dict[str, Any], parsed_trace)
        else:
            raise ValueError("EXP-04 output inventory has an unsupported artifact role")
        declared[relative.as_posix()] = reference
    if len(declared) != (1 if trace is not None else 0):
        raise ValueError("EXP-04 output inventory must contain exactly its optional P trace")
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name not in {MANIFEST_FILENAME, MANIFEST_DIGEST_FILENAME}
    }
    if actual != set(declared):
        raise ValueError("EXP-04 output inventory does not exactly match generated artifacts")
    digest_path = root / MANIFEST_DIGEST_FILENAME
    if digest_path.is_symlink() or not digest_path.is_file():
        raise ValueError("EXP-04 manifest digest file is missing")
    if digest_path.read_text(encoding="ascii") != (
        f"{sha256_bytes(manifest_bytes)}  {MANIFEST_FILENAME}\n"
    ):
        raise ValueError("EXP-04 manifest digest file does not match the manifest")

    exp02_ref = manifest["exp02_input"]
    exp02_dir = Path(exp02_ref["run_directory"])
    bundle, evidence, _, bundle_bytes = exp03._load_exp02(exp02_dir)
    if (
        bundle["run_id"] != exp02_ref["run_id"]
        or bundle["schema_version"] != exp02_ref["bundle_schema_version"]
        or bundle["bundle_status"] != exp02_ref["bundle_status"]
        or sha256_bytes(bundle_bytes) != exp02_ref["bundle_reference"]["sha256"]
        or exp02_ref["bundle_reference"]["path"] != BUNDLE_FILENAME
        or exp02_ref["bundle_reference"]["size_bytes"] != len(bundle_bytes)
        or exp02_ref["bundle_reference"]["role"] != "exp01_evidence_bundle"
        or evidence["source_revision"] != exp02_ref["source_revision"]
        or evidence["architecture_state"] != exp02_ref["architecture_state"]
        or bool(bundle["source_revision"].get("git_dirty", False)) != exp02_ref["source_git_dirty"]
        or bundle["fitness_representation_evidence"]
        != exp02_ref["representation_evidence_reference"]
        or sorted(
            {
                str(item["evaluator_execution"]["runtime_source_binding_status"])
                for item in evidence["representations"]
                if item["lifecycle_stage"] == "runtime"
            }
        )
        != exp02_ref["runtime_application_identity_status"]
    ):
        raise ValueError("EXP-04 EXP-02 source references disagree with validated inputs")

    sidecar_reference = manifest["external_evidence"]["sidecar_reference"]
    trust_reference = manifest["external_evidence"]["verifier_config_reference"]
    sidecar = None
    if trust_reference is not None:
        config_trust_context, recomputed_trust_reference = _external_trust_context(
            Path(trust_reference["config_reference"]["path"])
        )
        if recomputed_trust_reference != trust_reference:
            raise ValueError("EXP-04 external verifier reference disagrees with its configuration")
        trust_context = config_trust_context
    if sidecar_reference is not None:
        sidecar_path, sidecar_bytes, sidecar = _load_sidecar(Path(sidecar_reference["path"]))
        if (
            _file_reference(sidecar_path, sidecar_bytes, "p_adaptation_evidence_v2_sidecar")
            != sidecar_reference
        ):
            raise ValueError("EXP-04 external sidecar reference digest mismatch")

    p_reference = manifest["p_input"]["reference"]
    p_bundle: VerifiedPBundle | None = None
    if manifest["p_input"]["status"] == "verified":
        if not isinstance(p_reference, Mapping):
            raise ValueError("EXP-04 verified V3 input reference is missing")
        p_dir = Path(str(p_reference["directory"]))
        p_bundle = exp03.verify_method_p_input(p_dir, trust_context=trust_context)
        manifest_file, manifest_bytes_v3 = _read_regular_file(
            p_dir / "method_input_v3.json", "V3 method input manifest"
        )
        if (
            str(p_bundle.root) != p_reference["directory"]
            or p_bundle.manifest["bundle_sha256"] != p_reference["bundle_sha256"]
            or _file_reference(manifest_file, manifest_bytes_v3, "method_p_v3_manifest")
            != p_reference["manifest"]
            or p_bundle.snapshot["architecture"]["after_commit"]
            != p_reference["architecture_after_sha"]
            or p_bundle.snapshot["architecture"]["before_commit"]
            != p_reference["architecture_before_sha"]
            or p_bundle.manifest["policy_source_revision"] != p_reference["policy_source_revision"]
            or p_bundle.manifest["policy_bundle_sha256"] != p_reference["policy_bundle_sha256"]
        ):
            raise ValueError("EXP-04 V3 input references disagree with the verified bundle")
    elif p_reference is not None:
        raise ValueError("EXP-04 rejected or absent V3 input must not retain a verified reference")

    readback_verified: VerifiedAdaptationEvidence | None = None
    if sidecar is not None and p_bundle is not None:
        try:
            readback_verified = exp03.verify_method_p_evidence_sidecar(p_bundle, sidecar)
        except (ValueError, ContractValidationError) as error:
            readback_verified = None
            if manifest["external_evidence"]["verification_status"] != "rejected":
                raise ValueError("EXP-04 external sidecar failed readback verification") from error
        if manifest["external_evidence"]["verification_status"] == "verified":
            if readback_verified is None:
                raise ValueError("EXP-04 verified sidecar no longer has an available authority")
        elif manifest["external_evidence"]["verification_status"] == "authority_missing":
            if readback_verified is not None:
                raise ValueError("EXP-04 verifier status contradicts sidecar verification")

    expected_external_scope = (
        readback_verified.trust_scope
        if readback_verified is not None
        else trust_reference.get("trust_scope")
        if trust_reference is not None
        else None
    )
    expected_verifier_id = (
        readback_verified.verifier_id
        if readback_verified is not None
        else trust_reference.get("verifier_id")
        if trust_reference is not None
        else None
    )
    if (
        manifest["external_evidence"]["trust_scope"] != expected_external_scope
        or manifest["external_evidence"]["verifier_id"] != expected_verifier_id
    ):
        raise ValueError("EXP-04 verifier identity and scope disagree with verified authority")

    expected_admissions = _strict_representation_mappings(
        run_dir=exp02_dir,
        exp02_bundle=bundle,
        evidence=evidence,
        configuration=exp03._configuration_for_run(exp02_dir, bundle)[0],
        p_bundle=p_bundle,
    )
    stored_by_key = {
        (row["exp02_representation_id"], row["obligation_id"]): row
        for row in manifest["representation_admissions"]
    }
    expected_by_key = {
        (row["exp02_representation_id"], row["obligation_id"]): row for row in expected_admissions
    }
    if set(stored_by_key) != set(expected_by_key):
        raise ValueError("EXP-04 representation admission inventory differs from EXP-02 input")

    expected_sidecar_match = False
    expected_sidecar_reasons: list[str] = []
    if readback_verified is not None:
        expected_sidecar_match, expected_sidecar_reasons = _sidecar_observation_match(
            verified=readback_verified,
            admissions=expected_admissions,
            run_id=str(bundle["run_id"]),
            run_dir=exp02_dir,
            exp02_bundle=bundle,
        )
        if readback_verified.trust_scope != "PRODUCTION":
            expected_sidecar_match = False
            expected_sidecar_reasons.append("TEST_ONLY_EVIDENCE_CANNOT_AUTHORIZE_EXP04_ADMISSION")
        signed_pair_proofs = thaw_verified_payload(readback_verified).get("pair_proofs", [])
        if any(
            isinstance(row, Mapping) and row.get("status") == "VALID" for row in signed_pair_proofs
        ):
            expected_sidecar_match = False
            expected_sidecar_reasons.append(
                "POSITIVE_SEMANTIC_PROOF_REQUIRES_SEPARATE_G1_G4_AUTHORIZATION"
            )
    evidence_status = manifest["external_evidence"]["verification_status"]
    for key, expected in expected_by_key.items():
        stored = stored_by_key[key]
        for field_name in (
            "criterion_id",
            "criterion_intent",
            "observation_status",
            "exp02_evaluator",
            "execution",
            "scope",
            "metrics",
            "observed_compliance",
            "target_p_representation_id",
            "candidate_p_representation_ids",
            "binding_checks",
        ):
            if stored[field_name] != expected[field_name]:
                raise ValueError("EXP-04 admission fields disagree with validated source evidence")
        if stored["external_semantic_proof_status"] != _pair_proof_status(
            readback_verified,
            cast(str | None, expected["target_p_representation_id"]),
            str(expected["obligation_id"]),
        ):
            raise ValueError("EXP-04 semantic proof status disagrees with the verified sidecar")
        expected_admission_status = str(expected["admission_status"])
        expected_reason_codes = set(expected["reason_codes"])
        if evidence_status == "rejected":
            expected_admission_status = "rejected"
            expected_reason_codes.add("EXTERNAL_AUTHORIZATION_REJECTED")
        elif expected_admission_status != "validated_observation":
            expected_admission_status = "mapping_unresolved"
        elif readback_verified is None:
            expected_admission_status = "authority_missing"
            expected_reason_codes.add("EXTERNAL_VERIFIER_AUTHORITY_MISSING")
        elif not expected_sidecar_match:
            expected_admission_status = "rejected"
            expected_reason_codes.update(expected_sidecar_reasons)
        else:
            expected_admission_status = "admitted_execution_evidence"
        if stored["admission_status"] != expected_admission_status:
            raise ValueError("EXP-04 admission status contradicts verified inputs and authority")
        if set(stored["reason_codes"]) != expected_reason_codes:
            raise ValueError("EXP-04 admission reasons contradict verified inputs and authority")
    if trace is None:
        if (
            manifest["method_p"]["execution_status"] != "not_run"
            or manifest["method_p"]["trace_reference"] is not None
        ):
            raise ValueError("EXP-04 Method P execution status disagrees with trace presence")
    else:
        method_p = manifest["method_p"]
        trace_reference = next(
            (
                reference
                for reference in manifest["artifact_inventory"]
                if reference["role"] == "method_p_execution_trace"
            ),
            None,
        )
        if (
            method_p["execution_status"] != "completed"
            or method_p["trace_reference"] != trace_reference
            or trace["input_bundle_sha256"] != method_p["input_bundle_sha256"]
            or trace["architecture"]["before_commit"] != method_p["architecture_before_sha"]
            or trace["architecture"]["after_commit"] != method_p["architecture_after_sha"]
            or trace["exp02_evidence_admitted_to_p_calculations"]
            != (method_p["evidence_consumption_status"] == "consumed")
            or trace["exp02_observations_used_as_semantic_pair_evidence"] is not False
            or trace["prediction_v1"] is not None
            or trace["candidate_v1"] is not None
            or trace["adaptation_evidence_trust_scope"]
            != method_p["adaptation_evidence_trust_scope"]
        ):
            raise ValueError("EXP-04 manifest and Method P trace disagree")
        if method_p["governance_result"] != trace["governance"]["result"]:
            raise ValueError("EXP-04 governance result disagrees with Method P trace")
        trace_pairs = {
            (str(row["representation_id"]), str(row["obligation_id"])): row
            for row in trace["current_pairs"]
        }
        sidecar_evidence_rows: dict[tuple[str, str], Mapping[str, Any]] = {}
        if readback_verified is not None and expected_sidecar_match:
            for row in thaw_verified_payload(readback_verified).get("evaluator_evidence", []):
                if isinstance(row, Mapping) and isinstance(row.get("evidence"), Mapping):
                    sidecar_evidence_rows[
                        (str(row["representation_id"]), str(row["obligation_id"]))
                    ] = row["evidence"]
        for key, pair in trace_pairs.items():
            evidence_digest = pair.get("evaluator_evidence_sha256")
            if evidence_digest is None:
                continue
            sidecar_evidence = sidecar_evidence_rows.get(key)
            if (
                sidecar_evidence is None
                or sha256_bytes(canonical_json_bytes(dict(sidecar_evidence))) != evidence_digest
            ):
                raise ValueError(
                    "EXP-04 Method P trace evidence is not bound to the verified sidecar"
                )
        for admission in manifest["representation_admissions"]:
            pair = trace_pairs.get(
                (
                    str(admission["target_p_representation_id"] or ""),
                    str(admission["obligation_id"]),
                )
            )
            expected_consumption = (
                "consumed"
                if method_p["evidence_consumption_status"] == "consumed"
                and pair is not None
                and pair.get("evaluator_evidence_sha256")
                else "not_consumed"
            )
            if admission["p_evidence_consumption_status"] != expected_consumption:
                raise ValueError("EXP-04 per-representation evidence consumption is inconsistent")
    if manifest["coverage_claims"] != {
        "Coverage_P": "not_assessed",
        "Coverage_ref": "not_established",
        "semantic_validity": "not_independently_validated",
    }:
        raise ValueError("EXP-04 coverage claims exceed the DEVELOPMENT evidence boundary")
    return cast(dict[str, Any], manifest)


def write_admission_run(
    exp02_run_dir: Path,
    output_dir: Path,
    *,
    p_input_dir: Path | None = None,
    evidence_sidecar_path: Path | None = None,
    trust_config_path: Path | None = None,
    trust_context: Any | None = None,
    invocation: Sequence[str] | None = None,
) -> tuple[dict[str, Any], str]:
    """Write one unique EXP-04 run directory and validate all output digests."""
    destination = output_dir.resolve(strict=False)
    if output_dir.is_symlink() or destination.exists():
        raise FileExistsError(f"refusing to overwrite EXP-04 output directory: {destination}")
    if destination == exp02_run_dir.resolve(strict=True):
        raise ValueError("EXP-04 output directory must not replace its EXP-02 input")
    manifest, trace = build_admission_artifact(
        exp02_run_dir,
        p_input_dir=p_input_dir,
        evidence_sidecar_path=evidence_sidecar_path,
        trust_config_path=trust_config_path,
        trust_context=trust_context,
        invocation=invocation,
    )
    parent = destination.parent
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{destination.name}.", dir=parent) as temporary:
        staging = Path(temporary) / "run"
        staging.mkdir()
        if trace is not None:
            (staging / P_TRACE_FILENAME).write_bytes(pretty_json_bytes(trace))
        manifest_bytes = pretty_json_bytes(manifest)
        (staging / MANIFEST_FILENAME).write_bytes(manifest_bytes)
        manifest_digest = sha256_bytes(manifest_bytes)
        (staging / MANIFEST_DIGEST_FILENAME).write_text(
            f"{manifest_digest}  {MANIFEST_FILENAME}\n", encoding="ascii"
        )
        validate_admission_output(staging, trust_context=trust_context)
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(f"refusing to overwrite EXP-04 output directory: {destination}")
        os.rename(staging, destination)
    return validate_admission_output(destination, trust_context=trust_context), manifest_digest


def main(argv: list[str] | None = None) -> int:
    """Run the write-once EXP-04 DEVELOPMENT admission pipeline."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exp02-run-dir", required=True, type=Path)
    parser.add_argument("--p-input-dir", type=Path)
    parser.add_argument("--evidence-sidecar", type=Path)
    parser.add_argument("--trust-config", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        manifest, digest = write_admission_run(
            args.exp02_run_dir,
            args.output_dir,
            p_input_dir=args.p_input_dir,
            evidence_sidecar_path=args.evidence_sidecar,
            trust_config_path=args.trust_config,
            invocation=["python", "-m", "scripts.exp04_evidence_admission", *sys.argv[1:]],
        )
    except (OSError, ValueError, ProtocolError, ContractValidationError) as error:
        print(json.dumps({"status": "input_rejected", "error": str(error)}, sort_keys=True))
        return 1
    summary = {
        "status": manifest["status"],
        "exp02_run_id": manifest["exp02_input"]["run_id"],
        "p_input_status": manifest["p_input"]["status"],
        "evidence_verification_status": manifest["external_evidence"]["verification_status"],
        "representation_admissions": {
            status: sum(
                row["admission_status"] == status for row in manifest["representation_admissions"]
            )
            for status in (
                "validated_observation",
                "mapping_unresolved",
                "authority_missing",
                "admitted_execution_evidence",
                "rejected",
            )
        },
        "p_execution_status": manifest["method_p"]["execution_status"],
        "evidence_consumption_status": manifest["method_p"]["evidence_consumption_status"],
        "governance_result": manifest["method_p"]["governance_result"],
        "output_dir": str(args.output_dir.resolve(strict=True)),
        "manifest_sha256": digest,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    if manifest["status"] == "rejected":
        return 1
    return 0 if manifest["method_p"]["execution_status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
