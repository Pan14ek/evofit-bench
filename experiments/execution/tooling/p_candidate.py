"""Candidate configuration materialization and unchanged V1 output adapters."""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from typing import Any

import yaml

from experiments.execution.tooling.contracts import (
    validate_candidate,
    validate_payload,
    validate_prediction,
)
from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.hashing import canonical_json_bytes, sha256_bytes
from experiments.execution.tooling.p_governance import (
    GovernanceDecision,
    governance_authorizes_outputs,
)
from experiments.execution.tooling.p_operations import (
    OperationKind,
    OperationPlan,
    PlannedOperation,
)

_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_SHA1 = re.compile(r"^[a-f0-9]{40}$")
_SAFE_PATH = re.compile(r"^(?!/)(?!.*(?:^|/)\.\.(?:/|$))[A-Za-z0-9_./-]+$")
_V1_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def materialize_candidate(
    *,
    parent_configuration: Mapping[str, Any],
    parent_configuration_bytes: bytes,
    parent_path: str,
    parent_sha256: str,
    architecture_source_sha: str,
    policy_source_revision: str,
    policy_bundle_sha256: str,
    policy_ruleset_sha256: str,
    input_bundle_sha256: str,
    impact_assessment_sha256: str,
    method_version: str,
    configuration_version: str,
    operation_plan: OperationPlan,
    artifact_bytes: Mapping[str, bytes],
    valid_obligation_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Apply a reviewed plan to an immutable copy and validate exact artifact bytes."""
    if not _SHA1.fullmatch(architecture_source_sha):
        raise ContractValidationError("P03_CANDIDATE_ARCHITECTURE_SHA_INVALID")
    if (
        not _SHA256.fullmatch(parent_sha256)
        or sha256_bytes(parent_configuration_bytes) != parent_sha256
    ):
        raise ContractValidationError("P03_PARENT_CONFIGURATION_DIGEST_MISMATCH")
    parent_snapshot = _bind_parent_configuration(parent_configuration, parent_configuration_bytes)
    if not isinstance(parent_path, str) or _SAFE_PATH.fullmatch(parent_path) is None:
        raise ContractValidationError("P03_PARENT_CONFIGURATION_PATH_INVALID")
    if operation_plan.reject_reasons:
        raise ContractValidationError("P03_OPERATION_PLAN_REJECTED")
    _validate_operation_plan(operation_plan)
    rows_value = parent_snapshot.get("representations")
    if not isinstance(rows_value, list):
        raise ContractValidationError("P03_PARENT_REPRESENTATIONS_INVALID")
    representations = [copy.deepcopy(dict(row)) for row in rows_value if isinstance(row, Mapping)]
    if len(representations) != len(rows_value):
        raise ContractValidationError("P03_PARENT_REPRESENTATION_ROW_INVALID")
    by_id = {str(row.get("id")): row for row in representations}
    if len(by_id) != len(representations):
        raise ContractValidationError("P03_PARENT_REPRESENTATION_ID_DUPLICATE")
    changes = [operation.to_dict() for operation in operation_plan.operations]
    for operation in operation_plan.operations:
        _apply_operation(operation, by_id, representations)
    for row in representations:
        row.setdefault("evaluator_artifact", None)
        row.setdefault("applicability_scope", {})
        row.setdefault("evidence_contract", {})
        row.setdefault("active", True)
        row.setdefault("covers", [])
        if "soft_parameters" in row and not isinstance(row["soft_parameters"], Mapping):
            raise ContractValidationError("P03_SOFT_PARAMETERS_INVALID")
    payload: dict[str, Any] = {
        "schema_version": 1,
        "method_id": "P",
        "method_version": method_version,
        "architecture_source_sha": architecture_source_sha,
        "policy_source_revision": policy_source_revision,
        "policy_bundle_sha256": policy_bundle_sha256,
        "policy_ruleset_sha256": policy_ruleset_sha256,
        "input_bundle_sha256": input_bundle_sha256,
        "impact_assessment_sha256": impact_assessment_sha256,
        "configuration_version": configuration_version,
        "parent_configuration": {"path": parent_path, "sha256": parent_sha256},
        "representations": sorted(representations, key=lambda row: str(row.get("id"))),
        "soft_parameter_overrides": [
            operation.to_dict()
            for operation in operation_plan.operations
            if operation.operation is OperationKind.ADJUST
        ],
        "changes": changes,
        "candidate_validation": {"status": "not_run", "reason_codes": [], "evidence_refs": []},
    }
    validate_payload("p_candidate_configuration_v1.schema.json", payload)
    issues = _candidate_semantic_issues(
        payload["representations"], artifact_bytes, valid_obligation_ids
    )
    unmaterialized = {"ACTIVE_EVALUATOR_ARTIFACT_UNAVAILABLE", "EVALUATOR_ARTIFACT_BYTES_MISSING"}
    payload["candidate_validation"] = {
        "status": "failed" if issues & unmaterialized else "invalid" if issues else "valid",
        "reason_codes": sorted(issues),
        "evidence_refs": sorted(
            {
                str(row["evaluator_artifact"]["path"])
                for row in payload["representations"]
                if isinstance(row.get("evaluator_artifact"), Mapping)
            }
        ),
    }
    validate_payload("p_candidate_configuration_v1.schema.json", payload)
    return payload


def derive_configuration_version(
    *,
    parent_configuration_sha256: str,
    operation_plan_sha256: str,
    architecture_source_sha: str,
    policy_source_revision: str,
    policy_bundle_sha256: str,
) -> str:
    """Return a deterministic child version ID bound to its validated context.

    This development identifier is content-derived. It does not settle a
    production naming or release convention for configuration versions.
    """
    identity = {
        "parent_configuration_sha256": parent_configuration_sha256,
        "operation_plan_sha256": operation_plan_sha256,
        "architecture_source_sha": architecture_source_sha,
        "policy_source_revision": policy_source_revision,
        "policy_bundle_sha256": policy_bundle_sha256,
    }
    return "p-candidate-" + sha256_bytes(canonical_json_bytes(identity))[:32]


def _validate_operation_plan(operation_plan: OperationPlan) -> None:
    keys = [(item.target_type, item.target_id) for item in operation_plan.operations]
    if len(keys) != len(set(keys)):
        raise ContractValidationError("P03_OPERATION_TARGET_DUPLICATE")
    semantic = {
        "operations": [item.to_dict() for item in operation_plan.operations],
        "hold_reasons": sorted(set(operation_plan.hold_reasons)),
        "reject_reasons": sorted(set(operation_plan.reject_reasons)),
    }
    if sha256_bytes(canonical_json_bytes(semantic)) != operation_plan.plan_sha256:
        raise ContractValidationError("P03_OPERATION_PLAN_DIGEST_MISMATCH")


def candidate_sha256(candidate: Mapping[str, Any]) -> str:
    """Return the stable semantic digest of the complete development candidate."""
    validate_payload("p_candidate_configuration_v1.schema.json", dict(candidate))
    return sha256_bytes(canonical_json_bytes(dict(candidate)))


def normalize_parent_representation(row: Any) -> dict[str, Any]:
    """Normalize one source representation into the configuration projection."""
    required = ("id", "criterion", "stage", "evaluator", "covers")
    if not isinstance(row, Mapping) or any(
        not isinstance(row.get(key), list if key == "covers" else str) for key in required
    ):
        raise ContractValidationError("P03_PARENT_REPRESENTATION_INVALID")
    scope = row.get("applicability_scope")
    evidence_contract = row.get("evidence_contract")
    return {
        "id": row["id"],
        "active": True,
        "criterion": row["criterion"],
        "stage": row["stage"],
        "evaluator": row["evaluator"],
        "evaluator_artifact": row.get("evaluator_artifact"),
        "covers": sorted({value for value in row["covers"] if isinstance(value, str)}),
        "applicability_scope": dict(scope) if isinstance(scope, Mapping) else {},
        "evidence_contract": dict(evidence_contract)
        if isinstance(evidence_contract, Mapping)
        else {},
    }


def _bind_parent_configuration(
    parent_configuration: Mapping[str, Any], parent_configuration_bytes: bytes
) -> dict[str, Any]:
    """Validate one detached parent view and return the bytes-derived snapshot."""
    try:
        parsed_source = yaml.safe_load(parent_configuration_bytes)
        if not isinstance(parsed_source, Mapping):
            raise ContractValidationError("P03_PARENT_CONFIGURATION_CONTENT_MISMATCH")
        source_value = _snapshot_json_value(parsed_source)
        if not isinstance(source_value, dict):
            raise ContractValidationError("P03_PARENT_CONFIGURATION_CONTENT_MISMATCH")
        source: dict[str, Any] = source_value
        supplied = _snapshot_json_value(parent_configuration)
        if canonical_json_bytes(source) == canonical_json_bytes(supplied):
            return source
        source_rows = source.get("representations")
        schema_version = source.get("schema_version", 1)
        if (
            not isinstance(source_rows, list)
            or not isinstance(schema_version, int)
            or isinstance(schema_version, bool)
            or schema_version != 1
        ):
            raise ContractValidationError("P03_PARENT_CONFIGURATION_CONTENT_MISMATCH")
        projection = {
            "schema_version": 1,
            "representations": [normalize_parent_representation(row) for row in source_rows],
        }
        if canonical_json_bytes(projection) != canonical_json_bytes(supplied):
            raise ContractValidationError("P03_PARENT_CONFIGURATION_CONTENT_MISMATCH")
        projection_snapshot = _snapshot_json_value(projection)
        if not isinstance(projection_snapshot, dict):
            raise ContractValidationError("P03_PARENT_CONFIGURATION_CONTENT_MISMATCH")
        return projection_snapshot
    except (TypeError, ValueError, RecursionError, yaml.YAMLError) as error:
        raise ContractValidationError("P03_PARENT_CONFIGURATION_CONTENT_MISMATCH") from error


def _snapshot_json_value(value: Any) -> Any:
    """Detach JSON-shaped values from caller-owned or stateful mappings."""
    if isinstance(value, Mapping):
        items = list(value.items())
        if any(not isinstance(key, str) for key, _ in items):
            raise TypeError("Configuration mapping keys must be strings")
        return {key: _snapshot_json_value(item) for key, item in items}
    if isinstance(value, list | tuple):
        return [_snapshot_json_value(item) for item in value]
    if value is None or isinstance(value, str | bool | int | float):
        return value
    raise TypeError("Configuration values must be JSON-compatible")


def adapt_candidate_v1(
    candidate: Mapping[str, Any], *, governance: GovernanceDecision
) -> dict[str, Any]:
    """Project only the exact candidate authorized by a sealed governance ACCEPT."""
    validate_payload("p_candidate_configuration_v1.schema.json", dict(candidate))
    if not governance_authorizes_outputs(
        governance,
        candidate_configuration_sha256=candidate_sha256(candidate),
        architecture_source_sha=str(candidate.get("architecture_source_sha", "")),
        input_bundle_sha256=str(candidate.get("input_bundle_sha256", "")),
        operations=candidate.get("changes", []),
    ):
        raise ContractValidationError("P03_V1_OUTPUT_NOT_GOVERNED_ACCEPT")
    rows: list[dict[str, Any]] = []
    for source in candidate["representations"]:
        if not isinstance(source, Mapping):
            raise ContractValidationError("P03_CANDIDATE_V1_REPRESENTATION_INVALID")
        representation_id = str(source.get("id", ""))
        if not _V1_ID.fullmatch(representation_id):
            raise ContractValidationError("PREDICTION_V1_ID_UNREPRESENTABLE")
        rows.append(
            {
                key: copy.deepcopy(source[key])
                for key in (
                    "id",
                    "active",
                    "criterion",
                    "stage",
                    "evaluator",
                    "evaluator_artifact",
                    "covers",
                    "applicability_scope",
                    "evidence_contract",
                )
            }
        )
    legacy = {
        "schema_version": 1,
        "method_id": "P",
        "architecture_source_sha": candidate["architecture_source_sha"],
        "configuration_version": candidate["configuration_version"],
        "parent_configuration": dict(candidate["parent_configuration"]),
        "representations": rows,
        "changes": copy.deepcopy(candidate["changes"]),
        "candidate_validation": copy.deepcopy(candidate["candidate_validation"]),
    }
    validate_candidate(legacy)
    return legacy


def adapt_prediction_v1(
    *,
    architecture_source_sha: str,
    method_version: str,
    input_bundle_sha256: str,
    plan: OperationPlan,
    impact_records: Sequence[Mapping[str, Any]],
    candidate_configuration_sha256: str,
    governance: GovernanceDecision,
) -> dict[str, Any]:
    """Project only an accepted plan to the unchanged prediction-v1 contract.

    HOLD and INPUT_REJECTED are diagnostic outcomes and cannot be passed as a
    valid legacy prediction. The caller must only invoke this for a complete
    algorithm prediction, not as a way to mask unresolved evidence.
    """
    if plan.hold_reasons or plan.reject_reasons:
        raise ContractValidationError("PREDICTION_V1_UNAVAILABLE_FOR_BLOCKED_PLAN")
    if not governance_authorizes_outputs(
        governance,
        candidate_configuration_sha256=candidate_configuration_sha256,
        architecture_source_sha=architecture_source_sha,
        input_bundle_sha256=input_bundle_sha256,
        operations=[operation.to_dict() for operation in plan.operations],
    ):
        raise ContractValidationError("P03_V1_OUTPUT_NOT_GOVERNED_ACCEPT")
    affected: list[dict[str, str]] = []
    proposed: list[dict[str, str]] = []
    explanations: list[dict[str, Any]] = []
    for operation in plan.operations:
        if not _V1_ID.fullmatch(operation.target_id):
            raise ContractValidationError("PREDICTION_V1_ID_UNREPRESENTABLE")
        proposed.append(
            {
                "target_type": operation.target_type,
                "target_id": operation.target_id,
                "operation": operation.operation.value,
            }
        )
        if operation.operation is not OperationKind.RETAIN:
            affected.append(
                {
                    "target_type": operation.target_type,
                    "target_id": operation.target_id,
                    "predicted_operation": operation.operation.value,
                }
            )
            explanations.append(
                {
                    "target_type": operation.target_type,
                    "target_id": operation.target_id,
                    "rationale": ",".join(operation.reason_codes),
                    "evidence_refs": list(operation.evidence_refs),
                    "uncertainty": None,
                }
            )
    payload = {
        "schema_version": 1,
        "method_id": "P",
        "architecture_source_sha": architecture_source_sha,
        "method_version": method_version,
        "input_bundle_sha256": input_bundle_sha256,
        "predicted_affected": affected,
        "proposed_operations": proposed,
        "explanations": explanations,
        "artifact_hashes": {
            str(operation.payload["id"]): operation.artifact_sha256
            for operation in plan.operations
            if operation.payload is not None and operation.artifact_sha256 is not None
        },
    }
    validate_prediction(payload)
    return payload


def _apply_operation(
    operation: PlannedOperation,
    by_id: dict[str, dict[str, Any]],
    representations: list[dict[str, Any]],
) -> None:
    if operation.target_type == "representation":
        current = by_id.get(operation.target_id)
        if current is None:
            raise ContractValidationError("P03_OPERATION_TARGET_MISSING")
        if operation.operation is OperationKind.DEACTIVATE:
            current["active"] = False
        elif operation.operation is OperationKind.REPLACE:
            if not isinstance(operation.payload, Mapping):
                raise ContractValidationError("P03_REPLACEMENT_PAYLOAD_MISSING")
            new_id = str(operation.payload.get("id", ""))
            if not new_id or new_id in by_id:
                raise ContractValidationError("P03_REPLACEMENT_ID_COLLISION")
            current["active"] = False
            new_representation = copy.deepcopy(dict(operation.payload))
            new_representation["active"] = True
            by_id[new_id] = new_representation
            representations.append(new_representation)
        elif operation.operation is OperationKind.ADJUST:
            if not isinstance(operation.payload, Mapping):
                raise ContractValidationError("P03_ADJUSTMENT_PAYLOAD_MISSING")
            parameter = str(operation.payload.get("parameter", ""))
            parameters = dict(current.get("soft_parameters", {}))
            if parameters.get(parameter) != operation.payload.get("old_value"):
                raise ContractValidationError("P03_ADJUSTMENT_STALE_OLD_VALUE")
            parameters[parameter] = operation.payload.get("new_value")
            current["soft_parameters"] = parameters
        elif operation.operation is not OperationKind.RETAIN:
            raise ContractValidationError("P03_REPRESENTATION_OPERATION_INVALID")
    elif operation.target_type == "obligation" and operation.operation is OperationKind.ADD:
        if not isinstance(operation.payload, Mapping):
            raise ContractValidationError("P03_ADDITION_PAYLOAD_MISSING")
        new_id = str(operation.payload.get("id", ""))
        if not new_id or new_id in by_id:
            raise ContractValidationError("P03_ADDITION_ID_COLLISION")
        new_representation = copy.deepcopy(dict(operation.payload))
        new_representation["active"] = True
        by_id[new_id] = new_representation
        representations.append(new_representation)
    else:
        raise ContractValidationError("P03_OPERATION_TARGET_KIND_INVALID")


def _candidate_semantic_issues(
    representations: Sequence[Mapping[str, Any]],
    artifact_bytes: Mapping[str, bytes],
    valid_obligation_ids: Sequence[str] | None,
) -> set[str]:
    issues: set[str] = set()
    seen: set[str] = set()
    allowed_obligations = set(valid_obligation_ids) if valid_obligation_ids is not None else None
    for representation in representations:
        representation_id = representation.get("id")
        if representation_id in seen:
            issues.add("DUPLICATE_REPRESENTATION_ID")
        seen.add(str(representation_id))
        if allowed_obligations is not None and not _string_values(
            representation.get("covers")
        ).issubset(allowed_obligations):
            issues.add("ORPHANED_OBLIGATION_LINK")
        artifact = representation.get("evaluator_artifact")
        if not isinstance(artifact, Mapping):
            if representation.get("active") is True:
                issues.add("ACTIVE_EVALUATOR_ARTIFACT_UNAVAILABLE")
            continue
        path, digest = artifact.get("path"), artifact.get("sha256")
        if (
            not isinstance(path, str)
            or _SAFE_PATH.fullmatch(path) is None
            or not isinstance(digest, str)
            or not _SHA256.fullmatch(digest)
        ):
            issues.add("EVALUATOR_ARTIFACT_REFERENCE_INVALID")
        elif path not in artifact_bytes:
            issues.add("EVALUATOR_ARTIFACT_BYTES_MISSING")
        elif sha256_bytes(artifact_bytes[path]) != digest:
            issues.add("EVALUATOR_ARTIFACT_DIGEST_MISMATCH")
    return issues


def _string_values(value: Any) -> set[str]:
    return {item for item in value if isinstance(item, str)} if isinstance(value, list) else set()


__all__ = [
    "adapt_candidate_v1",
    "adapt_prediction_v1",
    "candidate_sha256",
    "derive_configuration_version",
    "materialize_candidate",
]
