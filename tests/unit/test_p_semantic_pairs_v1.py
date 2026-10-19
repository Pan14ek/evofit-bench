"""Exact-pair validity, evidence, compliance separation and coverage tests."""

from __future__ import annotations

from dataclasses import replace

from experiments.execution.tooling.p_applicability import ApplicabilityStatus, ProofStatus
from experiments.execution.tooling.p_semantic import (
    ComplianceStatus,
    CoverageStatus,
    PairStatus,
    assess_mandatory_coverage,
    assess_pair,
)
from tests.unit.p_spec03_support import (
    ARCH_AFTER,
    make_applicability,
    make_evaluator_evidence,
    make_obligation,
    make_representation,
    make_valid_pair,
)


def test_positive_exact_pair_requires_artifact_and_external_semantic_proof() -> None:
    pair, _rep, _obligation, _artifacts, proof = make_valid_pair()
    assert pair.status is PairStatus.VALID
    assert pair.semantic_proof_status == ProofStatus.VALID.value
    assert pair.semantic_verifier_id == proof.verifier_id
    assert pair.evidence_artifacts
    assert pair.assessment_sha256


def test_zero_exit_without_resolved_inspected_subjects_is_vacuous() -> None:
    pair, *_ = make_valid_pair(
        evidence_changes={
            "configured_targets": [],
            "resolved_targets": [],
            "inspected_subjects": [],
        }
    )
    assert pair.status is PairStatus.INVALID
    assert "VACUOUS_SUCCESS" in pair.reason_codes


def test_unreported_inspection_scope_remains_unknown_without_invented_zero() -> None:
    pair, *_ = make_valid_pair(
        evidence_changes={
            "configured_targets": [],
            "resolved_targets": [],
            "inspected_subjects": [],
            "inspected_edge_count": None,
        }
    )
    assert pair.status is PairStatus.UNKNOWN
    assert "EVALUATOR_INSPECTION_SCOPE_UNKNOWN" in pair.reason_codes
    assert "VACUOUS_SUCCESS" not in pair.reason_codes


def test_wrong_stage_architecture_or_mapping_never_reuses_pair_proof() -> None:
    wrong_stage, *_ = make_valid_pair(evidence_changes={"stage_applicable": False})
    wrong_revision, *_ = make_valid_pair(
        evidence_changes={
            "architecture_source_sha": "9999999999999999999999999999999999999999",
        }
    )
    assert wrong_stage.status is PairStatus.INVALID
    assert wrong_revision.status is PairStatus.INVALID
    assert "STAGE_OR_CONTEXT_MISMATCH" in wrong_stage.reason_codes
    assert "ARCHITECTURE_REVISION_MISMATCH" in wrong_revision.reason_codes


def test_clean_nonzero_exit_records_noncompliance_without_invalidating_monitor_semantics() -> None:
    pair, *_ = make_valid_pair(process_exit_code=2)
    assert pair.status is PairStatus.VALID
    assert pair.compliance_status is ComplianceStatus.NON_COMPLIANT
    assert "COMPLIANCE_VIOLATION_OBSERVED" in pair.reason_codes


def test_evaluator_infrastructure_failure_is_unknown_and_not_a_compliance_verdict() -> None:
    pair, *_ = make_valid_pair(
        evidence_changes={
            "infrastructure_status": "infrastructure_failure",
            "process_exit_code": None,
        }
    )
    assert pair.status is PairStatus.UNKNOWN
    assert pair.compliance_status is ComplianceStatus.UNKNOWN


def test_missing_evidence_or_artifact_bytes_is_unknown_not_covered() -> None:
    pair, rep, obligation, artifacts, proof = make_valid_pair()
    evidence, artifacts = make_evaluator_evidence(rep, obligation_id=obligation["id"])
    evidence_artifact_path = evidence["evidence_artifacts"][0]["path"]
    evaluator_artifact_path = rep["evaluator_artifact"]["path"]
    without_evidence_artifact = {
        path: content for path, content in artifacts.items() if path != evidence_artifact_path
    }
    missing_bytes = assess_pair(
        representation=rep,
        obligation=obligation,
        architecture_source_sha=ARCH_AFTER,
        evaluator_evidence=evidence,
        semantic_proof=proof,
        artifact_bytes=without_evidence_artifact,
        source_digests={"SYN_SOURCE_FACT": "6" * 64},
    )
    assert pair.status is PairStatus.VALID
    assert missing_bytes.status is PairStatus.UNKNOWN
    assert evaluator_artifact_path in without_evidence_artifact


def test_wrong_obligation_identity_cannot_borrow_same_metric_evidence() -> None:
    _pair, rep, obligation, _artifacts, proof = make_valid_pair()
    other = make_obligation(id="SYN_OBL_OTHER", criterion="SYN_CRIT_AUDIT")
    rep["covers"] = ["SYN_OBL_TRACE", "SYN_OBL_OTHER"]
    evidence, artifacts = make_evaluator_evidence(rep, obligation_id=obligation["id"])
    assessment = assess_pair(
        representation=rep,
        obligation=other,
        architecture_source_sha=ARCH_AFTER,
        evaluator_evidence=evidence,
        semantic_proof=proof,
        artifact_bytes=artifacts,
        source_digests={"SYN_SOURCE_FACT": "6" * 64},
    )
    assert assessment.status is PairStatus.INVALID
    assert assessment.obligation_id == "SYN_OBL_OTHER"


def test_semantic_compatibility_unknown_is_not_a_valid_pair() -> None:
    pair, *_ = make_valid_pair(evidence_changes={"semantic_compatible": None})
    assert pair.status is PairStatus.UNKNOWN
    assert "SEMANTIC_COMPATIBILITY_UNKNOWN" in pair.reason_codes


def test_same_valid_pair_counts_once_and_unknown_mandate_blocks_coverage() -> None:
    first, rep, obligation, artifacts, proof = make_valid_pair()
    second_rep = make_representation(id="REP_SYNTH_TRACE_BACKUP")
    second, *_ = make_valid_pair(representation=second_rep)
    applicability = make_applicability({"SYN_OBL_TRACE": ApplicabilityStatus.ACTIVE})
    complete = assess_mandatory_coverage(
        applicability=applicability,
        obligations=[obligation],
        pair_assessments=[first, second],
    )
    assert complete.status is CoverageStatus.COMPLETE
    assert complete.mandatory_total == complete.mandatory_covered == 1
    unresolved = assess_mandatory_coverage(
        applicability=make_applicability({"SYN_OBL_TRACE": ApplicabilityStatus.UNKNOWN}),
        obligations=[obligation],
        pair_assessments=[first],
    )
    assert unresolved.status is CoverageStatus.UNKNOWN
    assert unresolved.obligations[0].applicability_status == "UNKNOWN"


def test_stale_pair_architecture_revision_cannot_satisfy_coverage() -> None:
    pair, _rep, obligation, *_ = make_valid_pair()
    stale = replace(pair, architecture_source_sha="9999999999999999999999999999999999999999")
    coverage = assess_mandatory_coverage(
        applicability=make_applicability({obligation["id"]: ApplicabilityStatus.ACTIVE}),
        obligations=[obligation],
        pair_assessments=[stale],
    )
    assert coverage.status is CoverageStatus.UNKNOWN
    assert coverage.obligations[0].status == "UNKNOWN"
    assert "PAIR_ARCHITECTURE_REVISION_MISMATCH" in coverage.obligations[0].reason_codes


def test_conflicting_assessments_for_same_pair_cannot_count_as_valid() -> None:
    valid, _rep, obligation, *_ = make_valid_pair()
    invalid, *_ = make_valid_pair(evidence_changes={"stage_applicable": False})
    coverage = assess_mandatory_coverage(
        applicability=make_applicability({obligation["id"]: ApplicabilityStatus.ACTIVE}),
        obligations=[obligation],
        pair_assessments=[valid, invalid],
    )
    assert coverage.status is CoverageStatus.UNKNOWN
    assert coverage.obligations[0].status == "UNKNOWN"
    assert coverage.obligations[0].valid_pair_ids == ()
    assert "PAIR_ASSESSMENT_CONFLICT" in coverage.obligations[0].reason_codes


def test_same_status_pair_records_with_different_stages_are_conflicting() -> None:
    first, _rep, obligation, *_ = make_valid_pair()
    second, *_ = make_valid_pair(representation=make_representation(stage="runtime"))
    assert first.status is PairStatus.VALID
    assert second.status is PairStatus.VALID
    assert first.representation_id == second.representation_id
    assert first.stage != second.stage
    coverage = assess_mandatory_coverage(
        applicability=make_applicability({obligation["id"]: ApplicabilityStatus.ACTIVE}),
        obligations=[obligation],
        pair_assessments=[first, second],
        required_stages={obligation["id"]: ["ci", "runtime"]},
        stage_contract_verified=True,
    )
    assert coverage.status is CoverageStatus.UNKNOWN
    assert coverage.obligations[0].valid_pair_ids == ()
    assert "PAIR_ASSESSMENT_CONFLICT" in coverage.obligations[0].reason_codes


def test_mutated_pair_status_with_stale_digest_cannot_count_as_valid() -> None:
    valid, _rep, obligation, *_ = make_valid_pair()
    tampered = replace(valid, status=PairStatus.INVALID)
    coverage = assess_mandatory_coverage(
        applicability=make_applicability({obligation["id"]: ApplicabilityStatus.ACTIVE}),
        obligations=[obligation],
        pair_assessments=[valid, tampered],
    )
    assert coverage.status is CoverageStatus.UNKNOWN
    assert coverage.obligations[0].valid_pair_ids == ()
    assert "PAIR_ASSESSMENT_DIGEST_MISMATCH" in coverage.obligations[0].reason_codes


def test_high_score_or_covers_declaration_cannot_replace_exact_pair_evidence() -> None:
    representation = make_representation()
    obligation = make_obligation()
    coverage = assess_mandatory_coverage(
        applicability=make_applicability({"SYN_OBL_TRACE": ApplicabilityStatus.ACTIVE}),
        obligations=[obligation],
        pair_assessments=[],
    )
    assert "covers" in representation
    assert coverage.status is CoverageStatus.INCOMPLETE
    assert coverage.mandatory_covered == 0


def test_required_stage_set_needs_independent_stage_contract() -> None:
    pair, _rep, obligation, _artifacts, _proof = make_valid_pair()
    coverage = assess_mandatory_coverage(
        applicability=make_applicability({"SYN_OBL_TRACE": ApplicabilityStatus.ACTIVE}),
        obligations=[obligation],
        pair_assessments=[pair],
        required_stages={"SYN_OBL_TRACE": ["ci", "runtime"]},
        stage_contract_verified=None,
    )
    assert coverage.status is CoverageStatus.UNKNOWN
    assert "STAGE_CONTRACT_UNVERIFIED" in coverage.obligations[0].reason_codes
