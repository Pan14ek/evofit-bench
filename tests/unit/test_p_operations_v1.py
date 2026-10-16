"""Deterministic retain/replace/add/deactivate/adjust and cost-search tests."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from experiments.execution.tooling.hashing import sha256_bytes
from experiments.execution.tooling.p_applicability import ApplicabilityStatus
from experiments.execution.tooling.p_operations import (
    OperationKind,
    build_operation_plan,
    choose_candidate_plan,
    validate_materializable_template,
)
from experiments.execution.tooling.p_semantic import PairStatus
from tests.unit.p_spec03_support import (
    SYN_ARTIFACT,
    make_coverage,
    make_obligation,
    make_representation,
    make_valid_pair,
)


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


def test_invalid_representation_replacement_covers_all_its_live_mandatory_links() -> None:
    pair, rep, obligation, artifacts, _proof = make_valid_pair()
    invalid = replace(pair, status=PairStatus.INVALID)
    successor = template("REP_SYNTH_TRACE_V2", [obligation["id"]])
    digest = successor["representation"]["evaluator_artifact"]["sha256"]
    plan = build_operation_plan(
        representations=[rep],
        obligations=[obligation],
        applicability={obligation["id"]: "ACTIVE"},
        pair_assessments=[invalid],
        coverage=make_coverage([obligation], pairs=[invalid]),
        templates=[successor],
        artifact_bytes={**artifacts, "evaluators/REP_SYNTH_TRACE_V2.py": SYN_ARTIFACT},
        cost_model=cost_model(digest),
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
    plan = build_operation_plan(
        representations=[],
        obligations=[obligation],
        applicability={obligation["id"]: "ACTIVE"},
        pair_assessments=[],
        coverage=make_coverage([obligation]),
        templates=[addition],
        artifact_bytes={artifact_path: SYN_ARTIFACT},
        cost_model=cost_model(digest),
    )
    assert plan.ready
    assert plan.operations[0].target_type == "obligation"
    assert plan.operations[0].target_id == obligation["id"]
    assert plan.operations[0].operation is OperationKind.ADD
    assert plan.operations[0].artifact_sha256 == digest


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
        validate_materializable_template(wrong, artifact_bytes={"evaluators/bad.py": SYN_ARTIFACT})[
            2
        ]
        == "TEMPLATE_ARTIFACT_DIGEST_MISMATCH"
    )
    assert (
        validate_materializable_template(escaped, artifact_bytes={"../secret.py": SYN_ARTIFACT})[2]
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
        "authority_status": "TEST_ONLY",
        "target_id": rep["id"],
        "parameter": "sample_window",
        "old_value": 5,
        "new_value": 8,
        "bounds": {"minimum": 1, "maximum": 10},
        "rule_id": "SYN_SOFT_RULE",
        "rule_sha256": "a" * 64,
        "evidence_refs": ["SYN_RULE_AUTH"],
    }
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
        cost_model=model,
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
        cost_model=cost_model(digest, search_nodes=1),
    )
    missing_cost = build_operation_plan(
        representations=[],
        obligations=[q1],
        applicability={q1["id"]: "ACTIVE"},
        pair_assessments=[],
        coverage=make_coverage([q1]),
        templates=[first],
        artifact_bytes=artifacts,
        cost_model=cost_model(),
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
    assert choose_candidate_plan([cheaper, first], model) is first
    over_budget = {**model, "max_incremental_cost": 1}
    assert choose_candidate_plan([cheaper], over_budget) is None
