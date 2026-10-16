"""Fail-closed governance decisions, event history and conditional rollback."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from experiments.execution.tooling.contracts import validate_payload
from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.hashing import canonical_json_bytes, sha256_bytes
from experiments.execution.tooling.p_operations import OperationPlan
from experiments.execution.tooling.p_semantic import CoverageAssessment, CoverageStatus


class GovernanceResult(StrEnum):
    """Candidate governance outcomes; INPUT_REJECTED is not fitness rejection."""

    INPUT_REJECTED = "INPUT_REJECTED"
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    HOLD = "HOLD"


@dataclass(frozen=True)
class GovernanceDecision:
    """Version-bound, canonical decision with blockers and invariant verdicts."""

    payload: Mapping[str, Any]

    @property
    def result(self) -> GovernanceResult:
        return GovernanceResult(str(self.payload["result"]))

    def to_dict(self) -> dict[str, Any]:
        return dict(self.payload)


def decide_governance(
    *,
    method_version: str,
    architecture_before_sha: str,
    architecture_after_sha: str,
    policy_source_revision: str,
    policy_ruleset_sha256: str,
    input_bundle_sha256: str,
    parent_configuration_sha256: str,
    candidate_configuration_sha256: str | None,
    impact_assessment_sha256: str,
    coverage: CoverageAssessment,
    operation_plan: OperationPlan,
    invariant_verdicts: Mapping[str, str],
    cost_verdict: str,
    input_status: str,
    candidate_validation_status: str | None,
    pairs: Sequence[Mapping[str, Any]] = (),
    evidence_refs: Sequence[str] = (),
    additional_reasons: Sequence[str] = (),
) -> GovernanceDecision:
    """Apply SPEC03 result precedence without interpreting UNKNOWN as success."""
    _validate_identity(architecture_before_sha, 40, "architecture_before_sha")
    _validate_identity(architecture_after_sha, 40, "architecture_after_sha")
    for name, value in (
        ("policy_ruleset_sha256", policy_ruleset_sha256),
        ("input_bundle_sha256", input_bundle_sha256),
        ("parent_configuration_sha256", parent_configuration_sha256),
        ("impact_assessment_sha256", impact_assessment_sha256),
    ):
        _validate_identity(value, 64, name)
    if candidate_configuration_sha256 is not None:
        _validate_identity(candidate_configuration_sha256, 64, "candidate_configuration_sha256")

    reasons = (
        set(additional_reasons)
        | set(operation_plan.hold_reasons)
        | set(operation_plan.reject_reasons)
    )
    blockers = {
        row.obligation_id
        for row in coverage.obligations
        if row.mandatory is not False and row.status in {"UNKNOWN", "NOT_DEMONSTRATED"}
    }
    blocking_pairs = sorted(
        {
            (str(pair.get("representation_id")), str(pair.get("obligation_id")))
            for pair in pairs
            if pair.get("status") in {"UNKNOWN", "INVALID"}
            and pair.get("obligation_id") in blockers
        }
    )
    if input_status not in {"VALID", "UNDETERMINED", "INVALID"}:
        raise ContractValidationError("P03_INPUT_STATUS_INVALID")
    if input_status == "INVALID":
        result = GovernanceResult.INPUT_REJECTED
        reasons.add("INPUT_VALIDATION_REJECTED")
    elif any(value == "FAIL" for value in invariant_verdicts.values()):
        result = GovernanceResult.REJECT
        reasons.add("INVARIANT_VIOLATION_PROVEN")
    elif (
        operation_plan.reject_reasons
        or candidate_validation_status == "invalid"
        or cost_verdict == "FAIL"
    ):
        result = GovernanceResult.REJECT
        if candidate_validation_status == "invalid":
            reasons.add("CANDIDATE_VALIDATION_FAILED")
        if cost_verdict == "FAIL":
            reasons.add("AUTHORIZED_COST_LIMIT_EXCEEDED")
    elif coverage.status is CoverageStatus.INCOMPLETE and candidate_validation_status == "valid":
        result = GovernanceResult.REJECT
        reasons.add("MANDATORY_COVERAGE_INCOMPLETE")
    else:
        required_invariants = {f"INV-{index:02d}" for index in range(1, 13)}
        if input_status == "UNDETERMINED":
            reasons.add("INPUT_AUTHORITY_OR_COMPLETENESS_UNRESOLVED")
        if candidate_validation_status != "valid" or candidate_configuration_sha256 is None:
            reasons.add("CANDIDATE_NOT_POSITIVELY_VALIDATED")
        if coverage.status is not CoverageStatus.COMPLETE:
            reasons.update(coverage.reason_codes or ("MANDATORY_COVERAGE_NOT_PROVEN",))
        if cost_verdict != "PASS":
            reasons.add("COST_VERDICT_UNRESOLVED")
        missing_invariants = required_invariants - set(invariant_verdicts)
        if missing_invariants:
            reasons.add("INVARIANT_VERDICTS_MISSING")
        if any(value != "PASS" for value in invariant_verdicts.values()):
            reasons.add("INVARIANT_VERDICTS_NOT_ALL_POSITIVE")
        if operation_plan.hold_reasons:
            reasons.update(operation_plan.hold_reasons)
        if reasons:
            result = GovernanceResult.HOLD
        else:
            result = GovernanceResult.ACCEPT

    content: dict[str, Any] = {
        "schema_version": 1,
        "method_version": method_version,
        "algorithm_version": "P_GOVERNED_ADAPTATION_V1",
        "result": result.value,
        "architecture_before_sha": architecture_before_sha,
        "architecture_after_sha": architecture_after_sha,
        "policy_source_revision": policy_source_revision,
        "policy_ruleset_sha256": policy_ruleset_sha256,
        "input_bundle_sha256": input_bundle_sha256,
        "parent_configuration_sha256": parent_configuration_sha256,
        "candidate_configuration_sha256": candidate_configuration_sha256,
        "impact_assessment_sha256": impact_assessment_sha256,
        "coverage_assessment_sha256": coverage.assessment_sha256,
        "operations": [operation.to_dict() for operation in operation_plan.operations],
        "blocking_obligations": sorted(blockers),
        "blocking_pairs": [
            {"representation_id": representation_id, "obligation_id": obligation_id}
            for representation_id, obligation_id in blocking_pairs
        ],
        "invariant_verdicts": dict(sorted(invariant_verdicts.items())),
        "cost_verdict": cost_verdict,
        "evidence_refs": sorted(set(evidence_refs)),
        "reason_codes": sorted(reasons),
    }
    content["decision_sha256"] = sha256_bytes(canonical_json_bytes(content))
    validate_payload("p_governance_decision_v1.schema.json", content)
    return GovernanceDecision(content)


def append_event(
    trace: Mapping[str, Any],
    *,
    event_id: str,
    event_type: str,
    parent_configuration_sha256: str | None,
    configuration_sha256: str | None,
    context_sha256: str,
    recorded_at_utc: str,
    reason_codes: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
) -> dict[str, Any]:
    """Append an immutable hash-chained event; identical replay is idempotent."""
    validate_payload("p_adaptation_trace_v1.schema.json", dict(trace))
    events_value = trace["events"]
    events = [dict(item) for item in events_value]
    previous_sha = _validate_trace_chain(events)
    expected_head = previous_sha or sha256_bytes(canonical_json_bytes([]))
    if trace.get("head_sha256") != expected_head:
        raise ContractValidationError("P03_ADAPTATION_TRACE_HEAD_MISMATCH")
    prior = next((item for item in events if item.get("event_id") == event_id), None)
    if prior is not None:
        replay = {
            "event_id": event_id,
            "event_type": event_type,
            "parent_configuration_sha256": parent_configuration_sha256,
            "configuration_sha256": configuration_sha256,
            "context_sha256": context_sha256,
            "previous_event_sha256": prior.get("previous_event_sha256"),
            "reason_codes": sorted(set(reason_codes)),
            "evidence_refs": sorted(set(evidence_refs)),
        }
        if prior.get("semantic_sha256") == sha256_bytes(canonical_json_bytes(replay)) and all(
            prior.get(key) == value for key, value in replay.items()
        ):
            return dict(trace)
        raise ContractValidationError("P03_EVENT_ID_REPLAY_CONFLICT")
    semantic = {
        "event_id": event_id,
        "event_type": event_type,
        "parent_configuration_sha256": parent_configuration_sha256,
        "configuration_sha256": configuration_sha256,
        "context_sha256": context_sha256,
        "previous_event_sha256": previous_sha,
        "reason_codes": sorted(set(reason_codes)),
        "evidence_refs": sorted(set(evidence_refs)),
    }
    semantic_digest = sha256_bytes(canonical_json_bytes(semantic))
    event = {
        **semantic,
        "semantic_sha256": semantic_digest,
        "recorded_at_utc": recorded_at_utc,
    }
    new_events = [*events, event]
    payload = {
        "schema_version": 1,
        "head_sha256": sha256_bytes(canonical_json_bytes(event)),
        "events": new_events,
    }
    validate_payload("p_adaptation_trace_v1.schema.json", payload)
    return payload


def authorize_conditional_publish(
    *,
    decision: GovernanceDecision,
    validated_context_sha256: str,
    current_context_sha256: str,
    expected_parent_sha256: str,
    current_parent_sha256: str,
) -> bool:
    """Return true only for ACCEPT and a current context/parent CAS match."""
    if decision.result is not GovernanceResult.ACCEPT:
        return False
    expected_context = governance_context_sha256(decision.payload)
    return (
        expected_context == validated_context_sha256
        and validated_context_sha256 == current_context_sha256
        and expected_parent_sha256 == current_parent_sha256
        and expected_parent_sha256 == decision.payload.get("parent_configuration_sha256")
    )


def governance_context_sha256(decision: Mapping[str, Any]) -> str:
    """Hash the exact source/policy/ruleset/parent bindings that were validated."""
    fields = (
        "architecture_before_sha",
        "architecture_after_sha",
        "policy_source_revision",
        "policy_ruleset_sha256",
        "input_bundle_sha256",
        "parent_configuration_sha256",
    )
    if any(not isinstance(decision.get(field), str) for field in fields):
        raise ContractValidationError("P03_GOVERNANCE_CONTEXT_INCOMPLETE")
    return sha256_bytes(canonical_json_bytes({field: decision[field] for field in fields}))


def assess_rollback(
    *,
    prior_configuration_sha256: str,
    current_context_sha256: str,
    revalidation: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Permit rollback only when the old config passes fresh current-context checks."""
    _validate_identity(prior_configuration_sha256, 64, "prior_configuration_sha256")
    _validate_identity(current_context_sha256, 64, "current_context_sha256")
    required_invariants = {f"INV-{index:02d}" for index in range(1, 13)}
    verdicts = revalidation.get("invariant_verdicts") if isinstance(revalidation, Mapping) else None
    allowed = bool(
        revalidation is not None
        and revalidation.get("context_sha256") == current_context_sha256
        and revalidation.get("coverage_status") == "COMPLETE"
        and isinstance(verdicts, Mapping)
        and required_invariants.issubset(verdicts)
        and all(verdicts.get(key) == "PASS" for key in required_invariants)
        and revalidation.get("candidate_validation_status") == "valid"
        and revalidation.get("cost_verdict") == "PASS"
    )
    return {
        "status": "ROLLBACK_ALLOWED" if allowed else "ROLLBACK_BLOCKED",
        "configuration_sha256": prior_configuration_sha256 if allowed else None,
        "context_sha256": current_context_sha256,
        "reason_codes": [] if allowed else ["CURRENT_CONTEXT_REVALIDATION_NOT_POSITIVE"],
    }


def _validate_identity(value: Any, length: int, name: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != length
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise ContractValidationError("P03_IDENTITY_INVALID: " + name)


def _validate_trace_chain(events: Sequence[Mapping[str, Any]]) -> str | None:
    previous: str | None = None
    for event in events:
        semantic = {
            key: event.get(key)
            for key in (
                "event_id",
                "event_type",
                "parent_configuration_sha256",
                "configuration_sha256",
                "context_sha256",
                "previous_event_sha256",
                "reason_codes",
                "evidence_refs",
            )
        }
        expected_semantic = sha256_bytes(canonical_json_bytes(semantic))
        if (
            event.get("previous_event_sha256") != previous
            or event.get("semantic_sha256") != expected_semantic
        ):
            raise ContractValidationError("P03_ADAPTATION_TRACE_CHAIN_INVALID")
        previous = sha256_bytes(canonical_json_bytes(dict(event)))
    return previous


__all__ = [
    "GovernanceDecision",
    "GovernanceResult",
    "append_event",
    "assess_rollback",
    "authorize_conditional_publish",
    "decide_governance",
    "governance_context_sha256",
]
