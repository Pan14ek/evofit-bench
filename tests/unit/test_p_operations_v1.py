"""Deterministic retain/replace/add/deactivate/adjust and cost-search tests."""

from __future__ import annotations

import copy
from typing import Any

from experiments.execution.tooling.hashing import canonical_json_bytes, sha256_bytes
from experiments.execution.tooling.p_applicability import ApplicabilityStatus
from experiments.execution.tooling.p_impact import ImpactStatus
from experiments.execution.tooling.p_operations import (
    OperationKind,
    OperationPlan,
    choose_candidate_plan,
    template_descriptor_sha256,
    validate_materializable_template,
)
from experiments.execution.tooling.p_operations import (
    build_operation_plan as _build_operation_plan,
)
from experiments.execution.tooling.p_semantic import PairStatus
from tests.unit.p_spec03_support import (
    SYN_ARTIFACT,
    impact_with_status,
    make_coverage,
    make_impact_assessment,
    make_obligation,
    make_representation,
    make_valid_pair,
    pair_with_status,
)


def build_operation_plan(**kwargs: Any) -> OperationPlan:
    """Supply explicit complete synthetic impact to the pure planner tests."""
    impact = kwargs.pop("impact", None)
    if impact is None:
        impact = make_impact_assessment(
            list(kwargs["representations"]),
            list(kwargs["obligations"]),
            dict(kwargs["applicability"]),
        )
    return _build_operation_plan(**kwargs, impact=impact)


def cost_model(*digests: str, max_cost: float = 20, search_nodes: int = 100) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "model_version": "SYN_COST_V1",
        "authority_status": "TEST_ONLY",
        "max_incremental_cost": max_cost,
        "max_search_nodes": search_nodes,
        "candidate_costs": {digest: index + 1 for index, digest in enumerate(sorted(set(digests)))},
    }


def template(identifier: str, obligation_ids: list[str]) -> dict[str, Any]:
    rep = make_representation(
        id=identifier,
        covers=obligation_ids,
        evaluator_artifact={
            "path": f"evaluators/{identifier}.py",
            "sha256": sha256_bytes(SYN_ARTIFACT),
        },
    )
    return {
        "authority_status": "TEST_ONLY",
        "representation": rep,
        "evidence_refs": ["SYN_TEMPLATE_AUTH"],
    }


def test_valid_unaffected_configuration_is_retained() -> None:
    pair, rep, obligation, artifacts, _proof = make_valid_pair()
    coverage = make_coverage([obligation], pairs=[pair])
    plan = build_operation_plan(
        representations=[rep],
        obligations=[obligation],
        applicability={obligation["id"]: "ACTIVE"},
        pair_assessments=[pair],
        coverage=coverage,
        artifact_bytes=artifacts,
        cost_model=cost_model(),
    )
    assert plan.ready
    assert [(op.operation, op.target_id) for op in plan.operations] == [
        (OperationKind.RETAIN, rep["id"])
    ]


def test_proven_impact_requires_reassessment_but_does_not_override_valid_semantics() -> None:
    pair, rep, obligation, artifacts, _proof = make_valid_pair()
    impact = impact_with_status(
        make_impact_assessment([rep], [obligation]),
        ImpactStatus.PROVEN_AFFECTED,
    )
    plan = build_operation_plan(
        representations=[rep],
        obligations=[obligation],
        applicability={obligation["id"]: "ACTIVE"},
        pair_assessments=[pair],
        coverage=make_coverage([obligation], pairs=[pair]),
        impact=impact,
        artifact_bytes=artifacts,
        cost_model=cost_model(),
    )
    assert plan.ready
    assert len(plan.operations) == 1
    assert plan.operations[0].operation is OperationKind.RETAIN
    assert plan.operations[0].reason_codes == ("EXACT_PAIR_VALIDITY_PROVEN",)


def test_unresolved_impact_holds_a_mandatory_representation_without_deactivating_it() -> None:
    _pair, rep, obligation, artifacts, _proof = make_valid_pair()
    impact = impact_with_status(
        make_impact_assessment([rep], [obligation]),
        ImpactStatus.UNRESOLVED,
    )
    plan = build_operation_plan(
        representations=[rep],
        obligations=[obligation],
        applicability={obligation["id"]: "ACTIVE"},
        pair_assessments=[],
        coverage=make_coverage([obligation]),
        impact=impact,
        artifact_bytes=artifacts,
        cost_model=cost_model(),
    )
    assert not plan.reject_reasons
    assert "MANDATORY_IMPACT_UNRESOLVED" in plan.hold_reasons
    assert all(operation.operation is not OperationKind.DEACTIVATE for operation in plan.operations)


def test_affected_optional_representation_requires_current_pair_reassessment() -> None:
    obligation = make_obligation(
        id="SYN_OBL_OPTIONAL",
        criterion="SYN_CRIT_OPTIONAL",
        mandatory=False,
    )
    representation = make_representation(criterion="SYN_CRIT_OPTIONAL", covers=[obligation["id"]])
    impact = impact_with_status(
        make_impact_assessment([representation], [obligation], {obligation["id"]: "ACTIVE"}),
        ImpactStatus.PROVEN_AFFECTED,
    )
    plan = build_operation_plan(
        representations=[representation],
        obligations=[obligation],
        applicability={obligation["id"]: "ACTIVE"},
        pair_assessments=[],
        coverage=make_coverage([obligation]),
        impact=impact,
        artifact_bytes={},
        cost_model=cost_model(),
    )
    assert not plan.ready
    assert "IMPACTED_RETAIN_REASSESSMENT_MISSING" in plan.hold_reasons
    assert all(operation.operation is not OperationKind.RETAIN for operation in plan.operations)


def test_invalid_representation_replacement_covers_all_its_live_mandatory_links() -> None:
    pair, rep, obligation, artifacts, _proof = make_valid_pair()
    invalid = pair_with_status(pair, PairStatus.INVALID)
    successor = template("REP_SYNTH_TRACE_V2", [obligation["id"]])
    digest = successor["representation"]["evaluator_artifact"]["sha256"]
    descriptor_digest = template_descriptor_sha256(successor)
    plan = build_operation_plan(
        representations=[rep],
        obligations=[obligation],
        applicability={obligation["id"]: "ACTIVE"},
        pair_assessments=[invalid],
        coverage=make_coverage([obligation], pairs=[invalid]),
        templates=[successor],
        artifact_bytes={**artifacts, "evaluators/REP_SYNTH_TRACE_V2.py": SYN_ARTIFACT},
        authorized_template_descriptor_digests=frozenset({descriptor_digest}),
        cost_model=cost_model(digest),
        cost_model_authorized=True,
    )
    assert plan.ready
    assert len(plan.operations) == 1
    assert plan.operations[0].operation is OperationKind.REPLACE
    assert plan.operations[0].payload is not None
    assert plan.operations[0].payload["id"] == "REP_SYNTH_TRACE_V2"


def test_active_uncovered_obligation_adds_only_a_real_hash_bound_test_template() -> None:
    obligation = make_obligation()
    addition = template("REP_SYNTH_ADDED", [obligation["id"]])
    artifact_path = addition["representation"]["evaluator_artifact"]["path"]
    digest = addition["representation"]["evaluator_artifact"]["sha256"]
    descriptor_digest = template_descriptor_sha256(addition)
    plan = build_operation_plan(
        representations=[],
        obligations=[obligation],
        applicability={obligation["id"]: "ACTIVE"},
        pair_assessments=[],
        coverage=make_coverage([obligation]),
        templates=[addition],
        artifact_bytes={artifact_path: SYN_ARTIFACT},
        authorized_template_descriptor_digests=frozenset({descriptor_digest}),
        cost_model=cost_model(digest),
        cost_model_authorized=True,
    )
    assert plan.ready
    assert plan.operations[0].target_type == "obligation"
    assert plan.operations[0].target_id == obligation["id"]
    assert plan.operations[0].operation is OperationKind.ADD
    assert plan.operations[0].artifact_sha256 == digest


def test_same_artifact_bytes_do_not_authorize_a_different_template_descriptor() -> None:
    q1 = make_obligation(id="SYN_OBL_AUTHORIZED", criterion="SYN_CRIT_TRACE")
    q2 = make_obligation(id="SYN_OBL_UNAUTHORIZED", criterion="SYN_CRIT_TRACE", mandatory=False)
    authorized = template("REP_SYN_AUTHORIZED", [q1["id"]])
    changed = template("REP_SYN_CHANGED", [q2["id"]])
    authorized["representation"]["criterion"] = q1["criterion"]
    changed["representation"]["criterion"] = q2["criterion"]
    assert (
        authorized["representation"]["evaluator_artifact"]["sha256"]
        == changed["representation"]["evaluator_artifact"]["sha256"]
    )
    approved_descriptor = template_descriptor_sha256(authorized)
    assert approved_descriptor != template_descriptor_sha256(changed)
    assert (
        validate_materializable_template(
            changed,
            artifact_bytes={"evaluators/REP_SYN_CHANGED.py": SYN_ARTIFACT},
            authorized_template_descriptor_digests=frozenset({approved_descriptor}),
        )[2]
        == "TEMPLATE_AUTHORITY_UNVERIFIED"
    )
    plan = build_operation_plan(
        representations=[],
        obligations=[q1, q2],
        applicability={q1["id"]: "ACTIVE", q2["id"]: "ACTIVE"},
        pair_assessments=[],
        coverage=make_coverage([q1, q2]),
        templates=[authorized, changed],
        artifact_bytes={
            "evaluators/REP_SYN_AUTHORIZED.py": SYN_ARTIFACT,
            "evaluators/REP_SYN_CHANGED.py": SYN_ARTIFACT,
        },
        authorized_template_descriptor_digests=frozenset({approved_descriptor}),
        cost_model=cost_model(sha256_bytes(SYN_ARTIFACT)),
        cost_model_authorized=True,
    )
    assert [(operation.operation, operation.target_id) for operation in plan.operations] == [
        (OperationKind.ADD, q1["id"])
    ]


def test_template_authorization_binds_each_semantics_bearing_descriptor_field() -> None:
    obligation = make_obligation(id="SYN_OBL_DESCRIPTOR", criterion="SYN_CRIT_DESCRIPTOR")
    approved = template("REP_SYN_DESCRIPTOR", [obligation["id"]])
    approved["representation"]["criterion"] = obligation["criterion"]
    artifact_path = approved["representation"]["evaluator_artifact"]["path"]
    artifact_digest = approved["representation"]["evaluator_artifact"]["sha256"]
    approved_digest = template_descriptor_sha256(approved)
    mutations = (
        ("id", "REP_SYN_DIFFERENT"),
        ("criterion", "SYN_CRIT_DIFFERENT"),
        ("covers", ["SYN_OBL_DIFFERENT"]),
        ("stage", "test"),
        ("evaluator", "synthetic_other_evaluator"),
        ("applicability_scope", {"scope": "service:other"}),
        ("evidence_contract", {"contract_id": "SYN_OTHER_CONTRACT"}),
        (
            "evaluator_artifact",
            {"path": "evaluators/REP_SYN_OTHER.py", "sha256": artifact_digest},
        ),
    )

    for field, value in mutations:
        changed = copy.deepcopy(approved)
        changed["representation"][field] = value
        assert template_descriptor_sha256(changed) != approved_digest
        artifact_bytes = {artifact_path: SYN_ARTIFACT, "evaluators/REP_SYN_OTHER.py": SYN_ARTIFACT}
        normalized, digest, issue = validate_materializable_template(
            changed,
            artifact_bytes=artifact_bytes,
            authorized_template_descriptor_digests=frozenset({approved_digest}),
        )
        assert normalized is None
        assert digest is None
        assert issue == "TEMPLATE_AUTHORITY_UNVERIFIED"


def test_missing_or_untrusted_template_is_hold_not_a_fictional_add() -> None:
    obligation = make_obligation()
    plan = build_operation_plan(
        representations=[],
        obligations=[obligation],
        applicability={obligation["id"]: "ACTIVE"},
        pair_assessments=[],
        coverage=make_coverage([obligation]),
        templates=[],
        artifact_bytes={},
        cost_model=cost_model(),
    )
    assert plan.operations == ()
    assert not plan.reject_reasons
    assert "ACTIVE_MANDATORY_CONTROL_UNCOVERED" in plan.hold_reasons


def test_template_wrong_digest_or_path_traversal_is_never_materialized() -> None:
    good = template("REP_SYNTH_TEMPLATE", ["SYN_OBL_TRACE"])
    wrong = {
        "authority_status": "TEST_ONLY",
        "representation": {
            **good["representation"],
            "evaluator_artifact": {"path": "evaluators/bad.py", "sha256": "0" * 64},
        },
    }
    escaped = {
        "authority_status": "TEST_ONLY",
        "representation": {
            **good["representation"],
            "evaluator_artifact": {"path": "../secret.py", "sha256": sha256_bytes(SYN_ARTIFACT)},
        },
    }
    assert (
        validate_materializable_template(
            wrong,
            artifact_bytes={"evaluators/bad.py": SYN_ARTIFACT},
            authorized_template_descriptor_digests=frozenset({template_descriptor_sha256(wrong)}),
        )[2]
        == "TEMPLATE_ARTIFACT_DIGEST_MISMATCH"
    )
    assert (
        validate_materializable_template(
            escaped,
            artifact_bytes={"../secret.py": SYN_ARTIFACT},
            authorized_template_descriptor_digests=frozenset({template_descriptor_sha256(escaped)}),
        )[2]
        == "TEMPLATE_ARTIFACT_PATH_INVALID"
    )
    untrusted = {"authority_status": "UNVERIFIED", "representation": good["representation"]}
    assert (
        validate_materializable_template(untrusted, artifact_bytes={})[2]
        == "TEMPLATE_AUTHORITY_UNVERIFIED"
    )


def test_shared_representation_stays_active_when_one_q_is_inactive_but_another_is_active() -> None:
    q1 = make_obligation(id="SYN_OBL_INACTIVE", criterion="SYN_CRIT_AUDIT")
    q2 = make_obligation(id="SYN_OBL_ACTIVE", criterion="SYN_CRIT_AUDIT")
    rep = make_representation(covers=[q1["id"], q2["id"]])
    pair, _rep, _q, artifacts, _proof = make_valid_pair(representation=rep, obligation=q2)
    coverage = make_coverage(
        [q1, q2],
        statuses={q1["id"]: ApplicabilityStatus.INACTIVE, q2["id"]: ApplicabilityStatus.ACTIVE},
        pairs=[pair],
    )
    plan = build_operation_plan(
        representations=[rep],
        obligations=[q1, q2],
        applicability={q1["id"]: "INACTIVE", q2["id"]: "ACTIVE"},
        pair_assessments=[pair],
        coverage=coverage,
        artifact_bytes=artifacts,
        cost_model=cost_model(),
    )
    assert all(op.operation is not OperationKind.DEACTIVATE for op in plan.operations)


def test_unknown_mandatory_applicability_never_authorizes_deactivation() -> None:
    obligation = make_obligation()
    rep = make_representation()
    coverage = make_coverage([obligation], statuses={obligation["id"]: ApplicabilityStatus.UNKNOWN})
    plan = build_operation_plan(
        representations=[rep],
        obligations=[obligation],
        applicability={obligation["id"]: "UNKNOWN"},
        pair_assessments=[],
        coverage=coverage,
        artifact_bytes={},
        cost_model=cost_model(),
    )
    assert all(op.operation is not OperationKind.DEACTIVATE for op in plan.operations)
    assert "UNKNOWN_MANDATORY_LINK_PREVENTS_TRANSITION" in plan.hold_reasons


def test_deactivation_requires_all_linked_controls_verified_inactive() -> None:
    obligation = make_obligation()
    rep = make_representation()
    plan = build_operation_plan(
        representations=[rep],
        obligations=[obligation],
        applicability={obligation["id"]: "INACTIVE"},
        pair_assessments=[],
        coverage=make_coverage(
            [obligation], statuses={obligation["id"]: ApplicabilityStatus.INACTIVE}
        ),
        artifact_bytes={},
        cost_model=cost_model(),
    )
    assert len(plan.operations) == 1
    assert plan.operations[0].operation is OperationKind.DEACTIVATE


def test_adjustment_requires_authorized_bounded_soft_rule() -> None:
    obligation = make_obligation()
    rep = make_representation()
    valid_rule = {
        "target_id": rep["id"],
        "parameter": "sample_window",
        "old_value": 5,
        "new_value": 8,
        "bounds": {"minimum": 1, "maximum": 10},
        "rule_id": "SYN_SOFT_RULE",
        "evidence_refs": ["SYN_RULE_AUTH"],
    }
    valid_rule["rule_sha256"] = sha256_bytes(canonical_json_bytes(valid_rule))
    accepted = build_operation_plan(
        representations=[rep],
        obligations=[obligation],
        applicability={obligation["id"]: "INACTIVE"},
        pair_assessments=[],
        coverage=make_coverage(
            [obligation], statuses={obligation["id"]: ApplicabilityStatus.INACTIVE}
        ),
        artifact_bytes={},
        cost_model=cost_model(),
        adjustment_rules=[valid_rule],
        adjustments_authorized=True,
    )
    assert any(op.operation is OperationKind.ADJUST for op in accepted.operations)
    forbidden = dict(valid_rule, parameter="hard_threshold", hard_constraint=True)
    rejected = build_operation_plan(
        representations=[rep],
        obligations=[obligation],
        applicability={obligation["id"]: "INACTIVE"},
        pair_assessments=[],
        coverage=make_coverage(
            [obligation], statuses={obligation["id"]: ApplicabilityStatus.INACTIVE}
        ),
        artifact_bytes={},
        cost_model=cost_model(),
        adjustment_rules=[forbidden],
        adjustments_authorized=True,
    )
    assert "UNAUTHORIZED_HARD_OR_INTENT_ADJUSTMENT" in rejected.reject_reasons


def test_bounded_set_cover_prefers_fewer_operations_then_cost_then_ids() -> None:
    q1 = make_obligation(id="SYN_OBL_A", criterion="SYN_CRIT_AUDIT")
    q2 = make_obligation(id="SYN_OBL_B", criterion="SYN_CRIT_AUDIT")
    costs = {
        sha256_bytes(SYN_ARTIFACT): 3,
    }
    model = cost_model(*costs, max_cost=10)
    both = template("REP_SYNTH_BOTH", [q1["id"], q2["id"]])
    template_one = template("REP_SYNTH_ONE", [q1["id"]])
    template_two = template("REP_SYNTH_TWO", [q2["id"]])
    plan = build_operation_plan(
        representations=[],
        obligations=[q1, q2],
        applicability={q1["id"]: "ACTIVE", q2["id"]: "ACTIVE"},
        pair_assessments=[],
        coverage=make_coverage([q1, q2]),
        templates=[template_two, both, template_one],
        artifact_bytes={
            f"evaluators/{name}.py": SYN_ARTIFACT
            for name in ("REP_SYNTH_BOTH", "REP_SYNTH_ONE", "REP_SYNTH_TWO")
        },
        authorized_template_descriptor_digests=frozenset(
            {template_descriptor_sha256(item) for item in (both, template_one, template_two)}
        ),
        cost_model=model,
        cost_model_authorized=True,
    )
    adds = [op for op in plan.operations if op.operation is OperationKind.ADD]
    assert len(adds) == 1
    assert adds[0].payload is not None
    assert adds[0].payload["id"] == "REP_SYNTH_BOTH"
    assert adds[0].target_id == "SYN_OBL_A"


def test_search_budget_exhaustion_and_missing_cost_return_hold() -> None:
    q1 = make_obligation(id="SYN_OBL_A", criterion="SYN_CRIT_AUDIT")
    q2 = make_obligation(id="SYN_OBL_B", criterion="SYN_CRIT_AUDIT")
    first, second = template("REP_SYNTH_ONE", [q1["id"]]), template("REP_SYNTH_TWO", [q2["id"]])
    digest = first["representation"]["evaluator_artifact"]["sha256"]
    artifacts = {
        "evaluators/REP_SYNTH_ONE.py": SYN_ARTIFACT,
        "evaluators/REP_SYNTH_TWO.py": SYN_ARTIFACT,
    }
    exhausted = build_operation_plan(
        representations=[],
        obligations=[q1, q2],
        applicability={q1["id"]: "ACTIVE", q2["id"]: "ACTIVE"},
        pair_assessments=[],
        coverage=make_coverage([q1, q2]),
        templates=[first, second],
        artifact_bytes=artifacts,
        authorized_template_descriptor_digests=frozenset(
            {template_descriptor_sha256(first), template_descriptor_sha256(second)}
        ),
        cost_model=cost_model(digest, search_nodes=1),
        cost_model_authorized=True,
    )
    missing_cost = build_operation_plan(
        representations=[],
        obligations=[q1],
        applicability={q1["id"]: "ACTIVE"},
        pair_assessments=[],
        coverage=make_coverage([q1]),
        templates=[first],
        artifact_bytes=artifacts,
        authorized_template_descriptor_digests=frozenset({template_descriptor_sha256(first)}),
        cost_model=cost_model(),
        cost_model_authorized=True,
    )
    assert "BUDGET_EXHAUSTED" in exhausted.hold_reasons
    assert "COST_MODEL_UNRESOLVED" in missing_cost.hold_reasons


def test_cost_model_rejects_duplicate_or_over_budget_candidate_and_ties_are_stable() -> None:
    digest = sha256_bytes(SYN_ARTIFACT)
    first = {"operations": [{"operation": "retain", "target_id": "REP_SYNTH_TRACE"}]}
    cheaper = {
        "operations": [
            {"operation": "add", "target_id": "REP_SYNTH_TRACE", "artifact_sha256": digest}
        ]
    }
    model = {**cost_model(digest), "candidate_costs": {digest: 2}}
    assert choose_candidate_plan([cheaper, first], model, cost_model_authorized=True) is first
    over_budget = {**model, "max_incremental_cost": 1}
    assert choose_candidate_plan([cheaper], over_budget, cost_model_authorized=True) is None
