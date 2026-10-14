"""Policy resolution tests using synthetic SPEC 01 snapshots and verifier proofs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

from experiments.execution.tooling.contracts import load_schema
from experiments.execution.tooling.errors import ContractValidationError
from experiments.execution.tooling.p_applicability import (
    ApplicabilityAssessment,
    ApplicabilityStatus,
    CompiledRuleset,
    ObligationResult,
    ProofStatus,
    _combined_policy_bindings,
    _override_binding,
    evaluate_obligations,
    load_and_validate_ruleset,
)
from experiments.execution.tooling.p_input_validation import ValidationStatus, load_fact_vocabulary
from tests.unit.p_applicability_support import (
    add_policy,
    close_registry_for,
    evidence_ledger,
    proof_for,
    validation_result,
)
from tests.unit.p_applicability_support import (
    snapshot_fixture as _snapshot_fixture,
)

RULESET = Path("experiments/execution/contracts/applicability_ruleset_v1.json")
CATALOG = Path("fitness/catalog/architectural-obligations.yaml")


def snapshot_fixture() -> dict[str, Any]:
    """Return a fixture with no preexisting policy rows for isolated scenarios."""
    snapshot = _snapshot_fixture()
    snapshot["policies"] = []
    return snapshot


def _rules() -> CompiledRuleset:
    return load_and_validate_ruleset(RULESET, load_fact_vocabulary(), CATALOG)


def _assess(snapshot: dict[str, Any], **ledger_options: Any) -> ApplicabilityAssessment:
    return evaluate_obligations(
        snapshot,
        _rules(),
        evidence_ledger(snapshot, **ledger_options),
        "after",
        validation_result(),
    )


def _row(report: ApplicabilityAssessment, obligation_id: str) -> ObligationResult:
    return next(item for item in report.results if item.obligation_id == obligation_id)


def _closed(snapshot: dict[str, Any], obligation_id: str) -> None:
    close_registry_for(snapshot, obligation_id)


def test_verified_unconditional_mandate_is_active_and_report_has_all_18_rows() -> None:
    snapshot = snapshot_fixture()
    _closed(snapshot, "AC_PUBLIC_API")
    policy = add_policy(snapshot, policy_id="POL_PUBLIC_API")

    report = _assess(snapshot)
    result = _row(report, "AC_PUBLIC_API")

    assert result.status is ApplicabilityStatus.ACTIVE
    assert result.contributing_policy_ids == (policy["id"],)
    assert len(report.results) == 18
    assert len({item.obligation_id for item in report.results}) == 18
    Draft202012Validator.check_schema(load_schema("applicability_assessment_v1.schema.json"))
    Draft202012Validator(load_schema("applicability_assessment_v1.schema.json")).validate(
        report.to_dict()
    )


def test_closed_empty_registry_and_draft_policy_are_inactive() -> None:
    snapshot = snapshot_fixture()
    _closed(snapshot, "AC_PUBLIC_API")
    add_policy(snapshot, policy_id="POL_DRAFT", status="DRAFT")

    result = _row(_assess(snapshot), "AC_PUBLIC_API")

    assert result.status is ApplicabilityStatus.INACTIVE
    assert "APPLICABILITY_INACTIVE_PROVEN" in result.reason_codes


def test_open_registry_and_missing_policy_proof_remain_unknown() -> None:
    open_snapshot = snapshot_fixture()
    add_policy(open_snapshot, policy_id="POL_OPEN")
    open_result = _row(_assess(open_snapshot), "AC_PUBLIC_API")
    assert open_result.status is ApplicabilityStatus.UNKNOWN
    assert "POLICY_REGISTRY_OPEN" in open_result.reason_codes

    unverified_snapshot = snapshot_fixture()
    _closed(unverified_snapshot, "AC_PUBLIC_API")
    add_policy(unverified_snapshot, policy_id="POL_UNVERIFIED")
    unverified_result = _row(
        _assess(unverified_snapshot, policy_statuses={"POL_UNVERIFIED": ProofStatus.UNDETERMINED}),
        "AC_PUBLIC_API",
    )
    assert unverified_result.status is ApplicabilityStatus.UNKNOWN
    assert "POLICY_APPROVAL_UNVERIFIED" in unverified_result.reason_codes


def test_registry_closure_accepts_family_and_catalog_bound_universal_claims() -> None:
    rules = _rules()
    obligation = rules.obligations[0]
    family_snapshot = snapshot_fixture()
    close_registry_for(
        family_snapshot,
        obligation.obligation_id,
        fact_type=f"obligation_family:{obligation.criterion}",
    )
    add_policy(family_snapshot, policy_id="POL_FAMILY", obligation_id=obligation.obligation_id)
    assert (
        _row(_assess(family_snapshot), obligation.obligation_id).status
        is ApplicabilityStatus.ACTIVE
    )

    universal_snapshot = snapshot_fixture()
    close_registry_for(
        universal_snapshot,
        obligation.obligation_id,
        fact_type="obligation:all",
        assumptions=[f"obligation_catalog_sha256:{rules.obligation_catalog_sha256}"],
    )
    add_policy(universal_snapshot, policy_id="POL_ALL", obligation_id=obligation.obligation_id)
    assert (
        _row(_assess(universal_snapshot), obligation.obligation_id).status
        is ApplicabilityStatus.ACTIVE
    )

    unbound_snapshot = snapshot_fixture()
    close_registry_for(
        unbound_snapshot,
        obligation.obligation_id,
        fact_type="obligation:all",
        assumptions=["obligation_catalog_sha256:" + "0" * 64],
    )
    add_policy(unbound_snapshot, policy_id="POL_UNBOUND", obligation_id=obligation.obligation_id)
    assert (
        _row(_assess(unbound_snapshot), obligation.obligation_id).status
        is ApplicabilityStatus.UNKNOWN
    )


@pytest.mark.parametrize(
    ("unit_count", "expected"),
    [(2, ApplicabilityStatus.ACTIVE), (1, ApplicabilityStatus.INACTIVE)],
)
def test_conditional_policy_uses_typed_fact_truth(
    unit_count: int, expected: ApplicabilityStatus
) -> None:
    snapshot = snapshot_fixture()
    _closed(snapshot, "AC_PUBLIC_API")
    deployment = next(fact for fact in snapshot["facts"] if fact["id"] == "F_DEPLOYMENT")
    deployment["value"] = unit_count
    add_policy(
        snapshot,
        policy_id="POL_CONDITIONAL",
        kind="CONDITIONAL_MANDATE",
        condition_ref="COND_DECLARED_MULTI_UNIT",
    )

    result = _row(_assess(snapshot), "AC_PUBLIC_API")

    assert result.status is expected
    assert result.condition_ids == ("COND_DECLARED_MULTI_UNIT",)


def test_unknown_condition_and_expired_or_revoked_policy_do_not_create_active() -> None:
    unknown_snapshot = snapshot_fixture()
    _closed(unknown_snapshot, "AC_PUBLIC_API")
    add_policy(
        unknown_snapshot,
        policy_id="POL_CONDITION_UNKNOWN",
        kind="CONDITIONAL_MANDATE",
        condition_ref="COND_HAS_CAPABILITY_MODULE",
    )
    unknown = _row(_assess(unknown_snapshot), "AC_PUBLIC_API")
    assert unknown.status is ApplicabilityStatus.UNKNOWN
    assert "CONDITION_UNKNOWN" in unknown.reason_codes

    expired_snapshot = snapshot_fixture()
    _closed(expired_snapshot, "AC_PUBLIC_API")
    add_policy(
        expired_snapshot,
        policy_id="POL_EXPIRED",
        effective_until="2026-10-12T00:00:00Z",
    )
    assert _row(_assess(expired_snapshot), "AC_PUBLIC_API").status is ApplicabilityStatus.INACTIVE

    revoked_snapshot = snapshot_fixture()
    _closed(revoked_snapshot, "AC_PUBLIC_API")
    add_policy(revoked_snapshot, policy_id="POL_REVOKED", status="REVOKED")
    assert _row(_assess(revoked_snapshot), "AC_PUBLIC_API").status is ApplicabilityStatus.INACTIVE


def test_known_true_mandate_dominates_unknown_independent_mandates() -> None:
    snapshot = snapshot_fixture()
    _closed(snapshot, "AC_PUBLIC_API")
    known = add_policy(snapshot, policy_id="POL_KNOWN_TRUE")
    add_policy(
        snapshot,
        policy_id="POL_UNKNOWN_CONDITION",
        kind="CONDITIONAL_MANDATE",
        condition_ref="COND_HAS_CAPABILITY_MODULE",
    )

    result = _row(_assess(snapshot), "AC_PUBLIC_API")

    assert result.status is ApplicabilityStatus.ACTIVE
    assert result.contributing_policy_ids == (known["id"],)
    assert "CONDITION_UNKNOWN" in result.reason_codes


def test_unresolved_override_on_one_mandate_does_not_hide_another_true_mandate() -> None:
    snapshot = snapshot_fixture()
    _closed(snapshot, "AC_PUBLIC_API")
    first = add_policy(snapshot, policy_id="POL_TARGET")
    second = add_policy(snapshot, policy_id="POL_INDEPENDENT")
    add_policy(
        snapshot,
        policy_id="POL_UNVERIFIED_EXCEPTION",
        kind="EXCEPTION",
        target_policy_ids=[str(first["id"])],
    )

    result = _row(_assess(snapshot), "AC_PUBLIC_API")

    assert result.status is ApplicabilityStatus.ACTIVE
    assert result.contributing_policy_ids == (second["id"],)
    assert "OVERRIDE_UNRESOLVED" in result.reason_codes


def test_only_valid_named_override_suppresses_its_target_policy() -> None:
    snapshot = snapshot_fixture()
    _closed(snapshot, "AC_PUBLIC_API")
    mandate = add_policy(snapshot, policy_id="POL_MANDATE")
    override = add_policy(
        snapshot,
        policy_id="POL_EXCEPTION",
        kind="EXCEPTION",
        target_policy_ids=[str(mandate["id"])],
    )
    source_ids = [
        "REGISTRY",
        str(mandate["approval_source_id"]),
        str(override["approval_source_id"]),
        "CHARTER",
    ]
    pair_proof = proof_for(
        ProofStatus.VALID,
        _override_binding(override, mandate),
        snapshot,
        source_ids,
    )
    result = _row(
        _assess(snapshot, override_proofs={(str(override["id"]), str(mandate["id"])): pair_proof}),
        "AC_PUBLIC_API",
    )
    assert result.status is ApplicabilityStatus.INACTIVE


def test_missing_or_unauthorized_override_proof_cannot_suppress_mandate() -> None:
    snapshot = snapshot_fixture()
    _closed(snapshot, "AC_PUBLIC_API")
    mandate = add_policy(snapshot, policy_id="POL_MANDATE")
    add_policy(
        snapshot,
        policy_id="POL_EXCEPTION",
        kind="EXCEPTION",
        target_policy_ids=[str(mandate["id"])],
    )
    missing = _row(_assess(snapshot), "AC_PUBLIC_API")
    assert missing.status is ApplicabilityStatus.UNKNOWN
    assert "OVERRIDE_UNRESOLVED" in missing.reason_codes

    unauthorized = _row(
        _assess(snapshot, policy_statuses={"POL_EXCEPTION": ProofStatus.INVALID}),
        "AC_PUBLIC_API",
    )
    assert unauthorized.status is ApplicabilityStatus.ACTIVE
    assert "POLICY_APPROVAL_UNVERIFIED" in unauthorized.reason_codes


def test_opposite_polarity_policies_conflict_without_precedence_and_resolve_with_proof() -> None:
    snapshot = snapshot_fixture()
    _closed(snapshot, "AC_PUBLIC_API")
    required = add_policy(snapshot, policy_id="POL_REQUIRED", polarity="REQUIRED")
    forbidden = add_policy(snapshot, policy_id="POL_FORBIDDEN", polarity="FORBIDDEN")
    conflict = _row(_assess(snapshot), "AC_PUBLIC_API")
    assert conflict.status is ApplicabilityStatus.UNKNOWN
    assert "POLICY_CONFLICT" in conflict.reason_codes

    subject = {"higher_policy_id": str(required["id"]), "lower_policy_id": str(forbidden["id"])}
    bindings = _combined_policy_bindings(snapshot, required, forbidden)
    precedence_proof = proof_for(
        ProofStatus.VALID,
        subject,
        snapshot,
        [source_id for source_id, _digest in bindings],
    )
    resolved = _row(
        _assess(
            snapshot,
            precedence_proofs={(str(required["id"]), str(forbidden["id"])): precedence_proof},
        ),
        "AC_PUBLIC_API",
    )
    assert resolved.status is ApplicabilityStatus.ACTIVE
    assert "POLICY_CONFLICT" not in resolved.reason_codes


def test_closure_proof_scope_revision_and_authority_are_required() -> None:
    snapshot = snapshot_fixture()
    claim = close_registry_for(snapshot, "AC_PUBLIC_API")
    add_policy(snapshot, policy_id="POL_AUTHORITY")
    claim["architecture_revision"] = snapshot["architecture"]["before_commit"]

    result = _row(_assess(snapshot), "AC_PUBLIC_API")

    assert result.status is ApplicabilityStatus.UNKNOWN
    assert "POLICY_CLOSURE_UNVERIFIED" in result.reason_codes

    authority_missing = snapshot_fixture()
    _closed(authority_missing, "AC_PUBLIC_API")
    add_policy(authority_missing, policy_id="POL_NO_CHARTER_PROOF")
    ledger = evidence_ledger(authority_missing)
    from dataclasses import replace

    no_charter = replace(ledger, charter_proof=None)
    report = evaluate_obligations(
        authority_missing, _rules(), no_charter, "after", validation_result()
    )
    assert _row(report, "AC_PUBLIC_API").status is ApplicabilityStatus.UNKNOWN


def test_invalid_spec01_semantic_gate_rejects_applicability_evaluation() -> None:
    from dataclasses import replace

    snapshot = snapshot_fixture()
    _closed(snapshot, "AC_PUBLIC_API")
    rejected = replace(validation_result(), authority_status=ValidationStatus.INVALID)

    with pytest.raises(ContractValidationError, match="semantic gates: authority"):
        evaluate_obligations(
            snapshot,
            _rules(),
            evidence_ledger(snapshot),
            "after",
            rejected,
        )


def test_duplicate_policy_identifiers_are_unknown() -> None:
    snapshot = snapshot_fixture()
    _closed(snapshot, "AC_PUBLIC_API")
    add_policy(snapshot, policy_id="POL_DUPLICATE")
    add_policy(snapshot, policy_id="POL_DUPLICATE")

    result = _row(_assess(snapshot), "AC_PUBLIC_API")

    assert result.status is ApplicabilityStatus.UNKNOWN
    assert "INPUT_CONFLICT" in result.reason_codes


def test_registry_claim_for_other_obligation_does_not_close_this_catalog_row() -> None:
    snapshot = snapshot_fixture()
    close_registry_for(snapshot, "NOT_IN_CATALOG")
    add_policy(snapshot, policy_id="POL_PUBLIC_API")

    result = _row(_assess(snapshot), "AC_PUBLIC_API")

    assert result.status is ApplicabilityStatus.UNKNOWN
    assert "POLICY_CLOSURE_UNVERIFIED" in result.reason_codes
