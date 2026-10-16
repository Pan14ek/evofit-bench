"""Candidate materialization, V1 adapters, governance, history and rollback."""

from __future__ import annotations

import copy
from typing import Any

import pytest

from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.hashing import canonical_json_bytes, sha256_bytes
from experiments.execution.tooling.p_candidate import (
    adapt_candidate_v1,
    adapt_prediction_v1,
    candidate_sha256,
    derive_configuration_version,
    materialize_candidate,
)
from experiments.execution.tooling.p_governance import (
    GovernanceDecision,
    GovernanceResult,
    append_event,
    assess_rollback,
    authorize_conditional_publish,
    decide_governance,
    governance_context_sha256,
)
from experiments.execution.tooling.p_impact import ImpactStatus
from experiments.execution.tooling.p_operations import (
    OperationKind,
    OperationPlan,
    PlannedOperation,
)
from experiments.execution.tooling.p_semantic import CoverageAssessment, CoverageStatus
from tests.unit.p_spec03_support import (
    ARCH_AFTER,
    ARCH_BEFORE,
    SYN_ARTIFACT,
    make_coverage,
    make_obligation,
    make_representation,
    make_valid_pair,
)


def ready_plan(*operations: PlannedOperation) -> OperationPlan:
    body = {
        "operations": [item.to_dict() for item in operations],
        "hold_reasons": [],
        "reject_reasons": [],
    }
    return OperationPlan(tuple(operations), (), (), sha256_bytes(canonical_json_bytes(body)))


def parent_config() -> dict[str, Any]:
    return {"configuration_version": "SYN_CONFIG_1", "representations": [make_representation()]}


def make_candidate(
    plan: OperationPlan | None = None,
    *,
    parent_bytes: bytes | None = None,
    valid_obligation_ids: tuple[str, ...] | None = None,
    extra_artifact_bytes: dict[str, bytes] | None = None,
) -> dict[str, Any]:
    parent = parent_config()
    exact_parent_bytes = canonical_json_bytes(parent)
    rep = parent["representations"][0]
    operation_plan = plan or ready_plan(
        PlannedOperation(
            "representation", rep["id"], OperationKind.RETAIN, ("EXACT_PAIR_VALIDITY_PROVEN",)
        )
    )
    return materialize_candidate(
        parent_configuration=parent,
        parent_configuration_bytes=parent_bytes or exact_parent_bytes,
        parent_path="configs/synthetic-parent.json",
        parent_sha256=sha256_bytes(exact_parent_bytes),
        architecture_source_sha=ARCH_AFTER,
        policy_source_revision="SYN_POLICY_REV_1",
        policy_bundle_sha256="4" * 64,
        policy_ruleset_sha256="5" * 64,
        input_bundle_sha256="6" * 64,
        impact_assessment_sha256="7" * 64,
        method_version="P_GOVERNED_ADAPTATION_DEVELOPMENT_V1",
        configuration_version="SYN_CONFIG_2",
        operation_plan=operation_plan,
        artifact_bytes={
            rep["evaluator_artifact"]["path"]: SYN_ARTIFACT,
            **(extra_artifact_bytes or {}),
        },
        valid_obligation_ids=valid_obligation_ids,
    )


def accepted_decision(coverage: CoverageAssessment | None = None) -> GovernanceDecision:
    obligation = make_obligation()
    pair, _rep, _obligation, _artifacts, _proof = make_valid_pair()
    measured_coverage = coverage or make_coverage([obligation], pairs=[pair])
    return decide_governance(
        method_version="P_GOVERNED_ADAPTATION_DEVELOPMENT_V1",
        architecture_before_sha=ARCH_BEFORE,
        architecture_after_sha=ARCH_AFTER,
        policy_source_revision="SYN_POLICY_REV_1",
        policy_ruleset_sha256="5" * 64,
        input_bundle_sha256="6" * 64,
        parent_configuration_sha256="8" * 64,
        candidate_configuration_sha256="9" * 64,
        impact_assessment_sha256="a" * 64,
        coverage=measured_coverage,
        operation_plan=ready_plan(
            PlannedOperation(
                "representation",
                "REP_SYNTH_TRACE",
                OperationKind.RETAIN,
                ("EXACT_PAIR_VALIDITY_PROVEN",),
            )
        ),
        invariant_verdicts={f"INV-{index:02d}": "PASS" for index in range(1, 13)},
        cost_verdict="PASS",
        input_status="VALID",
        candidate_validation_status="valid",
    )


def test_candidate_materialization_binds_parent_artifacts_and_all_source_versions() -> None:
    candidate = make_candidate()
    assert candidate["candidate_validation"]["status"] == "valid"
    assert candidate["parent_configuration"]["sha256"] == sha256_bytes(
        canonical_json_bytes(parent_config())
    )
    assert candidate["policy_bundle_sha256"] == "4" * 64
    assert candidate["impact_assessment_sha256"] == "7" * 64
    assert candidate["configuration_version"] != parent_config()["configuration_version"]
    assert candidate_sha256(candidate) == candidate_sha256(copy.deepcopy(candidate))


def test_child_configuration_version_is_deterministic_and_parent_bound() -> None:
    values = {
        "parent_configuration_sha256": "1" * 64,
        "operation_plan_sha256": "2" * 64,
        "architecture_source_sha": ARCH_AFTER,
        "policy_source_revision": "SYN_POLICY_REV_1",
        "policy_bundle_sha256": "3" * 64,
    }
    first = derive_configuration_version(**values)
    assert first == derive_configuration_version(**values)
    assert first != derive_configuration_version(
        **{**values, "parent_configuration_sha256": "4" * 64}
    )


def test_candidate_rejects_duplicate_operation_targets_and_tampered_plan_digest() -> None:
    operation = PlannedOperation(
        "representation", "REP_SYNTH_TRACE", OperationKind.RETAIN, ("EXACT_PAIR_VALIDITY_PROVEN",)
    )
    duplicate = ready_plan(operation, operation)
    with pytest.raises(ContractValidationError, match="P03_OPERATION_TARGET_DUPLICATE"):
        make_candidate(duplicate)

    good = ready_plan(operation)
    tampered = OperationPlan(good.operations, (), (), "a" * 64)
    with pytest.raises(ContractValidationError, match="P03_OPERATION_PLAN_DIGEST_MISMATCH"):
        make_candidate(tampered)


def test_candidate_rejects_stale_parent_collision_and_orphaned_obligation_link() -> None:
    with pytest.raises(ContractValidationError, match="P03_PARENT_CONFIGURATION_DIGEST_MISMATCH"):
        make_candidate(parent_bytes=b"tampered parent bytes")

    parent_representation = parent_config()["representations"][0]
    collision = ready_plan(
        PlannedOperation(
            "representation",
            parent_representation["id"],
            OperationKind.REPLACE,
            ("EXACT_PAIR_INADEQUACY_PROVEN",),
            payload=parent_representation,
            artifact_sha256=parent_representation["evaluator_artifact"]["sha256"],
        )
    )
    with pytest.raises(ContractValidationError, match="P03_REPLACEMENT_ID_COLLISION"):
        make_candidate(collision)

    orphan = make_representation(
        id="REP_SYNTH_ORPHAN",
        covers=["SYN_OBL_GHOST"],
        evaluator_artifact={
            "path": "evaluators/REP_SYNTH_ORPHAN.py",
            "sha256": sha256_bytes(SYN_ARTIFACT),
        },
    )
    addition = ready_plan(
        PlannedOperation(
            "obligation",
            "SYN_OBL_GHOST",
            OperationKind.ADD,
            ("ACTIVE_MANDATORY_CONTROL_UNCOVERED",),
            payload=orphan,
            artifact_sha256=orphan["evaluator_artifact"]["sha256"],
        )
    )
    candidate = make_candidate(
        addition,
        valid_obligation_ids=("SYN_OBL_TRACE",),
        extra_artifact_bytes={"evaluators/REP_SYNTH_ORPHAN.py": SYN_ARTIFACT},
    )
    assert candidate["candidate_validation"]["status"] == "invalid"
    assert "ORPHANED_OBLIGATION_LINK" in candidate["candidate_validation"]["reason_codes"]


def test_v1_candidate_adapter_validates_without_changing_legacy_schema() -> None:
    legacy = adapt_candidate_v1(make_candidate())
    assert legacy["method_id"] == "P"
    assert "method_version" not in legacy
    assert "soft_parameter_overrides" not in legacy
    assert legacy["candidate_validation"]["status"] == "valid"


def test_v1_prediction_adapter_projects_exact_nonretain_targets_and_blocks_hold() -> None:
    obligation = make_obligation()
    representation = make_representation(id="REP_SYNTH_NEW")
    add = PlannedOperation(
        "obligation",
        obligation["id"],
        OperationKind.ADD,
        ("ACTIVE_MANDATORY_CONTROL_UNCOVERED",),
        payload=representation,
        artifact_sha256=representation["evaluator_artifact"]["sha256"],
    )
    plan = ready_plan(add)
    prediction = adapt_prediction_v1(
        architecture_source_sha=ARCH_AFTER,
        method_version="P_GOVERNED_ADAPTATION_DEVELOPMENT_V1",
        input_bundle_sha256="6" * 64,
        plan=plan,
        impact_records=[
            {"representation_id": "REP_SYNTH_TRACE", "status": ImpactStatus.PROVEN_AFFECTED.value}
        ],
    )
    assert prediction["predicted_affected"] == [
        {
            "target_type": "obligation",
            "target_id": obligation["id"],
            "predicted_operation": "add",
        }
    ]
    blocked = OperationPlan(plan.operations, ("COST_MODEL_UNRESOLVED",), (), "b" * 64)
    with pytest.raises(ContractValidationError, match="PREDICTION_V1_UNAVAILABLE_FOR_BLOCKED_PLAN"):
        adapt_prediction_v1(
            architecture_source_sha=ARCH_AFTER,
            method_version="P_DEV",
            input_bundle_sha256="6" * 64,
            plan=blocked,
            impact_records=[],
        )


def test_v1_adapter_rejects_identifiers_the_frozen_contract_cannot_represent() -> None:
    operation = PlannedOperation(
        "obligation",
        "SYN:OBL",
        OperationKind.ADD,
        ("ACTIVE_MANDATORY_CONTROL_UNCOVERED",),
    )
    with pytest.raises(ContractValidationError, match="PREDICTION_V1_ID_UNREPRESENTABLE"):
        adapt_prediction_v1(
            architecture_source_sha=ARCH_AFTER,
            method_version="P_DEV",
            input_bundle_sha256="6" * 64,
            plan=ready_plan(operation),
            impact_records=[],
        )


def test_governance_accepts_only_when_every_required_gate_is_positive() -> None:
    decision = accepted_decision()
    assert decision.result is GovernanceResult.ACCEPT
    assert decision.to_dict()["decision_sha256"]


def test_input_rejection_has_precedence_over_candidate_fitness_decisions() -> None:
    coverage = make_coverage()
    decision = decide_governance(
        method_version="P_DEV",
        architecture_before_sha=ARCH_BEFORE,
        architecture_after_sha=ARCH_AFTER,
        policy_source_revision="SYN_POLICY_REV_1",
        policy_ruleset_sha256="5" * 64,
        input_bundle_sha256="6" * 64,
        parent_configuration_sha256="8" * 64,
        candidate_configuration_sha256=None,
        impact_assessment_sha256="a" * 64,
        coverage=coverage,
        operation_plan=ready_plan(),
        invariant_verdicts={"INV-01": "FAIL"},
        cost_verdict="FAIL",
        input_status="INVALID",
        candidate_validation_status="invalid",
    )
    assert decision.result is GovernanceResult.INPUT_REJECTED


def test_unresolved_coverage_is_hold_and_proven_incomplete_candidate_is_reject() -> None:
    obligation = make_obligation()
    from experiments.execution.tooling.p_applicability import ApplicabilityStatus

    unknown_coverage = make_coverage(
        [obligation], statuses={obligation["id"]: ApplicabilityStatus.UNKNOWN}
    )
    held = accepted_decision(unknown_coverage)
    assert held.result is GovernanceResult.HOLD
    pair, _rep, _q, _artifacts, _proof = make_valid_pair()
    complete = make_coverage([obligation], pairs=[pair])
    incomplete = make_coverage([obligation])
    rejected = decide_governance(
        method_version="P_DEV",
        architecture_before_sha=ARCH_BEFORE,
        architecture_after_sha=ARCH_AFTER,
        policy_source_revision="SYN_POLICY_REV_1",
        policy_ruleset_sha256="5" * 64,
        input_bundle_sha256="6" * 64,
        parent_configuration_sha256="8" * 64,
        candidate_configuration_sha256="9" * 64,
        impact_assessment_sha256="a" * 64,
        coverage=incomplete,
        operation_plan=ready_plan(),
        invariant_verdicts={f"INV-{i:02d}": "PASS" for i in range(1, 13)},
        cost_verdict="PASS",
        input_status="VALID",
        candidate_validation_status="valid",
    )
    assert complete.status is CoverageStatus.COMPLETE
    assert rejected.result is GovernanceResult.REJECT


def test_proven_cost_limit_violation_rejects_only_the_candidate() -> None:
    decision = accepted_decision()
    payload = decision.to_dict()
    rejected = decide_governance(
        method_version=payload["method_version"],
        architecture_before_sha=payload["architecture_before_sha"],
        architecture_after_sha=payload["architecture_after_sha"],
        policy_source_revision=payload["policy_source_revision"],
        policy_ruleset_sha256=payload["policy_ruleset_sha256"],
        input_bundle_sha256=payload["input_bundle_sha256"],
        parent_configuration_sha256=payload["parent_configuration_sha256"],
        candidate_configuration_sha256=payload["candidate_configuration_sha256"],
        impact_assessment_sha256=payload["impact_assessment_sha256"],
        coverage=make_coverage([make_obligation()], pairs=[make_valid_pair()[0]]),
        operation_plan=ready_plan(),
        invariant_verdicts={f"INV-{index:02d}": "PASS" for index in range(1, 13)},
        cost_verdict="FAIL",
        input_status="VALID",
        candidate_validation_status="valid",
    )
    assert decision.result is GovernanceResult.ACCEPT
    assert rejected.result is GovernanceResult.REJECT


def test_append_only_event_chain_is_deterministic_and_identical_replay_is_idempotent() -> None:
    initial = {
        "schema_version": 1,
        "head_sha256": sha256_bytes(canonical_json_bytes([])),
        "events": [],
    }
    kwargs: dict[str, Any] = {
        "event_id": "SYN_EVENT_1",
        "event_type": "PROPOSED",
        "parent_configuration_sha256": "8" * 64,
        "configuration_sha256": "9" * 64,
        "context_sha256": "a" * 64,
        "recorded_at_utc": "2026-01-01T00:00:00Z",
        "reason_codes": ["SYNTHETIC_TEST"],
        "evidence_refs": ["SYN_EVENT_EVIDENCE"],
    }
    first = append_event(initial, **kwargs)
    replay = append_event(first, **{**kwargs, "recorded_at_utc": "2026-01-02T00:00:00Z"})
    assert replay == first
    assert len(first["events"]) == 1
    with pytest.raises(ContractValidationError, match="P03_EVENT_ID_REPLAY_CONFLICT"):
        append_event(first, **{**kwargs, "event_type": "HELD"})


def test_event_chain_tampering_is_detected_before_append() -> None:
    trace = {
        "schema_version": 1,
        "head_sha256": sha256_bytes(canonical_json_bytes([])),
        "events": [],
    }
    event = append_event(
        trace,
        event_id="SYN_EVENT_1",
        event_type="PROPOSED",
        parent_configuration_sha256=None,
        configuration_sha256="9" * 64,
        context_sha256="a" * 64,
        recorded_at_utc="2026-01-01T00:00:00Z",
    )
    changed = copy.deepcopy(event)
    changed["events"][0]["configuration_sha256"] = "b" * 64
    with pytest.raises(ContractValidationError, match="P03_ADAPTATION_TRACE_CHAIN_INVALID"):
        append_event(
            changed,
            event_id="SYN_EVENT_2",
            event_type="HELD",
            parent_configuration_sha256=None,
            configuration_sha256=None,
            context_sha256="a" * 64,
            recorded_at_utc="2026-01-01T00:00:00Z",
        )


def test_publish_requires_accept_and_current_context_parent_compare_and_swap() -> None:
    decision = accepted_decision()
    context = governance_context_sha256(decision.to_dict())
    assert authorize_conditional_publish(
        decision=decision,
        validated_context_sha256=context,
        current_context_sha256=context,
        expected_parent_sha256="8" * 64,
        current_parent_sha256="8" * 64,
    )
    assert not authorize_conditional_publish(
        decision=decision,
        validated_context_sha256=context,
        current_context_sha256="b" * 64,
        expected_parent_sha256="8" * 64,
        current_parent_sha256="8" * 64,
    )


def test_rollback_requires_positive_fresh_current_context_validation() -> None:
    blocked = assess_rollback(
        prior_configuration_sha256="8" * 64,
        current_context_sha256="a" * 64,
        revalidation=None,
    )
    valid = {
        "context_sha256": "a" * 64,
        "coverage_status": "COMPLETE",
        "invariant_verdicts": {f"INV-{index:02d}": "PASS" for index in range(1, 13)},
        "candidate_validation_status": "valid",
        "cost_verdict": "PASS",
    }
    allowed = assess_rollback(
        prior_configuration_sha256="8" * 64,
        current_context_sha256="a" * 64,
        revalidation=valid,
    )
    assert blocked["status"] == "ROLLBACK_BLOCKED"
    assert allowed["status"] == "ROLLBACK_ALLOWED"
