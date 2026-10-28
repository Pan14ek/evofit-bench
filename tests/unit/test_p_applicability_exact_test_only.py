"""Adversarial checks for versioned exact-set TEST_ONLY policy closure."""

from __future__ import annotations

import copy
from typing import Any

import pytest

from experiments.execution.tooling.hashing import canonical_json_bytes, sha256_bytes
from experiments.execution.tooling.p_applicability import (
    EvidenceLedger,
    EvidenceProof,
    ProofStatus,
)
from experiments.execution.tooling.p_applicability_c2_v2 import verify_exact_test_only_claims
from experiments.execution.tooling.p_governance import GovernanceResult, decide_governance
from experiments.execution.tooling.p_operations import OperationPlan
from tests.unit.p_spec03_support import (
    ARCH_AFTER,
    ARCH_BEFORE,
    make_coverage,
    make_obligation,
    make_valid_pair,
)

PROFILE_ID = "TEST_ONLY_EXACT_SET_PROFILE_V2"
SCOPE = "application"
SOURCE_ID = "EXACT_SCOPE_SOURCE"
SOURCE_SHA = "a" * 64
SELECTED = frozenset({"SYN_Q_A", "SYN_Q_B"})
AS_OF = "2026-10-28T00:00:00Z"


def _fixture() -> tuple[dict[str, Any], EvidenceLedger]:
    claims: list[dict[str, Any]] = []
    proofs: dict[str, EvidenceProof] = {}
    for obligation_id in sorted(SELECTED):
        for state, revision in (("before", ARCH_BEFORE), ("after", ARCH_AFTER)):
            claim_id = f"CLAIM_{state}_{obligation_id}"
            claim = {
                "id": claim_id,
                "kind": "AUTHORITATIVE_POLICY_REGISTRY",
                "fact_type": f"obligation:{obligation_id}",
                "state": state,
                "scope": SCOPE,
                "architecture_revision": revision,
                "policy_registry_version": PROFILE_ID,
                "as_of": AS_OF,
                "assumptions": [f"bounded_obligation_universe:{obligation_id}"],
                "evidence_source_ids": [SOURCE_ID],
            }
            claims.append(claim)
            proofs[claim_id] = EvidenceProof(
                ProofStatus.VALID,
                sha256_bytes(canonical_json_bytes(claim)),
                ((SOURCE_ID, SOURCE_SHA),),
                PROFILE_ID,
                ("EXACT_SCOPE_DECLARATION",),
            )
    snapshot = {
        "schema_version": "1.2",
        "architecture": {
            "before_commit": ARCH_BEFORE,
            "after_commit": ARCH_AFTER,
            "evaluation_as_of": AS_OF,
        },
        "sources": [{"id": SOURCE_ID, "sha256": SOURCE_SHA}],
        "completeness_claims": claims,
    }
    registry = {
        "closure": "CLAIMED_CLOSED",
        "closure_claim_ids": [row["id"] for row in claims],
        "registry_version": PROFILE_ID,
        "scope": SCOPE,
        "as_of": AS_OF,
    }
    snapshot["policy_registry"] = registry
    return snapshot, EvidenceLedger({}, {}, proofs)


def _verify(
    snapshot: dict[str, Any],
    ledger: EvidenceLedger,
    selected: frozenset[str] = SELECTED,
) -> tuple[bool, set[str], set[str], set[str]]:
    return verify_exact_test_only_claims(
        snapshot,
        selected,
        PROFILE_ID,
        SCOPE,
        ledger,
    )


def test_exact_test_only_closure_accepts_only_the_fully_bound_selected_set() -> None:
    snapshot, ledger = _fixture()

    valid, reasons, refs, unresolved = _verify(snapshot, ledger)

    assert valid is True
    assert reasons == set()
    assert "CLAIM_after_SYN_Q_A" in refs
    assert unresolved == set()


def test_missing_selected_obligation_fails_closed() -> None:
    snapshot, ledger = _fixture()

    valid, reasons, _refs, unresolved = _verify(snapshot, ledger, SELECTED | {"SYN_Q_MISSING"})

    assert valid is False
    assert "POLICY_CLOSURE_UNVERIFIED" in reasons
    assert unresolved == set(snapshot["policy_registry"]["closure_claim_ids"])


@pytest.mark.parametrize("attack", ["duplicate_id", "conflicting_row"])
def test_duplicate_or_conflicting_closure_claim_fails_closed(attack: str) -> None:
    snapshot, ledger = _fixture()
    claim = copy.deepcopy(snapshot["completeness_claims"][0])
    if attack == "duplicate_id":
        snapshot["policy_registry"]["closure_claim_ids"].append(
            snapshot["policy_registry"]["closure_claim_ids"][0]
        )
    else:
        claim["fact_type"] = "obligation:SYN_Q_OUTSIDE"
        claim["assumptions"] = ["bounded_obligation_universe:SYN_Q_OUTSIDE"]
        snapshot["completeness_claims"].append(claim)

    valid, reasons, _refs, _unresolved = _verify(snapshot, ledger)

    assert valid is False
    assert "POLICY_CLOSURE_UNVERIFIED" in reasons


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("architecture_revision", "f" * 40),
        ("scope", "another-scope"),
    ],
)
def test_wrong_revision_or_scope_fails_closed(field: str, value: str) -> None:
    snapshot, ledger = _fixture()
    claim = next(row for row in snapshot["completeness_claims"] if row["state"] == "after")
    claim[field] = value

    valid, reasons, _refs, _unresolved = _verify(snapshot, ledger)

    assert valid is False
    assert "POLICY_CLOSURE_UNVERIFIED" in reasons


@pytest.mark.parametrize("provenance", ["missing", "invalid"])
def test_missing_or_invalid_source_provenance_fails_closed(provenance: str) -> None:
    snapshot, ledger = _fixture()
    claim_id = "CLAIM_after_SYN_Q_A"
    proofs = dict(ledger.completeness_proofs)
    if provenance == "missing":
        proofs.pop(claim_id)
    else:
        valid_proof = proofs[claim_id]
        proofs[claim_id] = EvidenceProof(
            ProofStatus.INVALID,
            valid_proof.subject_sha256,
            valid_proof.source_bindings,
            valid_proof.verifier_id,
            valid_proof.evidence_refs,
        )
    invalid_ledger = EvidenceLedger({}, {}, proofs)

    valid, reasons, _refs, _unresolved = _verify(snapshot, invalid_ledger)

    assert valid is False
    assert "POLICY_CLOSURE_UNVERIFIED" in reasons


def test_universal_or_out_of_universe_closure_claim_is_rejected() -> None:
    snapshot, ledger = _fixture()
    claim = snapshot["completeness_claims"][0]
    claim["fact_type"] = "obligation:all"
    claim["assumptions"] = ["bounded_obligation_universe:all"]

    valid, reasons, _refs, _unresolved = _verify(snapshot, ledger)

    assert valid is False
    assert "POLICY_CLOSURE_UNVERIFIED" in reasons


@pytest.mark.parametrize("verdict", ["UNKNOWN", "FAIL"])
def test_exact_scope_does_not_override_unknown_or_failed_mandatory_invariants(
    verdict: str,
) -> None:
    obligation = make_obligation()
    pair, *_ = make_valid_pair(obligation=obligation)
    coverage = make_coverage([obligation], pairs=[pair])
    invariant_verdicts = {f"INV-{index:02d}": "PASS" for index in range(1, 13)}
    invariant_verdicts["INV-04"] = verdict
    body: dict[str, object] = {"operations": [], "hold_reasons": [], "reject_reasons": []}
    empty_plan = OperationPlan((), (), (), sha256_bytes(canonical_json_bytes(body)))

    decision = decide_governance(
        method_version="P_GOVERNED_ADAPTATION_DEVELOPMENT_V2_TEST_ONLY_EXACT_SET",
        architecture_before_sha=ARCH_BEFORE,
        architecture_after_sha=ARCH_AFTER,
        policy_source_revision=PROFILE_ID,
        policy_ruleset_sha256="1" * 64,
        input_bundle_sha256="2" * 64,
        parent_configuration_sha256="3" * 64,
        candidate_configuration_sha256="4" * 64,
        impact_assessment_sha256="5" * 64,
        coverage=coverage,
        operation_plan=empty_plan,
        invariant_verdicts=invariant_verdicts,
        cost_verdict="PASS",
        input_status="VALID",
        candidate_validation_status="valid",
    )

    assert decision.result is (
        GovernanceResult.HOLD if verdict == "UNKNOWN" else GovernanceResult.REJECT
    )
    expected_reason = (
        "INVARIANT_VERDICTS_NOT_ALL_POSITIVE"
        if verdict == "UNKNOWN"
        else "INVARIANT_VIOLATION_PROVEN"
    )
    assert expected_reason in decision.to_dict()["reason_codes"]
