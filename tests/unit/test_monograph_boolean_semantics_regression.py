"""Regression evidence for the monograph's Boolean-confirmation abstraction.

No implementation logic is changed by these tests. A status is encoded by two
Boolean statements: positively confirmed and negatively confirmed. (False,
False) means unresolved; it is NOT a third value of a mathematical predicate.

Scope: applicability expression composition, governance decision precedence,
and the frozen 8-scenario / 24-repetition DEVELOPMENT archive. These tests do
not prove whole-method equivalence or independent scientific validity.
"""

from __future__ import annotations

import json
from itertools import product
from pathlib import Path
from typing import Any

import pytest

from experiments.execution.tooling.hashing import canonical_json_bytes, sha256_bytes
from experiments.execution.tooling.p_applicability import (
    ApplicabilityStatus,
    TruthValue,
    evaluate_condition,
    load_and_validate_ruleset,
    tri_and,
    tri_not,
    tri_or,
)
from experiments.execution.tooling.p_governance import (
    _decide_governance_authorized,
    _issue_governance_pipeline_authorization,
    decide_governance,
)
from experiments.execution.tooling.p_input_validation import load_fact_vocabulary
from experiments.execution.tooling.p_operations import OperationPlan
from tests.unit.p_applicability_support import (
    add_fact,
    close_facts_for,
    evidence_ledger,
    snapshot_fixture,
)
from tests.unit.p_spec03_support import (
    ARCH_AFTER,
    ARCH_BEFORE,
    make_coverage,
    make_obligation,
    make_valid_pair,
)

# These are observations in the archived experiment, not corrected oracle labels.
ARCHIVED_OUTCOMES: dict[str, tuple[str, str]] = {
    "A1": ("retain", "ACCEPT"),
    "A2": ("retain", "ACCEPT"),
    "B1": ("add", "ACCEPT"),
    "B2": ("add", "ACCEPT"),
    "C1": ("replace", "ACCEPT"),
    "C2": ("replace", "ACCEPT"),
    "D1": ("hold", "HOLD"),
    "D2": ("hold", "REJECT"),
}
ARCHIVE = Path("experiments/pilots/mono_e1_dev_p_decisions_v1/run_v1/raw")
REQUIRED = {f"INV-{index:02d}" for index in range(1, 13)}


def _flags(value: TruthValue) -> tuple[bool, bool]:
    """(confirmed true, confirmed false); unresolved = (False, False)."""
    return value is TruthValue.TRUE, value is TruthValue.FALSE


def _read_flags(flags: tuple[bool, bool]) -> TruthValue:
    positive, negative = flags
    assert not (positive and negative), "Contradictory confirmations"
    if positive:
        return TruthValue.TRUE
    if negative:
        return TruthValue.FALSE
    return TruthValue.UNKNOWN


def _boolean_all(values: tuple[tuple[bool, bool], ...]) -> tuple[bool, bool]:
    assert values, "The existing tri_and rejects empty input"
    return all(positive for positive, _ in values), any(negative for _, negative in values)


def _boolean_any(values: tuple[tuple[bool, bool], ...]) -> tuple[bool, bool]:
    assert values, "The existing tri_or rejects empty input"
    return any(positive for positive, _ in values), all(negative for _, negative in values)


def _boolean_not(value: tuple[bool, bool]) -> tuple[bool, bool]:
    positive, negative = value
    return negative, positive


def test_boolean_confirmations_match_existing_and_or_not_truth_tables() -> None:
    values = tuple(TruthValue)
    for left, right in product(values, repeat=2):
        pair = (_flags(left), _flags(right))
        assert _read_flags(_boolean_all(pair)) is tri_and((left, right))
        assert _read_flags(_boolean_any(pair)) is tri_or((left, right))
        assert _read_flags(_boolean_not(_flags(left))) is tri_not(left)
        # FALSE combined with missing evidence is a proven negative,
        # not an unresolved result.
        assert not (_flags(left)[0] and _flags(left)[1])


def test_six_condition_conjunction_exhaustive_729_cases() -> None:
    """Covers every combination in the monograph's six-condition rule (10)."""
    for values in product(tuple(TruthValue), repeat=6):
        confirmed = tuple(_flags(value) for value in values)
        assert _read_flags(_boolean_all(confirmed)) is tri_and(values)
        # This is a property of the Boolean encoding, not of governance.
        all_positive, any_negative = _boolean_all(confirmed)
        assert all_positive == all(value is TruthValue.TRUE for value in values)
        assert any_negative == any(value is TruthValue.FALSE for value in values)


def test_boolean_statuses_keep_missing_absent_and_conflicting_facts_distinct() -> None:
    compiled = load_and_validate_ruleset(
        Path("experiments/execution/contracts/applicability_ruleset_v1.json"),
        load_fact_vocabulary(),
        Path("fitness/catalog/architectural-obligations.yaml"),
    )
    snapshot = snapshot_fixture()
    missing = evaluate_condition(
        "COND_HAS_CAPABILITY_MODULE", "after", snapshot, compiled, evidence_ledger(snapshot)
    )
    assert _flags(missing.truth) == (False, False)
    assert "NEGATIVE_EVIDENCE_INSUFFICIENT" in missing.reason_codes

    close_facts_for(snapshot, "component.capability_module")
    absent = evaluate_condition(
        "COND_HAS_CAPABILITY_MODULE", "after", snapshot, compiled, evidence_ledger(snapshot)
    )
    assert _flags(absent.truth) == (False, True)
    assert absent.truth is TruthValue.FALSE

    conflicting = snapshot_fixture()
    add_fact(
        conflicting,
        fact_id="F_DEPLOYMENT_CONFLICT",
        predicate="deployment.unit_count_declared",
        value=2,
    )
    unresolved = evaluate_condition(
        "COND_DECLARED_MULTI_UNIT",
        "after",
        conflicting,
        compiled,
        evidence_ledger(conflicting),
    )
    assert _flags(unresolved.truth) == (False, False)
    assert "FACT_CONFLICT" in unresolved.reason_codes


def _monograph_formula_3(completeness: bool, violations: int) -> tuple[str, bool | None]:
    """Meaning of the proposed (3): status separate from Boolean value."""
    assert violations >= 0
    if not completeness:
        return "UNKNOWN", None
    return ("COMPLIANT", True) if violations == 0 else ("NON_COMPLIANT", False)


@pytest.mark.parametrize("complete", [False, True])
@pytest.mark.parametrize("violations", [0, 1, 3])
def test_formula_3_keeps_boolean_result_distinct_from_inspection_status(
    complete: bool, violations: int
) -> None:
    status, value = _monograph_formula_3(complete, violations)
    old_monograph_value = (
        1 if complete and violations == 0 else 0 if complete and violations > 0 else "U"
    )
    assert (1 if value is True else 0 if value is False else "U") == old_monograph_value
    assert (status == "UNKNOWN") == (not complete)


def _monograph_formula_7(possible_worlds: tuple[bool, ...]) -> str:
    """Two Boolean confirmations plus a PROCEDURAL applicability status."""
    confirmed_active = bool(possible_worlds) and all(possible_worlds)
    confirmed_inactive = bool(possible_worlds) and not any(possible_worlds)
    assert not (confirmed_active and confirmed_inactive)
    if confirmed_active:
        return "ACTIVE"
    if confirmed_inactive:
        return "INACTIVE"
    return "UNKNOWN"


def test_formula_7_matches_existing_possible_worlds_definition_31_cases() -> None:
    for count in range(5):
        for worlds in product((True, False), repeat=count):
            # The old monograph rule returned 1/0/U; the new status is not a
            # third truth value. This tests the conceptual formula only, not
            # the implementation's policy-closure/authority decision tree.
            legacy = 1 if worlds and all(worlds) else 0 if worlds and not any(worlds) else "U"
            mapping = {1: "ACTIVE", 0: "INACTIVE", "U": "UNKNOWN"}
            assert _monograph_formula_7(worlds) == mapping[legacy]


def _plan(*, hold: bool = False, reject: bool = False) -> OperationPlan:
    hold_reasons = ("TEST_UNRESOLVED",) if hold else ()
    reject_reasons = ("TEST_PROVEN_PROHIBITION",) if reject else ()
    payload = {
        "operations": [],
        "hold_reasons": list(hold_reasons),
        "reject_reasons": list(reject_reasons),
    }
    return OperationPlan(
        (), hold_reasons, reject_reasons, sha256_bytes(canonical_json_bytes(payload))
    )


def _binary_governance(
    *,
    input_status: str,
    invariant_verdicts: dict[str, str],
    plan: OperationPlan | dict[str, Any],
    coverage_status: str,
    candidate_validation: str | None,
    candidate_present: bool,
    cost_verdict: str,
    pipeline_authorized: bool,
    additional_reasons: tuple[str, ...] = (),
) -> str:
    """Independent Boolean classification matching SPEC03's stated precedence.

    CONFIRMED REJECT has precedence over unresolved evidence. In particular,
    'not all positive' is not equivalent to a confirmed prohibition.
    """
    hold_reasons = (
        tuple(plan.hold_reasons) if isinstance(plan, OperationPlan) else tuple(plan["hold_reasons"])
    )
    reject_reasons = (
        tuple(plan.reject_reasons)
        if isinstance(plan, OperationPlan)
        else tuple(plan["reject_reasons"])
    )
    if input_status == "INVALID":
        return "INPUT_REJECTED"
    proven_prohibition = (
        any(value == "FAIL" for value in invariant_verdicts.values())
        or bool(reject_reasons)
        or candidate_validation == "invalid"
        or cost_verdict == "FAIL"
        or (coverage_status == "INCOMPLETE" and candidate_validation == "valid")
    )
    if proven_prohibition:
        return "REJECT"
    confirmations = (
        pipeline_authorized,
        input_status == "VALID",
        candidate_present,
        candidate_validation == "valid",
        coverage_status == "COMPLETE",
        cost_verdict == "PASS",
        set(invariant_verdicts) == REQUIRED,
        all(value == "PASS" for value in invariant_verdicts.values()),
        not hold_reasons,
        not additional_reasons,
    )
    return "ACCEPT" if all(confirmations) else "HOLD"


def _coverage(status: str) -> Any:
    obligation = make_obligation()
    if status == "COMPLETE":
        pair, *_ = make_valid_pair()
        return make_coverage([obligation], pairs=[pair])
    if status == "UNKNOWN":
        return make_coverage(
            [obligation],
            statuses={str(obligation["id"]): ApplicabilityStatus.UNKNOWN},
        )
    assert status == "INCOMPLETE"
    return make_coverage([obligation])


@pytest.mark.parametrize(
    ("case", "changes"),
    [
        ("authorized_accept", {}),
        ("public_without_authority", {"public": True}),
        ("invalid_input_overrides_failure", {"input": "INVALID", "inv": "FAIL"}),
        ("unresolved_input", {"input": "UNDETERMINED"}),
        ("proven_constraint_failure", {"inv": "FAIL"}),
        ("unresolved_constraint", {"inv": "UNKNOWN"}),
        ("missing_constraint_verdict", {"missing_inv": True}),
        ("unresolved_coverage", {"coverage": "UNKNOWN"}),
        ("incomplete_validated_candidate", {"coverage": "INCOMPLETE"}),
        ("invalid_candidate", {"candidate": "invalid"}),
        ("candidate_not_validated", {"candidate": None}),
        ("absent_candidate", {"present": False, "candidate": None}),
        ("absent_candidate_proven_violation", {"present": False, "candidate": None, "inv": "FAIL"}),
        ("cost_limit_exceeded", {"cost": "FAIL"}),
        ("cost_unknown", {"cost": "UNKNOWN"}),
        ("hold_plan", {"hold": True}),
        ("reject_plan", {"reject": True}),
        ("hold_and_invariant_failure", {"hold": True, "inv": "FAIL"}),
        ("hold_and_cost_failure", {"hold": True, "cost": "FAIL"}),
        ("additional_missing_evidence", {"additional": True}),
    ],
)
def test_boolean_governance_matches_actual_decision_precedence(
    case: str, changes: dict[str, Any]
) -> None:
    del case  # Visible in pytest parameter IDs; no fixture-specific behavior.
    verdicts = {key: "PASS" for key in REQUIRED}
    if "inv" in changes:
        verdicts["INV-04"] = changes["inv"]
    if changes.get("missing_inv"):
        verdicts.pop("INV-12")
    input_status = changes.get("input", "VALID")
    candidate_validation = changes.get("candidate", "valid")
    candidate_present = changes.get("present", True)
    coverage = _coverage(changes.get("coverage", "COMPLETE"))
    plan = _plan(hold=changes.get("hold", False), reject=changes.get("reject", False))
    additional = ("BEFORE_APPLICABILITY_UNRESOLVED",) if changes.get("additional") else ()
    args: dict[str, Any] = {
        "method_version": "P_GOVERNED_ADAPTATION_DEVELOPMENT_V1",
        "architecture_before_sha": ARCH_BEFORE,
        "architecture_after_sha": ARCH_AFTER,
        "policy_source_revision": "SYN_POLICY_REV_1",
        "policy_ruleset_sha256": "5" * 64,
        "input_bundle_sha256": "6" * 64,
        "parent_configuration_sha256": "8" * 64,
        "candidate_configuration_sha256": "9" * 64 if candidate_present else None,
        "impact_assessment_sha256": "a" * 64,
        "coverage": coverage,
        "operation_plan": plan,
        "invariant_verdicts": verdicts,
        "cost_verdict": changes.get("cost", "PASS"),
        "input_status": input_status,
        "candidate_validation_status": candidate_validation,
        "additional_reasons": additional,
    }
    if changes.get("public"):
        decision = decide_governance(**args)
        authorized = False
    else:
        authorization = _issue_governance_pipeline_authorization(**args)
        decision = _decide_governance_authorized(**args, pipeline_authorization=authorization)
        authorized = authorization is not None

    expected = _binary_governance(
        input_status=input_status,
        invariant_verdicts=verdicts,
        plan=plan,
        coverage_status=coverage.status.value,
        candidate_validation=candidate_validation,
        candidate_present=candidate_present,
        cost_verdict=args["cost_verdict"],
        pipeline_authorized=authorized,
        additional_reasons=additional,
    )
    assert decision.result.value == expected


@pytest.mark.parametrize(
    ("scenario_id", "repetition"),
    list(product(ARCHIVED_OUTCOMES, (1, 2, 3))),
)
def test_binary_governance_reproduces_archived_a1_to_d2(scenario_id: str, repetition: int) -> None:
    """Check all recorded repetitions; D2 keeps HOLD oracle vs REJECT observation."""
    raw = json.loads(
        (ARCHIVE / f"{scenario_id}_method_p_rep_{repetition:02d}.json").read_text(encoding="utf-8")
    )["result"]
    governance = raw["governance"]
    verdicts: dict[str, str] = governance["invariant_verdicts"]
    plan = raw["operation_plan"]
    candidate_validation = raw["candidate_validation"]["status"]
    coverage = raw["candidate_coverage"] or raw["current_coverage"]
    assert coverage is not None

    # This archive was emitted by the verified pipeline. INV-05 is its
    # input/evidence-acceptance verdict; these fixtures contain no bad inputs.
    assert verdicts["INV-05"] in {"PASS", "UNKNOWN"}
    input_status = "VALID" if verdicts["INV-05"] == "PASS" else "UNDETERMINED"
    positive = (
        input_status == "VALID"
        and candidate_validation == "valid"
        and raw["candidate_sha256"] is not None
        and coverage["status"] == "COMPLETE"
        and not plan["hold_reasons"]
        and not plan["reject_reasons"]
        and governance["cost_verdict"] == "PASS"
        and set(verdicts) == REQUIRED
        and all(value == "PASS" for value in verdicts.values())
    )
    expected = _binary_governance(
        input_status=input_status,
        invariant_verdicts=verdicts,
        plan=plan,
        coverage_status=coverage["status"],
        candidate_validation=candidate_validation,
        candidate_present=raw["candidate_sha256"] is not None,
        cost_verdict=governance["cost_verdict"],
        pipeline_authorized=positive,
    )
    operations = raw["proposed_operations"]
    operation = (
        operations[0]
        if len(operations) == 1
        else "hold"
        if plan["hold_reasons"] or plan["reject_reasons"]
        else "none"
    )
    expected_operation, expected_governance = ARCHIVED_OUTCOMES[scenario_id]
    assert operation == expected_operation
    assert governance["result"] == expected_governance == expected
    assert (governance["result"] == "ACCEPT") == (expected == "ACCEPT")
    if scenario_id == "D2":
        assert "INVARIANT_VIOLATION_PROVEN" in governance["reason_codes"]
        assert plan["hold_reasons"]
        assert governance["result"] == "REJECT"
    if scenario_id == "D1":
        assert "UNKNOWN" in verdicts.values()
        assert governance["result"] == "HOLD"


def test_declared_d2_reference_remains_hold_not_retrospectively_relabelled() -> None:
    root = ARCHIVE.parent.parent
    author = json.loads((root / "reference_v1.json").read_text(encoding="utf-8"))
    reference = {row["scenario_id"]: row for row in author["cases"]}
    assert reference["D2"]["expected_operation"] == "hold"
    assert reference["D2"]["expected_governance"] == "HOLD"
    assert ARCHIVED_OUTCOMES["D2"] == ("hold", "REJECT")
